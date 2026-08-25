"""
load_to_db.py
Reads processed_geo.jsonl and upserts every deal into Neon PostgreSQL.

Run this after geocode.py has produced a fresh processed_geo.jsonl:
    python load_to_db.py
    python load_to_db.py --input processed_geo.jsonl
"""

import argparse
import json
from pathlib import Path

from db import create_table, get_connection, upsert_deal

# Default input relative to the repo root
HERE = Path(__file__).parent
DEFAULT_INPUT = HERE.parent / "ai" / "processed_geo.jsonl"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT),
                        help="Path to the geocoded JSONL file")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"File not found: {input_path}")
        return

    conn = get_connection()
    create_table(conn)

    inserted = 0
    updated = 0
    errors = 0

    with conn.cursor() as cur, input_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # Check row count before to detect insert vs update
                cur.execute(
                    "SELECT 1 FROM deals WHERE channel = %s AND message_id = %s",
                    (record.get("channel"), record.get("message_id")),
                )
                exists = cur.fetchone() is not None
                upsert_deal(cur, record)
                if exists:
                    updated += 1
                else:
                    inserted += 1
            except Exception as e:
                print(f"  ✗ Line {line_num}: {e}")
                errors += 1
                conn.rollback()
                continue

        conn.commit()

    conn.close()

    print(f"\nDone — {inserted} inserted, {updated} updated, {errors} errors.")


if __name__ == "__main__":
    main()
