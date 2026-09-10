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

## 1. Standard library: `dot_product` — dot product of two equal-length numeric lists

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

## 2. Standard library: `cumsum` — cumulative (running) sum of a numeric list

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

## 3. Standard library: `caesar_cipher` — generalize `rot13` to an arbitrary integer shift

Add a standalone two-argument string builtin directly after `_rot13`
(`cinder/builtins.py`, search `def _rot13`, immediately before `def
_is_palindrome`) — `rot13` is the fixed-shift-of-13 special case of the
classic Caesar cipher; this generalizes it to any integer shift, the
same "generalize a fixed-parameter builtin into a parameterized sibling"
move `to_roman`/`from_roman` and `cumsum`/`sum` already made elsewhere in
this codebase. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(caesar_cipher("abc", 3));'
# -> <eval>:1:7: undefined name 'caesar_cipher'
```

**What it does.** Given a string and an integer shift, rotate every
ASCII letter forward through its own case's alphabet by `shift`
positions, wrapping around at the end (`z` shifted by `1` becomes `a`);
non-letter characters (digits, punctuation, whitespace) pass through
unchanged. The shift may be zero, negative, or larger than 26 — always
reduce it modulo 26 first (Python's `%` already returns a non-negative
result for a negative left operand, so no extra sign-handling is
needed). `rot13(s)` is exactly `caesar_cipher(s, 13)` for every `s`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `caesar_cipher("abc", 3)` is `"def"`.
- `caesar_cipher("xyz", 3)` is `"abc"` — wraps around past `z`.
- `caesar_cipher("ABC", 3)` is `"DEF"` — case preserved.
- `caesar_cipher("Hello, World!", 5)` is `"Mjqqt, Btwqi!"` — mixed case,
  punctuation, and a space all pass through correctly.
- `caesar_cipher("abc", 0)` is `"abc"` — a zero shift is the identity.
- `caesar_cipher("abc", 29)` is `"def"` — same as shift `3`, since `29 %
  26 == 3`.
- `caesar_cipher("abc", -1)` is `"zab"` — a negative shift rotates
  backward, wrapping past `a`.
- `caesar_cipher("rot13 test", 13)` is `"ebg13 grfg"`, identical to
  `rot13("rot13 test")` — confirms the `rot13`-is-a-special-case
  relationship above.
- `caesar_cipher("", 5)` is `""` — the empty string has no letters to
  shift.

Add directly after `_rot13` (search `def _rot13`, immediately before
`def _is_palindrome`) — keeps the new parameterized cipher next to the
fixed-shift sibling it generalizes:
```python
def _caesar_cipher(arguments: list, line: int, column: int) -> object:
    _require_arity("caesar_cipher", arguments, 2, line, column)
    value, shift = arguments
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"caesar_cipher() requires a string, got {type_name(value)}", line, column
        )
    if not isinstance(shift, int) or isinstance(shift, bool):
        raise CinderRuntimeError(
            f"caesar_cipher() requires an int, got {type_name(shift)}", line, column
        )
    shift = shift % 26
    result = []
    for ch in value:
        if "a" <= ch <= "z":
            result.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= ch <= "Z":
            result.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
        else:
            result.append(ch)
    return "".join(result)
```
(Same per-character case-branch shape as `_rot13` itself — search `def
_rot13` — just with `shift` substituted for the hardcoded `13`, reduced
modulo 26 once up front so the per-character arithmetic never has to
think about out-of-range or negative shifts.) Register the new dict
entry (search `"rot13": _rot13,`, add `"caesar_cipher":
_caesar_cipher,` directly after it, before `"is_palindrome":
_is_palindrome,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `caesar_cipher("Hello, World!", 5)` is `"Mjqqt, Btwqi!"` and
  `caesar_cipher("abc", 29)` is `"def"`.
- `caesar_cipher("abc", -1);` is `"zab"` and `caesar_cipher("abc", 0);`
  is `"abc"` — the negative-shift and zero-shift cases.
- For at least one non-trivial string `s`, `caesar_cipher(s, 13)` equals
  `rot13(s)` — the relationship the spec above depends on.
- `caesar_cipher(123, 3);` raises `CinderRuntimeError` matching
  `"caesar_cipher\(\) requires a string, got int"`.
- `caesar_cipher("abc", "x");` raises `CinderRuntimeError` matching
  `"caesar_cipher\(\) requires an int, got string"`.
- `caesar_cipher("abc", true);` raises `CinderRuntimeError` matching
  `"caesar_cipher\(\) requires an int, got bool"` (mirror the codebase's
  standard bool-is-not-an-int convention, same as `rotate`'s own second
  argument).
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_rot13`, search `def
_rot13`), `tests/test_builtins.py` (new `class TestCaesarCipher`,
modeled on `class TestRot13`, search that name, for the test shapes
above — place it near the existing `class TestRot13`). Once merged,
`README.md`'s existing `rot13` bullet needs `caesar_cipher` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `cumprod` — cumulative (running) product of a numeric list

Add a standalone list-transform builtin directly after `_product`
(`cinder/builtins.py`, search `def _product`, immediately before `def
_mean`) — the multiplicative sibling of task 2's `cumsum`, the same
scalar-to-running-list shape shift applied to `product` instead of
`sum`. (If task 2 has already merged by the time this is picked up,
`_cumsum` will sit between `_sum` and `_product`; this task's anchor is
`_product` itself, so the insertion point is unaffected either way.)
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(cumprod([1, 2, 3]));'
# -> <eval>:1:7: undefined name 'cumprod'
```

**What it does.** Given a list of numbers, return a new list of the same
length where each element is the running product of every element up to
and including that position — `result[i] = list[0] * list[1] * ... *
list[i]`. An empty list returns an empty list.

Worked examples (confirmed via direct computation of the algorithm
below):
- `cumprod([1, 2, 3])` is `[1, 2, 6]`.
- `cumprod([])` is `[]` — the empty list has no running product to
  build, vacuously empty.
- `cumprod([5])` is `[5]` — a single-element list returns that element's
  own running product, itself.
- `cumprod([1, -2, 3, -4])` is `[1, -2, -6, 24]` — negative elements
  flip the running product's sign.
- `cumprod([1.5, 2, 2])` is `[1.5, 3.0, 6.0]` (mixed int/float elements,
  ordinary numeric promotion — same as `sum`/`product`/`cumsum`).
- `cumprod([2, 0, 3])` is `[2, 0, 0]` — a zero permanently zeroes out
  every running product after it.

Add directly after `_product` (search `def _product`, immediately
before `def _mean`) — keeps the new running-product builtin next to the
plain total it generalizes:
```python
def _cumprod(arguments: list, line: int, column: int) -> object:
    _require_arity("cumprod", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"cumprod() requires a list, got {type_name(value)}", line, column
        )
    total = 1
    result = []
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"cumprod() requires a list of numbers, got {type_name(element)}", line, column
            )
        total = total * element
        result.append(total)
    return result
```
(Same validation shape as `_product` itself — search `def _product` —
just appending each running product to a result list instead of
discarding everything but the final one, mirroring `_cumsum`'s own
relationship to `_sum`.) Register the new dict entry (search
`"product": _product,`, add `"cumprod": _cumprod,` directly after it,
before `"mean": _mean,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `cumprod([1, 2, 3])` is `[1, 2, 6]` and `cumprod([1.5, 2, 2])` is
  `[1.5, 3.0, 6.0]`.
- `cumprod([]);` is `[]` and `cumprod([5]);` is `[5]` — the empty-list
  and single-element cases.
- `cumprod([2, 0, 3]);` is `[2, 0, 0]` — the zero-propagation case.
- `cumprod(123);` raises `CinderRuntimeError` matching
  `"cumprod\(\) requires a list, got int"`.
- `cumprod([1, "a"]);` raises `CinderRuntimeError` matching
  `"cumprod\(\) requires a list of numbers, got string"` (mirror
  `product`'s own non-numeric-element test for the exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_product`, search
`def _product`), `tests/test_builtins.py` (new `class TestCumprod`,
modeled on `class TestProduct`, search that name, for the test shapes
above — place it near the existing `class TestProduct`). Once merged,
`README.md`'s existing `product` bullet needs `cumprod` added right
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
