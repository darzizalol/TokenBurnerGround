#!/usr/bin/env bash
# run-night.sh — the Night Shift orchestrator.
# Started by cron at 22:00. Runs role sessions in a loop until 07:00.
# Each role is a headless `claude -p` session working in the repo root.

set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$DIR")"
LOGS="$DIR/logs"
LOCK="$DIR/.night.lock"
mkdir -p "$LOGS"

# Cron provides a bare environment; make sure claude and gh are reachable.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

NIGHT_LOG="$LOGS/night-$(date +%Y%m%d).log"
log() { echo "[$(date '+%F %T')] $*" >> "$NIGHT_LOG"; }

# 22:00 <= now < 07:00
in_window() {
  local h
  h=$(date +%-H)
  [ "$h" -ge 22 ] || [ "$h" -lt 7 ]
}

stop_requested() { grep -q "STATUS: STOP" "$DIR/HELP.md" 2>/dev/null; }

# --- single instance guard ---------------------------------------------------
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  log "another night shift is already running (pid $(cat "$LOCK")) — exiting."
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "=== night shift clocking in (pid $$) ==="

ROLES=(architect engineer reviewer qa release)
LIMIT_PATTERN='usage limit|limit reached|rate.?limit|out of (tokens|credits|usage)|exceeded.*(quota|limit)'
AUTH_PATTERN='failed to authenticate|oauth.*(expired|revoked)|invalid authentication|invalid.*api.?key|error.*401'

while in_window; do
  if stop_requested; then
    log "STATUS: STOP found in HELP.md — halting for the night."
    exit 0
  fi

  cd "$REPO" || exit 1
  git pull --rebase origin main >> "$NIGHT_LOG" 2>&1 || log "WARN: git pull failed; continuing with local state."

  for role in "${ROLES[@]}"; do
    in_window || break
    stop_requested && break

    SESSION_LOG="$LOGS/$(date +%Y%m%d-%H%M%S)-$role.log"
    log "session start: $role"
    timeout --kill-after=60 3600 claude -p "$(cat "$DIR/prompts/$role.md")" \
      --dangerously-skip-permissions > "$SESSION_LOG" 2>&1
    rc=$?
    log "session end: $role (exit $rc, log $(basename "$SESSION_LOG"))"

    # Auth watchdog: an expired/invalid login can't be fixed by an agent.
    # Page the human and end the shift instead of failing all night long.
    if grep -qiE "$AUTH_PATTERN" "$SESSION_LOG"; then
      log "AUTH FAILURE detected — paging the human and clocking out."
      "$DIR/notify.sh" "Night shift blocked: Claude auth" \
        "The claude CLI login is expired or invalid. Open a terminal, run 'claude', and log in. The shift resumes tomorrow at 22:00."
      { echo
        echo "## $(date '+%F %T') — orchestrator"
        echo "Claude CLI authentication failed during the $role session (see logs/$(basename "$SESSION_LOG"))."
        echo "Human: run 'claude' in a terminal and re-login. No agent can fix this."
      } >> "$DIR/HELP.md"
      exit 1
    fi

    # Token watchdog: on a usage limit, nap in 30-min slices until the
    # window resets or the shift ends. Limits are expected, not emergencies.
    if grep -qiE "$LIMIT_PATTERN" "$SESSION_LOG"; then
      log "usage limit detected — napping until tokens return."
      while in_window && ! stop_requested; do
        sleep 1800
        probe=$(claude -p "Reply with exactly: OK" --dangerously-skip-permissions 2>&1)
        if echo "$probe" | grep -q "OK" && ! echo "$probe" | grep -qiE "$LIMIT_PATTERN"; then
          log "tokens are back — resuming."
          break
        fi
        log "still limited — napping another 30 minutes."
      done
    fi
  done

  sleep 60
done

log "=== 07:00 window closed — night shift clocking out. good morning. ==="
