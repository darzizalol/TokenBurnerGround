#!/usr/bin/env bash
# run-night.sh — the Night Shift orchestrator.
# Started by cron at 22:00. Runs role sessions in a loop until 07:00.
# Two vendors, one constitution: Claude (claude CLI) architects, engineers,
# and releases; Gemini (gemini CLI) reviews and QAs. Cross-vendor review is
# deliberate — the authoring model never certifies its own work.

set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$DIR")"
LOGS="$DIR/logs"
LOCK="$DIR/.night.lock"
mkdir -p "$LOGS"

# Cron provides a bare environment; make sure claude, gemini and gh are reachable.
export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"

# --once: test mode — ignore the 22:00-07:00 window and run exactly one cycle.
ONCE=0
[ "${1:-}" = "--once" ] && ONCE=1

NIGHT_LOG="$LOGS/night-$(date +%Y%m%d).log"
log() { echo "[$(date '+%F %T')] $*" >> "$NIGHT_LOG"; }

# 22:00 <= now < 07:00 (always true in --once test mode)
in_window() {
  local h
  [ "$ONCE" = 1 ] && return 0
  h=$(date +%-H)
  [ "$h" -ge 22 ] || [ "$h" -lt 7 ]
}

stop_requested() { grep -q "^STATUS: STOP" "$DIR/HELP.md" 2>/dev/null; }

# --- single instance guard ---------------------------------------------------
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  log "another night shift is already running (pid $(cat "$LOCK")) — exiting."
  exit 0
fi
echo $$ > "$LOCK"

# --- shift start/end emails ---------------------------------------------------
SHIFT_START="$(date '+%F %T')"
STARTED=0
REPORT_SENT=0

send_report() {
  [ "$STARTED" = 1 ] || return 0
  [ "$REPORT_SENT" = 1 ] && return 0
  REPORT_SENT=1
  cd "$REPO" 2>/dev/null || return 0
  local commits prs
  commits=$(git log --since="$SHIFT_START" --pretty='- %s' 2>/dev/null | head -40)
  prs=$(gh pr list 2>/dev/null | head -20)
  "$DIR/email.sh" "🌅 Night shift report — $(date '+%F %H:%M')" \
"Shift ran from $SHIFT_START to $(date '+%F %T').

Commits landed on main tonight:
${commits:-(none)}

Open PRs right now:
${prs:-(none)}

Latest nightlog:
$(tail -n 30 "$DIR/NIGHTLOG.md" 2>/dev/null)

Raw session logs: nightshift/logs/ on $(hostname)." >> "$NIGHT_LOG" 2>&1
}

on_exit() { send_report; rm -f "$LOCK"; }
trap on_exit EXIT
trap 'exit 143' TERM INT   # ensure the EXIT trap (report + lock cleanup) runs on 07:00 kill

log "=== night shift clocking in (pid $$) ==="
"$DIR/email.sh" "🌙 Night shift clocked in — $(date +%F)" \
"The night shift started at $SHIFT_START on $(hostname).

Backlog snapshot:
$(head -n 15 "$REPO/BACKLOG.md" 2>/dev/null || echo '(no backlog yet — Night One: the Architect will invent the project)')

A progress report lands in this inbox when the shift ends (~07:00)." >> "$NIGHT_LOG" 2>&1
STARTED=1

# --- the crew -----------------------------------------------------------------
ROLES=(architect engineer reviewer qa release)
agent_for_role() { case "$1" in reviewer|qa) echo "gemini" ;; *) echo "claude" ;; esac; }

CLAUDE_LIMIT_PATTERN='usage limit|limit reached|rate.?limit|out of (tokens|credits|usage)|exceeded.*(quota|limit)'
CLAUDE_AUTH_PATTERN='failed to authenticate|oauth.*(expired|revoked)|invalid authentication|invalid.*api.?key|error.*401'
GEMINI_LIMIT_PATTERN='429|quota.?exceeded|resource.?exhausted|rate.?limit'
GEMINI_AUTH_PATTERN='not (logged|signed) in|please (log|sign) in|set an auth method|authenticationerror|error authenticating|authorization is required|credential.*(expired|invalid|not found)|invalid.*credential|login required|error.*40[13]'
GEMINI_DOWN=0   # set on Gemini auth failure; its roles are skipped for the rest of the night

while in_window; do
  if stop_requested; then
    log "STATUS: STOP found in HELP.md — halting for the night."
    exit 0
  fi

  cd "$REPO" || exit 1
  git pull --rebase --autostash origin main >> "$NIGHT_LOG" 2>&1 || log "WARN: git pull failed; continuing with local state."

  for role in "${ROLES[@]}"; do
    in_window || break
    stop_requested && break

    agent=$(agent_for_role "$role")

    if [ "$agent" = "gemini" ] && [ "$GEMINI_DOWN" = 1 ]; then
      log "skip: $role — gemini marked down for tonight."
      continue
    fi

    SESSION_LOG="$LOGS/$(date +%Y%m%d-%H%M%S)-$role.log"
    log "session start: $role ($agent)"
    case "$agent" in
      claude)
        timeout --kill-after=60 3600 claude -p "$(cat "$DIR/prompts/$role.md")" \
          --dangerously-skip-permissions > "$SESSION_LOG" 2>&1
        ;;
      gemini)
        timeout --kill-after=60 3600 gemini --yolo -p "$(cat "$DIR/prompts/$role.md")" \
          > "$SESSION_LOG" 2>&1
        ;;
    esac
    rc=$?
    log "session end: $role ($agent, exit $rc, log $(basename "$SESSION_LOG"))"

    # --- Gemini failures: skip, never fall back to the authoring model --------
    if [ "$agent" = "gemini" ] && [ "$rc" -ne 0 ]; then
      if grep -qiE "$GEMINI_AUTH_PATTERN" "$SESSION_LOG"; then
        GEMINI_DOWN=1
        log "gemini AUTH FAILURE — paging human; Reviewer/QA skipped for the rest of tonight."
        "$DIR/notify.sh" "Night shift: Gemini auth broken" \
          "The gemini CLI login failed, so Reviewer/QA sessions are skipped tonight and PRs wait. Run 'gemini' in a terminal and log in with Google."
        { echo
          echo "## $(date '+%F %T') — orchestrator"
          echo "Gemini CLI auth failed during the $role session (see logs/$(basename "$SESSION_LOG"))."
          echo "Reviewer/QA skipped for the night per constitution. Human: run 'gemini' and re-login."
        } >> "$DIR/HELP.md"
      elif grep -qiE "$GEMINI_LIMIT_PATTERN" "$SESSION_LOG"; then
        log "gemini quota limit — $role skipped this cycle; PRs wait for its verdict."
      else
        log "gemini session failed (exit $rc) — $role skipped this cycle."
      fi
      continue
    fi

    # --- Claude auth watchdog: unfixable by agents — page human, clock out ----
    if [ "$agent" = "claude" ] && grep -qiE "$CLAUDE_AUTH_PATTERN" "$SESSION_LOG"; then
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

    # --- Claude token watchdog: nap in 30-min slices until tokens return ------
    if [ "$agent" = "claude" ] && grep -qiE "$CLAUDE_LIMIT_PATTERN" "$SESSION_LOG"; then
      log "usage limit detected — napping until tokens return."
      while in_window && ! stop_requested; do
        sleep 1800
        probe=$(claude -p "Reply with exactly: OK" --dangerously-skip-permissions 2>&1)
        if echo "$probe" | grep -q "OK" && ! echo "$probe" | grep -qiE "$CLAUDE_LIMIT_PATTERN"; then
          log "tokens are back — resuming."
          break
        fi
        log "still limited — napping another 30 minutes."
      done
    fi
  done

  if [ "$ONCE" = 1 ]; then
    log "=== --once test cycle complete — clocking out. ==="
    exit 0
  fi
  sleep 60
done

log "=== 07:00 window closed — night shift clocking out. good morning. ==="
