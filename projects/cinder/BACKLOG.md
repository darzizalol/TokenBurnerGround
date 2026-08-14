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

## 1. Standard library: `aliquot_sum` — sum of an integer's proper divisors [claimed 2026-08-14T14:22:36Z]

Build: a fresh breadth task alongside task 1 (`is_perfect_cube`), both
following last cycle's depth work (map-destructuring key rename, landed
via PR #239), added this grooming pass to keep the backlog stocked
ahead of tonight's pace. Add `aliquot_sum(n)` to `cinder/builtins.py`,
registered right after `divisors` (search for `def _divisors`) — the
number-returning sibling of `divisors`'s list-returning trial-division
walk, and the value-returning counterpart to the
`is_perfect_number`/`is_abundant`/`is_deficient` cluster, all four of
which already trial-divide to `sqrt(n)` and differ only in what they do
with the divisors found (sum-and-compare for the three predicates,
collect-and-sort for `divisors`, sum-and-return here). The proper
divisors of `n` are every positive divisor of `n` except `n` itself
(e.g. `6`'s proper divisors are `1, 2, 3`, summing to `6`; `n` is
perfect/abundant/deficient exactly when `aliquot_sum(n)` is equal
to/greater than/less than `n`, so this builtin makes that comparison
inspectable instead of only answerable as a boolean):

```python
def _aliquot_sum(arguments: list, line: int, column: int) -> object:
    _require_arity("aliquot_sum", arguments, 1, line, column)
    value = _require_int("aliquot_sum", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "aliquot_sum() requires a positive integer, domain error", line, column
        )
    if value == 1:
        return 0
    total = 1
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            total += divisor
            complement = value // divisor
            if complement != divisor:
                total += complement
    return total
```

Model the arity/type-checking and the domain-error-on-`n < 1` split
exactly on `divisors`'s own structure (search for `def _divisors`) —
not the predicate cluster's "answer `false` on out-of-domain input"
convention, since there is no sensible "aliquot sum of a non-positive
number" answer, matching `divisors`'s own reasoning for the same choice.
Note the loop starts `total` at `1` (since `1` always divides `value`
for `value > 1`) and special-cases `value == 1` to return `0` directly
(the loop's `range(2, math.isqrt(1) + 1)` is empty and `1`'s only
positive divisor is itself, which is excluded — a proper divisor sum of
`0`, not `1`), mirroring `is_perfect_number`/`is_abundant`/
`is_deficient`'s own `total = 1 if value > 1 else 0` guard against
double-counting `1` as its own proper divisor.

Acceptance criteria:
- `aliquot_sum(6);` is `6` — `1 + 2 + 3 = 6`, confirming `6` is perfect
  (matches `is_perfect_number(6)` being `true`).
- `aliquot_sum(12);` is `16` — `1 + 2 + 3 + 4 + 6 = 16`, confirming `12`
  is abundant (matches `is_abundant(12)` being `true`).
- `aliquot_sum(8);` is `7` — `1 + 2 + 4 = 7`, confirming `8` is
  deficient (matches `is_deficient(8)` being `true`).
- `aliquot_sum(1);` is `0` — `1` has no proper divisors other than
  itself, which is excluded.
- `aliquot_sum(2);` is `1` — every prime's proper-divisor sum is `1`.
- `aliquot_sum(28);` is `28` — `1 + 2 + 4 + 7 + 14 = 28`, the next
  perfect number after `6`.
- `aliquot_sum(0);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires a positive integer, domain error"` — same
  message shape `divisors()` already produces for the same input.
- `aliquot_sum(-6);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires a positive integer, domain error"`.
- `aliquot_sum(5.0);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `aliquot_sum(true);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`divisors`/`is_perfect_number`/`is_abundant`/`is_deficient`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `aliquot_sum` added near `divisors`/`is_perfect_number`/
`is_abundant`/`is_deficient`, and `PROJECT.md`'s roadmap paragraph needs
it moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 2. Language: keyword arguments in function calls (`f(a: 1, b: 2)`)

Build: the depth task after tasks 1 and 2 stacked two breadth tasks
(`is_perfect_cube`, `aliquot_sum`) back to back, per `PROJECT.md`'s
breadth-vs-depth policy. Every function call today binds arguments to
parameters purely positionally — `fn greet(name, greeting = "hi") {
...}` can only be called `greet("Ada")`/`greet("Ada", "yo")`, never
`greet(greeting: "yo", name: "Ada")`. This adds trailing keyword
arguments, matched by parameter name, mirroring Python's own
positional-then-keyword calling convention. Verify the gap:
`python3 -m cinder.cli eval 'fn f(a, b) { return a - b; } print(f(b: 1, a: 5));'`
currently raises `ParseError` `"')' after arguments"` (the parser sees
`IDENTIFIER COLON` where it only expects an expression).

Scope is deliberately narrow: keyword arguments work only for
user-defined Cinder functions (`fn` declarations, anonymous `fn`
expressions, and arrow functions — anything that becomes a
`CinderFunction`), **not** for builtins (`map`, `filter`, `abs`, etc.),
which stay purely positional with their existing hand-rolled arity
checks. Calling a builtin with a keyword argument raises a clean
`CinderRuntimeError` rather than silently mis-binding. A keyword
argument can only target a plain named parameter — not a
list/map-destructuring parameter (`fn f({a, b}) { ... }`, which has no
single name to address) and not the trailing rest parameter (`fn f(a,
...rest) { ... }`, likewise nameless from the caller's perspective) —
both already fall out naturally as "no such keyword" errors below,
needing no special-casing.

**Lexing/parsing** (`cinder/parser.py`): the only new grammar is
`IDENTIFIER COLON expr` in call-argument position, unambiguous with one
token of lookahead — `_call_argument` (search for `def _call_argument`)
never otherwise sees `IDENTIFIER` immediately followed by `COLON` (a
ternary's `:` is preceded by `?`; slice colons only appear inside `[...]`
indexing, a different grammar position entirely). Add a new AST node
right above `Call` in `cinder/ast_nodes.py` (same file/region as
`Spread`, which this mirrors — neither joins the `Expr` Union since both
are only valid inside an argument/element list, never as a standalone
expression):

```python
@dataclass(frozen=True)
class KeywordArg:
    """A `name: expr` argument inside a call's argument list; `Call.arguments`/
    `OptionalCall.arguments` mix these with plain `Expr`s and `Spread`s."""

    name: str
    value: "Expr"
    line: int
    column: int
```

Import it in `cinder/parser.py` next to the existing `Spread` import.
Change `_call_argument` to:

```python
def _call_argument(self) -> Expr:
    if self._check(TokenType.DOT_DOT_DOT):
        dots = self._advance()
        return Spread(self._ternary(), dots.line, dots.column)
    if (
        self._check(TokenType.IDENTIFIER)
        and self._peek_next().type == TokenType.COLON
    ):
        name_token = self._advance()
        self._advance()  # consume ':'
        return KeywordArg(
            name_token.lexeme, self._ternary(), name_token.line, name_token.column
        )
    return self._ternary()
```

(`_peek_next` already exists — search for `def _peek_next`, and see its
use at the `_statement` labeled-loop lookahead for the same
one-token-ahead technique.) Then, in **both** `_finish_call` and
`_finish_optional_call` (search for both names — they build `arguments`
with near-identical `append`-then-`while COMMA` loops), enforce that once
a keyword argument has appeared, every later argument in that call must
also be one — mirror this shape into each loop:

```python
        arguments = []
        seen_keyword = False
        if not self._check(TokenType.RPAREN):
            arguments.append(self._call_argument())
            seen_keyword = isinstance(arguments[-1], KeywordArg)
            while self._check(TokenType.COMMA):
                self._advance()
                argument = self._call_argument()
                if seen_keyword and not isinstance(argument, KeywordArg):
                    raise ParseError(
                        "positional argument follows keyword argument",
                        paren.line,
                        paren.column,
                    )
                seen_keyword = seen_keyword or isinstance(argument, KeywordArg)
                arguments.append(argument)
```

(`_finish_optional_call` computes `paren` one line later than
`_finish_call` does — keep using whichever local already holds the `(`
token in that function, no need to introduce a new one.) A spread
argument (`...xs`) is allowed before keyword arguments in the same call
(it only ever fills positional slots) — this rule only forbids a plain
*positional* or *spread* argument coming **after** a keyword one.

**Evaluation** (`cinder/interpreter.py`): `_evaluate_call_arguments`
(search for `def _evaluate_call_arguments`) currently returns a flat
`list` of evaluated positional values. Change it to return
`tuple[list, dict]` — positional values plus a `name -> value` keyword
map:

```python
def _evaluate_call_arguments(self, arguments: list, env: Environment) -> "tuple[list, dict]":
    positional = []
    keywords: dict = {}
    for arg in arguments:
        if isinstance(arg, KeywordArg):
            if arg.name in keywords:
                raise CinderRuntimeError(
                    f"duplicate keyword argument {arg.name!r} in call",
                    arg.line,
                    arg.column,
                )
            keywords[arg.name] = self.evaluate(arg.value, env)
        elif isinstance(arg, Spread):
            value = self.evaluate(arg.expression, env)
            if not isinstance(value, list):
                raise CinderRuntimeError(
                    f"cannot spread {type_name(value)} in a function call",
                    arg.line,
                    arg.column,
                )
            positional.extend(value)
        else:
            positional.append(self.evaluate(arg, env))
    return positional, keywords
```

Update its two callers, `_evaluate_call`/`_evaluate_optional_call`
(search for both — same file, right below), to unpack the tuple and pass
both through to `call_value`:

```python
def _evaluate_call(self, expr: Call, env: Environment) -> object:
    callee = self.evaluate(expr.callee, env)
    arguments, keywords = self._evaluate_call_arguments(expr.arguments, env)
    return call_value(callee, arguments, expr.line, expr.column, keywords)
```

(same edit shape for `_evaluate_optional_call`, right after its existing
`if callee is None: return None` short-circuit). No other caller of
`_evaluate_call_arguments` exists. Every *other* caller of `call_value`
in the codebase (`map`/`filter`/`reduce`/every other builtin that
invokes a callback) already builds a plain positional Python list by
hand and never touches `KeywordArg` — those call sites are unaffected
and need no changes, since `call_value`'s new `keywords` parameter
defaults to `None`.

**Binding** (`cinder/interpreter.py`, `call_value` — search for `def
call_value`, the shared function-invocation entry point): add a
`keywords: "dict | None" = None` parameter. Reject keywords outright for
builtins (they stay positional-only):

```python
def call_value(
    callee: object, arguments: list, line: int, column: int, keywords: "dict | None" = None
) -> object:
    if isinstance(callee, Builtin):
        if keywords:
            raise CinderRuntimeError(
                f"{callee.name}() does not accept keyword arguments", line, column
            )
        return callee.call(arguments, line, column)
    if not isinstance(callee, CinderFunction):
        raise CinderRuntimeError(f"{type_name(callee)} is not callable", line, column)
    keywords = keywords or {}
```

Leave the existing `min_arity`/`max_arity` arity-error block (the
`if len(arguments) < min_arity or ...` check right after) **completely
untouched** when `keywords` is empty — that is the overwhelming common
case and its exact error-message text (`"expects at least/at most/{n}
argument(s), got {m}"`) is already covered by existing tests; don't
risk it. Instead, wrap that whole existing block in `if not keywords:`
and add a new `else:` branch alongside it for the keyword-argument path:

```python
    min_arity = callee.arity
    max_arity = None if callee.decl.rest_param else len(callee.decl.params)
    if not keywords:
        if len(arguments) < min_arity or (max_arity is not None and len(arguments) > max_arity):
            # ... existing message-building/raise, unchanged ...
    else:
        if max_arity is not None and len(arguments) > max_arity:
            raise CinderRuntimeError(
                f"{callee.name}() expects at most {max_arity} argument(s), got {len(arguments)}",
                line,
                column,
            )
        named_params = {p.name for p in callee.decl.params if p.name is not None}
        unexpected = sorted(set(keywords) - named_params)
        if unexpected:
            raise CinderRuntimeError(
                f"{callee.name}() got an unexpected keyword argument {unexpected[0]!r}",
                line,
                column,
            )
        missing = []
        for index, param in enumerate(callee.decl.params):
            if index < len(arguments):
                if param.name is not None and param.name in keywords:
                    raise CinderRuntimeError(
                        f"{callee.name}() got multiple values for parameter {param.name!r}",
                        line,
                        column,
                    )
                continue
            if param.default is not None:
                continue
            if param.name is not None and param.name in keywords:
                continue
            missing.append(param.name if param.name is not None else "<pattern>")
        if missing:
            names = ", ".join(repr(name) for name in missing)
            raise CinderRuntimeError(
                f"{callee.name}() missing required argument(s): {names}",
                line,
                column,
            )
```

Finally, in the parameter-binding loop right below (the `for index,
param in enumerate(callee.decl.params):` loop that currently does `value
= arguments[index] if index < len(arguments) else
Interpreter().evaluate(param.default, call_env)`), insert one new branch
so a keyword-supplied value is used when there's no positional value at
that index:

```python
        for index, param in enumerate(callee.decl.params):
            if index < len(arguments):
                value = arguments[index]
            elif param.name is not None and param.name in keywords:
                value = keywords[param.name]
            else:
                value = Interpreter().evaluate(param.default, call_env)
            ...  # rest of the loop body (destructure-bind or call_env.define) unchanged
```

This one `elif` is the only change to that loop, and it's a no-op
(never taken) whenever `keywords` is empty — so it changes nothing about
purely-positional calls, keyword-argument-free or not. Nothing else in
`call_value` (the `rest_param` handling, the `try`/`_ReturnSignal`/
`CinderRuntimeError` frame-append machinery) needs to change.

Acceptance criteria:
- `fn greet(name, greeting = "hi") { return greeting + ", " + name; }
  print(greet(name: "Ada", greeting: "yo"));` prints `yo, Ada`.
- `fn f(a, b) { return a - b; } print(f(b: 1, a: 5));` prints `4` — all
  arguments by keyword, order-independent, matching declaration-order
  binding rather than call-site order.
- `fn f(a, b) { return a - b; } print(f(5, b: 1));` prints `4` — mixing
  leading positional with trailing keyword.
- `fn f(a, b = 10) { return a + b; } print(f(a: 3));` prints `13` — a
  keyword-omitted trailing parameter still falls back to its default.
- `fn f(a, b) { return a; } f(1, a: 2);` raises `CinderRuntimeError`
  matching `"f() got multiple values for parameter 'a'"` — `a` supplied
  both positionally (index 0) and by keyword.
- `fn f(a) { return a; } f(a: 1, z: 2);` raises `CinderRuntimeError`
  matching `"f() got an unexpected keyword argument 'z'"`.
- `fn f(a, b) { return a; } f(a: 1);` raises `CinderRuntimeError`
  matching `"f() missing required argument(s): 'b'"`.
- `fn f(a: 1);` (i.e. `1: 2` — a positional argument after a keyword
  one) raises `ParseError` matching `"positional argument follows
  keyword argument"` — for example
  `fn f(a, b) { return a; } f(a: 1, 2);`.
- `map([1, 2, 3], x => x * 2);` and every other existing builtin-call
  test continue to pass unmodified — builtins never see a non-empty
  `keywords` dict from ordinary Cinder source, and internal
  `call_value(fn, [item], line, column)` call sites (no `keywords`
  argument at all) are unaffected by this change.
- `abs(x: -5);` raises `CinderRuntimeError` matching `"abs() does not
  accept keyword arguments"` — builtins reject keyword arguments
  outright rather than silently ignoring or mis-binding them.
- `fn f({a, b}) { return a; } f(a: 1);` raises `CinderRuntimeError`
  matching `"f() got an unexpected keyword argument 'a'"` — a
  destructuring parameter has no addressable name, so any keyword
  targeting it (even one that happens to share a key name inside the
  pattern) is simply unrecognized, not specially rejected.
- `fn f(a, ...rest) { return a; } f(a: 1, rest: 2);` raises
  `CinderRuntimeError` matching `"f() got an unexpected keyword
  argument 'rest'"` — the rest parameter is likewise not
  keyword-addressable.
- Every existing purely-positional call (no keyword arguments anywhere
  in the call) behaves identically to before this task, including the
  exact wording of every pre-existing arity-error message — this is
  purely additive syntax.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `KeywordArg`), `cinder/parser.py`
(`_call_argument`, `_finish_call`, `_finish_optional_call`, the `Spread`
import), `cinder/interpreter.py` (`_evaluate_call_arguments`,
`_evaluate_call`, `_evaluate_optional_call`, `call_value`),
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged,
`README.md`'s Functions bullet needs a keyword-argument mention, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_pronic` — oblong-number predicate

Build: the breadth task after task 3's depth work (keyword arguments in
function calls) per `PROJECT.md`'s breadth-vs-depth policy. Add
`is_pronic(n)` to `cinder/builtins.py`, registered right after
`is_perfect_cube` (search for `def _is_perfect_cube`, the current last
entry in the integer-property cluster once task 1 (`is_perfect_cube`)
lands — this task only depends on task 1, not task 3). A pronic (or
oblong, or heteromecic) number is an integer expressible as `k * (k +
1)` for some non-negative integer `k` — e.g. `6 = 2 * 3`, `12 = 3 * 4`,
`20 = 4 * 5` — one more root/product-based classification alongside
`is_perfect_square`/`is_perfect_cube` in that same cluster. Compute it
the same exact-integer way `is_perfect_square` does (`math.isqrt`, no
floating-point square root): for non-negative `n`, `k =
math.isqrt(n)` always lands on the unique integer with `k * k <= n <
(k + 1) * (k + 1)`, so `n` is pronic exactly when `k * (k + 1) == n`
(no need to also check `k - 1`, since pronic numbers are never
adjacent to another pronic number closely enough for `isqrt` to
land one short — verified by the acceptance criteria below).

```python
def _is_pronic(arguments: list, line: int, column: int) -> object:
    _require_arity("is_pronic", arguments, 1, line, column)
    value = _require_int("is_pronic", arguments[0], line, column)
    if value < 0:
        return False
    root = math.isqrt(value)
    return root * (root + 1) == value
```

Model the arity/type-checking exactly on `is_perfect_square`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). The
`value < 0` guard answers `false` on negative input rather than raising
a domain error, matching `is_perfect_square`/`is_leap_year`'s own
convention (no pronic number is ever negative, since `k * (k + 1) >= 0`
for every `k >= 0`).

Acceptance criteria:
- `is_pronic(0);` is `true` — `0 * 1 == 0`.
- `is_pronic(2);` is `true` — `1 * 2 == 2`.
- `is_pronic(6);` is `true` — `2 * 3 == 6`.
- `is_pronic(12);` is `true` — `3 * 4 == 12`.
- `is_pronic(20);` is `true` — `4 * 5 == 20`.
- `is_pronic(30);` is `true` — `5 * 6 == 30`.
- `is_pronic(1);` is `false` — no integer `k` satisfies `k * (k + 1) ==
  1`.
- `is_pronic(5);` is `false`.
- `is_pronic(9);` is `false` — a perfect square that is not also
  pronic (no integer is ever both, except neither `0` nor any other
  value coincides for this pair).
- `is_pronic(-6);` is `false` — negative input answers `false` without
  raising.
- `is_pronic(5.0);` raises `CinderRuntimeError` matching
  `"is_pronic() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `is_pronic(true);` raises `CinderRuntimeError` matching
  `"is_pronic() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_perfect_square`/`is_perfect_cube`, see current line numbers — shift
if earlier tasks this cycle landed first), `tests/test_builtins.py`.
Once merged, `README.md`'s Builtins bullet needs `is_pronic` added near
`is_perfect_square`/`is_perfect_cube`, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Language: default values in list-destructuring patterns (`let [a, b = 5] = expr;`)

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

## 5. Standard library: `collatz_length` — steps to reach 1 under the Collatz recurrence

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

## 6. Standard library: `is_strong_number` — sum of digit factorials equals the number

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
