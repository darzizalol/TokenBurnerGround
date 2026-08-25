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
## 1. Standard library: `cartesian_product` — the Cartesian product of N lists [claimed 2026-08-25T19:42:15Z]

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
— every arm today tests either exact equality (a literal pattern), matches
unconditionally (`_`/a bound identifier), or destructures a fixed-length
list (a list pattern, PR #316). Range patterns are the natural middle
ground for the scalar case: "does the subject fall in this range" rather
than "does it equal this one value" or "match anything at all" — the same
generalization Rust's `n @ 1..=9 => ...` and Python's `case 1 | 2 | 3:`
(via guards) address in their own pattern-matching syntax. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match (5) { 1..10 => "small", _ => "large" });'
# -> <eval>:1:20: expected '=>' after match pattern, found '..'
```

**Ordering note (updated this grooming pass):** flat list patterns
(formerly queued as "task 2") already landed on `main` via PR #316 —
`MatchArm` already carries a **fourth** field, `list_pattern`
(`"list | None"`), and `_match_arm`/`_evaluate_match` already branch on
it, before reaching the literal/wildcard/bound-identifier path, via a
leading `if self._check(TokenType.LBRACKET): ...` in `_match_arm` and a
leading `if arm.list_pattern is not None: ...` in `_evaluate_match`. This
task adds range patterns as a **fifth** field, `range_pattern`, alongside
`list_pattern` — every snippet below is grounded in today's actual code
(verified by reading `cinder/ast_nodes.py`/`cinder/parser.py`/
`cinder/interpreter.py` directly, post-#316) and **keeps the existing
`list_pattern` branches intact** in both functions — applying this task
must not regress flat list patterns. (Guards in `match` arms, formerly
queued ahead of this task too, was attempted and closed after three
failed review rounds — see `## Graveyard` below — so it no longer factors
into this task's field list either.) **Scope note:** only `INT` literal
bounds are accepted (not `FLOAT`, not arbitrary expressions) — this
matches the existing constraint that `range()`/range-literal bounds must
already be ints elsewhere in Cinder (`cinder/builtins.py`'s `_range`
raises `"range() requires int arguments"` for a float bound), so a
float-bounded range pattern would either need new float-range semantics
invented from scratch or would surface a confusing runtime error
mid-match — both real gaps, left for a future grooming pass, not this
task. A step component (`1..10..2`) is also out of scope for the same
reason: real range literals support it, but it adds a second layer of
parsing complexity range patterns don't need to be useful yet. Negative
bounds (`-10..0`) are also out of scope, but not by choice — this task
doesn't add them, it inherits an existing, pre-existing gap: **no** match
pattern today, literal or otherwise, accepts a negative number (`match
(-5) { -5 => "neg", _ => "pos" };` already fails to parse on current
`main`, `<eval>:1:20: expected a literal, identifier, or '_' in match
pattern, found '-'`, since `_match_pattern` only ever looks at a bare
literal token, never a unary-minus expression). Fixing that is task 4
below, not this one.

Today's `MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) — add
a fifth field, after the existing `list_pattern`:
```python
    pattern: "Expr | None"
    body: "Expr"
    binding: "str | None" = None
    list_pattern: "list | None" = None
    range_pattern: "RangeExpr | None" = None
```

Today's `_match_pattern` (`cinder/parser.py`, search `def _match_pattern`;
this is the scalar-pattern path, unrelated to and untouched by the
`list_pattern` branch in `_match_arm` below) currently returns a
`tuple[Expr | None, str | None]`; extend it to a 3-tuple and detect `..`/
`..=` right after an `INT` literal (string, float, bool, and nil literals
are unaffected — only `INT` gets the range-lookahead branch):
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

Today's `_match_arm` (`cinder/parser.py`, search `def _match_arm`) starts
with a `LBRACKET` check for list patterns (**keep this branch exactly as
it is on `main` today, just widen the `MatchArm(...)` call to pass
`None` for the new `range_pattern` field**); below it, its
tuple-unpacking needs widening to three elements, and its "cannot combine
with other patterns" guard needs to check both `pattern is None` *and*
`range_pattern is None` (a true wildcard/binding), since a range pattern
combined with a literal in one multi-value arm (`1, 2..5 => ...`) is
allowed — only the wildcard/bound-identifier kind is exclusive:
```python
    def _match_arm(self) -> "list[MatchArm]":
        if self._check(TokenType.LBRACKET):
            list_pattern = self._match_list_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return [MatchArm(None, body, None, list_pattern, None)]
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
            MatchArm(pattern, body, binding, None, range_pattern)
            for pattern, binding, range_pattern in entries
        ]
```

Today's `_evaluate_match` (`cinder/interpreter.py`, search `def
_evaluate_match`) starts with an `arm.list_pattern is not None` branch
(**keep this exactly as it is on `main` today**); the new range-pattern
branch goes directly after it, checked before the wildcard/binding/
literal path, since a range pattern is a membership test rather than a
`values_equal` comparison. Reuse `self._evaluate_range` (already used for
`for`-loop ranges, search `def _evaluate_range`) to materialize the
range's values, and the module-level `contains_value` helper (search `def
contains_value`, already shared by the `in` operator and the `contains()`
builtin) to test membership — both already exist, neither needs new
logic:
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
- `match ([1, 2]) { [a, b] => a + b, _ => 0 };` is still `3` — a
  regression check that flat list patterns (`arm.list_pattern`) still
  work unchanged after this task's `_match_arm`/`_evaluate_match` edits.
- `shape(parse('match (x) { 1..10 => "a", _ => "b" }'))` (see
  `tests/test_parser.py`) shows the first arm's 5-element tuple as
  `(None, ("Literal", "a"), None, None, ("RangeExpr", ("Literal", 1),
  ("Literal", 10), False, None))` — confirms the parse, not just the
  end-to-end value, and that `list_pattern` stays `None` on a range-
  pattern arm.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`), `cinder/parser.py`
(`_match_pattern`, `_match_arm`), `cinder/interpreter.py`
(`_evaluate_match`), `tests/test_parser.py` (the `shape()` helper's
`MatchExpr` branch needs its per-arm tuple widened from 4 to 5 elements —
search `arm.list_pattern,` inside `shape()` and add `shape(arm.range_pattern)
if arm.range_pattern is not None else None,` right after it — plus `class
TestMatchExpression`), `tests/test_interpreter.py` (extend `class
TestMatchExpression`, search that name, with the end-to-end cases above).
Once merged, `README.md`'s `match` expression bullet needs a range-pattern
example added, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

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
failed round — this task picks up a smaller, unrelated gap that task 2
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
after the guards graveyard entry. **Ordering note:** if task 2 (range
patterns) has already landed by the time this task is claimed,
`_match_pattern` will already return a 3-tuple (`pattern, binding,
range_pattern`) instead of the 2-tuple shown below — adapt the new
`MINUS` branch to return a 3-tuple (`Literal(...), None, None`) in that
case, the same way every other task in this backlog adapts to whichever
sibling landed first.

**Scope note:** only a literal `-<INT>` or `-<FLOAT>` is accepted — not
a general unary-minus *expression* (`-x`, `-(1 + 1)`). Match patterns
have never accepted arbitrary expressions (only literals, identifiers,
and `_`), and this task does not change that; it only widens "literal"
to include a leading `-` on a numeric literal, mirroring how the lexer/
parser already treat `-5` as a single negative literal in ordinary
expression position elsewhere in Cinder. Negative bounds on range
patterns (`-10..0`, task 2's own explicitly out-of-scope case) are not
addressed by this task either — that stays a real gap for range patterns
specifically, since a range pattern's bounds are parsed by task 2's own
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
yet" list trimmed (drop "negative literal patterns" from that list since
this task lands them), its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `power_set` — every subset of a list

Build: restocking the backlog from 4 back to 6 tasks now that
`nth_catalan` (PR #315) and flat list patterns in `match` arms (PR #316)
both landed since the last grooming pass, dropping the queue to
2-breadth/2-depth (`cartesian_product`, `nth_pentagonal` vs. range
patterns, negative literal patterns). This and task 6 below restock one
of each kind to restore 3-breadth/3-depth parity at the 6-task ceiling.
Cinder's collection-helper cluster already answers "every ordered
combination of one element from each of N lists" (`cartesian_product`,
task 1 above, still unclaimed) but has no way to answer the adjacent
question for a single list: "every subset of these elements, of every
size." `binomial` (PR #309) already answers the *counting* version of
this question ("how many size-`k` subsets does an `n`-element set have")
the same way `nth_catalan` answers "which Catalan number" rather than
"how many are there below N" — `power_set` is the *enumerating* sibling,
returning the actual subsets rather than a count, the same
enumerate-vs-count relationship `cartesian_product` has to `len(l1) *
len(l2) * ...`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(power_set([1, 2]));'
# -> <eval>:1:7: undefined name 'power_set' (did you mean 'is_superset'?)
```

Add to `cinder/builtins.py`, registered right after `_enumerate` (search
`def _enumerate`, itself already right after `_zip_with`; `itertools` is
already imported at the top of this module — no new import needed):
```python
def _power_set(arguments: list, line: int, column: int) -> object:
    _require_arity("power_set", arguments, 1, line, column)
    items = arguments[0]
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"power_set() requires a list, got {type_name(items)}", line, column
        )
    return [
        list(combo)
        for size in range(len(items) + 1)
        for combo in itertools.combinations(items, size)
    ]
```
`itertools.combinations(items, size)` over every size from `0` to
`len(items)` does the actual enumeration — this builtin is a thin,
validated wrapper, the same composition style `cartesian_product` uses
for `itertools.product`. Subsets come out ordered by increasing size,
and within a size in the same relative order as `items` itself (both
properties of `itertools.combinations`, not extra code this builtin
needs to add). The empty list is a load-bearing edge case, covered
explicitly below: `power_set([])` returns `[[]]` — the empty set has
exactly one subset, itself, matching the standard mathematical
convention (and `cartesian_product([])`'s own analogous `[[]]` result
for the same reason: `itertools.combinations([], 0)` yields exactly one
empty tuple). Also register the new dict entry (search `"cartesian_product":
_cartesian_product,` if task 1 has already landed and place this entry
directly after it; otherwise search `"enumerate": _enumerate,` and place
it directly after that instead — add `"power_set": _power_set,`).

Acceptance criteria:
- `power_set([]);` is `[[]]`.
- `power_set([1]);` is `[[], [1]]`.
- `power_set([1, 2]);` is `[[], [1], [2], [1, 2]]`.
- `power_set([1, 2, 3]);` is `[[], [1], [2], [3], [1, 2], [1, 3], [2, 3],
  [1, 2, 3]]` — ordered by increasing subset size, matching input order
  within each size.
- `len(power_set(l));` is `2 ** len(l)` for `l` equal to `[]`, `[1]`,
  `[1, 2]`, `[1, 2, 3]`, and `[1, 2, 3, 4]` — the standard subset-count
  identity, the same closed-form cross-check style `nth_pentagonal`'s
  acceptance criteria uses against `is_pentagonal`.
- `power_set("ab");` raises `CinderRuntimeError` matching `"power_set()
  requires a list, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `enumerate`/
`cartesian_product`, see current line numbers — shift if task 1 lands
first this cycle), `tests/test_builtins.py` (model on `class
TestEnumerate`/`class TestCartesianProduct`, search those names, for the
list-validation and arity-error test shapes). Once merged, `README.md`'s
Builtins bullet needs `power_set` added near `cartesian_product`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 6. Language: literal elements in list patterns (`[0, b] => ...`)

Build: restocking the second of two slots this grooming pass added to
restore the backlog to its 6-task, 3-breadth/3-depth ceiling (see task 5
above for the breadth half of the restock). Flat list patterns landed via
PR #316, but every element position in `[a, b]` must be a bound
identifier or `_` — a list pattern can test the *shape* of a list subject
(its length) but cannot test the *value* of any individual element, the
way a scalar pattern can (`5 => ...`). This task closes exactly that gap
for literal elements: `[0, b] => ...` matches a two-element list subject
whose first element equals `0`, binding `b` to the second element,
without requiring a nested `match`/`if` inside the arm body to check it.
`PROJECT.md`'s "Current frontier" section already flags this as a real
gap ("patterns with literal elements... remain real gaps for future
grooming passes, most of them blocked on their simpler sibling landing
and proving the form out first" — flat list patterns is that sibling, and
it has now landed). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ([1, 2]) { [1, b] => b, _ => 0 });'
# -> <eval>:1:25: expected an identifier or '_' inside list pattern, found '1'
```

**Scope note:** only bare literal tokens (`INT`, `FLOAT`, `STRING`,
`TRUE`, `FALSE`, `NIL`) are accepted per element — not arbitrary
expressions, not negative literals (unless task 4 above has already
landed by the time this is claimed, in which case reusing its `MINUS`
handling for consistency is a reasonable adaptation, but is not required
by this task's own acceptance criteria), and no nesting (`[1, [a, b]]` is
still out of scope — a real gap, left for a future task once this one
proves the "literal element" form out, the same staged approach
`nth_triangular` → `nth_pentagonal` used for figurate numbers). Rest
capture (`[a, ...rest]`) is also out of scope — a separate, unrelated
gap.

Today's `_match_list_pattern`/`_match_list_pattern_name`
(`cinder/parser.py`, search `def _match_list_pattern`) only ever consume
an `IDENTIFIER` token per element, returning `str | None`. Widen the
per-element return type to also allow a `Literal` expression node,
mirroring how `_match_pattern`'s own scalar branch already builds
`Literal` nodes for `INT`/`FLOAT`/`STRING`/`TRUE`/`FALSE`/`NIL` tokens:
```python
    def _match_list_pattern(self) -> "list[str | Expr | None]":
        self._advance()  # consume '['
        entries: "list[str | Expr | None]" = []
        if not self._check(TokenType.RBRACKET):
            entries.append(self._match_list_pattern_entry())
            while self._check(TokenType.COMMA):
                self._advance()
                entries.append(self._match_list_pattern_entry())
        self._consume(TokenType.RBRACKET, "']' after list pattern")
        return entries

    def _match_list_pattern_entry(self) -> "str | Expr | None":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            return None if token.lexeme == "_" else token.lexeme
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
            f"expected an identifier, '_', or a literal inside list pattern, "
            f"found {self._describe(token)}",
            token.line,
            token.column,
        )
```
(Rename `_match_list_pattern_name` to `_match_list_pattern_entry` — every
call site is the two loops inside `_match_list_pattern` itself, both
shown above already updated.)

Today's `_evaluate_match` (`cinder/interpreter.py`, search `def
_evaluate_match`) needs its `arm.list_pattern is not None` branch (the
first branch in the function) widened to check each entry's kind before
binding: a `Literal` entry is a value test (`values_equal`, falling
through — not raising — to the next arm on mismatch, exactly like a
scalar literal pattern already does), while a `str | None` entry keeps
its current bind-or-discard behavior unchanged:
```python
            if arm.list_pattern is not None:
                if not isinstance(subject, list) or len(subject) != len(arm.list_pattern):
                    continue
                arm_env = Environment(env)
                matched = True
                for entry, item in zip(arm.list_pattern, subject):
                    if isinstance(entry, Literal):
                        if not values_equal(item, self.evaluate(entry, arm_env)):
                            matched = False
                            break
                        continue
                    if entry is not None:
                        arm_env.define(entry, item)
                if not matched:
                    continue
                return self.evaluate(arm.body, arm_env)
```
`Literal` is already imported in `cinder/interpreter.py` (search `from
cinder.ast_nodes import (`, `Literal,` is already in that block) — no new
import needed. No changes are needed to `MatchArm` itself (`list_pattern`
stays typed loosely enough already) or to `_match_arm` (it just forwards
whatever `_match_list_pattern` returns, unchanged).

Acceptance criteria:
- `match ([1, 2]) { [1, b] => b, _ => 0 };` is `2` — a leading literal
  element matches and the trailing identifier binds.
- `match ([9, 2]) { [1, b] => b, _ => 0 };` is `0` — a non-matching
  literal element falls through to the next arm without raising.
- `match ([1, 2]) { [a, 2] => a, _ => 0 };` is `1` — a literal element in
  a non-leading position works the same way.
- `match (["x", 5]) { ["x", "y"] => "no", ["x", n] => n, _ => 0 };` is
  `5` — string literal elements compare by value, and the first arm's
  literal-vs-literal mismatch on the second element falls through
  correctly.
- `match ([true, 1]) { [true, n] => n, _ => 0 };` is `1` — `TRUE`/`FALSE`/
  `NIL` literal elements parse and match too, not just `INT`/`FLOAT`/
  `STRING`.
- `match ([1, 2]) { [a, b] => a + b, _ => 0 };` is still `3` — an
  all-identifier list pattern (PR #316's original form) is unaffected.
- `shape(parse('match (x) { [1, b] => b, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `list_pattern` as
  `[("Literal", 1), "b"]` — confirms the literal element parses to an
  actual `Literal` node, not a string, while the identifier element
  stays a plain string.
- `match (x) { [1, "y"] => 0 };` with `1` not followed by a valid literal
  or identifier (e.g. `[1, +]`) raises `ParseError` matching `"expected
  an identifier, '_', or a literal inside list pattern, found ..."`.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_list_pattern`,
`_match_list_pattern_name` → `_match_list_pattern_entry`),
`cinder/interpreter.py` (`_evaluate_match`), `tests/test_parser.py` (the
`shape()` helper already renders `arm.list_pattern` as-is — since entries
are now a mix of `str` and `Literal` nodes, the helper needs each
`Literal` entry rendered via `shape()` too: search `arm.list_pattern,`
inside `shape()`'s `MatchExpr` branch and change it to a list
comprehension that calls `shape(entry) if isinstance(entry, Expr) else
entry` per entry; also extend `class TestMatchExpression`),
`tests/test_interpreter.py` (extend `class TestMatchExpression` with the
end-to-end cases above). Once merged, `README.md`'s `match` expression
bullet needs its flat-list-pattern description updated to mention literal
elements and its "not supported yet" list trimmed accordingly, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

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
