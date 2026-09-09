# Promo Radar

An automated pipeline that scrapes Singapore deal and promotion posts from Telegram channels, uses an LLM to extract structured deal data, geocodes outlet locations, and serves everything through a cloud API to a React frontend.

---

## Features

- Scrapes messages and images from Telegram channels on an incremental schedule
- Uses an LLM (via OpenRouter) to parse unstructured promo text into structured fields - merchant, category, price, discount, validity dates, promo codes, outlet locations
- Geocodes outlet locations via Nominatim (OpenStreetMap)
- Fills missing outlet locations by searching OneMap with the merchant name
- Stores raw messages and enriched deals in a Neon (serverless PostgreSQL) database
- Serves deal data through a Google Cloud Function HTTP API with Supabase-signed image URLs
- React 19 frontend with an interactive Leaflet map, category filtering, and saved deals

---

## Tech Stack

| Layer | Technology |
|---|---|
| Scraper | Python, Telethon |
| AI extraction | OpenRouter (Gemini / GPT-class models) |
| Geocoding | Nominatim (OSM), OneMap (Singapore) |
| Database | Neon (serverless PostgreSQL), psycopg2 |
| Image storage | Supabase Storage |
| API | Google Cloud Functions, Node.js |
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
│   ├── brand_locations.py    # Fill missing locations via OneMap brand search
│   └── channels.txt          # List of Telegram channels to scrape
├── ai/
│   └── process.py            # LLM deal extraction via OpenRouter
├── db/
│   ├── db.py                 # DB connection, table creation, upsert helpers
│   └── load_to_db.py         # Manual JSONL → DB loader
├── functions/
│   └── index.js              # Google Cloud Function — GET /deals API
├── site/                     # React frontend (Vite + TanStack Router)
├── pipeline.py               # Orchestrates all pipeline steps
└── .github/workflows/
    └── deploy.yml            # CI/CD: deploy GCF + build and deploy GitHub Pages
```

---

## Pipeline

The pipeline runs four steps in sequence:

```
1. Scrape       — fetch new Telegram messages → raw_messages table
2. Process      — LLM extracts deal fields   → deals table
3. Geocode      — resolve outlet names to coordinates (Nominatim)
4. Brand lookup — fill remaining null locations via OneMap merchant search
```

Run the full pipeline:

```bash
python pipeline.py
```

Skip individual steps:

```bash
python pipeline.py --skip-scrape
python pipeline.py --skip-process
python pipeline.py --skip-geocode
python pipeline.py --skip-brand-locations
```

Other options:

```bash
python pipeline.py --model google/gemini-2.0-flash-exp:free   # override LLM model
python pipeline.py --limit 50                                  # process only 50 messages
python pipeline.py --reprocess                                 # redo already-processed messages
```

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

# Frontend (Cloud Function URL — used by Vite build)
VITE_GCF_URL=
```

---

## Deployment

### Cloud Function (API)

The `deploy.yml` workflow deploys the Cloud Function automatically on every push to `main`. For the first deploy, run manually to get the function URL:

```bash
gcloud functions deploy deals \
  --runtime nodejs20 \
  --trigger-http \
  --allow-unauthenticated \
  --region asia-southeast1 \
  --source functions/
```

Copy the returned URL and add it as the `VITE_GCF_URL` GitHub secret.

### GitHub Actions Secrets

| Secret | Description |
|---|---|
| `GCF_SA_KEY` | GCP Service Account key JSON (base64-encoded) |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `SUPABASE_BUCKET` | Supabase storage bucket name |
| `VITE_GCF_URL` | Deployed Cloud Function URL |

Once secrets are set, push to `main` — the workflow builds and deploys both the API and the frontend automatically.

---

## Location Handling

Deal locations are resolved in two stages:

1. **Geocode step** — outlet names extracted by the LLM are geocoded individually via Nominatim, with a local coordinate cache and a hardcoded fallback table for venues Nominatim doesn't recognise.

2. **Brand lookup step** — for deals where the message didn't mention any locations, the merchant name is searched against the [OneMap API](https://www.onemap.gov.sg) (Singapore's official mapping service) to discover known outlet coordinates. Results are cached in a `brand_outlets` table so each merchant is only looked up once.

### Potential future improvement

A further enhancement would be to use an LLM to enumerate all outlets for a given brand (Option 2), which could yield more complete and descriptive outlet data than a map search alone. This approach was not implemented due to AI token cost — querying per brand across many merchants would consume significant tokens. It remains a viable improvement once a cheaper or locally-hosted model is available.

---

## Local Development

Install Python dependencies:

```bash
pip install -r crawler/requirements.txt
pip install psycopg2-binary python-dotenv requests
```

Install and run the frontend locally:

```bash
cd site
npm install
npm run dev
```

Install and run the Cloud Function locally:

```bash
cd functions
npm install
npm start
```
