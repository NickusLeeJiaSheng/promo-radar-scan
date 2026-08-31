"""
geocode.py
Reads deals from the DB that have ungeocoded locations, geocodes them via
Nominatim (free, no key required), and writes the coords back to the DB.

Usage:
    python geocode.py
    python geocode.py --all     # re-geocode every deal, not just new ones

Nominatim docs: https://nominatim.org/release-docs/latest/api/Search/
"""

import argparse
import json
import sys
import time
from pathlib import Path

import psycopg2.extras
import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "db"))
from db import get_connection, create_tables  # noqa: E402

# ---------------------------------------------------------------------------
# Nominatim geocoder
# ---------------------------------------------------------------------------

NOMINATIM_URL     = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "promo-radar-scan/1.0 (geocoder)"}
REQUEST_DELAY     = 1.1  # seconds — must honour 1 req/sec rate limit


def geocode_nominatim(address: str) -> tuple[float, float] | None:
    """Return (lat, lng) via OSM Nominatim, biased to Singapore."""
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={
                "q":            f"{address}, Singapore",
                "format":       "json",
                "limit":        1,
                "countrycodes": "sg",
            },
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        results = r.json()
        if results:
            lat = float(results[0]["lat"])
            lng = float(results[0]["lon"])
            # Sanity-check: must be within Singapore bounding box
            if 1.1 < lat < 1.5 and 103.5 < lng < 104.2:
                return lat, lng
    except Exception as e:
        print(f"  ✗ Nominatim error for '{address}': {e}")
    return None


# Known coordinates for places Nominatim doesn't recognise
KNOWN_COORDS: dict[str, tuple[float, float]] = {
    "SMU Li Ka Shing Library":        (1.29666, 103.85011),
    "SMU Li Ka Shing Library, B1-25": (1.29666, 103.85011),
    "30 Victoria Street, #02-01B":    (1.29549, 103.85201),
}


def clean_address(raw: str) -> str:
    """Strip unit numbers so Nominatim can match the building name."""
    import re
    cleaned = re.sub(r"[,\s]+#?[BbLl]?\d{1,2}-\d{2,3}\b", "", raw)
    cleaned = re.sub(r",\s*Town Plaza", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip().rstrip(",").strip()


SKIP_LOCS = {"all outlets", "selected outlets", "singapore", "all outlets"}


def should_geocode(name: str) -> bool:
    return bool(name) and name.lower() not in SKIP_LOCS


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------

FETCH_UNGEOCODED_SQL = """
SELECT id, locations
FROM deals
WHERE locations IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(locations) AS loc
      WHERE (loc->>'lat') IS NULL
        AND loc->>'name' IS NOT NULL
        AND loc->>'name' != ''
  )
ORDER BY posted_at DESC
"""

FETCH_ALL_SQL = """
SELECT id, locations
FROM deals
WHERE locations IS NOT NULL
ORDER BY posted_at DESC
"""

UPDATE_LOCATIONS_SQL = """
UPDATE deals SET locations = %s::jsonb, updated_at = NOW()
WHERE id = %s
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true",
                        help="Re-geocode all deals, not just ones missing coords")
    args = parser.parse_args()

    conn = get_connection()
    create_tables(conn)

    query = FETCH_ALL_SQL if args.all else FETCH_UNGEOCODED_SQL

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        print("No deals need geocoding.")
        conn.close()
        return

    # ── Pass 1: collect all unique location strings that need geocoding ───────
    all_locations: set[str] = set()
    for row in rows:
        for loc in row["locations"]:
            name = loc.get("name", "")
            if should_geocode(name) and (args.all or loc.get("lat") is None):
                all_locations.add(name)

    print(f"Found {len(rows)} deals, {len(all_locations)} unique locations to geocode.\n")

    # ── Pass 2: geocode with caching ──────────────────────────────────────────
    geo_cache: dict[str, tuple[float, float] | None] = {}

    for i, loc in enumerate(sorted(all_locations), 1):
        clean = clean_address(loc)
        print(f"[{i}/{len(all_locations)}] '{clean}'", end=" ... ", flush=True)

        if loc in KNOWN_COORDS:
            geo_cache[loc] = KNOWN_COORDS[loc]
        elif clean in KNOWN_COORDS:
            geo_cache[loc] = KNOWN_COORDS[clean]
        else:
            candidates = [clean]
            if clean != loc:
                candidates.append(loc)
            if " & " in clean:
                candidates.append(clean.split(" & ")[0].strip())
            if "," in clean:
                candidates.append(clean.split(",")[0].strip())

            result = None
            for candidate in candidates:
                result = geocode_nominatim(candidate)
                if result:
                    break
                time.sleep(REQUEST_DELAY)

            geo_cache[loc] = result

        coords = geo_cache[loc]
        print(f"✓ {coords[0]:.5f}, {coords[1]:.5f}" if coords else "✗ not found")
        time.sleep(REQUEST_DELAY)

    # ── Pass 3: write enriched locations back to DB ───────────────────────────
    updated = 0

    with conn.cursor() as cur:
        for row in rows:
            enriched = []
            for loc in row["locations"]:
                name = loc.get("name", "")
                entry = dict(loc)  # preserve existing fields
                if should_geocode(name):
                    coords = geo_cache.get(name)
                    if coords:
                        entry["lat"], entry["lng"] = coords
                    elif args.all:
                        entry["lat"], entry["lng"] = None, None
                enriched.append(entry)

            cur.execute(UPDATE_LOCATIONS_SQL, (json.dumps(enriched), row["id"]))
            updated += 1

    conn.commit()
    conn.close()

    geocoded = sum(1 for v in geo_cache.values() if v is not None)
    print(f"\nDone — {geocoded}/{len(all_locations)} locations geocoded, {updated} deals updated in DB.")


if __name__ == "__main__":
    main()
