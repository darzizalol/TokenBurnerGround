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

## 2. Standard library: `is_achilles` — powerful but not itself a perfect power

Build: the breadth task after task 5's depth work (map literal shorthand
properties) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `is_perfect_power` has landed via PR
#274, dropping the count to the 5-task floor. `is_powerful_number`
(`cinder/builtins.py`) tests whether every prime factor of an integer
appears with exponent `2` or more; `is_perfect_power` tests whether an
integer is `m ** k` for some base `m` and exponent `k >= 2`. Every
perfect power greater than 1 is powerful, but not every powerful number
is a perfect power — `72 = 2^3 * 3^2` is powerful (both exponents `>=
2`) yet no single base/exponent pair produces it (it is not a perfect
square, cube, or any higher power). Numbers in exactly this gap are
called Achilles numbers (OEIS A052486), and nothing in the existing
cluster tests it. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_achilles(72));'
# -> CinderRuntimeError: undefined name 'is_achilles'
```

Add to `cinder/builtins.py`, registered right after `_is_powerful_number`
(search `def _is_powerful_number`, immediately before `_integer_kth_root`):
```python
def _is_achilles(arguments: list, line: int, column: int) -> object:
    _require_arity("is_achilles", arguments, 1, line, column)
    value = _require_int("is_achilles", arguments[0], line, column)
    if value < 2:
        return False
    remaining = value
    divisor = 2
    exponent_gcd = 0
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            count = 0
            while remaining % divisor == 0:
                remaining //= divisor
                count += 1
            if count < 2:
                return False
            exponent_gcd = math.gcd(exponent_gcd, count)
        divisor += 1
    if remaining > 1:
        return False
    return exponent_gcd == 1
```
This is `_is_powerful_number`'s own factorization loop (same structure,
same `count < 2: return False` powerful-check) with one addition: the
running `math.gcd` of every prime's exponent. A number is a perfect
power exactly when the `gcd` of its prime-factorization exponents
exceeds `1` (it then equals that `gcd`-th power of the product of each
prime raised to `exponent / gcd`) — so `exponent_gcd == 1` after the
powerful check both confirms "not a perfect power" and naturally
excludes single-prime-factor powers like `8 = 2^3` for free, since a
lone prime's own exponent becomes the `gcd` outright (`math.gcd(0, 3) ==
3`, not `1`). No need to call `_is_perfect_power` as a separate second
pass — the same loop and the same intermediate state (each prime's
exponent) answer both questions at once, avoiding factoring `value`
twice. `math.gcd` is already imported in `cinder/builtins.py` (used
throughout the number-theory cluster, e.g. `gcd`/`lcm`). `value < 2`
returns `false` up front rather than raising, matching
`is_powerful_number`'s own convention for non-positive input (`0`, `1`,
and negatives all fail the "has any prime factorization" precondition
the same way).

Acceptance criteria:
- `is_achilles(72);` is `true` — `2^3 * 3^2`, `gcd(3, 2) == 1`.
- `is_achilles(108);` is `true` — `2^2 * 3^3`, `gcd(2, 3) == 1`.
- `is_achilles(200);` is `true` — `2^3 * 5^2`, `gcd(3, 2) == 1`.
- `is_achilles(500);` is `true` — `2^2 * 5^3`, `gcd(2, 3) == 1`.
- `is_achilles(8);` is `false` — `2^3`, a single prime factor, so
  `exponent_gcd == 3` (a perfect cube, not an Achilles number).
- `is_achilles(36);` is `false` — `2^2 * 3^2`, `gcd(2, 2) == 2` (a
  perfect square).
- `is_achilles(4);` is `false` — `2^2`, single prime factor, perfect
  square.
- `is_achilles(12);` is `false` — `2^2 * 3^1`, exponent `1` on `3` fails
  the powerful check.
- `is_achilles(1);` is `false` — below the `n >= 2` floor.
- `is_achilles(0);` is `false`.
- `is_achilles(-72);` is `false` — negative input, following
  `is_powerful_number`'s existing convention rather than raising.
- `is_achilles(30);` is `false` — squarefree, no exponent reaches `2` at
  all (fails on the very first prime factor).
- `is_achilles(5.0);` raises `CinderRuntimeError` matching
  `"is_achilles() requires an int, got float"`.
- `is_achilles(true);` raises `CinderRuntimeError` matching
  `"is_achilles() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_powerful_number`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on `class TestIsPowerfulNumber`
and `class TestIsPerfectPower`, search either name). Once merged,
`README.md`'s Builtins bullet needs `is_achilles` added near
`is_powerful_number`/`is_perfect_power`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s roadmap paragraph needs this moved
from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 3. Language: named function expressions (`fn name(params) { ... }`) for self-referencing anonymous functions

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

## 4. Standard library: `is_pernicious` — a number whose binary popcount is itself prime

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

## 5. Language: inclusive range literal `a..=b` as sugar for `range(a, b + 1)`

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

## 6. Standard library: `is_sphenic` — a number that is the product of three distinct primes

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
