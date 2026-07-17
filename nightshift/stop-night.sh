#!/usr/bin/env bash
# stop-night.sh — hard stop for the night shift, run by cron at 07:00.
# Kills the orchestrator and everything it spawned (its process group).
# run-night.sh is started with setsid, so its pid == its process group id.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK="$DIR/.night.lock"

[ -e "$LOCK" ] || exit 0
PID="$(cat "$LOCK" 2>/dev/null)"
[ -n "$PID" ] || { rm -f "$LOCK"; exit 0; }

if kill -0 "$PID" 2>/dev/null; then
  kill -TERM -- "-$PID" 2>/dev/null
  sleep 10
  kill -KILL -- "-$PID" 2>/dev/null
  echo "[$(date '+%F %T')] stop-night: terminated night shift (pgid $PID)" \
    >> "$DIR/logs/night-$(date +%Y%m%d).log"
fi
rm -f "$LOCK"
