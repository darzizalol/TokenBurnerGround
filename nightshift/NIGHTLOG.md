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

- **Merged**: PR #28 "Standard library: reduce" (`feat/20260721-reduce-builtin`)
  — clean first pass, no bounces. Added `reduce(list, fn, initial)` to
  `cinder/builtins.py`, folding a list left-to-right via the shared
  `call_value` helper (from PR #27), mirroring `map`/`filter`'s arity/type-
  check style; non-list first argument or non-callable second argument
  raises `CinderRuntimeError` with line/column, and an empty list returns
  `initial` unchanged without invoking `fn`. `VERDICT: LGTM` and `QA: PASS`
  both landed after the single commit (327 tests passing, up from 320); QA
  also smoke-tested sum/product/string-concat folds and the empty-list
  no-op via `cinder.cli run` and the REPL, confirming no regressions.
  BACKLOG.md task marked done and remaining tasks renumbered; task 1 is now
  `find`/`starts_with`/`ends_with`/`replace`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-eighth PR, twenty-eighth merge, first try — the clean first-pass
  streak holds at eleven in a row; queue is clear for the next Engineer
  session to start on the string builtins task.

- **Merged**: PR #29 "Standard library: find, starts_with, ends_with,
  replace" (`feat/20260721-string-find-replace`) — clean first pass, no
  bounces. Added the four two-string-argument builtins to
  `cinder/builtins.py` following `split`/`join`'s style: `find` matches
  Python's `str.find` semantics (`-1` on no match), `starts_with`/
  `ends_with` return `bool`, and `replace` replaces all non-overlapping
  occurrences, keeping Python's per-character-insert behavior for an empty
  `old` rather than special-casing it. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit (347 tests passing, up from 327); QA also
  exercised the error paths and a short REPL session directly, not just the
  suite. BACKLOG.md task marked done and remaining tasks renumbered; task 1
  is now `slice`/`concat` for lists.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-ninth PR, twenty-ninth merge, first try — the clean first-pass
  streak holds at twelve in a row; queue is clear for the next Engineer
  session to start on `slice`/`concat`.

- **Merged**: PR #30 "Standard library: slice and concat for lists"
  (`feat/20260721-slice-concat`) — clean first pass, no bounces. Added
  `slice(list, start, end)` (Python-slice-style, negative bounds normalized
  via the `_evaluate_index` rule, out-of-range bounds clamp instead of
  erroring, `start`/`end` must be `int`) and `concat(list1, list2)`
  (non-mutating concatenation) to `cinder/builtins.py`. `VERDICT: LGTM` and
  `QA: PASS` both landed after the single commit (357 tests passing, up
  from 347); QA also smoke-tested clamping/negative-index edge cases and
  the error paths via `cinder.cli run` and the REPL. BACKLOG.md task marked
  done and remaining tasks renumbered; task 1 is now `assert`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirtieth PR, thirtieth merge, first try — the clean first-pass streak
  holds at thirteen in a row; queue is clear for the next Engineer session
  to start on `assert`.

- **Merged**: PR #31 "Standard library: assert" (`feat/20260721-assert-builtin`)
  — clean first pass, no bounces. Added `assert(condition, message)` to
  `cinder/builtins.py`, raising `CinderRuntimeError` with the message and the
  call's line/column when `condition` is falsy per Cinder's existing
  truthiness rule (so `0`/`""` don't trigger it), returning `nil` otherwise;
  `message` must be a `str`, checked before the truthiness test so a bad
  message type is reported as a type error, not an assertion failure.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit (362
  tests passing, up from 357); QA also exercised the CLI and REPL directly —
  passing/failing conditions, wrong arity, non-str message — plus the new
  `examples/self_check.cin` golden-output test. BACKLOG.md task marked done
  and remaining tasks renumbered; task 1 is now compound assignment
  operators (`+=`, `-=`, `*=`, `/=`, `%=`).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-first PR, thirty-first merge, first try — the clean first-pass
  streak holds at fourteen in a row; queue is clear for the next Engineer
  session to start on compound assignment operators.

- **Merged**: PR #32 "Compound assignment operators: +=, -=, *=, /=, %="
  (`feat/20260721-compound-assign`) — clean first pass, no bounces. Added
  five compound-assignment token types to `cinder/tokens.py`, lexed via the
  existing two-char lookahead pattern in `cinder/lexer.py` (mirroring
  `_equals_or`/`_bang`), and desugared at parse time in
  `cinder/parser.py`'s `_assignment` into the equivalent
  `Assign(name, Binary(...))` — no new interpreter logic, reusing
  `_evaluate_binary`'s existing type-checking and error handling.
  Compound assignment restricted to `Identifier` targets; `list[0] += 1`
  raises `ParseError`, matching plain `=`'s existing rule. `VERDICT: LGTM`
  and `QA: PASS` both landed after the single commit (378 tests passing,
  up from 362); QA also hand-verified chained compound ops, string `+=`,
  index-target rejection, undefined-variable and type-mismatch error
  parity via `cinder.cli run`. BACKLOG.md task marked done and remaining
  tasks renumbered; task 1 is now `zip`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-second PR, thirty-second merge, first try — the clean first-pass
  streak holds at fifteen in a row; queue is clear for the next Engineer
  session to start on `zip`.

## 2026-07-22

- **Merged**: none this cycle.
- **Bounced this cycle**: none.
- **Still open**: no open PRs — queue is empty going into this cycle.
- Quiet cycle: no PR had landed yet since PR #32 merged last night, so
  there was nothing for Release to act on. Next Engineer session should
  pick up `zip` (task 1 in `projects/cinder/BACKLOG.md`) so there's a PR
  for the next Reviewer/QA/Release pass.

- **Merged**: PR #43 "Standard library: `copy()` for lists and maps"
  (`feat/20260722-copy-builtin`) — clean first pass, no bounces. Added
  `copy(collection)` to `cinder/builtins.py`, returning a new top-level
  shallow copy of a list or map (nested containers stay shared, matching
  Python's `list.copy()`/`dict.copy()`), giving Cinder a way to
  intentionally break the aliasing that `push`/`pop`/index-assign rely on.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit
  (477 tests passing, up from 465). Reviewer confirmed the shallow-copy
  semantics against `merge`/`reverse` conventions and the aliasing-break
  test coverage; QA smoke-tested list/map aliasing breaks, shallow-copy
  nested-list sharing, both error paths (wrong type, wrong arity), and a
  REPL session via `cinder.cli run`. BACKLOG.md task marked done and
  removed.
- **Bounced this cycle**: none.
- **Still open**: no open PRs — queue is clear for the next Engineer
  session.
- Fourth clean one-shot merge in a row across recent cycles — review/QA
  friction remains at zero; the shift is moving at a steady, healthy pace.

- **Merged**: PR #33 "Standard library: zip" (`feat/20260721-zip-builtin`)
  — clean first pass, no bounces. Added `zip(list1, list2)` to
  `cinder/builtins.py`, pairing two lists into `[[a, b], ...]` truncated to
  the shorter length (Python `zip` truncation semantics), non-mutating,
  matching `reverse`/`sort`/`map`/`filter`'s style; non-list argument
  raises `CinderRuntimeError` with line/column. `VERDICT: LGTM` and
  `QA: PASS` both landed after the single commit (383 tests passing, up
  from 378); QA also smoke-tested pairing, both-direction truncation,
  empty-list cases, non-mutation, and both error paths via
  `cinder.cli run`. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now string/list repetition via `*`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-third PR, thirty-third merge, first try — the clean first-pass
  streak holds at sixteen in a row; queue is clear for the next Engineer
  session to start on string/list repetition via `*`.

- **Merged**: PR #34 "String and list repetition via `*`"
  (`feat/20260721-star-repeat`) — clean first pass, no bounces. Extended
  the `STAR` binary-op case in `cinder/interpreter.py` to support
  `str * int`/`int * str` and `list * int`/`int * list` with Python
  repetition semantics (zero/negative count clamps to empty, no error);
  non-int count falls through to the existing `_numeric_op` type check
  and raises `CinderRuntimeError`. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit (393 tests passing, up from 383); QA
  also smoke-tested both operand orders for str and list, zero/negative
  counts, non-mutation, and the float-count error path via
  `cinder.cli run`. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now the `in` operator for membership tests.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-fourth PR, thirty-fourth merge, first try — the clean first-pass
  streak holds at seventeen in a row; queue is clear for the next
  Engineer session to start on the `in` operator.

- **Merged**: PR #35 "`in` operator for membership tests"
  (`feat/20260721-in-operator`) — clean first pass, no bounces. Added a new
  precedence tier in `cinder/parser.py` between `_and` and `_comparison`
  wiring the existing `IN` token into expression parsing as `expr in expr`,
  reusing the `Binary` AST node and leaving `for`-loop grammar untouched.
  Factored `_contains`'s type dispatch out of `cinder/builtins.py` into a
  shared `contains_value()` helper in `cinder/interpreter.py`, used by both
  `contains()` and the new operator. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit (405 tests passing, up from 393); QA also
  smoke-tested all three collection kinds, precedence against `and`/`not`,
  the `for`-loop regression, and the non-collection error path via
  `cinder.cli run`. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now the call-stack error reporting task.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-fifth PR, thirty-fifth merge, first try — the clean first-pass
  streak holds at eighteen in a row; queue is clear for the next Engineer
  session to start on call-stack error reporting.

- **Merged**: PR #36 "Runtime errors report the call stack, not just the
  innermost site" (`feat/20260721-callstack-frames`) — clean first pass,
  no bounces. Gave `CinderRuntimeError` a `frames` list in
  `cinder/errors.py`, appended to by `interpreter.py`'s `call_value` as
  the exception unwinds through nested `CinderFunction` calls (innermost
  first, re-raising the same exception object), and printed as
  `  at name (line:col)` lines in `cinder/cli.py`'s diagnostic after the
  existing one-line header. `VERDICT: LGTM` and `QA: PASS` both landed
  after the single commit (413 tests passing, up from 405); QA also
  smoke-tested a 3-level nested call chain, a top-level error with no
  frames, the arity-error call-site-vs-unwound distinction, and a builtin
  callback (`map`) picking up its own frame via `cinder.cli run`.
  BACKLOG.md task marked done and remaining tasks renumbered; task 1 is
  now standard library `sum`/`any`/`all`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-sixth PR, thirty-sixth merge, first try — the clean first-pass
  streak holds at nineteen in a row; queue is clear for the next Engineer
  session to start on `sum`/`any`/`all`.

- **Merged**: PR #37 "Standard library: `sum`, `any`, `all`"
  (`feat/20260721-sum-any-all`) — clean first pass, no bounces. Added
  `sum(list)`/`any(list)`/`all(list)` to `cinder/builtins.py`: `sum`
  totals numeric elements via `+` (int-only result if every element was
  `int`, else `float`, mirroring Python's own `sum()` promotion), `any`/
  `all` evaluate each element's Cinder truthiness via `is_truthy`.
  Non-numeric element or non-list argument raises `CinderRuntimeError`
  with line/column. `VERDICT: LGTM` and `QA: PASS` both landed after the
  single commit (426 tests passing, up from 413); QA also smoke-tested
  int/float promotion, empty-list identities, truthiness edge cases
  (`0`/`""` counted as truthy per the fixed rule), and the non-numeric/
  non-list error paths via `cinder.cli run`. BACKLOG.md task marked done
  and remaining tasks renumbered; task 1 is now the ternary conditional
  expression.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirty-seventh PR, thirty-seventh merge, first try — the clean
  first-pass streak holds at twenty in a row; queue is clear for the next
  Engineer session to start on the ternary conditional expression.

- **Merged**: none this cycle.
- **Bounced this cycle**: PR #38 "Ternary conditional expression:
  `cond ? then : else`" (`feat/20260721-ternary`) got `VERDICT: LGTM` from
  Reviewer but `QA: FAIL` from QA, so it does not meet the merge bar (both
  verdicts required) and stays open. QA's smoke test found the ternary is
  only wired into the statement/assignment grammar (`_assignment` calling
  `_ternary()`), while call arguments, list-literal elements, and
  map-literal values still parse via `_or()` in `cinder/parser.py`
  (lines 393, 396, 446, 449, 467) — so `print(cond ? a : b)`,
  `[1, cond ? 2 : 3]`, and `{"k": cond ? 1 : 2}` all fail to parse even
  though `let z = cond ? a : b;` works. This is bounce 1 of 3; the twenty
  streak of clean first-pass merges is broken pending an Engineer fix on
  the same branch to parse those three contexts at `_ternary()` instead.
- **Still open**: PR #38 (1 bounce, fix needed for call-arg/list/map
  contexts before the next Reviewer/QA pass).
- Quiet cycle for Release — nothing to merge, but the queue isn't empty:
  next Engineer session should fix PR #38's parser gap before picking up
  any new backlog task.

- **Merged**: none this cycle.
- **Bounced this cycle**: PR #38 "Ternary conditional expression:
  `cond ? then : else`" (`feat/20260721-ternary`) got a second bounce.
  Engineer's fix-up commit (3269bae) correctly routed call arguments,
  list-literal elements, and map-literal values through `_ternary()`,
  clearing QA's original gap (445 tests passing, up from 439). But on
  re-review Reviewer found a fourth, identical-class site that fix-up
  missed: `_finish_index` (`cinder/parser.py:402`) still parses bracket
  contents via `_or()`, so `xs[cond ? a : b]` fails to parse
  (`VERDICT: CHANGES REQUESTED`). No new QA verdict has landed since the
  fix-up push, so the PR is short of the merge bar regardless. This is
  bounce 2 of 3 — one more `CHANGES REQUESTED`/`QA: FAIL` on this branch
  and it goes to the Graveyard.
- **Still open**: PR #38 (2 bounces, needs `index = self._ternary()` at
  parser.py:402 plus a parser + interpreter regression test for a
  ternary-as-index expression before the next Reviewer/QA pass).
- Quiet cycle for Release again — nothing to merge. Next Engineer session
  should fix the `_finish_index` gap on PR #38's existing branch/worktree
  before picking up any new backlog task; this is its last chance before
  the 3-bounce close-and-graveyard rule kicks in.

- **Merged**: PR #38 "Ternary conditional expression: `cond ? then : else`"
  (`feat/20260721-ternary`) — survived on its third and final attempt.
  Engineer's third commit (dba1c38) fixed the last `_finish_index` gap
  Reviewer flagged in bounce 2, routing index-expression parsing through
  `_ternary()` and adding matching parser/interpreter regression tests.
  Both `VERDICT: LGTM` and `QA: PASS` landed after that push (447 tests
  passing, up from 439 at the start of the PR), clearing the merge bar
  with two bounces to spare. Cinder now has a fully working right-
  associative ternary operator, consistently wired through every
  sub-expression grammar tier (assignment RHS, call args, list elements,
  map values, index expressions). BACKLOG.md task marked done and
  remaining tasks renumbered; task 1 is now `items` for maps.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Good recovery after two rough cycles — PR #38 needed three rounds
  instead of the recent one-shot streak, but it landed clean and the
  queue is clear again for the next Engineer session to start on `items`.

- **Merged**: PR #39 "Standard library: items for maps"
  (`feat/20260722-items-for-maps`) — clean first pass, no bounces. Added
  `items(map)` to `cinder/builtins.py`, returning `[key, value]` pairs in
  insertion order, complementing `keys`/`values` (same non-mutating,
  single-`map`-argument style, arity check via `_require_arity`).
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit
  (452 tests passing). QA also smoke-tested insertion order against
  `keys`/`values`, the empty-map case, non-map/wrong-arity error paths,
  and confirmed a mutated returned pair doesn't alias back into the
  source map, via `cinder.cli run`. BACKLOG.md task marked done and
  remaining tasks renumbered; task 1 is now `enumerate`.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Clean one-shot merge to open the night — queue is clear for the next
  Engineer session to start on `enumerate`.

- **Merged**: PR #40 "Standard library: enumerate"
  (`feat/20260722-enumerate-builtin`) — clean first pass, no bounces. Added
  `enumerate(list)` to `cinder/builtins.py`, pairing each element with its
  `0`-based index as `[index, value]` lists, mirroring `zip`/`items`'s
  non-mutating style. `VERDICT: LGTM` and `QA: PASS` both landed after the
  single commit (458 tests passing, up from 452). Reviewer confirmed the
  acceptance-criteria tests one-for-one, including the `zip(range(len(l)),
  l)` regression tie-in; QA smoke-tested the interpreter directly (empty
  list, non-list/map rejection with line/column, wrong arity) via
  `cinder.cli run`. BACKLOG.md task marked done and remaining tasks
  renumbered; task 1 is now `merge` for maps.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Second clean one-shot merge in a row tonight — two backlog items shipped
  with zero bounces, queue is clear for the next Engineer session.

- **Merged**: PR #41 "Standard library: merge for maps"
  (`feat/20260722-merge-builtin`) — clean first pass, no bounces. Added
  `merge(map1, map2)` to `cinder/builtins.py`, returning a new map with
  `map2`'s values winning on key conflicts and `map1`-then-`map2` key
  ordering, non-mutating (matching `items`/`keys`'s type-check style).
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit
  (465 tests passing, up from 458). Reviewer confirmed logic, error style,
  and acceptance-criteria coverage matched the backlog spec exactly; QA
  smoke-tested conflict resolution, key ordering, empty-map edge cases,
  non-mutation, and both error paths via `cinder.cli run`. BACKLOG.md task
  marked done and remaining tasks renumbered; task 1 is now `get` for safe
  map access.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Third clean one-shot merge in a row tonight — the backlog is moving fast
  with zero review/QA friction; queue is clear for the next Engineer
  session.

- **Merged**: PR #44 "Standard library: `sort_by` with a custom key
  function" (`feat/20260722-sort-by`) — clean first pass, no bounces.
  Added `sort_by(list, fn)` to `cinder/builtins.py`, calling `fn` once per
  element via the shared `call_value` helper and sorting by the resulting
  keys with Python's stable `sorted(..., key=...)`, rejecting mixed-type
  keys the same way `sort` rejects mixed-type elements. `VERDICT: LGTM`
  and `QA: PASS` both landed after the single commit (486 tests passing).
  Reviewer confirmed stability holds because the sort key is the decorated
  key only (never falling back to comparing unorderable elements) and that
  the empty-list case short-circuits without calling `fn`; QA smoke-tested
  a custom-key sort, non-mutation, the empty-list case, and all three error
  paths (non-list, non-callable, mixed-type keys) via `cinder.cli run`.
  Worktree `.worktrees/sort-by` removed before merge. BACKLOG.md task
  removed (renumbering left for the next Architect session, per the usual
  split of duties).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fourth clean one-shot merge in a row tonight — zero review/QA friction
  across the whole shift so far; queue is clear for the next Engineer
  session.

## 2026-07-23

- **Merged**: none.
- **Bounced this cycle**: PR #45 "Bitwise operators: &, |, ^, ~, <<, >>"
  (`feat/20260722-bitwise-ops`) — Reviewer flagged a real bug: negative
  shift counts on `<<`/`>>` crash with a raw Python `ValueError` instead
  of a clean `CinderRuntimeError`, the same class of guard `_divide_op`
  already has for division by zero. `_bitwise_op` in
  `cinder/interpreter.py` checks operand types via `_is_int` but never
  checks the shift amount's sign. `VERDICT: CHANGES REQUESTED` (1st
  bounce for this PR); no QA comment posted yet. Left on its branch for
  the next Engineer session to fix and add tests for both operators.
- **Still open**: PR #45, awaiting the fix above.
- First bounce after four clean nights in a row — a real, well-caught bug
  rather than review friction, and the fix is small and well-scoped for
  the next Engineer session.

- **Merged**: PR #45 "Bitwise operators: &, |, ^, ~, <<, >>"
  (`feat/20260722-bitwise-ops`) — one bounce, then clean. The Engineer
  fixed the negative-shift-count bug flagged above: `_bitwise_op` now
  checks `right < 0` for `LSHIFT`/`RSHIFT` before delegating to Python's
  `<<`/`>>`, raising `CinderRuntimeError` with line/column instead of a
  raw `ValueError`, mirroring `_divide_op`'s existing zero-division guard.
  Added `test_negative_left_shift_raises` and
  `test_negative_right_shift_raises`. `VERDICT: LGTM` and `QA: PASS` both
  landed after the fix commit (505 tests passing, was 503). QA also
  smoke-tested all six operators plus precedence (`2 << 3 <= 20`) and the
  type-mismatch path via the REPL and `cinder.cli run`. Worktree
  `.worktrees/bitwise-ops` removed before merge. BACKLOG.md task removed
  (renumbering left for the next Architect session).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Recovered cleanly from last cycle's bounce — the fix was exactly as
  scoped, no surprises, and the queue is clear again for the next
  Engineer session.

- **Merged**: PR #46 "Standard library: `remove` for maps"
  (`feat/20260722-map-remove`) — clean, one-shot merge. `remove(map, key)`
  added to `cinder/builtins.py`, mutating in place (matching `push`/`pop`'s
  style) and reusing the existing map-index path's "missing map key"
  wording and `get`'s hashability check for consistent error messages.
  `VERDICT: LGTM` and `QA: PASS` both landed after the sole commit (511
  tests passing, 24 subtests). QA also smoke-tested aliasing to confirm
  in-place mutation, plus the missing-key, non-map, unhashable-key, and
  wrong-arity error paths via `cinder.cli run`. Worktree
  `.worktrees/map-remove` removed before merge. BACKLOG.md task removed
  (renumbering left for the next Architect session).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Third clean one-shot merge in the last four PRs — the night shift keeps
  its pace, queue is clear for the next Engineer session.

- **Merged**: PR #47 "Standard library: type-predicate builtins"
  (`feat/20260722-type-predicates`) — clean, one-shot merge. Adds
  `is_list`, `is_map`, `is_string`, `is_number`, `is_bool`, `is_nil`, and
  `is_function` to `cinder/builtins.py`, reusing the existing
  `_is_numeric`/`_is_callable` helpers and `_require_arity` for consistent
  arity errors. `VERDICT: LGTM` and `QA: PASS` both landed after the sole
  commit (535 tests passing). QA also smoke-tested all seven predicates
  via `cinder.cli run` and the REPL, including the `is_number(true) ==
  false` bool/number exclusion and `is_function` recognizing both a
  builtin and a user-defined `fn`. Worktree `.worktrees/type-predicates`
  removed before merge. BACKLOG.md task removed (renumbering left for the
  next Architect session).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fourth clean one-shot merge in the last five PRs — steady pace, queue is
  clear for the next Engineer session.

- **Merged**: none.
- **Bounced this cycle**: PR #48 "Standard library: floor, ceil, pow, sqrt"
  (`feat/20260722-math-builtins-2`) — Reviewer found two real bugs in
  `_pow` (`cinder/builtins.py:412-425`): a negative base with a fractional
  exponent (e.g. `pow(-8, 0.5)`) silently leaks a Python `complex` instead
  of raising, the same hole `sqrt` already guards against; and
  `ZeroDivisionError`/`OverflowError` from Python's `**` (e.g. `pow(0,
  -1)`, `pow(10.0, 400)`) propagate uncaught instead of becoming a
  `CinderRuntimeError`. `floor`, `ceil`, and `sqrt` were confirmed correct.
  `VERDICT: CHANGES REQUESTED` (1st bounce for this PR); no QA comment
  posted yet. Left on its branch for the next Engineer session to add the
  base<0/fractional-exponent and zero-base/negative-exponent guards, with
  tests.
- **Still open**: PR #48, awaiting the fix above.
- Only one PR in flight tonight and it bounced on a real edge case in
  `pow`'s complex-number/exception handling — same shape of catch as the
  bitwise-shift bounce two cycles ago, so the next Engineer session has a
  clear, well-scoped fix.

- **Merged**: PR #48 "Standard library: floor, ceil, pow, sqrt"
  (`feat/20260722-math-builtins-2`) — one bounce, then clean. The Engineer
  fixed both bugs flagged above: `_pow` now raises `CinderRuntimeError` for
  a negative base with a fractional exponent (`isinstance(result,
  complex)` guard, same treatment `sqrt` already gets) and catches
  `ZeroDivisionError`/`OverflowError` from `base ** exp`, re-raising as
  `CinderRuntimeError` with line/column. Added regression tests for
  `pow(-8, 0.5)`, `pow(0, -1)`, and `pow(10.0, 400)`. `VERDICT: LGTM` and
  `QA: PASS` both landed after the fix commit (557 tests passing, was
  554). QA also smoke-tested `floor`/`ceil`/`pow`/`sqrt` plus all three
  fixed edge cases and a large-but-valid `pow(2, 1000)` via
  `cinder.cli run`. Worktree `.worktrees/math-builtins-2` removed before
  merge.
- **Merged**: PR #49 "Standard library: `index_of` for lists"
  (`feat/20260723-index-of`) — clean, one-shot merge. `index_of(list,
  item)` added to `cinder/builtins.py`, returning the index of the first
  element equal to `item` (Cinder `==` value equality) or `-1` if not
  found, matching `sort`/`reverse`/`contains`'s type-check style.
  `VERDICT: LGTM` and `QA: PASS` both landed after the sole commit (542
  tests passing). QA also smoke-tested not-found, nested-list value
  equality, and empty-list cases via `cinder.cli run`. Worktree
  `.worktrees/index-of` removed before merge.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Both PRs in the queue cleared this cycle — the math-builtins fix from
  last cycle held up exactly as scoped, and index_of landed clean on the
  first pass. BACKLOG.md tasks 1 and 2 removed and renumbered, and the
  math-builtins/index_of tasks' stale mutual references fixed.

- **Merged**: none.
- **Bounced this cycle**: PR #50 "Standard library: `unique` for lists"
  (`feat/20260723-unique-builtin`) — Reviewer posted `VERDICT: LGTM`, but
  QA caught a real correctness bug the review missed: `unique([1, true])`
  returns `[1]` and `unique([0, false])` returns `[0]`, silently dropping
  values that Cinder's own `==` treats as distinct (`_values_equal`
  requires matching types for non-numeric values, so `1 == true` is
  `false` in Cinder). Root cause is `_unique`'s Python `set()` fast path
  and its fallback `==` scan both inheriting Python's `1 == True` /
  `0 == False` conflation. QA also confirmed the same bug already exists
  on `main` in `contains`/`index_of`, pre-dating this PR — `unique` is
  internally consistent with them but all three now share the bug. `QA:
  FAIL` (1st bounce for this PR). Left on its branch for the next
  Engineer session; since the pre-existing `contains`/`index_of` bug is
  out of scope for this PR, the fix should be a bool-aware equality check
  scoped to `_unique` (or a shared helper if the Architect wants the
  broader fix picked up as a separate backlog task).
- **Still open**: PR #50, awaiting the fix above.
- Reviewer and QA disagreed for the first time this cycle — LGTM missed a
  bool/int equality edge case that QA's manual exercise caught, a good
  reminder that the two roles cover different ground. Quiet night
  otherwise: one PR in flight, one real bug found before it could ship.

- **Merged**: PR #50 "Standard library: `unique` for lists"
  (`feat/20260723-unique-builtin`) — one bounce, then clean. The Engineer
  fixed the bool/int conflation flagged above, scoped to `unique()` only:
  the fast path now keys its dedup `set` on `(isinstance(element, bool),
  element)` so `true`/`1` and `false`/`0` never collide, and the fallback
  scan now uses `interpreter._values_equal` instead of raw Python `==`, so
  both paths agree with Cinder's own `==` operator. Added regression tests
  for `unique([1, true, 0, false])` and a mixed hashable/unhashable case.
  Correctly left the broader `contains`/`index_of` fix to BACKLOG.md task
  1 rather than scope-creeping this PR. `VERDICT: LGTM` and `QA: PASS`
  both landed after the fix commit (574 tests passing, was 572). QA
  re-verified all the previously-failing cases by hand via `cinder.cli
  run`, plus the unhashable-fallback and non-list-argument paths. Worktree
  `.worktrees/unique-builtin` removed before merge. BACKLOG.md task 1
  removed and the remaining tasks renumbered (2-9 → 1-8), with the
  `count` task's stale "task 2" backreference to the `values_equal` helper
  fixed to "task 1".
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Recovered cleanly from last cycle's bounce, scoped exactly as the
  post-mortem suggested — the bool/int fix stayed local to `unique()` and
  didn't try to drag in the pre-existing `contains`/`index_of` bug, which
  is now top of the backlog for its own session. Queue is clear.

- **Merged**: PR #51 "Fix: `contains`, `index_of`, and `in` conflate
  `bool` with `int`" (`fix/20260723-bool-int-eq`) — clean first pass, no
  bounces. Renamed `Interpreter`'s `_values_equal` to `values_equal`
  (dropped the leading underscore, exported alongside `contains_value`)
  and used it in place of raw Python `==` in `contains_value`'s list
  branch (backs `contains()`/`in`) and `_index_of`'s scan, so both agree
  with Cinder's own `==` operator on bool-vs-int. Correctly left the
  dict-key branch's native `key in dict` lookup alone per the task's
  explicit scope — fixing bool/int map-key collisions is a bigger,
  separate change. Added regression tests for all four acceptance
  criteria; existing numeric/string/list/map-key tests untouched. `VERDICT:
  LGTM` and `QA: PASS` both landed after the single commit (577 tests
  passing, up from 574). Worktree `.worktrees/fix-bool-int-eq` removed
  before merge. BACKLOG.md task 1 removed, remaining tasks renumbered
  (2-8 → 1-7), and the `count` task's backreference to the `values_equal`
  helper updated to point at PR #51 instead of "task 1" (which no longer
  exists now that the fix has shipped).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Two clean merges in a row now — the latent bool/int equality bug that
  QA caught two cycles ago is fully closed out across `unique`, `contains`,
  `index_of`, and `in` (only the map-key case remains, tracked as a known
  limitation, not a bug). Queue is clear; next Engineer session picks up
  `count` for lists.

- **Merged**: PR #52 "Standard library: `count` for lists"
  (`feat/20260723-cinder-count`) — clean first pass, no bounces. Added
  `count(list, item)` to `cinder/builtins.py`, returning the `int` number
  of elements equal to `item` via `values_equal()` (correctly inheriting
  the bool/int fix from PR #51) — the counting counterpart to `index_of`,
  which only reports the first match. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit; QA smoke-tested matches, zero-match,
  empty-list, bool/int distinction, string/nested-list equality, and both
  error paths via the CLI, not just the test suite (585 tests passing, up
  from 577). Worktree `.worktrees/cinder-count` removed before merge.
  BACKLOG.md task 1 removed and remaining tasks renumbered (2-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Three clean merges in a row now — the night is going smoothly with no
  review/QA friction since the bool/int equality bug closed out. Queue is
  clear; next Engineer session picks up `flatten` for lists.

- **Merged**: PR #53 "Standard library: `flatten` for lists"
  (`feat/20260723-flatten-lists`) — clean first pass, no bounces. Added
  `flatten(list)` to `cinder/builtins.py`, flattening exactly one level of
  list-of-lists nesting into a new list (non-mutating, matching
  `concat`/`slice`'s type-check style) — non-list top-level elements pass
  through unchanged. `VERDICT: LGTM` and `QA: PASS` both landed after the
  single commit; QA smoke-tested one-level flatten, mixed non-list
  elements, empty-list cases, non-mutation, and both error paths via the
  CLI, not just the test suite (592 tests passing, up from 585). Worktree
  `.worktrees/flatten-lists` removed before merge. BACKLOG.md task 1
  removed and remaining tasks renumbered (2-6 → 1-5).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Four clean merges in a row now — the night shift is in a strong groove
  with no review/QA friction. Queue is clear; next Engineer session picks
  up `format` for string templating.

- **Merged**: PR #54 "Standard library: `format()` for string templating"
  (`feat/20260723-format-builtin`) — clean first pass, no bounces. Added
  `format(template, ...)` to `cinder/builtins.py`, a minimal sprintf-style
  templating builtin (variadic like `min`/`max`, two-pass scan validating
  brace pairs and placeholder count against argument count before
  substituting via `stringify()`). `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit; QA smoke-tested happy path, zero
  placeholders, list/string stringification, too-few/too-many args, a
  stray unmatched `{`, a non-`str` template, and a zero-arg call via the
  CLI, not just the test suite (601 tests passing, up from 592). Worktree
  `.worktrees/format-builtin` removed before merge. BACKLOG.md task 1
  removed and remaining tasks renumbered (2-6 → 1-5).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Five clean merges in a row now — the night shift's streak continues with
  no review/QA friction. Queue is clear; next Engineer session picks up
  persistent REPL command history.

- **Merged**: PR #55 "REPL: persistent command history across sessions"
  (`feat/20260723-repl-history`) — clean first pass, no bounces. Extended
  `_try_enable_readline()` in `cinder/repl.py` to load history from
  `projects/cinder/.cinder_history` on startup and added `_save_history()`
  to write it back on any clean exit via `try`/`finally` around
  `run_repl()`'s main loop, both guarded with `except OSError` matching
  the existing `except ImportError` fallback style; history file is
  gitignored and scoped inside the project directory. `VERDICT: LGTM` and
  `QA: PASS` both landed after the single commit; QA smoke-tested over a
  real pty (piped stdin doesn't exercise readline) — history written
  across a first session, recalled with Up-arrow in a fresh second
  session, and confirmed only command history persists, not variable
  state, plus the read-only-filesystem path via the suite (606 tests
  passing, up from 601). Worktree `.worktrees/repl-history` removed
  before merge. BACKLOG.md task 1 removed and remaining tasks renumbered
  (2-6 → 1-5).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Six clean merges in a row now — the night shift's streak continues
  uninterrupted with no review/QA friction. Queue is clear; next Engineer
  session picks up list slicing syntax.

- **Merged**: PR #56 "List slicing syntax: `list[start:end]`"
  (`feat/20260723-list-slicing`) — clean first pass, no bounces. Added a
  `SliceExpr` AST node and extended `_finish_index` in `cinder/parser.py`
  to parse an optional `:` inside `expr[...]`, falling back to plain
  indexing when absent; evaluated via a new `_evaluate_slice` in
  `cinder/interpreter.py` sharing bound normalization/clamping with the
  existing `slice()` builtin (deduped `_normalize_slice_bound` out of
  `cinder/builtins.py` into `interpreter.py`). Only `list`/`str` are
  sliceable; slices aren't assignable. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit; QA ran the full suite in a detached
  worktree and manually smoke-tested list/string slices, negative bounds,
  out-of-range clamping, copy semantics on `[:]`, plain indexing staying
  unaffected, and error paths for map slicing/bad assignment/non-int
  bounds via both the CLI and REPL (623 tests passing, up from 606).
  Worktree `.worktrees/list-slicing` removed before merge. BACKLOG.md
  task 1 removed and remaining tasks renumbered (2-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Seven clean merges in a row now — the night shift's streak continues
  uninterrupted with no review/QA friction. Queue is clear; next Engineer
  session picks up `group_by` for lists.

## 2026-07-24

- **Merged**: PR #57 "Standard library: `group_by` for lists"
  (`feat/20260723-group-by`) — clean first pass, no bounces. Added
  `group_by(list, fn)` to `cinder/builtins.py`, partitioning elements into
  a `map` keyed by `fn(element)`, reusing `call_value` and
  `_is_valid_key` from the existing `map`/`filter`/`sort_by`/`get` paths;
  a non-hashable key raises `CinderRuntimeError` matching `get`'s wording.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit; QA
  ran the full suite in a detached worktree and smoke-tested parity
  grouping, string-prefix grouping, empty-list short-circuit, and all
  four error branches via the CLI (633 tests passing, up from 623).
  Worktree `.worktrees/group-by` removed before merge. BACKLOG.md task 1
  removed and remaining tasks renumbered (2-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Eight clean merges in a row now — the night shift's streak continues
  uninterrupted with no review/QA friction. Queue is clear; next Engineer
  session picks up `try`/`catch` for runtime error recovery.
- **Merged**: PR #58 "try/catch for runtime error recovery"
  (`feat/20260723-try-catch`) — clean first pass, no bounces. Added
  `TRY`/`CATCH` keywords, a `TryStmt` AST node, and parser support for
  `try { ... } catch (name) { ... }`; the interpreter runs `try_block` in
  a child `Environment` and, on a caught `CinderRuntimeError`, binds the
  message to `catch_name` in a fresh child `Environment` and runs
  `catch_block`, with `break`/`continue`/`return` still propagating
  uncaught since they're Python-internal signals, not
  `CinderRuntimeError`. `VERDICT: LGTM` and `QA: PASS` both landed after
  the single commit; QA ran the full suite in a detached worktree and
  smoke-tested basic catch, nested try/catch, catch-name scoping,
  break/continue/return passthrough inside loops and functions, and the
  REPL path (650 tests passing, up from 633, 17 new). Worktree
  `.worktrees/try-catch` removed before merge. BACKLOG.md task 1 removed
  and remaining tasks renumbered (2-8 → 1-7).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Nine clean merges in a row — the streak holds, zero review/QA friction
  tonight. Queue is clear; next Engineer session picks up `chunk` for
  lists.
- **Merged**: PR #59 "Standard library: `chunk` for lists"
  (`feat/20260723-chunk-lists`) — clean first pass, no bounces. Added
  `chunk(list, size)` to `cinder/builtins.py`, splitting a list into
  consecutive sublists of length `size` (last sublist shorter on uneven
  remainder), non-mutating, matching `slice`/`concat`/`flatten`'s
  type-check style; `size` must be a positive `int`, checked before
  looking at the list's contents so it fires even for an empty list.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit; QA
  ran the full suite in a detached worktree and smoke-tested even/uneven
  splits, empty list, non-mutation, and all error branches via the CLI
  (661 tests passing, up from 650, 11 new). Worktree `.worktrees/chunk-lists`
  removed before merge. BACKLOG.md task 1 removed and remaining tasks
  renumbered (2-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Ten clean merges in a row — the streak holds, zero review/QA friction
  tonight. Queue is clear; next Engineer session picks up `partition` for
  lists.
- **Merged**: PR #60 "Standard library: `partition` for lists"
  (`feat/20260723-partition-lists`) — clean first pass, no bounces. Added
  `partition(list, fn)` to `cinder/builtins.py`, splitting a list into
  `[matching, non_matching]` based on `fn(element)`'s Cinder truthiness,
  reusing the shared `call_value`/`is_truthy` helpers and matching
  `map`/`filter`'s type-check style. `VERDICT: LGTM` and `QA: PASS` both
  landed after the single commit; QA ran the full suite in a detached
  worktree and smoke-tested even split, empty list (callback never
  invoked), all-matching/none-matching, and both type-error branches via
  the CLI (672 tests passing, up from 661, 11 new). Worktree
  `.worktrees/partition-lists` removed before merge. BACKLOG.md task 1
  removed and remaining tasks renumbered (2-9 → 1-8).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Eleven clean merges in a row — the streak holds, zero review/QA
  friction tonight. Queue is clear; next Engineer session picks up
  default parameter values for functions.
- **Merged**: none this cycle.
- **Bounced this cycle**: PR #61 "Default parameter values: `fn f(a, b
  = 1) { ... }`" (`feat/20260723-default-params`) got its first
  `VERDICT: CHANGES REQUESTED`. Reviewer found a real bug: default-value
  expressions in `call_value` (`interpreter.py:589-595`) are evaluated
  outside the `try/except CinderRuntimeError` block that appends the
  callee's frame to `error.frames`, so an error raised while evaluating a
  default (e.g. `fn f(a = g())` where `g()` raises) is missing the
  calling function's stack frame, unlike every error raised from the
  function body. One bounce so far (of 3 before graveyard); no QA verdict
  posted yet. Left open for the next Engineer session to fix on the same
  branch.
- **Still open**: PR #61 (1× changes requested, awaiting fix).
- The eleven-merge streak ends on review friction rather than a broken
  build — a real, well-isolated bug caught before merge, not a wasted
  night.
- **Merged**: PR #61 "Default parameter values: `fn f(a, b = 1) { ... }`"
  (`feat/20260723-default-params`) — one bounce, then clean. The Engineer's
  fix moved the default-parameter evaluation loop inside `call_value`'s
  existing `try/except CinderRuntimeError` so an error raised while
  evaluating a default now gets the caller's frame appended, same as any
  body error. `VERDICT: LGTM` landed after the fix commit, re-verifying the
  reviewer's own repro (`fn g() { return 1/0; } fn f(a = g()) { return a;
  } f();` now records both `g` and `f` frames) and confirming the new
  `test_error_in_default_expression_records_calling_frame` test plus a
  sweep of every other `.params` call site for the new tuple shape. QA ran
  the full suite in a detached worktree (686 tests passing, up from 650)
  and smoke-tested basic defaults, later-default-sees-earlier-parameter,
  the exact frame-fix repro end-to-end via the CLI, and both arity-range
  error messages — `QA: PASS`. Worktree `.worktrees/default-params`
  removed before merge. BACKLOG.md task 1 removed and remaining tasks
  renumbered (2-8 → 1-7), with a Done entry noting the bounce.
- **Bounced this cycle**: none (PR #61's bounce was last cycle; this cycle
  only merged the fix).
- **Still open**: no open PRs.
- Clean recovery from last cycle's review friction — the fix was small,
  targeted, and verified end-to-end rather than just unit-tested; the
  queue is clear and the night is going well.
- **Merged**: PR #62 "Block comments: `/* ... */`"
  (`feat/20260723-block-comments`) — clean first pass, no bounces. Extended
  `Lexer._skip_whitespace_and_comments` to recognize `/*...*/`, non-nesting
  (first `*/` wins, matching C/Java/JS), tracking embedded newlines so
  line/column stays correct for tokens after the comment, and raising
  `LexError(unterminated=True)` at EOF — reusing the same flag the REPL's
  `_needs_more_input` already branches on for unterminated strings, so no
  REPL changes were needed. `VERDICT: LGTM` and `QA: PASS` both landed
  after the single commit; QA ran the full suite in a detached worktree
  and smoke-tested leading/trailing/inline/multi-line comments, the
  non-nesting `/*/` edge case, `/` and `/=` regression, a `#`-comment
  containing literal `/*` text, and the unterminated case via both the CLI
  and REPL (696 tests passing, up from 686, 24 new). Worktree
  `.worktrees/block-comments` removed before merge. BACKLOG.md task 1
  removed and remaining tasks renumbered (2-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twelve of the last thirteen PRs have landed clean — the queue is clear
  and the night is going well; next Engineer session picks up `insert`
  and `remove_at` for lists.
- **Merged**: PR #63 "Standard library: `insert` and `remove_at` for lists"
  (`feat/20260723-insert-remove-at`) — clean first pass, no bounces. Added
  `insert(list, index, value)` and `remove_at(list, index)` to
  `cinder/builtins.py`, filling the gap between `push`/`pop` (end-only) and
  map's `remove` (key-based). Extracted a `normalize_index(index, length)`
  helper in `cinder/interpreter.py`, deduping the negative-index
  normalization that had been inlined three times, and pointed all four
  call sites (three existing plus the two new builtins) at it. `VERDICT:
  LGTM` and `QA: PASS` both landed after the single commit; QA ran the
  full suite in a detached worktree and smoke-tested middle/front/end/
  negative-index insert and remove, empty-list and out-of-range errors,
  and a wrong-type-index error via the CLI and REPL (711 tests passing,
  24 subtests, up from 696). Worktree `.worktrees/insert-remove-at`
  removed before merge. BACKLOG.md task 1 removed and remaining tasks
  renumbered (2-8 → 1-7).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirteen of the last fourteen PRs have landed clean — the queue is clear
  and the night is going well.
- **Merged**: PR #64 "Standard library: `ord` and `chr` for character/
  code-point conversion" (`feat/20260724-ord-chr`) — clean first pass, no
  bounces. Added `ord(s)` and `chr(n)` to `cinder/builtins.py`, following
  `_int`/`_float`'s single-argument conversion style and delegating to
  Python's own `ord()`/`chr()`, converting `ValueError` into
  `CinderRuntimeError` with line/column. `VERDICT: LGTM` and `QA: PASS`
  both landed after the single commit; QA ran the full suite in a
  detached worktree and smoke-tested round-trip conversion, non-ASCII
  code points, empty/multi-character strings, out-of-range and negative
  code points, bool-rejected-as-int, wrong arity, via both the CLI and
  REPL (723 tests passing, up from 711). Worktree `.worktrees/ord-chr`
  removed before merge. BACKLOG.md task 1 removed and remaining tasks
  renumbered (2-9 → 1-8).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fourteen of the last fifteen PRs have landed clean — the queue is clear
  and the night is going well.
- **Merged**: PR #65 "Standard library: `pad_start` and `pad_end` for
  strings" (`feat/20260724-pad-start-end`) — clean first pass, no bounces.
  Added `pad_start(s, width, fill)` and `pad_end(s, width, fill)` to
  `cinder/builtins.py`, following `_find`/`_replace`'s multi-`str`-argument
  style, with a shared `_check_pad_arguments` helper validating both.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit; QA
  ran the full suite in a detached worktree and smoke-tested happy path,
  no-op at/over width, empty-string input, multi-character fill, negative
  width, non-`str`/non-`int` arguments, and bool-rejected-as-width, via
  the CLI (741 tests passing, up from 723). Worktree
  `.worktrees/pad-start-end` removed before merge. BACKLOG.md task 1
  removed and remaining tasks renumbered (2-8 → 1-7).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fifteen of the last sixteen PRs have landed clean — the queue is clear
  and the night is going well.
- **Merged**: PR #66 "Standard library: `first` and `last` for lists"
  (`feat/20260724-first-last-builtins`) — clean first pass, no bounces.
  Added `first(list)` and `last(list)` to `cinder/builtins.py`, following
  `reverse`/`copy`'s non-mutating, single-arg style, raising
  `CinderRuntimeError` on empty-list or non-list arguments. `VERDICT: LGTM`
  and `QA: PASS` both landed after the single commit; QA ran the full
  suite in a detached worktree and smoke-tested multi-element and
  single-element lists, empty-list and non-list rejection, and wrong
  arity, via both the CLI and REPL (751 tests passing, up from 741).
  Worktree `.worktrees/first-last-builtins` removed before merge.
  BACKLOG.md task 1 removed and remaining tasks renumbered (2-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Sixteen of the last seventeen PRs have landed clean — the queue is
  clear and the night is going well.
- **Merged**: PR #67 "Standard library: `take` and `drop` for lists"
  (`feat/20260724-take-drop-builtins`) — clean first pass, no bounces.
  Added `take(list, n)` and `drop(list, n)` to `cinder/builtins.py`, both
  delegating to `slice`'s existing bound-clamping logic, rejecting
  negative `n` (unlike `slice` itself) with `CinderRuntimeError`.
  `VERDICT: LGTM` and `QA: PASS` both landed after the single commit; QA
  ran the full suite in a detached worktree and smoke-tested basic slices,
  clamped `n`, `n=0`, empty list, non-mutation, negative `n`, non-list
  and non-int arguments, and wrong arity, via both the CLI and REPL (769
  tests passing, up from 751). Worktree `.worktrees/take-drop-builtins`
  removed before merge. BACKLOG.md task 1 removed and remaining tasks
  renumbered (2-8 → 1-7).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Seventeen of the last eighteen PRs have landed clean — the queue is
  clear and the night continues to go well.

## 2026-07-25

- **Merged**: none this cycle.
- **Bounced this cycle**: none.
- **Still open**: no open PRs. `flat_map` for lists (BACKLOG.md task 1)
  is implemented, tested (777 tests pass), committed, and pushed to
  `origin/feat/20260724-flat-map`, but still has no PR — `gh pr create`
  keeps failing with a GitHub-side GraphQL error (`Something went wrong
  while executing your query`), now 5 attempts across two sessions with
  distinct support IDs each time. Retried once this cycle per the prior
  Engineer's note; still failing, so stopped per the 3x-repeat rule
  rather than burning more tokens on it. Worktree `.worktrees/flat-map`
  left in place for the next session to retry once GitHub's API
  recovers. See `nightshift/HELP.md` for full details.
- An unusually quiet night — GitHub's PR-creation API has been down
  since last cycle, so the only work sitting in the pipe is stuck behind
  it; nothing to review, QA, or merge until that clears or the team
  routes around it.
- **Merged**: none this cycle.
- **Bounced this cycle**: none.
- **Still open**: no open PRs (`gh pr list` returns `[]`). Two finished
  tasks remain stuck behind the `gh pr create` outage: `flat_map` for
  lists on `origin/feat/20260724-flat-map` (777 tests) and string
  interpolation on `origin/feat/20260724-string-interp` (794 tests), both
  still pushed with their worktrees intact, both now confirmed
  repo-wide/account-wide 500s on both the GraphQL and REST PR-creation
  paths (8 attempts total across four sessions/two nights) — see
  `nightshift/HELP.md`, already paged to the human via `notify.sh`.
  Nothing for Release to merge or close without a PR to carry verdict
  lines. Plain reads (`gh pr list`, `gh auth status`, `gh api
  /rate_limit`) all still work fine, so this looks scoped specifically to
  PR creation, not a token/auth/rate-limit problem.
- Still stuck behind the same blocker as last cycle — the fix here isn't
  more engineering, it's GitHub's PR-creation endpoint (or the token's
  permissions) recovering; everything else in the pipeline is idle
  waiting on it.
- **Merged**: PR #68 "Standard library: `flat_map` for lists"
  (`feat/20260724-flat-map`) — `flat_map(list, fn)` added to
  `cinder/builtins.py`. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS`,
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (task 1 is now string interpolation,
  still blocked on `gh pr create` — see below).
- **Bounced this cycle**: none.
- **Still open**: no open PRs (`gh pr list` returns `[]`). String
  interpolation (BACKLOG.md task 1) remains implemented, tested (794
  tests), committed, and pushed to `origin/feat/20260724-string-interp`
  with its worktree intact, but still has no PR — that's an Engineer-side
  retry, not something Release can act on.
- The `gh pr create` outage that stalled the last two cycles cleared
  sometime after the previous entry: `flat_map` went from pushed-but-
  unopenable to opened, reviewed, QA'd, and merged all in this one cycle.
  One task down, one still waiting on the same PR-creation retry.
- **Merged**: PR #69 "String interpolation: `\"...${expr}...\"`"
  (`feat/20260724-string-interp`) — rebased onto current `main`, opened
  cleanly (the `gh pr create` outage is confirmed fully cleared), Reviewer
  gave `VERDICT: LGTM`, QA gave `QA: PASS` (802 tests passing, up from
  794), squash-merged and branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-7 → 1-6).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Both tasks that were stuck behind the multi-night `gh pr create` outage
  are now shipped — the backlog queue is fully clear and the night is
  back to a clean, unblocked cadence.
- **Merged**: PR #70 "List destructuring in `let`: `let [a, b] = expr;`"
  (`feat/20260724-list-destructure`) — added a `DestructureLetStmt` AST
  node for flat positional list-pattern `let` bindings. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (817 tests passing, up from 802),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (1-7 → 1-7, now starting at `repeat` for
  lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- A smooth cycle — one clean PR in, reviewed, QA'd, and merged with no
  rework, keeping the recently-unblocked cadence going.
- **Merged**: PR #71 "Standard library: `repeat` for lists"
  (`feat/20260725-repeat-list`) — added `repeat(value, n)` to
  `cinder/builtins.py`, returning a new list of `n` shallow-aliased copies
  of `value`. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (824 tests
  passing, up from 817), both posted after the sole commit — clean squash
  merge, branch deleted, worktree removed first. BACKLOG.md task 1 marked
  done under `## Done` and remaining tasks renumbered (1-7 → 1-6, now
  starting at `map_values` for maps).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Another clean, unblocked cycle — the queue keeps moving with no rework
  since the `gh pr create` outage cleared.
- **Merged**: PR #72 "Standard library: `map_values` for maps`"
  (`feat/20260725-map-values`) — added `map_values(map, fn)` to
  `cinder/builtins.py`, returning a new map with each value replaced by
  `fn(value)` via the shared `call_value` helper. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (832 tests passing, up from 824),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (1-6 → 1-5, now starting at hex/binary/
  octal numeric literals).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Six clean cycles in a row since the `gh pr create` outage cleared — no
  rework, no blockers, just steady stdlib-builtin throughput.
- **Merged**: PR #73 "Numeric literals: hexadecimal, binary, and octal
  integers" (`feat/20260725-hex-int-literals`) — extended
  `cinder/lexer.py`'s number-scanning to recognize `0x`/`0X`, `0b`/`0B`,
  and `0o`/`0O` prefixed integer literals, producing an ordinary `INT`
  token with no AST/parser/interpreter changes needed. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (852 tests passing, up from 832),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (1-7 → 1-7, now starting at `find_index`
  for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Seven clean cycles in a row since the `gh pr create` outage cleared —
  the queue continues to move without friction.
- **Merged**: PR #74 "Standard library: `find_index` for lists"
  (`feat/20260725-find-index`) — added `find_index(list, fn)` to
  `cinder/builtins.py`, returning the index of the first element for which
  `fn(element)` is truthy (or `-1`), short-circuiting so `fn` is never
  called past the first match. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (859 tests passing, up from 852), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-7 → 1-6, now starting at `flatten_deep` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Eight clean cycles in a row since the `gh pr create` outage cleared —
  the queue keeps moving with no rework.
- **Merged**: PR #75 "Standard library: `flatten_deep` for lists"
  (`feat/20260725-flatten-deep`) — added `flatten_deep(list)` to
  `cinder/builtins.py`, the fully-recursive counterpart to the existing
  one-level `flatten` (PR #53), flattening list-of-lists nesting at every
  depth into a single new list. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (866 tests passing, up from 859), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-6 → 1-5, now starting at `min_by`/`max_by` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Nine clean cycles in a row since the `gh pr create` outage cleared —
  the queue keeps moving with no rework.
- **Merged**: PR #76 "Standard library: `min_by` and `max_by` for lists"
  (`feat/20260725-min-max-by`) — added `min_by(list, fn)`/`max_by(list,
  fn)` to `cinder/builtins.py`, selecting the element whose `fn(element)`
  result is smallest/largest via the shared `call_value` helper, matching
  `sort_by`'s callback style. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (881 tests passing, up from 866), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-5 → 1-4, now starting at `remove` value-based removal for
  lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Ten clean cycles in a row since the `gh pr create` outage cleared — the
  queue keeps moving with no rework.
- **Merged**: PR #77 "Standard library: value-based removal for lists via
  `remove`" (`feat/20260725-list-remove`) — extended the existing
  map-only `remove` builtin to also dispatch on `list`, the same way
  `contains` dispatches across list/map/string; `remove(list, value)`
  deletes and returns the first element equal to `value` (via the shared
  `values_equal` helper), mutating in place and raising on no match.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (886 tests passing,
  up from 881), both posted after the sole commit — clean squash merge,
  branch deleted, worktree removed first. BACKLOG.md task 1 marked done
  under `## Done` and remaining tasks renumbered (1-7 → 1-6, now starting
  at `invert` for maps).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Eleven clean cycles in a row since the `gh pr create` outage cleared —
  the queue keeps moving with no rework.
- **Merged**: PR #78 "Standard library: `invert()` for maps"
  (`feat/20260725-invert-map`) — added `invert(map)` to
  `cinder/builtins.py`, swapping each key/value pair (reusing
  `_is_valid_key` to reject a non-hashable value before it's used as a
  key), later entry wins on collision, matching `merge`'s rule;
  non-mutating. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (893
  tests passing, up from 886), both posted after the sole commit — clean
  squash merge, branch deleted, worktree removed first. BACKLOG.md task 1
  marked done under `## Done` and remaining tasks renumbered (1-8 → 1-7,
  now starting at `zip_with` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twelve clean cycles in a row since the `gh pr create` outage cleared —
  the queue keeps moving with no rework.
- **Merged**: PR #79 "Standard library: `zip_with()` for lists"
  (`feat/20260725-zip-with`) — added `zip_with(list1, list2, fn)` to
  `cinder/builtins.py`, pairing two lists elementwise via `fn(a, b)` (the
  shared `call_value` helper) instead of `zip`'s bare `[a, b]` pairing,
  truncated to the shorter list's length like `zip`. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (901 tests passing, up from 893),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (1-12 → 1-11, now starting at map
  destructuring in `let`).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Thirteen clean cycles in a row since the `gh pr create` outage cleared —
  the queue keeps moving with no rework.

## 2026-07-26

- **Merged**: PR #80 "Map destructuring in `let`: `let {a, b} = expr;`"
  (`feat/20260725-map-destructure`) — extended `DestructureLetStmt` (from
  PR #70's list form) with an `is_map` flag instead of a new AST node;
  binds each identifier by looking it up as a key in a map RHS, missing
  keys or a non-map RHS raise `CinderRuntimeError` with line/column, extra
  unnamed keys are silently ignored. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (918 tests passing, up from 901), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-11 → 1-10, now starting at `count_by` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fourteen clean cycles in a row since the `gh pr create` outage cleared —
  the queue keeps moving steadily, no rework needed on this task either.
- **Merged**: PR #81 "Standard library: `count_by` for lists"
  (`feat/20260725-count-by`) — added `count_by(list, fn)` to
  `cinder/builtins.py`, mirroring `group_by`'s `call_value`/`_is_valid_key`
  pattern but tallying group sizes into `{key: count}` instead of
  collecting elements. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS`
  (928 tests passing, up from 918), both posted after the sole commit —
  clean squash merge, branch deleted, worktree removed first. BACKLOG.md
  task 1 marked done under `## Done` and remaining tasks renumbered
  (1-10 → 1-9, now starting at `deep_copy` for lists and maps).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Fifteen clean cycles in a row since the `gh pr create` outage cleared —
  the queue is moving smoothly and steadily tonight.
- **Merged**: PR #82 "Standard library: `deep_copy` for lists and maps"
  (`feat/20260725-deep-copy`) — added `deep_copy(collection)` to
  `cinder/builtins.py`, recursing through arbitrary list/map nesting so
  every nested container in the result is a fresh copy, unlike the
  existing shallow `copy`. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (934 tests passing, up from 928), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-11 → 1-10, now starting at `distinct_by` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Sixteen clean cycles in a row since the `gh pr create` outage cleared —
  the backlog queue keeps emptying with no rework required.
- **Merged**: PR #83 "Standard library: `distinct_by` for lists"
  (`feat/20260725-distinct-by`) — added `distinct_by(list, fn)` to
  `cinder/builtins.py`, mirroring `group_by`/`count_by`'s `call_value`/
  `_is_valid_key` pattern but keeping the first element encountered per
  distinct `fn(element)` key. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (943 tests passing, up from 934), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-10 → 1-9, now starting at `strip_prefix`/`strip_suffix`
  for strings).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Seventeen clean cycles in a row since the `gh pr create` outage cleared —
  the night is going smoothly, nothing on fire.
- **Merged**: PR #84 "Standard library: `strip_prefix` and `strip_suffix`
  for strings" (`feat/20260725-strip-prefix-suffix`) — added thin wraps
  over `str.removeprefix`/`removesuffix` to `cinder/builtins.py`, matching
  `starts_with`/`ends_with`'s arity/error-message/registration shape.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (955 tests passing,
  up from 943), both posted after the sole commit — clean squash merge,
  branch deleted, worktree removed first. BACKLOG.md task 1 marked done
  under `## Done` and remaining tasks renumbered (1-10 → 1-9, now starting
  at `take_while`/`drop_while` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Eighteen clean cycles in a row since the `gh pr create` outage cleared —
  the backlog keeps emptying with no rework required.
- **Merged**: PR #85 "Standard library: `take_while` and `drop_while` for
  lists" (`feat/20260725-take-while-drop-while`) — added
  `take_while(list, fn)`/`drop_while(list, fn)` to `cinder/builtins.py`,
  following `partition`/`find_index`'s `call_value`/`is_truthy` pattern,
  both stopping at the first falsy result rather than scanning past it.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (971 tests passing,
  up from 955), both posted after the sole commit — clean squash merge,
  branch deleted, worktree removed first. BACKLOG.md task 1 marked done
  under `## Done` and remaining tasks renumbered (1-10 → 1-9, now starting
  at the spread operator in list literals).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Nineteen clean cycles in a row since the `gh pr create` outage cleared —
  the night shift is running like clockwork tonight.
- **Merged**: PR #86 "Spread operator in list literals:
  `[...list1, x, ...list2]`" (`feat/20260726-spread-list`) — added a
  `DOT_DOT_DOT` token and extended list-literal parsing/evaluation to splice
  `...expr` elements into the result, raising `CinderRuntimeError` with
  line/column for a non-list spread target; map literals explicitly out of
  scope, pinned by a regression test. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (979 tests passing, up from 971), both posted after the sole
  commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-10 → 1-9, now starting at `last_index_of` for lists); also
  updated task 6 (rest parameters)'s note that the spread-operator token it
  depends on has now actually merged.
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty clean cycles in a row since the `gh pr create` outage cleared — the
  backlog is healthy and the night is going smoothly.
- **Merged**: PR #87 "Standard library: `lines` and `words` for strings"
  (`feat/20260726-lines-words`) — added `lines(s)` (splits on literal
  `"\n"`, no `\r\n` special-casing) and `words(s)` (splits on whitespace
  runs via Python's argumentless `str.split()`, discarding empty entries)
  to `cinder/builtins.py`, following `trim`/`split`'s single-`str`-argument
  style. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (989 tests
  passing, up from 979), both posted after the sole commit — clean squash
  merge, branch deleted, worktree removed first. BACKLOG.md task 1 marked
  done under `## Done` and remaining tasks renumbered (1-9 → 1-8, now
  starting at `last_index_of` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-one clean cycles in a row since the `gh pr create` outage cleared —
  the backlog keeps emptying smoothly, no rework needed tonight.
- **Merged**: PR #88 "Standard library: `last_index_of` for lists"
  (`feat/20260726-last-index-of`) — added `last_index_of(list, item)` to
  `cinder/builtins.py`, the mirror of the existing `index_of` (PR #49),
  scanning from the end via the shared `values_equal` helper (agreeing with
  `index_of`/`contains`/`in` on bool-vs-int per PR #51) and returning the
  `int` index of the last match or `-1`. Reviewer gave `VERDICT: LGTM`, QA
  gave `QA: PASS` (995 tests passing, up from 989), both posted after the
  sole commit — clean squash merge, branch deleted, worktree removed first.
  BACKLOG.md task 1 marked done under `## Done` and remaining tasks
  renumbered (1-8 → 1-7, now starting at the `switch` statement).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-two clean cycles in a row since the `gh pr create` outage cleared —
  the backlog is healthy and the night keeps shipping without friction.
- **Merged**: PR #89 "switch statement" (`feat/20260726-switch-stmt`) —
  added new `SWITCH`/`CASE`/`DEFAULT` keywords, `SwitchStmt`/`SwitchCase`
  AST nodes, parser support, and interpreter evaluation: scrutinee
  evaluated exactly once, compared against each case value in source order
  via `values_equal`, first match's block runs with no fallthrough, falls
  back to `default` if present, else no-op; `switch` is not a loop, so
  `break`/`continue` inside a case still target an enclosing loop.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (1015 tests passing, up
  from 995), both posted after the sole commit — clean squash merge,
  branch deleted, worktree removed first. BACKLOG.md task 1 marked done
  under `## Done` and remaining tasks renumbered (1-7 → 1-6, now starting
  at `capitalize` for strings).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-three clean cycles in a row since the `gh pr create` outage
  cleared — the language keeps growing a feature a cycle with zero rework.
- **Merged**: PR #90 "Standard library: `capitalize` for strings"
  (`feat/20260726-capitalize`) — added `capitalize(s)` to
  `cinder/builtins.py`, uppercasing only the first character of `s` via
  `str.upper()` and leaving the rest untouched (deliberately not Python's
  `str.capitalize()`, which also lowercases the remainder). Empty string is
  a no-op. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (1022 tests
  passing, up from 1015), both posted after the sole commit — clean squash
  merge, branch deleted, worktree removed first. BACKLOG.md task 1 marked
  done under `## Done` and remaining tasks renumbered (1-6 → 1-5, now
  starting at `clamp` for numbers).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-four clean cycles in a row since the `gh pr create` outage
  cleared — the backlog keeps emptying smoothly night after night.
- **Merged**: PR #91 "Standard library: `clamp` for numbers"
  (`feat/20260726-clamp`) — added `clamp(n, lo, hi)` to `cinder/builtins.py`,
  following the same shape as `min`/`max`: per-argument numeric checks
  (bool excluded for free via `_is_numeric`), a `lo > hi` guard, then the
  clamp logic itself. Mixed int/float args pass through unchanged in type.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (1031 tests passing, up
  from 1022), both posted after the sole commit — clean squash merge,
  branch deleted, worktree removed first. BACKLOG.md task 1 marked done
  under `## Done` and remaining tasks renumbered (1-5 → 1-4, now starting
  at rest parameters in function declarations).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-five clean cycles in a row since the `gh pr create` outage
  cleared — the studio just keeps shipping, one small builtin at a time.

## 2026-07-27

- **Merged**: none this cycle.
- **Bounced this cycle**: none.
- **Still open**: no open PRs. BACKLOG.md task 1 (rest parameters in
  function declarations) is claimed and in progress in
  `.worktrees/rest-params` on `feat/20260726-rest-params`, but no PR has
  been opened yet — nothing for Release to act on this cycle.
- Quiet cycle: the Engineer is mid-task with nothing pushed for review
  yet, so there was nothing to merge or bounce, but the pipeline itself
  is healthy — no stuck PRs, no repeat failures, `main` still green.
- **Merged**: PR #92 "Rest parameters in function declarations:
  `fn f(a, ...rest) { ... }`" (`feat/20260726-rest-params`) — extends
  `FnDecl`/`FnExpr` with an optional trailing rest parameter, reusing the
  existing spread-operator ellipsis token in the parser and giving
  `call_value` a "no upper bound" arity case. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (1046 tests passing, up from 1038),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (2-15 → 1-14, now starting at `is_empty`
  for lists/maps/strings).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-six clean cycles in a row since the `gh pr create` outage
  cleared — the backlog's top task shipped the same night it was picked
  up, no rework needed.
- **Merged**: PR #93 "Standard library: `is_empty` for lists, maps, and
  strings" (`feat/20260726-is-empty`) — added `is_empty(collection)` to
  `cinder/builtins.py`, mirroring `len`'s existing type-check and
  arity-check pattern for `list`/`map`/`str`. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (1054 tests passing, up from 1046),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (2-14 → 1-13, now starting at
  `union`/`intersection`/`difference` for lists).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-seven clean cycles in a row since the `gh pr create` outage
  cleared — the studio hasn't needed a single round of rework in over
  three weeks of nights.
- **Merged**: PR #94 "Standard library: `union`, `intersection`,
  `difference` for lists" (`feat/20260726-union-intersection-difference`)
  — added all three to `cinder/builtins.py`, treating lists as unordered
  sets, factoring `unique`'s dedupe logic into a shared `_dedupe` helper
  and consolidating arity/type checks in `_require_two_lists`. Reviewer
  gave `VERDICT: LGTM`, QA gave `QA: PASS` (1072 tests passing, up from
  1054), both posted after the sole commit — clean squash merge, branch
  deleted, worktree removed first. BACKLOG.md task 1 marked done under
  `## Done` and remaining tasks renumbered (2-13 → 1-12, now starting at
  `pluck` for lists of maps).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-eight clean cycles in a row since the `gh pr create` outage
  cleared — a smooth, uneventful night for the studio.
- **Merged**: PR #95 "Standard library: `pluck` for lists of maps"
  (`feat/20260726-pluck`) — added `pluck(list, key)` to
  `cinder/builtins.py`, reusing `_is_valid_key` for key validation and
  matching map-index's raise-on-missing-key behavior. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (1079 tests passing, up from 1072),
  both posted after the sole commit — clean squash merge, branch deleted,
  worktree removed first. BACKLOG.md task 1 marked done under `## Done`
  and remaining tasks renumbered (2-12 → 1-11, now starting at `pick`/
  `omit` for maps).
- **Bounced this cycle**: none.
- **Still open**: no open PRs.
- Twenty-nine clean cycles in a row since the `gh pr create` outage
  cleared — another small builtin shipped clean, no drama tonight.
