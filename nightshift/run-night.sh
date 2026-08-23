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

# Only a line BEGINNING with the phrase counts — HELP.md's own instructions
# mention it mid-sentence, which must not trigger a halt.
stop_requested() { grep -q "^STATUS: STOP" "$DIR/HELP.md" 2>/dev/null; }

# --- single instance guard ---------------------------------------------------
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  log "another night shift is already running (pid $(cat "$LOCK")) — exiting."
  exit 0
fi
echo $$ > "$LOCK"

# --- shift start/end reports --------------------------------------------------
SHIFT_START="$(date '+%F %T')"
STARTED=0
REPORT_SENT=0
# Epoch of the last clock-out report. shift-watchdog.sh reads it at 07:05 to
# tell a quiet night apart from a shift that never ran.
STAMP="$DIR/.last-report"

# One body, every channel. Composing the report once is what keeps the email
# and the Telegram message saying the same thing; each transport handles its
# own formatting and failure modes, and neither can fail the shift.
announce() {
  "$DIR/email.sh"    "$1" "$2" >> "$NIGHT_LOG" 2>&1
  "$DIR/telegram.sh" "$1" "$2" >> "$NIGHT_LOG" 2>&1
}

send_report() {
  [ "$STARTED" = 1 ] || return 0
  [ "$REPORT_SENT" = 1 ] && return 0
  REPORT_SENT=1
  cd "$REPO" 2>/dev/null || return 0
  local commits prs
  commits=$(git log --since="$SHIFT_START" --pretty='- %s' 2>/dev/null | head -40)
  # One PR per line: gh's default table is columnar and wraps badly on a phone.
  prs=$(gh pr list --json number,title --jq '.[] | "- #\(.number) \(.title)"' 2>/dev/null | head -20)
  [ -n "$prs" ] || prs=$(gh pr list 2>/dev/null | head -20)
  announce "🌅 Night shift report — $(date '+%F %H:%M')" \
"Shift ran from $SHIFT_START to $(date '+%F %T').

Commits landed on main tonight:
${commits:-(none)}

Open PRs right now:
${prs:-(none)}

Latest nightlog:
$(tail -n 30 "$DIR/NIGHTLOG.md" 2>/dev/null)

$("$DIR/budget.sh" line 2>/dev/null)

Raw session logs: nightshift/logs/ on $(hostname)."
  date +%s > "$STAMP"
}

on_exit() { send_report; rm -f "$LOCK"; }
trap on_exit EXIT
trap 'exit 143' TERM INT   # ensure the EXIT trap (report + lock cleanup) runs on 07:00 kill

# --- monthly token budget ----------------------------------------------------
# The shift may spend at most MONTHLY_BUDGET_PCT of the account's monthly token
# allowance (see nightshift/budget.conf); budget.sh compares the two. Checked at
# clock-in and after every single role session, because one session can move the
# month's number by tens of millions of tokens.
#
# Returns 0 to keep working, 1 when the month's budget is spent — the caller
# clocks out. Standing down is a normal state, not a fault: the human is paged
# once per month, and every stood-down night still sends a message so that
# silence keeps meaning "something is broken".
budget_gate() {
  local phase="$1" once
  BUDGET_STATE=unknown
  BUDGET_MONTH="$(date +%Y-%m)"
  BUDGET_USED_PCT=0
  BUDGET_LINE="token budget: UNKNOWN — the guard itself failed to run."
  eval "$("$DIR/budget.sh" status 2>> "$NIGHT_LOG")" 2>> "$NIGHT_LOG" || true
  log "$BUDGET_LINE"

  once="$DIR/.budget-warned-$BUDGET_MONTH"
  if [ "$BUDGET_STATE" = warn ] && [ ! -e "$once" ]; then
    : > "$once"
    "$DIR/notify.sh" "Night shift at ${BUDGET_USED_PCT}% of its monthly token budget" \
      "$BUDGET_LINE — it stands down for the rest of the month once the budget is spent."
  fi

  [ "$BUDGET_STATE" = over ] || return 0

  log "MONTHLY TOKEN BUDGET SPENT ($phase) — standing down for the rest of $BUDGET_MONTH."
  once="$DIR/.budget-halted-$BUDGET_MONTH"
  if [ ! -e "$once" ]; then
    : > "$once"
    "$DIR/notify.sh" "Night shift stood down — monthly token budget spent" \
      "$BUDGET_LINE No roles run until $BUDGET_MONTH is over. Raise the numbers in nightshift/budget.conf to buy more."
    { echo
      echo "## $(date '+%F %T') — orchestrator"
      echo "Monthly token budget spent ($phase). $BUDGET_LINE"
      echo "The shift clocks in and straight back out without running roles until the"
      echo "calendar month rolls over. To buy more tokens for this month, raise"
      echo "MONTHLY_TOKEN_LIMIT or MONTHLY_BUDGET_PCT in nightshift/budget.conf."
      echo "Nothing is broken — no reply needed unless you want the shift back sooner."
    } >> "$DIR/HELP.md"
  fi

  announce "🛑 Night shift stood down — token budget spent ($(date +%F))" \
"$BUDGET_LINE

No role sessions ran ($phase). The shift resumes by itself when $BUDGET_MONTH ends.
To bring it back sooner, raise MONTHLY_TOKEN_LIMIT or MONTHLY_BUDGET_PCT in
nightshift/budget.conf on $(hostname)."
  REPORT_SENT=1        # this message replaces tonight's clock-out report
  date +%s > "$STAMP"  # a budgeted stand-down must not trip the 07:05 watchdog
  return 1
}

log "=== night shift clocking in (pid $$) ==="

# Token-burn odometer: backup refresh at clock-in (primary is the 07:15 cron,
# which counts the night that just finished). --force skips the lock check
# since we own the lock. Shares one idempotent script with the cron. Run before
# the budget gate so the gate and the odometer agree on the month's total.
"$DIR/update-ledger.sh" --force >> "$NIGHT_LOG" 2>&1 || log "WARN: ledger update failed."

# Nothing to announce as a clock-in if the month has no tokens left to spend.
budget_gate "at clock-in" || exit 0

announce "🌙 Night shift clocked in — $(date +%F)" \
"The night shift started at $SHIFT_START on $(hostname).

Backlog snapshot:
$(head -n 15 "$REPO/$(grep -m1 '^ACTIVE:' "$REPO/PROJECTS.md" 2>/dev/null | awk '{print $2}')/BACKLOG.md" 2>/dev/null || echo '(no active project yet — the Architect will invent one)')

$BUDGET_LINE

A progress report follows when the shift ends (~07:00)."
STARTED=1

ROLES=(architect engineer reviewer qa release)
LIMIT_PATTERN='usage limit|session limit|hit your.*limit|limit reached|rate.?limit|out of (tokens|credits|usage)|exceeded.*(quota|limit)'
AUTH_PATTERN='failed to authenticate|oauth.*(expired|revoked)|invalid authentication|invalid.*api.?key|error.*401'

while in_window; do
  if stop_requested; then
    log "STATUS: STOP found in HELP.md — halting for the night."
    exit 0
  fi

  cd "$REPO" || exit 1
  # The root checkout must always be on main; code work happens in .worktrees/.
  git checkout main >> "$NIGHT_LOG" 2>&1 || log "WARN: could not return root to main."
  git pull --rebase --autostash origin main >> "$NIGHT_LOG" 2>&1 || log "WARN: git pull failed; continuing with local state."
  git worktree prune >> "$NIGHT_LOG" 2>&1

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

    # The month's allowance is checked after every session, not once a cycle:
    # a single Engineer run can spend tens of millions of tokens.
    budget_gate "after the $role session" || exit 0
  done

  if [ "$ONCE" = 1 ]; then
    log "=== --once test cycle complete — clocking out. ==="
    exit 0
  fi
  sleep 60
done

log "=== 07:00 window closed — night shift clocking out. good morning. ==="
