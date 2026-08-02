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

## 1. Arithmetic compound assignment on index/dot-access targets: `xs[0] += 1`, `m.key += 1`

Build: extend the arithmetic compound-assign operators (`+=`, `-=`,
`*=`, `/=`, `%=`) to accept an `Index`-expression target — which
includes dot access (`m.key`), since `_finish_dot`
(`cinder/parser.py:948-952`) already desugars `m.key` straight into an
`Index(obj, Literal("key"))` node at parse time, identical to
`m["key"]`. This closes a gap the codebase already documents about
itself: `cinder/parser.py:15-23`'s module docstring and the comment at
`cinder/parser.py:170-171` both currently say the arithmetic set is
"identifier targets only", unlike the bitwise/shift set (`&=`, `|=`,
`^=`, `<<=`, `>>=`) which already accepts `Index` targets via
`_INDEX_TARGET_COMPOUND_ASSIGN_OPS` (`cinder/parser.py:172-178`) and
desugars into the dedicated `IndexCompoundAssign` AST node (not
`IndexAssign` wrapping a `Binary` over the same `Index` node — that
would evaluate `obj`/`index` twice at runtime; `IndexCompoundAssign`
evaluates each exactly once, both for the read and the write). The fix
is narrowly scoped: the branch at `cinder/parser.py:763-766` in
`_assignment` already builds `IndexCompoundAssign` for any op in
`_INDEX_TARGET_COMPOUND_ASSIGN_OPS` when `expr` is an `Index` node —
add the five arithmetic `TokenType`s (`PLUSEQ`, `MINUSEQ`, `STAREQ`,
`SLASHEQ`, `PERCENTEQ`, already keys in `_COMPOUND_ASSIGN_OPS` at
`cinder/parser.py:158-163`) into `_INDEX_TARGET_COMPOUND_ASSIGN_OPS`
(or otherwise widen that branch's condition to cover both sets — either
is fine, just don't duplicate the `IndexCompoundAssign`-construction
code path). No interpreter changes are needed:
`_evaluate_index_compound_assign` (`cinder/interpreter.py:620-633`)
already applies whatever binary operator the node carries via
`_apply_binary_operator` generically — it has no operator-specific
logic to extend. Update the stale "identifier targets only" language in
the `cinder/parser.py:15-23` module docstring and the
`cinder/parser.py:170-171` comment to reflect that the arithmetic and
bitwise/shift sets now behave the same way on this axis (a single
comment describing both together is fine — don't leave two comments
making contradictory claims).

Acceptance criteria:
- `let xs = [1, 2, 3]; xs[0] += 5; xs[0];` is `6` — the primary case,
  pin as the main regression test.
- `let m = {"count": 1}; m.count += 1; m.count;` is `2` — dot access as
  a target works too, since it desugars to the same `Index` node as
  bracket indexing; no separate handling needed.
- Each of `-=`, `*=`, `/=`, `%=` also works on an index target (e.g.
  `xs[0] -= 1;`, `xs[0] *= 2;`, `xs[0] /= 2;`, `xs[0] %= 2;`), not just
  `+=` — cover all five in tests, not just the primary case.
- `obj`/`index` are each evaluated exactly once, not twice: a test with
  a side-effecting index expression (e.g. call a function that mutates
  a shared counter and returns the counter's new value as the index)
  demonstrates the counter only advances once per compound-assign,
  matching the existing single-evaluation guarantee bitwise/shift
  compound-assign already has on the same targets — model this on
  however `tests/test_interpreter.py` already proves that guarantee for
  `&=`/`|=`/etc. on `Index` targets, if such a test exists; otherwise
  model it on the parser-level shape assertion in
  `tests/test_parser.py:946-964`
  (`test_bitwise_compound_assign_allows_index_target`), which already
  proves single-evaluation indirectly by asserting the desugared shape
  is `IndexCompoundAssign` and not a doubled `Index`-inside-`Binary`.
- Parser-level shape test: `xs[0] += 1;` desugars to `IndexCompoundAssign`
  with `TokenType.PLUS` as the operator, mirroring
  `test_bitwise_compound_assign_allows_index_target`
  (`tests/test_parser.py:946-964`) but for `+=`/`PLUSEQ` in place of
  `&=`/`AMPEQ`.
- Plain identifier targets are unaffected: `let x = 1; x += 1; x;` is
  still `2`, still desugars to a plain `Assign` wrapping a `Binary`, not
  `IndexCompoundAssign` — regression, not a new behavior for the
  already-working case.
- An invalid target still raises `ParseError` with "invalid assignment
  target" at the operator's line/column (e.g. `1 + 1 += 1;`) — the
  arithmetic set's error path for a non-`Identifier`, non-`Index`
  left-hand side is unchanged.
- Full test suite passes.

Likely files: `cinder/parser.py` (the `_INDEX_TARGET_COMPOUND_ASSIGN_OPS`
set and its module-docstring/comment, plus the `_assignment` branch —
see line numbers above), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s Operators bullet
(currently says "the arithmetic set which is identifier-only") and its
Data structures bullet (currently says "arithmetic compound-assign like
`m.key += 1` isn't supported, matching bracket indexing's own gap")
both need updating to reflect the closed gap — leave that to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `product` for the product of a list of numbers

Build: add `product(list)` to `cinder/builtins.py`, the multiplicative
counterpart of the existing `sum` (`cinder/builtins.py:1046-1060`) —
same shape, same validation, different fold. Model it directly on
`_sum`'s existing structure: arity 1, argument a `list` (else
`CinderRuntimeError` naming `product` and `type_name(value)`, matching
`sum`'s message shape: `"product() requires a list, got {type_name}"`
— note `sum` does not require the list to be non-empty, and `product`
shouldn't either), each element checked with the already-imported
`_is_numeric` (else `"product() requires a list of numbers, got
{type_name(element)}"`, matching `sum`'s per-element error shape
exactly). Fold with multiplication instead of addition, starting from
`1` (the multiplicative identity, exactly as `sum` starts its fold from
`0`, the additive identity) — this is what makes `product([])` well-
defined as `1` without a non-empty check, unlike `mean`/`median`/
`variance`/`std_dev`/`mode` which all require a non-empty list because
division/comparison by zero-length input is undefined for them.

Acceptance criteria:
- `product([1, 2, 3, 4]);` is `24` — the primary case, pin as the main
  regression test.
- `product([5]);` is `5` — a single-element list is its own product.
- `product([]);` is `1` — the empty product, the multiplicative
  identity, not an error (the key difference from `sum([])`, which is
  `0`, also not an error — both are defined on empty lists, unlike
  `mean`/`median`/`variance`/`std_dev`/`mode`).
- `product([2, 0, 3]);` is `0` — a zero element zeroes the whole
  product, ordinary multiplication semantics.
- `product([1, 2.5, 2]);` is `5` (or `5.0` — whichever numeric
  representation `sum`'s equivalent mixed-int/float case already
  produces for consistency; match `sum`'s existing int/float coercion
  behavior exactly, don't introduce a new rule).
- `product("abc");` (a string, not a list) raises `CinderRuntimeError`
  naming `product` and `string` in the message, matching `sum`'s
  equivalent error for the same input.
- `product([1, "two", 3]);` (a non-numeric element) raises
  `CinderRuntimeError` naming `product` and the offending element's
  type, matching `sum`'s equivalent error for the same input.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `sum`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `product` added near `sum` — leave that to the Architect's next
grooming pass, not this task.

---

## 3. Nil-coalescing compound assignment on index/dot-access targets: `xs[0] ??= 1`, `m.key ??= 1`

Build: extend `??=` to accept an `Index`-expression target (which
includes dot access, since `m.key` desugars into `Index(obj,
Literal("key"))` at parse time) — closing the last documented
compound-assign gap versus the bitwise/shift set. README's Operators
bullet already flags this in passing: `a ??= b` is "identifier targets
only". Today `_assignment` (`cinder/parser.py:738-749`) handles `QQEQ`
in its own branch, separate from the `_COMPOUND_ASSIGN_OPS` dict-driven
branch that handles the arithmetic/bitwise/shift sets — it desugars
`x ??= v` into `Assign(x.name, Logical(Identifier(x), QUESTION_QUESTION,
v))`, reusing the existing `Logical` node so `v` short-circuits exactly
like plain `??` (proven by `tests/test_parser.py:899-910`,
`test_qq_eq_desugars_to_assign_of_logical_question_question`). When
`expr` is anything but an `Identifier`, that branch falls through to
`raise ParseError("invalid assignment target", ...)`
(`cinder/parser.py:747-749`) — proven today by
`tests/test_parser.py:912-914`,
`test_qq_eq_index_target_raises_parse_error`, which this task flips
from expecting a `ParseError` to expecting a parsed
`IndexNilCoalesceAssign` shape (update, don't delete, that test).

Do not reuse `IndexCompoundAssign` for this: its interpreter evaluation
(`_evaluate_index_compound_assign`, `cinder/interpreter.py:621-635`)
unconditionally evaluates `expr.value` (line 632,
`rhs = self.evaluate(expr.value, env)`) before combining with
`_apply_binary_operator` — correct for `&=`/`|=`/etc. (which always
evaluate their RHS), but wrong for `??=`, whose entire point is to
*not* evaluate the RHS when the current value isn't `nil` (the
short-circuit already guaranteed for the identifier case via
`Logical`). Add a new dedicated AST node instead:
`IndexNilCoalesceAssign(obj, index, value, line, column)` in
`cinder/ast_nodes.py` (near `IndexCompoundAssign`,
`cinder/ast_nodes.py:110-122` — no `operator` field needed, the
operation is always `??`), and a new
`Interpreter._evaluate_index_nil_coalesce_assign` in
`cinder/interpreter.py` (near `_evaluate_index_compound_assign`,
dispatched from `evaluate()`'s `isinstance` chain alongside the
existing `IndexCompoundAssign` check at
`cinder/interpreter.py:245-246`) that: evaluates `obj` once, `index`
once, reads `current = self._index_get(obj, index, expr.line,
expr.column)`; `nil` is represented as Python `None` in this
interpreter (see `_evaluate_logical`'s `??` case,
`cinder/interpreter.py:738-741`, `if left is not None: return left`) —
mirror that check here: if `current is not None`, return `current`
immediately *without* evaluating `expr.value` and *without* calling
`_index_set` (skip the redundant write — matches the short-circuit
contract, and there's no observable difference since the value that
would be written back equals the value already there); if `current is
None`, evaluate `rhs = self.evaluate(expr.value, env)`, call
`self._index_set(obj, index, rhs, expr.line, expr.column)`, and return
`rhs`.

Wire the parser side: in `_assignment`'s `QQEQ` branch
(`cinder/parser.py:738-749`), after the existing
`isinstance(expr, Identifier)` case, add
`elif isinstance(expr, Index): return IndexNilCoalesceAssign(expr.obj,
expr.index, value, op_token.line, op_token.column)` before the final
`raise ParseError(...)` (which still applies to any other invalid
target, e.g. `1 + 1 ??= 1;`). Update any comment/docstring language
describing `??=` as identifier-only (near the `QQEQ` handling in
`cinder/parser.py`, and `IndexCompoundAssign`'s docstring in
`cinder/ast_nodes.py` if it enumerates the compound-assign family) to
reflect the closed gap.

Acceptance criteria:
- `let m = {"a": nil}; m["a"] ??= 5; m["a"];` is `5` — the primary
  case, pin as the main regression test.
- `let m = {"a": 1}; m["a"] ??= 5; m["a"];` is still `1` — `??=` leaves
  a non-nil current value untouched.
- `let m = {}; m.key ??= 5; m.key;` is `5` — dot access as a target
  works too, since it desugars to the same `Index` node.
- A test with a side-effecting index expression (a function that
  mutates a shared counter and returns the counter's new value as the
  index) proves `obj`/`index` are each evaluated exactly once, whether
  or not the current value is nil — model on however the existing
  single-evaluation tests for `IndexCompoundAssign` prove it in
  `tests/test_interpreter.py`.
- A test proves the RHS is *not* evaluated at all when the current
  value is non-nil — e.g. `let m = {"a": 1}; let calls = [];
  fn side() { push(calls, 1); return 99; } m["a"] ??= side();
  len(calls);` is `0` — the short-circuit guarantee, the whole point of
  this task.
- Parser-level shape test: `xs[0] ??= 1;` desugars to
  `IndexNilCoalesceAssign` with `obj`/`index`/`value` matching,
  mirroring `test_bitwise_compound_assign_allows_index_target`
  (`tests/test_parser.py:946-964`) but for the new node (no operator
  field to assert on).
- Update `tests/test_parser.py:912-914`'s
  `test_qq_eq_index_target_raises_parse_error` — it currently asserts
  `xs[0] ??= 1;` raises `ParseError`; that's no longer true, so rewrite
  it into a positive shape assertion (or fold it into the new shape
  test above) rather than leaving a stale test asserting the old, wrong
  behavior.
- Plain identifier targets are unaffected: `let x = nil; x ??= 1; x;`
  is still `1`, still desugars to `Assign`/`Logical` — regression, not
  a new behavior for the already-working case.
- An invalid target still raises `ParseError` with "invalid assignment
  target" at the operator's line/column (e.g. `1 + 1 ??= 1;`).
- Full test suite passes.

Likely files: `cinder/parser.py` (`_assignment`'s `QQEQ` branch,
`cinder/parser.py:738-749`), `cinder/ast_nodes.py` (new
`IndexNilCoalesceAssign`, near `cinder/ast_nodes.py:110-122`),
`cinder/interpreter.py` (new evaluator method, near
`cinder/interpreter.py:621-635`, plus the dispatch `isinstance` chain
around `cinder/interpreter.py:245-246`), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s Operators
bullet (currently says `a ??= b` is "identifier targets only") needs
updating — leave that to the Architect's next grooming pass, not this
task.

---

## 4. REPL `:load <path>` command to run a script into the current session

Build: add a `:load <path>` REPL meta-command, the natural next REPL
ergonomics step after tab completion (`cinder/repl.py`) — lets a session
pull in helper functions/data from a `.cin` file without retyping them,
then keep interacting with them at the prompt. Model the trigger on the
existing `EXIT_COMMAND` check at `cinder/repl.py:114-115` (`if not
buffered_lines and line.strip() == EXIT_COMMAND: return`): add a sibling
check, only when `buffered_lines` is empty (so `:load` can't appear
mid-continuation), for a line whose `.strip()` starts with `":load "`
(a bare `:load` with no path is a usage error, not a crash — see below).
On match, don't fall through to the normal tokenize/parse/execute path
for that line; instead read the path (`line.strip()[len(":load "):]
.strip()`), resolve it relative to the process's current working
directory (`Path(path)`, not relative to `cinder/repl.py`'s own
location — the user is loading *their* script, not a package-internal
one), and:
- If the file doesn't exist or can't be read, `write(...)` a one-line
  error (e.g. `f"could not read {path}: {exc}"`) and continue the loop —
  do not crash the REPL, matching how `CinderError` is already caught
  per-statement without killing the session (`cinder/repl.py:132-133`).
- Otherwise, tokenize + `parse_program` the file's contents and execute
  each statement against the *same* persistent `env`/`interpreter` the
  REPL prompt itself uses (so `let`/`fn`/`const` bindings from the file
  are visible at the prompt afterward) — reuse the exact same per-
  statement loop body already in `run_repl` (`cinder/repl.py:125-131`:
  `ExprStmt` echoes its value via `stringify`, everything else just
  `execute`s) rather than writing a second, diverging copy of it; the
  cleanest way is to factor that loop body into a small helper (e.g.
  `_run_statements(statements, interpreter, env, write)`) called from
  both the main loop and the `:load` handler, rather than duplicating
  the `isinstance(statement, ExprStmt)` branch inline in two places.
- A `LexError`/`ParseError`/`CinderRuntimeError` raised while
  tokenizing/parsing/executing the loaded file is caught the same way
  the main loop catches `CinderError` (`cinder/repl.py:132-133`), but
  the diagnostic's source label must be the loaded file's path, not the
  literal string `<repl>` (`REPL_SOURCE_NAME`, `cinder/repl.py:23`) —
  e.g. `f"{path}:{e.line}:{e.column}: {e.message}"` — so a user can tell
  a `:load`-time error apart from a prompt-time one. One bad statement
  in the loaded file should not prevent later statements in the *same*
  file from running, matching the main loop's existing per-statement
  isolation — catch per-statement inside the `:load` handler's loop,
  same as `cinder/repl.py:123-133` already does for prompt input, not
  one `try` wrapping the whole file.
- After a successful (or partially-successful) `:load`, tab completion
  must see the newly bound names immediately: no extra wiring should be
  needed here since `_make_completer` (`cinder/repl.py:34-46`) already
  re-reads `env.all_names()` fresh on every Tab press, but add a test
  proving it (see acceptance criteria).
- `:load` with no path (just `":load"` or `":load "` with nothing after
  it, once stripped) writes a usage error (e.g. `"usage: :load <path>"`)
  and does not attempt to open a file.

Acceptance criteria:
- Given a temp file `helpers.cin` containing `fn double(x) { return x *
  2; } let greeting = "hi";`, running `:load <path-to-helpers.cin>`
  then `double(21);` at the next prompt returns `42`, and `greeting;`
  returns `"hi"` — the primary case, pin as the main regression test.
  Model the temp-file setup on `tempfile`, already imported in
  `tests/test_repl.py` (see its `import tempfile` at the top).
- `:load <path-to-nonexistent-file>` writes one output containing the
  path (or the error message) and does *not* raise — the loop continues
  and a following `1 + 1;` still evaluates to `2` in the same session.
- A `.cin` file with a runtime error partway through (e.g. statement 1
  defines `let a = 1;`, statement 2 is `undefined_name;`, statement 3 is
  `let b = 2;`) still leaves `b` bound afterward — proves per-statement
  isolation inside `:load`, not one `try` around the whole file. The
  error output for statement 2 names the loaded file's path (not
  `<repl>`) in its diagnostic prefix.
- A bare `:load` (no path) writes a usage message and does not attempt a
  file read (no `FileNotFoundError`/traceback surfaces even if cwd has
  no file named `""`).
- `:load` only triggers at the start of a fresh statement (empty
  `buffered_lines`), matching how `EXIT_COMMAND` already behaves — e.g.
  typing `:load` isn't reachable mid-continuation since Cinder has no
  syntax that would put `:load` inside an unbalanced bracket anyway;
  a single test confirming the top-level trigger path is enough, don't
  over-test this edge.
- Existing REPL behavior (bare-expression echoing, multi-statement
  buffering, `CinderError` diagnostics on prompt input, `exit`) is
  unaffected — full existing `tests/test_repl.py` suite still passes
  unmodified alongside the new tests.
- Full test suite passes.

Likely files: `cinder/repl.py` (new `:load` branch near
`cinder/repl.py:114-115`, the extracted `_run_statements` helper
factored out of `cinder/repl.py:123-133`), `tests/test_repl.py`. Once
merged, `README.md`'s REPL section needs a `:load` mention — leave that
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `frequencies` for a list's per-element occurrence counts

Build: add `frequencies(list)` to `cinder/builtins.py`, returning a map
from each distinct element to the number of times it occurs in the
input list. Model it directly on `_count_by`'s existing structure
(`cinder/builtins.py:2268-2289`) — arity 1, argument a `list` (else
`CinderRuntimeError` naming `frequencies` and `type_name(value)`,
matching `count_by`'s message shape:
`"frequencies() requires a list, got {type_name}"`), building a plain
`dict` by iterating the list and doing `counts[key] = counts.get(key,
0) + 1` for `key = element` (`count_by` does the identical thing except
its key comes from calling a predicate function first — `frequencies`
has no predicate, the element *is* the key) — reuse `_is_valid_key`
(already imported, see its use at `cinder/builtins.py:2284`) to raise
`CinderRuntimeError(f"{type_name(key)} is not a valid map key", line,
column)` for a non-hashable element (a list or map), the exact error
`count_by`/`group_by`/`key_by` already raise for a non-valid-key result
— **do not** reach for `mode`'s `(is_bool, element)`-keyed fast path or
its `values_equal`-based fallback for unhashable elements
(`cinder/builtins.py:1150-1188`): those exist because `mode` only ever
*compares* counts internally and never returns the dict itself, so it
can use a disambiguating internal key shape freely, whereas
`frequencies` must return a real Cinder map, which is bound by the same
`1`/`true`-collide-as-keys behavior every other map-key-producing
builtin already has (`count_by`, `group_by`, `key_by` all use a plain
dict with no bool/int disambiguation — that's the established,
already-shipped convention for this family of builtins, not a bug to
route around here). Preserve first-appearance insertion order (falls
out for free from a plain Python `dict` and a single left-to-right
pass, same as `count_by`).

Acceptance criteria:
- `frequencies([1, 2, 2, 3, 3, 3]);` is `{1: 1, 2: 2, 3: 3}` — the
  primary case, pin as the main regression test.
- `frequencies(["a", "b", "a"]);` is `{"a": 2, "b": 1}` — strings work
  as keys too, not just numbers.
- `frequencies([]);` is `{}` — an empty list is well-defined, not an
  error (matches `count_by([], fn(x) { return x; })`'s behavior on an
  empty list).
- Key order in the result matches first appearance in the input list —
  assert on `keys(frequencies([3, 1, 3, 2]))` being `[3, 1, 2]`, not
  sorted or insertion-via-count order.
- `frequencies([true, false, true]);` is `{true: 2, false: 1}` — bools
  work as keys (and, matching `count_by`'s existing behavior, don't
  need special-casing against ints here).
- `frequencies([[1, 2], [1, 2]]);` (a list of lists, each not a valid
  map key) raises `CinderRuntimeError` naming `frequencies` — or at
  minimum matches whatever exact wording `group_by`'s
  `"{type_name(key)} is not a valid map key"` error produces for the
  same underlying reason, since this reuses that same check.
- `frequencies("abc");` (a string, not a list) raises
  `CinderRuntimeError` naming `frequencies` and `string` in the
  message, matching `count_by`'s equivalent error for the same input.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `count_by`/`mode`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `frequencies` added near `count_by` — leave that to the
Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
