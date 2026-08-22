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

## 1. Language: multiple `for` clauses in list/map comprehensions (`[x + y for x in xs for y in ys]`) [claimed 2026-08-22T14:02:48Z]

Build: the depth task after task 5's breadth work (`is_lucas_number`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that comma-separated expression statements has landed via PR
#289, dropping the count to the 5-task floor. Both comprehension forms
(`_list_comprehension`/`_map_comprehension`, `cinder/parser.py`) already
parse exactly one `for` clause with an optional trailing `if` filter — a
single loop variable (or list/map destructuring pattern), one `in
<iterable>`, one optional `if <condition>`. Python-style comprehensions
allow chaining multiple `for` clauses to iterate a cartesian product
(`[x + y for x in xs for y in ys]`, outer-to-inner in written order, each
clause optionally filtered by its own `if`, later clauses' conditions and
bodies able to see earlier clauses' loop variables), but Cinder has no
second-clause support at all today — the parser stops dead at the first
extra `for`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print([x + y for x in [1, 2] for y in [10, 20]]);'
# -> <eval>:1:30: expected ']' after list comprehension, found 'for'
python3 -m cinder.cli eval 'print({x: y for x in ["a", "b"] for y in [1, 2]});'
# -> <eval>:1:33: expected '}' after map comprehension, found 'for'
```
This is a guaranteed `ParseError` today for every comprehension with more
than one `for` clause, so no currently-valid Cinder program's meaning
changes.

Add a new frozen dataclass `ComprehensionClause` to `cinder/ast_nodes.py`,
right before `ListComprehension`, holding exactly the per-clause fields
`ListComprehension`/`MapComprehension` already have individually:
```python
@dataclass(frozen=True)
class ComprehensionClause:
    var_name: "str | None"
    iterable: "Expr"
    condition: "Expr | None"
    line: int
    column: int
    names: "list | None" = None
    rest: "str | None" = None
    is_map: bool = False
```
Give `ListComprehension` and `MapComprehension` one new field each,
appended last (after `is_map`, defaulting to `None`) so every existing
positional construction call site is unaffected, the same technique
`FnExpr.name`/`RangeExpr.inclusive` already used to extend a node without
breaking callers:
```python
    extra_clauses: "list[ComprehensionClause] | None" = None
```
In `cinder/parser.py`, extract the "parse one `for`-clause" logic
`_list_comprehension`/`_map_comprehension` each already inline (the
`var_name`/`names`/`rest`/`is_map` branch, `self._consume(TokenType.IN,
...)`, `iterable = self._ternary()`, the optional `if` block) into one
shared helper used by both, and by both the primary clause and any extra
ones:
```python
    def _comprehension_clause(self) -> "ComprehensionClause":
        var_name = None
        names = None
        rest = None
        is_map = False
        if self._check(TokenType.LBRACKET):
            names, rest = self._destructure_list_pattern()
        elif self._check(TokenType.LBRACE):
            names, rest = self._destructure_map_pattern()
            is_map = True
        else:
            var_name = self._consume(TokenType.IDENTIFIER, "loop variable after 'for'").lexeme
        self._consume(TokenType.IN, "'in' after loop variable")
        iterable = self._ternary()
        condition = None
        if self._check(TokenType.IF):
            self._advance()
            condition = self._ternary()
        return ComprehensionClause(
            var_name, iterable, condition, self._previous().line, self._previous().column,
            names=names, rest=rest, is_map=is_map,
        )
```
Then in both `_list_comprehension` (after its existing `self._advance()  #
consume 'for'` and before `self._consume(TokenType.RBRACKET, ...)`) and
`_map_comprehension` (mirrored, before `self._consume(TokenType.RBRACE,
...)`), replace the inlined per-clause parsing with one call to
`_comprehension_clause()` for the primary clause (unpacking its fields
into the existing `var_name`/`names`/`rest`/`is_map`/`iterable`/`condition`
locals the rest of each method already uses to build the `ListComprehension`/
`MapComprehension` constructor call — no other line in either method
changes), followed by a loop collecting any further clauses:
```python
        extra_clauses = []
        while self._check(TokenType.FOR):
            self._advance()  # consume 'for'
            extra_clauses.append(self._comprehension_clause())
```
and pass `extra_clauses=extra_clauses or None` into both constructor
calls, alongside the existing `names=`/`rest=`/`is_map=` keyword
arguments.

In `cinder/interpreter.py`, both `_evaluate_list_comprehension` and
`_evaluate_map_comprehension` currently inline "evaluate the iterable,
type-check it into `items`, loop binding one item per iteration, skip on
a falsy `condition`" as one flat loop. Extract the shared "resolve one
clause's items" and "bind one item into a clause's pattern" pieces (the
existing `isinstance(iterable, dict)`/`isinstance(iterable, (list, str))`
type-check block and the existing `if expr.is_map: ... elif expr.names is
not None: ... else: ...` binding block, both already duplicated verbatim
between the two methods) into two small helpers taking a
`ComprehensionClause`-shaped object (both `ListComprehension`/
`MapComprehension` and `ComprehensionClause` itself already have the
right attribute names, so no adapter is needed), then add one recursive
helper that walks a full clause list — the primary clause plus
`extra_clauses` — running the innermost callback once every clause's
binding and filter have passed:
```python
    def _comprehension_items(self, clause, env):
        iterable = self.evaluate(clause.iterable, env)
        if isinstance(iterable, dict):
            return list(iterable.keys())
        if isinstance(iterable, (list, str)):
            return list(iterable)
        raise CinderRuntimeError(
            f"'for'-in loop requires a list, string, or map, got {type_name(iterable)}",
            clause.line, clause.column,
        )

    def _bind_comprehension_clause(self, clause, item, env):
        if clause.is_map:
            self._bind_map_destructure(env, clause.names, clause.rest, item, clause.line, clause.column)
        elif clause.names is not None:
            self._bind_list_destructure(env, clause.names, clause.rest, item, clause.line, clause.column)
        else:
            env.define(clause.var_name, item)

    def _run_comprehension_clauses(self, clauses, index, env, on_match):
        clause = clauses[index]
        for item in self._comprehension_items(clause, env):
            iter_env = Environment(env)
            self._bind_comprehension_clause(clause, item, iter_env)
            if clause.condition is not None and not is_truthy(
                self.evaluate(clause.condition, iter_env)
            ):
                continue
            if index + 1 == len(clauses):
                on_match(iter_env)
            else:
                self._run_comprehension_clauses(clauses, index + 1, iter_env, on_match)
```
`_evaluate_list_comprehension` becomes: build the primary `ComprehensionClause`
from `expr`'s own flat fields, prepend it to `expr.extra_clauses or []`,
and call `_run_comprehension_clauses` with an `on_match` that appends
`self.evaluate(expr.element, final_env)` to the result list.
`_evaluate_map_comprehension` mirrors it, with an `on_match` that
evaluates `expr.key`/`expr.value`, runs the existing `_is_valid_key`
check unchanged, and assigns into the result dict — later clause
combinations overwrite earlier ones on a key collision, matching plain
Python dict-comprehension semantics and requiring no new conflict logic.

Acceptance criteria:
- `print([x + y for x in [1, 2] for y in [10, 20]]);` prints
  `[11, 21, 12, 22]` — cartesian product, first `for` outermost, matching
  Python's own iteration order.
- `print([[x, y] for x in [1, 2] for y in [1, 2] if x != y]);` prints
  `[[1, 2], [2, 1]]` — a second clause's `if` filters using that clause's
  own loop variable.
- `print({x: y for x in ["a", "b"] for y in [1, 2]});` prints
  `{"a": 2, "b": 2}` — a later clause combination overwrites an earlier
  one on a map-key collision, the same "last write wins" rule plain map
  literals already have.
- `print([x for x in [1, 2] for y in []]);` prints `[]` — an empty inner
  iterable yields no results at all, regardless of the outer iterable.
- `print([x + y + z for x in [1] for y in [10] for z in [100]]);` prints
  `[111]` — three clauses deep, not just two.
- `print([a + b for [a] in [[1], [2]] for b in [10, 20]]);` prints
  `[11, 21, 12, 22]` — a destructuring pattern in a non-final clause
  still binds correctly for the clauses after it.
- `print([[x, y] for x in [1, 2, 3] if x > 1 for y in [10, 20]]);` prints
  `[[2, 10], [2, 20], [3, 10], [3, 20]]` — a condition on a non-final
  clause filters before any later clause runs at all, not just before
  that clause's own body.
- `print([x for x in [1, 2, 3]]);` and `print({x: x * 2 for x in [1, 2]});`
  (single-clause forms) are unchanged — still print `[1, 2, 3]` and
  `{1: 2, 2: 4}` respectively, confirming `extra_clauses=None` regression
  behavior is identical to before this task.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `ComprehensionClause`, new
`extra_clauses` field on both existing comprehension nodes),
`cinder/parser.py` (`_comprehension_clause` new shared helper,
`_list_comprehension`/`_map_comprehension` updated to use it plus a
trailing `while self._check(TokenType.FOR)` loop), `cinder/interpreter.py`
(`_comprehension_items`/`_bind_comprehension_clause`/
`_run_comprehension_clauses` new helpers, `_evaluate_list_comprehension`/
`_evaluate_map_comprehension` rewritten atop them),
`tests/test_parser.py` (the `shape()` helper's existing
`ListComprehension`/`MapComprehension` branches, search `"ListComprehension"`/
`"MapComprehension"`, need an `extra_clauses` entry added to their tuples,
plus every existing shape-assertion call site for these two nodes updated
to match; add new parser-shape tests for a two-clause comprehension),
`tests/test_interpreter.py` (existing `class TestListComprehension`/
`class TestMapComprehension`, search those names, stay green unchanged as
the single-clause regression proof; add new test methods for the
multi-clause cases in the acceptance criteria above, in the same
classes). Once merged, `README.md`'s comprehension-related bullets need a
multi-clause mention added, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming
pass, not this task.

---

## 2. Standard library: `is_subsequence` — ordered-but-not-contiguous membership between two strings

Build: the breadth task after task 5's depth work (multiple `for` clauses
in list/map comprehensions) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `additive_persistence`
has landed via PR #290, dropping the count to the 5-task floor.
`is_rotation(a, b)` and `is_anagram(a, b)` (`cinder/builtins.py`) already
cover two of the classic two-string relationship predicates — "same
characters, cyclically shifted" and "same multiset of characters,
any order" — but neither answers the third and most common one: does
`a`'s characters all appear in `b`, in the same relative order, without
requiring them to be contiguous (e.g. `"ace"` is a subsequence of
`"abcde"`, `"aec"` is not — same three characters, wrong order).
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_subsequence("ace", "abcde"));'
# -> CinderRuntimeError: undefined name 'is_subsequence'
```

Add to `cinder/builtins.py`, registered right after `_is_rotation`
(search `def _is_rotation`, immediately before `_is_permutation`):
```python
def _is_subsequence(arguments: list, line: int, column: int) -> object:
    _require_arity("is_subsequence", arguments, 2, line, column)
    string1, string2 = arguments
    if not isinstance(string1, str):
        raise CinderRuntimeError(
            f"is_subsequence() requires a string as its first argument, got {type_name(string1)}",
            line, column,
        )
    if not isinstance(string2, str):
        raise CinderRuntimeError(
            f"is_subsequence() requires a string as its second argument, got {type_name(string2)}",
            line, column,
        )
    remaining = iter(string2)
    return all(character in remaining for character in string1)
```
This mirrors `_is_rotation`'s own two-string validation shape exactly
(search `def _is_rotation`) — two positional string arguments, each
checked and error-reported independently so a caller always learns
which argument was wrong. The body itself is the standard Python
two-pointer subsequence idiom expressed as a generator: `remaining` is
a single shared iterator over `string2`, and `character in remaining`
advances it past (and consumes) every character up to and including the
first match, so each successive lookup for `string1`'s next character
only ever searches the *unconsumed* tail of `string2` — a plain `in`
check against a fresh `string2` for every character would ignore
ordering entirely, matching `"ba"` against `"ab"` incorrectly. `all(...)`
short-circuits on the first character of `string1` that can't be found
in what's left, so no accumulator or index bookkeeping is needed; this
is the same "concise stdlib idiom over hand-rolled bookkeeping" choice
`_merge`'s two-line body already makes. The empty-string cases fall out
of this shape for free with no special-casing: `all()` over an empty
`string1` is vacuously `True` regardless of `string2` (the empty string
is a subsequence of anything, including the empty string), and a
non-empty `string1` against an empty `string2` is `False` at the first
character since an iterator over `""` yields nothing for `in` to match.
Also register the new dict entry (search `"is_rotation": _is_rotation,`,
add `"is_subsequence": _is_subsequence,` directly after it).

Acceptance criteria:
- `is_subsequence("ace", "abcde");` is `true` — the canonical example.
- `is_subsequence("aec", "abcde");` is `false` — same three characters as
  above, wrong relative order.
- `is_subsequence("", "abcde");` is `true` — the empty string is a
  subsequence of anything.
- `is_subsequence("abcde", "");` is `false` — nothing but the empty
  string is a subsequence of the empty string.
- `is_subsequence("", "");` is `true`.
- `is_subsequence("abcde", "abcde");` is `true` — a string is always a
  subsequence of itself.
- `is_subsequence("aa", "a");` is `false` — needs two `"a"`s available,
  only one exists.
- `is_subsequence("aa", "aba");` is `true` — the two `"a"`s need not be
  contiguous in `string2`.
- `is_subsequence("ba", "ab");` is `false` — same multiset of characters
  `is_anagram` would call equal, but wrong order for `is_subsequence`.
- `is_subsequence(1, "abc");` raises `CinderRuntimeError` matching
  `"is_subsequence() requires a string as its first argument, got int"`.
- `is_subsequence("abc", 1);` raises `CinderRuntimeError` matching
  `"is_subsequence() requires a string as its second argument, got int"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_rotation`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsRotation`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_subsequence`
added near `is_rotation`/`is_anagram`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s roadmap paragraph needs this moved
from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 3. Language: a map pattern nested inside a list pattern (`let [a, {b, c}] = [1, {"b": 2, "c": 3}];`)

Build: the depth task after task 5's breadth work (`is_subsequence`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that map concatenation via `+` has landed via PR #291, dropping
the count to the 5-task floor. Nested list-in-list destructuring patterns
landed via PR #273, and task 2 above queues the map-in-map half. The one
remaining corner of the nesting matrix this doesn't touch is a *map*
pattern nested inside a *list* pattern — today `_destructure_list_pattern_entry`
(`cinder/parser.py`) only recognizes a nested `[` (recursing into another
list pattern); a `{` in that same position is a guaranteed `ParseError`.
Verify the gap:
```sh
python3 -m cinder.cli eval 'let [a, {b, c}] = [1, {"b": 2, "c": 3}]; print(a); print(b); print(c);'
# -> <eval>:1:9: expected identifier in destructuring pattern, found '{'
```
This is a guaranteed `ParseError` today (a `{` can never appear where
`_destructure_list_pattern_entry` expects `[`/an identifier/a hole), so no
currently-valid Cinder program's meaning changes. This is exactly the case
`tests/test_interpreter.py`'s `TestDestructureNestedListPattern.
test_map_pattern_nested_in_list_still_rejected` currently pins as
permanently rejected — that test's premise flips with this task and must
be replaced (see Acceptance criteria).

Add a nested-`{` branch to `_destructure_list_pattern_entry`, alongside its
existing nested-`[` branch (search `def _destructure_list_pattern_entry`):
```python
        elif self._check(TokenType.LBRACE):
            nested_names, nested_rest = self._destructure_map_pattern()
            pattern = (nested_names, nested_rest, True)
            if self._check(TokenType.EQ):
                self._advance()
                default = self._ternary()
                return pattern, default
            if seen_default:
                token = self._peek()
                raise ParseError(
                    "element without a default value follows an element with one "
                    "in destructuring pattern",
                    token.line,
                    token.column,
                )
            return pattern, None
```
This mirrors the existing nested-`[` branch's own EQ/`seen_default`
handling exactly, but tags its pattern tuple with a trailing `True` —
deliberately a 3-element tuple, not the 2-element `(nested_names,
nested_rest)` the nested-`[` branch and the plain-assignment form's own
`_destructure_assign_pattern` (`cinder/parser.py`) already produce and
will keep producing unchanged. The trailing element is a length-based tag,
not a `dataclass`, kept consistent with how this codebase already threads
plain tuples through the destructuring machinery elsewhere (`(key,
binding, default)` in map patterns, `(name, default)` in list patterns).
Then teach `_bind_list_destructure` (`cinder/interpreter.py`) to recognize
the tagged shape, at both of its existing `isinstance(name, tuple):`
checks (one in the `rest is not None` branch, one below it — search
`isinstance(name, tuple)`, mirror the same change at each):
```python
                if isinstance(name, tuple) and len(name) == 3:
                    nested_names, nested_rest, _ = name
                    self._bind_map_destructure(
                        env, nested_names, nested_rest, item, line, column, use_assign
                    )
                elif isinstance(name, tuple):
                    nested_names, nested_rest = name
                    self._bind_list_destructure(
                        env, nested_names, nested_rest, item, line, column, use_assign
                    )
                elif name is not None:
                    self._bind_destructure_name(env, name, item, line, column, use_assign)
```
Because every existing 2-tuple production site (the nested-`[` branch, and
`_destructure_assign_pattern`'s own nested-list handling for the
plain-assignment form) is untouched, this task cannot regress any already-
landed nested-list-in-list behavior — the `len(name) == 3` check only ever
matches the new branch's own output. The plain-assignment form
(`[a, {b}] = expr;`) stays out of scope and keeps raising exactly as
today, for the same structural reason the equivalent list-in-map task
leaves it out of scope: `_destructure_assign_pattern` parses its pattern
from an already-built `ListLiteral`'s elements, handling only `Identifier`/
`Spread`/nested-`ListLiteral` shapes, with everything else (including a
`MapLiteral` element) falling through to its existing "invalid assignment
target" error — no new branch needed there, and none should be added.

Because `_destructure_list_pattern_entry` is the single shared entry point
every list-pattern call site funnels through — `let`, plain assignment
(list-in-list only, per above), `for`-loops, function params, and both
comprehension forms — nesting a map pattern works for free across all of
them except plain assignment, the same "pure plumbing" result the
nested-list task and the map-pattern rest element task both got from
their own shared helpers.

Acceptance criteria:
- `let [a, {b, c}] = [1, {"b": 2, "c": 3}]; print(a); print(b); print(c);`
  prints `1`, `2`, `3`.
- `let [{x, y}, a] = [{"x": 1, "y": 2}, 3]; print(x); print(y); print(a);`
  prints `1`, `2`, `3` — nested pattern in the first position works too,
  not just the last.
- `let [a, [b, {c}]] = [1, [2, {"c": 3}]]; print(a); print(b); print(c);`
  prints `1`, `2`, `3` — a map pattern nested inside a nested *list*
  pattern, confirming the two kinds of nesting compose.
- `let [a, {b, ...brest}] = [1, {"b": 2, "c": 3, "d": 4}]; print(brest);`
  prints `{"c": 3, "d": 4}` — a rest element inside the nested map pattern.
- `let [a, {b, c = 0}] = [1, {"b": 2}]; print(c);` prints `0` — a default
  value on a missing key inside the nested map pattern.
- `let [a, {b}] = [1, 2];` raises `CinderRuntimeError` matching `"cannot
  destructure int as a map"` — a non-map value at a nested position.
- `let [a, {b}] = [1, {}];` raises `CinderRuntimeError` matching
  `"destructuring pattern expects key 'b', not found in map"` — the
  existing missing-key error still fires correctly from inside a nested
  pattern.
- `for [a, {b}] in [[1, {"b": 2}], [3, {"b": 4}]] { print(a); print(b); }`
  prints `1`, `2`, `3`, `4` — the `for`-loop form.
- `fn f([a, {b}]) { return a + b; } print(f([1, {"b": 2}]));` prints `3` —
  the function-parameter form.
- `print([a + b for [a, {b}] in [[1, {"b": 2}], [3, {"b": 4}]]]);` prints
  `[3, 7]` — the comprehension loop-variable form.
- `[a, {b}] = [1, {"b": 2}];` still raises `ParseError` matching `"invalid
  assignment target"` — the plain-assignment form stays unsupported, out
  of scope for this task.
- `let {a, b: [c, d]} = {"a": 1, "b": [2, 3]};` still raises `ParseError`
  matching `"expected identifier in destructuring pattern, found '['"` —
  a list nested inside a map pattern (the mirror-direction gap) stays
  unsupported too, confirming this task didn't touch
  `_destructure_map_pattern_entry`.
- `tests/test_interpreter.py`'s `TestDestructureNestedListPattern.
  test_map_pattern_nested_in_list_still_rejected` is removed (its premise
  — that this syntax always raises — is exactly what this task makes
  false) and replaced with a new test class covering the positive cases
  above.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_list_pattern_entry`),
`cinder/interpreter.py` (`_bind_list_destructure`), `tests/test_parser.py`
(add a parser-shape test mirroring `test_list_destructure_assignment_nested_pattern_parses`,
confirming a `let`-form nested map pattern parses into the `(nested_names,
nested_rest, True)` shape), `tests/test_interpreter.py` (remove
`test_map_pattern_nested_in_list_still_rejected` from
`TestDestructureNestedListPattern`, add a new `class
TestDestructureMapPatternNestedInList` mirroring
`TestDestructureNestedListPattern`'s own style, placed near it). Once
merged, `README.md`'s destructuring bullet, its "Status & roadmap"
section, and `PROJECT.md`'s roadmap paragraph all need updating to note
this landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 4. Standard library: `is_hexagonal` — the third figurate-number membership predicate after `is_triangular`/`is_pentagonal`

Build: the breadth task after task 5's depth work (a map pattern nested
inside a list pattern) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_pentagonal` has
landed via PR #292, dropping the count to the 5-task floor.
`is_triangular`/`is_pentagonal` (`cinder/builtins.py`) already test
membership in the triangular (`0, 1, 3, 6, 10, ...`) and pentagonal
(`1, 5, 12, 22, 35, ...`) figurate-number sequences, each via a
closed-form `math.isqrt`-based identity rather than an accumulating
loop; the hexagonal numbers (`1, 6, 15, 28, 45, 66, ...`, `H(k) = k(2k
- 1)`) are the natural third member of that cluster and nothing in
Cinder tests membership in them today. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_hexagonal(15));'
# -> CinderRuntimeError: undefined name 'is_hexagonal'
```

Add to `cinder/builtins.py`, registered right after `_is_pentagonal`
(search `def _is_pentagonal`, immediately before `_is_prime`):
```python
def _is_hexagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_hexagonal", arguments, 1, line, column)
    value = _require_int("is_hexagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 8 * value + 1
    root = math.isqrt(candidate)
    return root * root == candidate and root % 4 == 3
```
This mirrors `_is_triangular`/`_is_pentagonal`'s exact shape: solving
`H(k) = k(2k - 1) = n` for `k` via the quadratic formula gives `k = (1 +
sqrt(8n + 1)) / 4`, so `n` is hexagonal iff `8n + 1` is a perfect square
whose exact integer root additionally satisfies `root % 4 == 3` (the
condition that makes `(1 + root)` divisible by 4, so `k` comes out an
integer) — the same "closed-form perfect-square identity plus one
modular-residue check" technique `is_pentagonal` already uses for its
own `root % 6 == 5` condition (triangular numbers need no such extra
check only because `8n + 1`'s root is always odd, which is already
exactly what solving *that* sequence's quadratic requires). `math.isqrt`
gives an exact integer root with no floating-point rounding risk, same
as both existing siblings. `0` and all negative inputs return `False` up
front, matching `is_triangular`/`is_pentagonal`'s own "closed domain, no
exception, just `false`" convention — unlike `is_triangular` (whose
`root % 4`-free check happens to accept `0` as `H(0)`'s degenerate
case), `is_hexagonal`'s modular check already excludes `0` on its own
(`8*0+1=1`, `root=1`, `1 % 4 == 1 != 3`), consistent with the standard
hexagonal-number sequence starting at `k=1`. Also register the new dict
entry (search `"is_pentagonal": _is_pentagonal,`, add `"is_hexagonal":
_is_hexagonal,` directly after it).

Acceptance criteria:
- `is_hexagonal(0);` is `false` — `0` is not a hexagonal number under
  the standard `k >= 1` convention.
- `is_hexagonal(1);` is `true` (`H(1)`), `is_hexagonal(6);` is `true`
  (`H(2)`), `is_hexagonal(15);` is `true` (`H(3)`), `is_hexagonal(28);`
  is `true` (`H(4)`), `is_hexagonal(45);` is `true` (`H(5)`),
  `is_hexagonal(66);` is `true` (`H(6)`).
- `is_hexagonal(2);` is `false`, `is_hexagonal(5);` is `false`,
  `is_hexagonal(10);` is `false`, `is_hexagonal(100);` is `false` — none
  of these are hexagonal numbers.
- `is_hexagonal(190);` is `true` — a larger hexagonal number (`H(10)`),
  confirming the check holds beyond small brute-forced cases.
- `is_hexagonal(-6);` is `false` — negative input, matching
  `is_triangular`/`is_pentagonal`'s own "not a valid domain, answer
  false rather than raise" convention.
- `is_hexagonal(6.0);` raises `CinderRuntimeError` matching
  `"is_hexagonal() requires an int, got float"`.
- `is_hexagonal(true);` raises `CinderRuntimeError` matching
  `"is_hexagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_pentagonal`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsPentagonal`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_hexagonal`
added near `is_triangular`/`is_pentagonal`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s roadmap paragraph needs this
moved from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 5. Language: a list pattern nested inside a map pattern (`let {a, b: [c, d]} = {"a": 1, "b": [2, 3]};`)

Build: the depth task after task 5's breadth work (`is_hexagonal`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that nested map-in-map destructuring patterns has landed via PR
#293, dropping the count to the 5-task floor. Nested list-in-list
destructuring patterns landed via PR #273, nested map-in-map destructuring
patterns landed via PR #293, and task 4 above queues the map-in-list half.
The one remaining corner of the nesting matrix neither of those touches is
a *list* pattern nested inside a *map* pattern — today
`_destructure_map_pattern_entry` (`cinder/parser.py`) only recognizes a
nested `{` after a binding's `:` (recursing into another map pattern); a
`[` in that same position is a guaranteed `ParseError`. Verify the gap:
```sh
python3 -m cinder.cli eval 'let {a, b: [c, d]} = {"a": 1, "b": [2, 3]}; print(a); print(c); print(d);'
# -> <eval>:1:12: expected identifier in destructuring pattern, found '['
```
This is a guaranteed `ParseError` today (a `[` can never appear where
`_destructure_map_pattern_entry` expects `{`/an identifier after `:`), so
no currently-valid Cinder program's meaning changes. This is exactly the
case `tests/test_interpreter.py`'s `TestDestructureNestedMapPattern.
test_list_pattern_nested_in_map_still_rejected` currently pins as
permanently rejected — that test's premise flips with this task and must
be replaced (see Acceptance criteria).

Add a nested-`[` branch to `_destructure_map_pattern_entry`, alongside its
existing nested-`{` branch (search `def _destructure_map_pattern_entry`):
```python
            elif self._check(TokenType.LBRACKET):
                nested_names, nested_rest = self._destructure_list_pattern()
                binding = (nested_names, nested_rest, True)
```
This mirrors the existing nested-`{` branch's own shape exactly (recurse
via the sibling pattern parser, store the result as `binding`), but tags
its pattern tuple with a trailing `True` — deliberately a 3-element tuple,
not the 2-element `(nested_names, nested_rest)` the nested-`{` branch
already produces and will keep producing unchanged. This is the same
length-based tagging technique task 5 (a map pattern nested inside a list
pattern) uses in the opposite nesting direction, kept consistent so both
halves of the "mixed nesting" gap resolve the same shape ambiguity the
same way. Then teach `_bind_map_destructure` (`cinder/interpreter.py`) to
recognize the tagged shape, at its existing `isinstance(binding, tuple):`
check (search `isinstance(binding, tuple)`):
```python
            if isinstance(binding, tuple) and len(binding) == 3:
                nested_names, nested_rest, _ = binding
                self._bind_list_destructure(
                    env, nested_names, nested_rest, item, line, column, use_assign
                )
            elif isinstance(binding, tuple):
                nested_names, nested_rest = binding
                self._bind_map_destructure(
                    env, nested_names, nested_rest, item, line, column, use_assign
                )
            else:
                self._bind_destructure_name(env, binding, item, line, column, use_assign)
```
Because the existing 2-tuple production site (the nested-`{` branch) is
untouched, this task cannot regress any already-landed nested-map-in-map
behavior — the `len(binding) == 3` check only ever matches the new
branch's own output. The plain-assignment form (`{a, b: [c]} = expr;`)
stays out of scope, for the same structural reason task 5's map-in-list
plain-assignment form does: no plain-assignment destructuring exists for
map patterns at all today (only list patterns get an assignment-target
reading via `_destructure_assign_pattern`), so there is no call site to
extend.

Because `_destructure_map_pattern_entry` is the single shared entry point
every map-pattern call site funnels through — `let`, `for`-loops, function
params, and both comprehension forms — nesting a list pattern works for
free across all of them, the same "pure plumbing" result task 5 and the
original nested-map-in-map task both got from their own shared helpers.

Acceptance criteria:
- `let {a, b: [c, d]} = {"a": 1, "b": [2, 3]}; print(a); print(c); print(d);`
  prints `1`, `2`, `3`.
- `let {x: [y, z], a} = {"x": [1, 2], "a": 3}; print(y); print(z); print(a);`
  prints `1`, `2`, `3` — nested pattern in the first position works too,
  not just the last.
- `let {a, b: {c: [d, e]}} = {"a": 1, "b": {"c": [2, 3]}}; print(a); print(d); print(e);`
  prints `1`, `2`, `3` — a list pattern nested inside a nested *map*
  pattern, confirming the two kinds of nesting compose.
- `let {a, b: [c, ...drest]} = {"a": 1, "b": [2, 3, 4]}; print(drest);`
  prints `[3, 4]` — a rest element inside the nested list pattern.
- `let {a, b: [c] = [0]} = {"a": 1}; print(c);` prints `0` — a default
  value on a missing key whose nested pattern is a list.
- `let {a, b: [c]} = {"a": 1, "b": 2};` raises `CinderRuntimeError`
  matching `"cannot destructure int as a list"` — a non-list value at a
  nested position.
- `let {a, b: [c]} = {"a": 1, "b": []};` raises `CinderRuntimeError`
  matching `"destructuring pattern expects 1 elements, got 0"` — the
  existing arity-mismatch error still fires correctly from inside a
  nested pattern.
- `for {a, b: [c]} in [{"a": 1, "b": [2]}, {"a": 3, "b": [4]}] { print(a); print(c); }`
  prints `1`, `2`, `3`, `4` — the `for`-loop form.
- `fn f({a, b: [c]}) { return a + c; } print(f({"a": 1, "b": [2]}));`
  prints `3` — the function-parameter form.
- `print([a + c for {a, b: [c]} in [{"a": 1, "b": [2]}, {"a": 3, "b": [4]}]]);`
  prints `[3, 7]` — the comprehension loop-variable form.
- `{a, b: [c]} = {"a": 1, "b": [2]};` still raises `ParseError` — map
  patterns have no plain-assignment form at all today, out of scope for
  this task.
- `tests/test_interpreter.py`'s `TestDestructureNestedMapPattern.
  test_list_pattern_nested_in_map_still_rejected` is removed (its premise
  — that this syntax always raises — is exactly what this task makes
  false) and replaced with a new test class covering the positive cases
  above.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_map_pattern_entry`),
`cinder/interpreter.py` (`_bind_map_destructure`), `tests/test_parser.py`
(add a parser-shape test mirroring the existing nested-map-pattern-shape
test, confirming a `let`-form nested list pattern parses into the
`(nested_names, nested_rest, True)` shape), `tests/test_interpreter.py`
(remove `test_list_pattern_nested_in_map_still_rejected` from
`TestDestructureNestedMapPattern`, add a new `class
TestDestructureListPatternNestedInMap` mirroring
`TestDestructureMapPatternNestedInList`'s own style, placed near it). Once
merged, `README.md`'s destructuring bullet, its "Status & roadmap"
section, and `PROJECT.md`'s roadmap paragraph all need updating to note
this landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 6. Standard library: `is_heptagonal` — the fourth figurate-number membership predicate after `is_triangular`/`is_pentagonal`/`is_hexagonal`

Build: the breadth task after task 5's depth work (a list pattern nested
inside a map pattern) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_lucas_number` has
landed via PR #294, dropping the count to the 5-task floor.
`is_triangular`/`is_pentagonal`/`is_hexagonal` (`cinder/builtins.py`,
`is_hexagonal` queued as task 4 above) test membership in three of the
figurate-number sequences, each via a closed-form `math.isqrt`-based
identity; the heptagonal numbers (`1, 7, 18, 34, 55, 81, 112, ...`,
`H(k) = k(5k - 3) / 2`) are the natural fourth member of that cluster
and nothing in Cinder tests membership in them today. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_heptagonal(18));'
# -> CinderRuntimeError: undefined name 'is_heptagonal'
```

Add to `cinder/builtins.py`, registered right after `_is_hexagonal`
(search `def _is_hexagonal`, immediately before `_is_prime` — task 4
above lands `_is_hexagonal` in exactly that spot):
```python
def _is_heptagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_heptagonal", arguments, 1, line, column)
    value = _require_int("is_heptagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 40 * value + 9
    root = math.isqrt(candidate)
    return root * root == candidate and root % 10 == 7
```
This mirrors `_is_triangular`/`_is_pentagonal`/`_is_hexagonal`'s exact
shape: solving `H(k) = k(5k - 3) / 2 = n` for `k` via the quadratic
formula gives `k = (3 + sqrt(40n + 9)) / 10`, so `n` is heptagonal iff
`40n + 9` is a perfect square whose exact integer root additionally
satisfies `root % 10 == 7` (the condition that makes `(3 + root)`
divisible by 10, so `k` comes out an integer) — the same "closed-form
perfect-square identity plus one modular-residue check" technique
`is_pentagonal`'s `root % 6 == 5` and `is_hexagonal`'s `root % 4 == 3`
already use, each figurate number's own quadratic leaving a different
modulus/residue pair. `math.isqrt` gives an exact integer root with no
floating-point rounding risk, same as every sibling in the cluster. `0`
and all negative inputs return `False` up front, matching
`is_triangular`/`is_pentagonal`/`is_hexagonal`'s own "closed domain, no
exception, just `false`" convention — `is_heptagonal`'s modular check
already excludes `0` on its own (`40*0+9=9`, `root=3`, `3 % 10 == 3 !=
7`), consistent with the standard heptagonal-number sequence starting at
`k=1`. Also register the new dict entry (search `"is_hexagonal":
_is_hexagonal,`, add `"is_heptagonal": _is_heptagonal,` directly after
it).

Acceptance criteria:
- `is_heptagonal(0);` is `false` — `0` is not a heptagonal number under
  the standard `k >= 1` convention.
- `is_heptagonal(1);` is `true` (`H(1)`), `is_heptagonal(7);` is `true`
  (`H(2)`), `is_heptagonal(18);` is `true` (`H(3)`), `is_heptagonal(34);`
  is `true` (`H(4)`), `is_heptagonal(55);` is `true` (`H(5)`),
  `is_heptagonal(81);` is `true` (`H(6)`), `is_heptagonal(112);` is
  `true` (`H(7)`).
- `is_heptagonal(2);` is `false`, `is_heptagonal(6);` is `false`,
  `is_heptagonal(17);` is `false`, `is_heptagonal(100);` is `false` —
  none of these are heptagonal numbers.
- `is_heptagonal(235);` is `true` — a larger heptagonal number
  (`H(10)`), confirming the check holds beyond small brute-forced cases.
- `is_heptagonal(-18);` is `false` — negative input, matching
  `is_triangular`/`is_pentagonal`/`is_hexagonal`'s own "not a valid
  domain, answer false rather than raise" convention.
- `is_heptagonal(18.0);` raises `CinderRuntimeError` matching
  `"is_heptagonal() requires an int, got float"`.
- `is_heptagonal(true);` raises `CinderRuntimeError` matching
  `"is_heptagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_hexagonal`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsHexagonal`, search that
name — falls back to `class TestIsPentagonal` if task 4 above hasn't
landed yet in whatever order tasks are claimed). Once merged,
`README.md`'s Builtins bullet needs `is_heptagonal` added near
`is_triangular`/`is_pentagonal`/`is_hexagonal`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s roadmap paragraph needs this
moved from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
