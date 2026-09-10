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

## 1. Standard library: `from_roman` — parse a Roman numeral string back to an integer

Add the natural inverse of `to_roman` (already merged — this task
reuses its `_ROMAN_VALUES` table). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(from_roman("MMXXVI"));'
# -> <eval>:1:7: undefined name 'from_roman'
```

**What it does.** Greedily strip the largest matching symbol/pair from
the front of the string (same `_ROMAN_VALUES` list `to_roman` walks,
search `_ROMAN_VALUES`), accumulating its value, until the string is
exhausted or nothing more matches. **Canonical numerals only**: reject
anything that isn't exactly what `to_roman` itself would have produced.
The simplest correct way to enforce that is a round-trip check —
after decoding, re-encode the total with `_to_roman` and require it to
equal the original input verbatim — rather than writing a separate
validation pass. This single check catches every malformed case for
free: leftover unconsumed characters (out-of-order symbols like `"VX"`
or `"IC"`), non-canonical repetition (`"IIII"` decodes to `4` but
re-encodes to `"IV"`, not `"IIII"`), lowercase input, and empty input
(decodes to `0`, outside the `1..3999` domain).

Worked examples (inverse of `to_roman`'s own worked examples, confirmed
by direct computation of the algorithm below, including a full
round-trip check of every integer `1..3999` through `to_roman` then
back through `from_roman`):
- `from_roman("I")` is `1`, `from_roman("IV")` is `4`, `from_roman("IX")`
  is `9`.
- `from_roman("XIV")` is `14`, `from_roman("XL")` is `40`,
  `from_roman("XLIX")` is `49`, `from_roman("XC")` is `90`.
- `from_roman("CDXLIV")` is `444`, `from_roman("CDXCIX")` is `499`,
  `from_roman("CM")` is `900`, `from_roman("CMXLIV")` is `944`.
- `from_roman("MCMXCIV")` is `1994`, `from_roman("MMXXVI")` is `2026`,
  `from_roman("MMMCMXCIX")` is `3999`.
- `from_roman(to_roman(n))` equals `n` for every `n` in `1..3999`.

Add directly after `_to_roman` (search `def _to_roman`, immediately
before `def _push`) — keeps the inverse next to its sibling:
```python
def _from_roman(arguments: list, line: int, column: int) -> object:
    _require_arity("from_roman", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"from_roman() requires a string, got {type_name(value)}", line, column
        )
    remaining = value
    total = 0
    for amount, symbol in _ROMAN_VALUES:
        while remaining.startswith(symbol):
            total += amount
            remaining = remaining[len(symbol):]
    valid = (
        not remaining
        and 1 <= total <= 3999
        and _to_roman([total], line, column) == value
    )
    if not valid:
        raise CinderRuntimeError(
            f"from_roman() '{value}' is not a valid canonical Roman numeral, "
            "domain error",
            line, column,
        )
    return total
```
(The `and`-chain short-circuits, so `_to_roman([total], ...)` — which
itself raises outside the `1..3999` domain — is only called once
`total` is already known to be in range.) Register the new dict entry
(search `"to_roman": _to_roman,`, add `"from_roman": _from_roman,`
directly after it, before `"push": _push,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `from_roman("MCMXCIV")` is `1994` and `from_roman("MMXXVI")` is `2026`.
- `from_roman("I");` is `1` and `from_roman("MMMCMXCIX");` is `3999` —
  the domain's two boundary values.
- `from_roman(to_roman(n));` equals `n` for at least a representative
  spread of `n` (e.g. `1, 4, 9, 40, 49, 90, 444, 900, 1994, 2026, 3999`)
  — the round-trip property.
- Non-canonical strings that a naive symbol-sum would wrongly accept
  all raise `CinderRuntimeError` matching `"from_roman\(\) '.*' is not
  a valid canonical Roman numeral, domain error"`: `from_roman("IIII")`
  (non-canonical `4`), `from_roman("VX")` and `from_roman("IC")`
  (out-of-order symbols), `from_roman("");` (empty).
- `from_roman("mmxxvi");` (lowercase) also raises the same domain error.
- `from_roman(2026);` raises `CinderRuntimeError` matching
  `"from_roman\(\) requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_to_roman`, search
`def _to_roman`), `tests/test_builtins.py` (new `class TestFromRoman`,
modeled on `class TestToRoman`, search that name, for the test shapes
above — place it near the existing `class TestToRoman`). Once merged,
`README.md`'s existing `to_roman` bullet needs `from_roman` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `longest_common_prefix` — longest shared prefix of a list of strings

Add a standalone list-of-strings builtin, not another `is_*`/`nth_*` pair —
that gap list stayed exhausted this pass too (re-audited programmatically:
every unpaired `is_*` name is still one of the already-rejected categories —
multi-arg, string/list-shaped with no integer ordering, a type predicate, or
one of the confirmed-too-sparse-or-slow names from earlier passes' History
entries). `longest_common_prefix` sits next to `hamming_distance`/
`levenshtein_distance` (`cinder/builtins.py`, search `def
_hamming_distance`) as another string-comparison utility, but generalized
from a pair to a whole list. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(longest_common_prefix(["flower", "flow", "flight"]));'
# -> <eval>:1:7: undefined name 'longest_common_prefix'
```

**What it does.** Given a list of strings, return the longest string that is
a prefix of every string in the list. Compare character by character across
all strings simultaneously (or equivalently, shrink a running prefix
candidate from the first string until every remaining string starts with
it); stop at the first mismatching position or the shortest string's end,
whichever comes first.

Worked examples (confirmed via direct computation of the algorithm below):
- `longest_common_prefix(["flower", "flow", "flight"])` is `"fl"`.
- `longest_common_prefix(["dog", "racecar", "car"])` is `""` (no common
  prefix at all).
- `longest_common_prefix(["interspecies", "interstellar", "interstate"])` is
  `"inters"`.
- `longest_common_prefix(["throne"])` is `"throne"` — a single-element list
  returns that element verbatim.
- `longest_common_prefix(["throne", "throne"])` is `"throne"` — identical
  strings share their whole length.
- `longest_common_prefix([])` is `""` — the empty list has no strings to
  disagree, so the shared prefix is vacuously empty.
- `longest_common_prefix(["", "abc"])` is `""` and
  `longest_common_prefix(["abc", ""])` is `""` — any empty string in the
  list forces an empty result.

Add directly after `_hamming_distance` (search `def _hamming_distance`,
immediately before `def _is_pangram`) — keeps the new multi-string
comparison utility next to its closest siblings:
```python
def _longest_common_prefix(arguments: list, line: int, column: int) -> object:
    _require_arity("longest_common_prefix", arguments, 1, line, column)
    items = arguments[0]
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"longest_common_prefix() requires a list, got {type_name(items)}",
            line, column,
        )
    for item in items:
        if not isinstance(item, str):
            raise CinderRuntimeError(
                f"longest_common_prefix() requires a list of strings, got {type_name(item)}",
                line, column,
            )
    if not items:
        return ""
    prefix = items[0]
    for candidate in items[1:]:
        while not candidate.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix
```
(Same validation shape as `_join` — search `def _join` — which already
requires a list of strings for its first argument; the shrink-from-the-left
loop is the standard longest-common-prefix algorithm, correct because
`prefix` only ever shrinks, so once it becomes `""` every subsequent
`candidate.startswith("")` would trivially be `True` — the early `return ""`
inside the loop just short-circuits that dead work.) Register the new dict
entry (search `"hamming_distance": _hamming_distance,`, add
`"longest_common_prefix": _longest_common_prefix,` directly after it,
before `"is_pangram": _is_pangram,`).

Acceptance criteria:
- Every worked example above holds exactly, including the empty-list and
  single-element-list cases.
- `longest_common_prefix(["flower", "flow", "flight"]);` is `"fl"` and
  `longest_common_prefix(["dog", "racecar", "car"]);` is `""` — the two
  headline worked examples.
- `longest_common_prefix(123);` raises `CinderRuntimeError` matching
  `"longest_common_prefix\(\) requires a list, got int"`.
- `longest_common_prefix([1, "a"]);` raises `CinderRuntimeError` matching
  `"longest_common_prefix\(\) requires a list of strings, got int"` (mirror
  `join`'s own non-string-element test for the exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_hamming_distance`,
search `def _hamming_distance`), `tests/test_builtins.py` (new `class
TestLongestCommonPrefix`, modeled on `class TestHammingDistance`, search
that name, for the test shapes above — place it near the existing `class
TestHammingDistance`/`class TestLevenshteinDistance`). Once merged,
`README.md`'s existing `hamming_distance` bullet needs
`longest_common_prefix` added right after it, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `binary_gap` — longest run of zeros between two ones in an integer's binary representation

Add a standalone integer-property builtin, not another `is_*`/`nth_*`
pair — that gap list stayed exhausted this pass too (re-audited
programmatically: every unpaired `is_*` name is still one of the
already-rejected categories — multi-arg, string/list-shaped with no
integer ordering, a type predicate, or one of the confirmed-too-sparse-
or-slow names from earlier passes' History entries). `binary_gap` sits
next to `to_bin` (`cinder/builtins.py`, search `def _to_bin`, right
before `def _to_oct`) as another single-int-argument builtin derived
from an integer's binary representation, and next to `collatz_length`/
`collatz_max` (search `def _collatz_length`) as another "compute one
property of an integer" builtin with the same positive-integer-domain
shape. This is a classic algorithm exercise (the Codility "BinaryGap"
kata) that has never been implemented here. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(binary_gap(9));'
# -> <eval>:1:7: undefined name 'binary_gap'
```

**What it does.** A binary gap is a maximal run of consecutive `0`s
that is bounded on both sides by a `1` in the integer's binary
representation — trailing zeros after the last `1` don't count, since
there's no closing `1` to bound them. Return the length of the longest
such gap, or `0` if none exists (including for any power of two, and
for `1` itself, which has only a single bit set).

Worked examples (confirmed by direct computation of the algorithm
below, matching the classic kata's own reference values):
- `binary_gap(9)` is `2` — `9` is `1001` in binary, one gap of two
  zeros between the two `1`s.
- `binary_gap(529)` is `4` — `529` is `1000010001` in binary, gaps of
  four and three zeros; the longest is four.
- `binary_gap(20)` is `1` — `20` is `10100` in binary, a single gap of
  one zero.
- `binary_gap(15)` is `0` — `15` is `1111` in binary, no zeros at all.
- `binary_gap(32)` is `0` — `32` is `100000` in binary, a single `1`
  followed only by trailing zeros with no closing `1`, so there is no
  bounded gap.
- `binary_gap(1)` is `0` — `1` is `1` in binary, only one bit set.
- `binary_gap(1041)` is `5` — `1041` is `10000010001` in binary, gaps
  of five and three zeros; the longest is five (the kata's own
  headline example).

Add directly after `_to_bin` (search `def _to_bin`, immediately before
`def _to_oct`) — keeps the new binary-representation builtin next to
the conversion it's derived from:
```python
def _binary_gap(arguments: list, line: int, column: int) -> object:
    _require_arity("binary_gap", arguments, 1, line, column)
    value = _require_int("binary_gap", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "binary_gap() requires a positive integer, domain error",
            line, column,
        )
    segments = format(value, "b").split("1")
    interior = segments[1:-1]
    return max((len(segment) for segment in interior), default=0)
```
(`format(value, "b")` always starts with `1` — no leading-zero edge
case to handle — so splitting on `"1"` always yields an empty first
segment; `segments[1:-1]` keeps only the zero-runs strictly between two
`1`s, dropping both that leading empty segment and the trailing
segment after the final `1` (unbounded trailing zeros, per the spec
above); `max(..., default=0)` handles the case where `interior` is
empty, e.g. `1` or any power of two.) Register the new dict entry
(search `"to_bin": _to_bin,`, add `"binary_gap": _binary_gap,` directly
after it, before `"to_oct": _to_oct,`).

Acceptance criteria:
- Every worked example above holds exactly, including `binary_gap(529)`
  is `4` and `binary_gap(1041)` is `5`.
- `binary_gap(1);`, `binary_gap(15);`, and `binary_gap(32);` are all
  `0` — the three no-gap shapes (single bit, all-ones, power of two)
  above.
- `binary_gap(0);` and `binary_gap(-5);` both raise
  `CinderRuntimeError` matching `"binary_gap\(\) requires a positive
  integer, domain error"`.
- `binary_gap(true);` raises `CinderRuntimeError` matching
  `"binary_gap\(\) requires an int, got bool"`.
- `binary_gap("9");` raises `CinderRuntimeError` matching
  `"binary_gap\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_to_bin`, search
`def _to_bin`), `tests/test_builtins.py` (new `class TestBinaryGap`,
modeled on `class TestCollatzLength`, search that name, for the test
shapes above — place it near the existing `class TestToBin`). Once
merged, `README.md`'s existing `to_bin` bullet needs `binary_gap` added
right after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `dot_product` — dot product of two equal-length numeric lists

Add a standalone two-list-argument builtin, not another `is_*`/`nth_*`
pair — that gap list stayed exhausted this pass too (re-audited
programmatically: every unpaired `is_*` name is still one of the
already-rejected categories — multi-arg, string/list-shaped with no
integer ordering, a type predicate, or one of the confirmed-too-sparse-
or-slow names from earlier passes' History entries). `dot_product` sits
next to `mean`/`geometric_mean`/`harmonic_mean`/`median`/`variance`/
`std_dev` (`cinder/builtins.py`, search `def _std_dev`) as another
numeric-list statistic, but two-argument like `hamming_distance` (search
`def _hamming_distance`) rather than one — mirror that function's
equal-length validation shape (its own `len(string1) != len(string2)`
check) since `dot_product` has the identical failure mode for
mismatched-length inputs. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(dot_product([1, 2, 3], [4, 5, 6]));'
# -> <eval>:1:7: undefined name 'dot_product'
```

**What it does.** Given two lists of numbers of equal length, return the
sum of the pairwise products of their elements — the standard dot
(scalar) product: `a[0]*b[0] + a[1]*b[1] + ... + a[n-1]*b[n-1]`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `dot_product([1, 2, 3], [4, 5, 6])` is `32` (`1*4 + 2*5 + 3*6`).
- `dot_product([1, 0], [0, 1])` is `0` — orthogonal unit vectors.
- `dot_product([], [])` is `0` — two empty lists have no terms to sum,
  vacuously zero.
- `dot_product([-1, 2], [3, -4])` is `-11` (`-1*3 + 2*-4`).
- `dot_product([2, 2, 2], [3, 3, 3])` is `18`.
- `dot_product([1.5, 2.5], [2, 4])` is `13.0` (mixed int/float elements,
  ordinary numeric promotion — same as every other numeric-list builtin
  here).

Add directly after `_std_dev` (search `def _std_dev`, immediately before
`def _mode`) — keeps the new numeric-list statistic next to its closest
siblings:
```python
def _dot_product(arguments: list, line: int, column: int) -> object:
    _require_arity("dot_product", arguments, 2, line, column)
    first, second = arguments
    if not isinstance(first, list):
        raise CinderRuntimeError(
            f"dot_product() requires a list as its first argument, got {type_name(first)}",
            line, column,
        )
    if not isinstance(second, list):
        raise CinderRuntimeError(
            f"dot_product() requires a list as its second argument, got {type_name(second)}",
            line, column,
        )
    for element in first + second:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"dot_product() requires lists of numbers, got {type_name(element)}",
                line, column,
            )
    if len(first) != len(second):
        raise CinderRuntimeError(
            f"dot_product() requires lists of equal length, got lengths {len(first)} and {len(second)}",
            line, column,
        )
    total = 0
    for a, b in zip(first, second):
        total = total + a * b
    return total
```
Register the new dict entry (search `"std_dev": _std_dev,`, add
`"dot_product": _dot_product,` directly after it, before `"mode":
_mode,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `dot_product([1, 2, 3], [4, 5, 6])` is `32` and
  `dot_product([1.5, 2.5], [2, 4])` is `13.0`.
- `dot_product([], []);` is `0` — the empty-list case.
- `dot_product(123, [1]);` raises `CinderRuntimeError` matching
  `"dot_product\(\) requires a list as its first argument, got int"`.
- `dot_product([1], "x");` raises `CinderRuntimeError` matching
  `"dot_product\(\) requires a list as its second argument, got string"`.
- `dot_product([1, "a"], [1, 2]);` raises `CinderRuntimeError` matching
  `"dot_product\(\) requires lists of numbers, got string"`.
- `dot_product([1, 2], [1, 2, 3]);` raises `CinderRuntimeError` matching
  `"dot_product\(\) requires lists of equal length, got lengths 2 and 3"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_std_dev`, search
`def _std_dev`), `tests/test_builtins.py` (new `class TestDotProduct`,
modeled on `class TestHammingDistance`, search that name, for the
two-argument/equal-length test shapes above — place it near the existing
`class TestStdDev`/`class TestMode`). Once merged, `README.md`'s
existing `std_dev` bullet needs `dot_product` added right after it, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Standard library: `cumsum` — cumulative (running) sum of a numeric list

Add a standalone list-transform builtin sitting directly next to `sum`/
`product` (`cinder/builtins.py`, search `def _sum`, immediately before
`def _product`) — a numeric-list builtin that returns a list rather than
a scalar, the same shape shift `run_length_encode`/`run_length_decode`
already have from a single value to a structured list. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(cumsum([1, 2, 3]));'
# -> <eval>:1:7: undefined name 'cumsum' (did you mean 'sum'?)
```

**What it does.** Given a list of numbers, return a new list of the same
length where each element is the running total of every element up to
and including that position — `result[i] = list[0] + list[1] + ... +
list[i]`. An empty list returns an empty list.

Worked examples (confirmed via direct computation of the algorithm
below):
- `cumsum([1, 2, 3])` is `[1, 3, 6]`.
- `cumsum([])` is `[]` — the empty list has no running total to build,
  vacuously empty.
- `cumsum([5])` is `[5]` — a single-element list returns that element's
  own running total, itself.
- `cumsum([1, -2, 3, -4])` is `[1, -1, 2, -2]` — negative elements
  shrink the running total.
- `cumsum([1.5, 2.5, 1])` is `[1.5, 4.0, 5.0]` (mixed int/float
  elements, ordinary numeric promotion — same as `sum`/`product`).
- `cumsum([0, 0, 0])` is `[0, 0, 0]`.

Add directly after `_sum` (search `def _sum`, immediately before `def
_product`) — keeps the new running-total builtin next to the plain
total it generalizes:
```python
def _cumsum(arguments: list, line: int, column: int) -> object:
    _require_arity("cumsum", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"cumsum() requires a list, got {type_name(value)}", line, column
        )
    total = 0
    result = []
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"cumsum() requires a list of numbers, got {type_name(element)}", line, column
            )
        total = total + element
        result.append(total)
    return result
```
(Same validation shape as `_sum` itself — search `def _sum` — just
appending each running total to a result list instead of discarding
everything but the final one.) Register the new dict entry (search
`"sum": _sum,`, add `"cumsum": _cumsum,` directly after it, before
`"product": _product,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `cumsum([1, 2, 3])` is `[1, 3, 6]` and `cumsum([1.5, 2.5, 1])` is
  `[1.5, 4.0, 5.0]`.
- `cumsum([]);` is `[]` and `cumsum([5]);` is `[5]` — the empty-list and
  single-element cases.
- `cumsum(123);` raises `CinderRuntimeError` matching
  `"cumsum\(\) requires a list, got int"`.
- `cumsum([1, "a"]);` raises `CinderRuntimeError` matching
  `"cumsum\(\) requires a list of numbers, got string"` (mirror `sum`'s
  own non-numeric-element test for the exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_sum`, search `def
_sum`), `tests/test_builtins.py` (new `class TestCumsum`, modeled on
`class TestSum`, search that name, for the test shapes above — place it
near the existing `class TestSum`/`class TestProduct`). Once merged,
`README.md`'s existing `sum` bullet needs `cumsum` added right after it,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

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
