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

## 1. Standard library: `range`

Build: extend `cinder/builtins.py` with `range(stop)` and `range(start,
stop)`, both returning a materialized `list` of ints from `start`
(default `0`, inclusive) up to `stop` (exclusive) — no lazy iterator type
exists in Cinder, so this must eagerly build the list, same as Python's
`list(range(...))`. Only integer arguments are accepted (no `float`,
matching list-index argument strictness elsewhere); reject any non-int
argument with `CinderRuntimeError` and line/column. A `stop <= start` (or
`stop <= 0` in the one-argument form) is not an error — it returns `[]`,
matching Python. Reject calls with zero arguments or more than two with
`CinderRuntimeError` (same variadic-arity style as `min`/`max` from task
1 — write the check inline). No `step` argument in this task, to keep it
one session; a 3-argument step form is a natural future task if wanted.

Acceptance criteria:
- `range(5)` is `[0, 1, 2, 3, 4]`; `range(2, 5)` is `[2, 3, 4]`.
- `range(0)` is `[]`; `range(3, 3)` is `[]`; `range(5, 2)` is `[]` (no
  error, matches Python).
- `range("x")` and `range(1, "x")` raise `CinderRuntimeError` with
  line/column; `range(1.5)` likewise (no float arguments).
- `range()` and `range(1, 2, 3)` raise `CinderRuntimeError` with
  line/column (wrong arity).
- `for i in range(3) { print(i); }` prints `0`, `1`, `2` on separate
  lines (exercises PR #17's list `for`-in with this builtin's output).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 2. Standard library: `map` and `filter`

Build: extend `cinder/builtins.py` with `map(list, fn)` and `filter(list,
fn)`, both returning a **new** list (non-mutating, matching `reverse`/`sort`)
and accepting a Cinder function *value* as the second argument — either a
`CinderFunction` (a `fn`-declared closure) or a `Builtin` (a stdlib function
passed by name, e.g. `abs`). Calling a `Builtin` is already a one-liner
(`callee.call(arguments, expr.line, expr.column)`, `cinder/interpreter.py:229`),
but calling a `CinderFunction` is currently *inline* logic inside
`Interpreter._evaluate_call` (`cinder/interpreter.py:225-248`: arity check,
new `Environment(callee.closure)`, `self.execute(callee.decl.body,
call_env)`, catch `_ReturnSignal`) — there is no reusable method for it yet.
First refactor that block into a standalone helper both call sites share
(e.g. a module-level `call_value(callee, arguments, line, column)` in
`interpreter.py` handling both `Builtin` and `CinderFunction` dispatch, with
`_evaluate_call` reduced to `return call_value(callee, arguments, expr.line,
expr.column)`); `Interpreter` holds no instance state so this is a
mechanical extraction, not a behavior change — the existing `_evaluate_call`
tests must keep passing unmodified. Then have `map`/`filter` in
`builtins.py` import and call that helper. `map`'s callback takes one
argument (the element) and its return value becomes the output element;
`filter`'s callback takes one argument and the element is kept iff the
return value is truthy (reuse the existing truthiness rule — `nil`/`false`
are falsy, everything else truthy). First argument must be a `list`; second
argument must be callable (`CinderFunction` or `Builtin`) — anything else
raises `CinderRuntimeError` with line/column, matching `sort`/`reverse`'s
type-check style. Propagate the callback's own `CinderRuntimeError` (e.g.
wrong arity) unchanged if it raises one.

Acceptance criteria:
- `map([1, 2, 3], fn(x) { return x * 2; })` is `[2, 4, 6]`.
- `filter([1, 2, 3, 4], fn(x) { return x > 2; })` is `[3, 4]`.
- `map([1, -2, 3], abs)` is `[1, 2, 3]` (built-in function passed by name).
- `map(5, fn(x) { return x; })` raises `CinderRuntimeError` (first arg not a
  list) with line/column.
- `map([1, 2], 5)` raises `CinderRuntimeError` (second arg not callable) with
  line/column.
- Neither builtin mutates its input list (regression test).
- `filter([], fn(x) { return true; })` is `[]`; same for `map` on `[]`.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Standard library: `reduce`

Build: extend `cinder/builtins.py` with `reduce(list, fn, initial)`,
folding the list left-to-right into a single value: `acc = initial`, then
for each element `acc = fn(acc, element)`, returning the final `acc`.
Depends on task 2's `call_value` helper in `cinder/interpreter.py` for
invoking `fn` (a `CinderFunction` or `Builtin`, two-argument callback) —
do not attempt this task before task 2 lands, and reuse `call_value`
rather than re-inlining call dispatch. First argument must be a `list`;
second argument must be callable; anything else raises
`CinderRuntimeError` with line/column, matching `map`/`filter`'s
type-check style. An empty list returns `initial` unchanged without
calling `fn`. Propagate the callback's own `CinderRuntimeError` (e.g.
wrong arity — `fn` here takes exactly two arguments, not one like
`map`/`filter`'s callback) unchanged if it raises one.

Acceptance criteria:
- `reduce([1, 2, 3], fn(acc, x) { return acc + x; }, 0)` is `6`.
- `reduce([1, 2, 3, 4], fn(acc, x) { return acc * x; }, 1)` is `24`.
- `reduce([], fn(acc, x) { return acc + x; }, 0)` is `0` (fn never called
  — regression test can assert this via a side-effecting fn, e.g. one
  that also mutates an outer list via `push`, and checking it stayed
  empty).
- `reduce(5, fn(acc, x) { return acc; }, 0)` raises `CinderRuntimeError`
  (first arg not a list) with line/column.
- `reduce([1, 2], 5, 0)` raises `CinderRuntimeError` (second arg not
  callable) with line/column.
- The list passed to `reduce` is unchanged afterward (regression test).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. Standard library: `find`, `starts_with`, `ends_with`, `replace`

Build: extend `cinder/builtins.py` with four string builtins, following
the existing two-string-argument style of `split(s, sep)`:
`find(s, sub)` returns the lowest index at which `sub` occurs in `s` (an
int), or `-1` if not found (matching Python's `str.find`, not `str.index`
— no exception for "not found"); `starts_with(s, prefix)` and
`ends_with(s, suffix)` return a `bool`; `replace(s, old, new)` returns a
**new** string with all non-overlapping occurrences of `old` replaced by
`new` (Python's `str.replace(old, new)`, no count limit). All four take
only `str` arguments — reject anything else (including a non-str `s`)
with `CinderRuntimeError` and line/column, matching `_split`'s type-check
style. An empty `old` in `replace` is a Python-legal no-op-per-character
edge case (`"ab".replace("", "-")` is `"-a-b-"` in Python) — keep that
behavior rather than special-casing it, since it matches host semantics
and no existing builtin special-cases empty separators except `split`
(which explicitly rejects them per PR #18 — `replace` is a different
operation and Python's `str.replace("")` doesn't raise, so don't add a
check here).

Acceptance criteria:
- `find("hello", "ll")` is `2`; `find("hello", "z")` is `-1`.
- `starts_with("hello", "he")` is `true`; `starts_with("hello", "x")` is
  `false`. Same shape for `ends_with`.
- `replace("aaa", "a", "b")` is `"bbb"`; `replace("hello", "z", "x")` is
  `"hello"` (no match, unchanged).
- Each builtin raises `CinderRuntimeError` with line/column when any
  argument isn't a `str`, and on wrong arity.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 5. Standard library: `slice` and `concat` for lists

Build: extend `cinder/builtins.py` with `slice(list, start, end)`,
returning a **new** list containing elements from index `start`
(inclusive) to `end` (exclusive), Python-slice-style — `start`/`end` may
be negative (same normalization rule `_evaluate_index` already applies
in `cinder/interpreter.py` for negative list/string indices: `index +
len(obj)`), and out-of-range bounds clamp rather than error (matching
Python's `list[start:end]` — `slice([1,2,3], 0, 10)` is `[1,2,3]`, not an
error). Also add `concat(list1, list2)`, returning a **new** list that is
`list1`'s elements followed by `list2`'s (neither input mutated, matching
`reverse`/`sort`'s non-mutating style — this is the two-list counterpart
to `push`'s single-element in-place append). `slice`'s `start`/`end` must
be `int` (reject `float`/other types with `CinderRuntimeError` and
line/column, matching `range`'s int-only rule); non-list first argument
to either builtin is likewise a `CinderRuntimeError`.

Acceptance criteria:
- `slice([1, 2, 3, 4], 1, 3)` is `[2, 3]`; `slice([1, 2, 3], -2, -1)` (once
  the negative-index rule linked above lands) is `[2]`.
- `slice([1, 2, 3], 0, 100)` is `[1, 2, 3]` (out-of-range end clamps, no
  error).
- `concat([1, 2], [3, 4])` is `[1, 2, 3, 4]`; `concat([], [1])` is `[1]`.
- Neither builtin mutates either input list (regression test).
- `slice(5, 0, 1)` and `concat(5, [1])` raise `CinderRuntimeError` with
  line/column (non-list argument); `slice([1,2], 0.5, 1)` likewise (non-int
  bound).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 6. Standard library: `assert`

Build: extend `cinder/builtins.py` with `assert(condition, message)`
(exactly two arguments — a value checked with Cinder's existing
truthiness rule, and a `str` message), raising `CinderRuntimeError` with
that message and the call's line/column if `condition` is falsy
(`nil`/`false`); returns `nil` (same as `print`) if the condition is
truthy and has no other effect. This gives Cinder programs themselves a
way to self-check invariants — useful for future example programs and
for exercising other builtins/language features from *within* `.cin`
scripts rather than only from the Python test suite. `message` must be a
`str` (reject non-str with `CinderRuntimeError`, matching every other
builtin's type-check style); wrong arity is likewise a
`CinderRuntimeError`.

Acceptance criteria:
- `assert(true, "should not fire");` runs with no error and no output.
- `assert(1 == 2, "math is broken");` raises `CinderRuntimeError` whose
  message includes `"math is broken"`, with line/column of the `assert`
  call.
- `assert(0, "zero is falsy? no");` does NOT raise (Cinder's `0` is
  truthy, per the fixed truthiness rule in `PROJECT.md` — this is a
  regression check that `assert` reuses that rule rather than Python
  truthiness).
- `assert(false, 42);` (non-str message) raises `CinderRuntimeError` for
  the bad argument type, not for the assertion itself.
- `assert(true);` and `assert(true, "x", "y");` (wrong arity) raise
  `CinderRuntimeError` with line/column.
- Add one `examples/*.cin` using `assert` to demonstrate a self-checking
  script, with its `.expected` golden file (empty stdout if all asserts
  pass silently).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`,
`examples/`.

---

## Done

- **Project scaffolding** — merged 2026-07-18T14:07:26Z via PR #1
  (`night/20260718-project-scaffolding`). Built `cinder/` package skeleton
  and `tests/` harness (argparse CLI stub, `TokenType.EOF` stub, passing
  test suite).
- **Lexer: tokenize literals, identifiers, operators, comments** — merged
  2026-07-18T14:17:28Z via PR #2 (`night/20260718-lexer`). Built
  `cinder/lexer.py`, fleshed out `cinder/tokens.py`'s `TokenType`, and added
  `LexError` with line/column to `cinder/errors.py`.
- **Parser: expressions with correct precedence** — merged
  2026-07-18T14:28:38Z via PR #3 (`night/20260718-parser`). Built
  `cinder/ast_nodes.py` and `cinder/parser.py`, a recursive-descent parser
  with standard precedence and parenthesized grouping/calls, plus
  `ParseError` with line/column in `cinder/errors.py`.
- **Tree-walking evaluator for expressions** — merged 2026-07-18T14:39:19Z
  via PR #4 (`night/20260718-evaluator-expressions`). Built
  `cinder/interpreter.py` with `Environment` (lexical scoping) and
  `Interpreter.evaluate()` for the full expression AST (arithmetic,
  comparisons, short-circuit logical ops, unary, grouping, identifier
  lookup); `Call` intentionally left unimplemented pending task 3 (was
  task 4 pre-renumber).
- **Statements: `let`, blocks, and end-to-end CLI wiring** — merged
  2026-07-19T14:07:31Z via PR #5 (`night/20260718-statements`). Built
  `ExprStmt`/`LetStmt`/`Block` AST nodes, parser support for `let`
  statements and `{ ... }` blocks plus `parse_program`, and
  `Interpreter.execute(stmt, env)` handling all three; wired
  `cinder/cli.py`'s `run` subcommand to lex→parse→execute a `.cin` file
  end to end. Started as WIP rescued after a prior session was killed
  mid-work by the nightly hard stop; rebased, reviewed, and verified
  before merge.
- **Control flow: `if`/`else` and `while`** — merged 2026-07-19T14:20:00Z
  via PR #6 (`feat/20260719-control-flow`). Built `IfStmt`/`WhileStmt` AST
  nodes, parser and evaluator support, and a minimal assignment expression
  (`name = expr`) with `Environment.assign` walking the scope chain. Pinned
  the truthiness rule (`nil`/`false` falsy, everything else truthy,
  including `0`/`""`) in `PROJECT.md`.
- **Functions: declarations, calls, closures, `return`** — merged
  2026-07-19T14:38:45Z via PR #7 (`feat/20260719-functions`). Built
  `FnDecl`/`ReturnStmt` AST nodes, parser support for `fn name(a, b) { ... }`
  and call expressions, and evaluator support for first-class functions
  that capture their defining `Environment` (closures), arity-checked
  calls, and `return` unwinding via an internal control-flow signal.
  Bounced once on review: top-level `return` originally leaked a raw
  `_ReturnSignal` Python traceback; fixed by tracking function-nesting
  depth in the parser and raising `ParseError` for `return` outside a
  function.
- **Data structures: lists and maps** — merged 2026-07-19T~14:50Z via PR #8
  (`feat/20260719-lists-maps`). Built `ListLiteral`/`MapLiteral`/`Index`/
  `IndexAssign` AST nodes, parser support for `[1, 2, 3]` and `{"a": 1}`
  literals plus `expr[expr]` get/set (backed by Python `list`/`dict`), and
  a `COLON` token for map-literal syntax. Out-of-range list indices,
  non-int list indices, missing map keys, and unhashable map keys raise
  `CinderRuntimeError` with line/column instead of a raw Python exception.
  Reviewer flagged a pre-existing, non-blocking grammar wrinkle: because
  `_statement()` special-cases a leading `{` as a block, a bare
  map-literal expression statement like `{"a": 1};` parses as a block, not
  a `MapLiteral` — worth fixing whenever statement-level map literals are
  needed.
- **Standard library: builtins (`print`, `len`, `type`, conversions)** —
  merged 2026-07-19T15:03:10Z via PR #9 (`feat/20260719-builtins`). Built
  `cinder/builtins.py` with `print`, `len`, `type`, `str`, `int`, `float`
  injected into the global `Environment`; renamed `_type_name` to
  `type_name` in `interpreter.py` to share it. Reviewer noted a minor,
  non-blocking semantic shift: `_evaluate_call` now evaluates arguments
  before the not-callable check, so side effects in args to a non-callable
  run before the error is raised.
- **Error diagnostics polish** — merged 2026-07-19T15:12:10Z via PR #10
  (`fix/20260719-error-diagnostics`). `cinder/cli.py`'s `run` subcommand now
  catches `CinderError` and prints a one-line `file:line:column: message`
  diagnostic to stderr with a non-zero exit code, instead of leaking a raw
  Python traceback. QA noted a non-blocking gap: a nonexistent script path
  still raises a raw `FileNotFoundError` traceback, since that's not a
  `CinderError` subclass — out of scope for this task.
- **Example programs** — merged 2026-07-19T19:08:09Z via PR #11
  (`feat/20260719-example-programs`). Built `examples/` with `fizzbuzz.cin`,
  `fibonacci.cin`, and `list_ops.cin`, each with a checked-in `.expected`
  golden-output file, plus `tests/test_examples.py` which subprocess-runs
  every `examples/*.cin` file and diffs stdout against its golden file so
  regressions anywhere in the pipeline get caught end to end.
- **Fix: statement-level map literals parse as blocks** — merged
  2026-07-19T19:26:49Z via PR #12 (`fix/20260719-map-literal-stmt`).
  `_brace_statement()` now speculatively parses a full `self._assignment()`
  (the same entry point `_expr_statement` uses) instead of just the bare
  `_map_literal()`, so a leading `{` at statement position that turns out
  to be a map literal — including with postfix indexing/calls or binary
  operators applied to it — is captured as `ExprStmt(MapLiteral)` instead
  of misfiring into a broken `Block`. Bounced once on review: the first
  pass only covered the bare-literal case (`{"a": 1};`) and still failed
  on `{"a": 1}["a"];`, `{"a": 1}();`, and `{"a": 1} == {"a": 1};`; fixed by
  broadening the speculative parse to the full expression grammar.
  Documented the disambiguation rule in `PROJECT.md`.
- **REPL: interactive read-eval-print loop** — merged 2026-07-19T19:46:39Z
  via PR #13 (`feat/20260719-repl`). Built `cinder/repl.py`: reads stdin
  line by line, accumulates input until a statement is complete, executes
  each complete statement against a persistent `Environment`, and echoes
  bare-expression values. Wired `cinder/cli.py`'s `repl` subcommand to it.
  Bounced once on review: `_needs_more_input` treated every `LexError` as
  "unterminated string" and kept buffering forever on an illegal character,
  silently swallowing all further input until EOF with no diagnostic; fixed
  by giving `LexError` an `unterminated: bool` flag set only at the
  unterminated-string sites in `cinder/lexer.py`, so other lex failures now
  fall through to the normal `CinderError` report-and-continue path.

---

- **Standard library: list/map growth and iteration helpers** — merged
  2026-07-19T19:55:16Z via PR #14 (`feat/20260719-list-map-helpers`). Added
  `push`, `pop`, `keys`, `values` builtins to `cinder/builtins.py`, mutating
  the underlying list/dict in place (consistent with existing index-assign
  reference semantics), plus `examples/collections.cin` exercised by the
  golden-output test harness. Reviewer noted a non-blocking nit: the module
  docstring still doesn't mention the new builtins.
- **Fix: `run` leaks raw traceback for missing/unreadable script** — merged
  2026-07-19T20:02:34Z via PR #15 (`fix/20260719-run-file-open`). Catches
  `OSError` around `run_file`'s `open()` and prints a clean one-line
  `cinder: run: <path>: <reason>` diagnostic to stderr with exit code 1,
  instead of leaking a raw Python traceback, for missing/unreadable script
  paths. `CinderError` handling is unchanged.
- **String indexing** — merged 2026-07-19T20:11:00Z via PR #16
  (`feat/20260719-string-indexing`). Extended `_evaluate_index`/
  `_evaluate_index_assign` in `cinder/interpreter.py` so `s[i]` returns a
  length-1 string for a valid `int` index, mirroring list indexing's
  out-of-range/non-int error style; `IndexAssign` on a string raises
  `CinderRuntimeError` explaining strings are immutable instead of
  crashing or silently no-oping.
- **`for`-in loop over lists** — merged 2026-07-20T~06:00Z via PR #17
  (`feat/20260720-for-in-loop`). Added `for NAME in EXPR { ... }` support:
  a `ForStmt` AST node, parser rule reusing block-statement parsing for the
  body, and evaluator support that evaluates the iterable once, raises
  `CinderRuntimeError` for a non-list iterable, and binds the loop variable
  in a fresh child `Environment` per iteration so closures created across
  iterations capture their own value rather than the final one.
  `break`/`continue` intentionally left out (shipped separately, PR #19).
- **Standard library: string methods** — merged 2026-07-20T14:29:19Z via
  PR #18 (`feat/20260720-string-methods`). Added `upper(s)`, `lower(s)`,
  `trim(s)`, `split(s, sep)`, and `join(list, sep)` to `cinder/builtins.py`,
  arity/type-checked the same way as `_len`/`_str`. Bounced once: `_split`
  let Python's `ValueError: empty separator` (from `str.split("")`) escape
  as a raw traceback instead of a `CinderRuntimeError`; fixed by rejecting
  an empty separator explicitly before calling `.split()`, matching the
  `_int`/`_float` exception-conversion pattern.
- **`break` and `continue` for loops** — merged 2026-07-20T14:44:02Z via
  PR #19 (`feat/20260720-break-continue`). Added `BreakStmt`/`ContinueStmt`
  AST nodes, parser support restricted to loop bodies via a `_loop_depth`
  counter mirroring `_fn_depth`'s handling of `return` (reset across
  function boundaries so `break`/`continue` can't leak out of a nested
  function to an outer loop), and interpreter support via
  `_BreakSignal`/`_ContinueSignal` caught at each loop's own execution site.
- **Standard library: math builtins (`abs`, `min`, `max`, `round`)** — merged
  2026-07-20T14:55:19Z via PR #20 (`feat/20260720-math-builtins`). Added
  `abs(n)`, `min(...)`/`max(...)` (variadic, one or more numeric arguments),
  and `round(n)` (ties-to-even, delegating to Python's built-in `round`) to
  `cinder/builtins.py`. `min`/`max` reject zero arguments with a dedicated
  inline variadic check since `_require_arity` only handles fixed arity.
- **REPL: command history via `readline`** — merged 2026-07-21T~00:00Z via
  PR #21 (`feat/20260720-repl-readline`). Added `_try_enable_readline()` to
  `cinder/repl.py`, called once at `run_repl()` startup, guarded with
  `try`/`except ImportError` so the REPL still starts without `readline`
  (e.g. stock Windows Python). No persistent history-file save/load —
  in-session history only, per the task's "keep it small" instruction.
- **Negative indexing for lists and strings** — merged 2026-07-21T~13:16Z via
  PR #22 (`feat/20260720-negative-indexing`). Extended `_evaluate_index`/
  `_evaluate_index_assign` in `cinder/interpreter.py` to normalize a negative
  index to `len(obj) + index` before bounds-checking, Python-style, for list
  read/assign and string read; string index-assignment still raises for
  immutability regardless of sign, per PR #16.

- **Standard library: `contains` and `reverse`** — merged 2026-07-21T~13:30Z
  via PR #23 (`feat/20260720-contains-reverse`). Added
  `contains(collection, item)` (list `==` membership, map key check, string
  substring check, `CinderRuntimeError` for other types) and `reverse(list)`
  (returns a new list, non-mutating, matching `split`/`join`'s style rather
  than `push`/`pop`'s in-place style) to `cinder/builtins.py`. Clean first
  pass, no bounces (277 tests passing, up from 268).

- **Standard library: `sort`** — merged 2026-07-20T20:03:01Z via PR #24
  (`feat/20260720-sort-builtin`). Added `sort(list)` to `cinder/builtins.py`,
  returning a new ascending-sorted list (non-mutating, matching `reverse`'s
  style) for all-numeric or all-string lists; mixed-type lists, unsupported
  element types, and non-list arguments raise `CinderRuntimeError` with
  line/column. Clean first pass, no bounces (285 tests passing, up from
  277).

- **`for`-in loop over strings and maps** — merged 2026-07-21T~14:00Z via
  PR #25 (`feat/20260720-for-in-str-map`). Extended `_execute_for` in
  `cinder/interpreter.py` to accept a string (iterates character-by-
  character) and a map (iterates over keys, matching `contains`/`keys`
  convention) in addition to lists; any other type still raises
  `CinderRuntimeError` with line/column. Clean first pass, no bounces
  (289 tests passing, up from 285).

## Graveyard

(none yet)
