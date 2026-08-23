#!/usr/bin/env bash
# budget.sh — the night shift's monthly token allowance guard.
#
# Policy lives in budget.conf; the token count comes from token-ledger.py,
# which reads the same transcripts the burn odometer is built from. This
# script is the only place the two are compared.
#
# Usage:
#   budget.sh status    print eval-able KEY=VALUE lines (see below)
#   budget.sh check     exit 0 while the month still has budget, 1 when spent
#   budget.sh line      print one human-readable summary line
#
# status keys: BUDGET_MONTH SPENT LIMIT PCT ALLOWED REMAINING USED_PCT STATE
#   STATE is ok | warn | over | unknown
#
# Fail-open by design: if the ledger cannot be read the guard reports
# `unknown` and lets the shift run. A broken counter must not cost a night's
# work — it is loud in the log instead.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$DIR/budget.conf"

MONTHLY_TOKEN_LIMIT=0
MONTHLY_BUDGET_PCT=35
WARN_PCT=80
# shellcheck disable=SC1090
[ -f "$CONF" ] && . "$CONF"

# The month a shift starting tonight belongs to: before noon we are in the
# small hours of a night that started yesterday, so the month is yesterday's.
if [ "$(date +%-H)" -lt 12 ]; then
  MONTH="$(date -d 'yesterday' +%Y-%m)"
else
  MONTH="$(date +%Y-%m)"
fi

SPENT="$(python3 "$DIR/token-ledger.py" month-total "$MONTH" 2>/dev/null)"

# Every number that reaches the arithmetic below is validated first: a typo in
# budget.conf must degrade to `unknown`, never to a silently wrong ceiling.
digits() { case "${1:-}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }
digits "$SPENT" || SPENT=""
digits "$MONTHLY_TOKEN_LIMIT" || MONTHLY_TOKEN_LIMIT=0
digits "$MONTHLY_BUDGET_PCT" || MONTHLY_BUDGET_PCT=0
digits "$WARN_PCT" || WARN_PCT=100

if [ -z "$SPENT" ] || [ "$MONTHLY_TOKEN_LIMIT" -le 0 ] || [ "$MONTHLY_BUDGET_PCT" -le 0 ]; then
  STATE=unknown; SPENT=0; ALLOWED=0; REMAINING=0; USED_PCT=0
else
  ALLOWED=$(( MONTHLY_TOKEN_LIMIT / 100 * MONTHLY_BUDGET_PCT ))
  REMAINING=$(( ALLOWED - SPENT ))
  [ "$REMAINING" -lt 0 ] && REMAINING=0
  USED_PCT=$(( SPENT * 100 / (ALLOWED > 0 ? ALLOWED : 1) ))
  if   [ "$SPENT" -ge "$ALLOWED" ];   then STATE=over
  elif [ "$USED_PCT" -ge "$WARN_PCT" ]; then STATE=warn
  else                                     STATE=ok
  fi
fi

# 1234567890 -> 1,234,567,890 without relying on the locale being set.
commas() { echo "$1" | sed -e :a -e 's/\(.*[0-9]\)\([0-9]\{3\}\)/\1,\2/;ta'; }

line() {
  if [ "$STATE" = unknown ]; then
    echo "token budget $MONTH: UNKNOWN — the ledger or budget.conf could not be read; letting the shift run."
  else
    echo "token budget $MONTH: $(commas "$SPENT") of $(commas "$ALLOWED") tokens used (${USED_PCT}% of the ${MONTHLY_BUDGET_PCT}% share of $(commas "$MONTHLY_TOKEN_LIMIT")), $(commas "$REMAINING") left [$STATE]"
  fi
}

case "${1:-status}" in
  status)
    echo "BUDGET_MONTH=$MONTH"
    echo "BUDGET_SPENT=$SPENT"
    echo "BUDGET_LIMIT=$MONTHLY_TOKEN_LIMIT"
    echo "BUDGET_PCT=$MONTHLY_BUDGET_PCT"
    echo "BUDGET_ALLOWED=$ALLOWED"
    echo "BUDGET_REMAINING=$REMAINING"
    echo "BUDGET_USED_PCT=$USED_PCT"
    echo "BUDGET_STATE=$STATE"
    echo "BUDGET_WARN_PCT=$WARN_PCT"
    # Emitted last and single-quoted so one `eval` gives the caller both the
    # numbers and the sentence it should log or send.
    echo "BUDGET_LINE='$(line | sed "s/'/'\\\\''/g")'"
    ;;
  check) [ "$STATE" = over ] && exit 1 || exit 0 ;;
  line)  line ;;
  *)     sed -n '2,20p' "$0"; exit 1 ;;
esac
