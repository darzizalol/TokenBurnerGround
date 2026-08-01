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

## 1. Standard library: `get_in` for safe nested access [claimed 2026-08-01T14:37:36Z]

Build: add `get_in(container, path, default)` to `cinder/builtins.py` —
walks a list of keys/indices through nested maps and lists in one call,
returning `default` the moment the path can't be followed (wrong
container type, missing key, or out-of-range index) instead of raising,
the way chaining `get(get(get(m, "a", {}), "b", {}), "c", nil)` would
require today for a three-level path. Signature and arity mirror `get`
(`_get`, `cinder/builtins.py:301-313`): `_require_arity("get_in",
arguments, 3, line, column)`, then unpack `container, path, default =
arguments`. `path` itself must be a `list` (raise `CinderRuntimeError`
`f"get_in() requires a list path, got {type_name(path)}"` at
`line`/`column` if not — this is a structural argument-type error like
`get`'s own checks, not a soft "not found" case). Then iterate `path`'s
elements in order, threading a `current` value that starts as
`container`: for each `key` in `path`, if `current` is a `dict`, use the
same key-validity check `_get` already uses (`_is_valid_key`,
`cinder/builtins.py` — reuse it, don't reimplement) and return `default`
immediately if `key` isn't a valid map-key type or isn't present in
`current` (no error — this is the soft/expected case `get_in` exists
for); if `current` is a `list`, return `default` immediately if `key`
isn't a plain `int` (reuse the same `isinstance(key, int) and not
isinstance(key, bool)` check `_insert`/`_remove_at` already use at
`cinder/builtins.py:213`/`235`) or, after normalizing with
`normalize_index(key, len(current))` (already imported into
`builtins.py` from `cinder.interpreter`, used the same way at
`cinder/builtins.py:218`/`240`), the normalized index falls outside
`[0, len(current))`; otherwise (`current` is neither a `dict` nor a
`list` but the path isn't exhausted yet — e.g. it bottomed out on a
number or string mid-path) return `default` immediately too, same
soft-failure treatment, no error. On each successful step, advance
`current` to the looked-up value and continue to the next path element.
After the loop completes without early return, return `current` (which
is `container` itself unchanged if `path` was empty — `get_in(x, [],
default)` is `x`, no navigation needed, matching the empty-path base
case of the walk). Only `path`'s own type is validated up front;
per-step problems (wrong container type, bad key type, missing key,
out-of-range index) are all part of `get_in`'s normal soft-fail
contract and must never raise `CinderRuntimeError` — that is the entire
point of the builtin relative to chaining raw index expressions
(`obj[a][b][c]`, which raises on the first bad step) or nested `get`
calls (which need a dummy default at every intermediate level to avoid
raising).

Acceptance criteria:
- `get_in({"a": {"b": {"c": 1}}}, ["a", "b", "c"], nil)` is `1` — the
  primary three-level nested-map walk, pin as the main regression test.
- `get_in({"a": {"b": 1}}, ["a", "x"], "missing")` is `"missing"` — a
  missing key partway through the path returns `default`, not an error.
- `get_in({"a": [1, 2, 3]}, ["a", 1], nil)` is `2` — the path can mix
  map keys and list indices in the same call.
- `get_in({"a": [1, 2, 3]}, ["a", 99], "oob")` is `"oob"` — an
  out-of-range list index mid-path returns `default`, not
  `CinderRuntimeError`.
- `get_in({"a": [1, 2, 3]}, ["a", -1], nil)` is `3` — negative list
  indices in the path normalize the same way plain indexing does.
- `get_in({"a": 5}, ["a", "b"], "nope")` is `"nope"` — the path tries to
  descend into `5` (neither map nor list) because it isn't exhausted
  yet; returns `default` instead of raising, distinct from the
  container-type errors `get`/`pluck` raise for their own top-level
  argument.
- `get_in({"a": 1}, [], "unused")` is `{"a": 1}` — an empty path returns
  the container itself unchanged.
- `get_in([1, [2, 3]], [1, 0], nil)` is `2` — works starting from a
  top-level list, not just a top-level map.
- `get_in({"a": 1}, "a", nil)` (a string, not a list, as `path`) raises
  `CinderRuntimeError` with message `"get_in() requires a list path, got
  string"` and line/column — the one case that *does* raise, since it's
  a caller error on `get_in`'s own argument shape, not a path-walk
  failure.
- Wrong arity raises `CinderRuntimeError` with line/column.
- `get_in` does not mutate `container` (assert the original nested
  structure is unchanged after the call).
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `get_in` added to the
alphabetically-grouped map/list-access names near `get`/`remove` — leave
that to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `curry` for single-argument currying

Build: add `curry(fn, arity)` to `cinder/builtins.py` — returns a new
callable Cinder value (same returned-function mechanism `pipe`/`compose`
already use, `cinder/builtins.py:1939-1974`: a `Builtin` closure built
with `call_value`, `cinder/interpreter.py:824`, to invoke the wrapped
function) that accepts its arguments **one at a time**, accumulating
them, and only actually calls `fn` once `arity` arguments have been
collected — e.g. `curry(fn(a, b, c) { return a + b + c; }, 3)(1)(2)(3)`
is `6`. Validate `fn` is callable up front (reuse `_is_callable`,
`cinder/builtins.py:1844`, raising `CinderRuntimeError` `f"curry()
requires a function as its first argument, got {type_name(fn)}"` at the
`curry(...)` call's own line/column if not — do not defer to first
invocation) and `arity` is a positive `int` (`isinstance(arity, int) and
not isinstance(arity, bool)` and `arity >= 1`; `arity < 1` including `0`
and negative values raises `CinderRuntimeError` `f"curry() requires
arity to be at least 1, got {arity}"`, non-int raises `f"curry()
requires an int arity, got {type_name(arity)}"` — both at the call
site). Each step's returned `Builtin` closure takes **exactly one**
argument (validate with `_require_arity`, `cinder/builtins.py:49`, using
a synthetic name like `"<curried function>"`, mirroring
`_piped`/`_composed`'s own approach for their returned closures' arity
checks), appends it to an accumulator list captured by that step's
closure (each step must capture its *own* accumulator snapshot — e.g.
via a default-argument or an immediately-applied helper — not a single
mutable list shared and mutated across steps, or partial application
from a shared base would corrupt sibling calls: calling `let step1 =
curry(fn, 2)(1); step1(2); step1(3);` twice must yield two independent
results, not accumulate `[1, 2, 3]`). Once the accumulator reaches
`arity` elements, call `fn` via `call_value(fn, accumulated, line,
column)` (the *inner* call's line/column — the site invoking the final
step, not `curry`'s own call site, mirroring `_piped`/`_composed`'s
rule) and return that result directly, not another wrapped function;
below `arity`, return a new one-argument `Builtin` closure over the
extended accumulator.

Acceptance criteria:
- `curry(fn(a, b) { return a + b; }, 2)(1)(2)` is `3` — two-step curry,
  pin as the primary test.
- `curry(fn(a, b, c) { return a + b + c; }, 3)(1)(2)(3)` is `6` —
  three-step curry, catches an off-by-one in the accumulate-until-arity
  logic.
- `let add5 = curry(fn(a, b) { return a + b; }, 2)(5); add5(1)` is `6`
  and `add5(10)` is `15` — a partially-applied step is reusable across
  multiple final calls, each producing an independent result (regression
  guard for accumulator-sharing bugs).
- `curry(fn(a, b) { return a + b; }, 2)(1)` is itself a callable Cinder
  value: `type()` of it reports the same type name an ordinary function
  value reports, and it's passable to `map`
  (`map([1, 2, 3], curry(fn(a, b) { return a + b; }, 2)(10)))` is
  `[11, 12, 13]`).
- `curry(1, 2)` (non-function `fn`) raises `CinderRuntimeError` with
  line/column at the `curry(...)` call site, before any step is invoked.
- `curry(fn(a) { return a; }, 0)` and `curry(fn(a) { return a; }, -1)`
  both raise `CinderRuntimeError` (`arity` must be at least 1) at the
  `curry(...)` call site.
- `curry(fn(a) { return a; }, "2")` (non-int `arity`) raises
  `CinderRuntimeError` at the call site.
- Calling any intermediate or final step with zero arguments or two-plus
  arguments raises `CinderRuntimeError` (arity mismatch on that step
  itself, not a Python-level crash) — regression-test both an
  intermediate step and the final step.
- Wrong arity on `curry` itself (not 2 arguments) raises
  `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `map`/`filter`/`reduce`,
`cinder/builtins.py:2237-2238` onward, alongside where `pipe`/`compose`
are registered), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `curry` added near `pipe`/`compose` — leave that to
the Architect's next grooming pass, not this task.

---

## 3. Standard library: `memoize` for caching pure functions

Build: add `memoize(fn)` to `cinder/builtins.py` — returns a new callable
Cinder value (the same returned-function mechanism `pipe`/`compose`/
`curry` already use, `cinder/builtins.py:1939-1974`: a `Builtin` closure
built with `call_value` to invoke the wrapped function) that caches
`fn`'s results by argument list, so calling it again with arguments
already seen returns the cached result without re-invoking `fn`.
Validate `fn` is callable up front (reuse `_is_callable`,
`cinder/builtins.py:1844`, raising `CinderRuntimeError` `f"memoize()
requires a function argument, got {type_name(fn)}"` at the `memoize(...)`
call's own line/column if not — do not defer to first invocation,
mirroring `curry`'s up-front validation). Unlike `pipe`/`compose`'s
single-argument returned closures, `memoize`'s returned closure accepts
**any number of arguments** (it must support wrapping functions of any
arity), so it does not call `_require_arity` on itself — it forwards
`call_args` straight to `fn` via `call_value(fn, call_args, call_line,
call_column)` using the *inner* call's line/column (the site invoking
the memoized function, not `memoize`'s own call site — mirror
`pipe`/`compose`/`curry`'s existing rule for this). Each call to
`memoize(fn)` creates one fresh `dict` cache captured by that call's own
closure — a brand-new cache per `memoize(...)` invocation, never shared
across two separate `memoize(...)` calls on the same underlying `fn`
(same "own accumulator" discipline `curry` already established for its
per-step accumulators, applied here to per-`memoize()`-call caches).
Before consulting or populating the cache, validate every element of
`call_args` is a valid cache key via `_is_valid_key`
(`cinder/interpreter.py:888-890`, already imported into `builtins.py`) —
on the first invalid argument found (in order), raise
`CinderRuntimeError` `f"memoize() cannot cache a call with a
{type_name(arg)} argument"` at the call site; this is a hard requirement,
not a soft fallback to calling `fn` uncached, since a silently-uncached
call would be a far more confusing failure mode than a clear error.
Build the cache key as `tuple((type(arg).__name__, arg) for arg in
call_args)`, **not** `tuple(call_args)` directly — a plain Python tuple
would conflate `1` and `true` as the same dict key (`hash(1) ==
hash(True)` and `1 == True` in Python), which contradicts Cinder's own
`values_equal` (`cinder/interpreter.py:932-937`, where a number and a
bool are never equal regardless of value); the `type(...).__name__`
prefix keeps `(1,)` and `(true,)` in separate cache slots. On a cache
hit, return the cached value directly without calling `fn` again; on a
miss, call `fn`, store the result under that key, and return it.

Acceptance criteria:
- `let calls = 0; fn f(x) { calls = calls + 1; return x * 2; } let
  memoized = memoize(f); memoized(5); memoized(5); memoized(3); calls;`
  is `2` — repeated calls with the same argument hit the cache and only
  invoke `fn` once per distinct argument, pin as the primary regression
  test.
- `let calls = 0; fn f(a, b) { calls = calls + 1; return a + b; } let
  memoized = memoize(f); memoized(1, 2); memoized(1, 2); memoized(2, 1);
  calls;` is `2` — multi-argument functions are cached by the full
  argument list, not just the first argument.
- `let calls = 0; fn f(x) { calls = calls + 1; return x; } let m1 =
  memoize(f); let m2 = memoize(f); m1(1); m2(1); calls;` is `2` — two
  separate `memoize(...)` calls on the same underlying function do not
  share a cache (regression guard mirroring `curry`'s independent-
  accumulator rule).
- `let calls = 0; fn f(x) { calls = calls + 1; return x; } let memoized
  = memoize(f); memoized(1); memoized(true); calls;` is `2` — a number
  argument and a boolean argument are cached separately even though
  Python would treat them as the same dict key, matching
  `values_equal`'s number/bool distinction; pin as an explicit
  regression test for the `type(...).__name__` cache-key prefix.
- `memoize(fn(x) { return x; })` is itself a callable Cinder value:
  `type()` of it reports the same type name an ordinary function value
  reports, and it's passable to `map` (`map([1, 2, 3], memoize(fn(x) {
  return x * 2; }))` is `[2, 4, 6]`).
- `memoize(1)` (non-function argument) raises `CinderRuntimeError` with
  line/column at the `memoize(...)` call site, before the returned
  closure is ever invoked.
- `let memoized = memoize(fn(x) { return x; }); memoized([1, 2]);` (a
  list argument) raises `CinderRuntimeError` with message `"memoize()
  cannot cache a call with a list argument"` and the call site's
  line/column, not `memoize(...)`'s own.
- `let memoized = memoize(fn(m) { return m; }); memoized({"a": 1});` (a
  map argument) raises `CinderRuntimeError` the same way, naming `map`
  in the message.
- Calling the memoized function with an arity mismatch for the wrapped
  function (e.g. wrapping a 2-parameter function and calling the
  memoized version with 1 argument) still raises `CinderRuntimeError`
  for wrong arity — the check happens naturally inside `call_value`'s
  dispatch to `fn`, not memoize's own closure, and must not be silently
  swallowed or cached.
- Wrong arity on `memoize` itself (not exactly 1 argument) raises
  `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `pipe`/`compose`/
`curry`, `cinder/builtins.py:2237-2238` onward), `tests/test_builtins.py`.
Once merged, `README.md`'s Builtins bullet needs `memoize` added near
`pipe`/`compose`/`curry` — leave that to the Architect's next grooming
pass, not this task.

---

## 4. Multiple values per `switch` case: `case 1, 2, 3: { ... }`

Build: let a single `switch` case match any of several values, instead of
requiring one `case` per value with duplicated bodies. Today `SwitchCase`
(`cinder/ast_nodes.py:327-330`) holds one `value: Expr`; change it to
`values: list` (a non-empty list of `Expr`, still frozen dataclass) and
update its docstring-adjacent `SwitchStmt` docstring
(`cinder/ast_nodes.py:333-341`) to describe multi-value cases. Parser:
in `_switch_statement` (`cinder/parser.py:603-639`), after `self._advance()`
consumes `case`, parse one `self._ternary()` (exactly as today) then loop
while `self._check(TokenType.COMMA)`: `self._advance()` and parse another
`self._ternary()`, appending each to a `values` list — mirror how call
arguments or list-literal elements are comma-parsed elsewhere in this
parser (same `while self._check(TokenType.COMMA): self._advance(); ...`
shape). Stop consuming values at `':'` exactly as before; the rest of the
case (colon, `{`-check, block body) is unchanged. Interpreter: in
`_execute_switch` (`cinder/interpreter.py:369-375`), replace the
single `values_equal(scrutinee, self.evaluate(case.value, env))` check
with a loop over `case.values`, evaluating each in source order (left to
right — evaluation order can matter if a case value expression has a
side effect, e.g. `case f(), g():`) and matching on the first one where
`values_equal(scrutinee, ...)` is `True`; short-circuit — do not
evaluate later value expressions in the same case once an earlier one
already matched. A single-value case (today's only form) is just a
`values` list of length 1, so no separate code path is needed for it —
this must not change behavior for any existing single-value `switch`
(regression-covered by the existing switch tests, which must keep
passing unmodified). No new token type needed (`TokenType.COMMA` already
exists and is used elsewhere in the parser).

Acceptance criteria:
- `switch (2) { case 1, 2, 3: { print("small"); } default: { print("big"); } }`
  prints `"small"` — the primary multi-value match, pin as the main
  regression test.
- `switch (5) { case 1, 2, 3: { print("small"); } default: { print("big"); } }`
  prints `"big"` — a scrutinee matching none of a multi-value case's
  values falls through to `default`, same as today's single-value miss.
- Existing single-value cases (`case 1: { ... }`) still parse and match
  exactly as before — run the existing switch test file unmodified and
  confirm it still passes (regression, not a new test).
- `switch (1) { case f(), g(): { ... } }` where `f()` has a side effect
  (e.g. increments a counter) and the scrutinee equals `f()`'s return
  value: `g()` is never called — evaluation short-circuits on first
  match (regression test with a counter, asserting `g`'s side-effect
  counter stays at 0).
- A case's value list can mix literal and computed expressions in the
  same case (e.g. `case 1, x + 1, "three":`) — values aren't required to
  be constant.
- `case 1, 2 : { ... }` with case values sharing one body still runs
  that one body when either value matches — no duplicated-block
  workaround needed at the call site anymore, which is the whole point
  of this task (add an example in `examples/` only if a suitable one
  already demonstrates `switch`; do not create a new example file just
  for this).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s `switch` bullet
under Control flow needs a mention of multi-value cases — leave that to
the Architect's next grooming pass, not this task.

---

## 5. List destructuring in `for`-loop variables: `for [k, v] in items(m) { ... }`

Build: let a `for`-in loop's variable position accept a list destructuring
pattern (the same `[name, name, ...rest]` syntax `let` already supports),
so iterating over pairs (e.g. `items(map)`, which yields `[key, value]`
two-element lists per CHANGELOG's `from_entries`/`items` entry) doesn't
require a manual `let [k, v] = pair;` as the first line of the loop body.
Only the foreach form (`ForStmt`, `cinder/ast_nodes.py:257-264`) is in
scope — the C-style `for (init; cond; step)` loop (`ForCStmt`) is
untouched. Only the list-pattern form (`[a, b, ...rest]`) is in scope —
map-pattern destructuring (`for {a, b} in ...`) is explicitly **out of
scope** for this task (an iterated item being map-shaped often enough to
justify it hasn't come up; don't add it speculatively).

AST: add two optional fields to `ForStmt` — `names: "list | None" = None`
and `rest: "str | None" = None` — after the existing `label` field, and
widen `var_name`'s type to `"str | None"`. The two forms are mutually
exclusive: a plain loop sets `var_name` and leaves `names`/`rest` at
their `None` default (all existing construction sites, and all existing
`.cin` programs, keep working unchanged); a destructuring loop sets
`var_name=None` and populates `names` (and optionally `rest`).

Parser: in `_for_statement` (`cinder/parser.py:374-391`), after the
existing `if self._check(TokenType.LPAREN):` branch for the C-style
form, add an `elif self._check(TokenType.LBRACKET):` branch. Factor the
pattern-parsing loop already used for `let`'s list form —
`_destructure_let_statement`'s body from the `self._advance()  # consume
'[' or '{'` line through the `while self._check(TokenType.COMMA):` loop
(`cinder/parser.py:275-296`, reusing `_destructure_rest_name` at
`cinder/parser.py:303-306` unchanged) — into a shared helper, e.g.
`_destructure_list_pattern(self) -> tuple[list, str | None]`, that
consumes `[`, the names/rest, and the closing `]`, and returns `(names,
rest)`; call it from both `_destructure_let_statement` (passing
`is_map=False`, replacing its inline list-pattern logic) and the new
for-loop branch, so the comma/rest/duplicate-rest parsing logic exists
in exactly one place. After the new branch parses the pattern, continue
exactly as the existing identifier path does — expect `TokenType.IN`,
parse the iterable, require the `{` body — and construct `ForStmt(None,
iterable, body, for_token.line, for_token.column, label, names=names,
rest=rest)`.

Interpreter: in `_execute_for` (`cinder/interpreter.py:402-424`), the
per-item binding line `iter_env.define(stmt.var_name, item)` becomes
conditional on `stmt.names is not None`. Factor the existing
list-destructure arity/rest logic already in the `DestructureLetStmt`
handler (`cinder/interpreter.py:278-304`: the "not a list" type check,
the `stmt.rest is not None` branch, and the exact-length branch) into a
shared helper, e.g. `_bind_list_destructure(env, names, rest, value,
line, column)`, and call it both from the `DestructureLetStmt` handler
and from `_execute_for` (passing `stmt.names`, `stmt.rest`, `item`,
`stmt.line`, `stmt.column` — the `for` statement's own line/column, not
per-item, matching how the existing single-name path already attributes
errors to the loop) — this mirrors task 4's "reuse, don't reimplement"
approach and avoids the arity/rest logic drifting between the two call
sites. Every iteration still gets its own fresh `iter_env`
(`Environment(env)`) exactly as today, so closures captured in the body
over a destructured binding see that iteration's values, not a later
one's — no change to that part of the loop's structure.

Acceptance criteria:
- `for [k, v] in items({"a": 1, "b": 2}) { print(k); print(v); }` prints
  `"a"`, `1`, `"b"`, `2` in insertion order — the primary pairs-iteration
  case this task exists for, pin as the main regression test.
- `for [first, ...rest] in [[1, 2, 3], [4, 5, 6]] { ... }` binds `first`
  and `rest` (a list) each iteration — rest elements work in the
  for-loop position exactly as they do in `let`.
- Iterating a list of two-element lists with `for [a, b] in [[1, 2]]`
  binds `a = 1, b = 2`.
- An item that isn't a list (e.g. iterating `for [a, b] in [1, 2, 3]`,
  each item a bare number) raises `CinderRuntimeError` at the loop's own
  line/column, not a Python-level crash.
- An item list of the wrong length with no rest present (e.g. `for [a,
  b] in [[1, 2, 3]]`) raises `CinderRuntimeError`, matching `let`'s
  arity-mismatch message shape.
- `outer: for [k, v] in items(m) { if (k == "b") { break outer; } }`
  compiles and runs — labeled `break`/`continue` still work on a
  destructuring loop exactly as on a plain one (regression, `stmt.label`
  is untouched by this change).
- Existing plain `for x in expr { ... }` loops (list, string, and map
  forms) still parse and run exactly as before — run the existing `for`
  tests unmodified and confirm they still pass (regression, not a new
  test).
- `let`'s own list-destructuring behavior (including its rest-element and
  error-message tests) is unchanged after factoring out
  `_destructure_list_pattern`/`_bind_list_destructure` — run the existing
  destructuring tests unmodified and confirm they still pass (regression
  for the refactor, not a new test).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s list-destructuring
bullet under Variables & scope needs a mention that `for` loops accept
the same pattern — leave that to the Architect's next grooming pass, not
this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
