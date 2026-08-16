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

## 1. Language: postfix `++`/`--` as a first-class assignment expression, not statement-only sugar

Build: the depth task after task 5's breadth work (`geometric_mean`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that uninitialized `let` declarations landed via PR #257,
dropping the count to the 5-task floor. `cinder/parser.py`'s own module
docstring (search for "statement-only sugar", right above
`_assignment`) spells out today's deliberate restriction: `x++`/`x--`
are recognized only by a one-off helper, `_expr_or_incdec`, called from
exactly three places — `_expr_statement` (a bare `x++;` statement) and
the C-style `for` loop's init/step clauses — rather than from
`_assignment` itself, "so they're unreachable from any expression
context." That restriction has become an inconsistency, not a
deliberate language design choice: every *other* assignment-flavored
operator (`=`, `+=`, `-=`, `*=`, `/=`, `%=`, `**=`, `//=`, `&=`, `|=`,
`^=`, `<<=`, `>>=`, `??=`) already *is* reachable as a `let` initializer,
as the RHS of a chained assignment, and inside a parenthesized
sub-expression, because `_assignment` itself recognizes them. `++`/`--`
are the one assignment-flavored form still walled off from all of that.
Verify the gap — every one of these already works today with `+=` in
place of `++`, but fails with `++`:
```sh
python3 -m cinder.cli eval 'let x = 1; let y = x++; print(y);'
# -> ParseError: expected ';' after variable declaration, found '++'
python3 -m cinder.cli eval 'let x = 1; let y = 0; y = x++; print(y);'
# -> ParseError: expected ';' after expression, found '++'
python3 -m cinder.cli eval 'let x = 1; let y = (x++); print(y);'
# -> ParseError: expected ')' after expression, found '++'
python3 -m cinder.cli eval 'let x = 1; let y = x += 1; print(y);'
# -> prints 2, no error — the exact sibling form this task brings ++/-- up to parity with
```

**Parsing** (`cinder/parser.py`): fold `_expr_or_incdec`'s body directly
into `_assignment`, as one more `if` branch alongside the existing
`EQ`/`QQEQ`/`_COMPOUND_ASSIGN_OPS` checks (order among these four
branches doesn't matter — they dispatch on disjoint token types):

```python
    def _assignment(self) -> Expr:
        expr = self._ternary()
        if self._check(TokenType.EQ):
            ...  # unchanged
        if self._check(TokenType.QQEQ):
            ...  # unchanged
        if self._peek().type in _COMPOUND_ASSIGN_OPS:
            ...  # unchanged
        if self._peek().type in _INCREMENT_DECREMENT_OPS:
            op_token = self._advance()
            binary_operator = Token(
                _INCREMENT_DECREMENT_OPS[op_token.type],
                op_token.lexeme[0],
                None,
                op_token.line,
                op_token.column,
            )
            one = Literal(1, op_token.line, op_token.column)
            if isinstance(expr, Identifier):
                return Assign(
                    expr.name,
                    Binary(expr, binary_operator, one),
                    op_token.line,
                    op_token.column,
                )
            if isinstance(expr, Index):
                return IndexCompoundAssign(
                    expr.obj, expr.index, binary_operator, one,
                    op_token.line, op_token.column,
                )
            raise ParseError(
                "invalid assignment target", op_token.line, op_token.column
            )
        return expr
```

This is a straight relocation of the existing body of
`_expr_or_incdec` (currently at the bottom of the file, right above
`_assignment`) — same `Identifier`/`Index` target check, same
`Assign`/`IndexCompoundAssign` desugaring, same "invalid assignment
target" error for anything else (a literal, a call result, a
parenthesized expression, etc. — unchanged, still a `ParseError`).
Once folded in, `_expr_or_incdec` has no remaining callers needing its
own name — delete it, and change its three call sites
(`_expr_statement`, and the `for`-loop init/step clauses in
`_for_c_statement`) to call `self._assignment()` directly instead,
exactly as every other statement-position expression already does.
**No interpreter changes at all**: this task changes only where the
parser is *willing to look* for `++`/`--`, not what AST node it builds
or how that node evaluates — `Assign`/`IndexCompoundAssign` already
evaluate to the new (post-increment) value, the same as every sibling
compound-assign operator already does (confirmed above: `y = x += 1;`
already prints `2`, not `1`), so `x++` used as an expression yields the
incremented value too, not a C-style pre-increment snapshot of the old
one — the natural, zero-extra-code consequence of reusing the exact
same desugaring, not a new design decision this task has to invent.

Out of scope, deliberately: this task does **not** change *precedence*
— `++`/`--` are still recognized at the same (loosest, assignment-level)
point in the grammar as today, just from more call sites. `-x++;`
already raises `"invalid assignment target"` today (`_unary` parses
`-x` into a single `Unary` node before `_expr_or_incdec` ever sees a
trailing `++`, and `Unary` isn't an `Identifier`/`Index`) and must keep
doing so — making postfix `++`/`--` bind tighter than unary prefix
operators (C's actual precedence) is a separate, riskier parser change
this task does not take on. Likewise, `++`/`--` still must not become
reachable from call arguments, index expressions, ternary branches, or
any other `_ternary()`-rooted position — none of the *other*
assignment operators are reachable there either (`print(x = 5)` is
`ParseError` today and must stay that way), so extending only `++`/`--`
into those positions would be a new inconsistency in the opposite
direction, not a fix for this one.

Also update the `cinder/parser.py` module docstring paragraph
(currently: `"x++"/"x--" are statement-only sugar for "x += 1"/"x -=
1" (not an expression form: "let b = a++;" is unparseable), handled in
"_expr_statement" rather than "_assignment" so they're unreachable
from any expression context.'`) to describe the new, corrected
behavior instead of the restriction this task removes; the two
sentences right after it about the lexer's doubled-`-`/doubled-`+`
prefix re-split (`--5`, `++5`) are unaffected and stay as-is.

Acceptance criteria:
- `let x = 1; let y = x++; print(x); print(y);` prints `2` then `2` —
  `x++` works as a `let` initializer, and yields the new value.
- `let x = 1; let y = 0; y = x++; print(x); print(y);` prints `2` then
  `2` — `x++` works as the RHS of a chained assignment.
- `let x = 1; let y = (x++); print(y);` prints `2` — works inside a
  parenthesized sub-expression.
- `let x = 5; let y = x--; print(x); print(y);` prints `4` then `4` —
  `--` gets the same treatment as `++`.
- `let xs = [1]; let y = xs[0]++; print(xs[0]); print(y);` prints `2`
  then `2` — an `Index` target works the same new-value way, via
  `IndexCompoundAssign`.
- `let x = 1; x++; print(x);` still prints `2` — the existing bare-
  statement form is unaffected.
- `for (let i = 0; i < 3; i++) { print(i); }` still prints `0`, `1`,
  `2` — the existing for-loop step-clause form is unaffected.
- `for (let i = 0; i < 3; i = i + 1) { }` (an ordinary assignment step,
  no `++`) still works unchanged — confirms the `_for_c_statement`
  call-site swap to `_assignment()` didn't regress the non-incdec path.
- `5++;` still raises `ParseError` matching `"invalid assignment
  target"` — an invalid target is still rejected, from every call site,
  not just the original one.
- `-x++;` still raises the same `"invalid assignment target"` error —
  confirms this task deliberately left precedence unchanged.
- `print(x++);` still raises `ParseError` (still unreachable from a
  call argument) — confirms `++`/`--` stayed at assignment-expression
  reachability, matching `=`/`+=`'s own existing `print(x = 5)`
  restriction, not creeping further into `_ternary()`-rooted positions.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_assignment`, delete
`_expr_or_incdec`, `_expr_statement`, `_for_c_statement`, the module
docstring), `tests/test_parser.py` and/or `tests/test_interpreter.py`
(wherever the existing statement-form `x++`/for-loop tests live —
search `INCREMENT_DECREMENT` or `x++`  — add the new expression-position
cases alongside them, plus the unchanged-precedence/unchanged-
reachability regression cases). Once merged, `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave that to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `digit_product` — the multiplicative counterpart to `digit_sum`

Build: the breadth task after task 5's depth work (postfix `++`/`--`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that `is_powerful_number` has landed via PR #258,
dropping the count to the 5-task floor. Add `digit_product(n)` to
`cinder/builtins.py`, registered right after `digit_sum` (search for
`def _digit_sum`, immediately before `_reverse_int`) — `digit_sum`
sums an integer's decimal digits; `digit_product` is its natural
multiplicative sibling, the same relationship `product` already has to
`sum` at the list level. Verify the gap: `python3 -m cinder.cli eval
'print(digit_product(23));'` currently raises `CinderRuntimeError`
`"undefined name 'digit_product'"` — no such builtin exists yet.

```python
def _digit_product(arguments: list, line: int, column: int) -> object:
    _require_arity("digit_product", arguments, 1, line, column)
    value = _require_int("digit_product", arguments[0], line, column)
    product = 1
    for digit in str(abs(value)):
        product *= int(digit)
    return product
```

Model the arity/type-checking exactly on `digit_sum`'s own structure:
`_require_arity`, then `_require_int` (reusing the shared helper — do
**not** hand-roll a separate `isinstance` check), then `abs(value)` to
normalize away the sign before walking digits, mirroring how
`digit_sum` already discards the sign via the same `str(abs(value))`
call rather than raising on negative input or letting a leading `-`
character corrupt the digit walk. A single-digit integer, including
`0`, is trivially its own digit product — the loop runs once and
returns that digit — the same trivial-degenerate-case convention
`digit_sum`/`is_palindrome_number` already establish. Any digit `0`
anywhere in the number collapses the whole product to `0`, which is
the correct mathematical answer, not a special case to guard against.

Acceptance criteria:
- `digit_product(0);` is `0` — single digit, trivially itself.
- `digit_product(5);` is `5` — single digit.
- `digit_product(23);` is `6` — `2 * 3`.
- `digit_product(123);` is `6` — `1 * 2 * 3`.
- `digit_product(999);` is `729` — `9 * 9 * 9`.
- `digit_product(10);` is `0` — a `0` digit collapses the product.
- `digit_product(-23);` is `6` — sign is discarded first, same
  convention as `digit_sum(-23)` returning `5`.
- `digit_product(5.0);` raises `CinderRuntimeError` matching
  `"digit_product() requires an int, got float"` — the same message
  shape `_require_int` already produces for `digit_sum`.
- `digit_product(true);` raises `CinderRuntimeError` matching
  `"digit_product() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_sum`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py` (model on the `TestDigitSum` test class,
search `class TestDigitSum`). Once merged, `README.md`'s Builtins
bullet needs `digit_product` added near `digit_sum`/`reverse_int`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 3. Language: trailing commas in list/map literals, call arguments, and function parameter lists

Build: the depth task after task 5's breadth work (`digit_product`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that single-quoted string literals landed via PR #259,
dropping the count to the 5-task floor. All four of `cinder/parser.py`'s
comma-separated-list parsers — `_list_literal`, `_map_literal`,
`_finish_call` (call arguments), and `_fn_param_list` (function
parameters) — share the identical shape: parse one element, then `while
self._check(TokenType.COMMA): self._advance(); <parse another element>`,
with no check that a comma might be the *last* thing before the closing
delimiter. A trailing comma — convenient when reordering elements or
diffing cleanly line-per-element, and already how every mainstream
scripting language (JS, Python, Rust) treats these four positions —
today hard-fails instead of being silently accepted. Verify the gap,
one failure per site:
```sh
python3 -m cinder.cli eval 'print([1, 2, 3,]);'
# -> ParseError: expected an expression, found ']'
python3 -m cinder.cli eval 'print({"a": 1, "b": 2,});'
# -> ParseError: expected an expression, found '}'
python3 -m cinder.cli eval 'fn f(a, b) { return a + b; } print(f(1, 2,));'
# -> ParseError: expected an expression, found ')'
python3 -m cinder.cli eval 'fn f(a, b,) { return a + b; } print(f(1, 2));'
# -> ParseError: expected parameter name, found ')'
```

**Parsing** (`cinder/parser.py`): in each of the four comma-loops, after
consuming the comma, check whether the very next token is that site's
closing delimiter and `break` instead of parsing another element — the
same "peek before committing to another element" shape, applied one
token later than usual. For `_list_literal`:
```python
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACKET):
                    break
                elements.append(self._list_element())
```
`_map_literal` takes the identical shape with `TokenType.RBRACE` and
`pairs.append(self._map_entry())`; `_finish_call` with
`TokenType.RPAREN` and `arguments.append(self._call_argument())`
(dropping the `seen_keyword` bookkeeping update for the loop iteration
that never happens — no other change to that function's keyword-arg
ordering check); `_fn_param_list` with `TokenType.RPAREN` and
`params.append(self._fn_param(seen_default))` inside its own
comma-loop. `_fn_param_list`'s rest-parameter branch needs no special
handling: a trailing comma after `...rest` (`fn f(a, ...rest,)`) hits
the same early `RPAREN` check and breaks cleanly before ever reaching
the existing "rest parameter must be the last parameter" guard, so it's
accepted — a comma with genuinely nothing meaningful after it, not a
second parameter smuggled in after the rest one.

Out of scope, deliberately: this task does **not** touch destructuring
patterns (`let [a, b,] = expr;`, `let {a, b,} = expr;`, `for [a, b,] in
...`, destructuring function parameters `fn f([a, b,]) { ... }`) or
list/map comprehension bodies — `_destructure_list_pattern`/
`_destructure_map_pattern` and the comprehension parsers are separate
call sites with their own comma-loops, not shared with the four covered
here, and folding them in would widen this beyond one focused session;
leave them as a candidate for a future, separately-scoped task if
still desired. Single-element trailing commas (`[1,]`, `{"a": 1,}`,
`f(1,)`, `fn f(a,) { ... }`) are in scope and must work the same as the
multi-element case — the `break` fires right after the one comma
regardless of how many elements preceded it.

Acceptance criteria:
- `print([1, 2, 3,]);` prints the list `[1, 2, 3]` — no longer a
  `ParseError`.
- `print([1,]);` prints `[1]` — single-element trailing comma.
- `print([]);` still parses as an empty list (unaffected — no comma at
  all in this case, confirms the empty-literal path wasn't touched).
- `print({"a": 1, "b": 2,});` prints the map `{"a": 1, "b": 2}`.
- `print({"a": 1,});` prints `{"a": 1}` — single-entry trailing comma.
- `print({});` still parses as an empty map (unaffected).
- `fn f(a, b) { return a + b; } print(f(1, 2,));` prints `3`.
- `fn f(a) { return a; } print(f(1,));` prints `1`.
- `fn f(a, b,) { return a + b; } print(f(1, 2));` prints `3` — trailing
  comma in the parameter list, not just the call.
- `fn f(a,) { return a; } print(f(1));` prints `1`.
- `fn f(a, ...rest,) { return rest; } print(f(1, 2, 3));` prints
  `[2, 3]` — trailing comma after a rest parameter is accepted.
- `fn f(a, ...rest, b) { return a; }` still raises `ParseError` matching
  `"rest parameter must be the last parameter"` — confirms a *real*
  parameter after the rest one is still rejected, only a bare trailing
  comma with nothing after it is now accepted.
- `[1, , 3];` (an empty slot between two commas, not a single trailing
  comma) still raises `ParseError` matching `"expected an expression,
  found ','"` — confirms this task only special-cases a comma
  immediately before the closing delimiter, not comma runs in general.
- Every pre-existing list/map-literal, call-argument, and
  function-parameter test continues to pass unmodified, including
  spread elements/arguments/rest parameters and keyword arguments
  without a trailing comma.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_list_literal`, `_map_literal`,
`_finish_call`, `_fn_param_list`), `tests/test_parser.py` (model on
`class TestCalls` and `class TestListsAndMaps`, search both). Once
merged, `README.md`'s Values/Calls-adjacent bullets need a mention that
trailing commas are accepted in these four positions, and `PROJECT.md`'s
roadmap paragraph needs this moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `is_evil` / `is_odious` — binary popcount-parity predicates

Build: the breadth task after task 5's depth work (trailing commas) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that `is_repdigit` has landed via PR #260, dropping the count to
the 5-task floor. Add `is_evil(n)`/`is_odious(n)` to `cinder/builtins.py`,
registered right after `is_power_of_two` (search for `def
_is_power_of_two`, immediately before `_is_palindrome_list`) —
`is_power_of_two` is currently the only builtin that reasons about a
number's binary representation rather than its decimal one, via the `n &
(n - 1) == 0` bit trick; evil/odious numbers are the natural next member
of that same "binary bit-trick" family, classifying every non-negative
integer by whether its binary representation has an even ("evil") or odd
("odious") count of `1` bits (its popcount) — together a complete two-way
partition of the non-negative integers, the same "every input lands in
exactly one bucket" shape `is_perfect_number`/`is_abundant`/`is_deficient`
already established for divisor sums. Verify the gap: `python3 -m
cinder.cli eval 'print(is_evil(3));'` currently raises
`CinderRuntimeError` `"undefined name 'is_evil'"` — no such builtin exists
yet.

```python
def _is_evil(arguments: list, line: int, column: int) -> object:
    _require_arity("is_evil", arguments, 1, line, column)
    value = _require_int("is_evil", arguments[0], line, column)
    if value < 0:
        raise CinderRuntimeError(
            "is_evil() requires a non-negative integer, domain error", line, column
        )
    return bin(value).count("1") % 2 == 0


def _is_odious(arguments: list, line: int, column: int) -> object:
    _require_arity("is_odious", arguments, 1, line, column)
    value = _require_int("is_odious", arguments[0], line, column)
    if value < 0:
        raise CinderRuntimeError(
            "is_odious() requires a non-negative integer, domain error", line, column
        )
    return bin(value).count("1") % 2 == 1
```

Model the arity/type-checking exactly on `is_power_of_two`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). Unlike
`is_power_of_two` (which answers `false` for non-positive input rather
than raising), negative input here raises a domain error instead —
popcount parity is only well-defined for a finite non-negative bit
pattern; Python's own two's-complement-style `bin(-5) == '-0b101'` would
silently count the `1`s in the magnitude only, producing a well-typed but
mathematically meaningless answer for a negative input rather than an
honest error, so this follows `divisors`'/`log()`'s "raise a domain error
rather than leak a wrong-looking result" convention instead of
`is_power_of_two`'s "false" one. `0` is a valid input (`bin(0) ==
'0b0'`, zero `1` bits, even, so `is_evil(0)` is `true`) — the trivial
base case, not a domain edge to guard against. Bundle both predicates in
this one task since each is a one-line delegation to the same
`bin(value).count("1") % 2` expression differing only in which parity it
accepts — matching how `is_int`/`is_float` and `is_subset`/`is_superset`
were each bundled as a single task earlier in this backlog's history,
rather than as two separate breadth tasks back to back (which the
breadth-vs-depth policy already treats as a signal to inject a depth
task instead).

Acceptance criteria:
- `is_evil(0);` is `true` — zero `1` bits, even.
- `is_evil(3);` is `true` — `0b11`, two `1` bits.
- `is_evil(5);` is `true` — `0b101`, two `1` bits.
- `is_evil(6);` is `true` — `0b110`, two `1` bits.
- `is_evil(1);` is `false` — `0b1`, one `1` bit (odd).
- `is_odious(1);` is `true`.
- `is_odious(2);` is `true` — `0b10`, one `1` bit.
- `is_odious(4);` is `true` — `0b100`, one `1` bit.
- `is_odious(3);` is `false`.
- For every integer `0` through `31`, `is_evil(n) != is_odious(n)` — the
  two predicates are exact complements over the same domain (test via a
  loop or an explicit list of both buckets).
- `is_evil(1024);` is `false` — `0b10000000000`, one `1` bit (odious).
- `is_evil(-1);` raises `CinderRuntimeError` matching `"is_evil()
  requires a non-negative integer, domain error"`.
- `is_odious(-4);` raises `CinderRuntimeError` matching `"is_odious()
  requires a non-negative integer, domain error"`.
- `is_evil(5.0);` raises `CinderRuntimeError` matching `"is_evil()
  requires an int, got float"` — the same message shape `_require_int`
  already produces elsewhere.
- `is_odious(true);` raises `CinderRuntimeError` matching `"is_odious()
  requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column, for both builtins.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register both near `is_power_of_two`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestIsPowerOfTwo` test
class, search `class TestIsPowerOfTwo`). Once merged, `README.md`'s
Builtins bullet needs `is_evil`/`is_odious` added near `is_power_of_two`,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Language: list concatenation via `+`, closing the gap between the existing `concat()` builtin and infix syntax

Build: the depth task after task 5's breadth work (`is_evil`/`is_odious`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that scientific notation for float literals has landed
via PR #261, dropping the count to the 5-task floor. `cinder/
interpreter.py`'s `_apply_binary_operator` already special-cases `+` for
two shapes — `_is_number(left) and _is_number(right)` and `isinstance(
left, str) and isinstance(right, str)` — falling through to an
"unsupported operand types" error for everything else, including two
lists. Meanwhile `*` already treats `list * int`/`int * list` as
repetition (`_repeat_op`, right above `_numeric_op` in the same file),
so lists already participate in one infix arithmetic operator; `+` is
the one still missing, even though the `concat()` builtin already does
exactly this as a function call (`cinder/builtins.py`, search `def
_concat`) — the same "builtin already exists, infix syntax doesn't"
gap `**` closed for `pow()`, and pipe closed for chained calls. Verify
the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2] + [3, 4]);'
# -> CinderRuntimeError: unsupported operand types for '+': list and list
python3 -m cinder.cli eval 'print(concat([1, 2], [3, 4]));'
# -> [1, 2, 3, 4] -- the exact same result, only reachable today via the builtin
```

In `_apply_binary_operator`'s `TokenType.PLUS` branch (`cinder/
interpreter.py`, right after the existing `isinstance(left, str) and
isinstance(right, str)` check and before the final `raise`), add one
more branch:
```python
            if isinstance(left, list) and isinstance(right, list):
                return left + right
```
Python's own list `+` already builds a fresh list without mutating
either operand — the same non-mutating convention `_repeat_op` already
established for `list * int` (see `test_list_repetition_does_not_mutate_
input` in `tests/test_interpreter.py`), so no extra copying logic is
needed. Mixed-type operands (`[1, 2] + "a"`, `[1, 2] + 3`, `[1, 2] +
{"a": 1}`) must keep raising the existing "unsupported operand types"
error — this task adds exactly one new accepted shape, list-plus-list,
not a general coercion. Because compound assignment desugars `+=` to an
ordinary `Binary` node with a `PLUS` operator and reuses
`_apply_binary_operator` (confirmed: `cinder/parser.py`'s
`_COMPOUND_ASSIGN_OPS` maps `PLUSEQ` to `PLUS`, no separate evaluation
path), `xs += [3, 4]` starts working the same moment this branch lands
— a zero-extra-code consequence of reusing the same dispatch, not a
second change to make. No parser or lexer changes at all: `+` is
already tokenized and already reaches `_apply_binary_operator` for
every operand type, this only widens what that function accepts.

Acceptance criteria:
- `[1, 2] + [3, 4];` is `[1, 2, 3, 4]`.
- `[] + [1];` is `[1]` and `[1] + [];` is `[1]` — an empty operand on
  either side.
- `[] + [];` is `[]`.
- `let a = [1, 2]; let b = [3, 4]; let c = a + b; print(a); print(b);
  print(c);` prints `[1, 2]`, `[3, 4]`, `[1, 2, 3, 4]` — neither
  original list is mutated, matching `_repeat_op`'s existing
  non-mutating convention.
- `let xs = [1, 2]; xs += [3, 4]; print(xs);` prints `[1, 2, 3, 4]` —
  `+=` on a list works for free via the shared `Binary`/`PLUS`
  desugaring, no separate code path.
- `let xs = [1]; xs = xs + [2] + [3]; print(xs);` is `[1, 2, 3]` — `+`
  stays left-associative for lists, same as it already is for numbers
  and strings.
- `[1, 2] + "a";` still raises `CinderRuntimeError` matching
  `"unsupported operand types for '+': list and string"`.
- `[1, 2] + 3;` still raises the same error shape, `"list and int"` —
  confirms this doesn't get swept into `*`'s repetition behavior.
- `[1, 2] + {"a": 1};` still raises the same error shape, `"list and
  map"`.
- `1 + 2;` is still `3` and `"a" + "b";` is still `"ab"` — the two
  existing `+` shapes are unaffected by the new branch.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`TokenType.PLUS` branch), `tests/test_interpreter.py` (model the new
list-plus-list cases on the existing `TestRepetition` class, which
covers `*`'s analogous list special-casing — search `class
TestRepetition`; add the mixed-type-still-raises cases near the
existing `+` error-shape assertions, search `TestArithmetic`),
`tests/test_errors.py` (existing `"unsupported operand types for
'+'"` assertions there are int/string cases and stay unmodified — no
new error-message assertions needed there since this task doesn't
change any error message, only adds one non-error branch). Once
merged, `README.md`'s Operators bullet needs a mention that `+` also
concatenates two lists (non-mutating, same as `concat()`), alongside
the existing `*` repetition mention, and `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
