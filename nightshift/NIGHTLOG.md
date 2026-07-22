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
