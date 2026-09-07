"""
brand_locations.py
Finds deals whose locations list is empty or null, searches OneMap for the
merchant name to discover outlet coordinates, then updates the deals table.

A `brand_outlets` cache table is used so each merchant is only looked up once.

Run after geocode.py (or as step 4 of the pipeline):
    python brand_locations.py
    python brand_locations.py --all       # re-process every null-location deal
    python brand_locations.py --limit 20  # cap number of merchants queried

OneMap Search API:
    https://www.onemap.gov.sg/api/common/elastic/search
    No API key required. ~250 req/min rate limit.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "db"))
from db import get_connection, create_tables  # noqa: E402

# ---------------------------------------------------------------------------
# OneMap Search API
# ---------------------------------------------------------------------------

ONEMAP_URL    = "https://www.onemap.gov.sg/api/common/elastic/search"
REQUEST_DELAY = 0.25  # 250 req/min → 0.25 s between calls

SG_BOUNDS = dict(lat_min=1.1, lat_max=1.5, lng_min=103.5, lng_max=104.2)

def _in_singapore(lat: float, lng: float) -> bool:
    return (
        SG_BOUNDS["lat_min"] < lat < SG_BOUNDS["lat_max"]
        and SG_BOUNDS["lng_min"] < lng < SG_BOUNDS["lng_max"]
    )


def search_onemap(query: str, max_results: int = 10) -> list[dict]:
    """
    Search OneMap for `query` and return a list of outlet dicts:
        [{"name": <BUILDING>, "lat": float, "lng": float}, ...]

    Deduplicates by (lat, lng) rounded to 5 dp.
    """
    outlets = []
    seen_coords: set[tuple] = set()
    page = 1

    while len(outlets) < max_results:
        try:
            resp = requests.get(
                ONEMAP_URL,
                params={
                    "searchVal":      query,
                    "returnGeom":     "Y",
                    "getAddrDetails": "Y",
                    "pageNum":        page,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ✗ OneMap error for '{query}': {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for r in results:
            try:
                lat = float(r["LATITUDE"])
                lng = float(r["LONGITUDE"])
            except (KeyError, ValueError):
                continue

            if not _in_singapore(lat, lng):
                continue

            key = (round(lat, 5), round(lng, 5))
            if key in seen_coords:
                continue
            seen_coords.add(key)

            # Use BUILDING name if present, fall back to ADDRESS
            name = (r.get("BUILDING") or r.get("ADDRESS") or query).strip()
            outlets.append({"name": name, "lat": lat, "lng": lng})

        # OneMap returns total_num_pages in the response
        total_pages = int(data.get("totalNumPages", 1))
        if page >= total_pages or page >= 3:  # cap at 3 pages (~30 results)
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    return outlets[:max_results]


# ---------------------------------------------------------------------------
# DB — brand_outlets cache table
# ---------------------------------------------------------------------------

FETCH_NULL_LOCATION_DEALS_SQL = """
SELECT id, merchant, locations
FROM deals
WHERE merchant IS NOT NULL
  AND (
      locations IS NULL
      OR locations = '[]'::jsonb
      OR NOT EXISTS (
          SELECT 1
          FROM jsonb_array_elements(locations) AS loc
          WHERE (loc->>'lat') IS NOT NULL
      )
  )
ORDER BY posted_at DESC
"""

FETCH_ALL_DEALS_SQL = """
SELECT id, merchant, locations
FROM deals
WHERE merchant IS NOT NULL
ORDER BY posted_at DESC
"""

UPSERT_BRAND_OUTLETS_SQL = """
INSERT INTO brand_outlets (merchant, outlets, looked_up_at)
VALUES (%s, %s::jsonb, NOW())
ON CONFLICT (merchant)
DO UPDATE SET outlets = EXCLUDED.outlets, looked_up_at = NOW()
"""

UPDATE_DEAL_LOCATIONS_SQL = """
UPDATE deals SET locations = %s::jsonb, updated_at = NOW()
WHERE id = %s
"""


def load_cached_brands(conn) -> dict[str, list]:
    """Return {merchant: outlets} for all rows already in brand_outlets."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT merchant, outlets FROM brand_outlets")
        return {row["merchant"]: row["outlets"] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fill missing deal locations via OneMap brand search"
    )
    parser.add_argument("--all",   action="store_true",
                        help="Re-process all deals, not just null-location ones")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of new merchants to query OneMap for")
    args = parser.parse_args()

    conn = get_connection()
    create_tables(conn)

    # ── Fetch deals that need locations ──────────────────────────────────────
    query_sql = FETCH_ALL_DEALS_SQL if args.all else FETCH_NULL_LOCATION_DEALS_SQL
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query_sql)
        deals = cur.fetchall()

    if not deals:
        print("No deals with missing locations found.")
        conn.close()
        return

    print(f"Found {len(deals)} deals with missing/empty locations.\n")

    # ── Determine which merchants need a OneMap lookup ────────────────────────
    brand_cache = load_cached_brands(conn)
    merchants_needed = sorted({
        d["merchant"] for d in deals
        if d["merchant"] not in brand_cache
    })

    if args.limit:
        merchants_needed = merchants_needed[: args.limit]

    print(f"{len(brand_cache)} merchants already cached, "
          f"{len(merchants_needed)} new merchants to query.\n")

    # ── Query OneMap for each new merchant ────────────────────────────────────
    with conn.cursor() as cur:
        for i, merchant in enumerate(merchants_needed, 1):
            print(f"[{i}/{len(merchants_needed)}] Searching '{merchant}' ...", end=" ", flush=True)
            outlets = search_onemap(merchant)
            brand_cache[merchant] = outlets
            cur.execute(UPSERT_BRAND_OUTLETS_SQL, (merchant, json.dumps(outlets)))
            print(f"✓ {len(outlets)} outlets found" if outlets else "✗ none found")
            time.sleep(REQUEST_DELAY)

    conn.commit()

    # ── Update deals with discovered outlets ─────────────────────────────────
    updated = 0
    with conn.cursor() as cur:
        for deal in deals:
            merchant = deal["merchant"]
            outlets  = brand_cache.get(merchant, [])
            if not outlets:
                continue  # still nothing — leave deal as-is

            cur.execute(UPDATE_DEAL_LOCATIONS_SQL, (json.dumps(outlets), deal["id"]))
            updated += 1

    conn.commit()
    conn.close()

    filled = sum(1 for m in brand_cache.values() if m)
    print(f"\nDone — {filled} merchants with outlets, {updated} deals updated in DB.")


if __name__ == "__main__":
    main()
