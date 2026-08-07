# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
All file paths in tasks are relative to this project's directory,
`projects/cinder/` — run the tests and the CLI from there.
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test in an isolated
worktree on a `<type>/<YYYYMMDD>-<slug>` branch (`feat`/`fix`/`chore`/`docs`/
`test` — see CLAUDE.md's worktree procedure), open a PR. Do not skip ahead to
a later task while an earlier one is unclaimed/open.

---

## 1. Standard library: `is_perfect_square` — perfect-square numeric predicate

Build: add `is_perfect_square(n)` to `cinder/builtins.py`, a numeric
builtin sitting right after `digit_sum` (already landed, and list/map
comprehensions have also landed and shifted the file's line numbers, so
search for `digit_sum` rather than trusting a specific line)
in the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`, currently
`cinder/builtins.py:1134-1165` before this cycle's other tasks land) —
it belongs there rather than next to `pow`/`gcd`/`lcm`/`factorial`
further down the file, sharing that cluster's "one property of a single
int" shape rather than the two-argument number-theoretic shape of the
farther-down group.

Model the arity/type-checking on `_is_prime`'s structure
(`cinder/builtins.py:1157-1159` before this cycle's other tasks land):
reuse `_require_arity("is_perfect_square", arguments, 1, line, column)`
and `_require_int("is_perfect_square", arguments[0], line, column)` (the
same helper `is_even`/`is_odd`/`is_divisible`/`is_prime`/`digit_sum`
already use, defined at `cinder/builtins.py:157-162` — raises
`CinderRuntimeError` with `f"{name}() requires an int, got
{type_name(value)}"` and rejects `bool` since `bool` is a Python `int`
subclass, so no separate bool-exclusion check is needed here). For the
computation: negative integers are never perfect squares, so return
`False` immediately when `value < 0` (matching `is_prime`'s own
`if value < 2: return False` early-out shape); otherwise use Python's
`math.isqrt(value)` (already imported as `math` at the top of
`builtins.py` — used by `factorial`/`sqrt`/etc., check the existing
`import math` before adding a duplicate) rather than
`math.sqrt(value) ** 0.5`-style floating point, since `math.isqrt`
returns an exact integer floor square root with no rounding-error risk
for large values: `root = math.isqrt(value)` then `return root * root
== value`.

Acceptance criteria:
- `is_perfect_square(0);` is `true` — `0 * 0 == 0`.
- `is_perfect_square(1);` is `true`.
- `is_perfect_square(4);` is `true`.
- `is_perfect_square(16);` is `true`.
- `is_perfect_square(15);` is `false` — between two perfect squares.
- `is_perfect_square(2);` is `false`.
- `is_perfect_square(-4);` is `false` — negative input, never a perfect
  square despite `4` itself being one; no domain error, just `false`,
  matching how `is_prime` returns `false` rather than erroring on
  out-of-domain input like negative numbers or `0`/`1`.
- `is_perfect_square(999999999999999999999999 * 999999999999999999999999);`
  (a large bignum perfect square, well past float precision) is `true`
  — confirms `math.isqrt` is used instead of a `** 0.5` float path that
  would lose precision at this magnitude.
- `is_perfect_square(3.0);` (float, even though numerically whole)
  raises `CinderRuntimeError` matching `"is_perfect_square() requires
  an int, got float"` — no implicit float-to-int coercion, matching
  `is_even`/`is_odd`/`is_prime`/`digit_sum`.
- `is_perfect_square(true);` (bool) raises `CinderRuntimeError`
  matching `"is_perfect_square() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_sum`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_perfect_square` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 2. Standard library: `is_armstrong` — Armstrong (narcissistic) number predicate

Build: add `is_armstrong(n)` to `cinder/builtins.py`, one more member of
the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`/`is_perfect_square`, task 1
above — by the time this task is claimed those will have landed and
shifted the file's line numbers, so search for `is_perfect_square`
rather than trusting a specific line) — an Armstrong number (also
called narcissistic) is one that equals the sum of its own decimal
digits, each raised to the power of the total digit count, e.g.
`153 = 1^3 + 5^3 + 3^3`. It's a natural sibling to land after
`digit_sum`/`is_perfect_square` since it does its own digit-by-digit
walk with a digit-count-dependent exponent rather than reusing
`digit_sum`'s plain sum.

Model the arity/type-checking on `_is_prime`'s structure
(`cinder/builtins.py:1167-1169` before this cycle's other tasks land):
reuse `_require_arity("is_armstrong", arguments, 1, line, column)` and
`_require_int("is_armstrong", arguments[0], line, column)` (the same
helper `is_even`/`is_odd`/`is_divisible`/`is_prime`/`digit_sum`/
`is_perfect_square` already use, defined at `cinder/builtins.py:157-162`
— raises `CinderRuntimeError` with `f"{name}() requires an int, got
{type_name(value)}"` and rejects `bool` since `bool` is a Python `int`
subclass, so no separate bool-exclusion check is needed here). For the
computation: negative integers are never Armstrong numbers (matching
`is_perfect_square`'s own negative-input-is-just-`false` convention, no
domain error), so return `False` immediately when `value < 0`;
otherwise convert to a digit string with `digits = str(value)`, compute
`power = len(digits)`, and return `sum(int(digit) ** power for digit in
digits) == value`. Single-digit numbers (`0`-`9`) are trivially
Armstrong numbers under this definition (`power == 1`, so the sum is
just the digit itself) — do not special-case them away.

Acceptance criteria:
- `is_armstrong(0);` is `true` — `0^1 == 0`.
- `is_armstrong(5);` is `true` — single digits are trivially Armstrong
  (`5^1 == 5`).
- `is_armstrong(9);` is `true`.
- `is_armstrong(153);` is `true` — `1^3 + 5^3 + 3^3 == 153`.
- `is_armstrong(9474);` is `true` — `9^4 + 4^4 + 7^4 + 4^4 == 9474`.
- `is_armstrong(10);` is `false` — `1^2 + 0^2 == 1 != 10`.
- `is_armstrong(123);` is `false`.
- `is_armstrong(-153);` is `false` — negative input, never Armstrong
  despite `153` itself being one; no domain error, just `false`,
  matching `is_perfect_square`'s negative-input convention.
- `is_armstrong(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"is_armstrong() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of the
  cluster.
- `is_armstrong(true);` (bool) raises `CinderRuntimeError` matching
  `"is_armstrong() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_perfect_square`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_armstrong` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Standard library: `is_leap_year` — Gregorian leap-year predicate

Build: add `is_leap_year(year)` to `cinder/builtins.py`, one more member
of the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`/`is_perfect_square`/`is_armstrong`,
tasks 1-2 above — by the time this task is claimed those will
have landed and shifted the file's line numbers, so search for
`is_armstrong` rather than trusting a specific line) — the Gregorian
calendar rule: a year is a leap year when divisible by 4, except
century years (divisible by 100), which are leap years only when also
divisible by 400 (so `2000` is a leap year, `1900` is not).

Model the arity/type-checking on `_is_prime`'s structure
(`cinder/builtins.py:1163-1165` before this cycle's other tasks land):
reuse `_require_arity("is_leap_year", arguments, 1, line, column)` and
`_require_int("is_leap_year", arguments[0], line, column)` (the same
helper the rest of the cluster already uses, defined at
`cinder/builtins.py:157-162` — raises `CinderRuntimeError` with
`f"{name}() requires an int, got {type_name(value)}"` and rejects
`bool` since `bool` is a Python `int` subclass, so no separate
bool-exclusion check is needed here). For the computation: the rule is
purely arithmetic on the magnitude, and it is well-defined (if
historically anachronistic) for zero and negative years too — do not
special-case sign away or raise a domain error, matching
`is_perfect_square`/`is_armstrong`'s "no domain errors, just an
arithmetic answer" convention: `return value % 4 == 0 and (value % 100
!= 0 or value % 400 == 0)`.

Acceptance criteria:
- `is_leap_year(2000);` is `true` — divisible by 400.
- `is_leap_year(1900);` is `false` — divisible by 100 but not 400.
- `is_leap_year(2024);` is `true` — divisible by 4, not by 100.
- `is_leap_year(2023);` is `false` — not divisible by 4.
- `is_leap_year(0);` is `true` — `0 % 4 == 0` and `0 % 400 == 0`, no
  domain error despite year `0` not existing on the actual Gregorian
  calendar; this builtin is pure arithmetic, not a calendar lookup.
- `is_leap_year(-2000);` is `true`, `is_leap_year(-1900);` is `false` —
  negative years follow the same arithmetic rule, no domain error,
  matching `is_perfect_square`/`is_armstrong`'s negative-input
  convention of "just compute it" rather than rejecting.
- `is_leap_year(4.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"is_leap_year() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of
  the cluster.
- `is_leap_year(true);` (bool) raises `CinderRuntimeError` matching
  `"is_leap_year() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_armstrong`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_leap_year` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `reverse_int` — reverse an integer's decimal digits

Build: add `reverse_int(n)` to `cinder/builtins.py`, sitting next to
`digit_sum` (already landed — by the time this task is claimed tasks 1-3
above will also have landed and shifted the file's line numbers, so
search for `digit_sum` rather than trusting a specific line) in the
integer-property cluster — unlike the predicates around it
(`is_leap_year`/`is_perfect_square`/`is_armstrong`), this one returns a
number rather than a boolean, the same shape `digit_sum` itself already
has, so it belongs immediately beside it rather than in the boolean
cluster proper.

Model the arity/type-checking on `digit_sum`'s own structure (once task
1 lands): reuse `_require_arity("reverse_int", arguments, 1, line,
column)` and `_require_int("reverse_int", arguments[0], line, column)`
(the same helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162`). For the computation, mirror `digit_sum`'s
sign handling exactly (normalize away the sign, reverse the magnitude,
then reapply the sign — a reversed negative number is still negative,
unlike `digit_sum` where the sign disappears into a plain positive
sum): `sign = -1 if value < 0 else 1`, `reversed_digits =
str(abs(value))[::-1]`, then `return sign * int(reversed_digits)`.
Leading zeros in the original number's reversed form simply disappear
via `int(...)`, matching how no integer literal can carry leading
zeros in the first place (e.g. `reverse_int(120)` produces the digit
string `"021"`, and `int("021")` is `21` — no special-casing needed,
Python's own `int()` conversion already drops the leading zero).

Acceptance criteria:
- `reverse_int(0);` is `0`.
- `reverse_int(5);` is `5`.
- `reverse_int(123);` is `321`.
- `reverse_int(-123);` is `-321` — sign is preserved, unlike
  `digit_sum` where it's discarded.
- `reverse_int(120);` is `21` — trailing zero in the original becomes a
  disappearing leading zero in the reversed form.
- `reverse_int(100);` is `1`.
- `reverse_int(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"reverse_int() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of
  the cluster.
- `reverse_int(true);` (bool) raises `CinderRuntimeError` matching
  `"reverse_int() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_sum`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `reverse_int` added near `digit_sum`, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `is_perfect_number` — sum-of-proper-divisors predicate

Build: add `is_perfect_number(n)` to `cinder/builtins.py`, one more member
of the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`/`is_perfect_square`/`is_armstrong`/
`is_leap_year`, tasks 1-4 above — by the time this task is claimed those
will have landed and shifted the file's line numbers, so search for
`is_leap_year` rather than trusting a specific line) — a perfect number
equals the sum of its own proper divisors (divisors excluding itself),
e.g. `6 = 1 + 2 + 3` and `28 = 1 + 2 + 4 + 7 + 14`. A natural sibling to
land after `is_armstrong`/`is_leap_year` since it shares their "classic
number-theory property, no domain error on out-of-range input" shape.

Model the arity/type-checking on `_is_prime`'s structure (search for
`def _is_prime` — the file's line numbers shift as earlier tasks this
cycle land): reuse `_require_arity("is_perfect_number", arguments, 1,
line, column)` and `_require_int("is_perfect_number", arguments[0],
line, column)` (the same helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162` — raises `CinderRuntimeError` with
`f"{name}() requires an int, got {type_name(value)}"` and rejects `bool`
since `bool` is a Python `int` subclass, so no separate bool-exclusion
check is needed here). For the computation: matching `is_prime`'s own
`if value < 2: return False` early-out (no proper divisor can sum to a
value below 2, and this also disposes of 0/negative input without a
domain error, matching `is_perfect_square`/`is_armstrong`/
`is_leap_year`'s "just answer, don't reject" convention for out-of-range
input), then sum proper divisors by trial division up to
`math.isqrt(value)` (the same bound `is_prime` already uses, and
`math` is already imported) pairing each divisor `d` that divides
evenly with its complement `value // d`, taking care not to double-count
a divisor equal to its own complement (i.e. when `d * d == value`) or to
include `value` itself: `total = 1` (1 is always a proper divisor for
`value > 1`), then for `d` from `2` to `math.isqrt(value)` inclusive,
whenever `value % d == 0`, add `d` to `total`, and if the complement
`value // d != d` and `value // d != value`, add it too. Return
`total == value`.

Acceptance criteria:
- `is_perfect_number(6);` is `true` — `1 + 2 + 3 == 6`.
- `is_perfect_number(28);` is `true` — `1 + 2 + 4 + 7 + 14 == 28`.
- `is_perfect_number(496);` is `true` — third perfect number, confirms
  the trial-division approach scales past the trivial cases.
- `is_perfect_number(12);` is `false` — `1 + 2 + 3 + 4 + 6 == 16 != 12`
  (abundant, not perfect).
- `is_perfect_number(1);` is `false` — no proper divisors other than
  none at all; `total` would be `1` from the `value > 1` guard not
  applying, but the early `value < 2` out-out returns `false` directly.
- `is_perfect_number(0);` is `false` — falls into the `value < 2`
  early-out, no domain error.
- `is_perfect_number(-6);` is `false` — negative input, never perfect
  despite `6` itself being one; no domain error, just `false`, matching
  `is_perfect_square`/`is_armstrong`/`is_leap_year`'s negative-input
  convention.
- `is_perfect_number(3.0);` (float, even though numerically whole)
  raises `CinderRuntimeError` matching `"is_perfect_number() requires
  an int, got float"` — no implicit float-to-int coercion, matching the
  rest of the cluster.
- `is_perfect_number(true);` (bool) raises `CinderRuntimeError` matching
  `"is_perfect_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_leap_year`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_perfect_number` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
