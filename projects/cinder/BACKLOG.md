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

## 1. Standard library: `factorial` — numeric builtin rounding out `pow`/`gcd`/`lcm`

Build: add `factorial(n)` to `cinder/builtins.py`, a numeric builtin
sitting next to `pow`/`gcd`/`lcm` (`cinder/builtins.py:1254-1363`). Register
it right after `lcm` — it belongs with that small cluster of
number-theoretic builtins, not the string/list families above or below it.

Model the arity/type-checking on `_gcd`/`_lcm`'s structure
(`cinder/builtins.py:1342-1363`): reuse `_require_arity("factorial",
arguments, 1, line, column)`, then check `arguments[0]` is an `int` and
not a `bool` (same `isinstance(value, int) and not isinstance(value,
bool)` guard `_gcd`/`_lcm` use per-argument), raising `CinderRuntimeError`
with `f"factorial() requires an int, got {type_name(value)}"` on failure.
Separately, negative input is a domain error, not a type error — mirror
`_log`'s own "requires a number" vs. "requires a positive number, domain
error" split (`cinder/builtins.py` around `_log`, two distinct checks, two
distinct messages): raise `CinderRuntimeError` with
`"factorial() requires a non-negative int, domain error"` when
`value < 0`. For the computation itself, delegate directly to Python's
`math.factorial(value)` (already imported — `builtins.py:17` has `import
math`) rather than hand-rolling a loop; Cinder ints are Python ints, so
there's no overflow to guard (unlike `pow()`, which does need its own
overflow/complex-result guards for float bases/exponents — `factorial`
only ever takes a non-negative int, so none of that machinery applies
here).

Acceptance criteria:
- `factorial(0);` is `1`.
- `factorial(1);` is `1`.
- `factorial(5);` is `120`.
- `factorial(10);` is `3628800`.
- `factorial(20);` is `2432902008176640000` — confirms no overflow/precision
  loss on a result too large for a 64-bit float to represent exactly.
- `factorial(-1);` raises `CinderRuntimeError` matching
  `"factorial() requires a non-negative int, domain error"`.
- `factorial(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"factorial() requires an int, got
  float"` — no implicit float-to-int coercion, matching how `gcd`/`lcm`
  reject floats today.
- `factorial(true);` (bool, which is a Python `int` subclass) raises
  `CinderRuntimeError` matching `"factorial() requires an int, got
  bool"` — same bool-exclusion `gcd`/`lcm`/`is_even`/`is_odd` already
  apply.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `gcd`/`lcm`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet needs
`factorial` added near `pow`/`gcd`/`lcm`, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_pangram` — alphabet-coverage string predicate

Build: add `is_pangram(string)` to `cinder/builtins.py`, a string
predicate testing whether `string` contains every letter of the English
alphabet at least once (case-insensitive — `"a"` and `"A"` both count
toward the same letter), sitting near `is_palindrome`/`is_anagram`/
`is_permutation` (`cinder/builtins.py:622-660`) in the string/list
multiset-predicate cluster rather than the `is_alpha`/`is_digit`/.../
`is_ascii` content-predicate family (`:683-731`): unlike that family,
`is_pangram` isn't a bare delegation to a single `str.is*()` Python
method — Python has no built-in for this, so the body needs actual
logic. Register right after `is_permutation` (which now sits right
after `is_anagram`, having landed since this task was first scoped),
ahead of `is_upper`.

Model the arity/type-checking on `_is_palindrome`'s structure
(`cinder/builtins.py:622-629`): reuse `_require_arity("is_pangram",
arguments, 1, line, column)`, check `arguments[0]` is a `str` (raising
`CinderRuntimeError` with `f"is_pangram() requires a string, got
{type_name(value)}"` on a non-string argument, matching the exact
wording pattern `is_palindrome`/`is_alpha`/etc. all use), then compute
the body as `set(string.ascii_lowercase) <= set(value.lower())` (`string`
module already imported for `ascii_lowercase`/`ascii_uppercase` elsewhere
in this file — check the existing `import string` at the top before
adding a duplicate; if absent, `set("abcdefghijklmnopqrstuvwxyz")` is an
equally fine literal, no need to add a new import for one character
class). Non-letter characters (digits, punctuation, whitespace) are
simply ignored by the set-membership check — no special-casing needed.

Acceptance criteria:
- `is_pangram("The quick brown fox jumps over the lazy dog");` is
  `true` — the canonical English pangram.
- `is_pangram("Pack my box with five dozen liquor jugs");` is `true` —
  a second, shorter canonical pangram, confirming the check isn't
  accidentally tied to the first example's specific length/casing.
- `is_pangram("hello world");` is `false` — missing most letters.
- `is_pangram("");` is `false` — empty string, matching the "empty is
  false" rule every other content-style predicate in this file follows.
- `is_pangram("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG");` is
  `true` — all-uppercase input, confirming the check is
  case-insensitive.
- `is_pangram("abcdefghijklmnopqrstuvwxyz");` is `true` — exactly the
  26 letters, no repeats, no filler text.
- `is_pangram(5);` (non-string argument) raises `CinderRuntimeError`
  matching `"is_pangram() requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_anagram`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_pangram` added near `is_palindrome`/`is_anagram`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `digit_sum` — sum of an integer's decimal digits

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

## 4. Language: list comprehensions — `[expr for x in iterable]` / `[expr for x in iterable if cond]`

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
