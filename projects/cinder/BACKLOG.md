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
## 1. Standard library: `cartesian_product` — the Cartesian product of N lists

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

## 2. Language: range patterns in `match` arms (`1..10 => "small"`)

Build: restocking the backlog back to 6 tasks now that multi-value literal
patterns landed via PR #312, per `PROJECT.md`'s breadth-vs-depth policy
(landing #312 dropped the queue to 3-breadth/2-depth: `nth_triangular`,
`nth_catalan`, `cartesian_product` vs. guards, flat list patterns — this
task restocks with depth to restore 3-breadth/3-depth parity, per the
explicit instruction the previous grooming pass left in `PROJECT.md`'s
"Current frontier" note). Cinder already has range *literals* (`1..10`,
`1..=10`, sugar over `range()`) and already uses them for membership tests
(`5 in 1..10` is `true`), but a `match` arm cannot use one as a pattern yet
— every arm today tests either exact equality (a literal pattern) or
matches unconditionally (`_`/a bound identifier). Range patterns are the
natural middle ground: "does the subject fall in this range" rather than
"does it equal this one value" or "match anything at all" — the same
generalization Rust's `n @ 1..=9 => ...` and Python's `case 1 | 2 | 3:`
(via guards) address in their own pattern-matching syntax. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match (5) { 1..10 => "small", _ => "large" });'
# -> <eval>:1:20: expected '=>' after match pattern, found '..'
```

**Ordering note:** task 2 (flat list patterns) is still queued ahead of
this and may land first, adding a `list_pattern`-shaped field to
`MatchArm`/`_match_arm`/`_evaluate_match` alongside the one shown below —
adapt to whatever the merged code actually looks like, the same way
`nth_triangular` adapted to `is_octagonal` landing first. (Guards in
`match` arms, formerly queued ahead of this task too, was attempted and
closed after three failed review rounds — see `## Graveyard` below — so
it no longer factors into this task's field list.) The code below is
grounded in **today's** actual code (verified by reading
`cinder/ast_nodes.py`/`cinder/parser.py`/`cinder/interpreter.py` directly,
post-#312, pre-task 2): add a fifth pattern *kind*, mutually exclusive
with the existing literal/wildcard/bound-identifier ones, storing a
`RangeExpr` (the same AST node `for i in 1..5` and `x in 1..10` already
use — reuse it, don't invent a new range representation) on the arm.
**Scope note:** only `INT` literal bounds are accepted (not `FLOAT`, not
arbitrary expressions) — this matches the existing constraint that
`range()`/range-literal bounds must already be ints elsewhere in Cinder
(`cinder/builtins.py`'s `_range` raises `"range() requires int arguments"`
for a float bound), so a float-bounded range pattern would either need new
float-range semantics invented from scratch or would surface a confusing
runtime error mid-match — both real gaps, left for a future grooming pass,
not this task. A step component (`1..10..2`) is also out of scope for the
same reason: real range literals support it, but it adds a second layer of
parsing complexity range patterns don't need to be useful yet. Negative
bounds (`-10..0`) are also out of scope, but not by choice — this task
doesn't add them, it inherits an existing, pre-existing gap: **no** match
pattern today, literal or otherwise, accepts a negative number (`match
(-5) { -5 => "neg", _ => "pos" };` already fails to parse on current
`main`, `<eval>:1:20: expected a literal, identifier, or '_' in match
pattern, found '-'`, since `_match_pattern` only ever looks at a bare
literal token, never a unary-minus expression). Fixing that is a real gap
worth its own future task, not this one.

Today's `MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) — add
a fourth field:
```python
    pattern: "Expr | None"
    body: "Expr"
    binding: "str | None" = None
    range_pattern: "RangeExpr | None" = None
```

Today's `_match_pattern` (`cinder/parser.py`, search `def _match_pattern`)
currently returns a `tuple[Expr | None, str | None]`; extend it to a
3-tuple and detect `..`/`..=` right after an `INT` literal (string,
float, bool, and nil literals are unaffected — only `INT` gets the
range-lookahead branch):
```python
    def _match_pattern(self) -> "tuple[Expr | None, str | None, RangeExpr | None]":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            if token.lexeme == "_":
                return None, None, None
            return None, token.lexeme, None
        if token.type == TokenType.INT:
            self._advance()
            start = Literal(token.literal, token.line, token.column)
            if self._check(TokenType.DOT_DOT) or self._check(TokenType.DOT_DOT_EQ):
                dots = self._advance()
                inclusive = dots.type is TokenType.DOT_DOT_EQ
                end_token = self._peek()
                if end_token.type != TokenType.INT:
                    raise ParseError(
                        "expected an int after '..' in match range pattern, found "
                        f"{self._describe(end_token)}",
                        end_token.line,
                        end_token.column,
                    )
                self._advance()
                end = Literal(end_token.literal, end_token.line, end_token.column)
                return None, None, RangeExpr(start, end, dots.line, dots.column, inclusive)
            return start, None, None
        if token.type in (TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column), None, None
        if token.type == TokenType.TRUE:
            self._advance()
            return Literal(True, token.line, token.column), None, None
        if token.type == TokenType.FALSE:
            self._advance()
            return Literal(False, token.line, token.column), None, None
        if token.type == TokenType.NIL:
            self._advance()
            return Literal(None, token.line, token.column), None, None
        raise ParseError(
            f"expected a literal, identifier, or '_' in match pattern, "
            f"found {self._describe(token)}",
            token.line,
            token.column,
        )
```

Today's `_match_arm` (`cinder/parser.py`, search `def _match_arm`) needs
its tuple-unpacking widened to three elements, and its "cannot combine
with other patterns" guard needs to check both `pattern is None` *and*
`range_pattern is None` (a true wildcard/binding), since a range pattern
combined with a literal in one multi-value arm (`1, 2..5 => ...`) is
allowed — only the wildcard/bound-identifier kind is exclusive:
```python
    def _match_arm(self) -> "list[MatchArm]":
        first_token = self._peek()
        entries = [self._match_pattern()]
        while self._check(TokenType.COMMA):
            self._advance()
            entries.append(self._match_pattern())
        if len(entries) > 1 and any(
            pattern is None and range_pattern is None
            for pattern, _, range_pattern in entries
        ):
            raise ParseError(
                "'_' or a bound identifier cannot be combined with other "
                "patterns in a match arm",
                first_token.line,
                first_token.column,
            )
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return [
            MatchArm(pattern, body, binding, range_pattern)
            for pattern, binding, range_pattern in entries
        ]
```

Today's `_evaluate_match` (`cinder/interpreter.py`, search `def
_evaluate_match`) needs a new branch checked first, since a range pattern
is a membership test rather than a `values_equal` comparison. Reuse
`self._evaluate_range` (already used for `for`-loop ranges, search `def
_evaluate_range`) to materialize the range's values, and the
module-level `contains_value` helper (search `def contains_value`,
already shared by the `in` operator and the `contains()` builtin) to test
membership — both already exist, neither needs new logic:
```python
    def _evaluate_match(self, expr: MatchExpr, env: Environment) -> object:
        subject = self.evaluate(expr.subject, env)
        for arm in expr.arms:
            if arm.range_pattern is not None:
                values = self._evaluate_range(arm.range_pattern, env)
                if contains_value(
                    values, subject, arm.range_pattern.line, arm.range_pattern.column
                ):
                    return self.evaluate(arm.body, env)
                continue
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
`contains_value` never raises for a list collection (only for a non-list/
map/string one, per its own body) and `values` is always a list here (
`_evaluate_range` delegates to `_range`, which always returns
`list(range(...))`), so this branch cannot itself raise — a subject of any
type simply fails to match and falls through to the next arm, exactly
like a non-equal literal pattern already does.

Acceptance criteria:
- `match (5) { 1..10 => "small", _ => "large" };` is `"small"`.
- `match (15) { 1..10 => "small", _ => "large" };` is `"large"` — `10` is
  exclusive of the upper bound, matching every other range-literal use in
  Cinder (`for i in 1..10`, `10 in 1..10` is `false`).
- `match (10) { 1..=10 => "small", _ => "large" };` is `"small"` — `..=`
  includes the upper bound.
- `match (1) { 1..10 => "small", _ => "large" };` is `"small"` — the lower
  bound is inclusive on both spellings.
- `match (6) { 1, 5..10, 20 => "matched", _ => "no" };` is `"matched"` — a
  range pattern combines with literal patterns in one multi-value arm
  (`6` falls in `5..10`, the second entry).
- `match ("x") { 1..10 => "n", _ => "s" };` is `"s"` — a non-numeric
  subject fails a range pattern without raising, falls through to `_`.
- `shape(parse('match (x) { 1..10 => "a", _ => "b" }'))` (see
  `tests/test_parser.py`) shows the range-pattern arm's shape including
  the `RangeExpr` shape `("RangeExpr", ("Literal", 1), ("Literal", 10),
  False, None)` in the extended per-arm tuple — confirms the parse, not
  just the end-to-end value.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`), `cinder/parser.py`
(`_match_pattern`, `_match_arm`), `cinder/interpreter.py`
(`_evaluate_match`), `tests/test_parser.py` (`shape()` helper's
`MatchExpr` branch, `class TestMatchExpression`), `tests/test_interpreter.py`
(extend `class TestMatchExpression`, search that name, with the end-to-end
cases above). Once merged, `README.md`'s `match` expression bullet needs a
range-pattern example added, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs refreshing —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_pentagonal` — the k-th pentagonal number by position

Build: restocking the backlog back to 6 tasks now that `nth_triangular`
landed via PR #313, per `PROJECT.md`'s breadth-vs-depth policy (landing
#313 dropped the queue to 2-breadth/3-depth: `nth_catalan`,
`cartesian_product` vs. guards, flat list patterns, range patterns —
this task restocks with breadth to restore 3-breadth/3-depth parity, per
the explicit instruction the previous grooming pass left in
`PROJECT.md`'s "Current frontier" note). `is_pentagonal` already exists
as a membership test, but Cinder has no way to ask "what is the k-th
pentagonal number" the way it can for triangular numbers
(`nth_triangular`, PR #313), Fibonacci (`nth_fibonacci`), primes
(`nth_prime`), and Lucas numbers (`nth_lucas`) — this is the exact same
"value-returning sibling of an `is_*` membership test" pattern
`nth_triangular` and `nth_lucas` already established, just for the next
figurate-number cluster member. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_pentagonal(5));'
# -> <eval>:1:7: undefined name 'nth_pentagonal'
```

Add to `cinder/builtins.py`, registered right after `_nth_triangular`
(search `def _nth_triangular`, immediately before `_is_prime`):
```python
def _nth_pentagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_pentagonal", arguments, 1, line, column)
    value = _require_int("nth_pentagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_pentagonal() requires a positive integer, domain error", line, column
        )
    return value * (3 * value - 1) // 2
```
The closed form `P(k) = k(3k - 1) / 2` is the standard 1-indexed
pentagonal number formula (`P(1) = 1, P(2) = 5, P(3) = 12, ...`) — no
indexing subtlety here unlike `nth_catalan`'s 0-indexed closed form,
since pentagonal numbers are already conventionally 1-indexed starting
at `P(1) = 1`, matching every other builtin in this `nth_*` cluster
directly. This mirrors `_nth_triangular`'s own shape exactly (arity
check, int check, domain check, one-line closed-form return) — a thin,
direct composition, not a new algorithm. A domain error (not a
sentinel value) for `value < 1` matches every other `nth_*` builtin's
own convention for their own "not a valid position" case. Also register
the new dict entry (search `"nth_triangular": _nth_triangular,`, add
`"nth_pentagonal": _nth_pentagonal,` directly after it).

Acceptance criteria:
- `nth_pentagonal(1);` is `1`, `nth_pentagonal(2);` is `5`,
  `nth_pentagonal(3);` is `12`, `nth_pentagonal(4);` is `22`,
  `nth_pentagonal(5);` is `35` — the first five pentagonal numbers.
- `nth_pentagonal(10);` is `145`.
- `nth_pentagonal(100);` is `14950`.
- `is_pentagonal(nth_pentagonal(n));` is `true` for every `n` from `1`
  to `100` — confirms the closed form agrees with the existing
  membership predicate across a wide range, the same cross-check
  `nth_triangular`'s own acceptance criteria used against
  `is_triangular`.
- `nth_pentagonal(0);` and `nth_pentagonal(-3);` both raise
  `CinderRuntimeError` matching `"nth_pentagonal() requires a positive
  integer, domain error"`.
- `nth_pentagonal(2.0);` raises `CinderRuntimeError` matching
  `"nth_pentagonal() requires an int, got float"`.
- `nth_pentagonal(true);` raises `CinderRuntimeError` matching
  `"nth_pentagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `nth_triangular`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestNthTriangular`, search
that name, including its `is_triangular`-agreement-style cross-check
test, adapted to `is_pentagonal`). Once merged, `README.md`'s Builtins
bullet needs `nth_pentagonal` added near `nth_triangular`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 4. Language: negative literal patterns in `match` arms (`-5 => "neg"`)

Build: restocking the backlog back to 6 tasks now that guards in `match`
arms was closed after three failed review rounds (see `## Graveyard`
below), dropping the queue from 6 to 5 (3-breadth/2-depth: `nth_catalan`,
`cartesian_product`, `nth_pentagonal` vs. flat list patterns, range
patterns). This restocks with depth to restore 3-breadth/3-depth parity,
continuing the alternation the guards task itself was standing in for.
Rather than re-attempt guards immediately — its postmortem below
identifies a real fix but a materially different implementation strategy
than what was tried three times, and re-queuing it cold risks a fourth
failed round — this task picks up a smaller, unrelated gap that task 4
(range patterns) explicitly flagged but explicitly left out of its own
scope: **no** match pattern today, literal or otherwise, accepts a
negative number. Verify the gap, on current `main`:
```sh
python3 -m cinder.cli eval 'print(match (-5) { -5 => "neg", 5 => "pos", _ => "other" });'
# -> <eval>:1:20: expected a literal, identifier, or '_' in match pattern, found '-'
```
This is a parser-only gap: `_match_pattern` (`cinder/parser.py`) only
ever looks at a bare literal token, never a unary-minus expression, so
`-5` in pattern position fails to parse at all — it never reaches
evaluation. Unlike guards, this fix touches exactly one function, has no
interaction with `_bracket_depth`/bare-arrow suppression, and does not
touch `MatchArm`'s field list at all (a negative literal is still just a
`Literal` pattern, same as a positive one) — a deliberately low-risk task
after the guards graveyard entry.

**Scope note:** only a literal `-<INT>` or `-<FLOAT>` is accepted — not
a general unary-minus *expression* (`-x`, `-(1 + 1)`). Match patterns
have never accepted arbitrary expressions (only literals, identifiers,
and `_`), and this task does not change that; it only widens "literal"
to include a leading `-` on a numeric literal, mirroring how the lexer/
parser already treat `-5` as a single negative literal in ordinary
expression position elsewhere in Cinder. Negative bounds on range
patterns (`-10..0`, task 4's own explicitly out-of-scope case) are not
addressed by this task either — that stays a real gap for range patterns
specifically, since a range pattern's bounds are parsed by task 4's own
code path, not `_match_pattern`'s literal branch this task changes.

Today's `_match_pattern` (`cinder/parser.py`, search `def
_match_pattern`) — add a new branch for a leading `MINUS` before the
existing `INT`/`FLOAT`/`STRING` branch, so `-5` and `-2.5` parse as a
single negated `Literal` rather than falling through to the "expected a
literal..." error:
```python
    def _match_pattern(self) -> "tuple[Expr | None, str | None]":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            if token.lexeme == "_":
                return None, None
            return None, token.lexeme
        if token.type == TokenType.MINUS:
            minus = self._advance()
            value_token = self._peek()
            if value_token.type not in (TokenType.INT, TokenType.FLOAT):
                raise ParseError(
                    "expected an int or float after '-' in match pattern, "
                    f"found {self._describe(value_token)}",
                    value_token.line,
                    value_token.column,
                )
            self._advance()
            return Literal(-value_token.literal, minus.line, minus.column), None
        if token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column), None
        ...  # TRUE/FALSE/NIL branches and the final raise are unchanged
```
The new branch consumes the `MINUS` token itself, so the resulting
`Literal`'s line/column point at the `-`, not the digit after it —
matching how every other pattern's `Literal` points at its own leading
token. No changes are needed to `_match_arm` (its multi-value
comma-handling and its "`_`/bound-identifier cannot combine with other
patterns" guard both already operate on `pattern is None`, and a negative
literal produces a non-`None` `Literal` pattern exactly like a positive
one) or to `_evaluate_match` (a negative-literal arm is compared with
the existing `values_equal(subject, self.evaluate(arm.pattern, env))`
branch, unchanged, since it's just another `Literal` expression to
evaluate).

Acceptance criteria:
- `match (-5) { -5 => "neg", 5 => "pos", _ => "other" };` is `"neg"`.
- `match (5) { -5 => "neg", 5 => "pos", _ => "other" };` is `"pos"`.
- `match (-2.5) { -2.5 => "neg-float", _ => "other" };` is `"neg-float"`.
- `match (0) { -5 => "neg", _ => "not"};` is `"not"` — a non-matching
  negative-literal pattern falls through to `_` without raising, exactly
  like a non-equal positive-literal pattern already does.
- `match (-1) { -5, -1, 3 => "matched", _ => "no" };` is `"matched"` —
  a negative literal combines with other literals in one multi-value arm
  (PR #312's comma-separated form), landing in the second position.
- `shape(parse('match (x) { -5 => "a", _ => "b" }'))` (see
  `tests/test_parser.py`) shows the arm's pattern as `("Literal", -5)` —
  confirms the parse produces a genuinely negated literal, not `5` with
  a sign dropped.
- `match (5) { -"x" => "a", _ => "b" };` raises `ParseError` matching
  `"expected an int or float after '-' in match pattern, found string
  'x'"` — `-` before a non-numeric literal is a parse error, not a
  silent fallback.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_pattern`), `tests/test_parser.py`
(`shape()` helper already renders `Literal` nodes; extend `class
TestMatchExpression`, search that name, with the parse-shape case above
and the new `ParseError` case), `tests/test_interpreter.py` (extend
`class TestMatchExpression` with the end-to-end cases above). Once
merged, `README.md`'s `match` expression bullet needs its "not supported
yet" list trimmed (it currently reads "no nested/list patterns, range
patterns, or guards yet" — drop "negative literals" from that list since
this task lands them), its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

### Language: guards in `match` arms (`n if n > 0 => "positive"`) — PR #314, closed 2026-08-25

Bounced 3x with `VERDICT: CHANGES REQUESTED`, all the same recurring bug:
each fix round patched `_bracket_depth` tracking (used to scope the
bare-arrow/guard `=>` ambiguity fix) for one nested construct — call/list/map
arguments (round 1), `match` expressions (round 2), `fn` expressions (round
3) — while the reviewer kept finding another construct the fix hadn't
threaded depth through, and round 3's review flagged a 4th possible gap
(`_arrow_body`'s bare-expression branch, `_block()`) that was never
confirmed either way. Next attempt should enumerate *every* production that
opens a paren/bracket/brace scope up front (grep `_bracket_depth` usages in
the closed PR's final diff for the list-so-far) rather than fixing gaps
reactively one review round at a time — or consider a structurally
different fix that doesn't need per-construct threading at all (e.g.
resolving the bare-arrow/guard ambiguity by lookahead at the `=>` site
instead of a suppression-depth counter).
