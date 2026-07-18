# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test on a
`night/<YYYYMMDD>-<slug>` branch, open a PR. Do not skip ahead to a later
task while an earlier one is unclaimed/open.

---

## 1. Tree-walking evaluator for expressions [claimed 2026-07-18T14:33:33Z]

Build: `cinder/interpreter.py` with an `Environment` class (name -> value,
with a parent pointer for lexical scoping, though only the global scope is
exercised yet) and an `Interpreter` with an `evaluate(expr, env)` entry
point that walks the expression AST from task 1: literal values, arithmetic
(`+ - * / %`, with `+` also doing string concatenation), comparisons,
logical `and`/`or` with short-circuit evaluation, unary (`- not`), and
grouping. `Identifier` evaluation looks up the name in `Environment` and
raises a runtime `CinderError` (with line info) if undeclared — there is no
`let` yet, so tests populate the `Environment` directly to exercise lookup.
No statement parsing, no CLI wiring in this task — evaluation is only
exercised by calling `Interpreter.evaluate()` on ASTs produced directly by
`cinder/parser.py`. `Call` nodes are explicitly out of scope here — there
are no functions to call yet (that's task 4) — do not implement `Call`
evaluation; leave it raising `NotImplementedError` or unhandled, tests
should not exercise it.

Acceptance criteria:
- Unit tests cover arithmetic results (including operator precedence
  carried over correctly from the AST), string concatenation, comparison
  results, logical short-circuit behavior (e.g. an `or` whose right side
  would error if evaluated), and unary/grouping.
- A test covers identifier lookup against a pre-populated `Environment` and
  a test covers lookup of an undeclared name raising `CinderError` with
  line info.
- Full test suite passes.

Likely files: `cinder/interpreter.py`, `cinder/errors.py`,
`tests/test_interpreter.py`.

---

## 2. Statements: `let`, blocks, and end-to-end CLI wiring

Build: statement-level AST nodes (`ExprStmt`, `LetStmt`, `Block`) in
`cinder/ast_nodes.py` and parser support for `let x = <expr>;`, bare
expression statements, and `{ ... }` blocks, plus a `parse_program` (or
similar) entry point turning a full token list into a list of statements.
Extend the task-1 `Interpreter` with an `execute(stmt, env)` that handles
`LetStmt` (declares in the current scope's `Environment`), `ExprStmt`
(evaluates and discards), and `Block` (opens a child `Environment` whose
parent is the enclosing scope, so inner `let` shadows outer without
mutating it). Wire `cinder/cli.py`'s `run` subcommand to actually
lex -> parse -> execute a `.cin` file end to end.

Acceptance criteria:
- `python3 -m cinder.cli run <file>` on a script containing `let x = 1 + 2;
  let y = x * 2;` runs without error (nothing to print yet — `print` is a
  later task, so tests should call the `Interpreter`/`Environment` API
  directly, not rely on stdout).
- Unit tests cover `let` declaration + lookup, block scoping (inner `let`
  shadows outer, outer unaffected after block exits), and a CLI-level test
  that runs a `let`-only script through `cinder.cli run` and exits zero.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `cinder/cli.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`, `tests/test_cli.py`.

---

## 3. Control flow: `if`/`else` and `while`

Build: `IfStmt` and `WhileStmt` AST nodes, parser support, and evaluator
support, using the truthiness rule: `false` and `nil` are falsy, everything
else (including `0` and `""`) is truthy — state this explicitly in
`PROJECT.md`'s architecture notes if not already documented, since later
tasks depend on it being fixed.

Acceptance criteria:
- Unit tests cover `if` with and without `else`, nested `if`, and a `while`
  loop that mutates a `let`-bound counter (e.g. sum 1..10 via a loop,
  assert the final value through the `Interpreter`/`Environment` API).
- A test explicitly pins the truthiness rule (`nil`/`false` falsy, `0`/`""`
  truthy).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_interpreter.py`, `PROJECT.md`.

---

## 4. Functions: declarations, calls, closures, `return`

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

## 5. Data structures: lists and maps

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

## 6. Standard library: builtins (`print`, `len`, `type`, conversions)

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

## 7. Error diagnostics polish

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

## 8. Example programs

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

---

## Graveyard

(none yet)
