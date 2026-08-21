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

## 2. Standard library: `additive_persistence` — steps of repeated digit-summing to reach one digit

Build: the breadth task after task 5's depth work (comma-separated
expression statements) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_sphenic` has landed
via PR #284, dropping the count to the 5-task floor.
`multiplicative_persistence` (`cinder/builtins.py`) already counts the
number of repeated digit-*multiplying* steps needed to reduce `n` to a
single digit; `digital_root` already computes the *value* a number
reduces to under repeated digit-*summing*, but via a closed-form
identity (`1 + (n - 1) % 9`) that never actually counts iterations.
Nothing today answers "how many summing steps does that take?" — the
natural sibling `multiplicative_persistence` is missing on the additive
side. `199` reduces `199 -> 19 -> 10 -> 1`, three steps; `9876` reduces
`9876 -> 30 -> 3`, two steps. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(additive_persistence(199));'
# -> CinderRuntimeError: undefined name 'additive_persistence'
```

Add to `cinder/builtins.py`, registered right after `_multiplicative_persistence`
(search `def _multiplicative_persistence`, immediately before `_reverse_int`):
```python
def _additive_persistence(arguments: list, line: int, column: int) -> object:
    _require_arity("additive_persistence", arguments, 1, line, column)
    value = _require_int("additive_persistence", arguments[0], line, column)
    value = abs(value)
    steps = 0
    while value >= 10:
        value = sum(int(digit) for digit in str(value))
        steps += 1
    return steps
```
This is `_multiplicative_persistence`'s own loop shape (search `def
_multiplicative_persistence`) — `abs()` the input once up front to discard
sign the same way `digit_sum`/`digital_root`/`multiplicative_persistence`
all already do, loop while `value >= 10` incrementing a step counter —
with the loop body's digit-*product* swapped for a digit-*sum*
(`sum(int(digit) for digit in str(value))`, the same summing expression
`digit_sum` itself uses), rather than computing `digital_root` and a step
count as two separate passes over the same reduction.

Acceptance criteria:
- `additive_persistence(0);` is `0`, `additive_persistence(9);` is `0` —
  already single-digit, no steps needed.
- `additive_persistence(99);` is `2` — `99 -> 18 -> 9`.
- `additive_persistence(199);` is `3` — `199 -> 19 -> 10 -> 1`.
- `additive_persistence(9876);` is `2` — `9876 -> 30 -> 3`.
- `additive_persistence(-199);` is `3` — sign discarded via `abs()` up
  front, matching `digit_sum`/`digital_root`/`multiplicative_persistence`'s
  own sign-discarding convention (not `reverse_int`'s sign-preserving
  one, since this returns a step count, not a number built from the
  input's own digits).
- `additive_persistence(5.0);` raises `CinderRuntimeError` matching
  `"additive_persistence() requires an int, got float"`.
- `additive_persistence(true);` raises `CinderRuntimeError` matching
  `"additive_persistence() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`multiplicative_persistence`, see current line numbers — shift if earlier
tasks this cycle land first), `tests/test_builtins.py` (model on `class
TestMultiplicativePersistence`, search that name). Once merged,
`README.md`'s Builtins bullet needs `additive_persistence` added near
`multiplicative_persistence`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming
pass, not this task.

---

## 3. Language: map concatenation via `+` (`{...} + {...}`)

Build: the depth task after task 5's breadth work (`additive_persistence`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that triple-quoted string literals has landed via PR #285,
dropping the count to the 5-task floor. `_apply_binary_operator`'s `PLUS`
branch (`cinder/interpreter.py`, search `if op == TokenType.PLUS:`) already
overloads `+` for three types — numbers, strings, and lists
(`isinstance(left, list) and isinstance(right, list): return left + right`)
— the list case added specifically to close the gap between the existing
`concat()` builtin and infix syntax. Maps are Cinder's fourth container
type and have the exact same kind of gap: `merge()` (`cinder/builtins.py`,
search `def _merge`) already implements right-biased shallow map merging
(`result = dict(map1); result.update(map2); return result`) as a builtin,
but there is no infix spelling for it — every other overloaded operator in
this file has an infix form, merge is the only container-combining builtin
left stuck as call-only syntax. Nothing about maps makes `+` ambiguous or
undesirable here: `merge()`'s semantics (map2's value wins on a key
collision, map1's key order preserved for shared keys, map2-only keys
appended after) are exactly what most languages' informal "dict overlay"
reading of `+` would produce, and Cinder already applies this same "give
the existing builtin an operator form" reasoning to `concat()`.

Verify the gap:
```sh
python3 -m cinder.cli eval 'print({"a": 1} + {"b": 2});'
# -> <eval>:1:16: unsupported operand types for '+': map and map
python3 -m cinder.cli eval 'let m = {"a": 1}; m += {"a": 2}; print(m);'
# -> <eval>:1:21: unsupported operand types for '+': map and map
```
This is a guaranteed `CinderRuntimeError` today for every map-plus-map
expression, so no currently-valid Cinder program's meaning changes.

**Interpreter only** (`cinder/interpreter.py`) — no lexer, parser, or AST
changes needed, since `+` is already a fully general `Binary`/compound-assign
operator and maps are already a first-class value type; this only extends
`_apply_binary_operator`'s existing `PLUS` branch with one more `isinstance`
case, the same shape the `list`/`list` case right above it already has:
```python
        if op == TokenType.PLUS:
            if _is_number(left) and _is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            if isinstance(left, dict) and isinstance(right, dict):
                result = dict(left)
                result.update(right)
                return result
            raise CinderRuntimeError(
                f"unsupported operand types for '+': {type_name(left)} and {type_name(right)}",
                operator.line,
                operator.column,
            )
```
The two-line merge body (`result = dict(left); result.update(right)`) is
`_merge`'s own body verbatim (search `def _merge`, its `result = dict(map1);
result.update(map2); return result` after the type checks) — it can't be
called directly from here since `cinder/builtins.py` imports *from*
`cinder/interpreter.py` (search `from cinder.interpreter import` near the
top of `builtins.py`), not the other way around, so importing `_merge` back
into `interpreter.py` would be a circular import; inlining these two lines
is the same tradeoff the list case already makes by writing `left + right`
directly instead of importing `_concat`. No new type-check branch is needed
either — `left`/`right` are already known to both be `dict` from the
`isinstance` guard, and `dict(left)` always succeeds on a `dict`, so there's
no failure mode requiring its own `CinderRuntimeError` the way, say,
`_bitwise_op`'s int-only guard needs one.

Because this only touches the shared `PLUS` branch, every existing caller of
`+` gets map support automatically, with no separate implementation needed:
plain `m1 + m2` (`_evaluate_binary`), `+=` on an identifier target (parser.py
desugars `PLUSEQ` into `Assign(name, Binary(expr, PLUS, value))`, which
evaluates through this same branch), and `+=` on an index or dot-access
target (`PLUSEQ` is already in `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` in
`cinder/parser.py`, so `xs[0] += {"a": 1}` / `obj.key += {"a": 1}` desugar
into `IndexCompoundAssign`, which also calls `_apply_binary_operator` — see
`cinder/interpreter.py`'s `IndexCompoundAssign` handler, search `result =
self._apply_binary_operator(expr.operator, current, rhs)`) — exactly
mirroring how list `+=` already works for free through the same
desugaring once list `+` landed.

Acceptance criteria:
- `print({"a": 1} + {"b": 2});` prints `{"a": 1, "b": 2}`.
- `print({"a": 1} + {"a": 2});` prints `{"a": 2}` — right map wins on a key
  collision, matching `merge()`'s own conflict rule
  (`test_merge_map2_wins_on_conflict`).
- `print({} + {"a": 1});` prints `{"a": 1}`; `print({"a": 1} + {});` prints
  `{"a": 1}` — either side empty.
- `print(list((({"a": 1, "b": 2} + {"b": 3, "c": 4})).keys()));` (or an
  equivalent `keys()` call) yields `["a", "b", "c"]` — left map's key order
  preserved for shared/left-only keys, right map's new keys appended after,
  matching `merge()`'s own `test_merge_key_order_map1_then_map2_only_keys`.
- `let a = {"a": 1}; let b = {"b": 2}; let c = a + b; print(a); print(b);`
  prints `{"a": 1}` then `{"b": 2}` — neither input is mutated, mirroring
  `TestListConcatenation.test_does_not_mutate_inputs`.
- `let m = {"a": 1}; m += {"b": 2}; print(m);` prints `{"a": 1, "b": 2}` —
  compound assignment on an identifier target.
- `let xs = [{"a": 1}]; xs[0] += {"b": 2}; print(xs[0]);` prints
  `{"a": 1, "b": 2}` — compound assignment on an index target.
- `let obj = {"m": {"a": 1}}; obj.m += {"b": 2}; print(obj.m);` prints
  `{"a": 1, "b": 2}` — compound assignment on a dot-access target (which
  desugars to the same `Index` path).
- `let m = {"a": 1} + {"b": 2} + {"c": 3}; print(m);` prints
  `{"a": 1, "b": 2, "c": 3}` — left-associative chaining, mirroring
  `TestListConcatenation.test_left_associative`.
- `{"a": 1} + [1, 2];` still raises `CinderRuntimeError` matching
  `"unsupported operand types for '+': map and list"` — mixed map/list is
  unaffected.
- `{"a": 1} + "x";` still raises `CinderRuntimeError` matching
  `"unsupported operand types for '+': map and string"` — mixed map/string
  is unaffected.
- `{"a": 1} + 1;` still raises `CinderRuntimeError` matching `"unsupported
  operand types for '+': map and int"` — mixed map/number is unaffected.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s `PLUS`
branch), `tests/test_interpreter.py` (model on `class TestListConcatenation`,
search that name — add a parallel `class TestMapConcatenation` right after
it with the same shape: two maps, empty left/right, non-mutation, compound
assignment, left-associativity, plus the mixed-type error cases). Once
merged, `README.md`'s list-concatenation bullet (search "list concatenation
via") needs a mention of the map case added alongside it, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s roadmap paragraph needs
this moved from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `is_pentagonal` — the closed-form figurate-number sibling of `is_triangular`

Build: the breadth task after task 5's depth work (map concatenation via
`+`) per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog
back to 6 tasks now that `is_circular_prime` has landed via PR #286,
dropping the count to the 5-task floor. `is_triangular` (`cinder/builtins.py`)
already tests membership in the triangular numbers (`0, 1, 3, 6, 10, ...`)
via a closed-form perfect-square check (`8n + 1` is a perfect square) rather
than an accumulating loop; `is_fibonacci`/`is_perfect_square` use the same
`math.isqrt`-based exact-integer technique for their own closed forms. The
pentagonal numbers (`1, 5, 12, 22, 35, ...`, generated by `P_k = k * (3k -
1) / 2` for `k = 1, 2, 3, ...`) are the next figurate-number family after
triangular and have an equally clean closed form, but nothing in Cinder
tests membership in it today. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_pentagonal(5));'
# -> CinderRuntimeError: undefined name 'is_pentagonal'
```

Add to `cinder/builtins.py`, registered right after `_is_triangular`
(search `def _is_triangular`, immediately before `_is_prime`):
```python
def _is_pentagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_pentagonal", arguments, 1, line, column)
    value = _require_int("is_pentagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 24 * value + 1
    root = math.isqrt(candidate)
    return root * root == candidate and root % 6 == 5
```
This mirrors `_is_triangular`'s own shape exactly (search `def
_is_triangular`) — solving `P_k = k * (3k - 1) / 2 = value` for `k` via the
quadratic formula gives `k = (1 + sqrt(24 * value + 1)) / 6`, so `k` is a
positive integer exactly when `24 * value + 1` is a perfect square *and*
its integer square root is `≡ 5 (mod 6)` (the `+ 1` in the numerator only
divides evenly by `6` when the root lands on that residue) — the second
condition is the one place this differs from `is_triangular`'s plain
perfect-square check, since triangular numbers' `k = (-1 + sqrt(8n + 1)) /
2` has no equivalent modular constraint. `0` is deliberately *not*
pentagonal under this test (`candidate = 1`, `root = 1`, `1 % 6 == 1`, not
`5`) — unlike `is_triangular(0)` being `true` — because the pentagonal
sequence conventionally starts at `k = 1` (`P_1 = 1`), with no `k = 0`
term the way triangular numbers have `T_0 = 0`; this was verified against
a brute-force `k * (3 * k - 1) // 2 for k in range(1, 1000)` membership
set before writing this task; do not go add a `value == 0` special case.
Also register the new registration-dict entry in the builtins dict (search
`"is_triangular": _is_triangular,`, add `"is_pentagonal": _is_pentagonal,`
directly after it).

Acceptance criteria:
- `is_pentagonal(0);` is `false` — the pentagonal sequence starts at `1`,
  unlike `is_triangular(0)` being `true`.
- `is_pentagonal(1);` is `true`, `is_pentagonal(5);` is `true`,
  `is_pentagonal(12);` is `true`, `is_pentagonal(22);` is `true`,
  `is_pentagonal(35);` is `true` — the first five pentagonal numbers
  (`k = 1..5`).
- `is_pentagonal(2);` is `false`, `is_pentagonal(4);` is `false`,
  `is_pentagonal(10);` is `false`, `is_pentagonal(100);` is `false` — none
  of these are pentagonal.
- `is_pentagonal(-5);` is `false` — negative input, matching
  `is_triangular`/`is_fibonacci`'s own "not a valid domain, answer false
  rather than raise" convention.
- `is_pentagonal(40755);` is `true` — a large pentagonal number
  (`k = 165`), confirming the closed form holds beyond small brute-forced
  cases.
- `is_pentagonal(5.0);` raises `CinderRuntimeError` matching
  `"is_pentagonal() requires an int, got float"`.
- `is_pentagonal(true);` raises `CinderRuntimeError` matching
  `"is_pentagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_triangular`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsTriangular`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_pentagonal`
added near `is_triangular`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not this
task.

---

## 5. Language: nested map-in-map destructuring patterns (`let {a, b: {c, d}} = {...}`)

Build: the depth task after task 5's breadth work (`is_pentagonal`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that missing string escape sequences has landed via PR #287,
dropping the count to the 5-task floor. Nested list-in-list destructuring
patterns (`let [a, [b, c]] = [1, [2, 3]];`) landed via PR #273
(`feat/20260818-nested-list-destructure`), but that task was explicitly
scoped to list-in-list only — `PROJECT.md`'s roadmap paragraph for it says
map nesting either direction stays out of scope, still a `ParseError`, and
`CHANGELOG.md` confirms the same. That deferred half never got picked back
up. Map patterns are the one destructuring shape that still can't nest at
all: `_destructure_map_pattern_entry` (`cinder/parser.py`, search `def
_destructure_map_pattern_entry`) parses a `key`, an optional `: binding`
rename, and an optional `= default`, but the `binding` after `:` is always
required to be a bare `IDENTIFIER` — there's no branch for a nested `{`
the way `_destructure_list_pattern_entry` (`cinder/parser.py`) already has
for a nested `[`. `_bind_map_destructure` (`cinder/interpreter.py`)
correspondingly has no `isinstance(binding, tuple)` branch, unlike
`_bind_list_destructure`'s existing `isinstance(name, tuple)` branch that
recurses into `_bind_list_destructure` again for a nested list pattern.
Verify the gap:
```sh
python3 -m cinder.cli eval 'let {a, b: {c, d}} = {"a": 1, "b": {"c": 2, "d": 3}}; print(a); print(c); print(d);'
# -> <eval>:1:12: expected identifier in destructuring pattern, found '{'
python3 -m cinder.cli eval 'let {outer: {inner}} = {"outer": {"inner": 5}}; print(inner);'
# -> <eval>:1:13: expected identifier in destructuring pattern, found '{'
```
This is a guaranteed `ParseError` today (a `{` can never appear where an
`IDENTIFIER` is demanded after `:` in a map pattern), so no currently-valid
Cinder program's meaning changes.

Add a nested branch to `_destructure_map_pattern_entry`, mirroring the
shape `_destructure_list_pattern_entry` already uses for `[`:
```python
    def _destructure_map_pattern_entry(self) -> "tuple[str, object, Expr | None]":
        key = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
        if self._check(TokenType.COLON):
            self._advance()
            if self._check(TokenType.LBRACE):
                nested_names, nested_rest = self._destructure_map_pattern()
                binding = (nested_names, nested_rest)
            else:
                binding = self._consume(
                    TokenType.IDENTIFIER, "identifier in destructuring pattern"
                ).lexeme
        else:
            binding = key
        default = None
        if self._check(TokenType.EQ):
            self._advance()
            default = self._ternary()
        return key, binding, default
```
`default` parsing is unchanged and untouched — it already runs after
`binding` is computed regardless of which branch set it, so a default on a
nested pattern slot (`{b: {c, d} = {"c": 0, "d": 0}}`) falls out for free
exactly the way it did for nested list patterns. Then add the matching
bind-time branch to `_bind_map_destructure` (`cinder/interpreter.py`),
mirroring `_bind_list_destructure`'s existing `isinstance(name, tuple)`
branch, right before the existing `self._bind_destructure_name(env,
binding, item, line, column, use_assign)` call in its `for key, binding,
default in names:` loop:
```python
            if isinstance(binding, tuple):
                nested_names, nested_rest = binding
                self._bind_map_destructure(
                    env, nested_names, nested_rest, item, line, column, use_assign
                )
            else:
                self._bind_destructure_name(env, binding, item, line, column, use_assign)
```
`_bind_map_destructure`'s own existing `if not isinstance(value, dict):
raise CinderRuntimeError(f"cannot destructure {type_name(value)} as a
map", ...)` guard at the top already covers a non-map value landing at a
nested slot with no changes needed, exactly as `_bind_list_destructure`'s
equivalent guard already does for nested list patterns.

Because `_destructure_map_pattern_entry` is the single shared entry point
every map-pattern call site funnels through — `let`, plain assignment
(`_try_map_destructure_assign_statement`), `for`-loops, function params,
and both comprehension forms — nesting works for free across all of them,
no per-call-site changes required, the same "pure plumbing" result the
nested-list task and the map-pattern rest element task both got from
their own shared helpers.

Deliberately scoped to map-in-map nesting only, mirroring the precedent
the list task set: a list pattern nested inside a map pattern (`{b: [c,
d]}`) and a map pattern nested inside a list pattern (`[a, {b, c}]`,
already covered by the existing regression test
`test_map_pattern_nested_in_list_still_rejected` in
`tests/test_interpreter.py`'s `TestDestructureNestedListPattern`) both stay
out of scope and continue raising `ParseError` exactly as today — this
task does not touch `_destructure_list_pattern_entry` at all, so that
existing test must stay green unchanged as proof.

Acceptance criteria:
- `let {a, b: {c, d}} = {"a": 1, "b": {"c": 2, "d": 3}}; print(a); print(c); print(d);`
  prints `1`, `2`, `3`.
- `let {a: {x, y}, b} = {"a": {"x": 1, "y": 2}, "b": 3}; print(x); print(y); print(b);`
  prints `1`, `2`, `3` — nested pattern in the first position works too, not
  just the last.
- `let {a: {b: {c}}} = {"a": {"b": {"c": 5}}}; print(c);` prints `5` —
  arbitrary nesting depth, mirroring the arbitrary-nesting-depth coverage
  the list task already has.
- `let {a: {b, ...brest}} = {"a": {"b": 1, "c": 2, "d": 3}}; print(brest);`
  prints `{"c": 2, "d": 3}` — a rest element inside a nested pattern.
- `let {a: {x}, ...rest} = {"a": {"x": 1}, "b": 2, "c": 3}; print(rest);`
  prints `{"b": 2, "c": 3}` — a rest element at the outer level combined
  with a nested pattern elsewhere in the same pattern.
- `let {b: {c, d} = {"c": 0, "d": 0}} = {}; print(c); print(d);` prints
  `0`, `0` — a default value on a missing key whose value would otherwise
  be a nested pattern.
- `let {a: {b, c}} = {"a": 1};` raises `CinderRuntimeError` matching
  `"cannot destructure int as a map"` — a non-map value at a nested
  position.
- `let {a: {b}} = {"a": {}};` raises `CinderRuntimeError` matching
  `"destructuring pattern expects key 'b', not found in map"` — the
  existing missing-key error still fires correctly from inside a nested
  pattern.
- `let x = 0; let y = 0; {outer: {x, y}} = {"outer": {"x": 1, "y": 2}}; print(x); print(y);`
  prints `1`, `2` — the plain-assignment destructuring form.
- `let total = 0; for {a: {x}} in [{"a": {"x": 1}}, {"a": {"x": 2}}] { total = total + x; } print(total);`
  prints `3` — the `for`-loop form.
- `fn f({a: {x, y}}) { return x + y; } print(f({"a": {"x": 1, "y": 2}}));`
  prints `3` — the function-parameter form.
- `print([x for {a: {x}} in [{"a": {"x": 1}}, {"a": {"x": 2}}]]);`
  prints `[1, 2]` — the comprehension loop-variable form.
- `let {b: [c, d]} = {"b": [1, 2]};` still raises `ParseError` matching
  `"expected identifier in destructuring pattern, found '['"` — a list
  nested inside a map pattern stays unsupported, out of scope for this
  task.
- `TestDestructureNestedListPattern.test_map_pattern_nested_in_list_still_rejected`
  in `tests/test_interpreter.py` stays green with no changes — a map
  pattern nested inside a list pattern stays unsupported too, confirming
  this task didn't touch `_destructure_list_pattern_entry`.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_map_pattern_entry`),
`cinder/interpreter.py` (`_bind_map_destructure`), `tests/test_parser.py`
(add a parser-shape test mirroring `test_list_destructure_assignment_nested_pattern_parses`,
confirming a nested map pattern parses into the `(key, (nested_names,
nested_rest), default)` shape), `tests/test_interpreter.py` (add a new
`class TestDestructureNestedMapPattern` mirroring
`TestDestructureNestedListPattern` test-for-test, placed near it). Once
merged, `README.md`'s destructuring bullet, its "Status & roadmap"
section, and `PROJECT.md`'s roadmap paragraph all need updating to note
nested map-in-map patterns landed — leave all three to the Architect's
next grooming pass, not this task.

---

## 6. Standard library: `is_lucas_number` — the Lucas-sequence sibling of `is_fibonacci`

Build: the breadth task after task 5's depth work (nested map-in-map
destructuring patterns) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_sad_number` has landed
via PR #288, dropping the count to the 5-task floor. `is_fibonacci`
(`cinder/builtins.py`) already tests membership in the Fibonacci sequence
(`0, 1, 1, 2, 3, 5, 8, ...`) via a closed-form perfect-square identity
(`5n² ± 4` is a perfect square); the Lucas sequence is Fibonacci's
standard companion sequence — same recurrence (`L(n) = L(n-1) + L(n-2)`),
different seed (`L(0) = 2, L(1) = 1` instead of `F(0) = 0, F(1) = 1`),
giving `2, 1, 3, 4, 7, 11, 18, 29, 47, 76, ...` — but nothing in Cinder
tests membership in it today, and unlike Fibonacci it has no equally
simple closed-form membership test (the analogous identity involves the
golden ratio directly rather than a clean integer perfect-square check),
so this task generates and compares instead. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_lucas_number(18));'
# -> CinderRuntimeError: undefined name 'is_lucas_number'
```

Add to `cinder/builtins.py`, registered right after `_is_fibonacci`
(search `def _is_fibonacci`, immediately before `_is_happy_number`):
```python
def _is_lucas_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_lucas_number", arguments, 1, line, column)
    value = _require_int("is_lucas_number", arguments[0], line, column)
    if value < 1:
        return False
    if value in (1, 2):
        return True

    previous, current = 1, 3  # L(1), L(2)
    while current < value:
        previous, current = current, previous + current
    return current == value
```
The sequence is not monotonic at its very start (`L(0) = 2` then
`L(1) = 1` dips back down before climbing from `L(2) = 3` onward), so a
plain "advance while below target" loop starting from `L(0)` would skip
straight past `1` — the two special cases handle `1` (`L(1)`) and `2`
(`L(0)`) explicitly up front, and the loop itself starts from the first
strictly-increasing pair (`L(1) = 1, L(2) = 3`) so `current < value`
termination is safe for every value from `3` upward, the same
generate-and-compare shape `is_kaprekar`/`is_harshad`-style iterative
predicates already use elsewhere in this file where no closed form
exists. `0` and all negative inputs return `False` up front — `0` never
appears in the Lucas sequence, matching `is_fibonacci`'s own "closed
domain, no exception, just `false`" convention for out-of-sequence
input. Also register the new dict entry (search `"is_fibonacci":
_is_fibonacci,`, add `"is_lucas_number": _is_lucas_number,` directly
after it).

Acceptance criteria:
- `is_lucas_number(0);` is `false` — `0` is never a Lucas number.
- `is_lucas_number(1);` is `true` (`L(1)`), `is_lucas_number(2);` is
  `true` (`L(0)`) — the two seed values, handled by the explicit special
  case.
- `is_lucas_number(3);` is `true`, `is_lucas_number(4);` is `true`,
  `is_lucas_number(7);` is `true`, `is_lucas_number(11);` is `true`,
  `is_lucas_number(18);` is `true`, `is_lucas_number(29);` is `true` —
  `L(2)` through `L(7)`.
- `is_lucas_number(5);` is `false`, `is_lucas_number(6);` is `false`,
  `is_lucas_number(10);` is `false`, `is_lucas_number(100);` is `false` —
  none of these are Lucas numbers.
- `is_lucas_number(76);` is `true` — a larger Lucas number (`L(9)`),
  confirming the loop holds beyond small brute-forced cases.
- `is_lucas_number(-5);` is `false` — negative input, matching
  `is_fibonacci`/`is_triangular`'s own "not a valid domain, answer false
  rather than raise" convention.
- `is_lucas_number(5.0);` raises `CinderRuntimeError` matching
  `"is_lucas_number() requires an int, got float"`.
- `is_lucas_number(true);` raises `CinderRuntimeError` matching
  `"is_lucas_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_fibonacci`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsFibonacci`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_lucas_number`
added near `is_fibonacci`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not this
task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
