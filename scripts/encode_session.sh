#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# encode_session.sh
#
# Base64-encodes the Telegram session file so it can be stored as a CI secret.
#
# Usage:
#   chmod +x scripts/encode_session.sh
#   ./scripts/encode_session.sh
#
# Then copy the printed value and add it as:
#   GitHub → Settings → Secrets → Actions → TELEGRAM_SESSION
#   GitLab → Settings → CI/CD → Variables → TELEGRAM_SESSION  (Masked = on)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SESSION_FILE="$(dirname "$0")/../crawler/telegram_session.session"

if [ ! -f "$SESSION_FILE" ]; then
  echo "❌  Session file not found at: $SESSION_FILE"
  echo "    Run the crawler locally first so Telethon creates it."
  exit 1
fi

echo "✅  Encoded session (copy the value below into your CI secret):"
echo ""
base64 < "$SESSION_FILE"
