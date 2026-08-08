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

## 1. Standard library: `digital_root` — repeated-digit-sum-to-single-digit [claimed 2026-08-08T14:45Z]

Build: add `digital_root(n)` to `cinder/builtins.py`, sitting next to
`digit_sum`/`reverse_int` (search for `def _reverse_int` — by the time
this task is claimed, task 1 above will have landed and shifted line
numbers) rather than the boolean predicate cluster — like `reverse_int`,
it returns a number, not a boolean. The digital root of a non-negative
integer is what you get by repeatedly summing its decimal digits until
a single digit remains (e.g. `38 -> 3+8=11 -> 1+1=2`, so
`digital_root(38) == 2`). Like `digit_sum` (not `reverse_int`), sign is
ignored rather than preserved — a digital root is a magnitude property,
and `digit_sum` already sets this convention for the cluster.

Model the arity/type-checking on `_digit_sum`'s structure (search for
`def _digit_sum`): reuse `_require_arity("digital_root", arguments, 1,
line, column)` and `_require_int("digital_root", arguments[0], line,
column)` (the same helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162`). For the computation, do **not** write a
naive repeated-summing loop — use the well-known O(1) digital-root
identity instead, since Cinder ints are arbitrary-precision and a large
bignum could otherwise force many summing passes: take `value =
abs(value)` first (sign ignored, per above), then `return 0 if value ==
0 else 1 + (value - 1) % 9` (the standard closed-form digital root:
every nonzero value maps to `1..9`, cycling every 9, and `0` is the one
fixed point the modular formula doesn't cover on its own).

Acceptance criteria:
- `digital_root(0);` is `0`.
- `digital_root(5);` is `5` — single digit is its own digital root.
- `digital_root(38);` is `2` — `3+8=11`, then `1+1=2`.
- `digital_root(9999);` is `9` — `9+9+9+9=36`, then `3+6=9`.
- `digital_root(-38);` is `2` — sign ignored, matching `digit_sum`'s
  convention (not `reverse_int`'s sign-preserving one).
- `digital_root(999999999999999999999999);` is `9` — a bignum case
  confirming the closed-form approach handles arbitrary-precision
  input without a slow repeated-summing loop.
- `digital_root(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"digital_root() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of the
  cluster.
- `digital_root(true);` (bool) raises `CinderRuntimeError` matching
  `"digital_root() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `reverse_int`/
`digit_sum`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `digital_root` added near `digit_sum`/
`reverse_int`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 2. Language: bare single-identifier arrow functions `x => expr`

Build: extend arrow-function support (landed in `feat/20260808-arrow-
functions`, PR #205) to the bare single-identifier parameter form —
`x => x * 2` with no parentheses around the single parameter — the
form that task's own scope note explicitly deferred ("no bare
single-identifier form (`x => expr`)"). This is a language-depth task,
not another stdlib predicate: the backlog has run `is_palindrome_number`
and `digital_root` back-to-back since arrow functions landed, and
`PROJECT.md`'s roadmap explicitly calls out watching this balance —
two predicates is enough runway before injecting depth again, per the
same policy that promoted arrow functions to the top of the backlog
last cycle. `is_composite`/`is_power_of_two` (tasks 4-5 below) pick
breadth back up right after this lands.

Unlike the parenthesized form (`(x) => expr`, `_try_arrow_function` in
`cinder/parser.py`), this form needs **no speculative parse/backtrack**
— it is unambiguous with one token of lookahead. Search for
`_try_arrow_function` and `_primary` in `cinder/parser.py`: the
`IDENTIFIER` branch of `_primary` (around where `token.type ==
TokenType.IDENTIFIER` currently just advances and returns an
`Identifier`) is the only place a bare identifier starts an expression,
and `FAT_ARROW` cannot legally follow an identifier anywhere else in
the grammar, so there is nothing to backtrack away from. Use the
existing `self._peek_next()` helper (already used elsewhere in the
parser for lookahead, e.g. the ternary-vs-map-literal `COLON` check) to
test `self._peek_next().type == TokenType.FAT_ARROW` right after
peeking the `IDENTIFIER` token, before deciding whether to fall through
to the plain-`Identifier` case. On a match: consume the identifier
token, consume the `FAT_ARROW` (via `self._consume`, matching
`_try_arrow_function`'s own message style, e.g. `"'=>' after arrow
function parameter"`), then parse the body the same way
`_try_arrow_function` does — `body_expr = self._assignment()`, wrapped
as `Block([ReturnStmt(body_expr, ...)])` — and return a `FnExpr` with
`params=[(name, None)]` (single parameter, no default) and
`rest_param=None`. Reuse `_try_arrow_function`'s exact
Block/ReturnStmt-wrapping shape rather than reinventing it; consider
factoring the shared "wrap a body expression into a one-`return`
`Block`" step into a small helper both call, but only if it does not
complicate either call site — do not force an abstraction that isn't a
clean fit.

Keep this scoped exactly like the parenthesized form: expression-bodied
only. A `{` immediately after `=>` in this form must **not** be treated
as a block body — same out-of-scope boundary
`test_arrow_block_body_not_supported` already documents for the
parenthesized form (search `tests/test_parser.py`); a bare-identifier
arrow with a `{`-body should raise the same way. Do not touch
`_try_arrow_function` itself or the parenthesized-form grammar — this
task only adds the new single-token-lookahead branch in `_primary`'s
`IDENTIFIER` case.

Acceptance criteria:
- `let double = x => x * 2; double(5);` is `10`.
- `let square = n => n * n; [1, 2, 3].map(square);` is `[1, 4, 9]` —
  works as a `map` callback the same way the parenthesized form
  already does.
- `let f = x => x > 0 ? "pos" : "neg"; f(-3);` is `"neg"` — ternary
  body, mirroring the parenthesized form's `test_arrow_body_is_ternary`
  coverage.
- Nesting/closures: `let adder = x => (y => x + y); adder(3)(4);` is
  `7` — a bare-identifier arrow returning another arrow, closing over
  the outer parameter, mirroring
  `test_arrow_nests_and_closes_over_outer_param`'s coverage for the
  parenthesized form.
- `x;` alone (a bare identifier used as a plain expression, no `=>`
  following) still parses as an `Identifier`, not an arrow function —
  confirm the existing "identifier as a plain expression" behavior is
  unchanged (e.g. `let x = 5; x;` still evaluates to `5`).
- `let f = x => { return x; }; f(1);` raises `ParseError` — block
  body after a bare-identifier arrow is out of scope, mirroring
  `test_arrow_block_body_not_supported`.
- The zero-parameter (`() => expr`) and multi-parameter
  (`(a, b) => expr`) parenthesized forms, and parenthesized single-
  parameter form (`(x) => expr`), still parse exactly as before —
  this task adds a new branch, it must not change
  `_try_arrow_function`'s existing behavior or its own tests.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_primary`'s `IDENTIFIER` branch,
near `_try_arrow_function`), `tests/test_parser.py` (near the existing
`test_arrow_*` tests, search `class.*Arrow` or `test_arrow_no_params`).
Once merged, `README.md`'s language-features bullet for arrow functions
needs the bare-identifier form mentioned, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_composite` — non-prime-above-one predicate

Build: add `is_composite(n)` to `cinder/builtins.py`, registered right
next to `is_prime` (search for `def _is_prime` — by the time this task
is claimed, tasks 1-3 above will have landed and shifted line numbers)
in the integer-property predicate cluster. A composite number is an
integer greater than `1` that is *not* prime (e.g. `4`, `6`, `8`, `9`);
this completes the classical three-way split of the non-negative
integers into prime, composite, and neither (`0`, `1`) the same way
`is_perfect_number`/`is_abundant`/`is_deficient` cover every positive
integer's divisor-sum classification.

Model the arity/type-checking and trial-division loop on `_is_prime`'s
own structure exactly (search for `def _is_prime`): reuse
`_require_arity("is_composite", arguments, 1, line, column)` and
`_require_int("is_composite", arguments[0], line, column)` (the same
helper the rest of the cluster uses, defined at
`cinder/builtins.py:157-162`). Do **not** call `_is_prime`'s function
object and negate its result — `_is_prime` returns `False` for `n < 2`
too, which would make `is_composite` incorrectly `true` for `0`, `1`,
and every negative number. Instead give `is_composite` its own
early-out — `if value < 4: return False` (the smallest composite
number is `4`; `2` and `3` are prime, `0`/`1`/negatives are neither) —
then reuse the same `int(value ** 0.5) + 1`-bounded trial-division loop
`_is_prime` uses (from `2` up to that bound, checking `value % divisor
== 0`), returning `True` the moment a divisor is found and `False` if
the loop completes without one (i.e. `value` is actually prime, so not
composite).

Acceptance criteria:
- `is_composite(4);` is `true` — smallest composite number.
- `is_composite(6);` is `true`.
- `is_composite(9);` is `true` — odd composite, confirms the loop
  isn't only catching even numbers.
- `is_composite(97);` is `false` — a larger prime.
- `is_composite(2);` is `false`, `is_composite(3);` is `false` — the
  two smallest primes, must not be swept in by an off-by-one on the
  early-out.
- `is_composite(1);` is `false`, `is_composite(0);` is `false`,
  `is_composite(-6);` is `false` — non-positive/non-composite input,
  no domain error, and specifically *not* `true` the way naively
  negating `is_prime(n)` would incorrectly produce.
- `is_composite(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"is_composite() requires an int, got
  float"` — no implicit float-to-int coercion, matching the rest of
  the cluster.
- `is_composite(true);` (bool) raises `CinderRuntimeError` matching
  `"is_composite() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_prime`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_composite` added near `is_prime`, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `is_power_of_two` — power-of-two predicate via bit trick

Build: add `is_power_of_two(n)` to `cinder/builtins.py`, registered
right after `is_composite` (search for `def _is_composite` — by the
time this task is claimed, tasks 1-4 above will have landed and
shifted line numbers) in the integer-property predicate cluster. A
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

## 5. Language: block-bodied arrow functions `(params) => { ... }` and `x => { ... }`

Build: extend both arrow-function forms — parenthesized (`_try_arrow_function`
in `cinder/parser.py`, from `feat/20260808-arrow-functions`, PR #205) and
bare single-identifier (added by task 2 above, in `_primary`'s `IDENTIFIER`
branch) — to accept a block body, `{ <statement>* }`, as an alternative to
the current expression-only body. Both prior arrow-function tasks
deliberately deferred this ("no block-bodied form"); this is a language-depth
task, not another stdlib predicate, following directly from tasks 3-4 above
(`is_composite`, `is_power_of_two`) per `PROJECT.md`'s breadth-vs-depth
policy — two single-builtin predicate tasks queued back-to-back is the
signal to inject depth again. Concrete motivation for scoping it now: any
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
`LBRACE`-check-and-branch at the bare-identifier site added by task 2, so
both forms share the same body-parsing behavior. Consider factoring the
shared "parse either an expression body (wrapped in a synthetic return) or
a block body" logic into one small helper called from both sites, but only
if it's a clean fit — do not force an abstraction that complicates either
call site.

This task also retires `test_arrow_block_body_not_supported` in
`tests/test_parser.py` (search for it) and task 2's equivalent
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

This task depends on task 2 (bare single-identifier arrow functions)
having landed first, since it extends both forms — do not claim it out
of order while task 2 is still unclaimed/open, per this file's "do not
skip ahead" rule at the top.

Likely files: `cinder/parser.py` (`_try_arrow_function`, and
`_primary`'s `IDENTIFIER` branch added by task 2), `tests/test_parser.py`
(replace `test_arrow_block_body_not_supported` and task 2's equivalent
bare-identifier assertion with positive-case tests), `tests/
test_interpreter.py` (execution-level tests for multi-statement bodies).
Once merged, `README.md`'s arrow-function bullet and `PROJECT.md`'s
roadmap paragraph need updating — leave both to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
