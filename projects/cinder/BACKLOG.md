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

## 1. Language: safe navigation bracket indexing `obj?.[expr]` [claimed 2026-08-08T19:40:16Z]

Build: extend the existing safe navigation operator — currently
dot-only (`m?.key`, short-circuits to `nil` when `m` is `nil` instead of
raising, single level only; search `QUESTION_DOT` in `cinder/parser.py`)
— to also accept a bracket form, `obj?.[expr]`, the same relationship
plain `.`/`[...]` already have for non-optional access (`_finish_dot`
vs. `_finish_index` in `cinder/parser.py`). Concrete motivation: today
`?.` only works for map string-key access shaped like an identifier
(`m?.name`); it has no answer for a computed key (`m?.[key_var]`) or for
a possibly-`nil` list (`xs?.[0]`), both of which currently have no
optional-chaining option at all and must fall back to a manual `xs ==
nil ? nil : xs[0]` ternary.

This is a smaller task than it looks: the AST node and interpreter side
already do all the work generically. `OptionalIndex` (`cinder/
ast_nodes.py`) already carries an arbitrary `index: Expr`, not just an
identifier-derived key — `_finish_optional_dot` (`cinder/parser.py`)
just happens to always build that index from an `IDENTIFIER` token
today. `_evaluate_optional_index` (`cinder/interpreter.py`, search `def
_evaluate_optional_index`) already short-circuits to `nil` on a `nil`
receiver and otherwise delegates to `_index_get`, the same helper
`_evaluate_index` uses for plain `[...]` access — `_index_get` already
handles both lists (with negative-index normalization) and maps. So
**no interpreter changes are needed at all**; this is a parser-only
task.

In `_finish_optional_dot` (`cinder/parser.py`, search `def
_finish_optional_dot`): after consuming the `?.` token, check
`self._check(TokenType.LBRACKET)` first. If true, consume `[`, parse the
index the same way `_finish_index` does for a plain (non-slice) index —
call `self._ternary()` for the index expression, then consume `]` — and
return `OptionalIndex(obj, index, dot.line, dot.column)`. If false, fall
through to the existing identifier-based path unchanged. Do **not**
support slicing in the bracket form (`obj?.[a:b]`) — plain index only;
if a `:` follows the index expression where `]` is expected, let the
existing `_consume(TokenType.RBRACKET, ...)` call raise its normal
`ParseError`, the same way an unexpected token anywhere else does. No
change is needed to keep `obj?.[expr]` out of assignment position:
`_assignment` (`cinder/parser.py`) already only special-cases
`Identifier`/`Index`/`ListLiteral` as valid targets and raises
`"invalid assignment target"` for anything else, so an `OptionalIndex`
built from the new bracket form is rejected automatically, exactly like
the existing dot form already is (see
`test_optional_dot_access_assignment_raises_parse_error` in
`tests/test_parser.py`).

Acceptance criteria:
- `let m = {"a": 1}; m?.["a"];` is `1` — computed-key bracket form on a
  non-nil map.
- `let m = nil; m?.["a"];` is `nil` — short-circuits on `nil`, same as
  the existing dot form.
- `let xs = [10, 20, 30]; xs?.[1];` is `20` — bracket form works on
  lists, which the dot form never could (`xs?.1` isn't valid syntax).
- `let xs = nil; xs?.[0];` is `nil` — short-circuits for lists too.
- `let key = "a"; let m = {"a": 1}; m?.[key];` is `1` — the index is an
  arbitrary expression, not just a literal, confirming this isn't just
  string-literal sugar.
- `let m = {"a": 1}; m?.[key] ?? "default";` composes with `??`, same
  as the dot form already does.
- `let xs = [1, 2, 3]; xs?.[-1];` is `3` — negative-index normalization
  still applies, since this goes through the same `_index_get` plain
  indexing already uses.
- `let m = {"a": 1}; m?.["a"] = 2;` raises `ParseError` ("invalid
  assignment target") — bracket-form safe navigation is read-only, same
  as the dot form.
- `let m = {"a": 1}; m?.[0:1];` raises `ParseError` — no slicing through
  the optional-bracket form.
- Existing dot-form safe navigation (`m?.key`) and its own tests are
  completely unaffected — this task only adds a new branch when `[`
  follows `?.`.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_finish_optional_dot`), `tests/
test_parser.py` (extend the `shape()`-based AST assertions alongside
`test_optional_dot_access_desugars_to_optional_index`), `tests/
test_interpreter.py` (execution-level tests for the map/list/nil/
negative-index cases above). Once merged, `README.md`'s safe navigation
bullet needs `obj?.[expr]` mentioned alongside `m?.key`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_fibonacci` — Fibonacci-membership predicate

Build: add `is_fibonacci(n)` to `cinder/builtins.py`, registered right
after `is_coprime` (search for `def _is_coprime` — by the time this task
is claimed, task 1 above will have landed and shifted line numbers).
This is a fresh breadth task queued after task 1's depth work (safe
navigation bracket indexing) per `PROJECT.md`'s breadth-vs-depth policy.
A non-negative integer `n` is a Fibonacci number (`0, 1, 1, 2, 3, 5, 8,
13, ...`) exactly when `5n² + 4` or `5n² - 4` is a perfect square — do
**not** implement this by iterating/generating the sequence up to `n`,
which would be needlessly slow for large `n` given Cinder's
arbitrary-precision ints. Use `math.isqrt` the same exact-integer way
`_is_perfect_square` already does (search for `def _is_perfect_square`)
to test each candidate: compute `r = math.isqrt(candidate)` and check
`r * r == candidate`.

Model the arity/type-checking on `_is_perfect_square`'s or
`_is_coprime`'s structure: reuse `_require_arity("is_fibonacci",
arguments, 1, line, column)` and `_require_int("is_fibonacci",
arguments[0], line, column)`. Negative input is not an error — mirror
`_is_perfect_square`'s own convention of answering `false` on negative
input rather than raising, since "is this integer a Fibonacci number" is
a well-defined question for negative integers too (the answer is simply
always `false`, since the sequence is only ever defined for `n >= 0`).

Acceptance criteria:
- `is_fibonacci(0);` is `true`, `is_fibonacci(1);` is `true` — both
  appear in the sequence (`1` appears twice, at index 1 and 2, but the
  predicate only cares about membership).
- `is_fibonacci(2);` is `true`, `is_fibonacci(3);` is `true`,
  `is_fibonacci(5);` is `true`, `is_fibonacci(8);` is `true`,
  `is_fibonacci(13);` is `true`, `is_fibonacci(144);` is `true`.
- `is_fibonacci(4);` is `false`, `is_fibonacci(6);` is `false`,
  `is_fibonacci(100);` is `false` — non-members between/around real
  Fibonacci numbers.
- `is_fibonacci(-5);` is `false` — negative input answers `false` rather
  than raising, matching `is_perfect_square`'s convention.
- `is_fibonacci(832040);` is `true` — a larger, real Fibonacci number
  (F(30)), confirming the closed-form test rather than an unrolled
  lookup table of small cases.
- `is_fibonacci(3.0);` (float) raises `CinderRuntimeError` matching
  `"is_fibonacci() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `is_fibonacci(true);` (bool) raises `CinderRuntimeError` matching
  `"is_fibonacci() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_coprime`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_fibonacci` added near `is_perfect_square`/`is_armstrong`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_happy_number` — happy-number recurrence predicate

Build: add `is_happy_number(n)` to `cinder/builtins.py`, registered
right after `is_fibonacci` (search for `def _is_fibonacci` — by the
time this task is claimed, tasks 1-2 above will have landed and shifted
line numbers). A "happy number" is defined by a recurrence: replace `n`
with the sum of the squares of its decimal digits, and repeat; `n` is
happy if this process eventually reaches `1`, unhappy if it instead
falls into a cycle that never includes `1` (every non-happy positive
integer provably cycles rather than diverging — the classic example is
`4 -> 16 -> 37 -> 58 -> 89 -> 145 -> 42 -> 20 -> 4`, repeating forever).
Detect the cycle with a `set` of previously-seen values: loop computing
the next value, and at each step return `True` the moment the value
becomes `1`, or return `False` the moment the value repeats a
previously-seen one (add each new value to the set before computing the
next). Do **not** cap the loop at a fixed iteration count as a
cycle-detection substitute — that risks misclassifying a slow-to-cycle
unhappy number as happy (or vice versa) if the cap is too low; the
seen-set approach is exact and terminates on every input since the
digit-square-sum of any number below `10^k` is bounded, forcing a
revisit within finitely many steps.

Model the arity/type-checking on `_is_fibonacci`'s or
`_is_perfect_square`'s structure: reuse `_require_arity("is_happy_number",
arguments, 1, line, column)` and `_require_int("is_happy_number",
arguments[0], line, column)`. Negative input is not an error — mirror
`_is_perfect_square`'s own convention of answering `false` on negative
input rather than raising, since the digit-square-sum recurrence is
only conventionally defined for non-negative integers.

Acceptance criteria:
- `is_happy_number(1);` is `true` — the base case, zero steps needed.
- `is_happy_number(7);` is `true` — `7 -> 49 -> 97 -> 130 -> 10 -> 1`.
- `is_happy_number(19);` is `true` — a slightly longer chain:
  `19 -> 82 -> 68 -> 100 -> 1`.
- `is_happy_number(4);` is `false` — falls into the canonical
  `4 -> 16 -> 37 -> 58 -> 89 -> 145 -> 42 -> 20 -> 4` cycle.
- `is_happy_number(2);` is `false`, `is_happy_number(3);` is `false` —
  both eventually reach the same `4`-cycle.
- `is_happy_number(0);` is `false` — `0` maps to itself
  (`0 -> 0`), an immediate one-value cycle that never includes `1`.
- `is_happy_number(-7);` is `false` — negative input answers `false`
  rather than raising, matching `is_perfect_square`'s convention.
- `is_happy_number(97);` is `true` — a larger multi-digit happy number,
  confirming the recurrence handles more than one digit-squaring pass.
- `is_happy_number(3.0);` (float) raises `CinderRuntimeError` matching
  `"is_happy_number() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `is_happy_number(true);` (bool) raises `CinderRuntimeError` matching
  `"is_happy_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_fibonacci`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_happy_number` added near `is_perfect_square`/`is_fibonacci`,
and `PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task. This is the second breadth task queued back-to-back with
`is_fibonacci`; per `PROJECT.md`'s breadth-vs-depth policy, the next
grooming pass after this task is claimed should inject a language-depth
task rather than a third predicate.

---

## 4. Language: numeric literal underscores (`1_000_000`, `0xFF_FF`, `3.14_159`)

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

## 5. Standard library: `is_triangular` — triangular-number predicate

Build: add `is_triangular(n)` to `cinder/builtins.py`, registered right
after `is_happy_number` (search for `def _is_happy_number` — by the
time this task is claimed, tasks 1-4 above will have landed and shifted
line numbers). A non-negative integer `n` is a triangular number (`0,
1, 3, 6, 10, 15, 21, ...`, the sum `1 + 2 + ... + k` for some `k >= 0`)
exactly when `8n + 1` is a perfect square — the same closed-form,
`math.isqrt`-based exact-integer technique `is_fibonacci` and
`_is_perfect_square` already use (compute `r = math.isqrt(candidate)`
and check `r * r == candidate`), not an accumulating loop that adds
`1, 2, 3, ...` until it reaches or passes `n`. This is a fresh breadth
task queued after task 4's depth work (numeric literal underscores) per
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

## 6. Language: destructuring loop variables in list/map comprehensions

Build: extend list comprehensions (`[expr for x in iterable]`) and map
comprehensions (`{k: v for x in iterable}`) to accept a list-destructuring
loop variable in place of the single identifier, mirroring the plain
`for`-loop's own `for [k, v] in items(m) { ... }` support (`ForStmt`'s
`names`/`rest` fields, `cinder/ast_nodes.py`) — today `for [k, v] in
items(m) { ... }` works as a statement but `[k + v for [k, v] in
items(m)]` has no comprehension equivalent and must fall back to a
full statement-form loop building a list by hand with `push`. This is a
depth task queued after task 5's breadth work (`is_triangular`) per
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
