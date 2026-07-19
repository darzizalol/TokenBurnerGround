# NIGHTLOG — one entry per night, written by the Release Manager

The morning paper: what shipped, what bounced, what's still open.

---

## 2026-07-18

- **Merged**: PR #1 "Project scaffolding" (`night/20260718-project-scaffolding`)
  — `cinder/` package skeleton (`__init__.py`, `tokens.py` with a
  `TokenType.EOF` stub, `cli.py` argparse entrypoint with `run`/`repl`
  subcommands) plus a passing `tests/` harness. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS`, both after the sole commit — clean
  merge, no bounces. BACKLOG.md task 1 marked done and remaining tasks
  renumbered; task 1 is now the lexer.
- **Bounced**: none.
- **Still open**: no open PRs.
- First night of Cinder is off to a clean start — scaffolding landed on the
  first pass with no review/QA friction, so the lexer task is unblocked for
  the next Engineer session.

- **Merged**: PR #2 "Lexer: tokenize literals, identifiers, operators,
  comments" (`night/20260718-lexer`) — `cinder/lexer.py`, a fleshed-out
  `TokenType` enum in `cinder/tokens.py`, and `LexError` in
  `cinder/errors.py`, with 19/19 tests passing. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS`, both after the sole commit — clean
  merge, no bounces. BACKLOG.md task 1 marked done and remaining tasks
  renumbered; task 1 is now the parser.
- **Bounced**: none.
- **Still open**: no open PRs.
- Second PR in a row landed clean on the first pass — the night shift is on
  a roll, two-for-two with no review/QA friction so far.

- **Merged**: PR #3 "Parser: expressions with correct precedence"
  (`night/20260718-parser`) — `cinder/ast_nodes.py`, `cinder/parser.py` (a
  recursive-descent parser with the full precedence chain and
  parenthesized grouping/calls), and `ParseError` in `cinder/errors.py`,
  with 34/34 tests passing. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS`, both after the sole commit — clean merge, no bounces.
  BACKLOG.md task 1 marked done and remaining tasks renumbered; task 1 is
  now the tree-walking evaluator for expressions.
- **Bounced**: none.
- **Still open**: no open PRs.
- Three for three now — every PR tonight has landed clean on the first
  pass, no review/QA friction at all so far.

- **Merged**: PR #4 "Tree-walking evaluator for expressions"
  (`night/20260718-evaluator-expressions`) — `cinder/interpreter.py` with
  `Environment` (lexical scoping via parent pointer) and
  `Interpreter.evaluate()` covering the full expression AST (arithmetic,
  string concat, comparisons, short-circuit `and`/`or`, unary, grouping,
  identifier lookup), plus `CinderRuntimeError` additions in
  `cinder/errors.py`, with 64 tests passing. Reviewer gave `VERDICT: LGTM`,
  QA gave `QA: PASS`, both after the sole commit — clean merge, no bounces.
  BACKLOG.md task 1 marked done and remaining tasks renumbered; task 1 is
  now statements (`let`, blocks, CLI wiring).
- **Bounced**: none.
- **Still open**: no open PRs.
- Four for four tonight — every PR has landed clean on the first pass, no
  review/QA friction at all so far.

## 2026-07-19

- **Merged**: PR #5 "Statements: let, blocks, and end-to-end CLI wiring"
  (`night/20260718-statements`) — `ExprStmt`/`LetStmt`/`Block` AST nodes,
  parser support for `let` and `{ ... }` blocks plus `parse_program`, and
  `Interpreter.execute(stmt, env)`; wired `cinder/cli.py`'s `run`
  subcommand to lex→parse→execute a `.cin` file end to end, 81 tests
  passing. This branch started as unreviewed WIP rescued after a prior
  session was killed mid-work by the hard stop; this cycle's Engineer
  rebased it onto current `main`, and Reviewer/QA both signed off on the
  rebased result (`VERDICT: LGTM`, `QA: PASS`, both after the sole commit)
  — clean merge, no bounces. BACKLOG.md task 1 marked done and remaining
  tasks renumbered; task 1 is now control flow (`if`/`else`, `while`).
- **Bounced**: none.
- **Still open**: no open PRs.
- Five for five across the two nights so far — the rescued WIP from the
  hard-stop interruption made it through review and QA cleanly on the
  first try, no repeat of the interruption.

- **Merged**: PR #6 "Control flow: if/else and while"
  (`feat/20260719-control-flow`) — `IfStmt`/`WhileStmt` AST nodes, parser
  and evaluator support, and a minimal assignment expression
  (`name = expr`) with `Environment.assign` walking the scope chain to
  mutate `let`-bound variables; truthiness rule (`nil`/`false` falsy,
  everything else including `0`/`""` truthy) pinned in `PROJECT.md`, 96
  tests passing. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS`, both
  after the sole commit — clean merge, no bounces. BACKLOG.md task 1
  marked done and remaining tasks renumbered; task 1 is now functions
  (declarations, calls, closures, `return`).
- **Bounced**: none.
- **Still open**: no open PRs.
- Six for six across the two nights now — every PR so far has landed clean
  on first review/QA pass, no bounces at all yet this project.

- **Merged**: none this cycle.
- **Bounced**: PR #7 "Functions: declarations, calls, closures, return"
  (`feat/20260719-functions`) got `VERDICT: CHANGES REQUESTED` (1 of 3) —
  Reviewer found `return` outside a function crashes with a raw internal
  `_ReturnSignal` Python exception instead of a clean `CinderRuntimeError`
  (uncaught in `Interpreter.execute`, no handler in `cinder/cli.py`); no
  QA comment posted yet either. Left on its branch for the next Engineer
  session to fix.
- **Still open**: PR #7, awaiting a fix push.
- First bounce of the project — the streak of clean first-pass merges ends
  at six, but the review process is working as designed (caught a real gap
  in error-diagnostic coverage before it reached `main`).

- **Merged**: PR #7 "Functions: declarations, calls, closures, return"
  (`feat/20260719-functions`) — `FnDecl`/`ReturnStmt` AST nodes, parser
  support for `fn name(a, b) { ... }` and call expressions, and evaluator
  support for first-class functions capturing their defining `Environment`
  (closures), arity-checked calls, recursion, and `return` unwinding via an
  internal control-flow signal. Fix commit (584f6cf) resolved the earlier
  bounce by tracking function-nesting depth in the parser and raising
  `ParseError` for `return` outside a function, with new tests for
  top-level `return`, `return` inside a top-level `if`/`while`, and depth
  resetting after a fn body closes. Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` on the re-review, both after the fix commit — 114/114
  tests passing. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now data structures (lists and maps).
- **Bounced**: none this cycle (PR #7's single bounce was from the prior
  cycle, fixed and merged this cycle).
- **Still open**: no open PRs.
- Recovered cleanly from the project's first bounce — one round trip
  through Reviewer feedback and the fix landed on the second pass, exactly
  as the process is meant to work.
