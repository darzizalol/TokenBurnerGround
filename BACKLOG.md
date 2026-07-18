# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test on a
`night/<YYYYMMDD>-<slug>` branch, open a PR. Do not skip ahead to a later
task while an earlier one is unclaimed/open.

---

## 1. Lexer: tokenize literals, identifiers, operators, comments

Build: `cinder/lexer.py` with a `Lexer` class (or `tokenize(source: str) ->
list[Token]` function) producing a full token stream for: integer and float
literals, double-quoted strings (with `\n`, `\t`, `\\`, `\"` escapes),
identifiers, keywords (`let`, `if`, `else`, `while`, `fn`, `return`, `true`,
`false`, `nil`, `and`, `or`, `not`), operators/punctuation (`+ - * / %  ==
!= < <= > >= = ( ) { } [ ] , ; .`), and `#`-to-end-of-line comments
(discarded, not emitted as tokens). Every `Token` carries `line` and
`column`. Flesh out `cinder/tokens.py`'s `TokenType` enum with every kind
above plus `EOF`. Unterminated strings and unrecognized characters raise a
`LexError` (add to `cinder/errors.py`) carrying line/column — do not just
raise a bare `Exception`.

Acceptance criteria:
- Unit tests cover: each literal kind, each keyword, each operator, comment
  stripping, and at least one multi-line source producing correct
  line/column on tokens after the first line.
- Unit tests cover both error cases (unterminated string, unknown
  character) and assert the raised `LexError` has correct line/column.
- `python3 -m unittest discover -s tests -v` passes in full (not just the
  new tests).

Likely files: `cinder/lexer.py`, `cinder/tokens.py`, `cinder/errors.py`,
`tests/test_lexer.py`.

---

## 2. Parser: expressions with correct precedence

Build: `cinder/ast_nodes.py` with dataclasses for expression nodes
(`Literal`, `Identifier`, `Unary`, `Binary`, `Logical`, `Grouping`, `Call` —
`Call` can be defined now even though functions aren't evaluable yet) and
`cinder/parser.py` with a recursive-descent/Pratt parser turning a token
list into an expression AST, handling standard precedence (unary `- not` >
`* / %` > `+ -` > comparisons > `and` > `or`) and parenthesized grouping.
Parse errors raise `ParseError` (in `cinder/errors.py`) with line/column and
a message naming what was expected vs. found.

Acceptance criteria:
- Unit tests assert the AST shape (or a stable string/repr of it) for
  representative expressions covering every precedence level, e.g.
  `1 + 2 * 3`, `(1 + 2) * 3`, `not true and false`, `-1 + 2`.
- Unit tests cover at least two malformed-input cases raising `ParseError`
  with correct line info.
- Full test suite still passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`, `cinder/errors.py`,
`tests/test_parser.py`.

---

## 3. Statement parsing + tree-walking evaluator for expressions and `let`

Build: statement-level AST nodes (`ExprStmt`, `LetStmt`, `Block`) and
parser support for `let x = <expr>;`, bare expression statements, and `{
... }` blocks. Build `cinder/interpreter.py` with an `Environment` class
(name -> value, with a parent pointer for lexical scoping) and an
`Interpreter` that evaluates expression ASTs (literals, arithmetic,
comparisons, string concatenation with `+`, logical `and`/`or` with
short-circuit, unary/grouping) plus `LetStmt` (declares in current scope)
and `Block` (opens a child scope). Wire `cinder/cli.py`'s `run` subcommand
to actually lex+parse+interpret a file end to end.

Acceptance criteria:
- `python3 -m cinder.cli run <file>` on a script containing `let x = 1 + 2;
  let y = x * 2;` runs without error (nothing to print yet — `print` is a
  later task, so tests should call the `Interpreter` API directly, not rely
  on stdout).
- Unit tests cover arithmetic/string/logical evaluation results, `let`
  declaration + lookup, block scoping (inner `let` shadows outer, outer
  unaffected after block exits), and referencing an undeclared name raises a
  runtime `CinderError` with line info.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `cinder/errors.py`, `cinder/cli.py`,
`tests/test_interpreter.py`.

---

## 4. Control flow: `if`/`else` and `while`

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

## 5. Functions: declarations, calls, closures, `return`

Build: `FnDecl` (named function statement) and `return` statement AST
nodes, parser support for `fn name(a, b) { ... }` and call expressions
`name(a, b)` (the `Call` node from task 2 becomes evaluable), and evaluator
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

## 6. Data structures: lists and maps

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

## 7. Standard library: builtins (`print`, `len`, `type`, conversions)

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

## 8. Error diagnostics polish

Build: unify `LexError`/`ParseError`/runtime `CinderError` under one base
class with consistent `.line`, `.column`, `.message` fields (adjust
whichever of tasks 2/3/4 didn't already do this fully), and make
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

## 9. Example programs

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

---

## Graveyard

(none yet)
