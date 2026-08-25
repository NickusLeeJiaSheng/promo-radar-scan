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
CREATE TABLE IF NOT EXISTS raw_messages (
    id            SERIAL PRIMARY KEY,
    channel       TEXT,
    channel_title TEXT,
    message_id    INTEGER,
    posted_at     TIMESTAMPTZ,
    text          TEXT,
    image_key     TEXT,
    scraped_at    TIMESTAMPTZ DEFAULT NOW(),
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
    -- locations is an array of {name, lat, lng} objects
    locations         JSONB,
    redemption_method TEXT,
    restrictions      JSONB,
    promo_code        TEXT,
    more_info         TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (channel, message_id)
);
"""


def create_tables(conn):
    """Create all tables if they don't already exist."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLES_SQL)
    conn.commit()
    print("Tables 'raw_messages' and 'deals' are ready.")


# Keep old name as an alias for load_to_db.py compatibility
def create_table(conn):
    create_tables(conn)


UPSERT_RAW_MESSAGE_SQL = """
INSERT INTO raw_messages (channel, channel_title, message_id, posted_at, text, image_key)
VALUES (%(channel)s, %(channel_title)s, %(message_id)s, %(posted_at)s, %(text)s, %(image_key)s)
ON CONFLICT (channel, message_id)
DO UPDATE SET
    channel_title = EXCLUDED.channel_title,
    posted_at     = EXCLUDED.posted_at,
    text          = EXCLUDED.text,
    image_key     = EXCLUDED.image_key;
"""


def upsert_raw_message(cur, message_data: dict):
    """Upsert a single raw scraped message."""
    cur.execute(UPSERT_RAW_MESSAGE_SQL, {
        "channel":       message_data.get("channel"),
        "channel_title": message_data.get("channel_title"),
        "message_id":    message_data.get("message_id"),
        "posted_at":     message_data.get("posted_at"),
        "text":          message_data.get("text"),
        "image_key":     message_data.get("image_key"),
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
ON CONFLICT (channel, message_id)
DO UPDATE SET
    channel_title     = EXCLUDED.channel_title,
    posted_at         = EXCLUDED.posted_at,
    posted_date       = EXCLUDED.posted_date,
    raw_input         = EXCLUDED.raw_input,
    merchant          = EXCLUDED.merchant,
    category          = EXCLUDED.category,
    offer             = EXCLUDED.offer,
    price             = EXCLUDED.price,
    original_price    = EXCLUDED.original_price,
    discount          = EXCLUDED.discount,
    valid_from        = EXCLUDED.valid_from,
    valid_to          = EXCLUDED.valid_to,
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
