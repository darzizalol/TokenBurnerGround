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

## 1. Standard library: `nth_emirp` — emirp found at a 1-indexed position [claimed 2026-09-06T20:25:26Z]

Build: `is_emirp` (`cinder/builtins.py`, search `def _is_emirp`: a prime
whose decimal-digit reversal is a *different* prime, e.g. `13` is an emirp
since `31` is prime and `31 != 13`, but a palindromic prime like `11` is
not) has no value-returning `nth_*` sibling, the same gap
`nth_smith_number`/`nth_carmichael_number`/`nth_twin_prime`/
`nth_self_number` (all already merged, `#406`/`#408`/`#410`/`#411`)
already close for their own predicates. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(nth_emirp(1));'
# -> <eval>:1:7: undefined name 'nth_emirp' (did you mean 'is_emirp'?)
```

Worked examples: the first twenty emirps (OEIS A006567, confirmed by
scanning with `is_emirp` directly) are `13, 17, 31, 37, 71, 73, 79, 97,
107, 113, 149, 157, 167, 179, 199, 311, 337, 347, 359, 389`, so
`nth_emirp(1)` is `13` and `nth_emirp(10)` is `113`. The 50th is `1193`.

Add directly after `_is_emirp` (search `def _is_emirp`, immediately
before `def _is_circular_prime`) — keeps the value-returning helper next
to the predicate it mirrors, matching where `nth_twin_prime` itself sits
right after `is_twin_prime`:
```python
def _nth_emirp(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_emirp", arguments, 1, line, column)
    value = _require_int("nth_emirp", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_emirp() requires a positive integer, domain error",
            line, column,
        )

    def _trial_division_is_prime(candidate: int) -> bool:
        if candidate < 2:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return False
        return True

    def _is_emirp_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        if not _trial_division_is_prime(candidate):
            return False
        reversed_candidate = int(str(candidate)[::-1])
        if reversed_candidate == candidate:
            return False
        return _trial_division_is_prime(reversed_candidate)

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_emirp_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_twin_prime`/`_nth_carmichael_number`, with the
inner candidate check copied verbatim from `_is_emirp`'s own body instead
of calling `_is_emirp` directly — the same "duplicate the tiny predicate
body instead of a redundant `_require_arity`/`_require_int` round-trip
per candidate" choice every recent `nth_*` task already makes.) Register
the new dict entry (search `"is_emirp": _is_emirp,`, add `"nth_emirp":
_nth_emirp,` directly after it, before `"is_circular_prime":
_is_circular_prime,`).

Acceptance criteria:
- `nth_emirp(1);` through `nth_emirp(15);` are `13, 17, 31, 37, 71, 73,
  79, 97, 107, 113, 149, 157, 167, 179, 199` in order — the worked
  example above.
- `nth_emirp(20);` is `389` and `nth_emirp(50);` is `1193` — further
  worked examples confirming the scan scales past the first twenty.
- For every `position` in `1..50`, `is_emirp(nth_emirp(position))` is
  `true` — the same self-consistency check `nth_smith_number`/
  `nth_carmichael_number`/`nth_twin_prime`/`nth_self_number`'s own test
  suites already run against their predicates.
- `nth_emirp(0);`, `nth_emirp(-3);` both raise `CinderRuntimeError`
  matching `"nth_emirp\(\) requires a positive integer, domain error"`.
- `nth_emirp(true);` raises `CinderRuntimeError` matching
  `"nth_emirp\(\) requires an int, got bool"`.
- `nth_emirp("5");` raises `CinderRuntimeError` matching
  `"nth_emirp\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_emirp`, search
`def _is_emirp`), `tests/test_builtins.py` (new `class TestNthEmirp`,
modeled on `class TestNthTwinPrime`, search that name, for the test
shapes above — place it near the existing `class TestIsEmirp`, search
that name). Once merged, `README.md`'s existing `is_emirp` bullet needs
`nth_emirp` added right after it, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `nth_polydivisible` — polydivisible number found at a 1-indexed position

Build: `is_polydivisible` (`cinder/builtins.py`, search `def
_is_polydivisible`: a non-negative integer whose every digit-prefix of
length `i` is divisible by `i`, e.g. `1230` is polydivisible since `1 %
1 == 0`, `12 % 2 == 0`, `123 % 3 == 0`, `1230 % 4 == 0`) has no
value-returning `nth_*` sibling, the same gap `nth_smith_number`/
`nth_carmichael_number`/`nth_twin_prime`/`nth_self_number` (all already
merged, `#406`/`#408`/`#410`/`#411`), and
`nth_emirp` (task 1 above) already close for their own predicates.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_polydivisible(1));'
# -> <eval>:1:7: undefined name 'nth_polydivisible' (did you mean
#    'is_polydivisible'?)
```

Worked examples: the first twenty polydivisible numbers (confirmed by
scanning with `is_polydivisible` directly) are `0, 1, 2, 3, 4, 5, 6, 7,
8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28`, so `nth_polydivisible(1)`
is `0` and `nth_polydivisible(10)` is `9`. The 20th is `28`, the 50th is
`88`.

Like `nth_self_number` (already merged, `#411`), position `1` maps to candidate `0`, not `1`:
every single digit `0`-`9` is trivially polydivisible (`is_polydivisible`'s
own `range(1, len(digits) + 1)` loop only ever checks prefix length `1`
for a one-digit number, and any integer mod `1` is `0`), and `0` is the
smallest value `is_polydivisible` ever accepts (it returns `false`
outright for negative input, per its own `if value < 0: return False`
guard), so the scan must start *before* `0` (`candidate = -1`,
incremented before the first check) to avoid silently excluding it from
the sequence forever.

Add directly after `_is_polydivisible` (search `def _is_polydivisible`,
immediately before `def _is_pandigital`) — keeps the value-returning
helper next to the predicate it mirrors:
```python
def _nth_polydivisible(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_polydivisible", arguments, 1, line, column)
    value = _require_int("nth_polydivisible", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_polydivisible() requires a positive integer, domain error",
            line, column,
        )

    def _is_polydivisible_candidate(candidate: int) -> bool:
        digits = str(candidate)
        return all(
            int(digits[:i]) % i == 0 for i in range(1, len(digits) + 1)
        )

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_polydivisible_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_polydivisible`'s own
body minus its `value < 0` guard, since the scan never visits a negative
candidate — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice every recent `nth_*` task already makes.) Register the new dict
entry (search `"is_polydivisible": _is_polydivisible,`, add
`"nth_polydivisible": _nth_polydivisible,` directly after it, before
`"is_pandigital": _is_pandigital,`).

Acceptance criteria:
- `nth_polydivisible(1);` through `nth_polydivisible(10);` are `0, 1, 2,
  3, 4, 5, 6, 7, 8, 9` in order — the worked example above.
- `nth_polydivisible(20);` is `28` and `nth_polydivisible(50);` is `88`
  — further worked examples confirming the scan scales past the first
  ten.
- For every `position` in `1..50`,
  `is_polydivisible(nth_polydivisible(position))` is `true` — the same
  self-consistency check `nth_smith_number`/`nth_carmichael_number`/
  `nth_twin_prime`/`nth_self_number`/`nth_emirp`'s own test suites
  already run against their predicates.
- `nth_polydivisible(0);`, `nth_polydivisible(-3);` both raise
  `CinderRuntimeError` matching `"nth_polydivisible\(\) requires a
  positive integer, domain error"` — note this domain check is on the
  *position* argument, unrelated to `0` being a valid *polydivisible
  number* itself (`nth_polydivisible(1)` legitimately returns `0`).
- `nth_polydivisible(true);` raises `CinderRuntimeError` matching
  `"nth_polydivisible\(\) requires an int, got bool"`.
- `nth_polydivisible("5");` raises `CinderRuntimeError` matching
  `"nth_polydivisible\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_polydivisible`,
search `def _is_polydivisible`), `tests/test_builtins.py` (new `class
TestNthPolydivisible`, modeled on `class TestIsPolydivisible`, search
that name, for the test shapes above — place it near that existing
class). Once merged, `README.md`'s existing `is_polydivisible` bullet
needs `nth_polydivisible` added right after it, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `nth_trimorphic_number` — trimorphic number found at a 1-indexed position

Build: `is_trimorphic_number` (`cinder/builtins.py`, search `def
_is_trimorphic_number`: a non-negative integer whose cube ends in the
number itself, e.g. `24 ** 3 = 13824`, which ends in `24`) has no
value-returning `nth_*` sibling, the same gap `nth_smith_number`/
`nth_carmichael_number`/`nth_twin_prime`/`nth_self_number` (all already
merged, `#406`/`#408`/`#410`/`#411`),
`nth_emirp` (task 1 above), and `nth_polydivisible` (task 2 above)
already close for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_trimorphic_number(1));'
# -> <eval>:1:7: undefined name 'nth_trimorphic_number' (did you mean
#    'is_trimorphic_number'?)
```

Worked examples: the first twenty trimorphic numbers (confirmed by
scanning with `is_trimorphic_number` directly) are `0, 1, 4, 5, 6, 9,
24, 25, 49, 51, 75, 76, 99, 125, 249, 251, 375, 376, 499, 501`, so
`nth_trimorphic_number(1)` is `0` and `nth_trimorphic_number(10)` is
`51`. The 15th is `249`, the 20th is `501`, the 50th is `109376`.

Like `nth_self_number` (already merged, `#411`) and `nth_polydivisible`
(task 2 above), position `1` maps to candidate `0`, not `1`: `is_trimorphic_number(0)`
is `true` (`str(0 ** 3)` is `"0"`, which trivially ends with `"0"`), and
`0` is the smallest value `is_trimorphic_number` ever accepts (it
returns `false` outright for negative input, per its own `if value < 0:
return False` guard), so the scan must start *before* `0` (`candidate =
-1`, incremented before the first check) to avoid silently excluding it
from the sequence forever. Unlike `nth_self_number`/`nth_polydivisible`
though, not every single digit qualifies — `str(d ** 3)` only ends in
`d` for `d` in `{0, 1, 4, 5, 6, 9}` (`2 ** 3 = 8`, `3 ** 3 = 27`, `7 **
3 = 343`, `8 ** 3 = 512` all end in a different last digit), which is
why `2`, `3`, `7`, `8` are absent from the worked-example list above.

Add directly after `_is_trimorphic_number` (search `def
_is_trimorphic_number`, immediately before `def _is_keith_number`) —
keeps the value-returning helper next to the predicate it mirrors:
```python
def _nth_trimorphic_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_trimorphic_number", arguments, 1, line, column)
    value = _require_int("nth_trimorphic_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_trimorphic_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_trimorphic_number_candidate(candidate: int) -> bool:
        return str(candidate ** 3).endswith(str(candidate))

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_trimorphic_number_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_trimorphic_number`'s
own body minus its `value < 0` guard, since the scan never visits a
negative candidate — the same "duplicate the tiny predicate body
instead of a redundant `_require_arity`/`_require_int` round-trip per
candidate" choice every recent `nth_*` task already makes.) Register
the new dict entry (search `"is_trimorphic_number":
_is_trimorphic_number,`, add `"nth_trimorphic_number":
_nth_trimorphic_number,` directly after it, before `"is_keith_number":
_is_keith_number,`).

Acceptance criteria:
- `nth_trimorphic_number(1);` through `nth_trimorphic_number(10);` are
  `0, 1, 4, 5, 6, 9, 24, 25, 49, 51` in order — the worked example above.
- `nth_trimorphic_number(15);` is `249`, `nth_trimorphic_number(20);` is
  `501`, and `nth_trimorphic_number(50);` is `109376` — further worked
  examples confirming the scan scales well past the first ten.
- For every `position` in `1..50`,
  `is_trimorphic_number(nth_trimorphic_number(position))` is `true` —
  the same self-consistency check `nth_smith_number`/
  `nth_carmichael_number`/`nth_twin_prime`/`nth_self_number`/
  `nth_polydivisible`'s own test suites already run against their
  predicates.
- `nth_trimorphic_number(0);`, `nth_trimorphic_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_trimorphic_number\(\) requires a
  positive integer, domain error"` — note this domain check is on the
  *position* argument, unrelated to `0` being a valid *trimorphic
  number* itself (`nth_trimorphic_number(1)` legitimately returns `0`).
- `nth_trimorphic_number(true);` raises `CinderRuntimeError` matching
  `"nth_trimorphic_number\(\) requires an int, got bool"`.
- `nth_trimorphic_number("5");` raises `CinderRuntimeError` matching
  `"nth_trimorphic_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after
`_is_trimorphic_number`, search `def _is_trimorphic_number`),
`tests/test_builtins.py` (new `class TestNthTrimorphicNumber`, modeled
on `class TestNthCarmichaelNumber`, search that name, for the test shapes
above — place it near the existing `class TestIsTrimorphicNumber`,
search that name). Once merged, `README.md`'s existing
`is_trimorphic_number` bullet needs `nth_trimorphic_number` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `nth_circular_prime` — circular prime found at a 1-indexed position

Build: `is_circular_prime` (`cinder/builtins.py`, search `def
_is_circular_prime`: a prime where every rotation of its decimal digits
is also prime, e.g. `197` is circular since `197`, `971`, and `719` are
all prime) has no value-returning `nth_*` sibling, the same gap
`nth_smith_number`/`nth_carmichael_number`/`nth_twin_prime`/`nth_self_number`
(all already merged, `#406`/`#408`/`#410`/`#411`),
`nth_emirp` (task 1 above), and `nth_polydivisible`
(task 2 above) already close for their own predicates. Verify the gap:
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

## 5. Standard library: `nth_sad_number` — sad number found at a 1-indexed position

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

## 6. Standard library: `nth_vampire_number` — vampire number found at a 1-indexed position

Build: `is_vampire_number` (`cinder/builtins.py`, search `def
_is_vampire_number`: an even-digit-count integer whose decimal digits
can be rearranged into two equal-length "fangs" that multiply back to
it, e.g. `1260 = 21 * 60` and `sorted("1260") == sorted("2160")`, with
both-fangs-ending-in-zero pairs excluded as trivial) has no
value-returning `nth_*` sibling, the same gap `nth_smith_number`/
`nth_carmichael_number`/`nth_twin_prime`/`nth_self_number` (all already
merged, `#406`/`#408`/`#410`/`#411`), `nth_emirp` (task 1),
`nth_polydivisible` (task 2), `nth_trimorphic_number` (task 3), and
`nth_circular_prime` (task 4) already close for their own predicates.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_vampire_number(1));'
# -> <eval>:1:7: undefined name 'nth_vampire_number' (did you mean
#    'is_vampire_number'?)
```

Worked examples: the first twenty vampire numbers (confirmed by
scanning with `is_vampire_number` directly) are `1260, 1395, 1435,
1530, 1827, 2187, 6880, 102510, 104260, 105210, 105264, 105750, 108135,
110758, 115672, 116725, 117067, 118440, 120600, 123354`, so
`nth_vampire_number(1)` is `1260` and `nth_vampire_number(10)` is
`105210`. The 15th is `115672`, the 20th is `123354`, the 50th is
`163944`.

Unlike `nth_self_number`/`nth_polydivisible`/`nth_trimorphic_number`,
there is no `0`-as-valid-candidate quirk here — `is_vampire_number`
rejects anything under 4 digits outright (`digit_count < 4` in its own
body), so the scan can start at `candidate = 0` same as the
prime-based `nth_*` tasks. But like `nth_circular_prime`
(task 4), vampire numbers thin out: the fang-search inside
`is_vampire_number` is itself an `O(10^(digits/2))` loop, so a single
`nth_vampire_number(50)` call is measurably slower (~3 seconds observed
locally) than the fast `nth_*` builtins in this backlog. Keep the
self-consistency acceptance check below at `1..15` rather than the
`1..50` other recent `nth_*` tasks use — repeating the scan from
scratch 50 times (as that check does) would multiply into an
unacceptably slow test suite, the same tradeoff `nth_carmichael_number`
(`#408`) and `nth_circular_prime` (task 4) already made for the same
reason.

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
(Identical shape to `_nth_circular_prime`, with the inner candidate
check copied verbatim from `_is_vampire_number`'s own body instead of
calling `_is_vampire_number` directly — the same "duplicate the tiny
predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice every recent `nth_*` task already
makes.) Register the new dict entry (search `"is_vampire_number":
_is_vampire_number,`, add `"nth_vampire_number": _nth_vampire_number,`
directly after it, before `"num_divisors": _num_divisors,`).

Acceptance criteria:
- `nth_vampire_number(1);` through `nth_vampire_number(10);` are `1260,
  1395, 1435, 1530, 1827, 2187, 6880, 102510, 104260, 105210` in order
  — the worked example above.
- `nth_vampire_number(15);` is `115672`, `nth_vampire_number(20);` is
  `123354`, and `nth_vampire_number(50);` is `163944` — further worked
  examples confirming the scan scales past the first ten (the `50` case
  is expected to take a few seconds — see the performance note above,
  not a bug).
- For every `position` in `1..15`,
  `is_vampire_number(nth_vampire_number(position))` is `true` — a
  reduced-range self-consistency check (see the performance note above
  for why `1..15` and not `1..50` here), the same style
  `nth_carmichael_number`/`nth_circular_prime`'s own test suites already
  use for the same reason.
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

Likely files: `cinder/builtins.py` (directly after
`_is_vampire_number`, search `def _is_vampire_number`),
`tests/test_builtins.py` (new `class TestNthVampireNumber`, modeled on
`class TestNthCircularPrime`, search that name, for the test shapes and
reduced-range self-consistency check above — place it near the
existing `class TestIsVampireNumber`, search that name). Once merged,
`README.md`'s existing `is_vampire_number` bullet needs
`nth_vampire_number` added right after it, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass,
not this task.

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
