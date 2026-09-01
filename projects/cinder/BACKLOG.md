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

## 1. Language: `else` clause on C-style `for` loops (closes the loop-`else` arc for all four loop kinds)

Build: `while` (#352), the foreach `for`-in form (#358), and `do`-`while`
(#361) all now have a trailing Python-style `else { ... }` clause. The
one loop kind left out every time is the classic three-clause
`for (init; cond; step) { ... }` (`ForCStmt`,
`cinder/ast_nodes.py`, search `class ForCStmt`). This task closes that
last gap. Verify it:
```sh
python3 -m cinder.cli eval 'for (let i = 0; i < 3; i = i + 1) { print(i); } else { print("done"); }'
# -> <eval>:1:46: expected ';' after for-loop init  (parses "else" as a
#    fresh statement, i.e. the C-style for loop has no else support at all)
```

Semantics mirror `ForStmt.else_branch` (see its docstring, search `class
ForStmt`) and the C-style loop's own body/exit shape: the `else` block
runs exactly once when the condition clause evaluates false with no
intervening `break` — including immediately, if the condition was
already false before the first iteration (`for (; false;) { ... } else {
ran = true; }` still runs the `else`), and including an omitted
condition clause never being false on its own (`for (;;) { if (x) {
break; } } else { ... }` can only skip the `else` via that `break`, never
by falling out the condition, since an empty condition is always-true —
see `ForCStmt`'s own docstring). `continue` does not skip it; an
uncaught exception, `return`, or a propagating labeled `break`/`continue`
does, since control never reaches the post-loop check in that case.

Grammar wrinkle: exactly like `for`-in (`_for_statement`, search `def
_for_statement`), the C-style form's body is always a brace-delimited
`Block` (`self._block()`, never a bare single statement — see
`_for_c_statement`'s existing `expected '{' before for-loop body` check),
so there is no dangling-`else`/if-attachment ambiguity to resolve: an
`else` immediately following the body's closing `}` unambiguously
belongs to the `for`, the same reasoning `_for_statement` already
documents for its own trailing `else` check.

Edit three files:

1. `cinder/ast_nodes.py` (search `class ForCStmt`), add one field at the
   end, after `label: "str | None" = None`, and extend the docstring:
```python
@dataclass(frozen=True)
class ForCStmt:
    """Classic three-clause `for (init; cond; step) { ... }`, distinct from
    the foreach `ForStmt` above. `init`/`step` are `None` when their clause
    is empty (`for (;;) { ... }` is a valid infinite loop); `condition` is
    `None` when omitted, treated as always-true at execution time.

    `else_branch` is `None` unless the loop carries a trailing
    `else { ... }` clause; when present, it runs exactly once, when the
    condition becomes false *without* an intervening `break` — including
    immediately, if the condition was already false (or omitted, which
    never happens on its own since an omitted condition is always-true) —
    mirroring `ForStmt`/`WhileStmt`'s own `else_branch`. `continue` does
    not skip it (only `break` does); an uncaught exception, `return`, or
    propagating labeled `break`/`continue` from the body also skips it.
    """

    init: "Stmt | None"
    condition: "Expr | None"
    step: "Stmt | None"
    body: "Block"
    line: int
    column: int
    label: "str | None" = None
    else_branch: "Stmt | None" = None
```

2. `cinder/parser.py`'s `_for_c_statement` (search `def
   _for_c_statement`): after the existing `body = self._block()` /
   `self._loop_labels.pop()` lines and before the `return ForCStmt(...)`,
   add the same else-check `_for_statement` already has, and thread it
   into the constructor call:
```python
        self._loop_labels.append(label)
        body = self._block()
        self._loop_labels.pop()
        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            else_branch = self._statement()
        return ForCStmt(
            init,
            condition,
            step,
            body,
            for_token.line,
            for_token.column,
            label,
            else_branch=else_branch,
        )
```
(Only the `else_branch = None` block and the `else_branch=else_branch`
constructor argument are new — everything above is unchanged, shown in
full only so the exact insertion point is unambiguous.)

3. `cinder/interpreter.py`'s `_execute_for_c` (search `def
   _execute_for_c`): track a `broke` flag through the existing loop
   exactly the way `_execute_for` already does, then check it after the
   loop ends:
```python
    def _execute_for_c(self, stmt: ForCStmt, env: Environment) -> None:
        loop_env = Environment(env)
        if stmt.init is not None:
            self.execute(stmt.init, loop_env)
        broke = False
        while True:
            iter_env = Environment(env)
            iter_env._values.update(loop_env._values)
            iter_env._frozen.update(loop_env._frozen)
            if stmt.condition is not None and not is_truthy(
                self.evaluate(stmt.condition, iter_env)
            ):
                break
            try:
                self.execute(stmt.body, iter_env)
            except _BreakSignal as signal:
                if signal.label is not None and signal.label != stmt.label:
                    raise
                broke = True
                break
            except _ContinueSignal as signal:
                if signal.label is not None and signal.label != stmt.label:
                    raise
            loop_env._values.update(iter_env._values)
            loop_env._frozen.update(iter_env._frozen)
            if stmt.step is not None:
                self.execute(stmt.step, loop_env)
        if not broke and stmt.else_branch is not None:
            self.execute(stmt.else_branch, env)
```
(Only the `broke = False` init, the `broke = True` before the `break` in
the `_BreakSignal` handler, and the final `if not broke and
stmt.else_branch is not None:` block are new — everything else, including
the existing docstring-documented per-iteration `Environment` copying, is
unchanged.)

Acceptance criteria (mirror `TestForElse` in `tests/test_interpreter.py`,
search that class, one-for-one where a C-style equivalent makes sense):
- `for (let i = 0; i < 3; i = i + 1) { x = i; } else { done = true; }`
  runs the `else` — all three iterations complete, condition then false,
  no `break`.
- `for (; false;) { x = 1; } else { done = true; }` also runs the `else`
  — the condition is false before the first iteration, body never runs,
  mirrors `for`-in's own empty-iterable case.
- `let i = 0; for (;; i = i + 1) { if (i == 2) { break; } } else { ran =
  true; }` does **not** run the `else` — a `break` skips it even with an
  always-true omitted condition.
- `let i = 0; for (; i < 3; i = i + 1) { if (i == 1) { continue; } }
  else { ran = true; }` still runs the `else` — `continue` does not skip
  it, only `break` does.
- `outer: for (let i = 0; i < 1; i = i + 1) { for (let j = 0; j < 1; j =
  j + 1) { break outer; } } else { ran = true; }` does **not** run the
  outer loop's `else` — a labeled `break` targeting the outer loop skips
  its `else`, exactly like `while`/`for`-in's own labeled-break case.
- `fn f() { for (let i = 0; i < 1; i = i + 1) { return 1; } else { return
  2; } } f();` returns `1`, not `2` — `return` from the body skips the
  `else`.
- `for (let i = 0; i < 2; i = i + 1) { x = i; }` (no `else` at all) still
  behaves exactly as before — a regression guard mirroring
  `test_while_without_else_still_behaves_as_before`/the `for`-in
  equivalent.
- `for (let i = 0; i < 1; i = i + 1) { } else x = 1;` (an unbraced
  single-statement `else`, not a block) parses and runs `x = 1` —
  confirms the `else` branch is parsed via the generic `_statement()` the
  same way `while`/`for`-in's own is, not hardcoded to require a block.
- A closure captured inside the `else` branch still sees the loop's
  final `init`-declared binding value (e.g. `let fns = []; for (let i =
  0; i < 3; i = i + 1) { } else { fns = push(fns, fn() { return i; }); }
  fns[0]();` returns `3`) — the `else` runs in the outer `env`, after
  `loop_env`'s values have been copied back in on the last completed
  iteration, not in a stale `iter_env`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`ForCStmt`, search `class
ForCStmt`), `cinder/parser.py` (`_for_c_statement`, search `def
_for_c_statement`), `cinder/interpreter.py` (`_execute_for_c`, search
`def _execute_for_c`), `tests/test_parser.py` (new `class
TestForCElse`, modeled on `class TestForElse`, search that name, for the
parse-shape assertions), `tests/test_interpreter.py` (new `class
TestForCElse`, modeled on `class TestForElse`, search that name — it
sits right after the existing `class TestForCStatement`, search that
name, for context — for the runtime behavior above). Once merged,
`README.md`'s Control flow bullet needs a C-style-for-else mention next
to the existing `while`/`for`-in/`do`-`while` ones, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Language: `throw`/`catch` carry any value, not just strings

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

## 3. Standard library: `is_keith_number` — digit-recurrence self-generating number

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

## 4. Language: `&` (intersection) operator for lists (set-style, mirrors list `-`)

Build: PR #356 gave `-` a map-map branch (key-based removal), and task 2
in this file gives it a list-list branch too (set-style difference,
`[1, 2, 3] - [2]` is `[1, 3]`) — mirroring the existing `difference()`
builtin's set semantics. Cinder's list builtins also already answer the
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
TestListIntersection`, modeled on `class TestMapDifference` or task 2's
`TestListDifference`, search either name, for the test shapes above).
Once merged, `README.md`'s language-operators bullet needs a list-`&`
mention next to the existing map/list `-` ones, its "Status & roadmap"
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
