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

## 1. Language: destructuring loop variables in list/map comprehensions [claimed 2026-08-09T19:17:14Z]

Build: extend list comprehensions (`[expr for x in iterable]`) and map
comprehensions (`{k: v for x in iterable}`) to accept a list-destructuring
loop variable in place of the single identifier, mirroring the plain
`for`-loop's own `for [k, v] in items(m) { ... }` support (`ForStmt`'s
`names`/`rest` fields, `cinder/ast_nodes.py`) — today `for [k, v] in
items(m) { ... }` works as a statement but `[k + v for [k, v] in
items(m)]` has no comprehension equivalent and must fall back to a
full statement-form loop building a list by hand with `push`. This is
the depth task queued after `is_triangular` landed (breadth work) per
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

## 2. Standard library: `lerp` — linear interpolation

Build: add `lerp(a, b, t)` to `cinder/builtins.py`, registered right
after `clamp` (search for `def _clamp`) — the two are natural
neighbors, both simple numeric-range helpers. This is a fresh breadth
task queued after task 1's depth work (destructuring comprehension loop
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

## 3. Language: map-destructuring `for`-loop variables (`for {a, b} in list_of_maps { ... }`)

Build: `for`-loops already accept a list-destructuring loop variable
(`for [k, v] in items(m) { ... }`, `ForStmt.names`/`rest` in
`cinder/ast_nodes.py`), and `let` already accepts a map-destructuring
pattern (`let {a, b} = expr;`, `DestructureLetStmt.is_map`) — but the
two features were never crossed: there is no way to write
`for {a, b} in list_of_maps { ... }` to destructure each map in an
iterable of maps by key, so a caller who wants that today must fall
back to `for m in list_of_maps { let a = m.a; let b = m.b; ... }`. This
is the depth task queued after task 2's breadth work (`lerp`) per
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

## 4. Standard library: `is_emirp` — emirp predicate

Build: add `is_emirp(n)` to `cinder/builtins.py`, registered right after
`_is_composite` (search for `def _is_composite`) — it's the natural
third member of that prime-family cluster, alongside `is_prime`/
`is_composite`. This is a fresh breadth task queued after task 3's
depth work (map-destructuring `for`-loop variables) per `PROJECT.md`'s
breadth-vs-depth policy, continuing the same one-breadth-then-depth
alternation task 2 (`lerp`) got after task 1's comprehension-
destructuring depth work.

An **emirp** ("prime" spelled backwards) is a prime number whose
decimal-digit reversal is a *different* prime — palindromic primes
like `11` or `2` don't count, since reversing them gives the same
number back. `13` is the canonical example: it's prime, and its
reversal `31` is also prime and not equal to `13`.

Do not call `_is_prime`/`_reverse_int` directly — both take the
`(arguments, line, column)` builtin-dispatch signature, not a raw
`int`, so reuse isn't a straight function call. Instead inline the same
two techniques already used elsewhere: `_is_composite`'s own
trial-division-to-`sqrt(n)` loop (copy its shape, don't factor a shared
helper — `is_composite` already sits right next to `is_prime` without
one) for primality, and `_reverse_int`'s `str(abs(value))[::-1]`
digit-reversal (sign doesn't matter here since `is_emirp` only ever
considers non-negative primes) to get the reversed value, then check
both the original and reversed values are prime and unequal.

Model the arity/type-checking on `_is_prime`'s structure: reuse
`_require_arity("is_emirp", arguments, 1, line, column)` and
`_require_int("is_emirp", arguments[0], line, column)`. Negative input
is not a separate error case — mirror `is_prime`'s own convention where
any `value < 2` simply answers `false`, which negative input already
satisfies with no extra check needed.

Acceptance criteria:
- `is_emirp(13);` is `true`, `is_emirp(17);` is `true`,
  `is_emirp(31);` is `true`, `is_emirp(79);` is `true`,
  `is_emirp(97);` is `true` — classic emirp pairs in both directions.
- `is_emirp(2);` is `false`, `is_emirp(11);` is `false` — palindromic
  primes are not emirps, since their reversal equals themselves.
- `is_emirp(4);` is `false`, `is_emirp(15);` is `false`,
  `is_emirp(20);` is `false` — non-primes answer `false` regardless of
  what their reversal looks like.
- `is_emirp(0);` is `false`, `is_emirp(1);` is `false` — below the
  prime threshold, matching `is_prime`'s own convention.
- `is_emirp(-13);` is `false` — negative input answers `false` without
  raising, falling out of the same `value < 2` check `is_prime` uses,
  not a special-cased guard.
- `is_emirp(107);` is `true` — a larger three-digit emirp (reversal
  `701`, also prime), confirming the trial-division check scales past
  small hand-checkable cases.
- `is_emirp(3.0);` (float) raises `CinderRuntimeError` matching
  `"is_emirp() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `is_emirp(true);` (bool) raises `CinderRuntimeError` matching
  `"is_emirp() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_composite`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_emirp` added near `is_prime`/`is_composite`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 5. Language: list/map-destructuring function parameters (`fn f([a, b]) { ... }`, `fn f({a, b}) { ... }`)

Build: extend function-parameter parsing/binding — shared by named
`fn` declarations, anonymous `fn` expressions, and parenthesized arrow
functions alike, since all three route through `_fn_param_list`/
`_fn_param` in `cinder/parser.py` (search both) — to accept a list- or
map-destructuring pattern in place of a plain identifier parameter,
mirroring the patterns `let`, plain assignment, and (after task 3
lands) `for`-loops already accept in every other binding position.
Today a caller passing e.g. a `[x, y]` point or a `{a, b}` options
record must destructure it by hand on the first line of the body
(`fn dist(p) { let [x, y] = p; ... }`); this closes that gap so
`fn dist([x, y]) { ... }` works directly. This is the depth task
queued after task 4's breadth work (`is_emirp`) per `PROJECT.md`'s
breadth-vs-depth policy.

In `cinder/ast_nodes.py`: `FnDecl`/`FnExpr` currently carry
`params: list` of raw `(name: str, default: Expr | None)` tuples
(built by `_fn_param`). Add a `Param` dataclass — the same field shape
`ForStmt` already uses for its own pattern flexibility — with
`name: "str | None"`, `default: "Expr | None" = None`,
`names: "list | None" = None`, `rest: "str | None" = None`, and
`is_map: bool = False`. A plain identifier parameter sets only
`name`/`default` (`names=None`); a list-destructuring parameter sets
`name=None, names=names, rest=rest`; a map-destructuring parameter
sets `name=None, names=names, is_map=True`. Change `FnDecl.params`/
`FnExpr.params`'s annotation from `list` of tuples to `list[Param]`.

In `cinder/parser.py`: change `_fn_param` to check
`self._check(TokenType.LBRACKET)`/`self._check(TokenType.LBRACE)`
before its current unconditional
`self._consume(TokenType.IDENTIFIER, "parameter name")`. On `[`, call
the existing `_destructure_list_pattern()` helper to get `names, rest`
and return `Param(name=None, names=names, rest=rest)` — no default
allowed: a destructuring parameter followed by `=` raises `ParseError`
(e.g. `"destructuring parameter cannot have a default value"`), since
there's no single value to show as a default. On `{`, call
`_destructure_map_pattern()` (the helper task 3 extracts out of
`_destructure_let_statement`) to get `names` and return
`Param(name=None, names=names, is_map=True)`, same no-default
restriction. Otherwise keep the existing identifier-plus-optional-
default path, now returning `Param(name=name_token.lexeme,
default=default)` instead of a bare tuple. A destructuring parameter
counts as "has no default" for the existing `seen_default` tracking in
`_fn_param_list` — no new rule needed, since `seen_default` already
only flips true when a default is actually seen.

In `cinder/interpreter.py`: `CinderFunction.arity` currently does
`sum(1 for _, default in self.decl.params if default is None)` —
change the unpacking to iterate `Param` objects
(`sum(1 for param in self.decl.params if param.default is None)`); a
destructuring parameter's `default` is always `None` so it already
counts as required, no special-case needed. `call_value`'s parameter-
binding loop currently does
`for index, (param_name, default) in enumerate(callee.decl.params):
... call_env.define(param_name, value)` — change to iterate `Param`
objects and, after resolving `value` (argument or evaluated default,
unchanged), branch on `param.names is not None`: if `param.is_map`,
call the existing `self._bind_map_destructure(call_env, param.names,
value, line, column)`; elif list pattern, call
`self._bind_list_destructure(call_env, param.names, param.rest, value,
line, column)`; else keep `call_env.define(param.name, value)`. Reuse
the same errors those helpers already raise (`CinderRuntimeError` for
a non-list/non-map argument or a missing map key) — no new error text
to design.

Acceptance criteria:
- `fn dist([x, y]) { return x * x + y * y; } print(dist([3, 4]));`
  prints `25` — the motivating list-destructuring case.
- `fn describe({name, age}) { return name + " is " + str(age); }
  print(describe({"name": "Al", "age": 30}));` prints `Al is 30` — the
  motivating map-destructuring case.
- `fn f([a, ...rest]) { return rest; } print(f([1, 2, 3]));` prints
  `[2, 3]` — the trailing rest element works in a destructuring
  parameter exactly as it does in `let`/`for`.
- A destructuring parameter combines with a plain trailing rest
  *parameter*: `fn f([a, b], ...more) { return [a, b, more]; }
  print(f([1, 2], 3, 4));` prints `[1, 2, [3, 4]]` — the parameter-
  list-level rest (extra positional arguments) and a pattern-level
  rest (inside one `[...]` parameter) are independent features that
  don't conflict.
- Anonymous `fn` expressions and parenthesized arrow functions accept
  the same patterns: `let f = fn([a, b]) { return a + b; };
  print(f([1, 2]));` and `print((([a, b]) => a + b)([1, 2]));` both
  print `3`.
- `fn f([a, b] = [1, 2]) { return a; }` raises `ParseError` (a
  destructuring parameter cannot have a default value).
- `fn f([a, b]) { return a; } f(5);` (a non-list argument where a list
  pattern was declared) raises the same `CinderRuntimeError`
  `_bind_list_destructure` already raises for `let [a, b] = 5;`, not a
  silent crash.
- `fn f({a, b}) { return a; } f({"a": 1});` (a map argument missing an
  expected key) raises the same `CinderRuntimeError`
  `_bind_map_destructure` already raises for `let {a, b} = {"a": 1};`.
- Existing plain-identifier parameters, defaults, and rest parameters
  (`fn f(a, b = 1, ...rest) { ... }`) are completely unaffected.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`FnDecl`, `FnExpr`, new `Param`),
`cinder/parser.py` (`_fn_param`, `_fn_param_list`),
`cinder/interpreter.py` (`CinderFunction.arity`, `call_value`), `tests/
test_parser.py`, `tests/test_interpreter.py`. Once merged, `README.md`'s
Functions bullet needs the destructuring-parameter form mentioned, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `divisors` — list an integer's positive divisors

Build: add `divisors(n)` to `cinder/builtins.py`, registered right
after `_is_deficient` (search for `def _is_deficient`) — it's the
natural value-returning sibling of the `is_perfect_number`/
`is_abundant`/`is_deficient` cluster, all three of which already do
their own trial-division-to-`sqrt(n)` walk over divisor pairs and
discard the individual divisors, keeping only their sum. This is a
fresh breadth task queued after task 5's depth work (destructuring
function parameters) per `PROJECT.md`'s breadth-vs-depth policy,
restarting the alternation after two depth tasks (3, 5) sandwiched a
single breadth task (4) between them.

`divisors(n)` returns the sorted list of every positive integer that
evenly divides `n`, including `1` and `n` itself. Mirror
`_is_perfect_number`'s exact trial-division shape (loop `divisor` from
`2` to `math.isqrt(value)` inclusive, and for each exact divisor
collect both `divisor` and its complement `value // divisor` when they
differ) but collect into a list instead of summing, seed the list with
`1` the same way `_is_perfect_number` seeds `total = 1` (skip that seed
when `value == 1`, since `1`'s only divisor is itself, not `1` twice),
and `sorted(...)` the result before returning — the trial-division walk
does not yield divisors in sorted order (it finds small/large pairs
together), so sorting is required, not cosmetic.

Model the arity/type-checking on `_is_perfect_number`'s structure: reuse
`_require_arity("divisors", arguments, 1, line, column)` and
`_require_int("divisors", arguments[0], line, column)`. Unlike
`is_perfect_number`/`is_abundant`/`is_deficient` (which answer `false`
for `value < 1` or `value < 2`), `n < 1` has no valid divisor list —
`0` is divisible by everything and negative numbers don't fit the
"positive divisors" contract — so raise a domain error instead of
returning an empty list, mirroring `_log`'s own type-vs-domain-error
split (search `def _log`): a non-int argument is a type error via
`_require_int`, but `n < 1` is a separate domain error raised
afterward, `CinderRuntimeError` matching `"divisors() requires a
positive integer, domain error"`.

Acceptance criteria:
- `divisors(6);` is `[1, 2, 3, 6]` — the textbook case.
- `divisors(1);` is `[1]` — the one-element edge case, no doubled `1`.
- `divisors(13);` is `[1, 13]` — a prime has exactly two divisors.
- `divisors(28);` is `[1, 2, 4, 7, 14, 28]` — a perfect number's
  divisors (excluding `28` itself sum to `28`, confirming this shares
  the same divisor set `is_perfect_number(28)` already validates as
  `true`).
- `divisors(100);` is `[1, 2, 4, 5, 10, 20, 25, 50, 100]` — a larger
  composite with several divisor pairs, confirming results come back
  sorted rather than in trial-division-discovery order.
- `divisors(0);` and `divisors(-6);` both raise `CinderRuntimeError`
  matching `"divisors() requires a positive integer, domain error"`.
- `divisors(3.0);` (float) raises `CinderRuntimeError` matching
  `"divisors() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `divisors(true);` (bool) raises `CinderRuntimeError` matching
  `"divisors() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_deficient`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `divisors` added near `is_perfect_number`/`is_abundant`/
`is_deficient`, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
