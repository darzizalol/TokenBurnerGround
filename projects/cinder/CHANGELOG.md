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
