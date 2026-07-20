# BACKLOG.md

Prioritized task list for Cinder (see `PROJECT.md` for vision/architecture).
All file paths in tasks are relative to this project's directory,
`projects/cinder/` — run the tests and the CLI from there.
**Top task = next Engineer's job.** Each task is sized for one focused
session. Engineer: claim the top task, implement + test in an isolated
worktree on a `<type>/<YYYYMMDD>-<slug>` branch (`feat`/`fix`/`chore`/`docs`/
`test` — see CLAUDE.md's worktree procedure), open a PR. Do not skip ahead to
a later task while an earlier one is unclaimed/open.

---

## 1. Standard library: string methods

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

## 2. `break` and `continue` for loops

Build: add `break` and `continue` statement support for both `while` and
`for`-in loops. New `BreakStmt`/`ContinueStmt` AST nodes
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
- Same two behaviors for `for`-in loops.
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

## 3. Standard library: math builtins

Build: extend `cinder/builtins.py` with `abs(n)`, `min(...)`, `max(...)`
(both variadic — one or more numeric arguments, `int` or `float`), and
`round(n)` (rounds to the nearest integer, ties-to-even, matching Python's
built-in `round`). Follow the existing arity/type-check style (`_len`,
`_str`): raise `CinderRuntimeError` with line/column for a non-numeric
argument, and for `min`/`max`, for zero arguments. `abs`/`round` are
single-argument like `_str`/`_int`; `min`/`max` need their own arity check
since they accept a variable number of arguments (`_require_arity` doesn't
fit them — write a small variadic check inline, e.g. reject only zero
arguments).

Acceptance criteria:
- `abs(-3)` is `3`, `abs(-3.5)` is `3.5`; `abs("x")` raises
  `CinderRuntimeError` with line/column.
- `min(3, 1, 2)` is `1`, `max(3, 1, 2)` is `3`; each works with a single
  argument (`min(5)` is `5`) and raises `CinderRuntimeError` with zero
  arguments or any non-numeric argument.
- `round(2.5)` is `2`, `round(3.5)` is `4` (ties-to-even); `round("x")`
  raises `CinderRuntimeError` with line/column.
- Unit tests cover happy path, wrong argument type, and (for `min`/`max`)
  wrong arity for each of the four builtins.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. REPL: command history via `readline`

Build: wire Python's stdlib `readline` module into `cinder/repl.py` so the
REPL supports up/down arrow history navigation and left/right/Home/End
in-line editing, matching ordinary shell REPL ergonomics (Python's own
`python3` REPL gets this for free from `readline`; Cinder's hand-rolled
input loop currently doesn't because it likely reads via `input()` without
`readline` imported, or reads stdin directly). Import `readline` at REPL
startup (guard with `try`/`except ImportError` — `readline` is unavailable
on some platforms, e.g. stock Windows Python; the REPL must still start
without it, just without history). Do not add persistent history-file
save/load across sessions — in-session history only, keep this task small.

Acceptance criteria:
- Running the REPL, entering a few statements, then pressing the up arrow
  recalls the previously entered line for editing/re-execution (verify via
  a manual smoke test description in the PR body — arrow-key interaction
  isn't practically unit-testable through a subprocess pipe).
- Existing REPL behavior (multiline buffering for unterminated statements,
  expression echoing, error reporting) is unchanged — full existing
  `tests/test_repl.py` suite still passes since none of it depends on
  `readline`.
- On a platform/build without `readline` (simulate by temporarily forcing
  the import to fail in a test, or by testing the `except ImportError`
  branch directly), the REPL still starts and runs correctly, just without
  history.
- Full test suite passes.

Likely files: `cinder/repl.py`, `tests/test_repl.py`.

---

## 5. Negative indexing for lists and strings

Build: extend the list branch of `_evaluate_index`/`_evaluate_index_assign`
in `cinder/interpreter.py`, and the string-indexing code merged via PR #16,
to support Python-style negative indices: `-1` means the last element,
`-len(obj)` the first. Normalize a negative index to `len(obj) + index`
before bounds-checking; anything still out of range after normalizing
raises `CinderRuntimeError` in the same style as today's positive-index
errors. Index *assignment* with a negative index on a list mutates the
corresponding positive slot; assigning to any string index (negative or
not) still raises per the string-immutability rule from PR #16.

Acceptance criteria:
- `[1, 2, 3][-1]` is `3`, `[1, 2, 3][-3]` is `1`; `[1, 2, 3][-4]` raises
  `CinderRuntimeError` (out of range) with line/column.
- `"hello"[-1]` is `"o"`, `"hello"[-5]` is `"h"`; `"hello"[-6]` raises
  `CinderRuntimeError` with line/column.
- `[1, 2, 3][-1] = 9` sets the last element to `9`, leaving the rest
  unchanged.
- Existing non-negative indexing behavior is unchanged (regression tests).
- Full test suite passes.

Likely files: `cinder/interpreter.py`, `tests/test_interpreter.py`.

---

## 6. Standard library: `contains` and `reverse`

Build: extend `cinder/builtins.py` with `contains(collection, item)` —
membership check on a list (`==` against each element), a map (checks
keys, not values), or a string (substring check) — returning a `bool`;
and `reverse(list)`, which returns a **new** list with elements in
reverse order and does **not** mutate its input (unlike `push`/`pop`,
which mutate in place — `reverse` follows `split`/`join`'s
returns-something-new style instead; note this distinction in the PR
body so it isn't mistaken for an inconsistency). `contains` raises
`CinderRuntimeError` for any other collection type (int/float/bool/nil);
`reverse` raises `CinderRuntimeError` for any non-list argument. Both
follow the existing arity/type-check style (`_len`, `_str`).

Acceptance criteria:
- `contains([1, 2, 3], 2)` is `true`; `contains([1, 2, 3], 9)` is `false`.
- `contains({"a": 1}, "a")` is `true`; `contains({"a": 1}, "b")` is
  `false` (checks keys, not values).
- `contains("hello", "ell")` is `true`; `contains("hello", "xyz")` is
  `false`.
- `contains(5, 1)` raises `CinderRuntimeError` with line/column.
- `reverse([1, 2, 3])` is `[3, 2, 1]`, and the original list passed in is
  unchanged afterward (regression test proving no mutation).
- `reverse("hi")` raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 7. Standard library: `sort`

Build: extend `cinder/builtins.py` with `sort(list)`, returning a **new**
ascending-sorted list (non-mutating, matching `reverse` from task 6) that
accepts either an all-numeric list (`int`/`float`, compared numerically)
or an all-string list (compared lexicographically). Reject mixed
numeric/string lists and any list containing an unsupported element type
(list, map, bool, nil) with `CinderRuntimeError` and line/column; an empty
list sorts to `[]`. Follow the existing arity/type-check style.

Acceptance criteria:
- `sort([3, 1, 2])` is `[1, 2, 3]`; `sort([2.5, 1.1])` is `[1.1, 2.5]`;
  `sort(["b", "a"])` is `["a", "b"]`.
- `sort([])` is `[]`.
- `sort([1, "a"])` raises `CinderRuntimeError` (mixed types) with
  line/column.
- `sort` on a non-list argument raises `CinderRuntimeError` with
  line/column.
- The list passed to `sort` is unchanged afterward (regression test, same
  non-mutation guarantee as `reverse`).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

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
- **REPL: interactive read-eval-print loop** — merged 2026-07-19T19:46:39Z
  via PR #13 (`feat/20260719-repl`). Built `cinder/repl.py`: reads stdin
  line by line, accumulates input until a statement is complete, executes
  each complete statement against a persistent `Environment`, and echoes
  bare-expression values. Wired `cinder/cli.py`'s `repl` subcommand to it.
  Bounced once on review: `_needs_more_input` treated every `LexError` as
  "unterminated string" and kept buffering forever on an illegal character,
  silently swallowing all further input until EOF with no diagnostic; fixed
  by giving `LexError` an `unterminated: bool` flag set only at the
  unterminated-string sites in `cinder/lexer.py`, so other lex failures now
  fall through to the normal `CinderError` report-and-continue path.

---

- **Standard library: list/map growth and iteration helpers** — merged
  2026-07-19T19:55:16Z via PR #14 (`feat/20260719-list-map-helpers`). Added
  `push`, `pop`, `keys`, `values` builtins to `cinder/builtins.py`, mutating
  the underlying list/dict in place (consistent with existing index-assign
  reference semantics), plus `examples/collections.cin` exercised by the
  golden-output test harness. Reviewer noted a non-blocking nit: the module
  docstring still doesn't mention the new builtins.
- **Fix: `run` leaks raw traceback for missing/unreadable script** — merged
  2026-07-19T20:02:34Z via PR #15 (`fix/20260719-run-file-open`). Catches
  `OSError` around `run_file`'s `open()` and prints a clean one-line
  `cinder: run: <path>: <reason>` diagnostic to stderr with exit code 1,
  instead of leaking a raw Python traceback, for missing/unreadable script
  paths. `CinderError` handling is unchanged.
- **String indexing** — merged 2026-07-19T20:11:00Z via PR #16
  (`feat/20260719-string-indexing`). Extended `_evaluate_index`/
  `_evaluate_index_assign` in `cinder/interpreter.py` so `s[i]` returns a
  length-1 string for a valid `int` index, mirroring list indexing's
  out-of-range/non-int error style; `IndexAssign` on a string raises
  `CinderRuntimeError` explaining strings are immutable instead of
  crashing or silently no-oping.
- **`for`-in loop over lists** — merged 2026-07-20T~06:00Z via PR #17
  (`feat/20260720-for-in-loop`). Added `for NAME in EXPR { ... }` support:
  a `ForStmt` AST node, parser rule reusing block-statement parsing for the
  body, and evaluator support that evaluates the iterable once, raises
  `CinderRuntimeError` for a non-list iterable, and binds the loop variable
  in a fresh child `Environment` per iteration so closures created across
  iterations capture their own value rather than the final one.
  `break`/`continue` intentionally left out (now backlog task 2).

## Graveyard

(none yet)
