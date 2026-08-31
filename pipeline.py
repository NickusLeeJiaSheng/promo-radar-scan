"""
pipeline.py
Runs the full deal pipeline in sequence:

    1. crawler/main.py    — scrape new Telegram messages → raw_messages table
    2. ai/process.py      — call OpenRouter on unprocessed rows → deals table
    3. crawler/geocode.py — geocode locations in the deals table

Usage:
    python pipeline.py                   # run all steps
    python pipeline.py --skip-scrape     # skip step 1 (use existing raw_messages)
    python pipeline.py --skip-process    # skip step 2
    python pipeline.py --skip-geocode    # skip step 3
    python pipeline.py --model google/gemini-2.0-flash-exp:free
    python pipeline.py --limit 50        # only process 50 raw messages
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

CRAWLER  = HERE / "crawler" / "main.py"
PROCESS  = HERE / "ai"      / "process.py"
GEOCODE  = HERE / "crawler" / "geocode.py"


def run(label: str, cmd: list[str]) -> bool:
    """Run a subprocess step, streaming output. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"  STEP: {label}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        print(f"\n✗ '{label}' failed with exit code {result.returncode}")
        return False
    print(f"\n✓ '{label}' completed successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run the full promo-radar pipeline")
    parser.add_argument("--skip-scrape",  action="store_true", help="Skip the Telegram scrape step")
    parser.add_argument("--skip-process", action="store_true", help="Skip the OpenRouter processing step")
    parser.add_argument("--skip-geocode", action="store_true", help="Skip the geocoding step")
    parser.add_argument("--model",  default=None, help="Override OpenRouter model for process.py")
    parser.add_argument("--limit",  type=int, default=None, help="Limit messages processed by process.py")
    parser.add_argument("--reprocess", action="store_true", help="Re-process already-processed messages")
    args = parser.parse_args()

    steps_run = 0
    steps_failed = 0

    # ── Step 1: Scrape ────────────────────────────────────────────────────────
    if not args.skip_scrape:
        ok = run("Scrape Telegram channels", [sys.executable, str(CRAWLER)])
        if not ok:
            steps_failed += 1
            print("Aborting pipeline — scrape failed.")
            sys.exit(1)
        steps_run += 1
    else:
        print("Skipping scrape step.")

    # ── Step 2: Process via OpenRouter ───────────────────────────────────────
    if not args.skip_process:
        process_cmd = [sys.executable, str(PROCESS)]
        if args.model:
            process_cmd += ["--model", args.model]
        if args.limit:
            process_cmd += ["--limit", str(args.limit)]
        if args.reprocess:
            process_cmd += ["--reprocess"]

        ok = run("Process raw messages with OpenRouter", process_cmd)
        if not ok:
            steps_failed += 1
            print("Aborting pipeline — processing failed.")
            sys.exit(1)
        steps_run += 1
    else:
        print("Skipping process step.")

    # ── Step 3: Geocode ───────────────────────────────────────────────────────
    if not args.skip_geocode:
        ok = run("Geocode deal locations", [sys.executable, str(GEOCODE)])
        if not ok:
            steps_failed += 1
        else:
            steps_run += 1
    else:
        print("Skipping geocode step.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Pipeline complete — {steps_run} steps succeeded, {steps_failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
