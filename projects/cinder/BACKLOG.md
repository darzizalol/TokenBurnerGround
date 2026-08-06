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

## 1. Standard library: `digit_sum` — sum of an integer's decimal digits

Build: add `digit_sum(n)` to `cinder/builtins.py`, a numeric builtin
sitting right after `is_prime` (`cinder/builtins.py:1137-1145`) in the
integer-property predicate cluster (`is_even`/`is_odd`/`is_divisible`/
`is_prime`, `cinder/builtins.py:1114-1145`) — it isn't itself a
predicate (it returns a number, not `true`/`false`), but it belongs
next to that cluster rather than next to `pow`/`gcd`/`lcm`/`factorial`
further down the file, since it shares their "one property of a single
int" shape rather than the two-argument number-theoretic shape of that
farther-down group.

Model the arity/type-checking on `_is_prime`'s structure
(`cinder/builtins.py:1137-1139`): reuse `_require_arity("digit_sum",
arguments, 1, line, column)` and `_require_int("digit_sum",
arguments[0], line, column)` (the same helper `is_even`/`is_odd`/
`is_divisible`/`is_prime` already use — defined at
`cinder/builtins.py:157-162`, raises `CinderRuntimeError` with
`f"{name}() requires an int, got {type_name(value)}"` and rejects `bool`
since `bool` is a Python `int` subclass, so no separate bool-exclusion
check is needed here). For the computation, take the absolute value
first (`digit_sum` is a property of a number's magnitude, not its sign —
matching how `factorial`'s task above treats domain errors as distinct
from type errors, `digit_sum` sidesteps the question entirely by
normalizing sign away rather than rejecting negative input), then sum
the digits: `sum(int(digit) for digit in str(abs(value)))` is sufficient
— no need for a hand-rolled `% 10` / `// 10` loop.

Acceptance criteria:
- `digit_sum(0);` is `0`.
- `digit_sum(5);` is `5`.
- `digit_sum(123);` is `6`.
- `digit_sum(999);` is `27`.
- `digit_sum(-123);` is `6` — sign is ignored, same magnitude as `123`.
- `digit_sum(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"digit_sum() requires an int, got
  float"` — no implicit float-to-int coercion, matching `is_even`/
  `is_odd`/`is_prime`.
- `digit_sum(true);` (bool) raises `CinderRuntimeError` matching
  `"digit_sum() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_prime`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `digit_sum` added near `is_even`/`is_odd`/`is_divisible`/
`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 2. Language: list comprehensions — `[expr for x in iterable]` / `[expr for x in iterable if cond]`

Build: teach the list-literal grammar a comprehension form, so
`[x * 2 for x in range(5)]` becomes `[0, 2, 4, 6, 8]` without spelling out
`map`/`filter` by hand. This is a **language** task (grammar + AST +
interpreter), the first one in seven cycles — the backlog has been all
stdlib predicates lately (`is_anagram`/`is_permutation`/`is_numeric`
landed, `is_blank`/`factorial`/`is_pangram`/`digit_sum` queued above);
`PROJECT.md`'s own principle is to mix language depth in periodically
rather than run either track in one long block, and today there is no
comprehension syntax at all — only the eager `map`/`filter` builtins,
which need an intermediate function value even for a one-line
transform.

Scope deliberately narrow, matching how other single-session language
features here have shipped incrementally (e.g. destructuring assignment
landed flat/non-nested first, `{a,b} = expr` as a separate later task):
- Exactly one `for` clause, one loop variable — a plain `IDENTIFIER`
  only, not the `[a, b]`/`{a, b}` destructuring patterns `ForStmt`
  supports (`cinder/ast_nodes.py:304-312`, `names`/`rest` fields) — those
  are a plausible future follow-up, not this task.
- At most one optional trailing `if <cond>` filter clause.
- No nested `for` clauses (no `[x for x in a for y in b]`).
- List comprehensions only — no map-literal comprehension counterpart
  (`{k: v for ...}`) in this task.

Grammar/parsing: add a new frozen dataclass `ListComprehension` to
`cinder/ast_nodes.py` (near `ListLiteral`) with fields `element: Expr`,
`var_name: str`, `iterable: Expr`, `condition: "Expr | None"`, `line: int`,
`column: int`. In `cinder/parser.py`, `_list_literal`
(`cinder/parser.py:1120-1129`) currently parses the first element via
`_list_element()` then loops on `COMMA`. After parsing that first
element, check `self._check(TokenType.FOR)` (the `FOR` token is already a
keyword — reused here as a lookahead, not repurposed) before checking for
a comma: if present, this is a comprehension, not a plain list — consume
`for`, an `IDENTIFIER` (the loop variable — reject other left-hand shapes
outright, no destructuring in this task), `in`, then `_ternary()` for the
iterable expression; if the next token is `IF`, consume it and parse
another `_ternary()` for the condition; finally consume `]` and return a
`ListComprehension`, skipping the existing comma-loop entirely (a
comprehension can't also have sibling comma-separated elements — `[x for
x in y, z]` is not valid syntax). If `FOR` is not present after the first
element, fall through to the existing comma-loop path unchanged — plain
list literals keep working exactly as today.

Interpreter: in `cinder/interpreter.py`, add a branch (near
`ListLiteral`'s existing handling) for `ListComprehension` that mirrors
`_execute_for`'s iteration shape (`cinder/interpreter.py:484-511`) rather
than reinventing it — same iterable-type dispatch (`dict` keys, or
`list`/`str` elements, else `CinderRuntimeError` with the identical
`"'for'-in loop requires a list, string, or map, got {type_name(...)}"`
message for consistency), and same fresh-child-`Environment`-per-iteration
binding (so a closure created inside the comprehension's element
expression captures that iteration's value, not a shared mutable
variable — the same closure-correctness concern `_execute_for`'s own
comment already documents). For each item: bind `var_name` in the fresh
iteration environment, evaluate `condition` if present and skip the item
when falsy, otherwise evaluate `element` and append the result to the
output list. No `break`/`continue` handling needed — comprehensions have
no loop body statements, just the one element expression.

Acceptance criteria:
- `[x * 2 for x in [1, 2, 3]];` is `[2, 4, 6]`.
- `[x for x in range(10) if x % 2 == 0];` is `[0, 2, 4, 6, 8]` — filter
  clause works.
- `[x for x in [] ];` is `[]` — empty iterable, empty result.
- `[x for x in [1, 2, 3] if x > 10];` is `[]` — filter excludes
  everything, still a valid empty list, not an error.
- `["-" + c for c in "abc"];` is `["-a", "-b", "-c"]` — string iterable
  works the same way `for`-in over a string already does.
- `[k for k in {"a": 1, "b": 2}];` is `["a", "b"]` (order matches
  existing map key iteration order) — map iterable yields keys, same as
  `for`-in over a map.
- A closure captured per-iteration observes that iteration's binding, not
  the last one — e.g. `let fns = [fn() { return x; } for x in [1, 2, 3]];
  print(fns[0]()); print(fns[2]());` prints `1` then `3`, not `3` then
  `3`.
- `[x for x in 5];` (non-iterable) raises `CinderRuntimeError` matching
  `"'for'-in loop requires a list, string, or map, got int"`.
- A plain list literal with a `for`-shaped *element value* still parses
  correctly as a normal list where unambiguous, and existing list-literal
  tests (comma-separated elements, spread `...`, empty `[]`) keep
  passing unmodified — this task only adds a new form, it must not change
  the existing one.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `ListComprehension` dataclass),
`cinder/parser.py` (`_list_literal`, `~line 1120`), `cinder/interpreter.py`
(new evaluate branch near `ListLiteral`'s handling, `_execute_for` as the
iteration-shape reference at `~line 484`), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s language-features
bullet list and `PROJECT.md`'s roadmap paragraph need list comprehensions
moved from backlog to landed, and a map-comprehension follow-up task
(`{k: v for ...}`) is a natural next scope for the Architect to consider
— leave both to the Architect's next grooming pass, not this task.

---

## 3. Language: map comprehensions — `{k: v for x in iterable}` / `{k: v for x in iterable if cond}`

Build: the map-literal counterpart to task 2's list comprehensions —
`{x: x * x for x in [1, 2, 3]}` becomes `{1: 1, 2: 4, 3: 9}`. This task
is scoped to land *after* task 2 (list comprehensions) is merged, since
it deliberately mirrors that task's grammar/AST/interpreter shape rather
than inventing a second one — do not claim this task while task 2 is
still open on the backlog.

Scope, matching task 2's narrowness exactly (same reasoning: single
non-destructuring loop variable, one optional filter, no nesting):
- Exactly one `for` clause, one loop variable — a plain `IDENTIFIER`
  only, no destructuring.
- At most one optional trailing `if <cond>` filter clause.
- No nested `for` clauses.
- Map comprehensions only — this task does not touch list comprehension
  syntax at all, it's purely the `{...}` counterpart.

Grammar/parsing: add a new frozen dataclass `MapComprehension` to
`cinder/ast_nodes.py` (near `MapLiteral`) with fields `key: Expr`,
`value: Expr`, `var_name: str`, `iterable: Expr`, `condition: "Expr |
None"`, `line: int`, `column: int`. In `cinder/parser.py`, `_map_literal`
(`cinder/parser.py:1137-1146`) currently parses the first entry via
`_map_entry()` then loops on `COMMA`; `_map_entry` in turn dispatches to
either `Spread` or `_map_pair()` (`key: value`, `cinder/parser.py:1148-
1158`). After parsing the first pair's `key`/`:`/`value` inside a new
comprehension-aware version of that first-entry parse, check
`self._check(TokenType.FOR)` before checking for a comma: if present,
consume `for`, an `IDENTIFIER`, `in`, then `_ternary()` for the iterable;
if `IF` follows, consume it and parse another `_ternary()` for the
condition; finally consume `}` and return a `MapComprehension` — skip
the existing comma-loop entirely, same as task 2's list version. Note one
wrinkle list comprehensions didn't have: a map entry starts with `key:
value`, two expressions, not one, so the `FOR` lookahead has to happen
after both are parsed, not after a single element like `_list_element()`.
If `FOR` is not present after the first pair, fall through to the
existing comma-loop path unchanged — plain map literals (including
`Spread` entries, which remain untouched by this task) keep working
exactly as today. Reuse the statement-level `{`-disambiguation logic
unchanged (Design principles in `PROJECT.md`) — a comprehension is just
one more shape the speculative map-literal parse attempt can produce, it
doesn't need its own disambiguation branch.

Interpreter: in `cinder/interpreter.py`, add a branch (near
`_evaluate_map_literal`, `cinder/interpreter.py:579-601`) for
`MapComprehension` that mirrors task 2's `ListComprehension` evaluation
(same iterable-type dispatch and fresh-child-`Environment`-per-iteration
binding for closure correctness) but builds a `dict` instead of a
`list`: for each item, bind `var_name` in the fresh iteration
environment, evaluate `condition` if present and skip when falsy,
otherwise evaluate `key` and `value`, validate the key with the existing
`_is_valid_key` check (same `CinderRuntimeError` message
`_evaluate_map_literal` already raises — `f"{type_name(key)} is not a
valid map key"` — reuse it rather than writing a new one), and set
`result[key] = value`. Later keys overwrite earlier ones on collision,
matching plain map-literal semantics (`{"a": 1, "a": 2}` already keeps
the last write).

Acceptance criteria:
- `{x: x * x for x in [1, 2, 3]};` is `{1: 1, 2: 4, 3: 9}`.
- `{x: x for x in range(5) if x % 2 == 0};` is `{0: 0, 2: 2, 4: 4}` —
  filter clause works.
- `{x: x for x in []};` is `{}` — empty iterable, empty result.
- `{k: len(k) for k in ["a", "bb", "ccc"]};` is `{"a": 1, "bb": 2,
  "ccc": 3}` — key and value can be independent expressions.
- `{x: 1 for x in [1, 1, 2]};` is `{1: 1, 2: 1}` — colliding keys
  collapse the same way a hand-written map literal with duplicate keys
  does, not an error.
- A closure captured per-iteration observes that iteration's binding,
  same as task 2's equivalent case (e.g. a comprehension value built
  from `fn() { return x; }` per iteration must not all close over the
  same final `x`).
- `{k: v for k in 5};` (non-iterable) raises `CinderRuntimeError`
  matching `"'for'-in loop requires a list, string, or map, got int"`.
- `{k: k for k in [[1], [2]]};` (unhashable key, a list) raises
  `CinderRuntimeError` matching `"list is not a valid map key"` — same
  message `_evaluate_map_literal` already raises for a plain map literal
  with an unhashable key.
- A plain map literal (including one with `Spread` entries) keeps
  parsing and evaluating exactly as before — existing map-literal tests
  must keep passing unmodified.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `MapComprehension` dataclass),
`cinder/parser.py` (`_map_literal`/`_map_entry`, `~line 1137`),
`cinder/interpreter.py` (`_evaluate_map_literal` as the sibling
reference, `~line 579`), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s language-features
bullet list and `PROJECT.md`'s roadmap paragraph need map comprehensions
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `is_perfect_square` — perfect-square numeric predicate

Build: add `is_perfect_square(n)` to `cinder/builtins.py`, a numeric
builtin sitting right after `digit_sum` (task 1 above — by the time this
task is claimed, tasks 1-4 will have landed and shifted the file's line
numbers, so search for `digit_sum` rather than trusting a specific line)
in the integer-property predicate cluster (`is_even`/`is_odd`/
`is_divisible`/`is_prime`/`digit_sum`, currently
`cinder/builtins.py:1134-1165` before this cycle's other tasks land) —
it belongs there rather than next to `pow`/`gcd`/`lcm`/`factorial`
further down the file, sharing that cluster's "one property of a single
int" shape rather than the two-argument number-theoretic shape of the
farther-down group.

Model the arity/type-checking on `_is_prime`'s structure
(`cinder/builtins.py:1157-1159` before this cycle's other tasks land):
reuse `_require_arity("is_perfect_square", arguments, 1, line, column)`
and `_require_int("is_perfect_square", arguments[0], line, column)` (the
same helper `is_even`/`is_odd`/`is_divisible`/`is_prime`/`digit_sum`
already use, defined at `cinder/builtins.py:157-162` — raises
`CinderRuntimeError` with `f"{name}() requires an int, got
{type_name(value)}"` and rejects `bool` since `bool` is a Python `int`
subclass, so no separate bool-exclusion check is needed here). For the
computation: negative integers are never perfect squares, so return
`False` immediately when `value < 0` (matching `is_prime`'s own
`if value < 2: return False` early-out shape); otherwise use Python's
`math.isqrt(value)` (already imported as `math` at the top of
`builtins.py` — used by `factorial`/`sqrt`/etc., check the existing
`import math` before adding a duplicate) rather than
`math.sqrt(value) ** 0.5`-style floating point, since `math.isqrt`
returns an exact integer floor square root with no rounding-error risk
for large values: `root = math.isqrt(value)` then `return root * root
== value`.

Acceptance criteria:
- `is_perfect_square(0);` is `true` — `0 * 0 == 0`.
- `is_perfect_square(1);` is `true`.
- `is_perfect_square(4);` is `true`.
- `is_perfect_square(16);` is `true`.
- `is_perfect_square(15);` is `false` — between two perfect squares.
- `is_perfect_square(2);` is `false`.
- `is_perfect_square(-4);` is `false` — negative input, never a perfect
  square despite `4` itself being one; no domain error, just `false`,
  matching how `is_prime` returns `false` rather than erroring on
  out-of-domain input like negative numbers or `0`/`1`.
- `is_perfect_square(999999999999999999999999 * 999999999999999999999999);`
  (a large bignum perfect square, well past float precision) is `true`
  — confirms `math.isqrt` is used instead of a `** 0.5` float path that
  would lose precision at this magnitude.
- `is_perfect_square(3.0);` (float, even though numerically whole)
  raises `CinderRuntimeError` matching `"is_perfect_square() requires
  an int, got float"` — no implicit float-to-int coercion, matching
  `is_even`/`is_odd`/`is_prime`/`digit_sum`.
- `is_perfect_square(true);` (bool) raises `CinderRuntimeError`
  matching `"is_perfect_square() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_sum`/
`is_prime`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `is_perfect_square` added near `is_even`/`is_odd`/
`is_divisible`/`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
