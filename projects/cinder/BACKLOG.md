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

## 1. Standard library: `is_abundant` — sum-of-proper-divisors-exceeds-n predicate [claimed 2026-08-07T20:18:14Z]

Build: add `is_abundant(n)` to `cinder/builtins.py`, one more member of
the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`/`is_perfect_square`/`is_armstrong`/
`is_leap_year`/`reverse_int`/`is_perfect_number`, already landed —
search for `is_perfect_number` rather than trusting a specific line) —
an abundant number's proper divisors (divisors
excluding itself) sum to *more* than the number itself, e.g. `12`:
`1 + 2 + 3 + 4 + 6 = 16 > 12`. It's the natural next member after
`is_perfect_number` since perfect/abundant/deficient (task 2 below) are
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

## 2. Standard library: `is_deficient` — sum-of-proper-divisors-below-n predicate

Build: add `is_deficient(n)` to `cinder/builtins.py`, completing the
perfect/abundant/deficient divisor-sum trio alongside `is_perfect_number`
(already landed) and `is_abundant` (task 1 above — by the time this task is
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

## 3. Standard library: `is_palindrome_number` — numeric-digit palindrome predicate

Build: add `is_palindrome_number(n)` to `cinder/builtins.py`, sitting
next to `reverse_int` (already landed, search for `reverse_int` rather
than trusting a specific line) rather than the boolean predicate
cluster proper — it belongs here because it's built directly on top of
`reverse_int` rather than being an independent digit-by-digit walk like
`is_armstrong`/`is_perfect_square`. This is the numeric sibling to the
existing string `is_palindrome` (which already tests whether a *string*
reads the same forwards and backwards): this one tests whether an
integer's decimal digits do.

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

## 4. Standard library: `digital_root` — repeated-digit-sum-to-single-digit

Build: add `digital_root(n)` to `cinder/builtins.py`, sitting next to
`digit_sum`/`reverse_int` (search for `def _reverse_int` — by the time
this task is claimed, tasks 1-4 above will have landed and shifted line
numbers) rather than the boolean predicate cluster — like `reverse_int`,
it returns a number, not a boolean. The digital root of a non-negative
integer is what you get by repeatedly summing its decimal digits until
a single digit remains (e.g. `38 -> 3+8=11 -> 1+1=2`, so
`digital_root(38) == 2`). Like `digit_sum` (not `reverse_int`), sign is
ignored rather than preserved — a digital root is a magnitude property,
and `digit_sum` already sets this convention for the cluster.

Model the arity/type-checking on `_digit_sum`'s structure (search for
`def _digit_sum`): reuse `_require_arity("digital_root", arguments, 1,
line, column)` and `_require_int("digital_root", arguments[0], line,
column)` (the same helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162`). For the computation, do **not** write a
naive repeated-summing loop — use the well-known O(1) digital-root
identity instead, since Cinder ints are arbitrary-precision and a large
bignum could otherwise force many summing passes: take `value =
abs(value)` first (sign ignored, per above), then `return 0 if value ==
0 else 1 + (value - 1) % 9` (the standard closed-form digital root:
every nonzero value maps to `1..9`, cycling every 9, and `0` is the one
fixed point the modular formula doesn't cover on its own).

Acceptance criteria:
- `digital_root(0);` is `0`.
- `digital_root(5);` is `5` — single digit is its own digital root.
- `digital_root(38);` is `2` — `3+8=11`, then `1+1=2`.
- `digital_root(9999);` is `9` — `9+9+9+9=36`, then `3+6=9`.
- `digital_root(-38);` is `2` — sign ignored, matching `digit_sum`'s
  convention (not `reverse_int`'s sign-preserving one).
- `digital_root(999999999999999999999999);` is `9` — a bignum case
  confirming the closed-form approach handles arbitrary-precision
  input without a slow repeated-summing loop.
- `digital_root(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"digital_root() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of the
  cluster.
- `digital_root(true);` (bool) raises `CinderRuntimeError` matching
  `"digital_root() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `reverse_int`/
`digit_sum`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `digital_root` added near `digit_sum`/
`reverse_int`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 5. Standard library: `is_composite` — non-prime-above-one predicate

Build: add `is_composite(n)` to `cinder/builtins.py`, registered right
next to `is_prime` (search for `def _is_prime` — by the time this task
is claimed, tasks 1-4 above will have landed and shifted line numbers)
in the integer-property predicate cluster. A composite number is an
integer greater than `1` that is *not* prime (e.g. `4`, `6`, `8`, `9`);
this completes the classical three-way split of the non-negative
integers into prime, composite, and neither (`0`, `1`) the same way
`is_perfect_number`/`is_abundant`/`is_deficient` cover every positive
integer's divisor-sum classification.

Model the arity/type-checking and trial-division loop on `_is_prime`'s
own structure exactly (search for `def _is_prime`): reuse
`_require_arity("is_composite", arguments, 1, line, column)` and
`_require_int("is_composite", arguments[0], line, column)` (the same
helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162`). Do **not** call `_is_prime`'s function
object and negate its result — `_is_prime` returns `False` for `n < 2`
too, which would make `is_composite` incorrectly `true` for `0`, `1`,
and every negative number. Instead give `is_composite` its own
early-out — `if value < 4: return False` (the smallest composite
number is `4`; `2` and `3` are prime, `0`/`1`/negatives are neither) —
then reuse the same `int(value ** 0.5) + 1`-bounded trial-division loop
`_is_prime` uses (from `2` up to that bound, checking `value % divisor
== 0`), returning `True` the moment a divisor is found and `False` if
the loop completes without one (i.e. `value` is actually prime, so not
composite).

Acceptance criteria:
- `is_composite(4);` is `true` — smallest composite number.
- `is_composite(6);` is `true`.
- `is_composite(9);` is `true` — odd composite, confirms the loop
  isn't only catching even numbers.
- `is_composite(97);` is `false` — a larger prime.
- `is_composite(2);` is `false`, `is_composite(3);` is `false` — the
  two smallest primes, must not be swept in by an off-by-one on the
  early-out.
- `is_composite(1);` is `false`, `is_composite(0);` is `false`,
  `is_composite(-6);` is `false` — non-positive/non-composite input,
  no domain error, and specifically *not* `true` the way naively
  negating `is_prime(n)` would incorrectly produce.
- `is_composite(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"is_composite() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of
  the cluster.
- `is_composite(true);` (bool) raises `CinderRuntimeError` matching
  `"is_composite() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_prime`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_composite` added near `is_prime`, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
