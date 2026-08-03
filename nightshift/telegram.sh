#!/usr/bin/env bash
# telegram.sh — message the human on Telegram. Usage: telegram.sh "Subject" "Body"
#
# Transport: Telegram Bot API sendMessage via curl. Same two-argument contract
# as email.sh, so both can be driven from one composed body.
# Reads from nightshift/.env (gitignored — this repo is public, never
# commit credentials):
#   TELEGRAM_BOT_TOKEN  bot token from @BotFather
#   TELEGRAM_CHAT_ID    destination chat (your own user id, or a group id)
#
# Telegram caps one message at 4096 characters. A night-shift report with 40
# commits and a nightlog tail blows past that, so long bodies are split on line
# boundaries and sent as numbered parts rather than truncated.
#
# Setup: message the bot once from Telegram (send /start — a bot cannot open a
# conversation with you), then run `telegram.sh --resolve-chat-id` to print the
# chat ids it can see, and put the right one in .env.
#
# Best-effort: never fails the caller.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$DIR/.env" ] && . "$DIR/.env"

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN:-}"
MAX=3600   # headroom under Telegram's 4096 for the header, quote tags and marker

# --- chat id discovery --------------------------------------------------------
if [ "${1:-}" = "--resolve-chat-id" ]; then
  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "telegram.sh: TELEGRAM_BOT_TOKEN not set in nightshift/.env" >&2
    exit 1
  fi
  curl -fsS -m 20 "$API/getUpdates" | python3 -c '
import json, sys
seen = {}
for upd in json.load(sys.stdin).get("result", []):
    for key in ("message", "edited_message", "channel_post", "my_chat_member"):
        chat = (upd.get(key) or {}).get("chat")
        if not chat or chat.get("id") is None:
            continue
        seen[chat["id"]] = (
            chat.get("title")
            or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
            or chat.get("username")
            or chat.get("type", "")
        )
if not seen:
    sys.exit("no chats yet — open Telegram, send the bot /start, then re-run")
for cid, name in seen.items():
    print(f"{cid}\t{name}")
'
  exit $?
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "telegram.sh: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in nightshift/.env — skipping telegram" >&2
  exit 0
fi

SUBJECT="${1:-Night Shift}"
BODY="${2:-(no message provided)}"

# HTML is the safe parse mode here: only three characters need escaping, versus
# MarkdownV2's eighteen. Commit subjects and log lines are arbitrary text.
esc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

HEADER="<b>$(printf '%s' "$SUBJECT" | esc)</b>"
TEXT="$(printf '%s' "$BODY" | esc)"

# --- split on line boundaries -------------------------------------------------
# Split first, wrap second. The body is sent as a Telegram quote, and a
# <blockquote> spanning a chunk boundary would leave unbalanced HTML and earn a
# 400 — so each chunk opens and closes its own quote below.
# Deliberately no <pre>/<code> spans either: same hazard, and monospace reads
# worse than plain text on a phone.
CHUNKS=()
cur=""
while IFS= read -r line || [ -n "$line" ]; do
  # A single line longer than the cap (a pasted URL, a runaway log line) has no
  # boundary to split on — hard-wrap it.
  while [ ${#line} -gt "$MAX" ]; do
    [ -n "$cur" ] && { CHUNKS+=("$cur"); cur=""; }
    CHUNKS+=("${line:0:$MAX}")
    line="${line:$MAX}"
  done
  if [ $(( ${#cur} + ${#line} + 1 )) -gt "$MAX" ]; then
    CHUNKS+=("$cur")
    cur="$line"
  elif [ -n "$cur" ]; then
    cur="$cur"$'\n'"$line"
  else
    cur="$line"
  fi
done <<< "$TEXT"
[ -n "$cur" ] && CHUNKS+=("$cur")
[ ${#CHUNKS[@]} -eq 0 ] && CHUNKS=("(empty)")

# --- send ---------------------------------------------------------------------
n=${#CHUNKS[@]}
i=0
failed=0
for chunk in "${CHUNKS[@]}"; do
  i=$((i + 1))
  # The quote wraps the body only: the header stays outside it so the subject
  # line remains scannable in the chat list, and so does the part marker.
  payload="<blockquote>$chunk</blockquote>"
  [ "$i" = 1 ] && payload="$HEADER"$'\n'"$payload"
  [ "$n" -gt 1 ] && payload="$payload"$'\n'"<i>($i/$n)</i>"

  # -f is omitted on purpose: on a 400 we want Telegram's "description" field,
  # which -f would swallow. Success is the "ok":true in the JSON body.
  resp=$(curl -sS -m 30 -X POST "$API/sendMessage" \
    --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
    --data-urlencode "parse_mode=HTML" \
    --data-urlencode "disable_web_page_preview=true" \
    --data-urlencode "text=$payload" 2>&1)
  case "$resp" in
    *'"ok":true'*) ;;
    *) echo "telegram.sh: send failed (part $i/$n) — $resp" >&2; failed=1 ;;
  esac
  [ "$i" -lt "$n" ] && sleep 0.3   # keep the parts in order
done

[ "$failed" = 0 ] && echo "telegram.sh: sent — $SUBJECT ($n part(s))"
exit 0
