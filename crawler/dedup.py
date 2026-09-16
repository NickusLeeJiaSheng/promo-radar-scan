"""
dedup.py
Finds and merges near-duplicate deals in the deals table.

Two deals are considered duplicates when they share the same merchant,
valid_from, valid_to AND their offer strings are at least SIMILARITY_THRESHOLD
similar (Jaccard token overlap).

The earliest-posted deal is kept; later duplicates are deleted.

Usage:
    python dedup.py
    python dedup.py --dry-run              # show what would be merged without changing DB
    python dedup.py --threshold 0.7        # lower threshold = more aggressive merging (default 0.8)
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2.extras
from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

sys.path.insert(0, str(HERE.parent / "db"))
from db import get_connection  # noqa: E402

SIMILARITY_THRESHOLD = 0.8

# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------

def normalise_merchant(name: str) -> str:
    """Strip common suffixes so 'Ajumma's' and 'Ajumma's Korean Restaurant' group together."""
    name = name.lower().strip()
    name = re.sub(r"['\u2019]", "", name)
    suffixes = [
        r"\s+(restaurant|cafe|coffee|bistro|kitchen|bar|grill|eatery|bakery|sg|singapore|pte|ltd|holdings)$"
    ]
    for pattern in suffixes:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
    return name


def tokenise(text: str) -> set[str]:
    """Lowercase, strip punctuation, split into word tokens."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return set(text.split())


def jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two strings based on word token sets."""
    ta, tb = tokenise(a), tokenise(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------

FETCH_DEALS_SQL = """
SELECT id, channel, merchant, offer, valid_from, valid_to, posted_at
FROM deals
WHERE merchant IS NOT NULL AND offer IS NOT NULL
ORDER BY merchant, valid_from, valid_to, posted_at ASC
"""

DELETE_DEAL_SQL = "DELETE FROM deals WHERE id = %s"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Merge near-duplicate deals")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print duplicates without deleting")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD,
                        help=f"Jaccard similarity threshold (default {SIMILARITY_THRESHOLD})")
    args = parser.parse_args()

    conn = get_connection()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(FETCH_DEALS_SQL)
        deals = cur.fetchall()

    print(f"Loaded {len(deals)} deals.\n")

    # ── Group by (valid_from, valid_to) then check merchant + offer similarity ─
    groups: dict[tuple, list] = defaultdict(list)
    for deal in deals:
        key = (
            str(deal["valid_from"]) if deal["valid_from"] else "null",
            str(deal["valid_to"])   if deal["valid_to"]   else "null",
        )
        groups[key].append(deal)

    # Only care about groups with more than one deal
    candidate_groups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Found {len(candidate_groups)} groups with potential duplicates.\n")

    to_delete: list[int] = []

    for key, group in candidate_groups.items():
        valid_from, valid_to = key
        survivors = []

        for deal in group:
            is_dup = False
            for survivor in survivors:
                merchant_score = jaccard(
                    normalise_merchant(deal["merchant"]),
                    normalise_merchant(survivor["merchant"])
                )
                offer_score = jaccard(deal["offer"], survivor["offer"])
                # Duplicate if merchants are similar (>0.6) AND offers are similar (>threshold)
                if merchant_score >= 0.6 and offer_score >= args.threshold:
                    print(
                        f"  DUPLICATE (merchant={merchant_score:.2f}, offer={offer_score:.2f})\n"
                        f"  [{deal['channel']}] {deal['merchant']} — '{deal['offer'][:60]}'\n"
                        f"  ← matches [{survivor['channel']}] {survivor['merchant']} — '{survivor['offer'][:60]}'\n"
                        f"  valid: {valid_from} → {valid_to}\n"
                    )
                    to_delete.append(deal["id"])
                    is_dup = True
                    break
            if not is_dup:
                survivors.append(deal)

    print(f"Total duplicates to remove: {len(to_delete)}")

    if args.dry_run:
        print("[dry-run] No changes made.")
        conn.close()
        return

    if not to_delete:
        print("Nothing to delete.")
        conn.close()
        return

    with conn.cursor() as cur:
        for deal_id in to_delete:
            cur.execute(DELETE_DEAL_SQL, (deal_id,))

    conn.commit()
    conn.close()
    print(f"✓ Deleted {len(to_delete)} duplicate deal(s).")


if __name__ == "__main__":
    main()
