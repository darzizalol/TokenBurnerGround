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

## 1. Standard library: `median_absolute_deviation` — median-based measure of dispersion [claimed 2026-09-12T15:06:11Z]

Add a standalone list-transform-shaped statistic builtin directly
after `_median` (`cinder/builtins.py`, search `def _median`,
immediately before `def _midrange`) — the median-based sibling of
`variance`/`std_dev`: where those two measure dispersion around the
*mean* by squaring deviations, `median_absolute_deviation` measures
dispersion around the *median* by taking absolute deviations and
reducing with `median` again instead of squaring and averaging, which
makes it robust to outliers in a way `variance`/`std_dev` are not (one
huge value skews a mean-based measure far more than a median-based
one). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(median_absolute_deviation([1, 2, 3, 4, 5]));'
# -> <eval>:1:7: undefined name 'median_absolute_deviation' (did you mean 'median'?)
```

**What it does.** Given a non-empty list of numbers, compute `m =
median(list)`, then return `median([abs(x - m) for x in list])` — the
median of the absolute deviations from the list's own median. Unlike
`variance`/`std_dev`, a constant or single-element list is not a
division-by-zero case here (there is no division at all), so those
shapes return `0` rather than raising.

Worked examples (confirmed via direct computation of the algorithm
below):
- `median_absolute_deviation([1, 2, 3, 4, 5])` is `1` — median `3`,
  absolute deviations `[2, 1, 0, 1, 2]`, median of those (sorted `[0,
  1, 1, 2, 2]`) is `1`.
- `median_absolute_deviation([1, 2, 3, 4, 5, 6, 7, 8, 9])` is `2` —
  median `5`, absolute deviations sorted `[0, 1, 1, 2, 2, 3, 3, 4,
  4]`, median `2`.
- `median_absolute_deviation([1, 3, 5, 7, 9, 11])` is `3.0` — median
  `6.0` (even-length list, averages the two middle elements, same as
  `median` itself), absolute deviations sorted `[1, 1, 3, 3, 5, 5]`,
  median `(3 + 3) / 2 = 3.0`.
- `median_absolute_deviation([4, 4, 4])` is `0` — constant list, no
  raise (unlike `std_dev`, which raises further downstream builtins
  like `zscore`/`correlation` that divide by it).
- `median_absolute_deviation([5])` is `0` — single-element list.
- `median_absolute_deviation([]);` raises `CinderRuntimeError` — no
  elements to find a median of (same reason `median`/`midrange`
  reject an empty list).

Add directly after `_median` (search `def _median`, immediately before
`def _midrange`):
```python
def _median_absolute_deviation(arguments: list, line: int, column: int) -> object:
    _require_arity("median_absolute_deviation", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"median_absolute_deviation() requires a list, got {type_name(value)}",
            line, column,
        )
    if not value:
        raise CinderRuntimeError(
            "median_absolute_deviation() requires a non-empty list", line, column
        )
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"median_absolute_deviation() requires a list of numbers, got {type_name(element)}",
                line, column,
            )
    center = _median(arguments, line, column)
    deviations = [abs(element - center) for element in value]
    return _median([deviations], line, column)
```
(Calls `_median` directly, twice — once for the center, once for the
final reduction over deviations — rather than re-deriving the
sort-and-average-the-middle logic, so the two builtins' notion of
"median" can't drift apart; same reuse-the-sibling-builtin shape
`_correlation` uses for `_covariance`.) Register the new dict entry
(search `"median": _median,`, add `"median_absolute_deviation":
_median_absolute_deviation,` directly after it, before `"midrange":
_midrange,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `median_absolute_deviation([1, 2, 3, 4, 5])` is `1` and
  `median_absolute_deviation([1, 3, 5, 7, 9, 11])` is `3.0`.
- `median_absolute_deviation([4, 4, 4])` is `0` and
  `median_absolute_deviation([5])` is `0` — neither raises.
- `median_absolute_deviation([]);` raises `CinderRuntimeError` matching
  `"median_absolute_deviation\(\) requires a non-empty list"`.
- `median_absolute_deviation(123);` raises `CinderRuntimeError`
  matching `"median_absolute_deviation\(\) requires a list, got int"`.
- `median_absolute_deviation([1, "a"]);` raises `CinderRuntimeError`
  matching `"median_absolute_deviation\(\) requires a list of numbers,
  got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_median`, search
`def _median`), `tests/test_builtins.py` (new `class
TestMedianAbsoluteDeviation`, modeled on `class TestMedian`/`class
TestStdDev`, search either name, for the test shapes above — place it
near the existing `class TestMedian`). Once merged, `README.md`'s
builtins quick-reference list (search `median`, `midrange` sits right
after it) needs `median_absolute_deviation` added right after
`median`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `nth_perfect_number` — the k-th perfect number

Add directly after `_is_perfect_number` (`cinder/builtins.py`, search
`def _is_perfect_number`, immediately before `def
_is_practical_number`) — the value-returning sibling every other
divisor-sum classification predicate in this family already has
(`is_abundant`/`nth_abundant`, `is_deficient`/`nth_deficient`,
`is_practical_number`/`nth_practical_number`,
`is_semiperfect`/`nth_semiperfect`), the one member still missing it.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_perfect_number(1));'
# -> <eval>:1:7: undefined name 'nth_perfect_number' (did you mean 'nth_perfect_cube'?)
```

**What it does.** Given a positive integer `k`, return the `k`-th
perfect number (1-indexed) — a positive integer equal to the sum of
its own proper divisors, the same condition `_is_perfect_number`
already checks, applied here as a sequential scan exactly like
`_nth_abundant`/`_nth_deficient` already do for their own predicates.

**Performance note — read before implementing or writing tests.**
Perfect numbers are extraordinarily sparse: the first four are `6`,
`28`, `496`, `8128`, but the fifth is `33550336`. A sequential
trial-division scan (the same `O(sqrt(candidate))`-per-candidate
approach `nth_abundant`/`nth_deficient` already use) checking every
candidate up to that point is computationally infeasible to run in a
test — millions of candidates, each requiring a trial-division pass.
Cap every test and worked example at `k <= 4` (candidate `8128`, a few
thousand fast candidate checks); do **not** write or document a test
for `nth_perfect_number(5)` or any larger `k` — that is a known,
intentional scope boundary of this task, not an oversight to "complete."

Worked examples (confirmed via direct computation of the algorithm
below):
- `nth_perfect_number(1)` is `6`.
- `nth_perfect_number(2)` is `28`.
- `nth_perfect_number(3)` is `496`.
- `nth_perfect_number(4)` is `8128`.
- `nth_perfect_number(0);` raises `CinderRuntimeError` — domain error,
  same convention `nth_abundant(0)`/`nth_deficient(0)` already use.
- `nth_perfect_number(-1);` raises `CinderRuntimeError` — domain error.
- `nth_perfect_number(1.5);` raises `CinderRuntimeError` — not an int.
- `nth_perfect_number("a");` raises `CinderRuntimeError` — not an int.

Add directly after `_is_perfect_number` (search `def
_is_perfect_number`, immediately before `def _is_practical_number`):
```python
def _nth_perfect_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_perfect_number", arguments, 1, line, column)
    value = _require_int("nth_perfect_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_perfect_number() requires a positive integer, domain error", line, column
        )

    def _is_perfect_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        total = 1
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                total += divisor
                complement = candidate // divisor
                if complement != divisor and complement != candidate:
                    total += complement
        return total == candidate

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_perfect_candidate(candidate):
            count += 1
    return candidate
```
(`_is_perfect_candidate` mirrors `_is_perfect_number`'s own divisor-sum
loop exactly — including the `complement != candidate` guard, dead in
practice since `divisor` never reaches `1`, but kept for the same
reason `_is_perfect_number` has it: so the two functions' notion of
"perfect" can't silently drift apart — rather than the slightly
different loop shape `_nth_abundant`/`_nth_deficient` use.) Register
the new dict entry (search `"is_perfect_number": _is_perfect_number,`,
add `"nth_perfect_number": _nth_perfect_number,` directly after it,
before `"is_practical_number": _is_practical_number,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `nth_perfect_number(1)` is `6` through `nth_perfect_number(4)` is
  `8128`.
- `nth_perfect_number(0);` and `nth_perfect_number(-1);` both raise
  `CinderRuntimeError` matching `"nth_perfect_number\(\) requires a
  positive integer, domain error"`.
- `nth_perfect_number(1.5);` and `nth_perfect_number("a");` both raise
  `CinderRuntimeError` matching `"nth_perfect_number\(\) requires an
  int, got (float|string)"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- No test calls `nth_perfect_number(5)` or higher — see the performance
  note above.
- Full test suite passes (and finishes in normal time — a test that
  hangs or takes unusually long past this task's change is a sign the
  `k <= 4` cap above was violated).

Likely files: `cinder/builtins.py` (directly after `_is_perfect_number`,
search `def _is_perfect_number`), `tests/test_builtins.py` (new `class
TestNthPerfectNumber`, modeled on `class TestNthAbundant`/`class
TestNthDeficient`, search either name, for the test shapes above —
place it near the existing `class TestIsPerfectNumber`). Once merged,
`README.md`'s builtins quick-reference list (search
`is_perfect_number`) needs `nth_perfect_number` added right after it,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_weird_number` — the k-th weird number

Add directly after `_is_weird_number` (`cinder/builtins.py`, search
`def _is_weird_number`, immediately before `def _is_semiperfect`) —
the same value-returning-sibling gap task 2 above closes for
`is_perfect_number`, here for `is_weird_number` (abundant but not
semiperfect — no subset of its proper divisors sums to it exactly).
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_weird_number(1));'
# -> <eval>:1:7: undefined name 'nth_weird_number' (did you mean 'is_weird_number'?)
```

**What it does.** Given a positive integer `k`, return the `k`-th
weird number (1-indexed) — a positive integer whose proper divisors
sum to more than itself (abundant) but no subset of them sums to it
exactly (not semiperfect) — the same condition `_is_weird_number`
already checks, applied here as a sequential scan exactly like
`_nth_semiperfect` already does for its own predicate. Unlike task 2's
perfect numbers, weird numbers are dense enough close to their start
for a sequential scan to stay fast well past `k = 6` — the first six
are `70`, `836`, `4030`, `5830`, `7192`, `7912`, all comfortably small.

Worked examples (confirmed via direct computation of the algorithm
below):
- `nth_weird_number(1)` is `70` — the smallest weird number.
- `nth_weird_number(2)` is `836`.
- `nth_weird_number(3)` is `4030`.
- `nth_weird_number(4)` is `5830`.
- `nth_weird_number(5)` is `7192`.
- `nth_weird_number(6)` is `7912`.
- `nth_weird_number(0);` raises `CinderRuntimeError` — domain error,
  same convention `nth_semiperfect(0)` already uses.
- `nth_weird_number(-1);` raises `CinderRuntimeError` — domain error.
- `nth_weird_number(1.5);` raises `CinderRuntimeError` — not an int.
- `nth_weird_number("a");` raises `CinderRuntimeError` — not an int.

Add directly after `_is_weird_number` (search `def _is_weird_number`,
immediately before `def _is_semiperfect`):
```python
def _nth_weird_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_weird_number", arguments, 1, line, column)
    value = _require_int("nth_weird_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_weird_number() requires a positive integer, domain error", line, column
        )

    def _is_weird_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        divisors = [1]
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                divisors.append(divisor)
                complement = candidate // divisor
                if complement != divisor:
                    divisors.append(complement)
        if sum(divisors) <= candidate:
            return False
        reachable = {0}
        for divisor in divisors:
            reachable |= {
                total + divisor for total in reachable if total + divisor <= candidate
            }
        return candidate not in reachable

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_weird_candidate(candidate):
            count += 1
    return candidate
```
(`_is_weird_candidate` mirrors `_is_weird_number`'s own
divisor-collection-then-subset-sum-reachability logic exactly, so the
two functions' notion of "weird" can't silently drift apart — same
reuse-the-sibling-predicate's-exact-logic discipline task 2 above uses
for `_is_perfect_number`.) Register the new dict entry (search
`"is_weird_number": _is_weird_number,`, add `"nth_weird_number":
_nth_weird_number,` directly after it, before `"is_semiperfect":
_is_semiperfect,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `nth_weird_number(1)` is `70` through `nth_weird_number(6)` is
  `7912`.
- `nth_weird_number(0);` and `nth_weird_number(-1);` both raise
  `CinderRuntimeError` matching `"nth_weird_number\(\) requires a
  positive integer, domain error"`.
- `nth_weird_number(1.5);` and `nth_weird_number("a");` both raise
  `CinderRuntimeError` matching `"nth_weird_number\(\) requires an
  int, got (float|string)"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_weird_number`,
search `def _is_weird_number`), `tests/test_builtins.py` (new `class
TestNthWeirdNumber`, modeled on `class TestNthSemiperfect`, search that
name, for the test shapes above — place it near the existing `class
TestIsWeirdNumber`). Once merged, `README.md`'s builtins
quick-reference list (search `is_weird_number`) needs
`nth_weird_number` added right after it, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass,
not this task.

---

## 4. Standard library: `nth_armstrong` — the k-th Armstrong (narcissistic) number

Add directly after `_is_armstrong` (`cinder/builtins.py`, search `def
_is_armstrong`, immediately before `def _is_disarium`) — the same
value-returning-sibling gap tasks 2 and 3 above close for
`is_perfect_number`/`is_weird_number`, here for `is_armstrong`: a
positive integer equal to the sum of its own digits each raised to the
power of the digit count (`153 = 1^3 + 5^3 + 3^3`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_armstrong(1));'
# -> <eval>:1:7: undefined name 'nth_armstrong' (did you mean 'is_armstrong'?)
```

**What it does.** Given a positive integer `k`, return the `k`-th
Armstrong number (1-indexed, starting from `0`) — the same condition
`_is_armstrong` already checks, applied here as a sequential scan
exactly like `_nth_perfect_number`/`_nth_weird_number` already do for
their own predicates. Unlike task 2's perfect numbers, Armstrong
numbers are cheap to test (a digit-sum-of-powers check, not trial
division) and stay dense enough through this task's range for a plain
scan to finish instantly — the single-digit numbers `0`-`9` are all
trivially Armstrong numbers (any one digit raised to the power `1` is
itself), then the next one doesn't appear until `153`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `nth_armstrong(1)` is `0`.
- `nth_armstrong(2)` is `1`.
- `nth_armstrong(10)` is `9` — the last of the ten trivial single-digit
  Armstrong numbers.
- `nth_armstrong(11)` is `153` — the first multi-digit Armstrong
  number.
- `nth_armstrong(12)` is `370`.
- `nth_armstrong(13)` is `371`.
- `nth_armstrong(14)` is `407`.
- `nth_armstrong(15)` is `1634`.
- `nth_armstrong(0);` raises `CinderRuntimeError` — domain error, same
  convention `nth_perfect_number(0)`/`nth_weird_number(0)` already use.
- `nth_armstrong(-1);` raises `CinderRuntimeError` — domain error.
- `nth_armstrong(1.5);` raises `CinderRuntimeError` — not an int.
- `nth_armstrong("a");` raises `CinderRuntimeError` — not an int.

Add directly after `_is_armstrong` (search `def _is_armstrong`,
immediately before `def _is_disarium`):
```python
def _nth_armstrong(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_armstrong", arguments, 1, line, column)
    value = _require_int("nth_armstrong", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_armstrong() requires a positive integer, domain error", line, column
        )

    def _is_armstrong_candidate(candidate: int) -> bool:
        digits = str(candidate)
        power = len(digits)
        return sum(int(digit) ** power for digit in digits) == candidate

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_armstrong_candidate(candidate):
            count += 1
    return candidate
```
(`_is_armstrong_candidate` mirrors `_is_armstrong`'s own digit-power-sum
check exactly — including counting `0` as the first Armstrong number,
same as `_is_armstrong(0)` already returns `True` — so the two
functions' notion of "Armstrong" can't silently drift apart; same
reuse-the-sibling-predicate's-exact-logic discipline tasks 2/3 above
use for `_is_perfect_number`/`_is_weird_number`. Starts `candidate` at
`-1`, one below `_is_perfect_number`/`_is_weird_number`'s starting
point of `0`, since `0` itself is a valid Armstrong number here and
must be reachable as `nth_armstrong(1)`.) Register the new dict entry
(search `"is_armstrong": _is_armstrong,`, add `"nth_armstrong":
_nth_armstrong,` directly after it, before `"is_disarium":
_is_disarium,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `nth_armstrong(1)` is `0`, `nth_armstrong(10)` is `9`, and
  `nth_armstrong(15)` is `1634`.
- `nth_armstrong(0);` and `nth_armstrong(-1);` both raise
  `CinderRuntimeError` matching `"nth_armstrong\(\) requires a
  positive integer, domain error"`.
- `nth_armstrong(1.5);` and `nth_armstrong("a");` both raise
  `CinderRuntimeError` matching `"nth_armstrong\(\) requires an int,
  got (float|string)"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_armstrong`,
search `def _is_armstrong`), `tests/test_builtins.py` (new `class
TestNthArmstrong`, modeled on `class TestNthPerfectNumber`/`class
TestNthWeirdNumber` from tasks 2/3 above, search either name, for the
test shapes above — place it near the existing `class
TestIsArmstrong`). Once merged, `README.md`'s builtins quick-reference
list (search `is_armstrong`) needs `nth_armstrong` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 5. Standard library: `percentile` — p-th percentile of a numeric list (linear interpolation)

Add directly after `_midrange` (`cinder/builtins.py`, search `def
_midrange`, immediately before `def _population_variance`) — a real
gap in the `mean`/`median`/`midrange`/`variance`/`std_dev`/`mode`
statistics cluster: none of those existing builtins let a caller ask
for an arbitrary rank between minimum and maximum, only the fixed 0th/
50th/100th-percentile-shaped ones (`min`/`max` from elsewhere,
`median`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(percentile([1, 2, 3, 4, 5], 50));'
# -> <eval>:1:7: undefined name 'percentile' (did you mean 'midrange'?)
```

**What it does.** Given a non-empty list of numbers and a rank `p` in
`[0, 100]`, return the `p`-th percentile using linear interpolation
between the two nearest ranks (the same method `numpy.percentile`
calls `"linear"`, its default): sort the list, compute `index = (p /
100) * (n - 1)` (0-indexed, `n` = list length), then if `index` lands
exactly on an element return it directly, otherwise linearly
interpolate between `ordered[floor(index)]` and `ordered[ceil(index)]`
by the fractional part of `index`. This makes `percentile(list, 50)`
always exactly equal `median(list)`, for both odd- and even-length
lists — a useful cross-check when testing.

Worked examples (confirmed via direct computation of the algorithm
below):
- `percentile([1, 2, 3, 4, 5], 50)` is `3` — `index = 2`, lands exactly
  on `ordered[2]`.
- `percentile([1, 2, 3, 4, 5], 25)` is `2` — `index = 1`.
- `percentile([1, 2, 3, 4, 5], 75)` is `4` — `index = 3`.
- `percentile([1, 2, 3, 4, 5], 0)` is `1` and `percentile([1, 2, 3, 4,
  5], 100)` is `5` — the endpoints.
- `percentile([1, 2, 3, 4], 50)` is `2.5` — `index = 1.5`, interpolates
  halfway between `ordered[1] = 2` and `ordered[2] = 3`; matches
  `median([1, 2, 3, 4])` exactly, as the cross-check above predicts.
- `percentile([5], 37)` is `5` — single-element list, every percentile
  returns the one element; not a division-by-zero case (`n - 1 = 0`
  makes `index` always `0` regardless of `p`).
- `percentile([], 50);` raises `CinderRuntimeError` — no elements.
- `percentile([1, 2, 3], 150);` and `percentile([1, 2, 3], -5);` both
  raise `CinderRuntimeError` — `p` outside `[0, 100]` is a domain
  error, not clamped.

Add directly after `_midrange` (search `def _midrange`, immediately
before `def _population_variance`):
```python
def _percentile(arguments: list, line: int, column: int) -> object:
    _require_arity("percentile", arguments, 2, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"percentile() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("percentile() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"percentile() requires a list of numbers, got {type_name(element)}", line, column
            )
    rank = arguments[1]
    if not _is_numeric(rank):
        raise CinderRuntimeError(
            f"percentile() requires a number for its second argument, got {type_name(rank)}",
            line, column,
        )
    if rank < 0 or rank > 100:
        raise CinderRuntimeError(
            "percentile() requires a number between 0 and 100 for its second argument, domain error",
            line, column,
        )
    ordered = sorted(value)
    index = (rank / 100) * (len(ordered) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
```
(Reuses `_is_numeric`/`type_name`/`_require_arity` the same way every
sibling statistics builtin does; `math.floor`/`math.ceil` are already
imported in this module for `nth_perfect_number`/`nth_weird_number`.)
Register the new dict entry (search `"midrange": _midrange,`, add
`"percentile": _percentile,` directly after it, before `"variance":
_variance,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `percentile([1, 2, 3, 4], 50)` is `2.5` and `percentile([5], 37)` is
  `5`.
- `percentile(list, 50)` equals `median(list)` exactly for at least one
  odd-length and one even-length list (the cross-check above).
- `percentile([]` , `50);` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a non-empty list"`.
- `percentile(123, 50);` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a list, got int"`.
- `percentile([1, "a"], 50);` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a list of numbers, got string"`.
- `percentile([1, 2, 3], "a");` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a number for its second argument, got
  string"`.
- `percentile([1, 2, 3], 150);` and `percentile([1, 2, 3], -5);` both
  raise `CinderRuntimeError` matching `"percentile\(\) requires a
  number between 0 and 100.*domain error"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_midrange`, search
`def _midrange`), `tests/test_builtins.py` (new `class TestPercentile`,
modeled on `class TestMedian`/`class TestMidrange`, search either name,
for the test shapes above — place it near the existing `class
TestMidrange`). Once merged, `README.md`'s builtins quick-reference
list (search `midrange`) needs `percentile` added right after it, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's
next grooming pass, not this task.

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
