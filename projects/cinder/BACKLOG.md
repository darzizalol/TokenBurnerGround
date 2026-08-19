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

## 2. Standard library: `is_kaprekar` — numbers whose square splits back into themselves

Build: the breadth task after task 5's depth work (range literal `a..b`)
per `PROJECT.md`'s breadth-vs-depth policy, continuing the two-tasks-
at-once restock started by task 5 (see task 5's own restock note — two
merges, comma-separated `let`/`const` declarations and `cbrt`, dropped
the backlog from 6 to 4 in one stretch with no grooming pass in
between, so this pass adds both a depth and a breadth task to get back
to 6). A Kaprekar number is a positive integer `n` whose square, when
split into a right part and a left part at some digit boundary, sums
back to `n` — e.g. `45`: `45 ** 2 == 2025`, split as `20` and `25`,
`20 + 25 == 45`. Nothing in the existing digit-pattern/number-theory
cluster (`is_automorphic`, `is_harshad`, `is_perfect_cube`, ...) tests
this; `is_automorphic` (`str(value * value).endswith(str(value))`) is
actually the fixed special case of a Kaprekar split at the boundary
where the right part has exactly as many digits as `n` itself, so this
task is a natural generalization sitting right next to it. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(is_kaprekar(45));'
# -> CinderRuntimeError: undefined name 'is_kaprekar'
```

Add to `cinder/builtins.py`, registered right after `_is_automorphic`
(search `def _is_automorphic`, immediately before `_is_harshad`):
```python
def _is_kaprekar(arguments: list, line: int, column: int) -> object:
    _require_arity("is_kaprekar", arguments, 1, line, column)
    value = _require_int("is_kaprekar", arguments[0], line, column)
    if value < 1:
        return False
    square = value * value
    digits = str(square)
    for split in range(1, len(digits) + 1):
        right = square % (10 ** split)
        left = square // (10 ** split)
        if right != 0 and left + right == value:
            return True
    return False
```
The `right != 0` guard skips vacuous splits (a leading-zero right part,
e.g. `n=10`, `square=100`: the `split=2` boundary gives `right=0,
left=1`, which is not a real two-part split); the loop runs `split` up
to and including `len(digits)` (not stopping one short) so the
whole-square/zero-left split is reachable too — this is what makes `1`
qualify (`1 ** 2 == 1`, `split=1` gives `right=1, left=0`,
`0 + 1 == 1`) without a separate trivial-case branch, matching the
standard sequence (OEIS A006886: `1, 9, 45, 55, 99, 297, 703, 999,
...`). `value < 1` returns `false` up front rather than raising,
matching the digit-pattern cluster's existing convention for `0`/
negative input (`is_repdigit`, `is_palindrome_number`, `is_harshad`
all do the same) rather than the "negative can legitimately be true"
convention `is_perfect_cube`/`is_perfect_power` use — a Kaprekar split
has no meaningful negative case, the same reasoning `is_undulating`
(task 4 elsewhere in this file) already used for the same choice.

Acceptance criteria:
- `is_kaprekar(1);` is `true` — trivial split (`0 + 1 == 1`).
- `is_kaprekar(9);` is `true` (`81` → `8 + 1 == 9`).
- `is_kaprekar(45);` is `true` (`2025` → `20 + 25 == 45`).
- `is_kaprekar(55);` is `true` (`3025` → `30 + 25 == 55`).
- `is_kaprekar(99);` is `true` (`9801` → `98 + 01 == 99`).
- `is_kaprekar(297);` is `true` (`88209` → `88 + 209 == 297`).
- `is_kaprekar(703);` is `true` (`494209` → `494 + 209 == 703`).
- `is_kaprekar(999);` is `true` (`998001` → `998 + 001 == 999`).
- `is_kaprekar(2223);` is `true` (`4941729` → `494 + 1729 == 2223`).
- `is_kaprekar(0);` is `false` — below the `n >= 1` floor.
- `is_kaprekar(10);` is `false` — `100`'s only nontrivial split has a
  zero right part.
- `is_kaprekar(2);` is `false` (`4`, no split sums to `2`).
- `is_kaprekar(100);` is `false`.
- `is_kaprekar(-45);` is `false` — negative input, following the
  cluster's existing convention rather than raising.
- `is_kaprekar(5.0);` raises `CinderRuntimeError` matching
  `"is_kaprekar() requires an int, got float"`.
- `is_kaprekar(true);` raises `CinderRuntimeError` matching
  `"is_kaprekar() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_automorphic`, see
current line numbers — shift if task 5 lands first this cycle),
`tests/test_builtins.py` (model on `class TestIsAutomorphic` and `class
TestIsHarshad`, search either name). Once merged, `README.md`'s
Builtins bullet needs `is_kaprekar` added near `is_automorphic`/
`is_harshad`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 3. Language: map literal shorthand properties `{a, b}` as sugar for `{"a": a, "b": b}`

Build: the depth task after task 5's breadth work (`is_kaprekar`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that nested list-in-list destructuring patterns landed via PR
#273, dropping the count to the 5-task floor. Map-pattern *destructuring*
already has a shorthand — `let {a, b} = expr;` binds `a`/`b` by looking
up those keys — but *constructing* a map has no equivalent inverse: today
`{a, b}` (an existing local `a`/`b` you want keyed by their own names) is
always a `ParseError`, forcing the verbose `{"a": a, "b": b}` every time.
Verify the gap:
```sh
python3 -m cinder.cli eval 'let a = 1; let b = 2; print({a, b});'
# -> ParseError: expected ':' after map key, found ','
```
Confirm this exact program was already a guaranteed `ParseError` before
this task in both ways the parser could read it: at statement position
`{a, b};` fails the same way (map-literal attempt hits the same missing
colon; the block-statement fallback then also fails, since `a` isn't
followed by `;`), and inside a call/expression position like
`print({a, b})` there is no block-vs-map ambiguity to fall back to at
all — `{a, b}` there is unconditionally the map-literal attempt, and it
already raises the identical `"expected ':' after map key"` error. So no
currently-valid Cinder program's meaning changes.

**Important existing behavior to build on top of, not around**: an
ordinary map literal's key position is a full expression, evaluated at
runtime — `{a: 5}` with `let a = 1;` already produces `{1: 5}` (an
*integer* key `1`, `a`'s value, not the string `"a"`). Shorthand `{a}` is
therefore genuinely new sugar, not a restatement of existing behavior: it
uses the identifier's own *name* as a string key while still reading its
*value* for the map value — the same name-as-key/value-as-value split
`let {a, b} = expr;` already uses in the destructuring direction, just
inverted.

Add the shorthand branch to `_map_entry` in `cinder/parser.py` (the
`_map_pair`/`_map_comprehension`/`_map_literal` trio right after it are
unchanged):
```python
    def _map_entry(self):
        if self._check(TokenType.DOT_DOT_DOT):
            dots = self._advance()
            return Spread(self._ternary(), dots.line, dots.column)
        if self._check(TokenType.IDENTIFIER) and self._peek_next().type in (
            TokenType.COMMA,
            TokenType.RBRACE,
        ):
            name = self._advance()
            key = Literal(name.lexeme, name.line, name.column)
            value = Identifier(name.lexeme, name.line, name.column)
            return (key, value)
        return self._map_pair()
```
`Literal`/`Identifier` are both already imported in `cinder/parser.py`
(used throughout). This is the same "identifier immediately followed by
a specific lookahead token" technique `_call_argument` already uses to
recognize keyword arguments (`self._check(TokenType.IDENTIFIER) and
self._peek_next().type == TokenType.COLON`), just checking for
`COMMA`/`RBRACE` instead of `COLON` — and checking those specific two
tokens, not "anything but `:`", is what keeps this from misfiring: an
identifier followed by `for` (map comprehension source, `{a for a in
xs}`) or anything else falls straight through to the existing
`_map_pair()` path unchanged, so map comprehensions need no exclusion
logic of their own — the lookahead condition already keeps this scoped
to plain map literals only, for free. `_evaluate_map_literal`
(`cinder/interpreter.py`) needs no changes at all: it already evaluates
each pair's `key_expr`/`value_expr` generically, so a shorthand pair's
`Literal`/`Identifier` nodes are indistinguishable at runtime from any
other map entry.

Acceptance criteria:
- `let a = 1; let b = 2; print({a, b});` prints `{"a": 1, "b": 2}`.
- `let a = 1; print({a});` prints `{"a": 1}` — single shorthand entry.
- `let a = 1; print({a,});` prints `{"a": 1}` — shorthand plus trailing
  comma still works (existing trailing-comma handling is untouched).
- `let a = 1; print({a: 5});` still prints `{1: 5}` — an identifier
  immediately followed by `:` is completely unaffected, still an
  ordinary key expression (`a`'s *value*, not its name).
- `let a = 1; let b = 2; print({a, "c": 3, b});` prints
  `{"a": 1, "c": 3, "b": 2}` — shorthand and ordinary `key: value` pairs
  freely mix in one literal, in either order.
- `let a = 1; print({a, ...{"b": 2}});` prints `{"a": 1, "b": 2}` —
  shorthand composes with the existing spread entry.
- `let a = 1; print({["b" for b in [a]]: 1});` — not a real case, skip;
  instead confirm `[a for a in [1, 2]]` (list comprehension) still
  parses unaffected, and `{a for a in [1, 2]}`
  raises the same `ParseError` it already did (`"expected ':' after map
  key, found 'for'"` or equivalent) — map comprehensions are untouched,
  since `for` fails the `COMMA`/`RBRACE` lookahead.
- `print({});` still prints `{}` — empty map literal unaffected (no
  identifier to even reach the new branch).
- `{a, b};` — a shorthand map literal used as a bare statement — prints
  nothing but does not raise (same as any other map-literal-expression
  statement today, e.g. `{"a": 1};`).
- An undefined shorthand name raises the ordinary `"undefined name"`
  `CinderRuntimeError`, e.g. `{undefined_var};` — no special-cased error
  message, since the value side is an ordinary `Identifier` evaluation.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_map_entry`), `tests/test_parser.py`
(model on `class` containing `test_map_literal_with_spread`/
`test_map_literal`, search either name, plus add shorthand-vs-comprehension
and shorthand-vs-explicit-key regression cases near
`test_plain_map_literal_still_parses_after_comprehension_added`),
`tests/test_interpreter.py` (model on whatever covers
`test_map_literal_statement_unaffected`, search that name, for an
end-to-end `eval` case). Once merged, `README.md`'s map-literal
description needs a mention of the shorthand near the existing spread
entry (`{...m}`) description, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming
pass, not this task.

---

## 4. Standard library: `is_achilles` — powerful but not itself a perfect power

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

## 5. Language: named function expressions (`fn name(params) { ... }`) for self-referencing anonymous functions

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

## 6. Standard library: `is_pernicious` — a number whose binary popcount is itself prime

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
current line numbers — shift if task 1's range literal lands first this
cycle), `tests/test_builtins.py` (model on `class TestIsEvil` and `class
TestIsOdious`, search either name). Once merged, `README.md`'s Builtins
bullet needs `is_pernicious` added near `is_evil`/`is_odious`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave all three to
the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
