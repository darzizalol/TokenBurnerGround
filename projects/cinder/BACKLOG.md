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

## 1. Language: `|` (union) operator for lists (set-style, mirrors list `&`/`-`)

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

## 2. Standard library: `is_polydivisible` — polydivisible number predicate

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

## 3. Language: `^` (symmetric difference) operator for lists (set-style, mirrors list `&`/`|`/`-`)

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

## 4. Standard library: `is_self_number` — Colombian/self-number predicate

Build: Cinder already has two digit-sum-iteration predicates sitting
side by side (`is_happy_number`/`is_sad_number`, `cinder/builtins.py`,
search `def _is_happy_number`: repeatedly replace the value with the
sum of its digits' squares and watch for a cycle) but nothing that
checks the unrelated *self number* (a.k.a. Colombian number) property —
a number `n` is a self number when no smaller number `m` "generates"
it via `m + digit_sum(m) = n` (plain digit sum, not sum-of-squares —
a different digit function from the happy/sad pair, and no iteration:
just one generator search). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_self_number(20));'
# -> <eval>:1:7: undefined name 'is_self_number'
```

Definition and worked examples: `n` is a self number if there is no
`m` with `m + digit_sum(m) == n`. `20` is a self number: checking
every `m` from `1` to `19`, none of `1+1=2`, `2+2=4`, ..., `19+10=29`
lands on `20` (the closest misses are `14+5=19` and `15+6=21` — `20`
sits in the gap), so nothing generates it. `21` is *not* a self number:
`15 + digit_sum(15) = 15 + 6 = 21`, so `15` generates it. Single-digit
odd numbers are all self numbers (`1, 3, 5, 7, 9`) while single-digit
even numbers are not (e.g. `2 = 1 + digit_sum(1)`, `4 = 2 +
digit_sum(2)`) — this matches OEIS A003052, whose first terms are `1,
3, 5, 7, 9, 20, 31, 42, 53, 64, 75, 86, 97, 108, 110, 121, ...`.

Algorithm: any generator `m` of `n` must satisfy `m < n` (since
`digit_sum(m) >= 0`, with equality only at `m = 0`) and `m >= n - 9*d`
where `d` is `n`'s digit count (since `digit_sum(m) <= 9*d` for any
`m` with at most `d` digits, capping how far below `n` a generator can
sit). Search only that bounded window rather than every `m` from `0`
to `n`:
```python
def _is_self_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_self_number", arguments, 1, line, column)
    value = _require_int("is_self_number", arguments[0], line, column)
    if value < 0:
        return False
    digit_count = len(str(value))
    lower_bound = max(0, value - 9 * digit_count)
    for candidate in range(lower_bound, value):
        if candidate + sum(int(digit) for digit in str(candidate)) == value:
            return False
    return True
```
Add this directly after `_is_sad_number` (search `def _is_sad_number`,
immediately before `def _nth_happy_number`) — keeps it grouped with
the file's other digit-sum predicates even though the underlying
digit function (plain sum, not sum-of-squares) and check (a bounded
generator search, not a cycle-detecting loop) both differ. Also
register the new dict entry (search `"is_sad_number":
_is_sad_number,`, add `"is_self_number": _is_self_number,` directly
after it, before `"nth_happy_number": _nth_happy_number,`).

Acceptance criteria:
- `is_self_number(20);` is `true` — the smallest two-digit self
  number, the worked example above.
- `is_self_number(21);` is `false` — generated by `15` (`15 +
  digit_sum(15) = 21`), the contrasting worked example above.
- `is_self_number(1);`, `is_self_number(3);`, `is_self_number(9);` are
  all `true` — single-digit odd numbers, matching OEIS A003052's first
  terms.
- `is_self_number(2);`, `is_self_number(4);`, `is_self_number(8);` are
  all `false` — single-digit even numbers, each generated by `n/2`
  (e.g. `2 = 1 + digit_sum(1)`).
- `is_self_number(31);`, `is_self_number(42);`, `is_self_number(97);`,
  `is_self_number(121);` are all `true` — further OEIS A003052 terms,
  confirming the check scales past two digits.
- `is_self_number(100);` and `is_self_number(101);` are both `false` —
  three-digit numbers with generators (`91 + digit_sum(91) = 100`,
  `91 + digit_sum(91)`... use `95 + 6 = 101`), confirming the bounded
  search window doesn't cut off valid generators early.
- `is_self_number(0);` is `true` — no negative `m` exists to generate
  it, a trivial edge rather than a domain error.
- `is_self_number(-5);` is `false` — negative numbers are not self
  numbers outright, matching `is_happy_number`/`is_perfect_number`'s
  own negative-number convention in this file (return `false`, don't
  raise).
- `is_self_number(true);` raises `CinderRuntimeError` matching
  `"is_self_number() requires an int, got bool"` — `_require_int`
  rejects `bool` even though Cinder's `bool` is a Python `int`
  subclass, same guard every other int-only predicate in this file
  relies on.
- `is_self_number("20");` raises `CinderRuntimeError` matching
  `"is_self_number() requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_sad_number`,
search `def _is_sad_number`), `tests/test_builtins.py` (new `class
TestIsSelfNumber`, modeled on `class TestIsSadNumber`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `is_self_number` added near `is_happy_number`/
`is_sad_number`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 5. Language: `|` (union) operator for maps (key-based, mirrors map `&`/`-`'s "left's values win" convention)

Build: map `&` (intersection, PR #369) and map `-` (difference, an earlier
pass) both follow the same "keys decide, left's values win" convention
(`cinder/interpreter.py`, search `TokenType.AMP and isinstance(left,
dict)`: `{key: value for key, value in left.items() if key in right}`
keeps left's value for any shared key). Map `+` already exists
(`_apply_binary_operator`'s `PLUS` branch, search `isinstance(left,
dict) and isinstance(right, dict)`) but is a *general* merge where
**right's** values win on conflicts (`result = dict(left); result.update(right)`)
— it is not spelled as a set operator and does not follow the `&`/`-`
family's left-wins convention. This task gives maps a `|` union that
*does* follow that convention: all keys from both sides, left's value
wins when a key exists in both. Verify the gap:
```sh
python3 -m cinder.cli eval 'print({"a": 1} | {"b": 2});'
# -> <eval>:1:15: unsupported operand types for '|': map and map
```

Scope: map-map only. This is the map-side counterpart deferred by
`BACKLOG.md` task 1's own Scope note ("map-map `|` union is a plausible
future task, not this one"). This task does not depend on task 1 (list
`|`) landing first, in either order: each touches its own `isinstance`
branch under the `PIPE` dispatch and neither reads the other's code. If
task 1 has already landed, its `if op == TokenType.PIPE and
isinstance(left, list)...` block will sit nearby — leave it untouched;
this task only adds a dict-dict block.

Edit `cinder/interpreter.py`'s `_apply_binary_operator`, immediately
above the existing dispatch to `_bitwise_op` (search `TokenType.PIPE,`
inside the `if op in (` tuple that also lists `AMP`/`CARET`/`LSHIFT`/
`RSHIFT`): add a dict-dict special case for `PIPE`:
```python
        if op == TokenType.PIPE and isinstance(left, dict) and isinstance(right, dict):
            result = dict(right)
            result.update(left)
            return result
```
(Starting from `right` and overlaying `left` on top means: right-only
keys survive from the base, left-only keys get added, and any key
present in both ends up holding left's value because `update(left)`
applies last — this is the opposite base/overlay order from `+`'s
`dict(left); result.update(right)`, which is exactly why `+` and this
new `|` disagree on conflicts. Only this new block is added; the `AMP`
dict block and any list `PIPE` block from task 1 are untouched.)

The compound-assignment desugaring (`|=`) already works for free once
`|` itself handles maps, exactly as `&=`/`-='s existing coverage
documents — no separate wiring needed.

Acceptance criteria (mirror `TestMapIntersection`/`TestMapDifference`'s
shape in `tests/test_interpreter.py`; map equality in these tests is by
content via `assertEqual`, not key order, so don't assert on ordering):
- `{"a": 1, "b": 2} | {"a": 99, "c": 3}` is `{"a": 1, "b": 2, "c": 3}` —
  shared key `"a"` keeps left's value `1`, not right's `99`.
- `{"a": 1} | {}` is `{"a": 1}` and `{} | {"a": 1}` is `{"a": 1}` —
  either empty side leaves the other's entries untouched.
- `{"a": 1, "b": 2} | {"a": 1, "b": 2}` is `{"a": 1, "b": 2}` — full
  overlap, both sides agree so the result is unambiguous.
- `{"a": 1} | {"b": 2}` is `{"a": 1, "b": 2}` — disjoint keys, simple
  combination.
- Does not mutate inputs: `let m = {"a": 1}; let c = m | {"a": 2, "b": 3};`
  leaves `m` as `{"a": 1}` and `c` as `{"a": 1, "b": 3}`.
- Left-associative: `{"a": 1} | {"a": 2, "b": 2} | {"a": 3, "c": 3}` is
  `{"a": 1, "b": 2, "c": 3}` (first pass keeps `"a": 1` since it's the
  left side of the first `|`; that result is then the left side of the
  second `|`, so `"a": 1` still wins over the third map's `"a": 3`).
- Compound assignment works: `let m = {"a": 1}; m |= {"a": 2, "b": 2};`
  leaves `m` as `{"a": 1, "b": 2}` (identifier target); also test an
  index target and a dot target, mirroring `TestMapIntersection`'s own
  compound-assignment cases.
- `2 | 3` (both ints) is still `3` — existing bitwise-OR behavior is
  unchanged, a regression guard.
- `{"a": 1} | 3` and `2 | {"a": 1}` still raise `CinderRuntimeError`
  matching `"unsupported operand types for '|': ..."` — mixed
  map/non-map operands remain a type error.
- `{"a": 1} | [1, 2]` also raises the same type error — list operands
  are unsupported by the dict branch (and, unless task 1 has already
  landed first, by the list branch too — either way this task asserts
  only the map-vs-list mismatch case, not list-vs-list).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`AMP`/`PIPE`/`CARET`/`LSHIFT`/`RSHIFT` dispatch, search
`TokenType.PIPE,`), `tests/test_interpreter.py` (new `class
TestMapUnion`, modeled on `class TestMapIntersection`, search that
name, for the test shapes above). Once merged, `README.md`'s
language-operators bullet needs a map-`|` mention next to the existing
map `&`/`-` ones, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `is_weird_number` — abundant but not semiperfect

Build: Cinder already has the perfect/abundant/deficient family
(`_is_perfect_number`/`_is_abundant`/`_is_deficient`, `cinder/builtins.py`,
search `def _is_deficient`: each sums a number's proper divisors via
trial division up to `math.isqrt(value)` and compares the sum to the
number) but nothing that goes one step further into *weird numbers* — a
number is weird when it is abundant (its proper divisors sum to more
than the number) **and** not semiperfect (no subset of its proper
divisors sums exactly to the number). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_weird_number(70));'
# -> <eval>:1:7: undefined name 'is_weird_number'
```

Worked examples: `70` is the smallest weird number — its proper
divisors are `1, 2, 5, 7, 10, 14, 35` (sum `74 > 70`, abundant), and no
subset of `{1, 2, 5, 7, 10, 14, 35}` sums to exactly `70`, so it's not
semiperfect either. Contrast `20`: proper divisors `1, 2, 4, 5, 10` (sum
`22 > 20`, abundant), but `10 + 5 + 4 + 1 = 20` — a subset does sum to
the number, so `20` is semiperfect and therefore *not* weird despite
being abundant. `12` is the same story: divisors `1, 2, 3, 4, 6` (sum
`16 > 12`, abundant) but `6 + 4 + 2 = 12`, semiperfect, not weird. `6`
and `28` are perfect (divisors sum to exactly the number, not more), so
they fail the abundance check outright and are not weird either. The
next few weird numbers after `70` are `836`, `4030`, `5830`, `7192`,
`7912`, `9272`, `10430`, ... (OEIS A006037).

Add to `cinder/builtins.py`, directly after `_is_deficient` (search `def
_is_deficient`, immediately before `def _is_automorphic`) — keeps it
grouped with the other proper-divisor-sum predicates:
```python
def _is_weird_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_weird_number", arguments, 1, line, column)
    value = _require_int("is_weird_number", arguments[0], line, column)
    if value < 2:
        return False
    divisors = [1]
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            divisors.append(divisor)
            complement = value // divisor
            if complement != divisor:
                divisors.append(complement)
    if sum(divisors) <= value:
        return False
    reachable = {0}
    for divisor in divisors:
        reachable |= {total + divisor for total in reachable if total + divisor <= value}
    return value not in reachable
```
(The `reachable` loop is a standard subset-sum sweep, bounded above by
`value` at every step so it never grows unbounded — proper divisors are
few even for large composite numbers, so this stays fast.) Also
register the new dict entry (search `"is_deficient": _is_deficient,`,
add `"is_weird_number": _is_weird_number,` directly after it, before
`"is_automorphic": _is_automorphic,`).

Acceptance criteria:
- `is_weird_number(70);` is `true` — the smallest weird number, the
  worked example above.
- `is_weird_number(836);`, `is_weird_number(4030);`,
  `is_weird_number(5830);` are all `true` — further OEIS A006037 terms,
  confirming the check scales past the smallest instance.
- `is_weird_number(20);` and `is_weird_number(12);` are both `false` —
  abundant but semiperfect, the two contrasting worked examples above.
- `is_weird_number(24);` is `false` — another abundant-but-semiperfect
  number (`24`'s divisors `1, 2, 3, 4, 6, 8, 12` sum to `36`, but
  `12 + 8 + 4 = 24`).
- `is_weird_number(6);` and `is_weird_number(28);` are both `false` —
  perfect numbers, not abundant at all (sum of proper divisors equals
  the number, not more), so they fail before the semiperfect check even
  runs.
- `is_weird_number(1);`, `is_weird_number(0);` are both `false` —
  trivially not abundant.
- `is_weird_number(-70);` is `false` — negative numbers return `false`
  outright, matching `is_abundant`/`is_deficient`'s own negative-number
  convention in this file, not a domain error.
- `is_weird_number(true);` raises `CinderRuntimeError` matching
  `"is_weird_number() requires an int, got bool"`, since `_require_int`
  rejects `bool` even though Cinder's `bool` is a Python `int`
  subclass (same guard every other int-only predicate in this file
  already relies on).
- `is_weird_number("70");` raises `CinderRuntimeError` matching
  `"is_weird_number() requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_deficient`,
search `def _is_deficient`), `tests/test_builtins.py` (new `class
TestIsWeirdNumber`, modeled on `class TestIsAbundant`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `is_weird_number` added near `is_abundant`/`is_deficient`,
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
