"""
cleanup.py
Removes expired deals from the deals table and orphaned raw_messages.

Phase 1 — Deals:
  A deal is considered expired when its valid_to date is strictly before today's
  date (SGT / local server time). Deals with a NULL valid_to are kept — they are
  assumed to be ongoing.

Phase 2 — raw_messages:
  A message is considered expired when its message_id and channel are no longer
  in the deals table.

Usage:
    python cleanup.py            # delete expired deals + orphaned raw_messages
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

# ── Phase 1: expired deals ──────────────────────────────────────────────────

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

# ── Phase 2: orphaned raw_messages ──────────────────────────────────────────
#
# A raw_message is orphaned when it has been processed (processed = TRUE) but
# its (channel, message_id) pair is no longer referenced by any row in deals.
# We match on BOTH channel AND message_id because message_ids are per-channel
# — different channels can reuse the same number.
# Unprocessed rows (processed = FALSE) are always kept so fresh scrapes are
# never deleted before the pipeline has a chance to run.

FETCH_ORPHAN_MESSAGES_SQL = """
SELECT rm.id, rm.channel, rm.message_id, rm.posted_at::date AS posted_date
FROM raw_messages rm
WHERE rm.processed = TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM deals d
      WHERE d.channel    = rm.channel
        AND d.message_id = rm.message_id
  )
ORDER BY rm.posted_at DESC;
"""

DELETE_ORPHAN_MESSAGES_SQL = """
DELETE FROM raw_messages
WHERE processed = TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM deals d
      WHERE d.channel    = raw_messages.channel
        AND d.message_id = raw_messages.message_id
  );
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
    print(f"Cleanup: reference date = {today}")

    conn = get_connection()

    # ── Phase 1: expired deals ───────────────────────────────────────────────
    print("\n── Phase 1: expired deals ──")
    with conn.cursor() as cur:
        cur.execute(FETCH_EXPIRED_SQL, {"today": today})
        expired_rows = cur.fetchall()

    if not expired_rows:
        print("No expired deals found.")
    else:
        print(f"Found {len(expired_rows)} expired deal(s):")
        for row in expired_rows:
            deal_id, merchant, offer, valid_to = row
            offer_preview = (offer or "")[:60]
            print(f"  [{deal_id}] {merchant} — {offer_preview} (expired {valid_to})")

    # ── Phase 2: orphaned raw_messages ───────────────────────────────────────
    print("\n── Phase 2: orphaned raw_messages ──")
    with conn.cursor() as cur:
        cur.execute(FETCH_ORPHAN_MESSAGES_SQL)
        orphan_rows = cur.fetchall()

    if not orphan_rows:
        print("No orphaned raw_messages found.")
    else:
        print(f"Found {len(orphan_rows)} orphaned raw_message(s):")
        for row in orphan_rows:
            msg_id, channel, message_id, posted_date = row
            print(f"  [raw#{msg_id}] channel={channel} message_id={message_id} posted={posted_date}")

    # ── Apply or dry-run ─────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[dry-run] No changes made.")
        conn.close()
        return

    if not expired_rows and not orphan_rows:
        print("\nNothing to delete.")
        conn.close()
        return

    with conn.cursor() as cur:
        cur.execute(DELETE_EXPIRED_SQL, {"today": today})
        deleted_deals = cur.rowcount

        cur.execute(DELETE_ORPHAN_MESSAGES_SQL)
        deleted_messages = cur.rowcount

    conn.commit()
    conn.close()

    print(f"\n✓ Deleted {deleted_deals} expired deal(s).")
    print(f"✓ Deleted {deleted_messages} orphaned raw_message(s).")


if __name__ == "__main__":
    main()
