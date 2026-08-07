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

## 1. Standard library: `reverse_int` — reverse an integer's decimal digits [claimed 2026-08-07T19:57:28Z]

Build: add `reverse_int(n)` to `cinder/builtins.py`, sitting next to
`digit_sum` (already landed — by the time this task is claimed task 1
above will also have landed and shifted the file's line numbers, so
search for `digit_sum` rather than trusting a specific line) in the
integer-property cluster — unlike the predicates around it
(`is_leap_year`/`is_perfect_square`/`is_armstrong`), this one returns a
number rather than a boolean, the same shape `digit_sum` itself already
has, so it belongs immediately beside it rather than in the boolean
cluster proper.

Model the arity/type-checking on `digit_sum`'s own structure: reuse
`_require_arity("reverse_int", arguments, 1, line,
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

## 2. Standard library: `is_perfect_number` — sum-of-proper-divisors predicate

Build: add `is_perfect_number(n)` to `cinder/builtins.py`, one more member
of the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`/`is_perfect_square`/`is_armstrong`/
`is_leap_year`, already landed, plus task 1 above — by the time this task
is claimed those will have landed and shifted the file's line numbers, so
search for `is_leap_year` rather than trusting a specific line) — a perfect number
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

## 3. Standard library: `is_abundant` — sum-of-proper-divisors-exceeds-n predicate

Build: add `is_abundant(n)` to `cinder/builtins.py`, one more member of
the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`/`is_perfect_square`/`is_armstrong`/
`is_leap_year`/`reverse_int`/`is_perfect_number`, tasks 1-2 above — by the
time this task is claimed those will have landed and shifted the file's
line numbers, so search for `is_perfect_number` rather than trusting a
specific line) — an abundant number's proper divisors (divisors
excluding itself) sum to *more* than the number itself, e.g. `12`:
`1 + 2 + 3 + 4 + 6 = 16 > 12`. It's the natural next member after
`is_perfect_number` since perfect/abundant/deficient (task 5 below) are
the three classical divisor-sum classifications, and every positive
integer falls into exactly one of them.

Model the arity/type-checking on `_is_perfect_number`'s structure
(search for `def _is_perfect_number`): reuse
`_require_arity("is_abundant", arguments, 1, line, column)` and
`_require_int("is_abundant", arguments[0], line, column)` (the same
helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162`). For the computation, reuse the same
`math.isqrt`-bounded trial-division divisor sum `_is_perfect_number`
already computes, but do **not** factor it into a shared helper as part
of this task — keep the sum inline here too, matching how `is_prime` and
`is_perfect_number` each already duplicate their own trial-division loop
rather than sharing one; a refactor is out of scope for a single-builtin
task. Unlike `is_perfect_number`'s `if value < 2: return False`
early-out, `value == 1` is a real case here (its proper-divisor sum is
`0`, which is *not* greater than `1`, so `is_abundant(1)` must be
`false` without an early-out masking it): `if value < 1: return False`
(no domain error for non-positive input, matching
`is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`'s
"just answer" convention), then `total = 1 if value > 1 else 0`, then
for `d` from `2` to `math.isqrt(value)` inclusive, whenever `value % d
== 0`, add `d` to `total`, and if the complement `value // d != d`, add
it too (no need to also exclude `value` itself here, unlike
`is_perfect_number` — the loop only ever reaches divisors up to
`math.isqrt(value)` and their complements, never `value` itself, since
`d` starts at `2`). Return `total > value`.

Acceptance criteria:
- `is_abundant(12);` is `true` — `1 + 2 + 3 + 4 + 6 == 16 > 12`.
- `is_abundant(18);` is `true` — `1 + 2 + 3 + 6 + 9 == 21 > 18`.
- `is_abundant(24);` is `true` — a second, larger case.
- `is_abundant(6);` is `false` — `6` is perfect (`sum == 6`), not
  abundant (`sum > 6` is false).
- `is_abundant(8);` is `false` — `1 + 2 + 4 == 7 < 8`, deficient.
- `is_abundant(1);` is `false` — proper-divisor sum is `0`, not `> 1`;
  confirms the `value == 1` case isn't swallowed by an incorrect
  early-out.
- `is_abundant(0);` is `false`, `is_abundant(-12);` is `false` —
  non-positive input, no domain error, matching the cluster's
  negative/zero-input convention.
- `is_abundant(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"is_abundant() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of the
  cluster.
- `is_abundant(true);` (bool) raises `CinderRuntimeError` matching
  `"is_abundant() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_perfect_number`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_abundant` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `is_deficient` — sum-of-proper-divisors-below-n predicate

Build: add `is_deficient(n)` to `cinder/builtins.py`, completing the
perfect/abundant/deficient divisor-sum trio alongside `is_perfect_number`
(task 2) and `is_abundant` (task 3 above — by the time this task is
claimed it will have landed and shifted the file's line numbers, so
search for `is_abundant` rather than trusting a specific line) — a
deficient number's proper divisors sum to *less* than the number itself,
e.g. `8`: `1 + 2 + 4 = 7 < 8`. Every positive integer is exactly one of
perfect, abundant, or deficient, so this is the natural task to close
out the trio right after `is_abundant`.

Model the arity/type-checking and computation on `_is_abundant`'s
structure exactly (search for `def _is_abundant`) — same
`_require_arity("is_deficient", arguments, 1, line, column)` and
`_require_int("is_deficient", arguments[0], line, column)` calls, same
`if value < 1: return False` non-positive early-out (no domain error),
same `total = 1 if value > 1 else 0` plus `math.isqrt`-bounded
trial-division loop building `total`. The only difference from
`is_abundant` is the final comparison: return `total < value` instead of
`total > value` (so a perfect number, where `total == value`, is
correctly neither abundant nor deficient — do not use `<=`/`>=` for
either predicate, or a perfect number would incorrectly satisfy one of
them).

Acceptance criteria:
- `is_deficient(8);` is `true` — `1 + 2 + 4 == 7 < 8`.
- `is_deficient(1);` is `true` — proper-divisor sum is `0 < 1`.
- `is_deficient(10);` is `true` — `1 + 2 + 5 == 8 < 10`.
- `is_deficient(6);` is `false` — `6` is perfect (`sum == 6`), not
  deficient (`sum < 6` is false).
- `is_deficient(12);` is `false` — `12` is abundant (`sum == 16 > 12`),
  not deficient.
- `is_deficient(0);` is `false`, `is_deficient(-8);` is `false` —
  non-positive input, no domain error, matching the cluster's
  negative/zero-input convention.
- `is_deficient(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"is_deficient() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of the
  cluster.
- `is_deficient(true);` (bool) raises `CinderRuntimeError` matching
  `"is_deficient() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_abundant`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_deficient` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Standard library: `is_palindrome_number` — numeric-digit palindrome predicate

Build: add `is_palindrome_number(n)` to `cinder/builtins.py`, sitting
next to `reverse_int` (task 1 above — by the time this task is claimed
task 1 will have landed and shifted the file's line numbers, so search
for `reverse_int` rather than trusting a specific line) rather than the
boolean predicate cluster proper — it belongs here because it's built
directly on top of `reverse_int` rather than being an independent
digit-by-digit walk like `is_armstrong`/`is_perfect_square`. This is the
numeric sibling to the existing string `is_palindrome` (which already
tests whether a *string* reads the same forwards and backwards): this
one tests whether an integer's decimal digits do.

**Depends on task 1 (`reverse_int`) already being merged** — if task 1
is still open/unclaimed when this task is picked up, claim task 1
first instead of skipping ahead (per this file's own "do not skip
ahead" rule above).

Model the arity/type-checking on `reverse_int`'s own structure (search
for `def _reverse_int`): reuse `_require_arity("is_palindrome_number",
arguments, 1, line, column)` and `_require_int("is_palindrome_number",
arguments[0], line, column)` (the same helper the rest of the cluster
uses, defined at `cinder/builtins.py:157-162`). For the computation,
negative input is always `false` — the leading `-` sign breaks digit
symmetry on its own, so there is no ambiguity to resolve (unlike
`reverse_int` itself, this predicate does not need to reapply a sign):
`if value < 0: return False`, otherwise compare the value directly
against its own reversed digit string, *not* against a call to the
`_reverse_int` helper — reuse the digit-string reversal
(`str(value)[::-1]`) directly rather than routing through
`_reverse_int`'s sign-handling logic, since that logic exists to solve
a problem (preserving sign) this predicate has already special-cased
away: `return str(value) == str(value)[::-1]`.

Acceptance criteria:
- `is_palindrome_number(0);` is `true`.
- `is_palindrome_number(5);` is `true` — single digit.
- `is_palindrome_number(121);` is `true`.
- `is_palindrome_number(12321);` is `true` — odd-length palindrome.
- `is_palindrome_number(123);` is `false`.
- `is_palindrome_number(120);` is `false` — trailing zero breaks
  symmetry (reversed digit-string is `"021"`, not equal to `"120"`).
- `is_palindrome_number(-121);` is `false` — negative input is always
  `false`, even though `121` itself is a palindrome; no domain error.
- `is_palindrome_number(3.0);` (float, even though numerically whole)
  raises `CinderRuntimeError` matching `"is_palindrome_number()
  requires an int, got float"` — no implicit float-to-int coercion,
  matching the rest of the cluster.
- `is_palindrome_number(true);` (bool) raises `CinderRuntimeError`
  matching `"is_palindrome_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `reverse_int`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_palindrome_number` added near `is_palindrome`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
