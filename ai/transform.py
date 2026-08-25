"""
transform.py
Converts raw_messages.jsonl → training_data.jsonl
Handles both goodlobang and sgfooddeals channel formats.
"""

import json
import re
from datetime import datetime
from pathlib import Path

INPUT_FILE  = "raw_messages.jsonl"
OUTPUT_FILE = "training_data.jsonl"

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ref_year(posted_at: str) -> int:
    try:
        return datetime.fromisoformat(posted_at).year
    except Exception:
        return datetime.utcnow().year


def clean_md(text: str) -> str:
    """Strip markdown bold/italic markers and collapse whitespace."""
    text = re.sub(r"\*+|__", "", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_emoji(text: str) -> str:
    """Remove emoji / symbol characters, collapse whitespace."""
    cleaned = re.sub(
        r"["
        r"\U0001F000-\U0001FFFF"
        r"\U00010000-\U0010FFFF"
        r"\u2600-\u27BF"
        r"\u2B00-\u2BFF"
        r"\uFE00-\uFEFF"
        r"]+",
        "", text, flags=re.UNICODE
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_date(text: str, ref_year: int) -> str | None:
    if not text:
        return None
    text = text.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3,9})(?:\s+(\d{4}))?", text)
    if m:
        day = int(m.group(1))
        mon = MONTH_MAP.get(m.group(2)[:3].lower())
        year = int(m.group(3)) if m.group(3) else ref_year
        if mon:
            return f"{year}-{mon:02d}-{day:02d}"
    m = re.match(r"([A-Za-z]{3,9})\s+(\d{1,2})(?:\s+(\d{4}))?", text)
    if m:
        mon = MONTH_MAP.get(m.group(1)[:3].lower())
        day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else ref_year
        if mon:
            return f"{year}-{mon:02d}-{day:02d}"
    return None


def parse_date_range(raw: str, ref_year: int) -> tuple[str | None, str | None]:
    """Parse a date string into (valid_from, valid_to)."""
    raw = raw.strip()

    # "Now till dd Mon" or "Now - dd Mon"
    m = re.match(r"now\s+(?:till|[-–])\s+(.+)", raw, re.IGNORECASE)
    if not m:
        m = re.match(r"now\s*[-–]\s*(.+)", raw, re.IGNORECASE)
    if m:
        rest = m.group(1).strip()
        parts = rest.split()
        date_str = parts[0] + (" " + parts[1] if len(parts) > 1 else "")
        return None, parse_date(date_str, ref_year)

    # "dd Mon, HH - dd Mon, HH" (Live Nation style)
    m = re.match(
        r"(\d{1,2}\s+[A-Za-z]{3})[,\s]+[\d:\.apm\s]+-\s*(\d{1,2}\s+[A-Za-z]{3})",
        raw, re.IGNORECASE
    )
    if m:
        return parse_date(m.group(1), ref_year), parse_date(m.group(2), ref_year)

    # "dd - dd Mon" same month
    m = re.match(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]{3,9})", raw)
    if m:
        mon = m.group(3)
        return (parse_date(f"{m.group(1)} {mon}", ref_year),
                parse_date(f"{m.group(2)} {mon}", ref_year))

    # "dd Mon - dd Mon [yyyy]"
    m = re.match(
        r"(\d{1,2}\s+[A-Za-z]{3,9})\s*[-–]\s*(\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?)",
        raw
    )
    if m:
        return parse_date(m.group(1), ref_year), parse_date(m.group(2), ref_year)

    # Single date "dd Mon"
    if re.search(r"today", raw, re.IGNORECASE):
        return None, None
    parts = raw.split()
    if len(parts) >= 2:
        d = parse_date(f"{parts[0]} {parts[1]}", ref_year)
        if d:
            return d, d

    return None, None


def extract_price_and_original(text: str, offer_lines: list[str]) -> tuple[str | None, str | None]:
    # U.P. pattern
    m = re.search(
        r"\$(\d+(?:\.\d+)?)[^(\n]*\(U\.?P\.?\s*\$(\d+(?:\.\d+)?)\)",
        text, re.IGNORECASE
    )
    if m:
        return f"${m.group(1)}", f"${m.group(2)}"
    # Price in offer lines
    for line in offer_lines:
        m = re.search(r"\$(\d+(?:\.\d+)?)", line)
        if m:
            return f"${m.group(1)}", None
    return None, None


def extract_discount(text: str, offer_lines: list[str]) -> str | None:
    combined = " ".join(offer_lines) + " " + text

    if re.search(r"1[-\s]for[-\s]1", combined, re.IGNORECASE):
        return "1-for-1"

    m = re.search(r"up\s+to\s+(\d+)\s*%\s*(?:off|cashback)", combined, re.IGNORECASE)
    if m:
        return f"Up to {m.group(1)}% OFF"

    m = re.search(r"(\d+)\s*%\s*off", combined, re.IGNORECASE)
    if m:
        return f"{m.group(1)}% OFF"

    if re.search(r"\bfree\b", combined, re.IGNORECASE):
        m = re.search(r"\bfree\b\s+(.{3,50}?)(?:[.\n]|$)", combined, re.IGNORECASE)
        if m:
            desc = strip_emoji(clean_md(m.group(1))).strip()
            return f"FREE {desc}" if desc else "FREE"
        return "FREE"

    if re.search(r"cashback", combined, re.IGNORECASE):
        return "Cashback"

    return None


def extract_locations(text: str) -> list[str]:
    locs = []
    for line in text.split("\n"):
        if "📍" in line:
            raw = clean_md(line.split("📍", 1)[1]).strip()
            if raw:
                for part in re.split(r"\s*\|\s*", raw):
                    part = part.strip()
                    if part:
                        locs.append(part)
    return locs


def extract_promo_code(text: str) -> str | None:
    m = re.search(r"[<\[]([A-Z0-9_\-]{4,25})[>\]]", text)
    if m:
        return m.group(1)
    return None


def extract_restrictions(text: str, channel: str) -> list[str]:
    restrictions = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("❗"):
            raw = re.sub(r"^❗[\uFE0F\uFE0E]?\s*", "", stripped)
            raw = clean_md(raw).strip()
            if raw:
                for part in re.split(r"\.\s+", raw):
                    part = part.strip().rstrip(".")
                    if part:
                        restrictions.append(part)
        elif channel == "sgfooddeals" and re.search(r"T&Cs apply", stripped, re.IGNORECASE):
            if not stripped.startswith("🔹"):
                raw = clean_md(stripped).strip()
                if raw:
                    restrictions.append(raw)
    return restrictions


def extract_more_info(text: str) -> str | None:
    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^\)]+)\)", text):
        url = m.group(2)
        if any(x in url for x in ("tco.sg", "bit.ly", "grb.to")):
            return url
    m = re.search(r"(tco\.sg/\S+)", text)
    if m:
        return m.group(1).rstrip(".,\n")
    m = re.search(r"(bit\.ly/\S+)", text)
    if m:
        return m.group(1).rstrip(".,\n")
    return None


# ---------------------------------------------------------------------------
# Category classifier — expanded keyword lists
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "food & beverage": [
        # food/drink items
        "burger", "pizza", "sushi", "ramen", "noodle", "chicken", "fries",
        "bubble tea", "milk tea", "coffee", "matcha", "yogurt", "gelato",
        "ice cream", "soft serve", "cone", "cake", "tart", "croissant",
        "donut", "doughnut", "macaron", "cream puff", "cookie", "pastry",
        "poke", "rice", "hotpot", "kbbq", "wings", "pretzel", "mochi",
        "bao", "prata", "dumpling", "dim sum", "steak", "wagyu", "seafood",
        "oyster", "satay", "laksa", "mala", "pasta", "toast", "sandwich",
        "wrap", "bowl", "taco", "waffle", "smoothie", "shake", "juice",
        "acai", "tiramisu", "popcorn", "boba", "puff", "roll",
        "scoops", "scoop", "float", "latte", "flat white", "kaya",
        # deal contexts
        "buffet", "brunch", "lunch set", "set meal", "omakase", "sashimi",
        "free-flow", "dining", "dine-in", "dine in",
        # merchants
        "starbucks", "mcdonald", "popeyes", "a&w", "jollibee", "mos burger",
        "wingstop", "kfc", "subway", "smöoy", "smooy", "tsujiri", "udders",
        "liho", "chagee", "chapanda", "guzman", "moreyogurt", "burnt cones",
        "rrooll", "ramen king", "tavola", "heytea", "haus coffee", "eat pizza",
        "gopizza", "haidilao", "springleaf", "pepper lunch", "shake shack",
        "4fingers", "collin", "captain kim", "ghost kakigori", "matchaya",
        "hana restaurant", "harry", "bangkok jam", "red house seafood",
        "woke ramen", "acid bar", "morganfield", "monster planet", "pang pang",
        "noodle star", "kokoro", "famous amos", "pizza hut", "hecha", "beutea",
        "blacktree", "yimanfen", "ramen keisuke", "carnaby", "daya",
        "kimpson", "mr. farmer", "7-eleven", "milkfish", "gotcha",
        "ya kun", "krispy kreme", "dunkin", "gong cha", "koi the",
        "playmade", "mr coconut", "beard papa", "pastamania", "tipo",
        "big fish small fish", "swensen", "beauty in the pot", "nine fresh",
        "hokkaido baked", "dipndip", "hot hideout", "yoajung", "amacha",
        "afterwit", "koggii", "yo-chi", "annabelle", "garett", "garret",
        "chia puddies", "shiroyama", "the oyster", "boost", "project acai",
        "summer acai", "kei kaisendon", "beast and butterflies", "cloutea",
        "jett barbecue", "twg tea", "lickers", "mystery sandwich",
        "the winery", "poke theory", "tai cheong", "gotcha fresh tea",
        "munchi", "bingxue", "nana's green tea", "creamier", "nine fresh",
        "don don donki", "hawker", "cafe", "restaurant", "bakery", "eatery",
        "food", "eat", "drink", "koi the", "koi ", "acai", "soft spot",
        "huo lu huo", "uniqlo lunch", "summer acai", "the summer",
    ],
    "entertainment": [
        "concert", "ticket", "live nation", "show", "marquee",
        "club", "party", "festival", "bazaar", "food fair", "pop-up",
        "giveaway", "lucky draw", "karaoke", "photobooth", "photo booth",
        "photo studio", "themed run", "bowling", "cable car",
        "gardens by the bay", "sentosa", "universal studios", "uss",
        "adventure cove", "rws season pass", "fireworks",
    ],
    "travel": [
        "flight", "hotel", "airline", "krisflyer", "miles", "singapore airlines",
        "travel", "booking", "destination", "staycation",
    ],
    "shopping": [
        "grabmall", "electronics", "dji", "jbl", "honor", "oppo",
        "grocery", "frozen food", "supermarket", "fairprice", "sheng siong",
        "amazon", "iherb", "shopee", "lazada", "cb brand",
        "shoe", "sneaker", "converse", "superga", "adidas", "nike",
        "jewellery", "jewelry", "sk jewellery", "lego", "sony", "samsonite",
        "luggage", "lenskart", "don don donki",
        "foot locker", "ikea", "beauty fiesta", "beauty brand", "beauty sale",
        "uniqlo", "fashion", "apparel", "clothes",
    ],
    "lifestyle": [
        "slimming", "hair care", "treatment", "wellness", "gym", "spa",
        "facial", "ezslim", "dorra", "yun nam",
        "redeemsg", "cable car", "singapore cable car",
        "photobooth", "photo booth", "studio", "labubu", "collectible",
        "water dispenser", "home appliance",
    ],
    "telco / tech": [
        "circles.life", "tuas power", "electricity", "data", "5g", "sim",
        "phone plan", "kwh", "ai tools", "chatgpt", "claude", "gemini",
        "youtrip",
    ],
    "app / platform": [
        "grab app", "grabfood", "grabmart", "starbucks app", "foodpanda",
        "kris+", "happy point", "grab dine out", "paylater by grab",
        "chope", "grabcab",
    ],
    "finance / cards": [
        "ocbc", "dbs", "uob", "citibank", "credit card", "cashback card",
        "miles card",
    ],
}


def classify_category(merchant: str, offer_lines: list[str], text: str) -> str:
    combined = (merchant + " " + " ".join(offer_lines) + " " + text).lower()
    scores: dict[str, int] = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in kws if kw in combined)
        if count:
            scores[cat] = count
    if scores:
        return max(scores, key=scores.get)
    return "other"


def is_roundup(text: str) -> bool:
    """True if the post is a multi-merchant roundup (numbered list ≥3 items)."""
    # Unicode numbered emoji: 1️⃣ = \u0031\uFE0F\u20E3, also matches plain digits
    numbered = re.findall(r"\d\uFE0F\u20E3", text)
    if len(numbered) >= 3:
        return True
    # Fallback: plain "1️⃣" style counting via character inspection
    count = len(re.findall(r"[1-9]️⃣", text))
    return count >= 3


def is_non_deal(text: str) -> bool:
    """True if post has no deal content (articles, shoutouts, channel promos)."""
    if re.search(r"#(?:article|shoutout|uniqueevent|freebie)\b", text, re.IGNORECASE):
        return True
    # Explicit channel promo / survey patterns
    if re.search(
        r"join\s+.*\s+telegram\s+channel|subscribe|follow us|"
        r"national youth council|performative purity|quiz to measure|"
        r"share what you",
        text, re.IGNORECASE
    ):
        return True
    # No date, price, or deal keyword at all
    has_deal_signal = re.search(
        r"[📅📆]|⏰|\$\d|1-for-1|1 for 1|% off|FREE\b|free-flow",
        text, re.IGNORECASE
    )
    if not has_deal_signal:
        # Unless a bullet line has one
        for line in text.split("\n"):
            if ("🔹" in line or "➡️" in line) and re.search(
                r"\$\d|1-for-1|% off|FREE\b|free-flow", line, re.IGNORECASE
            ):
                return False
        return True
    return False


# ---------------------------------------------------------------------------
# Channel-specific parsers
# ---------------------------------------------------------------------------

def parse_goodlobang(raw: dict) -> dict:
    text      = raw["text"]
    posted_at = raw.get("posted_at", "")
    ref_year  = _ref_year(posted_at)

    # Merchant from first bold segment on first line, skip emoji-only matches
    first_line = text.split("\n")[0]
    merchant = ""
    for match in re.findall(r"\*\*(.+?)\*\*", first_line):
        cleaned = strip_emoji(clean_md(match))
        if cleaned:
            merchant = cleaned
            break
    if not merchant:
        merchant = strip_emoji(clean_md(first_line))

    # Offers: ➡️ bullets
    offer_lines = [
        clean_md(line.split("➡️", 1)[1])
        for line in text.split("\n") if "➡️" in line
    ]
    offer = offer_lines[0] if offer_lines else None

    price, original_price = extract_price_and_original(text, offer_lines)
    discount = extract_discount(text, offer_lines)

    # Date line
    date_raw = None
    for line in text.split("\n"):
        if re.search(r"[📆📅]", line):
            date_raw = clean_md(re.sub(r"[📆📅]", "", line)).strip()
            break
    valid_from, valid_to = parse_date_range(date_raw, ref_year) if date_raw else (None, None)

    # Time string: date line + clock/⏰ lines
    time_parts = []
    if date_raw:
        time_parts.append(date_raw)
    for line in text.split("\n"):
        if re.search(r"[\u23F0\u23F1⏰\U0001F550-\U0001F567]", line):
            t = re.sub(r"[^\x20-\x7E]", "", line).strip(" -–|")
            if t:
                time_parts.append(t)
    time_str = " | ".join(p for p in time_parts if p) or None

    locations  = extract_locations(text)
    promo_code = extract_promo_code(text)
    redemption = None
    for line in text.split("\n"):
        if "💃" in line:
            redemption = clean_md(line.split("💃", 1)[1]).strip() or None
            break

    restrictions = extract_restrictions(text, "goodlobang")
    more_info    = extract_more_info(text)

    if is_roundup(text):
        category = "roundup"
    elif is_non_deal(text):
        category = "non-deal"
    else:
        category = classify_category(merchant, offer_lines, text)

    return _build(raw, merchant, category, offer, price, original_price,
                  discount, valid_from, valid_to, time_str, locations,
                  redemption, restrictions, promo_code, more_info)


def parse_sgfooddeals(raw: dict) -> dict:
    text      = raw["text"]
    posted_at = raw.get("posted_at", "")
    ref_year  = _ref_year(posted_at)

    if is_non_deal(text):
        return _build(raw, None, "non-deal", None, None, None,
                      None, None, None, None, [], None, [], None,
                      extract_more_info(text))

    if is_roundup(text):
        return _build(raw, None, "roundup", None, None, None,
                      None, None, None, None, [], None, [], None,
                      extract_more_info(text))

    # Merchant + offer: title format is "**Merchant: Offer**"
    first_line = text.split("\n")[0]
    # Collect all bold segments on the first line (handles "**A**\n**B: offer**")
    all_bold = re.findall(r"\*\*(.+?)\*\*", text.split("\n")[0] + "\n" + text.split("\n")[1] if len(text.split("\n")) > 1 else text.split("\n")[0])
    title_raw = ""
    for b in all_bold:
        cleaned = strip_emoji(clean_md(b)).strip(": ")
        if cleaned and len(cleaned) > 2:
            title_raw = cleaned
            break
    if not title_raw:
        title_raw = strip_emoji(clean_md(first_line)).strip(": ")

    if ":" in title_raw:
        colon_idx = title_raw.index(":")
        merchant = title_raw[:colon_idx].strip()
        offer    = title_raw[colon_idx + 1:].strip() or None
    else:
        merchant = title_raw
        offer    = None

    # Bullet lines for additional context
    bullet_lines = [
        clean_md(line.split("🔹", 1)[1])
        for line in text.split("\n") if "🔹" in line
    ]
    if not offer and bullet_lines:
        offer = bullet_lines[0]

    price, original_price = extract_price_and_original(text, ([offer] if offer else []) + bullet_lines)
    discount = extract_discount(text, ([offer] if offer else []) + bullet_lines)

    # Date line (strip markdown links inside it)
    date_raw = None
    for line in text.split("\n"):
        if re.search(r"[📅📆]", line):
            cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", line)
            date_raw = clean_md(re.sub(r"[📅📆]", "", cleaned)).strip()
            break
    valid_from, valid_to = parse_date_range(date_raw, ref_year) if date_raw else (None, None)

    # Time: ⏰ lines
    time_parts = []
    if date_raw:
        time_parts.append(date_raw)
    for line in text.split("\n"):
        if "⏰" in line:
            t = clean_md(line.split("⏰", 1)[1]).strip()
            if t:
                time_parts.append(t)
    time_str = " | ".join(p for p in time_parts if p) or None

    locations    = extract_locations(text)
    promo_code   = extract_promo_code(text)
    restrictions = extract_restrictions(text, "sgfooddeals")
    more_info    = extract_more_info(text)
    category     = classify_category(merchant, bullet_lines, text)

    return _build(raw, merchant, category, offer, price, original_price,
                  discount, valid_from, valid_to, time_str, locations,
                  None, restrictions, promo_code, more_info)


def _build(raw, merchant, category, offer, price, original_price,
           discount, valid_from, valid_to, time_str, locations,
           redemption, restrictions, promo_code, more_info) -> dict:
    return {
        "channel":           raw.get("channel"),
        "channel_title":     raw.get("channel_title"),
        "message_id":        raw.get("message_id"),
        "posted_at":         raw.get("posted_at"),
        "merchant":          merchant,
        "category":          category,
        "offer":             offer,
        "price":             price,
        "original_price":    original_price,
        "discount":          discount,
        "valid_from":        valid_from,
        "valid_to":          valid_to,
        "time":              time_str,
        "locations":         locations,
        "redemption_method": redemption,
        "restrictions":      restrictions,
        "promo_code":        promo_code,
        "more_info":         more_info,
        "raw_text":          raw.get("text"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

PARSERS = {
    "goodlobang":  parse_goodlobang,
    "sgfooddeals": parse_sgfooddeals,
}


def main():
    input_path  = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return

    count = 0
    errors = 0
    with (
        input_path.open("r", encoding="utf-8") as fin,
        output_path.open("w", encoding="utf-8") as fout,
    ):
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                raw    = json.loads(line)
                ch     = raw.get("channel", "")
                parser = PARSERS.get(ch, parse_goodlobang)
                record = parser(raw)
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
            except Exception as e:
                errors += 1
                print(f"Error on message {raw.get('message_id')}: {e}")

    print(f"Done — {count} records written to {output_path} ({errors} errors)")


if __name__ == "__main__":
    main()
