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

## 1. Standard library: `to_set` — convert a list into a `Set` value

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

## 2. Standard library: `rms` — quadratic mean (root mean square) of a numeric list

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

## 3. Standard library: `zscore` — standardize a numeric list to zero mean, unit variance

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

## 4. Standard library: `covariance` — population covariance of two equal-length numeric lists

Add a standalone two-list numeric-statistic builtin directly after
`_dot_product` (`cinder/builtins.py`, search `def _dot_product`,
immediately before `def _mode`) — combines `dot_product`'s two-list
validation shape (equal length, both all-numeric) with `variance`'s
non-empty requirement (population covariance divides by `n`, same
division-by-zero reason `variance`/`std_dev` reject an empty list) to
give the two-list generalization of `variance`: how two lists vary
together instead of how one varies alone. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(covariance([1, 2, 3], [4, 5, 6]));'
# -> <eval>:1:7: undefined name 'covariance' (did you mean 'variance'?)
```

**What it does.** Given two non-empty numeric lists of equal length,
return `mean((x[i] - mean(x)) * (y[i] - mean(y)) for i in range(n))` —
the population covariance (divide by `n`, not `n - 1`, same convention
`_population_variance` already uses). Positive when the two lists tend
to move together, negative when they move oppositely, `0` when one
list is constant or the two are uncorrelated.

Worked examples (confirmed via direct computation of the algorithm
below):
- `covariance([1, 2, 3], [4, 5, 6])` is `0.6666666666666666` — both
  lists increase together.
- `covariance([1, 2, 3], [6, 5, 4])` is `-0.6666666666666666` — the
  same lists, second one reversed, flips the sign.
- `covariance([1, 2, 3], [1, 2, 3])` equals `variance([1, 2, 3])`
  (`0.6666666666666666`) — a list's covariance with itself is its own
  variance, a cross-check in the same spirit as
  `test_harmonic_mean_am_gm_hm_inequality` (search that name in
  `tests/test_builtins.py`) for the Pythagorean means.
- `covariance([1, 2, 3, 4], [10, 10, 10, 10])` is `0.0` — a constant
  second list has no variation to covary with, regardless of the
  first.
- `covariance([5], [5])` is `0.0` — a single-element pair.
- `covariance([], []);` raises `CinderRuntimeError` — empty lists, no
  elements to average (same reason `variance`/`std_dev` reject an
  empty list; unlike `dot_product`, which tolerates empty lists since
  it never divides by `n`).
- `covariance([1, 2], [1, 2, 3]);` raises `CinderRuntimeError` — unequal
  lengths, mirroring `dot_product`'s own length check.

Add directly after `_dot_product` (search `def _dot_product`,
immediately before `def _mode`):
```python
def _covariance(arguments: list, line: int, column: int) -> object:
    _require_arity("covariance", arguments, 2, line, column)
    first, second = arguments
    if not isinstance(first, list):
        raise CinderRuntimeError(
            f"covariance() requires a list as its first argument, got {type_name(first)}",
            line, column,
        )
    if not isinstance(second, list):
        raise CinderRuntimeError(
            f"covariance() requires a list as its second argument, got {type_name(second)}",
            line, column,
        )
    for element in first + second:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"covariance() requires lists of numbers, got {type_name(element)}",
                line, column,
            )
    if len(first) != len(second):
        raise CinderRuntimeError(
            f"covariance() requires lists of equal length, got lengths {len(first)} and {len(second)}",
            line, column,
        )
    if not first:
        raise CinderRuntimeError("covariance() requires non-empty lists", line, column)
    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    total = 0
    for x, y in zip(first, second):
        total = total + (x - first_mean) * (y - second_mean)
    return total / len(first)
```
(Same equal-length/all-numeric validation as `_dot_product` — search
`def _dot_product` — plus the same non-empty guard `_variance`/
`_std_dev` use, since this divides by `len(first)` where
`_dot_product` never divides at all.) Register the new dict entry
(search `"dot_product": _dot_product,`, add `"covariance":
_covariance,` directly after it, before `"mode": _mode,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `covariance([1, 2, 3], [4, 5, 6])` is `0.6666666666666666` and
  `covariance([1, 2, 3], [6, 5, 4])` is `-0.6666666666666666`.
- `covariance([1, 2, 3], [1, 2, 3])` equals `variance([1, 2, 3])`
  exactly.
- `covariance([1, 2, 3, 4], [10, 10, 10, 10])` is `0.0` and
  `covariance([5], [5])` is `0.0`.
- `covariance([], []);` raises `CinderRuntimeError` matching
  `"covariance\(\) requires non-empty lists"`.
- `covariance([1, 2], [1, 2, 3]);` raises `CinderRuntimeError` matching
  `"covariance\(\) requires lists of equal length, got lengths 2 and
  3"`.
- `covariance(5, [1, 2]);` raises `CinderRuntimeError` matching
  `"covariance\(\) requires a list as its first argument, got int"`
  (and the mirrored message for a bad second argument).
- `covariance([1, "a"], [1, 2]);` raises `CinderRuntimeError` matching
  `"covariance\(\) requires lists of numbers, got string"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_dot_product`,
search `def _dot_product`), `tests/test_builtins.py` (new `class
TestCovariance`, modeled on `class TestDotProduct`/`class TestVariance`,
search either name, for the test shapes above — place it near the
existing `class TestDotProduct`). Once merged, `README.md`'s builtins
quick-reference list (search `dot_product`) needs `covariance` added
right after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `correlation` — Pearson correlation coefficient of two equal-length numeric lists

Add a standalone two-list numeric-statistic builtin directly after
`_covariance` (`cinder/builtins.py`, once task 4 lands `_covariance`
will sit directly after `_dot_product`, immediately before `_mode` —
add `_correlation` directly after `_covariance`, still before `_mode`)
— the normalized sibling of `covariance`: dividing covariance by the
product of both lists' standard deviations rescales it to always fall
in `[-1, 1]`, independent of the lists' units. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(correlation([1, 2, 3], [4, 5, 6]));'
# -> <eval>:1:7: undefined name 'correlation' (did you mean 'covariance'?)
```

**What it does.** Given two non-empty numeric lists of equal length,
return `covariance(x, y) / (std_dev(x) * std_dev(y))` — the Pearson
correlation coefficient (reusing `_covariance` from task 4 and the
existing `_population_variance`/`math.sqrt` shape `_std_dev` already
uses for the denominator). `std_dev` of a single-element or constant
list is `0` (same fact `zscore`'s task writeup above relied on), which
would divide by zero, so those two shapes raise instead of computing —
exactly the same guard `zscore` already added for the same underlying
reason.

Worked examples (confirmed via direct computation of the algorithm
below):
- `correlation([1, 2, 3], [4, 5, 6])` is `1.0` — one list is an exact
  increasing linear function of the other, perfect positive
  correlation.
- `correlation([1, 2, 3], [6, 5, 4])` is `-1.0` — an exact decreasing
  linear function, perfect negative correlation.
- `correlation([1, 2, 3], [1, 2, 3])` is `1.0` — a list is always
  perfectly correlated with itself.
- `correlation([1, 2, 3, 4], [2, 4, 5, 4])` is `0.7181848464596078` —
  a non-perfect case: covariance `0.875`, `std_dev` of the two lists
  `1.118033988749895` and `1.0897247358851685`.
- `correlation([1, 2, 3, 4], [10, 10, 10, 10]);` raises
  `CinderRuntimeError` — the second list is constant, `std_dev` is
  `0`, correlation is undefined (division by zero).
- `correlation([5], [5]);` raises `CinderRuntimeError` — single-element
  lists, `std_dev` is `0` on both sides.
- `correlation([], []);` raises `CinderRuntimeError` — empty lists, no
  elements to average (same reason `covariance` rejects them).
- `correlation([1, 2], [1, 2, 3]);` raises `CinderRuntimeError` —
  unequal lengths, mirroring `covariance`'s own length check.

Add directly after `_covariance` (once task 4 lands; search `def
_covariance`, add `_correlation` immediately after it, still before
`def _mode`):
```python
def _correlation(arguments: list, line: int, column: int) -> object:
    _require_arity("correlation", arguments, 2, line, column)
    first, second = arguments
    if not isinstance(first, list):
        raise CinderRuntimeError(
            f"correlation() requires a list as its first argument, got {type_name(first)}",
            line, column,
        )
    if not isinstance(second, list):
        raise CinderRuntimeError(
            f"correlation() requires a list as its second argument, got {type_name(second)}",
            line, column,
        )
    for element in first + second:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"correlation() requires lists of numbers, got {type_name(element)}",
                line, column,
            )
    if len(first) != len(second):
        raise CinderRuntimeError(
            f"correlation() requires lists of equal length, got lengths {len(first)} and {len(second)}",
            line, column,
        )
    if not first:
        raise CinderRuntimeError("correlation() requires non-empty lists", line, column)
    first_deviation = math.sqrt(_population_variance(first))
    second_deviation = math.sqrt(_population_variance(second))
    if first_deviation == 0 or second_deviation == 0:
        raise CinderRuntimeError(
            "correlation() requires lists with non-zero standard deviation", line, column
        )
    covariance_value = _covariance(arguments, line, column)
    return covariance_value / (first_deviation * second_deviation)
```
(Calls `_covariance` directly rather than re-deriving the mean-of-products
sum, so the two builtins' arithmetic can't drift apart; reuses
`_population_variance` — search `def _population_variance` — the same
private helper `variance`/`std_dev`/`zscore` already share.) Register
the new dict entry (search `"covariance": _covariance,`, add
`"correlation": _correlation,` directly after it, before `"mode":
_mode,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `correlation([1, 2, 3], [4, 5, 6])` is `1.0`,
  `correlation([1, 2, 3], [6, 5, 4])` is `-1.0`, and
  `correlation([1, 2, 3, 4], [2, 4, 5, 4])` is `0.7181848464596078`.
- `correlation([1, 2, 3], [1, 2, 3])` is `1.0`.
- `correlation([1, 2, 3, 4], [10, 10, 10, 10]);` and
  `correlation([5], [5]);` both raise `CinderRuntimeError` matching
  `"correlation\(\) requires lists with non-zero standard deviation"`.
- `correlation([], []);` raises `CinderRuntimeError` matching
  `"correlation\(\) requires non-empty lists"`.
- `correlation([1, 2], [1, 2, 3]);` raises `CinderRuntimeError` matching
  `"correlation\(\) requires lists of equal length, got lengths 2 and
  3"`.
- `correlation(5, [1, 2]);` raises `CinderRuntimeError` matching
  `"correlation\(\) requires a list as its first argument, got int"`
  (and the mirrored message for a bad second argument).
- `correlation([1, "a"], [1, 2]);` raises `CinderRuntimeError` matching
  `"correlation\(\) requires lists of numbers, got string"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_covariance`, once
task 4 lands), `tests/test_builtins.py` (new `class TestCorrelation`,
modeled on `class TestDotProduct`/the eventual `class TestCovariance`
from task 4, search either name, for the test shapes above — place it
near the existing `class TestDotProduct`). Once merged, `README.md`'s
builtins quick-reference list (search `dot_product`, `covariance` will
sit right after it once task 4 lands) needs `correlation` added right
after `covariance`, its "Status & roadmap" section needs updating, and
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
