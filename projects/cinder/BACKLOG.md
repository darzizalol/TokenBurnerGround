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

## 1. Language: arrow function expressions `(params) => expr` [claimed 2026-08-08T14:16:53Z]

Build: add arrow-function syntax as sugar for the existing anonymous `fn`
expression, e.g. `(x) => x * 2`, `(a, b) => a + b`, `() => 42`. This is a
language-depth task — the last one to land was list/map comprehensions
many nights ago (see `PROJECT.md`'s Roadmap history); everything since has
been stdlib-predicate breadth, seven builtins in a row (`is_perfect_square`
through `is_deficient`) and counting — longer than the seven-cycle breadth
run that prompted comprehensions in the first place. This task is bumped to
the top of the backlog for that reason: `PROJECT.md`'s roadmap explicitly
flags a long uninterrupted predicate streak as the signal to inject a
language-depth task rather than let it run further, and three more
predicate tasks were queued ahead of this one before this grooming pass.
Cinder's callback-heavy builtins (`map`, `filter`, `sort_by`, `group_by`,
...) today require the verbose `fn(x) { return x * 2; }` form for even a
one-expression callback — arrow syntax closes that ergonomic gap the same
way JS/other scripting languages do, without adding a new evaluation
concept: it desugars entirely into the existing `FnExpr` AST node
(`cinder/ast_nodes.py:221`), so **no interpreter changes are needed at
all** — this is a parser-only feature.

Scope, deliberately narrow (do not exceed it in this task):
- **Only the parenthesized form.** `(x) => expr` and `() => expr` and
  `(a, b) => expr` — not the bare single-identifier form some languages
  allow (`x => expr` with no parens), which would require lookahead after
  *every* identifier in expression position and is a much bigger,
  riskier change. Out of scope for this task.
- **Expression body only**, not a block body. `(x) => x * 2` is in scope;
  `(x) => { let y = x * 2; return y; }` is not — that ambiguity (is `{`
  after `=>` a block-bodied arrow function or an object/map literal being
  returned?) is exactly the kind of thing `PROJECT.md`'s existing
  `{`-disambiguation design principle exists to solve for statement
  position, but arrow bodies are expression position, a different
  problem; leave block-bodied arrows for a future task if ever wanted.
- Same parameter grammar `fn` already supports: default values
  (`(a, b = 1) => a + b`) and a single trailing rest parameter
  (`(a, ...rest) => a`), reusing the existing `_fn_param`/`_fn_rest_param`
  helpers (`cinder/parser.py:589-` — search for `def _fn_param`) as-is,
  not reimplementing parameter parsing.

Lexer: add a `FAT_ARROW` token type (`cinder/tokens.py`) for `=>`. In
`cinder/lexer.py`'s `_equals_or` (search for `def _equals_or`, handles
`=`/`==` today), check for `>` *before* falling through to the existing
`=`-or-`==` check, so `=` (EQ), `==` (EQEQ), and `=>` (FAT_ARROW) are all
distinguished from the same entry point without disturbing the existing
two.

Parser: the ambiguity is that `(` at expression position (`_primary`,
`cinder/parser.py:1104`) already unconditionally parses a grouping
expression (`(expr)`) — `(x)` and `(x, y) => ...`'s parameter list look
identical until you've either failed to find a valid param-list shape or
found the `=>` after the closing `)`. Resolve this with a speculative
parse, the same backtracking pattern `_brace_statement` already uses for
the `{`-disambiguation problem (search for `def _brace_statement`: save
`start = self.pos`, attempt the speculative parse in a `try`/`except
ParseError`, restore `self.pos = start` and fall through on failure).
Concretely, when `_primary` sees `LPAREN`: save position, attempt to
parse a parameter list (reusing `_fn_param`/`_fn_rest_param`, comma-
separated, same shape `_fn_params_and_body` parses between its own
`LPAREN`/`RPAREN`) followed by `RPAREN` then `FAT_ARROW`; if that whole
sequence parses cleanly, parse the body via `_assignment()` (the same
tier `_fn_params_and_body`'s block-bodied `fn` uses isn't the right
comparison since bodies differ, but arrow-body expression precedence
should be `_assignment()` — the same precedence a `return <expr>;`
accepts, so `(x) => x + 1` and `(x) => a ? b : c` both work without extra
parens) and return an `FnExpr` whose `body` is a synthetic
`Block([ReturnStmt(body_expr, line, column)])` (`cinder/ast_nodes.py:293`
`Block`, `:366` `ReturnStmt`) — this is what makes the feature a pure
desugar with zero interpreter changes, since `FnExpr` evaluation already
knows how to run a `Block` body and `return` out of it. If parsing the
param list, `)`, or `=>` fails at any point, restore `self.pos` and fall
through to the existing grouping-expression code path unchanged (so
`(x)`, `(x + 1)`, `(x, y)` used as e.g. a malformed expression still
error exactly as they do today, and ordinary grouping like `(a + b) * c`
is untouched).

Acceptance criteria:
- `let double = (x) => x * 2; double(21);` is `42`.
- `let add = (a, b) => a + b; add(2, 3);` is `5`.
- `let always_42 = () => 42; always_42();` is `42` — zero-parameter form.
- `(x, y = 10) => x + y` called with one argument uses the default,
  matching `fn`'s own default-parameter behavior exactly.
- `(a, ...rest) => rest` called with 3 arguments returns a 2-element
  list, matching `fn`'s own rest-parameter behavior exactly.
- `map([1, 2, 3], (x) => x * x);` is `[1, 4, 9]` — arrow functions work
  directly as callback arguments to existing higher-order builtins with
  no other changes needed.
- `(x) => x > 0 ? "pos" : "neg"` — ternary in an arrow body works (proves
  the body is parsed at `_assignment()` precedence, not something
  narrower).
- Ordinary parenthesized grouping is unaffected: `(1 + 2) * 3;` is still
  `9`. `(x);` (a bare identifier in parens, no `=>` following) must still
  fall through to plain grouping and evaluate `x`'s value, not error —
  it has one parameter-shaped token inside the parens, but no `=>` after
  the `)`, so the speculative arrow-parse must fail and hand control back
  to the existing grouping path.
- A malformed arrow attempt like `(x, ) => x;` (trailing comma, no
  parameter after it) still raises the same `ParseError` `fn`'s own
  parameter parsing would raise for the equivalent shape, not a
  confusing "expected expression" grouping-fallback error — write a test
  that documents whichever specific error message actually surfaces
  after implementing the backtrack, rather than asserting one in
  advance.
- Arrow functions nest and close over variables exactly like `fn`
  expressions do (they *are* `FnExpr`s): `let make_adder = (n) => (x) =>
  x + n; make_adder(10)(5);` is `15`.
- Full test suite passes.

Likely files: `cinder/tokens.py` (new `FAT_ARROW` token type),
`cinder/lexer.py` (`_equals_or`), `cinder/parser.py` (`_primary`'s
`LPAREN` branch, new helper reusing `_fn_param`/`_fn_rest_param`),
`tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_interpreter.py`
(or `tests/test_builtins.py` for the `map`-callback case). Once merged,
`README.md` needs a short arrow-function mention near wherever `fn`
expressions/closures are documented, and `PROJECT.md`'s roadmap paragraph
needs it moved from backlog to landed — leave both to the Architect's
next grooming pass, not this task.

---

## 2. Standard library: `is_palindrome_number` — numeric-digit palindrome predicate

Build: add `is_palindrome_number(n)` to `cinder/builtins.py`, sitting
next to `reverse_int` (already landed, search for `reverse_int` rather
than trusting a specific line) rather than the boolean predicate
cluster proper — it belongs here because it's built directly on top of
`reverse_int` rather than being an independent digit-by-digit walk like
`is_armstrong`/`is_perfect_square`. This is the numeric sibling to the
existing string `is_palindrome` (which already tests whether a *string*
reads the same forwards and backwards): this one tests whether an
integer's decimal digits do.

Model the arity/type-checking on `reverse_int`'s own structure (search
for `def _reverse_int`): reuse `_require_arity("is_palindrome_number",
arguments, 1, line, column)` and `_require_int("is_palindrome_number",
arguments[0], line, column)` (the same helper the rest of the cluster
uses, defined at `cinder/builtins.py:157-162`). For the computation,
negative input is always `false` — the leading `-` sign breaks digit
symmetry on its own, so there is no ambiguity to resolve (unlike
`reverse_int` itself, this predicate does not need to reapply a sign):
`if value < 0: return False`, otherwise compare the value directly
against its own reversed digit string, *not* against a call to the
`_reverse_int` helper — reuse the digit-string reversal
(`str(value)[::-1]`) directly rather than routing through
`_reverse_int`'s sign-handling logic, since that logic exists to solve
a problem (preserving sign) this predicate has already special-cased
away: `return str(value) == str(value)[::-1]`.

Acceptance criteria:
- `is_palindrome_number(0);` is `true`.
- `is_palindrome_number(5);` is `true` — single digit.
- `is_palindrome_number(121);` is `true`.
- `is_palindrome_number(12321);` is `true` — odd-length palindrome.
- `is_palindrome_number(123);` is `false`.
- `is_palindrome_number(120);` is `false` — trailing zero breaks
  symmetry (reversed digit-string is `"021"`, not equal to `"120"`).
- `is_palindrome_number(-121);` is `false` — negative input is always
  `false`, even though `121` itself is a palindrome; no domain error.
- `is_palindrome_number(3.0);` (float, even though numerically whole)
  raises `CinderRuntimeError` matching `"is_palindrome_number()
  requires an int, got float"` — no implicit float-to-int coercion,
  matching the rest of the cluster.
- `is_palindrome_number(true);` (bool) raises `CinderRuntimeError`
  matching `"is_palindrome_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `reverse_int`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_palindrome_number` added near `is_palindrome`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 3. Standard library: `digital_root` — repeated-digit-sum-to-single-digit

Build: add `digital_root(n)` to `cinder/builtins.py`, sitting next to
`digit_sum`/`reverse_int` (search for `def _reverse_int` — by the time
this task is claimed, task 2 above will have landed and shifted line
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

## 4. Standard library: `is_composite` — non-prime-above-one predicate

Build: add `is_composite(n)` to `cinder/builtins.py`, registered right
next to `is_prime` (search for `def _is_prime` — by the time this task
is claimed, tasks 2-3 above will have landed and shifted line numbers)
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

## 5. Standard library: `is_power_of_two` — power-of-two predicate via bit trick

Build: add `is_power_of_two(n)` to `cinder/builtins.py`, registered
right after `is_composite` (search for `def _is_composite` — by the
time this task is claimed, tasks 2-4 above will have landed and
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
