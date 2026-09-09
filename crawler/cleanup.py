"""
cleanup.py
Removes expired deals from the deals table.

A deal is considered expired when its valid_to date is strictly before today's
date (SGT / local server time). Deals with a NULL valid_to are kept — they are
assumed to be ongoing.

Usage:
    python cleanup.py            # delete expired deals
    python cleanup.py --dry-run  # print what would be deleted without touching the DB
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

sys.path.insert(0, str(HERE.parent / "db"))
from db import get_connection  # noqa: E402

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

FETCH_EXPIRED_SQL = """
SELECT id, merchant, offer, valid_to
FROM deals
WHERE valid_to IS NOT NULL
  AND valid_to < %(today)s
ORDER BY valid_to DESC;
"""

DELETE_EXPIRED_SQL = """
DELETE FROM deals
WHERE valid_to IS NOT NULL
  AND valid_to < %(today)s;
"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Remove expired deals from the database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expired deals without deleting them",
    )
    args = parser.parse_args()

    today = date.today().isoformat()
    print(f"Cleanup: checking for deals expired before {today}")

    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(FETCH_EXPIRED_SQL, {"today": today})
        rows = cur.fetchall()

    if not rows:
        print("No expired deals found. Nothing to do.")
        conn.close()
        return

    print(f"\nFound {len(rows)} expired deal(s):")
    for row in rows:
        deal_id, merchant, offer, valid_to = row
        offer_preview = (offer or "")[:60]
        print(f"  [{deal_id}] {merchant} — {offer_preview} (expired {valid_to})")

    if args.dry_run:
        print("\n[dry-run] No changes made.")
        conn.close()
        return

    with conn.cursor() as cur:
        cur.execute(DELETE_EXPIRED_SQL, {"today": today})
        deleted = cur.rowcount
    conn.commit()
    conn.close()

    print(f"\n✓ Deleted {deleted} expired deal(s).")


if __name__ == "__main__":
    main()
