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

## 1. Standard library: `is_octagonal` — membership test for the octagonal numbers

Build: the breadth task restocking the backlog back to 6 tasks now that
task 2 (bare comma multi-target assignment) rounds out this pass's
depth work, per `PROJECT.md`'s breadth-vs-depth policy. `is_triangular`,
`is_pentagonal`, `is_hexagonal`, and `is_heptagonal`
(`cinder/builtins.py`) already form a cluster of figurate-number
membership predicates, each using the same closed-form
`math.isqrt`-based identity with a different modular-residue check;
`is_octagonal` is the natural fifth member — octagonal numbers
(`1, 8, 21, 40, 65, 96, ...`) are as standard a figurate family as the
other four and nothing in Cinder tests membership in them yet. Verify
the gap:
```sh
python3 -m cinder.cli eval 'print(is_octagonal(8));'
# -> <eval>:1:7: undefined name 'is_octagonal' (did you mean 'is_pentagonal'?)
```

Add to `cinder/builtins.py`, registered right after `_is_heptagonal`
(search `def _is_heptagonal`, immediately before `_is_prime`):
```python
def _is_octagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_octagonal", arguments, 1, line, column)
    value = _require_int("is_octagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 3 * value + 1
    root = math.isqrt(candidate)
    return root * root == candidate and (1 + root) % 3 == 0
```
The `n`-th octagonal number is `P(n) = n * (3n - 2)`; solving
`3n^2 - 2n - value = 0` for `n` gives
`n = (1 + sqrt(1 + 3 * value)) / 3`, so `value` is octagonal iff
`1 + 3 * value` is a perfect square (`candidate`/`root`, the same
`math.isqrt` technique `is_triangular`/`is_pentagonal`/`is_hexagonal`/
`is_heptagonal` all use) *and* `(1 + root)` is divisible by `3` — the
modular-residue check that rules out roots which solve the algebraic
identity but don't correspond to an integer `n` (the same role
`is_pentagonal`'s `root % 6 == 5`, `is_hexagonal`'s `root % 4 == 3`,
and `is_heptagonal`'s `root % 10 == 7` each play for their own family).
`0` and negative inputs return `false` rather than raising, matching
every sibling predicate's closed-domain convention — this is a
membership test, not a value-returning function, so there is a
sensible (negative) answer for any integer input, unlike `collatz_max`/
`nth_prime`-style functions that raise on an invalid domain. Also
register the new dict entry (search `"is_heptagonal": _is_heptagonal,`,
add `"is_octagonal": _is_octagonal,` directly after it).

Acceptance criteria:
- `is_octagonal(1);` is `true` (`P(1) = 1`).
- `is_octagonal(0);` is `false` — `0` is not in the sequence under this
  cluster's 1-indexed convention (matches `is_heptagonal(0)`, `false`).
- For each of `1, 8, 21, 40, 65, 96` (the first six octagonal numbers,
  `P(1)` through `P(6)`), `is_octagonal(value);` is `true`.
- For each of `2, 5, 9, 20, 50, 100` (non-members interleaved among the
  above), `is_octagonal(value);` is `false`.
- `is_octagonal(29800);` is `true` — `P(100) = 100 * 298 = 29800`,
  confirming the check holds well beyond small brute-forced cases.
- `is_octagonal(-8);` is `false` — negative input, no domain error.
- `is_octagonal(8.0);` raises `CinderRuntimeError` matching
  `"is_octagonal() requires an int, got float"`.
- `is_octagonal(true);` raises `CinderRuntimeError` matching
  `"is_octagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_heptagonal`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsHeptagonal`, search
that name, for both the membership-cluster test shapes and the
arity/type-error test shapes). Once merged, `README.md`'s Builtins
bullet needs `is_octagonal` added right after its `is_heptagonal`
mention, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `binomial` — the binomial coefficient (`n` choose `k`)

Build: restocking the backlog back to 6 tasks now that `collatz_max`
landed via PR #303, per `PROJECT.md`'s breadth-vs-depth policy (task 3
above is breadth; alternation would prefer depth here, but no
well-scoped depth gap survived verification this pass — see the
"Current frontier" note in `PROJECT.md` — so this restocks with a
second breadth task, which the policy explicitly allows
occasionally). `factorial` (`cinder/builtins.py`) computes `n!` but
nothing in Cinder answers the combinatorics question built on top of
it: how many ways to choose `k` items from `n`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(binomial(5, 2));'
# -> <eval>:1:7: undefined name 'binomial'
```

Add to `cinder/builtins.py`, registered right after `_factorial`
(search `def _factorial`, immediately before `_sum`):
```python
def _binomial(arguments: list, line: int, column: int) -> object:
    _require_arity("binomial", arguments, 2, line, column)
    n, k = arguments
    for position, value in (("first", n), ("second", k)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CinderRuntimeError(
                f"binomial() requires an int as its {position} argument, "
                f"got {type_name(value)}",
                line, column,
            )
    if n < 0 or k < 0:
        raise CinderRuntimeError(
            "binomial() requires non-negative n and k, domain error", line, column
        )
    return math.comb(n, k)
```
This mirrors `_gcd`/`_lcm`'s own two-int-argument style (search
`def _gcd`, immediately above `_factorial`) — a `for position, value in
(...)` loop checking both arguments share the same type-error shape —
and `_factorial`'s own choice to delegate to a stdlib `math` function
rather than a hand-rolled loop, since `math.comb` is exact-integer and
already the standard library's own answer to this exact question. `k >
n` is not a domain error: `math.comb(n, k)` correctly returns `0` for
that case (zero ways to choose more items than exist), matching every
combinatorics textbook's convention, so no extra check is needed beyond
what `math.comb` already enforces. Also register the new dict entry
(search `"factorial": _factorial,`, add `"binomial": _binomial,`
directly after it).

Acceptance criteria:
- `binomial(5, 2);` is `10`, `binomial(5, 0);` is `1`, `binomial(5, 5);`
  is `1` — the standard small cases.
- `binomial(0, 0);` is `1` — the empty-choose-empty edge case.
- `binomial(10, 3);` is `120`.
- `binomial(30, 15);` is `155117520` — confirms the check holds well
  beyond small brute-forced cases.
- `binomial(5, 8);` is `0` — choosing more items than exist returns
  `0`, not a domain error.
- `binomial(-1, 2);` and `binomial(5, -1);` both raise
  `CinderRuntimeError` matching `"binomial() requires non-negative n
  and k, domain error"`.
- `binomial(5.0, 2);` raises `CinderRuntimeError` matching `"binomial()
  requires an int as its first argument, got float"`.
- `binomial(5, true);` raises `CinderRuntimeError` matching
  `"binomial() requires an int as its second argument, got bool"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `factorial`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (add a `class TestBinomial` modeled on `class
TestFactorial`, search that name, for both the combinatorics-value test
shapes and the arity/type/domain-error test shapes, plus `class
TestGcd`, search that name, for the two-argument type-error message
shape). Once merged, `README.md`'s Builtins bullet needs `binomial`
added near `factorial`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_lucas` — the k-th Lucas number by position

Build: restocking the backlog back to 6 tasks now that a `match`
expression with literal patterns and a `_` wildcard landed via PR #304,
per `PROJECT.md`'s breadth-vs-depth policy (that task was depth;
alternation restocks with breadth here). `is_lucas_number`
(`cinder/builtins.py`) tests membership in the Lucas sequence, and
`nth_fibonacci` (landed via PR #306) already answers the same "which
position" question for Fibonacci numbers, but nothing in Cinder
answers the complementary question for Lucas numbers: given a
1-indexed position, what value is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_lucas(5));'
# -> <eval>:1:7: undefined name 'nth_lucas'
```

Add to `cinder/builtins.py`, registered right after `_is_lucas_number`
(search `def _is_lucas_number`, immediately before `_is_happy_number` —
if task 1 has landed first, `_nth_fibonacci` will sit between them;
register `_nth_lucas` after whichever of the two is currently last):
```python
def _nth_lucas(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_lucas", arguments, 1, line, column)
    value = _require_int("nth_lucas", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_lucas() requires a positive integer, domain error", line, column
        )
    previous, current = 1, 3  # L(1), L(2)
    if value == 1:
        return previous
    for _ in range(value - 2):
        previous, current = current, previous + current
    return current
```
This mirrors `_is_lucas_number`'s own indexing convention exactly
(search `def _is_lucas_number`): that predicate's internal loop seeds
`previous, current = 1, 3` and comments them `L(1), L(2)`, i.e. this
cluster's 1-indexed Lucas sequence starts at `L(1) = 1, L(2) = 3, L(3)
= 4, ...` and deliberately omits the standard mathematical `L(0) = 2`
seed — there is no `nth_lucas(0)` any more than there's an
`is_lucas_number` match for the value `2` counted as position `0`.
Getting this seed wrong (e.g. starting from `L(0) = 2, L(1) = 1` like
the textbook definition) would silently desynchronize `nth_lucas` from
`is_lucas_number`'s own notion of position, so `nth_lucas(n)` and
`is_lucas_number`'s internal walk must agree position-for-position —
verified directly in the acceptance criteria below. A domain error (not
a sentinel value) for `value < 1` matches `nth_prime`/`nth_fibonacci`'s
own convention for their own "not a valid input" case, since this is a
value-returning function, not a predicate. Also register the new dict
entry (search `"is_lucas_number": _is_lucas_number,`, add `"nth_lucas":
_nth_lucas,` directly after it).

Acceptance criteria:
- `nth_lucas(1);` is `1`, `nth_lucas(2);` is `3`, `nth_lucas(3);` is
  `4`, `nth_lucas(4);` is `7`, `nth_lucas(5);` is `11` — the first five
  Lucas numbers by this cluster's 1-indexed convention.
- `nth_lucas(10);` is `123`.
- `nth_lucas(15);` is `1364` — confirms the check holds well beyond
  small brute-forced cases.
- For each `n` in `1..15`, `is_lucas_number(nth_lucas(n));` is `true` —
  `nth_lucas` and `is_lucas_number` agree on the same sequence.
- `nth_lucas(0);` and `nth_lucas(-3);` both raise `CinderRuntimeError`
  matching `"nth_lucas() requires a positive integer, domain error"`.
- `nth_lucas(2.0);` raises `CinderRuntimeError` matching `"nth_lucas()
  requires an int, got float"`.
- `nth_lucas(true);` raises `CinderRuntimeError` matching `"nth_lucas()
  requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_lucas_number`,
see current line numbers — shift if earlier tasks this cycle land
first), `tests/test_builtins.py` (model on `class TestIsLucasNumber`,
search that name, for both the sequence-value test shapes and the
arity/type-error test shapes — the domain-error test shape instead
mirrors `class TestCollatzLength`, search that name, since `nth_lucas`
raises rather than returning `false` for an invalid position). Once
merged, `README.md`'s Builtins bullet needs `nth_lucas` added near
`is_lucas_number`/`nth_fibonacci`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Language: bound-identifier patterns in `match` arms

Build: restocking the backlog back to 6 tasks now that `nth_prime` landed
via PR #305, per `PROJECT.md`'s breadth-vs-depth policy (tasks 1, 3, 4,
and 5 above are all breadth; alternation resumes with depth here — the
queue was already lopsided 4-breadth-to-1-depth, and `PROJECT.md`'s
"Current frontier" note from the previous grooming pass explicitly
flagged this as the next depth pick). PR #304 added a `match` expression
with literal patterns (`1`, `"a"`, `true`, `nil`, ...) and a `_` wildcard
that matches unconditionally but binds nothing — deliberately scoped
small, with richer patterns called out as a natural follow-up. The
gap: there is no way to match unconditionally *and* capture the
subject's value under a name, the way every pattern-matching language
this feature is modeled on (Rust, Python's `match`, Swift, ...) supports
as its most basic capture form. `tests/test_parser.py`'s own
`test_match_bound_identifier_pattern_raises` (search that name) already
documents today's behavior as a `ParseError` — this task's job is to
flip that into working, useful syntax. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match (5) { 0 => "zero", n => n + 1 });'
# -> <eval>:1:31: expected a literal or '_' in match pattern, found identifier 'n'
```

Add a `binding` field to `MatchArm` (`cinder/ast_nodes.py`, search
`class MatchArm`):
```python
@dataclass(frozen=True)
class MatchArm:
    """`pattern` is `None` for an unconditional arm — either the `_`
    wildcard (`binding` also `None`) or a bound-identifier pattern
    (`binding` holds the name), both of which match unconditionally
    and are otherwise compared via `values_equal`, the same helper
    `SwitchStmt` case-matching already uses, when `pattern` is not
    `None`. A bound-identifier arm's `binding` name is defined, holding
    the match subject's value, in a fresh child scope that only
    `body`'s evaluation sees — it does not leak into the enclosing
    scope, mirroring `TryStmt`'s own `catch_name` binding
    (`cinder/interpreter.py`'s `_execute_try`)."""

    pattern: "Expr | None"
    body: "Expr"
    binding: "str | None" = None
```
Update `MatchExpr`'s own docstring (search `class MatchExpr`,
immediately below) to mention bound-identifier arms alongside the `_`
wildcard as the two kinds of unconditional arm.

In `cinder/parser.py`, change `_match_pattern` (search
`def _match_pattern`) to return a `(pattern, binding)` pair instead of
a bare pattern, accepting any identifier (not just `_`) as an
unconditional arm:
```python
    def _match_pattern(self) -> "tuple[Expr | None, str | None]":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            if token.lexeme == "_":
                return None, None
            return None, token.lexeme
        if token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column), None
        if token.type == TokenType.TRUE:
            self._advance()
            return Literal(True, token.line, token.column), None
        if token.type == TokenType.FALSE:
            self._advance()
            return Literal(False, token.line, token.column), None
        if token.type == TokenType.NIL:
            self._advance()
            return Literal(None, token.line, token.column), None
        raise ParseError(
            f"expected a literal, identifier, or '_' in match pattern, "
            f"found {self._describe(token)}",
            token.line,
            token.column,
        )
```
And update `_match_arm` (search `def _match_arm`, immediately above)
to unpack the pair and thread `binding` through:
```python
    def _match_arm(self) -> MatchArm:
        pattern, binding = self._match_pattern()
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return MatchArm(pattern, body, binding)
```
`TRUE`/`FALSE`/`NIL` are their own token types (not `IDENTIFIER`), so
this doesn't create any ambiguity with the existing literal-keyword
branches — the new `IDENTIFIER` branch only ever sees names like `n`,
`x`, or `_`.

In `cinder/interpreter.py`, update `_evaluate_match` (search
`def _evaluate_match`) to bind the identifier in a fresh child scope
before evaluating the body, mirroring `_execute_try`'s `catch_env`
pattern (search `def _execute_try`, `catch_env = Environment(env)`):
```python
    def _evaluate_match(self, expr: MatchExpr, env: Environment) -> object:
        subject = self.evaluate(expr.subject, env)
        for arm in expr.arms:
            if arm.pattern is None:
                if arm.binding is None:
                    return self.evaluate(arm.body, env)
                arm_env = Environment(env)
                arm_env.define(arm.binding, subject)
                return self.evaluate(arm.body, arm_env)
            if values_equal(subject, self.evaluate(arm.pattern, env)):
                return self.evaluate(arm.body, env)
        raise CinderRuntimeError("no match arm matched value", expr.line, expr.column)
```
No placement restriction is added — an unconditional arm (wildcard or
bound-identifier) before a later arm makes that later arm unreachable,
exactly as already true of `_` today (verified nowhere in the existing
suite), so this task does not introduce a dead-arm check either; that's
a separate, out-of-scope static-analysis feature, not part of closing
this gap.

Acceptance criteria:
- `match (5) { 0 => "zero", n => n + 1 };` is `6` — a bound-identifier
  arm both matches unconditionally and makes the subject's value
  available in its body.
- `match (0) { 0 => "zero", n => n + 1 };` is `"zero"` — an earlier
  literal arm still wins over a later bound-identifier arm, confirming
  arms are still tried strictly in source order.
- `let x = 99; match (5) { n => n }; print(x);` prints `99` — the
  binding is scoped to the arm's body only and does not leak into or
  shadow the enclosing scope after the match expression finishes.
- `let n = 1; let result = match (5) { n => n * 2 }; print(n); print(result);`
  prints `1` then `10` — an identifier pattern's binding shadows an
  outer variable of the same name *inside the arm body only*; the
  outer `n` is unaffected.
- `match (5) { _ => "wildcard" };` still is `"wildcard"` — the existing
  non-binding `_` wildcard is unchanged.
- `let _ = 5; print(_);` still prints `5` — `_` remains usable as an
  ordinary variable name outside match patterns, unaffected by this
  change (mirrors the existing `test_bare_underscore_identifier_still_works`
  coverage in both `tests/test_parser.py` and `tests/test_interpreter.py`).
- `match (true) { flag => flag };` is `true` — works for non-numeric
  subject types too, not just integers.
- `tests/test_parser.py`'s existing `test_match_bound_identifier_pattern_raises`
  (search that name) must be replaced — bound-identifier patterns no
  longer raise `ParseError`; update or remove that test in favor of a
  shape assertion for the new syntax (e.g. via `shape()`, see below).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`, `MatchExpr`
docstrings), `cinder/parser.py` (`_match_pattern`, `_match_arm`),
`cinder/interpreter.py` (`_evaluate_match`), `tests/test_parser.py`
(the `shape()` helper's `MatchExpr` branch, search `isinstance(node,
MatchExpr)`, needs its per-arm tuple extended from `(pattern_shape,
body_shape)` to `(pattern_shape, body_shape, arm.binding)` — this means
`test_match_shape`, `test_match_literal_patterns`, and
`test_match_usable_as_let_initializer` each need a trailing `None`
added to every existing arm tuple in their expected output, plus
replacing `test_match_bound_identifier_pattern_raises` as described
above; all four live in `class TestMatchExpression`, search that name),
`tests/test_interpreter.py` (extend `class TestMatchExpression`, search
that name, with the binding/shadowing/scoping end-to-end cases above).
Once merged, `README.md`'s `match` expression bullet needs a
bound-identifier example added, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Language: multi-value literal patterns in match arms (`1, 2 => "small"`)

Build: restocking the backlog back to 6 tasks now that `nth_fibonacci`
landed via PR #306, per `PROJECT.md`'s breadth-vs-depth policy
(`nth_fibonacci` was breadth; alternation restocks with depth here — the
queue was 2-depth/3-breadth after the last pass, and a depth restock
keeps that ratio from drifting further). PR #304's `match` expression
scoped its patterns down to a single literal (or `_`) per arm;
`tests/test_parser.py`'s own `test_match_multi_value_arm_raises` (search
that name) already documents today's behavior as a `ParseError`, sitting
right next to `test_match_bound_identifier_pattern_raises` (task 5's own
gap-marker) — these two tests were left side by side flagging sibling
gaps, and this task closes the second one. Every pattern-matching
language this feature is modeled on (Rust's `1 | 2 => ...`, Python's
`case 1 | 2:`) lets one arm answer for several literal values without
repeating the body; Cinder cannot yet. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match (2) { 1, 2 => "one-or-two", _ => "other" });'
# -> <eval>:1:20: expected '=>' after match pattern, found ','
```

Change `_match_arm` (search `def _match_arm`, `cinder/parser.py`) to
collect a comma-separated list of patterns before `=>`, then desugar
into one flat `MatchArm` per pattern, all sharing the same `body` node —
this needs no `ast_nodes.py` or `cinder/interpreter.py` changes at all,
since `MatchArm` and `_evaluate_match` (search `def _evaluate_match`)
already try arms one at a time in source order and stop at the first
match; N arms with identical bodies behave exactly like one arm with N
patterns would, for free:
```python
    def _match_arm(self) -> "list[MatchArm]":
        first_token = self._peek()
        patterns = [self._match_pattern()]
        while self._check(TokenType.COMMA):
            self._advance()
            patterns.append(self._match_pattern())
        if len(patterns) > 1 and any(pattern is None for pattern in patterns):
            raise ParseError(
                "'_' cannot be combined with other patterns in a match arm",
                first_token.line,
                first_token.column,
            )
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return [MatchArm(pattern, body) for pattern in patterns]
```
And update `_match_expr` (search `def _match_expr`, immediately above) to
flatten the list instead of appending a single arm:
```python
    def _match_expr(self) -> Expr:
        match_token = self._advance()  # consume 'match'
        self._consume(TokenType.LPAREN, "'(' after 'match'")
        subject = self._assignment()
        self._consume(TokenType.RPAREN, "')' after match subject")
        self._consume(TokenType.LBRACE, "'{' after match subject")
        arms = list(self._match_arm())
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACE):
                break
            arms.extend(self._match_arm())
        self._consume(TokenType.RBRACE, "'}' after match arms")
        return MatchExpr(subject, arms, match_token.line, match_token.column)
```
The comma token is doing double duty here — separating patterns *within*
one arm's pattern list, and separating *arms* from each other — but
there is no ambiguity: `_match_arm`'s own comma-loop only runs while
collecting patterns, strictly before `=>` is consumed, so it can never
accidentally swallow the comma that starts the next arm (that comma is
only ever reached, and consumed, by `_match_expr`'s own loop, after
`_match_arm` has already returned). Trace `match (x) { 1, 2 => "a", 3 =>
"b" }`: `_match_arm` collects `[1, 2]` (stopping because `=>` follows
`2`, not a comma), consumes `=>`, parses body `"a"` (stops before the
following comma — `_ternary()` never consumes a top-level comma);
control returns to `_match_expr`, which sees that comma as its own arm
separator and calls `_match_arm` again for `3 => "b"`. No backtracking
or lookahead is needed anywhere in this change. Mixing `_` into a
multi-value list (`1, _ => ...` or `_, 1 => ...`) is rejected at parse
time rather than silently accepted — allowing it would make every
pattern beside the wildcard dead code in an already-non-obvious way, and
there is no such thing as "the wildcard, but only sometimes" for a
construct that already has a bare `_` for "always."

Acceptance criteria:
- `match (2) { 1, 2 => "one-or-two", _ => "other" };` is `"one-or-two"`.
- `match (5) { 1, 2 => "one-or-two", _ => "other" };` is `"other"` — a
  non-matching subject still falls through to a later arm.
- `match (3) { 1, 2, 3 => "small", _ => "large" };` is `"small"` — three
  patterns sharing one arm, not just two.
- `match (nil) { false, nil => "falsy-ish", true => "truthy" };` is
  `"falsy-ish"`, and `match (true) { false, nil => "falsy-ish", true =>
  "truthy" };` is `"truthy"` — mixed literal types (`bool`, `nil`)
  combine in one multi-value arm.
- `match (5) { 1, 2 => "a" };` raises `CinderRuntimeError` matching
  `"no match arm matched value"` — no wildcard present and the subject
  matches neither pattern.
- `shape(parse('match (x) { 1, 2 => "ab", _ => "c" }'))` (see
  `tests/test_parser.py`) desugars to three flat arms, the same `body`
  shape repeated for the two literals that share it: `[(("Literal", 1),
  ("Literal", "ab")), (("Literal", 2), ("Literal", "ab")), (None,
  ("Literal", "c"))]` — confirms the desugaring, not just the
  end-to-end value.
- `match (1) { 1, _ => "x" };` and `match (1) { _, 1 => "x" };` both
  raise `ParseError` matching `"'_' cannot be combined with other
  patterns in a match arm"`.
- `match (1) { 1, 2 => "ok", };` (trailing comma after the arm, before
  `}`) is still `"ok"` — unaffected by this change, confirming the
  pattern-list comma-loop and the arm-separator comma-loop don't
  interfere with each other.
- `tests/test_parser.py`'s existing `test_match_multi_value_arm_raises`
  (search that name) must be replaced — multi-value arms no longer raise
  `ParseError`; update or remove that test in favor of a shape assertion
  for the new syntax.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_arm`, `_match_expr`),
`tests/test_parser.py` (`class TestMatchExpression`, search that name —
replace `test_match_multi_value_arm_raises`, add the multi-value shape
assertion and the `_`-combination `ParseError` cases), `tests/test_interpreter.py`
(extend `class TestMatchExpression`, search that name, with the
multi-value end-to-end value cases above). Once merged, `README.md`'s
`match` expression bullet needs a multi-value example added, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
