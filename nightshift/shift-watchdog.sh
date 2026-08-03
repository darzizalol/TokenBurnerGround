#!/usr/bin/env bash
# shift-watchdog.sh — 07:05 safety net for the morning report.
#
# The clock-in and clock-out messages are sent by run-night.sh itself, which
# means a shift that never started sends nothing at all — silence that looks
# exactly like a quiet night. This runs five minutes after clock-out and speaks
# up only when no report landed.
#
# run-night.sh stamps nightshift/.last-report (epoch seconds) when it sends the
# clock-out report. A shift starting at 22:00 and ending any time before 07:00
# leaves a stamp less than 12 hours old, so that is the threshold.
#
# Best-effort and quiet by design: it says nothing on a normal morning.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$DIR/.last-report"
LOCK="$DIR/.night.lock"
MAX_AGE=43200   # 12h

# A human-requested halt is not a fault — don't page about it.
if grep -q "^STATUS: STOP" "$DIR/HELP.md" 2>/dev/null; then
  exit 0
fi

now=$(date +%s)
last=$(cat "$STAMP" 2>/dev/null || echo 0)
case "$last" in ''|*[!0-9]*) last=0 ;; esac
age=$(( now - last ))

if [ "$last" -gt 0 ] && [ "$age" -lt "$MAX_AGE" ]; then
  exit 0   # a report went out tonight — nothing to say
fi

if [ "$last" -gt 0 ]; then
  last_seen="$(date -d "@$last" '+%F %T' 2>/dev/null || echo "epoch $last") ($(( age / 3600 ))h ago)"
else
  last_seen="never"
fi

if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  lock_state="a night shift is STILL RUNNING (pid $(cat "$LOCK")) — 07:00 stop-night.sh did not kill it"
else
  lock_state="no night shift process is running"
fi

BODY="No night shift report was sent for the night just ended.

Last report: $last_seen
Process:     $lock_state
Host:        $(hostname)

Cron tail:
$(tail -n 15 "$DIR/logs/cron.log" 2>/dev/null || echo '(no cron.log)')

Check that the 22:00 cron fired and that run-night.sh got past its lock check."

"$DIR/telegram.sh" "⚠️ No night shift report — $(date '+%F')" "$BODY"
"$DIR/email.sh"    "⚠️ No night shift report — $(date '+%F')" "$BODY"
exit 0
