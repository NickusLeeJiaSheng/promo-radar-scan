"""
geocode.py
Reads processed.jsonl, geocodes ALL locations for each deal via Nominatim
(free, no key required), and writes processed_geo.jsonl.

Each deal's prediction will contain a `locations` array of objects:
    [{"name": "Sengkang Grand Mall, 01-03", "lat": 1.3833, "lng": 103.8922}, ...]

Vague locations like "All outlets" are kept in the array but without coords.

Usage:
    python geocode.py
    python geocode.py --input processed.jsonl --output processed_geo.jsonl

Nominatim docs: https://nominatim.org/release-docs/latest/api/Search/
"""

import argparse
import json
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# OneMap geocoder
# ---------------------------------------------------------------------------

# Nominatim (OSM) — free, no key required, 1 req/sec limit
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "promo-radar-scan/1.0 (geocoder)"}
# Must honour 1 req/sec rate limit
REQUEST_DELAY = 1.1  # seconds


def geocode_nominatim(address: str) -> tuple[float, float] | None:
    """Return (lat, lng) via OSM Nominatim, biased to Singapore."""
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={
                "q": f"{address}, Singapore",
                "format": "json",
                "limit": 1,
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
            # Sanity-check: must be in Singapore bounding box
            if 1.1 < lat < 1.5 and 103.5 < lng < 104.2:
                return lat, lng
    except Exception as e:
        print(f"  ✗ Nominatim error for '{address}': {e}")
    return None


# Known coordinates for places Nominatim doesn't recognise
KNOWN_COORDS: dict[str, tuple[float, float]] = {
    "SMU Li Ka Shing Library":          (1.29666, 103.85011),
    "SMU Li Ka Shing Library, B1-25":   (1.29666, 103.85011),
    "30 Victoria Street, #02-01B":      (1.29549, 103.85201),
}


def clean_address(raw: str) -> str:
    """
    Strip unit numbers and simplify so OneMap can match the building name.
    E.g. "Sengkang Grand Mall, 01-03" → "Sengkang Grand Mall"
    """
    import re
    # Remove unit/level patterns like ", 01-03" or "#B1-07"
    cleaned = re.sub(r"[,\s]+#?[BbLl]?\d{1,2}-\d{2,3}\b", "", raw)
    # Remove "Town Plaza" suffix noise
    cleaned = re.sub(r",\s*Town Plaza", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip().rstrip(",").strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="processed.jsonl")
    parser.add_argument("--output", default="processed_geo.jsonl")
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return

    # --- Pass 1: collect all unique location strings ---
    records: list[dict] = []
    all_locations: set[str] = set()

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
                pred = rec.get("prediction", rec)  # support both flat and nested
                for loc in pred.get("locations", []):
                    if loc and loc not in ("All outlets", "Selected outlets",
                                           "Singapore", "All Outlets"):
                        all_locations.add(loc)
            except json.JSONDecodeError:
                pass

    print(f"Loaded {len(records)} records with {len(all_locations)} unique locations to geocode.")

    # --- Pass 2: geocode unique locations (cache results) ---
    geo_cache: dict[str, tuple[float, float] | None] = {}

    for i, loc in enumerate(sorted(all_locations), 1):
        clean = clean_address(loc)
        print(f"[{i}/{len(all_locations)}] Geocoding: '{clean}' (from '{loc}')")

        # Try progressively simpler variants until one works
        candidates = [clean]
        if clean != loc:
            candidates.append(loc)
        # Also try just the first token before " & " for multi-outlet strings
        if " & " in clean:
            candidates.append(clean.split(" & ")[0].strip())
        # Try stripping trailing descriptors like "Canopy Plaza Level 1"
        if "," in clean:
            candidates.append(clean.split(",")[0].strip())

        result = None
        # Check known-coords overrides first (no API call needed)
        if loc in KNOWN_COORDS:
            result = KNOWN_COORDS[loc]
        elif clean in KNOWN_COORDS:
            result = KNOWN_COORDS[clean]
        else:
            for candidate in candidates:
                result = geocode_nominatim(candidate)
                if result:
                    break
                time.sleep(REQUEST_DELAY)

        geo_cache[loc] = result
        if result:
            print(f"  ✓ {result[0]:.5f}, {result[1]:.5f}")
        else:
            print(f"  ✗ Not found — will use None")

        time.sleep(REQUEST_DELAY)

    # --- Pass 3: write output with locations array [{name, lat, lng}, ...] ---
    ok = 0
    skipped = 0

    with output_path.open("w", encoding="utf-8") as f:
        for rec in records:
            pred = rec.get("prediction", rec)
            raw_locations: list[str] = pred.get("locations", [])

            # Build enriched locations array — every location kept, coords added where available
            enriched: list[dict] = []
            any_geocoded = False
            for loc in raw_locations:
                coords = geo_cache.get(loc)
                entry: dict = {"name": loc, "lat": None, "lng": None}
                if coords:
                    entry["lat"], entry["lng"] = coords
                    any_geocoded = True
                enriched.append(entry)

            # Replace flat locations list + old lat/lng with the new enriched array
            if "prediction" in rec:
                rec["prediction"]["locations"] = enriched
                # Remove old flat lat/lng fields if they exist
                rec["prediction"].pop("lat", None)
                rec["prediction"].pop("lng", None)
            else:
                rec["locations"] = enriched
                rec.pop("lat", None)
                rec.pop("lng", None)

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            if any_geocoded:
                ok += 1
            else:
                skipped += 1

    print(f"\nDone — {ok} deals with at least one geocoded location, {skipped} with no coordinates.")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
