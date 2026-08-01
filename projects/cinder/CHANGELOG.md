# CHANGELOG.md

Archived merge history for Cinder, split out of `BACKLOG.md` on
2026-07-30 to keep the active backlog short — every completed task used
to accumulate here forever, and Engineer/Reviewer/QA sessions were
re-reading a growing wall of finished history just to find the top
unclaimed task. This file is pure record; nobody needs to read it to
pick up new work. See `BACKLOG.md` for active tasks and `PROJECT.md`
for vision/architecture.

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
- **Numeric literals: hexadecimal, binary, and octal integers** — merged
  2026-07-25T14:19:09Z via PR #73 (`feat/20260725-hex-int-literals`).
  Extended `cinder/lexer.py`'s number-scanning to recognize `0x`/`0X`,
  `0b`/`0B`, and `0o`/`0O` prefixed integer literals, producing an ordinary
  `INT` token whose value is the parsed Python `int` (no AST/parser/
  interpreter change needed). Bare `0` and leading-zero decimals stay on
  the existing decimal path; empty digit runs and out-of-alphabet digits
  raise `LexError` at the literal's start. Clean first pass, no bounces
  (852 tests passing, up from 832).
- **Standard library: `find_index` for lists** — merged 2026-07-25T14:30:53Z
  via PR #74 (`feat/20260725-find-index`). Added `find_index(list, fn)` to
  `cinder/builtins.py`, returning the index of the first element for which
  `fn(element)` is truthy (or `-1`), short-circuiting so `fn` is never
  called past the first match. Complements `index_of`'s equality search the
  way `filter` complements `contains`. Clean first pass, no bounces (859
  tests passing, up from 852).
- **Standard library: `flatten_deep` for lists** — merged 2026-07-25T14:42:15Z
  via PR #75 (`feat/20260725-flatten-deep`). Added `flatten_deep(list)` to
  `cinder/builtins.py`, the fully-recursive counterpart to the existing
  one-level `flatten` (PR #53), flattening list-of-lists nesting at every
  depth into a single new list; non-mutating, matching `flatten`/`concat`'s
  type-check style. Clean first pass, no bounces (866 tests passing, up
  from 859).
- **Standard library: `min_by` and `max_by` for lists** — merged
  2026-07-25T14:53:40Z via PR #76 (`feat/20260725-min-max-by`). Added
  `min_by(list, fn)`/`max_by(list, fn)` to `cinder/builtins.py`, selecting
  the element whose `fn(element)` result is smallest/largest via the
  shared `call_value` helper, matching `sort_by`'s callback style;
  first-match tie-break, empty-list/non-list/non-callable/wrong-arity/
  mixed-type-key errors all mirror `min`/`max`/`sort_by`. Clean first
  pass, no bounces (881 tests passing, up from 866).
- **Standard library: value-based removal for lists via `remove`** — merged
  2026-07-25T15:04:38Z via PR #77 (`feat/20260725-list-remove`). Extended
  the existing map-only `remove` builtin to also dispatch on `list`, the
  same way `contains` dispatches across list/map/string — `remove(list,
  value)` deletes and returns the first element equal to `value` (via the
  shared `values_equal` helper, agreeing with `==`/`contains`/`index_of`
  on bool-vs-int), mutating in place and raising on no match. Fills the
  last gap in the list-removal trio: `pop` (end), `remove_at` (by index),
  `remove` (by value). Clean first pass, no bounces (886 tests passing, up
  from 881).
- **Standard library: `invert` for maps** — merged 2026-07-25T~ via PR #78
  (`feat/20260725-invert-map`). Added `invert(map)` to `cinder/builtins.py`,
  swapping each key/value pair (reusing `_is_valid_key` to reject a
  non-hashable value before it's used as a key), later entry wins on
  collision, matching `merge`'s rule; non-mutating. Clean first pass, no
  bounces (893 tests passing, up from 886).
- **Standard library: `zip_with` for lists** — merged 2026-07-26T~ via PR #79
  (`feat/20260725-zip-with`). Added `zip_with(list1, list2, fn)` to
  `cinder/builtins.py`, pairing two lists elementwise via `fn(a, b)` (the
  shared `call_value` helper) instead of `zip`'s bare `[a, b]` pairing,
  truncated to the shorter list's length like `zip`. Clean first pass, no
  bounces (901 tests passing, up from 893).
- **Map destructuring in `let`: `let {a, b} = expr;`** — merged
  2026-07-26T~ via PR #80 (`feat/20260725-map-destructure`). Extended
  `DestructureLetStmt` (from PR #70's list form) with an `is_map` flag
  rather than a new AST node; `let {a, b} = expr;` binds each identifier by
  looking it up as a key in a map RHS, missing keys or a non-map RHS raise
  `CinderRuntimeError` with line/column, extra unnamed keys are silently
  ignored (no positional arity check like the list form, since maps are
  looked up by name). Clean first pass, no bounces (918 tests passing, up
  from 901).
- **Standard library: `count_by` for lists** — merged 2026-07-25T19:47:47Z
  via PR #81 (`feat/20260725-count-by`). Added `count_by(list, fn)` to
  `cinder/builtins.py`, mirroring `group_by`'s `call_value`/`_is_valid_key`
  pattern but tallying group sizes into `{key: count}` instead of collecting
  elements, saving a `map_values(group_by(list, fn), fn(v) { len(v) })`
  round-trip. Clean first pass, no bounces (928 tests passing, up from 918).
- **Standard library: `deep_copy` for lists and maps** — merged
  2026-07-26T~ via PR #82 (`feat/20260725-deep-copy`). Added
  `deep_copy(collection)` to `cinder/builtins.py`, recursing through
  arbitrary list/map nesting so every nested container in the result is a
  fresh copy (unlike the existing shallow `copy`). Clean first pass, no
  bounces (934 tests passing, up from 928).
- **Standard library: `distinct_by` for lists** — merged 2026-07-25T20:08:36Z
  via PR #83 (`feat/20260725-distinct-by`). Added `distinct_by(list, fn)` to
  `cinder/builtins.py`, mirroring `group_by`/`count_by`'s `call_value`/
  `_is_valid_key` pattern but keeping the first element encountered per
  distinct `fn(element)` key instead of collecting/counting. Clean first
  pass, no bounces (943 tests passing, up from 934).
- **Standard library: `strip_prefix` and `strip_suffix` for strings** —
  merged 2026-07-25T20:19:48Z via PR #84
  (`feat/20260725-strip-prefix-suffix`). Added thin wraps over
  `str.removeprefix`/`removesuffix` to `cinder/builtins.py`, matching
  `starts_with`/`ends_with`'s arity/error-message/registration shape.
  Clean first pass, no bounces (955 tests passing, up from 943).
- **Standard library: `take_while` and `drop_while` for lists** — merged
  2026-07-25T20:31:59Z via PR #85 (`feat/20260725-take-while-drop-while`).
  Added `take_while(list, fn)`/`drop_while(list, fn)` to
  `cinder/builtins.py`, following `partition`/`find_index`'s
  `call_value`/`is_truthy` pattern; both stop at the first falsy result
  rather than scanning past it, matching `itertools.takewhile`/`dropwhile`.
  Clean first pass, no bounces (971 tests passing, up from 955).
- **Spread operator in list literals: `[...list1, x, ...list2]`** — merged
  2026-07-26T14:10:56Z via PR #86 (`feat/20260726-spread-list`). Added a
  `DOT_DOT_DOT` token, extended list-literal parsing/`_evaluate_list_literal`
  to splice `...expr` elements (each must evaluate to a `list`, raising
  `CinderRuntimeError` with line/column otherwise) among ordinary elements;
  map literals explicitly excluded, pinned by a regression test. Clean first
  pass, no bounces (979 tests passing, up from 971).
- **Standard library: `lines` and `words` for strings** — merged
  2026-07-26T14:21:14Z via PR #87 (`feat/20260726-lines-words`). Added
  `lines(s)` (splits on literal `"\n"`, no `\r\n` special-casing) and
  `words(s)` (splits on whitespace runs via Python's argumentless
  `str.split()`, discarding empty entries) to `cinder/builtins.py`,
  following `trim`/`split`'s single-`str`-argument style. Clean first pass,
  no bounces (989 tests passing, up from 979).
- **Standard library: `last_index_of` for lists** — merged 2026-07-26T~ via
  PR #88 (`feat/20260726-last-index-of`). Added `last_index_of(list, item)`
  to `cinder/builtins.py`, the mirror of the existing `index_of` (PR #49),
  scanning from the end via the shared `values_equal` helper (agreeing with
  `index_of`/`contains`/`in` on bool-vs-int per PR #51) and returning the
  `int` index of the last match or `-1`. Clean first pass, no bounces (995
  tests passing, up from 989).
- **`switch` statement** — merged 2026-07-26T~ via PR #89
  (`feat/20260726-switch-stmt`). Added new `SWITCH`/`CASE`/`DEFAULT`
  keywords, `SwitchStmt`/`SwitchCase` AST nodes, parser support, and
  interpreter evaluation: scrutinee evaluated exactly once, compared
  against each case value in source order via `values_equal`, first match's
  block runs with no fallthrough, falls back to `default` if present, else
  no-op. Each case body is a real block with its own child `Environment`;
  `switch` is not a loop, so `break`/`continue` inside a case still target
  an enclosing loop. Clean first pass, no bounces (1015 tests passing, up
  from 995).
- **Standard library: `capitalize` for strings** — merged 2026-07-26T~ via
  PR #90 (`feat/20260726-capitalize`). Added `capitalize(s)` to
  `cinder/builtins.py`, uppercasing only the first character of `s` via
  `str.upper()` and leaving the rest untouched — deliberately not Python's
  `str.capitalize()`, which also lowercases the remainder. Empty string is
  a no-op. Clean first pass, no bounces (1022 tests passing, up from 1015).
- **Standard library: `clamp` for numbers** — merged 2026-07-26T~ via PR #91
  (`feat/20260726-clamp`). Added `clamp(n, lo, hi)` to `cinder/builtins.py`,
  following the same shape as `min`/`max`: per-argument numeric checks, a
  `lo > hi` guard, then the clamp logic. Mixed int/float args pass through
  unchanged in type. Clean first pass, no bounces (1031 tests passing, up
  from 1022).
- **Rest parameters in function declarations: `fn f(a, ...rest) { ... }`**
  — merged 2026-07-27T~ via PR #92 (`feat/20260726-rest-params`). Extended
  `FnDecl`/`FnExpr` with a `rest_param: str | None` field; parser reuses
  the existing spread-operator ellipsis token to parse an optional
  trailing `...name`, rejecting it via `ParseError` if not last or if more
  than one is given. `call_value`'s arity check gains a "no upper bound"
  case when `rest_param` is set, extra positional args collected into a
  list. Combines with default parameters; works for anonymous `fn(...)`
  too. Clean first pass, no bounces (1046 tests passing, up from 1038).
- **Standard library: `is_empty` for lists, maps, and strings** — merged
  2026-07-26T19:39:42Z via PR #93 (`feat/20260726-is-empty`). Added
  `is_empty(collection)` to `cinder/builtins.py`, mirroring `len`'s
  type-check and arity-check pattern for `list`/`map`/`str`. Clean first
  pass, no bounces (1054 tests passing, up from 1046).
- **Standard library: `union`, `intersection`, `difference` for lists** —
  merged 2026-07-27T~ via PR #94 (`feat/20260726-union-intersection-difference`).
  Added all three to `cinder/builtins.py`, treating lists as unordered
  sets; factored `unique`'s dedupe logic into a shared `_dedupe` helper
  (bool/int-safe hashable fast path with `values_equal` fallback for
  unhashable elements) reused across all three, plus a `_require_two_lists`
  helper consolidating arity/type validation. First-list order preserved.
  Clean first pass, no bounces (1072 tests passing, up from 1054).
- **Standard library: `pluck` for lists of maps** — merged 2026-07-26T19:59:50Z
  via PR #95 (`feat/20260726-pluck`). Added `pluck(list, key)` to
  `cinder/builtins.py`, reusing `_is_valid_key` for key validation and
  matching map-index's raise-on-missing-key behavior (not `get`'s
  default-fill). Clean first pass, no bounces (1079 tests passing, up
  from 1072).
- **Standard library: `pick` and `omit` for maps** — merged
  2026-07-27T~ via PR #96 (`feat/20260726-pick-omit`). Added
  `pick(map, keys)`/`omit(map, keys)` to `cinder/builtins.py`; `pick`
  iterates `keys` (order-controlling, guarded by `_is_valid_key`) while
  `omit` comprehends over `target.items()` to preserve source order,
  both matching `merge`/`invert`'s style and silently skipping
  keys absent from the map. Clean first pass, no bounces (1095 tests
  passing, up from 1079).
- **Nil-coalescing operator: `a ?? b`** — merged 2026-07-26T20:26:00Z via
  PR #97 (`feat/20260726-nil-coalescing`). Added a `QUESTION_QUESTION`
  token via the lexer's existing two-char lookahead pattern, a new
  `_nullish` precedence tier between `_ternary` and `_or` (binds looser
  than `or`, tighter than the ternary), and an `is not None` check (not
  truthiness) in `_evaluate_logical`, so `0 ?? 5` is `0` and `false ?? 5`
  is `false`. Right-associative and short-circuiting like `and`/`or`.
  Clean first pass, no bounces (1108 tests passing, up from 1095).
- **Standard library: `gcd` and `lcm` for numbers** — merged
  2026-07-27T14:11:31Z via PR #98 (`feat/20260726-gcd-lcm`). Added both to
  `cinder/builtins.py` via `math.gcd`/`math.lcm`, int-only (unlike
  `clamp`/`min`/`max`), matching `floor`/`ceil`/`pow`/`sqrt`'s
  single-expression style. Clean first pass, no bounces (1123 tests
  passing, up from 1108).
- **Standard library: `mean` and `median` for lists of numbers** — merged
  2026-07-27T14:21:43Z via PR #99 (`feat/20260727-mean-median`). Added both
  to `cinder/builtins.py`: `mean` sums and divides by count, always
  returning `float`; `median` sorts a non-mutating copy and returns the
  middle element (odd length) or float mean of the two middle elements
  (even length). Rebased once after PR #98 merged (docstring/README
  listing conflict only, no functional changes); re-reviewed and
  re-QA'd post-rebase (1136 tests passing, up from 1123).
- **Spread arguments in function calls: `f(...args)`** — merged
  2026-07-27T14:35:01Z via PR #100 (`feat/20260727-spread-call-args`). The
  call-site counterpart to PR #86's list-literal spread and PR #92's rest
  parameters: parser wraps a leading `...` call argument in the existing
  `Spread` node (mirroring `_list_element`), interpreter splices its list
  elements into the flat argument list before arity checking/`call_value`
  (mirroring `_evaluate_list_literal`'s spread handling, non-list raises
  `CinderRuntimeError` with line/column). Works for user functions,
  builtins, and rest-param callees; multiple/mixed spreads evaluated left
  to right. Clean first pass, no bounces (1146 tests passing, up from
  1136).
- **Standard library: `sin`, `cos`, `tan`, `log` math builtins** — merged
  2026-07-27T14:47:07Z via PR #101 (`feat/20260727-sin-cos-tan-log`). Added
  all four to `cinder/builtins.py` following `floor`/`ceil`/`sqrt`'s
  single-numeric-argument style (PR #48), always returning `float`; `log`
  raises a domain error (matching `sqrt`'s negative-input handling) for
  `n <= 0` instead of letting Python's `ValueError` escape. Clean first
  pass, no bounces (1164 tests passing, up from 1146).
- **Standard library: `shuffle` and `sample` for lists** — merged
  2026-07-27T19:47:09Z via PR #102 (`feat/20260727-shuffle-sample`). Added
  both to `cinder/builtins.py` using stdlib `random` (no new dependency),
  non-mutating and matching `reverse`/`sort`'s style; `sample` selects by
  index so duplicate values in the source list are preserved correctly.
  `n` must be a non-negative `int` (`bool` explicitly excluded), and
  `n > len(list)` raises `CinderRuntimeError` with line/column. Clean
  first pass, no bounces (1177 tests passing, up from 1164).
- **Bitwise/shift compound assignment operators: `&=`, `|=`, `^=`, `<<=`,
  `>>=`** — merged 2026-07-27T20:00:52Z via PR #103
  (`feat/20260727-bitwise-compound-assign`). Extended the compound-assign
  family to the four bitwise operators and both shifts, including
  index-expression targets (`xs[0] &= 3`). Bounced once on review: the
  index-target desugaring reused the same `Index` AST node for both the
  read and the write, double-evaluating a side-effecting index/object
  expression; fixed by adding a dedicated `IndexCompoundAssign` node that
  evaluates `obj`/`index` exactly once, with `_evaluate_index`/
  `_evaluate_index_assign` split into shared `_index_get`/`_index_set`
  helpers. 1182 tests passing, up from 1177.
- **Standard library: `map_keys` for maps** — merged 2026-07-27T20:10:49Z via
  PR #104 (`feat/20260727-map-keys`). Added `map_keys(map, fn)` to
  `cinder/builtins.py`, the key-side counterpart to `map_values`, reusing
  `_is_valid_key` to reject a non-hashable transformed key and matching
  `merge`/`invert`'s later-insertion-wins collision rule. Clean first pass,
  no bounces (1204 tests passing, up from 1182).
- **Standard library: `trim_start` and `trim_end` for strings** — merged
  2026-07-29T14:10:26Z via PR #106 (`feat/20260728-trim-start-end`). Added
  `trim_start(s)`/`trim_end(s)` to `cinder/builtins.py` delegating to
  `str.lstrip()`/`str.rstrip()`, the one-sided counterparts to `trim`.
  Clean first pass, no bounces (1214 tests passing, up from 1204).
- **Standard library: `sign` for numbers** — merged 2026-07-29T14:10:19Z via
  PR #107 (`feat/20260729-sign-builtin`). Added `sign(n)` to
  `cinder/builtins.py`, returning `1`/`-1`/`0` as an `int` regardless of
  whether `n` is `int` or `float`, matching `abs`'s single-numeric-argument
  style. Clean first pass, no bounces (1213 tests passing).
- **Standard library: `title` for strings** — merged 2026-07-29T14:22:52Z via
  PR #105 (`feat/20260727-title-string`). Added `title(s)` to
  `cinder/builtins.py`, uppercasing only the first alphabetic character of
  each whitespace-separated word while preserving whitespace runs and
  apostrophe handling (`won't` -> `Won't`), deliberately diverging from
  Python's `str.title()`. Bounced by a merge conflict (not a review/QA
  failure) against `main` after tasks 2/3 landed on the same README area;
  rebased and re-reviewed clean (1232 tests passing).
- **Standard library: `random_int` and `random_choice`** — merged
  2026-07-29T14:33:40Z via PR #108 (`feat/20260729-random-int-choice`).
  Added `random_int(min, max)` and `random_choice(list)` to
  `cinder/builtins.py` via Python's stdlib `random` module, tested by
  property (in-bounds / list-membership) rather than exact-value
  assertions since both are non-deterministic. Clean first pass, no
  bounces (1242 tests passing).
- **Standard library: `round` with an optional `digits` argument** — merged
  2026-07-29T~ via PR #109 (`feat/20260729-round-digits`). Extended
  `round(n)` to accept an optional `digits` argument, following `min`/
  `max`'s manual-bounds-check style; delegates to Python's own
  `round(n, digits)` (banker's rounding), rejects non-numeric `n`, non-`int`
  or negative `digits` (with a `bool` guard since `bool` is an `int`
  subclass), and 0/3+-arity calls. Clean first pass, no bounces (1250
  tests passing, up from 1242).
- **Standard library: `to_fixed` for fixed-decimal number formatting** —
  merged 2026-07-29T14:56:13Z via PR #110 (`feat/20260729-to-fixed`). Added
  `to_fixed(n, digits)` to `cinder/builtins.py`, the string-output
  counterpart to `round(n, digits)` (PR #109): formats `n` via Python's own
  `f"{n:.{digits}f}"` format spec, mirroring `round`'s argument validation
  (non-numeric `n`; non-`int` or negative `digits`; wrong arity). Clean
  first pass, no bounces (1259 tests passing, up from 1250).
- **Increment/decrement statement operators: `++`, `--`** — merged
  2026-07-29T19:41:48Z via PR #111 (`feat/20260729-inc-dec-ops`). Added
  `PLUSPLUS`/`MINUSMINUS` tokens (extending `+`/`-` lexing to check for a
  doubled character before falling back to the compound-assign check) and
  statement-only `x++;`/`x--;` sugar desugaring to `x = x + 1;`/`x = x - 1;`
  at parse time, reusing compound assignment's existing lvalue restriction
  (identifier or index expression) and `IndexCompoundAssign` node for
  single-evaluation of index targets. Not an expression form — `let b =
  a++;` doesn't parse. Clean first pass, no bounces (1279 tests passing, up
  from 1259).
- **Standard library: `interleave` for two lists** — merged
  2026-07-29T20:58:50Z via PR #112 (`feat/20260729-interleave`). Added
  `interleave(list1, list2)` to `cinder/builtins.py`, reusing
  `_require_two_lists` for validation; flattens elements alternately from
  each list, appending whichever list's remainder is left once the other
  runs out (unlike `zip`/`zip_with`, which truncate to the shorter
  length). Clean first pass, no bounces (1288 tests passing).
- **Standard library: `from_entries` for maps** — merged
  2026-07-29T20:58:46Z via PR #113 (`feat/20260729-from-entries`). Added
  `from_entries(list)` to `cinder/builtins.py`, the inverse of `items(map)`
  — takes a list of `[key, value]` pairs and builds a new map, later entry
  wins on duplicate keys (matching `merge`/`pick`), reusing `_is_valid_key`
  for key validation. Clean first pass, no bounces (1288 tests passing).
- **Standard library: `to_hex`, `to_bin`, `to_oct` for integers** — merged
  2026-07-29T21:11:43Z via PR #114 (`feat/20260729-to-hex-bin-oct`). Added
  the string-formatting counterpart to the numeric-literal-parsing side
  (`0x1F`/`0b101`/`0o17` literals, PR #73): each returns the lowercase,
  unprefixed digit string for `n` via `format(n, 'x'/'b'/'o')`, sign
  preserved for negative ints. Clean first pass, no bounces.
- **`finally` block for `try`/`catch`** — merged 2026-07-30 via PR #115
  (`feat/20260729-finally-block`). Extended `TryStmt` with an optional
  `finally_block`, made `catch` optional (at least one of catch/finally
  still required), and implemented `_execute_try` with a Python
  `try/finally` around the existing `try/except` so finally runs on every
  exit path — clean, caught, uncaught error, or `break`/`continue`/`return`
  — via Python's own finally semantics. Clean first pass, no bounces (1324
  tests passing).
- **Standard library: `split_at` for lists** — merged 2026-07-30T14:05:13Z
  via PR #116 (`feat/20260729-split-at`). Added `split_at(list, index)` to
  `cinder/builtins.py`, returning `[left, right]` at `index`; reuses
  `_normalize_slice_bound` (already used by `_slice`/`_take`/`_drop`) so
  negative indices count from the end and out-of-range indices clamp
  instead of erroring, matching `slice`'s bound-handling. Clean first
  pass, no bounces (1335 tests passing).
- **Standard library: `rotate` for lists** — merged 2026-07-30T14:15:58Z
  via PR #117 (`feat/20260730-rotate`). Added `rotate(list, n)` to
  `cinder/builtins.py`, returning a new list rotated left by `n`
  positions (`list[n % len:] + list[:n % len]`), matching Python's own
  list-rotation idiom; negative `n` rotates right, empty list is always a
  no-op (avoids `n % 0`). Non-mutating, matching `reverse`/`sort`/
  `shuffle`'s style. Clean first pass, no bounces (1345 tests passing).
- **`do { ... } while (cond);` loop** — merged 2026-07-30T14:29:17Z via
  PR #118 (`feat/20260730-do-while`). Added a `DO` keyword token and a
  `DoWhileStmt` AST node mirroring `WhileStmt`, with the parser requiring
  the trailing `;` after `while (cond)` (unlike plain `while`, since the
  body was already consumed as a statement) and reusing `_loop_depth`
  bumping so `break`/`continue` are valid inside it; the interpreter runs
  the body once unconditionally, then loops on check-then-repeat, with
  `break` exiting without rechecking `cond` and `continue` skipping
  straight to the condition check. Clean first pass, no bounces (1354
  tests passing).
- **`const` declarations for immutable bindings** — merged
  2026-07-30T19:33:12Z via PR #119 (`feat/20260730-const-decl`). Added a
  `CONST` keyword token and a `ConstStmt` AST node mirroring `LetStmt`;
  `Environment` gained a per-scope `_frozen: set[str]` populated by
  `define_const`, checked in `assign` before mutating and raising
  `CinderRuntimeError` at the assignment's line/column; `define` (plain
  `let`) discards a name from `_frozen` so redeclaring a previously-const
  name with `let` in the same scope unfreezes it. Index-assignment through
  a const binding is unaffected by design. Bounced once (Reviewer asked
  for missing regression tests on the let/const redeclaration interaction
  and `x++` on a const), fixed with test-only follow-up commit, then LGTM
  (1372 tests passing).
- **Standard library: `unzip` for lists** — merged 2026-07-30T19:33:16Z
  via PR #120 (`feat/20260730-unzip`). Added `unzip(pairs)` to
  `cinder/builtins.py`, the inverse of `zip`: takes a list of 2-element
  pairs and returns `[list_of_firsts, list_of_seconds]`, validating arity,
  list-ness, and per-element shape (naming the offending index on
  failure). Empty input returns `[[], []]`. Clean first pass, no bounces
  (1362 tests passing).
- **C-style `for (init; cond; step) { ... }` loop** — merged
  2026-07-30T19:56:16Z via PR #121 (`feat/20260730-c-for`). Added a
  `ForCStmt` AST node parsed by peeking for `(` right after `for` to
  disambiguate from the foreach form; `init` is a `let` declaration or an
  expression/increment statement, `condition` defaults to always-true when
  omitted, `step` runs unconditionally after each iteration (including
  after `continue`, which falls through rather than re-raising) so it
  can't be skipped. Bounced once (Reviewer caught that the init `let`
  binding was reused across iterations instead of getting a fresh
  per-iteration `Environment`, breaking closures captured inside the
  body — the foreach form already handles this correctly); fixed by
  running the body in a fresh child environment each iteration, then
  LGTM (1396 tests passing).
- **Standard library: `zip_longest` for lists** — merged
  2026-07-30T20:07:29Z via PR #122 (`feat/20260730-zip-longest`). Added
  `zip_longest(list1, list2, fill)` to `cinder/builtins.py`, pairing two
  lists element-wise like `zip` but padding the shorter list with `fill`
  instead of truncating, via stdlib `itertools.zip_longest`. Clean first
  pass, no bounces (1403 tests passing).
- **Standard library: `group_consecutive` for lists** — merged
  2026-07-30T20:17:30Z via PR #123 (`feat/20260730-group-consecutive`).
  Added `group_consecutive(list)` to `cinder/builtins.py`, run-length
  grouping of adjacent equal elements (structural equality via plain
  Python `==`, same assumption `unique`/`distinct_by` rely on) — the
  list-native cousin of `group_by`. Clean first pass, no bounces (1410
  tests passing).
- **Nil-coalescing compound assignment: `??=`** — merged
  2026-07-30T20:29:25Z via PR #124 (`feat/20260730-qqeq`). Added `??=` as
  a compound-assignment sibling desugaring `x ??= v` to
  `Assign(x, Logical(x, QUESTION_QUESTION, v))` rather than the generic
  `Binary`-based compound-assign path, preserving `??`'s short-circuit
  (right side only evaluated when `x` is `nil`). New `QQEQ` token lexed
  by extending `_question`'s existing `??` disambiguation. Identifier
  targets only — index targets (`xs[0] ??= 1`) raise `ParseError` by
  design. Clean first pass, no bounces (1420 tests passing).
- **Standard library: `sliding_window` for lists** — merged
  2026-07-30T20:40:27Z via PR #125 (`feat/20260730-sliding-window`).
  Added `sliding_window(list, size)` to `cinder/builtins.py`, the
  overlapping-window counterpart to `chunk` (contiguous runs of `size`
  elements sliding forward by one, rather than partitioning into
  disjoint pieces). Mirrors `chunk`'s validation exactly, but a `size`
  larger than the list produces `[]` rather than an error. Clean first
  pass, no bounces (1432 tests passing).
- **Standard library: `deep_equal` for structural equality** — merged
  2026-07-31T14:17:01Z via PR #126 (`feat/20260731-deep-equal`). Added
  `deep_equal(a, b)` to `cinder/builtins.py`: recursive structural
  equality for lists (pairwise, by length) and maps (by key set, order-
  independent), with scalar comparisons delegating to `values_equal` so
  `deep_equal`'s int/float coercion and bool-exclusion semantics stay
  permanently tied to `==`'s. Bounced once on review: the scalar branch
  originally reimplemented that coercion/exclusion logic instead of
  reusing `values_equal`, risking silent drift between the two; fixed by
  delegating. Clean after the one fix (1441 tests passing, up from 1432).
- **CLI: `-e`/`--eval` flag to run an inline snippet** — merged
  2026-07-31T14:27:50Z via PR #127 (`feat/20260731-cli-eval-flag`).
  Added an `eval` subcommand to `cinder/cli.py` alongside `run`/`repl`,
  taking the snippet text as a positional argument instead of a file
  path. Factored `run_file`'s lex/parse/execute body into a shared
  `_run_source` helper so both paths reuse it; errors report with an
  `<eval>:` prefix (no filename) via the same `CinderError` line/column
  formatting `run` already used. Clean first pass, no bounces (1446
  tests passing).
- **"Did you mean...?" suggestions for undefined-name errors** — merged
  2026-07-31T14:40:36Z via PR #128 (`feat/20260731-did-you-mean`). Added
  `Environment.all_names()` (`cinder/interpreter.py`), walking the scope
  chain including the outermost `Environment` that holds builtins, and
  used stdlib `difflib.get_close_matches` (cutoff 0.6, n=1) in both
  `_evaluate_identifier` and `_evaluate_assign` to append `(did you mean
  'x'?)` to `undefined name` errors when a close match exists, leaving
  the no-match message byte-for-byte unchanged. Clean first pass, no
  bounces (1452 tests passing).
- **Labeled `break`/`continue` for nested loops** — merged
  2026-07-31T19:36:52Z via PR #129 (`feat/20260731-labeled-loops`). Added
  an optional `label: str | None` field to each loop AST node and to
  `BreakStmt`/`ContinueStmt`; the parser peeks for `IDENTIFIER ':'` before
  a loop keyword at statement position and replaced the old `_loop_depth`
  int counter with a `_loop_labels` stack so a labeled break/continue can
  be validated against every enclosing loop, not just counted; the
  interpreter's `_BreakSignal`/`_ContinueSignal` now carry an optional
  label and re-raise unchanged when a loop's own label doesn't match,
  propagating to the next enclosing loop via ordinary Python exception
  propagation. Clean first pass, no bounces (1473 tests passing, up from
  1452).
- **Standard library: `key_by` for lists** — merged 2026-07-31T19:47:30Z
  via PR #130 (`feat/20260731-key-by`). Added `_key_by` to
  `cinder/builtins.py`, mirroring `_group_by`'s validation exactly
  (arity, list check, callable check, `_is_valid_key` check with
  matching error phrasing) but indexing each key directly to the item
  itself, with plain `result[key] = item` giving last-write-wins on
  duplicate keys. Clean first pass, no bounces (1482 tests passing, up
  from 1473).
- **Standard library: `deep_merge` for maps** — merged 2026-07-31T20:08:42Z
  via PR #131 (`feat/20260731-deep-merge`). Added `deep_merge(map1, map2)`
  to `cinder/builtins.py`, the recursive counterpart to `merge`: nested
  maps present on both sides merge key-by-key instead of `map2`'s inner
  map clobbering `map1`'s wholesale; lists and other non-map values still
  follow `merge`'s last-write-wins rule. Bounced once on review:
  `_deep_merge_values` assigned values by reference for keys present in
  only one input (or a non-dict value winning a leaf conflict), so
  mutating the result could leak back into the caller's original maps;
  fixed by routing every non-recursed value through the existing
  `_deep_copy_value` helper, with new tests mutating the *result* after
  the merge (1494 tests passing, up from 1482).
- **Spread elements in map literals: `{...map1, "k": v}`** — merged
  2026-07-31T20:22:55Z via PR #132 (`feat/20260731-map-spread`). Extended
  the spread operator, previously only accepted in list literals and call
  arguments, to map literals: `MapLiteral.pairs` now mixes plain
  `(key, value)` tuples with `Spread` entries, parsed by a new
  `_map_entry()` mirroring `_list_element()`, and evaluated by
  `_evaluate_map_literal` via `dict.update` for left-to-right
  last-write-wins across explicit keys and spreads alike. Clean first
  pass, no bounces (1503 tests passing, up from 1494).
- **Function composition: `pipe` and `compose`** — merged
  2026-07-31T20:34:16Z via PR #133 (`feat/20260731-pipe-compose`). Added
  `pipe(...fns)` and `compose(...fns)` to `cinder/builtins.py`, the first
  builtins to return a new callable Cinder value instead of computing a
  result directly: each validates every argument is callable up front,
  then returns a `Builtin` closure that threads a single argument through
  every wrapped function via `call_value`, `pipe` left-to-right and
  `compose` right-to-left, with zero functions acting as identity. Clean
  first pass, no bounces (1517 tests passing, up from 1503).
- **Rest element in list destructuring: `let [a, b, ...rest] = expr;`** —
  merged 2026-08-01T~ via PR #134 (`feat/20260801-rest-destructure`). Added
  an optional `rest: str | None` field to `DestructureLetStmt`, list-form
  only (map destructuring untouched); parser reuses the spread token exactly
  as function rest parameters do and requires the rest name be the pattern's
  last element, raising `ParseError` otherwise. Interpreter requires
  `len(value) >= len(names)` (not `==`) when a rest is present, binding the
  remainder as a list (empty if nothing's left over). Clean first pass, no
  bounces (1526 tests passing, up from 1517).
- **`throw` statement for user-raised errors** — merged 2026-08-01T14:30:36Z
  via PR #135 (`feat/20260801-throw-statement`). Added `TokenType.THROW`,
  a `ThrowStmt` AST node mirroring `ReturnStmt`'s shape (expression
  mandatory, unlike `return`'s optional value), and interpreter support
  raising `CinderRuntimeError` directly for `str` values (caught by
  existing `try`/`catch`/`finally` machinery, no new signal class needed)
  or a type error for non-`str` values, using the codebase's
  `type_name()` convention (`"got int"`) rather than the backlog's
  literal wording (`"got number"`). Clean first pass, no bounces (1534
  tests passing, up from 1526).
- **Standard library: `get_in` for safe nested access** — merged
  2026-08-01T14:43:18Z via PR #136 (`feat/20260801-get-in`). Added
  `get_in(container, path, default)` to `cinder/builtins.py`: walks a
  list of map keys/list indices through nested containers in one call,
  reusing `_is_valid_key` and `normalize_index` (the same helpers
  `get`/`pluck`/`insert`/`remove_at` already use) rather than
  reimplementing key/index validation. Every per-step failure (bad key
  type, missing key, out-of-range index, non-container mid-path) is a
  soft `return default`; only a non-list `path` argument raises
  `CinderRuntimeError`. Clean first pass, no bounces (1545 tests
  passing, up from 1534).
- **Standard library: `curry` for single-argument currying** — merged
  2026-08-01T14:56:25Z via PR #137 (`feat/20260801-curry`). Added
  `curry(fn, arity)` to `cinder/builtins.py`, the same returned-function
  mechanism `pipe`/`compose` already use: a chain of one-argument
  `Builtin` closures, each capturing its own accumulator snapshot so
  partial applications are independent and reusable, that calls `fn` via
  `call_value` once `arity` arguments have been collected. Clean first
  pass, no bounces (1555 tests passing, up from 1545).
- **Standard library: `memoize` for caching pure functions** — merged
  2026-08-01T15:11:30Z via PR #138 (`feat/20260801-memoize`). Added
  `memoize(fn)` to `cinder/builtins.py`, the same returned-closure
  mechanism `pipe`/`compose`/`curry` already use: a fresh `dict` cache
  per `memoize(...)` call, keyed on `(type name, value)` pairs so a
  number and a bool argument never collide, matching `values_equal`'s
  number/bool distinction. Clean first pass, no bounces (1565 tests
  passing, up from 1555).
- **Multiple values per `switch` case: `case 1, 2, 3: { ... }`** — merged
  2026-08-02T~ via PR #139 (`feat/20260801-switch-multi-value`). Changed
  `SwitchCase.value: Expr` to `values: list` (non-empty), with the parser
  comma-parsing extra case values the same way call arguments/list
  literals already do, and the interpreter matching `case.values` left to
  right, short-circuiting on the first match so later value expressions'
  side effects don't run once an earlier one matched. Single-value cases
  are unaffected. Clean first pass, no bounces (1571 tests passing, up
  from 1565).
- **List destructuring in `for`-loop variables: `for [k, v] in items(m) { ... }`**
  — merged 2026-08-01T19:45:14Z via PR #140 (`feat/20260801-for-destructure`).
  `ForStmt` gained optional `names`/`rest` fields alongside `var_name`
  (mutually exclusive), with the parser's pattern-parsing loop factored
  out of `_destructure_let_statement` into a shared
  `_destructure_list_pattern` helper used by both `let` and the new
  `for [a, b] in ...` form, and the interpreter's arity/rest binding
  logic similarly factored into `_bind_list_destructure`, shared between
  `DestructureLetStmt` and `_execute_for`. Map-pattern destructuring in
  `for` stays out of scope. Clean first pass, no bounces (1588 tests
  passing, up from 1571).
