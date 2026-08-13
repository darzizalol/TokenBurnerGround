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

## 1. Standard library: `is_harshad` — digit-sum divisibility predicate [claimed 2026-08-13T19:46:07Z]

Build: add `is_harshad(n)` to `cinder/builtins.py`, registered right
after `is_automorphic` (search for `def _is_automorphic`, the current
last entry in the integer-property cluster) — the breadth task after
extended slice assignment for lists' depth work (landed via PR #237) per
`PROJECT.md`'s breadth-vs-depth policy. A positive integer `n` is a
Harshad (or Niven) number when it is evenly divisible by the sum of
its own decimal digits, e.g. `18` is Harshad since `1 + 8 = 9` and `18
% 9 == 0`; `19` is not, since `1 + 9 = 10` and `19 % 10 != 0`. It joins
the `is_perfect_square`/`is_armstrong`/`is_leap_year`/
`is_perfect_number`/`is_abundant`/`is_deficient`/`is_automorphic`
integer-property cluster as one more digit-based classification.

Compute the digit sum inline with the same plain walk `digit_sum`
already uses internally — `sum(int(digit) for digit in
str(abs(value)))` (search for `def _digit_sum` to copy its exact
expression) — rather than calling the `digit_sum` builtin's own
`(arguments, line, column)` wrapper, since that wrapper expects a
Cinder argument list, not a bare Python int:

```python
def _is_harshad(arguments: list, line: int, column: int) -> object:
    _require_arity("is_harshad", arguments, 1, line, column)
    value = _require_int("is_harshad", arguments[0], line, column)
    if value < 1:
        return False
    digit_total = sum(int(digit) for digit in str(value))
    return value % digit_total == 0
```

Model the arity/type-checking exactly on `_is_automorphic`'s structure:
`_require_arity("is_harshad", arguments, 1, line, column)`, then
`value = _require_int("is_harshad", arguments[0], line, column)`
(reusing the shared `_require_int` helper — do **not** hand-roll a
separate `isinstance` check). The `value < 1` guard matches
`is_abundant`/`is_deficient`'s own convention of answering `false` on
zero and negative input rather than raising a domain error — it also
sidesteps a `ZeroDivisionError` that a bare digit-sum-of-zero would
otherwise cause, since `digit_total` is only ever `0` when `value` is
`0`, which this guard already excludes before the division runs.

Acceptance criteria:
- `is_harshad(18);` is `true` — `1 + 8 = 9`, `18 % 9 == 0`.
- `is_harshad(19);` is `false` — `1 + 9 = 10`, `19 % 10 != 0`.
- `is_harshad(1);` is `true` — every single nonzero digit divides
  itself.
- `is_harshad(12);` is `true` — `1 + 2 = 3`, `12 % 3 == 0`.
- `is_harshad(11);` is `false` — `1 + 1 = 2`, `11 % 2 != 0`.
- `is_harshad(100);` is `true` — `1 + 0 + 0 = 1`, `100 % 1 == 0`
  (every integer is divisible by `1`).
- `is_harshad(0);` is `false` — excluded by the `value < 1` guard
  rather than raising a division-by-zero error.
- `is_harshad(-18);` is `false` — negative input answers `false`
  without raising, matching `is_abundant`/`is_deficient`'s convention.
- `is_harshad(5.0);` raises `CinderRuntimeError` matching
  `"is_harshad() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `is_harshad(true);` raises `CinderRuntimeError` matching
  `"is_harshad() requires an int, got bool"` — `_require_int` already
  excludes `bool` from passing as an int.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_deficient`/`is_automorphic`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_harshad` added near
`is_perfect_number`/`is_abundant`/`is_deficient`/`is_automorphic`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 2. Language: map-destructuring key rename (`let {a: x, b} = expr;`)

Build: the depth task after task 1's breadth work (`is_harshad`) per
`PROJECT.md`'s breadth-vs-depth policy. Every map-destructuring form —
`let {a, b} = expr;`, plain assignment `{a, b} = expr;`, `for {a, b} in
list_of_maps { ... }`, function params `fn f({a, b}) { ... }`, and both
comprehension loop-variable forms — currently binds each name to a
variable of the *same* name as the map key it reads (`{a, b}` always
declares `a` and `b`). There is no way to bind under a different local
name, unlike JS destructuring's `const {a: x} = obj`. Verify the gap:
`python3 -m cinder.cli eval 'let {a: x} = {"a": 1}; print(x);'` currently
raises `ParseError` `"'}' after destructuring pattern"` (the parser sees
`IDENTIFIER COLON` where it only expects `IDENTIFIER COMMA`/`RBRACE`).

All five forms share two parser entry points and one interpreter entry
point, so the change is centralized rather than five separate edits:
`_destructure_map_pattern` (search for `def _destructure_map_pattern` in
`cinder/parser.py`) is called by `let`, `for`, params, and both
comprehensions; `_try_map_destructure_assign_statement` (search for that
name, same file) has its own inlined copy of the same identifier-list
loop for the plain-assignment form; both feed `names`/`rest` straight
into `_bind_map_destructure` (search for `def _bind_map_destructure` in
`cinder/interpreter.py`), the single place that actually reads keys out
of the map and binds variables. Changing what `names` holds and how
`_bind_map_destructure` consumes it is the whole feature — none of the
five call sites need their own changes.

Change `names` from a flat `list[str]` (map key doubles as binding name)
to a `list[tuple[str, str]]` of `(key, binding)` pairs, `binding`
defaulting to `key` when no rename is written. Add a shared parsing
helper right above `_destructure_map_pattern`:

```python
def _destructure_map_pattern_entry(self) -> "tuple[str, str]":
    key = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    if self._check(TokenType.COLON):
        self._advance()
        binding = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    else:
        binding = key
    return key, binding
```

In `_destructure_map_pattern`, replace both
`names.append(self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme)`
lines (the initial entry and the one inside the `while COMMA` loop) with
`names.append(self._destructure_map_pattern_entry())`. Do the same for
the two matching lines inside
`_try_map_destructure_assign_statement`'s own `try` block. Nothing else
in either function changes — the rest-element handling, the
rest-must-be-last check (`_RestNotLast` in the assignment form), and the
trailing `}`/`=` consumption are all untouched, since they operate on
`names` as an opaque list either way.

In `_bind_map_destructure`, unpack the pairs and use the *key* for the
map lookup and the *binding* for the environment write, and use a set of
keys (not the tuple list itself) to compute the rest element's leftover
keys:

```python
def _bind_map_destructure(
    self,
    env: Environment,
    names: list,
    rest: "str | None",
    value: object,
    line: int,
    column: int,
    use_assign: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise CinderRuntimeError(
            f"cannot destructure {type_name(value)} as a map",
            line,
            column,
        )
    seen_keys = set()
    for key, binding in names:
        seen_keys.add(key)
        if key not in value:
            raise CinderRuntimeError(
                f"destructuring pattern expects key {key!r}, not found in map",
                line,
                column,
            )
        self._bind_destructure_name(env, binding, value[key], line, column, use_assign)
    if rest is not None:
        remaining = {k: v for k, v in value.items() if k not in seen_keys}
        self._bind_destructure_name(env, rest, remaining, line, column, use_assign)
```

The error message keeps referencing the *key* (what's missing from the
map), not the binding name, since that's what a reader needs to fix.
`DestructureLetStmt`/`DestructureAssign`/`ForStmt`/`Param`/
`ListComprehension`/`MapComprehension` in `cinder/ast_nodes.py` need no
field changes — `names: list` already accepts either shape, and every
consumer of `.names` (grep confirms only `_bind_map_destructure` and
`_bind_list_destructure` read it, dispatched by each node's own `is_map`
flag) already routes map-mode data through the function above.

No rename support is added to *list*-pattern destructuring
(`let [a, b] = expr;`) — list patterns are purely positional, so
"rename" has no meaning there; this task only touches
`_destructure_map_pattern`/`_try_map_destructure_assign_statement`/
`_bind_map_destructure`.

Test-shape ripple: every existing `test_parser.py` assertion that checks
a map-destructure node's `.names` as a flat list of plain strings (e.g.
`["a", "b"]` for `{a, b} = ...;`) now needs updating to the pair form
(`[("a", "a"), ("b", "b")]`) — search `test_parser.py` for
`is_map=True` sites and the surrounding `DestructureLetStmt`/
`DestructureAssign` shape tuples that precede them; the `shape()`/
`stmt_shape()` helpers themselves need no changes since they just
forward whatever `.names` holds. This is a mechanical, no-behavior-change
update for every pre-existing plain-name test; only the *new* rename
tests exercise the actual feature.

Acceptance criteria:
- `let {a: x, b} = {"a": 1, "b": 2}; print(x); print(b);` prints `1`
  then `2` — `a`'s value binds to `x`, `b` binds to itself (no rename).
- `{a: x} = {"a": 5}; print(x);` (plain-assignment form, `x` already
  declared via `let x = 0;` beforehand) prints `5`.
- `for {a: x, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}] { print(x + b); }`
  prints `3` then `7`.
- `fn f({a: x}) { return x; } print(f({"a": 9}));` prints `9`.
- `print([x for {a: x} in [{"a": 1}, {"a": 2}]]);` prints `[1, 2]`.
- `let {a: x, ...rest} = {"a": 1, "b": 2, "c": 3}; print(x); print(rest);`
  prints `1` then `{"b": 2, "c": 3}` — the rest element still collects by
  *key*, unaffected by the earlier rename.
- `let {a: x} = {"b": 1};` raises `CinderRuntimeError` matching
  `"destructuring pattern expects key 'a', not found in map"` — the
  error names the source key, not the binding `x`.
- Plain, non-renamed patterns (`let {a, b} = expr;` and every other
  existing form) behave identically to before this task — this is purely
  additive syntax.
- `let {a: x, a: y} = {"a": 1};` (same key renamed twice) is not
  specially rejected — it parses and runs like any other repeated-name
  destructuring pattern already does today (last binding wins, no new
  validation added for this task).
- Full test suite passes, including the updated `.names` shape
  assertions described above.

Likely files: `cinder/parser.py` (new `_destructure_map_pattern_entry`,
both call sites), `cinder/interpreter.py` (`_bind_map_destructure`),
`tests/test_parser.py` (shape assertions plus new rename tests),
`tests/test_interpreter.py` (new rename tests for `let`/assignment/
`for`/params/comprehensions). Once merged, `README.md`'s destructuring
bullets need a rename mention added to each of the five forms, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_perfect_cube` — integer cube-root predicate

Build: the breadth task after task 2's depth work (map-destructuring key
rename) per `PROJECT.md`'s breadth-vs-depth policy. A positive, negative,
or zero integer `n` is a perfect cube when some integer `k` satisfies
`k ** 3 == n` (e.g. `27 = 3**3`, `-8 = (-2)**3`, `0 = 0**3`). It joins the
`is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`/
`is_abundant`/`is_deficient`/`is_automorphic`/`is_harshad`
integer-property cluster as one more digit/root-based classification —
register it right after `is_harshad` (search for `def _is_harshad`, the
current last entry in the cluster once task 1 lands).

Unlike `is_perfect_square` (which excludes negative input, since no real
square root of a negative number is an integer), cube roots of negative
numbers *are* real and integral — `-8`'s cube root is `-2` — so this
predicate must accept negative input rather than short-circuiting to
`false` the way `is_perfect_square` does. There is no `math.icbrt` in the
standard library (unlike `math.isqrt` for squares), and a floating-point
`round(n ** (1/3))` risks exactly the rounding-error problem
`math.isqrt` was chosen to avoid for squares — so compute an exact
integer cube root via binary search on the magnitude, then restore the
sign:

```python
def _integer_cube_root(magnitude: int) -> int:
    if magnitude == 0:
        return 0
    low, high = 0, magnitude
    while low < high:
        mid = (low + high + 1) // 2
        if mid ** 3 <= magnitude:
            low = mid
        else:
            high = mid - 1
    return low


def _is_perfect_cube(arguments: list, line: int, column: int) -> object:
    _require_arity("is_perfect_cube", arguments, 1, line, column)
    value = _require_int("is_perfect_cube", arguments[0], line, column)
    magnitude = abs(value)
    root = _integer_cube_root(magnitude)
    return root ** 3 == magnitude
```

`_integer_cube_root` operates on the non-negative magnitude only, so its
own result is always non-negative; the predicate doesn't need to
reconstruct the signed root at all, since cubing preserves sign
symmetry: `magnitude` is a perfect cube iff `abs(value)` is, for either
sign of `value`. Model the arity/type-checking exactly on
`_is_harshad`/`_is_perfect_square`'s structure: `_require_arity`, then
`_require_int` (reusing the shared helper — do **not** hand-roll a
separate `isinstance` check).

Acceptance criteria:
- `is_perfect_cube(27);` is `true` — `3 ** 3 == 27`.
- `is_perfect_cube(1);` is `true` — `1 ** 3 == 1`.
- `is_perfect_cube(0);` is `true` — `0 ** 3 == 0`.
- `is_perfect_cube(-8);` is `true` — `(-2) ** 3 == -8`, unlike
  `is_perfect_square`, negative input is not automatically `false`.
- `is_perfect_cube(-27);` is `true` — `(-3) ** 3 == -27`.
- `is_perfect_cube(8);` is `true` — `2 ** 3 == 8`.
- `is_perfect_cube(9);` is `false` — no integer cubes to `9`.
- `is_perfect_cube(-9);` is `false` — no integer cubes to `-9` either.
- `is_perfect_cube(1000000);` is `true` — `100 ** 3 == 1000000`, a case
  large enough that a naive `round(n ** (1/3))` float approach could
  plausibly drift off by one, proving the binary-search approach is
  exact.
- `is_perfect_cube(5.0);` raises `CinderRuntimeError` matching
  `"is_perfect_cube() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_perfect_cube(true);` raises `CinderRuntimeError` matching
  `"is_perfect_cube() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_harshad`/`is_perfect_square`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_perfect_cube` added near
`is_perfect_square`/`is_armstrong`/`is_automorphic`/`is_harshad`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `aliquot_sum` — sum of an integer's proper divisors

Build: a fresh breadth task after task 2's depth work (map-destructuring
key rename), added this grooming pass to keep the backlog stocked ahead
of tonight's pace. Add `aliquot_sum(n)` to `cinder/builtins.py`,
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

## 5. Language: keyword arguments in function calls (`f(a: 1, b: 2)`)

Build: the depth task after tasks 3 and 4 stacked two breadth tasks
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

## 6. Standard library: `is_pronic` — oblong-number predicate

Build: the breadth task after task 5's depth work (keyword arguments in
function calls) per `PROJECT.md`'s breadth-vs-depth policy. Add
`is_pronic(n)` to `cinder/builtins.py`, registered right after
`is_perfect_cube` (search for `def _is_perfect_cube`, the current last
entry in the integer-property cluster once task 5's neighbor, task 3,
lands — this task only depends on task 3, not task 5). A pronic (or
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
