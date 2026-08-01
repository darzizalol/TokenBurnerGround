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

## 1. Multiple values per `switch` case: `case 1, 2, 3: { ... }`

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

## 2. List destructuring in `for`-loop variables: `for [k, v] in items(m) { ... }`

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
errors to the loop) — this mirrors task 1's "reuse, don't reimplement"
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

## 3. Dot access sugar for map string keys: `m.key` as sugar for `m["key"]`

Build: let a map be read/written with dot notation (`m.key`) as pure
syntactic sugar for bracket indexing with a string literal (`m["key"]`) —
no new AST node, no interpreter changes. `TokenType.DOT` already exists
(`cinder/tokens.py:87`) and the lexer already emits a standalone `DOT`
token for any `.` that isn't consumed while scanning a number literal
(`cinder/lexer.py:349`), so no lexer change is needed either. In `_call`
(`cinder/parser.py:878-888`, the postfix loop that already handles `(`
and `[` after a primary expression), add a third branch:
`elif self._check(TokenType.DOT): expr = self._finish_dot(expr)`. Add
`_finish_dot`, modeled on `_finish_index` (`cinder/parser.py:907-920`):
consume the `DOT`, require the next token be `TokenType.IDENTIFIER`
(raise `ParseError` `"expected a property name after '.'"` at the
identifier-position token if not — this means dot access only reaches
identifier-shaped keys, never a keyword or a computed key; `m["if"]` or
`m[k]` remain the only way to reach those, which is an accepted
limitation, not a bug to work around), and return `Index(obj,
Literal(name_token.lexeme, name_token.line, name_token.column), dot.line,
dot.column)` — i.e. dot access desugars into exactly the same `Index`
node (`cinder/ast_nodes.py:94-98`) that `m["key"]` already produces, just
with the bracket-expression replaced by a string literal built from the
identifier's lexeme.

This reuse is what makes the task small: `_assignment`
(`cinder/parser.py:700-760`) and the statement-level `_expr_or_incdec`
(`cinder/parser.py:662-698`) both already dispatch on `isinstance(expr,
Index)` — not on how that `Index` was produced — to build `IndexAssign`,
`IndexCompoundAssign` (for the bitwise/shift compound-assign set), and
`++`/`--` targets. Because `_finish_dot` produces a plain `Index`, plain
assignment (`m.key = v`), the bitwise/shift compound-assign set (`m.key
&= 3`), and increment/decrement (`m.key++`) all work automatically with
zero additional parser or interpreter code — do not add special-case
handling for any of these; if you find yourself editing
`interpreter.py`, you've taken a wrong turn. The one exception already
true of bracket indexing (not a new gap this task introduces): the
arithmetic compound-assign set (`+=` etc.) is identifier-only, so `m.key
+= 1` raises `"invalid assignment target"` exactly as `m["key"] += 1`
already does today — out of scope to change here.

Acceptance criteria:
- `let m = {"a": 1}; m.a;` is `1` — the primary read case, pin as the
  main regression test.
- `let m = {"nested": {"b": 2}}; m.nested.b;` is `2` — chained dot access
  through nested maps.
- `let m = {"a": 1}; m.a = 5; m.a;` is `5` — dot access as an assignment
  target.
- `let m = {"x": 6}; m.x &= 3; m.x;` is `2` — dot access as a bitwise
  compound-assign target, same as `m["x"] &= 3` today.
- `let m = {"x": 1}; m.x++; m.x;` is `2` — dot access as an
  increment-statement target, same as `m["x"]++;` today.
- `let m = {"a": 1}; m.a += 1;` raises `CinderRuntimeError` (or
  `ParseError`, matching whatever `m["a"] += 1` already raises today —
  check and mirror it exactly) — dot access does not gain arithmetic
  compound-assign where bracket indexing doesn't have it either.
- `let m = {"a": 1}; m.b;` (missing key) raises `CinderRuntimeError` at
  the `.b` site, the same error `m["b"]` already raises for a missing
  key — no special-cased "did you mean" behavior for dot access.
- `let xs = [1, 2, 3]; xs.foo;` (dot access on a list) raises
  `CinderRuntimeError` — same error `xs["foo"]` already raises today
  (list indices must be `int`), not a new/different message.
- `let m = {"greet": fn(name) { return "hi " + name; }}; m.greet("Ada");`
  is `"hi Ada"` — a map value reached via dot access is callable exactly
  like one reached via bracket access (no special method-call binding of
  `self`/`this` — Cinder has none, and this task must not add one).
- `m.if;` where `m` is a map (dot access followed by a keyword rather
  than a plain identifier) raises `ParseError` at the `.` — dot access
  never reaches keyword-named keys; this is the documented limitation,
  not a regression to fix.
- Existing bracket indexing (`m["key"]`, `xs[0]`, slices, all existing
  assignment/compound-assignment/increment forms on `Index` targets) is
  completely unchanged — run the existing indexing/assignment tests
  unmodified and confirm they still pass (regression, not a new test;
  this task only ever adds a new way to *produce* an `Index` node, never
  changes what happens to one after it's produced).
- Full test suite passes.

Likely files: `cinder/parser.py` (the only file expected to change),
`tests/test_parser.py`, `tests/test_interpreter.py` (end-to-end dot-access
programs, mirroring how other sugar features are end-to-end tested).
Once merged, `README.md`'s `Data structures` bullet needs a mention that
maps also support dot access for string keys — leave that to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `pick_by`/`omit_by` for predicate-based map filtering

Build: add `pick_by(map, predicate)` and `omit_by(map, predicate)` to
`cinder/builtins.py`, filling the gap `pick`/`omit`
(`cinder/builtins.py:465-494`) leave open — those two take an explicit
list of keys, but there's no way today to keep/drop map entries by a
condition on the key or value the way `filter` (`cinder/builtins.py:1929-
1942`) already does for lists. Model both new functions directly on
`_pick`/`_omit`'s existing shape (arity 2, first argument a `dict`), with
the `keys: list` argument replaced by a `predicate` callable argument
validated with `_is_callable` (imported already via
`cinder/interpreter.py`'s exports used elsewhere in this file — mirror
`filter`'s own validation at `cinder/builtins.py:1937-1941` exactly,
including its error message shape) instead of `isinstance(keys, list)`.
For each `key, value` pair in the target map (iterate `target.items()`,
same as `_omit`'s dict-comprehension today), call the predicate via
`call_value(predicate, [key, value], line, column)` — the *call site's*
`line`/`column` (this builtin's own, since the predicate is invoked
synchronously inline, not via a separately-tracked call site — same
attribution `filter` already uses for its own predicate calls) — and
check truthiness with `is_truthy` on the result, exactly as `filter`
does. `pick_by` keeps an entry when the predicate call is truthy;
`omit_by` keeps an entry when it is falsy — the two are exact mirror
images of each other, same as `pick`/`omit` already are. Preserve
insertion order (build the result via a dict comprehension or explicit
loop over `target.items()` in order, never via any operation that could
reorder keys).

Acceptance criteria:
- `pick_by({"a": 1, "b": 2, "c": 3}, fn(k, v) { return v > 1; });` is
  `{"b": 2, "c": 3}` — the primary value-predicate case, pin as the main
  regression test.
- `omit_by({"a": 1, "b": 2, "c": 3}, fn(k, v) { return v > 1; });` is
  `{"a": 1}` — the exact complement of the `pick_by` case above on the
  same input and predicate.
- `pick_by({"a": 1, "bb": 2, "ccc": 3}, fn(k, v) { return len(k) == 1; });`
  is `{"a": 1}` — the predicate can inspect the key, not just the value.
- `pick_by({}, fn(k, v) { return true; });` is `{}` — an empty map
  produces an empty result without invoking the predicate.
- `pick_by({"a": 1, "b": 2}, fn(k, v) { return false; });` is `{}` and
  `omit_by({"a": 1, "b": 2}, fn(k, v) { return false; });` is
  `{"a": 1, "b": 2}` — an always-false predicate is the identity for
  `omit_by` and empties `pick_by`, confirming the two aren't accidentally
  swapped.
- `pick_by([1, 2, 3], fn(k, v) { return true; });` (a list, not a map)
  raises `CinderRuntimeError` naming `pick_by` and `list` in the message,
  at the call site's line/column; `omit_by` raises the equivalent error
  for the same input.
- `pick_by({"a": 1}, "not a function");` raises `CinderRuntimeError`
  naming `pick_by` and the actual argument's type in the message
  (mirroring `filter`'s non-callable-second-argument error shape); same
  for `omit_by`.
- Wrong arity on either builtin (not exactly 2 arguments) raises
  `CinderRuntimeError` with line/column.
- Result key insertion order matches the source map's iteration order
  for both builtins (e.g. `keys(pick_by({"z": 1, "a": 2}, fn(k, v) {
  return true; }));` is `["z", "a"]`, not re-sorted).
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `pick`/`omit`,
`cinder/builtins.py:2217-2218`), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `pick_by`/`omit_by` added near
`pick`/`omit` — leave that to the Architect's next grooming pass, not
this task.

---

## 5. Standard library: `take_right`/`drop_right` for taking/dropping from a list's end

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
