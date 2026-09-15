"""
brand_locations.py
Finds deals whose locations list is empty or null, searches OneMap for the
merchant name to discover outlet coordinates, then updates the deals table.

For merchants OneMap can't find, falls back to asking an LLM (via OpenRouter)
to enumerate Singapore outlet locations, then geocodes those via Nominatim.

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
import os
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

sys.path.insert(0, str(HERE.parent / "db"))
from db import get_connection, create_tables  # noqa: E402

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL  = "openrouter/free"

# ---------------------------------------------------------------------------
# OneMap Search API
# ---------------------------------------------------------------------------

ONEMAP_URL    = "https://www.onemap.gov.sg/api/common/elastic/search"
REQUEST_DELAY = 0.25  # 250 req/min → 0.25 s between calls

# ---------------------------------------------------------------------------
# Nominatim geocoder (for AI-suggested outlet names)
# ---------------------------------------------------------------------------

NOMINATIM_URL     = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "promo-radar-scan/1.0 (brand-locations)"}
NOMINATIM_DELAY   = 1.1

SG_BOUNDS = dict(lat_min=1.1, lat_max=1.5, lng_min=103.5, lng_max=104.2)


def _in_singapore(lat: float, lng: float) -> bool:
    return (
        SG_BOUNDS["lat_min"] < lat < SG_BOUNDS["lat_max"]
        and SG_BOUNDS["lng_min"] < lng < SG_BOUNDS["lng_max"]
    )


def geocode_nominatim(address: str) -> tuple[float, float] | None:
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={"q": f"{address}, Singapore", "format": "json",
                    "limit": 1, "countrycodes": "sg"},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        results = r.json()
        if results:
            lat, lng = float(results[0]["lat"]), float(results[0]["lon"])
            if _in_singapore(lat, lng):
                return lat, lng
    except Exception as e:
        print(f"    Nominatim error for '{address}': {e}")
    return None


# ---------------------------------------------------------------------------
# AI fallback — ask LLM to list Singapore outlets for a brand
# ---------------------------------------------------------------------------

AI_SYSTEM_PROMPT = """You are a Singapore retail location assistant.
Given a brand or merchant name, list its known outlet locations in Singapore.
Return ONLY a JSON array of outlet name strings, e.g.:
["Outlet Name at Mall A", "Outlet Name at Mall B"]
If you don't know any outlets, return an empty array: []
No explanation, no markdown, no code fences."""


def ask_ai_for_outlets(merchant: str) -> list[str]:
    """Ask OpenRouter LLM to list Singapore outlets for a merchant. Returns list of name strings."""
    if not OPENROUTER_KEY:
        return []
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/promo-radar-scan",
        "X-Title":       "promo-radar-scan",
    }
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user",   "content": f"List Singapore outlet locations for: {merchant}"},
        ],
        "temperature": 0.1,
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        names = json.loads(content)
        if isinstance(names, list):
            return [str(n) for n in names if n]
    except Exception as e:
        print(f"    AI error for '{merchant}': {e}")
    return []


def ai_outlets_to_coords(merchant: str) -> list[dict]:
    """Use AI to get outlet names, then geocode each via Nominatim."""
    names = ask_ai_for_outlets(merchant)
    if not names:
        return []

    outlets = []
    for name in names[:10]:  # cap at 10 outlets per brand
        coords = geocode_nominatim(f"{merchant} {name}")
        if not coords:
            coords = geocode_nominatim(name)
        if coords:
            outlets.append({"name": name, "lat": coords[0], "lng": coords[1]})
        time.sleep(NOMINATIM_DELAY)

    return outlets


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

    # ── Query OneMap for each new merchant, fall back to AI ──────────────────
    with conn.cursor() as cur:
        for i, merchant in enumerate(merchants_needed, 1):
            print(f"[{i}/{len(merchants_needed)}] Searching '{merchant}' on OneMap ...", end=" ", flush=True)
            outlets = search_onemap(merchant)

            if outlets:
                print(f"✓ {len(outlets)} outlets found")
            else:
                print("✗ not found — trying AI fallback ...", end=" ", flush=True)
                outlets = ai_outlets_to_coords(merchant)
                print(f"✓ {len(outlets)} outlets from AI" if outlets else "✗ AI found nothing")

            brand_cache[merchant] = outlets
            cur.execute(UPSERT_BRAND_OUTLETS_SQL, (merchant, json.dumps(outlets)))
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
