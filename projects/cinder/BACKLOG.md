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


## 1. Standard library: `copy` for lists and maps [claimed 2026-07-22T19:30:16Z]

Build: add `copy(collection)` to `cinder/builtins.py`, returning a new
top-level `list` or `dict` (shallow copy — nested lists/maps inside it are
still shared with the original, matching Python's `list.copy()`/
`dict.copy()` semantics, not a deep copy) for a `list` or `map` argument.
This exists because Cinder's lists/maps are reference types (assignment
aliases, `push`/`pop`/index-assign mutate in place, per PR #14/#8) with no
way today to intentionally break aliasing. Any other argument type raises
`CinderRuntimeError` with line/column, matching `reverse`/`sort`'s
type-check style.

Acceptance criteria:
- `let a = [1, 2]; let b = copy(a); push(b, 3);` leaves `a` as `[1, 2]`
  and `b` as `[1, 2, 3]` (the whole point of the builtin — regression test
  against aliasing).
- Same shape for maps: `let a = {"x": 1}; let b = copy(a); b["y"] = 2;`
  leaves `a` as `{"x": 1}`.
- `copy([1, [2, 3]])`'s inner list is still the *same* object as the
  original's inner list (shallow-copy regression test — mutating the
  original's nested list via `push` is visible through the copy's nested
  list too).
- `copy(5)` and `copy("a")` raise `CinderRuntimeError` with line/column
  (unsupported argument type).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Standard library: `sort_by` with a custom key function

Build: add `sort_by(list, fn)` to `cinder/builtins.py`, returning a new
ascending-sorted list (non-mutating, matching `sort`'s style) ordered by
each element's `fn(element)` result rather than the element itself —
complementing `sort`, which only handles all-numeric or all-string lists
directly. Call `fn` once per element via the shared `call_value` helper
(same pattern `map`/`filter`/`reduce` already use, imported from
`cinder/interpreter.py`), then sort by the resulting keys using Python's
stable `sorted(..., key=...)`; the keys themselves must be all-numeric or
all-string (reuse `_is_numeric`/the same mixed-type rejection `_sort`
already applies to the *key* results, not the original elements — a
mixed-type key set raises `CinderRuntimeError`). First argument must be
`list` and second must be callable (`CinderFunction` or `Builtin`),
matching `map`/`filter`'s type-check style.

Acceptance criteria:
- `sort_by([3, 1, 2], fn(x) { return x; })` is `[1, 2, 3]` (identity key
  matches plain `sort`).
- `sort_by(["bb", "a", "ccc"], fn(x) { return len(x); })` is
  `["a", "bb", "ccc"]` (sorts by string length, not lexicographic order).
- `sort_by([], fn(x) { return x; })` is `[]`; `fn` is never called on an
  empty list.
- Sort is stable: two elements with equal keys keep their relative input
  order (regression test with e.g. `[[1, "a"], [1, "b"]]` keyed by the
  first element).
- `sort_by(5, fn(x) { return x; })` and `sort_by([1, 2], 5)` raise
  `CinderRuntimeError` with line/column (non-list / non-callable argument).
- `sort_by([1, "a"], fn(x) { return x; })` raises `CinderRuntimeError`
  (mixed-type keys, same rule `sort` already enforces).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. Bitwise operators: `&`, `|`, `^`, `~`, `<<`, `>>`

Build: add six token types to `cinder/tokens.py`'s `TokenType`
(`AMP`, `PIPE`, `CARET`, `TILDE`, `LSHIFT`, `RSHIFT`) and lex them in
`cinder/lexer.py` — `~` is single-char, `<<`/`>>` need the same two-char
lookahead pattern already used for `<=`/`>=`/compound-assignment (watch
for ambiguity with the existing `LT`/`GT`/`LTEQ`/`GTEQ` tokens: `<<` must
not be lexed as two `LT`s or collide with `<=`). Add a new precedence tier
in `cinder/parser.py` for the five binary operators (`&`, `|`, `^`, `<<`,
`>>`) between `_comparison` and `_factor` — pick one sub-tier per operator
group following C's relative precedence (`|` loosest, then `^`, then `&`,
then `<<`/`>>` tightest, all looser than `+`/`-`/`*`/`/`/`%`) — reusing
the existing `Binary` AST node, no new node needed. `~` is unary: extend
`_unary` (alongside the existing `-`/`not` handling) with a new `Unary`
case, reusing the existing `Unary` AST node. In
`cinder/interpreter.py`'s `_evaluate_binary`/`_evaluate_unary`, implement
each operator via Python's own bitwise operators, restricted to `int`
operands only (a `float` or any non-numeric operand on either side raises
`CinderRuntimeError` with line/column — unlike `+`/`-`/`*`/`/`, bitwise
ops do not auto-promote floats).

Acceptance criteria:
- `5 & 3` is `1`; `5 | 2` is `7`; `5 ^ 1` is `4`; `~5` is `-6` (Python's
  own bitwise semantics — two's-complement `int`, matching Python `int`
  since Cinder ints are backed by Python `int`).
- `1 << 3` is `8`; `16 >> 2` is `4`.
- `1 | 2 == 3` parses as `1 | (2 == 3)` or `(1 | 2) == 3` — pick one
  consistent with the chosen precedence tier and add a parser test
  pinning it explicitly (precedence is this task's main risk).
- `2 + 3 << 1` is `10` (`<<` binds looser than `+`, so this is
  `(2 + 3) << 1`, not `2 + (3 << 1)`).
- `5.0 & 3`, `"a" | 1`, `~"a"`, `~5.0` each raise `CinderRuntimeError` with
  line/column (no float/non-numeric operands for bitwise ops).
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`.

---

## 5. Standard library: `remove` for maps

Build: add `remove(map, key)` to `cinder/builtins.py`, deleting `key` from
`map` **in place** (mutating, matching `push`/`pop`'s in-place style rather
than `merge`/`copy`'s non-mutating style — this is the map counterpart to
`pop`) and returning the removed value. First argument must be `map`,
raising `CinderRuntimeError` with line/column for a non-map argument,
matching `keys`/`values`'s type-check style. A missing key raises
`CinderRuntimeError` with line/column too — same "key not found" wording
the existing map-index path in `cinder/interpreter.py` already raises for
`map[missing_key]` (reuse it rather than inventing new wording, same rule
task 3 (`get`) followed for its hashability check).

Acceptance criteria:
- `let m = {"a": 1, "b": 2}; remove(m, "a");` leaves `m` as `{"b": 2}`
  (mutates in place — regression test that the original map, not a copy,
  changed).
- `remove({"a": 1}, "a")` returns `1` (the removed value).
- `remove({"a": 1}, "z")` raises `CinderRuntimeError` with line/column
  (missing key), matching plain `{"a": 1}["z"]` indexing's existing error.
- `remove(5, "a")` raises `CinderRuntimeError` with line/column (non-map
  first argument).
- `remove({"a": 1}, [1, 2])` raises `CinderRuntimeError` (unhashable key),
  matching `get`'s (task 3) handling of the same case.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 6. Standard library: type-predicate builtins

Build: add seven single-argument builtins to `cinder/builtins.py` —
`is_list`, `is_map`, `is_string`, `is_number`, `is_bool`, `is_nil`,
`is_function` — each returning a `bool`, complementing the existing
`type(value)` (which returns a type-name string) with direct predicates for
`if`/`while` conditions. `is_number` is `true` for both `int` and `float`
(reuse `_is_numeric`, already defined in `builtins.py`); `is_function` is
`true` for both a `CinderFunction` and a `Builtin` (reuse `_is_callable`,
already defined for `map`/`filter`/`sort_by`). Each takes exactly one
argument of any type — wrong arity raises `CinderRuntimeError` via the
existing `_require_arity` helper, but there is no "wrong type" error case
since every Cinder value is a valid argument to every predicate.

Acceptance criteria:
- `is_list([1])` is `true`; `is_list({"a": 1})` is `false`.
- `is_map({"a": 1})` is `true`; `is_map([1])` is `false`.
- `is_string("a")` is `true`; `is_number(1)` is `true`; `is_number(1.5)` is
  `true`; `is_number("1")` is `false`.
- `is_bool(true)` is `true`; `is_bool(0)` is `false` (Cinder booleans are a
  distinct type from `int`, not `0`/`1`).
- `is_nil(nil)` is `true`; `is_nil(false)` is `false`.
- `is_function(fn(x) { return x; })` is `true` for both a named `fn` and an
  anonymous `fn(x) { ... }` expression, and for a builtin passed by
  reference (e.g. `is_function(len)` — confirm builtins are first-class
  values that can be looked up by name, matching how `map`/`filter` already
  accept them); `is_function(1)` is `false`.
- Calling any of the seven with zero or two arguments raises
  `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 7. Standard library: `floor`, `ceil`, `pow`, `sqrt`

Build: add four math builtins to `cinder/builtins.py`, complementing the
existing `abs`/`min`/`max`/`round` (see PR #20). `floor(n)`/`ceil(n)` take one
numeric argument and return an `int` (delegate to Python's `math.floor`/
`math.ceil`). `pow(base, exp)` takes two numeric arguments and returns
`base ** exp` via Python's `**` (int result if both args are `int` and the
result is exact, else `float` — mirror Python's own `**` promotion, same
spirit as `sum`'s int/float promotion from PR #37). `sqrt(n)` takes one
numeric argument, delegates to `math.sqrt`, always returns a `float`, and
raises `CinderRuntimeError` with line/column for a negative argument (Cinder
has no complex numbers) instead of letting Python's `ValueError` escape.
Each of the four rejects a non-numeric argument or wrong arity with
`CinderRuntimeError` and line/column, matching `abs`/`round`'s type-check
style.

Acceptance criteria:
- `floor(1.5)` is `1`; `floor(-1.5)` is `-2`; `ceil(1.1)` is `2`;
  `ceil(-1.1)` is `-1`.
- `pow(2, 10)` is `1024` (`int` result); `pow(2, 0.5)` is `~1.414`
  (`float` result); `pow(2, -1)` is `0.5`.
- `sqrt(9)` is `3.0` (always `float`, even for a perfect square);
  `sqrt(2)` is `~1.414`.
- `sqrt(-1)` raises `CinderRuntimeError` with line/column (no complex
  numbers).
- `floor("a")`, `ceil(nil)`, `pow(2, "a")`, `sqrt("a")` each raise
  `CinderRuntimeError` with line/column (non-numeric argument).
- Wrong arity (e.g. `floor()`, `pow(2)`) raises `CinderRuntimeError` with
  line/column for all four.
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

## Graveyard

(none yet)
