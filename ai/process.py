"""
process.py
Reads unprocessed raw_messages from the DB, sends each one to an OpenRouter
LLM to extract deal fields, then upserts the result into the deals table.

Run after main.py (crawl) and before geocode.py:
    python process.py
    python process.py --model google/gemini-flash-1.5          # override model
    python process.py --limit 50                               # process N messages
    python process.py --reprocess                              # redo already-processed ones

Requires in .env:
    DATABASE_URL=...
    OPENROUTER_API_KEY=...
"""

import argparse
import json
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
import os

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

sys.path.insert(0, str(HERE.parent / "db"))
from db import get_connection, create_tables  # noqa: E402

DATABASE_URL    = os.getenv("DATABASE_URL")
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY")

# Default to a free model — override with --model flag
# Uses OpenRouter's free router — automatically picks from available free models
DEFAULT_MODEL   = "openrouter/free"
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"

# ---------------------------------------------------------------------------
# System prompt — instructs the model to return a strict JSON object
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a deal extraction assistant. Given a Telegram promotion message, extract the deal fields and return ONLY a valid JSON object with exactly these keys:

{
  "merchant": string,
  "category": string,         // one of: food & beverage, shopping, beauty, entertainment, travel, hotels, electronics, fitness, services, other
  "offer": string,            // full offer description
  "price": string | null,     // e.g. "$6.10"
  "original_price": string | null,
  "discount": string | null,  // e.g. "30% OFF", "1-for-1"
  "valid_from": string | null, // YYYY-MM-DD
  "valid_to": string | null,   // YYYY-MM-DD
  "time": string | null,      // opening hours or time restriction
  "locations": [string],      // list of outlet names or areas
  "redemption_method": string | null,
  "restrictions": [string],   // list of T&C strings
  "promo_code": string | null,
  "more_info": string | null  // URL or link
}

Return ONLY the JSON object. No explanation, no markdown, no code fences."""

# ---------------------------------------------------------------------------
# OpenRouter call
# ---------------------------------------------------------------------------

def call_openrouter(text: str, model: str, retries: int = 3) -> dict | None:
    """Send a message to OpenRouter and return the parsed JSON prediction."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/promo-radar-scan",
        "X-Title":       "promo-radar-scan",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": text},
        ],
        "temperature": 0.1,  # low temp for consistent structured output
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data    = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences if the model wraps the JSON anyway
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            print(f"    JSON parse error (attempt {attempt}): {e}")
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            print(f"    HTTP {status} error (attempt {attempt}): {e}")
            if status == 429:
                # Rate limited — wait before retrying
                time.sleep(5 * attempt)
        except Exception as e:
            print(f"    Error (attempt {attempt}): {e}")

        if attempt < retries:
            time.sleep(2)

    return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

FETCH_UNPROCESSED_SQL = """
SELECT
    r.id,
    r.channel,
    r.channel_title,
    r.message_id,
    r.posted_at,
    r.text
FROM raw_messages r
LEFT JOIN deals d ON d.channel = r.channel AND d.message_id = r.message_id
WHERE r.text IS NOT NULL AND r.text != ''
  AND d.id IS NULL   -- not yet processed
ORDER BY r.posted_at DESC
{limit_clause}
"""

FETCH_ALL_SQL = """
SELECT
    r.id,
    r.channel,
    r.channel_title,
    r.message_id,
    r.posted_at,
    r.text
FROM raw_messages r
WHERE r.text IS NOT NULL AND r.text != ''
ORDER BY r.posted_at DESC
{limit_clause}
"""

UPSERT_DEAL_SQL = """
INSERT INTO deals (
    channel, channel_title, message_id, posted_at, posted_date,
    raw_input, merchant, category, offer, price, original_price,
    discount, valid_from, valid_to, time, locations,
    redemption_method, restrictions, promo_code, more_info, updated_at
) VALUES (
    %(channel)s, %(channel_title)s, %(message_id)s, %(posted_at)s,
    %(posted_at)s::date,
    %(raw_input)s, %(merchant)s, %(category)s, %(offer)s, %(price)s,
    %(original_price)s, %(discount)s, %(valid_from)s, %(valid_to)s,
    %(time)s, %(locations)s, %(redemption_method)s, %(restrictions)s,
    %(promo_code)s, %(more_info)s, NOW()
)
ON CONFLICT (merchant, offer, valid_from, valid_to)
DO UPDATE SET
    channel           = EXCLUDED.channel,
    channel_title     = EXCLUDED.channel_title,
    message_id        = EXCLUDED.message_id,
    posted_at         = EXCLUDED.posted_at,
    posted_date       = EXCLUDED.posted_at::date,
    raw_input         = EXCLUDED.raw_input,
    category          = EXCLUDED.category,
    price             = EXCLUDED.price,
    original_price    = EXCLUDED.original_price,
    discount          = EXCLUDED.discount,
    time              = EXCLUDED.time,
    locations         = EXCLUDED.locations,
    redemption_method = EXCLUDED.redemption_method,
    restrictions      = EXCLUDED.restrictions,
    promo_code        = EXCLUDED.promo_code,
    more_info         = EXCLUDED.more_info,
    updated_at        = NOW();
"""


def upsert_deal_from_prediction(cur, row: dict, pred: dict):
    locations   = pred.get("locations") or []
    restrictions = pred.get("restrictions") or []

    # Normalise locations to [{name, lat, lng}] — geocoding happens later
    if locations and isinstance(locations[0], str):
        locations = [{"name": loc, "lat": None, "lng": None} for loc in locations]

    params = {
        "channel":           row["channel"],
        "channel_title":     row["channel_title"],
        "message_id":        row["message_id"],
        "posted_at":         str(row["posted_at"]),
        "raw_input":         row["text"],
        "merchant":          pred.get("merchant"),
        "category":          pred.get("category"),
        "offer":             pred.get("offer"),
        "price":             pred.get("price"),
        "original_price":    pred.get("original_price"),
        "discount":          pred.get("discount"),
        "valid_from":        pred.get("valid_from") or None,
        "valid_to":          pred.get("valid_to") or None,
        "time":              pred.get("time"),
        "locations":         json.dumps(locations),
        "redemption_method": pred.get("redemption_method"),
        "restrictions":      json.dumps(restrictions),
        "promo_code":        pred.get("promo_code"),
        "more_info":         pred.get("more_info"),
    }
    cur.execute(UPSERT_DEAL_SQL, params)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Process raw messages into deals via OpenRouter")
    parser.add_argument("--model",      default=DEFAULT_MODEL, help="OpenRouter model ID")
    parser.add_argument("--limit",      type=int, default=None, help="Max messages to process")
    parser.add_argument("--reprocess",  action="store_true",   help="Re-process already-processed messages")
    parser.add_argument("--delay",      type=float, default=0.5, help="Seconds to wait between API calls (default 0.5)")
    args = parser.parse_args()

    if not OPENROUTER_KEY:
        print("Error: OPENROUTER_API_KEY is not set in .env")
        sys.exit(1)

    limit_clause = f"LIMIT {args.limit}" if args.limit else ""
    query = (FETCH_ALL_SQL if args.reprocess else FETCH_UNPROCESSED_SQL).format(
        limit_clause=limit_clause
    )

    conn = get_connection()
    create_tables(conn)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        print("No unprocessed messages found.")
        conn.close()
        return

    print(f"Processing {len(rows)} messages with model: {args.model}\n")

    ok = skipped = errors = 0

    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['channel']} #{row['message_id']} — ", end="", flush=True)

        pred = call_openrouter(row["text"], args.model)

        if pred is None:
            print("✗ model call failed, skipping")
            errors += 1
            continue

        # Skip non-deals (model may return category "non-deal" or "roundup")
        cat = (pred.get("category") or "").lower()
        if cat in ("non-deal", "roundup", ""):
            print(f"skip ({cat})")
            skipped += 1
            continue

        try:
            with conn.cursor() as cur:
                upsert_deal_from_prediction(cur, row, pred)
            conn.commit()
            print(f"✓ {pred.get('merchant')} — {pred.get('offer', '')[:50]}")
            ok += 1
        except Exception as e:
            print(f"✗ DB error: {e}")
            conn.rollback()
            errors += 1

        # Polite delay between API calls to avoid rate limiting
        if i < len(rows):
            time.sleep(args.delay)

    conn.close()
    print(f"\nDone — {ok} inserted/updated, {skipped} skipped, {errors} errors.")


if __name__ == "__main__":
    main()
