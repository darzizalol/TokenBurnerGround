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

## 1. Language: multi-value literal patterns in match arms (`1, 2 => "small"`)

Build: restocking the backlog back to 6 tasks now that `nth_fibonacci`
landed via PR #306, per `PROJECT.md`'s breadth-vs-depth policy
(`nth_fibonacci` was breadth; alternation restocks with depth here — the
queue was 2-depth/3-breadth after the last pass, and a depth restock
keeps that ratio from drifting further). PR #304's `match` expression
scoped its patterns down to a single literal (or `_`) per arm;
`tests/test_parser.py`'s own `test_match_multi_value_arm_raises` (search
that name) already documents today's behavior as a `ParseError`, sitting
right next to `test_match_bound_identifier_pattern_raises` (task 2's own
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

## 2. Standard library: `nth_triangular` — the k-th triangular number by position

Build: restocking the backlog back to 6 tasks now that bare comma
multi-target assignment landed via PR #307, per `PROJECT.md`'s
breadth-vs-depth policy (that task was depth; alternation restocks with
breadth here, per the explicit instruction the previous grooming pass
left in `PROJECT.md`'s "Current frontier" note). `is_triangular`
(`cinder/builtins.py`) tests triangular-number membership, and
`nth_prime`/`nth_fibonacci`/`nth_lucas` already answer the same "which
position" question for their own sequences, but nothing in Cinder
answers the complementary question for triangular numbers: given a
1-indexed position, what value is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_triangular(5));'
# -> <eval>:1:7: undefined name 'nth_triangular'
```

Add to `cinder/builtins.py`, registered right after `_is_octagonal`
(search `def _is_octagonal`, which itself sits directly after
`_is_heptagonal` and immediately before `_is_prime` — register
`_nth_triangular` between `_is_octagonal` and `_is_prime`):
```python
def _nth_triangular(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_triangular", arguments, 1, line, column)
    value = _require_int("nth_triangular", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_triangular() requires a positive integer, domain error", line, column
        )
    return value * (value + 1) // 2
```
Unlike `nth_fibonacci`/`nth_lucas`, which iterate a recurrence, or
`nth_prime`, which counts up while sieving, triangular numbers have an
exact closed form (`T(n) = n * (n + 1) / 2`), so `nth_triangular` needs
no loop — mirroring `is_triangular`'s own closed-form check
(`8 * value + 1` a perfect square) rather than the iterative pattern of
its sequence-position siblings. Mind the indexing subtlety this shares
with `nth_lucas`: `is_triangular(0)` is `true` (`T(0) = 0` is a
degenerate member of the membership test — see
`test_is_triangular_degenerate_and_first_cases` in
`tests/test_builtins.py`), but `nth_triangular(1)` must still be `1`,
not `0` — position `1` is the first *positive* triangular number, the
same convention `nth_fibonacci(1)` already uses (`1`, not the `F(0) = 0`
seed, even though `is_fibonacci(0)` is also `true`). Getting this wrong
(returning `0` for position `1`, or starting the closed form at `n = 0`)
would silently desynchronize `nth_triangular` from every other `nth_*`
builtin's shared "position `1` is the first positive term" convention —
verified directly in the acceptance criteria below. A domain error (not
a sentinel value) for `value < 1` matches `nth_prime`/`nth_fibonacci`/
`nth_lucas`'s own convention for their own "not a valid position" case.
Also register the new dict entry (search `"is_octagonal":
_is_octagonal,`, add `"nth_triangular": _nth_triangular,` directly
after it).

Acceptance criteria:
- `nth_triangular(1);` is `1`, `nth_triangular(2);` is `3`,
  `nth_triangular(3);` is `6`, `nth_triangular(4);` is `10`,
  `nth_triangular(5);` is `15` — the first five (positive) triangular
  numbers by this convention.
- `nth_triangular(10);` is `55`.
- `nth_triangular(100);` is `5050` — confirms the closed form holds well
  beyond small brute-forced cases.
- For each `n` in `1..100`, `is_triangular(nth_triangular(n));` is
  `true` — `nth_triangular` and `is_triangular` agree on the same
  sequence.
- `nth_triangular(0);` and `nth_triangular(-3);` both raise
  `CinderRuntimeError` matching `"nth_triangular() requires a positive
  integer, domain error"` — position `0` is invalid input, it does not
  return the degenerate `T(0) = 0` seed that `is_triangular(0)` accepts
  as a member.
- `nth_triangular(2.0);` raises `CinderRuntimeError` matching
  `"nth_triangular() requires an int, got float"`.
- `nth_triangular(true);` raises `CinderRuntimeError` matching
  `"nth_triangular() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_heptagonal`/
`is_octagonal`, see current line numbers — shift if earlier tasks this
cycle land first), `tests/test_builtins.py` (model on `class
TestNthFibonacci`, search that name, for both the sequence-value test
shapes and the arity/type-error test shapes — the domain-error test
shape also mirrors `class TestNthPrime`, search that name). Once
merged, `README.md`'s Builtins bullet needs `nth_triangular` added near
`is_triangular`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 3. Language: guards in `match` arms (`n if n > 0 => "positive"`)

Build: restocking the backlog back to 6 tasks now that `is_octagonal`
landed via PR #308, per `PROJECT.md`'s breadth-vs-depth policy
(`is_octagonal` was breadth; alternation restocks with depth here — the
queue was 3-breadth/2-depth after task 4 (`nth_triangular`) was added,
so this depth restock brings it to 3-breadth/3-depth, exact parity).
The pattern-matching arc opened by PR #304 already has two more depth
tasks queued ahead of this one (task 2, bound-identifier patterns, and
task 3, multi-value literal patterns) — guards are the third natural
follow-up `PROJECT.md`'s "Current frontier" note calls out
(nested/destructuring patterns are the remaining one, left for a future
pass). A guard is an extra boolean condition on an arm, evaluated only
once the arm's pattern already matches, letting one pattern split into
several arms by an arbitrary expression instead of only by literal
equality — every pattern-matching language this feature is modeled on
(Rust's `n if n > 0 => ...`, Python's `case n if n > 0:`) has this.
Verify the gap against today's codebase:
```sh
python3 -m cinder.cli eval 'let x = 5; print(match (0) { 0 if x > 3 => "big-zero", _ => "other" });'
# -> <eval>:1:32: expected '=>' after match pattern, found 'if'
```

**Ordering note:** this is task 5, behind tasks 1-4 above, so by the
time it is claimed, tasks 2 (bound-identifier patterns) and 3
(multi-value literal patterns) will most likely have already landed and
changed the exact shape of `MatchArm`, `_match_pattern`, and
`_match_arm` shown below — task 4 (`nth_triangular`) faced the same kind
of ordering uncertainty about whether `is_octagonal` would land first
and resolved it by adapting to whatever the merged code actually looked
like; do the same here. The code below is grounded in **today's** actual
code (verified by reading
`cinder/ast_nodes.py`/`cinder/parser.py`/`cinder/interpreter.py`
directly) so the *principle* is exact even if the exact diff has
shifted: parse an optional `if <expr>` immediately after the pattern
(and after any binding, if task 2 landed) and before the `=>`; store it
as one more field on `MatchArm`; at eval time, only treat the arm as
matching if the pattern already matched (or is a wildcard) **and** the
guard (if present) evaluates truthy — a false guard falls through to
the next arm exactly as a non-matching pattern would, it does not raise
or stop the search. If task 2 landed first and introduced a
per-arm child scope for the bound identifier, evaluate the guard in
that same child scope (so the guard can see the binding), not the outer
`env` — mirror whatever scope `arm.body` itself is evaluated in.

Today's starting point, `MatchArm` (`cinder/ast_nodes.py`, search
`class MatchArm`):
```python
@dataclass(frozen=True)
class MatchArm:
    """`pattern` is `None` for the `_` wildcard (matches unconditionally,
    evaluating no expression); otherwise a `Literal` node compared against
    the match subject via `values_equal`, the same helper `SwitchStmt`
    case-matching already uses. `guard`, when not `None`, is an extra
    condition evaluated only after the pattern itself already matches (or
    unconditionally for a wildcard arm) — if the guard evaluates falsy, the
    arm is skipped and matching continues with the next arm, exactly as if
    this arm's pattern had not matched at all."""

    pattern: "Expr | None"
    body: "Expr"
    guard: "Expr | None" = None
```
(If task 2 already added a `binding: "str | None" = None` field, add
`guard` as a new trailing field after it instead, and fold the guard
sentence above into that field's own docstring paragraph rather than
replacing it.)

Today's `_match_arm`/`_match_pattern` (`cinder/parser.py`, search `def
_match_arm`):
```python
    def _match_arm(self) -> MatchArm:
        pattern = self._match_pattern()
        guard = None
        if self._check(TokenType.IF):
            self._advance()
            guard = self._ternary()
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return MatchArm(pattern, body, guard)
```
`TokenType.IF` is already used the same way — an optional trailing
condition parsed with `self._ternary()` — by `_comprehension_clause`
(search `def _comprehension_clause`, the `if self._check(TokenType.IF)`
block), so this mirrors an existing, working pattern in this same
parser rather than inventing new lookahead machinery. If task 3 (which
turns `_match_arm` into a comma-collecting, multi-pattern-returning
method) landed first, parse the `if <expr>` once, after the whole
comma-separated pattern list and before `=>`, and apply the same
`guard` value to every desugared `MatchArm` produced from that arm
(they share one guard, the same way they already share one `body`).

Today's `_evaluate_match` (`cinder/interpreter.py`, search `def
_evaluate_match`):
```python
    def _evaluate_match(self, expr: MatchExpr, env: Environment) -> object:
        subject = self.evaluate(expr.subject, env)
        for arm in expr.arms:
            if arm.pattern is None or values_equal(subject, self.evaluate(arm.pattern, env)):
                if arm.guard is not None and not is_truthy(self.evaluate(arm.guard, env)):
                    continue
                return self.evaluate(arm.body, env)
        raise CinderRuntimeError("no match arm matched value", expr.line, expr.column)
```
`is_truthy` (module-level in `cinder/interpreter.py`, search `def
is_truthy`) is the same helper `if`/`while`/`and`/`or` already use, so
guard truthiness follows Cinder's one fixed truthiness rule (`false`
and `nil` falsy, everything else — including `0` and `""` — truthy)
with no special case. The guard is evaluated **after** confirming the
pattern already matched, never before — this ordering is load-bearing,
not incidental: it lets a guard reference values that would be
meaningless or erroring to evaluate against a non-matching subject
(see the short-circuit acceptance case below), and it means a guard
never runs at all for an arm whose pattern was never going to match in
the first place.

Acceptance criteria:
- `let x = 5; print(match (0) { 0 if x > 3 => "big-zero", 0 => "zero", _ => "other" });`
  is `"big-zero"` — guard true, arm matches.
- `let x = 1; print(match (0) { 0 if x > 3 => "big-zero", 0 => "zero", _ => "other" });`
  is `"zero"` — guard false, falls through to a later arm with the same
  literal pattern but no guard.
- `match (5) { _ if false => "never", _ => "fallback" };` is
  `"fallback"` — a wildcard arm with a false guard is skipped even
  though a bare wildcard would otherwise always match; matching
  continues to the next arm.
- `match (5) { _ => "always" };` (no guard at all) is still `"always"`
  — unguarded arms are unaffected by this change.
- `match (1) { 0 if undefined_name => "x", _ => "y" };` is `"y"` and
  does **not** raise a runtime error for the undefined name — confirms
  the guard on the `0` arm is never evaluated at all, because the
  pattern (`0`) never matched the subject (`1`) in the first place; the
  short-circuit order (pattern first, guard second) is load-bearing, not
  incidental.
- `match (7) { n if n > 100 => "huge", n if n > 3 => "medium" };` raising
  or matching correctly is **not** in scope unless task 2 has already
  landed (bound-identifier patterns) — if it has not, write this
  acceptance case instead against literal patterns only, e.g. `match (7)
  { 7 if false => "a", 7 if true => "b" };` is `"b"`, two guarded arms
  sharing one literal pattern, only the second's guard is true.
- `tests/test_parser.py`'s `shape()` helper's `MatchExpr` branch (search
  `isinstance(node, MatchExpr)`) needs its per-arm tuple extended to
  include the guard shape (`shape(arm.guard) if arm.guard is not None
  else None`), and every existing expected-shape tuple in `class
  TestMatchExpression` (search that name, in both
  `tests/test_parser.py` and this file's own new tests) updated to match
  the new field count — including a `None` for every arm that has no
  guard, exactly as task 2's own note about adding a trailing `None` for
  `binding` describes for that field.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`, `MatchExpr`
docstrings), `cinder/parser.py` (`_match_arm`), `cinder/interpreter.py`
(`_evaluate_match`), `tests/test_parser.py` (`shape()` helper's
`MatchExpr` branch and `class TestMatchExpression`, search that name),
`tests/test_interpreter.py` (extend `class TestMatchExpression`, search
that name, with the guard end-to-end cases above). Once merged,
`README.md`'s `match` expression bullet needs a guard example added,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" bullet needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `nth_catalan` — the k-th Catalan number by position

Build: restocking the backlog back to 6 tasks now that `binomial` landed
via PR #309, per `PROJECT.md`'s breadth-vs-depth policy (`binomial` was
breadth; alternation restocks with breadth again here — landing
`binomial` dropped the queue to 2-breadth/3-depth (`nth_lucas`,
`nth_triangular` vs. tasks 2, 3, 5 above), and `PROJECT.md`'s own
"Current frontier" note from the previous grooming pass explicitly said
the next pass should restock with breadth to restore parity). The
Catalan numbers are the natural next combinatorics builtin now that
`binomial` exists: `C(n) = binomial(2n, n) / (n + 1)`, and nothing in
Cinder can compute them yet. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_catalan(5));'
# -> <eval>:1:7: undefined name 'nth_catalan'
```

Add to `cinder/builtins.py`, registered right after `_binomial` (search
`def _binomial`, immediately before `_sum`):
```python
def _nth_catalan(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_catalan", arguments, 1, line, column)
    value = _require_int("nth_catalan", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_catalan() requires a positive integer, domain error", line, column
        )
    index = value - 1
    return math.comb(2 * index, index) // (index + 1)
```
Mind the indexing subtlety this shares with `nth_triangular`/`nth_lucas`:
the standard mathematical definition is 0-indexed (`C(0) = 1, C(1) = 1,
C(2) = 2, ...`), but every `nth_*` builtin in this cluster
(`nth_fibonacci`, `nth_prime`, `nth_lucas`, `nth_triangular`) treats
position `1` as the first term of the sequence, not position `0` — so
`nth_catalan(1)` must return `C(0) = 1` (the sequence's first term under
this convention), `nth_catalan(2)` must return `C(1) = 1` (the second
term, also `1` — Catalan numbers happen to repeat once at the start),
and so on, with `index = value - 1` doing the conversion from Cinder's
1-indexed position to the closed form's 0-indexed `n`. Getting this
wrong (using `value` directly as `n` instead of `value - 1`) would
silently shift every result by one position relative to the sequence's
well-known values — verified directly in the acceptance criteria below.
`math.comb`, not a hand-rolled loop, matches `_binomial`'s own
implementation choice (search `def _binomial`) — this builtin is a thin
composition of the same primitive, not a new algorithm. A domain error
(not a sentinel value) for `value < 1` matches every other `nth_*`
builtin's own convention for their own "not a valid position" case.
Also register the new dict entry (search `"binomial": _binomial,`, add
`"nth_catalan": _nth_catalan,` directly after it).

Acceptance criteria:
- `nth_catalan(1);` is `1`, `nth_catalan(2);` is `1`, `nth_catalan(3);`
  is `2`, `nth_catalan(4);` is `5`, `nth_catalan(5);` is `14`,
  `nth_catalan(6);` is `42` — the first six Catalan numbers by this
  cluster's 1-indexed convention (note positions 1 and 2 are both `1`,
  which is correct — the sequence itself repeats there, not an
  off-by-one bug).
- `nth_catalan(10);` is `4862`.
- `nth_catalan(15);` is `2674440` — confirms the closed form holds well
  beyond small brute-forced cases.
- `nth_catalan(0);` and `nth_catalan(-3);` both raise
  `CinderRuntimeError` matching `"nth_catalan() requires a positive
  integer, domain error"`.
- `nth_catalan(2.0);` raises `CinderRuntimeError` matching
  `"nth_catalan() requires an int, got float"`.
- `nth_catalan(true);` raises `CinderRuntimeError` matching
  `"nth_catalan() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `binomial`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestBinomial` and `class
TestNthFibonacci`, search those names, for both the sequence-value test
shapes and the arity/type-error test shapes — the domain-error test
shape mirrors `class TestNthFibonacci`'s own zero/negative cases). Once
merged, `README.md`'s Builtins bullet needs `nth_catalan` added near
`binomial`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
