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
- **Dot access sugar for map string keys: `m.key` as sugar for `m["key"]`**
  — merged 2026-08-02T19:57:24Z via PR #141 (`feat/20260801-dot-access`).
  Added a `_finish_dot` postfix branch in `parser.py`'s `_call` that
  desugars `m.key` into exactly the same `Index(obj, Literal("key"))`
  node bracket indexing already produces, so assignment, bitwise/shift
  compound-assign, and `++`/`--` on dot targets all work with zero
  interpreter changes (existing dispatch keys off `isinstance(expr,
  Index)`, not how it was built). Dot access only reaches
  identifier-shaped keys (`m.if` raises `ParseError`); arithmetic
  compound-assign (`m.key += 1`) stays unsupported, matching bracket
  indexing's existing gap. Clean first pass, no bounces (1603 tests
  passing, up from 1588).
- **Standard library: `pick_by`/`omit_by` for predicate-based map
  filtering** — merged 2026-08-01T20:09:27Z via PR #142
  (`feat/20260801-pick-by-omit-by`). Both mirror `pick`/`omit`'s
  arity/type-check shape and `filter`'s predicate-validation shape,
  keeping (`pick_by`) or dropping (`omit_by`) each `key, value` pair
  based on `call_value(predicate, [key, value], ...)`'s truthiness,
  preserving source insertion order. Clean first pass, no bounces (1617
  tests passing, up from 1603).
- **Standard library: `take_right`/`drop_right` for taking/dropping from
  a list's end** — merged 2026-08-01T20:22:48Z via PR #143
  (`feat/20260801-take-right-drop-right`). Both mirror `take`/`drop`'s
  arity/type-check shape exactly, reusing `_normalize_slice_bound` to
  clamp `n` against the list's length; `take_right` returns the last `n`
  elements in original order, `drop_right` returns everything except
  them, neither mutates the input list. Clean first pass, no bounces
  (1635 tests passing, up from 1617).
- **Standard library: `variance`/`std_dev` for a list of numbers** — merged
  2026-08-02T~ via PR #144 (`feat/20260801-variance-std-dev`). Added both to
  `cinder/builtins.py`, following `mean`/`median`'s arity/type-check shape
  exactly; population variance (divide by `n`, matching Cinder's existing
  no-sample-vs-population convention), with the shared mean/squared-
  deviation logic factored into an internal `_population_variance` helper
  so `std_dev` doesn't duplicate it or call `variance` through `call_value`.
  Clean first pass, no bounces (1648 tests passing, up from 1635).
- **REPL tab completion for builtin names and in-scope variables** — merged
  2026-08-02T14:12:13Z via PR #145 (`feat/20260802-repl-tab-complete`). Wired
  `readline`'s completer API into `_try_enable_readline`, which now takes the
  top-level `Environment` and re-reads its bindings on every completer call
  (via `Environment.all_names()`, reused from the existing did-you-mean
  suggestions rather than adding a new accessor) so session-defined variables
  complete immediately alongside builtins/keywords. Clean first pass, no
  bounces (1653 tests passing, up from 1648).
- **Standard library: `mode` for the most frequently occurring value in a
  list** — merged 2026-08-02T14:24:52Z via PR #146
  (`feat/20260802-mode-builtin`). Added to `cinder/builtins.py`, modeled on
  `_dedupe`'s two-path counting approach rather than `mean`/`median`'s
  numeric-only validation, since `mode` works on any valid Cinder value: a
  fast path keyed on `(is_bool, element)` for valid map keys (splitting `1`
  from `true`), falling back to a `values_equal`-based count for
  non-hashable values (lists). Ties resolve to first appearance in the
  input list. Clean first pass, no bounces (1662 tests passing, up from
  1653).
- **Arithmetic compound assignment on index/dot-access targets** — merged
  2026-08-02T14:38Z via PR #147 (`feat/20260802-arith-index-compound`).
  Widened `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` in `cinder/parser.py` to
  cover `+=`, `-=`, `*=`, `/=`, `%=` alongside the existing bitwise/shift
  set, so `xs[0] += 1` and `m.key += 1` (which desugars to the same
  `Index` node) now work; no interpreter changes needed since
  `_evaluate_index_compound_assign` already applies whatever operator the
  desugared node carries generically. Clean first pass, no bounces (1667
  tests passing, up from 1662).
- **Standard library: `product` for the product of a list of numbers** —
  merged 2026-08-02T14:51:01Z via PR #148
  (`feat/20260802-product-builtin`). Added to `cinder/builtins.py`, modeled
  directly on `_sum`'s structure with the fold starting from `1` instead of
  `0`, so `product([])` is well-defined as `1` with no non-empty check.
  Clean first pass, no bounces (1675 tests passing, up from 1667).
- **Nil-coalescing compound assignment on index/dot-access targets** —
  merged 2026-08-02T15:08:14Z via PR #149 (`feat/20260802-index-qq-eq`).
  Added a dedicated `IndexNilCoalesceAssign` AST node and interpreter
  evaluator (rather than reusing `IndexCompoundAssign`, whose evaluator
  unconditionally evaluates the RHS) so `xs[0] ??= 1` and `m.key ??= 1`
  keep `??=`'s short-circuit contract: the RHS is only evaluated, and
  `obj`/`index` only written back, when the current value is `nil`. Clean
  first pass, no bounces (1684 tests passing, up from 1675).
- **REPL `:load <path>` command to run a script into the current
  session** — merged 2026-08-03T19:31:58Z via PR #150
  (`feat/20260802-repl-load`). Added a `:load` meta-command, triggered only
  at the start of a fresh statement, and factored the per-statement
  execution loop out of `run_repl` into a shared `_run_statements` helper
  so both the prompt and `:load` get identical `CinderError` isolation and
  `ExprStmt` echoing. Loaded-file diagnostics are labeled with the file's
  path instead of `<repl>`, and per-statement isolation means one bad
  statement in the loaded file doesn't block later ones from running.
  Clean first pass, no bounces (1691 tests passing, up from 1684).
- **Standard library: `frequencies` for a list's per-element occurrence
  counts** — merged 2026-08-02T19:42:37Z via PR #151
  (`feat/20260802-frequencies`). Added to `cinder/builtins.py`, modeled
  directly on `_count_by`'s structure with the element itself as the key
  instead of a predicate result, reusing `_is_valid_key` for the same
  "not a valid map key" error `count_by`/`group_by`/`key_by` already
  raise. Plain dict accumulation preserves first-appearance insertion
  order. Clean first pass, no bounces (1699 tests passing, up from 1691).
- **Safe navigation operator `?.` for map access** — merged
  2026-08-02T19:57:28Z via PR #152 (`feat/20260802-safe-nav`). Added a new
  `QUESTION_DOT` token, an `OptionalIndex` AST node (parsed alongside
  `Index` in `_call`'s postfix loop, deliberately excluded from
  `_assignment` so `m?.key = 5` still raises `ParseError`), and
  `_evaluate_optional_index` in the interpreter, short-circuiting to `nil`
  when the base is `nil` and otherwise delegating to the existing
  `_index_get`. Single-level short-circuit only, composes with `??` for
  `m?.key ?? default`. Clean first pass, no bounces (1713 tests passing,
  up from 1699).
- **Standard library: `compact` to drop falsy elements from a list** —
  merged 2026-08-02T20:08:01Z via PR #153 (`feat/20260802-compact`).
  Added to `cinder/builtins.py`, modeled directly on `_filter`'s
  structure with arity 1 and a comprehension gated on the existing
  `is_truthy` helper, dropping only Cinder's own falsy set (`nil`,
  `false`) and keeping `0`, `0.0`, `""` and everything else. Clean first
  pass, no bounces (1719 tests passing, up from 1713).
- **Standard library: `find_last_index` — index of the last element
  matching a predicate** — merged 2026-08-02T20:19:10Z via PR #154
  (`feat/20260802-find-last-index`). Added to `cinder/builtins.py`,
  modeled directly on `_find_index`'s arity/type checks but iterating in
  reverse the same way `_last_index_of` does, returning the highest index
  where the predicate holds or `-1` if none match. Clean first pass, no
  bounces (1727 tests passing, up from 1719).
- **Exponentiation operator `**`** — merged 2026-08-03T14:09:18Z via PR
  #155 (`feat/20260802-exp-operator`). Added `TokenType.STARSTAR` and
  lexer support in `_op_or_compound_assign`, a right-associative
  `_power()` precedence level in the parser (between `_factor` and
  `_unary`, deliberately making unary minus bind tighter than `**` so
  `-2 ** 2 == 4`), and a `_power_op` in the interpreter. One bounce:
  first pass reused `_numeric_op` directly and leaked raw Python
  `ZeroDivisionError`/`OverflowError`/`complex` results instead of
  matching the existing `pow()` builtin's guards; fixed by adding
  `_power_op` mirroring `_pow()`'s try/except and complex-result
  rejection, with tests for `0 ** -1`, `2.0 ** 100000`, and
  `(-8) ** 0.5`. `**=` compound assignment intentionally deferred to
  task 2. 1744 tests passing (up from 1727).
- **Compound assignment `**=` for exponentiation** — merged
  2026-08-03T14:23:23Z via PR #157 (`feat/20260803-starstareq`). Added
  `TokenType.STARSTAREQ` and lexer support in `_op_or_compound_assign`
  (mirrors the `<`/`<=`/`<<`/`<<=` cascade pattern), and wired it into
  the parser's dict-driven `_COMPOUND_ASSIGN_OPS`/
  `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` — no interpreter changes needed
  since desugaring reuses the existing `**` `Binary`/`IndexCompoundAssign`
  paths unchanged. Covers identifier, index, and dot-access targets,
  const-target errors, and type errors. Clean first pass, no bounces
  (1752 tests passing, up from 1744).
- **Standard library: `sum_by`** — merged 2026-08-03T14:36:22Z via PR
  #158 (`feat/20260803-sum-by`). Added `sum_by(list, fn)` to
  `cinder/builtins.py`, closing the last gap in the `min_by`/`max_by`/
  `sort_by`/`group_by`/`count_by`/`distinct_by` family — a numbers-only
  fold-by-key counterpart to `sum`, modeled on `_min_max_by`'s arity/
  type checks and `_sum`'s accumulation, with empty list well-defined
  as `0` (mirroring `sum([])`) rather than erroring like `min_by`/
  `max_by` do. Clean first pass, no bounces (1759 tests passing, up
  from 1752).
- **Standard library: `reject`** — merged 2026-08-03T14:49:17Z via PR
  #159 (`feat/20260803-reject`). Added `reject(list, fn)` to
  `cinder/builtins.py`, the predicate complement of `filter` — modeled
  line for line on `_filter`'s structure with the truthiness check
  inverted (`not is_truthy(...)`), closing the same "opposite of an
  existing predicate combinator" gap `omit`/`omit_by` already closed for
  `pick`/`pick_by`. Clean first pass, no bounces (1770 tests passing,
  up from 1759). `README.md`'s Builtins list still needs `reject` added
  near `filter` — left to the Architect's next grooming pass.
- **Standard library: `find_last`** — merged 2026-08-03T19:09:52Z via PR
  #160 (`feat/20260803-find-last`). Added `find_last(string,
  substring)` to `cinder/builtins.py`, the string-search analog of
  `find_last_index` — modeled line for line on `_find`'s structure,
  swapping `str.find` for `str.rfind`. Clean first pass, no bounces
  (1779 tests passing, up from 1770). `README.md`'s Builtins list still
  needs `find_last` added near `find` — left to the Architect's next
  grooming pass.
- **Standard library: `none`** — merged 2026-08-04T~ via PR #161
  (`feat/20260803-none-builtin`). Added `none(list)` to
  `cinder/builtins.py`, closing the last gap in the `any`/`all` pair —
  modeled line for line on `_all`'s structure with the truthiness check
  inverted (`not any(is_truthy(...))`). Confirmed against actual
  interpreter truthiness (`nil`/`false` only) rather than the backlog's
  originally-stated (and wrong) expectation that `0`/`""` were falsy.
  Clean first pass, no bounces (1785 tests passing, up from 1779).
  `README.md`'s Builtins list still needs `none` added near `any`/`all`
  — left to the Architect's next grooming pass.
- **Standard library: `zip_object`** — merged 2026-08-03T19:33:20Z via
  PR #162 (`feat/20260803-zip-object`). Added `zip_object(keys,
  values)` to `cinder/builtins.py`, building a map straight from two
  parallel lists — closes the ergonomic gap between `zip()` and
  `from_entries()` that previously required manually composing
  `from_entries(zip(keys, values))`, the same shape `frequencies`
  closed between `group_by` and `len`. Clean first pass, no bounces
  (1794 tests passing, up from 1785). `README.md`'s Builtins list still
  needs `zip_object` added near `from_entries`/`items` — left to the
  Architect's next grooming pass.
- **Standard library: `symmetric_difference`** — merged 2026-08-03
  via PR #163 (`feat/20260803-symmetric-difference`). Added
  `symmetric_difference(list1, list2)` to `cinder/builtins.py`,
  completing the set-ops trio started by `union`/`intersection`/
  `difference` with the classic fourth member — implemented as
  `_difference([list1, list2]) + _difference([list2, list1])`, deduped
  per side like the other set-ops. Clean first pass, no bounces (1803
  tests passing, up from 1794). GitHub's merge API partially failed on
  this one — the squash commit landed on `main` directly but the PR
  itself never flipped to "merged" and the branch was never deleted
  (see `nightshift/HELP.md` 2026-08-03T19:47Z); PR #163 closed and its
  branch removed by hand to reconcile. `README.md`'s Builtins list
  still needs `symmetric_difference` added near `union`/`intersection`/
  `difference` — left to the Architect's next grooming pass.
- **Floor division operator `//`** — merged 2026-08-03T19:58:40Z via PR
  #164 (`feat/20260803-floor-division`). Added a `SLASHSLASH` token
  (`cinder/tokens.py`), lexed in `_op_or_compound_assign`
  (`cinder/lexer.py`, deliberately without a `//=` compound-assign form
  — same as `**` shipping before `**=`), parsed at `/`'s existing
  left-associative precedence tier alongside `%` (`cinder/parser.py`'s
  `_FACTOR` set), and evaluated by reusing `_divide_op` with
  `lambda a, b: a // b` (`cinder/interpreter.py`), inheriting its
  existing zero-division/type-check guard unchanged. Closes the gap
  between `/` (true division) and the awkward `floor(a / b)`. Clean
  first pass, no bounces (1816 tests passing, up from 1803).
  `README.md`'s Operators bullet still needs `//` added next to the
  rest of the arithmetic set — left to the Architect's next grooming
  pass.
- **Compound assignment `//=` for floor division** — merged
  2026-08-03T20:15:37Z via PR #165
  (`feat/20260803-floor-div-compound-assign`). Added a `SLASHSLASHEQ`
  token (`cinder/tokens.py`), lexed in `_op_or_compound_assign`
  (`cinder/lexer.py`) mirroring the existing `**`/`**=` branch, and
  wired into the parser's existing dict-driven compound-assign
  desugaring (`_COMPOUND_ASSIGN_OPS` and
  `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` in `cinder/parser.py`) — no
  interpreter changes needed, since `x //= 2` desugars to
  `Binary(SLASHSLASH)`, reusing `//`'s existing evaluation unchanged.
  Clean first pass, no bounces (1825 tests passing, up from 1816).
  `README.md`'s Operators bullet still needs `//=` added next to `//`
  — left to the Architect's next grooming pass.
- **Standard library: `replace_first`** — merged 2026-08-04T14:12:37Z via
  PR #166 (`feat/20260804-replace-first`). Added `replace_first(string,
  old, new)` to `cinder/builtins.py`, modeled directly on `_replace`
  (same arity-3 and argument-type checks, same three error messages
  with the name swapped in) but calling `value.replace(old, new, 1)`
  instead of `value.replace(old, new)`, giving `replace` the same
  first/last split `find`/`find_last` and `index_of`/`last_index_of`
  already have. Registered right after `"replace": _replace,`. Clean
  first pass, no bounces (1834 tests passing, up from 1825).
  `README.md`'s Builtins bullet still needs `replace_first` added next
  to `replace` — left to the Architect's next grooming pass.
- **Standard library: `interpose`** — merged 2026-08-04T14:24:54Z via
  PR #167 (`feat/20260804-interpose`). Added `interpose(list,
  separator)` to `cinder/builtins.py`, modeled on `_interleave`'s
  arity/type-check structure (single-list arity-2 check, type check
  only on the first argument), inserting `separator` before every
  element except the first via `enumerate`. Registered right after
  `"interleave": _interleave,`. Clean first pass, no bounces (1840
  tests passing, up from 1834). `README.md`'s Builtins bullet still
  needs `interpose` added next to `interleave` — left to the
  Architect's next grooming pass.
- **Standard library: `truncate`** — merged 2026-08-04T14:36:36Z via
  PR #168 (`feat/20260804-truncate`). Added `truncate(string,
  max_length, suffix)` to `cinder/builtins.py`, modeled on
  `_pad_start`/`_pad_end`'s structure including a shared
  `_check_truncate_arguments` validation helper (string first
  argument, non-bool non-negative int `max_length`, string `suffix`).
  No-op when `len(value) <= max_length`; otherwise returns
  `value[:max(0, max_length - len(suffix))] + suffix`, which can
  exceed `max_length` when `suffix` is longer than the cap — an
  accepted edge case, not a bug. Registered right after `"pad_end":
  _pad_end,`. Clean first pass, no bounces (1851 tests passing, up
  from 1840). `README.md`'s Builtins bullet still needs `truncate`
  added next to `pad_start`/`pad_end` — left to the Architect's next
  grooming pass.
- **Language: `not in` — negated membership operator** — merged
  2026-08-04T14:54:10Z via PR #169 (`feat/20260804-not-in`). Added
  `not in` as a single combined binary operator at `in`'s own
  precedence tier (synthesized `TokenType.NOT_IN` token in
  `_membership`, mirroring the compound-assign desugaring pattern),
  rather than as unary `not` applied afterward — `not x in y` was
  previously dead syntax parsing as the unrelated `(not x) in y`, now
  unchanged as a regression case. Reuses `contains_value` as-is in the
  interpreter, inheriting list/map/string membership semantics and
  error messages from `in`. Clean first pass, no bounces (1862 tests
  passing, up from 1851). `README.md`'s language feature bullets and
  `PROJECT.md`'s roadmap still need `not in` added — left to the
  Architect's next grooming pass.
- **Standard library: `chars` — split a string into a list of its
  characters** — merged 2026-08-04T19:06:55Z via PR #170
  (`feat/20260804-chars-builtin`). Added `chars(string)` returning
  `list(value)`, modeled directly on `_lines`/`_words` (same arity-1
  check, same type-check/error-message shape). Handles the empty
  string correctly (`list("") == []`) with no special case, and
  preserves whitespace characters unlike `words`. Registered right
  after `"words": _words,`. Clean first pass, no bounces (1868 tests
  passing, up from 1862). `README.md`'s Builtins bullet still needs
  `chars` added near `lines`/`words` — left to the Architect's next
  grooming pass.
- **Standard library: `is_even`/`is_odd` — integer parity predicates**
  — merged 2026-08-04T19:17:35Z via PR #171
  (`feat/20260804-is-even-odd`). Added both, modeled on `_sign` but
  using `_require_int` (not `_is_numeric`) so a whole-valued float
  like `4.0` is still a type error, not silently truncated. Correct
  for negative integers via Python's `%` semantics. Registered right
  after `"sign": _sign,`. Clean first pass, no bounces (1881 tests
  passing, up from 1868). `README.md`'s Builtins bullet still needs
  `is_even`/`is_odd` added near the other type predicates — left to
  the Architect's next grooming pass.
- **Standard library: `swap_case` — flip each character's case** —
  merged 2026-08-05T19:30:04Z via PR #172 (`feat/20260804-swap-case`).
  Added `swap_case(string)`, modeled on `_capitalize`'s structure,
  delegating to Python's `str.swapcase()` (leaves non-alphabetic
  characters untouched, empty string is a no-op). Registered right
  after `"title": _title,`. Clean first pass, no bounces (1888 tests
  passing, up from 1881). `README.md`'s Builtins bullet still needs
  `swap_case` added near `capitalize`/`title` — left to the
  Architect's next grooming pass.
- **Standard library: `pad_center` — center a string within a width**
  — merged 2026-08-05T19:42:08Z via PR #173
  (`feat/20260804-pad-center`). Added `pad_center(string, width,
  fill)`, modeled on `_pad_start`/`_pad_end`'s structure and reusing
  `_check_pad_arguments` unchanged, delegating to Python's
  `str.center()` (extra odd padding character goes left, same no-op
  `>=` width boundary as `pad_start`/`pad_end`). Registered right
  after `"pad_end": _pad_end,`. Clean first pass, no bounces (1898
  tests passing, up from 1888). `README.md`'s Builtins bullet still
  needs `pad_center` added near `pad_start`/`pad_end` — left to the
  Architect's next grooming pass.
- **Standard library: `is_palindrome` — test whether a string reads
  the same forwards and backwards** — merged 2026-08-04T19:53:41Z via
  PR #174 (`feat/20260804-is-palindrome`). Added `is_palindrome(string)`,
  modeled on `_capitalize`'s/`_title`'s structure (literal
  `value == value[::-1]`, no case-folding or whitespace stripping).
  Registered right after `"is_string": _is_string,`. Clean first pass,
  no bounces (1907 tests passing, up from 1898). `README.md`'s
  Builtins bullet still needs `is_palindrome` added near the other
  `is_*` predicates — left to the Architect's next grooming pass.
- **Standard library: `is_int`/`is_float` — split `is_number`'s single
  kind into its two concrete ones** — merged 2026-08-04T20:07:37Z via
  PR #175 (`feat/20260804-is-int-is-float`). Added `is_int(value)` and
  `is_float(value)`, modeled on `_is_list`'s/`_is_map`'s structure as
  kind predicates (no type error on non-numeric input, just `false`).
  `is_int` excludes `bool` the same way `_is_numeric` does; `is_float`
  is a plain `isinstance` check. Registered right after `"is_number":
  _is_number,`. Clean first pass, no bounces (1926 tests passing, up
  from 1907). `README.md`'s Builtins bullet still needs `is_int`/
  `is_float` added near the other `is_*` type predicates — left to the
  Architect's next grooming pass.
- **Standard library: `is_prime` — test whether an integer is prime**
  — merged 2026-08-05 via PR #176 (`feat/20260804-is-prime`). Added
  `is_prime(value)`, modeled on `_is_even`'s/`_is_odd`'s structure
  (arity-1, `_require_int` validation so a bool or non-integer raises
  rather than returning `false`), trial-dividing up to `sqrt(n)` — the
  standard minimal-correct approach for a non-performance-critical
  scripting stdlib. Registered right after `"is_odd": _is_odd,`.
- **Standard library: `is_sorted` — test whether a list is in
  non-decreasing order** — merged 2026-08-05T14:09:27Z via PR #177
  (`feat/20260805-is-sorted`). Added `is_sorted(list)`, modeled on
  `_sort`'s structure (same arity-1 and list-type checks, same
  mixed-numbers-or-strings-only validation, empty list returns `true`
  instead of `[]`), returning `value == sorted(value)` as a
  non-decreasing check. Registered right after `is_palindrome`,
  grouped with the other property predicates. Reviewer gave `VERDICT:
  LGTM`, QA gave `QA: PASS` (1946 tests passing, up from 1936, plus
  CLI smoke tests covering duplicates, empty/single-element lists,
  string ordering, and mixed-type/non-list/arity errors), both after
  the sole commit — clean merge, no bounces. `README.md`'s Builtins
  bullet still needs `is_sorted` added near the other `is_*`
  predicates — left to the Architect's next grooming pass.
- **Standard library: `is_upper`/`is_lower` — string case predicates**
  — merged 2026-08-05 via PR #178 (`feat/20260805-is-upper-lower`).
  Added `is_upper(string)`/`is_lower(string)`, modeled on
  `_swap_case`'s structure (arity-1, single string-type check),
  delegating directly to Python's `str.isupper()`/`str.islower()`.
  Registered right after `is_palindrome`, grouped with the other
  property predicates. Reviewer gave `VERDICT: LGTM`, QA gave `QA:
  PASS` (1962 tests passing, up from 1946, plus CLI smoke tests
  covering mixed case, digit-inclusive/digit-only/empty strings,
  unicode, and non-string/arity errors), both after the sole commit —
  clean merge, no bounces. `README.md`'s Builtins bullet still needs
  `is_upper`/`is_lower` added near the other `is_*` predicates — left
  to the Architect's next grooming pass.
- **Standard library: `is_alpha`/`is_digit`/`is_alnum`/`is_space` —
  string content predicates** — merged 2026-08-05 via PR #179
  (`feat/20260805-is-alpha-digit-alnum-space`). Added
  `is_alpha(string)`/`is_digit(string)`/`is_alnum(string)`/`is_space(string)`,
  modeled on `_is_upper`'s/`_is_lower`'s structure (arity-1, single
  string-type check), delegating directly to Python's
  `str.isalpha()`/`str.isdigit()`/`str.isalnum()`/`str.isspace()`.
  Registered right next to `is_upper`/`is_lower`, grouped with the
  other property predicates; all four are `false` on the empty
  string. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (1982
  tests passing, up from 1962, plus CLI smoke tests covering
  unicode and non-string/arity errors), both after the sole commit —
  clean merge, no bounces. `README.md`'s Builtins bullet still needs
  `is_alpha`/`is_digit`/`is_alnum`/`is_space` added near the other
  `is_*` predicates — left to the Architect's next grooming pass.
- **Standard library: `is_positive`/`is_negative`/`is_zero` — numeric
  sign predicates** — merged 2026-08-05 via PR #180
  (`feat/20260805-is-positive-negative-zero`). Added
  `is_positive(value)`/`is_negative(value)`/`is_zero(value)`, modeled on
  `_sign`'s structure (arity-1, `_is_numeric` guard so floats are valid
  input and bools are rejected), delegating directly to Python's `>`/`<`/`==`
  comparison operators. Registered right after `sign` in the builtins
  dict, keeping the numeric-property-predicate family contiguous.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (2004 tests passing,
  up from 1982, plus CLI smoke tests covering float/bool/non-numeric
  errors and mutual exclusivity), both after the sole commit — clean
  merge, no bounces. `README.md`'s Builtins bullet still needs
  `is_positive`/`is_negative`/`is_zero` added near `sign` — left to the
  Architect's next grooming pass.
- **Standard library: `is_unique` — list-has-no-duplicates predicate** —
  merged 2026-08-05 via PR #181 (`feat/20260805-is-unique`). Added
  `is_unique(list)`, delegating to the existing `_dedupe` helper
  (`len(_dedupe(value)) == len(value)`) rather than reimplementing
  duplicate detection, inheriting deep-equality semantics for free.
  Registered right after `is_sorted`, grouped with the other list
  property predicates. Reviewer gave `VERDICT: LGTM`, QA gave
  `QA: PASS` (2012 tests passing, up from 2004, plus CLI smoke tests
  covering deep-equality on maps, mixed numeric/string types, and
  arity/type errors), both after the sole commit — clean merge, no
  bounces. `README.md`'s Builtins bullet still needs `is_unique` added
  near the other `is_*` predicates — left to the Architect's next
  grooming pass.
- **Language: slice step — `list[start:end:step]` / `string[start:end:step]`**
  — merged 2026-08-05 via PR #182 (`feat/20260805-slice-step`). Extended
  `SliceExpr` with a `step` field; grammar parses an optional second
  `:step` in `_finish_index`, evaluator delegates bound normalization to
  Python's own `slice(start, end, step).indices(length)` rather than
  hand-rolling negative-step math. Non-int step raises `"slice step must
  be an int, got {type}"`, zero step raises `"slice step must not be
  zero"`; stepped slices remain non-assignable. Reviewer gave `VERDICT:
  CHANGES REQUESTED` first (a test named for non-int-step coverage was
  actually exercising the pre-existing non-int-start check), Engineer
  fixed the test to target the step path, then Reviewer gave `VERDICT:
  LGTM` and QA gave `QA: PASS` (2028 tests passing, plus CLI smoke tests
  covering forward/reverse/stepped slices on both lists and strings,
  zero/non-int step errors, and non-assignability) — one bounce, clean
  merge after. `README.md`'s slicing bullet and `PROJECT.md`'s roadmap
  paragraph still need the step form documented as landed — left to the
  Architect's next grooming pass.
- **Standard library: `is_divisible` — two-argument numeric divisibility
  predicate** — merged 2026-08-06 via PR #183 (`feat/20260805-is-divisible`).
  Added `_is_divisible` (`cinder/builtins.py:1084-1092`) reusing
  `_require_arity`/`_require_int` per the backlog spec, validating both
  operands before an explicit zero-divisor guard that raises a dedicated
  `CinderRuntimeError` instead of letting Python's `%` throw. Registered
  right after `is_odd`, ahead of `is_prime`. Reviewer gave `VERDICT: LGTM`,
  QA gave `QA: PASS` (2042 tests passing, plus CLI smoke tests covering sign
  combinations, zero-divisor and non-int/bool/string argument errors in both
  positions, and wrong arity), both after the sole commit — clean merge, no
  bounces.
- **Language: destructuring assignment — `[a, b] = expr;`** — merged
  2026-08-06T14:12:30Z via PR #186 (`feat/20260806-destructure-assign`).
  Added `DestructureAssign` as a new `Expr` node (`cinder/ast_nodes.py`)
  produced by `_assignment` (`cinder/parser.py`) when a bare `=` follows a
  flat-identifier `ListLiteral` LHS (optionally with a trailing rest
  spread), reusing the existing "invalid assignment target" error for
  every other shape; `_evaluate_destructure_assign`
  (`cinder/interpreter.py`) reuses `_bind_list_destructure`'s length-check
  messages and mirrors `_evaluate_assign`'s error translation
  (`KeyError` → undefined-name, `_ConstAssignError` → const message),
  assigning via `env.assign` rather than `env.define`. Scope: flat list
  patterns only, no nesting, map-pattern assignment left for a future
  task. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (2080 tests
  passing, plus CLI smoke tests covering the swap idiom, rest capture,
  destructuring an index-expression result, and all four runtime/parse
  error shapes), both after the sole commit — clean merge, no bounces.
  `README.md`'s destructuring bullet and `PROJECT.md`'s roadmap paragraph
  still need this form documented as landed — left to the Architect's
  next grooming pass.
- **Standard library: `is_disjoint` — no-common-elements predicate for
  lists** — merged 2026-08-06T14:27:06Z via PR #187
  (`feat/20260806-is-disjoint`). Added `_is_disjoint` to
  `cinder/builtins.py`, registered right after `is_superset`; reuses
  `_require_two_lists` for arity/type validation and `_contains_value`
  (deep equality) for membership, mirroring `_is_subset`/`_is_superset`'s
  structure exactly — `not any(_contains_value(list2, element) for
  element in list1)`. Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS`
  (2089 tests passing plus CLI smoke tests), both after the sole commit —
  clean merge, no bounces. `README.md`'s Builtins bullet still needs
  `is_disjoint` added near the rest of the set-ops family — left to the
  Architect's next grooming pass.
- **Language: map-pattern destructuring assignment — `{a, b} = expr;`** —
  merged 2026-08-06T14:44:56Z via PR #188
  (`feat/20260806-map-destructure-assign`). Extended map-pattern
  destructuring to plain assignment (the map-shaped counterpart to
  `[a, b] = expr;`, PR #186): added an `is_map` flag to the existing
  `DestructureAssign` AST node, taught `_brace_statement` a third
  speculative parse attempt for `{a, b} = expr;` tried between the
  existing map-literal-expression attempt and the `_block()` fallback,
  and extended `_evaluate_destructure_assign` with a map branch that
  assigns (not defines) into already-declared bindings via a new
  `_bind_map_destructure` extraction shared with `DestructureLetStmt`'s
  inline map handling. Flat patterns only, no nesting/renaming/rest.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (2104 tests passing
  plus CLI smoke tests covering binding, const/undefined/missing-key/
  non-map errors, and non-interference with map literals and empty
  blocks), both after the sole commit — clean merge, no bounces.
  `README.md`'s destructuring bullet and `PROJECT.md`'s roadmap
  paragraph still need this form documented as landed — left to the
  Architect's next grooming pass.
- **Standard library: `is_anagram` — two-string character-multiset
  predicate** — merged 2026-08-07 via PR #189
  (`feat/20260806-is-anagram`). Added `is_anagram(string1, string2)` to
  `cinder/builtins.py`, registered right after `is_palindrome`, using
  `collections.Counter(string1) == Counter(string2)` for the comparison
  (case-sensitive, no whitespace stripping). Reviewer gave `VERDICT:
  LGTM`, QA gave `QA: PASS` (2114 tests passing plus CLI smoke tests
  covering true/false/empty/length-mismatch/order-independence/
  case-sensitivity/non-string-argument/arity cases), both after the sole
  commit — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need `is_anagram` moved from
  backlog to landed — left to the Architect's next grooming pass.
- **Standard library: `is_permutation` — two-list character/element-multiset
  predicate** — merged 2026-08-07 via PR #190
  (`feat/20260806-is-permutation`). Added `is_permutation(list1, list2)` to
  `cinder/builtins.py`, registered right after `is_anagram`, using
  `values_equal`-based O(n²) multiset removal (length short-circuit, then
  match-and-remove against a working copy of `list2`) instead of
  `Counter`/`set`, since list elements can be unhashable (nested
  lists/maps) — the same fallback `_dedupe` already uses. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (2123 tests passing plus CLI smoke
  tests covering reordered/count-mismatch/empty/length-mismatch/nested-list/
  int-string-distinction/non-list-argument/arity cases), both after the
  sole commit — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need `is_permutation` moved from
  backlog to landed — left to the Architect's next grooming pass.
- **Standard library: `is_numeric` — string numeric-content predicate** —
  merged 2026-08-07 via PR #191 (`feat/20260806-is-numeric`). Added
  `is_numeric(string)` to `cinder/builtins.py`, registered right after
  `is_ascii` in the string content-predicate family, delegating to
  `str.isnumeric()` via a new `_is_numeric_string` function (named to
  avoid shadowing the existing unrelated `_is_numeric` int/float helper).
  Broader than `is_digit`: also true for fraction characters (`"½"`),
  superscript/subscript digits, and non-Latin numerals. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (2130 tests passing plus CLI smoke
  tests covering the numeric-vs-digit distinguishing case, empty string,
  non-digit, non-string-arg, and arity-error cases), both after the sole
  commit — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need `is_numeric` moved from
  backlog to landed — left to the Architect's next grooming pass.
- **Standard library: `is_blank` — whitespace-or-empty string predicate**
  — merged 2026-08-06 via PR #192 (`feat/20260806-is-blank`). Added
  `is_blank(string)` to `cinder/builtins.py`, registered right after
  `is_space`, filling the gap `is_space` deliberately leaves open:
  `str.isspace()` is `false` on the empty string, so `is_blank` checks
  `value == "" or value.isspace()` instead of delegating to a single
  `str.is*()` method like the rest of the content-predicate family.
  Reviewer gave `VERDICT: LGTM`, QA gave `QA: PASS` (2137 tests passing
  plus CLI/REPL smoke tests covering empty, spaces-only, other-whitespace,
  non-blank, padded-non-blank, non-string-arg, and arity-error cases),
  both after the sole commit — clean merge, no bounces. `README.md`'s
  Builtins bullet and `PROJECT.md`'s roadmap paragraph still need
  `is_blank` moved from backlog to landed — left to the Architect's next
  grooming pass.
- **Standard library: `factorial` — numeric builtin rounding out
  `pow`/`gcd`/`lcm`** — merged 2026-08-07 via PR #193
  (`feat/20260806-factorial`). Added `factorial(n)` to
  `cinder/builtins.py`, registered right after `lcm`, delegating to
  `math.factorial` with the same arity/type-guard structure as
  `gcd`/`lcm` and a domain-error split for negative input mirroring
  `_log`'s type-vs-domain-error convention. Reviewer gave `VERDICT: LGTM`,
  QA gave `QA: PASS` (2146 tests passing, 26 subtests, plus CLI/REPL
  smoke tests covering 0/1/5/10/20 including bignum precision at `20!`,
  negative/float/bool type and domain errors, and arity errors), both
  after the sole commit — clean merge, no bounces. `README.md`'s
  Builtins bullet and `PROJECT.md`'s roadmap paragraph still need
  `factorial` moved from backlog to landed — left to the Architect's next
  grooming pass.
- **Standard library: `is_pangram` — alphabet-coverage string predicate**
  — merged 2026-08-07 via PR #194 (`feat/20260806-is-pangram`). Added
  `is_pangram(string)` to `cinder/builtins.py`, registered right after
  `is_permutation` in the string/list multiset-predicate cluster,
  case-insensitive alphabet-coverage check via
  `set(string.ascii_lowercase) <= set(value.lower())`. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (2154 tests passing, plus CLI smoke
  tests covering both canonical pangrams, non-pangram, empty string,
  all-uppercase casing, and the exact-26-letter case, plus non-string and
  arity errors), both after the sole commit — clean merge, no bounces.
  `README.md`'s Builtins bullet and `PROJECT.md`'s roadmap paragraph
  still need `is_pangram` moved from backlog to landed — left to the
  Architect's next grooming pass.
- **Standard library: `digit_sum` — sum of an integer's decimal digits**
  — merged 2026-08-07 via PR #195 (`feat/20260806-digit-sum`). Added
  `digit_sum(n)` to `cinder/builtins.py`, registered right after
  `is_prime` in the integer-property cluster, normalizing sign via
  `abs(value)` before summing digits with
  `sum(int(digit) for digit in str(abs(value)))`. Reviewer gave
  `VERDICT: LGTM`, QA gave `QA: PASS` (2162 tests passing, plus CLI smoke
  tests covering zero, single/multi-digit, negative-sign-ignored, large
  ints, float/bool type errors, and arity errors), both after the sole
  commit — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need `digit_sum` moved from
  backlog to landed — left to the Architect's next grooming pass.
- **Language: list comprehensions** — merged 2026-08-07T14:31:03Z via
  PR #196 (`feat/20260807-list-comprehensions`). Added `[expr for x in
  iterable]` / `[expr for x in iterable if cond]` to the list-literal
  grammar: new `ListComprehension` AST node, `_list_literal` lookahead
  for `FOR` after the first element to dispatch to a new
  `_list_comprehension`, and `_evaluate_list_comprehension` mirroring
  `_execute_for`'s iterable-type dispatch and fresh-per-iteration
  `Environment` for closure correctness. Reviewer's first pass found a
  real bug (`[...[1,2] for x in [1,2]]` parsed a `Spread` as the
  comprehension head and crashed the interpreter with a raw Python
  `TypeError` instead of a `CinderError`); Engineer fixed it by
  rejecting a `Spread` head at parse time with a `ParseError`, Reviewer
  then gave `VERDICT: LGTM` and QA gave `QA: PASS` (2175 tests passing,
  plus CLI smoke tests covering transform, filter, empty
  iterable/filter, string/map iterables, per-iteration closures,
  non-iterable errors, and the fixed spread-head case) — one bounce,
  fixed same night. `README.md`'s language-features bullet list and
  `PROJECT.md`'s roadmap paragraph still need list comprehensions moved
  from backlog to landed — left to the Architect's next grooming pass.
- **Language: map comprehensions** — merged 2026-08-07 via PR #197
  (`feat/20260807-map-comprehensions`). Added the map-literal
  counterpart to list comprehensions — `{k: v for x in iterable}` /
  `{k: v for x in iterable if cond}` — mirroring PR #196's grammar/AST/
  interpreter shape exactly: new `MapComprehension` AST node, `_map_literal`
  lookahead for `FOR` after the first `key: value` pair (with a leading
  `Spread` head rejected via `ParseError`, matching the list-comprehension
  precedent), and `_evaluate_map_comprehension` reusing the existing
  `_is_valid_key` check and fresh-per-iteration `Environment` for closure
  correctness. Colliding keys collapse to the last write, matching plain
  map-literal semantics. Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2188 tests passing, plus CLI smoke tests covering transform,
  filter, empty iterable, key/value independence, collision, unhashable
  keys, non-iterable source, spread-head rejection, and per-iteration
  closure capture) — clean merge, no bounces. `README.md`'s
  language-features bullet list and `PROJECT.md`'s roadmap paragraph
  still need map comprehensions moved from backlog to landed — left to
  the Architect's next grooming pass.
- **Standard library: `is_perfect_square`** — merged 2026-08-07T19:31:10Z
  via PR #198 (`feat/20260807-is-perfect-square`). Added
  `is_perfect_square(n)` to `cinder/builtins.py`'s integer-property
  predicate cluster, next to `digit_sum`, using `math.isqrt` for exact
  bignum-safe computation instead of a float `** 0.5` path. Negative
  input returns `false` rather than erroring, matching `is_prime`'s
  convention; `bool` rejected via the shared `_require_int` check.
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2199 tests
  passing, plus CLI smoke tests covering true/false cases, a large
  bignum perfect square past float precision, and float/bool type
  rejection) — clean merge, no bounces. `README.md`'s Builtins bullet
  and `PROJECT.md`'s roadmap paragraph still need `is_perfect_square`
  moved from backlog to landed — left to the Architect's next grooming
  pass.
- **Standard library: `is_armstrong`** — merged 2026-08-07T19:41:28Z via
  PR #199 (`feat/20260807-is-armstrong`). Added `is_armstrong(n)` to
  `cinder/builtins.py`'s integer-property predicate cluster, next to
  `is_perfect_square`, checking whether `n` equals the sum of its own
  decimal digits each raised to the digit-count power. Negative input
  returns `false` rather than erroring, matching `is_perfect_square`'s
  convention; `bool` rejected via the shared `_require_int` check.
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2210 tests
  passing, plus CLI smoke tests covering true/false cases including a
  4-digit Armstrong number beyond the specced cases, and negative/type
  rejection) — clean merge, no bounces. `README.md`'s Builtins bullet
  and `PROJECT.md`'s roadmap paragraph still need `is_armstrong` moved
  from backlog to landed — left to the Architect's next grooming pass.
- **Standard library: `is_leap_year`** — merged 2026-08-07T19:52:27Z via
  PR #200 (`feat/20260807-is-leap-year`). Added `is_leap_year(year)` to
  `cinder/builtins.py`'s integer-property predicate cluster, next to
  `is_armstrong`, implementing the Gregorian leap-year rule (divisible
  by 4, except century years unless also divisible by 400). Zero and
  negative years compute without a domain error, matching
  `is_perfect_square`/`is_armstrong`'s convention; `bool` rejected via
  the shared `_require_int` check. Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2220 tests passing, plus CLI smoke tests covering
  century/ordinary leap and non-leap years, zero, negative years, and
  float/bool type rejection) — clean merge, no bounces. `README.md`'s
  Builtins bullet and `PROJECT.md`'s roadmap paragraph still need
  `is_leap_year` moved from backlog to landed — left to the Architect's
  next grooming pass.
- **Standard library: `reverse_int`** — merged 2026-08-07T20:02:06Z via
  PR #201 (`feat/20260807-reverse-int`). Added `reverse_int(n)` to
  `cinder/builtins.py`, next to `digit_sum` in the integer-property
  cluster, reversing an int's decimal digits while preserving sign
  (leading zeros in the reversed form disappear via `int()` conversion,
  matching how no integer literal can carry leading zeros). Reviewer
  gave `VERDICT: LGTM` and QA gave `QA: PASS` (2229 tests passing, plus
  CLI smoke tests covering zero, single/multi-digit, negative,
  trailing-zero, and float/bool type rejection) — clean merge, no
  bounces. `README.md`'s Builtins bullet and `PROJECT.md`'s roadmap
  paragraph still need `reverse_int` moved from backlog to landed —
  left to the Architect's next grooming pass.
- **Standard library: `is_perfect_number`** — merged 2026-08-07T20:12:14Z
  via PR #202 (`feat/20260807-is-perfect-number`). Added
  `is_perfect_number(n)` to `cinder/builtins.py`, joining the
  integer-property predicate cluster: sums proper divisors via
  trial-division up to `math.isqrt(value)`, pairing each divisor with its
  complement and skipping the double-count on perfect squares. Values
  below 2 return `false` with no domain error, matching the cluster's
  convention. Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2239
  tests passing, plus CLI smoke tests covering perfect numbers up to the
  5th (33550336), an abundant number, a perfect square, and float/bool
  type rejection) — clean merge, no bounces. `README.md`'s Builtins
  bullet and `PROJECT.md`'s roadmap paragraph still need
  `is_perfect_number` moved from backlog to landed — left to the
  Architect's next grooming pass.
- **Standard library: `is_abundant`** — merged 2026-08-08T~ via PR #203
  (`feat/20260807-is-abundant`). Added `is_abundant(n)` to
  `cinder/builtins.py`, joining the integer-property predicate cluster
  next to `is_perfect_number`: sums proper divisors via the same
  `math.isqrt`-bounded trial-division loop, kept inline rather than
  factored into a shared helper (in scope stayed a single-builtin task),
  returning `total > value`. Non-positive input returns `false` with no
  domain error, matching the cluster's convention; `value == 1` is a
  real (non-early-outed) case since its divisor sum is `0`. Reviewer
  gave `VERDICT: LGTM` and QA gave `QA: PASS` (2250 tests passing, plus
  CLI smoke tests covering abundant/perfect/deficient numbers, the
  smallest odd abundant number (945), zero/negative input, and
  float/bool type rejection) — clean merge, no bounces. `README.md`'s
  Builtins bullet and `PROJECT.md`'s roadmap paragraph still need
  `is_abundant` moved from backlog to landed — left to the Architect's
  next grooming pass.
- **Standard library: `is_deficient`** — merged 2026-08-08T14:09:37Z via
  PR #204 (`feat/20260807-is-deficient`). Added `is_deficient(n)` to
  `cinder/builtins.py`, completing the perfect/abundant/deficient
  divisor-sum trio next to `is_perfect_number`/`is_abundant`: same
  `math.isqrt`-bounded trial-division sum, returning `total < value`.
  Non-positive input returns `false` with no domain error, matching the
  cluster's convention. Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2260 tests passing, plus CLI smoke tests covering
  deficient/perfect/abundant numbers, zero/negative input, and
  float/bool type rejection) — clean merge, no bounces. `README.md`'s
  Builtins bullet and `PROJECT.md`'s roadmap paragraph still need
  `is_deficient` moved from backlog to landed — left to the Architect's
  next grooming pass.
- **Language: arrow function expressions `(params) => expr`** — merged
  2026-08-08T14:26:37Z via PR #205 (`feat/20260808-arrow-functions`).
  Added arrow-function syntax as sugar for the existing anonymous `fn`
  expression — parenthesized parameter list + expression body only
  (`(x) => x * 2`, `(a, b = 1) => a + b`, `(a, ...rest) => rest`),
  desugaring entirely into the existing `FnExpr` AST node with zero
  interpreter changes. Lexer gained a `FAT_ARROW` token; the parser
  disambiguates `(` at expression position from plain grouping via a
  speculative parse/backtrack, the same pattern `_brace_statement`
  already used for `{`-disambiguation. Reviewer gave `VERDICT: LGTM`
  (traced the backtracking logic by hand against grouping/default-param
  edge cases, confirmed no `_fn_depth`/`_loop_labels` side effects leak
  from the speculative branch) and QA gave `QA: PASS` (2284 tests
  passing, plus CLI/REPL smoke tests covering zero/one/two-param arrows,
  arrow-as-callback to `map`/`filter`, nesting/closures, and clean
  rejection of out-of-scope forms like bare-identifier and block-bodied
  arrows) — clean merge, no bounces. This closes out the language-depth
  task injected to break a seven-cycle stdlib-predicate breadth streak.
  `README.md` still needs a short arrow-function mention and
  `PROJECT.md`'s roadmap paragraph still needs it moved from backlog to
  landed — left to the Architect's next grooming pass.
- **Standard library: `is_palindrome_number`** — merged 2026-08-08T14:38:26Z
  via PR #206 (`feat/20260808-is-palindrome-number`). Added
  `is_palindrome_number(n)` to `cinder/builtins.py` next to `reverse_int`,
  testing whether an integer's decimal digits read the same forwards and
  backwards — the numeric sibling to the existing string `is_palindrome`.
  Negative input always short-circuits to `false`; computation reuses
  direct digit-string reversal (`str(value) == str(value)[::-1]`) rather
  than routing through `reverse_int`'s sign-handling logic. Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2294 tests passing plus CLI/REPL
  smoke tests) — clean merge, no bounces. `README.md`'s Builtins bullet
  and `PROJECT.md`'s roadmap paragraph still need updating — left to the
  Architect's next grooming pass.
- **Standard library: `digital_root`** — merged 2026-08-08T14:49:27Z via
  PR #207 (`feat/20260808-digital-root`). Added `digital_root(n)` to
  `cinder/builtins.py` next to `digit_sum`/`reverse_int`, using the O(1)
  closed-form digital-root identity (`1 + (value - 1) % 9`, with `0` as
  the fixed point) rather than a repeated-summing loop, since Cinder ints
  are arbitrary-precision. Sign is ignored, matching `digit_sum`'s
  convention. Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2303
  tests passing plus CLI/REPL smoke tests, including a 24-digit bignum
  case) — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need updating — left to the
  Architect's next grooming pass.
- **Language: bare single-identifier arrow functions `x => expr`** —
  merged 2026-08-08T18:43:07Z via PR #208 (`feat/20260808-bare-arrow-fn`).
  Extended arrow-function support (PR #205) to the unparenthesized
  single-parameter form, via a one-token-lookahead branch in `_primary`'s
  `IDENTIFIER` case (no backtracking needed, since `FAT_ARROW` can't
  legally follow a bare identifier anywhere else in the grammar), reusing
  `_try_arrow_function`'s Block/ReturnStmt-wrapping shape. Block bodies
  stay out of scope, matching the parenthesized form's existing boundary.
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2314 tests passing
  plus CLI/REPL smoke tests) — clean merge, no bounces. `README.md`'s
  arrow-function bullet and `PROJECT.md`'s roadmap paragraph still need
  updating — left to the Architect's next grooming pass.
- **Standard library: `is_composite`** — merged 2026-08-08T18:43:11Z via
  PR #209 (`feat/20260808-is-composite`). Added `is_composite(n)` to
  `cinder/builtins.py` next to `is_prime`, completing the classical
  prime/composite/neither three-way split of the non-negative integers.
  Gives its own `value < 4` early-out rather than negating `is_prime`'s
  result (which would incorrectly return `true` for `0`, `1`, and every
  negative number), then reuses `is_prime`'s trial-division loop. Reviewer
  gave `VERDICT: LGTM` and QA gave `QA: PASS` (2314 tests passing plus
  CLI/REPL smoke tests) — clean merge, no bounces. `README.md`'s Builtins
  bullet and `PROJECT.md`'s roadmap paragraph still need updating — left
  to the Architect's next grooming pass.
- **Standard library: `is_power_of_two`** — merged 2026-08-08T18:56:39Z
  via PR #210 (`feat/20260808-is-power-of-two`). Added
  `is_power_of_two(n)` to `cinder/builtins.py` next to `is_composite`,
  using the classic bit trick (`n > 0 and (n & (n - 1)) == 0`) rather
  than a loop or `log2` — the first builtin in the integer-property
  cluster to use Cinder's own bitwise `&` operator. Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2334 tests passing plus
  CLI/REPL smoke tests, including a 2^51 bignum-adjacent case) — clean
  merge, no bounces. `README.md`'s Builtins bullet and `PROJECT.md`'s
  roadmap paragraph still need updating — left to the Architect's next
  grooming pass.
- **Language: block-bodied arrow functions `(params) => { ... }` and
  `x => { ... }`** — merged 2026-08-08T19:09:27Z via PR #211
  (`feat/20260808-arrow-block-body`). Extended both arrow-function forms
  to accept a block body via a shared `_arrow_body` parser helper that
  mirrors `_fn_params_and_body`'s `_fn_depth`/`_loop_labels` bookkeeping,
  so `return`/`break`/`continue` inside a block-bodied arrow behave
  exactly like an ordinary `fn` body; block bodies do not implicitly
  return their last expression. No interpreter changes were needed —
  `call_value` already executes the body generically. Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2345 tests passing plus
  CLI smoke tests covering implicit-no-return, map-callback use, and
  own-loop break/continue) — clean merge, no bounces. `README.md`'s
  arrow-function bullet and `PROJECT.md`'s roadmap paragraph still need
  updating — left to the Architect's next grooming pass.
- **Standard library: `is_palindrome_list`** — merged 2026-08-08T19:22:10Z
  via PR #212 (`feat/20260808-is-palindrome-list`). Added
  `is_palindrome_list(list)` to `cinder/builtins.py`, registered right
  after `is_power_of_two`, completing the palindrome predicate family
  alongside `is_palindrome` (strings) and `is_palindrome_number`
  (integers). Uses `values_equal` for deep equality rather than
  `==`/`[::-1]`, so nested lists/maps compare structurally. Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2353 tests passing plus CLI
  smoke tests covering nested-value deep equality, wrong-type, and
  wrong-arity cases) — clean merge, no bounces. `README.md`'s Builtins
  bullet and `PROJECT.md`'s roadmap paragraph still need updating — left
  to the Architect's next grooming pass.
- **Standard library: `is_coprime`** — merged 2026-08-08T19:33:31Z via
  PR #213 (`feat/20260808-is-coprime`). Added `is_coprime(a, b)` to
  `cinder/builtins.py`, registered right after `is_divisible`, the other
  two-argument member of the integer-property predicate cluster
  (`is_even`/`is_odd`/`is_divisible`/`is_prime`/`is_composite`). Calls
  `math.gcd` directly (rather than routing through the existing `gcd()`
  builtin) and checks `== 1`; `math.gcd`'s handling of negative and zero
  arguments needed no special-casing. Reviewer gave `VERDICT: LGTM` and
  QA gave `QA: PASS` (2362 tests passing plus CLI smoke tests covering
  zero, negative, and equal-value edge cases plus wrong-type/wrong-arity
  errors) — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need updating — left to the
  Architect's next grooming pass.
- **Language: safe navigation bracket indexing `obj?.[expr]`** — merged
  2026-08-09T14:09:39Z via PR #214 (`feat/20260808-optional-bracket-
  index`). Extended `_finish_optional_dot` (`cinder/parser.py`) to check
  for a `[` after `?.` and, when present, parse a plain (non-slice)
  index the same way `_finish_index` does before building the existing
  generic `OptionalIndex` node — falling through to the prior
  identifier-only path otherwise. No interpreter changes were needed:
  `_evaluate_optional_index` already short-circuited to `nil` on a `nil`
  receiver and delegated to `_index_get`, the same helper plain `[...]`
  indexing already used for both lists (with negative-index
  normalization) and maps. Slicing (`obj?.[a:b]`) is intentionally
  unsupported and simply falls through to the existing `RBRACKET`
  consume's normal `ParseError`; assignment through the bracket form was
  already rejected for free by `_assignment`'s existing target-type
  check. Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2376
  tests passing plus CLI/REPL smoke tests covering computed keys,
  negative indices, nil short-circuiting through nested chains, slice
  rejection, and assignment rejection) — clean merge, no bounces.
  `README.md`'s safe navigation bullet and `PROJECT.md`'s roadmap
  paragraph still need updating — left to the Architect's next grooming
  pass.
- **Standard library: `is_fibonacci`** — merged 2026-08-09T14:23:17Z via
  PR #215 (`feat/20260809-is-fibonacci`). Added `is_fibonacci(n)` to
  `cinder/builtins.py`, registered right after `is_coprime`. Tests
  Fibonacci-sequence membership via the closed-form `5n² + 4` or
  `5n² - 4` perfect-square identity, using `math.isqrt` the same
  exact-integer way `is_perfect_square` already does rather than
  generating the sequence up to `n`; negative input answers `false`
  rather than raising, matching `is_perfect_square`'s convention.
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2385 tests
  passing plus CLI smoke tests covering zero, small and large real
  Fibonacci numbers, non-members, negative input, and wrong-type/
  wrong-arity errors) — clean merge, no bounces.
- **Standard library: `is_happy_number`** — merged 2026-08-09T14:34:55Z
  via PR #216 (`feat/20260809-is-happy-number`). Added
  `is_happy_number(n)` to `cinder/builtins.py`, registered right after
  `is_fibonacci`. Tests the happy-number recurrence (repeatedly replace
  `n` with the sum of the squares of its decimal digits; happy if this
  reaches `1`, unhappy if it instead falls into a cycle) using a `set`
  of previously-seen values for exact cycle detection rather than a
  fixed iteration cap; negative input answers `false` rather than
  raising, matching `is_perfect_square`'s convention. Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2393 tests passing plus CLI
  smoke tests covering the base case, known happy numbers, the
  canonical 4-cycle, zero, negative input, a large multi-digit input,
  and wrong-type/wrong-arity errors) — clean merge, no bounces.
  `README.md`'s Builtins bullet and `PROJECT.md`'s roadmap paragraph
  still need updating — left to the Architect's next grooming pass.
- **Language: numeric literal underscores (`1_000_000`, `0xFF_FF`,
  `3.14_159`)** — merged 2026-08-09T14:48:59Z via PR #217
  (`feat/20260809-numeric-underscores`). Taught `_number` and
  `_prefixed_int` in `cinder/lexer.py` to accept `_` as a digit-group
  separator, only consumed between two valid digits (leading, trailing,
  and doubled underscores stop consumption rather than raising, falling
  through to identifier/error handling exactly like any other
  non-digit character). `lexeme` keeps the raw underscores; `value_str`/
  `int()`/`float()` conversion strips them first. Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2402 tests passing plus CLI
  smoke tests covering hex/binary/octal/float/int forms and the
  trailing/doubled/leading-underscore edge cases) — clean merge, no
  bounces. `README.md`'s numeric-literals bullet and `PROJECT.md`'s
  roadmap paragraph still need updating — left to the Architect's next
  grooming pass.
- **Standard library: `is_triangular` — triangular-number predicate** —
  merged 2026-08-09T15:00:32Z via PR #218
  (`feat/20260809-is-triangular`). Added `is_triangular(n)` to
  `cinder/builtins.py` next to `is_happy_number`, using the same
  closed-form `8n + 1` perfect-square check (`math.isqrt`) as
  `is_fibonacci`/`_is_perfect_square` rather than an accumulating loop;
  negative input answers `false` rather than raising, matching
  `is_perfect_square`'s convention. Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2410 tests passing plus CLI smoke tests covering
  true/false/negative/large/type/arity cases) — clean merge, no
  bounces. `README.md`'s Builtins bullet and `PROJECT.md`'s roadmap
  paragraph still need updating — left to the Architect's next grooming
  pass.
- **Language: destructuring loop variables in list/map comprehensions**
  — merged 2026-08-09T19:23:48Z via PR #219
  (`feat/20260809-destructuring-comprehension`). Extended
  `ListComprehension`/`MapComprehension` (`cinder/ast_nodes.py`) with
  optional `names`/`rest` fields alongside `var_name`, mirroring
  `ForStmt`; parser and interpreter reuse the existing
  `_destructure_list_pattern()` and `_bind_list_destructure()` helpers
  already shared by for-loops and `let`-destructuring, so error
  behavior (non-list item, wrong pattern arity) matches the for-loop
  exactly. Reviewer gave `VERDICT: LGTM` (with a non-blocking cosmetic
  nit about a stray assertion in `test_destructure_with_filter`) and QA
  gave `QA: PASS` (2427 tests passing plus CLI smoke tests covering
  list/map comprehension destructuring, rest elements, `if` filters,
  and non-list/wrong-arity error cases) — clean merge, no bounces.
  `README.md`'s comprehension bullets and `PROJECT.md`'s roadmap
  paragraph still need updating — left to the Architect's next grooming
  pass.
- **Standard library: `lerp` — linear interpolation** — merged
  2026-08-09T19:34:09Z via PR #220 (`feat/20260809-lerp`). Added
  `lerp(a, b, t)` to `cinder/builtins.py` next to `clamp`, computing the
  unclamped `a + (b - a) * t` (matching most graphics/game-math
  libraries; a caller wanting clamping composes it explicitly via the
  existing `clamp(t, 0, 1)`), with no `a == b` short-circuit and no
  `lo <= hi`-style relationship check between `a`/`b` since `a > b` is a
  valid downward interpolation. Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2438 tests passing plus CLI smoke tests covering the
  halfway case, both `t` endpoints, extrapolation above 1 and below 0,
  `a > b`, `a == b`, and non-numeric/wrong-arity error cases) — clean
  merge, no bounces. `README.md`'s Builtins bullet and `PROJECT.md`'s
  roadmap paragraph still need updating — left to the Architect's next
  grooming pass.
- **Standard library: `is_emirp` — emirp predicate** — merged
  2026-08-11T14:11:32Z via PR #222 (`feat/20260811-is-emirp`). Added
  `is_emirp(n)` to `cinder/builtins.py` next to `is_composite`,
  completing the prime-family cluster alongside `is_prime`/
  `is_composite`. Inlines `is_composite`'s own trial-division-to-
  `sqrt(n)` primality loop rather than factoring a shared helper, and
  `_reverse_int`'s `str(value)[::-1]` digit-reversal technique, then
  checks the original and reversed values are both prime and unequal;
  palindromic primes (`2`, `11`) are excluded since their reversal
  equals themselves. Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2461 tests passing plus CLI smoke tests covering classic
  emirp pairs in both directions, palindromic-prime exclusion,
  non-prime/sub-threshold/negative inputs, and float/bool/arity error
  paths) — clean merge, no bounces. `README.md`'s Builtins bullet and
  `PROJECT.md`'s roadmap paragraph still need updating — left to the Architect's next
  grooming pass.
- **Language: map-destructuring `for`-loop variables** — merged
  2026-08-09T19:49:41Z via PR #221 (`feat/20260809-for-map-destructure`).
  Crossed the existing list-destructuring `for`-loop
  (`for [k, v] in items(m) { ... }`) with the existing map-destructuring
  `let` (`let {a, b} = expr;`): `ForStmt` (`cinder/ast_nodes.py`) gained
  an `is_map` field mirroring `DestructureLetStmt`'s own flag, the
  map-pattern identifier-collecting loop inlined in
  `_destructure_let_statement` was extracted into a shared
  `_destructure_map_pattern` parser helper reused by both `let {a, b} =
  ...` and the new `for {a, b} in ...` branch, and `_execute_for` now
  dispatches to the existing `_bind_map_destructure` interpreter helper
  when `stmt.is_map`, reusing the same `CinderRuntimeError` messages
  `let {a, b} = ...` already raises for a non-map item or a missing key
  — pure plumbing, no new binding logic. Reviewer gave `VERDICT: LGTM`
  and QA gave `QA: PASS` (2452 tests passing plus CLI smoke tests
  covering the motivating multi-name case, single-name patterns,
  non-map/missing-key errors, and a labeled `break outer` through a
  nested loop) — clean merge, no bounces. `README.md`'s `for`-loop
  bullet and `PROJECT.md`'s roadmap paragraph updated in this same
  grooming pass.
- **Language: list/map-destructuring function parameters** — merged
  2026-08-11T14:41:43Z via PR #223 (`feat/20260811-fn-destructure-params`).
  Added a `Param` dataclass to `cinder/ast_nodes.py` generalizing
  `FnDecl`/`FnExpr`'s old `(name, default)` tuple params to also carry
  `names`/`rest`/`is_map` for destructuring parameters; `_fn_param` in
  `cinder/parser.py` now accepts a `[...]`/`{...}` pattern in place of a
  plain identifier, reusing `_destructure_list_pattern`/
  `_destructure_map_pattern`; `CinderFunction.arity` and `call_value` in
  `cinder/interpreter.py` iterate `Param` objects and dispatch to the
  existing `_bind_list_destructure`/`_bind_map_destructure` helpers for
  destructuring params. First review round caught a real correctness
  bug: the new `LBRACKET`/`LBRACE` branches skipped the `seen_default`
  ordering check, so `fn f(a = 1, [b, c]) { ... }` parsed successfully
  and then crashed with a raw Python `TypeError` at call time instead of
  a clean `ParseError`; fixed by raising the same
  "parameter without a default value follows a parameter with one"-style
  `ParseError` in both destructuring branches, with two new parser tests
  covering the list and map cases. Second round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2480 tests passing plus CLI
  smoke tests covering named/anonymous/arrow-fn destructuring params,
  combined pattern-level and parameter-list-level rest, and the fixed
  default-ordering error) — one bounce, then clean.
- **Standard library: `divisors`** — merged 2026-08-11T19:35:51Z via PR #224
  (`feat/20260811-divisors`). Added `divisors(n)` to `cinder/builtins.py`,
  registered after `is_deficient`, returning the sorted list of every
  positive integer that evenly divides `n` (including `1` and `n` itself).
  Mirrors `_is_perfect_number`'s trial-division-to-`sqrt(n)` shape but
  collects divisor pairs into a list instead of summing them; `n < 1` raises
  a domain error since `0`/negatives have no valid divisor list. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2490 tests
  passing plus CLI smoke tests covering golden-path cases, perfect squares,
  and domain/type/arity errors).
- **Language: optional call chaining (`f?.(...)`)** — merged
  2026-08-11T19:50:06Z via PR #225 (`feat/20260811-optional-call-chaining`).
  Extended the safe-navigation family (`m?.key`, `obj?.[expr]`) to cover
  calls: added `OptionalCall` to `cinder/ast_nodes.py`, parser support via
  `_finish_optional_call`, and an interpreter evaluator that short-circuits
  to `nil` (without evaluating arguments) when the callee is `nil`, sharing
  argument evaluation with plain `Call` through a new
  `_evaluate_call_arguments` helper. Single-level only, matching the rest of
  the `?.` family. Clean first round: Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2507 tests passing plus CLI smoke tests covering
  short-circuit, call-through, argument-not-evaluated, chaining, and
  non-callable-still-raises cases).
- **Standard library: `is_rotation` — string rotation predicate** — merged
  2026-08-11T20:00:50Z via PR #226 (`feat/20260811-is-rotation`). Added
  `is_rotation(a, b)` to `cinder/builtins.py`, registered right after
  `is_anagram` in the two-string predicate family: strings must be equal
  length, then the standard doubled-string trick (`b in (a + a)`)
  determines whether `b` is a rotation of `a`, stricter than `is_anagram`'s
  same-multiset test. Clean first round: Reviewer gave `VERDICT: LGTM` and
  QA gave `QA: PASS` (2517 tests passing plus CLI smoke tests covering
  true rotation, self-rotation, both-empty, anagram-but-not-rotation,
  length mismatch, symmetry, and both type-error messages).
- **Language: map-destructuring loop variables in list/map comprehensions**
  — merged 2026-08-12T20:15:25Z via PR #227
  (`feat/20260811-comprehension-map-destructure`). Closed the last corner
  of the destructuring-loop-variable matrix: `[k + v for {a, b} in
  list_of_maps]` and `{k: v for {a, b} in list_of_maps}` now destructure
  each map by key, reusing the same `_destructure_map_pattern`/
  `_bind_map_destructure` helpers already shared by `let`, assignment-
  destructuring, and `for`-loops. Added `is_map` to `ListComprehension`/
  `MapComprehension`, wired an `elif LBRACE` branch into
  `_list_comprehension`/`_map_comprehension`, and threaded the same
  three-way bind (`is_map` → map destructure, `names` → list destructure,
  else plain bind) into `_evaluate_list_comprehension`/
  `_evaluate_map_comprehension`, mirroring `_execute_for`'s existing
  shape. Clean first round: Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2533 tests passing plus CLI smoke tests covering the
  motivating list/map comprehension cases, `if`-filter interaction,
  missing-key error, non-map-item error, and list-pattern regression).
- **Standard library: `is_balanced` — balanced-brackets predicate** —
  merged 2026-08-12T14:24:48Z via PR #228 (`feat/20260811-is-balanced`).
  Added `is_balanced(s)` to `cinder/builtins.py`, registered right after
  `is_pangram`: a left-to-right scan with a stack, pushing openers and
  popping-and-comparing against a `{closer: opener}` map on each closer,
  balanced iff the stack is empty at the end. The project's first
  stack-based parsing predicate, distinct from the multiset/reversal
  delegations the rest of the string-predicate cluster uses. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2544 tests
  passing plus CLI smoke tests covering nesting, empty string, no-brackets,
  interleaved/crossed pairs, unclosed opener, opener-less closer, and both
  type/arity errors).
- **Language: rest element in map-destructuring patterns
  (`let {a, ...rest} = m;`)** — merged 2026-08-12T14:24:53Z via PR #229
  (`feat/20260812-map-destructure-rest`). Closed the last gap between the
  two destructuring pattern kinds: `_destructure_map_pattern` in
  `cinder/parser.py` now returns `(names, rest)` instead of a bare list,
  mirroring `_destructure_list_pattern`'s existing `...rest` handling, and
  all five call sites (`let`, `for`, `fn` params, list/map comprehensions)
  thread the new `rest` field into their AST nodes. `_bind_map_destructure`
  in `cinder/interpreter.py` gained a `rest` parameter that builds a fresh
  dict of every key not named in the pattern, bound through the same
  `_bind_destructure_name` helper the list-rest case already shares.
  Plain-assignment map-destructuring (`{a, b} = expr;`) deliberately does
  not gain `...rest` support here — left for a future task. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2549 tests
  passing plus CLI smoke tests covering all five call sites, empty rest,
  fresh-per-iteration binding, rest-not-last, and the untouched
  plain-assignment form).
- **Standard library: `is_isogram` — no-repeated-letter predicate** —
  merged 2026-08-12T14:39:41Z via PR #230 (`feat/20260812-is-isogram`).
  Added `is_isogram(s)` to `cinder/builtins.py`, registered right after
  `is_blank`: lowercases the string, filters to alphabetic characters, and
  compares the filtered length to the length of the `set` built from it —
  equal lengths means no letter repeated. Non-letter characters (digits,
  hyphens, spaces, punctuation) are ignored entirely, neither counting
  toward nor breaking a collision. A single-pass character-frequency
  check, distinct from the multiset/reversal delegations the rest of the
  string-predicate cluster uses. Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2572 tests passing plus CLI
  smoke tests covering case-insensitive collisions, punctuation/digits
  ignored, empty string, and both type/arity errors).
- **Language: rest element in plain-assignment map-destructuring
  (`{a, ...rest} = expr;`)** — merged 2026-08-12T19:46:40Z via PR #231
  (`feat/20260812-map-destructure-assign-rest`). Closed the gap PR #229
  deliberately left open: `_try_map_destructure_assign_statement` in
  `cinder/parser.py` now accepts an optional trailing `...rest`, threading
  it into `DestructureAssign.rest` the same way the `let`/`for`/`fn` map
  patterns already do; no interpreter changes needed since
  `_evaluate_destructure_assign` already threaded `expr.rest` through.
  First round: Reviewer found the deferred rest-violation raise could be
  swallowed by the function's own blanket `except ParseError: return None`
  when a non-identifier token followed a misplaced rest (e.g.
  `{a, ...rest, 5} = {};`), reproducing the exact confusing `_block()`
  fallback error the PR claimed to eliminate — `VERDICT: CHANGES
  REQUESTED`. Fixed by switching to an eager raise via a `_RestNotLast`
  marker exception (not a `ParseError` subclass, so it can't be caught by
  that same handler), mirroring the sibling `_destructure_map_pattern`/
  `_destructure_list_pattern` eager-raise approach. Second round: `VERDICT:
  LGTM` and `QA: PASS` (2580 tests passing plus CLI smoke tests covering
  the fixed swallowed-error case and adjacent valid/invalid shapes).
- **Standard library: `levenshtein_distance` — string edit distance** —
  merged 2026-08-12T19:57:12Z via PR #232
  (`feat/20260812-levenshtein-distance`). Added `levenshtein_distance(a,
  b)` to `cinder/builtins.py`, registered right after `is_permutation`:
  standard row-by-row DP kept to a single rolling 1-D list rather than a
  full 2-D matrix, since only the previous row is needed to compute the
  final distance. Arity/type-checking modeled verbatim on `is_anagram`'s
  two-argument "first argument"/"second argument" message shape. The
  project's first dynamic-programming builtin, and a third distinct
  implementation technique for the string-comparison family alongside
  `is_balanced`'s stack scan and `is_isogram`'s frequency-set check.
  Clean first round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS`
  (2592 tests passing plus CLI smoke tests covering the kitten/sitting
  and flaw/lawn canonical examples, both-empty/one-empty directions,
  symmetry, and both type/arity error paths).
- **Language: chained comparison operators (`a < b < c`)** — merged
  2026-08-12T20:12:12Z via PR #233 (`feat/20260812-chained-comparison`).
  Added a new `ChainedComparison` AST node so a run of two-or-more
  *ordering* operators (`<`, `<=`, `>`, `>=`) evaluates as `a < b and b
  < c`, each operand evaluated exactly once with left-to-right
  short-circuiting, reusing `_compare` verbatim for identical error
  messages. Chains mixing in `==`/`!=`, and single comparisons, keep
  today's exact left-fold `Binary` behavior unchanged — scoped
  deliberately to the pure-ordering case, which previously always
  raised `CinderRuntimeError` ("unsupported operand types for
  comparison: bool and {type}") since a `Binary` left-fold compared a
  `bool` intermediate against the next operand. Clean first round:
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2606 tests
  passing plus CLI smoke tests covering ordering/mixed-ordering chains,
  the `==`/`!=` left-fold regression cases, and a `track()`
  side-effect-counter proof of single-evaluation/short-circuiting).
- **Standard library: `is_automorphic`** — merged 2026-08-12T20:24:54Z via
  PR #234 (`feat/20260812-is-automorphic`). Added `is_automorphic(n)` to
  `cinder/builtins.py`, registered right after `is_deficient`, joining the
  `is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`/
  `is_abundant`/`is_deficient` integer-property cluster. Implemented as a
  plain string check (`str(n * n).endswith(str(n))`) mirroring
  `_is_palindrome_number`/`_is_armstrong`, with arity/type-checking modeled
  on `_is_armstrong`'s structure and negative input answering `false`
  without raising, matching every sibling in the cluster. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2618 tests
  passing plus CLI smoke tests covering larger automorphic numbers not in
  the backlog's examples, false cases, and both type/arity error paths).
- **Language: slice assignment for lists (`list[start:end] = other_list;`)**
  — merged 2026-08-13T14:14:41Z via PR #235 (`feat/20260813-slice-assign`).
  Added a `SliceAssign` AST node, a parser branch in `_assignment()`, and
  `_evaluate_slice_assign` in `cinder/interpreter.py`, mirroring the
  read-side `_evaluate_slice` bound-normalization logic verbatim so
  read/write slicing never diverge. Scoped to the step-less form only —
  a stepped slice target (`list[a:b:c] = value;`) still raises
  `ParseError` `"invalid assignment target"`, explicitly deferred to a
  future task (see backlog's extended-slice-assignment task). String
  targets still raise the existing `"strings are immutable and do not
  support item assignment"` error. Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2630 tests passing plus CLI
  smoke tests covering growth, shrink, omitted bounds, negative-bound
  normalization, out-of-range clamping, return-value semantics, and the
  non-list-value/string-target/stepped-slice error paths).
- **Standard library: `hamming_distance`** — merged 2026-08-13T~ via PR #236
  (`feat/20260813-hamming-distance`). Added `hamming_distance(a, b)` to
  `cinder/builtins.py`, registered right after `levenshtein_distance`, the
  simpler equal-length position-wise-scan counterpart to
  `levenshtein_distance`'s DP-based any-length metric. Unequal-length input
  raises a domain-specific `CinderRuntimeError` rather than truncating or
  padding. Clean first round: Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2640 tests passing plus CLI smoke tests covering the classic
  textbook example, both-empty, identical strings, symmetry, and the
  unequal-length/non-string/wrong-arity error paths).
- **Language: extended slice assignment for lists
  (`list[start:end:step] = other_list;`)** — merged 2026-08-13T~ via PR #237
  (`feat/20260813-extended-slice-assign`). The direct follow-on to
  step-less slice assignment (PR #235): `SliceAssign` gains a `step` field,
  threaded through in one pass to avoid double-normalizing the slice bounds,
  and assigned via Python's own 3-argument extended-slice-assignment
  machinery so a length mismatch on a real extended slice (any step other
  than `1`) raises `CinderRuntimeError` instead of silently truncating,
  growing, or shrinking. Clean first round: Reviewer gave `VERDICT: LGTM`
  and QA gave `QA: PASS` (2637 tests passing plus CLI smoke tests covering
  stepped replace, negative-step reverse, explicit `step=1` grow behavior,
  and the length-mismatch/non-list-value/zero-step/string-immutability
  error paths).
- **Standard library: `is_harshad` — digit-sum divisibility predicate** —
  merged 2026-08-13T19:50:13Z via PR #238 (`feat/20260813-is-harshad`).
  Added `is_harshad(n)` to `cinder/builtins.py`, registered right after
  `is_automorphic` in the integer-property cluster: a positive integer is
  Harshad (Niven) when it's evenly divisible by the sum of its own decimal
  digits, computed with the same inline digit-sum walk `digit_sum` uses
  internally. Zero and negative input answer `false` rather than raising,
  matching the `is_abundant`/`is_deficient` convention and sidestepping a
  division by zero. Clean first round: Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2658 tests passing plus CLI smoke tests covering true/
  false cases including the Hardy–Ramanujan number 1729, zero/negative
  edge cases, and the float/bool/wrong-arity error paths).
- **Language: map-destructuring key rename (`let {a: x, b} = expr;`)** —
  merged 2026-08-13T20:12:01Z via PR #239
  (`feat/20260813-map-destructure-rename`). Added JS-style `{key:
  binding}` renaming to every map-destructuring form — `let`, plain
  assignment, `for`, function params, and both comprehension
  loop-variable forms — via a shared parser helper
  (`_destructure_map_pattern_entry`) and by changing `_bind_map_destructure`
  in `cinder/interpreter.py` to unpack `(key, binding)` pairs, using the
  key for the map lookup/rest-computation and the binding for the
  environment write. List-pattern destructuring is untouched (positional,
  renaming has no meaning there). Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2669 tests passing plus CLI
  smoke tests covering rename across all five forms, rename+rest,
  missing-binding-after-colon ParseError, and repeated-rename
  last-binding-wins).
- **Standard library: `is_perfect_cube` — integer cube-root predicate** —
  merged 2026-08-13T20:24:43Z via PR #240
  (`feat/20260813-is-perfect-cube`). Added `is_perfect_cube(n)` to
  `cinder/builtins.py`, registered right after `is_harshad` in the
  integer-property cluster. Computes an exact integer cube root via
  binary search on the magnitude (`_integer_cube_root`), avoiding the
  float-drift risk of `round(n ** (1/3))`, then restores sign symmetry —
  unlike `is_perfect_square`, negative input is accepted (`-8` is a
  perfect cube via `(-2) ** 3`). Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2681 tests passing plus CLI
  smoke tests covering positive/negative/zero cubes, non-cubes on both
  signs, a 10^36 bignum case, and the float/bool/wrong-arity error
  paths).
- **Standard library: `aliquot_sum` — sum of an integer's proper
  divisors** — merged 2026-08-14T14:27:10Z via PR #241
  (`feat/20260814-aliquot-sum`). Added `aliquot_sum(n)` to
  `cinder/builtins.py`, registered right after `divisors`: the
  value-returning counterpart to `is_perfect_number`/`is_abundant`/
  `is_deficient`'s boolean comparisons, sharing the same sqrt-walk
  trial-division pattern as `_divisors` but summing instead of
  collecting. Domain error on `n < 1` and `n == 1` special-cased to `0`,
  mirroring `divisors`'s own error-handling convention. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2692
  tests passing plus CLI smoke tests covering perfect/abundant/
  deficient/prime cases and the domain/float/bool/wrong-arity error
  paths).
- **Language: keyword arguments in function calls (`f(a: 1, b: 2)`)** —
  merged 2026-08-14T14:51:08Z via PR #242
  (`feat/20260814-kwargs-call`). Added trailing keyword arguments for
  user-defined Cinder functions, matched by parameter name and
  order-independent, mirroring Python's positional-then-keyword calling
  convention. New `KeywordArg` AST node parsed by `_call_argument`,
  enforced positional-after-keyword as a parse error in both
  `_finish_call` and `_finish_optional_call`. `call_value` binds
  keywords against declared parameter names with duplicate-value,
  unexpected-keyword, and missing-required-argument checks; builtins
  reject keyword arguments outright rather than silently mis-binding.
  Destructuring and rest parameters are correctly unaddressable by
  keyword since they fall out of `named_params` naturally. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2712
  tests passing plus CLI/REPL smoke tests covering order-independent
  binding, defaults, duplicate/unexpected/missing keyword errors,
  positional-after-keyword parse errors, and destructuring/rest/builtin
  rejection).
- **Standard library: `collatz_length` — steps to reach 1 under the
  Collatz recurrence** — merged 2026-08-14T20:12:48Z via PR #245
  (`feat/20260814-collatz-length`). Added `collatz_length(n)` to
  `cinder/builtins.py`, registered right after `is_happy_number`: joins
  its iterate-and-count-steps shape, repeatedly replacing `n` with `n /
  2` (even) or `3n + 1` (odd) until it reaches `1` and counting steps,
  with no cycle guard needed since the Collatz conjecture holds for
  every integer ever checked. Unlike the boolean-predicate cluster, `n
  < 1` raises a domain error rather than returning `false`, mirroring
  `divisors`/`aliquot_sum`'s type-vs-domain-error convention since this
  builtin returns a number. Clean first round: Reviewer gave `VERDICT:
  LGTM` and QA gave `QA: PASS` (2753 tests passing plus CLI smoke tests
  covering base cases, the long-running `collatz_length(27) == 111`
  case, and the float/bool type-error and domain-error paths).
- **Standard library: `is_pronic` — oblong-number predicate** — merged
  2026-08-14T19:39:34Z via PR #243 (`feat/20260814-is-pronic`). Added
  `is_pronic(n)` to `cinder/builtins.py`, registered right after
  `is_perfect_cube`: an integer `n` is pronic (oblong) when `n = k *
  (k + 1)` for some non-negative integer `k`, computed the same
  exact-integer way as `is_perfect_square` (`math.isqrt`, no
  floating-point square root) with a single `root * (root + 1) ==
  value` check. Negative input answers `false` without raising,
  matching `is_perfect_square`/`is_leap_year`'s own convention. Clean
  first round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS`
  (2725 tests passing plus CLI smoke tests covering true/false cases,
  a huge pronic product with no overflow/precision issues, and the
  float/string type-error paths).
- **Language: default values in list-destructuring patterns
  (`let [a, b = 5] = expr;`)** — merged 2026-08-14T19:59:14Z via PR #244
  (`feat/20260814-list-destructure-defaults`). Extended `let`/`for`/
  function-param/comprehension list-destructuring patterns to accept a
  trailing `= expr` per element, evaluated left-to-right in the binding
  `Environment` so a later default can see an earlier bound name (e.g.
  `let [a, b = a + 1] = [5];` binds `b` to `6`). Changed
  `_destructure_list_pattern`'s `names` shape from flat `list[str]` to
  `list[tuple[str, Expr | None]]`, mirroring `_fn_param`'s own
  `seen_default`-tracking convention for defaults-must-trail ordering;
  `_bind_list_destructure` fills missing trailing values from their
  defaults. Plain-assignment form (`[a, b] = expr;`) intentionally left
  untouched — still a `ParseError`, out of scope per the task's own
  scope note. Clean first round: Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2743 tests passing plus CLI smoke tests covering
  rest-pattern interaction, cross-form parity across let/for/params/
  comprehensions, and the out-of-scope plain-assignment form's
  unchanged parse error).
- **Standard library: `is_strong_number` — sum of digit factorials
  equals the number** — merged 2026-08-14T20:28:58Z via PR #246
  (`feat/20260814-is-strong-number`). Added `is_strong_number(n)` to
  `cinder/builtins.py`, registered right after `is_armstrong`: the
  digit-factorial-sum sibling of `is_armstrong`'s digit-power-sum
  check, reusing the already-registered `factorial` builtin's
  underlying `math.factorial` rather than reimplementing it. A strong
  number (factorion) is a positive integer equal to the sum of the
  factorials of its own decimal digits; exactly four exist in base 10
  (`1`, `2`, `145`, `40585`). Negative input answers `false` without
  raising, matching `is_armstrong`/`is_pronic`'s own convention (avoids
  `int(digit)` choking on a literal `-` character). Clean first round:
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2764 tests
  passing plus CLI smoke tests covering all four known factorions, the
  `0`/`1` fixed-point edge cases, the negative guard, and the
  float/bool type-error paths).
- **Language: unary `+` operator (`+expr`)** — merged 2026-08-15T14:07:29Z
  via PR #247 (`feat/20260815-unary-plus`). Added `TokenType.PLUS` to
  the parser's `_UNARY` set and mirrored the existing `MINUSMINUS`
  re-split in `_unary` for the `PLUSPLUS` lexer token, so `++5` parses
  as nested `Unary(PLUS, ...)` the same way `--5` already did.
  `_evaluate_unary` gained a `PLUS` branch modeled exactly on `MINUS`'s
  type-checking (numbers only, `bool` rejected). Postfix `x++`/`x--`
  sugar untouched — different parse position, confirmed by existing
  tests still passing plus new coverage for both. Clean first round:
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2777 tests
  passing).
- **Standard library: `num_divisors`** — merged 2026-08-15T14:20:46Z via
  PR #248 (`feat/20260815-num-divisors`). Added `num_divisors(n)` to
  `cinder/builtins.py`, registered right after `aliquot_sum`: the
  count-returning sibling of `divisors`'s list-returning walk and
  `aliquot_sum`'s sum-returning walk, all trial-dividing to `sqrt(n)`
  and pairing each divisor with its complement. `n < 1` raises a domain
  error, matching the divisor cluster's type-vs-domain-error convention.
  Clean first round: Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2787 tests passing, plus CLI smoke tests including a
  larger perfect-power case beyond the fixed test set).
- **Language: default values in map-destructuring patterns** — merged
  2026-08-15T14:35:04Z via PR #249
  (`feat/20260815-map-destructure-defaults`). Extended
  `_destructure_map_pattern_entry` (`cinder/parser.py`) to parse an
  optional `= expr` default after each entry, and
  `_bind_map_destructure` (`cinder/interpreter.py`) to evaluate it in
  pattern order when a key is missing from the source map — so
  `let {a, b = 5} = {"a": 1}` binds `b` to `5`, and a later default can
  reference an earlier binding (`let {a, b = a + 1} = {"a": 5}`). Since
  all five map-pattern forms (`let`, plain assignment, `for`, fn params,
  comprehensions) already share this one parser entry point, every form
  gained defaults for free, including plain assignment, unlike the
  list-pattern version. A default only fires on a genuinely missing key,
  not a present-but-falsy value; whole-pattern defaults on fn params
  remain rejected. Clean first round: Reviewer gave `VERDICT: LGTM` and
  QA gave `QA: PASS` (2806 tests passing).
- **Standard library: `prime_factors`** — merged 2026-08-15T14:54:10Z via
  PR #250 (`feat/20260815-prime-factors`). Added `prime_factors(n)` to
  `cinder/builtins.py`, registered right after `aliquot_sum`: unlike
  `divisors`/`aliquot_sum`/`num_divisors`, which pair divisors up to
  `sqrt(n)` against the fixed original value, this uses standard trial
  division to strip small prime factors out of a shrinking copy of `n`,
  recording each repeated factor with multiplicity in ascending order
  (`12 -> [2, 2, 3]`, `360 -> [2, 2, 2, 3, 3, 5]`). `n < 1` raises a
  domain error, matching the divisor cluster's type-vs-domain-error
  convention; `prime_factors(1)` returns `[]` with no special-casing
  needed since both loop guards fall through naturally. Clean first
  round: Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2816
  tests passing, plus CLI smoke tests covering larger inputs like
  `1000000` and the prime `999983`).
- **Language: hole elements in list-destructuring patterns** — merged
  2026-08-16T19:13:39Z via PR #251 (`feat/20260815-list-hole`). Closed
  the last gap in the destructuring-pattern cluster: `let [a, , c] = expr;`
  now binds `a`/`c` and skips the middle position instead of raising a
  `ParseError`, across all four list-pattern forms (`let`, `for`, fn
  params, comprehensions). `cinder/parser.py`'s
  `_destructure_list_pattern_entry` recognizes a hole only where a
  `COMMA` is seen right after `[` or right after a just-consumed comma
  — a trailing comma before `]` and the plain-assignment form stay
  unaffected. `cinder/interpreter.py`'s two binding loops guard
  `_bind_destructure_name` with `if name is not None`, so a hole's value
  is still computed (index arithmetic and arity checks stay correct) but
  never bound. Clean first round: Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2837 tests passing).
- **Standard library: `is_squarefree`** — merged 2026-08-15T19:27:04Z
  via PR #252 (`feat/20260815-is-squarefree`). Added `is_squarefree(n)`
  to the integer-property predicate cluster right after `is_pronic`: a
  positive integer is squarefree when no perfect square greater than
  `1` divides it evenly, checked via the same `sqrt(n)`-bounded
  trial-division shape `is_prime`/`is_composite` already use, testing
  `divisor * divisor` divisibility directly. `n < 1` returns `false`
  rather than raising, matching the boolean-predicate cluster's
  convention; `is_squarefree(1)` is `true` for free since the empty
  `range(2, 2)` loop falls through. Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2848 tests passing).
- **Language: optional catch binding** — merged 2026-08-15T19:40:25Z
  via PR #253 (`feat/20260815-optional-catch-binding`). `catch { ... }`
  (no `(name)`) is now valid syntax, sugar for the common "just
  recover, don't inspect the error" case; the named form
  `catch (e) { ... }` is completely unchanged. `cinder/parser.py`'s
  `_try_statement` only parses the `(name)` group when the token right
  after `catch` is actually `(`, otherwise `catch_name` stays `None`
  (no AST change needed, `TryStmt.catch_name` was already `str | None`).
  `cinder/interpreter.py`'s `_execute_try` only calls
  `catch_env.define(...)` when `stmt.catch_name is not None`; the catch
  block still gets its own fresh child environment either way, so a
  `let` inside it still doesn't leak. Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2855 tests passing).
- **Standard library: `is_amicable`** — merged 2026-08-16T00:00:00Z via
  PR #254 (`feat/20260815-is-amicable`). Two positive integers `a != b`
  are an amicable pair when each one's own proper-divisor sum equals
  the other (e.g. `220`/`284`, `1184`/`1210`); a private
  `_aliquot_sum_value` helper mirrors `_aliquot_sum`'s trial-division
  body, called once per argument. `a == b` is rejected up front so a
  perfect number like `6` is never amicable with itself even though its
  own proper-divisor sum loops back to itself; domain handling
  (`< 1` → `false`) follows the boolean-predicate cluster's convention,
  not the divisor cluster's raise-on-invalid one. Clean first round:
  Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2865 tests
  passing).
- **Language: pipe operator (`a |> f` as sugar for `f(a)`)** — merged
  2026-08-16T14:08:56Z via PR #255 (`feat/20260815-pipe-operator`).
  Added a new `PIPE_ARROW` (`|>`) token in `cinder/lexer.py`, checked
  ahead of the `_COMPOUND_ASSIGN_TOKENS` fallback so it doesn't shadow
  `|`/`|=`; a new `_pipe` precedence level in `cinder/parser.py` between
  `_ternary` and `_nullish`, left-associative so `a |> f |> g` is
  `(a |> f) |> g`; and evaluation in `cinder/interpreter.py` that reuses
  `call_value` for the implicit call, evaluating both sides fully as
  ordinary expressions before calling — so `a |> curry(add, 2)` is not
  Elixir-style argument-splicing, it calls whatever `curry(add, 2)`
  returns with `a`. Clean first round: Reviewer gave `VERDICT: LGTM` and
  QA gave `QA: PASS` (2883 tests passing).
- **Standard library: `is_semiprime` — product of exactly two primes** —
  merged 2026-08-16T14:22:26Z via PR #256 (`feat/20260816-is-semiprime`).
  Added `is_semiprime(n)` to `cinder/builtins.py`, registered right
  after `is_composite`: trial-division factor counting with an early
  `factor_count > 2` bailout, the third member of the
  `is_prime`/`is_composite`/`is_semiprime` classification trio.
  `n < 2` returns `false` rather than raising, matching the
  boolean-predicate cluster's convention. Clean first round: Reviewer
  gave `VERDICT: LGTM` and QA gave `QA: PASS` (2897 tests passing).
- **Language: uninitialized `let` declarations (`let x;`, defaults to
  `nil`)** — merged 2026-08-16T14:35:41Z via PR #257
  (`feat/20260816-uninitialized-let`). `_let_statement` in
  `cinder/parser.py` now defaults the initializer to a bare `nil`
  literal when `let NAME` is immediately followed by `;`, instead of
  unconditionally requiring `= expr`; `const` is untouched (still
  requires an initializer), and the C-style `for` loop's init clause
  now also accepts an uninitialized `let i` for free, though it still
  raises a runtime type error on the first comparison since `i` is
  never assigned before the condition runs. Clean first round: Reviewer
  gave `VERDICT: LGTM` and QA gave `QA: PASS` (2902 tests passing).
- **Standard library: `is_powerful_number` — every prime factor appears
  with exponent 2 or more** — merged 2026-08-16T14:53Z via PR #258
  (`feat/20260816-is-powerful-number`). Added `is_powerful_number(n)` to
  `cinder/builtins.py`, registered right after `is_squarefree`: a
  trial-division peel that fully divides out each factor's multiplicity
  and fails fast on a count below `2`, with a trailing `remaining == 1`
  check catching a leftover prime above the sqrt bound. `n < 1` returns
  `false` rather than raising, matching the boolean-predicate cluster's
  convention. Clean first round: Reviewer gave `VERDICT: LGTM` and QA
  gave `QA: PASS` (2916 tests passing).
- **Language: single-quoted string literals (`'...'` as an alternate
  delimiter)** — merged 2026-08-16T19:12:17Z via PR #259
  (`feat/20260816-single-quote-strings`). `_string` in `cinder/lexer.py`
  now takes the opening quote character as a parameter instead of
  hardcoding `"` for both the terminator check and `tokenize`'s
  dispatch, so `'` is recognized as a second string delimiter; `\'` was
  added to `_ESCAPES` alongside the existing `\"` entry. Interpolation,
  escapes, and error shapes are shared and unchanged between both
  delimiters since `_string` was already delimiter-agnostic apart from
  the two hardcoded quote checks — no parser or interpreter changes.
  Clean first round: Reviewer gave `VERDICT: LGTM` and QA gave
  `QA: PASS` (2924 tests passing).
- **Standard library: `is_repdigit`** — every decimal digit is the same
  — merged 2026-08-16T19:25:06Z via PR #260
  (`feat/20260816-is-repdigit`). Registered in `cinder/builtins.py`
  right after `is_palindrome_number`; models its arity/type checking
  on that builtin (`_require_arity`, `_require_int`), returns `false`
  for negative input rather than raising, and treats any single-digit
  value (including `0`) as trivially a repdigit since its decimal
  string has exactly one character. Pure string/set check on
  `str(value)` — no trial division needed. Clean first round: Reviewer
  gave `VERDICT: LGTM` and QA gave `QA: PASS` (2937 tests passing).
- **Language: scientific notation for float literals (`1e3`, `1.5e-2`,
  `2E+10`)** — merged 2026-08-16T19:40:30Z via PR #261
  (`feat/20260816-scientific-notation`). `_number` in `cinder/lexer.py`
  gained an optional exponent-suffix block after the existing
  fractional-part handling: an `e`/`E` followed by a digit or `+`/`-`
  sign commits to consuming an exponent, reusing the same underscore-
  separator gate as the mantissa/fraction digit runs, and raises
  `LexError` (`"expected digits after exponent"`) if no digits follow.
  An exponent always forces `is_float = True`. No parser or interpreter
  changes — `float(value_str)` already parses the full grammar once
  underscores are stripped. Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2948 tests passing).
- **Standard library: `geometric_mean` — the nth root of a list's
  product** — merged 2026-08-16T19:53:21Z via PR #262
  (`feat/20260816-geometric-mean`). `_geometric_mean` in
  `cinder/builtins.py`, registered right after `_mean`, is the
  statistics cluster's first non-arithmetic average: arity/type
  checking mirrors `mean`/`median`/`variance` (`_require_arity`,
  `isinstance(value, list)`, non-empty, `_is_numeric` per element), plus
  one extra requirement checked only after the numeric check — every
  element must be strictly positive, raising a domain error rather than
  dividing by zero or requiring complex arithmetic, the same convention
  `log()` already uses. Clean first round: Reviewer gave
  `VERDICT: LGTM` and QA gave `QA: PASS` (2960 tests passing).
- **Language: postfix `++`/`--` as a first-class assignment expression**
  — merged 2026-08-17T14:09Z via PR #263
  (`feat/20260816-postfix-incdec-expr`). Folded `_expr_or_incdec`'s body
  directly into `cinder/parser.py`'s `_assignment` as a fourth branch
  alongside `EQ`/`QQEQ`/compound-assign, so `x++`/`x--` are now
  reachable anywhere any other assignment operator already is — a `let`
  initializer, the RHS of a chained assignment, inside a parenthesized
  sub-expression — instead of only as a bare statement or a `for`-loop
  step clause. No interpreter changes: `Assign`/`IndexCompoundAssign`
  already evaluate to the new (post-increment) value. Precedence and
  reachability from call arguments/ternary branches deliberately
  unchanged (`-x++;`, `print(x++);` still raise). Bounced once on
  review: a stale "statement-only sugar" comment next to
  `_INCREMENT_DECREMENT_OPS` contradicted the PR's own change; fixed,
  then Reviewer gave `VERDICT: LGTM` and QA gave `QA: PASS` (2971 tests
  passing).
- **Standard library: `digit_product` — the multiplicative counterpart to
  `digit_sum`** — merged 2026-08-17T~14:26Z via PR #264
  (`feat/20260817-digit-product`). Added `digit_product(n)` to
  `cinder/builtins.py`, registered right after `digit_sum`, modeled
  exactly on its arity/type-check/sign-discard structure
  (`_require_arity` → `_require_int` → `abs(value)` before the digit
  walk); any `0` digit collapses the product to `0`. Clean first pass,
  no bounces (2981 tests passing, up from 2971).
- **Language: trailing commas in list/map literals, call arguments, and
  function parameter lists** — merged 2026-08-17T~18:26Z via PR #265
  (`feat/20260817-trailing-commas`). All four of `cinder/parser.py`'s
  comma-separated-list parsers (`_list_literal`, `_map_literal`,
  `_finish_call`, `_fn_param_list`) now `break` on a comma immediately
  followed by the closing delimiter instead of hard-failing, including
  single-element trailing commas and a trailing comma right after a rest
  parameter. Destructuring patterns and comprehension bodies remain out
  of scope (left as a separate backlog task). Clean first pass, no
  bounces (2992 tests passing, up from 2981).
- **Standard library: `is_evil` / `is_odious` — binary popcount-parity
  predicates** — merged 2026-08-17T~18:26Z via PR #266
  (`feat/20260817-is-evil-odious`). Added both to `cinder/builtins.py`
  right after `is_power_of_two`, each a one-line delegation to
  `bin(value).count("1") % 2` differing only in which parity it accepts;
  arity/type checking mirrors `is_power_of_two` via `_require_arity` →
  `_require_int`, but negative input raises a domain error (following
  `divisors`/`log()`'s convention) rather than returning `false`, since
  popcount parity isn't meaningful for Python's two's-complement `bin()`
  output on negative integers. Clean first pass, no bounces (2993 tests
  passing, up from 2992).
- **Language: list concatenation via `+`** — merged 2026-08-17T~18:45Z via
  PR #267 (`feat/20260818-list-plus-concat`). Added a
  `isinstance(left, list) and isinstance(right, list)` branch to
  `cinder/interpreter.py`'s `_apply_binary_operator` `PLUS` case,
  returning `left + right` (a fresh list, non-mutating), closing the gap
  between the existing `concat()` builtin and infix syntax the same way
  `*` already does for list repetition. Mixed-type operands still raise
  `CinderRuntimeError`; `+=` on lists works for free via the shared
  `Binary`/`PLUS` desugaring. Clean first pass, no bounces (3014 tests
  passing, up from 2993).
- **Standard library: `harmonic_mean`** — merged 2026-08-17T19:02:03Z via
  PR #268 (`feat/20260817-harmonic-mean`). Added to `cinder/builtins.py`
  right after `geometric_mean`, modeled directly on its validation shape
  (list/non-empty/numeric/positive checks) with the sum-of-reciprocals
  computation swapped in for the final step, completing the
  arithmetic/geometric/harmonic Pythagorean-means trio in the statistics
  cluster. Clean first pass, no bounces (3025 tests passing, up from
  3014).
- **Language: trailing commas in destructuring patterns** — merged
  2026-08-18T14:11Z via PR #269
  (`feat/20260817-trailing-commas-destructure`). Added a
  `if self._check(RBRACKET/RBRACE): break` guard to each of
  `cinder/parser.py`'s three destructuring comma-loops
  (`_destructure_map_pattern`, `_destructure_list_pattern`,
  `_try_map_destructure_assign_statement`), placed before the "rest must
  be last" check, extending task 2's trailing-comma support (list/map
  literals, call arguments, function parameters) to `let`/`for`/fn-param/
  comprehension destructuring patterns and the plain map-assign form. A
  documented side effect: a hole immediately before the closing
  delimiter (`let [a, ,] = [1, 2];`) is now accepted the same way a
  trailing comma after a real element is. Clean first pass, no bounces
  (3048 tests passing, up from 3025).
- **Standard library: `multiplicative_persistence`** — merged
  2026-08-18T14:26:29Z via PR #270
  (`feat/20260818-multiplicative-persistence`). Added
  `_multiplicative_persistence` to `cinder/builtins.py`, registered right
  after `digit_product`/before `reverse_int` — the loop-driven counterpart
  to `digital_root`'s closed-form additive reduction, since no closed
  form exists for the multiplicative case. Sign discarded once via
  `abs()` before the loop; each step inlines the same per-digit-multiply
  walk `digit_product` uses rather than calling its dispatch-signature
  builtin directly. Clean first pass, no bounces (3058 tests passing, up
  from 3048).
- **Language: comma-separated multiple variable declarations in a single
  `let`/`const` statement** — merged 2026-08-18T14:42:57Z via PR #271
  (`feat/20260818-decl-seq`). Added a new `DeclSeq` AST node
  (`cinder/ast_nodes.py`) executed against the *same* `Environment` as
  its declarations rather than a fresh child one (unlike `Block`), so
  `let a = 1, b = a + 1;` lands both names in the caller's scope with
  later initializers able to see earlier names; `_let_statement`/
  `_const_statement` factor their single-declaration body into a shared
  per-name helper looped on a trailing comma, collapsing back to a plain
  `LetStmt`/`ConstStmt` for the single-declaration case so no existing
  call site changes shape. `for (let i = 0, j = 3; ...)` started working
  for free since `_execute_for_c` already dispatches generically.
  Reviewer flagged a non-blocking, inert side effect: `LetStmt`/
  `ConstStmt.line/column` now stamp from the identifier token rather
  than the `let`/`const` keyword, for every declaration, not just
  comma-separated ones — nothing reads those fields at runtime. Clean
  first pass, no bounces (3069 tests passing, up from 3058).
- **Standard library: `cbrt` — real cube root** — merged
  2026-08-18T19:21:51Z via PR #272 (`feat/20260818-cbrt`). Added `cbrt`
  to `cinder/builtins.py`, registered right after `sqrt`, taking the
  magnitude's cube root and reapplying the original sign via
  `math.copysign` to avoid Python's `**` producing a complex result for
  a negative base with a fractional exponent — unlike `sqrt`, no domain
  check, since every real number has a real cube root. Reviewer noted a
  non-blocking nit: `cbrt(-0.0)` returns `-0.0` rather than `0.0`, not
  covered by acceptance criteria and inert since `-0.0 == 0.0`. Clean
  first pass, no bounces (3078 tests passing, up from 3069).
- **Language: nested list-in-list destructuring patterns** — merged
  2026-08-18T19:39:39Z via PR #273
  (`feat/20260818-nested-list-destructure`). Added a nested-pattern
  branch to `_destructure_list_pattern_entry` and
  `_destructure_assign_pattern` in `cinder/parser.py`, and a matching
  `isinstance(name, tuple)` branch in both loops of
  `_bind_list_destructure` in `cinder/interpreter.py` — nesting works
  for free across all five list-pattern call sites (`let`, plain
  assignment, `for`, fn params, comprehensions) since they all funnel
  through the same shared helpers. Composes correctly with existing
  rest/default/hole handling at any nesting depth; map-in-list nesting
  stays out of scope and still raises `ParseError`. Reviewer flagged a
  non-blocking nit: `_destructure_assign_pattern`'s docstring is now
  stale (still describes only plain identifiers/rest). Clean first
  pass, no bounces (3090 tests passing, up from 3078).
- **Standard library: `is_perfect_power`** — merged 2026-08-18T19:53:40Z
  via PR #274 (`feat/20260818-is-perfect-power`). Added
  `is_perfect_power` to
  `cinder/builtins.py`, registered right after `is_powerful_number`,
  generalizing `is_perfect_square`/`is_perfect_cube`/`is_powerful_number`'s
  fixed-exponent checks into "is there any integer `k >= 2` and base `m`
  with `m ** k == n`". Introduces `_integer_kth_root`, a general
  binary-search sibling of the existing fixed-exponent
  `_integer_cube_root`, leaving the latter untouched. Negative input is
  accepted (`-8 = (-2) ** 3`) but only via odd exponents, since an even
  power can never be negative. Clean first pass, no bounces (3109 tests
  passing, up from 3090).
- **Language: raw string literals `r"..."`/`r'...'`** — merged
  2026-08-18T20:08:31Z via PR #275 (`feat/20260819-raw-strings`). Added
  the escape/interpolation-free sibling to ordinary strings.
  `Lexer.tokenize()`'s dispatch gets a new branch, checked before the
  existing `char.isalpha()` branch, recognizing a leading `r`
  immediately followed by a quote; a new `_raw_string` method (sibling
  to `_string`) scans to the matching close quote taking every
  character literally, emitting the same `TokenType.STRING` ordinary
  strings use. No escape mechanism inside a raw string, so it cannot
  contain its own delimiter quote — the other quote character can
  always be used instead. Clean first pass, no bounces (3124 tests
  passing, up from 3109).
- **Standard library: `is_undulating`** — merged 2026-08-19T14:11:47Z
  via PR #276 (`feat/20260818-is-undulating`). Added `is_undulating` to
  `cinder/builtins.py`, registered right after `is_repdigit`, testing
  whether an integer's decimal digits strictly alternate between
  exactly two distinct values (e.g. `121`, `2323`). Follows the
  digit-pattern cluster's existing conventions: negative input returns
  `false` rather than raising, and both the three-digit minimum and
  distinct-first-two-digits checks run up front before the alternation
  scan. Clean first pass, no bounces (3138 tests passing, up from
  3124).
- **Language: range literal `a..b` — sugar over the existing `range()`
  builtin** — merged 2026-08-19T14:24:43Z via PR #277
  (`feat/20260819-range-literal`). Added `RangeExpr`
  (`cinder/ast_nodes.py`) and `_range_expr` (`cinder/parser.py`, sitting
  between membership and bitwise-or in precedence), desugaring `a..b` to
  a call into the existing `_range` builtin so both spellings share one
  error message and one validation path. Exclusive of `b`, matching
  `range()`'s own two-argument semantics; usable directly as a `for`-loop
  source (`for i in 1..5 { ... }`). Reviewer's first pass gave `VERDICT:
  CHANGES REQUESTED` — the new `TestRangeLiteral` test class had been
  spliced into the middle of the existing `TestSlicing` class body,
  mislabeling ~14 unrelated slice-assignment tests; Engineer fixed the
  insertion point with no behavior change, then Reviewer gave `VERDICT:
  LGTM` and QA gave `QA: PASS` — one bounce, clean merge after (3140
  tests passing, up from 3138).
- **Standard library: `is_kaprekar`** — merged 2026-08-19T14:39:06Z via
  PR #278 (`feat/20260819-is-kaprekar`). Added `is_kaprekar` to
  `cinder/builtins.py`, registered right after `is_automorphic`
  (automorphic numbers are the fixed special case of a Kaprekar split at
  the digit boundary matching `n`'s own length), testing whether a
  number's square splits into two parts that sum back to the number
  itself (e.g. `45`: `45 ** 2 == 2025`, `20 + 25 == 45`). Handles
  leading-zero right parts via `right != 0` (verified by hand for `99`,
  `999`, `2223`). Clean first pass, no bounces (3171 tests passing, up
  from 3140).
- **Language: map literal shorthand properties `{a, b}`** — merged
  2026-08-19T19:28:00Z via PR #279 (`feat/20260819-map-shorthand`).
  `_map_entry` (`cinder/parser.py`) adds a one-token lookahead
  (`IDENTIFIER` followed by `COMMA`/`RBRACE`) building the shorthand
  `(Literal(name), Identifier(name))` pair, the same technique
  `_call_argument` already uses for keyword arguments — the
  construction-side inverse of the map-destructuring shorthand
  `let {a, b} = expr;` already had. Composes with explicit `key: value`
  entries, spread, and trailing commas in the same literal; map
  comprehensions are unaffected since they always require an explicit
  `key: value` before `for`, failing the shorthand's lookahead. No
  interpreter changes needed — `_evaluate_map_literal` already evaluates
  key/value generically. Clean first pass, no bounces (3186 tests
  passing, up from 3171).
- **Standard library: `is_achilles`** — merged 2026-08-19T19:50:16Z via
  PR #280 (`feat/20260819-is-achilles`). Added `is_achilles` to
  `cinder/builtins.py`, registered right after `is_powerful_number` and
  right before `is_perfect_power`, testing whether an integer is
  powerful (every prime factor's exponent `>= 2`) but *not* itself a
  perfect power (OEIS A052486, e.g. `72 = 2^3 * 3^2`). Reuses
  `is_powerful_number`'s own factorization loop, tracking a running
  `math.gcd` of each prime's exponent alongside it — a number is a
  perfect power exactly when that gcd exceeds `1`, so `exponent_gcd ==
  1` after the powerful check both confirms "not a perfect power" and
  excludes single-prime-factor powers for free, with no second
  factorization pass needed. Clean first pass, no bounces (3201 tests
  passing, up from 3186).
- **Language: inclusive range literal `a..=b`** — merged
  2026-08-20T14:11:19Z via PR #283 (`feat/20260820-inclusive-range`).
  Added a `DOT_DOT_EQ` token (`cinder/lexer.py`'s `_dot`, mirroring how
  `_lt` already checks for a trailing `=` on `<<`), an `inclusive: bool
  = False` field on `RangeExpr` (`cinder/ast_nodes.py`), parser support
  for either spelling (`cinder/parser.py`'s `_range_expr`), and an
  interpreter bump of the end bound by one when inclusive, only for a
  non-bool int so invalid end values still reach `range()`'s own
  validation with an unchanged error message
  (`cinder/interpreter.py`'s `_evaluate_range`). `a..b` (exclusive)
  is unaffected. Clean first pass, no bounces (3228 tests passing,
  up from 3217).
- **Standard library: `is_sphenic`** — merged 2026-08-20T14:27:40Z via PR
  #284 (`feat/20260820-is-sphenic`). Added `_is_sphenic`
  (`cinder/builtins.py`), testing whether an integer is the product of
  exactly three distinct primes each appearing exactly once (`30 = 2 * 3
  * 5`), reusing `_is_semiprime`'s factorization loop shape with an added
  `count != 1: return False` check to reject repeated factors like `12 =
  2^2 * 3` and `60 = 2^2 * 3 * 5`. Clean first pass, no bounces (3242
  tests passing, up from 3228).
- **Language: triple-quoted string literals `"""..."""`/`'''...'''`** —
  merged 2026-08-20T18:16:58Z via PR #285
  (`feat/20260820-triple-quoted-strings`). Extended the lexer's
  plain-string branch (`cinder/lexer.py`'s `tokenize` dispatch and
  `_string`) to recognize a run of three matching quote characters as
  the delimiter instead of one, reusing the existing STRING/
  INTERP_STRING tokens and `_string` loop so escapes, interpolation,
  and multi-line handling are all unchanged. The raw-string branch is
  untouched by design; `r"""..."""` keeps its existing (pre-existing,
  out-of-scope) behavior. Clean first pass, no bounces (3255 tests
  passing, up from 3242).
- **Standard library: `is_circular_prime` — a prime where every digit
  rotation is also prime** — merged 2026-08-20T18:33:13Z via PR #286
  (`feat/20260820-is-circular-prime`). Added `_is_circular_prime` to
  `cinder/builtins.py` right after `_is_emirp`, rotating a number's
  decimal digits via string slicing and trial-dividing each rotation
  with a local `_trial_division_is_prime` helper; leading-zero
  rotations (e.g. `103` → `"031"`) collapse correctly via `int()`
  since any digit-`0` value is guaranteed a rotation ending in `0`.
  Clean first pass, no bounces (3267 tests passing, up from 3255).
- **Language: missing string escape sequences (`\r`, `\0`, `\b`, `\f`, `\v`,
  `\uXXXX`)** — merged 2026-08-20T18:47:36Z via PR #287
  (`feat/20260820-string-escapes`). Extended `Lexer._ESCAPES`
  (`cinder/lexer.py`) with the five missing one-character escapes and added
  a `_unicode_escape` method for `\uXXXX` (exactly 4 hex digits,
  case-insensitive), reusing `_string`'s existing cursor primitives; raw
  strings are unaffected by design. Clean first pass, no bounces (3274
  tests passing, up from 3267).
- **Standard library: `is_sad_number` — the complement of
  `is_happy_number`** — merged 2026-08-21T19:04:10Z via PR #288
  (`feat/20260820-is-sad-number`). Added `_is_sad_number` to
  `cinder/builtins.py` right after `_is_happy_number`, inverting that
  function's own loop at exactly its two exit points (cycle found →
  `True`, reach `1` → `False`) rather than negating a call to it, so the
  negative-input domain guard stays its own explicit `False` rather than
  an implicit consequence of blind negation. Clean first pass, no bounces
  (3282 tests passing, up from 3274).
- **Language: comma-separated multiple statements in expression-statement
  position (`a = 1, b = 2;`)** — merged 2026-08-21T14:14:58Z via PR #289
  (`feat/20260821-comma-expr-stmt`). Extended `_expr_statement`
  (`cinder/parser.py`) to loop on `TokenType.COMMA` the same way
  `_let_statement`/`_const_statement` already do, collecting multiple
  `ExprStmt`s into a `DeclSeq` when more than one is present — reused the
  existing `ExprStmt`/`DeclSeq` nodes and the interpreter's existing
  `DeclSeq` handler, so no lexer/AST/interpreter changes were needed.
  Clean first pass, no bounces (3291 tests passing, up from 3282).
- **Standard library: `additive_persistence` — steps of repeated
  digit-summing to reach one digit** — merged 2026-08-21T14:33:17Z via PR
  #290 (`feat/20260821-additive-persistence`). Added
  `_additive_persistence` to `cinder/builtins.py` right after
  `_multiplicative_persistence`, mirroring its loop shape exactly —
  `abs()` the input once up front, loop while `value >= 10` incrementing a
  step counter — with the loop body's digit-product swapped for a
  digit-sum, the same summing expression `digit_sum` itself uses. Clean
  first pass, no bounces (3300 tests passing, up from 3291).
- **Language: map concatenation via `+` (`{...} + {...}`)** — merged
  2026-08-21T19:25:15Z via PR #291 (`feat/20260821-map-concat`). Added an
  `isinstance(left, dict) and isinstance(right, dict)` branch to
  `_apply_binary_operator`'s `PLUS` case (`cinder/interpreter.py`),
  inlining `merge()`'s own body (right-biased shallow merge, no mutation
  of inputs) since `builtins.py` imports from `interpreter.py` and calling
  `_merge` directly would be circular. `+=` on identifier/index/dot
  targets falls out for free through existing desugaring. Clean first
  pass, no bounces (3313 tests passing, up from 3300).
- **Standard library: `is_pentagonal`** — merged 2026-08-21T19:42:30Z via
  PR #292 (`feat/20260821-is-pentagonal`). Added `_is_pentagonal` to
  `cinder/builtins.py` right after `_is_triangular`, mirroring its
  closed-form perfect-square shape but with an added mod-6 residue check
  (`24n + 1` a perfect square whose root is `≡ 5 (mod 6)`) that the
  pentagonal quadratic requires. `is_pentagonal(0)` is `false`, unlike
  `is_triangular(0)` being `true` — the pentagonal sequence starts at
  `k = 1`, no `k = 0` term. Clean first pass, no bounces (3321 tests
  passing, up from 3313).
- **Language: nested map-in-map destructuring patterns** — merged
  2026-08-21T19:57:19Z via PR #293 (`feat/20260821-nested-map-destructure`).
  Added a nested branch to `_destructure_map_pattern_entry`
  (`cinder/parser.py`), mirroring `_destructure_list_pattern_entry`'s
  existing nested-`[` handling, so a `{` after `:` parses into a
  `(nested_names, nested_rest)` tuple instead of always requiring a bare
  identifier. Added the matching `isinstance(name, tuple)` recursion branch
  to `_bind_map_destructure` (`cinder/interpreter.py`), mirroring
  `_bind_list_destructure`. Because `_destructure_map_pattern_entry` is the
  single shared entry point every map-pattern call site funnels through,
  nesting works for free across `let`/assignment/`for`/fn-param/
  comprehension with no per-call-site changes. Deliberately scoped to
  map-in-map only — list-in-map and map-in-list nesting both continue to
  raise `ParseError`. Clean first pass, no bounces (3335 tests passing, up
  from 3321).
- **Standard library: `is_lucas_number`** — merged 2026-08-21T20:13:21Z via
  PR #294 (`feat/20260821-is-lucas-number`). Added `_is_lucas_number` to
  `cinder/builtins.py`, registered right after `_is_fibonacci`. Generates
  and compares iteratively (`L(n) = L(n-1) + L(n-2)`, seed `L(0)=2,
  L(1)=1`) since Lucas numbers have no clean closed-form membership test
  the way Fibonacci's perfect-square identity gives it — the same shape
  `is_kaprekar`/`is_harshad` already use. `1` and `2` are explicit special
  cases since the sequence dips from `L(0)=2` to `L(1)=1` before climbing,
  which a plain "advance while below target" loop from `L(0)` would skip
  past. `0` and negatives return `false`. Clean first pass, no bounces
  (3344 tests passing, up from 3335).
- **Language: multiple `for` clauses in list/map comprehensions** — merged
  2026-08-22T14:10:51Z via PR #295 (`feat/20260822-multi-for-comprehension`).
  Added a `ComprehensionClause` dataclass (`cinder/ast_nodes.py`) and an
  `extra_clauses` field on both `ListComprehension`/`MapComprehension`, so
  `[x + y for x in xs for y in ys]`-style chained `for` clauses now parse
  and evaluate as a cartesian product — outer-to-inner in written order,
  each clause with its own optional `if` filter, later clauses able to see
  earlier clauses' bound loop variables (including destructured ones).
  `cinder/parser.py` gained a shared `_comprehension_clause()` helper used
  for both the primary and any extra clauses. `cinder/interpreter.py`
  gained `_comprehension_items`/`_bind_comprehension_clause`/
  `_run_comprehension_clauses`, replacing the duplicated single-clause
  loops in `_evaluate_list_comprehension`/`_evaluate_map_comprehension`.
  Map comprehensions resolve key collisions across clause combinations
  last-write-wins, matching plain map-literal semantics. Clean first pass,
  no bounces (3359 tests passing, up from 3344).
- **Standard library: `is_subsequence`** — merged 2026-08-22T14:27:32Z via
  PR #296 (`feat/20260822-is-subsequence`). Added `_is_subsequence` to
  `cinder/builtins.py`, registered right after `_is_rotation`. The third
  classic two-string relationship predicate after `is_rotation` (cyclic
  shift) and `is_anagram` (multiset equality): tests whether one string's
  characters all appear in another, in the same relative order, without
  requiring contiguity. Implemented as the standard two-pointer idiom via
  a single shared `iter()` over the second string and `all(character in
  remaining for character in string1)`, so ordering falls out for free and
  empty-string cases need no special-casing. Clean first pass, no bounces
  (3371 tests passing, up from 3359).
- **Language: a map pattern nested inside a list pattern** — merged
  2026-08-22T14:44:43Z via PR #297 (`feat/20260822-nested-map-in-list`).
  Added a nested-`{` branch to `_destructure_list_pattern_entry`
  (`cinder/parser.py`), mirroring its existing nested-`[` branch but
  tagging the pattern as a 3-tuple `(nested_names, nested_rest, True)` to
  disambiguate from the 2-tuple list-pattern shape; taught
  `_bind_list_destructure` (`cinder/interpreter.py`) to recognize the
  tagged shape at both of its `isinstance(name, tuple):` call sites.
  Works across all four pattern call sites (`let`, `for`, function params,
  both comprehension forms); the plain-assignment form and the
  mirror-direction gap (list nested inside a map pattern) remain
  out of scope, unaffected. Clean first pass, no bounces (3383 tests
  passing, up from 3371).
- **Standard library: `is_hexagonal`** — merged 2026-08-22T15:02:22Z via
  PR #298 (`feat/20260822-is-hexagonal`). Added the third figurate-number
  membership predicate after `is_triangular`/`is_pentagonal`
  (`cinder/builtins.py`), using the same closed-form `math.isqrt`
  identity: `n` is hexagonal iff `8n + 1` is a perfect square whose root
  satisfies `root % 4 == 3`. `0` and negative inputs return `false`
  rather than raising, matching its siblings' convention. Clean first
  pass, no bounces (3391 tests passing, up from 3383).
- **Language: a list pattern nested inside a map pattern** — merged
  2026-08-22T19:24:09Z via PR #299 (`feat/20260822-list-in-map`). Added
  a nested-`[` branch to `_destructure_map_pattern_entry`
  (`cinder/parser.py`), mirroring its existing nested-`{` branch but
  tagging the pattern as a 3-tuple `(nested_names, nested_rest, True)`,
  the same length-tagging convention PR #297 used for the opposite
  nesting direction; taught `_bind_map_destructure`
  (`cinder/interpreter.py`) to recognize the tagged shape and route to
  `_bind_list_destructure`. Works across all four pattern call sites
  (`let`, `for`, function params, both comprehension forms); also
  guarded the plain-assignment map-destructure path so `{a, b: [c]} =
  ...;` keeps raising rather than silently gaining a reading nothing
  implements. With this landing, every corner of the list/map nesting
  matrix (list-in-list, map-in-map, map-in-list, list-in-map) is
  covered. Clean first pass, no bounces (3401 tests passing, up from
  3391).
- **Standard library: `is_heptagonal`** — merged 2026-08-23T~ via PR #300
  (`feat/20260822-is-heptagonal`). Added `is_heptagonal(n)` to
  `cinder/builtins.py`, the fourth figurate-number membership predicate
  after `is_triangular`/`is_pentagonal`/`is_hexagonal`, using the same
  closed-form perfect-square identity: `n` is heptagonal iff `40n + 9` is
  a perfect square whose `math.isqrt` root also satisfies `root % 10 ==
  7`. `0` and negative inputs return `false` rather than raising, matching
  its siblings' convention. Clean first pass, no bounces (3409 tests
  passing, up from 3401).
- **Language: a step component for range expressions** — merged
  2026-08-23T~ via PR #301 (`feat/20260822-range-step`). `RangeExpr` and
  the `range()` builtin gain an optional third **step** argument:
  `start..end..step` / `start..=end..step` for the syntax form,
  `range(start, stop, step)` for the builtin. Negative steps now produce
  descending ranges (`10..0..-2` → `[10, 8, 6, 4, 2]`), and the inclusive-
  end adjustment flips direction (`end - 1` instead of `end + 1`) when the
  step is negative so a descending inclusive bound survives correctly. A
  step of `0` raises `CinderRuntimeError`; only a plain `..` is accepted
  as the step separator, `..=` there stays a `ParseError`. Clean first
  pass, no bounces (3427 tests passing, up from 3409).
- **Standard library: `collatz_max`** — merged 2026-08-23T14:22:05Z via
  PR #303 (`feat/20260823-collatz-max`). Added `collatz_max(n)` to
  `cinder/builtins.py`, the value-returning sibling of `collatz_length`:
  returns the highest value the Collatz (3n+1) sequence reaches before
  collapsing to `1`, tracking a running peak instead of a step count.
  Mirrors `collatz_length`'s exact loop shape and domain-error
  convention (`n < 1` raises). Clean first pass, no bounces (3436 tests
  passing, up from 3427).
- **Language: a `match` expression with literal patterns and a `_`
  wildcard** — merged 2026-08-23T14:42:04Z via PR #304
  (`feat/20260823-match-expr`). Adds `match (subject) { pattern => body,
  ..., _ => body }` as a value-producing expression, the counterpart to
  the existing `switch` statement: literal patterns (`int`/`float`/
  `string`/`true`/`false`/`nil`) or a `_` wildcard, one pattern per arm,
  tried in source order via the existing `values_equal` helper (the same
  cross-type equality `switch` already uses), raising
  `CinderRuntimeError` if no arm matches. `_match_pattern` special-cases
  a bare `_` before general expression parsing to avoid colliding with
  the single-identifier arrow-function sugar (`_ => body`). Bindings,
  guards, and nested/destructuring patterns are out of scope for this
  first version. Clean first pass, no bounces (3454 tests passing, up
  from 3436).
- **Standard library: `nth_prime`** — merged 2026-08-23T14:55:44Z via
  PR #305 (`feat/20260823-nth-prime`). Added `nth_prime(k)` to
  `cinder/builtins.py`, the complementary "which prime" question to
  `is_prime`/`is_composite`/`is_semiprime`/`prime_factors`: given a
  1-indexed position, returns the prime found there via incremental
  trial division. Mirrors `_is_circular_prime`'s locally-scoped
  trial-division style rather than delegating to `_is_prime` (which
  takes the CLI `(arguments, line, column)` shape, not a plain
  `int -> bool` one); domain error for `k < 1` matches
  `collatz_length`'s convention for value-returning functions. Clean
  first pass, no bounces (3463 tests passing, up from 3454).
- **Standard library: `nth_fibonacci`** — merged 2026-08-24 via PR #306
  (`feat/20260823-nth-fibonacci`). Added `nth_fibonacci(n)` to
  `cinder/builtins.py`, the complementary "which value" question to
  `is_fibonacci`/`is_lucas_number`'s membership tests and `nth_prime`'s
  own "which position" pattern: given a 1-indexed position, returns the
  Fibonacci number found there via a plain iterative walk up the
  recurrence (mirrors `is_lucas_number`'s own generate-and-track loop
  style, deliberately avoiding Binet's formula, which loses exact-integer
  precision at large n under floating point). Domain error for `n < 1`
  matches `nth_prime`'s convention for value-returning functions. Clean
  first pass, no bounces (3471 tests passing, up from 3463).
- **Language: bare comma multi-target assignment** — merged 2026-08-24
  via PR #307 (`feat/20260823-multi-target-assign`). Added
  `_try_multi_assign_statement` to `cinder/parser.py`, a speculative
  parse tried before `_expr_statement`'s existing single-target/comma-
  separated-statements parse, so `a, b = 1, 2;` (and the swap idiom
  `a, b = b, a;`) desugar to the same `DestructureAssign` node the
  bracketed form `[a, b] = expr;` already produces — reusing its runtime
  semantics (RHS evaluated once, length-checked, assigned left to right)
  with no interpreter changes. A single RHS expression that evaluates to
  a list (e.g. a function call) unpacks directly rather than being
  wrapped; multiple comma-separated RHS values are wrapped in a
  `ListLiteral`. Backs out cleanly to the prior parse on any non-
  matching shape, leaving `a = 1, 2;` (PR #289's `DeclSeq` form) and
  `a, b;` (independent statements) unchanged. Clean first pass, no
  bounces (3486 tests passing, up from 3471).
- **Standard library: `is_octagonal`** — merged 2026-08-24 via PR #308
  (`feat/20260823-is-octagonal`). Added `is_octagonal(value)` to
  `cinder/builtins.py`, the fifth member of the figurate-number
  membership-predicate cluster alongside `is_triangular`/
  `is_pentagonal`/`is_hexagonal`/`is_heptagonal`: `1 + 3 * value` is a
  perfect square whose root satisfies `(1 + root) % 3 == 0`, via the
  same `math.isqrt` closed-form technique as its siblings. `0` and
  negative inputs return `false` rather than raising, matching the
  cluster's closed-domain convention. Clean first pass, no bounces
  (3494 tests passing, up from 3486).
- **Standard library: `binomial`** — merged 2026-08-24 via PR #309
  (`feat/20260823-binomial`). Added `binomial(n, k)` to
  `cinder/builtins.py`, delegating to `math.comb(n, k)` and mirroring
  `_gcd`'s two-argument type-check-loop style; negative `n`/`k` raises a
  domain error, `k > n` correctly returns `0` (not an error), matching
  combinatorics convention. Clean first pass, no bounces (3506 tests
  passing, 28 subtests, up from 3494).
- **Standard library: `nth_lucas`** — merged 2026-08-24 via PR #310
  (`feat/20260823-nth-lucas`). Added `nth_lucas(n)`, the k-th Lucas
  number by 1-indexed position, to `cinder/builtins.py`, mirroring
  `nth_fibonacci`'s recurrence-iteration style and `is_lucas_number`'s
  own `L(1)=1, L(2)=3` seed so the two stay in sync position-for-
  position; `value < 1` raises a domain error rather than returning the
  textbook `L(0) = 2` seed. Clean first pass, no bounces.
- **Language: bound-identifier patterns in `match` arms** — merged
  2026-08-24 via PR #311 (`feat/20260824-match-bound-ident`). Any
  identifier other than `_` in a `match` arm pattern now matches
  unconditionally and binds the subject's value for the arm's body, in
  a fresh child scope (`cinder/interpreter.py`'s `_evaluate_match`,
  mirroring `_execute_try`'s `catch_env` pattern) that does not leak
  into or shadow the enclosing scope. Closes the gap PR #304
  deliberately left open alongside the `_` wildcard. Clean first pass,
  no bounces (3521 tests passing, up from 3506).
- **Language: multi-value literal patterns in `match` arms** — merged
  2026-08-24 via PR #312 (`feat/20260824-multi-value-match-patterns`).
  `1, 2 => body` in a `match` arm now desugars in the parser
  (`_match_arm`, `cinder/parser.py`) into N flat `MatchArm`s sharing one
  `body`, since `_evaluate_match` already tries arms in source order and
  stops at the first match — no `interpreter.py` changes needed. Mixing
  `_` or a bound identifier into a multi-value list is rejected at parse
  time via the same `pattern is None` check bound-identifier patterns
  already produced. Clean first pass, no bounces (3530 tests passing, up
  from 3521).
- **Standard library: `nth_triangular` — the k-th triangular number by
  position** — merged 2026-08-24T15:49:55Z via PR #313
  (`feat/20260824-nth-triangular`). `_nth_triangular`
  (`cinder/builtins.py`) uses the closed form `T(n) = n * (n + 1) // 2`,
  registered between `_is_octagonal` and `_is_prime`. Position `1` is
  the first *positive* triangular number (`nth_triangular(1) == 1`, not
  the degenerate `T(0) = 0` that `is_triangular(0)` accepts), matching
  the shared convention of `nth_fibonacci`/`nth_prime`/`nth_lucas`;
  `value < 1` raises a domain error. Clean first pass, no bounces (3539
  tests passing, up from 3530).
- **Standard library: `nth_catalan` — the k-th Catalan number by
  position** — merged 2026-08-25T14:47:56Z via PR #315
  (`feat/20260825-nth-catalan`). `_nth_catalan` (`cinder/builtins.py`)
  is a thin composition of `_binomial`'s own `math.comb`, using
  `C(n) = binomial(2n, n) / (n + 1)` with `index = value - 1` converting
  Cinder's 1-indexed position convention to the closed form's 0-indexed
  `n` (`nth_catalan(1) == 1`, `nth_catalan(2) == 1`, matching the
  sequence's own early repeat, not an off-by-one bug). Domain error for
  `value < 1`, matching every other `nth_*` builtin. Clean first pass,
  no bounces (3547 tests passing, up from 3539).
- **Language: flat list patterns in `match` arms (`[a, b] => a + b`)**
  — merged 2026-08-25T19:28:39Z via PR #316
  (`feat/20260825-match-list-patterns`). A leading `[` in `_match_arm`
  (`cinder/parser.py`) now parses a flat name list into a new
  `MatchArm.list_pattern` field (`cinder/ast_nodes.py`), mutually
  exclusive with the existing literal-pattern and bound-identifier
  fields; `_evaluate_match` (`cinder/interpreter.py`) tests the
  subject's shape (`isinstance` list check + length match) before
  binding each element in a fresh child `Environment` that does not
  leak into the enclosing scope, falling through to the next arm on a
  non-list subject or a length mismatch rather than raising. `_` inside
  a pattern discards that position; a repeated name (`[a, a] => a`)
  binds left to right, so the later position wins. Deliberately flat —
  no nesting, no literal sub-pattern elements, no rest/spread — those
  remain explicit future follow-ups. Clean first pass, no bounces (3558
  tests passing, up from 3547).
- **Standard library: `cartesian_product` — the Cartesian product of N
  lists** — merged 2026-08-25T19:46:47Z via PR #317
  (`feat/20260825-cartesian-product`). `_cartesian_product`
  (`cinder/builtins.py`) validates arity, outer-list type, and
  per-element list type, then delegates to `itertools.product(*lists)`,
  the same thin-wrapper composition style `nth_catalan` used for
  `math.comb`. `cartesian_product([])` returns `[[]]` (Cartesian product
  of zero sets is the singleton empty tuple, matching
  `itertools.product()`'s own no-argument behavior); `cartesian_product([[1,
  2], []])` returns `[]` (an empty inner list means no element can be
  drawn, handled natively by `itertools.product`, no special-casing
  needed). Clean first pass, no bounces (3566 tests passing, up from
  3558).
- **Language: range patterns in `match` arms (`1..10 => "small"`)** —
  merged 2026-08-25T20:05:29Z via PR #318
  (`feat/20260825-range-match-patterns`). `MatchArm` gained a fifth
  field, `range_pattern`, threaded through `ast_nodes.py`, `parser.py`,
  and `interpreter.py` alongside the existing `list_pattern`. The
  interpreter reuses the same `_evaluate_range` + `contains_value`
  machinery already used for `x in 1..5`, so both exclusive (`..`) and
  inclusive (`..=`) bounds share the existing off-by-one handling with
  no new logic duplicated, and a non-numeric subject falls through to
  the next arm instead of raising. Range patterns combine freely with
  literals in one multi-value arm (`0, 100..1000, 9999 => ...`) but,
  like list patterns, can't combine with a wildcard/bound identifier in
  the same arm. Clean first pass, no bounces (3578 tests passing, up
  from 3566).
- **Standard library: `nth_pentagonal` — the k-th pentagonal number by
  position** — merged 2026-08-26T04:15Z via PR #319
  (`feat/20260825-nth-pentagonal`). `_nth_pentagonal`
  (`cinder/builtins.py`) mirrors `_nth_triangular`'s shape exactly
  (arity check, int check, domain check, one-line closed-form return),
  computing `P(k) = k(3k - 1) / 2`. Cross-checked against
  `is_pentagonal` for every `n` from 1 to 100. Clean first pass, no
  bounces (3587 tests passing, up from 3578).
- **Language: negative literal patterns in `match` arms (`-5 => "neg"`)**
  — merged 2026-08-26T14:08:02Z via PR #320
  (`feat/20260826-neg-literal-match`). `_match_pattern`
  (`cinder/parser.py`) gained a `MINUS` branch that consumes a leading
  `-` before an `INT`/`FLOAT` literal and returns a negated `Literal`
  (line/column pointing at the `-`, not the digit); `-` before a
  non-numeric literal raises `ParseError`. No changes needed to
  `_match_arm` or `_evaluate_match` — a negative literal is still just a
  `Literal` pattern, so multi-value arms and evaluation reuse existing
  code paths unchanged. General unary-minus expressions and negative
  range-pattern bounds remain out of scope. Clean first pass, no
  bounces (3595 tests passing, up from 3587).
- **Standard library: `power_set` — every subset of a list** — merged
  2026-08-26T14:20:35Z via PR #321 (`feat/20260826-power-set`).
  `_power_set` (`cinder/builtins.py`) mirrors `_cartesian_product`'s
  thin-wrapper composition style, enumerating every subset via
  `itertools.combinations(items, size)` across sizes `0` to `len(items)`.
  Registered directly after `_cartesian_product`/`_enumerate` in the
  builtins dict. `power_set([])` returns `[[]]` per the standard
  mathematical convention. Cross-checked the `2**n` cardinality identity
  across five list sizes. Clean first pass, no bounces (3602 tests
  passing, up from 3595).
- **Language: literal elements in list patterns (`[0, b] => ...`)** —
  merged 2026-08-26T14:31:38Z via PR #322
  (`feat/20260826-literal-list-elements`). Widened `_match_list_pattern`'s
  per-element parsing (renamed `_match_list_pattern_name` to
  `_match_list_pattern_entry`, `cinder/parser.py`) to accept a bare
  literal token (`INT`/`FLOAT`/`STRING`/`TRUE`/`FALSE`/`NIL`) per element
  in addition to a bound identifier or `_`, mirroring `_match_pattern`'s
  own scalar-literal `Literal` construction; `_evaluate_match`'s
  list-pattern branch (`cinder/interpreter.py`) now checks each entry's
  kind, testing `Literal` entries with `values_equal` (falling through to
  the next arm on mismatch) while identifier/`_` entries keep their
  existing bind-or-discard behavior. Nested list patterns as elements
  (`[1, [a, b]]`) and rest capture remain out of scope. Clean first pass,
  no bounces (3609 tests passing, up from 3602).
- **Standard library: `nth_hexagonal` — the k-th hexagonal number by
  position** — merged 2026-08-27T03:23:08+08:00 via PR #323
  (`feat/20260826-nth-hexagonal`). Added `_nth_hexagonal`
  (`cinder/builtins.py`) using the closed form `H(k) = k(2k - 1)`,
  mirroring `_nth_triangular`/`_nth_pentagonal`'s arity/type/domain-check
  structure exactly. Registered in the builtins dispatch table alongside
  the other `nth_*` entries. Clean first pass, no bounces (3618 tests
  passing).
- **Language: rest capture in list patterns (`[a, ...rest] => ...`)** —
  merged 2026-08-27T03:41:38+08:00 via PR #324
  (`feat/20260826-rest-capture-list-pattern`). Widened
  `_match_list_pattern` (`cinder/parser.py`) to optionally parse a
  trailing `...name` (or `..._` to discard) after the fixed-prefix
  entries, returning an `(entries, rest)` tuple; `MatchArm` gained a
  `list_rest` field (`cinder/ast_nodes.py`) as its fifth positional slot;
  `_evaluate_match` (`cinder/interpreter.py`) now accepts subjects with
  *at least* as many elements as the fixed prefix when a rest is present
  and binds the tail as a sliced copy. Mirrors the "rest capture" escape
  hatch `let`/assignment destructuring already had. Clean first pass, no
  bounces (3630 tests passing).
- **Standard library: `permutations` — every ordering of a list** —
  merged 2026-08-26T19:55:34Z via PR #325
  (`feat/20260826-permutations`). Added `_permutations`
  (`cinder/builtins.py`), a thin wrapper over
  `itertools.permutations(items)` (full-length only, no `r` argument),
  registered directly after `power_set` in the builtins dispatch table.
  Duplicate elements are not de-duplicated, matching
  `itertools.permutations`'s position-based (not value-based) behavior.
  Clean first pass, no bounces (3638 tests passing).
- **Language: flat map patterns in `match` arms (`{a, b} => ...`)** —
  merged 2026-08-26T20:09:20Z via PR #326
  (`feat/20260826-match-map-pattern`). Added a `map_pattern` field to
  `MatchArm` (`cinder/ast_nodes.py`), a `{` branch in `_match_arm` plus
  `_match_map_pattern`/`_match_map_pattern_name` (`cinder/parser.py`),
  and a matching branch in `_evaluate_match` (`cinder/interpreter.py`).
  Bare bound-identifier keys only — a map pattern matches if the subject
  is a map containing every named key, extra keys are ignored, and a
  missing key or non-map subject falls through without raising, mirroring
  the same "falls through, doesn't raise" convention flat list patterns
  and range patterns already use. Closes the same destructuring-vs-match
  gap flat list patterns (PR #316) closed for lists. Clean first pass, no
  bounces (3650 tests passing).
- **Standard library: `combinations` — every r-length combination of a
  list** — merged 2026-08-27T~ via PR #327
  (`feat/20260826-combinations`). Added `_combinations`
  (`cinder/builtins.py`), a thin wrapper over
  `itertools.combinations(items, size)` registered directly after
  `permutations` in the builtins dispatch table, guarding negative size
  explicitly for a clean `CinderRuntimeError` (itertools would otherwise
  raise a Python-level `ValueError`). `size == 0` returns `[[]]`, `size >
  len(items)` returns `[]`, and duplicate elements are not de-duplicated,
  matching `itertools`'s own semantics. Closes the same
  enumerate-vs-count gap `binomial` has to `power_set` itself, the exact
  gap `permutations` (PR #325) already closed for orderings against
  `is_permutation`. Clean first pass, no bounces (3661 tests passing, up
  from 3650).
- **Standard library: `nth_heptagonal` — the k-th heptagonal number by
  position** — merged 2026-08-27T14:16:00Z via PR #328
  (`feat/20260827-nth-heptagonal`). Added `_nth_heptagonal`
  (`cinder/builtins.py`), registered directly after `_nth_hexagonal` in the
  builtins dispatch table: arity check, int check, domain check (`value <
  1`), one-line closed-form return `H(k) = k(5k - 3) // 2`, cross-checked
  against `_is_heptagonal`'s own `40 * value + 9` perfect-square test for
  positions 1-100. Fourth member of the "value-returning sibling of an
  `is_*` membership test" pattern in the figurate-number cluster, after
  `nth_triangular` (PR #313), `nth_pentagonal` (PR #319), and
  `nth_hexagonal` (PR #323). Clean first pass, no bounces (3670 tests
  passing, up from 3661).
- **Language: negative bounds in range patterns (`-10..0 => "neg"`)** —
  merged 2026-08-27T14:28:49Z via PR #329
  (`feat/20260827-neg-range-bounds`). Negative literal patterns (PR #320)
  let a plain literal pattern be negated, but range patterns (PR #318)
  could only parse an `INT` literal bound, so `-10..0 => "neg"` raised a
  `ParseError` instead of parsing. Widened `_match_pattern`'s `MINUS`
  branch (`cinder/parser.py`) to check for a trailing `..`/`..=` after a
  negative int, and factored a shared `_match_range_bound` helper (used by
  both the negative-start and positive-start paths) so either bound of a
  range pattern can now be negative. Float bounds after `-` remain
  literal-pattern only. Clean first pass, no bounces (3681 tests passing,
  up from 3670).
- **Language: nested list patterns in `match` arms (`[a, [b, c]] => ...`)**
  — merged 2026-08-27T19:24:05Z via PR #330
  (`feat/20260827-nested-list-match`). Flat list patterns, literal
  elements, and rest capture had all landed, but a list-pattern element
  still couldn't itself be a list pattern — the last flat-vs-nested gap in
  list patterns, already closed for `let` destructuring and for map
  patterns one level down. Added a branch to
  `_match_list_pattern_entry` (`cinder/parser.py`) that recurses into
  `_match_list_pattern` itself on a leading `[`, giving arbitrary-depth
  nesting and nested rest capture for free from the existing production.
  Factored `_evaluate_match`'s inline list-matching logic
  (`cinder/interpreter.py`) into a recursive `_match_list_entries` helper
  so nested tuple entries can call back into the same matching logic.
  Clean first pass, no bounces (3691 tests passing, up from 3681).
- **Standard library: `nth_octagonal` — the k-th octagonal number by
  position** — merged 2026-08-27T19:24:10Z via PR #331
  (`feat/20260827-nth-octagonal`). Added `_nth_octagonal`
  (`cinder/builtins.py`), registered directly after `_nth_heptagonal` in
  the builtins dispatch table: arity check, int check, domain check
  (`value < 1`), one-line closed-form return `O(k) = k(3k - 2)`,
  cross-checked against `_is_octagonal`'s own `3 * value + 1`
  perfect-square test for positions 1-100. Fifth member of the
  "value-returning sibling of an `is_*` membership test" pattern in the
  figurate-number cluster, after `nth_triangular` (PR #313),
  `nth_pentagonal` (PR #319), `nth_hexagonal` (PR #323), and
  `nth_heptagonal` (PR #328). Clean first pass, no bounces (3690 tests
  passing, up from 3681).
- **Language: per-key rename in match map patterns (`{a: x, b} => ...`)**
  — merged 2026-08-28 via PR #332 (`feat/20260827-match-map-rename`). Flat
  match map patterns (PR #326) only bound each key to a variable of the
  same name; widened `_match_map_pattern`/`_match_map_pattern_entry`
  (`cinder/parser.py`) to return `(key, binding)` pairs, mirroring `let`
  map destructuring's existing `_destructure_map_pattern_entry` split, and
  updated the interpreter's `map_pattern` match branch
  (`cinder/interpreter.py`) to bind `value` under `binding` instead of
  `key`. Scoped to bare rename only — no nesting, no rest capture, no
  defaults, staged the same way flat map patterns themselves were. Clean
  first pass, no bounces (3710 tests passing, up from 3690).
- **Standard library: `combinations_with_replacement` — r-length selections
  that allow repeats** — merged 2026-08-27T19:54:47Z via PR #333
  (`feat/20260827-combinations-with-replacement`). Added
  `_combinations_with_replacement` to `cinder/builtins.py`, mirroring
  `_combinations`'s exact shape (arity check, list check, int check,
  non-negative-size check, one-line `itertools` wrapper) but omitting the
  `size > len(items)` check since replacement makes that valid. Completes
  the classic itertools "selections" trio (`permutations`, `combinations`,
  `combinations_with_replacement`). Clean first pass, no bounces (3720
  tests passing, up from 3710).
- **Standard library: `is_nonagonal` — the sixth figurate-number membership
  test** — merged 2026-08-28 via PR #334 (`feat/20260827-is-nonagonal`).
  Added `_is_nonagonal` to `cinder/builtins.py`, registered directly after
  `_is_octagonal`: arity check, int check, early-`False` on negative, then
  the same perfect-square-plus-modular-residue shape as its five siblings
  (`candidate = 56n + 25` must be a perfect square whose root satisfies
  `(root + 5) % 14 == 0`). Completes the triangular..nonagonal membership
  cluster. Clean first pass, no bounces (3727 tests passing, up from
  3720).
- **Standard library: `is_catalan` — membership test for `nth_catalan`'s
  existing sibling** — merged 2026-08-29T14:10:01Z via PR #336
  (`feat/20260829-is-catalan`). Added `_is_catalan` to
  `cinder/builtins.py`, registered directly after `nth_catalan`: since
  Catalan numbers have no closed-form membership test, it follows
  `_is_perfect_power`'s bounded iterative-search shape instead, growing
  candidates via the same `math.comb(2*index, index) // (index+1)`
  formula `_nth_catalan` uses and stopping as soon as a candidate meets or
  exceeds the target. Completes the last `nth_*` builtin without a
  matching `is_*` counterpart. Clean first pass, no bounces (3734 tests
  passing, up from 3727).
- **Language: rest capture in match map patterns
  (`{a, ...rest} => ...`)** — merged 2026-08-29T14:10:04Z via PR #335
  (`feat/20260827-rest-capture-map`). Ported the existing list-pattern
  rest-capture machinery to map patterns: `_match_map_pattern_rest_name`
  in `cinder/parser.py` mirrors `_match_list_pattern_rest_name` (same
  "expected an identifier or '_'" error, same `_`-discards convention,
  rest must be last), the interpreter folds leftover keys into
  `arm.map_rest` unless it's `"_"`, and `ast_nodes.py` gained a `map_rest`
  field alongside `list_rest`. Closes the last capability gap between
  match map patterns and list patterns. Clean first pass, no bounces
  (3741 tests passing, up from 3734).
- **Language: nested patterns as map pattern values (`{a: {b, c}} => ...`,
  `{a: [x, y]} => ...`)** — merged 2026-08-29T14:29:04Z via PR #337
  (`feat/20260829-nested-map-pattern-values`). Widened
  `_match_map_pattern_entry` (`cinder/parser.py`) to recurse into
  `_match_list_pattern`/`_match_map_pattern` when a map pattern's value
  slot is followed by `[`/`{`; a nested list pattern is tagged as a
  3-tuple `(entries, rest, True)` while a nested map pattern stays a
  2-tuple `(entries, rest)`, mirroring the disambiguation
  `_destructure_map_pattern_entry` already uses, so the new
  `_match_map_entries` interpreter helper (mirroring
  `_match_list_entries`) can dispatch unambiguously. Nesting works to
  arbitrary depth and composes with per-key rename (PR #332) and rest
  capture (PR #335). Closes the last flat-vs-nested gap between match map
  patterns and everything else in Cinder that already destructures maps.
  Clean first pass, no bounces (3761 tests passing, 28 subtests passing,
  up from 3741).
- **Language: default values for trailing elements in match list
  patterns (`[a, b = 0] => ...`)** — merged 2026-08-29T14:49:17Z via PR
  #338 (`feat/20260829-match-list-defaults`). Widened
  `_match_list_pattern_entry` (`cinder/parser.py`) to return a `(entry,
  default)` pair for every entry kind, mirroring
  `_destructure_list_pattern_entry`'s own shape, and only offering a
  trailing `= expr` after a plain identifier; `_match_list_entries`
  (`cinder/interpreter.py`) evaluates the default in the arm's own
  environment when the subject runs out of elements, left-to-right, so
  an earlier-bound element is visible to a later default. Defaults widen
  the minimum matchable length, not the maximum, and compose with rest
  capture and nesting for free via the shared recursive production.
  Closes the last capability gap between match list patterns and `let`
  list destructuring. Clean first pass, no bounces (3772 tests passing,
  up from 3761).
- **Standard library: `is_twin_prime` — membership test for primes with
  a twin partner** — merged 2026-08-29T15:03:36Z via PR #339
  (`feat/20260829-is-twin-prime`). Added `_is_twin_prime`
  (`cinder/builtins.py`), registered directly after `_is_circular_prime`,
  following that predicate's own shape of a locally-scoped trial-division
  helper rather than a shared module-level one, matching the file's
  existing convention for the prime-relationship cluster. `n` is a twin
  prime when it is itself prime and at least one of `n - 2`/`n + 2` is
  also prime, covering both lower- and upper-twin cases. Closes the last
  gap in the `is_semiprime`/`is_sphenic`/`is_emirp`/`is_circular_prime`
  adjacency/structure cluster. Clean first pass, no bounces (3780 tests
  passing, up from 3772).
- **Standard library: `nth_nonagonal` — the k-th nonagonal number by
  position** — merged 2026-08-29T16:11:34Z via PR #340
  (`feat/20260829-nth-nonagonal`). Added `_nth_nonagonal`
  (`cinder/builtins.py`), registered directly after `_nth_octagonal`,
  implementing the closed form `N(k) = k(7k - 5)/2` — the same formula
  `_is_nonagonal`'s own membership check already verifies against.
  Closes the last figurate-number gap: every `nth_triangular` through
  `nth_octagonal` sibling now has a matching `is_*` counterpart and vice
  versa. Clean first pass, no bounces (3789 tests passing, up from 3780).
- **Standard library: `nth_happy_number` — the k-th happy number by
  position** — merged 2026-08-29T16:27:45Z via PR #341
  (`feat/20260829-nth-happy-number`). Added `_nth_happy_number`
  (`cinder/builtins.py`), registered directly after `_is_sad_number`,
  following `nth_prime`'s sequential candidate-scan shape (happy numbers
  have no closed form) with a locally-scoped cycle-detection helper for
  the happiness check. Gives the happy/sad-number cluster a value-returning
  counterpart the way the figurate-number and prime clusters already have.
  Clean first pass, no bounces (3799 tests passing, up from 3789).
- **Language: default values in match map patterns (`{a, b = 0} => ...`)**
  — merged 2026-08-29T16:46:35Z via PR #342
  (`feat/20260829-match-map-defaults`). Widened
  `_match_map_pattern_entry` (`cinder/parser.py`) to parse an optional
  `= expr` on a plain-identifier or renamed binding, and the
  interpreter's `map_pattern` match branch (`cinder/interpreter.py`) to
  evaluate the default, in the arm's own environment left-to-right, when
  a key is absent instead of failing the match. Composes with rename
  (PR #332) and rest capture (PR #335) in the same pattern; nested
  list/map sub-patterns stay out of scope, mirroring list-pattern
  defaults' (PR #338) own restriction. Clean first pass, no bounces
  (3809 tests passing, up from 3799).
- **Standard library: `nth_semiprime` — the k-th semiprime by position**
  — merged 2026-08-29T17:01:40Z via PR #343
  (`feat/20260829-nth-semiprime`). Added `_nth_semiprime`
  (`cinder/builtins.py`), registered directly after `_is_semiprime`,
  following `nth_prime`'s/`nth_happy_number`'s sequential candidate-scan
  shape (semiprimes have no closed form) with a locally-scoped
  factor-count helper reused from `is_semiprime`'s own logic. Clean
  first pass, no bounces (3819 tests passing, up from 3809).
- **Standard library: `nth_pronic` — the k-th pronic number by position**
  — merged 2026-08-29T21:22:40Z via PR #344
  (`feat/20260829-nth-pronic`). Added `_nth_pronic`
  (`cinder/builtins.py`), registered directly after `_is_pronic`,
  using the closed form `N(k) = k * (k + 1)` (the same relationship
  `is_pronic` already checks membership against), mirroring
  `nth_octagonal`'s one-line shape. Clean first pass, no bounces (3828
  tests passing, up from 3819).
- **Language: range case values in `switch` statements** — merged
  2026-08-29T21:33:51Z via PR #345 (`feat/20260829-switch-range-case`).
  Fixed `_execute_switch` (`cinder/interpreter.py`) to special-case a
  `RangeExpr`-typed case value via `_evaluate_range` + `contains_value`,
  mirroring `_evaluate_match`'s existing `range_pattern` branch, instead
  of materializing the range to a list and comparing it with
  `values_equal` (which could never match a scalar scrutinee). Clean
  first pass, no bounces (3834 tests passing, up from 3828).
- **Standard library: `nth_abundant` — the k-th abundant number by
  position** — merged 2026-08-29T21:46:38Z via PR #346
  (`feat/20260829-nth-abundant`). Added `_nth_abundant`
  (`cinder/builtins.py`), registered directly after `_is_abundant`,
  a sequential candidate scan mirroring `nth_prime`'s shape since
  abundant numbers have no closed form. Clean first pass, no bounces
  (3842 tests passing, up from 3834).
- **Standard library: `nth_repdigit` — the k-th repdigit by position** —
  merged 2026-08-29T22:03:38Z via PR #347 (`feat/20260829-nth-repdigit`).
  Added `_nth_repdigit` (`cinder/builtins.py`), registered directly after
  `_is_repdigit`, a sequential candidate scan mirroring `nth_abundant`'s/
  `nth_semiprime`'s shape since repdigits have no closed form; tests
  capped at `k = 50` per the task's performance note (candidate scan cost
  grows exponentially with position). Clean first pass, no bounces (3852
  tests passing, up from 3842).
- **Language: whole-value `as` binding in match list/map patterns** —
  merged 2026-08-30T~06:20Z via PR #348 (`feat/20260829-as-whole-binding`).
  Added a new `as` keyword (`cinder/tokens.py`), `MatchArm.whole_binding`
  (`cinder/ast_nodes.py`), a `_match_whole_binding` parser helper wired
  into the list/map pattern branches of `_match_arm`, and interpreter
  support in `_evaluate_match` that defines the binding in the arm's own
  child environment right before the body runs — composes with rest
  capture and defaults, scoped per-arm with no leak. Clean first pass, no
  bounces (3864 tests passing, up from 3852).
- **Language: lexicographic comparison operators for lists** (`[1, 2] <
  [1, 3]`) — merged 2026-08-30T~06:20Z via PR #349
  (`feat/20260830-list-lexicographic-compare`). Admitted `list`/`list`
  into `_compare`'s `comparable` check (`cinder/interpreter.py`) and
  wrapped the actual `<`/`<=`/`>`/`>=` in `try`/`except TypeError` so a
  mismatched element type partway through a comparison raises a clean
  `CinderRuntimeError` instead of a raw Python `TypeError`; chained
  comparisons (`a < b < c`) got the fix for free via the shared
  `_compare` method. Clean first pass, no bounces (3873 tests passing, up
  from 3864).
- **Standard library: `is_disarium` — digit-position-power sum test** —
  merged 2026-08-30T~15:15Z via PR #350 (`feat/20260830-is-disarium`).
  Added `_is_disarium` (`cinder/builtins.py`), registered directly after
  `_is_armstrong`, mirroring its shape but raising each digit to its own
  1-indexed positional exponent instead of one shared exponent. Clean
  first pass, no bounces (3883 tests passing, up from 3873).
- **Standard library: `nth_kaprekar` — the k-th Kaprekar number by
  position** — merged 2026-08-30T~15:15Z via PR #351
  (`feat/20260830-nth-kaprekar`). Added `_nth_kaprekar`
  (`cinder/builtins.py`), registered directly after `_is_kaprekar`, a
  sequential candidate scan mirroring `nth_prime`'s shape since Kaprekar
  numbers have no closed form; cross-check test capped at `k = 20` per
  the task's performance note. Clean first pass, no bounces (3892 tests
  passing, up from 3883).
- **Language: `else` clause on `while` loops (Python-style loop-`else`)**
  — merged 2026-08-30T~15:38Z via PR #352 (`feat/20260830-while-else`).
  Added a defaulted `WhileStmt.else_branch` field (`cinder/ast_nodes.py`),
  a trailing-`else` lookahead in `_while_statement`
  (`cinder/parser.py`) mirroring `_if_statement`'s, and a `broke`-flag
  skip check in the interpreter's `WhileStmt` branch. Scoped to plain
  `while` only, not `do`-`while`/foreach `for`/C-style `for`. Deliberate
  dangling-attachment behavior change for `if (cond) while (x) {} else
  {}` (the `else` now binds to the `while`), locked in with a regression
  test. Clean first pass, no bounces (3906 tests passing, up from 3892).
- **Standard library: `is_smith_number`** — merged 2026-08-30T~15:43Z via
  PR #353 (`feat/20260830-is-smith-number`). Added `_is_smith_number`
  (`cinder/builtins.py`), registered directly after `prime_factors`,
  reimplementing the `_is_prime`-shaped trial-division pre-check and the
  `_prime_factors`-shaped factorization loop locally rather than calling
  either directly, matching `_nth_semiprime`/`_is_sphenic`'s existing
  convention. Compares `digit_sum(n)` against the combined digit sum of
  `n`'s prime factors with multiplicity; primes and non-composites
  excluded by definition. Clean first pass, no bounces (3922 tests
  passing, up from 3906).
- **Language: ordering comparison operators (`<`/`<=`/`>`/`>=`) for
  maps** — merged 2026-08-30T~15:56Z via PR #354
  (`feat/20260830-map-ordering`). Extended `_compare`
  (`cinder/interpreter.py`) to accept `dict`/`dict` by comparing each
  map's items as a list of `(key, value)` pairs sorted by key, then
  lexicographically comparing those two sorted lists the same way list
  comparison already does — consistent with `==`'s existing
  order-independent map equality. Reuses the same `try`/`except
  TypeError` pattern already used for incomparable list elements, with
  `is_map_compare` captured before `left`/`right` are reassigned so the
  except branch still picks the right message. Scoped to direct
  map-vs-map comparison only — a map nested inside a list still raises,
  since list comparison delegates to Python's native list `<` rather
  than routing back through `_compare`; locked in with a regression
  test. Clean first pass, no bounces (3933 tests passing, up from
  3922).
- **Standard library: `is_pandigital` — 0-to-9 pandigital number
  test** — merged 2026-08-30T~16:08Z via PR #355
  (`feat/20260830-is-pandigital`). Added `_is_pandigital`
  (`cinder/builtins.py`), grouped with the other digit predicates
  directly after `_is_disarium`: a number is pandigital iff its decimal
  digits are exactly the multiset `{0,1,...,9}`, each appearing once,
  i.e. `len(digits) == 10 and set(digits) == set("0123456789")`.
  Negative numbers excluded, matching every other `is_*` digit
  predicate's own convention. Scoped to the single unambiguous "0 to 9"
  definition only — the "1 to 9" zeroless and "at least once" variants
  some sources also call "pandigital" are deliberately left for a
  future, differently named builtin. Clean first pass, no bounces (3944
  tests passing, up from 3933).
- **Language: difference operator (`-`) for maps** — merged
  2026-08-30T19:47:04Z via PR #356 (`feat/20260830-map-difference`).
  `_apply_binary_operator`'s `MINUS` branch (`cinder/interpreter.py`)
  now special-cases `dict`/`dict` as key-based removal — a fresh map of
  every left-operand pair whose key is absent from the right operand,
  mirroring the existing `PLUS` branch's dict-merge special case and
  giving `+`'s inverse an infix spelling. Scoped to `map`/`map` only;
  list difference left for a future task. Clean first pass, no bounces
  (3958 tests passing, up from 3944).
- **Standard library: `transpose` — matrix (list-of-lists) transpose** —
  merged 2026-08-30T20:01:12Z via PR #357 (`feat/20260830-transpose`).
  Added `_transpose` (`cinder/builtins.py`), grouped with the other
  zip-family collection functions directly after `_unzip`: generalizes
  `unzip`'s special-case two-column transpose to an arbitrary-width
  matrix (a list of same-length rows), validating the outer argument is
  a list and every row is a list of equal length, with empty matrices
  and all-empty-row matrices both returning `[]`. Clean first pass, no
  bounces (3968 tests passing, up from 3958).
- **Language: `else` clause on `for`-in loops (Python-style loop-`else`)**
  — merged 2026-08-31T~ via PR #358 (`feat/20260830-for-else`). Extends
  the `else { ... }` clause PR #352 added for plain `while` loops to the
  foreach `for NAME in EXPR { ... }` form: `ForStmt` gains an
  `else_branch` field, the parser consumes a trailing `else` after the
  for-body block (unambiguous here since a `for`'s body is always
  brace-delimited, unlike `while`'s), and `_execute_for` tracks a
  `broke` flag through iteration to run `else_branch` only when the
  loop exits without an intervening `break` — `continue` doesn't skip
  it, `return`/uncaught exception/propagating labeled `break` do.
  Scoped to the foreach form only; `ForCStmt` and `DoWhileStmt` remain
  future tasks. Clean first pass, no bounces (3981 tests passing, up
  from 3968).
- **Standard library: `is_vampire_number` — digit-permutation factor
  pairs** — merged 2026-09-01 via PR #359
  (`feat/20260901-is-vampire-number`). Added `_is_vampire_number`
  (`cinder/builtins.py`), grouped directly after `_is_smith_number`:
  tests whether an even-digit-count number's decimal digits can be
  rearranged into two equal-length "fangs" that multiply back to it
  (OEIS A014575), excluding the trivial case where both fangs are
  multiples of 10. Clean first pass, no bounces (3995 tests passing, up
  from 3981). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Standard library: `is_trimorphic_number` — cube-ending
  digit-invariance test** — merged 2026-09-01 via PR #360
  (`feat/20260901-is-trimorphic-number`). Added `_is_trimorphic_number`
  (`cinder/builtins.py`), grouped directly after `_is_automorphic`: the
  one-power extension testing whether a number's cube ends in the
  number itself (OEIS A033819); every automorphic number is
  automatically trimorphic, but the reverse doesn't hold (`24` is
  trimorphic but not automorphic), and a dedicated regression test
  pins that non-alias distinction. Clean first pass, no bounces (4009
  tests passing, up from 3995). README/PROJECT.md updates left to the
  Architect's next grooming pass.
- **Language: `else` clause on `do`-`while` loops (Python-style
  loop-`else`, the last loop kind)** — merged 2026-09-01 via PR #361
  (`feat/20260901-do-while-else`). Threaded a `broke` flag through
  `DoWhileStmt`'s existing loop (`cinder/interpreter.py`) and an
  else-or-semicolon branch through `_do_while_statement`
  (`cinder/parser.py`), mirroring `WhileStmt.else_branch`'s established
  pattern: the `else` block runs once on normal completion, skipped by
  `break` (including labeled) or a propagating `return`/exception,
  unaffected by `continue`. No dangling-`else` ambiguity since the
  trailing `else` sits after the `while (cond)` clause. Closes the gap
  PR #352 and the foreach `for`-in `else` task both explicitly left
  open. Clean first pass, no bounces (4022 tests passing, up from
  4009). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Standard library: `is_munchausen_number` — digit-to-its-own-power
  sum test** — merged 2026-09-02 via PR #362
  (`feat/20260901-is-munchausen-number`). Added `_is_munchausen_number`
  to `cinder/builtins.py`, grouped with the other digit-power-sum
  predicates after `is_strong_number`, using a `0**0 := 0` convention
  override (Python's own `0 ** 0` is `1`) to match the standard
  reference definition. Clean first pass, no bounces (4032 tests
  passing, up from 4022). README/PROJECT.md updates left to the
  Architect's next grooming pass.
- **Language: `-` (difference) operator for lists (set-style, mirrors
  map `-`)** — merged 2026-09-02 via PR #363
  (`feat/20260901-list-difference-operator`). Added a list-list branch
  to `_apply_binary_operator`'s `MINUS` case in `cinder/interpreter.py`,
  alongside the existing map-map branch from PR #356, giving list `-`
  the same set-style semantics as the `difference()` builtin
  (left-dedup via `values_equal`, then drop anything found in the
  right). Clean first pass, no bounces (4036 tests passing, up from
  4032). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Language: `else` clause on C-style `for` loops** — merged
  2026-09-01T18:49:41Z via PR #364 (`feat/20260901-for-c-else`). Added
  `else_branch` to `ForCStmt` in `cinder/ast_nodes.py`, an else-check in
  `_for_c_statement` mirroring `_for_statement`'s, and a `broke`-flag
  post-loop check in `_execute_for_c` mirroring `_execute_for`'s —
  running the else in `loop_env` (not `env`) so closures see the final
  `init`-declared binding. Closes the loop-`else` arc for all four loop
  kinds (`while` #352, `for`-in #358, `do`-`while` #361, `for`-C-style
  #364). Clean first pass, no bounces (4058 tests passing, up from
  4036). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Language: `throw`/`catch` carry any value, not just strings** —
  merged 2026-09-02 via PR #365 (`feat/20260902-throw-catch-value`).
  Added an optional `value` field (defaulting to `message`) to
  `CinderRuntimeError` in `cinder/errors.py`, guarded by a module-level
  `_UNSET` sentinel so a genuinely thrown `nil`/`false` isn't mistaken
  for "no value supplied"; `ThrowStmt` now evaluates and passes the raw
  value through (using `stringify` only for the display `.message`),
  and `_execute_try` binds `catch (e)` to `error.value` instead of
  `error.message`. Fixes the double-failure bug where throwing a
  non-string value got caught with the type-check's own error text
  instead of the thrown value. All ~430 internal `CinderRuntimeError`
  call sites are unaffected since none pass `value=`. Clean first pass,
  no bounces (4065 tests passing, up from 4058). README/PROJECT.md
  updates left to the Architect's next grooming pass.
- **Standard library: `is_keith_number` — digit-recurrence self-generating
  number** — merged 2026-09-02 via PR #366
  (`feat/20260901-is-keith-number`). Added `_is_keith_number` to
  `cinder/builtins.py`, directly after `_is_trimorphic_number`: seeds an
  n-digit number's own digits as a sequence, extends it with a
  digit-count-wide Fibonacci-style recurrence, and checks whether the
  original value reappears as a later term. Single-digit and negative
  inputs are excluded per the standard convention (OEIS A007629 starts
  at `14`). Clean first pass, no bounces (4076 tests passing, up from
  4065). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Language: `&` (intersection) operator for lists (set-style, mirrors
  list `-`)** — merged 2026-09-02 via PR #367
  (`feat/20260901-list-amp-intersection`). Added a list-list special
  case for `AMP` in `_apply_binary_operator`
  (`cinder/interpreter.py`), directly above the existing `_bitwise_op`
  dispatch: dedupes the left list via `values_equal`, then keeps
  elements also present in the right via `contains_value` — the same
  set semantics as the existing `intersection()` builtin, now with an
  infix spelling mirroring list `-`'s difference. Int-int `&` and
  every other operand combination still fall through unchanged to
  `_bitwise_op`. Clean first pass, no bounces (4092 tests passing, up
  from 4076). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Standard library: `run_length_encode` / `run_length_decode` —
  consecutive-run compression** — merged 2026-09-02 via PR #368
  (`feat/20260902-run-length-encode`). Added the pair to
  `cinder/builtins.py` directly after `group_consecutive`, mirroring
  `zip`/`unzip` and `flatten`/`chunk` as inverse siblings:
  `run_length_encode(xs)` collapses each maximal run of consecutive
  equal elements (via `values_equal`, not native `==`, so `1` and
  `true` never merge) into a `[value, count]` pair, and
  `run_length_decode(pairs)` is the exact inverse. Clean first pass,
  no bounces (4109 tests passing, up from 4092). README/CHANGELOG/
  PROJECT.md updates left to the Architect's next grooming pass.
- **Language: `&` (intersection) operator for maps (key-based, mirrors
  map `-`)** — merged 2026-09-02 via PR #369
  (`feat/20260902-map-and-intersection`). Added a dict-dict special
  case for `AMP` in `_apply_binary_operator` (`cinder/interpreter.py`),
  directly above the existing list-list `AMP` branch, mirroring `MINUS`'s
  dict-dict branch: key-based intersection keeping the *left* map's
  value for every key present in both sides, right-side values ignored
  entirely — the same "keys decide, left's values win" convention map
  `-` already set. Compound assignment (`&=`) on a map target works for
  free. Clean first pass, no bounces (4125 tests passing, up from 4109).
  README/PROJECT.md updates left to the Architect's next grooming pass.
- **Standard library: `is_luhn_valid` — Luhn checksum validator for
  digit strings** — merged 2026-09-02 via PR #370
  (`feat/20260902-is-luhn-valid`). Added `_is_luhn_valid` to
  `cinder/builtins.py` directly after `_is_numeric_string`: type-checks
  the argument is a string, checks it's non-empty and every character
  is an ASCII digit (`"0123456789"` membership, not `str.isdigit()`,
  to avoid non-ASCII Unicode digit characters), then doubles every
  second digit from the right with the classic >9 correction and
  checks the total sum is a multiple of 10. Type error fires before the
  digit-content error. Clean first pass, no bounces (4138 tests passing,
  up from 4125). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Language: `|` (union) operator for lists (set-style, mirrors list
  `&`/`-`)** — merged 2026-09-02 via PR #371
  (`feat/20260902-list-union`). Added a list-list special case for
  `PIPE` in `_apply_binary_operator` (`cinder/interpreter.py`),
  directly above the existing dispatch to `_bitwise_op`: concatenates
  both operands and dedupes via `values_equal`-based membership (not
  native `==`/`in`), matching `union()`'s "dedupe the concatenation,
  first-seen order" convention. Int-int `|` still falls through
  unchanged to `_bitwise_op`; mixed list/non-list operands still raise
  the existing type error. Compound assignment (`|=`) works for free.
  Clean first pass, no bounces (4154 tests passing, up from 4138).
  README/PROJECT.md updates left to the Architect's next grooming pass.
- **Standard library: `is_polydivisible`** — merged 2026-09-03 via PR #372
  (`feat/20260902-is-polydivisible`). Added `_is_polydivisible` to
  `cinder/builtins.py`, directly after `_is_disarium`: checks that every
  length-`i` prefix of a non-negative int's decimal digits is divisible
  by `i`. Clean first pass, no bounces (4167 tests passing, up from
  4154). README/PROJECT.md updates left to the Architect's next grooming
  pass.
- **Language: `^` (symmetric difference) operator for lists (set-style,
  mirrors list `&`/`|`/`-`)** — merged 2026-09-03 via PR #373
  (`feat/20260902-list-caret-symdiff`). Added a list-list special case
  for `CARET` in `_apply_binary_operator` (`cinder/interpreter.py`),
  directly above the existing dispatch to `_bitwise_op`: dedupes each
  side independently via `values_equal`-based membership, then returns
  left-only elements followed by right-only elements, matching
  `symmetric_difference()`'s convention. Int-int `^` still falls
  through unchanged to `_bitwise_op`; mixed list/non-list operands
  still raise the existing type error. Compound assignment (`^=`)
  works for free. Clean first pass, no bounces (4183 tests passing, up
  from 4167). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Standard library: `is_self_number` — Colombian/self-number
  predicate** — merged 2026-09-02 via PR #374
  (`feat/20260902-is-self-number`). Added `_is_self_number` to
  `cinder/builtins.py`, directly after `_is_sad_number`: a bounded
  generator search (`m >= n - 9*d`) checking whether any smaller `m`
  satisfies `m + digit_sum(m) == n`, matching OEIS A003052. Clean
  first pass, no bounces (4194 tests passing, up from 4183).
  README/PROJECT.md updates left to the Architect's next grooming
  pass.
- **Language: `|` (union) operator for maps** — merged 2026-09-02 via
  PR #375 (`feat/20260902-map-pipe-union`). Added a dict-dict special
  case for `PIPE` in `_apply_binary_operator` (`cinder/interpreter.py`),
  directly above the dispatch to `_bitwise_op`: `result = dict(right);
  result.update(left)` gives left's value priority on conflicts,
  mirroring map `&`/`-`'s "left's values win" convention (map `+`
  remains the separate, right-wins general merge). Int-int and
  list-list `|` still fall through unchanged; mixed map/non-map
  operands still raise the existing type error. Compound assignment
  (`|=`) works for free. Clean first pass, no bounces (4209 tests
  passing, up from 4194). README/PROJECT.md updates left to the
  Architect's next grooming pass.
- **Standard library: `is_weird_number` — abundant but not semiperfect**
  — merged 2026-09-03 via PR #377 (`feat/20260903-is-weird-number`).
  Added `_is_weird_number` to `cinder/builtins.py`, directly after
  `_is_deficient`: checks abundance (proper divisors sum to more than
  the number) then rules out semiperfect numbers via a bounded 0/1
  subset-sum sweep over those divisors, matching OEIS A006037. Clean
  first pass, no bounces (4224 tests passing, up from 4209).
  README/PROJECT.md updates left to the Architect's next grooming
  pass.
- **Language: `^` (symmetric difference) operator for maps** — merged
  2026-09-03 via PR #378 (`feat/20260903-map-symmetric-difference`).
  Added a dict-dict `CARET` special case to `_apply_binary_operator`
  in `cinder/interpreter.py`, directly above the dispatch to
  `_bitwise_op`: shared keys are excluded entirely, left-only and
  right-only entries keep their own values, following the "keys
  decide" convention already established by map `&`/`-`/`|` and
  mirroring list `^`'s (PR #373) semantics. Compound assignment
  (`^=`) works for free via the existing desugaring. Completes the
  map side of the `&`/`|`/`-`/`^` set-operator family. Clean first
  pass, no bounces (4238 tests passing, up from 4224).
  README/PROJECT.md updates left to the Architect's next grooming
  pass.
- **Standard library: `is_carmichael_number`** — merged 2026-09-03 via
  PR #379 (`feat/20260903-is-carmichael-number`). Added
  `_is_carmichael_number` to `cinder/builtins.py`, directly after
  `_is_smith_number`: trial-divides to build a factor list with
  repetition, then applies Korselt's 1899 criterion (composite,
  squarefree, and `(p-1) | (n-1)` for every prime factor `p`) to
  identify Fermat pseudoprimes without any modular exponentiation
  loop. Clean first pass, no bounces (4252 tests passing, up from
  4238). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Language: `<=>` (spaceship / three-way comparison) operator** —
  merged 2026-09-03T19:27:18Z via PR #380
  (`feat/20260903-spaceship-operator`). Added `SPACESHIP` token
  (`cinder/tokens.py`/`cinder/lexer.py`, next to `GTEQ`), parser
  support in `_COMPARISON` but not `_ORDERING` (so it left-folds as a
  `Binary` rather than chaining), and interpreter evaluation
  (`cinder/interpreter.py:1302-1307`) that reuses `_compare(...,
  TokenType.LT)` and `values_equal` — zero duplicated comparability
  logic, inherits `<`'s type rules and errors for free. Clean first
  pass, no bounces (4265 tests passing, up from 4252).
  README/PROJECT.md updates left to the Architect's next grooming
  pass.
- **Standard library: `is_palindrome_permutation`** — merged
  2026-09-03T19:27:23Z via PR #381
  (`feat/20260903-is-palindrome-permutation`). Added
  `_is_palindrome_permutation` to `cinder/builtins.py`, directly after
  `_is_anagram`: a string permutes into a palindrome iff at most one
  character has an odd count (`Counter`-based), following the file's
  exact-character, case-sensitive convention. Clean first pass, no
  bounces (4263 tests passing at review time, branched before PR
  #380 landed). README/PROJECT.md updates left to the Architect's
  next grooming pass.
- **Standard library: `is_practical_number`** — merged
  2026-09-03T19:45:31Z via PR #382
  (`feat/20260903-is-practical-number`). Added
  `_is_practical_number` to `cinder/builtins.py`, directly after
  `_is_perfect_number`: collects proper divisors via trial division,
  then runs a bounded subset-sum reachability sweep (the same shape
  `_is_weird_number` already uses) to check every integer `1..n-1` is
  reachable as a sum of distinct proper divisors. Clean first pass,
  no bounces (4293 tests passing, up from 4265). README/PROJECT.md
  updates left to the Architect's next grooming pass.
- **Language: map spread (`...m`) in function calls as keyword
  arguments** — merged 2026-09-04T~00:05Z via PR #383
  (`feat/20260903-map-spread-kwargs`). Added a `dict` branch to
  `_evaluate_call_arguments`'s `Spread` case in `cinder/interpreter.py`,
  ahead of the existing `list` branch, merging each entry into
  `keywords` and reusing the `KeywordArg` branch's duplicate-keyword
  check; a non-string map key raises its own `CinderRuntimeError`
  instead of leaking a raw `TypeError`. `Call` and `OptionalCall` both
  route through the shared helper, so `f?.(...m)` picked it up for
  free. Clean first pass, no bounces (4307 tests passing, up from
  4293). README/PROJECT.md updates left to the Architect's next
  grooming pass.
- **Standard library: `nth_deficient`** — merged 2026-09-03T20:14:02Z
  via PR #384 (`feat/20260903-nth-deficient`). Added `_nth_deficient`
  to `cinder/builtins.py`, directly after `_nth_abundant`: an exact
  structural mirror with the comparison flipped from `>` to `<` in the
  nested candidate helper, matching the existing `_is_abundant`/
  `_is_deficient` relationship. Clean first pass, no bounces (4315
  tests passing, up from 4307). README/PROJECT.md updates left to the
  Architect's next grooming pass.
