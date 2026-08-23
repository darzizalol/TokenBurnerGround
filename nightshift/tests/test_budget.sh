#!/usr/bin/env bash
# Tests for nightshift/budget.sh — the monthly token-budget guard.
#
# budget.sh always shells out to token-ledger.py for the month's spend, so
# each test runs a copy of budget.sh in a scratch directory alongside a stub
# token-ledger.py that just echoes a fixed token count. That keeps every
# case pinned to a known SPENT value without touching real transcripts.
#
# Run: bash nightshift/tests/test_budget.sh

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NIGHTSHIFT="$(dirname "$HERE")"

fail=0
pass=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "FAIL: $desc"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

# Builds a scratch nightshift dir: a copy of the real budget.sh next to a
# stub token-ledger.py that ignores its arguments and prints $1.
make_sandbox() {
  local spent="$1" sandbox
  sandbox="$(mktemp -d)"
  cp "$NIGHTSHIFT/budget.sh" "$sandbox/budget.sh"
  cat > "$sandbox/token-ledger.py" <<EOF
#!/usr/bin/env python3
print($spent)
EOF
  chmod +x "$sandbox/budget.sh" "$sandbox/token-ledger.py"
  echo "$sandbox"
}

write_conf() {
  local sandbox="$1" limit="$2" pct="$3" warn="$4"
  cat > "$sandbox/budget.conf" <<EOF
MONTHLY_TOKEN_LIMIT=$limit
MONTHLY_BUDGET_PCT=$pct
WARN_PCT=$warn
EOF
}

# --- ok: well under the budget ----------------------------------------------
sandbox="$(make_sandbox 1000)"
write_conf "$sandbox" 1000000 35 80   # allowed = 350,000
out="$(bash "$sandbox/budget.sh" status)"
eval "$out"
assert_eq "ok: state" "ok" "$BUDGET_STATE"
assert_eq "ok: allowed" "350000" "$BUDGET_ALLOWED"
assert_eq "ok: remaining" "349000" "$BUDGET_REMAINING"
bash "$sandbox/budget.sh" check
assert_eq "ok: check exit code" "0" "$?"
rm -rf "$sandbox"

# --- warn: over WARN_PCT of the allowance but not yet spent -----------------
sandbox="$(make_sandbox 300000)"
write_conf "$sandbox" 1000000 35 80   # allowed = 350,000; 300,000/350,000 = 85%
out="$(bash "$sandbox/budget.sh" status)"
eval "$out"
assert_eq "warn: state" "warn" "$BUDGET_STATE"
bash "$sandbox/budget.sh" check
assert_eq "warn: check still exits 0" "0" "$?"
rm -rf "$sandbox"

# --- over: budget fully spent ------------------------------------------------
sandbox="$(make_sandbox 400000)"
write_conf "$sandbox" 1000000 35 80   # allowed = 350,000; spent exceeds it
out="$(bash "$sandbox/budget.sh" status)"
eval "$out"
assert_eq "over: state" "over" "$BUDGET_STATE"
assert_eq "over: remaining floors at zero" "0" "$BUDGET_REMAINING"
bash "$sandbox/budget.sh" check
assert_eq "over: check exit code" "1" "$?"
line="$(bash "$sandbox/budget.sh" line)"
case "$line" in
  *"[over]"*) pass=$((pass + 1)) ;;
  *) fail=$((fail + 1)); echo "FAIL: over: line reports [over]"; echo "  actual: $line" ;;
esac
rm -rf "$sandbox"

# --- unknown: missing/malformed budget.conf degrades safely, never a wrong ceiling
sandbox="$(make_sandbox 999999999)"
write_conf "$sandbox" "not-a-number" 35 80
out="$(bash "$sandbox/budget.sh" status)"
eval "$out"
assert_eq "unknown: bad limit -> state" "unknown" "$BUDGET_STATE"
bash "$sandbox/budget.sh" check
assert_eq "unknown: check fails open (exit 0)" "0" "$?"
rm -rf "$sandbox"

# --- unknown: ledger itself fails to produce a number -----------------------
sandbox="$(mktemp -d)"
cp "$NIGHTSHIFT/budget.sh" "$sandbox/budget.sh"
cat > "$sandbox/token-ledger.py" <<'EOF'
#!/usr/bin/env python3
import sys
sys.exit(1)
EOF
chmod +x "$sandbox/budget.sh" "$sandbox/token-ledger.py"
write_conf "$sandbox" 1000000 35 80
out="$(bash "$sandbox/budget.sh" status)"
eval "$out"
assert_eq "unknown: ledger failure -> state" "unknown" "$BUDGET_STATE"
bash "$sandbox/budget.sh" check
assert_eq "unknown: ledger failure still fails open" "0" "$?"
rm -rf "$sandbox"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
