#!/usr/bin/env bash
# install-cron.sh — arm (or re-arm) the night shift timers. Idempotent.
#   22:00 start the orchestrator (setsid gives it its own process group)
#   07:00 hard-stop anything still running

set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Paths may contain spaces — keep them quoted in the crontab lines.
( crontab -l 2>/dev/null | grep -v '# nightshift' || true
  echo "0 22 * * * /usr/bin/setsid \"$DIR/run-night.sh\" >> \"$DIR/logs/cron.log\" 2>&1 # nightshift"
  echo "0 7 * * * \"$DIR/stop-night.sh\" >> \"$DIR/logs/cron.log\" 2>&1 # nightshift"
) | crontab -

echo "Night shift armed:"
crontab -l | grep '# nightshift'
