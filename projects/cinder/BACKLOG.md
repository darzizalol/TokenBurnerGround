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

## 1. Language: spread a `Set` positionally in list literals and function calls; reject it cleanly in map literals [claimed 2026-09-11T14:23:15Z]

`CinderSet` (`cinder/interpreter.py`, search `class CinderSet(dict)`) is
implemented as a `dict` subclass with elements as keys, which gives it
insertion-order `for`-in iteration, comprehension iteration, and `in`
membership for free — those three already work correctly today despite
`README.md` still (incorrectly) claiming they don't; this task does not
touch them. But that same `dict`-subclass trick makes the three spread
sites (`cinder/interpreter.py`) actively **wrong** for a `Set` operand,
in three different ways. Verify all three gaps:
```sh
python3 -m cinder.cli eval 'print([...{1, 2, 3}]);'
# -> <eval>:1:8: cannot spread set in a list literal
# (wrong: a Set is a natural source for a list literal, same as ...[1,2,3])

python3 -m cinder.cli eval 'fn f(a,b,c) { print(a+b+c); } f(...{1, 2, 3});'
# -> <eval>:1:33: cannot spread map with non-string key 1 as keyword arguments
# (wrong AND confusing: this treats the Set as a map-spread purely because
# `isinstance(value, dict)` matches it first, producing an error about
# "keyword arguments" for code that never mentioned any)

python3 -m cinder.cli eval 'print({...{1, 2, 3}});'
# -> {1: true, 2: true, 3: true}
# (wrong: silently "succeeds" by leaking the Set's internal dict
# representation — {element: True} for every element — into a map,
# instead of raising; nothing about a Set has key:value pairs to spread)
```

**What each fix does.**
- List literals (`[...expr]`): a `Set` operand should spread its elements
  positionally, in insertion order, exactly like spreading a `list` does.
  `[...{1, 2, 3}]` should be `[1, 2, 3]`; `[0, ...{1, 2}, 3]` should be
  `[0, 1, 2, 3]`.
- Function calls (`f(...expr)`): a `Set` operand should spread its
  elements as positional arguments, exactly like spreading a `list` does
  — not as a keyword-argument map-spread. `f(...{1, 2, 3})` (with `f`
  defined to take three positional parameters) should return the same
  result as `f(...[1, 2, 3])`.
- Map literals (`{...expr}`): a `Set` operand has no key:value pairs to
  contribute and must raise a clean `CinderRuntimeError`, exactly like
  spreading a `list` or a number already does, not silently succeed by
  leaking `CinderSet`'s internal `{element: True}` dict representation.

Worked examples (confirmed via direct trace of the fixes below):
- `[...{1, 2, 3}]` is `[1, 2, 3]` — insertion order preserved.
- `[0, ...{1, 2}, 3, ...{4, 5}]` is `[0, 1, 2, 3, 4, 5]` — composes with
  other elements and multiple spreads, mirroring the existing
  `test_list_literal_multiple_spreads` list-spread test.
- Given `fn f(a, b, c) { return a + b + c; }`, `f(...{1, 2, 3})` is `6`
  — Set elements become positional arguments, in insertion order.
- `{...{1, 2, 3}};` raises `CinderRuntimeError` matching `"cannot spread
  set in a map literal"`.
- `[...{1, 2}]` composed with a plain list spread still works
  unaffected: `[...{1, 2}, ...[3, 4]]` is `[1, 2, 3, 4]`.
- Plain `list`/`map`/other-type spread behavior at all three sites is
  completely unchanged — this task only adds a new, previously-missing
  branch for `CinderSet`, it doesn't touch the existing `list`/`dict`
  branches' logic.

Fix all three sites in `cinder/interpreter.py`:

1. `_evaluate_list_literal` (search `def _evaluate_list_literal`) — add a
   `CinderSet` branch before the existing `list` check (order doesn't
   matter here since `list` and `CinderSet` are disjoint types, but
   matching the call-argument fix's ordering keeps the two consistent):
   ```python
   if isinstance(element, Spread):
       value = self.evaluate(element.expression, env)
       if isinstance(value, CinderSet):
           result.extend(value.keys())
       elif isinstance(value, list):
           result.extend(value)
       else:
           raise CinderRuntimeError(
               f"cannot spread {type_name(value)} in a list literal",
               element.line,
               element.column,
           )
   ```

2. `_evaluate_call_arguments` (search `def _evaluate_call_arguments`) —
   add a `CinderSet` branch **before** the existing `isinstance(value,
   dict)` branch; ordering matters here since `CinderSet` is a `dict`
   subclass, so the existing `dict` check would otherwise keep
   intercepting it first:
   ```python
   elif isinstance(arg, Spread):
       value = self.evaluate(arg.expression, env)
       if isinstance(value, CinderSet):
           positional.extend(value.keys())
       elif isinstance(value, dict):
           for key, entry_value in value.items():
               ...  # unchanged
       elif isinstance(value, list):
           positional.extend(value)
       else:
           raise CinderRuntimeError(
               f"cannot spread {type_name(value)} in a function call",
               arg.line,
               arg.column,
           )
   ```

3. `_evaluate_map_literal` (search `def _evaluate_map_literal`) — add a
   `CinderSet` check **before** the existing `isinstance(value, dict)`
   check, for the same subclass-ordering reason as above:
   ```python
   if isinstance(entry, Spread):
       value = self.evaluate(entry.expression, env)
       if isinstance(value, CinderSet):
           raise CinderRuntimeError(
               "cannot spread set in a map literal",
               entry.line,
               entry.column,
           )
       if not isinstance(value, dict):
           raise CinderRuntimeError(
               f"cannot spread {type_name(value)} in a map literal",
               entry.line,
               entry.column,
           )
       ...  # unchanged
   ```

Acceptance criteria:
- Every worked example above holds exactly, including `[...{1, 2, 3}]`
  is `[1, 2, 3]` and `f(...{1, 2, 3})` is `6` for a three-positional-arg
  `f`.
- `{...{1, 2, 3}};` raises `CinderRuntimeError` matching `"cannot spread
  set in a map literal"`.
- Spreading a plain `list` or `map` (non-`Set`) at all three sites still
  behaves exactly as before — every existing spread test in
  `tests/test_interpreter.py` (`TestListsAndMaps`,
  `TestSpreadCallArguments`, `TestMapSpreadCallArguments`) still passes
  unmodified.
- Wrong-type spreads (e.g. `[...5]`, `{...5}`, `f(...5)`) still raise
  their existing `"cannot spread <type> in a ..."` messages unchanged.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (the three sites named above:
`_evaluate_list_literal`, `_evaluate_call_arguments`,
`_evaluate_map_literal`), `tests/test_interpreter.py` (new test methods
in the existing `TestListsAndMaps` class for the list-literal and
map-literal cases, and in `TestSpreadCallArguments` for the call-argument
case — search those class names — modeled on the existing
`test_list_literal_with_spread`/`test_map_literal_spreading_non_map_raises`
tests). Once merged, `README.md`'s Set bullet (search `Set literals
{1, 2, 3}`) needs its stale "no spread" clause replaced with a note that
list-literal and call-argument spread now work (and map-literal spread
raises cleanly), `PROJECT.md`'s "Current frontier" section needs
refreshing, and `BACKLOG.md`'s own "Backlog policy" alternation is
satisfied by this landing as the depth task — leave all three to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `cummin` — cumulative (running) minimum of a numeric list

Add a standalone list-transform builtin directly after `_cummax`
(`cinder/builtins.py`, search `def _cummax`, immediately before `def
_clamp`) — the minimizing sibling of the already-merged `cummax`, the
same running-aggregate shape applied to `min` instead of `max`.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(cummin([5, 3, 4, 1, 2]));'
# -> <eval>:1:7: undefined name 'cummin' (did you mean 'min'?)
```

**What it does.** Given a list of numbers, return a new list of the same
length where each element is the running minimum of every element up to
and including that position — `result[i] = min(list[0], list[1], ...,
list[i])`. An empty list returns an empty list.

Worked examples (confirmed via direct computation of the algorithm
below):
- `cummin([5, 3, 4, 1, 2])` is `[5, 3, 3, 1, 1]`.
- `cummin([])` is `[]` — the empty list has no running minimum to
  build, vacuously empty.
- `cummin([5])` is `[5]` — a single-element list returns that element's
  own running minimum, itself.
- `cummin([-1, -2, -3])` is `[-1, -2, -3]` — an already-descending list
  keeps dropping.
- `cummin([3, 2.5, 4])` is `[3, 2.5, 2.5]` (mixed int/float elements,
  ordinary numeric comparison — same as `min`/`max`).
- `cummin([3, 3, 3])` is `[3, 3, 3]`.

Add directly after `_cummax` (search `def _cummax`):
```python
def _cummin(arguments: list, line: int, column: int) -> object:
    _require_arity("cummin", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"cummin() requires a list, got {type_name(value)}", line, column
        )
    result = []
    running = None
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"cummin() requires a list of numbers, got {type_name(element)}", line, column
            )
        running = element if running is None else min(running, element)
        result.append(running)
    return result
```
(Same list-in/list-out shape as `_cummax` — search `def _cummax` —
just tracking a running minimum instead.) Register the new dict entry
(search `"cummax": _cummax,`, add `"cummin": _cummin,` directly after
it, before `"clamp": _clamp,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `cummin([5, 3, 4, 1, 2])` is `[5, 3, 3, 1, 1]` and `cummin([3, 2.5,
  4])` is `[3, 2.5, 2.5]`.
- `cummin([]);` is `[]` and `cummin([5]);` is `[5]` — the empty-list and
  single-element cases.
- `cummin([-1, -2, -3]);` is `[-1, -2, -3]` — the already-descending
  case.
- `cummin(123);` raises `CinderRuntimeError` matching
  `"cummin\(\) requires a list, got int"`.
- `cummin([1, "a"]);` raises `CinderRuntimeError` matching
  `"cummin\(\) requires a list of numbers, got string"` (mirror `min`'s
  own non-numeric-element test for the exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_cummax`, search
`def _cummax`), `tests/test_builtins.py` (new `class
TestCummin`, modeled on `class TestMin`, search that name, for the test
shapes above — place it near the existing `class TestMin`/`class
TestCummax`). Once merged, `README.md`'s existing `min` bullet needs
`cummin` added right after it, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 3. Standard library: `longest_common_suffix` — mirror `longest_common_prefix` from the other end

Add a standalone list-of-strings builtin directly after
`_longest_common_prefix` (`cinder/builtins.py`, search `def
_longest_common_prefix`, immediately before `def _is_pangram`) — the
suffix-side mirror of `longest_common_prefix` (the same
directional-generalization move `to_roman`/`from_roman` and
`rot13`/`caesar_cipher` already made). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(longest_common_suffix(["flower", "power", "shower"]));'
# -> <eval>:1:7: undefined name 'longest_common_suffix'
```

**What it does.** Given a list of strings, return the longest string
that is a suffix of every string in the list — the same walk
`longest_common_prefix` does, just comparing from the end of each
string instead of the start. An empty list, or a list containing any
empty string, returns `""`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `longest_common_suffix(["flower", "power", "shower"])` is `"ower"`.
- `longest_common_suffix(["dog", "racecar", "car"])` is `""` — no
  shared suffix.
- `longest_common_suffix(["testing", "resting", "nesting"])` is
  `"esting"`.
- `longest_common_suffix(["throne"])` is `"throne"` — a single-element
  list returns that element's own suffix, itself.
- `longest_common_suffix(["throne", "throne"])` is `"throne"` —
  identical strings share their whole length.
- `longest_common_suffix([])` is `""` — the empty list has no strings
  to compare.
- `longest_common_suffix(["cat", ""])` is `""` — any empty string in
  the list forces an empty result, since nothing is a suffix of `""`
  except `""` itself.

Add directly after `_longest_common_prefix` (search `def
_longest_common_prefix`, immediately before `def _is_pangram`) — keeps
the new suffix builtin next to the prefix sibling it mirrors:
```python
def _longest_common_suffix(arguments: list, line: int, column: int) -> object:
    _require_arity("longest_common_suffix", arguments, 1, line, column)
    items = arguments[0]
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"longest_common_suffix() requires a list, got {type_name(items)}",
            line, column,
        )
    for item in items:
        if not isinstance(item, str):
            raise CinderRuntimeError(
                f"longest_common_suffix() requires a list of strings, got {type_name(item)}",
                line, column,
            )
    if not items:
        return ""
    suffix = items[0]
    for candidate in items[1:]:
        while not candidate.endswith(suffix):
            suffix = suffix[1:]
            if not suffix:
                return ""
    return suffix
```
(Same shrink-until-it-fits loop as `_longest_common_prefix` — search
`def _longest_common_prefix` — just trimming from the front of the
running `suffix` and matching with `endswith` instead of trimming from
the back and matching with `startswith`.) Register the new dict entry
(search `"longest_common_prefix": _longest_common_prefix,`, add
`"longest_common_suffix": _longest_common_suffix,` directly after it,
before `"is_pangram": _is_pangram,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `longest_common_suffix(["flower", "power", "shower"])` is `"ower"`
  and `longest_common_suffix(["testing", "resting", "nesting"])` is
  `"esting"`.
- `longest_common_suffix([]);` is `""` and
  `longest_common_suffix(["throne"]);` is `"throne"` — the empty-list
  and single-element cases.
- `longest_common_suffix(["cat", ""]);` is `""` — the empty-string-in-
  list case.
- `longest_common_suffix(123);` raises `CinderRuntimeError` matching
  `"longest_common_suffix\(\) requires a list, got int"`.
- `longest_common_suffix([1, 2]);` raises `CinderRuntimeError` matching
  `"longest_common_suffix\(\) requires a list of strings, got int"`
  (mirror `longest_common_prefix`'s own non-string-element test for the
  exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after
`_longest_common_prefix`, search `def _longest_common_prefix`),
`tests/test_builtins.py` (new `class TestLongestCommonSuffix`, modeled
on `class TestLongestCommonPrefix`, search that name, for the test
shapes above — place it near the existing `class
TestLongestCommonPrefix`). Once merged, `README.md`'s existing
`longest_common_prefix` bullet needs `longest_common_suffix` added
right after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `diff` — successive differences of a numeric list

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

## 5. Standard library: `midrange` — average of a numeric list's minimum and maximum

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

## 6. Standard library: `to_set` — convert a list into a `Set` value

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
