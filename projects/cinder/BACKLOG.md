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

## 1. Standard library: `nth_vampire_number` — vampire number found at a 1-indexed position [claimed 2026-09-08T14:28:24Z]

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
quirk here. Also like `nth_circular_prime` (already merged), the
per-candidate check itself
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

## 2. Standard library: `nth_evil` — evil number found at a 1-indexed position

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
performance caveat needed here, unlike the already-merged
`nth_circular_prime` or `nth_vampire_number` (task 1 above).

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

## 3. Standard library: `nth_odious` — odious number found at a 1-indexed position

Build: `is_odious` (`cinder/builtins.py`, search `def _is_odious`: a
non-negative integer whose binary representation has an *odd* number of
`1` bits — the complement of `is_evil`, which requires an even count)
has no value-returning `nth_*` sibling, the same gap `nth_evil` (task 2
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
`nth_trimorphic_number`/`nth_sad_number` (task 2 above and already
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

## 4. Standard library: `nth_composite` — composite number found at a 1-indexed position

Build: `is_composite` (`cinder/builtins.py`, search `def _is_composite`:
a non-negative integer with a divisor strictly between `1` and itself —
the complement of `is_prime`, `value < 4` returns `false` outright since
`0`/`1`/`2`/`3` are never composite) has no value-returning `nth_*`
sibling, unlike its own opposite `is_prime` (`nth_prime` already exists,
search `def _nth_prime`, sitting directly above `_is_composite` in the
file). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_composite(1));'
# -> <eval>:1:7: undefined name 'nth_composite' (did you mean
#    'is_composite'?)
```

Worked examples: the first twenty composite numbers (confirmed by
scanning with `is_composite` directly) are `4, 6, 8, 9, 10, 12, 14, 15,
16, 18, 20, 21, 22, 24, 25, 26, 27, 28, 30, 32`, so `nth_composite(1)`
is `4` and `nth_composite(10)` is `18`. The 15th is `26`, the 20th is
`32`, the 50th is `70`. Composites are dense — every integer that isn't
`0`, `1`, or prime — so unlike the digit-quirk or prime-rotation `nth_*`
tasks elsewhere in this backlog, this scan stays fast at every position
(confirmed locally: `nth_composite(50)` via `python3 -m cinder.cli eval`
returns in well under a second), no performance caveat needed.

Like `nth_prime` (same file, directly above `_is_composite`), position
`1` maps to candidate `4`, not `0` or `1`: `is_composite` rejects every
value under `4` outright, so the scan can start at `candidate = 3`
(incremented before the first check) with no off-by-one risk.

Add directly after `_is_composite` (search `def _is_composite`,
immediately before `def _is_semiprime`) — keeps the value-returning
helper next to the predicate it mirrors:
```python
def _nth_composite(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_composite", arguments, 1, line, column)
    value = _require_int("nth_composite", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_composite() requires a positive integer, domain error",
            line, column,
        )

    def _is_composite_candidate(candidate: int) -> bool:
        if candidate < 4:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return True
        return False

    count = 0
    candidate = 3
    while count < value:
        candidate += 1
        if _is_composite_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_composite`'s own body,
the same "duplicate the tiny predicate body instead of a redundant
`_require_arity`/`_require_int` round-trip per candidate" choice every
recent `nth_*` task already makes.) Register the new dict entry (search
`"is_composite": _is_composite,`, add `"nth_composite":
_nth_composite,` directly after it, before `"is_semiprime":
_is_semiprime,`).

Acceptance criteria:
- `nth_composite(1);` through `nth_composite(10);` are `4, 6, 8, 9, 10,
  12, 14, 15, 16, 18` in order — the worked example above.
- `nth_composite(15);` is `26`, `nth_composite(20);` is `32`, and
  `nth_composite(50);` is `70` — further worked examples confirming the
  scan scales well past the first ten.
- For every `position` in `1..50`,
  `is_composite(nth_composite(position))` is `true` — the same
  self-consistency check every recent `nth_*` task's own test suite
  already runs against its predicate.
- `nth_composite(0);`, `nth_composite(-3);` both raise
  `CinderRuntimeError` matching `"nth_composite\(\) requires a positive
  integer, domain error"`.
- `nth_composite(true);` raises `CinderRuntimeError` matching
  `"nth_composite\(\) requires an int, got bool"`.
- `nth_composite("5");` raises `CinderRuntimeError` matching
  `"nth_composite\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_composite`,
search `def _is_composite`), `tests/test_builtins.py` (new `class
TestNthComposite`, modeled on `class TestNthPrime`, search that name,
for the test shapes above — place it near the existing `class
TestIsComposite`, search that name). Once merged, `README.md`'s existing
`is_composite` bullet needs `nth_composite` added right after it, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Standard library: `nth_power_of_two` — power of two found at a 1-indexed position

Build: `is_power_of_two` (`cinder/builtins.py`, search `def
_is_power_of_two`: a positive integer with exactly one set bit, tested
via the classic `value & (value - 1) == 0` trick, `value < 1` returns
`false` outright) has no value-returning `nth_*` sibling. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(nth_power_of_two(1));'
# -> <eval>:1:7: undefined name 'nth_power_of_two' (did you mean
#    'is_power_of_two'?)
```

Unlike every sequential-scan `nth_*` task elsewhere in this backlog,
powers of two have an exact closed form — position `k` is `2 ** (k -
1)` — the same shape `nth_octagonal`/`nth_nonagonal`/`nth_decagonal`
(search `def _nth_octagonal` for the pattern to copy) already use for
their own closed-form sequences, so there is no candidate scan and no
performance caveat: `nth_power_of_two(1)` is `1`, `nth_power_of_two(5)`
is `16`, `nth_power_of_two(10)` is `512`, `nth_power_of_two(20)` is
`524288`, and `nth_power_of_two(50)` is `562949953421312` (all four
confirmed by direct computation of `2 ** (k - 1)`; Python's arbitrary-
precision integers make even the 50th position instant, no overflow
concern the way a fixed-width language would have).

Add directly after `_is_power_of_two` (search `def _is_power_of_two`,
immediately before `def _is_evil`) — keeps the value-returning helper
next to the predicate it mirrors:
```python
def _nth_power_of_two(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_power_of_two", arguments, 1, line, column)
    value = _require_int("nth_power_of_two", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_power_of_two() requires a positive integer, domain error",
            line, column,
        )
    return 2 ** (value - 1)
```
(Same shape as `_nth_octagonal`/`_nth_nonagonal`/`_nth_decagonal` — a
direct closed-form return, no loop, no inner candidate-check helper,
since there's nothing to scan.) Register the new dict entry (search
`"is_power_of_two": _is_power_of_two,`, add `"nth_power_of_two":
_nth_power_of_two,` directly after it, before `"is_evil": _is_evil,`).

Acceptance criteria:
- `nth_power_of_two(1);` through `nth_power_of_two(5);` are `1, 2, 4, 8,
  16` in order — the closed-form doubling sequence.
- `nth_power_of_two(10);` is `512`, `nth_power_of_two(20);` is `524288`,
  and `nth_power_of_two(50);` is `562949953421312` — further worked
  examples confirming the closed form holds at larger positions.
- For every `position` in `1..50`,
  `is_power_of_two(nth_power_of_two(position))` is `true` — the same
  self-consistency check every recent `nth_*` task's own test suite
  already runs against its predicate.
- `nth_power_of_two(0);`, `nth_power_of_two(-3);` both raise
  `CinderRuntimeError` matching `"nth_power_of_two\(\) requires a
  positive integer, domain error"`.
- `nth_power_of_two(true);` raises `CinderRuntimeError` matching
  `"nth_power_of_two\(\) requires an int, got bool"`.
- `nth_power_of_two("5");` raises `CinderRuntimeError` matching
  `"nth_power_of_two\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_power_of_two`,
search `def _is_power_of_two`), `tests/test_builtins.py` (new `class
TestNthPowerOfTwo`, modeled on `class TestNthOctagonal`, search that
name, for the test shapes above — place it near the existing `class
TestIsPowerOfTwo`, search that name). Once merged, `README.md`'s
existing `is_power_of_two` bullet needs `nth_power_of_two` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `nth_pernicious` — pernicious number found at a 1-indexed position

Build: `is_pernicious` (`cinder/builtins.py`, search `def
_is_pernicious`: a non-negative integer whose popcount (number of set
bits) is itself prime, e.g. `3` is `0b11`, popcount `2`, which is
prime, so it's pernicious) has no value-returning `nth_*` sibling, the
same gap `nth_evil`/`nth_odious` (tasks 2-3 above, not yet merged)
close for their own popcount-based predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_pernicious(1));'
# -> <eval>:1:7: undefined name 'nth_pernicious' (did you mean
#    'is_pernicious'?)
```

Worked examples: the first twenty pernicious numbers (confirmed by
scanning with `is_pernicious` directly) are `3, 5, 6, 7, 9, 10, 11, 12,
13, 14, 17, 18, 19, 20, 21, 22, 24, 25, 26, 28`, so `nth_pernicious(1)`
is `3` and `nth_pernicious(10)` is `14`. The 15th is `21`, the 20th is
`28`, the 50th is `74`. Like `nth_evil`/`nth_odious`, pernicious numbers
are dense (roughly half of all integers below any given bound have a
prime popcount, since popcount grows with bit-length and small primes
like `2`/`3`/`5`/`7` cover most practical popcounts), so the scan stays
fast at every position — confirmed locally: scanning to the 50th
pernicious number takes well under a millisecond in raw Python, no
performance caveat needed.

Unlike `nth_evil` (position `1` maps to candidate `0`) or `nth_odious`
(position `1` maps to candidate `1`), position `1` maps to candidate
`3` here: `is_pernicious(0)` is `false` (popcount `0`, not prime),
`is_pernicious(1)` is `false` (popcount `1`, not prime — `1` is never
prime), and `is_pernicious(2)` is `false` (popcount `1`, same reason).
The scan can still start from `candidate = -1` (incremented before the
first check, the same shape `nth_evil`/`nth_odious` use) — it will
simply check and reject `0`, `1`, and `2` before finding `3`, which is
harmless and keeps all three sibling implementations structurally
identical for anyone reading them side by side.

Add directly after `_is_pernicious` (search `def _is_pernicious`,
immediately before `def _is_palindrome_list`) — keeps the
value-returning helper next to the predicate it mirrors:
```python
def _nth_pernicious(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_pernicious", arguments, 1, line, column)
    value = _require_int("nth_pernicious", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_pernicious() requires a positive integer, domain error",
            line, column,
        )

    def _is_pernicious_candidate(candidate: int) -> bool:
        popcount = bin(candidate).count("1")
        if popcount < 2:
            return False
        for divisor in range(2, int(popcount ** 0.5) + 1):
            if popcount % divisor == 0:
                return False
        return True

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_pernicious_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_pernicious`'s own body
minus its `value < 0` guard, since the scan never visits a negative
candidate — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice every recent `nth_*` task already makes.) Register the new dict
entry (search `"is_pernicious": _is_pernicious,`, add `"nth_pernicious":
_nth_pernicious,` directly after it, before `"is_palindrome_list":
_is_palindrome_list,`).

Acceptance criteria:
- `nth_pernicious(1);` through `nth_pernicious(10);` are `3, 5, 6, 7, 9,
  10, 11, 12, 13, 14` in order — the worked example above.
- `nth_pernicious(15);` is `21`, `nth_pernicious(20);` is `28`, and
  `nth_pernicious(50);` is `74` — further worked examples confirming
  the scan scales well past the first ten.
- For every `position` in `1..50`,
  `is_pernicious(nth_pernicious(position))` is `true` — the same
  self-consistency check every recent `nth_*` task's own test suite
  already runs against its predicate.
- `nth_pernicious(0);`, `nth_pernicious(-3);` both raise
  `CinderRuntimeError` matching `"nth_pernicious\(\) requires a
  positive integer, domain error"`.
- `nth_pernicious(true);` raises `CinderRuntimeError` matching
  `"nth_pernicious\(\) requires an int, got bool"`.
- `nth_pernicious("5");` raises `CinderRuntimeError` matching
  `"nth_pernicious\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_pernicious`,
search `def _is_pernicious`), `tests/test_builtins.py` (new `class
TestNthPernicious`, modeled on `class TestNthSmithNumber`, search that
name, for the test shapes above — place it near the existing `class
TestIsPernicious`, search that name). Once merged, `README.md`'s
existing `is_pernicious` bullet needs `nth_pernicious` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

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
