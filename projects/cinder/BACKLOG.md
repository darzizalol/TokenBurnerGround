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

## 1. Standard library: `is_power_of_two` — power-of-two predicate via bit trick

Build: add `is_power_of_two(n)` to `cinder/builtins.py`, registered
right after `is_composite` (search for `def _is_composite`) in the
integer-property predicate cluster. A
power of two is `1, 2, 4, 8, 16, ...` — the classic bit-trick
predicate: for `n > 0`, `n` is a power of two exactly when `n & (n -
1) == 0` (a power of two has exactly one set bit, so subtracting one
flips every bit below it, and the two share no set bits — Cinder's
`&` operator, already used elsewhere in the language, makes this a
one-line check without any loop or `log2`). This is the first
builtin in the cluster to use Cinder's own bitwise operators rather
than pure arithmetic, a small nod toward exercising more of the
language surface, not just adding to it.

Model the arity/type-checking on `_is_prime`'s structure (search for
`def _is_prime`): reuse `_require_arity("is_power_of_two", arguments,
1, line, column)` and `_require_int("is_power_of_two", arguments[0],
line, column)` (the same helper the rest of the cluster uses, defined
at `cinder/builtins.py:157-162`). For the computation: `if value < 1:
return False` (the bit trick only holds for positive `n` — `0 & -1`
is `0` in Python's arbitrary-precision two's-complement semantics,
which would wrongly satisfy the check, so `0` and every negative
number must be excluded up front), otherwise `return (value & (value
- 1)) == 0`.

Acceptance criteria:
- `is_power_of_two(1);` is `true` — `2^0`.
- `is_power_of_two(2);` is `true`, `is_power_of_two(4);` is `true`,
  `is_power_of_two(1024);` is `true`.
- `is_power_of_two(3);` is `false`, `is_power_of_two(6);` is `false`,
  `is_power_of_two(1023);` is `false` — one less than a power of two,
  confirms the bit trick isn't off-by-one.
- `is_power_of_two(0);` is `false` — excluded explicitly, not merely
  by coincidence of the bit trick.
- `is_power_of_two(-4);` is `false` — negative input, no domain
  error, matching the cluster's non-positive-input convention.
- `is_power_of_two(2251799813685248);` (2^51, a bignum-adjacent case)
  is `true` — confirms the bit trick works past small-int ranges.
- `is_power_of_two(3.0);` (float, even though numerically whole)
  raises `CinderRuntimeError` matching `"is_power_of_two() requires
  an int, got float"` — no implicit float-to-int coercion, matching
  the rest of the cluster.
- `is_power_of_two(true);` (bool) raises `CinderRuntimeError`
  matching `"is_power_of_two() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_composite`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_power_of_two` added near `is_perfect_square`/
`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 2. Language: block-bodied arrow functions `(params) => { ... }` and `x => { ... }`

Build: extend both arrow-function forms — parenthesized (`_try_arrow_function`
in `cinder/parser.py`, from `feat/20260808-arrow-functions`, PR #205) and
bare single-identifier (landed in `feat/20260808-bare-arrow-fn`, PR #208, in
`_primary`'s `IDENTIFIER` branch) — to accept a block body, `{ <statement>* }`,
as an alternative to the current expression-only body. Both prior arrow-function
tasks deliberately deferred this ("no block-bodied form"); this is a
language-depth task, not another stdlib predicate, following directly from
`is_composite` (landed, PR #209) and `is_power_of_two` (task 1 above) per
`PROJECT.md`'s breadth-vs-depth policy — two single-builtin predicate tasks
queued back-to-back is the signal to inject depth again. Concrete motivation
for scoping it now: any
arrow-function callback needing more than one statement (log a value before
returning, compute an intermediate result, branch on a condition) currently
has no option but to fall back to the verbose `fn` form, defeating the
sugar's purpose.

Unlike the expression-bodied form, a block body does **not** implicitly
return its last expression — the caller must write `return` explicitly,
exactly like an ordinary `fn` body. Cinder has no implicit-return blocks
anywhere else in the language, and arrow functions should not be the first.
A block-bodied arrow is simply "the same `{ ... }` body an ordinary `fn`
expression already accepts, spelled after `=>` instead of after a parameter
list."

In `_try_arrow_function`: after consuming `FAT_ARROW`, check
`self._check(TokenType.LBRACE)`. If true, parse the body the same way
`_fn_params_and_body` does — call `self._block()` wrapped in its
`_fn_depth`/`_loop_labels` bookkeeping (search `def _fn_params_and_body`),
so `return`/`break`/`continue` validity inside the block matches an
ordinary function body — instead of the current unconditional `body_expr =
self._assignment()` / synthetic-`ReturnStmt` wrap. If false, keep the
existing expression-body path unchanged. Apply the identical
`LBRACE`-check-and-branch at the bare-identifier site (PR #208), so
both forms share the same body-parsing behavior. Consider factoring the
shared "parse either an expression body (wrapped in a synthetic return) or
a block body" logic into one small helper called from both sites, but only
if it's a clean fit — do not force an abstraction that complicates either
call site.

This task also retires `test_arrow_block_body_not_supported` in
`tests/test_parser.py` (search for it) and PR #208's equivalent
bare-identifier-form assertion — replace both with tests asserting the
block body now parses and executes correctly rather than raising
`ParseError`.

Acceptance criteria:
- `let f = (x) => { let y = x * 2; return y; }; f(5);` is `10`.
- `let f = x => { let y = x * 2; return y; }; f(5);` is `10` —
  bare-identifier form gets the same treatment.
- `let f = () => { return 42; }; f();` is `42` — zero-param block body.
- `let f = (a, b) => { if (a > b) { return a; } return b; }; f(3, 7);`
  is `7` — multi-statement/control-flow body, confirming the block
  reuses ordinary statement parsing, not just a single `return`.
- `let f = (x) => { x * 2; }; f(5);` is `nil` — a block body with no
  explicit `return` falls off the end like any other function; it does
  **not** implicitly return the last expression's value. Confirms no
  implicit-return behavior was accidentally introduced.
- `[1, 2, 3].map(x => { return x * x; });` is `[1, 4, 9]` — works as a
  callback the same way expression-bodied arrows already do.
- `let adder = (x) => { return (y) => { return x + y; }; }; adder(3)(4);`
  is `7` — nested block-bodied arrows, closures still work.
- Expression-bodied arrows (both forms) are completely unaffected:
  `let f = (x) => x * 2; f(5);` is `10` and `let g = x => x * 2; g(5);`
  is `10` still parse/evaluate exactly as before — this task only adds
  a new branch when `{` follows `=>`, it must not change the existing
  expression-body path or its own tests.
- `break`/`continue` inside a loop inside a block-bodied arrow's body
  resolve to that arrow's own loop, not an enclosing one — confirms
  `_loop_labels` bookkeeping is threaded through the same way
  `_fn_params_and_body` threads it for ordinary `fn` bodies.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_try_arrow_function`, and
`_primary`'s `IDENTIFIER` branch added by PR #208), `tests/test_parser.py`
(replace `test_arrow_block_body_not_supported` and PR #208's equivalent
bare-identifier assertion with positive-case tests), `tests/
test_interpreter.py` (execution-level tests for multi-statement bodies).
Once merged, `README.md`'s arrow-function bullet and `PROJECT.md`'s
roadmap paragraph need updating — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Standard library: `is_palindrome_list` — list palindrome predicate

Build: add `is_palindrome_list(list)` to `cinder/builtins.py`, registered
right after `is_power_of_two` (search for `def _is_power_of_two` — by the
time this task is claimed, tasks 1-2 above will have landed and shifted
line numbers). This extends the "reads the same forwards and backwards"
predicate family — `is_palindrome` for strings, `is_palindrome_number` for
integers (search either) — to its third and final natural domain: lists,
e.g. `[1, 2, 1]` or `["a", "b", "a"]`.

Do **not** implement this as `value == value[::-1]`. List elements can be
unhashable nested lists/maps, and Python's own `==` on those follows
Python's equality rules, not Cinder's — the codebase already has a
dedicated deep-equality helper for exactly this reason. Search for
`values_equal` (imported from `cinder.interpreter`, already used by
`_is_unique`/`_is_permutation`/`_remove`/`_index_of`-style helpers) and
use it to compare `value[i]` against `value[len(value) - 1 - i]` for each
`i` in the first half of the list, short-circuiting `False` on the first
mismatch; an empty list or single-element list is trivially `True`.

Model the arity/type-checking on `_is_sorted`'s or `_is_unique`'s
structure (search for `def _is_unique`): reuse
`_require_arity("is_palindrome_list", arguments, 1, line, column)`, then
check `isinstance(value, list)` directly and raise `CinderRuntimeError`
matching `"is_palindrome_list() requires a list, got {type}"` on a
mismatch (mirroring `_is_unique`'s own error message shape) — there is no
existing `_require_list` helper, so write the inline check the same way
`_is_unique`/`_is_sorted` already do rather than adding a new shared
helper for a single caller.

Acceptance criteria:
- `is_palindrome_list([1, 2, 1]);` is `true`.
- `is_palindrome_list([1, 2, 3]);` is `false`.
- `is_palindrome_list([]);` is `true` — empty list, vacuously a
  palindrome, matching `is_palindrome`'s own empty-string convention.
- `is_palindrome_list([1]);` is `true` — single element.
- `is_palindrome_list(["a", "b", "b", "a"]);` is `true` — even length,
  strings not just numbers.
- `is_palindrome_list([[1, 2], 3, [1, 2]]);` is `true` — nested lists as
  elements, confirming `values_equal` (deep equality) is used rather
  than a bare `==`/identity comparison that could wrongly reject
  structurally-equal-but-distinct nested values.
- `is_palindrome_list("abcba");` (a string, not a list) raises
  `CinderRuntimeError` matching `"is_palindrome_list() requires a list,
  got string"` — this predicate is list-only; `is_palindrome` already
  covers strings, so there is no fallback/coercion here.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_power_of_two`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_palindrome_list` added near `is_palindrome`/
`is_palindrome_number`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `is_coprime` — two-integer coprimality predicate

Build: add `is_coprime(a, b)` to `cinder/builtins.py`, registered right
after `is_divisible` (search for `def _is_divisible`, currently around
line 1156) — the other two-argument member of the integer-property
predicate cluster (`is_even`/`is_odd`/`is_divisible`/`is_prime`/
`is_composite`). Two integers are coprime (relatively prime) when their
only common positive divisor is `1`, i.e. `gcd(a, b) == 1`. Python's
stdlib `math` module is already imported in `builtins.py` (used by
`_gcd`, `_is_perfect_square`, `_factorial`, etc.) and its `math.gcd`
handles negative and zero arguments the same way this task needs (always
returns a non-negative result, e.g. `math.gcd(-12, 18) == 6`,
`math.gcd(0, 0) == 0`) — call `math.gcd` directly rather than routing
through the existing `gcd()` builtin's own Cinder-level function
(`_gcd`), since that would mean re-deriving/re-validating arguments that
have already been validated here.

Model the arity/type-checking on `_is_divisible`'s structure (search for
`def _is_divisible`): reuse `_require_arity("is_coprime", arguments, 2,
line, column)` and `_require_int("is_coprime", arguments[N], line,
column)` for each of the two arguments (the same helper the rest of the
cluster uses). Unlike `is_divisible`, there is no "must not be zero"
guard to add — `math.gcd(0, n)` is well-defined (`abs(n)`), so
`is_coprime(0, n)` is simply `false` for any nonzero `n` and
`is_coprime(0, 0)` is `false` (`gcd(0, 0) == 0 != 1`), both handled
naturally by the plain `== 1` check with no special-casing.

Acceptance criteria:
- `is_coprime(8, 15);` is `true` — no common factor.
- `is_coprime(12, 18);` is `false` — share a factor of `6`.
- `is_coprime(1, 5);` is `true` — `1` is coprime with everything,
  including itself: `is_coprime(1, 1);` is `true`.
- `is_coprime(0, 5);` is `false`, `is_coprime(0, 0);` is `false` — zero
  shares every divisor with any number (and with itself), so it is
  never coprime with anything, including `0`.
- `is_coprime(-8, 15);` is `true`, `is_coprime(-12, 18);` is `false` —
  negative input, sign doesn't affect the shared-divisor question.
- `is_coprime(17, 17);` is `false` — a number is only coprime with
  itself when that number is `1`.
- `is_coprime(3.0, 5);` (float) raises `CinderRuntimeError` matching
  `"is_coprime() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the cluster.
- `is_coprime(3, true);` (bool as second argument) raises
  `CinderRuntimeError` matching `"is_coprime() requires an int, got
  bool"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_divisible`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_coprime` added near `is_divisible`/`is_prime`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 5. Language: safe navigation bracket indexing `obj?.[expr]`

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
