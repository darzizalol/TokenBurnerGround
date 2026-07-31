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

## 1. Spread elements in map literals: `{...map1, "k": v}`

Build: extend the spread operator, currently only accepted inside list
literals and call arguments (`Spread` node, `cinder/ast_nodes.py:69-76`;
parsed at `_list_element`, `cinder/parser.py:939-943`; evaluated in
`_evaluate_list_literal`, `cinder/interpreter.py:456-469`), to also work
inside map literals. `MapLiteral.pairs` (`cinder/ast_nodes.py:86-90`) is
currently `list[tuple[Expr, Expr]]`; change its contents to mix `tuple`
entries (plain `key: value` pairs, as today) with `Spread` entries,
mirroring how `ListLiteral.elements` already mixes plain `Expr` and
`Spread`. Parser: add a `_map_entry()` method mirroring `_list_element()`
— if the next token is `DOT_DOT_DOT`, consume it and return
`Spread(self._ternary(), dots.line, dots.column)`; otherwise delegate to
the existing `_map_pair()` and return its `(key, value)` tuple unchanged.
Update `_map_literal()` (`cinder/parser.py:945-953`) to call
`_map_entry()` in both places it currently calls `_map_pair()` directly
(the first entry and each comma-separated one). Interpreter: in
`_evaluate_map_literal` (`cinder/interpreter.py:472-482`), iterate
`expr.pairs` and branch on `isinstance(entry, Spread)`: if so, evaluate
`entry.expression`, require the result is a `dict` (else
`CinderRuntimeError` `f"cannot spread {type_name(value)} in a map
literal"` at `entry.line`/`entry.column`, matching the phrasing pattern
`_evaluate_list_literal`/`_evaluate_call` already use for their own kind
of literal/call), then `result.update(value)`; otherwise keep today's
per-pair logic (evaluate key, `_is_valid_key` check, evaluate value,
assign) unchanged. Splicing order follows plain iteration/last-write-wins
— no special-casing needed since `dict.update`/assignment already give
"later entry wins" for free, whether the later entry is a spread or an
explicit key.

Acceptance criteria:
- `{"a": 1, ...{"b": 2}}` is `{"a": 1, "b": 2}`.
- `{...{"a": 1}, "a": 2}` is `{"a": 2}` — an explicit key after a spread
  overrides the spread's value for that key.
- `{...{"a": 1}, ...{"a": 2, "b": 3}}` is `{"a": 2, "b": 3}` — a later
  spread overrides an earlier one key-by-key, not wholesale.
- `{...{}}` is `{}`; `{}` (no spread at all) still parses as today's
  empty map literal, not a block (regression test — don't disturb the
  existing empty-`{}`-is-a-map disambiguation).
- Spreading a non-map value, e.g. `{...[1, 2]}` or `{...5}`, raises
  `CinderRuntimeError` with the message `"cannot spread {type} in a map
  literal"` and the spread expression's line/column.
- A map literal mixing multiple spreads and explicit keys in any order
  (e.g. `{"x": 0, ...{"a": 1}, "y": 2, ...{"a": 3}}`) evaluates left to
  right with strict last-write-wins: `{"x": 0, "a": 3, "y": 2}`.
- List-literal spread and call-argument spread both still behave exactly
  as before (regression tests) — this task only adds a new place spread
  is accepted, it must not change existing behavior.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s Data Structures
bullet ("map literals don't support spread") will need updating too —
leave that to the Architect's next grooming pass, not this task.

---

## 2. Function composition: `pipe` and `compose`

Build: add `pipe(...fns)` and `compose(...fns)` to `cinder/builtins.py` —
each takes zero or more Cinder function values (variable arity, no fixed
argument count — mirror how `_min`/`_max` at `cinder/builtins.py:766-784`
already validate a variable-length `arguments` list with no
`_require_arity` call) and *returns a new callable Cinder value* rather
than computing a result directly. This is the first builtin in the
codebase to hand back a function instead of a plain value, but the
mechanism already exists: `Builtin` (`cinder/interpreter.py:149-161`) is
a thin wrapper around any Python closure with signature `(arguments:
list, line: int, column: int) -> object`, and `call_value`
(`cinder/interpreter.py:824`, already imported into `builtins.py` and
used by `map`/`filter`/`reduce` to invoke a Cinder function value passed
in) is exactly what a returned function needs to call each wrapped `fn`
in turn. Validate every element of `fns` is callable up front (loop over
`arguments`, `_is_callable` check per element — reuse `_is_callable` at
`cinder/builtins.py:1844` — raising `CinderRuntimeError` with the
same `f"pipe() requires a function for each argument, got
{type_name(...)}"`/`compose()` phrasing, at the `pipe`/`compose` call's
own `line`/`column`) — not deferred to when the returned function is
later invoked. The returned `Builtin`'s inner closure takes exactly one
argument `x` (validate with `_require_arity` using a synthetic name,
e.g. `"<piped function>"`/`"<composed function>"`, so a wrong-arity call
on the *result* of `pipe`/`compose` gets a sensible error instead of a
Python `TypeError`) and threads it through every wrapped function via
`call_value(fn, [x], line, column)` per step, using the *inner* call's
`line`/`column` (the site that invokes the composed function) for each
`call_value` invocation, not `pipe`/`compose`'s own call site. `pipe`
applies left to right (`pipe(f, g, h)(x)` is `h(g(f(x)))`, matching
Unix-pipe/data-flow order); `compose` applies right to left
(`compose(f, g, h)(x)` is `f(g(h(x)))`, matching standard mathematical
composition order — the two differ only in whether the closure iterates
`fns` forwards or in `reversed(fns)`). Zero functions (`pipe()`/
`compose()`) returns an identity function: calling it with one argument
returns that argument unchanged.

Acceptance criteria:
- `pipe(fn(x) { return x + 1; }, fn(x) { return x * 2; })(5)` is `12`
  (`(5 + 1) * 2`) — left-to-right order, pin as the primary `pipe` test.
- `compose(fn(x) { return x + 1; }, fn(x) { return x * 2; })(5)` is `11`
  (`5 * 2 + 1`) — right-to-left order, pin as the primary `compose` test,
  explicitly asserting it differs from `pipe`'s result on the same two
  functions.
- `pipe()(5)` is `5` and `compose()(5)` is `5` — zero-argument identity
  case for both.
- `pipe(fn(x) { return x; })(5)` is `5` — single-function pipeline is a
  no-op pass-through (regression guard distinguishing "one function" from
  "zero functions" taking the same code path correctly).
- The value returned by `pipe`/`compose` is itself a first-class Cinder
  value: assignable to a `let`, passable to `map`
  (`map([1, 2, 3], pipe(fn(x) { return x + 1; }))` is `[2, 3, 4]`), and
  `type()` of it reports the same type name an ordinary function value
  reports (regression test — it must not be a distinguishable "special"
  type from the caller's perspective).
- `pipe(1, fn(x) { return x; })` (a non-function argument anywhere in the
  list) raises `CinderRuntimeError` with line/column at the `pipe(...)`
  call site itself, before the returned function is ever invoked; same
  for `compose`.
- Calling the *result* of `pipe(...)`/`compose(...)` with zero arguments
  or two-or-more arguments raises `CinderRuntimeError` (arity mismatch on
  the composed function itself, not a Python-level crash).
- A three-function pipeline/composition (not just two) is covered by at
  least one test each, to catch an off-by-one in the fold direction.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register both in `_BUILTINS`,
`cinder/builtins.py:2096` onward, near `map`/`filter`/`reduce`'s
entries), `tests/test_builtins.py`. Update the module docstring's
builtin-name list at the top of `cinder/builtins.py` and the README's
Builtins bullet once merged — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Rest element in list destructuring: `let [a, b, ...rest] = expr;`

Build: extend list-destructuring `let` (`DestructureLetStmt`,
`cinder/ast_nodes.py:216-221`, currently `names: list` plus an `is_map`
flag with no rest concept) to accept an optional trailing rest name,
reusing the spread token exactly as function parameters already do
(`fn f(a, ...rest) { ... }`, parsed at `_fn_params_and_body`,
`cinder/parser.py:419-458`, whose comma loop raises `ParseError("rest
parameter must be the last parameter", ...)` at `cinder/parser.py:432-436`
via `TokenType.DOT_DOT_DOT`). Add a `rest: str | None` field to
`DestructureLetStmt`, defaulting to `None`. Parser: in
`_destructure_let_statement` (`cinder/parser.py:269-283`), only for the
list form (`is_map=False` — map destructuring keeps its current
exact-keys behavior unchanged, rest is list-only for this task), after
parsing each comma-separated identifier, check whether the next token is
`DOT_DOT_DOT`; if so, consume it, consume one more `IDENTIFIER` as the
rest name, and require it to be the *last* pattern element — a
non-`]`/`,` token immediately after (i.e. anything but the closing
bracket) following the rest name is a `ParseError` (mirror the phrasing
`_fn_params_and_body`'s existing rest-parameter-must-be-last check uses,
at `cinder/parser.py:432-436`, adapted to: `f"rest element must be last
in destructuring pattern, found {self._describe(token)}"` with the
offending token's line/column). Interpreter: in `execute`'s
`DestructureLetStmt` branch (`cinder/interpreter.py:259-286`), when
`stmt.rest is not None`, require `len(value) >= len(stmt.names)` (not
`==` — the fixed names must all have a source element, the rest soaks up
whatever's left, including zero), bind each fixed name positionally as
today, then `env.define(stmt.rest, list(value[len(stmt.names):]))`
(always a list, even if empty). When `stmt.rest is None`, behavior is
byte-for-byte unchanged from today (the existing `len(value) !=
len(stmt.names)` exact-match check still applies).

Acceptance criteria:
- `let [a, b, ...rest] = [1, 2, 3, 4]; [a, b, rest]` is `[1, 2, [3, 4]]`.
- `let [a, ...rest] = [1]; [a, rest]` is `[1, []]` — rest binds an empty
  list when there's nothing left over, pin as an explicit regression
  test.
- `let [...rest] = [1, 2, 3]; rest` is `[1, 2, 3]` — a pattern that's
  only a rest element (no fixed names before it) captures everything.
- `let [a, b, ...rest] = [1]` (fewer elements than fixed names, even
  with a rest present) raises `CinderRuntimeError` with line/column —
  rest does not relax the minimum-length requirement for the fixed
  names before it.
- `let [a, ...rest, b] = [1, 2, 3];` (rest not last) raises `ParseError`
  with line/column.
- Map destructuring (`let {a, b} = expr;`) is completely unaffected —
  existing tests still pass unchanged (regression test — this task only
  touches the list form).
- Destructuring without any rest element (`let [a, b] = [1, 2];`) still
  requires an exact length match, byte-for-byte the same error as today
  on mismatch (regression test).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, the README's Variables & scope
bullet ("flat positional binding, no nesting/rest") needs a wording
update — leave that to the Architect's next grooming pass, not this
task.

---

## 4. `throw` statement for user-raised errors

Build: add a `throw EXPR;` statement so Cinder code can raise its own
runtime errors with a custom message, instead of the only way to
signal failure today being `assert(cond, message)` (`_assert`,
`cinder/builtins.py:1765-1774`) or an error that already happened
naturally — both catchable today only via `try { ... } catch (name) {
... }` (`_execute_try`, `cinder/interpreter.py:366-377`, which binds
`error.message`, a plain string, to `name`). Mirror `assert`'s own
message-typing rule exactly: the thrown value must be a `str` (`throw`
does not accept arbitrary values the way `return` does — same
constraint `_assert` already imposes on its second argument, and for the
same reason: `catch (name)` binds a plain string today and this task
must not change that contract). Lex/parse: no new token type needed —
add `TokenType.THROW` as a new keyword (mirror how `TokenType.RETURN` is
lexed/reserved) and a `ThrowStmt` AST node (`expression: Expr`, `line:
int`, `column: int`, mirroring `ReturnStmt`'s shape). Parser: dispatch
`THROW` in `_statement()` (`cinder/parser.py:214-245`, alongside the
existing `RETURN`/`BREAK`/`CONTINUE` dispatch) to a new
`_throw_statement()` that consumes `throw`, parses one expression via
`self._assignment()`, consumes the trailing `;`, and returns
`ThrowStmt(expression, throw_token.line, throw_token.column)` (mirror
`_return_statement`'s shape, but the expression is required, not
optional — `throw;` with no value is a `ParseError`, `"expected
expression after 'throw'"` at the `throw` token's line/column).
Interpreter: in `execute` (`cinder/interpreter.py`, alongside the
`ReturnStmt`/`BreakStmt`/`ContinueStmt` handling around lines 342-348),
evaluate `stmt.expression`; if the result isn't a `str`, raise
`CinderRuntimeError(f"throw requires a string message, got
{type_name(value)}", stmt.line, stmt.column)` (same phrasing pattern as
`_assert`'s type check); otherwise raise `CinderRuntimeError(value,
stmt.line, stmt.column)` directly — no new signal/exception class
needed, `try`/`catch` already catches any `CinderRuntimeError` via
`_execute_try`, so a thrown error is caught exactly like a
builtin-raised one, `finally` still runs (regression-covered by
`_execute_try`'s existing `finally` block, untouched by this task), and
an uncaught `throw` still reports line/column (and a call-stack trace if
thrown from inside a nested call) exactly like any other uncaught
`CinderRuntimeError` today.

Acceptance criteria:
- `try { throw "boom"; } catch (e) { print(e); }` prints `boom` — a
  thrown string is caught and bound exactly like a naturally-raised
  error's message.
- An uncaught `throw "boom";` at top level raises `CinderRuntimeError`
  with message `"boom"` and the `throw` statement's own line/column
  (regression test asserting the structured fields, not just that it
  raises).
- `throw 42;` (non-string operand) raises `CinderRuntimeError` with
  message `"throw requires a string message, got number"` and the
  `throw` statement's own line/column — the type error itself, distinct
  from the "thrown" error it would otherwise be.
- `throw` inside a function called from another function still reports
  the full call-stack trace on the way out, same as any other runtime
  error raised deep in a call chain (reuse whatever existing test
  pattern `test_interpreter.py` uses for call-stack frames on a
  naturally-raised error).
- `try { throw "x"; } finally { <side effect>; }` (no catch block) still
  runs the `finally` body before the error propagates uncaught
  (regression test pinning `finally`'s existing run-before-propagate
  semantics against this new source of error).
- `throw;` with no expression raises `ParseError` with line/column.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/ast_nodes.py`,
`cinder/parser.py`, `cinder/interpreter.py`, `tests/test_lexer.py`,
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged, the
README's Control flow bullet needs a `throw` mention — leave that to the
Architect's next grooming pass, not this task.

---

## 5. Standard library: `get_in` for safe nested access

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

## 6. Standard library: `curry` for single-argument currying

Build: add `curry(fn, arity)` to `cinder/builtins.py` — returns a new
callable Cinder value (same returned-function mechanism task 2's
`pipe`/`compose` introduces: a `Builtin` closure built with `call_value`,
`cinder/interpreter.py:824`, to invoke the wrapped function) that accepts
its arguments **one at a time**, accumulating them, and only actually
calls `fn` once `arity` arguments have been collected — e.g.
`curry(fn(a, b, c) { return a + b + c; }, 3)(1)(2)(3)` is `6`. Validate
`fn` is callable up front (reuse `_is_callable`, `cinder/builtins.py:1844`,
raising `CinderRuntimeError` `f"curry() requires a function as its first
argument, got {type_name(fn)}"` at the `curry(...)` call's own
line/column if not — do not defer to first invocation) and `arity` is a
positive `int` (`isinstance(arity, int) and not isinstance(arity, bool)`
and `arity >= 1`; `arity < 1` including `0` and negative values raises
`CinderRuntimeError` `f"curry() requires arity to be at least 1, got
{arity}"`, non-int raises `f"curry() requires an int arity, got
{type_name(arity)}"` — both at the call site). Each step's returned
`Builtin` closure takes **exactly one** argument (validate with
`_require_arity`, `cinder/builtins.py:49`, using a synthetic name like
`"<curried function>"`, mirroring task 2's approach for its own returned
closures' arity checks), appends it to an accumulator list captured by
that step's closure (each step must capture its *own* accumulator
snapshot — e.g. via a default-argument or an immediately-applied helper
— not a single mutable list shared and mutated across steps, or partial
application from a shared base would corrupt sibling calls: calling
`let step1 = curry(fn, 2)(1); step1(2); step1(3);` twice must yield two
independent results, not accumulate `[1, 2, 3]`). Once the accumulator
reaches `arity` elements, call `fn` via `call_value(fn, accumulated,
line, column)` (the *inner* call's line/column — the site invoking the
final step, not `curry`'s own call site, mirroring task 2's rule) and
return that result directly, not another wrapped function; below
`arity`, return a new one-argument `Builtin` closure over the extended
accumulator.

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
`cinder/builtins.py:2194` onward, alongside wherever task 2 registers
`pipe`/`compose`), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `curry` added near `pipe`/`compose` — leave that to
the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
