#!/usr/bin/env bash
# notify.sh — ping the human when something needs human hands.
# Usage: nightshift/notify.sh "Short title" "One-line summary and what to do"
#
# Channels:
#   1. Linux desktop notification (notify-send) — always attempted.
#   2. Email via Web3Forms (email.sh) — if WEB3FORMS_KEY is set in nightshift/.env.
#   3. Phone push via ntfy.sh — only if NTFY_TOPIC is set in nightshift/.env.
#      (Install the ntfy app, subscribe to your topic, done. No account needed.)
#
# This script never fails the caller: notification channels are best-effort.
# The durable record of the escalation belongs in nightshift/HELP.md.

set -u

TITLE="${1:-Night Shift}"
MSG="${2:-(no message provided)}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Optional config (NTFY_TOPIC=...)
[ -f "$DIR/.env" ] && . "$DIR/.env"

# Cron/headless sessions have no desktop env vars; point at the user session bus.
export DISPLAY="${DISPLAY:-:0}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"

if command -v notify-send >/dev/null 2>&1; then
  notify-send --urgency=critical --app-name="Night Shift" "🌙 $TITLE" "$MSG" 2>/dev/null || true
fi

"$DIR/email.sh" "⚠️ $TITLE" "$MSG" >/dev/null 2>&1 || true

if [ -n "${NTFY_TOPIC:-}" ]; then
  curl -fsS -m 10 -H "Title: $TITLE" -H "Priority: high" -H "Tags: crescent_moon" \
    -d "$MSG" "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1 || true
fi
