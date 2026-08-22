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

## 1. Standard library: `is_hexagonal` — the third figurate-number membership predicate after `is_triangular`/`is_pentagonal`

Build: the breadth task queued after a map pattern nested inside a list
pattern landed via PR #297 (the prior top task) per `PROJECT.md`'s
breadth-vs-depth policy. `is_pentagonal` landed via PR #292; PR #297
dropped the backlog to its 5-task floor — this grooming pass renumbers
the remaining tasks starting at 1 and restocks with a new task 6 (see
bottom of file) to bring the count back to 6.
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
section needs updating, and `PROJECT.md`'s "Current frontier" bullet
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 2. Language: a list pattern nested inside a map pattern (`let {a, b: [c, d]} = {"a": 1, "b": [2, 3]};`)

Build: the depth task after task 1's breadth work (`is_hexagonal`) per
`PROJECT.md`'s breadth-vs-depth policy. Nested list-in-list
destructuring patterns landed via PR #273, nested map-in-map
destructuring patterns landed via PR #293, and a map pattern nested
inside a list pattern landed via PR #297. The one remaining corner of
the nesting matrix none of those touches is a *list* pattern nested
inside a *map* pattern — today
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
length-based tagging technique PR #297 (a map pattern nested inside a
list pattern) uses in the opposite nesting direction, kept consistent so both
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
stays out of scope, for the same structural reason PR #297's map-in-list
plain-assignment form does: no plain-assignment destructuring exists for
map patterns at all today (only list patterns get an assignment-target
reading via `_destructure_assign_pattern`), so there is no call site to
extend.

Because `_destructure_map_pattern_entry` is the single shared entry point
every map-pattern call site funnels through — `let`, `for`-loops, function
params, and both comprehension forms — nesting a list pattern works for
free across all of them, the same "pure plumbing" result PR #297 and the
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
merged, `README.md`'s destructuring bullet and its "Status & roadmap"
section need updating to note this landed, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Standard library: `is_heptagonal` — the fourth figurate-number membership predicate after `is_triangular`/`is_pentagonal`/`is_hexagonal`

Build: the breadth task after task 2's depth work (a list pattern nested
inside a map pattern) per `PROJECT.md`'s breadth-vs-depth policy.
`is_lucas_number` landed via PR #294.
`is_triangular`/`is_pentagonal`/`is_hexagonal` (`cinder/builtins.py`,
`is_hexagonal` queued as task 1 above) test membership in three of the
figurate-number sequences, each via a closed-form `math.isqrt`-based
identity; the heptagonal numbers (`1, 7, 18, 34, 55, 81, 112, ...`,
`H(k) = k(5k - 3) / 2`) are the natural fourth member of that cluster
and nothing in Cinder tests membership in them today. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_heptagonal(18));'
# -> CinderRuntimeError: undefined name 'is_heptagonal'
```

Add to `cinder/builtins.py`, registered right after `_is_hexagonal`
(search `def _is_hexagonal`, immediately before `_is_prime` — task 1
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
name — falls back to `class TestIsPentagonal` if task 1 above hasn't
landed yet in whatever order tasks are claimed). Once merged,
`README.md`'s Builtins bullet needs `is_heptagonal` added near
`is_triangular`/`is_pentagonal`/`is_hexagonal`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" bullet
needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Language: a step component for range expressions (`start..end..step`, `start..=end..step`)

Build: the depth task after task 3's breadth work (`is_heptagonal`) per
`PROJECT.md`'s breadth-vs-depth policy. Multiple `for` clauses in
list/map comprehensions landed via PR #295. Range
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
updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Standard library: `collatz_max` — the peak value reached by the Collatz (3n+1) recurrence

Build: the breadth task after task 4's depth work (a step component for
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

## 6. Language: a `match` expression with literal patterns and a `_` wildcard

Build: the depth task after task 5's breadth work (`collatz_max`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks. This is a new arc, not another destructuring-nesting corner: with
task 2 above (a list pattern nested inside a map pattern) landing, every
corner of the list/map pattern nesting matrix is closed, and
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
