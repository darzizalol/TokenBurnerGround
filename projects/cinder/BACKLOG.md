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

## 1. Language: default values in list-destructuring patterns (`let [a, b = 5] = expr;`)

Build: the depth task after task 4's breadth work (`is_pronic`) per
`PROJECT.md`'s breadth-vs-depth policy. Every list-destructuring form —
`let [a, b] = expr;`, plain assignment `[a, b] = expr;`, `for [a, b] in
list_of_pairs { ... }`, function params `fn f([a, b]) { ... }`, and both
comprehension loop-variable forms — currently requires the source list
to have *exactly* as many elements as the pattern names (or, with a
`...rest`, at least that many); there is no way to say "use this value
if the source list didn't have one", unlike function parameters, which
already support `fn f(a, b = 1) { ... }`. Verify the gap:
`python3 -m cinder.cli eval 'let [a, b = 5] = [1]; print(a); print(b);'`
currently raises `CinderRuntimeError` `"destructuring pattern expects 2
elements, got 1"` (`cinder/interpreter.py`'s `_bind_list_destructure`
has no concept of an optional trailing name).

Scoped to **list** patterns only — map patterns already have a
different, well-defined behavior for a "missing" key (`"destructuring
pattern expects key 'x', not found in map"`, a domain error, not a
gap), so adding defaults there is a separate design decision, left for
a future task if wanted. Also scoped to the **`let`/`for`/param/
comprehension forms only**, not the plain-assignment form
(`[a, b] = expr;`) — that form parses its pattern by first parsing an
ordinary `ListLiteral` (`_destructure_assign_pattern`, called from
`_brace_statement`'s sibling logic after `_assignment()` succeeds) and
list-literal elements parse via `_list_element`, which calls `_ternary()`
(search for `def _list_element` — confirms `b = 5` is not a valid
list-element expression at that precedence, so `[a, b = 5] = expr;`
would already be a `ParseError` before ever reaching
`_destructure_assign_pattern`; teaching that form to accept per-element
defaults would mean special-casing `=` inside `_list_element` itself,
a materially different, riskier change than this task's scope).

All four in-scope forms share one parser entry point,
`_destructure_list_pattern` (search for `def _destructure_list_pattern`
in `cinder/parser.py`), and one interpreter entry point,
`_bind_list_destructure` (search for `def _bind_list_destructure` in
`cinder/interpreter.py`) — the same centralization the map-destructuring
key rename task (PR #239) relied on for the map-pattern side. Note
`_bind_list_destructure` is
*also* called for the out-of-scope plain-assignment form (from
`_evaluate_destructure_assign`), so its `names` parameter's shape must
stay uniform across both parsing paths even though only one produces
real defaults.

Change `names` from a flat `list[str]` to a `list[tuple[str, "Expr |
None"]]` of `(name, default)` pairs, `default` being `None` when no `=
expr` was written. Add a shared parsing helper right above
`_destructure_list_pattern`, mirroring `_fn_param`'s own
`seen_default`-tracking convention for plain function parameters
(search for `def _fn_param`, the `seen_default` parameter and the
"destructuring parameter without a default value follows a parameter
with one" `ParseError` it raises — same ordering rule, applied one
level down to pattern *elements* instead of whole parameters):

```python
def _destructure_list_pattern_entry(self, seen_default: bool) -> "tuple[str, Expr | None]":
    name_token = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern")
    if self._check(TokenType.EQ):
        self._advance()
        default = self._ternary()
        return name_token.lexeme, default
    if seen_default:
        raise ParseError(
            "element without a default value follows an element with one "
            "in destructuring pattern",
            name_token.line,
            name_token.column,
        )
    return name_token.lexeme, None
```

In `_destructure_list_pattern`, replace both
`names.append(self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme)`
lines (the initial entry and the one inside the `while COMMA` loop)
with a call to the new helper, tracking `seen_default` the same way
`_fn_param_list` does:

```python
    def _destructure_list_pattern(self) -> "tuple[list, str | None]":
        self._advance()  # consume '['
        names = []
        rest = None
        seen_default = False
        if self._check(TokenType.DOT_DOT_DOT):
            rest = self._destructure_rest_name()
        else:
            names.append(self._destructure_list_pattern_entry(seen_default))
            seen_default = names[-1][1] is not None
        while self._check(TokenType.COMMA):
            self._advance()
            if rest is not None:
                token = self._peek()
                raise ParseError(
                    f"rest element must be last in destructuring pattern, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._destructure_rest_name()
            else:
                names.append(self._destructure_list_pattern_entry(seen_default))
                seen_default = seen_default or names[-1][1] is not None
        self._consume(TokenType.RBRACKET, "']' after destructuring pattern")
        return names, rest
```

This automatically covers `let`, `for`, list-comprehension loop
variables, and function-parameter destructuring (`_fn_param`'s
`LBRACKET` branch calls `_destructure_list_pattern` directly — search
for the call site, it needs no changes itself). `_fn_param`'s *existing*
rejection of a whole-pattern default (`fn f([a, b] = [1, 2])`, the
`if self._check(TokenType.EQ): raise ParseError("destructuring
parameter cannot have a default value", ...)` block right after the
`_destructure_list_pattern()` call) stays completely untouched and
unaffected — that check fires on the `=` *after* the closing `]`, while
this task's new per-element defaults are consumed *inside* the brackets,
so the two features don't interact; `fn f([a, b = 1]) { ... }` (a
per-element default) is accepted by this task, `fn f([a, b] = [1, 2])
{ ... }` (a whole-pattern default) still isn't, by design.

In `_destructure_assign_pattern` (the plain-assignment form's own
pattern builder, kept out of scope for real defaults per the note
above), change the one line `names.append(element.name)` to
`names.append((element.name, None))` so its output shape matches the
new `(name, default)` pair convention `_bind_list_destructure` now
expects uniformly, regardless of which parsing path produced it.

In `_bind_list_destructure`, unpack the pairs, compute how many names
are *required* (those with no default — defaults are enforced trailing
by the parser, so this is just "everything before the first default"),
and fill in missing trailing values from their defaults, evaluated in
`env` in pattern order (so a later default *can* see an earlier
pattern name already bound in the same `env` — e.g. `let [a, b = a + 1]
= [5];` binds `b` to `6`, since `a` is `env.define`'d before `b`'s
default is evaluated; this is a deliberate, useful consequence of
left-to-right processing, not a special case):

```python
def _bind_list_destructure(
    self,
    env: Environment,
    names: list,
    rest: "str | None",
    value: object,
    line: int,
    column: int,
    use_assign: bool = False,
) -> None:
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"cannot destructure {type_name(value)} as a list",
            line,
            column,
        )
    required = sum(1 for _, default in names if default is None)
    has_defaults = required < len(names)
    if rest is not None:
        if len(value) < required:
            raise CinderRuntimeError(
                f"destructuring pattern expects at least {required} elements, "
                f"got {len(value)}",
                line,
                column,
            )
        for index, (name, default) in enumerate(names):
            item = value[index] if index < len(value) else self.evaluate(default, env)
            self._bind_destructure_name(env, name, item, line, column, use_assign)
        self._bind_destructure_name(
            env, rest, list(value[len(names):]), line, column, use_assign
        )
        return
    if len(value) < required or len(value) > len(names):
        if has_defaults:
            raise CinderRuntimeError(
                f"destructuring pattern expects between {required} and {len(names)} "
                f"elements, got {len(value)}",
                line,
                column,
            )
        raise CinderRuntimeError(
            f"destructuring pattern expects {len(names)} elements, got {len(value)}",
            line,
            column,
        )
    for index, (name, default) in enumerate(names):
        item = value[index] if index < len(value) else self.evaluate(default, env)
        self._bind_destructure_name(env, name, item, line, column, use_assign)
```

Note when no name in the pattern has a default, `required == len(names)`
and `has_defaults` is `False`, so both branches raise the *exact* same
message text as today — this is purely additive for every pre-existing
pattern. `_bind_destructure_name` itself needs no changes. `call_value`
(search for `def call_value`) needs **no changes at all** — its
existing `Interpreter()._bind_list_destructure(call_env, param.names,
param.rest, value, line, column)` call site (in the `if param.names is
not None: ... else: ...` dispatch, right after parameter-value
selection) already forwards `param.names` opaquely, so it benefits from
element-level defaults automatically once `_fn_param` starts producing
the new pair shape. (If task 3, keyword arguments, has landed by the
time this task is picked up, that value-selection block will look
slightly different — it'll also check `keywords` — but the destructure-bind
call right below it is unaffected either way, per task 3's own note that
its `keywords` change doesn't touch that part of the loop.)

Acceptance criteria:
- `let [a, b = 5] = [1]; print(a); print(b);` prints `1` then `5` — `b`
  has no source value, so its default is used.
- `let [a, b = 5] = [1, 2]; print(b);` prints `2` — a default is only
  used when the source list doesn't reach that position.
- `let [a, b = a + 1] = [5]; print(b);` prints `6` — a later default
  can reference an earlier pattern name already bound in the same
  `let`.
- `[a, b] = [b, a];` (no defaults anywhere) behaves identically to
  before this task — purely additive syntax.
- `for [a, b = 0] in [[1], [2, 3]] { print(a + b); }` prints `1` then
  `5` — the destructuring loop-variable form gets defaults too.
- `fn f([a, b = 10]) { return a + b; } print(f([1]));` prints `11`.
- `print([a + b for [a, b = 100] in [[1], [2, 3]]]);` prints
  `[101, 5]`.
- `let [a = 1, ...rest] = []; print(a); print(rest);` prints `1` then
  `[]` — a default combines with a trailing rest element; the rest
  collects nothing since the source list was empty.
- `let [a, b = 1] = [];` raises `CinderRuntimeError` matching
  `"destructuring pattern expects between 1 and 2 elements, got 0"` —
  `a` has no default so it's still required, but the message accounts
  for the range a default makes possible, not a single fixed count.
- `let [a, b = 1] = [1, 2, 3];` raises `CinderRuntimeError` matching
  `"destructuring pattern expects between 1 and 2 elements, got 3"` —
  too many elements and no rest to absorb the extra one.
- `let [a, b = 1, ...rest] = [];` raises `CinderRuntimeError` matching
  `"destructuring pattern expects at least 1 elements, got 0"` — the
  rest-present branch's message, distinct from the no-rest "between X
  and Y" wording above: with a rest element there's no upper bound to
  report, only the lower one.
- `let [a] = [1, 2];` (no defaults) raises `CinderRuntimeError` matching
  `"destructuring pattern expects 1 elements, got 2"` — the exact,
  unchanged pre-existing message text for a pattern with no defaults.
- `fn f([a = 1, b]) { return a; }` raises `ParseError` matching
  `"element without a default value follows an element with one in
  destructuring pattern"` — a required element after a defaulted one.
- `fn f([a, b] = [1, 2]) { ... }` (a whole-pattern default, not a
  per-element one) still raises `ParseError` matching `"destructuring
  parameter cannot have a default value"` — unaffected by this task.
- `[a, b = 5] = [1];` (the plain-assignment form) raises `ParseError`
  — per-element defaults are out of scope for that form; it still
  fails the same way it does today (as an invalid list-literal element
  before even reaching destructuring-pattern validation).
- Full test suite passes.

Likely files: `cinder/parser.py` (new
`_destructure_list_pattern_entry`, `_destructure_list_pattern`,
`_destructure_assign_pattern`'s one-line shape fix),
`cinder/interpreter.py` (`_bind_list_destructure`), `tests/test_parser.py`
(shape assertions for every list-pattern — i.e. `is_map=False` —
`DestructureLetStmt`/`ForStmt`/`Param`/`ListComprehension`/
`MapComprehension` site changes from flat strings like `["a"]` to pair
form `[("a", None)]`, plus new default-value tests; search for
`"DestructureLetStmt"` and similar in `stmt_shape`/`shape` call sites),
`tests/test_interpreter.py` (new default-value tests for `let`/
assignment/`for`/params/comprehensions). Once merged, `README.md`'s
destructuring bullets need a defaults mention added for list patterns,
and `PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `collatz_length` — steps to reach 1 under the Collatz recurrence

Build: the breadth task after task 5's depth work (default values in
list-destructuring patterns) per `PROJECT.md`'s breadth-vs-depth
policy. For a positive integer `n`, the Collatz (3n+1) recurrence
repeatedly replaces `n` with `n / 2` if `n` is even, or `3n + 1` if
`n` is odd, until it reaches `1`; `collatz_length(n)` returns the
number of steps that takes (e.g. `6 -> 3 -> 10 -> 5 -> 16 -> 8 -> 4 ->
2 -> 1` is 8 steps). It joins `is_happy_number`'s
iterate-and-count-steps technique (search for `def _is_happy_number`,
the natural neighbor to register next to — same "keep applying a
recurrence until a stopping condition" shape, just counting steps
instead of tracking a `seen` set for cycle detection, since the
Collatz conjecture — unproven but true for every integer ever
checked, including anything reachable via a 64-bit Cinder int — is
that this process always reaches `1`, never cycles, so no cycle guard
is needed):

```python
def _collatz_length(arguments: list, line: int, column: int) -> object:
    _require_arity("collatz_length", arguments, 1, line, column)
    value = _require_int("collatz_length", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "collatz_length() requires a positive integer, domain error", line, column
        )
    steps = 0
    n = value
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps
```

Model the arity/type-checking exactly on `is_happy_number`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). Unlike
`is_happy_number` (which answers `false` on out-of-domain input), `n <
1` raises a domain error rather than returning a number — there is no
sensible Collatz step count for zero or negative input (the recurrence
isn't defined there), mirroring `divisors`/`aliquot_sum`'s own
type-vs-domain-error convention rather than the boolean-predicate
cluster's answer-`false` one, since this builtin returns a number, not
a boolean.

Acceptance criteria:
- `collatz_length(1);` is `0` — already at `1`, zero steps needed.
- `collatz_length(2);` is `1` — `2 -> 1`.
- `collatz_length(4);` is `2` — `4 -> 2 -> 1`.
- `collatz_length(6);` is `8` — `6 -> 3 -> 10 -> 5 -> 16 -> 8 -> 4 -> 2
  -> 1`.
- `collatz_length(27);` is `111` — the famous long-running example for
  a small starting value, a case large enough to catch an off-by-one
  in the loop's step counting.
- `collatz_length(0);` raises `CinderRuntimeError` matching
  `"collatz_length() requires a positive integer, domain error"`.
- `collatz_length(-6);` raises `CinderRuntimeError` matching
  `"collatz_length() requires a positive integer, domain error"`.
- `collatz_length(5.0);` raises `CinderRuntimeError` matching
  `"collatz_length() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `collatz_length(true);` raises `CinderRuntimeError` matching
  `"collatz_length() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_happy_number`/`is_fibonacci`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `collatz_length` added near
`is_happy_number`/`is_fibonacci`, and `PROJECT.md`'s roadmap paragraph
needs it moved from backlog to landed — leave both to the Architect's
next grooming pass, not this task.

---

## 3. Standard library: `is_strong_number` — sum of digit factorials equals the number

Build: a second breadth task after task 5's `collatz_length`, restocking
the backlog back past its 5-task floor rather than strictly alternating
into a depth task this time (mirroring how `aliquot_sum` followed
`is_perfect_cube` two breadth tasks in a row for the same restocking
reason). Add `is_strong_number(n)` to `cinder/builtins.py`, registered
right after `is_armstrong` (search for `def _is_armstrong`) — the
digit-factorial-sum sibling of `is_armstrong`'s digit-power-sum check,
same "read each decimal digit, apply a per-digit transform, sum, and
compare to `n`" shape, reusing the already-registered `factorial`
builtin's underlying `math.factorial` rather than reimplementing it.
A strong number (also called a factorion) is a positive integer equal
to the sum of the factorials of its own decimal digits — e.g. `145 =
1! + 4! + 5! = 1 + 24 + 120 = 145`. Exactly four exist in base 10 (`1`,
`2`, `145`, `40585`); `0` and `1` are edge cases worth naming explicitly
in tests since `0! == 1` (so a single `"0"` digit sums to `1`, not `0`,
making `is_strong_number(0)` false) while `1! == 1` (so `is_strong_number(1)`
is true, `1` being its own digit-factorial sum):

```python
def _is_strong_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_strong_number", arguments, 1, line, column)
    value = _require_int("is_strong_number", arguments[0], line, column)
    if value < 0:
        return False
    return sum(math.factorial(int(digit)) for digit in str(value)) == value
```

Model the arity/type-checking exactly on `is_armstrong`'s own structure:
`_require_arity`, then `_require_int` (reusing the shared helper — do
**not** hand-roll a separate `isinstance` check). The `value < 0` guard
answers `false` on negative input rather than raising a domain error,
matching `is_armstrong`/`is_pronic`'s own convention (no negative
integer has a well-defined "sum of digit factorials" comparison, since
`str(value)` for a negative `value` would include a literal `-`
character that `int(digit)` can't parse — the early return avoids ever
reaching that call, exactly how `is_armstrong` avoids the equivalent
issue for its own digit-power sum).

Acceptance criteria:
- `is_strong_number(1);` is `true` — `1! = 1`.
- `is_strong_number(2);` is `true` — `2! = 2`.
- `is_strong_number(145);` is `true` — `1! + 4! + 5! = 1 + 24 + 120 =
  145`, the best-known example.
- `is_strong_number(40585);` is `true` — `4! + 0! + 5! + 8! + 5! =
  24 + 1 + 120 + 40320 + 120 = 40585`, the largest base-10 strong
  number.
- `is_strong_number(0);` is `false` — `0!` is `1`, not `0`, so the
  single-digit sum doesn't equal the value.
- `is_strong_number(3);` is `false` — `3! = 6 != 3`.
- `is_strong_number(25);` is `false` — `2! + 5! = 2 + 120 = 122 != 25`.
- `is_strong_number(-145);` is `false` — negative input answers `false`
  without raising.
- `is_strong_number(5.0);` raises `CinderRuntimeError` matching
  `"is_strong_number() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_strong_number(true);` raises `CinderRuntimeError` matching
  `"is_strong_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_armstrong`/`is_perfect_number`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_strong_number` added
near `is_armstrong`, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## 4. Language: unary `+` operator (`+expr`)

Build: a language-depth task closing a real asymmetry in the unary
operator set. Every other classic unary operator is implemented —
`-` (arithmetic negation), `not` (logical), `~` (bitwise complement) —
but plain unary `+` isn't. Verify the gap:
`python3 -m cinder.cli eval 'print(+5);'` currently raises `ParseError`
`"expected an expression, found '+'"` (`cinder/parser.py`'s
`_UNARY = {TokenType.MINUS, TokenType.NOT, TokenType.TILDE}`, search
for `_UNARY = {`, simply never included `TokenType.PLUS`). The gap is
also asymmetric with the doubled-token case already handled for minus:
`python3 -m cinder.cli eval 'print(--5);'` already evaluates to `5`
today (`_unary`, search for `def _unary`, explicitly re-splits a
lexer-merged `MINUSMINUS` token into nested `Unary(MINUS, ...)` nodes,
per the comment at the top of `cinder/parser.py`, lines 27-36), but
`python3 -m cinder.cli eval 'print(++5);'` raises `ParseError`
`"expected an expression, found '++'"` — there's no equivalent
`PLUSPLUS` re-split.

Not in scope: this does **not** touch the statement-only postfix
`x++`/`x--` sugar (`_INCREMENT_DECREMENT_OPS`, `_expr_or_incdec`,
search for both) at all — that machinery only fires *after*
`_assignment()` already returned a complete `Identifier`/`Index`
expression, checking for a *trailing* `PLUSPLUS`/`MINUSMINUS` token;
this task only ever adds handling for a *leading* `PLUS`/`PLUSPLUS`
token at the start of `_unary()`, an entirely different parse
position, so the two can't collide (confirmed: `x++;`/`x--;` still
parse exactly as before, since `_unary()` never runs on the `x` token
itself — `x` is a plain `IDENTIFIER`, not a unary-operator token).
Also not in scope: no new AST node — `Unary` (`cinder/ast_nodes.py`)
already carries an arbitrary operator `Token`, so no changes are
needed there at all.

**Parsing** (`cinder/parser.py`): add `TokenType.PLUS` to `_UNARY`:

```python
_UNARY = {TokenType.MINUS, TokenType.PLUS, TokenType.NOT, TokenType.TILDE}
```

This alone makes `_unary`'s existing generic branch
(`if self._peek().type in _UNARY: operator = self._advance(); operand
= self._unary(); return Unary(operator, operand)`) handle a single
`+expr` for free — no other change needed for that case. Then, mirror
the existing `MINUSMINUS` re-split branch (the first `if` in `_unary`)
with an equivalent `PLUSPLUS` branch, for the same reason stated in
that branch's own comment: a leading `++` in expression position can
never be a postfix increment, since there's nothing before it to
increment, so it unambiguously means double unary plus:

```python
def _unary(self) -> Expr:
    if self._check(TokenType.MINUSMINUS):
        token = self._advance()
        minus = Token(TokenType.MINUS, "-", None, token.line, token.column)
        return Unary(minus, Unary(minus, self._unary()))
    if self._check(TokenType.PLUSPLUS):
        token = self._advance()
        plus = Token(TokenType.PLUS, "+", None, token.line, token.column)
        return Unary(plus, Unary(plus, self._unary()))
    if self._peek().type in _UNARY:
        operator = self._advance()
        operand = self._unary()
        return Unary(operator, operand)
    return self._call()
```

Update the file's top-of-file grammar docstring (lines 1-9) — the
precedence line currently reads `+ - > * / % > unary (- not ~)`;
change to `+ - > * / % > unary (- + not ~)`. Also extend the
`MINUSMINUS` explanation paragraph (lines 27-36) with one sentence
noting `PLUSPLUS` gets the identical treatment for the identical
reason, so the doc doesn't go stale relative to the code.

**Evaluation** (`cinder/interpreter.py`): `_evaluate_unary` (search for
`def _evaluate_unary`) currently branches on `MINUS`/`NOT`/`TILDE`. Add
a `PLUS` branch, modeled exactly on the existing `MINUS` branch's
type-checking (reusing `_NUMERIC`/`type_name`, already imported/defined
in this module — no new imports needed), rejecting `bool` the same way
`MINUS` does (`isinstance(operand, bool)` is checked separately since
`bool` is a Python `int` subclass):

```python
    def _evaluate_unary(self, expr: Unary, env: Environment) -> object:
        operand = self.evaluate(expr.operand, env)
        if expr.operator.type == TokenType.MINUS:
            if not isinstance(operand, _NUMERIC) or isinstance(operand, bool):
                raise CinderRuntimeError(
                    f"unary '-' requires a number, got {type_name(operand)}",
                    expr.operator.line,
                    expr.operator.column,
                )
            return -operand
        if expr.operator.type == TokenType.PLUS:
            if not isinstance(operand, _NUMERIC) or isinstance(operand, bool):
                raise CinderRuntimeError(
                    f"unary '+' requires a number, got {type_name(operand)}",
                    expr.operator.line,
                    expr.operator.column,
                )
            return +operand
        if expr.operator.type == TokenType.NOT:
            return not is_truthy(operand)
        ...  # TILDE branch unchanged
```

`+operand` is a true no-op for `int`/`float` (Python's own unary `+`
is identity for both) — this exists purely so `+expr` type-checks and
composes with the rest of the unary chain (`-+5`, `++5`), not to
transform the value.

Acceptance criteria:
- `print(+5);` prints `5`.
- `print(+5.5);` prints `5.5`.
- `print(+0);` prints `0`.
- `print(-+5);` prints `-5` — unary plus composes with unary minus,
  doesn't cancel or flip it.
- `print(++5);` prints `5` — the doubled-token `PLUSPLUS` re-split
  case, mirroring `--5` already printing `5` today.
- `print(2 + +3);` prints `5` — binary `+` followed by a unary `+`
  operand (space-separated so they lex as two distinct `PLUS` tokens,
  not one merged `PLUSPLUS`).
- `print(+(-5));` prints `-5` — parenthesized grouping under unary
  plus is unaffected.
- `print(+true);` raises `CinderRuntimeError` matching `"unary '+'
  requires a number, got bool"`.
- `print(+"abc");` raises `CinderRuntimeError` matching `"unary '+'
  requires a number, got string"`.
- `print(+nil);` raises `CinderRuntimeError` matching `"unary '+'
  requires a number, got nil"`.
- `print(+[1, 2]);` raises `CinderRuntimeError` matching `"unary '+'
  requires a number, got list"`.
- `let x = 5; x++; print(x);` still prints `6` and `let x = 5; x--;
  print(x);` still prints `4` — the pre-existing postfix `x++`/`x--`
  statement sugar is completely unaffected by this task (different
  parse position, per the Not-in-scope discussion above).
- Every pre-existing unary-minus/`not`/`~` test continues to pass
  unmodified — this task only adds a new branch/token to each
  function, changing nothing about the existing ones.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_UNARY`, `_unary`, top-of-file
grammar docstring), `cinder/interpreter.py` (`_evaluate_unary`),
`tests/test_parser.py` (shape assertions for `+5`/`++5`/`-+5`, modeled
on the existing `("Unary", TokenType.MINUS, ...)` shape assertions —
search for `"Unary"` in the shape helper), `tests/test_interpreter.py`
(new cases in `TestUnaryAndGrouping`, modeled on `test_unary_minus`/
`test_double_unary_minus`, plus error-path tests modeled on
`test_unary_minus_on_string_raises`). Once merged, `README.md`'s
Operators bullet needs a unary-`+` mention, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 5. Standard library: `num_divisors` — count of an integer's positive divisors

Build: the breadth task after task 5's depth work (unary `+`) per
`PROJECT.md`'s breadth-vs-depth policy — also restocking the backlog
back to 6 tasks now that keyword arguments (the task that used to sit
at the top of this file) has landed and dropped the count to the
5-task floor. Add `num_divisors(n)` to `cinder/builtins.py`, registered
right after `aliquot_sum` (search for `def _aliquot_sum`, the current
last entry in the divisor cluster) — the count-returning sibling of
`divisors`'s list-returning walk and `aliquot_sum`'s sum-returning walk,
all three of which already trial-divide to `sqrt(n)` pairing each
divisor with its complement; `num_divisors` just counts instead of
collecting or summing:

```python
def _num_divisors(arguments: list, line: int, column: int) -> object:
    _require_arity("num_divisors", arguments, 1, line, column)
    value = _require_int("num_divisors", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "num_divisors() requires a positive integer, domain error", line, column
        )
    if value == 1:
        return 1
    count = 2  # 1 and value itself
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            count += 1
            complement = value // divisor
            if complement != divisor:
                count += 1
    return count
```

Model the arity/type-checking exactly on `divisors`/`aliquot_sum`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). `n < 1`
raises a domain error rather than returning a count, mirroring
`divisors`/`aliquot_sum`'s own type-vs-domain-error convention rather
than the boolean-predicate cluster's answer-`false` one, since this
builtin returns a number, not a boolean. The `value == 1` special case
matches `divisors`/`aliquot_sum`'s own early-return (avoids the
`range(2, math.isqrt(1) + 1)` loop trivially running zero times and
undercounting — `1`'s only divisor is itself, counted once, not the
`count = 2` starting assumption every other value gets).

Acceptance criteria:
- `num_divisors(1);` is `1` — `1`'s only divisor is itself.
- `num_divisors(7);` is `2` — a prime has exactly two divisors, `1`
  and itself.
- `num_divisors(6);` is `4` — `1, 2, 3, 6`.
- `num_divisors(28);` is `6` — `1, 2, 4, 7, 14, 28` (also a perfect
  number, a useful cross-check against `divisors(28)`'s existing
  length).
- `num_divisors(36);` is `9` — a perfect square, exercising the
  `complement == divisor` dedup path (`6` is only counted once even
  though it pairs with itself).
- `num_divisors(0);` raises `CinderRuntimeError` matching
  `"num_divisors() requires a positive integer, domain error"`.
- `num_divisors(-6);` raises `CinderRuntimeError` matching
  `"num_divisors() requires a positive integer, domain error"`.
- `num_divisors(5.0);` raises `CinderRuntimeError` matching
  `"num_divisors() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `num_divisors(true);` raises `CinderRuntimeError` matching
  `"num_divisors() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`divisors`/`aliquot_sum`, see current line numbers — shift if earlier
tasks this cycle landed first), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `num_divisors` added near
`divisors`/`aliquot_sum`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
