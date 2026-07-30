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

## 1. `const` declarations for immutable bindings [claimed 2026-07-30T14:37:48Z]

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

## 2. Standard library: `unzip` for lists

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

## 3. C-style `for (init; cond; step) { ... }` loop

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

## 4. Standard library: `zip_longest` for lists

Build: add `zip_longest(list1, list2, fill)` to `cinder/builtins.py` —
like `zip` (`_zip` at `cinder/builtins.py:1584-1597`, which truncates to
the shorter list via Python's own `zip`) but pads the shorter list with
`fill` instead of truncating, so the result always has
`max(len(list1), len(list2))` pairs. Reuse the same two-list validation
style `_zip` already uses (a `list` check on each argument, not
`_require_two_lists` since that helper is arity-2 only and this builtin
is arity-3) plus `_require_arity("zip_longest", arguments, 3, line,
column)`. Implement with `itertools.zip_longest(list1, list2,
fillvalue=fill)` (stdlib `itertools` — no new dependency, already usable
via Python's standard library) wrapped in a list comprehension producing
`[a, b]` pairs, mirroring `_zip`'s `[[a, b] for a, b in ...]` shape.

Acceptance criteria:
- `zip_longest([1, 2, 3], ["a", "b"], nil)` is `[[1, "a"], [2, "b"], [3,
  nil]]` — shorter list padded with `fill` (here `nil`) once it runs out.
- `zip_longest([1], [1, 2, 3], 0)` is `[[1, 1], [0, 2], [0, 3]]` — padding
  works symmetrically when the *first* list is shorter.
- `zip_longest([1, 2], [1, 2], "x")` is `[[1, 1], [2, 2]]` — equal-length
  lists behave exactly like `zip`, `fill` unused.
- `zip_longest([], [], 0)` is `[]`.
- `zip_longest([], [1, 2], 0)` is `[[0, 1], [0, 2]]`.
- A non-list first or second argument raises `CinderRuntimeError` with
  line/column (mirror `_zip`'s two separate checks/messages).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 5. Standard library: `group_consecutive` for lists

Build: add `group_consecutive(list)` to `cinder/builtins.py` — groups
*adjacent* equal elements into sublists, i.e. run-length grouping (the
list-native cousin of `group_by`, which groups by key across the whole
list regardless of position — `_group_by` at
`cinder/builtins.py:1781-...`). Equality between elements uses the same
`==` semantics Cinder's interpreter already applies to values (structural
equality for lists/maps, value equality for numbers/strings/bools/nil) —
implement by iterating once, comparing each element to the last element
of the current run with plain Python `==` (safe here since Cinder values
are plain Python `int`/`float`/`str`/`bool`/`None`/`list`/`dict` at
runtime, same assumption `unique`/`distinct_by` already rely on), and
starting a new run on a mismatch. Validate with
`_require_arity("group_consecutive", arguments, 1, line, column)` then a
`list` check, mirroring `_flatten`'s single-list validation style
(`cinder/builtins.py:1506-...`).

Acceptance criteria:
- `group_consecutive([1, 1, 2, 2, 2, 1])` is `[[1, 1], [2, 2, 2], [1]]` —
  note the trailing `1` is its own group since it's not adjacent to the
  earlier `1, 1` run.
- `group_consecutive([1, 2, 3])` is `[[1], [2], [3]]` — no adjacent
  duplicates means every element is its own singleton group.
- `group_consecutive([])` is `[]`.
- `group_consecutive(["a", "a", "a"])` is `[["a", "a", "a"]]` — a single
  run covering the whole list.
- `group_consecutive([[1, 2], [1, 2], [3]])` is `[[[1, 2], [1, 2]],
  [[3]]]` — structural equality groups equal *list* elements adjacently,
  not just primitives.
- A non-list argument raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 6. Nil-coalescing compound assignment: `??=`

Build: add `x ??= expr;` as a compound-assignment sibling to the existing
set (`+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`, handled
via `_COMPOUND_ASSIGN_OPS` in `cinder/parser.py:138-149`) that assigns
`expr` to `x` only when `x` is currently `nil`, mirroring the existing
`??` nil-coalescing operator (`_nullish` in `cinder/parser.py:621-627`,
lexed in `cinder/lexer.py:351-357`'s `_question`, evaluated as a
short-circuiting `Logical` node at `cinder/interpreter.py:577` — `right`
is only evaluated when `left` is `nil`, unlike `or` which short-circuits
on any truthy value). `??=` cannot reuse the existing compound-assign
desugaring path used by `+=`/etc. as-is: that path wraps the target and
value in a `Binary` node (`cinder/parser.py:584`:
`binary = Binary(expr, binary_operator, value)`), but `Binary` always
evaluates both operands eagerly — `x ??= f()` must not call `f()` when
`x` is already non-nil, exactly like `??` doesn't evaluate its right side
unnecessarily. Instead, when the new `QQEQ` token is seen, desugar to
`Assign(expr.name, Logical(expr, qq_operator, value), ...)`, where
`qq_operator` is a synthetic `Token(TokenType.QUESTION_QUESTION, "??",
None, op_token.line, op_token.column)` — mirroring how the existing path
builds `binary_operator` from `op_token` at `cinder/parser.py:576-582`,
but typed `QUESTION_QUESTION` (not `QQEQ`) since `_evaluate_logical`
(`cinder/interpreter.py:567-581`) dispatches on `expr.operator.type` and
only recognizes `OR`/`AND`/`QUESTION_QUESTION` — a `Logical` node
carrying `QQEQ` would hit that function's final `raise TypeError`. This
is the same `Logical` shape `??` itself produces, just constructed
directly in `_assignment()` rather than routed through the generic
`_COMPOUND_ASSIGN_OPS` dict/`Binary` path (since that dict maps each
compound-assign token to a plain binary operator token, which doesn't
fit a short-circuiting `Logical` node).
Add `QQEQ = auto()` to `cinder/tokens.py` (near `QUESTION_QUESTION`), and
teach `cinder/lexer.py`'s `_question` to check for a third `=` after
matching the second `?` (i.e. `??=` scans as one token, not `??` followed
by `=`) — mirror how `_question` already uses `self._match("?")` to
distinguish `?` from `??`, adding a further `self._match("=")` check once
`??` has matched to decide between emitting `QUESTION_QUESTION` and the
new `QQEQ`. Only an `Identifier` target is supported (matching the
arithmetic compound-assign ops' identifier-only restriction noted at
`cinder/parser.py:150-151` — `??=` is not added to
`_INDEX_TARGET_COMPOUND_ASSIGN_OPS`, so `xs[0] ??= 1` is out of scope for
this task and should raise the same "invalid assignment target"
`ParseError` an unsupported index target already raises for e.g. `xs[0]
%= 2`).

Acceptance criteria:
- `let x = nil; x ??= 5; x` is `5`.
- `let x = 1; x ??= 5; x` is `1` — non-nil `x` is left untouched.
- `let x = false; x ??= 5; x` is `false` — `false` is not `nil`, so it is
  *not* replaced (contrast with `x ||= 5`-style truthiness, which this
  language doesn't have; this pins that `??=` checks nil-ness only).
- `let calls = 0; fn bump() { calls = calls + 1; return 99; } let x = 1;
  x ??= bump(); calls` is `0` — the right-hand side is not evaluated when
  the target is already non-nil (short-circuiting, same as `??`).
- `let calls = 0; fn bump() { calls = calls + 1; return 99; } let x = nil;
  x ??= bump(); calls` is `1` and `x` is `99` — the right-hand side *is*
  evaluated exactly once when the target is `nil`.
- `let xs = [nil]; xs[0] ??= 1;` raises a `ParseError` ("invalid
  assignment target") with line/column — index targets are out of scope
  for this task.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/parser.py`,
`tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.

---

## 7. Standard library: `sliding_window` for lists

Build: add `sliding_window(list, size)` to `cinder/builtins.py` — like
`chunk` (`_chunk` at `cinder/builtins.py:1599-1615`) but windows
*overlap* by `size - 1` elements instead of partitioning the list into
disjoint pieces, i.e. every contiguous run of `size` elements, sliding
forward by one each time (`[list[i:i+size] for i in range(0, len(list) -
size + 1)]`). Mirror `_chunk`'s validation exactly: `_require_arity`,
a `list` check on the first argument, an `int`-and-not-`bool` check on
`size` (`isinstance(size, int) and not isinstance(size, bool)`, following
`cinder/builtins.py:1607`'s existing pattern since Cinder's runtime
booleans are Python `bool`, a subclass of `int`), and a positive-size
check — reusing the exact same error-message phrasing `_chunk` uses with
`sliding_window` substituted for `chunk`. Unlike `chunk`, a `size` larger
than the list's length is not an error: it simply produces zero windows
(`sliding_window([1, 2], 5)` is `[]`), matching what the range-based
comprehension above naturally does when `len(list) - size + 1 <= 0` —
add an explicit test pinning this rather than special-casing it as an
error.

Acceptance criteria:
- `sliding_window([1, 2, 3, 4], 2)` is `[[1, 2], [2, 3], [3, 4]]`.
- `sliding_window([1, 2, 3, 4], 3)` is `[[1, 2, 3], [2, 3, 4]]`.
- `sliding_window([1, 2, 3], 1)` is `[[1], [2], [3]]`.
- `sliding_window([1, 2], 5)` is `[]` — window larger than the list
  produces no windows, not an error.
- `sliding_window([], 1)` is `[]`.
- A non-list first argument raises `CinderRuntimeError` with line/column.
- A non-int, or int-but-`bool`, `size` raises `CinderRuntimeError` with
  line/column.
- A zero or negative `size` raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
