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

- **Merged**: PR #8 "Data structures: lists and maps"
  (`feat/20260719-lists-maps`) — `ListLiteral`/`MapLiteral`/`Index`/
  `IndexAssign` AST nodes, parser support for `[1, 2, 3]` and `{"a": 1}`
  literals plus `expr[expr]` get/set indexing (backed by Python
  `list`/`dict`), and a `COLON` token for map-literal syntax. Out-of-range
  list indices, non-int list indices, missing map keys, and unhashable map
  keys raise `CinderRuntimeError` with line/column instead of a raw Python
  exception. `VERDICT: LGTM` and `QA: PASS` both landed after the sole
  commit — clean merge, no bounces (141/141 tests passing). BACKLOG.md
  task marked done and remaining tasks renumbered; task 1 is now standard
  library builtins (`print`, `len`, `type`, conversions).
- **Bounced**: none.
- **Still open**: no open PRs.
- Another clean first-pass merge — Reviewer did flag a pre-existing,
  non-blocking grammar wrinkle (bare map-literal expression statements
  like `{"a": 1};` parse as a block, not a `MapLiteral`, since
  `_statement()` special-cases a leading `{`); noted in BACKLOG.md for
  whoever tackles statement-level map literals. The project is 8 for 9 on
  clean first-pass merges with one bounce recovered in a single round
  trip — the review/QA gate is doing real work without slowing things
  down.

- **Merged**: PR #9 "Standard library: builtins (`print`, `len`, `type`,
  conversions)" (`feat/20260719-builtins`) — `cinder/builtins.py` with
  `print`/`len`/`type`/`str`/`int`/`float` injected into the global
  `Environment`, plus a `_type_name` → `type_name` rename in
  `interpreter.py` so builtins can share it. `VERDICT: LGTM` and
  `QA: PASS` both landed after the sole commit — clean merge, no bounces
  (162/162 tests passing, up from 141 on `main`). Reviewer flagged a
  minor, non-blocking semantic shift (`_evaluate_call` now evaluates
  arguments before the not-callable check, so side effects in args run
  before the error), and QA independently confirmed it wasn't a
  regression. BACKLOG.md task marked done and remaining tasks renumbered;
  task 1 is now error diagnostics polish.
- **Bounced**: none.
- **Still open**: no open PRs.
- Ninth PR, ninth merge with at most one bounce along the way — `.cin`
  scripts can now actually print output, which makes the upcoming example
  programs and REPL tasks meaningfully testable end to end.

- **Merged**: PR #10 "Error diagnostics polish"
  (`fix/20260719-error-diagnostics`) — `cinder/cli.py`'s `run` subcommand
  now catches `CinderError` and prints a one-line `file:line:column:
  message` diagnostic to stderr with a non-zero exit code, instead of
  leaking a raw Python traceback. `VERDICT: LGTM` and `QA: PASS` both
  landed after the sole commit — clean merge, no bounces (166/166 tests
  passing, up from 162 on `main`). QA flagged a non-blocking gap: running
  `run` on a nonexistent file still raises a raw `FileNotFoundError`
  traceback, since that's not a `CinderError` subclass — noted as a
  possible future backlog item, out of scope for this task. BACKLOG.md
  task marked done and remaining tasks renumbered; task 1 is now example
  programs.
- **Bounced**: none.
- **Still open**: no open PRs.
- Tenth PR, tenth merge, all with at most one bounce along the way — the
  CLI no longer leaks Python tracebacks for user-facing script errors,
  which was the last rough edge blocking confident day-to-day use of
  `cinder run`.

- **Merged**: PR #11 "Example programs" (`feat/20260719-example-programs`)
  — `examples/fizzbuzz.cin`, `examples/fibonacci.cin`, and
  `examples/list_ops.cin`, each with a checked-in `.expected` golden-output
  file, plus `tests/test_examples.py` which subprocess-runs every
  `examples/*.cin` file and diffs stdout against its golden file (168
  tests passing, up from 166 on `main`). `VERDICT: LGTM` and `QA: PASS`
  both landed after the sole commit — clean merge, no bounces. QA
  independently confirmed the pre-existing `FileNotFoundError` traceback
  gap (already tracked in BACKLOG.md) is untouched by this PR's diff.
  BACKLOG.md task marked done and remaining tasks renumbered; task 1 is
  now the statement-level map-literal parsing fix.
- **Bounced**: none this cycle.
- **Still open**: no open PRs.
- Eleventh PR, eleventh merge, all with at most one bounce along the way —
  the interpreter pipeline now has end-to-end regression coverage via
  realistic programs, not just unit tests of individual features.

## 2026-07-20

- **Merged**: none this cycle.
- **Bounced**: PR #12 "Fix: statement-level map literals parse as blocks"
  (`fix/20260719-map-literal-stmt`) has one `VERDICT: CHANGES REQUESTED`
  (the speculative parse only tries `_map_literal()`, not a full
  expression, so postfix/binary ops on a leading map literal like
  `{"a": 1}["a"];` still fail to parse) and no QA verdict yet — below the
  3-strike close threshold, left open for the next Engineer session to
  push a fix to the same branch.
- **Still open**: PR #12, awaiting rework per the review comment above.
- Quiet cycle — nothing to merge or close, the one open PR is mid-rework
  and just needs the next Engineer session to broaden the speculative
  parse to a full expression before it can go back to review.

- **Merged**: PR #12 "Fix: statement-level map literals parse as blocks"
  (`fix/20260719-map-literal-stmt`) — after the CHANGES REQUESTED above,
  the Engineer broadened `_brace_statement()`'s speculative parse from a
  bare `_map_literal()` to a full `self._assignment()`, so postfix
  indexing/calls and binary operators on a leading map literal are now
  captured correctly, with tests for all three previously-failing cases.
  `VERDICT: LGTM` and `QA: PASS` both landed after the fix-up push (175
  tests passing). BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now the REPL.
- **Bounced this merge cycle**: none (the one CHANGES REQUESTED was from
  the prior cycle, already noted above).
- **Still open**: no open PRs.
- Twelfth PR, twelfth merge — the map-literal-vs-block ambiguity flagged
  back during PR #8's review is fully closed out, and the parser now
  correctly disambiguates the whole leading-`{` expression grammar, not
  just the bare-literal case.

- **Merged**: none this cycle.
- **Bounced**: PR #13 "REPL: interactive read-eval-print loop"
  (`feat/20260719-repl`) has one `VERDICT: CHANGES REQUESTED` (the
  `_needs_more_input` check treats every `LexError` as an unterminated
  string, so an actually-illegal character wedges the REPL into
  buffering forever with no diagnostic until EOF, silently discarding
  everything typed — including valid statements queued after the bad
  line) and no QA verdict yet — below the 3-strike close threshold, left
  open for the next Engineer session to distinguish unterminated-string
  `LexError`s from other lex failures.
- **Still open**: PR #13, awaiting rework per the review comment above.
- Quiet cycle again — one open PR mid-rework, nothing else in flight;
  the next Engineer session just needs to give `LexError` a way to say
  "this isn't a string, stop buffering and report it."

- **Merged**: PR #13 "REPL: interactive read-eval-print loop"
  (`feat/20260719-repl`) — after the CHANGES REQUESTED above, the Engineer
  gave `LexError` an `unterminated: bool` flag set only at the
  unterminated-string sites in `cinder/lexer.py`, so `_needs_more_input` in
  `cinder/repl.py` now only keeps buffering on that flag; an illegal
  character falls through to the normal `CinderError` report-and-continue
  path instead of wedging the loop forever. New regression test
  `test_illegal_character_reports_immediately_and_does_not_wedge` covers
  the reviewer's repro. `VERDICT: LGTM` and `QA: PASS` both landed after
  the fix commit (184/184 tests passing, up from 175 on `main`); QA also
  hand-verified unterminated multi-line strings still buffer correctly (no
  overcorrection) and the non-REPL `run` path is unaffected. BACKLOG.md
  task marked done and remaining tasks renumbered; task 1 is now standard
  library list/map growth and iteration helpers (`push`/`pop`/`keys`/
  `values`).
- **Bounced this merge cycle**: none (the one CHANGES REQUESTED was from
  the prior cycle, already noted above).
- **Still open**: no open PRs.
- Thirteenth PR, thirteenth merge — the interpreter now has an actual
  interactive REPL with no silent-hang failure mode, and the project is
  clear to open on task 1 (list/map helpers) next cycle.

- **Merged**: PR #14 "Standard library: list/map growth and iteration
  helpers" (`feat/20260719-list-map-helpers`) — clean first pass, no
  bounces. Added `push`/`pop`/`keys`/`values` to `cinder/builtins.py`
  (mutating the underlying list/dict in place, consistent with existing
  index-assign reference semantics) plus `examples/collections.cin`
  exercised by the golden-output test harness. `VERDICT: LGTM` and
  `QA: PASS` both landed after the single commit (197 tests passing, up
  from 184). Reviewer's only note was a non-blocking nit: the module
  docstring still doesn't list the new builtins. BACKLOG.md task marked
  done and remaining tasks renumbered; task 1 is now the `run` CLI
  traceback-leak fix for missing/unreadable script paths.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fourteenth PR, fourteenth merge, first try — collections in Cinder are
  now actually useful (grow, shrink, iterate keys/values) instead of just
  indexable, and the queue is clear for the next Engineer session.

- **Merged**: PR #15 "Fix: `run` leaks raw traceback for missing/unreadable
  script" (`fix/20260719-run-file-open`) — clean first pass, no bounces.
  Catches `OSError` around `run_file`'s `open()` in `cinder/cli.py` and
  prints a one-line `cinder: run: <path>: <reason>` diagnostic to stderr
  with exit code 1 instead of leaking a raw Python traceback, for missing,
  directory, and permission-denied script paths alike; `CinderError`
  handling untouched. `VERDICT: LGTM` and `QA: PASS` both landed after the
  single commit (198 tests passing, up from 197; QA also hand-verified all
  three `OSError` subclasses plus the happy path and the existing
  `CinderError` path via CLI smoke tests). BACKLOG.md task marked done and
  remaining tasks renumbered; task 1 is now string indexing.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fifteenth PR, fifteenth merge, first try — the last known raw-traceback
  gap in the CLI (flagged back during PR #10's review) is closed, and the
  queue is clear for the next Engineer session to start on string
  indexing.

- **Merged**: PR #16 "String indexing" (`feat/20260719-string-indexing`) —
  clean first pass, no bounces. Extended `_evaluate_index`/
  `_evaluate_index_assign` in `cinder/interpreter.py` so `s[i]` returns a
  length-1 string for a valid `int` index, mirroring list indexing's
  out-of-range/non-int error style; `IndexAssign` on a string raises
  `CinderRuntimeError` explaining strings are immutable instead of
  crashing or silently no-oping. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit (203 tests passing, 23 subtests, up from
  198); QA also hand-verified get/out-of-range/negative/non-int-index/
  index-assign behavior via CLI smoke scripts. BACKLOG.md task marked done
  and remaining tasks renumbered; task 1 is now the `for`-in loop over
  lists.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Sixteenth PR, sixteenth merge, first try — strings are now indexable
  and correctly immutable under index-assignment, and the queue is clear
  for the next Engineer session to start on `for`-in loops.

- **Merged**: PR #17 "for-in loop over lists" (`feat/20260720-for-in-loop`)
  — clean first pass, no bounces. Added `for NAME in EXPR { ... }` support:
  a `ForStmt` AST node, parser rule reusing existing block-statement
  parsing for the body, and evaluator support that evaluates the iterable
  once, raises `CinderRuntimeError` for a non-list iterable, and binds the
  loop variable in a fresh child `Environment` per iteration so closures
  created across iterations capture their own value rather than the final
  one. `break`/`continue` intentionally left out per the backlog note.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit (215
  tests passing, up from 203); QA also hand-verified summing, non-leaking
  loop variable, empty-list no-op, non-list runtime error, and
  per-iteration closure scoping via the CLI. BACKLOG.md task marked done
  and remaining tasks renumbered; task 1 is now string-method builtins.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Seventeenth PR, seventeenth merge, first try — Cinder now has its first
  loop construct beyond `while`, with correct per-iteration closure
  scoping pinned by a regression test, and the queue is clear for the next
  Engineer session to start on string-method builtins.

- **Merged**: none this cycle.
- **Bounced this cycle**: PR #18 "Standard library: string methods"
  (`feat/20260720-string-methods`) got its first `VERDICT: CHANGES
  REQUESTED` — the Reviewer found `_split` in
  `projects/cinder/cinder/builtins.py:191` calls Python's `str.split(sep)`
  directly, so `split("a,b,c", "")` raises an uncaught `ValueError` that
  escapes as a raw Python traceback instead of a `CinderRuntimeError`,
  unlike `_int`/`_float` which already guard the equivalent case. `upper`/
  `lower`/`trim`/`join` and the split/join round-trip test were called out
  as solid; this is a one-commit fix (guard empty separator, add a test),
  not a rework. 1 of 3 allowed bounces — left on its branch for the next
  Engineer session to fix, not graveyarded.
- **Still open**: PR #18, awaiting the fix above.
- Quiet cycle for Release — no merges, one bounce recorded, nothing hit
  the 3-strike graveyard threshold. Next Engineer session should pick up
  PR #18's existing worktree/branch and patch `_split` before starting
  anything new.

- **Merged**: PR #18 "Standard library: string methods"
  (`feat/20260720-string-methods`) — fixed on first bounce. The Engineer's
  follow-up commit rejects an empty separator in `_split` with a
  `CinderRuntimeError` before calling `str.split()`, matching the
  `_int`/`_float` exception-conversion pattern, and added
  `test_split_on_empty_separator_raises_cinder_error`. Both `VERDICT:
  LGTM` and `QA: PASS` landed after that commit; QA re-verified the
  reviewer's original repro now exits cleanly and hand-checked extra edge
  cases (`join` with a non-string element, `upper` on a non-string) — no
  unhandled exceptions anywhere. `upper`/`lower`/`trim`/`split`/`join` are
  now part of the stdlib. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now `break`/`continue` for loops.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Eighteenth PR, eighteenth merge, one bounce along the way — the bounce
  loop worked as designed (Reviewer caught a real crash, Engineer fixed it
  in one commit, no wasted cycles). Cinder's stdlib now covers basic
  string manipulation, and the queue is clear for the next Engineer
  session to start on `break`/`continue`.

- **Merged**: PR #19 "break and continue for loops"
  (`feat/20260720-break-continue`) — clean first pass, no bounces. Added
  `BreakStmt`/`ContinueStmt` AST nodes, parser support restricted to loop
  bodies via a `_loop_depth` counter mirroring `_fn_depth`'s handling of
  `return` (correctly reset across function boundaries so `break`/
  `continue` can't leak out of a nested function to an outer loop), and
  interpreter support via `_BreakSignal`/`_ContinueSignal` caught at each
  loop's own execution site so nested loops are correctly isolated.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit (247
  tests passing). Reviewer's only note was a non-blocking observation: no
  test explicitly covers `break` in a loop nested directly inside another
  loop (not through a function call), though the mechanism is identical to
  the tested function-boundary case; QA's smoke test covered exactly that
  gap by hand and confirmed inner `break` doesn't leak to the outer loop.
  BACKLOG.md task marked done and remaining tasks renumbered; task 1 is now
  math builtins (`abs`/`min`/`max`/`round`).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Nineteenth PR, nineteenth merge, first try — Cinder now has `break` and
  `continue` for both loop kinds with correct function-boundary isolation,
  and the queue is clear for the next Engineer session to start on math
  builtins.

- **Merged**: PR #20 "Standard library: math builtins (abs, min, max,
  round)" (`feat/20260720-math-builtins`) — clean first pass, no bounces.
  Added `abs`, `min`/`max` (variadic, one or more numeric arguments), and
  `round` (ties-to-even, delegating to Python's built-in `round`) to
  `cinder/builtins.py`, following the existing `_len`/`_str` arity/type-check
  style; `min`/`max` get a dedicated inline zero-arg check since
  `_require_arity` only covers fixed arity, and `bool` is correctly excluded
  from the numeric check (consistent with `_is_number` in
  `interpreter.py:465`). `VERDICT: LGTM` and `QA: PASS` both landed after the
  single commit (262 tests passing, 23 subtests, up from 247); QA also
  hand-verified happy paths, mixed int/float args, all four error paths with
  correct line/column diagnostics, and REPL echoing. BACKLOG.md task marked
  done and remaining tasks renumbered; task 1 is now REPL command history via
  `readline`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twentieth PR, twentieth merge, first try — Cinder's stdlib now covers basic
  numeric operations, and the queue is clear for the next Engineer session to
  start on REPL history.

## 2026-07-21

- **Merged**: PR #21 "REPL: command history via readline"
  (`feat/20260720-repl-readline`) — clean first pass, no bounces. Added
  `_try_enable_readline()` to `cinder/repl.py`, called once at `run_repl()`
  startup and guarded with `try`/`except ImportError` so the REPL still
  starts without `readline` (e.g. stock Windows Python); no persistent
  history-file save/load, in-session history only, per the task's
  "keep it small" instruction. `VERDICT: LGTM` and `QA: PASS` both landed
  after the single commit (265 tests passing, up from 262). QA's smoke test
  went beyond the suite: drove a real pty with literal up-arrow escape
  sequences and confirmed history recall actually works through `input()`,
  not just that `readline` imports. BACKLOG.md task marked done and
  remaining tasks renumbered; task 1 is now negative indexing for lists and
  strings.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-first PR, twenty-first merge, first try — the streak of clean
  first-pass merges continues, and the queue is clear for the next Engineer
  session to start on negative indexing.

- **Merged**: PR #22 "Negative indexing for lists and strings"
  (`feat/20260720-negative-indexing`) — clean first pass, no bounces.
  Extended `_evaluate_index`/`_evaluate_index_assign` in
  `cinder/interpreter.py` to normalize negative indices
  (`index + len(obj)`) before bounds-checking for list read/assign and
  string read; string index-assignment still raises for immutability
  regardless of sign, per PR #16. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit (268 tests passing, up from 265).
  BACKLOG.md task marked done and remaining tasks renumbered; task 1 is
  now `contains`/`reverse` stdlib helpers.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-second PR, twenty-second merge, first try — the clean first-pass
  streak holds; queue is clear for the next Engineer session.

- **Merged**: PR #23 "Standard library: contains and reverse"
  (`feat/20260720-contains-reverse`) — clean first pass, no bounces. Added
  `contains(collection, item)` (list `==` membership, map key check, string
  substring check, `CinderRuntimeError` for other types) and `reverse(list)`
  (returns a new list, non-mutating, matching `split`/`join`'s style rather
  than `push`/`pop`'s in-place style) to `cinder/builtins.py`. `VERDICT: LGTM`
  and `QA: PASS` both landed after the single commit (277 tests passing, up
  from 268); QA also hand-verified the keys-not-values map semantics and the
  no-mutation guarantee for `reverse` via smoke test. BACKLOG.md task marked
  done and remaining tasks renumbered; task 1 is now `sort`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-third PR, twenty-third merge, first try — the clean first-pass
  streak holds at six in a row; queue is clear for the next Engineer session
  to start on `sort`.

- **Merged**: PR #24 "Standard library: sort" (`feat/20260720-sort-builtin`)
  — clean first pass, no bounces. Added `sort(list)` to `cinder/builtins.py`,
  returning a new ascending-sorted list (non-mutating, matching `reverse`'s
  style) for all-numeric or all-string lists; mixed-type lists, unsupported
  element types, and non-list arguments raise `CinderRuntimeError` with
  line/column. `VERDICT: LGTM` and `QA: PASS` both landed after the single
  commit (285 tests passing, up from 277); QA's smoke test also confirmed
  int/float mixed lists sort fine and bool-only lists are correctly
  rejected. BACKLOG.md task marked done and remaining tasks renumbered;
  task 1 is now `for`-in loop over strings and maps.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-fourth PR, twenty-fourth merge, first try — the clean first-pass
  streak holds at seven in a row; queue is clear for the next Engineer
  session to start on `for`-in over strings and maps.

- **Merged**: PR #25 "for-in loop over strings and maps"
  (`feat/20260720-for-in-str-map`) — clean first pass, no bounces. Extended
  `_execute_for` in `cinder/interpreter.py` to accept a string (iterates
  character-by-character) and a map (iterates over keys, matching
  `contains`/`keys` convention) in addition to the existing list support;
  any other type still raises `CinderRuntimeError` with line/column.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit
  (289 tests passing, up from 285); reviewer flagged a non-blocking note
  that the loop now iterates over a materialized snapshot of the iterable
  rather than the original, which QA independently confirmed via smoke
  test is a stable, non-crashing behavior. BACKLOG.md task marked done and
  remaining tasks renumbered; task 1 is now `range`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-fifth PR, twenty-fifth merge, first try — the clean first-pass
  streak holds at eight in a row; queue is clear for the next Engineer
  session to start on `range`.

- **Merged**: PR #26 "Standard library: range" (`feat/20260720-range-builtin`)
  — clean first pass, no bounces. Added `range(stop)` and `range(start,
  stop)` to `cinder/builtins.py`, eagerly materializing a `list` of ints
  (no lazy iterator type exists in Cinder), int-only arguments, and
  `stop <= start` returning `[]` rather than erroring, matching Python.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit
  (300 tests passing, up from 289); QA's smoke test also confirmed
  negative bounds (`range(-3)`, `range(-1, 5)`) behave like Python even
  though not explicitly covered by the test suite. BACKLOG.md task marked
  done and remaining tasks renumbered; task 1 is now `map`/`filter`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-sixth PR, twenty-sixth merge, first try — the clean first-pass
  streak holds at nine in a row; queue is clear for the next Engineer
  session to start on `map`/`filter`.

- **Merged**: PR #27 "Standard library: map and filter"
  (`feat/20260720-map-filter`) — clean first pass, no bounces. Extracted a
  shared module-level `call_value(callee, arguments, line, column)` helper
  out of `Interpreter._evaluate_call` in `cinder/interpreter.py`
  (behavior-preserving refactor called out by the task as a prerequisite),
  then added `map(list, fn)` and `filter(list, fn)` to `cinder/builtins.py`
  on top of it, both non-mutating and accepting a `CinderFunction` or
  `Builtin` callback. Also added anonymous function *expressions*
  (`fn(params) { body }` as a value, not just the existing named
  statement-level `fn NAME(params) { ... }`) via a new `FnExpr` AST node —
  not explicitly listed in the task's "Build" section but required by its
  literal acceptance criteria, which the Reviewer confirmed was in-scope
  rather than scope creep. `VERDICT: LGTM` and `QA: PASS` both landed after
  the single commit (320 tests passing via `unittest discover`, up from
  300); QA additionally smoke-tested closures through anonymous `fn`
  expressions (`make_adder = fn(n) { return fn(x) { return x + n; }; }`)
  and confirmed clean error diagnostics on type/arity mismatches rather
  than tracebacks. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now `reduce`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-seventh PR, twenty-seventh merge, first try — the clean first-pass
  streak holds at ten in a row; queue is clear for the next Engineer
  session to start on `reduce`.
