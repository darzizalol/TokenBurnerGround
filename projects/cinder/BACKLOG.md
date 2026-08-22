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

## 1. Standard library: `collatz_max` — the peak value reached by the Collatz (3n+1) recurrence

Build: the breadth task after task 1's depth work (a step component for
range expressions) per `PROJECT.md`'s breadth-vs-depth policy.
`is_subsequence` landed via PR #296.
`collatz_length` (`cinder/builtins.py`) already counts how many steps
the Collatz recurrence takes to reach `1` from a positive integer, but
discards every intermediate value along the way; `collatz_max` is its
natural value-returning sibling, reporting the highest value the
sequence reaches before it collapses to `1` — the same
"count-vs-collect/track" split `divisors`/`num_divisors` already have
between them (`divisors` collects, `num_divisors` counts; here
`collatz_length` counts steps, `collatz_max` tracks the peak). Verify
the gap:
```sh
python3 -m cinder.cli eval 'print(collatz_max(6));'
# -> CinderRuntimeError: undefined name 'collatz_max'
```

Add to `cinder/builtins.py`, registered right after `_collatz_length`
(search `def _collatz_length`, immediately before `_is_triangular`):
```python
def _collatz_max(arguments: list, line: int, column: int) -> object:
    _require_arity("collatz_max", arguments, 1, line, column)
    value = _require_int("collatz_max", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "collatz_max() requires a positive integer, domain error", line, column
        )
    peak = value
    n = value
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        if n > peak:
            peak = n
    return peak
```
This mirrors `_collatz_length`'s exact loop shape (same halve-if-even,
`3n + 1`-if-odd step, same `n < 1` domain-error convention — Collatz is
only defined for positive integers, so this raises rather than
answering `false` the way the closed-form membership predicates do,
matching `collatz_length`'s own choice) but tracks a running maximum
instead of a step count. `peak` starts at `value` itself so an input
already at its own maximum (including `n = 1`, whose sequence is just
`[1]`) still returns correctly with no special-casing. Also register
the new dict entry (search `"collatz_length": _collatz_length,`, add
`"collatz_max": _collatz_max,` directly after it).

Acceptance criteria:
- `collatz_max(1);` is `1` — the sequence is just `[1]`, already at its
  own peak.
- `collatz_max(6);` is `16` (sequence `6, 3, 10, 5, 16, 8, 4, 2, 1`).
- `collatz_max(7);` is `52` (sequence `7, 22, 11, 34, 17, 52, 26, 13,
  40, 20, 10, 5, 16, 8, 4, 2, 1`).
- `collatz_max(27);` is `9232` — the classic large-peak example,
  confirming the check holds well beyond small brute-forced cases.
- `collatz_max(0);` and `collatz_max(-5);` both raise
  `CinderRuntimeError` matching `"collatz_max() requires a positive
  integer, domain error"`.
- `collatz_max(6.0);` raises `CinderRuntimeError` matching
  `"collatz_max() requires an int, got float"`.
- `collatz_max(true);` raises `CinderRuntimeError` matching
  `"collatz_max() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `collatz_length`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestCollatzLength`, search
that name). Once merged, `README.md`'s Builtins bullet needs
`collatz_max` added right after its `collatz_length` mention, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 2. Language: a `match` expression with literal patterns and a `_` wildcard

Build: the depth task after task 1's breadth work (`collatz_max`) per
`PROJECT.md`'s breadth-vs-depth policy. This is a new arc, not another
destructuring-nesting corner: with a list pattern nested inside a map
pattern landing via PR #299, every corner of the list/map pattern
nesting matrix is closed, and
`PROJECT.md`'s "Current frontier" section already names "pattern matching
beyond destructuring, e.g. a `match` expression" as the natural next
depth direction. This task is a deliberately small first step into that
arc: literal patterns only (`int`/`float`/`string`/`true`/`false`/`nil`)
plus a `_` wildcard, one pattern per arm, no guards, no bindings, no
nested/destructuring patterns — those are all natural follow-ups once
this lands, not this task's job. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match (2) { 1 => "one", 2 => "two", _ => "other" });'
# -> <eval>:1:7: expected an expression, found 'match'
```

`switch` (`cinder/parser.py`'s `_switch_statement`, `cinder/ast_nodes.py`'s
`SwitchStmt`/`SwitchCase`, `cinder/interpreter.py`'s `_execute_switch`) is
the closest existing feature — a value tried against `case` values via the
`values_equal` helper (search `def values_equal`, `cinder/interpreter.py`)
already used for exactly this — but it's a *statement* whose case bodies
are blocks, so it cannot be used as a value (`let x = switch (n) { ... };`
is a `ParseError` today, and stays one — out of scope to change). `match`
is the value-producing counterpart: an *expression*, parsed in `_primary`
alongside `_list_literal`/`_map_literal`, whose arm bodies are single
expressions (reusing `values_equal` for the same match semantics `switch`
already has, so `1 == 1.0`-style cross-type equality behaves identically
in both).

Add a `MATCH` token (search `SWITCH = auto()`, `cinder/tokens.py`, add
`MATCH = auto()` right after it) and register the keyword (search
`"switch": TokenType.SWITCH,`, add `"match": TokenType.MATCH,` right
after it). Reuse the existing `FAT_ARROW` (`=>`) token for arm bodies —
it already exists for arrow-function literals (search `FAT_ARROW`,
`cinder/parser.py`) and needs no new lexer work.

Add two AST nodes (search `class Ternary`, `cinder/ast_nodes.py`, add
both right after it):
```python
@dataclass(frozen=True)
class MatchArm:
    """`pattern` is `None` for the `_` wildcard (matches unconditionally,
    evaluating no expression); otherwise a `Literal` node compared against
    the match subject via `values_equal`, the same helper `SwitchStmt`
    case-matching already uses."""

    pattern: "Expr | None"
    body: "Expr"


@dataclass(frozen=True)
class MatchExpr:
    """`match (subject) { pattern => body, ..., _ => body }`. `subject` is
    evaluated exactly once; `arms` are tried in source order via
    `values_equal` and the first match's `body` is evaluated and returned
    (no fallthrough, short-circuits on first match same as `SwitchStmt`).
    If no arm matches (including no `_` wildcard arm present), raises
    `CinderRuntimeError` — unlike `switch`'s `default`, there is no silent
    no-op: `match` is an expression and must produce a value or fail."""

    subject: "Expr"
    arms: list
    line: int
    column: int
```

Add parsing in `_primary` (search `def _primary`, `cinder/parser.py`,
add right after the `TokenType.FN` branch):
```python
        if token.type == TokenType.MATCH:
            return self._match_expr()
```
Then the three new parse methods (place near `_switch_statement`):
```python
    def _match_expr(self) -> Expr:
        match_token = self._advance()  # consume 'match'
        self._consume(TokenType.LPAREN, "'(' after 'match'")
        subject = self._assignment()
        self._consume(TokenType.RPAREN, "')' after match subject")
        self._consume(TokenType.LBRACE, "'{' after match subject")
        arms = [self._match_arm()]
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACE):
                break
            arms.append(self._match_arm())
        self._consume(TokenType.RBRACE, "'}' after match arms")
        return MatchExpr(subject, arms, match_token.line, match_token.column)

    def _match_arm(self) -> MatchArm:
        pattern = self._match_pattern()
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return MatchArm(pattern, body)

    def _match_pattern(self) -> "Expr | None":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER and token.lexeme == "_":
            self._advance()
            return None
        if token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column)
        if token.type == TokenType.TRUE:
            self._advance()
            return Literal(True, token.line, token.column)
        if token.type == TokenType.FALSE:
            self._advance()
            return Literal(False, token.line, token.column)
        if token.type == TokenType.NIL:
            self._advance()
            return Literal(None, token.line, token.column)
        raise ParseError(
            f"expected a literal or '_' in match pattern, found {self._describe(token)}",
            token.line,
            token.column,
        )
```
The arm body is parsed at `_ternary()` precedence — the same tier
`_map_pair`'s value and `_list_literal`'s elements already use — so a
bare `,` at that precedence still ends the arm, keeping the comma-
separated arm list unambiguous with no lookahead tricks needed. Each arm
carries exactly one pattern (no `1, 2 => ...` multi-value arms, unlike
`switch`'s `case v1, v2:`) — out of scope for this task, precisely
because arms are themselves comma-separated here (`switch` avoids that
ambiguity by having no arm separator at all, relying on the `case`/
`default` keyword to end a block-bodied case); adding multi-pattern arms
later needs a different separator (e.g. `|`) to stay unambiguous, a
natural follow-up.

`_match_pattern` special-cases a lone `_` identifier *before* falling
through to any general expression parsing, and deliberately does not
call `_primary`/`_ternary` at all for patterns (constructing `Literal`
nodes directly instead) — this sidesteps a real collision: `_primary`'s
existing single-identifier-arrow-function sugar (search `if self._peek_next().type == TokenType.FAT_ARROW`,
right after the `TokenType.IDENTIFIER` branch) means any bare identifier
immediately followed by `=>` parses as a `FnExpr`, so `_ => body` parsed
through the general expression grammar would silently become an arrow
function *value* used as a pattern (always failing to match, never
raising) instead of the wildcard. Checking for `_` directly, before ever
touching `_primary`, avoids this entirely; every other identifier in
pattern position (not just `_`) correctly stays a `ParseError` from
`_match_pattern`'s final `raise` branch, since only literals and `_` are
valid patterns in this first version.

Add evaluation in `evaluate` (search `if isinstance(expr, Ternary):`,
`cinder/interpreter.py`, add right after its `return` line):
```python
        if isinstance(expr, MatchExpr):
            return self._evaluate_match(expr, env)
```
Then the evaluator itself (place near `_evaluate_ternary`):
```python
    def _evaluate_match(self, expr: MatchExpr, env: Environment) -> object:
        subject = self.evaluate(expr.subject, env)
        for arm in expr.arms:
            if arm.pattern is None or values_equal(subject, self.evaluate(arm.pattern, env)):
                return self.evaluate(arm.body, env)
        raise CinderRuntimeError("no match arm matched value", expr.line, expr.column)
```

Acceptance criteria:
- `print(match (2) { 1 => "one", 2 => "two", _ => "other" });` prints
  `"two"`.
- `print(match (5) { 1 => "one", 2 => "two", _ => "other" });` prints
  `"other"` — the wildcard arm.
- `let x = match (true) { false => 0, true => 1 };` then `print(x);`
  prints `1` — usable as a value in a `let` initializer, confirming this
  is an expression, not a statement.
- `print(match ("b") { "a" => 1, "b" => 2, "c" => 3 });` prints `2` —
  string patterns.
- `print(match (1.5) { 1 => "int one", 1.5 => "float one-half", _ => "other" });`
  prints `"float one-half"` — float patterns, and confirms `1` (int) does
  not spuriously match `1.5` (float).
- `print(match (nil) { nil => "nothing", _ => "something" });` prints
  `"nothing"` — `nil` as a pattern.
- `print(match (3) { 1 => "one", 2 => "two" });` raises
  `CinderRuntimeError` matching `"no match arm matched value"` — no `_`
  wildcard present and no arm matched.
- `let double = x => x * 2; print(double(5));` prints `10` — ordinary
  arrow functions are unaffected by the new `_match_pattern` wildcard
  handling, since it only ever runs inside a `match` arm's pattern
  position.
- `let _ = 5; print(_);` prints `5` — a bare `_` as an ordinary
  identifier (outside match-pattern position) is still valid and
  unaffected.
- `print(match (1) { x => 1, _ => 2 });` raises `ParseError` matching
  `"expected a literal or '_' in match pattern, found ..."` — a bound
  identifier pattern (anything other than `_`) is out of scope for this
  first version.
- `print(match (1) { 1, 2 => "one or two", _ => "other" });` raises
  `ParseError` — multi-value arms are out of scope for this task (see
  above); confirm this fails cleanly (at the unexpected `,` after the
  first pattern's arm) rather than silently misparsing.
- `print(match (1) { });` raises `ParseError` — a match expression with
  zero arms (nothing before the immediate `}`) is invalid, since
  `_match_pattern` finds no valid pattern token there.
- Full test suite passes.

Likely files: `cinder/tokens.py` (`MATCH` token + keyword), `cinder/ast_nodes.py`
(`MatchArm`, `MatchExpr`), `cinder/parser.py` (`_primary`, `_match_expr`,
`_match_arm`, `_match_pattern`), `cinder/interpreter.py` (`evaluate`
dispatch, `_evaluate_match`), `tests/test_lexer.py` (add `match` keyword
lexing alongside the existing `switch` keyword test), `tests/test_parser.py`
(add a `class TestMatchExpression` mirroring `TestSwitchStatement`'s own
style, search that name), `tests/test_interpreter.py` (same, a `class
TestMatchExpression` mirroring `TestSwitchStatement`). Once merged,
`README.md`'s Features list and its "Status & roadmap" section need
updating to note a first, literal-only `match` expression landed, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing to note the
pattern-matching-beyond-destructuring arc has begun — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_prime` — the k-th prime number by position

Build: the breadth task after task 2's depth work (a `match` expression
with literal patterns and a `_` wildcard) per `PROJECT.md`'s
breadth-vs-depth policy. `is_prime`/`is_composite`/`is_semiprime`
(`cinder/builtins.py`) all test membership in various prime-adjacent
categories, and `prime_factors` lists an integer's own factors, but
nothing in Cinder answers the complementary "which prime" question:
given a 1-indexed position, what prime is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_prime(1));'
# -> CinderRuntimeError: undefined name 'nth_prime'
```

Add to `cinder/builtins.py`, registered right after `_is_prime` (search
`def _is_prime`, immediately before `_is_composite`):
```python
def _nth_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_prime", arguments, 1, line, column)
    value = _require_int("nth_prime", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_prime() requires a positive integer, domain error", line, column
        )
    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        is_prime = True
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return candidate
```
This mirrors `_is_circular_prime`'s own locally-scoped trial-division
style (search `def _is_circular_prime`) — a plain nested loop, not a
call out to `_is_prime` itself — rather than reusing `_is_prime`
directly, since `_is_prime` takes the CLI-facing `(arguments, line,
column)` shape, not a plain `int -> bool` one; every other builtin that
needs a bare primality check inline already makes this same choice.
`1`-indexed like ordinal position is described everywhere else in the
language, so `nth_prime(1) = 2` (no `0`th prime). A domain error (not a
count of `false`) for `value < 1` matches `collatz_length`'s own
convention for its own "not a valid input" case, since this is a
value-returning function, not a predicate — there is no sensible prime
to return for position `0` or a negative position, unlike the
figurate-number predicates' "closed domain, just answer false"
convention. Also register the new dict entry (search `"is_prime":
_is_prime,`, add `"nth_prime": _nth_prime,` directly after it).

Acceptance criteria:
- `nth_prime(1);` is `2`, `nth_prime(2);` is `3`, `nth_prime(3);` is `5`,
  `nth_prime(4);` is `7`, `nth_prime(5);` is `11` — the first five
  primes by position.
- `nth_prime(10);` is `29`.
- `nth_prime(100);` is `541` — confirms the check holds well beyond
  small brute-forced cases.
- `nth_prime(0);` and `nth_prime(-3);` both raise `CinderRuntimeError`
  matching `"nth_prime() requires a positive integer, domain error"`.
- `nth_prime(2.0);` raises `CinderRuntimeError` matching `"nth_prime()
  requires an int, got float"`.
- `nth_prime(true);` raises `CinderRuntimeError` matching `"nth_prime()
  requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_prime`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsPrime`, search that
name, for the arity/type-error test shapes — the domain-error test
shape instead mirrors `class TestCollatzLength`, search that name,
since `nth_prime` raises rather than returning `false` for an invalid
position). Once merged, `README.md`'s Builtins bullet needs `nth_prime`
added near `is_prime`/`prime_factors`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Standard library: `nth_fibonacci` — the k-th Fibonacci number by position

Build: the breadth task restocking the backlog after a list pattern
nested inside a map pattern landed via PR #299, per `PROJECT.md`'s
breadth-vs-depth policy (task 2 above is this pass's depth task;
alternation resumes with breadth here). `is_fibonacci`/
`is_lucas_number` (`cinder/builtins.py`) both test membership in their
respective sequences, and `nth_prime` (task 3 above) already queues the
same "which position" question for primes, but nothing in Cinder
answers the complementary question for Fibonacci numbers: given a
1-indexed position, what value is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_fibonacci(10));'
# -> CinderRuntimeError: undefined name 'nth_fibonacci'
```

Add to `cinder/builtins.py`, registered right after `_is_lucas_number`
(search `def _is_lucas_number`, immediately before `_is_happy_number`):
```python
def _nth_fibonacci(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_fibonacci", arguments, 1, line, column)
    value = _require_int("nth_fibonacci", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_fibonacci() requires a positive integer, domain error", line, column
        )
    previous, current = 0, 1
    for _ in range(value - 1):
        previous, current = current, previous + current
    return current
```
This mirrors `_is_lucas_number`'s own generate-and-track loop style — a
plain iterative walk up the recurrence, not a closed form — deliberately
avoiding Binet's formula (`(phi**k - psi**k) / sqrt(5)`), which relies
on irrational `sqrt(5)` and loses exact-integer precision for large `k`
under floating point; the iterative walk stays exact at any size, same
tradeoff `is_fibonacci`'s own closed-form membership check avoids by
using `math.isqrt` instead of a literal square root. `1`-indexed like
`nth_prime`'s own convention, so `nth_fibonacci(1) = 1` and
`nth_fibonacci(2) = 1` (the sequence's two seed values), not `nth_fibonacci(1) = 0`.
A domain error (not a sentinel value) for `value < 1` matches
`nth_prime`'s own convention for its own "not a valid input" case, since
this is a value-returning function, not a predicate — there is no
sensible Fibonacci number to return for position `0` or a negative
position. Also register the new dict entry (search `"is_lucas_number":
_is_lucas_number,`, add `"nth_fibonacci": _nth_fibonacci,` directly
after it).

Acceptance criteria:
- `nth_fibonacci(1);` is `1`, `nth_fibonacci(2);` is `1`,
  `nth_fibonacci(3);` is `2`, `nth_fibonacci(4);` is `3`,
  `nth_fibonacci(5);` is `5` — the first five Fibonacci numbers by
  position.
- `nth_fibonacci(10);` is `55`.
- `nth_fibonacci(20);` is `6765` — confirms the check holds well beyond
  small brute-forced cases.
- `nth_fibonacci(0);` and `nth_fibonacci(-3);` both raise
  `CinderRuntimeError` matching `"nth_fibonacci() requires a positive
  integer, domain error"`.
- `nth_fibonacci(2.0);` raises `CinderRuntimeError` matching
  `"nth_fibonacci() requires an int, got float"`.
- `nth_fibonacci(true);` raises `CinderRuntimeError` matching
  `"nth_fibonacci() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_lucas_number`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsFibonacci`, search that
name, for the arity/type-error test shapes — the domain-error test
shape instead mirrors `class TestCollatzLength`, search that name,
since `nth_fibonacci` raises rather than returning `false` for an
invalid position). Once merged, `README.md`'s Builtins bullet needs
`nth_fibonacci` added near `is_fibonacci`/`is_lucas_number`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Language: bare comma multi-target assignment (`a, b = 1, 2;`, swap idiom `a, b = b, a;`)

Build: the depth task restocking the backlog back to 6 tasks now that
`is_heptagonal` landed via PR #300, per `PROJECT.md`'s breadth-vs-depth
policy (tasks 3 and 4 above are both breadth; alternation resumes with
depth here). Cinder already has bracketed list-destructuring assignment
(`[a, b] = expr;`, `cinder/parser.py`'s `_assignment`, the
`isinstance(expr, ListLiteral)` branch) and, since PR #289, allows
comma-separated *independent* statements at expression-statement
position (`a = 1, b = 2;`, `f(), g();`, via `_expr_statement`'s
`DeclSeq` wrapping). Bare comma multi-target assignment — the
unbracketed sugar Python-family languages use for the swap idiom — has
never been added, and the gap is worse than a missing feature: it
*silently misbehaves* rather than raising, because `_expr_statement`'s
existing comma-loop happily reinterprets `a, b = 1, 2;` as three
unrelated statements. Verify the gap:
```sh
python3 -m cinder.cli eval 'let a = 0; let b = 0; a, b = 1, 2; print(a); print(b);'
# -> 0
#    1
# (wrong: should print 1 then 2 — instead `a, b = 1, 2;` silently parses
# as three independent ExprStmts: `a` (no-op), `b = 1` (assignment,
# `2` discarded as its own no-op statement); no error at all)
python3 -m cinder.cli eval 'let a = 1; let b = 2; a, b = b, a; print(a); print(b);'
# -> 1
#    2
# (wrong: should print 2 then 1, the swap — instead it parses as `a`
# (no-op), `b = b` (self-assign), `a` (no-op); nothing swaps)
```

Add a new speculative-parse helper, `_try_multi_assign_statement`, called
from `_expr_statement` (search `def _expr_statement`, `cinder/parser.py`)
before its existing `first = self._assignment()` line:
```python
    def _expr_statement(self) -> Stmt:
        multi_assign = self._try_multi_assign_statement()
        if multi_assign is not None:
            return multi_assign
        first = self._assignment()
        statements = [ExprStmt(first)]
        ...
```
Place the new method near `_try_map_destructure_assign_statement` (search
that name, `cinder/parser.py`), mirroring its speculative-parse-with-
backtrack shape (save `self.pos`, attempt a parse, reset and return `None`
on any `ParseError` so the caller falls through unchanged):
```python
    def _try_multi_assign_statement(self) -> "Stmt | None":
        """Speculatively parses bare comma-separated multi-target
        assignment `a, b = 1, 2;` (including the swap idiom
        `a, b = b, a;`), tried before `_expr_statement`'s existing
        single-target/comma-separated-statements parse. Desugars to the
        same `DestructureAssign` node the bracketed form `[a, b] = expr;`
        already produces (`_assignment`'s `isinstance(expr, ListLiteral)`
        branch), reusing its runtime semantics for free: RHS evaluated
        once, length-checked, assigned left to right — so the RHS is
        evaluated in full (both `b` and `a` in the swap case) before any
        target is written, which is what makes the swap idiom correct.
        Returns `None` on any shape mismatch — fewer than two
        comma-separated identifiers, or no top-level `=` following them —
        leaving `self.pos` untouched so the caller's own `_assignment()`-
        based parse runs unchanged; this keeps `a = 1, 2;` (single target,
        PR #289's DeclSeq form) and `a, b;` (two independent identifier
        statements) parsing exactly as before, since both fail this
        speculative parse (too few names, or no top-level `=`)."""
        start = self.pos
        try:
            names = [self._consume(TokenType.IDENTIFIER, "identifier")]
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._consume(TokenType.IDENTIFIER, "identifier"))
            if len(names) < 2 or not self._check(TokenType.EQ):
                self.pos = start
                return None
            eq_token = self._advance()
            values = [self._assignment()]
            while self._check(TokenType.COMMA):
                self._advance()
                values.append(self._assignment())
        except ParseError:
            self.pos = start
            return None
        self._consume(TokenType.SEMICOLON, "';' after multi-target assignment")
        pattern_names = [(name.lexeme, None) for name in names]
        value = values[0] if len(values) == 1 else ListLiteral(
            values, eq_token.line, eq_token.column
        )
        return ExprStmt(
            DestructureAssign(
                pattern_names, None, value, eq_token.line, eq_token.column, is_map=False
            )
        )
```
The `len(values) == 1` branch matters beyond the literal cases above: it
lets a single RHS expression that itself evaluates to a list (e.g. a
function call) unpack directly — `a, b = pair();` behaves exactly like
`[a, b] = pair();` — rather than wrapping it in a synthetic one-element
list that would only ever fail the length check. Multiple comma-
separated RHS values (`1, 2` or `b, a`) *do* get wrapped in a
`ListLiteral`, since Cinder — unlike Python — has no bare tuple literal;
this is the moral equivalent of Python constructing an implicit tuple
from `a, b = 1, 2`'s right-hand side. No interpreter changes are needed:
`_evaluate_destructure_assign` and `_bind_list_destructure`
(`cinder/interpreter.py`) already evaluate `expr.value` once, require a
list, and raise the existing `"destructuring pattern expects N elements,
got M"` `CinderRuntimeError` on a length mismatch — this task is parser-
only, reusing that machinery unchanged. Out of scope for this first
version, all left as natural follow-ups: a trailing `...rest` element, a
trailing comma before `=`, and nested bracket/brace targets mixed into
the bare form (`a, [b, c] = ...`) — the bracketed form already covers
that need on its own.

Acceptance criteria:
- `let a = 0; let b = 0; a, b = 1, 2; print(a); print(b);` prints `1`
  then `2`.
- `let a = 1; let b = 2; a, b = b, a; print(a); print(b);` prints `2`
  then `1` — the swap idiom, confirming the RHS is fully evaluated
  before either target is written.
- `let a = 0; let b = 0; let c = 0; a, b, c = 1, 2, 3; print(a); print(b); print(c);`
  prints `1`, `2`, `3` — three targets, not just two.
- `fn pair() { return [1, 2]; } let a = 0; let b = 0; a, b = pair(); print(a); print(b);`
  prints `1` then `2` — a single RHS expression that evaluates to a list
  unpacks directly, exactly like `[a, b] = pair();` already does.
- `let a = 0; let b = 0; a, b = 1, 2, 3;` raises `CinderRuntimeError`
  matching `"destructuring pattern expects 2 elements, got 3"` — reusing
  the existing destructuring length-check error verbatim.
- `let a = 0; a = 1, 2;` is unchanged: still parses as PR #289's
  `DeclSeq` of two `ExprStmt`s (`a = 1` then the no-op `2`), `print(a);`
  afterward prints `1` — single-target assignment followed by a
  comma-separated statement is not reinterpreted as multi-assign.
- `let a = 1; let b = 2; a, b;` is unchanged: still two independent
  `ExprStmt`s (bare identifier reads, no-ops), `print(a); print(b);`
  afterward prints `1` then `2` — untouched.
- `f(), g();` (two independent call-expression statements) is unchanged
  — still parses and runs as PR #289 left it, confirming the new
  speculative parse backs out cleanly on any non-identifier-list shape.
- `let a = 0; a, 5 = 1, 2;` raises `ParseError` — a non-identifier in
  target position falls all the way through to the existing "invalid
  assignment target"-style failure once every fallback is exhausted,
  not a silent misparse.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_expr_statement`,
`_try_multi_assign_statement`, placed near
`_try_map_destructure_assign_statement`), `tests/test_parser.py` (add
tests near `test_expr_statement_comma_separated_becomes_decl_seq`,
search that name, and alongside `class TestDestructureAssign`'s parser-
level coverage), `tests/test_interpreter.py` (extend `class
TestDestructureAssign`, search that name, with the swap-idiom and
`pair()`-unpacking end-to-end cases). Once merged, `README.md`'s
"Variables & scope" bullet (the existing `[a, b] = expr;` plain-
assignment mention) needs a note that the bare form is now supported
too, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" bullet needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
