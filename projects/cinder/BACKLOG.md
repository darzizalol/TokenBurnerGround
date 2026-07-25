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

## 1. Numeric literals: hexadecimal, binary, and octal integers

Build: extend `cinder/lexer.py`'s number-scanning to recognize `0x`/`0X`
(hex), `0b`/`0B` (binary), and `0o`/`0O` (octal) prefixed integer literals in
addition to today's decimal-only scanning, producing an ordinary `NUMBER`
token whose value is the parsed Python `int` (no downstream AST/parser/
interpreter change needed — the literal node already just carries whatever
numeric value the lexer hands it). Only apply the prefix check when a digit
run starts with `0` followed immediately by `x`/`b`/`o` (case-insensitive); a
bare `0` or `0` followed by more decimal digits (`0`, `07`) keeps the
existing decimal-literal path unchanged (Cinder has no octal-by-leading-zero
surprise, unlike C). Reject an empty digit run after the prefix (`0x` alone)
and any digit outside the base's alphabet (`0x1G`, `0b12`, `0o8`) as a
`LexError` with line/column pointing at the literal's start. These literals
are integer-only — no `0x1.5` float form.

Acceptance criteria:
- `0x1F` lexes/evaluates to `31`; `0xff` to `255`.
- `0b1010` lexes/evaluates to `10`.
- `0o17` lexes/evaluates to `15`.
- `0` and `007` still lex as decimal `0` and `7` respectively (unchanged, no
  octal-by-leading-zero).
- `0x` alone (no digits after the prefix) raises `LexError` with
  line/column.
- `0x1G`, `0b12`, `0o8` (digit outside the base's alphabet) raise `LexError`
  with line/column.
- Hex/binary/octal literals work anywhere a number literal already does:
  arithmetic (`0xFF + 1` is `256`), comparisons, list indices, function
  arguments.
- Existing decimal integer/float literal tests are unaffected.
- Full test suite passes.

Likely files: `cinder/lexer.py`, `tests/test_lexer.py`,
`tests/test_interpreter.py`.

---

## 2. Standard library: `find_index` for lists

Build: add `find_index(list, fn)` to `cinder/builtins.py` — returns the
`int` index of the first element for which `fn(element)` is truthy (via the
shared `call_value` helper and Cinder's truthiness rule, matching `filter`/
`partition`'s predicate style), or `-1` if no element matches (short-
circuits — doesn't call `fn` on elements after the first match).
Complements the existing `index_of` (which finds by `==` equality) the same
way `filter` complements `contains`: a predicate-based search for when
equality isn't enough (e.g. "first even number", "first string longer than
3 characters").

Acceptance criteria:
- `find_index([1, 2, 3, 4], fn(n) { n > 2 })` is `2` (0-based index of `3`).
- `find_index([1, 2, 3], fn(n) { n > 10 })` is `-1` (no match).
- `find_index([], fn(n) { n })` is `-1` (empty list, `fn` never called).
- Short-circuits: `fn` is not called for elements after the first match
  (verify via a counter closure or side-effecting list in a test).
- `find_index(5, fn(n) { n })` raises `CinderRuntimeError` with line/column
  (non-list first argument).
- `find_index([1, 2], 5)` raises `CinderRuntimeError` with line/column
  (non-callable second argument).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Standard library: `flatten_deep` for lists

Build: add `flatten_deep(list)` to `cinder/builtins.py` — recursively
flattens list-of-lists nesting at every depth into a single new list, the
fully-recursive counterpart to the existing `flatten` (which only flattens
one level, PR #53). Reuse `flatten`'s non-list-elements-pass-through
behavior at each level rather than duplicating it; implement recursively
(or with an explicit stack) so an empty nested list `[[], 1]` contributes
nothing rather than erroring. Non-mutating, matching `flatten`/`concat`'s
type-check style.

Acceptance criteria:
- `flatten_deep([1, [2, 3], [4, [5, 6]]])` is `[1, 2, 3, 4, 5, 6]`.
- `flatten_deep([[[1]], [[2]]])` is `[1, 2]` (arbitrary depth).
- `flatten_deep([1, 2, 3])` is `[1, 2, 3]` (no nesting, unchanged).
- `flatten_deep([[], 1, []])` is `[1]` (empty nested lists contribute
  nothing).
- `flatten_deep([])` is `[]`.
- `flatten_deep(5)` raises `CinderRuntimeError` with line/column (non-list
  argument).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. Standard library: `min_by` and `max_by` for lists

Build: add `min_by(list, fn)` and `max_by(list, fn)` to `cinder/builtins.py`
— like `min`/`max` but selecting the element whose `fn(element)` result is
smallest/largest, via the shared `call_value` helper (matching `sort_by`/
`group_by`'s callback style), rather than comparing elements directly.
Complements `sort_by` (which orders the whole list by a key) for the common
"just give me the best one" case that otherwise requires
`sort_by(list, fn)[0]` (wasteful full sort) or a manual `reduce` loop.

Acceptance criteria:
- `min_by([3, 1, 2], fn(n) { n })` is `1`; `max_by([3, 1, 2], fn(n) { n })`
  is `3`.
- `min_by(["ccc", "a", "bb"], fn(s) { len(s) })` is `"a"` (shortest string).
- On ties (equal `fn` results), the *first* matching element wins for both
  (stable, matching Python's `min`/`max` tie-break).
- `min_by([], fn(n) { n })` and `max_by([], fn(n) { n })` raise
  `CinderRuntimeError` with line/column (empty list — no well-defined
  answer, matching `min`/`max`'s zero-argument rejection).
- `min_by(5, fn(n) { n })` raises `CinderRuntimeError` with line/column
  (non-list first argument).
- `min_by([1, 2], 5)` raises `CinderRuntimeError` with line/column
  (non-callable second argument).
- Wrong arity raises `CinderRuntimeError` with line/column.
- `fn`'s results must be comparable with `<` (numbers or strings, matching
  `sort`'s type restriction); comparing incompatible or mixed types raises
  `CinderRuntimeError`.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 5. Standard library: value-based removal for lists via `remove`

Build: extend the existing `remove` builtin (`cinder/builtins.py`, today
map-only: `remove(map, key)`) to also accept a `list` as its first
argument, dispatching on the argument's type the same way `contains`
already dispatches across list/map/string — for a list, `remove(list,
value)` deletes and discards the *first* element equal to `value` (via
the shared `values_equal` helper, so it agrees with `==`/`contains`/
`index_of` on bool-vs-int per PR #51), mutating the list in place and
returning the removed value, matching `pop`/`remove_at`'s in-place style
and the existing map behavior's raise-on-missing style. Fills the last
gap in the list-removal trio: `pop` (end), `remove_at` (by index),
`remove` (by value) — today removing by value requires `index_of` +
`remove_at` as two separate calls. Non-list, non-map first argument keeps
today's `remove() requires a map, got ...` error but reworded to mention
both accepted types.

Acceptance criteria:
- `let l = [1, 2, 3]; remove(l, 2); l` is `[1, 3]`.
- `remove(l, value)` on a list returns the removed value (`2` above).
- Only the *first* matching element is removed: `remove([1, 2, 1], 1)`
  leaves `[2, 1]`.
- `remove([1, 2], 5)` raises `CinderRuntimeError` with line/column (value
  not found in list — no silent no-op).
- Existing map behavior (`remove(map, key)`) is unchanged, including its
  missing-key and invalid-key errors — add a regression test pinning this.
- `remove(5, 1)` raises `CinderRuntimeError` with line/column (neither
  list nor map first argument).
- Wrong arity raises `CinderRuntimeError` with line/column.
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
- **`try`/`catch` for runtime error recovery** — merged 2026-07-24T~00:00Z via
  PR #58 (`feat/20260723-try-catch`). Added `TRY`/`CATCH` keywords, a
  `TryStmt` AST node, and parser support for `try { ... } catch (name) {
  ... }`; `Interpreter` runs `try_block` in a child `Environment` and, on a
  caught `CinderRuntimeError`, binds the message to `catch_name` in a fresh
  child `Environment` and runs `catch_block`.
  `break`/`continue`/`return` (Python-internal signals, not
  `CinderRuntimeError`) still propagate through uncaught. Clean first pass,
  no bounces (650 tests passing, 17 new).
- **Standard library: `chunk` for lists** — merged 2026-07-24T~00:15Z via
  PR #59 (`feat/20260723-chunk-lists`). Added `chunk(list, size)` to
  `cinder/builtins.py`, splitting a list into consecutive sublists of
  length `size` (last sublist shorter on uneven remainder), non-mutating,
  matching `slice`/`concat`/`flatten`'s type-check style. Clean first pass,
  no bounces (661 tests passing, 11 new).
- **Standard library: `partition` for lists** — merged 2026-07-24T~ via
  PR #60 (`feat/20260723-partition-lists`). Added `partition(list, fn)` to
  `cinder/builtins.py`, splitting a list into `[matching, non_matching]`
  using Cinder truthiness via the shared `call_value`/`is_truthy` helpers,
  matching `map`/`filter`'s type-check style. Clean first pass, no bounces
  (672 tests passing, 11 new).
- **Default parameter values: `fn f(a, b = 1) { ... }`** — merged
  2026-07-24T~ via PR #61 (`feat/20260723-default-params`). Extended
  `FnDecl`/`FnExpr.params` to `list[tuple[str, Expr | None]]`, parser support
  for `= <expr>` per parameter (enforcing default-after-default), and
  `CinderFunction.arity` becoming a minimum with `call_value`'s arity check
  now a min/max range that evaluates missing trailing defaults fresh against
  `call_env` each call. Bounced once on review: default-expression evaluation
  ran outside the `try/except CinderRuntimeError` that appends the caller's
  frame, so an error raised while evaluating a default was missing the
  calling function's frame; fixed by moving the evaluation loop inside the
  same try/except (686 tests passing, up from 650).
- **Block comments: `/* ... */`** — merged 2026-07-24T~ via PR #62
  (`feat/20260723-block-comments`). Extended
  `Lexer._skip_whitespace_and_comments` to recognize `/*...*/`, non-nesting
  (first `*/` wins), with line/column tracking preserved across embedded
  newlines and `LexError(unterminated=True)` on EOF reusing the same flag
  the REPL's `_needs_more_input` already branches on for unterminated
  strings. Clean first pass, no bounces (696 tests passing, 24 new).
- **Standard library: `insert` and `remove_at` for lists** — merged
  2026-07-24T14:11:10Z via PR #63 (`feat/20260723-insert-remove-at`). Added
  `insert(list, index, value)` and `remove_at(list, index)` to
  `cinder/builtins.py`, filling the gap between `push`/`pop` (end-only) and
  map's `remove` (key-based). Extracted a shared `normalize_index(index,
  length)` helper in `cinder/interpreter.py`, deduping the negative-index
  normalization that had been inlined three times, and pointed all four
  call sites at it. Clean first pass, no bounces (711 tests passing, 24
  subtests, up from 696).
- **Standard library: `ord` and `chr` for character/code-point conversion**
  — merged 2026-07-24T~ via PR #64 (`feat/20260724-ord-chr`). Added
  `ord(s)` and `chr(n)` to `cinder/builtins.py`, following `_int`/`_float`'s
  single-argument conversion style and delegating to Python's own
  `ord()`/`chr()`, converting `ValueError` into `CinderRuntimeError` with
  line/column. Clean first pass, no bounces (723 tests passing, up from
  711).
- **Standard library: `pad_start` and `pad_end` for strings** — merged
  2026-07-24T14:32:04Z via PR #65 (`feat/20260724-pad-start-end`). Added
  `pad_start(s, width, fill)` and `pad_end(s, width, fill)` to
  `cinder/builtins.py`, following `_find`/`_replace`'s multi-`str`-argument
  style; shared `_check_pad_arguments` helper validates both. Clean first
  pass, no bounces (741 tests passing, up from 723).
- **Standard library: `first` and `last` for lists** — merged
  2026-07-24T14:41:59Z via PR #66 (`feat/20260724-first-last-builtins`).
  Added `first(list)` and `last(list)` to `cinder/builtins.py`, following
  `reverse`/`copy`'s non-mutating, single-arg style. Clean first pass, no
  bounces (751 tests passing, up from 741).
- **Standard library: `take` and `drop` for lists** — merged
  2026-07-24T14:53:09Z via PR #67 (`feat/20260724-take-drop-builtins`).
  Added `take(list, n)` and `drop(list, n)` to `cinder/builtins.py`, both
  delegating to the same bound-clamping logic `slice` uses. Clean first
  pass, no bounces (769 tests passing, up from 751).
- **Standard library: `flat_map` for lists** — merged 2026-07-25T20:02:51Z via
  PR #68 (`feat/20260724-flat-map`). Added `flat_map(list, fn)` to
  `cinder/builtins.py`, equivalent to `flatten(map(list, fn))` as a single
  builtin via the shared `call_value` helper, following `map`/`filter`'s
  type-check style. This was the PR blocked across five sessions and two
  nights by a repo-wide `gh pr create` GraphQL 500 (see `nightshift/HELP.md`);
  the 500 cleared on retry with no code changes needed. Clean first pass
  once opened — Reviewer and QA both approved without rework (777 tests
  passing, up from 769).
- **String interpolation: `"...${expr}..."`** — merged 2026-07-25T20:20Z via
  PR #69 (`feat/20260724-string-interp`). Let double-quoted string literals
  embed `${expr}` placeholders (brace-depth tracked so nested `{}` doesn't
  end a placeholder early), added the `InterpString` AST node, and moved
  `stringify()` from `builtins.py` to `interpreter.py` to avoid a circular
  import. Also blocked for a night by the same repo-wide `gh pr create` 500
  as `flat_map`; rebased onto `main` once the outage cleared and opened
  cleanly. Clean first pass — Reviewer and QA both approved without rework
  (802 tests passing, up from 794).
- **List destructuring in `let`: `let [a, b] = expr;`** — merged
  2026-07-25T20:29:26Z via PR #70 (`feat/20260724-list-destructure`). Added a
  `DestructureLetStmt` AST node, parsed only when `let` is immediately
  followed by `[`; binds a flat list of plain identifier names positionally
  to the RHS, which must evaluate to a `list` of exactly the right length
  (no nesting, no rest element, no silent truncation/padding). Clean first
  pass, no bounces (817 tests passing, up from 802).
- **Standard library: `repeat` for lists** — merged 2026-07-24T20:39:38Z via
  PR #71 (`feat/20260725-repeat-list`). Added `repeat(value, n)` to
  `cinder/builtins.py`, returning a new list of `n` shallow-aliased copies
  of `value`, complementing `range`'s role for non-numeric sequences. Clean
  first pass, no bounces (824 tests passing, up from 817).
- **Standard library: `map_values` for maps** — merged 2026-07-25T14:07:23Z
  via PR #72 (`feat/20260725-map-values`). Added `map_values(map, fn)` to
  `cinder/builtins.py`, returning a new map with the same keys and each
  value replaced by `fn(value)` via the shared `call_value` helper, matching
  `map`/`filter`/`group_by`'s style. Clean first pass, no bounces (832 tests
  passing, up from 824).

## Graveyard

(none yet)
