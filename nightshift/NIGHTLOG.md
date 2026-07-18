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
