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

## 1. Standard library: `interleave` for two lists [claimed 2026-07-29T20:42:36Z]

Build: add `interleave(list1, list2)` to `cinder/builtins.py`, reusing the
`_require_two_lists` helper (line 1058, already used by `union`/
`intersection`/`difference`) for argument validation. Returns a new flat
list alternating one element from `list1`, one from `list2`, continuing
with whichever list still has elements once the other runs out (unlike
`zip`/`zip_with`, which truncate to the shorter length and pair elements
instead of flattening them).

Acceptance criteria:
- `interleave([1, 3, 5], [2, 4, 6])` is `[1, 2, 3, 4, 5, 6]`.
- `interleave([1, 2], [10, 20, 30, 40])` is `[1, 10, 2, 20, 30, 40]` (once
  the shorter list runs out, the rest of the longer list is appended as-is
  — this divergence from `zip`'s truncation is the point of the builtin).
- `interleave([], [1, 2])` is `[1, 2]`; `interleave([1, 2], [])` is
  `[1, 2]`.
- `interleave([], [])` is `[]`.
- A non-list argument raises `CinderRuntimeError` with line/column (reusing
  `_require_two_lists`'s existing error shape).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 2. Standard library: `from_entries` for maps [claimed 2026-07-29T20:53:20Z]

Build: add `from_entries(list)` to `cinder/builtins.py`, the inverse of the
existing `items(map)` — takes a list of `[key, value]` pairs and returns a
new map, matching `merge`/`pick`'s later-entry-wins collision rule (same
rule `items` itself round-trips: `from_entries(items(m))` reproduces `m`
for any map `m` with hashable keys, which is a good regression test).
Reuse `_is_valid_key` for key validation, matching `map_keys`/`invert`'s
existing guard.

Acceptance criteria:
- `from_entries([["a", 1], ["b", 2]])` is `{"a": 1, "b": 2}`.
- `from_entries([["a", 1], ["a", 2]])` is `{"a": 2}` — later entry wins.
- `from_entries([])` is `{}`.
- `from_entries(items({"x": 1, "y": 2}))` is `{"x": 1, "y": 2}` — round-trip
  regression test tying it to `items`.
- Each element of the list must itself be a 2-element list (`[key, value]`);
  anything else (wrong-length list, non-list element) raises
  `CinderRuntimeError` with line/column.
- A non-hashable key (e.g. a list) raises `CinderRuntimeError` with
  line/column, matching `_is_valid_key`'s existing guard elsewhere.
- Non-list top-level argument raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Standard library: `to_hex`, `to_bin`, `to_oct` for integers

Build: add `to_hex(n)`, `to_bin(n)`, `to_oct(n)` to `cinder/builtins.py` —
the string-formatting counterpart to the numeric-literal-parsing side
already shipped (`0x1F`/`0b101`/`0o17` literals, PR #73): each returns the
lowercase, unprefixed digit string for `n` in that base (via Python's
`format(n, 'x')`/`'b'`/`'o'`, not `hex()`/`bin()`/`oct()`, which include a
`0x`/`0b`/`0o` prefix that isn't wanted here), following `str`/`chr`'s
single-numeric-argument style.

Acceptance criteria:
- `to_hex(255)` is `"ff"`; `to_bin(5)` is `"101"`; `to_oct(8)` is `"10"`.
- `to_hex(0)` is `"0"`; `to_bin(0)` is `"0"`; `to_oct(0)` is `"0"`.
- `to_hex(-255)` is `"-ff"` (sign preserved, no two's-complement encoding —
  matching Python's own `format(n, 'x')` behavior for negative ints).
- A non-`int` argument (e.g. a `float` or `str`) raises
  `CinderRuntimeError` with line/column, for all three.
- Wrong arity raises `CinderRuntimeError` with line/column, for all three.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. `finally` block for `try`/`catch`

Build: extend the existing `try { ... } catch (name) { ... }`
(`TryStmt` in `cinder/ast_nodes.py:279-284`, parsed by `_try_statement` in
`cinder/parser.py:415-439`, executed by `_execute_try` in
`cinder/interpreter.py:284-290`) with an optional trailing
`finally { ... }` block that always runs — whether the `try` block
succeeded, raised a `CinderRuntimeError` caught by `catch`, or unwound via
an uncaught Python-internal control-flow signal (`_BreakSignal`,
`_ContinueSignal`, `_ReturnSignal`, or an uncaught `CinderRuntimeError`
from inside `catch` itself). Add a `FINALLY` keyword token to
`cinder/tokens.py`, give `TryStmt` a `finally_block: "Block" | None` field,
parse an optional `finally { ... }` after the existing catch clause
(reusing `_block()`), and implement `_execute_try` with a `try/finally`
around the existing `try/except CinderRuntimeError` so the finally block
runs via Python's own `finally` semantics regardless of exit path — no
change needed to how `break`/`continue`/`return` propagate through `try`
today, since Python's `finally` already re-raises after running.

Acceptance criteria:
- `let log = []; try { push(log, 1); } finally { push(log, 2); } log` is
  `[1, 2]` — finally runs after a clean try with no catch triggered.
- `let log = []; try { push(log, 1); assert(false, "x"); } catch (e) {
  push(log, 2); } finally { push(log, 3); } log` is `[1, 2, 3]` — finally
  runs after catch handles an error.
- A `return` inside a function's `try` block still runs `finally` before
  the function actually returns (test via a function that pushes to an
  outer-scope list in `finally` then checks the list after calling the
  function).
- `break`/`continue` inside a loop's `try` block still run `finally` before
  actually breaking/continuing the loop.
- `try { ... } finally { ... }` with no `catch` clause at all is valid
  (finally-only, matching a common pattern in other languages) — add a
  parser test and an interpreter test for this form.
- Omitting `finally` entirely still behaves exactly as before (regression
  test pinning today's catch-only behavior unchanged).
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`.

---

## 5. Standard library: `split_at` for lists

Build: add `split_at(list, index)` to `cinder/builtins.py` — returns
`[left, right]` where `left` is `list[0:index]` and `right` is
`list[index:]`, reusing `_normalize_slice_bound` (already imported from
`cinder/interpreter.py`, used by `_slice`/`_take`/`_drop` at
`cinder/builtins.py:1332-1386`) so a negative `index` counts from the end
and an out-of-range `index` clamps into `[0, len(list)]` instead of
erroring — matching `slice`'s bound-handling exactly, just splitting at
one point instead of two.

Acceptance criteria:
- `split_at([1, 2, 3, 4, 5], 2)` is `[[1, 2], [3, 4, 5]]`.
- `split_at([1, 2, 3], 0)` is `[[], [1, 2, 3]]`; `split_at([1, 2, 3], 3)`
  is `[[1, 2, 3], []]`.
- `split_at([1, 2, 3], -1)` is `[[1, 2], [3]]` (negative index counts from
  the end, like `slice`).
- `split_at([1, 2, 3], 10)` is `[[1, 2, 3], []]`; `split_at([1, 2, 3],
  -10)` is `[[], [1, 2, 3]]` (out-of-range clamps, doesn't error).
- `split_at([], 0)` is `[[], []]`.
- Non-list first argument raises `CinderRuntimeError` with line/column.
- Non-`int` index raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 6. Standard library: `rotate` for lists

Build: add `rotate(list, n)` to `cinder/builtins.py` — returns a new list
rotated left by `n` positions (`list[n:] + list[:n]` after reducing `n`
modulo the list's length), matching Python's own list-rotation idiom;
negative `n` rotates right. Non-mutating, matching `reverse`/`sort`/
`shuffle`'s style. An empty list is always returned unchanged regardless
of `n` (avoid `n % 0`).

Acceptance criteria:
- `rotate([1, 2, 3, 4, 5], 2)` is `[3, 4, 5, 1, 2]` (rotate left by 2).
- `rotate([1, 2, 3, 4, 5], -1)` is `[5, 1, 2, 3, 4]` (negative `n` rotates
  right).
- `rotate([1, 2, 3], 0)` is `[1, 2, 3]` (no-op).
- `rotate([1, 2, 3], 3)` is `[1, 2, 3]`; `rotate([1, 2, 3], 4)` is
  `[2, 3, 1]` (`n` larger than length wraps via modulo).
- `rotate([], 5)` is `[]` (empty list is always a no-op, no
  division-by-zero on the modulo).
- Non-list first argument raises `CinderRuntimeError` with line/column.
- Non-`int` `n` raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 7. `do { ... } while (cond);` loop

Build: add a `do { ... } while (<expr>);` loop that runs the body once
unconditionally before checking `cond` — the mirror of `while`'s
check-first semantics (`_while_statement` in `cinder/parser.py:281-289`,
executed inline in `Interpreter.execute` at `cinder/interpreter.py:245-253`
— there is no separate `_execute_while` method). Add a `DO` keyword token
to `cinder/tokens.py` (alongside `WHILE`, plus a `"do": TokenType.DO`
entry in the `KEYWORDS` map), and a `DoWhileStmt` AST node mirroring
`WhileStmt` (`cinder/ast_nodes.py:230-235`: `condition`, `body`, `line`,
`column`). Parse `do <statement> while (<expr>);` — note the trailing
semicolon after the `while (cond)` clause, unlike plain `while`, since the
body was already consumed as a statement and there's no block left to
terminate the statement; reuse `_loop_depth` bumping around the body
exactly like `_while_statement` does so `break`/`continue` are valid
inside it. Execute by running the body once, then looping on the same
check-then-repeat structure `WhileStmt` uses, with `break`/`continue`
caught the same way.

Acceptance criteria:
- `let i = 0; let log = []; do { push(log, i); i = i + 1; } while (i < 3);
  log` is `[0, 1, 2]`.
- `let i = 5; let log = []; do { push(log, i); } while (i < 0); log` is
  `[5]` — body runs exactly once even though the condition is false from
  the start (the defining difference from `while`).
- `break` inside the body exits the loop immediately without re-checking
  `cond` — test via a `do` loop whose condition is always true but whose
  body `break`s after one iteration.
- `continue` inside the body skips to the condition check, not back to
  the top of the body unconditionally — test with a counter that would
  infinite-loop if `continue` re-ran the body without re-checking `cond`.
- `do { ... } while (cond)` with no trailing `;` raises a `ParseError`
  with line/column (semicolon required, matching every other simple
  statement).
- Existing `while` loops are unaffected — add a regression test that a
  plain `while (cond) { ... }` still parses/executes exactly as before.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`.

---

## 8. `const` declarations for immutable bindings

Build: add `const NAME = expr;` as a sibling to `let` that binds `NAME` in
the current scope like `LetStmt` does (`cinder/interpreter.py:195-197`:
`env.define(stmt.name, self.evaluate(stmt.initializer, env))`) but forbids
any later assignment to that name — plain (`NAME = ...`), compound
(`NAME += ...`, desugared through `Assign` at parse time per PR #32/#103),
and any other form that funnels through `Environment.assign`
(`cinder/interpreter.py:141-148`) — raising `CinderRuntimeError` with
line/column instead of silently mutating. Since `Environment._values`
(`cinder/interpreter.py:123-148`) is currently a plain
`dict[str, object]` with no per-name metadata, add a parallel
`self._frozen: set[str] = set()` to `Environment`, populated by a new
`define_const` method (or a `const: bool` flag on the existing `define`),
and check it at the top of `assign` before mutating, raising there. Add a
`CONST` keyword token (`cinder/tokens.py`, alongside `LET`) and a
`ConstStmt` AST node mirroring `LetStmt` (`cinder/ast_nodes.py:199-204`:
`name`, `initializer`, `line`, `column`). Index-assignment (`xs[i] = ...`)
is unaffected by this task — it mutates the list/map object referenced by
a binding, not the binding itself, so `const xs = [1]; xs[0] = 2;` still
works; only rebinding the name `xs` itself is forbidden.

Acceptance criteria:
- `const x = 5; x` is `5`.
- `const x = 5; x = 6;` raises `CinderRuntimeError` with line/column (the
  assignment's location), leaving `x` unchanged.
- `const x = 5; x += 1;` raises `CinderRuntimeError` with line/column
  (compound assignment funnels through the same `assign` path).
- `const xs = [1, 2]; xs[0] = 9; xs` is `[9, 2]` — index-assignment
  through a `const` binding is unaffected, since it mutates the list, not
  the name.
- `const` requires an initializer — `const x;` raises a `ParseError` with
  line/column.
- A `const` in an inner block scope shadowing an outer `let`/`const` of
  the same name is a fresh, independent binding (matching `let`'s
  existing shadowing rule) — reassigning the *outer* name after the inner
  block exits still works if the outer was `let`.
- Redeclaring the same name with a second `const` (or `let`) in the
  *same* scope — pick whichever `let`'s existing redeclaration behavior
  already is (likely silently rebinds, since `Environment.define` just
  overwrites the dict entry) and add a regression test pinning it, rather
  than introducing new redeclaration-checking behavior as a side effect
  of this task.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
