# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test in an isolated
worktree on a `<type>/<YYYYMMDD>-<slug>` branch (`feat`/`fix`/`chore`/`docs`/
`test` — see CLAUDE.md's worktree procedure), open a PR. Do not skip ahead to
a later task while an earlier one is unclaimed/open.

---

## 1. Error diagnostics polish

Build: unify `LexError`/`ParseError`/runtime `CinderError` under one base
class with consistent `.line`, `.column`, `.message` fields (adjust
whichever of the earlier tasks didn't already do this fully), and make
`cinder/cli.py`'s `run` subcommand catch `CinderError` and print a
human-readable one-line diagnostic (`file:line:column: message`) to stderr
with a non-zero exit code, instead of letting a Python traceback leak to
the user.

Acceptance criteria:
- Unit tests assert the exact stderr format for a lex error, a parse error,
  and a runtime error triggered via `cinder.cli run` (subprocess or
  captured stdout/stderr), each with correct line/column.
- Exit code is non-zero for all three error kinds, zero for a script that
  runs cleanly.
- Full test suite passes.

Likely files: `cinder/errors.py`, `cinder/cli.py`, `tests/test_errors.py`,
`tests/test_cli.py`.

---

## 2. Example programs

Build: `examples/` directory with 3-4 `.cin` programs exercising everything
built so far — at minimum `fizzbuzz.cin` (loop + if/else + modulo),
`fibonacci.cin` (recursive function), and `list_ops.cin` (list/map
manipulation + print). Add a golden-output test that runs each example
through `cinder.cli run` and asserts stdout matches a checked-in expected
output file (`examples/fizzbuzz.expected`, etc.), so regressions in any
earlier layer get caught by example programs too, not just unit tests.

Acceptance criteria:
- At least 3 example `.cin` programs, each with a matching `.expected`
  golden file, each covering a different combination of features.
- A test iterates the examples directory and asserts actual vs. expected
  output for each.
- Full test suite passes.

Likely files: `examples/*.cin`, `examples/*.expected`, `tests/test_examples.py`.

---

## 3. REPL: interactive read-eval-print loop

Build: `cinder/repl.py` implementing the actual REPL — reads lines from
stdin, accumulates input until a statement is complete (reuse the lexer's
brace/paren tracking or a simple heuristic: keep reading while braces are
unbalanced), lexes/parses/executes each complete statement against a
persistent `Environment` that survives across inputs (so a variable `let`-
bound on one line is visible on the next), and prints the value of bare
expression statements the way a REPL should (skip printing for statements
that produce no value, e.g. `let`). Catches any `CinderError` per statement
using the same formatting as the `run` subcommand (task 2) and continues the
loop instead of crashing it. Exits cleanly on EOF (Ctrl-D) or an `exit`
command. Wire `cinder/cli.py`'s `repl` subcommand to actually call it instead
of printing "not implemented yet".

Acceptance criteria:
- Unit/integration tests drive the REPL via piped stdin (subprocess or by
  calling the REPL's loop function directly with an injected input source)
  and assert on printed output: a `let` followed by referencing the variable
  on the next line, a bare expression echoing its value, a `CinderError`
  (e.g. undefined variable) printing a diagnostic and the loop continuing to
  accept further input afterward, and clean exit on EOF.
- `cinder/cli.py repl` no longer prints the "not implemented yet" placeholder.
- Full test suite passes.

Likely files: `cinder/repl.py`, `cinder/cli.py`, `tests/test_repl.py`.

---

## 4. Fix: statement-level map literals parse as blocks

Build: fix the grammar ambiguity flagged during review of PR #8. Because
`_statement()` special-cases any leading `{` as the start of a `Block`, a
bare map-literal expression statement like `{"a": 1};` currently parses as
a (broken/misinterpreted) block instead of a `MapLiteral` wrapped in an
`ExprStmt`. Give the parser enough lookahead (or a backtracking attempt) at
a leading `{` to distinguish "block of statements" from "map literal
expression": e.g. peek past the first `{`, and if the next tokens form
`expr COLON` before any statement-ending token, parse a map literal
expression statement instead of a block. Empty `{}` may stay a block (or be
special-cased to an empty map) — pick one and document it in `PROJECT.md`
if it's not already covered by the truthiness/grammar notes.

Acceptance criteria:
- `{"a": 1};` as a top-level or in-block statement parses as an `ExprStmt`
  wrapping a `MapLiteral`, not a `Block`.
- Existing block syntax (`{ let x = 1; print(x); }`) still parses as a
  `Block` — add a regression test pinning this alongside the new map-literal
  statement test.
- Full test suite passes, including the new cases.

Likely files: `cinder/parser.py`, `tests/test_parser.py`.

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

---

## Graveyard

(none yet)
