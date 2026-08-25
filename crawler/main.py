import os
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv
from telethon import TelegramClient

# Always load .env from the repo root (one level up from crawler/)
HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

# Add db/ to path so we can import db helpers
sys.path.insert(0, str(HERE.parent / "db"))

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# AWS S3
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("AWS_REGION", "ap-southeast-1")

s3 = boto3.client(
    "s3",
    region_name=S3_REGION
)

client = TelegramClient(
    str(HERE / "telegram_session"),
    API_ID,
    API_HASH
)

OUTPUT_FILE = HERE / "raw_messages_weekly.jsonl"

# ---------------------------------------------------------------------------
# Last-scrape tracking
# ---------------------------------------------------------------------------

LAST_SCRAPED_FILE = HERE / "last_scraped.json"
# Fallback window if no last_scraped.json exists yet
FALLBACK_DAYS = 7


def load_cutoff() -> datetime:
    """
    Return the cutoff datetime to scrape from.
    Uses the timestamp saved in last_scraped.json if it exists,
    otherwise falls back to FALLBACK_DAYS ago.
    """
    if LAST_SCRAPED_FILE.exists():
        try:
            data = json.loads(LAST_SCRAPED_FILE.read_text())
            cutoff = datetime.fromisoformat(data["last_scraped_at"])
            print(f"Resuming from last scrape: {cutoff.isoformat()}")
            return cutoff
        except Exception as e:
            print(f"Could not read {LAST_SCRAPED_FILE}, falling back to {FALLBACK_DAYS} days: {e}")

    cutoff = datetime.now(timezone.utc) - timedelta(days=FALLBACK_DAYS)
    print(f"No last_scraped.json found — scraping last {FALLBACK_DAYS} days.")
    return cutoff


def save_cutoff(dt: datetime):
    """Persist the scrape timestamp so the next run can resume from here."""
    LAST_SCRAPED_FILE.write_text(
        json.dumps({"last_scraped_at": dt.isoformat()}, indent=2)
    )
    print(f"Saved last scrape time: {dt.isoformat()}")


CUTOFF_DATE = load_cutoff()
# Record the time this run started — saved after a successful scrape
RUN_STARTED_AT = datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# Database connection (opened once, shared across all channel scrapes)
# ---------------------------------------------------------------------------

from db import create_tables, get_connection, upsert_raw_message  # noqa: E402

try:
    db_conn = get_connection()
    create_tables(db_conn)
except Exception as e:
    print(f"Warning: could not connect to database — messages will only be saved to file. ({e})")
    db_conn = None


def load_channels():
    with open(HERE / "channels.txt", "r", encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip() and not line.strip().startswith("#")
        ]


def save_message(message_data):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
        file.write(
            json.dumps(message_data, ensure_ascii=False) + "\n"
        )


async def save_image(message, channel_name):
    """
    Download Telegram image and upload it to S3.
    Returns the S3 object key, or None if there is no image or S3 is not configured.
    """
    if not message.photo:
        return None

    if not S3_BUCKET:
        return None

    # Example:
    # sgfooddeals/4030.jpg
    image_key = f"{channel_name}/{message.id}.jpg"

    try:
        # Download image from Telegram to memory
        image_bytes = await client.download_media(
            message,
            file=bytes
        )

        if not image_bytes:
            return None

        # Upload to S3
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=image_key,
            Body=image_bytes,
            ContentType="image/jpeg"
        )

        print(f"Uploaded image: {image_key}")

        return image_key

    except Exception as e:
        print(
            f"Failed to save image "
            f"{channel_name} message {message.id}: {e}"
        )

        return None


async def main():
    channels = load_channels()

    for channel_name in channels:
        print("\n" + "=" * 50)
        print(f"Crawling: {channel_name}")
        print("=" * 50)

        try:
            channel = await client.get_entity(channel_name)

            print(f"Reading: {channel.title}")

            async for message in client.iter_messages(
                channel,
                limit=800
            ):
                # Ignore messages without text
                if not message.text:
                    continue

                # Stop once we've gone past the cutoff
                if message.date and message.date < CUTOFF_DATE:
                    print(f"Reached cutoff ({CUTOFF_DATE.isoformat()}) for {channel_name}, stopping.")
                    break

                # Save image separately
                image_key = await save_image(
                    message,
                    channel_name
                )

                message_data = {
                    "channel": channel_name,
                    "channel_title": channel.title,
                    "message_id": message.id,
                    "posted_at": (
                        message.date.isoformat()
                        if message.date
                        else None
                    ),
                    "text": message.text,

                    # Only a reference to the image
                    "image_key": image_key
                }

                save_message(message_data)

                # Also save to database if connection is available
                if db_conn:
                    try:
                        with db_conn.cursor() as cur:
                            upsert_raw_message(cur, message_data)
                        db_conn.commit()
                    except Exception as e:
                        print(f"  DB error saving {channel_name} message {message.id}: {e}")
                        db_conn.rollback()

                print(
                    f"Saved {channel_name} "
                    f"message {message.id}"
                )

        except Exception as e:
            print(f"Failed to crawl {channel_name}: {e}")


with client:
    client.loop.run_until_complete(main())
    # Only update the cutoff after all channels have been scraped successfully
    save_cutoff(RUN_STARTED_AT)
    if db_conn:
        db_conn.close()