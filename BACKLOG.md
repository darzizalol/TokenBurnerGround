# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test in an isolated
worktree on a `<type>/<YYYYMMDD>-<slug>` branch (`feat`/`fix`/`chore`/`docs`/
`test` — see CLAUDE.md's worktree procedure), open a PR. Do not skip ahead to
a later task while an earlier one is unclaimed/open.

---

## 1. REPL: interactive read-eval-print loop [claimed 2026-07-19T19:30:39Z]

Build: `cinder/repl.py` implementing the actual REPL — reads lines from
stdin, accumulates input until a statement is complete (reuse the lexer's
brace/paren tracking or a simple heuristic: keep reading while braces are
unbalanced), lexes/parses/executes each complete statement against a
persistent `Environment` that survives across inputs (so a variable `let`-
bound on one line is visible on the next), and prints the value of bare
expression statements the way a REPL should (skip printing for statements
that produce no value, e.g. `let`). Catches any `CinderError` per statement
using the same `file:line:column: message` formatting the `run` subcommand
already uses (`cinder/cli.py`, merged in PR #10) and continues the loop
instead of crashing it. Exits cleanly on EOF (Ctrl-D) or an `exit` command.
Wire `cinder/cli.py`'s `repl` subcommand to actually call it instead of
printing "not implemented yet".

Acceptance criteria:
- Unit/integration tests drive the REPL via piped stdin (subprocess or by
  calling the REPL's loop function directly with an injected input source)
  and assert on printed output: a `let` followed by referencing the variable
  on the next line, a bare expression echoing its value, a `CinderError`
  (e.g. undefined variable) printing a diagnostic and the loop continuing to
  accept further input afterward, and clean exit on EOF.
- `cinder/cli.py repl` no longer prints the "not implemented yet" placeholder.
- Full test suite passes — note `tests/test_cli.py::test_repl_not_implemented_exits_zero`
  currently asserts the old placeholder text and must be updated (not deleted;
  replace it with an assertion appropriate to the new REPL behavior, e.g. that
  `repl` on empty/EOF stdin exits 0) or it will fail once the placeholder is
  removed.

Likely files: `cinder/repl.py`, `cinder/cli.py`, `tests/test_repl.py`,
`tests/test_cli.py`.

---

## 2. Standard library: list/map growth and iteration helpers

Build: `cinder/builtins.py` currently only supports list/map access via
`expr[expr]` get/set (from task "Data structures: lists and maps") — there
is no way for a Cinder script to grow a list, remove an entry, or iterate a
map's keys. Add builtins: `push(list, value)` (appends, returns the
mutated list), `pop(list)` (removes and returns the last element, raises
`CinderRuntimeError` on an empty list), `keys(map)` (returns a list of the
map's keys, insertion order), and `values(map)` (returns a list of the
map's values, same order). Each must arity/type-check its arguments the
same way `_len`/`_str` do and raise `CinderRuntimeError` with line/column on
misuse (e.g. `push` on a non-list, `pop` on an empty list, `keys`/`values`
on a non-map).

Acceptance criteria:
- Unit tests for each of the four builtins: happy path, wrong argument
  type, wrong arity, and (for `pop`) the empty-list error case.
- An example-worthy `.cin` snippet using at least `push` and `keys`
  together is exercised by a test (does not need its own file under
  `examples/` unless task 1 has already landed — if it has, add one there
  instead of duplicating coverage).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Fix: `run` leaks raw traceback for missing/unreadable script

Build: `cinder/cli.py`'s `run_file` opens the script path with a bare
`open(path, ...)`; when the path doesn't exist (or isn't readable), Python
raises `FileNotFoundError`/`OSError`, which isn't a `CinderError` subclass,
so `main()`'s `except CinderError` doesn't catch it and the CLI leaks a raw
Python traceback instead of a clean diagnostic. QA flagged this as a
non-blocking gap when reviewing PR #10 (error diagnostics polish). Catch
`OSError` around the file open in `run_file` (or in `main`, wherever fits
the existing structure) and print a one-line, non-traceback message to
stderr — e.g. `cinder: run: <path>: <reason>` — with a non-zero exit code,
consistent in spirit with how `CinderError` is already reported. Do not
change the exit code or message for the existing `CinderError` path.

Acceptance criteria:
- Running `cinder run <nonexistent-path>` prints a one-line diagnostic to
  stderr (no Python traceback) and exits non-zero.
- Running `cinder run` on a script that lexes/parses/executes fine still
  behaves exactly as before (exit 0, stdout unaffected).
- A `CinderError` raised during execution still produces the existing
  `file:line:column: message` diagnostic — this task must not touch that
  path's behavior, only add handling for the file-open failure.
- Test drives `main()` (or the CLI as a subprocess) with a nonexistent path
  and asserts no traceback leaks and the exit code is non-zero.
- Full test suite passes.

Likely files: `cinder/cli.py`, `tests/test_cli.py` (new, if it doesn't
already exist).

---

## 4. String indexing

Build: extend `_evaluate_index` in `cinder/interpreter.py` to support
indexing into strings: `s[i]` returns a length-1 string for a valid `int`
index, mirroring list indexing's error style for out-of-range or non-int
indices (`CinderRuntimeError` with line/column). Strings stay immutable —
`IndexAssign` on a string (e.g. `"hi"[0] = "y"`) must raise
`CinderRuntimeError` explaining strings can't be mutated, not crash or
silently no-op. `len()` already handles strings (merged in the builtins
task); no change needed there.

Acceptance criteria:
- `"hello"[0]` evaluates to `"h"`; `"hello"[4]` to `"o"`.
- Out-of-range or non-int index on a string raises `CinderRuntimeError`
  with line/column, in the same style as list-index errors.
- Assigning to a string index raises `CinderRuntimeError` instead of
  crashing or mutating anything.
- Unit tests cover all three cases above.
- Full test suite passes.

Likely files: `cinder/interpreter.py`, `tests/test_interpreter.py`.

---

## 5. `for`-in loop over lists

Build: add a `for item in expr { ... }` statement — a new `ForStmt` AST
node (`cinder/ast_nodes.py`), parser support (`cinder/parser.py`) for
`for NAME in EXPR BLOCK`, reusing existing block-statement parsing for the
body, and evaluator support (`cinder/interpreter.py`) that evaluates EXPR
once, raises `CinderRuntimeError` if the result isn't a list, then iterates
its elements binding NAME in a fresh child `Environment` per iteration (so
a closure created inside the loop body captures that iteration's value, not
the final one — consistent with how `fn` closures already work). Do not
implement `break`/`continue`; leave that as a future task if it's needed.

Acceptance criteria:
- `for x in [1, 2, 3] { print(x); }` prints `1`, `2`, `3` on separate
  lines.
- Looping over a non-list expression (e.g. `for x in 5 { }`) raises
  `CinderRuntimeError` with line/column.
- A function defined inside the loop body that captures the loop variable
  retains its own iteration's value, not the final one — add a regression
  test pinning this per-iteration scoping.
- Full test suite passes, including new parser/interpreter tests for
  `ForStmt`.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.

---

## 6. Standard library: string methods

Build: extend `cinder/builtins.py` with string-manipulation builtins:
`upper(s)`, `lower(s)`, `trim(s)` (strips leading/trailing whitespace),
`split(s, sep)` (returns a list of strings, splitting on the literal
separator — no regex), and `join(list, sep)` (concatenates a list of
strings with `sep` between elements, raising `CinderRuntimeError` if any
element isn't a string). Each must arity/type-check its arguments the same
way `_len`/`_str` do and raise `CinderRuntimeError` with line/column on
misuse (e.g. `upper` on a non-string, `join` on a non-list first argument
or a list containing a non-string element).

Acceptance criteria:
- Unit tests for each of the five builtins: happy path, wrong argument
  type, and wrong arity.
- `split`/`join` round-trip on a representative case (e.g.
  `join(split("a,b,c", ","), ",")` equals the original string).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 7. `break` and `continue` for loops

Build: add `break` and `continue` statement support for `while` and (once
task 5 lands) `for`-in loops. New `BreakStmt`/`ContinueStmt` AST nodes
(`cinder/ast_nodes.py`), parser support (`cinder/parser.py`) for the bare
`break;` / `continue;` keywords, restricted to loop bodies the same way
`return` is restricted to function bodies today — track loop-nesting depth
during parsing and raise `ParseError` (with line/column) if `break`/
`continue` appears outside a loop. Evaluator support (`cinder/interpreter.py`)
via internal control-flow signals following the existing `_ReturnSignal`
pattern: `break` unwinds to the nearest enclosing loop's execution and stops
it; `continue` unwinds to the nearest enclosing loop's execution and
proceeds to its next iteration (for `while`, re-checks the condition; for
`for`-in, advances to the next element).

Acceptance criteria:
- `while` loop with a `break` inside an `if` exits the loop immediately,
  not running remaining iterations.
- `while` loop with a `continue` inside an `if` skips the rest of that
  iteration's body but keeps looping.
- Same two behaviors for `for`-in loops (depends on task 5 having merged).
- `break`/`continue` used outside any loop raises `ParseError` with
  line/column, at parse time (not a runtime crash).
- `break`/`continue` inside a function nested inside a loop body still
  refers to that loop, not some caller's loop (regression test recommended
  since `return` already threads through nested calls via exceptions —
  `break`/`continue` must not accidentally unwind past a function call
  boundary it shouldn't).
- Full test suite passes, including new parser/interpreter tests.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.

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

---

## Graveyard

(none yet)
