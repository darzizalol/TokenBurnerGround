#!/usr/bin/env bash
# update-ledger.sh — regenerate the token-burn odometer and push it.
#
# Rebuilds nightshift/burn.svg + tokens.csv + the README embed from the local
# claude transcript store, then commits/pushes only if the total changed.
# Idempotent: safe to run any number of times.
#
# Primary trigger: cron at 07:15, just after the 07:00 stop, so the night that
# just finished is counted immediately (its transcripts are complete on disk).
# The runner also calls it at 22:00 clock-in with --force as a backup, in case
# the machine was asleep at 07:15.
#
# Usage:
#   update-ledger.sh            standalone: refuse if a shift is running
#   update-ledger.sh --force    skip the lock check (caller owns the lock)

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$DIR")"
LOCK="$DIR/.night.lock"
LOG="$DIR/logs/ledger.log"
mkdir -p "$DIR/logs"

# Cron delivers a bare environment; make git/gh/python reachable.
export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

# Standalone runs must not fight an active shift for the git index.
if [ "$FORCE" = 0 ] && [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  log "a night shift is active (pid $(cat "$LOCK")) — skipping standalone ledger update."
  exit 0
fi

cd "$REPO" || { log "cannot cd to repo"; exit 1; }

# Sync main before committing so the push is a fast-forward. (--force only
# skips the lock check, not this — the root checkout is always on main.)
git checkout main >> "$LOG" 2>&1 || log "WARN: cannot checkout main"
git pull --rebase --autostash origin main >> "$LOG" 2>&1 || log "WARN: git pull failed; using local state."

if ! python3 "$DIR/token-ledger.py" update >> "$LOG" 2>&1; then
  log "WARN: token-ledger.py failed."
  exit 1
fi

git add README.md nightshift/tokens.csv nightshift/burn.svg >> "$LOG" 2>&1
if git diff --cached --quiet; then
  log "no change in token burn — nothing to commit."
  exit 0
fi

total=$(grep -o 'aria-label="[0-9,]*' nightshift/burn.svg | head -1 | grep -o '[0-9,]*')
if git commit -m "chore: update token-burn odometer (${total:-?} tokens)" >> "$LOG" 2>&1 \
   && git push origin main >> "$LOG" 2>&1; then
  log "pushed updated odometer: $total"
else
  log "WARN: commit/push failed."
  exit 1
fi
