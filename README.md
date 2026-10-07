# 📡 Promo Radar

> Automatically collects Singapore deals from Telegram, enriches them with AI, and surfaces them on an interactive map.

**Live site →** [nickusleejiasheng.github.io/promo-radar-scan](https://nickusleejiasheng.github.io/promo-radar-scan/)

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TELEGRAM CHANNELS                            │
│                  @goodlobang  @sgfooddeals  ...                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Raw message text + images
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1 — SCRAPE  (crawler/main.py)                                 │
│                                                                     │
│  • Telethon reads messages since last_scraped.json timestamp        │
│  • Downloads attached images → uploads to Supabase Storage          │
│  • Saves raw text + image path to raw_messages table (Neon DB)      │
│  • Updates last_scraped.json so next run is incremental             │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Unprocessed rows in raw_messages
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2 — AI EXTRACTION  (ai/process.py)                            │
│                                                                     │
│  • Sends each unprocessed message to OpenRouter LLM                 │
│  • System prompt instructs model to return strict JSON:             │
│      merchant, category, offer, price, discount,                    │
│      valid_from, valid_to, locations, promo_code, ...               │
│  • Parsed result upserted into deals table                          │
│  • Skips non-deals (roundups, announcements)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Deals with location names (no coords yet)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3 — GEOCODE  (crawler/geocode.py)                             │
│                                                                     │
│  • For each outlet name extracted by AI, queries Nominatim (OSM)    │
│  • Validates coords are within Singapore bounding box               │
│  • Local in-memory cache avoids duplicate API calls per run         │
│  • Hardcoded fallback table for venues Nominatim can't find         │
│  • Writes lat/lng back into deals.locations JSONB column            │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Deals still missing coordinates
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4 — BRAND LOOKUP  (crawler/brand_locations.py)                │
│                                                                     │
│  • Finds deals where all locations still have null lat/lng          │
│  • Searches OneMap API (SG govt) by merchant name                   │
│  • If OneMap returns nothing → asks LLM to list known SG outlets    │
│    → geocodes each via Nominatim                                     │
│  • Results cached in brand_outlets table (never re-queried)         │
└────────────────────────────┬────────────────────────────────────────┘
                             │  All deals enriched
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5 — DEDUP  (crawler/dedup.py)                                 │
│                                                                     │
│  • Groups deals by (valid_from, valid_to)                           │
│  • Computes Jaccard token similarity on merchant + offer text       │
│  • Deals with >80% similarity treated as cross-channel duplicates   │
│  • Earliest-posted deal kept, duplicate deleted                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6 — CLEANUP  (crawler/cleanup.py)                             │
│                                                                     │
│  • Deletes deals where valid_to < today                             │
│  • Deletes orphaned raw_messages no longer linked to any deal       │
│  • Deletes corresponding images from Supabase Storage               │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Clean, enriched deals in Neon DB
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  API  (functions/index.js — Google Cloud Run)                       │
│                                                                     │
│  GET /deals                                                         │
│  • Queries deals JOIN raw_messages from Neon DB                     │
│  • Generates Supabase signed URLs for each deal image (1hr expiry)  │
│  • Returns JSON array with CORS headers + 5min CDN cache            │
└────────────────────────────┬────────────────────────────────────────┘
                             │  JSON deals array
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND  (site/ — React 19 + Vite + TanStack Router)              │
│                                                                     │
│  • Fetches deals from Cloud Run on load (5min stale-while-revalidate│
│  • Interactive Leaflet map with category-coloured markers           │
│  • Blue dot shows user's current GPS location                       │
│  • Locate-me button flies map back to user position                 │
│  • Category filter, search, saved deals (localStorage)             │
│  • Deal detail page with full info, image, location map             │
│                                                                     │
│  Deployed to GitHub Pages via GitHub Actions on every push to main  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Features

- **Incremental scraping** — tracks last scrape timestamp so only new messages are fetched each run
- **LLM deal extraction** — parses unstructured Telegram promo text into structured fields: merchant, category, price, discount, validity dates, promo codes, outlet locations
- **Multi-stage geocoding** — outlet names resolved via Nominatim → OneMap → AI fallback, with a persistent `brand_outlets` cache so each brand is only looked up once
- **Smart deduplication** — same deal posted across multiple channels detected via Jaccard token similarity on offer text and merchant name normalisation
- **Automated cleanup** — expired deals and their Supabase Storage images are deleted daily
- **Interactive map** — Leaflet map with category-coloured markers, user location dot, and locate-me button
- **Signed image URLs** — deal images served securely via Supabase Storage time-limited signed URLs
- **Daily CI/CD** — GitHub Actions runs the full pipeline on schedule and deploys the frontend on every push

---

## Tech Stack

| Layer | Technology |
|---|---|
| Scraper | Python, Telethon |
| AI extraction | OpenRouter (Gemini / GPT-class models) |
| Geocoding | Nominatim (OSM), OneMap (Singapore) |
| Database | Neon (serverless PostgreSQL) |
| Image storage | Supabase Storage |
| API | Google Cloud Run Functions, Node.js |
| Frontend | React 19, TypeScript, TanStack Router, Leaflet, Tailwind CSS, shadcn/ui |
| Build | Vite |
| CI/CD | GitHub Actions → GitHub Pages |

---

## Project Structure

```
promo-radar-scan/
├── crawler/
│   ├── main.py               # Telegram scraper (Telethon)
│   ├── geocode.py            # Geocode outlet names via Nominatim
│   ├── brand_locations.py    # Fill missing locations via OneMap + AI fallback
│   ├── dedup.py              # Merge near-duplicate deals (Jaccard similarity)
│   ├── cleanup.py            # Remove expired deals + orphaned Supabase images
│   └── channels.txt          # Telegram channels to scrape
├── ai/
│   └── process.py            # LLM deal extraction via OpenRouter
├── db/
│   ├── db.py                 # DB connection, table creation, upsert helpers
│   └── load_to_db.py         # Manual JSONL → DB loader
├── functions/
│   └── index.js              # Google Cloud Run Function — GET /deals API
├── site/                     # React 19 frontend (Vite + TanStack Router)
├── pipeline.py               # Orchestrates all pipeline steps
└── .github/workflows/
    ├── deploy.yml            # Build & deploy frontend to GitHub Pages
    └── pipeline.yml          # Run data pipeline daily at 10:00 SGT
```

---

## Pipeline

The full pipeline runs 6 steps in sequence, triggered daily at 10:00 SGT via GitHub Actions:

| Step | Script | What it does |
|---|---|---|
| 1 | `crawler/main.py` | Scrape new Telegram messages → `raw_messages` table |
| 2 | `ai/process.py` | LLM extracts deal fields → `deals` table |
| 3 | `crawler/geocode.py` | Resolve outlet names to coordinates via Nominatim |
| 4 | `crawler/brand_locations.py` | Fill null locations via OneMap + AI fallback |
| 5 | `crawler/dedup.py` | Merge near-duplicate deals across channels |
| 6 | `crawler/cleanup.py` | Delete expired deals + orphaned Supabase images |

**Run locally:**

```bash
python pipeline.py                           # run all steps
python pipeline.py --skip-scrape             # skip step 1
python pipeline.py --skip-process            # skip step 2
python pipeline.py --skip-geocode            # skip step 3
python pipeline.py --skip-brand-locations    # skip step 4
python pipeline.py --skip-dedup              # skip step 5
python pipeline.py --skip-cleanup            # skip step 6
python pipeline.py --model google/gemini-2.0-flash-exp:free
python pipeline.py --limit 50               # process only 50 messages
python pipeline.py --reprocess              # redo already-processed messages
```

---

## Location Handling

Deal locations are resolved in three stages:

1. **Geocode** — outlet names extracted by the LLM are geocoded via Nominatim, with a hardcoded fallback table for venues it doesn't recognise
2. **OneMap lookup** — for deals with no locations, the merchant name is searched against the [OneMap API](https://www.onemap.gov.sg) (Singapore's official mapping service). Results are cached in a `brand_outlets` table so each merchant is only looked up once
3. **AI fallback** — if OneMap returns nothing, the LLM is asked to enumerate known Singapore outlet locations for that brand, which are then geocoded via Nominatim

> **Potential future improvement:** A more complete approach would use the LLM to enumerate all outlets for every brand regardless of whether OneMap found results. This was not implemented due to AI token cost at scale — it remains a viable improvement once a cheaper or locally-hosted model is available.

---

## Environment Variables

Create a `.env` file in the repo root:

```env
# Telegram
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# OpenRouter
OPENROUTER_API_KEY=

# Neon PostgreSQL
DATABASE_URL=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_BUCKET=deal-images

# Frontend (Cloud Run Function URL — injected at Vite build time)
VITE_GCF_URL=
```

---

## Deployment

### Backend API (Google Cloud Run)

The Cloud Function is in `functions/`. For the first deploy, run manually to get the URL:

```bash
gcloud functions deploy deals \
  --runtime nodejs20 \
  --trigger-http \
  --allow-unauthenticated \
  --region asia-southeast1 \
  --source functions/
```

Copy the returned URL → add as `VITE_GCF_URL` GitHub secret.

Set these environment variables in the Cloud Run console:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `SUPABASE_BUCKET` | Supabase storage bucket name |
| `ALLOWED_ORIGIN` | Your GitHub Pages URL (e.g. `https://username.github.io`) |

### GitHub Actions Secrets

| Secret | Description |
|---|---|
| `TELEGRAM_API_ID` | Telegram app API ID |
| `TELEGRAM_API_HASH` | Telegram app API hash |
| `TELEGRAM_SESSION` | base64-encoded `telegram_session.session` file |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `SUPABASE_BUCKET` | Supabase storage bucket name |
| `VITE_GCF_URL` | Deployed Cloud Run Function URL |

Once secrets are set, push to `main` — the frontend deploys automatically. The data pipeline runs daily at 10:00 SGT or can be triggered manually from the Actions tab.

### Encode Telegram session for CI

```bash
base64 -i crawler/telegram_session.session | tr -d '\n'
```

Copy the output as the `TELEGRAM_SESSION` secret value.

---

## Local Development

**Python pipeline:**

```bash
pip install -r crawler/requirements.txt
```

**Frontend:**

```bash
cd site
npm install
npm run dev
```

**Cloud Function (local):**

```bash
cd functions
npm install
npm start
# Serves at http://localhost:8080
```
