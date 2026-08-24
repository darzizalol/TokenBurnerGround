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

## 1. Language: multi-value literal patterns in match arms (`1, 2 => "small"`) [claimed 2026-08-24T14:20:27Z]

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

**Ordering note (updated during grooming, 2026-08-24):** bound-identifier
patterns (PR #311) landed since this task was first written, so
`_match_pattern` today returns a `(pattern, binding)` tuple, not a bare
pattern — the sketch below is grounded in the actual current code, not
the pre-#311 version. Change `_match_arm` (search `def _match_arm`,
`cinder/parser.py`) to collect a comma-separated list of `(pattern,
binding)` entries before `=>`, then desugar into one flat `MatchArm` per
entry, all sharing the same `body` node — this needs no `ast_nodes.py`
or `cinder/interpreter.py` changes at all, since `MatchArm` and
`_evaluate_match` (search `def _evaluate_match`) already try arms one at
a time in source order and stop at the first match; N arms with
identical bodies behave exactly like one arm with N patterns would, for
free. A multi-value list mixing in the `_` wildcard *or* a
bound-identifier pattern is rejected the same way — both surface as
`pattern is None` from `_match_pattern`, so the existing wildcard check
already covers bound identifiers too, for free:
```python
    def _match_arm(self) -> "list[MatchArm]":
        first_token = self._peek()
        entries = [self._match_pattern()]
        while self._check(TokenType.COMMA):
            self._advance()
            entries.append(self._match_pattern())
        if len(entries) > 1 and any(pattern is None for pattern, _ in entries):
            raise ParseError(
                "'_' or a bound identifier cannot be combined with other "
                "patterns in a match arm",
                first_token.line,
                first_token.column,
            )
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return [MatchArm(pattern, body, binding) for pattern, binding in entries]
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
  `tests/test_parser.py`, whose `shape()` helper already renders each arm
  as a 3-tuple `(pattern_shape_or_None, body_shape, binding)` per the
  bound-identifier task) desugars to three flat arms, the same `body`
  shape repeated for the two literals that share it: `[(("Literal", 1),
  ("Literal", "ab"), None), (("Literal", 2), ("Literal", "ab"), None),
  (None, ("Literal", "c"), None)]` — confirms the desugaring, not just
  the end-to-end value.
- `match (1) { 1, _ => "x" };` and `match (1) { _, 1 => "x" };` both
  raise `ParseError` matching `"'_' or a bound identifier cannot be
  combined with other patterns in a match arm"`.
- `match (1) { 1, n => "x" };` also raises that same `ParseError` — a
  bound-identifier pattern (any non-`_` identifier) is rejected from a
  multi-value list exactly like `_` is, since both desugar to `pattern is
  None` from `_match_pattern` and share one rejection check.
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

## 5. Language: flat list patterns in `match` arms (`[a, b] => a + b`)

Build: restocking the backlog back to 6 tasks now that `nth_lucas`
(breadth, PR #310) and bound-identifier patterns (depth, PR #311) both
landed since the last grooming pass, dropping the queue from 6 to 4
(tasks 1-4 above). This restock adds one depth task and one breadth
task (task 6, below) to bring it back to 6 at 3-breadth/3-depth parity,
continuing the alternation this task 5 (depth) follows task 4
(breadth). This closes the one follow-up `PROJECT.md`'s "Current
frontier" note has flagged but never queued since the pattern-matching
arc opened with PR #304: "Nested/destructuring patterns inside match
arms remain the one follow-up not yet queued." Scoped down from that
open-ended description to something one session can finish: **flat**
list patterns only — `[a, b]` binds each element of a same-length list
subject to a name (or discards it with `_`), no nesting, no literal
sub-patterns, no rest/spread. Cinder's existing `let [a, b] = list;`
destructuring (`cinder/parser.py`'s `_destructure_list_pattern`,
`cinder/interpreter.py`'s `_bind_list_destructure`) already supports far
more (nested patterns, rest capture, map patterns) — this task
deliberately does not reuse that machinery or match its full power, since
match arms need pattern *testing* (does this list have this shape at
all, falling through to the next arm if not) rather than destructuring's
unconditional *binding* (raise if the shape doesn't fit). Nested list
patterns, literal elements inside a pattern (`[0, b] => ...`), and rest
capture (`[a, ...rest] => ...`) are explicitly out of scope for this
task — real gaps, left for a future grooming pass once this flat form is
solid. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ([1, 2]) { [a, b] => a + b, _ => 0 });'
# -> <eval>:1:20: expected a literal, identifier, or '_' in match pattern, found '['
```

**Ordering note:** tasks 1 (multi-value patterns) and 3 (guards) are
still ahead of this in the queue and may land first, changing
`MatchArm`'s exact field list and `_match_arm`'s exact shape — adapt to
whatever the merged code actually looks like, the same way task 4
(`nth_triangular`) adapted to `is_octagonal` landing first. The sketch
below is grounded in **today's** actual code (verified by reading
`cinder/ast_nodes.py`/`cinder/parser.py`/`cinder/interpreter.py`
directly, post-#311, pre-#(task 1)/#(task 3)), so the *principle* is
exact even if the exact diff has shifted: detect a leading `[` in
`_match_arm` before falling into the existing literal/wildcard/
bound-identifier path, parse a flat name list, and store it as one more
field on `MatchArm` that the existing literal-pattern and
bound-identifier fields stay `None` for (list patterns are a third,
mutually-exclusive pattern kind, not a combination of the other two).

Today's `MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) —
add a fourth field:
```python
    pattern: "Expr | None"
    body: "Expr"
    binding: "str | None" = None
    list_pattern: "list | None" = None  # list[str | None]; None = not a list pattern
```

Today's `_match_arm`/`_match_pattern` (`cinder/parser.py`, search `def
_match_arm`):
```python
    def _match_arm(self) -> MatchArm:
        if self._check(TokenType.LBRACKET):
            list_pattern = self._match_list_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return MatchArm(None, body, None, list_pattern)
        pattern, binding = self._match_pattern()
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return MatchArm(pattern, body, binding)

    def _match_list_pattern(self) -> "list[str | None]":
        self._advance()  # consume '['
        names: "list[str | None]" = []
        if not self._check(TokenType.RBRACKET):
            names.append(self._match_list_pattern_name())
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._match_list_pattern_name())
        self._consume(TokenType.RBRACKET, "']' after list pattern")
        return names

    def _match_list_pattern_name(self) -> "str | None":
        token = self._peek()
        if token.type != TokenType.IDENTIFIER:
            raise ParseError(
                f"expected an identifier or '_' inside list pattern, "
                f"found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._advance()
        return None if token.lexeme == "_" else token.lexeme
```
`[]` (empty brackets) is a valid pattern — `names` stays `[]`, matching
only a same-length (zero-length) list subject; the `if not
self._check(RBRACKET)` guard mirrors how argument lists and other
comma-separated forms already handle the empty case elsewhere in this
parser.

Today's `_evaluate_match` (`cinder/interpreter.py`, search `def
_evaluate_match`) needs a new branch checked first, since a list pattern
is a shape test rather than a `values_equal` comparison:
```python
    def _evaluate_match(self, expr: MatchExpr, env: Environment) -> object:
        subject = self.evaluate(expr.subject, env)
        for arm in expr.arms:
            if arm.list_pattern is not None:
                if not isinstance(subject, list) or len(subject) != len(arm.list_pattern):
                    continue
                arm_env = Environment(env)
                for name, item in zip(arm.list_pattern, subject):
                    if name is not None:
                        arm_env.define(name, item)
                return self.evaluate(arm.body, arm_env)
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
A non-list subject, or a list of the wrong length, does not raise —
it simply fails to match this arm and falls through to the next one,
`continue`ing the loop exactly like a non-equal literal pattern already
does; this keeps list patterns consistent with every other pattern
kind's "no match here, try the next arm" behavior rather than
introducing a new kind of failure mode. The child scope
(`Environment(env)`) mirrors bound-identifier's own child-scope pattern
directly above it (and `_execute_try`'s `catch_env`) — bindings live
only for `arm.body`'s evaluation and do not leak into or shadow `env`.
A repeated name in one pattern (`[a, a] => a`) is not rejected: `zip`
binds left to right and `Environment.define` silently overwrites, so
the later position wins — no special-case duplicate-name detection,
matching this task's "flat and simple" scope.

Acceptance criteria:
- `match ([1, 2]) { [a, b] => a + b, _ => 0 };` is `3`.
- `match ([1]) { [a, b] => a + b, [a] => a, _ => 0 };` is `1` — a
  length-2 pattern that doesn't fit falls through to a length-1 pattern
  that does, not an error.
- `match ([1, 2, 3]) { [a, b] => a + b, _ => "no match" };` is
  `"no match"` — a length-3 subject doesn't fit a length-2 pattern,
  falls through to `_`.
- `match (5) { [a, b] => a + b, _ => "not a list" };` is `"not a list"`
  — a non-list subject fails the list pattern without raising, falls
  through to `_`.
- `match ([1, 2]) { [_, b] => b, _ => 0 };` is `2` — `_` inside a list
  pattern discards that position without binding a name.
- `match ([]) { [] => "empty", _ => "nonempty" };` is `"empty"` — `[]`
  matches only a zero-length list.
- `match ([1, 2]) { [a, a] => a, _ => "dup" };` is `2` — a repeated name
  binds left to right, the later position wins, per the note above.
- `let a = 100; match ([1, 2]) { [a, b] => a + b, _ => 0 }; print(a);`
  prints `100` — the outer `a` is unchanged after the match, confirming
  list-pattern bindings live in a child scope that does not leak,
  mirroring bound-identifier's own scoping test.
- `shape(parse('match (x) { [a, _] => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the list-pattern arm's shape including
  `["a", None]` as the pattern names — confirms the parse, not just the
  end-to-end value.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`), `cinder/parser.py`
(`_match_arm`, new `_match_list_pattern`/`_match_list_pattern_name`),
`cinder/interpreter.py` (`_evaluate_match`), `tests/test_parser.py`
(`shape()` helper's `MatchExpr` branch, `class TestMatchExpression`),
`tests/test_interpreter.py` (extend `class TestMatchExpression` with the
end-to-end cases above). Once merged, `README.md`'s `match` expression
bullet needs a list-pattern example added, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" bullet
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 6. Standard library: `cartesian_product` — the Cartesian product of N lists

Build: restocking the backlog back to 6 tasks alongside task 5 above
(breadth, following task 5's depth, continuing the alternation task 4
→ task 5 already restarted). Cinder's collection-helper cluster is deep
(`zip`/`zip_longest`/`zip_with`/`unzip`, `flatten`/`flatten_deep`,
`chunk`/`sliding_window`, `interleave`/`interpose`, and more) but has no
way to combine several lists into every ordered tuple of one element
from each — the Cartesian product, the collection-side analogue to
`binomial`/`nth_catalan`'s combinatorics-side counting. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(cartesian_product([[1, 2], [3, 4]]));'
# -> <eval>:1:7: undefined name 'cartesian_product'
```

Add to `cinder/builtins.py`, registered right after `_zip_with` (search
`def _zip_with`, itself already imported alongside `itertools` at the
top of this module — no new import needed):
```python
def _cartesian_product(arguments: list, line: int, column: int) -> object:
    _require_arity("cartesian_product", arguments, 1, line, column)
    lists = arguments[0]
    if not isinstance(lists, list):
        raise CinderRuntimeError(
            f"cartesian_product() requires a list, got {type_name(lists)}", line, column
        )
    for index, item in enumerate(lists):
        if not isinstance(item, list):
            raise CinderRuntimeError(
                f"cartesian_product() requires a list of lists, element {index} is "
                f"{type_name(item)}",
                line,
                column,
            )
    return [list(combo) for combo in itertools.product(*lists)]
```
Mirrors `_zip`'s own per-argument list-type-check style (search `def
_zip`), just looped over one outer list of lists instead of two fixed
positional arguments. `itertools.product(*lists)` does the actual work —
this builtin is a thin, validated wrapper, the same composition style
`nth_catalan` used for `math.comb`. Two edge cases are load-bearing and
covered explicitly below: `cartesian_product([])` (an empty outer list)
returns `[[]]` — one empty combination, not zero combinations, matching
the standard mathematical convention that the Cartesian product of zero
sets is the singleton set containing the empty tuple, and exactly what
`itertools.product()` called with no arguments already returns; while
`cartesian_product([[1, 2], []])` (an empty *inner* list present among
otherwise non-empty ones) returns `[]` — zero combinations, since no
element can be drawn from the empty list, which `itertools.product`
already handles correctly with no special-case code needed. Also
register the new dict entry (search `"zip_with": _zip_with,`, add
`"cartesian_product": _cartesian_product,` directly after it).

Acceptance criteria:
- `cartesian_product([[1, 2], [3, 4]]);` is `[[1, 3], [1, 4], [2, 3],
  [2, 4]]`.
- `cartesian_product([[1, 2], [3, 4], [5]]);` is `[[1, 3, 5], [1, 4, 5],
  [2, 3, 5], [2, 4, 5]]` — three input lists, not just two.
- `cartesian_product([[1, 2]]);` is `[[1], [2]]` — a single input list
  still produces one-element combinations, not a flat list.
- `cartesian_product([]);` is `[[]]` — the empty-outer-list convention
  above, not `[]`.
- `cartesian_product([[1, 2], []]);` is `[]` — the empty-inner-list case
  above.
- `cartesian_product("ab");` raises `CinderRuntimeError` matching
  `"cartesian_product() requires a list, got string"`.
- `cartesian_product([1, 2]);` raises `CinderRuntimeError` matching
  `"cartesian_product() requires a list of lists, element 0 is int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `zip_with`/`unzip`,
see current line numbers — shift if earlier tasks this cycle land
first), `tests/test_builtins.py` (model on `class TestZip`/`class
TestZipWith`, search those names, for the list-of-lists validation test
shapes, and `class TestBinomial` for the arity-error test shape). Once
merged, `README.md`'s Builtins bullet needs `cartesian_product` added
near `zip`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
