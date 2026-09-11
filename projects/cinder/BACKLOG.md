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

## 1. Standard library: `diff` — successive differences of a numeric list

Add a standalone list-transform builtin directly after `_cumsum`
(`cinder/builtins.py`, search `def _cumsum`, immediately before `def
_product`) — the inverse-shaped sibling of `cumsum`: where `cumsum`
turns a list into its running totals, `diff` turns a list into the
gaps between consecutive elements (`cumsum(diff(list))[i] + list[0]`
reconstructs `list[i + 1]` for every `i`, though the task itself only
needs the forward computation below, not that identity). Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(diff([1, 3, 6, 10]));'
# -> <eval>:1:7: undefined name 'diff'
```

**What it does.** Given a list of numbers, return a new list one
element shorter where each element is the difference between a pair of
consecutive elements in the input — `result[i] = list[i + 1] -
list[i]`. A list with fewer than two elements (empty or single-element)
has no consecutive pair to difference, so it returns `[]`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `diff([1, 3, 6, 10])` is `[2, 3, 4]`.
- `diff([])` is `[]` — no elements, no consecutive pair.
- `diff([5])` is `[]` — one element, still no consecutive pair.
- `diff([5, 5, 5])` is `[0, 0]` — a constant list differences to all
  zeros.
- `diff([10, 7, 3])` is `[-3, -4]` — a decreasing sequence differences
  to negative values.
- `diff([1.5, 3, 4.5])` is `[1.5, 1.5]` (mixed int/float elements,
  ordinary numeric subtraction — same as `cumsum`/`sum`).
- `diff([1, -2, 3])` is `[-3, 5]` — negative elements subtract as
  usual.

Add directly after `_cumsum` (search `def _cumsum`, immediately before
`def _product`) — keeps the new differencing builtin next to the
running-total sibling it inverts:
```python
def _diff(arguments: list, line: int, column: int) -> object:
    _require_arity("diff", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"diff() requires a list, got {type_name(value)}", line, column
        )
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"diff() requires a list of numbers, got {type_name(element)}", line, column
            )
    result = []
    for i in range(len(value) - 1):
        result.append(value[i + 1] - value[i])
    return result
```
(Same validate-then-walk shape as `_cumsum` — search `def _cumsum` —
just subtracting each element from its successor instead of
accumulating a running total, and producing one fewer element than the
input instead of the same count.) Register the new dict entry (search
`"cumsum": _cumsum,`, add `"diff": _diff,` directly after it, before
`"product": _product,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `diff([1, 3, 6, 10])` is `[2, 3, 4]` and `diff([1.5, 3, 4.5])` is
  `[1.5, 1.5]`.
- `diff([]);` is `[]` and `diff([5]);` is `[]` — the empty-list and
  single-element cases.
- `diff([10, 7, 3]);` is `[-3, -4]` — the decreasing-sequence case.
- `diff(123);` raises `CinderRuntimeError` matching `"diff\(\) requires
  a list, got int"`.
- `diff([1, "a"]);` raises `CinderRuntimeError` matching `"diff\(\)
  requires a list of numbers, got string"` (mirror `cumsum`'s own
  non-numeric-element test for the exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_cumsum`, search
`def _cumsum`), `tests/test_builtins.py` (new `class TestDiff`, modeled
on `class TestCumsum`, search that name, for the test shapes above —
place it near the existing `class TestCumsum`). Once merged,
`README.md`'s existing `cumsum` bullet needs `diff` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `midrange` — average of a numeric list's minimum and maximum

Add a standalone list-statistic builtin directly after `_median`
(`cinder/builtins.py`, search `def _median`, immediately before `def
_population_variance`) — a third measure of central tendency sitting
next to `mean`/`median`, simpler than either: the average of a list's
smallest and largest values. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(midrange([1, 2, 10]));'
# -> <eval>:1:7: undefined name 'midrange'
```

**What it does.** Given a non-empty list of numbers, return
`(min(list) + max(list)) / 2` — the point halfway between the list's
smallest and largest elements. Unlike `mean`/`median`, a single pass
over the list only needs its extremes, not every element's
contribution. An empty list has no minimum or maximum, so it raises,
same as `mean`/`median` do for the same reason.

Worked examples (confirmed via direct computation of the algorithm
below):
- `midrange([1, 2, 10])` is `5.5` — halfway between `1` and `10`.
- `midrange([5])` is `5.0` — a single-element list's min and max are
  both itself, so the midrange is that element (as a float, dividing by
  2).
- `midrange([4, 4, 4])` is `4.0` — a constant list's min and max are
  equal, so the midrange is that constant.
- `midrange([-3, 7])` is `2.0` — negative elements participate in
  min/max normally.
- `midrange([1.5, 2, 8.5])` is `5.0` (mixed int/float elements,
  ordinary numeric comparison and division — same as `mean`/`median`).
- `midrange([]);` raises `CinderRuntimeError` — no elements, no
  minimum or maximum to average.

Add directly after `_median` (search `def _median`, immediately before
`def _population_variance`) — keeps the new midpoint statistic next to
the central-tendency builtins it sits alongside:
```python
def _midrange(arguments: list, line: int, column: int) -> object:
    _require_arity("midrange", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"midrange() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("midrange() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"midrange() requires a list of numbers, got {type_name(element)}", line, column
            )
    return (min(value) + max(value)) / 2
```
(Same validate-then-reduce shape as `_mean`/`_median` — search either —
just averaging the extremes instead of summing every element or
sorting.) Register the new dict entry (search `"median": _median,`,
add `"midrange": _midrange,` directly after it, before `"variance":
_variance,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `midrange([1, 2, 10])` is `5.5` and `midrange([1.5, 2, 8.5])` is
  `5.0`.
- `midrange([5]);` is `5.0` and `midrange([4, 4, 4]);` is `4.0` — the
  single-element and constant-list cases.
- `midrange([-3, 7]);` is `2.0` — the negative-element case.
- `midrange([]);` raises `CinderRuntimeError` matching
  `"midrange\(\) requires a non-empty list"` (mirror `mean`'s/
  `median`'s own empty-list test for the exact message shape).
- `midrange(123);` raises `CinderRuntimeError` matching
  `"midrange\(\) requires a list, got int"`.
- `midrange([1, "a"]);` raises `CinderRuntimeError` matching
  `"midrange\(\) requires a list of numbers, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_median`, search
`def _median`), `tests/test_builtins.py` (new `class TestMidrange`,
modeled on `class TestMean`/`class TestMedian`, search either name, for
the test shapes above — place it near the existing `class TestMedian`).
Once merged, `README.md`'s existing `median` bullet needs `midrange`
added right after it, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `to_set` — convert a list into a `Set` value

Add a standalone conversion builtin directly after `_is_disjoint`
(`cinder/builtins.py`, search `def _is_disjoint`, immediately before
`def _interleave`) — the runtime-`Set`-constructing counterpart to the
existing `union`/`intersection`/`difference`/`symmetric_difference`/
`is_subset`/`is_superset`/`is_disjoint` cluster, all of which already
implement set-style *semantics* on plain lists but never produce an
actual `CinderSet` value. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(to_set([1, 2, 2, 3]));'
# -> <eval>:1:7: undefined name 'to_set' (did you mean 'to_oct'?)
```

**What it does.** Given a list, return a new `Set` (a `CinderSet` runtime
value, same as a `{1, 2, 3}` literal produces) containing that list's
elements, deduplicated, in first-seen order — reusing the exact
element-validation rule Set literals already enforce (`cinder/
interpreter.py`'s `_evaluate_set_literal`, search `def
_evaluate_set_literal`: every element must satisfy `_is_valid_key`, the
same rule map keys use, so a list or map element is rejected). Note this
builtin can produce an **empty** `Set` (`to_set([])`), something no Set
*literal* can spell — `{}` is grammatically claimed by the empty map
literal (see `README.md`'s Set bullet, "empty braces still an empty
map") — so `to_set([])` closes a real expressiveness gap, not just a
convenience wrapper.

Worked examples (confirmed via direct computation of the algorithm
below):
- `to_set([1, 2, 2, 3])` equals `{1, 2, 3}` (Set equality is
  order-insensitive, already implemented).
- `to_set([])` is an empty `Set` — `len(to_set([]))` is `0`, and
  `to_set([]) == to_set([])` is `true`; there is no source-syntax way to
  spell this literally, only via this builtin.
- `to_set([1, "a", 1, "a"])` equals `{1, "a"}` — dedup across mixed
  types, same `values_equal` semantics the Set literal's own
  construction and `_dedupe`/`_contains_value` (search either, used by
  `union`/`intersection` above) already use.
- `to_set([3, 1, 2, 1])` stringifies in first-seen order: `str(to_set([3,
  1, 2, 1]))` is `"{3, 1, 2}"` — same "elements become dict keys,
  insertion order" behavior `_evaluate_set_literal` already gives a
  literal.
- `to_set([[1, 2]])` raises `CinderRuntimeError` matching `"list is not a
  valid set element"` — mirrors the Set literal's own
  `test_set_literal_invalid_element_list_raises` (search that name in
  `tests/test_interpreter.py`) for the exact message shape, since a list
  element isn't a valid dict/set key.
- `to_set([{"a": 1}])` raises `CinderRuntimeError` matching `"map is not
  a valid set element"` — same reasoning, mirrors
  `test_set_literal_invalid_element_map_raises`.
- `to_set(5);` raises `CinderRuntimeError` matching `"to_set\(\) requires
  a list, got int"`.

Add directly after `_is_disjoint` (search `def _is_disjoint`):
```python
def _to_set(arguments: list, line: int, column: int) -> object:
    _require_arity("to_set", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"to_set() requires a list, got {type_name(value)}", line, column
        )
    result = CinderSet()
    for element in value:
        if not _is_valid_key(element):
            raise CinderRuntimeError(
                f"{type_name(element)} is not a valid set element", line, column
            )
        result[element] = True
    return result
```
(Same element-validation rule as `_evaluate_set_literal` — search that
name in `cinder/interpreter.py` — reused here for a builtin instead of a
literal.) Add `CinderSet` to the existing `from cinder.interpreter
import (...)` block at the top of `cinder/builtins.py` (search
`_is_valid_key,`, add `CinderSet,` to that same import list — it's
already imported for `_is_valid_key`, just not for `CinderSet` itself).
Register the new dict entry (search `"is_disjoint": _is_disjoint,`, add
`"to_set": _to_set,` directly after it, before `"interleave":
_interleave,`).

Acceptance criteria:
- Every worked example above holds exactly, including `to_set([1, 2, 2,
  3])` equals `{1, 2, 3}` and `to_set([])` is an empty `Set` with
  `len(to_set([])) == 0`.
- `to_set([1, "a", 1, "a"])` equals `{1, "a"}` — the mixed-type dedup
  case.
- `str(to_set([3, 1, 2, 1]))` is `"{3, 1, 2}"` — the first-seen-order
  stringify case.
- `to_set([[1, 2]]);` raises `CinderRuntimeError` matching `"list is not
  a valid set element"`, and `to_set([{"a": 1}]);` raises matching `"map
  is not a valid set element"`.
- `to_set(5);` raises `CinderRuntimeError` matching `"to_set\(\) requires
  a list, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_disjoint`,
search `def _is_disjoint`, plus the `from cinder.interpreter import`
block at the top), `tests/test_builtins.py` (new `class TestToSet`,
modeled on `class TestIsDisjoint`/the Set-literal validation tests in
`tests/test_interpreter.py`'s `TestSetLiteral`, search either name, for
the test shapes above — place it near the existing set-style-builtin
tests). Once merged, `README.md`'s Set bullet (search `Set literals
{1, 2, 3}`) needs its "no `is_set`/`to_set` builtin" clause updated to
drop `to_set` from that list (leaving `is_set` as the one remaining
noted gap), its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave all
three to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `rms` — quadratic mean (root mean square) of a numeric list

Add a standalone list-statistic builtin directly after `_harmonic_mean`
(`cinder/builtins.py`, search `def _harmonic_mean`, immediately before
`def _median`) — the fourth classical Pythagorean mean, sitting next to
`mean`/`geometric_mean`/`harmonic_mean`: the square root of the average
of the squared elements. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(rms([1, 2, 3]));'
# -> <eval>:1:7: undefined name 'rms'
```

**What it does.** Given a non-empty list of numbers, return
`sqrt(sum(x^2 for x in list) / len(list))`. Unlike `geometric_mean`/
`harmonic_mean`, squaring makes every element non-negative before the
average, so `rms` places **no positivity restriction** on its input —
negative elements are fine, only the empty list is rejected (same
reason `mean`/`median`/`std_dev` reject it: no elements to average).

Worked examples (confirmed via direct computation of the algorithm
below):
- `rms([1, 2, 3])` is `2.160246899469287` — `sqrt((1 + 4 + 9) / 3)`.
- `rms([3, 4])` is `3.5355339059327378` — `sqrt((9 + 16) / 2)`.
- `rms([5])` is `5.0` — a single-element list's rms is that element's
  absolute value (as a float).
- `rms([-3, 3])` is `3.0` — negative elements are squared away, so this
  does *not* raise (the positivity check `geometric_mean`/
  `harmonic_mean` both have does not apply here).
- `rms([0, 0, 0])` is `0.0`.
- `rms([1, 2, 4])` is greater than or equal to `mean([1, 2, 4])` —
  the QM-AM inequality, the same kind of cross-check
  `test_harmonic_mean_am_gm_hm_inequality` (search that name in
  `tests/test_builtins.py`) already makes for the other three means.
- `rms([]);` raises `CinderRuntimeError` — no elements to average.

Add directly after `_harmonic_mean` (search `def _harmonic_mean`,
immediately before `def _median`) — keeps the new quadratic mean next
to the other three Pythagorean means it completes:
```python
def _rms(arguments: list, line: int, column: int) -> object:
    _require_arity("rms", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"rms() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("rms() requires a non-empty list", line, column)
    squared_total = 0
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"rms() requires a list of numbers, got {type_name(element)}", line, column
            )
        squared_total = squared_total + element ** 2
    return math.sqrt(squared_total / len(value))
```
(Same validate-then-reduce shape as `_mean`/`_harmonic_mean` — search
either — just averaging squares instead of raw values or reciprocals,
and square-rooting the result; `math` is already imported in this
module for `_std_dev`.) Register the new dict entry (search
`"harmonic_mean": _harmonic_mean,`, add `"rms": _rms,` directly after
it, before `"median": _median,`).

Acceptance criteria:
- Every worked example above holds exactly, including `rms([1, 2,
  3])` is `2.160246899469287` and `rms([3, 4])` is
  `3.5355339059327378`.
- `rms([5]);` is `5.0` and `rms([0, 0, 0]);` is `0.0` — the
  single-element and all-zero cases.
- `rms([-3, 3]);` is `3.0` and does not raise — negative elements are
  accepted, unlike `geometric_mean`/`harmonic_mean`.
- `rms([1, 2, 4])` is greater than or equal to `mean([1, 2, 4])` — the
  QM-AM inequality cross-check, mirroring
  `test_harmonic_mean_am_gm_hm_inequality`'s style.
- `rms([]);` raises `CinderRuntimeError` matching `"rms\(\) requires a
  non-empty list"`.
- `rms(123);` raises `CinderRuntimeError` matching `"rms\(\) requires a
  list, got int"`.
- `rms([1, "a"]);` raises `CinderRuntimeError` matching `"rms\(\)
  requires a list of numbers, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_harmonic_mean`,
search `def _harmonic_mean`), `tests/test_builtins.py` (new `class
TestRms`, modeled on `class TestHarmonicMean`/`class
TestGeometricMean`, search either name, for the test shapes above —
place it near the existing `class TestHarmonicMean`). Once merged,
`README.md`'s builtins quick-reference list (search `harmonic_mean`)
needs `rms` added right after it, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 5. Standard library: `zscore` — standardize a numeric list to zero mean, unit variance

Add a standalone list-transform builtin directly after `_std_dev`
(`cinder/builtins.py`, search `def _std_dev`, immediately before `def
_dot_product`) — the transform-shaped sibling of `mean`/`std_dev`:
where those two reduce a list to a single summary number, `zscore`
reuses the same `_population_variance` helper to turn every element
into how many standard deviations it sits from the list's mean.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(zscore([1, 2, 3]));'
# -> <eval>:1:7: undefined name 'zscore' (did you mean 'is_coprime'?)
```

**What it does.** Given a non-empty list of numbers, return a new list
of the same length where `result[i] = (list[i] - mean(list)) /
std_dev(list)` — each element's population z-score. `std_dev` of a
single-element or constant list is `0` (verified: `std_dev([5])` is
`0`, `std_dev([4, 4, 4])` is `0`), which would divide by zero, so
those two shapes raise instead of computing.

Worked examples (confirmed via direct computation of the algorithm
below):
- `zscore([2, 4, 4, 4, 5, 5, 7, 9])` is `[-1.5, -0.5, -0.5, -0.5, 0.0,
  0.0, 1.0, 2.0]` — the same textbook list `std_dev`'s own test uses
  (`tests/test_builtins.py`, `test_std_dev_of_textbook_example`, mean
  `5`, `std_dev` exactly `2`), so every element divides out evenly.
- `zscore([1, 2, 3])` is `[-1.224744871391589, 0.0, 1.224744871391589]`
  — mean `2`, `std_dev` `sqrt(2/3)`.
- `zscore([5])` raises `CinderRuntimeError` — single-element list,
  `std_dev` is `0`.
- `zscore([4, 4, 4])` raises `CinderRuntimeError` — constant list,
  `std_dev` is `0`.
- `zscore([])` raises `CinderRuntimeError` — empty list, no mean to
  compute (same reason `mean`/`std_dev` reject it).

Add directly after `_std_dev` (search `def _std_dev`, immediately
before `def _dot_product`):
```python
def _zscore(arguments: list, line: int, column: int) -> object:
    _require_arity("zscore", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"zscore() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("zscore() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"zscore() requires a list of numbers, got {type_name(element)}", line, column
            )
    total = 0
    for element in value:
        total = total + element
    mean = total / len(value)
    standard_deviation = math.sqrt(_population_variance(value))
    if standard_deviation == 0:
        raise CinderRuntimeError(
            "zscore() requires a list with non-zero standard deviation", line, column
        )
    return [(element - mean) / standard_deviation for element in value]
```
(Reuses `_population_variance` — search `def _population_variance` —
the same private helper `_variance`/`_std_dev` already share, so the
mean/variance math can't drift between the three.) Register the new
dict entry (search `"std_dev": _std_dev,`, add `"zscore": _zscore,`
directly after it, before `"dot_product": _dot_product,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `zscore([2, 4, 4, 4, 5, 5, 7, 9])` is `[-1.5, -0.5, -0.5, -0.5, 0.0,
  0.0, 1.0, 2.0]` and `zscore([1, 2, 3])` is
  `[-1.224744871391589, 0.0, 1.224744871391589]`.
- `zscore([5]);` and `zscore([4, 4, 4]);` both raise
  `CinderRuntimeError` matching `"zscore\(\) requires a list with
  non-zero standard deviation"`.
- `zscore([]);` raises `CinderRuntimeError` matching `"zscore\(\)
  requires a non-empty list"`.
- `zscore(123);` raises `CinderRuntimeError` matching `"zscore\(\)
  requires a list, got int"`.
- `zscore([1, "a"]);` raises `CinderRuntimeError` matching
  `"zscore\(\) requires a list of numbers, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_std_dev`, search
`def _std_dev`), `tests/test_builtins.py` (new `class TestZscore`,
modeled on `class TestStdDev`/`class TestMean`, search either name,
for the test shapes above — place it near the existing `class
TestStdDev`). Once merged, `README.md`'s builtins quick-reference list
(search `std_dev`) needs `zscore` added right after it, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

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
