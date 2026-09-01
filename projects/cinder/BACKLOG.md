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

## 1. Language: `throw`/`catch` carry any value, not just strings [claimed 2026-09-01T18:57:32Z]

Build: `throw` (`cinder/interpreter.py`, search `if isinstance(stmt,
ThrowStmt):`) currently rejects any thrown value that isn't a `str`, and
`catch (e)` (`_execute_try`, search `def _execute_try`) always binds `e`
to `error.message` — the *string* every `CinderRuntimeError` carries,
whether it came from a user `throw` or an internal type/arity error. This
is more than just a limitation: because the "must be a string" check
itself raises a `CinderRuntimeError`, throwing a non-string value gets
*caught by the surrounding `catch`* with `e` bound to the check's own
error text, not the value the user actually threw — a confusing double
failure, not a clean rejection. Verify the gap:
```sh
python3 -m cinder.cli eval 'try { throw {"kind": "MyError", "msg": "oops"}; } catch (e) { print(e.msg); }'
# -> <eval>:1:70: string index must be an int, got string
#    (e is bound to "throw requires a string message, got map" — the
#    type-check's own message, not the thrown map — so `.msg` tries to
#    index that string and blows up on an unrelated error)
```

This task lets `throw` accept any Cinder value and makes `catch` bind
the original value, not a stringified message — while leaving every
*internal* error (type errors, arity errors, etc., the ~430 other
`CinderRuntimeError(...)` call sites across `cinder/interpreter.py` and
`cinder/builtins.py`) behaving exactly as before, since none of those
call sites pass the new field described below.

Edit two files:

1. `cinder/errors.py`'s `CinderRuntimeError` (search `class
   CinderRuntimeError`): add an optional `value` field, defaulting to
   the error's own `message` when not given. Use a module-level sentinel
   (not `None`) so a genuinely thrown `nil` — which is Python `None` at
   runtime, see `PROJECT.md`'s truthiness note — isn't mistaken for "no
   value supplied":
```python
_UNSET = object()


class CinderRuntimeError(CinderError):
    """Raised by the interpreter for errors detected during evaluation.

    `frames` records the call chain the error passed through on its way out,
    one `(function_name, call_line, call_column)` tuple per call-site,
    innermost call first. Empty for an error raised directly at top level.

    `value` is the original Cinder value a `catch (e)` clause binds `e`
    to. It defaults to `message` itself (every internal engine error is,
    in effect, a string-valued exception) unless explicitly overridden —
    `ThrowStmt` handling is the only caller that does, passing the
    literal value the user threw.
    """

    def __init__(
        self, message: str, line: int, column: int, value: object = _UNSET
    ):
        super().__init__(message, line, column)
        self.frames: list[tuple[str, int, int]] = []
        self.value = message if value is _UNSET else value
```
(Every other one of the ~430 existing `CinderRuntimeError(...)` call
sites is unchanged — none of them pass `value=`, so `error.value ==
error.message` for all of them, exactly matching today's behavior.)

2. `cinder/interpreter.py`, two spots:
   - The `ThrowStmt` branch of `execute` (search `if isinstance(stmt,
     ThrowStmt):`): drop the string-only type check entirely and pass
     the evaluated value straight through, using the module's existing
     `stringify` (search `def stringify`, already used elsewhere in this
     file — no new import needed) to build the display message:
```python
        if isinstance(stmt, ThrowStmt):
            value = self.evaluate(stmt.expression, env)
            raise CinderRuntimeError(
                stringify(value), stmt.line, stmt.column, value=value
            )
```
   - `_execute_try` (search `def _execute_try`): bind the catch name to
     `error.value` instead of `error.message`:
```python
                catch_env = Environment(env)
                if stmt.catch_name is not None:
                    catch_env.define(stmt.catch_name, error.value)
```
(Only the `error.message` → `error.value` change; everything else in
`_execute_try`, including the `finally` handling, is untouched.)

Acceptance criteria:
- `try { throw "boom"; } catch (e) { print(e); }` still prints `boom` —
  regression guard, matches the existing
  `test_thrown_string_is_caught_and_bound`.
- `throw "boom";` uncaught still has `.message == "boom"` at line 1,
  column 1 — regression guard, matches the existing
  `test_uncaught_throw_raises_with_own_line_and_column`.
- `try { throw {"kind": "MyError", "msg": "oops"}; } catch (e) { print(e.msg); }`
  prints `oops` — the exact gap demonstrated above, now fixed cleanly.
- `try { throw 42; } catch (e) { print(e + 1); }` prints `43` — the
  caught value keeps its real type (`int`), not a stringified form.
- `try { throw [1, 2, 3]; } catch (e) { print(e[1]); }` prints `2`.
- `try { throw nil; } catch (e) { print(e == nil); }` prints `true` —
  confirms the sentinel correctly distinguishes "no value" from a
  genuinely thrown `nil` (`None` at the Python level).
- `try { throw false; } catch (e) { print(e); }` prints `false` — a
  second falsy-value regression guard alongside `nil`, since `false`
  must not be confused with "value not supplied" either.
- `throw 42;` uncaught now succeeds (no longer a type error): `.message
  == "42"` and `.value == 42`. Replaces `test_throw_non_string_raises_type_error`
  (delete it — it asserted exactly the restriction this task removes).
- `throw {"a": 1};` uncaught has `.message == '{"a": 1}'` — reuses
  `stringify`'s existing map-rendering format for the display message
  (matches what `print({"a": 1});` already outputs).
- Internal errors are unaffected: `try { 1 + "a"; } catch (e) { print(e); }`
  still prints the exact same type-error string it always has, since
  `_apply_binary_operator`'s `CinderRuntimeError(...)` call (like the
  ~430 others) never passes `value=`, so `error.value` still equals
  `error.message` there.
- `test_throw_inside_nested_call_reports_call_stack` and
  `test_finally_runs_before_throw_propagates_uncaught` still pass
  unmodified — call-stack frames and `finally` ordering are untouched.
- Full test suite passes.

Likely files: `cinder/errors.py` (`CinderRuntimeError`, search `class
CinderRuntimeError`), `cinder/interpreter.py` (`ThrowStmt` branch of
`execute`, search `if isinstance(stmt, ThrowStmt):`; `_execute_try`,
search `def _execute_try`), `tests/test_interpreter.py` (`class
TestThrowStatement`, search that name — delete
`test_throw_non_string_raises_type_error`, add new tests for the
non-string throw/catch cases above). Once merged, `README.md`'s
error-handling bullet needs a mention that `throw`/`catch` carry any
value now (not just strings), its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `is_keith_number` — digit-recurrence self-generating number

Build: Cinder already has several "does a number reproduce itself under
some digit-driven process" predicates — `is_automorphic`/
`is_trimorphic_number` (`cinder/builtins.py`, search `def
_is_automorphic`, immediately followed by `def
_is_trimorphic_number`) check whether a power of the number *ends in*
the number's own digits, and `is_kaprekar`/`nth_kaprekar` (search `def
_is_kaprekar`) split the number's square and check the halves sum back
to it. Missing is the Keith number test: take an n-digit number's own
digits as the first n terms of a sequence, then generate each further
term as the sum of the previous n terms (a digit-count-wide
Fibonacci-style recurrence) — if the original number itself eventually
appears as a later term, it is a Keith number. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_keith_number(197));'
# -> <eval>:1:7: undefined name 'is_keith_number' (did you mean 'is_kaprekar'?)
```

Worked example, `197` (3 digits, so each new term sums the previous
three): seed `[1, 9, 7]`, then `1+9+7=17`, `9+7+17=33`, `7+17+33=57`,
`17+33+57=107`, `33+57+107=197` — the sequence hits `197` exactly, so
it's a Keith number. Contrast `20` (2 digits): seed `[2, 0]`, then
`2`, `2`, `4`, `6`, `10`, `16`, `26` — the sequence overshoots `20`
(jumping from `16` to `26`) without ever landing on it exactly, so
`20` is not a Keith number; once a term meets or exceeds the original
value the search is over; there's no valid domain where more terms
could still hit it exactly, since the sequence is non-decreasing once
all digits are non-negative (which they always are).

The one domain wrinkle every published definition agrees on: Keith
numbers require **at least two digits** — a single digit's "sequence"
would just be that digit repeating itself starting from the seed, a
trivial case that ordinarily isn't counted as a Keith number in any of
the reference lists (OEIS A007629 starts at `14`, the smallest
2-digit example, not at any single digit). Exclude single-digit inputs
explicitly rather than letting the general recurrence accidentally
"pass" them.

Add to `cinder/builtins.py`, directly after `_is_trimorphic_number`
(search `def _is_trimorphic_number`, immediately before `def
_is_kaprekar`) — keeps it grouped with the other digit-recurrence/
digit-driven number predicates:
```python
def _is_keith_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_keith_number", arguments, 1, line, column)
    value = _require_int("is_keith_number", arguments[0], line, column)
    if value < 0:
        return False
    digits = [int(digit) for digit in str(value)]
    digit_count = len(digits)
    if digit_count < 2:
        return False
    sequence = digits[:]
    while sequence[-1] < value:
        sequence.append(sum(sequence[-digit_count:]))
    return sequence[-1] == value
```
Also register the new dict entry (search `"is_trimorphic_number":
_is_trimorphic_number,`, add `"is_keith_number": _is_keith_number,`
directly after it, before `"is_kaprekar": _is_kaprekar,`).

Acceptance criteria:
- `is_keith_number(14);` is `true` — the smallest Keith number
  (OEIS A007629's first term): seed `[1, 4]`, `4+1=5`, `1+5=6`, ...,
  eventually `14` (`5, 9, 14`).
- `is_keith_number(19);` is `true` — seed `[1, 9]`, `1+9=10`,
  `9+10=19`, hits on the very next term.
- `is_keith_number(197);` is `true` — the worked 3-digit example above.
- `is_keith_number(742);` is `true` — another known multi-digit Keith
  number, confirming the check isn't hardcoded to 2/3-digit inputs.
- `is_keith_number(20);` is `false` — the worked overshoot example
  above.
- `is_keith_number(100);` is `false` — seed `[1, 0, 0]` stays at `0`/`1`
  forever without reaching `100` (`0, 0, 1, 1, 2, ...` all strictly
  less until it eventually overshoots), confirming a non-Keith case
  with interior zero digits.
- `is_keith_number(9);` is `false` — single-digit input, excluded by
  the "at least two digits" convention even though it trivially
  "contains itself".
- `is_keith_number(0);` is `false` — same single-digit exclusion.
- `is_keith_number(-14);` is `false` — negative numbers excluded
  (mirrors `is_trimorphic_number`'s own convention), despite `14`
  itself being Keith.
- `is_keith_number(1.5);` raises `CinderRuntimeError` matching
  `"is_keith_number() requires an int, got float"` (via
  `_require_int`'s existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after
`_is_trimorphic_number`, search `def _is_trimorphic_number`),
`tests/test_builtins.py` (new `class TestIsKeithNumber`, modeled
directly on `class TestIsTrimorphicNumber`, search that name, for the
true/false/domain-edge/type-error test shapes above). Once merged,
`README.md`'s Builtins bullet needs `is_keith_number` added near
`is_trimorphic_number`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 3. Language: `&` (intersection) operator for lists (set-style, mirrors list `-`)

Build: PR #356 gave `-` a map-map branch (key-based removal), and PR #363
gave it a list-list branch too (set-style difference, `[1, 2, 3] - [2]`
is `[1, 3]`) — mirroring the existing `difference()` builtin's set
semantics. Cinder's list builtins also already answer the
intersection question as a function (`intersection()`,
`cinder/builtins.py`, search `def _intersection`: dedupes the left
list, keeps only elements also present in the right, both lists
treated as unordered sets — the same convention `union`/`difference`/
`symmetric_difference` share), but `&` has no list meaning at all today
— it is bitwise-int-only (`_bitwise_op`, `cinder/interpreter.py`,
search `def _bitwise_op`, unconditionally requires both operands to be
`int`). This task gives `intersection()` the same infix spelling task 2
gives `difference()`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2, 3] & [2, 3, 4]);'
# -> <eval>:1:17: unsupported operand types for '&': list and list
```

Scope: list-list only, matching how `-` got its dict branch (#356) and
list branch (task 2) as two separate, smaller tasks rather than one —
map-map `&` intersection is a plausible future task, not this one. This
task does not depend on task 2 landing first; either order is fine.

Edit `cinder/interpreter.py`'s `_apply_binary_operator`, immediately
above the existing dispatch to `_bitwise_op` (search `TokenType.AMP,`
inside the `if op in (` tuple that also lists `PIPE`/`CARET`/
`LSHIFT`/`RSHIFT`): add a list-list special case for `AMP` specifically,
reusing `contains_value` (search `def contains_value`, already used a
few lines above for the `IN`/`NOT_IN` branches) for `values_equal`-based
membership rather than Python's native `in`:
```python
        if op == TokenType.AMP and isinstance(left, list) and isinstance(right, list):
            deduped: list = []
            for element in left:
                if not any(values_equal(element, kept) for kept in deduped):
                    deduped.append(element)
            return [
                element
                for element in deduped
                if contains_value(right, element, operator.line, operator.column)
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
(Only the new `if op == TokenType.AMP and isinstance(left, list)...`
block is added, directly above the existing bitwise dispatch — `PIPE`/
`CARET`/`LSHIFT`/`RSHIFT` and int-int `AMP` all still fall through
unchanged to `_bitwise_op`, which still rejects every other
non-int/non-list-list combination exactly as it does today.)

The compound-assignment desugaring (`&=`) already works for free once
`&` itself handles lists, exactly as `-=`'s existing coverage for maps
documents — no separate wiring needed.

Acceptance criteria (mirror `TestMapDifference`/task 2's
`TestListDifference` shape in `tests/test_interpreter.py`):
- `[1, 2, 3] & [2, 3, 4]` is `[2, 3]` — the basic case, left-to-right
  order.
- `[1, 2, 2, 3] & [2]` is `[2]` — the left side is deduped first.
- `[1, 2, 3] & []` is `[]` and `[] & [1, 2]` is `[]` — either empty
  side empties the result.
- `[1, 2] & [1, 2]` is `[1, 2]` — full overlap keeps everything
  (deduped).
- `[1, 2] & [3, 4]` is `[]` — no overlap.
- Does not mutate inputs: `let a = [1, 2, 3]; let c = a & [2];` leaves
  `a` as `[1, 2, 3]` and `c` as `[2]`.
- Left-associative: `[1, 2, 3] & [1, 2] & [2]` is `[2]`.
- Compound assignment works: `let xs = [1, 2, 3]; xs &= [2, 3];` leaves
  `xs` as `[2, 3]` (identifier target); also test an index target and a
  dot target, mirroring task 2's own compound-assignment cases.
- `[1, true, 2] & [true]` is `[true]` — uses `values_equal`, not
  Python's native `==`/`in`, so `1` is not conflated with `true`.
- `2 & 3` (both ints) is still `2` — existing bitwise-AND behavior is
  unchanged, a regression guard.
- `[1, 2] & 3` and `2 & [1, 2]` still raise `CinderRuntimeError`
  matching `"unsupported operand types for '&': ..."` — mixed
  list/non-list operands remain a type error, same message shape
  `_bitwise_op` already produces.
- `[1, 2] & {"a": 1}` also raises the same type error — map operands
  are unsupported (deferred per the Scope note above).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`AMP`/`PIPE`/`CARET`/`LSHIFT`/`RSHIFT` dispatch, search
`TokenType.AMP,`), `tests/test_interpreter.py` (new `class
TestListIntersection`, modeled on `class TestMapDifference`, search that
name, for the test shapes above). Once merged, `README.md`'s
language-operators bullet needs a list-`&` mention next to the existing
map/list `-` ones, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `run_length_encode` / `run_length_decode` — consecutive-run compression

Build: Cinder already has `group_consecutive` (`cinder/builtins.py`, search
`def _group_consecutive`) which splits a list into sublists of consecutive
equal elements (e.g. `[1, 1, 2, 2, 2, 3]` becomes `[[1, 1], [2, 2, 2],
[3]]`), but there is no way to get the classic compressed `(value, count)`
form of that same grouping, or to expand it back out. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(run_length_encode([1, 1, 2, 2, 2, 3]));'
# -> <eval>:1:7: undefined name 'run_length_encode' (did you mean
#    'group_consecutive'?)
```

This task adds both directions as a pair, mirroring how `zip`/`unzip` or
`flatten`/`chunk` already live as inverse siblings in this file.
`run_length_encode(xs)` returns a list of `[value, count]` pairs, one per
maximal run of consecutive equal elements (equality via `values_equal`,
not Python's native `==` — see the existing `_dedupe` comment, search
`native hash/eq treat`, for why: Cinder's `==` does not conflate `1` and
`true` the way Python's does, so runs must not merge across that boundary
either). `run_length_decode(pairs)` is the exact inverse: expand each
`[value, count]` pair back into `count` repetitions of `value`,
concatenated in order.

Add to `cinder/builtins.py`, directly after `_group_consecutive` (search
`def _group_consecutive`, immediately before `def _zip`) — keeps the pair
grouped with the other consecutive-run/list-transform builtins:
```python
def _run_length_encode(arguments: list, line: int, column: int) -> object:
    _require_arity("run_length_encode", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"run_length_encode() requires a list, got {type_name(value)}",
            line, column,
        )
    result: list = []
    for element in value:
        if result and values_equal(result[-1][0], element):
            result[-1][1] += 1
        else:
            result.append([element, 1])
    return result


def _run_length_decode(arguments: list, line: int, column: int) -> object:
    _require_arity("run_length_decode", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"run_length_decode() requires a list, got {type_name(value)}",
            line, column,
        )
    result: list = []
    for i, pair in enumerate(value):
        if not isinstance(pair, list) or len(pair) != 2:
            raise CinderRuntimeError(
                f"run_length_decode() requires a list of [value, count] "
                f"pairs, got {type_name(pair)} at index {i}",
                line, column,
            )
        element, count = pair
        if not isinstance(count, int) or isinstance(count, bool):
            raise CinderRuntimeError(
                f"run_length_decode() requires an int count, got "
                f"{type_name(count)} at index {i}",
                line, column,
            )
        if count < 0:
            raise CinderRuntimeError(
                f"run_length_decode() requires a non-negative count, got "
                f"{count} at index {i}",
                line, column,
            )
        result.extend([element] * count)
    return result
```
Also register both dict entries (search `"group_consecutive":
_group_consecutive,`, add directly after it, before `"zip": _zip,`):
```python
    "run_length_encode": _run_length_encode,
    "run_length_decode": _run_length_decode,
```

Acceptance criteria:
- `run_length_encode([1, 1, 2, 2, 2, 3]);` is `[[1, 2], [2, 3], [3, 1]]`.
- `run_length_encode([]);` is `[]`.
- `run_length_encode([5]);` is `[[5, 1]]` — single element, count 1.
- `run_length_encode([1, 2, 3]);` is `[[1, 1], [2, 1], [3, 1]]` — no runs
  longer than 1, still one pair per element.
- `run_length_encode([1, true, true]);` is `[[1, 1], [true, 2]]` — uses
  `values_equal`, not native `==`, so `1` never merges into the `true`
  run even though Python's own `==`/hashing would conflate them.
- `run_length_decode([[1, 2], [2, 3], [3, 1]]);` is
  `[1, 1, 2, 2, 2, 3]` — the exact inverse of the first case.
- `run_length_decode([]);` is `[]`.
- `run_length_decode([[5, 0]]);` is `[]` — a zero count contributes
  nothing.
- Round-trips: `run_length_decode(run_length_encode(xs))` equals `xs` for
  `xs` in `[]`, `[1]`, `[1, 1, 2, 2, 2, 3]`, and `["a", "a", "b"]`.
- `run_length_encode(5);` and `run_length_decode(5);` both raise
  `CinderRuntimeError` matching `"...() requires a list, got int"`.
- `run_length_decode([[1, 2], 5]);` raises `CinderRuntimeError` matching
  `"run_length_decode() requires a list of [value, count] pairs, got int
  at index 1"`.
- `run_length_decode([[1, 2, 3]]);` (a 3-element pair) raises the same
  `"requires a list of [value, count] pairs"` error, index 0.
- `run_length_decode([[1, "a"]]);` raises `CinderRuntimeError` matching
  `"run_length_decode() requires an int count, got string at index 0"`.
- `run_length_decode([[1, -1]]);` raises `CinderRuntimeError` matching
  `"run_length_decode() requires a non-negative count, got -1 at index
  0"`.
- Wrong arity (not exactly 1 argument) on either builtin raises
  `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_group_consecutive`,
search `def _group_consecutive`), `tests/test_builtins.py` (new `class
TestRunLengthEncode` and `class TestRunLengthDecode`, modeled on `class
TestGroupConsecutive`, search that name, for the test shapes above; it
sits right after `class TestChunk`, search that name, for context). Once
merged, `README.md`'s Builtins bullet needs `run_length_encode`/
`run_length_decode` added near `group_consecutive`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 5. Language: `&` (intersection) operator for maps (key-based, mirrors map `-`)

Build: task 3 above gives `&` a list-list branch, and the map side of
`-` (PR #356) already established what a key-based map operator looks
like: `{"a": 1, "b": 2} - {"a": 1}` is `{"b": 2}` — keys present in the
right map are dropped from the left, *values on the right are ignored
entirely* (`{"a": 1} - {"a": 99}` still removes `"a"` even though the
values don't match). `&` has no map meaning at all today — like list
`&` before task 3, it falls straight through to `_bitwise_op`, which
rejects any non-int operand. Task 3's own Scope note calls this out
explicitly as deferred, not in-scope there: "map-map `&` intersection
is a plausible future task, not this one." This task is that task, once
task 3 has landed (both edit the same dispatch block in
`_apply_binary_operator`, so task 3's list-list branch must be merged
first — this task's diff assumes it's already there). Verify the gap:
```sh
python3 -m cinder.cli eval 'print({"a": 1, "b": 2} & {"a": 1, "c": 3});'
# -> <eval>:1:24: unsupported operand types for '&': map and map
```

Semantics: key-based intersection, keeping the *left* map's value for
every key present in both — the same "keys decide, left's values win"
convention map `-` already set, not a value-equality check. So
`{"a": 1, "b": 2} & {"a": 99, "c": 3}` is `{"a": 1}`: key `"a"` is kept
(present on both sides) with its value taken from the left, `"b"` is
dropped (left-only, not present on the right), `"c"` is dropped
(right-only, not present on the left), and the right map's `"a": 99`
never surfaces.

Edit `cinder/interpreter.py`'s `_apply_binary_operator`, immediately
above the list-list `AMP` branch task 3 adds (search `if op ==
TokenType.AMP and isinstance(left, list)`) — add a dict-dict special
case first, mirroring `MINUS`'s existing dict-dict branch just above in
the same method (search `if isinstance(left, dict) and isinstance(right,
dict):` under the `MINUS` case):
```python
        if op == TokenType.AMP and isinstance(left, dict) and isinstance(right, dict):
            return {key: value for key, value in left.items() if key in right}
        if op == TokenType.AMP and isinstance(left, list) and isinstance(right, list):
```
(Only the new dict-dict `if` line is added, directly above task 3's
list-list `if`; that line's own `and isinstance(left, list)` check
already means it never fires for dicts, so the two branches can't
collide — order between them doesn't actually matter, but placing the
dict check first keeps `AMP`'s branches in the same left-to-right
type order `MINUS`'s dict-then-list branches already use, two lines
above.)

The compound-assignment desugaring (`&=`) already works for free on a
map target once `&` itself handles maps, exactly as `-=` does for maps
today — no separate wiring needed.

Acceptance criteria (mirror `TestMapDifference`'s shape in
`tests/test_interpreter.py`, search that name):
- `{"a": 1, "b": 2} & {"a": 1, "c": 3}` is `{"a": 1}` — the basic case.
- `{"a": 1, "b": 2} & {"a": 99}` is `{"a": 1}` — right-side value is
  ignored, left's value wins (mirrors `test_right_value_is_ignored` for
  `-`).
- `{"a": 1} & {}` is `{}` and `{} & {"a": 1}` is `{}` — either side
  empty empties the result.
- `{"a": 1, "b": 2} & {"a": 1, "b": 2}` is `{"a": 1, "b": 2}` — full
  overlap keeps everything.
- `{"a": 1, "b": 2} & {"c": 3}` is `{}` — no shared keys.
- Does not mutate inputs: `let m = {"a": 1, "b": 2}; let c = m & {"a": 1};`
  leaves `m` as `{"a": 1, "b": 2}` and `c` as `{"a": 1}`.
- Left-associative: `{"a": 1, "b": 2, "c": 3} & {"a": 1, "b": 2} & {"b": 2}`
  is `{"b": 2}`.
- Compound assignment works: `let m = {"a": 1, "b": 2}; m &= {"a": 1};`
  leaves `m` as `{"a": 1}` (identifier target); also test an index
  target and a dot target, mirroring `TestMapDifference`'s own
  `test_compound_assignment_on_index_target`/`_on_dot_target`.
- `2 & 3` (both ints) is still `2` — existing bitwise-AND behavior is
  unchanged, a regression guard.
- `[1, 2] & [1]` (both lists, from task 3) is still `[1]` — confirms
  the new dict-dict branch doesn't shadow or reorder ahead of the
  list-list branch it sits next to.
- `{"a": 1} & 3` and `3 & {"a": 1}` still raise `CinderRuntimeError`
  matching `"unsupported operand types for '&': ..."` — mixed
  map/non-map operands remain a type error.
- `{"a": 1} & [1, 2]` also raises the same type error — map/list
  operands are unsupported (neither branch's `isinstance` pair
  matches).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s `AMP`
dispatch, search `if op == TokenType.AMP and isinstance(left, list)`,
added by task 3), `tests/test_interpreter.py` (new `class
TestMapIntersection`, modeled on `class TestMapDifference`, search that
name, for the test shapes above). Once merged, `README.md`'s
language-operators bullet needs a map-`&` mention next to the list-`&`
one task 3 adds, its "Status & roadmap" section needs updating, and
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
