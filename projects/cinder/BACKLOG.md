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

## 1. Language: named function expressions (`fn name(params) { ... }`) for self-referencing anonymous functions [claimed 2026-08-19T19:57:54Z]

Build: the depth task after task 5's breadth work (`is_achilles`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that raw string literals have landed via PR #275, dropping the
count to the 5-task floor. `fn(params) { ... }` at expression position is
always anonymous today — a function that wants to call itself recursively
has no name of its own to call, and must instead close over whatever
outer variable it happens to be assigned to (`let f = fn(n) { return n
<= 1 ? 1 : n * f(n - 1); };` — this already works, since the call happens
after the `let` completes, but it breaks the moment the function is
passed straight into a call argument or reassigned to a second variable,
since there is no outer binding to fall back on other than the original
one). Verify the gap:
```sh
python3 -m cinder.cli eval 'let x = fn foo() { return 1; }; print(x());'
# -> ParseError: expected '(' after 'fn', found 'foo'
```
An identifier immediately after `fn` at expression position is already a
guaranteed `ParseError` today (`_fn_expression` unconditionally consumes
`(` next), so no currently-valid program's meaning changes by making that
adjacency mean something new. This is scoped to plain `fn` expressions
only, not arrow functions — arrow syntax has no natural place to put a
name between `=>` and its parameter list, and `fact => fact + 1` already
means something else entirely (an ordinary single-identifier arrow
parameter named `fact`), so arrow functions stay anonymous. Statement
position (`fn foo() { ... }`, parsed by the separate `_fn_declaration` →
`FnDecl` path, which already requires and has always required a name) is
untouched — the dispatcher in `_statement` sends `fn` there before
`_primary`'s `_fn_expression` branch is ever reached, so there is no
ambiguity between the two.

**AST** (`cinder/ast_nodes.py`): add an optional `name` field to `FnExpr`,
appended last (after `column`) so every existing positional
`FnExpr(params, rest_param, body, line, column)` call site keeps working
unchanged, defaulting the new function's own name to `None`:
```python
@dataclass(frozen=True)
class FnExpr:
    params: list
    rest_param: "str | None"
    body: "Block"
    line: int
    column: int
    name: "str | None" = None
```

**Parsing** (`cinder/parser.py`): `_fn_expression` optionally consumes an
`IDENTIFIER` right after the `fn` keyword, before the parameter list:
```python
    def _fn_expression(self) -> Expr:
        fn_token = self._advance()
        name = None
        if self._check(TokenType.IDENTIFIER):
            name = self._advance().lexeme
        params, rest_param, body = self._fn_params_and_body()
        return FnExpr(params, rest_param, body, fn_token.line, fn_token.column, name)
```

**Interpreter** (`cinder/interpreter.py`): the self-reference must be
visible *only* inside calls to that specific function value — never
leaking into the enclosing scope, and not tied to whatever outer variable
(if any) the function is assigned to. `call_value`'s `call_env` is
already a fresh child `Environment` created per call
(`call_env = Environment(callee.closure)`, right before the parameter-
binding loop) — bind the name there, before parameters are bound, so a
same-named parameter shadows it within its own call the same way any
inner `let` would shadow an outer name:
```python
    call_env = Environment(callee.closure)
    if isinstance(callee.decl, FnExpr) and callee.decl.name is not None:
        call_env.define(callee.decl.name, callee)
    try:
        for index, param in enumerate(callee.decl.params):
```
`FnExpr` is already imported at the top of `cinder/interpreter.py`, no
new import needed.

**Required fix, not optional — read before writing tests**:
`CinderFunction.name` (`cinder/interpreter.py`, just above `call_value`)
currently reads:
```python
    @property
    def name(self) -> str:
        return getattr(self.decl, "name", "<anonymous>")
```
This works today only because plain `FnExpr` has *no* `name` attribute at
all, so `getattr`'s missing-attribute fallback kicks in. Once `FnExpr`
unconditionally carries a `name` field (defaulting to `None`, not
missing), `getattr` always finds the attribute — for an anonymous
function it would now return `None` instead of falling back to
`"<anonymous>"`, silently breaking every arity/keyword-argument error
message and call-stack frame for anonymous functions (e.g. `"None()
expects 1 argument(s), got 0"`). Fix the property to treat a `None` name
the same as a missing one:
```python
    @property
    def name(self) -> str:
        return getattr(self.decl, "name", None) or "<anonymous>"
```
(Safe for `FnDecl` too — its `name` is always a non-empty identifier
string, which is truthy.)

**Tests** (`tests/test_parser.py`): `shape()`'s `FnExpr` branch
(search `if isinstance(node, FnExpr):`) currently returns a 4-tuple —
extend it to a 5-tuple with the name appended last:
```python
    if isinstance(node, FnExpr):
        return ("FnExpr", params_shape(node.params), node.rest_param, stmt_shape(node.body), node.name)
```
Every existing `"FnExpr"` shape assertion in this file (25 occurrences —
confirm the current count with `grep -c '"FnExpr"' tests/test_parser.py`
before starting, in case another task landed one first this cycle) is a
4-tuple with no name; each needs a trailing `None` appended (they're all
genuinely anonymous fixtures, including every arrow-function test, since
arrows always desugar to a nameless `FnExpr`). Do this as a mechanical
pass — `grep -n '"FnExpr"' tests/test_parser.py` to enumerate every site,
then add `None` as the tuple's new last element at each one — rather than
trying to special-case which ones "don't need it"; none of them do,
since none exercise the new named form.

Acceptance criteria:
- `let f = fn fact(n) { return n <= 1 ? 1 : n * fact(n - 1); };
  print(f(5));` prints `120` — self-reference by the function's own name,
  with no dependence on the outer `let` binding.
- `let g = fn fact(n) { return n <= 1 ? 1 : n * fact(n - 1); }; let h =
  g; g = nil; print(h(5));` prints `120` — the self-reference resolves
  through the function's own private per-call binding, not through
  whatever outer variable it happens to be assigned to; reassigning (or
  nil-ing) the original outer variable does not break `h`'s recursion.
- `print(map([1, 2, 3], fn double(x) { return x * 2; }));` prints
  `[2, 4, 6]` — the named form works directly as a call argument, with no
  `let` needed at all.
- `let f = fn f(f) { return f + 1; }; print(f(10));` prints `11` — a
  same-named parameter shadows the function's own self-binding within
  that call, since parameters are bound after the self-reference in the
  same call environment.
- `fn standalone() { return 1; }` at statement position is unaffected —
  still parses as an ordinary `FnDecl` via `_fn_declaration`, never
  reaching `_fn_expression` at all.
- `let f = fn fact(n) { return n; }; f();` raises `CinderRuntimeError`
  matching `"fact() expects 1 argument(s), got 0"` — arity errors use the
  given name.
- `let f = fn(n) { return n; }; f();` still raises `CinderRuntimeError`
  matching `"<anonymous>() expects 1 argument(s), got 0"` — confirms the
  `CinderFunction.name` fallback still works for genuinely anonymous
  functions now that `FnExpr` always carries a `name` field.
- `(n) => n + 1` and `n => n + 1` are both unaffected — arrow functions
  still desugar to a nameless `FnExpr`, and there is no syntax for naming
  one (a bare identifier before `=>` already means an ordinary
  single-parameter arrow, not a function name).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`FnExpr`), `cinder/parser.py`
(`_fn_expression`), `cinder/interpreter.py` (`CinderFunction.name`,
`call_value`), `tests/test_parser.py` (`shape()`'s `FnExpr` branch plus
every existing `"FnExpr"` shape assertion, search `class
TestFunctionExpressions` or similar for where to add new cases),
`tests/test_interpreter.py` (model on `class` containing
`test_anonymous_function_bound_with_let`/
`test_anonymous_function_called_immediately`, search either name, for
end-to-end `eval` cases covering recursion, shadowing, and the error
message regression). Once merged, `README.md`'s Functions bullet needs a
mention of the named form near the existing anonymous-`fn`-expression
description, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to landed
— leave all three to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_pernicious` — a number whose binary popcount is itself prime

Build: the breadth task after task 5's depth work (named function
expressions) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `is_undulating` has landed via PR #276,
dropping the count to the 5-task floor. `is_evil`/`is_odious`
(`cinder/builtins.py`) already test the *parity* of an integer's binary
popcount (count of `1` bits) — even for `is_evil`, odd for `is_odious`.
Nothing yet asks a different, equally natural question of the same
popcount: whether it is itself a *prime* number. `7` is `111` in binary
(popcount `3`, prime, so pernicious); `8` is `1000` (popcount `1`, not
prime, so not pernicious). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_pernicious(7));'
# -> CinderRuntimeError: undefined name 'is_pernicious'
```

Add to `cinder/builtins.py`, registered right after `_is_odious` (search
`def _is_odious`, immediately before `_is_palindrome_list`):
```python
def _is_pernicious(arguments: list, line: int, column: int) -> object:
    _require_arity("is_pernicious", arguments, 1, line, column)
    value = _require_int("is_pernicious", arguments[0], line, column)
    if value < 0:
        raise CinderRuntimeError(
            "is_pernicious() requires a non-negative integer, domain error",
            line,
            column,
        )
    popcount = bin(value).count("1")
    if popcount < 2:
        return False
    for divisor in range(2, int(popcount ** 0.5) + 1):
        if popcount % divisor == 0:
            return False
    return True
```
The `divisor` loop is `_is_prime`'s own trial-division shape (search
`def _is_prime`), applied to `popcount` instead of `value` directly —
reuse the shape, not the function itself, since `_is_prime` takes the
dispatcher's `(arguments, line, column)` signature and would need
re-wrapping `popcount` into a fake arguments list for no benefit over
just inlining the four-line loop. Negative input raises a domain error
(`value < 0`) rather than returning `false`, matching `is_evil`/
`is_odious`'s own convention right above it — not the "return false on
out-of-domain input" convention most other digit/bit predicates in this
file use — since a popcount is only meaningful for a non-negative
integer, the same reasoning `is_evil`/`is_odious` already applied.

Acceptance criteria:
- `is_pernicious(3);` is `true` — `11`, popcount `2` (prime).
- `is_pernicious(5);` is `true` — `101`, popcount `2`.
- `is_pernicious(6);` is `true` — `110`, popcount `2`.
- `is_pernicious(7);` is `true` — `111`, popcount `3` (prime).
- `is_pernicious(9);` is `true` — `1001`, popcount `2`.
- `is_pernicious(0);` is `false` — popcount `0`, not prime.
- `is_pernicious(1);` is `false` — `1`, popcount `1`, not prime (`1` is
  never prime).
- `is_pernicious(2);` is `false` — `10`, popcount `1`.
- `is_pernicious(8);` is `false` — `1000`, popcount `1`.
- `is_pernicious(15);` is `false` — `1111`, popcount `4` (not prime).
- `is_pernicious(-3);` raises `CinderRuntimeError` matching
  `"is_pernicious() requires a non-negative integer, domain error"`.
- `is_pernicious(5.0);` raises `CinderRuntimeError` matching
  `"is_pernicious() requires an int, got float"`.
- `is_pernicious(true);` raises `CinderRuntimeError` matching
  `"is_pernicious() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_odious`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsEvil` and `class
TestIsOdious`, search either name). Once merged, `README.md`'s Builtins
bullet needs `is_pernicious` added near `is_evil`/`is_odious`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave all three to
the Architect's next grooming pass, not this task.

---

## 3. Language: inclusive range literal `a..=b` as sugar for `range(a, b + 1)`

Build: the depth task after task 5's breadth work (`is_pernicious`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that the exclusive range literal `a..b` has landed via PR
#277, dropping the count to the 5-task floor. `a..b` (`RangeExpr`,
`cinder/parser.py`/`cinder/interpreter.py`) already desugars to
`range(a, b)` — exclusive of `b`, matching the two-argument `range()`
builtin it sits on top of — but there is no inclusive spelling: writing
a loop that must include its upper bound (`for i in 1..=5 { ... }` to
print `1` through `5`) forces either `1..6` (off-by-one, easy to get
wrong at the call site) or the more verbose `range(1, 6)`. Verify the
gap:
```sh
python3 -m cinder.cli eval 'for i in 1..=5 { print(i); }'
# -> ParseError: <eval>:1:13: expected an expression, found '='
```
This is a guaranteed `ParseError` today (`DOT_DOT` immediately followed
by `=` — the lexer emits a bare `DOT_DOT` token and the parser's
`_range_expr` then tries to parse an expression starting with `=`, which
fails), so no currently-valid Cinder program's meaning changes.

**Lexing** (`cinder/lexer.py`): `_dot` already special-cases two
successive `.` characters (as opposed to one or three) into a
`DOT_DOT` token — extend that branch to check for a trailing `=`
first, the same way `_lt`'s own `<<`-vs-`<<=` branch already checks for
a trailing `=` after recognizing `<<`:
```python
    def _dot(self, start_line: int, start_col: int):
        if self._peek() == "." and self._peek_next() == ".":
            self._advance()
            self._advance()
            self.tokens.append(
                Token(TokenType.DOT_DOT_DOT, "...", None, start_line, start_col)
            )
        elif self._peek() == ".":
            self._advance()
            if self._match("="):
                self.tokens.append(
                    Token(TokenType.DOT_DOT_EQ, "..=", None, start_line, start_col)
                )
            else:
                self.tokens.append(
                    Token(TokenType.DOT_DOT, "..", None, start_line, start_col)
                )
        else:
            self.tokens.append(Token(TokenType.DOT, ".", None, start_line, start_col))
```
`_match` is already the shared one-character-lookahead-and-consume
helper every other compound-operator branch in this file uses (see
`_lt`/`_bang`/`_question`). Add `DOT_DOT_EQ = auto()` to
`cinder/tokens.py`'s `TokenType` enum, next to the existing `DOT_DOT`/
`DOT_DOT_DOT` pair.

**AST** (`cinder/ast_nodes.py`): add an optional `inclusive` field to
`RangeExpr`, appended last (after `column`) so every existing positional
`RangeExpr(start, end, line, column)` call site keeps working unchanged,
defaulting to exclusive — the same technique task 4's `FnExpr.name`
field used:
```python
@dataclass(frozen=True)
class RangeExpr:
    start: "Expr"
    end: "Expr"
    line: int
    column: int
    inclusive: bool = False
```

**Parsing** (`cinder/parser.py`): `_range_expr` accepts either token,
recording which one matched:
```python
    def _range_expr(self) -> Expr:
        expr = self._bitor()
        if self._check(TokenType.DOT_DOT) or self._check(TokenType.DOT_DOT_EQ):
            dots = self._advance()
            end = self._bitor()
            inclusive = dots.type is TokenType.DOT_DOT_EQ
            return RangeExpr(expr, end, dots.line, dots.column, inclusive)
        return expr
```

**Interpreter** (`cinder/interpreter.py`): `_evaluate_range` bumps the
end bound by one before delegating to the existing `_range` builtin,
but only when it is safe to do so — an invalid end value (wrong type,
or a `bool`, which `isinstance(x, int)` would otherwise wrongly accept)
must still reach `_range`'s own validation unchanged, so its error
message stays identical regardless of which spelling was used:
```python
    def _evaluate_range(self, expr: RangeExpr, env: Environment) -> object:
        start = self.evaluate(expr.start, env)
        end = self.evaluate(expr.end, env)
        if expr.inclusive and isinstance(end, int) and not isinstance(end, bool):
            end = end + 1
        from cinder.builtins import _range  # local: see note above this method
        return _range([start, end], expr.line, expr.column)
```
No changes needed to `_range` itself — reusing its existing validation
and list construction is what keeps both spellings sharing one error
message, the same reuse `range()`/`a..b` already established for each
other.

**Tests** (`tests/test_parser.py`): `shape()`'s `RangeExpr` branch
(search `if isinstance(node, RangeExpr):`) currently returns a 2-tuple —
extend it to a 3-tuple with `inclusive` appended last:
```python
    if isinstance(node, RangeExpr):
        return ("RangeExpr", shape(node.start), shape(node.end), node.inclusive)
```
All 4 existing `"RangeExpr"` shape assertions in `class
TestListsAndMaps` (search `def test_range_literal`,
`test_range_binds_looser_than_arithmetic`,
`test_range_binds_tighter_than_membership`) need a trailing `False`
appended — they all exercise the exclusive `..` spelling.

Acceptance criteria:
- `let out = []; for i in 1..=5 { out = out + [i]; } print(out);`
  prints `[1, 2, 3, 4, 5]` — inclusive of the upper bound.
- `let out = []; for i in 1..5 { out = out + [i]; } print(out);` still
  prints `[1, 2, 3, 4]` — the existing exclusive spelling is unaffected.
- `print(5..=5);` prints `[5]` — a single-element inclusive range when
  both bounds are equal (`5..5` stays `[]`, unaffected).
- `print(5..=1);` prints `[]` — descending bounds produce an empty list,
  same as `a..b` already does, since `range(5, 2)` is empty.
- `print(1..=3 in [1, 2, 3]);` raises the ordinary `"list is not
  comparable"`-style membership error unaffected by this task — instead
  confirm `3 in 1..=5` evaluates the range first then tests membership,
  printing `true` (mirrors the existing `x in 1..5` precedence test).
- `1..="5";` raises `CinderRuntimeError` matching `"range() requires int
  arguments, got string"` — an invalid end value still reaches `_range`'s
  own validation unchanged, not silently coerced by the `+ 1` bump.
- `true..=5;` raises `CinderRuntimeError` matching `"range() requires
  int arguments, got bool"` — a `bool` start is rejected the same way
  `a..b` already rejects it.
- `1..=5..=10;` raises `ParseError` — ranges still don't chain, matching
  `a..b`'s existing `test_range_does_not_chain` behavior.
- `f(...args)` — an unrelated three-dot spread call — is unaffected by
  the new two-dot-plus-equals lexer branch (`test_dot_dot_dot_unaffected_by_range_grammar`
  stays green).
- Full test suite passes.

Likely files: `cinder/tokens.py` (`DOT_DOT_EQ`), `cinder/lexer.py`
(`_dot`), `cinder/ast_nodes.py` (`RangeExpr`), `cinder/parser.py`
(`_range_expr`), `cinder/interpreter.py` (`_evaluate_range`),
`tests/test_lexer.py` (model on whatever covers `DOT_DOT`/`DOT_DOT_DOT`
tokenization, search `DOT_DOT`), `tests/test_parser.py` (`shape()`'s
`RangeExpr` branch plus its 4 existing assertions, `class
TestListsAndMaps`), `tests/test_interpreter.py` (`class
TestRangeLiteral`, search that name, for end-to-end `eval` cases
covering inclusion, descending bounds, and the type-error passthrough).
Once merged, `README.md`'s range-literal description needs a mention of
the inclusive spelling right next to the existing `a..b` description,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
roadmap paragraph needs this moved from backlog to landed — leave all
three to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `is_sphenic` — a number that is the product of three distinct primes

Build: the breadth task after task 5's depth work (inclusive range literal
`a..=b`) per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog
back to 6 tasks now that `is_kaprekar` has landed via PR #278, dropping the
count to the 5-task floor. `is_semiprime` (`cinder/builtins.py`) already
tests whether an integer is the product of exactly two primes counted with
multiplicity (`4 = 2 * 2`, `6 = 2 * 3`). A sphenic number is the natural next
member of that same "product of primes" family: the product of exactly
three *distinct* primes, each appearing exactly once (`30 = 2 * 3 * 5`,
`42 = 2 * 3 * 7`) — not just any integer with three prime factors counted
with multiplicity, since `12 = 2^2 * 3` and `8 = 2^3` both have three prime
factors by multiplicity but neither is sphenic (both repeat a factor).
Nothing in the existing cluster tests this. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_sphenic(30));'
# -> CinderRuntimeError: undefined name 'is_sphenic'
```

Add to `cinder/builtins.py`, registered right after `_is_semiprime` (search
`def _is_semiprime`, immediately before `_is_emirp`):
```python
def _is_sphenic(arguments: list, line: int, column: int) -> object:
    _require_arity("is_sphenic", arguments, 1, line, column)
    value = _require_int("is_sphenic", arguments[0], line, column)
    if value < 2:
        return False
    remaining = value
    distinct_count = 0
    divisor = 2
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            count = 0
            while remaining % divisor == 0:
                remaining //= divisor
                count += 1
            if count != 1:
                return False
            distinct_count += 1
            if distinct_count > 3:
                return False
        divisor += 1
    if remaining > 1:
        distinct_count += 1
    return distinct_count == 3
```
This is `_is_semiprime`'s own factorization loop shape (peel each prime
factor's full multiplicity in an inner `while`, walking `divisor` up to
`sqrt(remaining)`), generalized from "exactly two prime factors counted
with multiplicity" to "exactly three *distinct* prime factors, each
appearing exactly once". The extra `count != 1: return False` check right
after peeling a factor's full multiplicity is what enforces "each exactly
once" — a squared-or-higher factor like `12 = 2^2 * 3` fails there, which
`is_semiprime`'s coarser total-multiplicity counting doesn't need to check
since it never distinguishes "one factor twice" from "two distinct
factors". `value < 2` returns `false` up front rather than raising, matching
`is_semiprime`'s own convention for non-positive input.

Acceptance criteria:
- `is_sphenic(30);` is `true` — `2 * 3 * 5`.
- `is_sphenic(42);` is `true` — `2 * 3 * 7`.
- `is_sphenic(105);` is `true` — `3 * 5 * 7`.
- `is_sphenic(1001);` is `true` — `7 * 11 * 13`.
- `is_sphenic(8);` is `false` — `2^3`, a single repeated prime.
- `is_sphenic(12);` is `false` — `2^2 * 3`, one factor repeats.
- `is_sphenic(60);` is `false` — `2^2 * 3 * 5`, one factor repeats even
  though three distinct primes divide it.
- `is_sphenic(7);` is `false` — a single prime, not three.
- `is_sphenic(1);` is `false` — below the `n >= 2` floor.
- `is_sphenic(0);` is `false`.
- `is_sphenic(-30);` is `false` — negative input, following
  `is_semiprime`'s existing convention rather than raising.
- `is_sphenic(5.0);` raises `CinderRuntimeError` matching
  `"is_sphenic() requires an int, got float"`.
- `is_sphenic(true);` raises `CinderRuntimeError` matching
  `"is_sphenic() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_semiprime`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py` (model on `class TestIsSemiprime`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_sphenic` added
near `is_semiprime`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to landed —
leave all three to the Architect's next grooming pass, not this task.

---

## 5. Language: triple-quoted string literals `"""..."""`/`'''...'''`

Build: the depth task after task 5's breadth work (`is_sphenic`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that map literal shorthand properties has landed via PR #279,
dropping the count to the 5-task floor. Ordinary strings already tolerate a
literal embedded newline just fine (`Lexer._advance` already tracks
line/column across any character, strings included, so `"a\nb"` written
with a real newline instead of the `\n` escape already lexes and prints
across two lines) — so the gap triple-quoting closes isn't multi-line text,
it's *quote-heavy* text: today embedding the delimiter's own quote
character requires escaping every single occurrence (`"she said \"hi\" to
\"me\""`), which gets noisy fast for content like JSON snippets or
dialogue with a lot of quotes. A triple-quoted string only ends at three
consecutive matching quote characters, so a lone occurrence of the quote
character inside is just ordinary content. Verify the gap:
```sh
python3 -m cinder.cli eval 'print("""she said "hi" to "me" today""");'
# -> ParseError: <eval>:1:9: expected ')' after arguments, found '"she said "'
# (the first unescaped '"' after 'said ' ends the "string" only two
# characters in; the rest re-lexes as bare code)
```

**Lexing only** (`cinder/lexer.py`) — no parser, AST, or interpreter
changes needed, since this reuses the exact `TokenType.STRING`/
`TokenType.INTERP_STRING` tokens ordinary strings already produce; every
downstream consumer of those tokens is unaffected. `tokenize()`'s
dispatch (search `if char == '"' or char == "'":`, right at the top of
the `char` dispatch chain) currently always calls `self._string(...)`
for a lone quote — add a lookahead for two more of the same quote
character first:
```python
            if char == '"' or char == "'":
                if self._peek() == char and self._peek_next() == char:
                    self._advance()
                    self._advance()
                    self._string(start_line, start_col, quote=char, triple=True)
                else:
                    self._string(start_line, start_col, quote=char)
```
This is scoped to the plain-string branch only — the `r"..."`/`r'...'`
raw-string branch right below it (`elif char == "r" and self._peek() in
('"', "'"):`) is untouched, so `r"""..."""` keeps its current (already
slightly odd, pre-existing, out-of-scope-to-fix) behavior of treating the
first `"` as the raw string's own closing quote; adding raw triple-quote
support is a separate future task, not this one.

`_string` (search `def _string`) gains a `triple` parameter and switches
its start-position bookkeeping and its termination check from a single
quote character to a 3-character delimiter, computed once so both cases
share one loop body:
```python
    def _string(self, start_line: int, start_col: int, quote: str, triple: bool = False):
        start_pos = self.pos - (3 if triple else 1)  # position of the opening quote(s)
        delimiter = quote * 3 if triple else quote
        parts: list = []  # str segments and ("expr", raw, line, col) placeholders
        chars = []
        has_interp = False
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string", start_line, start_col, unterminated=True
                )
            if self.source[self.pos : self.pos + len(delimiter)] == delimiter:
                for _ in delimiter:
                    self._advance()
                break
            if self._peek() == "$" and self._peek_next() == "{":
                ...  # unchanged
```
Everything below the two changed lines (the `$`/`${` interpolation branch,
the `\`-escape branch, the plain-character branch, and the final
`parts.append`/`Token` construction) stays exactly as it is today — this
is a two-line change to the loop's start/termination logic, not a
rewrite. `self.source[self.pos : self.pos + len(delimiter)] == delimiter`
naturally covers the single-quote case too (`len(delimiter) == 1`), so
there is no separate `if triple: ... else: ...` branch inside the loop.
Escapes and `${...}` interpolation both continue to work exactly as they
do in ordinary strings, since this is the same loop body — a triple-quoted
string is not a raw string, only a differently-delimited one.

Acceptance criteria:
- `print("""she said "hi" to "me" today""");` prints
  `she said "hi" to "me" today` — embedded double quotes need no
  escaping inside a `"""`-delimited string, so long as no run of three
  appears before the intended close.
- `print('''it's a "quoted" word''');` prints `it's a "quoted" word` —
  a `'''`-delimited string tolerates both an embedded `'` (so long as
  it's not three in a row) and embedded `"` unescaped.
- A literal embedded newline still works the same as it already does for
  ordinary strings: write `print("""line one` then an actual newline in
  the source then `line two""");` — prints two lines (confirms this task
  didn't regress the pre-existing single-quote multi-line behavior).
- Interpolation still works: `let x = 5; print("""value: ${x}!""");`
  prints `value: 5!`.
- Escapes still work: ``print("""a\tb""");`` prints `a`, a tab, `b`.
- `"""unterminated` (no closing triple-quote before EOF) raises
  `LexError` matching `"unterminated string"`.
- `print("""""");` — a triple-quote open (3 quotes) immediately
  followed by a triple-quote close (3 more quotes), 6 total — prints an
  empty string.
- `r"""raw triple""";` — unaffected by this task; still whatever it does
  today (raw-string branch untouched), not a regression to chase down
  here.
- The existing single-quote-delimited string suite (escapes,
  interpolation, unterminated-string errors) is fully unaffected — every
  existing `TestLiterals`/`TestStringInterpolation`/`TestErrors` test in
  `tests/test_lexer.py` stays green with no changes needed to any of
  them.
- Full test suite passes.

Likely files: `cinder/lexer.py` (`tokenize`'s dispatch, `_string`),
`tests/test_lexer.py` (`class TestLiterals`, search `def
test_raw_string_double_quoted_escapes_not_processed` for where the
string-literal tests cluster; add a handful of `test_triple_quoted_*`
cases there), `tests/test_interpreter.py` (one or two end-to-end `eval`
cases confirming `print("""...""")` output, model on whichever class
covers `test_string_basic`-style interpreter tests). Once merged,
`README.md`'s string-literals bullet needs a mention of the triple-quoted
form right next to the existing raw-string description, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s roadmap paragraph
needs this moved from backlog to landed — leave all three to the
Architect's next grooming pass, not this task.

---

## 6. Standard library: `is_circular_prime` — a prime where every digit rotation is also prime

Build: the breadth task after task 5's depth work (triple-quoted string
literals) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `is_achilles` has landed via PR #280,
dropping the count to the 5-task floor. `is_emirp` already combines
primality with a digit transformation (reversal); `is_rotation` already
has the "rotate a sequence and compare" technique, just for two strings
handed in explicitly rather than generated from one number. Nothing yet
combines the two: a circular prime is a prime number where *every*
rotation of its decimal digits is also prime — not just the one reversal
`is_emirp` checks, and not compared against a second value the way
`is_rotation` is, but generated and checked against itself. `197` is
circular (`197`, `971`, `719` all prime); `19` is not (`91 = 7 * 13`).
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_circular_prime(197));'
# -> CinderRuntimeError: undefined name 'is_circular_prime'
```

Add to `cinder/builtins.py`, registered right after `_is_emirp` (search
`def _is_emirp`, immediately before `_is_power_of_two`):
```python
def _is_circular_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("is_circular_prime", arguments, 1, line, column)
    value = _require_int("is_circular_prime", arguments[0], line, column)
    if value < 2:
        return False

    def _trial_division_is_prime(candidate: int) -> bool:
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return False
        return True

    digits = str(value)
    for index in range(len(digits)):
        rotated = int(digits[index:] + digits[:index])
        if not _trial_division_is_prime(rotated):
            return False
    return True
```
The nested `_trial_division_is_prime` is `_is_prime`'s own trial-division
shape (search `def _is_prime`), factored into a local helper here rather
than duplicated once per rotation — the same trial-division loop
`_is_emirp` already duplicates textually for its two checks (original
value and reversal), just called from a loop here since the number of
rotations varies with digit count instead of always being exactly two.
`digits[index:] + digits[:index]` is the same left-rotation slicing
`_is_rotation` conceptually relies on (`string2 in string1 + string1`),
applied directly to produce each rotation rather than testing membership
of one. A leading-zero rotation (e.g. `103` rotating to `"031"`) collapses
correctly via `int(...)` dropping the leading zero — `int("031")` is `31`,
tested for primality on its actual numeric value like any other
rotation, not rejected or specially handled, matching how Cinder has no
separate "numeric string" type to preserve the zero.

Acceptance criteria:
- `is_circular_prime(2);` is `true` — single-digit prime, only rotation
  is itself.
- `is_circular_prime(11);` is `true` — both rotations (`11`, `11`) prime.
- `is_circular_prime(13);` is `true` — `13` and `31` both prime.
- `is_circular_prime(17);` is `true` — `17` and `71` both prime.
- `is_circular_prime(197);` is `true` — `197`, `971`, `719` all prime.
- `is_circular_prime(4);` is `false` — not prime at all.
- `is_circular_prime(19);` is `false` — `91 = 7 * 13`, not prime.
- `is_circular_prime(103);` is `false` — rotation `031` is `31` (prime),
  but rotation `310` is not prime, so still false; confirms leading-zero
  rotations are evaluated numerically rather than skipped.
- `is_circular_prime(0);` is `false` — below the `n >= 2` floor.
- `is_circular_prime(1);` is `false`.
- `is_circular_prime(-13);` is `false` — negative input, following
  `is_emirp`'s existing "return false rather than raise" convention for
  out-of-domain input.
- `is_circular_prime(5.0);` raises `CinderRuntimeError` matching
  `"is_circular_prime() requires an int, got float"`.
- `is_circular_prime(true);` raises `CinderRuntimeError` matching
  `"is_circular_prime() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_emirp`, see current
line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsEmirp`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_circular_prime`
added near `is_emirp`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to landed —
leave all three to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
