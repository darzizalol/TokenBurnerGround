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
## 1. Standard library: `nth_pentagonal` — the k-th pentagonal number by position [claimed 2026-08-25T20:14:50Z]

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

## 2. Language: negative literal patterns in `match` arms (`-5 => "neg"`)

Build: restocking the backlog back to 6 tasks now that guards in `match`
arms was closed after three failed review rounds (see `## Graveyard`
below), dropping the queue from 6 to 5 (3-breadth/2-depth: `nth_catalan`,
`cartesian_product`, `nth_pentagonal` vs. flat list patterns, range
patterns). This restocks with depth to restore 3-breadth/3-depth parity,
continuing the alternation the guards task itself was standing in for.
Rather than re-attempt guards immediately — its postmortem below
identifies a real fix but a materially different implementation strategy
than what was tried three times, and re-queuing it cold risks a fourth
failed round — this task picks up a smaller, unrelated gap that task 1
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
after the guards graveyard entry. **Ordering note:** if task 1 (range
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
patterns (`-10..0`, task 1's own explicitly out-of-scope case) are not
addressed by this task either — that stays a real gap for range patterns
specifically, since a range pattern's bounds are parsed by task 1's own
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

## 3. Standard library: `power_set` — every subset of a list

Build: restocking the backlog from 4 back to 6 tasks now that
`nth_catalan` (PR #315) and flat list patterns in `match` arms (PR #316)
both landed since the last grooming pass, dropping the queue to
2-breadth/2-depth (`cartesian_product`, `nth_pentagonal` vs. range
patterns, negative literal patterns) at the time this task was written.
`cartesian_product` has since landed too, via PR #317, and the backlog
was renumbered accordingly — this task and task 5 below restock one of
each kind to restore 3-breadth/3-depth parity at the 6-task ceiling.
Cinder's collection-helper cluster already answers "every ordered
combination of one element from each of N lists" (`cartesian_product`,
merged via PR #317) but has no way to answer the adjacent
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
`def _enumerate`, itself already right after `_cartesian_product`, which
landed via PR #317; `itertools` is already imported at the top of this
module — no new import needed):
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
empty tuple). Also register the new dict entry (search `"enumerate":
_enumerate,` — already directly preceded by `"cartesian_product":
_cartesian_product,` since PR #317 landed — and place `"power_set":
_power_set,` directly after it).

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
`cartesian_product`, see current line numbers), `tests/test_builtins.py`
(model on `class TestEnumerate`/`class TestCartesianProduct`, search
those names, for the list-validation and arity-error test shapes). Once merged, `README.md`'s
Builtins bullet needs `power_set` added near `cartesian_product`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Language: literal elements in list patterns (`[0, b] => ...`)

Build: restocking the second of two slots this grooming pass added to
restore the backlog to its 6-task, 3-breadth/3-depth ceiling (see task 4
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
expressions, not negative literals (unless task 3 above has already
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

## 5. Standard library: `nth_hexagonal` — the k-th hexagonal number by position

Build: restocking the backlog back to its 6-task, 3-breadth/3-depth
ceiling now that `cartesian_product` (PR #317) landed, dropping the queue
to 5 tasks (2-breadth/3-depth: `nth_pentagonal`, `power_set` vs. range
patterns, negative literal patterns, literal list elements). This
restocks with breadth to restore parity, per `PROJECT.md`'s alternation
policy. `is_hexagonal` already exists as a membership test, but Cinder
has no way to ask "what is the k-th hexagonal number" the way it can for
triangular numbers (`nth_triangular`, PR #313), Fibonacci
(`nth_fibonacci`), primes (`nth_prime`), and Lucas numbers (`nth_lucas`)
— the exact same "value-returning sibling of an `is_*` membership test"
pattern `nth_triangular` and task 2 above (`nth_pentagonal`, still
unclaimed) already establish for the figurate-number cluster, just for
its third member. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_hexagonal(5));'
# -> <eval>:1:7: undefined name 'nth_hexagonal'
```

**Ordering note:** if task 2 (`nth_pentagonal`) has already landed by the
time this task is claimed, register `nth_hexagonal` directly after
`nth_pentagonal` instead of after `nth_triangular` — same adaptive
placement every sibling task in this backlog already uses.

Add to `cinder/builtins.py`, registered right after `_nth_triangular`
(search `def _nth_triangular`, immediately before `_is_prime` — or
directly after `_nth_pentagonal` if task 2 has already landed):
```python
def _nth_hexagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_hexagonal", arguments, 1, line, column)
    value = _require_int("nth_hexagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_hexagonal() requires a positive integer, domain error", line, column
        )
    return value * (2 * value - 1)
```
The closed form `H(k) = k(2k - 1)` is the standard 1-indexed hexagonal
number formula (`H(1) = 1, H(2) = 6, H(3) = 15, ...`), matching
`_is_hexagonal`'s own derivation (`cinder/builtins.py`, search `def
_is_hexagonal`: it tests `8 * value + 1` for a perfect square with an
odd-mod-4 root, the standard membership test for this same closed form).
This mirrors `_nth_triangular`'s and `_nth_pentagonal`'s shape exactly
(arity check, int check, domain check, one-line closed-form return) — a
thin, direct composition, not a new algorithm. Also register the new
dict entry (search `"nth_triangular": _nth_triangular,`, add
`"nth_hexagonal": _nth_hexagonal,` directly after it — or directly after
`"nth_pentagonal": _nth_pentagonal,` if task 2 has already landed).

Acceptance criteria:
- `nth_hexagonal(1);` is `1`, `nth_hexagonal(2);` is `6`,
  `nth_hexagonal(3);` is `15`, `nth_hexagonal(4);` is `28`,
  `nth_hexagonal(5);` is `45` — the first five hexagonal numbers.
- `nth_hexagonal(10);` is `190`.
- `nth_hexagonal(100);` is `19900`.
- `is_hexagonal(nth_hexagonal(n));` is `true` for every `n` from `1` to
  `100` — confirms the closed form agrees with the existing membership
  predicate across a wide range, the same cross-check `nth_triangular`'s
  and `nth_pentagonal`'s own acceptance criteria used.
- `nth_hexagonal(0);` and `nth_hexagonal(-3);` both raise
  `CinderRuntimeError` matching `"nth_hexagonal() requires a positive
  integer, domain error"`.
- `nth_hexagonal(2.0);` raises `CinderRuntimeError` matching
  `"nth_hexagonal() requires an int, got float"`.
- `nth_hexagonal(true);` raises `CinderRuntimeError` matching
  `"nth_hexagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `nth_triangular`/
`nth_pentagonal`, see current line numbers — shift depending on which
sibling tasks land first), `tests/test_builtins.py` (model on `class
TestNthTriangular`, search that name, including its `is_triangular`-
agreement-style cross-check test, adapted to `is_hexagonal`). Once
merged, `README.md`'s Builtins bullet needs `nth_hexagonal` added near
`nth_triangular`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 6. Language: rest capture in list patterns (`[a, ...rest] => ...`)

Build: restocking the sixth and final slot to bring the backlog back to its
6-task, 3-breadth/3-depth ceiling now that range patterns in `match` arms
landed via PR #318 (dropping the queue from 6 to 5: `nth_pentagonal`,
`power_set`, `nth_hexagonal` — breadth, 3 — vs. negative literal patterns,
literal list elements — depth, 2). Restocking with a depth task restores
parity. Flat list patterns (PR #316) can only test a list subject's *exact*
length (`[a, b]` matches only a 2-element list) — Cinder's `let`/assignment
destructuring already has a "rest capture" escape hatch for this same shape
mismatch (`let [a, ...rest] = xs;`, `cinder/parser.py`'s
`_destructure_list_pattern`/`_destructure_rest_name`), but match list
patterns have no equivalent: there is no way to write a list-pattern arm that
matches "at least N elements, bind the first N, capture everything else."
Verify the gap, on current `main`:
```sh
python3 -m cinder.cli eval 'print(match ([1, 2, 3]) { [a, ...rest] => rest, _ => "no" });'
# -> <eval>:1:31: expected an identifier or '_' inside list pattern, found '...'
```

**Scope note:** rest capture must be the last element in a list pattern
(`[a, ...rest]` is valid, `[...rest, a]` is not — matching
`_destructure_list_pattern`'s own "rest element must be last" restriction)
and only one rest element is allowed per pattern. `...rest` binds the
remaining elements as a new list (a copy via slicing, not a view). `..._`
(discarding the captured tail while still requiring "at least N elements")
is valid too, mirroring how a bare element can already be `_` to discard —
unlike a discarded plain element (which parses to `None`), a discarded rest
is kept as the literal name `"_"` so the interpreter can tell "no rest
capture" (`None`) apart from "rest capture, discarded" (`"_"`); see below.
This task does not touch literal list elements (task 4 above, still
unclaimed as of this writing) — if that task has already landed by the time
this one is claimed, follow the **Ordering note** below instead of the code
shown.

**Ordering note:** if literal elements in list patterns (task 4) has already
landed by the time this task is claimed, `_match_list_pattern_entry` (not
`_match_list_pattern_name`) will already exist and return `str | Expr | None`
per element — add the `DOT_DOT_DOT` branch to `_match_list_pattern` (the
caller) exactly as shown below, just calling `_match_list_pattern_entry` in
place of `_match_list_pattern_name` for the non-rest branches; the
interpreter-side length check (`>=` instead of `==` when a rest is present)
and rest-slice binding are unaffected by which element parser is in place.

Today's `_match_list_pattern`/`_match_list_pattern_name`
(`cinder/parser.py`, search `def _match_list_pattern`) only ever parse a
fixed-length list of identifier/`_` entries and never check for
`TokenType.DOT_DOT_DOT`. Widen it to optionally end in a rest capture,
mirroring `_destructure_list_pattern`'s own rest-checking loop shape:
```python
    def _match_list_pattern(self) -> "tuple[list[str | None], str | None]":
        self._advance()  # consume '['
        names: "list[str | None]" = []
        rest: "str | None" = None
        if not self._check(TokenType.RBRACKET):
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._match_list_pattern_rest_name()
            else:
                names.append(self._match_list_pattern_name())
            while self._check(TokenType.COMMA):
                self._advance()
                if rest is not None:
                    token = self._peek()
                    raise ParseError(
                        f"rest capture must be last in list pattern, found {self._describe(token)}",
                        token.line,
                        token.column,
                    )
                if self._check(TokenType.DOT_DOT_DOT):
                    rest = self._match_list_pattern_rest_name()
                else:
                    names.append(self._match_list_pattern_name())
        self._consume(TokenType.RBRACKET, "']' after list pattern")
        return names, rest

    def _match_list_pattern_rest_name(self) -> str:
        self._advance()  # consume '...'
        token = self._peek()
        if token.type != TokenType.IDENTIFIER:
            raise ParseError(
                f"expected an identifier or '_' after '...' in list pattern, "
                f"found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._advance()
        return token.lexeme  # kept as "_" itself when discarded, see scope note
```
`_match_arm` (`cinder/parser.py`, search `def _match_arm`) currently does
`list_pattern = self._match_list_pattern()` then constructs
`MatchArm(None, body, None, list_pattern, None)` — update to unpack the new
two-tuple and pass the rest name into `MatchArm`'s new field:
```python
        if self._check(TokenType.LBRACKET):
            list_pattern, list_rest = self._match_list_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return [MatchArm(None, body, None, list_pattern, None, list_rest)]
```
`MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) needs a sixth
field, appended after `range_pattern` (appending, not inserting, keeps every
existing positional `MatchArm(...)` call site elsewhere in the parser valid
without touching them):
```python
    list_rest: "str | None" = None
```
`_evaluate_match` (`cinder/interpreter.py`, search `def _evaluate_match`)'s
`arm.list_pattern is not None` branch currently requires
`len(subject) != len(arm.list_pattern)` to fail the arm; widen it to accept
"at least" when a rest is present, and bind the tail:
```python
            if arm.list_pattern is not None:
                min_len = len(arm.list_pattern)
                length_ok = (
                    len(subject) >= min_len if arm.list_rest is not None
                    else len(subject) == min_len
                )
                if not isinstance(subject, list) or not length_ok:
                    continue
                arm_env = Environment(env)
                for name, item in zip(arm.list_pattern, subject):
                    if name is not None:
                        arm_env.define(name, item)
                if arm.list_rest is not None and arm.list_rest != "_":
                    arm_env.define(arm.list_rest, subject[min_len:])
                return self.evaluate(arm.body, arm_env)
```

Acceptance criteria:
- `match ([1, 2, 3]) { [a, ...rest] => rest, _ => "no" };` is `[2, 3]`.
- `match ([1]) { [a, ...rest] => rest, _ => "no" };` is `[]` — rest captures
  an empty tail when the subject is exactly as long as the fixed prefix.
- `match ([1, 2]) { [a, b, ...rest] => rest, _ => "no" };` is `[]`, and the
  same arm against `[1, 2, 3]` gives `[3]`.
- `match ([]) { [a, ...rest] => "yes", _ => "no" };` is `"no"` — a rest
  pattern still requires at least as many elements as its fixed prefix; it
  does not make the prefix optional.
- `match ([1, 2, 3]) { [a, ..._] => a, _ => "no" };` is `1` — a discarded
  rest (`..._`) still allows the "at least N" match without binding
  anything.
- `match ("ab") { [a, ...rest] => "yes", _ => "no" };` is `"no"` — a
  non-list subject falls through without raising, same as today's
  fixed-length list patterns.
- `match ([1, 2]) { [a, b] => a + b, _ => 0 };` is still `3` — a list
  pattern with no rest capture is unaffected (`arm.list_rest` is `None`, so
  `length_ok` is the same exact-length check as before).
- `match (x) { [a, ...rest, b] => 0, _ => 1 };` (rest not last) raises
  `ParseError` matching `"rest capture must be last in list pattern, found
  'b'"`.
- `match (x) { [...5] => 0, _ => 1 };` (rest not followed by an identifier
  or `_`) raises `ParseError` matching `"expected an identifier or '_'
  after '...' in list pattern, found '5'"`.
- `shape(parse('match (x) { [a, ...rest] => rest, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's 6-tuple ending in `"rest"` —
  confirms `list_rest` threads through to the AST; a plain `[a, b]` pattern's
  shape ends in `None`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`), `cinder/parser.py`
(`_match_list_pattern`, new `_match_list_pattern_rest_name`, `_match_arm`),
`cinder/interpreter.py` (`_evaluate_match`), `tests/test_parser.py` (the
`shape()` helper's `MatchExpr` branch — search `arm.list_pattern,` inside
it — needs a 6th tuple element, `arm.list_rest`, appended; extend `class
TestMatchExpression`), `tests/test_interpreter.py` (extend `class
TestMatchExpression` with the end-to-end cases above). Once merged,
`README.md`'s `match` expression bullet needs "rest capture" dropped from
its "not supported yet" list and a short description added near the
flat-list-pattern description, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs refreshing —
leave both to the Architect's next grooming pass, not this task.

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
