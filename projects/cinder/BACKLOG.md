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

## 1. Language: numeric literal underscores (`1_000_000`, `0xFF_FF`, `3.14_159`) [claimed 2026-08-09T14:42:45Z]

Build: teach the lexer to accept `_` as a digit-group separator in
integer, float, and prefixed (hex/binary/octal) numeric literals — the
same readability convenience Python's own literal syntax offers, e.g.
`1_000_000`, `3.14_159`, `0xFF_FF`, `0b1010_0101`. This is a
lexer-only, single-session depth task queued per `PROJECT.md`'s
breadth-vs-depth policy after two stdlib-breadth tasks (`is_fibonacci`,
`is_happy_number`) in a row above.

In `_number` (`cinder/lexer.py`, search `def _number`): the digit-scan
loops currently read `while self._peek().isdigit(): digits.append(self.
_advance())` in two places (the integer-part loop and, inside the
`is_float` branch, the fractional-part loop). Change the loop condition
in both places to also accept `_`, but only append it to `digits` if it
is *between* two digits — i.e. only consume the `_` (advancing past it
without appending) when `self._peek() == "_"` and the *previous*
character read was a digit and `self._peek_next()` is also a digit;
otherwise the `_` is not part of the literal at all and scanning stops
there (so `1_` lexes as the INT `1` followed by whatever `_` starts —
an identifier token — exactly like today's behavior for any other
trailing non-digit character; do not raise for a trailing/leading/
doubled underscore, just stop consuming, matching how `_number` already
treats `.` when not followed by a digit, see the existing `self._peek()
== "." and self._peek_next().isdigit()` guard immediately below the
integer-part loop). The float-literal decimal point check itself
(`self._peek() == "." and self._peek_next().isdigit()`) needs no
change — an underscore adjacent to the `.` (`1_.5` or `1._5`) simply
isn't consumed by either digit-scan loop, so the number lexes as `1`
(or `1_` per the rule above) followed by separate `.`/`5` tokens, which
already produces a `ParseError` downstream since `.5` alone isn't a
valid statement — no new lexer-level error is needed for that case.
Strip underscores from the collected `digits` list before joining into
`lexeme` for `int()`/`float()` conversion (`"".join(c for c in digits
if c != "_")`), but keep them in the token's own `lexeme` field
(`"".join(digits)`) so error messages and `str()`-of-token round-trip
the original source text.

In `_prefixed_int` (`cinder/lexer.py`, search `def _prefixed_int`):
apply the same treatment to its digit-scan loop
(`while self._peek().isalnum(): ...`) — accept `_` under the identical
between-two-valid-digits rule (previous character consumed was a valid
digit for this base, and `self._peek_next()` is also alnum), stopping
consumption otherwise. Do **not** allow `_` immediately after the
`0x`/`0b`/`0o` prefix (`0x_FF`) — there is no "previous digit" at that
position, so the existing rule already excludes it with no extra code.
Strip underscores before the `int(..., base)` conversion the same way,
keep them in `lexeme`.

Acceptance criteria:
- `1_000_000;` evaluates as the `INT` `1000000`.
- `3.14_159;` evaluates as the `FLOAT` `3.14159`.
- `0xFF_FF;` evaluates as the `INT` `65535`, `0b1010_0101;` evaluates as
  `165`, `0o17_7;` evaluates as `127`.
- `1_2_3;` evaluates as `123` — multiple separators in one literal.
- `1_;` lexes as `INT` `1` followed by a separate `_` identifier token
  (a trailing underscore is not consumed into the number) — confirm via
  a lexer-level token-list test, not just an end-to-end value, since
  `1_;` alone as a statement is a `ParseError` (two statements butted
  together with no operator) and that parse failure is the correct,
  expected behavior here, not a bug to work around.
- `1__0;` lexes as `INT` `1` followed by an `__0` identifier token (a
  doubled underscore stops consumption at the first one, since the
  character immediately after it is `_`, not a digit) — same
  lexer-level token-list assertion approach as above.
- `_1;` (leading underscore, no digit before it) lexes as a plain
  identifier token `_1`, never reaching `_number` at all — confirms the
  existing identifier-vs-number dispatch in the lexer's main loop is
  untouched by this change.
- Existing plain numeric literals without underscores (`42`, `3.14`,
  `0xFF`) are completely unaffected — full existing lexer/parser/
  interpreter test suite still passes unchanged.
- Full test suite passes.

Likely files: `cinder/lexer.py` (`_number`, `_prefixed_int`), `tests/
test_lexer.py` (token-list assertions for the separator, boundary, and
rejection-via-non-consumption cases above). Once merged, `README.md`'s
numeric-literals bullet (search "hex (`0x1F`)") needs the underscore
form mentioned, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Standard library: `is_triangular` — triangular-number predicate

Build: add `is_triangular(n)` to `cinder/builtins.py`, registered right
after `is_happy_number` (search for `def _is_happy_number` — by the
time this task is claimed, tasks 1-2 above will have landed and shifted
line numbers). A non-negative integer `n` is a triangular number (`0,
1, 3, 6, 10, 15, 21, ...`, the sum `1 + 2 + ... + k` for some `k >= 0`)
exactly when `8n + 1` is a perfect square — the same closed-form,
`math.isqrt`-based exact-integer technique `is_fibonacci` and
`_is_perfect_square` already use (compute `r = math.isqrt(candidate)`
and check `r * r == candidate`), not an accumulating loop that adds
`1, 2, 3, ...` until it reaches or passes `n`. This is a fresh breadth
task queued after task 2's depth work (numeric literal underscores) per
`PROJECT.md`'s breadth-vs-depth policy.

Model the arity/type-checking on `_is_fibonacci`'s or
`_is_happy_number`'s structure: reuse `_require_arity("is_triangular",
arguments, 1, line, column)` and `_require_int("is_triangular",
arguments[0], line, column)`. Negative input is not an error — mirror
`_is_perfect_square`'s own convention of answering `false` on negative
input rather than raising, since triangular numbers are only ever
defined for `n >= 0`.

Acceptance criteria:
- `is_triangular(0);` is `true`, `is_triangular(1);` is `true` — the
  degenerate (`k = 0`) and first (`k = 1`) cases.
- `is_triangular(3);` is `true`, `is_triangular(6);` is `true`,
  `is_triangular(10);` is `true`, `is_triangular(15);` is `true`,
  `is_triangular(21);` is `true`.
- `is_triangular(2);` is `false`, `is_triangular(4);` is `false`,
  `is_triangular(5);` is `false`, `is_triangular(100);` is `false` —
  non-members between/around real triangular numbers.
- `is_triangular(-6);` is `false` — negative input answers `false`
  rather than raising, matching `is_perfect_square`'s convention.
- `is_triangular(500500);` is `true` — a larger, real triangular number
  (sum `1` through `1000`), confirming the closed-form test rather than
  an unrolled lookup table of small cases.
- `is_triangular(3.0);` (float) raises `CinderRuntimeError` matching
  `"is_triangular() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `is_triangular(true);` (bool) raises `CinderRuntimeError` matching
  `"is_triangular() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_happy_number`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_triangular` added near `is_perfect_square`/
`is_fibonacci`, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## 3. Language: destructuring loop variables in list/map comprehensions

Build: extend list comprehensions (`[expr for x in iterable]`) and map
comprehensions (`{k: v for x in iterable}`) to accept a list-destructuring
loop variable in place of the single identifier, mirroring the plain
`for`-loop's own `for [k, v] in items(m) { ... }` support (`ForStmt`'s
`names`/`rest` fields, `cinder/ast_nodes.py`) — today `for [k, v] in
items(m) { ... }` works as a statement but `[k + v for [k, v] in
items(m)]` has no comprehension equivalent and must fall back to a
full statement-form loop building a list by hand with `push`. This is a
depth task queued after task 2's breadth work (`is_triangular`) per
`PROJECT.md`'s breadth-vs-depth policy.

In `cinder/ast_nodes.py`: `ListComprehension` and `MapComprehension`
currently carry a single `var_name: str` field. Add `names: "list |
None" = None` and `rest: "str | None" = None` fields to both, the same
shape `ForStmt` already uses, and make `var_name` accept `None` (used
when `names` is set instead, exactly like `ForStmt.var_name` already
can be `None`).

In `cinder/parser.py`: `_list_comprehension` and `_map_comprehension`
currently do `var_token = self._consume(TokenType.IDENTIFIER, "loop
variable after 'for'")` unconditionally. Change both to check
`self._check(TokenType.LBRACKET)` first — if true, call the existing
`self._destructure_list_pattern()` helper (search `def
_destructure_list_pattern`, already used by `_for_statement` for
exactly this purpose) to get `names, rest`, and construct the
`ListComprehension`/`MapComprehension` with `var_name=None,
names=names, rest=rest`; otherwise fall through to the existing
identifier-based path unchanged (`var_name=var_token.lexeme,
names=None, rest=None`).

In `cinder/interpreter.py`: `_evaluate_list_comprehension` and
`_evaluate_map_comprehension` currently do `iter_env.define(expr.
var_name, item)` unconditionally each iteration. Change both to mirror
`_execute_for`'s own branch (search `def _execute_for`, look at its
`if stmt.names is not None: self._bind_list_destructure(...)` vs.
`else: iter_env.define(stmt.var_name, item)` split): if `expr.names is
not None`, call the existing `self._bind_list_destructure(iter_env,
expr.names, expr.rest, item, expr.line, expr.column)` helper (already
used by `_execute_for` and `DestructureLetStmt`, raises a clean
`CinderRuntimeError` if `item` isn't a list); otherwise keep the
existing `iter_env.define(expr.var_name, item)` line unchanged.

Acceptance criteria:
- `[k + "=" + str(v) for [k, v] in items({"a": 1, "b": 2})]` produces
  a list with `"a=1"` and `"b=2"` (order matches `items`' own key
  order) — destructuring works for list comprehensions over map
  entries, the motivating case.
- `{k: v * 2 for [k, v] in items({"a": 1, "b": 2})}` produces `{"a": 2,
  "b": 4}` — destructuring works for map comprehensions too.
- `[a + b for [a, b] in [[1, 2], [3, 4], [5, 6]]]` is `[3, 7, 11]` —
  works over a plain list of lists, not just `items()` output.
- `[a for [a, ...rest] in [[1, 2, 3], [4, 5]]]` is `[1, 4]` and
  `[rest for [a, ...rest] in [[1, 2, 3], [4, 5]]]` is `[[2, 3], [5]]` —
  the trailing rest element works in comprehensions exactly as it does
  in `for [a, ...rest] in ... { ... }`.
- `[x for [a, b] in [[1, 2], 3]]` (a non-list element partway through
  the iterable) raises `CinderRuntimeError` — same error `_bind_list_
  destructure` already raises for `for [a, b] in ... { ... }` on a
  non-list item, not a silent skip or Python-level crash.
- The optional `if` filter clause still works after a destructuring
  loop variable: `[a for [a, b] in [[1, 2], [3, 4]] if a > 1]` is
  `[3]`, and the filter expression can reference the destructured
  names.
- Existing single-identifier comprehensions (`[x * 2 for x in xs]`,
  `{x: x for x in xs}`) and their own tests are completely unaffected.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`ListComprehension`,
`MapComprehension`), `cinder/parser.py` (`_list_comprehension`,
`_map_comprehension`), `cinder/interpreter.py`
(`_evaluate_list_comprehension`, `_evaluate_map_comprehension`),
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged,
`README.md`'s comprehension bullets need the destructuring form
mentioned, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 4. Standard library: `lerp` — linear interpolation

Build: add `lerp(a, b, t)` to `cinder/builtins.py`, registered right
after `clamp` (search for `def _clamp`) — the two are natural
neighbors, both simple numeric-range helpers. This is a fresh breadth
task queued after task 3's depth work (destructuring comprehension loop
variables) per `PROJECT.md`'s breadth-vs-depth policy. `lerp(a, b, t)`
linearly interpolates between `a` and `b` by fraction `t`: return
`a + (b - a) * t`. Unlike `clamp`, do **not** clamp `t` to `[0, 1]` —
`t` outside that range is valid and extrapolates past `a`/`b`, matching
the conventional unclamped `lerp` found in most graphics/game-math
libraries; a caller who wants clamping can compose it explicitly with
the existing `clamp(t, 0, 1)` builtin.

Model the arity/type-checking on `_clamp`'s structure: reuse
`_require_arity("lerp", arguments, 3, line, column)`, then check all
three arguments with `_is_numeric` the same way `_clamp` loops over
`("first", n), ("second", lo), ("third", hi)` — raise
`CinderRuntimeError` with a matching per-position message
(`"lerp() requires a number as its {position} argument, got
{type_name(value)}"`) for whichever of `a`/`b`/`t` (first/second/third)
fails. No upper/lower-bound relationship check is needed between `a` and
`b` (unlike `clamp`'s `lo <= hi` requirement) — `a > b` is a perfectly
valid interpolation range (interpolating downward), so do not add a
check that would reject it.

Acceptance criteria:
- `lerp(0, 10, 0.5);` is `5.0` — the textbook halfway case.
- `lerp(0, 10, 0);` is `0` and `lerp(0, 10, 1);` is `10` — the
  fraction's own endpoints return `a` and `b` exactly.
- `lerp(10, 20, 2);` is `30` — `t` outside `[0, 1]` extrapolates rather
  than clamping.
- `lerp(0, 10, -1);` is `-10` — extrapolation works below `0` too.
- `lerp(20, 10, 0.5);` is `15.0` — `a > b` (interpolating downward) is
  valid, not an error.
- `lerp(5, 5, 0.5);` is `5.0` — `a == b` still routes through the same
  `a + (b - a) * t` formula rather than an `a == b` short-circuit, so
  the result is float (`5 + 0 * 0.5`) even though the interpolated
  value never moves; this confirms there's no special-cased early
  return, just the one general formula.
- `lerp("0", 10, 0.5);` raises `CinderRuntimeError` matching `"lerp()
  requires a number as its first argument, got string"`; analogous
  errors for a non-numeric second or third argument, matching `_clamp`'s
  own per-position message convention.
- Wrong arity (not exactly 3 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `clamp`, see current
line numbers — shift if earlier tasks this cycle landed first), `tests/
test_builtins.py`. Once merged, `README.md`'s Builtins bullet needs
`lerp` added near `clamp`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Language: map-destructuring `for`-loop variables (`for {a, b} in list_of_maps { ... }`)

Build: `for`-loops already accept a list-destructuring loop variable
(`for [k, v] in items(m) { ... }`, `ForStmt.names`/`rest` in
`cinder/ast_nodes.py`), and `let` already accepts a map-destructuring
pattern (`let {a, b} = expr;`, `DestructureLetStmt.is_map`) — but the
two features were never crossed: there is no way to write
`for {a, b} in list_of_maps { ... }` to destructure each map in an
iterable of maps by key, so a caller who wants that today must fall
back to `for m in list_of_maps { let a = m.a; let b = m.b; ... }`. This
is the depth task queued after task 4's breadth work (`lerp`) per
`PROJECT.md`'s breadth-vs-depth policy.

In `cinder/ast_nodes.py`: `ForStmt` currently carries `names`/`rest`
(list-pattern only) with no way to say "this pattern is a map pattern."
Add an `is_map: bool = False` field, the same field
`DestructureLetStmt` already has, defaulting to `False` so every
existing `ForStmt` construction site (list-destructuring and plain
identifier) is unaffected.

In `cinder/parser.py`: `_destructure_let_statement` (search `def
_destructure_let_statement`) currently inlines its map-pattern parsing
directly in an `if is_map:` branch — consume `{`, read a
comma-separated list of plain identifiers via
`self._consume(TokenType.IDENTIFIER, "identifier in destructuring
pattern")`, consume `}`. Extract that identifier-collecting loop (not
the `{`/`}` consumption around it, since `_for_statement` needs its own
brace handling) into a new helper `_destructure_map_pattern(self) ->
list`, mirroring the existing `_destructure_list_pattern`'s shape
(consumes its own delimiters, returns just `names` — no `rest`, since
map patterns don't have one, matching `let {a, b} = expr;`'s own
no-rest behavior). Call it from `_destructure_let_statement` in place
of the inlined loop. Then in `_for_statement` (search `def
_for_statement`), add an `elif self._check(TokenType.LBRACE):` branch
alongside the existing `if self._check(TokenType.LBRACKET):` branch,
calling `self._destructure_map_pattern()` to get `names` and setting a
new local `is_map = True` (default `False` otherwise), and pass
`is_map=is_map` through to the `ForStmt(...)` construction at the end
of the function.

In `cinder/interpreter.py`: `_execute_for` (search `def _execute_for`)
currently does `if stmt.names is not None:
self._bind_list_destructure(...) else: iter_env.define(stmt.var_name,
item)`. Change the `if stmt.names is not None:` branch to check
`stmt.is_map` first: when `True`, call the existing
`self._bind_map_destructure(iter_env, stmt.names, item, stmt.line,
stmt.column)` (already used by `DestructureLetStmt` and
`DestructureAssign`, raises a clean `CinderRuntimeError` if `item` isn't
a map or is missing an expected key); otherwise keep the existing
`_bind_list_destructure` call unchanged.

Acceptance criteria:
- `for {a, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}] { print(a + b); }`
  prints `3` then `7` — the motivating case.
- `for {a} in [{"a": 1}, {"a": 2}] { print(a); }` prints `1` then `2` —
  a single-name pattern works too, not just multi-name.
- `for {a} in [{"a": 1}, 5] { print(a); }` raises `CinderRuntimeError`
  matching `"cannot destructure int as a map"` the moment the
  non-map item is reached — same error `_bind_map_destructure` already
  raises for `let {a} = 5;`, not a silent skip.
- `for {a, b} in [{"a": 1}] { print(a); }` raises `CinderRuntimeError`
  matching `"destructuring pattern expects key 'b', not found in map"`
  — a map missing an expected key fails the same way `let {a, b} =
  {"a": 1};` already does.
- `for {a, ...rest} in [...]` raises a `ParseError` (expected an
  identifier, found `...`) — map patterns have no rest element, exactly
  like `let {a, ...rest} = expr;` already has none; nothing new needs
  building for this, it falls out of `_destructure_map_pattern` only
  ever consuming identifiers.
- A labeled map-pattern loop works with `break`/`continue` targeting an
  outer loop: `outer: for {a} in [{"a": 1}] { for x in [1] { break
  outer; } }` exits cleanly.
- Existing list-destructuring for-loops (`for [k, v] in items(m) {
  ... }`) and plain-identifier for-loops are completely unaffected.
- `let {a, b} = expr;`'s own existing map-destructuring behavior is
  unaffected now that it calls the extracted `_destructure_map_pattern`
  helper instead of its old inlined loop.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`ForStmt`), `cinder/parser.py`
(`_destructure_let_statement`, new `_destructure_map_pattern`,
`_for_statement`), `cinder/interpreter.py` (`_execute_for`), `tests/
test_parser.py`, `tests/test_interpreter.py`. Once merged, `README.md`'s
`for`-loop bullet needs the map-destructuring form mentioned, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
