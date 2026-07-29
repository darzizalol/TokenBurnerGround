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

## 1. Standard library: `split_at` for lists [claimed 2026-07-29T21:30:40Z]

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

## 2. Standard library: `rotate` for lists

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

## 3. `do { ... } while (cond);` loop

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

## 4. `const` declarations for immutable bindings

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

## 5. Standard library: `unzip` for lists

Build: add `unzip(pairs)` to `cinder/builtins.py` — the inverse of `zip`
(`_zip` at `cinder/builtins.py:1558-1571`): takes a list of 2-element
`[a, b]` pairs and returns `[list_of_firsts, list_of_seconds]`. Validate
with `_require_arity("unzip", arguments, 1, line, column)` then check the
argument is a `list`; each element must itself be a `list` of length
exactly 2 (raise `CinderRuntimeError` naming the offending index on any
element that isn't a 2-element list, e.g. `f"unzip() requires a list of
2-element lists, got {type_name(element)} at index {i}"` or similar,
mirroring the style of `_require_two_lists` at
`cinder/builtins.py:1082-1095`). An empty input list returns `[[], []]`
(not an error) — reduces from `zip(pairs)`'s intuition that unzip and
`zip` should round-trip: `zip(*unzip(pairs)) == pairs` in spirit, though
Cinder's `zip` only takes exactly two lists so the round-trip is via
`zip(unzip(pairs)[0], unzip(pairs)[1])`.

Acceptance criteria:
- `unzip([[1, "a"], [2, "b"], [3, "c"]])` is `[[1, 2, 3], ["a", "b",
  "c"]]`.
- `unzip([])` is `[[], []]`.
- `unzip([[1, 2]])` is `[[1], [2]]`.
- `zip(unzip(pairs)[0], unzip(pairs)[1])` reproduces the original `pairs`
  for a non-empty example — add this as an explicit round-trip test
  alongside the direct-output assertions above.
- A non-list argument raises `CinderRuntimeError` with line/column.
- An element that isn't a list, or is a list of the wrong length (0, 1, or
  3+ elements), raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 6. C-style `for (init; cond; step) { ... }` loop

Build: add a second `for` form alongside the existing foreach
(`for NAME in EXPR { ... }`, `ForStmt` in `cinder/ast_nodes.py:238-244`,
parsed by `_for_statement` in `cinder/parser.py:291-309`, executed by
`_execute_for` in `cinder/interpreter.py:292-...`): a classic three-clause
`for (init; cond; step) { ... }`, disambiguated at parse time by peeking
right after the `for` keyword — the foreach form always continues with an
`IDENTIFIER` then `in`, while the C-style form always continues with `(`,
so `_for_statement` can dispatch on `self._check(TokenType.LPAREN)` before
falling into the existing identifier-consuming path. Add a `ForCStmt` AST
node (`init: Stmt | None`, `condition: Expr | None`, `step: Stmt | None`,
`body: Stmt`, `line`, `column`) to `cinder/ast_nodes.py`. Parse: `init` is
either a `let` declaration (reuse `_let_statement`, which already consumes
its own trailing `;`) or an expression/increment statement reusing the
same expr-then-optional-`++`/`--`-then-`;` logic `_expr_statement` uses
today (`cinder/parser.py:482-515`) — factor that logic out of
`_expr_statement` into a helper both call, since the for-loop needs it
without necessarily wrapping every clause; an empty init clause (just
`;`) is valid and leaves `init` as `None`. `condition` is an optional
`_assignment()` expression, defaulting to always-true when omitted
(`for (;;) { ... }` is a valid infinite loop, matching C). `step` is an
optional expression/increment (same helper as init, but not consuming a
trailing `;` — the closing `)` terminates it instead). Execute in
`_interpreter.py`: create a fresh child `Environment` for the loop (so an
`init` `let` doesn't leak into the enclosing scope, matching block-scoping
elsewhere), run `init` once, then loop while `condition` is truthy (or
unconditionally if omitted): run `body` catching `_BreakSignal` (exit the
loop) and `_ContinueSignal` (fall through *without* re-raising — do not
`continue` the Python loop directly, since `step` must still run before
the next condition check), then always run `step` (if present) before
re-checking `condition` — this mirrors the do-while task's
continue-runs-step-not-body distinction so `continue` can't skip `step`
and infinite-loop.

Acceptance criteria:
- `let log = []; for (let i = 0; i < 3; i = i + 1) { push(log, i); } log`
  is `[0, 1, 2]`.
- `let log = []; for (let i = 0; i < 3; i++) { push(log, i); } log` is
  `[0, 1, 2]` — `i++` works as the step clause.
- `let i = 0; let log = []; for (; i < 3; i++) { push(log, i); }` (empty
  init) is `[0, 1, 2]`, reusing the outer `i`.
- `for (let i = 0; i < 5; i++) { if (i == 2) { break; } push(log, i); }`
  stops after `[0, 1]` — `break` exits without running `step` again.
- `let log = []; for (let i = 0; i < 5; i++) { if (i == 2) { continue; }
  push(log, i); } log` is `[0, 1, 3, 4]` — `continue` skips to `step`,
  not back to the top of `body` unconditionally (test with a case that
  would infinite-loop if `step` were skipped).
- `for (;;) { break; }` parses and runs (condition omitted = infinite
  loop, immediately broken).
- `init`'s `let i = 0` is scoped to the loop only — referencing `i` after
  the loop raises a name-resolution `CinderRuntimeError`, it doesn't leak
  into the enclosing scope.
- The existing foreach `for NAME in EXPR { ... }` is unaffected — add a
  regression test that it still parses/executes exactly as before.
- Full test suite passes.

Likely files: `cinder/tokens.py` (none new needed — reuses existing
`LPAREN`/`SEMICOLON`/`RPAREN`), `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_lexer.py` (only if untouched
regression coverage is missing), `tests/test_parser.py`,
`tests/test_interpreter.py`.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
