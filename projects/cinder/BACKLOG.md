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

## 1. `try`/`catch` for runtime error recovery

Build: add `try { ... } catch (name) { ... }` as a new statement, giving
Cinder scripts a way to recover from a runtime error instead of the whole
program dying — the last major control-flow gap versus `if`/`while`/
`for`-in/`break`/`continue` (see `## Done` for those). Add `TRY`/`CATCH`
keywords to `KEYWORDS` in `cinder/tokens.py` (same pattern as `if`/`while`),
a `TryStmt` AST node (`try_block: Block`, `catch_name: str`,
`catch_block: Block`, line, column) in `cinder/ast_nodes.py`, and parser
support in `cinder/parser.py` reusing the existing block-parsing helper for
both bodies (`try { <stmt>* } catch (name) { <stmt>* }` — the parenthesized
catch name is required, no bare `catch { ... }` form, keep the grammar
small). In `cinder/interpreter.py`, executing a `TryStmt` runs `try_block`
in a child `Environment`; if it raises `CinderRuntimeError`, bind the
error's message (a `str`, matching how `cli.py` already prints
`err.message`) to `catch_name` in a **fresh** child `Environment` and run
`catch_block` against it, then continue after the `TryStmt` normally (the
error does not propagate further). Only `CinderRuntimeError` is caught —
`LexError`/`ParseError` happen before execution starts and are irrelevant
here; `_BreakSignal`/`_ContinueSignal`/`_ReturnSignal` (Python-internal
control-flow signals, not `CinderRuntimeError`) must NOT be caught, so
`break`/`continue`/`return` inside a `try` block still propagate through it
exactly as they do through `if`/blocks today — do not add a broad `except
CinderError` or bare `except`. If `catch_block` itself raises, that
propagates normally (no re-catch).

Acceptance criteria:
- `try { let x = 1 / 0; } catch (e) { print(e); }` prints the division's
  error message instead of crashing the program.
- After a caught error, execution continues past the `try`/`catch`
  statement (a statement following it still runs).
- `try { 1; } catch (e) { print("unreached"); }` never runs the catch block
  when no error occurs.
- `catch_name` (`e` above) is scoped to the catch block only — referencing
  it after the `try`/`catch` statement raises the normal "undefined
  variable" `CinderRuntimeError`.
- `for x in [1] { try { break; } catch (e) {} }` still exits the loop —
  `break` inside `try` is not swallowed as a caught error.
- A `return` inside a function body's `try` block still returns from the
  function, not just the `try` statement.
- `LexError`/`ParseError` are unaffected (still uncaught, unrelated to
  `try`/`catch`, which only runs at execution time).
- An error raised inside `catch_block` itself is not re-caught — it
  propagates normally.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.

---

## 2. Standard library: `chunk` for lists

Build: add `chunk(list, size)` to `cinder/builtins.py`, splitting `list`
into consecutive sublists of length `size` (the last sublist may be
shorter if `len(list)` doesn't divide evenly), non-mutating, matching
`slice`/`concat`/`flatten`'s type-check style. `size` must be a positive
`int`; `size <= 0` raises `CinderRuntimeError` with line/column (no
infinite-sublists or divide-by-zero ambiguity, and this check applies
before looking at the list's contents, so it fires even for an empty
list). First argument must be `list`.

Acceptance criteria:
- `chunk([1, 2, 3, 4, 5], 2)` is `[[1, 2], [3, 4], [5]]` (uneven
  remainder gets its own shorter sublist).
- `chunk([1, 2, 3, 4], 2)` is `[[1, 2], [3, 4]]` (evenly divides).
- `chunk([1, 2, 3], 1)` is `[[1], [2], [3]]`.
- `chunk([], 3)` is `[]` (empty list, valid size, no error).
- `chunk([1, 2, 3], 0)` raises `CinderRuntimeError` with line/column
  (non-positive size).
- `chunk([1, 2, 3], -1)` raises `CinderRuntimeError` with line/column.
- `chunk(5, 2)` raises `CinderRuntimeError` with line/column (non-list
  first argument).
- `chunk([1, 2, 3], "2")` raises `CinderRuntimeError` with line/column
  (non-int size).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Standard library: `partition` for lists

Build: add `partition(list, fn)` to `cinder/builtins.py`, splitting `list`
into `[matching, non_matching]` — two new lists, in original relative
order — based on `fn(element)`'s Cinder truthiness (`is_truthy`, the same
helper `filter`/`any`/`all` already use), called once per element via the
shared `call_value` helper (`map`/`filter`/`sort_by`/`group_by`'s pattern).
This is `group_by`'s two-bucket sibling — factor a shared helper out of
`_group_by` and `_partition` if that keeps the diff clean, but don't block
on `group_by` landing first; if it hasn't yet, implement `partition`
standalone against `call_value`/`is_truthy` directly. First argument must
be `list`, second must be callable, matching `map`/`filter`'s type-check
style.

Acceptance criteria:
- `partition([1, 2, 3, 4, 5, 6], fn(n) { n % 2 == 0 })` is
  `[[2, 4, 6], [1, 3, 5]]` (matching first, non-matching second, original
  relative order preserved in each).
- `partition([], fn(n) { n })` is `[[], []]` (empty list, `fn` never
  called).
- `partition([1, 2, 3], fn(n) { true })` is `[[1, 2, 3], []]`;
  `partition([1, 2, 3], fn(n) { false })` is `[[], [1, 2, 3]]`.
- `partition([0, "", 1, "a"], fn(x) { x })` uses Cinder truthiness, not
  Python's — `0` and `""` are truthy in Cinder, so this is
  `[[0, "", 1, "a"], []]`.
- `partition(5, fn(n) { n })` raises `CinderRuntimeError` with line/column
  (non-list first argument).
- `partition([1, 2], 5)` raises `CinderRuntimeError` with line/column
  (non-callable second argument).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. Default parameter values: `fn f(a, b = 1) { ... }`

Build: let a function/lambda parameter carry a default expression, evaluated
at call time (not definition time) when the caller omits that argument.
`_fn_params_and_body` in `cinder/parser.py` (shared by `_fn_declaration` and
`_fn_expression` — both `FnDecl` and `FnExpr` go through it) currently parses
`params` as a plain `list[str]`; change each entry to a `(name: str,
default: Expr | None)` pair, parsing an optional `= <ternary-level
expression>` after the parameter name (same precedence tier `_map_pair`'s
value and `_list_literal`'s elements already use — do not pull in the full
comma-containing `_assignment()` grammar, since a bare `,` there would be
ambiguous with the next parameter). Once any parameter has a default, every
parameter after it must also have one — enforce this in the parser, raising
`ParseError` at the offending parameter's token, mirroring how Python
rejects non-default-after-default. `CinderFunction.arity` in
`cinder/interpreter.py` (currently `len(self.decl.params)`) becomes a
*minimum* arity — the property should return the count of parameters
*without* a default; `call_value`'s arity check changes from `len(arguments)
!= callee.arity` to a range check (`len(arguments) < min_arity or
len(arguments) > len(params)`), and the call-binding loop evaluates each
missing trailing parameter's default expression (against `call_env`, so a
later default can reference an earlier parameter, e.g. `fn f(a, b = a) {
}`) instead of zipping only supplied arguments. Builtins are unaffected —
this task only touches `CinderFunction`/`FnDecl`/`FnExpr`.

Acceptance criteria:
- `fn greet(name, greeting = "hi") { return greeting + " " + name; }`:
  `greet("Bo")` is `"hi Bo"`; `greet("Bo", "hey")` is `"hey Bo"`.
- `fn f(a, b = a + 1) { return b; }`; `f(5)` is `6` (later default sees
  earlier parameter's bound value).
- Too few arguments to cover all non-default parameters still raises
  `CinderRuntimeError` with line/column and a message stating the expected
  range (e.g. `f() expects at least 1 argument(s), got 0`).
- Too many arguments (more than the full parameter list) still raises
  `CinderRuntimeError` with line/column.
- `fn f(a = 1, b) { }` raises `ParseError` at `b` (non-default parameter
  after a default one).
- A default expression is re-evaluated on every call that needs it, not
  cached — `let counter = 0; fn f(a = counter) { counter += 1; return a; }`
  called twice returns `0` then `1` (this behavior may already fall out of
  "evaluated at call time"; just don't special-case caching in).
- Anonymous `fn(a, b = 2) { ... }` (an `FnExpr`, e.g. passed to `map`)
  supports defaults identically to named `fn` declarations.
- Full test suite passes.

Likely files: `cinder/parser.py`, `cinder/ast_nodes.py`,
`cinder/interpreter.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.

---

## 5. Block comments: `/* ... */`

Build: extend `Lexer._skip_whitespace_and_comments` in `cinder/lexer.py`
(currently handles only `#`-to-end-of-line comments) to also recognize a
`/*` prefix and skip everything up to and including the matching `*/`,
tracking newlines inside the comment so `line`/`column` tracking for
tokens *after* the comment stays correct (reuse whatever line-increment
logic `_advance()`/the string-literal scanner already applies for
embedded `\n`). Block comments do **not** nest — the first `*/` found
closes the comment, matching C/Java/JS, not Rust. An unterminated block
comment (`/*` with no matching `*/` before EOF) raises `LexError` with the
line/column of the opening `/*`, mirroring the existing unterminated-string
error (set the same `unterminated: bool` flag introduced in PR #13 so the
REPL's multi-line continuation logic in `cinder/repl.py` treats an
in-progress block comment as "needs more input" rather than a hard error —
check `_needs_more_input` in `repl.py` before assuming this is free).
Plain `/` (division) and `/=` must still lex correctly when not followed by
`*` — this only adds one more lookahead case alongside the existing
`SLASH`/`SLASHEQ` disambiguation.

Acceptance criteria:
- `/* comment */ print(1);` runs and prints `1`.
- `print(1); /* trailing */` runs and prints `1`.
- A block comment spanning multiple lines doesn't corrupt line numbers —
  an error raised on the line *after* a multi-line block comment reports
  the correct line, not one shifted by the comment's line count.
- `1 /* comment */ + 2` still parses as `1 + 2` (comment acts as
  whitespace between tokens).
- `10 / 2` and `x /= 2` still lex correctly (division/compound-assign
  unaffected by the new `/*` lookahead).
- `/* unterminated` (no closing `*/`) raises `LexError` with the line/column
  of the opening `/*`, not a silent hang or an error at EOF with no
  location.
- `# /* not a block comment */` — a `#` line comment containing `/*` text
  is still just skipped to end-of-line as before (block-comment detection
  only triggers when `/*` starts outside of another comment).
- Full test suite passes.

Likely files: `cinder/lexer.py`, `cinder/repl.py`, `tests/test_lexer.py`.

---

## 6. Standard library: `insert` and `remove_at` for lists

Build: add `insert(list, index, value)` and `remove_at(list, index)` to
`cinder/builtins.py`, filling the gap between `push`/`pop` (end-only) and
map's `remove` (key-based, not positional) — Cinder currently has no way to
add or remove a list element at an arbitrary position. Both mutate the
underlying list in place and return `nil` (`insert`) or the removed element
(`remove_at`), consistent with `push`/`pop`'s existing in-place-mutation
style (not `slice`/`concat`/`reverse`'s copy style). `index` supports the
same negative-index normalization already shared by `_evaluate_index`/
`slice()`/`_evaluate_slice` (reuse `_normalize_slice_bound` or the
non-slice negative-index helper `_evaluate_index` uses — do not
reimplement the normalization). `insert`'s valid range is `0` to
`len(list)` inclusive (append-at-end via `insert(list, len(list), v)` is
legal, matching Python's `list.insert`); `remove_at`'s valid range is `0`
to `len(list) - 1` (an empty list has no valid index). Out-of-range or
non-int `index`, or a non-list first argument, raises `CinderRuntimeError`
with line/column, matching `push`/`pop`'s type-check style.

Acceptance criteria:
- `let l = [1, 2, 3]; insert(l, 1, 99); l` is `[1, 99, 2, 3]`.
- `let l = [1, 2, 3]; insert(l, 0, 99); l` is `[99, 1, 2, 3]` (insert at
  front).
- `let l = [1, 2, 3]; insert(l, 3, 99); l` is `[1, 2, 3, 99]` (insert at
  `len(list)`, i.e. append).
- `let l = [1, 2, 3]; insert(l, -1, 99); l` is `[1, 2, 99, 3]` (negative
  index normalizes the same way indexing/slicing do).
- `let l = [1, 2, 3]; remove_at(l, 1)` returns `2` and leaves `l` as
  `[1, 3]`.
- `let l = [1, 2, 3]; remove_at(l, -1)` returns `3` and leaves `l` as
  `[1, 2]` (negative index).
- `insert([1, 2], 5, 0)` raises `CinderRuntimeError` with line/column
  (index out of range).
- `remove_at([], 0)` raises `CinderRuntimeError` with line/column (empty
  list, no valid index).
- `insert([1, 2], "0", 9)` / `remove_at([1, 2], "0")` raise
  `CinderRuntimeError` with line/column (non-int index).
- `insert(5, 0, 9)` / `remove_at(5, 0)` raise `CinderRuntimeError` with
  line/column (non-list first argument).
- Wrong arity raises `CinderRuntimeError` with line/column for both.
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
  `break`/`continue` intentionally left out (shipped separately, PR #19).
- **Standard library: string methods** — merged 2026-07-20T14:29:19Z via
  PR #18 (`feat/20260720-string-methods`). Added `upper(s)`, `lower(s)`,
  `trim(s)`, `split(s, sep)`, and `join(list, sep)` to `cinder/builtins.py`,
  arity/type-checked the same way as `_len`/`_str`. Bounced once: `_split`
  let Python's `ValueError: empty separator` (from `str.split("")`) escape
  as a raw traceback instead of a `CinderRuntimeError`; fixed by rejecting
  an empty separator explicitly before calling `.split()`, matching the
  `_int`/`_float` exception-conversion pattern.
- **`break` and `continue` for loops** — merged 2026-07-20T14:44:02Z via
  PR #19 (`feat/20260720-break-continue`). Added `BreakStmt`/`ContinueStmt`
  AST nodes, parser support restricted to loop bodies via a `_loop_depth`
  counter mirroring `_fn_depth`'s handling of `return` (reset across
  function boundaries so `break`/`continue` can't leak out of a nested
  function to an outer loop), and interpreter support via
  `_BreakSignal`/`_ContinueSignal` caught at each loop's own execution site.
- **Standard library: math builtins (`abs`, `min`, `max`, `round`)** — merged
  2026-07-20T14:55:19Z via PR #20 (`feat/20260720-math-builtins`). Added
  `abs(n)`, `min(...)`/`max(...)` (variadic, one or more numeric arguments),
  and `round(n)` (ties-to-even, delegating to Python's built-in `round`) to
  `cinder/builtins.py`. `min`/`max` reject zero arguments with a dedicated
  inline variadic check since `_require_arity` only handles fixed arity.
- **REPL: command history via `readline`** — merged 2026-07-21T~00:00Z via
  PR #21 (`feat/20260720-repl-readline`). Added `_try_enable_readline()` to
  `cinder/repl.py`, called once at `run_repl()` startup, guarded with
  `try`/`except ImportError` so the REPL still starts without `readline`
  (e.g. stock Windows Python). No persistent history-file save/load —
  in-session history only, per the task's "keep it small" instruction.
- **Negative indexing for lists and strings** — merged 2026-07-21T~13:16Z via
  PR #22 (`feat/20260720-negative-indexing`). Extended `_evaluate_index`/
  `_evaluate_index_assign` in `cinder/interpreter.py` to normalize a negative
  index to `len(obj) + index` before bounds-checking, Python-style, for list
  read/assign and string read; string index-assignment still raises for
  immutability regardless of sign, per PR #16.

- **Standard library: `contains` and `reverse`** — merged 2026-07-21T~13:30Z
  via PR #23 (`feat/20260720-contains-reverse`). Added
  `contains(collection, item)` (list `==` membership, map key check, string
  substring check, `CinderRuntimeError` for other types) and `reverse(list)`
  (returns a new list, non-mutating, matching `split`/`join`'s style rather
  than `push`/`pop`'s in-place style) to `cinder/builtins.py`. Clean first
  pass, no bounces (277 tests passing, up from 268).

- **Standard library: `sort`** — merged 2026-07-20T20:03:01Z via PR #24
  (`feat/20260720-sort-builtin`). Added `sort(list)` to `cinder/builtins.py`,
  returning a new ascending-sorted list (non-mutating, matching `reverse`'s
  style) for all-numeric or all-string lists; mixed-type lists, unsupported
  element types, and non-list arguments raise `CinderRuntimeError` with
  line/column. Clean first pass, no bounces (285 tests passing, up from
  277).

- **`for`-in loop over strings and maps** — merged 2026-07-21T~14:00Z via
  PR #25 (`feat/20260720-for-in-str-map`). Extended `_execute_for` in
  `cinder/interpreter.py` to accept a string (iterates character-by-
  character) and a map (iterates over keys, matching `contains`/`keys`
  convention) in addition to lists; any other type still raises
  `CinderRuntimeError` with line/column. Clean first pass, no bounces
  (289 tests passing, up from 285).

- **Standard library: `range`** — merged 2026-07-20T20:22:20Z via PR #26
  (`feat/20260720-range-builtin`). Added `range(stop)` and `range(start,
  stop)` to `cinder/builtins.py`, eagerly materializing a `list` of ints
  (no lazy iterator type exists in Cinder), int-only arguments, and
  `stop <= start` returning `[]` rather than erroring, matching Python.
  Clean first pass, no bounces (300 tests passing, up from 289).

- **Standard library: `map` and `filter`** — merged 2026-07-21T~13:52Z via
  PR #27 (`feat/20260720-map-filter`). Extracted a shared module-level
  `call_value(callee, arguments, line, column)` helper out of
  `Interpreter._evaluate_call` in `cinder/interpreter.py` (behavior-preserving
  refactor), then added `map(list, fn)` and `filter(list, fn)` to
  `cinder/builtins.py` on top of it, both non-mutating and accepting a
  `CinderFunction` or `Builtin` callback. Also added anonymous function
  *expressions* (`fn(params) { body }` usable as a value, not just the
  existing named statement-level `fn NAME(params) { ... }`) via a new
  `FnExpr` AST node, since the task's acceptance criteria required passing a
  bare `fn(x) { ... }` literal as a call argument. Clean first pass, no
  bounces (320 tests passing, up from 300).

- **Standard library: `reduce`** — merged 2026-07-21T~14:07Z via PR #28
  (`feat/20260721-reduce-builtin`). Added `reduce(list, fn, initial)` to
  `cinder/builtins.py`, folding a list left-to-right via the shared
  `call_value` helper (from PR #27); non-list first argument or non-callable
  second argument raises `CinderRuntimeError` with line/column, matching
  `map`/`filter`'s type-check style, and an empty list returns `initial`
  without calling `fn`. Clean first pass, no bounces (327 tests passing, up
  from 320).

- **Standard library: `find`, `starts_with`, `ends_with`, `replace`** —
  merged 2026-07-21T~14:16Z via PR #29 (`feat/20260721-string-find-replace`).
  Added the four two-string-argument builtins to `cinder/builtins.py`
  following `split`/`join`'s style: `find` matches Python's `str.find`
  semantics (`-1` on no match), `starts_with`/`ends_with` return `bool`,
  and `replace` replaces all non-overlapping occurrences, keeping Python's
  per-character-insert behavior for an empty `old` rather than special-casing
  it. Each rejects non-`str` arguments and wrong arity with
  `CinderRuntimeError` and line/column. Clean first pass, no bounces
  (347 tests passing, up from 327).

- **Standard library: `slice` and `concat` for lists** — merged
  2026-07-21T14:26:12Z via PR #30 (`feat/20260721-slice-concat`). Added
  `slice(list, start, end)` (Python-slice-style, negative bounds normalized
  via the `_evaluate_index` rule, out-of-range bounds clamp instead of
  erroring, `start`/`end` must be `int`) and `concat(list1, list2)`
  (non-mutating list concatenation) to `cinder/builtins.py`. Non-list first
  argument raises `CinderRuntimeError` with line/column. Clean first pass,
  no bounces (357 tests passing, up from 347).

- **Standard library: `assert`** — merged 2026-07-21T~14:35Z via PR #31
  (`feat/20260721-assert-builtin`). Added `assert(condition, message)` to
  `cinder/builtins.py`, raising `CinderRuntimeError` with the message and
  the call's line/column when `condition` is falsy per Cinder's existing
  truthiness rule (so `0`/`""` don't trigger it), and returning `nil`
  otherwise; `message` must be a `str`, checked before the truthiness test.
  Added `examples/self_check.cin` exercised by the golden-output test
  harness. Clean first pass, no bounces (362 tests passing, up from 357).

- **Compound assignment operators: `+=`, `-=`, `*=`, `/=`, `%=`** — merged
  2026-07-21T14:45:45Z via PR #32 (`feat/20260721-compound-assign`). Added
  five compound-assignment token types to `cinder/tokens.py`, lexed via the
  existing two-char lookahead pattern in `cinder/lexer.py`, and desugared
  at parse time in `cinder/parser.py`'s `_assignment` into the equivalent
  `Assign(name, Binary(...))`, reusing `_evaluate_binary`'s existing
  type-checking with no new interpreter logic. Restricted to `Identifier`
  targets; `list[0] += 1` raises `ParseError`, matching plain `=`. Clean
  first pass, no bounces (378 tests passing, up from 362).

- **Standard library: `zip`** — merged 2026-07-22T~ via PR #33
  (`feat/20260721-zip-builtin`). Added `zip(list1, list2)` to
  `cinder/builtins.py`, pairing two lists into `[[a, b], ...]` truncated to
  the shorter length (Python `zip` semantics), non-mutating, matching
  `reverse`/`sort`/`map`/`filter`'s style; non-list argument raises
  `CinderRuntimeError` with line/column. Clean first pass, no bounces
  (383 tests passing, up from 378).
- **String and list repetition via `*`** — merged 2026-07-22T~ via PR #34
  (`feat/20260721-star-repeat`). Extended the `STAR` binary-op case in
  `cinder/interpreter.py` to support `str * int`/`int * str` and
  `list * int`/`int * list` with Python repetition semantics (zero/negative
  count clamps to empty, no error); non-int count falls through to the
  existing `_numeric_op` type check and raises `CinderRuntimeError`. Clean
  first pass, no bounces (393 tests passing, up from 383).
- **`in` operator for membership tests** — merged 2026-07-22T~ via PR #35
  (`feat/20260721-in-operator`). Added a new precedence tier in
  `cinder/parser.py` between `_and` and `_comparison` wiring the existing
  `IN` token into expression parsing as `expr in expr`, without touching
  `for`-loop grammar. Factored `_contains`'s type dispatch out of
  `cinder/builtins.py` into a shared `contains_value()` helper in
  `cinder/interpreter.py`, used by both `contains()` and the new `in`
  operator. Clean first pass, no bounces (405 tests passing, up from 393).
- **Runtime errors report the call stack, not just the innermost site** —
  merged 2026-07-22T~ via PR #36 (`feat/20260721-callstack-frames`). Gave
  `CinderRuntimeError` a `frames` list in `cinder/errors.py`, appended to
  by `interpreter.py`'s `call_value` as the exception unwinds through
  nested `CinderFunction` calls (innermost first), and printed as
  `  at name (line:col)` lines in `cinder/cli.py`'s diagnostic after the
  existing one-line header. Clean first pass, no bounces (413 tests
  passing, up from 405).
- **Standard library: `sum`, `any`, `all`** — merged 2026-07-21T20:18:37Z
  via PR #37 (`feat/20260721-sum-any-all`). Added three variadic-over-a-
  list aggregate builtins to `cinder/builtins.py`: `sum(list)` totals
  numeric elements via `+` (int-only result if every element was `int`,
  else `float`, mirroring Python's own `sum()` promotion), `any(list)`/
  `all(list)` evaluate each element's Cinder truthiness via `is_truthy`.
  Non-numeric element or non-list argument raises `CinderRuntimeError`
  with line/column. Clean first pass, no bounces (426 tests passing, up
  from 413).

- **Standard library: `items` for maps** — merged 2026-07-22T~ via PR #39
  (`feat/20260722-items-for-maps`). Added `items(map)` to
  `cinder/builtins.py`, returning `[key, value]` pairs in insertion order,
  complementing `keys`/`values` (same non-mutating, single-`map`-argument
  style). Clean first pass, no bounces (452 tests passing).

- **Standard library: `enumerate`** — merged 2026-07-22T14:37:25Z via PR #40
  (`feat/20260722-enumerate-builtin`). Added `enumerate(list)` to
  `cinder/builtins.py`, pairing each element with its `0`-based index as
  `[index, value]` lists, mirroring `zip`/`items`'s non-mutating style; a
  regression test ties it to `zip(range(len(l)), l)`. Clean first pass, no
  bounces (458 tests passing, up from 452).

- **Standard library: `merge` for maps** — merged 2026-07-22T~ via PR #41
  (`feat/20260722-merge-builtin`). Added `merge(map1, map2)` to
  `cinder/builtins.py`, returning a new map with `map2`'s values winning
  on key conflicts and `map1`-then-`map2` key ordering, non-mutating
  (matching `items`/`keys`'s type-check style). Clean first pass, no
  bounces (465 tests passing, up from 458).

- **Standard library: `get` for safe map access** — merged 2026-07-22T~ via
  PR #42 (`feat/20260722-get-builtin`). Added `get(map, key, default)` to
  `cinder/builtins.py`, returning `map[key]` if present else `default`,
  never raising for a missing key (unlike `map[key]` indexing); non-map
  first argument and unhashable-key second argument raise
  `CinderRuntimeError` with line/column, reusing the existing map-index
  path's wording.

- **Standard library: `copy` for lists and maps** — merged 2026-07-22T~ via
  PR #43 (`feat/20260722-copy-builtin`). Added `copy(collection)` to
  `cinder/builtins.py`, returning a new top-level shallow copy of a list
  or map (nested containers stay shared, matching Python's
  `list.copy()`/`dict.copy()`), giving Cinder a way to intentionally break
  the aliasing `push`/`pop`/index-assign rely on. Clean first pass, no
  bounces (477 tests passing, up from 465).

- **Standard library: math builtins (`floor`, `ceil`, `pow`, `sqrt`)** —
  merged 2026-07-23T~ via PR #48 (`feat/20260722-math-builtins-2`). Added
  `floor(n)`/`ceil(n)` (delegate to `math.floor`/`math.ceil`), `pow(base,
  exp)` (delegates to Python's `**` for int/float promotion), and `sqrt(n)`
  (delegates to `math.sqrt`, raises `CinderRuntimeError` for negative input
  since Cinder has no complex numbers) to `cinder/builtins.py`. Bounced once:
  `_pow` let a negative base with a fractional exponent silently return a
  Python `complex`, and let `ZeroDivisionError`/`OverflowError` from
  `base ** exp` escape as raw Python tracebacks instead of
  `CinderRuntimeError`; fixed with a `complex`-result guard and a
  try/except around the exponentiation (557 tests passing, up from 542).

- **Standard library: `index_of` for lists** — merged 2026-07-23T~ via
  PR #49 (`feat/20260723-index-of`). Added `index_of(list, item)` to
  `cinder/builtins.py`, returning the `int` index of the first element
  equal to `item` (Cinder `==` value equality) or `-1` if not found — the
  list counterpart to the existing `find` for strings. Clean first pass,
  no bounces (542 tests passing).

- **Standard library: `unique` for lists** — merged 2026-07-23T14:32Z via
  PR #50 (`feat/20260723-unique-builtin`). Added `unique(list)` to
  `cinder/builtins.py`: a `set`-backed fast path when every element is
  hashable, falling back to a linear `==` scan otherwise (matching
  `sort`/`contains`'s existing unhashable-element limitation). Bounced
  once on QA: the fast path's bare Python `set()` conflated `bool` with
  `int` (`1 == True`), diverging from Cinder's own `==` operator; fixed by
  keying the set on `(isinstance(element, bool), element)` and switching
  the fallback scan to `interpreter._values_equal`. Surfaced the same
  latent bug in `contains`/`index_of`/`in`, tracked separately and fixed
  below. 574 tests passing, up from 572.

- **Fix: `contains`, `index_of`, and `in` conflate `bool` with `int`** —
  merged 2026-07-23T~ via PR #51 (`fix/20260723-bool-int-eq`). Renamed
  `Interpreter`'s `_values_equal` to `values_equal` (dropped leading
  underscore, exported alongside `contains_value`) and used it in place of
  raw Python `==` in `contains_value`'s list branch (`cinder/interpreter.py`,
  backs `contains()`/`in`) and `_index_of`'s scan (`cinder/builtins.py`), so
  both agree with `==` on bool-vs-int. Left `contains_value`'s dict-key
  branch (native `key in dict`) alone — fixing bool/int map-key collisions
  needs a bigger change to how map keys are stored. Clean first pass, no
  bounces (577 tests passing, up from 574).

- **Standard library: `count` for lists** — merged 2026-07-23T14:54:08Z via
  PR #52 (`feat/20260723-cinder-count`). Added `count(list, item)` to
  `cinder/builtins.py`, returning the `int` number of elements equal to
  `item` via `values_equal()` (so it correctly inherits the bool/int fix
  from #51) — the counting counterpart to `index_of`, which only reports
  the first match. Clean first pass, no bounces (585 tests passing, up
  from 577).
- **Standard library: `flatten` for lists** — merged 2026-07-23T15:05:12Z via
  PR #53 (`feat/20260723-flatten-lists`). Added `flatten(list)` to
  `cinder/builtins.py`, flattening exactly one level of list-of-lists
  nesting into a new list (non-mutating, matching `concat`/`slice`'s
  type-check style) — non-list top-level elements pass through unchanged.
  Clean first pass, no bounces (592 tests passing, up from 585).

- **Standard library: `format` for string templating** — merged
  2026-07-23T~ via PR #54 (`feat/20260723-format-builtin`). Added
  `format(template, ...)` to `cinder/builtins.py`, a minimal sprintf-style
  templating builtin (variadic like `min`/`max`, two-pass scan validating
  brace pairs and placeholder count before substituting via `stringify()`).
  Mismatched placeholder/argument counts, a stray `{` not part of a `{}`
  pair, a non-`str` template, and a zero-arg call all raise
  `CinderRuntimeError` with line/column. Clean first pass, no bounces
  (601 tests passing, up from 592).
- **REPL: persistent command history across sessions** — merged
  2026-07-23T15:28:03Z via PR #55 (`feat/20260723-repl-history`). Extended
  `_try_enable_readline()` in `cinder/repl.py` to load history from
  `projects/cinder/.cinder_history` on startup and added `_save_history()`
  to write it back on any clean exit, wrapped in `try`/`finally` around
  `run_repl()`'s main loop; both load and save are guarded with `except
  OSError`, matching the existing `except ImportError` fallback style.
  History file is gitignored and scoped inside the project directory.
  Clean first pass, no bounces (606 tests passing, up from 601).
- **List slicing syntax: `list[start:end]`** — merged 2026-07-23T15:44:24Z via
  PR #56 (`feat/20260723-list-slicing`). Added a `SliceExpr` AST node and
  extended `_finish_index` in `cinder/parser.py` to parse an optional `:`
  inside `expr[...]`, falling back to plain indexing when absent; evaluated
  in `cinder/interpreter.py` via a new `_evaluate_slice` sharing bound
  normalization/clamping with the existing `slice()` builtin (deduped the
  now-shared `_normalize_slice_bound` out of `cinder/builtins.py`). Only
  `list`/`str` are sliceable; slices aren't assignable (falls through to the
  existing invalid-assignment-target error). Clean first pass, no bounces
  (623 tests passing).
- **Standard library: `group_by` for lists** — merged 2026-07-23T19:25:03Z via
  PR #57 (`feat/20260723-group-by`). Added `group_by(list, fn)` to
  `cinder/builtins.py`, partitioning elements into a `map` keyed by
  `fn(element)`, reusing `call_value` and `_is_valid_key` from the existing
  `map`/`filter`/`sort_by`/`get` paths; a non-hashable key raises
  `CinderRuntimeError`. Clean first pass, no bounces (633 tests passing).

## Graveyard

(none yet)
