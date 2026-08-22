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

## 2. Language: a map pattern nested inside a list pattern (`let [a, {b, c}] = [1, {"b": 2, "c": 3}];`)

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

## 3. Standard library: `is_hexagonal` — the third figurate-number membership predicate after `is_triangular`/`is_pentagonal`

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

## 4. Language: a list pattern nested inside a map pattern (`let {a, b: [c, d]} = {"a": 1, "b": [2, 3]};`)

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

## 5. Standard library: `is_heptagonal` — the fourth figurate-number membership predicate after `is_triangular`/`is_pentagonal`/`is_hexagonal`

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

## 6. Language: a step component for range expressions (`start..end..step`, `start..=end..step`)

Build: the depth task after task 5's breadth work (`is_heptagonal`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that multiple `for` clauses in list/map comprehensions has
landed via PR #295, dropping the count to the 5-task floor. Range
expressions (`cinder/ast_nodes.py`'s `RangeExpr`) always imply an
implicit step of `1` today — there is no way to skip elements, and no
way to count *down*, since `_range` (`cinder/builtins.py`) always calls
Python's `range(start, stop)` with no third argument. Verify the gap:
```sh
python3 -m cinder.cli eval 'for (x in 1..10..2) { print(x); }'
# -> <eval>:1:16: expected ';' after for-loop init, found '..'
python3 -m cinder.cli eval 'print(10..0);'
# -> [] (silently empty — a descending bound with the implicit step of 1
#    can never produce anything, and today there is no way to ask for a
#    negative step to fix that)
```

Add an optional third `_bitor()` operand to `_range_expr` (search
`def _range_expr`, `cinder/parser.py`):
```python
    def _range_expr(self) -> Expr:
        expr = self._bitor()
        if self._check(TokenType.DOT_DOT) or self._check(TokenType.DOT_DOT_EQ):
            dots = self._advance()
            end = self._bitor()
            inclusive = dots.type is TokenType.DOT_DOT_EQ
            step = None
            if self._check(TokenType.DOT_DOT):
                self._advance()
                step = self._bitor()
            return RangeExpr(expr, end, dots.line, dots.column, inclusive, step)
        return expr
```
Only a plain `..` is accepted as the step separator (not `..=` — the
inclusivity is already fixed by the first separator, so a second one
carrying its own inclusivity would be meaningless); `1..=10..2` is valid
(inclusive range, step `2`), `1..10..=2` is not and stays a `ParseError`
the same way it is today, since nothing consumes a `..=` in that
position.

Add the field to `RangeExpr` (search `class RangeExpr`,
`cinder/ast_nodes.py`), appended last so the existing single call site
that constructs it with 5 positional arguments keeps working unchanged:
```python
class RangeExpr:
    start: "Expr"
    end: "Expr"
    line: int
    column: int
    inclusive: bool = False
    step: "Expr | None" = None
```

Thread it through `_evaluate_range` (search `def _evaluate_range`,
`cinder/interpreter.py`):
```python
    def _evaluate_range(self, expr: RangeExpr, env: Environment) -> object:
        start = self.evaluate(expr.start, env)
        end = self.evaluate(expr.end, env)
        step = self.evaluate(expr.step, env) if expr.step is not None else None
        if expr.inclusive and isinstance(end, int) and not isinstance(end, bool):
            descending = (
                isinstance(step, int) and not isinstance(step, bool) and step < 0
            )
            end = end - 1 if descending else end + 1
        from cinder.builtins import _range  # local: builtins.py imports
        # from interpreter.py at module level already, so a top-level
        # import the other way round here would be circular; importing
        # inside the method instead defers it until both modules have
        # finished loading, which is safe.
        arguments = [start, end] if step is None else [start, end, step]
        return _range(arguments, expr.line, expr.column)
```
The `descending` check flips the inclusive-end adjustment's direction:
today `..=` always adds `1` so the upper bound survives Python's
exclusive-`stop` semantics, but that only works for an ascending walk —
`10..=0..-2` needs `end` pushed to `-1`, not `1`, so `0` (not `-2`)
survives as the last element counted down to.

Extend `_range` (search `def _range`, `cinder/builtins.py`) from its
current 1-or-2-argument form to also accept a third:
```python
def _range(arguments: list, line: int, column: int) -> object:
    if len(arguments) == 1:
        start, stop, step = 0, arguments[0], 1
    elif len(arguments) == 2:
        start, stop = arguments
        step = 1
    elif len(arguments) == 3:
        start, stop, step = arguments
    else:
        raise CinderRuntimeError(
            f"range() expects 1 to 3 argument(s), got {len(arguments)}", line, column
        )
    for value in (start, stop, step):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CinderRuntimeError(
                f"range() requires int arguments, got {type_name(value)}", line, column
            )
    if step == 0:
        raise CinderRuntimeError("range() step must not be zero", line, column)
    return list(range(start, stop, step))
```
This matches Python's own `range(start, stop, step)` three-argument
shape exactly, so the underlying `list(range(...))` call needs no other
change — a negative step already produces a descending list on its own
once `start > stop`, no separate direction-handling code needed.

Acceptance criteria:
- `print(1..10..2);` is `[1, 3, 5, 7, 9]`.
- `print(1..=10..2);` is `[1, 3, 5, 7, 9]` — `10` isn't reached by the
  step, so the inclusive marker changes nothing here.
- `print(0..=10..2);` is `[0, 2, 4, 6, 8, 10]` — `10` is reached, so the
  inclusive marker's `end - 1`-vs-`+ 1` split doesn't matter for a
  positive step either way in this particular case; also confirm
  `print(0..=9..2);` is `[0, 2, 4, 6, 8]` (`9` itself is never hit).
- `print(10..0..-2);` is `[10, 8, 6, 4, 2]` — the first negative-step,
  descending range Cinder has ever been able to produce.
- `print(10..=0..-2);` is `[10, 8, 6, 4, 2, 0]` — inclusive descending,
  confirming the `descending` branch's `end - 1` adjustment (`end`
  becomes `-1`, not `1`) is what lets `0` survive.
- `print(10..=1..-3);` is `[10, 7, 4, 1]` — a step that lands exactly on
  the inclusive bound.
- `for (x in 1..10..2) { print(x); }` prints `1`, `3`, `5`, `7`, `9` —
  usable in a `for`-loop exactly like a step-less range already is.
- `print([x for x in 0..10..3]);` is `[0, 3, 6, 9]` — usable as a
  comprehension source.
- `print(1..10..0);` raises `CinderRuntimeError` matching `"range()
  step must not be zero"`.
- `print(1..10..1.5);` raises `CinderRuntimeError` matching `"range()
  requires int arguments, got float"`.
- `print(range(0, 10, 2));` is `[0, 2, 4, 6, 8]` and
  `print(range(10, 0, -2));` is `[10, 8, 6, 4, 2]` — the `range()`
  builtin itself gains the same third argument directly, not just
  through `..` syntax.
- `print(range(1, 10, 0));` raises `CinderRuntimeError` matching
  `"range() step must not be zero"`.
- `print(range(1, 2, 3, 4));` raises `CinderRuntimeError` matching
  `"range() expects 1 to 3 argument(s), got 4"`.
- `print(1..10);` and `print(1..=10);` are unchanged (`[1..9]` and
  `[1..10]` respectively) — no step given still means the existing
  implicit-step-of-1 behavior, confirming this is purely additive.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_range_expr`), `cinder/ast_nodes.py`
(`RangeExpr`), `cinder/interpreter.py` (`_evaluate_range`),
`cinder/builtins.py` (`_range`), `tests/test_parser.py` (add tests
alongside the existing range tests, search `test_range_literal` and its
neighbors around `TestRange`-style range-parsing tests), `tests/test_interpreter.py`
(extend `class TestRangeLiteral`, search that name), `tests/test_builtins.py`
(extend `class TestRange`, search that name, for the `range()` builtin's
new third argument). Once merged, `README.md`'s "Coming up next" bullet
in "Status & roadmap" and its ranges mention in the Features list need
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming
pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
