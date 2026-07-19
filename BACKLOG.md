# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test in an isolated
worktree on a `<type>/<YYYYMMDD>-<slug>` branch (`feat`/`fix`/`chore`/`docs`/
`test` — see CLAUDE.md's worktree procedure), open a PR. Do not skip ahead to
a later task while an earlier one is unclaimed/open.

---

## 1. Functions: declarations, calls, closures, `return`

Build: `FnDecl` (named function statement) and `return` statement AST
nodes, parser support for `fn name(a, b) { ... }` and call expressions
`name(a, b)` (the `Call` node from the parser task becomes evaluable), and evaluator
support: functions are first-class values that capture their defining
`Environment` (closures), calling pushes a new child scope with parameters
bound, `return` unwinds via a control-flow signal (e.g. a Python exception
internal to the interpreter, not exposed as a `CinderError`) up to the
nearest function call boundary. Recursion must work (a function can call
itself by name).

Acceptance criteria:
- Unit tests: recursive factorial and/or fibonacci by function call produce
  correct values; a closure test (a function returning another function
  that captures an outer variable, called after the outer function
  returns, still sees the captured value); calling with the wrong argument
  count raises a runtime `CinderError`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `cinder/errors.py`, `tests/test_interpreter.py`.

---

## 2. Data structures: lists and maps

Build: list literals `[1, 2, 3]` and map literals `{"a": 1, "b": 2}` as AST
nodes + parser support, index expressions `expr[expr]` for both get and set
(`list[0] = 5`, `map["a"] = 5`), and evaluator support backed by Python
`list`/`dict` under the hood. Out-of-range list index or missing map key
raises a runtime `CinderError` with line info, not a raw Python
`IndexError`/`KeyError` leaking through.

Acceptance criteria:
- Unit tests cover list/map literal construction, get/set indexing for
  both, nested structures (list of maps, etc.), and the two error cases
  (bad list index, missing map key) asserting a `CinderError` is raised
  (not a bare Python exception).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `cinder/errors.py`, `tests/test_interpreter.py`.

---

## 3. Standard library: builtins (`print`, `len`, `type`, conversions)

Build: `cinder/builtins.py` exposing builtin functions injected into the
global `Environment` at interpreter startup: `print(...)` (writes to
stdout, space-joined, trailing newline — this is what makes `.cin` scripts
finally produce visible output), `len(x)` (works on strings, lists, maps),
`type(x)` (returns a type name string), `str(x)`, `int(x)`, `float(x)`.
Wire real `.cin` example scripts using `print` so `cinder run` output
becomes observable end to end.

Acceptance criteria:
- Unit tests for each builtin covering normal and at least one error case
  (e.g. `len(42)` raises `CinderError`).
- An integration-style test that runs a small script through
  `cinder.cli run` (via `subprocess` or by capturing stdout) and asserts on
  printed output — this is the first test exercising the full
  lex→parse→interpret→builtin pipeline end to end.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `cinder/interpreter.py`,
`tests/test_builtins.py`.

---

## 4. Error diagnostics polish

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

## 5. Example programs

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

---

## Graveyard

(none yet)
