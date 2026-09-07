"""
db.py
Database helpers for Neon PostgreSQL.

Provides:
  - get_connection()  — returns a psycopg2 connection using DATABASE_URL from .env
  - create_table()    — creates the deals table if it doesn't exist
  - upsert_deal()     — inserts or updates a single deal row
"""

import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Always load .env from the repo root (one level up from db/)
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Return a psycopg2 connection to Neon."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in your .env file.")
    return psycopg2.connect(DATABASE_URL, sslmode="require")


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS brand_outlets (
    id           SERIAL PRIMARY KEY,
    merchant     TEXT UNIQUE NOT NULL,
    outlets      JSONB NOT NULL DEFAULT '[]',
    looked_up_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_messages (
    id            SERIAL PRIMARY KEY,
    channel       TEXT,
    channel_title TEXT,
    message_id    INTEGER,
    posted_at     TIMESTAMPTZ,
    text          TEXT,
    image_url     TEXT,
    scraped_at    TIMESTAMPTZ DEFAULT NOW(),
    processed     BOOLEAN DEFAULT FALSE,
    UNIQUE (channel, message_id)
);

CREATE TABLE IF NOT EXISTS deals (
    id                SERIAL PRIMARY KEY,
    channel           TEXT,
    channel_title     TEXT,
    message_id        INTEGER,
    posted_at         TIMESTAMPTZ,
    posted_date       DATE,
    raw_input         TEXT,
    merchant          TEXT,
    category          TEXT,
    offer             TEXT,
    price             TEXT,
    original_price    TEXT,
    discount          TEXT,
    valid_from        DATE,
    valid_to          DATE,
    time              TEXT,
    locations         JSONB,
    redemption_method TEXT,
    restrictions      JSONB,
    promo_code        TEXT,
    more_info         TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    -- Deduplicate across channels: same merchant + offer + validity = same promo
    UNIQUE (merchant, offer, valid_from, valid_to)
);
"""


# Older DBs stored image_url as BYTEA. CREATE TABLE IF NOT EXISTS never fixes that.
MIGRATE_IMAGE_URL_TO_TEXT_SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'raw_messages'
          AND column_name = 'image_url'
          AND udt_name = 'bytea'
    ) THEN
        ALTER TABLE raw_messages
            ALTER COLUMN image_url TYPE TEXT
            USING convert_from(image_url, 'UTF8');
    END IF;
END $$;
"""


def create_tables(conn):
    """Create all tables if they don't already exist."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLES_SQL)
        cur.execute(MIGRATE_IMAGE_URL_TO_TEXT_SQL)
    conn.commit()
    print("Tables 'brand_outlets', 'raw_messages' and 'deals' are ready.")


# Keep old name as an alias for load_to_db.py compatibility
def create_table(conn):
    create_tables(conn)


UPSERT_RAW_MESSAGE_SQL = """
INSERT INTO raw_messages (channel, channel_title, message_id, posted_at, text, image_url)
VALUES (%(channel)s, %(channel_title)s, %(message_id)s, %(posted_at)s, %(text)s, %(image_url)s)
ON CONFLICT (channel, message_id)
DO UPDATE SET
    channel_title = EXCLUDED.channel_title,
    posted_at     = EXCLUDED.posted_at,
    text          = EXCLUDED.text,
    image_url     = EXCLUDED.image_url;
"""


def upsert_raw_message(cur, message_data: dict):
    """Upsert a single raw scraped message."""
    cur.execute(UPSERT_RAW_MESSAGE_SQL, {
        "channel":       message_data.get("channel"),
        "channel_title": message_data.get("channel_title"),
        "message_id":    message_data.get("message_id"),
        "posted_at":     message_data.get("posted_at"),
        "text":          message_data.get("text"),
        "image_url":     message_data.get("image_url"),
    })


UPSERT_SQL = """
INSERT INTO deals (
    channel, channel_title, message_id, posted_at, posted_date,
    raw_input, merchant, category, offer, price, original_price,
    discount, valid_from, valid_to, time, locations,
    redemption_method, restrictions, promo_code, more_info, updated_at
) VALUES (
    %(channel)s, %(channel_title)s, %(message_id)s, %(posted_at)s, %(posted_date)s,
    %(raw_input)s, %(merchant)s, %(category)s, %(offer)s, %(price)s, %(original_price)s,
    %(discount)s, %(valid_from)s, %(valid_to)s, %(time)s, %(locations)s,
    %(redemption_method)s, %(restrictions)s, %(promo_code)s, %(more_info)s, NOW()
)
ON CONFLICT (merchant, offer, valid_from, valid_to)
DO UPDATE SET
    -- Keep the earliest channel that posted this deal
    channel           = CASE WHEN deals.posted_at <= EXCLUDED.posted_at THEN deals.channel ELSE EXCLUDED.channel END,
    channel_title     = CASE WHEN deals.posted_at <= EXCLUDED.posted_at THEN deals.channel_title ELSE EXCLUDED.channel_title END,
    message_id        = CASE WHEN deals.posted_at <= EXCLUDED.posted_at THEN deals.message_id ELSE EXCLUDED.message_id END,
    posted_at         = LEAST(deals.posted_at, EXCLUDED.posted_at),
    posted_date       = LEAST(deals.posted_date, EXCLUDED.posted_date),
    raw_input         = CASE WHEN deals.posted_at <= EXCLUDED.posted_at THEN deals.raw_input ELSE EXCLUDED.raw_input END,
    -- Always take the latest processed fields in case geocoding improved
    category          = EXCLUDED.category,
    price             = EXCLUDED.price,
    original_price    = EXCLUDED.original_price,
    discount          = EXCLUDED.discount,
    time              = EXCLUDED.time,
    locations         = EXCLUDED.locations,
    redemption_method = EXCLUDED.redemption_method,
    restrictions      = EXCLUDED.restrictions,
    promo_code        = EXCLUDED.promo_code,
    more_info         = EXCLUDED.more_info,
    updated_at        = NOW();
"""


def upsert_deal(cur, record: dict):
    """
    Upsert a single deal from a processed_geo.jsonl record.
    Expects the new locations format: [{"name": ..., "lat": ..., "lng": ...}, ...]
    """
    pred = record.get("prediction", record)

    params = {
        "channel":           record.get("channel"),
        "channel_title":     record.get("channel_title"),
        "message_id":        record.get("message_id"),
        "posted_at":         record.get("posted_at"),
        "posted_date":       record.get("posted_date"),
        "raw_input":         record.get("input"),
        "merchant":          pred.get("merchant"),
        "category":          pred.get("category"),
        "offer":             pred.get("offer"),
        "price":             pred.get("price"),
        "original_price":    pred.get("original_price"),
        "discount":          pred.get("discount"),
        "valid_from":        pred.get("valid_from") or None,
        "valid_to":          pred.get("valid_to") or None,
        "time":              pred.get("time"),
        # locations is already a list of {name, lat, lng} dicts after geocode.py update
        "locations":         json.dumps(pred.get("locations", [])),
        "redemption_method": pred.get("redemption_method"),
        "restrictions":      json.dumps(pred.get("restrictions", [])),
        "promo_code":        pred.get("promo_code"),
        "more_info":         pred.get("more_info"),
    }

    cur.execute(UPSERT_SQL, params)
