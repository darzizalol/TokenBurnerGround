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

## 1. Standard library: `nth_circular_prime` — circular prime found at a 1-indexed position

Build: `is_circular_prime` (`cinder/builtins.py`, search `def
_is_circular_prime`: a prime where every rotation of its decimal digits
is also prime, e.g. `197` is circular since `197`, `971`, and `719` are
all prime) has no value-returning `nth_*` sibling, the same gap
`nth_smith_number`/`nth_carmichael_number`/`nth_twin_prime`/`nth_self_number`/
`nth_emirp` (all already merged, `#406`/`#408`/`#410`/`#411`/`#412`),
and `nth_polydivisible` (already merged, `#414`) already close for their own
predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_circular_prime(1));'
# -> <eval>:1:7: undefined name 'nth_circular_prime' (did you mean
#    'is_circular_prime'?)
```

Worked examples: the first twenty circular primes (confirmed by
scanning with `is_circular_prime` directly) are `2, 3, 5, 7, 11, 13,
17, 31, 37, 71, 73, 79, 97, 113, 131, 197, 199, 311, 337, 373`, so
`nth_circular_prime(1)` is `2` and `nth_circular_prime(10)` is `71`.
The 15th is `131`, the 20th is `373`, the 50th is `919393`.

Unlike the twin-prime/emirp scans, circular primes thin out fast once
digit-count grows (every digit but `1` in a multi-digit circular prime
must itself be a valid non-leading rotation digit, so the whole
sequence effectively collapses to permutations of `1`, `3`, `7`, `9` — a
known number-theoretic fact, not a bug to fix), so a single
`nth_circular_prime(50)` call is measurably slower (~3 seconds observed
locally) than the other `nth_*` builtins in this backlog. Keep the
self-consistency acceptance check below at `1..15` rather than the
`1..50` other recent `nth_*` tasks use — repeating the scan from
scratch 50 times (as that check does) would multiply into an
unacceptably slow test suite, the same tradeoff `nth_carmichael_number`
(`#408`) already made for the same reason (its own test only checks
`1..15`).

Add directly after `_is_circular_prime` (search `def
_is_circular_prime`, immediately before `def _is_twin_prime`) — keeps
the value-returning helper next to the predicate it mirrors:
```python
def _nth_circular_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_circular_prime", arguments, 1, line, column)
    value = _require_int("nth_circular_prime", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_circular_prime() requires a positive integer, domain error",
            line, column,
        )

    def _trial_division_is_prime(candidate: int) -> bool:
        if candidate < 2:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return False
        return True

    def _is_circular_prime_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        digits = str(candidate)
        for index in range(len(digits)):
            rotated = int(digits[index:] + digits[:index])
            if not _trial_division_is_prime(rotated):
                return False
        return True

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_circular_prime_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_twin_prime`/`_nth_emirp`, with the inner
candidate check copied verbatim from `_is_circular_prime`'s own body
instead of calling `_is_circular_prime` directly — the same "duplicate
the tiny predicate body instead of a redundant
`_require_arity`/`_require_int` round-trip per candidate" choice every
recent `nth_*` task already makes.) Register the new dict entry (search
`"is_circular_prime": _is_circular_prime,`, add `"nth_circular_prime":
_nth_circular_prime,` directly after it, before `"is_twin_prime":
_is_twin_prime,`).

Acceptance criteria:
- `nth_circular_prime(1);` through `nth_circular_prime(15);` are `2, 3,
  5, 7, 11, 13, 17, 31, 37, 71, 73, 79, 97, 113, 131` in order — the
  worked example above.
- `nth_circular_prime(20);` is `373` and `nth_circular_prime(50);` is
  `919393` — further worked examples confirming the scan scales past
  the first fifteen (the `50` case is expected to take a few seconds —
  see the performance note above, not a bug).
- For every `position` in `1..15`,
  `is_circular_prime(nth_circular_prime(position))` is `true` — a
  reduced-range self-consistency check (see the performance note above
  for why `1..15` and not `1..50` here), the same style
  `nth_carmichael_number`'s own test suite already uses for the same
  reason.
- `nth_circular_prime(0);`, `nth_circular_prime(-3);` both raise
  `CinderRuntimeError` matching `"nth_circular_prime\(\) requires a
  positive integer, domain error"`.
- `nth_circular_prime(true);` raises `CinderRuntimeError` matching
  `"nth_circular_prime\(\) requires an int, got bool"`.
- `nth_circular_prime("5");` raises `CinderRuntimeError` matching
  `"nth_circular_prime\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_circular_prime`,
search `def _is_circular_prime`), `tests/test_builtins.py` (new `class
TestNthCircularPrime`, modeled on `class TestNthCarmichaelNumber`,
search that name, for the test shapes and reduced-range self-consistency
check above — place it near the existing `class TestIsCircularPrime`,
search that name). Once merged, `README.md`'s existing
`is_circular_prime` bullet needs `nth_circular_prime` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `nth_sad_number` — sad number found at a 1-indexed position

Build: `is_sad_number` (`cinder/builtins.py`, search `def _is_sad_number`:
a non-negative integer that, under repeated replace-with-sum-of-squared-digits,
never reaches `1` and instead cycles — the complement of `is_happy_number`,
e.g. `2` is sad since its trajectory `2, 4, 16, 37, 58, 89, 145, 42, 20, 4,
...` repeats `4` without ever hitting `1`) has no value-returning `nth_*`
sibling, unlike its own opposite `is_happy_number` (`nth_happy_number`
already exists, search `def _nth_happy_number`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_sad_number(1));'
# -> <eval>:1:7: undefined name 'nth_sad_number' (did you mean
#    'is_sad_number'?)
```

Worked examples: the first ten sad numbers (confirmed by scanning with
`is_sad_number` directly) are `0, 2, 3, 4, 5, 6, 8, 9, 11, 12`, so
`nth_sad_number(1)` is `0` and `nth_sad_number(10)` is `12`. The 20th is
`25`, the 50th is `60` — sad numbers are dense (happy numbers are the rare
exception, not the rule), so unlike the prime-based or digit-quirk `nth_*`
tasks elsewhere in this backlog, this scan is fast at every position.

Like `nth_self_number`/`nth_polydivisible`/`nth_trimorphic_number`
(already merged or above), position `1` maps to candidate `0`, not `1`:
`is_sad_number(0)` is `true` (`0`'s trajectory is just `0, 0, 0, ...`,
which cycles at `0` without ever reaching `1`), and `0` is the smallest
value `is_sad_number` ever accepts (it returns `false` outright for
negative input, per its own `if value < 0: return False` guard), so the
scan must start *before* `0` (`candidate = -1`, incremented before the
first check) to avoid silently excluding it from the sequence forever.

Add directly after `_is_sad_number` (search `def _is_sad_number`,
immediately before `def _is_self_number`) — keeps the value-returning
helper next to the predicate it mirrors:
```python
def _nth_sad_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_sad_number", arguments, 1, line, column)
    value = _require_int("nth_sad_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_sad_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_sad_number_candidate(candidate: int) -> bool:
        seen = set()
        while candidate != 1:
            if candidate in seen:
                return True
            seen.add(candidate)
            candidate = sum(int(digit) ** 2 for digit in str(candidate))
        return False

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_sad_number_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_sad_number`'s own body
minus its `value < 0` guard, since the scan never visits a negative
candidate — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice every recent `nth_*` task already makes.) Register the new dict
entry (search `"is_sad_number": _is_sad_number,`, add `"nth_sad_number":
_nth_sad_number,` directly after it, before `"is_self_number":
_is_self_number,`).

Acceptance criteria:
- `nth_sad_number(1);` through `nth_sad_number(10);` are `0, 2, 3, 4, 5,
  6, 8, 9, 11, 12` in order — the worked example above.
- `nth_sad_number(20);` is `25` and `nth_sad_number(50);` is `60` —
  further worked examples confirming the scan scales past the first ten.
- For every `position` in `1..50`,
  `is_sad_number(nth_sad_number(position))` is `true` — the same
  self-consistency check `nth_smith_number`/`nth_carmichael_number`/
  `nth_twin_prime`/`nth_self_number`/`nth_emirp`/`nth_polydivisible`/
  `nth_trimorphic_number`/`nth_circular_prime`'s own test suites already
  run against their predicates.
- `nth_sad_number(0);`, `nth_sad_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_sad_number\(\) requires a positive
  integer, domain error"` — note this domain check is on the *position*
  argument, unrelated to `0` being a valid *sad number* itself
  (`nth_sad_number(1)` legitimately returns `0`).
- `nth_sad_number(true);` raises `CinderRuntimeError` matching
  `"nth_sad_number\(\) requires an int, got bool"`.
- `nth_sad_number("5");` raises `CinderRuntimeError` matching
  `"nth_sad_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_sad_number`,
search `def _is_sad_number`), `tests/test_builtins.py` (new `class
TestNthSadNumber`, modeled on `class TestNthHappyNumber`, search that
name, for the test shapes above — place it near the existing `class
TestIsSadNumber`, search that name). Once merged, `README.md`'s existing
`is_sad_number` bullet needs `nth_sad_number` added right after it, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Standard library: `nth_vampire_number` — vampire number found at a 1-indexed position

Build: `is_vampire_number` (`cinder/builtins.py`, search `def
_is_vampire_number`: an even-digit-count, non-negative integer that
splits into two equal-half "fangs" whose digits, put back together and
sorted, reproduce the original number's own sorted digits — e.g. `1260
= 21 * 60`, and `sorted("1260") == sorted("21" + "60")` — excluding the
trivial case where both fangs end in `0`) has no value-returning
`nth_*` sibling, the same gap `nth_smith_number`/`nth_carmichael_number`/
`nth_twin_prime`/`nth_self_number`/`nth_emirp` (all already merged,
`#406`/`#408`/`#410`/`#411`/`#412`) already close for their own
predicates. This task was scoped once before (2026-09-06 grooming pass)
then deliberately dropped back out unclaimed the following night to hold
the queue at 5 tasks while requeuing the higher-priority `match`-guards
depth task above — it was deferred, not dead, and is reconstructed here
from scratch against current `main`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_vampire_number(1));'
# -> <eval>:1:7: undefined name 'nth_vampire_number' (did you mean
#    'is_vampire_number'?)
```

Worked examples: the first twenty vampire numbers (confirmed by scanning
with `is_vampire_number` directly) are `1260, 1395, 1435, 1530, 1827,
2187, 6880, 102510, 104260, 105210, 105264, 105750, 108135, 110758,
115672, 116725, 117067, 118440, 120600, 123354`, so
`nth_vampire_number(1)` is `1260` and `nth_vampire_number(10)` is
`105210`. The 15th is `115672`, the 20th is `123354`, the 50th is
`163944`.

Unlike the digit-quirk `nth_*` tasks (`nth_self_number`,
`nth_polydivisible`, `nth_trimorphic_number`, `nth_sad_number`), no
candidate below `1000` is ever vampiric (`is_vampire_number`'s own
`digit_count % 2 != 0 or digit_count < 4` guard rejects every value
under four digits outright), so the scan starts at `candidate = 0`
exactly like `nth_smith_number`/`nth_carmichael_number`/`nth_twin_prime`
already do — there is no off-by-one "position 1 maps to candidate 0"
quirk here. Also like `nth_circular_prime` (task 1 above, not yet
merged), the per-candidate check itself
(a fang search over every value in `[10**(half-1), 10**half)`) gets more
expensive as candidates grow into six digits, so a full
`nth_vampire_number(50)` scan is measurably slower (~2-3 seconds
observed locally) than the digit-quirk `nth_*` builtins — keep the
self-consistency acceptance check below at `1..15` rather than `1..50`,
the same tradeoff `nth_carmichael_number`/`nth_circular_prime` already
made for the same reason.

Add directly after `_is_vampire_number` (search `def
_is_vampire_number`, immediately before `def _num_divisors`) — keeps
the value-returning helper next to the predicate it mirrors:
```python
def _nth_vampire_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_vampire_number", arguments, 1, line, column)
    value = _require_int("nth_vampire_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_vampire_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_vampire_number_candidate(candidate: int) -> bool:
        digits = str(candidate)
        digit_count = len(digits)
        if digit_count % 2 != 0 or digit_count < 4:
            return False
        half = digit_count // 2
        lower = 10 ** (half - 1)
        upper = 10 ** half
        target = sorted(digits)
        for fang_a in range(lower, upper):
            if candidate % fang_a != 0:
                continue
            fang_b = candidate // fang_a
            if fang_b < lower or fang_b >= upper:
                continue
            if fang_a % 10 == 0 and fang_b % 10 == 0:
                continue
            if sorted(str(fang_a) + str(fang_b)) == target:
                return True
        return False

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_vampire_number_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_vampire_number`'s own
body, minus its `value < 0` early return, since the scan never visits a
negative candidate — the same "duplicate the tiny predicate body
instead of a redundant `_require_arity`/`_require_int` round-trip per
candidate" choice every recent `nth_*` task already makes.) Register
the new dict entry (search `"is_vampire_number": _is_vampire_number,`,
add `"nth_vampire_number": _nth_vampire_number,` directly after it,
before `"num_divisors": _num_divisors,`).

Acceptance criteria:
- `nth_vampire_number(1);` through `nth_vampire_number(7);` are `1260,
  1395, 1435, 1530, 1827, 2187, 6880` in order — the four-digit prefix
  of the worked example above.
- `nth_vampire_number(10);` is `105210`, `nth_vampire_number(15);` is
  `115672`, and `nth_vampire_number(20);` is `123354` — further worked
  examples confirming the scan crosses the four-digit-to-six-digit
  boundary correctly (there are no five-digit vampire numbers at all;
  digit-count must be even).
- `nth_vampire_number(50);` is `163944` — a worked example confirming
  the scan scales well past the first twenty (expected to take a few
  seconds — see the performance note above, not a bug).
- For every `position` in `1..15`,
  `is_vampire_number(nth_vampire_number(position))` is `true` — a
  reduced-range self-consistency check (see the performance note above
  for why `1..15` and not `1..50` here), the same style
  `nth_carmichael_number`'s and `nth_circular_prime`'s own test suites
  already use for the same reason.
- `nth_vampire_number(0);`, `nth_vampire_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_vampire_number\(\) requires a
  positive integer, domain error"`.
- `nth_vampire_number(true);` raises `CinderRuntimeError` matching
  `"nth_vampire_number\(\) requires an int, got bool"`.
- `nth_vampire_number("5");` raises `CinderRuntimeError` matching
  `"nth_vampire_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_vampire_number`,
search `def _is_vampire_number`), `tests/test_builtins.py` (new `class
TestNthVampireNumber`, modeled on `class TestNthCarmichaelNumber`,
search that name, for the test shapes and reduced-range self-consistency
check above — place it near the existing `class TestIsVampireNumber`,
search that name). Once merged, `README.md`'s existing
`is_vampire_number` bullet needs `nth_vampire_number` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `nth_evil` — evil number found at a 1-indexed position

Build: `is_evil` (`cinder/builtins.py`, search `def _is_evil`: a
non-negative integer whose binary representation has an even number of
`1` bits, e.g. `3` is `0b11`, two set bits, so it's evil; its complement
`is_odious` requires an odd count) has no value-returning `nth_*`
sibling, the same gap `nth_smith_number`/`nth_carmichael_number`/
`nth_twin_prime`/`nth_self_number`/`nth_emirp` (all already merged,
`#406`/`#408`/`#410`/`#411`/`#412`) already close for their own
predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_evil(1));'
# -> <eval>:1:7: undefined name 'nth_evil' (did you mean 'is_evil'?)
```

Worked examples: the first twenty evil numbers (confirmed by scanning
with `is_evil` directly) are `0, 3, 5, 6, 9, 10, 12, 15, 17, 18, 20, 23,
24, 27, 29, 30, 33, 34, 36, 39`, so `nth_evil(1)` is `0` and
`nth_evil(10)` is `18`. The 20th is `39`, the 50th is `99`. Unlike the
prime-based or digit-quirk `nth_*` tasks elsewhere in this backlog, evil
numbers are exactly half of all non-negative integers by construction
(popcount parity), so the scan stays fast at every position — no
performance caveat needed here, unlike `nth_circular_prime`/
`nth_vampire_number` above.

Like `nth_self_number`/`nth_polydivisible`/`nth_trimorphic_number`/
`nth_sad_number` (already merged or above), position `1` maps to
candidate `0`, not `1`: `is_evil(0)` is `true` (`bin(0)` is `"0b0"`,
zero set bits, which is even), and `0` is the smallest value `is_evil`
ever accepts (it raises `CinderRuntimeError` outright for negative
input, per its own `if value < 0` guard — note this is a *raise*, not a
`return False` like most other digit-quirk predicates in this backlog,
but irrelevant here since the scan never visits a negative candidate),
so the scan must start *before* `0` (`candidate = -1`, incremented
before the first check) to avoid silently excluding it from the
sequence forever.

Add directly after `_is_evil` (search `def _is_evil`, immediately
before `def _is_odious`) — keeps the value-returning helper next to the
predicate it mirrors:
```python
def _nth_evil(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_evil", arguments, 1, line, column)
    value = _require_int("nth_evil", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_evil() requires a positive integer, domain error",
            line, column,
        )

    def _is_evil_candidate(candidate: int) -> bool:
        return bin(candidate).count("1") % 2 == 0

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_evil_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_evil`'s own body minus
its `value < 0` guard, since the scan never visits a negative candidate
— the same "duplicate the tiny predicate body instead of a redundant
`_require_arity`/`_require_int` round-trip per candidate" choice every
recent `nth_*` task already makes.) Register the new dict entry (search
`"is_evil": _is_evil,`, add `"nth_evil": _nth_evil,` directly after it,
before `"is_odious": _is_odious,`).

Acceptance criteria:
- `nth_evil(1);` through `nth_evil(10);` are `0, 3, 5, 6, 9, 10, 12, 15,
  17, 18` in order — the worked example above.
- `nth_evil(20);` is `39` and `nth_evil(50);` is `99` — further worked
  examples confirming the scan scales past the first ten.
- For every `position` in `1..50`, `is_evil(nth_evil(position))` is
  `true` — the same self-consistency check `nth_smith_number`/
  `nth_carmichael_number`/`nth_twin_prime`/`nth_self_number`/
  `nth_emirp`'s own test suites already run against their predicates.
- `nth_evil(0);`, `nth_evil(-3);` both raise `CinderRuntimeError`
  matching `"nth_evil\(\) requires a positive integer, domain error"` —
  note this domain check is on the *position* argument, unrelated to
  `0` being a valid *evil number* itself (`nth_evil(1)` legitimately
  returns `0`).
- `nth_evil(true);` raises `CinderRuntimeError` matching
  `"nth_evil\(\) requires an int, got bool"`.
- `nth_evil("5");` raises `CinderRuntimeError` matching
  `"nth_evil\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_evil`, search
`def _is_evil`), `tests/test_builtins.py` (new `class TestNthEvil`,
modeled on `class TestNthSmithNumber`, search that name, for the test
shapes above — place it near the existing `class TestIsEvilIsOdious`,
search that name). Once merged, `README.md`'s existing `is_evil` bullet
needs `nth_evil` added right after it, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Standard library: `nth_odious` — odious number found at a 1-indexed position

Build: `is_odious` (`cinder/builtins.py`, search `def _is_odious`: a
non-negative integer whose binary representation has an *odd* number of
`1` bits — the complement of `is_evil`, which requires an even count)
has no value-returning `nth_*` sibling, the same gap `nth_evil` (task 4
above, not yet merged) closes for its own opposite predicate. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(nth_odious(1));'
# -> <eval>:1:7: undefined name 'nth_odious' (did you mean 'is_odious'?)
```

Worked examples: the first ten odious numbers (confirmed by scanning
with `is_odious` directly) are `1, 2, 4, 7, 8, 11, 13, 14, 16, 19`, so
`nth_odious(1)` is `1` and `nth_odious(10)` is `19`. The 15th is `28`,
the 20th is `38`, the 50th is `98`. Like `is_evil`, odious numbers are
exactly half of all non-negative integers by construction (popcount
parity), so the scan stays fast at every position — no performance
caveat needed here.

Unlike `nth_evil`/`nth_self_number`/`nth_polydivisible`/
`nth_trimorphic_number`/`nth_sad_number` (task 4 above and already
merged siblings), position `1` maps to candidate `1`, not `0`:
`is_odious(0)` is `false` (`bin(0)` is `"0b0"`, zero set bits, which is
even, not odd), so `0` is never itself an odious number. The scan can
still start from `candidate = -1` (incremented before the first check,
the same shape `nth_evil` uses) — it will simply check and reject `0`
before finding `1`, which is harmless and keeps the two sibling
implementations structurally identical for anyone reading them side by
side.

Add directly after `_is_odious` (search `def _is_odious`, immediately
before `def _is_pernicious`) — keeps the value-returning helper next to
the predicate it mirrors:
```python
def _nth_odious(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_odious", arguments, 1, line, column)
    value = _require_int("nth_odious", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_odious() requires a positive integer, domain error",
            line, column,
        )

    def _is_odious_candidate(candidate: int) -> bool:
        return bin(candidate).count("1") % 2 == 1

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_odious_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_odious`'s own body
minus its `value < 0` guard, since the scan never visits a negative
candidate — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice every recent `nth_*` task already makes.) Register the new dict
entry (search `"is_odious": _is_odious,`, add `"nth_odious":
_nth_odious,` directly after it, before `"is_pernicious":
_is_pernicious,`).

Acceptance criteria:
- `nth_odious(1);` through `nth_odious(10);` are `1, 2, 4, 7, 8, 11, 13,
  14, 16, 19` in order — the worked example above.
- `nth_odious(15);` is `28`, `nth_odious(20);` is `38`, and
  `nth_odious(50);` is `98` — further worked examples confirming the
  scan scales well past the first ten.
- For every `position` in `1..50`, `is_odious(nth_odious(position))` is
  `true` — the same self-consistency check every recent `nth_*` task's
  own test suite already runs against its predicate.
- `nth_odious(0);`, `nth_odious(-3);` both raise `CinderRuntimeError`
  matching `"nth_odious\(\) requires a positive integer, domain error"`.
- `nth_odious(true);` raises `CinderRuntimeError` matching
  `"nth_odious\(\) requires an int, got bool"`.
- `nth_odious("5");` raises `CinderRuntimeError` matching
  `"nth_odious\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_odious`, search
`def _is_odious`), `tests/test_builtins.py` (new `class TestNthOdious`,
modeled on `class TestNthSmithNumber`, search that name, for the test
shapes above — place it near the existing `class TestIsEvilIsOdious`,
search that name). Once merged, `README.md`'s existing `is_odious`
bullet needs `nth_odious` added right after it, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

### Language: guards in `match` arms (`n if n > 0 => "positive"`) — PR #314, closed 2026-08-25

Bounced 3x with `VERDICT: CHANGES REQUESTED`, all the same recurring bug:
each fix round patched `_bracket_depth` tracking (used to scope the
bare-arrow/guard `=>` ambiguity fix) for one nested construct — call/list/map
arguments (round 1), `match` expressions (round 2), `fn` expressions (round
3) — while the reviewer kept finding another construct the fix hadn't
threaded depth through, and round 3's review flagged a 4th possible gap
(`_arrow_body`'s bare-expression branch, `_block()`) that was never
confirmed either way. Next attempt should enumerate *every* production that
opens a paren/bracket/brace scope up front (grep `_bracket_depth` usages in
the closed PR's final diff for the list-so-far) rather than fixing gaps
reactively one review round at a time — or consider a structurally
different fix that doesn't need per-construct threading at all (e.g.
resolving the bare-arrow/guard ambiguity by lookahead at the `=>` site
instead of a suppression-depth counter).

**Resolved 2026-09-08, merged as `#413`.** Requeued 2026-09-07 with
exactly the alternative strategy this postmortem called for (parse the
guard via the parser's ordinary `_ternary()` entry point instead of any
hand-rolled bracket/token scan) — that fix took two more review rounds
(a call/list/index/grouping leak, then a nested-`match` leak) before
landing clean, but never regressed to the original `_bracket_depth`
bug class this postmortem was about. See `CHANGELOG.md` for the full
three-round history.
