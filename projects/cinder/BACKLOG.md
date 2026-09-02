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

## 1. Standard library: `is_luhn_valid` — Luhn checksum validator for digit strings

Build: Cinder has plenty of digit-driven number predicates
(`is_keith_number` above, `is_kaprekar`, `is_armstrong`, ...) but nothing
that validates the classic Luhn checksum — the mod-10 algorithm used to
catch single-digit errors and transpositions in credit card numbers, IMEI
numbers, and similar identifiers (ISO/IEC 7812). It's a different shape of
task from the number predicates above: it operates on a **string** of
digit characters (an identifier like a card number, not a numeric value —
leading zeros matter and the input can be longer than fits comfortably as
an `int` for some real-world identifiers), and it's a checksum algorithm
rather than a digit-recurrence/digit-ending question. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_luhn_valid("4539148803436467"));'
# -> <eval>:1:7: undefined name 'is_luhn_valid'
```

Algorithm: starting from the rightmost digit and moving left, double
every second digit (i.e. the 2nd, 4th, 6th, ... digits counting from the
right); if a doubled digit exceeds 9, subtract 9 from it (equivalent to
summing its own two digits, e.g. `doubled 16` becomes `7`, the same as
`1 + 6`); sum every digit (doubled ones after the >9 correction,
untouched ones as-is); the string is Luhn-valid if that sum is a
multiple of 10.

Worked example, `"79927398713"` (the classic Wikipedia example, reading
right to left: `3,1,7,8,9,3,7,2,9,9,7`): digits at odd positions from
the right (2nd, 4th, ...: `1, 8, 3, 2, 9`) get doubled and corrected
(`2, 16->7, 6, 4, 18->9`), everything else stays put; the full sum is
`3+2+7+7+9+6+7+4+9+9+7 = 70`, a multiple of 10, so it's valid — flip
the last digit to `"79927398710"` and the same process sums to `67`, not
a multiple of 10, so it's invalid.

**Digit-character landmine**: do not use Python's `str.isdigit()`/`int()`
to validate/parse each character — `str.isdigit()` returns `True` for
non-ASCII Unicode digit characters like `"²"` (superscript two) that
`int()` cannot parse the way this checksum needs (it would either raise
or silently misinterpret the character's value). Check membership in the
literal ASCII set `"0123456789"` instead, e.g. `all(ch in "0123456789"
for ch in value)` — the same reason `is_ascii`'s own check (search `def
_is_ascii`) uses `.isascii()` rather than a looser Unicode-permissive
test where a narrower one is actually meant.

Add to `cinder/builtins.py`, directly after `_is_numeric_string` (search
`def _is_numeric_string`, immediately before `def _is_sorted`) — keeps
it grouped with the other string-shaped validators:
```python
def _is_luhn_valid(arguments: list, line: int, column: int) -> object:
    _require_arity("is_luhn_valid", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"is_luhn_valid() requires a string, got {type_name(value)}",
            line, column,
        )
    if not value or any(ch not in "0123456789" for ch in value):
        raise CinderRuntimeError(
            "is_luhn_valid() requires a non-empty string of ASCII digits",
            line, column,
        )
    total = 0
    for index, ch in enumerate(reversed(value)):
        digit = int(ch)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0
```
Also register the new dict entry (search `"is_numeric":
_is_numeric_string,`, add `"is_luhn_valid": _is_luhn_valid,` directly
after it, before `"is_sorted": _is_sorted,`).

Acceptance criteria:
- `is_luhn_valid("4539148803436467");` is `true` — a known-valid test
  Visa-format number.
- `is_luhn_valid("4539148803436468");` is `false` — same number with the
  last digit off by one, breaks the checksum.
- `is_luhn_valid("79927398713");` is `true` — the classic Wikipedia
  worked example above.
- `is_luhn_valid("79927398710");` is `false` — the same digits with the
  last one zeroed, from the same worked example.
- `is_luhn_valid("4111111111111111");` is `true` — another commonly used
  Luhn-valid test number, confirming the check isn't hardcoded to one
  length.
- `is_luhn_valid("0");` is `true` — single digit, sum is `0`, trivially
  a multiple of 10.
- `is_luhn_valid("9");` is `false` — single digit, sum is `9`, not a
  multiple of 10.
- `is_luhn_valid("0000000000");` is `true` — an all-zero identifier is a
  degenerate but valid case (sum `0`), not a domain error.
- `is_luhn_valid("");` raises `CinderRuntimeError` matching
  `"is_luhn_valid() requires a non-empty string of ASCII digits"` — the
  empty string is rejected outright rather than trivially "passing" with
  a vacuous sum of `0`.
- `is_luhn_valid("123a");` raises `CinderRuntimeError` matching the same
  message — any non-digit character anywhere in the string is a domain
  error, not just at the start/end.
- `is_luhn_valid("12 34");` raises the same error — whitespace inside the
  string is not silently stripped/ignored.
- `is_luhn_valid(4539148803436467);` (an int, not a string) raises
  `CinderRuntimeError` matching `"is_luhn_valid() requires a string, got
  int"` — the type check, not the digit-content check, fires first.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_numeric_string`,
search `def _is_numeric_string`), `tests/test_builtins.py` (new `class
TestIsLuhnValid`, modeled on `class TestIsNumeric`, search that name, for
the true/false/domain-edge/type-error test shapes above). Once merged,
`README.md`'s Builtins bullet needs `is_luhn_valid` added near
`is_numeric`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Language: `|` (union) operator for lists (set-style, mirrors list `&`/`-`)

Build: tasks 1 and 3 above give `&` list-list and map-map branches, and
`-` already has both (PR #356 map, task from an earlier pass for list).
Cinder's list builtins already answer the union question as a function
(`union()`, `cinder/builtins.py`, search `def _union`: dedupes the
concatenation of both lists left-to-right, so a value present in either
side survives exactly once, in first-seen order — the same convention
`intersection()`/`difference()`/`symmetric_difference()` share), but `|`
has no list meaning at all today — it is bitwise-int-only (`_bitwise_op`,
`cinder/interpreter.py`, search `def _bitwise_op`, unconditionally
requires both operands to be `int`). This task gives `union()` the same
infix spelling task 1 gives `intersection()` and the existing `-`
operator gives `difference()`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2, 3] | [2, 3, 4]);'
# -> <eval>:1:17: unsupported operand types for '|': list and list
```

Scope: list-list only, matching how `&`/`-` each got their list branch
as a task separate from any map branch — map-map `|` union is a
plausible future task, not this one. This task does not depend on
tasks 1-4 landing first; whichever order they land in, this task's own
diff only touches the `PIPE` branch, never the `AMP`/`MINUS` branches
those tasks add or already have.

Edit `cinder/interpreter.py`'s `_apply_binary_operator`, immediately
above the existing dispatch to `_bitwise_op` (search `TokenType.PIPE,`
inside the `if op in (` tuple that also lists `AMP`/`CARET`/`LSHIFT`/
`RSHIFT`): add a list-list special case for `PIPE` specifically,
reusing `values_equal`-based membership (the same pattern the `MINUS`
dict/list branches just above already use) rather than Python's native
`==`/`in`:
```python
        if op == TokenType.PIPE and isinstance(left, list) and isinstance(right, list):
            combined: list = []
            for element in left + right:
                if not any(values_equal(element, kept) for kept in combined):
                    combined.append(element)
            return combined
        if op in (
            TokenType.AMP,
            TokenType.PIPE,
            TokenType.CARET,
            TokenType.LSHIFT,
            TokenType.RSHIFT,
        ):
            return self._bitwise_op(operator, left, right, op)
```
(Only the new `if op == TokenType.PIPE and isinstance(left, list)...`
block is added, directly above the existing bitwise dispatch — `AMP`/
`CARET`/`LSHIFT`/`RSHIFT` and int-int `PIPE` all still fall through
unchanged to `_bitwise_op`. If tasks 1/3's own `AMP` list/map branches
have already landed by the time this task is implemented, they will
sit as separate `if op == TokenType.AMP and ...` blocks nearby — leave
them untouched; this task only adds the `PIPE` block.)

The compound-assignment desugaring (`|=`) already works for free once
`|` itself handles lists, exactly as `&=`/`-=`'s existing coverage
documents — no separate wiring needed.

Acceptance criteria (mirror `TestListIntersection`/`TestListDifference`'s
shape in `tests/test_interpreter.py`):
- `[1, 2, 3] | [2, 3, 4]` is `[1, 2, 3, 4]` — the basic case, left
  elements first in original order, then new right-only elements.
- `[1, 2, 2, 3] | [2]` is `[1, 2, 3]` — duplicates on either side are
  deduped, first occurrence kept.
- `[1, 2, 3] | []` is `[1, 2, 3]` (deduped) and `[] | [1, 2]` is
  `[1, 2]` — either empty side leaves the other's deduped elements.
- `[1, 2] | [1, 2]` is `[1, 2]` — full overlap, no duplicates added.
- `[1, 2] | [3, 4]` is `[1, 2, 3, 4]` — no overlap, simple concatenation
  (deduped, though there's nothing to dedupe here).
- Does not mutate inputs: `let a = [1, 2, 3]; let c = a | [4];` leaves
  `a` as `[1, 2, 3]` and `c` as `[1, 2, 3, 4]`.
- Left-associative: `[1] | [2] | [1, 3]` is `[1, 2, 3]`.
- Compound assignment works: `let xs = [1, 2]; xs |= [2, 3];` leaves
  `xs` as `[1, 2, 3]` (identifier target); also test an index target
  and a dot target, mirroring task 1's own compound-assignment cases.
- `[1, true, 2] | [true, 3]` is `[1, true, 2, 3]` — uses `values_equal`,
  not Python's native `==`/`in`, so `1` is not conflated with `true`
  when deduping.
- `2 | 3` (both ints) is still `3` — existing bitwise-OR behavior is
  unchanged, a regression guard.
- `[1, 2] | 3` and `2 | [1, 2]` still raise `CinderRuntimeError`
  matching `"unsupported operand types for '|': ..."` — mixed
  list/non-list operands remain a type error, same message shape
  `_bitwise_op` already produces.
- `[1, 2] | {"a": 1}` also raises the same type error — map operands
  are unsupported (deferred per the Scope note above).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`AMP`/`PIPE`/`CARET`/`LSHIFT`/`RSHIFT` dispatch, search
`TokenType.PIPE,`), `tests/test_interpreter.py` (new `class
TestListUnion`, modeled on `class TestListDifference`, search that
name, for the test shapes above). Once merged, `README.md`'s
language-operators bullet needs a list-`|` mention next to the
existing list `&`/`-` ones, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `is_polydivisible` — polydivisible number predicate

Build: Cinder has plenty of digit-position-based number predicates
(`is_disarium`, `cinder/builtins.py`, search `def _is_disarium`: each
digit raised to its 1-based position, summed, must equal the number
itself) but nothing that checks the classic *polydivisible* property —
a number is polydivisible when, reading its decimal digits left to
right, every prefix of length `i` is itself divisible by `i`: the
1-digit prefix by 1 (always true), the 2-digit prefix by 2, the 3-digit
prefix by 3, and so on up through the full number divided by its own
digit count. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_polydivisible(381654729));'
# -> <eval>:1:7: undefined name 'is_polydivisible'
```

Worked example, `381654729` (the largest polydivisible number that uses
each of the digits 1-9 exactly once, a well-known instance of this
property): prefix `3` div by 1 ✓, `38` div by 2 (`19`) ✓, `381` div by 3
(digit sum `12`) ✓, `3816` div by 4 (last two digits `16`) ✓, `38165`
div by 5 (ends in `5`) ✓, `381654` div by 6 (even and digit-sum-`27`
divisible by 3) ✓, `3816547` div by 7 (`545221 * 7`) ✓, `38165472` div
by 8 (last three digits `472 / 8 = 59`) ✓, `381654729` div by 9 (digit
sum `45`) ✓ — every prefix checks out, so it's polydivisible. Contrast
`106`: `1` div by 1 ✓, `10` div by 2 ✓, but `106` is not divisible by 3
(digit sum `7`), so it fails at the last prefix and the whole number is
not polydivisible.

Add to `cinder/builtins.py`, directly after `_is_disarium` (search `def
_is_disarium`, immediately before `def _is_pandigital`) — keeps it
grouped with the other digit-position predicates:
```python
def _is_polydivisible(arguments: list, line: int, column: int) -> object:
    _require_arity("is_polydivisible", arguments, 1, line, column)
    value = _require_int("is_polydivisible", arguments[0], line, column)
    if value < 0:
        return False
    digits = str(value)
    return all(int(digits[:i]) % i == 0 for i in range(1, len(digits) + 1))
```
Also register the new dict entry (search `"is_disarium":
_is_disarium,`, add `"is_polydivisible": _is_polydivisible,` directly
after it, before `"is_pandigital": _is_pandigital,`).

Acceptance criteria:
- `is_polydivisible(381654729);` is `true` — the classic pandigital
  worked example above.
- `is_polydivisible(106);` is `false` — fails at the 3-digit prefix
  (`106 % 3 != 0`), the contrasting worked example above.
- `is_polydivisible(0);` is `true` — a single digit's 1-digit prefix is
  always divisible by 1, trivially valid (matches `is_disarium(0)`'s
  own trivially-true single-digit convention, same file).
- `is_polydivisible(9);` is `true` — same trivial single-digit case,
  non-zero.
- `is_polydivisible(12);` is `true` — `1 % 1 == 0` and `12 % 2 == 0`.
- `is_polydivisible(11);` is `false` — `1 % 1 == 0` but `11 % 2 != 0`.
- `is_polydivisible(105);` is `true` — `1 % 1 == 0`, `10 % 2 == 0`,
  `105 % 3 == 0`.
- `is_polydivisible(1230);` is `false` — fails at the 4-digit prefix
  (`1230 % 4 != 0`), confirming the check runs all the way to the full
  number, not just a leading few digits.
- `is_polydivisible(-381654729);` is `false` — negative numbers return
  `false` outright, matching `is_disarium`/`is_armstrong`'s own
  negative-number convention in this file, not a domain error.
- `is_polydivisible(5);` (a bool-free plain int) and
  `is_polydivisible(true);` — the latter raises `CinderRuntimeError`
  matching `"is_polydivisible() requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `is_polydivisible("106");` raises `CinderRuntimeError` matching
  `"is_polydivisible() requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_disarium`,
search `def _is_disarium`), `tests/test_builtins.py` (new `class
TestIsPolydivisible`, modeled on `class TestIsDisarium`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `is_polydivisible` added near `is_disarium`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 4. Language: `^` (symmetric difference) operator for lists (set-style, mirrors list `&`/`|`/`-`)

Build: tasks 1/3 above give list-list `&`/`|` infix spellings of the
existing `intersection()`/`union()` builtins, and list-list `-` (an
earlier pass) already gave `difference()` the same treatment. Cinder's
list builtins already answer the symmetric-difference question as a
function (`symmetric_difference()`, `cinder/builtins.py`, search `def
_symmetric_difference`: dedupes each side independently, then returns
left-only elements followed by right-only elements — the same
"dedupe-per-side, this-side-first" convention `intersection()`/
`union()`/`difference()` already share), but `^` has no list meaning
today — it is bitwise-int-only (`_bitwise_op`, `cinder/interpreter.py`,
search `def _bitwise_op`, the `TokenType.CARET` branch does `left ^
right` and unconditionally requires both operands to be `int`). This
task completes the set-operator family that tasks 1/3 and the earlier
`-` task started — after this lands, `&`/`|`/`-`/`^` all have list
meanings mirroring their same-named builtins. Verify the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2, 3] ^ [2, 3, 4]);'
# -> <eval>:1:17: unsupported operand types for '^': list and list
```

Scope: list-list only, matching how `&`/`|`/`-` each got their list
branch as a task separate from any map branch — map-map `^` symmetric
difference is a plausible future task, not this one. This task does
not depend on tasks 1-4 landing first; whichever order they land in,
this task's own diff only touches the `CARET` branch, never the
`AMP`/`PIPE`/`MINUS` branches those tasks add or already have.

Edit `cinder/interpreter.py`'s `_apply_binary_operator`, immediately
above the existing dispatch to `_bitwise_op` (search `TokenType.PIPE,`
inside the `if op in (` tuple that also lists `AMP`/`CARET`/`LSHIFT`/
`RSHIFT`): add a list-list special case for `CARET` specifically,
reusing `values_equal`-based membership (the same pattern the `MINUS`/
`AMP` list branches already use) rather than Python's native
`==`/`in`:
```python
        if op == TokenType.CARET and isinstance(left, list) and isinstance(right, list):
            left_deduped: list = []
            for element in left:
                if not any(values_equal(element, kept) for kept in left_deduped):
                    left_deduped.append(element)
            right_deduped: list = []
            for element in right:
                if not any(values_equal(element, kept) for kept in right_deduped):
                    right_deduped.append(element)
            return [
                element for element in left_deduped
                if not contains_value(right, element, operator.line, operator.column)
            ] + [
                element for element in right_deduped
                if not contains_value(left, element, operator.line, operator.column)
            ]
        if op in (
            TokenType.AMP,
            TokenType.PIPE,
            TokenType.CARET,
            TokenType.LSHIFT,
            TokenType.RSHIFT,
        ):
            return self._bitwise_op(operator, left, right, op)
```
(Only the new `if op == TokenType.CARET and isinstance(left, list)...`
block is added, directly above the existing bitwise dispatch —
`AMP`/`PIPE`/`LSHIFT`/`RSHIFT` and int-int `CARET` all still fall
through unchanged to `_bitwise_op`. If task 3's own `PIPE` list branch
has already landed by the time this task is implemented, it will sit
as a separate `if op == TokenType.PIPE and ...` block nearby — leave it
untouched; this task only adds the `CARET` block.)

The compound-assignment desugaring (`^=`) already works for free once
`^` itself handles lists, exactly as `&=`/`|=`/`-='s existing coverage
documents — no separate wiring needed.

Acceptance criteria (mirror `TestListIntersection`/`TestListDifference`'s
shape in `tests/test_interpreter.py`):
- `[1, 2, 3] ^ [2, 3, 4]` is `[1, 4]` — the basic case, left-only
  elements first (in original order), then right-only elements.
- `[1, 1, 2] ^ [2, 2, 3]` is `[1, 3]` — duplicates on either side are
  deduped before the comparison, first occurrence kept.
- `[1, 2, 3] ^ []` is `[1, 2, 3]` (deduped) and `[] ^ [1, 2]` is
  `[1, 2]` — either empty side leaves the other's deduped elements.
- `[1, 2] ^ [1, 2]` is `[]` — full overlap, nothing left on either
  side.
- `[1, 2] ^ [3, 4]` is `[1, 2, 3, 4]` — no overlap, simple
  concatenation of the deduped sides.
- Does not mutate inputs: `let a = [1, 2, 3]; let c = a ^ [2, 4];`
  leaves `a` as `[1, 2, 3]` and `c` as `[1, 3, 4]`.
- Left-associative: `[1, 2] ^ [2, 3] ^ [3, 4]` is `[1, 4]` (first pass
  `[1, 2] ^ [2, 3]` is `[1, 3]`, then `[1, 3] ^ [3, 4]` is `[1, 4]`).
- Compound assignment works: `let xs = [1, 2]; xs ^= [2, 3];` leaves
  `xs` as `[1, 3]` (identifier target); also test an index target and
  a dot target, mirroring task 1's own compound-assignment cases.
- `[1, true, 2] ^ [true, 3]` is `[1, 2, 3]` — uses `values_equal`, not
  Python's native `==`/`in`, so `1` is not conflated with `true` when
  deduping/comparing.
- `2 ^ 3` (both ints) is still `1` — existing bitwise-XOR behavior is
  unchanged, a regression guard.
- `[1, 2] ^ 3` and `2 ^ [1, 2]` still raise `CinderRuntimeError`
  matching `"unsupported operand types for '^': ..."` — mixed
  list/non-list operands remain a type error, same message shape
  `_bitwise_op` already produces.
- `[1, 2] ^ {"a": 1}` also raises the same type error — map operands
  are unsupported (deferred per the Scope note above).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`AMP`/`PIPE`/`CARET`/`LSHIFT`/`RSHIFT` dispatch, search
`TokenType.PIPE,`), `tests/test_interpreter.py` (new `class
TestListSymmetricDifference`, modeled on `class TestListDifference`,
search that name, for the test shapes above). Once merged, `README.md`'s
language-operators bullet needs a list-`^` mention next to the existing
list `&`/`|`/`-` ones, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

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
