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

## 1. Standard library: `take_right`/`drop_right` for taking/dropping from a list's end

Build: add `take_right(list, n)` and `drop_right(list, n)` to
`cinder/builtins.py`, the end-anchored complements of the existing
`take`/`drop` (`cinder/builtins.py:1516-1551`), which only work from the
front. Model both directly on `_take`/`_drop`'s existing shape: arity 2,
first argument a `list` (raise `CinderRuntimeError` naming the function
and the actual type otherwise, matching `take`'s message shape exactly:
`"take_right() requires a list as its first argument, got {type_name}"`),
second argument a non-bool `int` (same `isinstance(n, int) and not
isinstance(n, bool)` check `take`/`drop` already use, same error message
shape with the function's own name), and a `CinderRuntimeError` on a
negative `n` (`"take_right() requires a non-negative n"`). Reuse
`_normalize_slice_bound` (already imported at `cinder/builtins.py:26`,
used by both `take`/`drop` and plain slicing) to clamp `n` against the
list's length exactly as `take`/`drop` do — an `n` larger than the list's
length must not raise, it must clamp to the whole list, same as `take`/
`drop` today. `take_right` returns the last `n` elements in their
original order (not reversed); `drop_right` returns everything except
the last `n` elements. Both must work on an empty list (`n` clamps to
`0`, both return `[]`) and leave the input list unmodified (return a new
list, exactly as `take`/`drop` do via Python slicing, never mutate the
argument in place).

Acceptance criteria:
- `take_right([1, 2, 3, 4, 5], 2);` is `[4, 5]` — the primary case, pin
  as the main regression test.
- `drop_right([1, 2, 3, 4, 5], 2);` is `[1, 2, 3]` — the exact complement
  of the case above on the same input and `n`.
- `take_right([1, 2, 3], 0);` is `[]` and `drop_right([1, 2, 3], 0);` is
  `[1, 2, 3]` — `n = 0` is take-nothing/drop-nothing, not an error.
- `take_right([1, 2, 3], 10);` is `[1, 2, 3]` and `drop_right([1, 2, 3],
  10);` is `[]` — an `n` larger than the list's length clamps instead of
  raising, matching `take`/`drop`'s existing clamp behavior.
- `take_right([], 3);` is `[]` and `drop_right([], 3);` is `[]` — both
  handle an empty input list without error.
- `take_right([1, 2, 3], -1);` and `drop_right([1, 2, 3], -1);` each
  raise `CinderRuntimeError` naming a non-negative requirement, at the
  call site's line/column — same shape as `take(xs, -1)`/`drop(xs, -1)`
  today.
- `take_right("abc", 2);` (a string, not a list) raises
  `CinderRuntimeError` naming `take_right` and `string` in the message;
  `drop_right` raises the equivalent error for the same input — neither
  builtin operates on strings, matching `take`/`drop`'s list-only scope.
- Wrong arity on either builtin (not exactly 2 arguments) raises
  `CinderRuntimeError` with line/column.
- The input list is unchanged after either call (e.g. `let xs = [1, 2,
  3]; take_right(xs, 1); xs;` is still `[1, 2, 3]`) — no in-place
  mutation.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `take`/`drop`,
`cinder/builtins.py:2329-2330`), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `take_right`/`drop_right` added near
`take`/`drop` — leave that to the Architect's next grooming pass, not
this task.

---

## 2. Standard library: `variance`/`std_dev` for a list of numbers

Build: add `variance(list)` and `std_dev(list)` to `cinder/builtins.py`,
the natural next stop after `mean`/`median` (`cinder/builtins.py:1026-
1064`) — population variance and standard deviation (divide by `n`, not
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
`cinder/builtins.py:2283-2284`), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `variance`/`std_dev` added near
`mean`/`median` — leave that to the Architect's next grooming pass, not
this task.

---

## 3. REPL tab completion for builtin names and in-scope variables

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

## 4. Standard library: `mode` for the most frequently occurring value in a list

Build: add `mode(list)` to `cinder/builtins.py`, the natural next stop
after `mean`/`median`/`variance`/`std_dev` (`cinder/builtins.py:1026-`
onward, plus wherever this cycle's `variance`/`std_dev` task lands them)
— but unlike those four, `mode` isn't numeric-only: it works on any
valid Cinder value (strings, bools, lists, maps, ...), so model its
counting logic on `_dedupe`'s existing two-path approach
(`cinder/builtins.py:1148-1166`) rather than `_mean`'s numeric-only
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
