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

## 1. Language: guards in `match` arms (`n if n > 0 => "positive"`)

Build: restocking the backlog back to 6 tasks now that `is_octagonal`
landed via PR #308, per `PROJECT.md`'s breadth-vs-depth policy. The
pattern-matching arc opened by PR #304 has since grown bound-identifier
patterns (PR #311) and multi-value literal patterns (PR #312) — guards
are the next natural follow-up `PROJECT.md`'s "Current frontier" note
calls out (flat list patterns, queued as task 4 below, and
nested/destructuring patterns beyond that are the remaining ones). A
guard is an extra boolean condition on an arm, evaluated only once the
arm's pattern already matches, letting one pattern split into several
arms by an arbitrary expression instead of only by literal equality —
every pattern-matching language this feature is modeled on (Rust's `n
if n > 0 => ...`, Python's `case n if n > 0:`) has this. Verify the gap
against today's codebase:
```sh
python3 -m cinder.cli eval 'let x = 5; print(match (0) { 0 if x > 3 => "big-zero", _ => "other" });'
# -> <eval>:1:32: expected '=>' after match pattern, found 'if'
```

**Ordering note:** task 3 (flat list patterns) is also queued and may
land first, adding a `list_pattern`-shaped branch to `MatchArm`/
`_match_arm`/`_evaluate_match` alongside the ones shown below — adapt to
whatever the merged code actually looks like, the same way `nth_triangular`
adapted to `is_octagonal` landing first. The code below is grounded in
**today's** actual code (verified by reading `cinder/ast_nodes.py`/
`cinder/parser.py`/`cinder/interpreter.py` directly, post-#311/#312): parse
an optional `if <expr>` after the whole comma-separated pattern list and
before the `=>`; store it as one more field on `MatchArm`; at eval time,
only treat the arm as matching if the pattern already matched (or is a
wildcard/binding) **and** the guard (if present) evaluates truthy — a
false guard falls through to the next arm exactly as a non-matching
pattern would, it does not raise or stop the search. A guard on a
bound-identifier arm must be evaluated in that arm's own child scope (so
it can see the binding), not the outer `env`.

Today's `MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) —
add a fourth field:
```python
    pattern: "Expr | None"
    body: "Expr"
    binding: "str | None" = None
    guard: "Expr | None" = None
```

Today's `_match_arm`/`_match_pattern` (`cinder/parser.py`, search `def
_match_arm`):
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
Add guard parsing between the comma-loop and the `FAT_ARROW` consume,
and thread it through the list comprehension so every desugared arm
from one multi-value pattern list shares the same guard (the same way
they already share one `body`):
```python
        guard = None
        if self._check(TokenType.IF):
            self._advance()
            guard = self._ternary()
        self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
        body = self._ternary()
        return [MatchArm(pattern, body, binding, guard) for pattern, binding in entries]
```
`TokenType.IF` is already used the same way — an optional trailing
condition parsed with `self._ternary()` — by `_comprehension_clause`
(search `def _comprehension_clause`, the `if self._check(TokenType.IF)`
block), so this mirrors an existing, working pattern in this same
parser rather than inventing new lookahead machinery.

Today's `_evaluate_match` (`cinder/interpreter.py`, search `def
_evaluate_match`):
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
Add a guard check right before each of the three `return
self.evaluate(arm.body, ...)` lines, using `continue` instead of
returning when the guard is falsy — evaluate the guard in `arm_env` for
the bound-identifier branch (so it can see the binding) and in `env` for
the other two:
```python
            if arm.pattern is None:
                if arm.binding is None:
                    if arm.guard is not None and not is_truthy(self.evaluate(arm.guard, env)):
                        continue
                    return self.evaluate(arm.body, env)
                arm_env = Environment(env)
                arm_env.define(arm.binding, subject)
                if arm.guard is not None and not is_truthy(self.evaluate(arm.guard, arm_env)):
                    continue
                return self.evaluate(arm.body, arm_env)
            if values_equal(subject, self.evaluate(arm.pattern, env)):
                if arm.guard is not None and not is_truthy(self.evaluate(arm.guard, env)):
                    continue
                return self.evaluate(arm.body, env)
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
- `match (7) { n if n > 100 => "huge", n if n > 3 => "medium" };` is
  `"medium"` — a guard on a bound-identifier arm can see the binding
  (`n`), and a false guard on the first bound-identifier arm falls
  through to the second.
- `let n = 100; match (7) { n if n > 3 => "shadowed", _ => "other" };
  print(n);` prints `100` — the guard's `n` refers to the arm's own
  binding, not the outer `n`, and evaluating the guard does not leak the
  binding into the outer scope either.
- `tests/test_parser.py`'s `shape()` helper's `MatchExpr` branch (search
  `isinstance(node, MatchExpr)`) needs its per-arm tuple extended to
  include the guard shape (`shape(arm.guard) if arm.guard is not None
  else None`), and every existing expected-shape tuple in `class
  TestMatchExpression` (search that name, in both `tests/test_parser.py`
  and this file's own new tests) updated to match the new field count —
  including a `None` for every arm that has no guard.
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

## 2. Standard library: `nth_catalan` — the k-th Catalan number by position

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

## 3. Language: flat list patterns in `match` arms (`[a, b] => a + b`)

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

**Ordering note:** task 1 (guards) is still ahead of this in the queue
and may land first, changing `MatchArm`'s exact field list and
`_match_arm`'s exact shape — adapt to whatever the merged code actually
looks like, the same way `nth_triangular` (#313) adapted to
`is_octagonal` landing first. The sketch below is grounded in **today's**
actual code (verified by reading
`cinder/ast_nodes.py`/`cinder/parser.py`/`cinder/interpreter.py`
directly, post-#312, pre-task 1), so the *principle* is exact even if
the exact diff has shifted: detect a leading `[` in
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

## 4. Standard library: `cartesian_product` — the Cartesian product of N lists

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

## 5. Language: range patterns in `match` arms (`1..10 => "small"`)

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

**Ordering note:** tasks 1 (guards) and 3 (flat list patterns) are also
queued and may land first, adding a `guard`/`list_pattern`-shaped field to
`MatchArm`/`_match_arm`/`_evaluate_match` alongside the ones shown below —
adapt to whatever the merged code actually looks like, the same way
`nth_triangular` adapted to `is_octagonal` landing first. The code below is
grounded in **today's** actual code (verified by reading
`cinder/ast_nodes.py`/`cinder/parser.py`/`cinder/interpreter.py` directly,
post-#312, pre-tasks 2/4): add a fifth pattern *kind*, mutually exclusive
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

## 6. Standard library: `nth_pentagonal` — the k-th pentagonal number by position

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
