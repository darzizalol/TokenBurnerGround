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

## 1. Standard library: `variance`/`std_dev` for a list of numbers [claimed 2026-08-01T20:28:01Z]

Build: add `variance(list)` and `std_dev(list)` to `cinder/builtins.py`,
the natural next stop after `mean`/`median` (`cinder/builtins.py:1064-
1099`) — population variance and standard deviation (divide by `n`, not
`n - 1`; Cinder has no separate sample-vs-population statistics concept
anywhere else, so don't introduce one here). Model both directly on
`_mean`'s existing shape: arity 1, argument a non-empty `list` of
numbers, using the exact same validation `_mean`/`_median` already use —
`isinstance(value, list)` (else `CinderRuntimeError` naming the
function and `type_name(value)`), non-empty (else `"...() requires a
non-empty list"`), and each element checked with the already-imported
`_is_numeric` (else `"...() requires a list of numbers, got
{type_name(element)}"`). `variance` computes the mean first (reuse the
same summation approach `_mean` uses, or call `_mean`'s logic inline —
either is fine, just don't duplicate the non-empty/type-checking twice
per call), then returns the mean of each element's squared deviation
from that mean: `sum((x - mean) ** 2 for x in value) / len(value)`.
`std_dev` returns `variance`'s result passed through `math.sqrt` (`math`
is already imported at the top of `builtins.py` for `gcd`/`lcm`/etc) —
implement `std_dev` by calling the same computation `variance` uses
(factor the shared mean/squared-deviation logic into one internal
helper both call, rather than reimplementing it twice or having
`std_dev` call the public `_variance` function recursively through
`call_value` — it's an internal Python-level call, not a Cinder-level
one).

Acceptance criteria:
- `variance([2, 4, 4, 4, 5, 5, 7, 9]);` is `4` — the textbook example
  (population variance of this exact set), pin as the main regression
  test.
- `std_dev([2, 4, 4, 4, 5, 5, 7, 9]);` is `2` — `sqrt(4)`, the exact
  companion of the `variance` case above on the same input.
- `variance([5]);` is `0` and `std_dev([5]);` is `0` — a single-element
  list has zero spread.
- `variance([3, 3, 3]);` is `0` — identical elements have zero variance.
- `variance([]);` and `std_dev([]);` each raise `CinderRuntimeError`
  naming a non-empty-list requirement, matching `mean([])`/`median([])`'s
  existing error shape exactly.
- `variance("abc");` (a string, not a list) raises `CinderRuntimeError`
  naming `variance` and `string` in the message; `std_dev` raises the
  equivalent error for the same input.
- `variance([1, "two", 3]);` (a non-numeric element) raises
  `CinderRuntimeError` naming `variance` and the offending element's
  type; `std_dev` raises the equivalent error for the same input.
- Wrong arity on either builtin (not exactly 1 argument) raises
  `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `mean`/`median`,
`cinder/builtins.py:2361-2362`), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `variance`/`std_dev` added near
`mean`/`median` — leave that to the Architect's next grooming pass, not
this task.

---

## 2. REPL tab completion for builtin names and in-scope variables

Build: wire up `readline`'s completer API so pressing Tab in the REPL
completes builtin function names and the current top-level environment's
variable names — the natural next step in the REPL-ergonomics line
(multiline input and persistent history already landed per `PROJECT.md`'s
Roadmap history). Scope this to `cinder/repl.py`'s existing
`_try_enable_readline` (`cinder/repl.py:33-46`), which already does the
one other piece of `readline` setup (history load); add the completer
registration there, guarded the same way history loading already is —
if `import readline` fails, completion is simply unavailable and the
REPL keeps working exactly as it does today (this is the whole reason
`_try_enable_readline` returns a bool already; no new fallback path
needed). Implement a completer function, e.g. `_make_completer(env)`
returning a `readline`-shaped `completer(text, state)` closure: on each
call with a given `text` prefix, build the candidate list once (keyword
names — reuse `KEYWORDS` from `cinder/tokens.py:97-...` — plus builtin
names from `cinder.builtins._BUILTINS`'s keys, plus the *current*
top-level environment's own defined names. `Environment`
(`cinder/interpreter.py:165-...`) has no public accessor for its
bindings today — it only exposes `define`/`define_const`/`get`/`assign`
over a private `_values` dict — so add one: a small `names(self) ->
list[str]` method returning `list(self._values.keys())` (the REPL's
environment is a single flat top-level scope with no parent, so this
one method covers it; no need to walk `.parent` for this task). Use
that new method from the completer rather than reaching into
`_values` directly from `repl.py`, filter the combined candidate list
to those starting with `text`, sort them, and return the `state`
th match or `None` once exhausted (the standard `readline` completer
contract — `state` counts up from `0` on repeated calls for the same
prefix). Call `readline.set_completer(...)` and
`readline.parse_and_bind("tab: complete")` inside
`_try_enable_readline`, after the history-loading `try`/`except` block.
The completer needs the top-level `Environment` instance, which
`_try_enable_readline` doesn't currently receive — thread it through
as a new parameter (`_try_enable_readline(env)`), updating `run_repl`'s
one call site (`cinder/repl.py`, where `_try_enable_readline()` is
currently called with no arguments) to pass the `Environment` it already
constructs via `create_global_environment()`. Completion candidates
should reflect variables defined *so far* in the session (re-read the
environment's bindings on every completer invocation, not a snapshot
taken once at startup) — this means the completer closure must capture
the live `Environment` object, not a copy of its names.

Acceptance criteria:
- Completer function invoked with `text="pri"`, `state=0` returns
  `"print"` (the sole keyword/builtin match for that prefix) — the
  primary case, pin as the main regression test. Drive this by calling
  the completer function directly in tests (as `readline` itself isn't
  practical to drive interactively in a headless test suite — match
  whatever pattern `tests/test_repl.py`'s existing readline tests already
  use for testing `readline`-adjacent behavior without a real terminal).
- A prefix matching multiple builtins (e.g. `text="ma"` matching `map`,
  `map_values`, `map_keys`, `max`, `max_by`, ...) returns each match in
  turn across increasing `state` values, sorted, then `None` once
  exhausted.
- A prefix matching nothing (e.g. `text="zzz"`) returns `None` at
  `state=0`.
- After `let my_var = 1;` has been evaluated in a session's
  `Environment`, a completer built against that same environment
  completes `text="my_v"` to `"my_var"` — session-defined variables are
  completable, not just builtins/keywords.
- A variable defined in one REPL session/`Environment` does not leak
  into completion for a *different*, unrelated `Environment` instance —
  completer candidates come from the `Environment` it was built with,
  not a shared/global source.
- `_try_enable_readline` still returns `False` without raising when
  `readline` is unavailable (mock `sys.modules["readline"] = None`
  exactly as the existing
  `test_try_enable_readline_returns_false_without_raising_when_missing`
  test already does) — completion setup must live inside the same
  successful-import path, not run unguarded.
- The REPL still works end-to-end with completion wired up (a full
  `run_repl` smoke test with a couple of statements produces the same
  output as before this task) — regression, not a new behavior.
- Full test suite passes.

Likely files: `cinder/repl.py`, `tests/test_repl.py`. Once merged,
`README.md`'s "Three front ends" bullet (or a new bullet near it) needs
a one-line mention of Tab completion — leave that to the Architect's
next grooming pass, not this task.

---

## 3. Standard library: `mode` for the most frequently occurring value in a list

Build: add `mode(list)` to `cinder/builtins.py`, the natural next stop
after `mean`/`median`/`variance`/`std_dev` (`cinder/builtins.py:1064-`
onward, plus wherever this cycle's `variance`/`std_dev` task lands them)
— but unlike those four, `mode` isn't numeric-only: it works on any
valid Cinder value (strings, bools, lists, maps, ...), so model its
counting logic on `_dedupe`'s existing two-path approach
(`cinder/builtins.py:1186-1202`) rather than `_mean`'s numeric-only
validation. Arity 1, argument a non-empty `list` (else `CinderRuntimeError`
naming `mode` and `type_name(value)`; empty list raises `"mode() requires
a non-empty list"`, matching `mean([])`/`median([])`'s existing message
shape). Count occurrences left-to-right: if every element is a valid map
key (`_is_valid_key`, same check `_dedupe`'s fast path already uses),
count via a `dict` keyed on `(isinstance(element, bool), element)` exactly
as `_dedupe` does (so `1` and `true` never collide); otherwise fall back
to `_dedupe`'s O(n²) path, counting via `values_equal` against a list of
`(element, count)` pairs built incrementally. Either way, return the
*first-encountered* element among those with the maximum count — ties
are broken by first appearance in the input list, not by any ordering on
the values themselves (arbitrary Cinder values, e.g. lists/maps, aren't
orderable). Do not introduce a "return all tied modes as a list" variant;
that's a different, unrequested return shape — single-value return only.

Acceptance criteria:
- `mode([1, 2, 2, 3]);` is `2` — the primary case, pin as the main
  regression test.
- `mode([1, 1, 2, 2]);` is `1` — a tie between `1` and `2` (two each)
  resolves to `1`, the one that appeared first.
- `mode([5]);` is `5` — a single-element list is its own mode.
- `mode(["a", "b", "b", "c"]);` is `"b"` — works on strings, not just
  numbers (the key difference from `mean`/`median`/`variance`/`std_dev`).
- `mode([true, false, true]);` is `true`, and `mode([1, true, 1]);` is
  `1` (the bool/int split from `_dedupe`'s comment applies here too — `1`
  and `true` must not be counted together).
- `mode([[1], [1], [2]]);` is `[1]` — a list of lists exercises the
  `values_equal` fallback path, since lists aren't valid map keys.
- `mode([]);` raises `CinderRuntimeError` naming a non-empty-list
  requirement, at the call site's line/column.
- `mode("abc");` (a string, not a list) raises `CinderRuntimeError`
  naming `mode` and `string` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `mean`/`median`, see
current line numbers — shift if this cycle's `variance`/`std_dev` task
landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `mode` added near `mean`/`median` — leave that to
the Architect's next grooming pass, not this task.

---

## 4. Arithmetic compound assignment on index/dot-access targets: `xs[0] += 1`, `m.key += 1`

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

## 5. Standard library: `product` for the product of a list of numbers

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
