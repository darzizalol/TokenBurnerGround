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

## 1. Standard library: `nth_prime` — the k-th prime number by position [claimed 2026-08-23T14:51:09Z]

Build: the breadth task after a `match` expression with literal patterns
and a `_` wildcard (PR #304) per `PROJECT.md`'s
breadth-vs-depth policy. `is_prime`/`is_composite`/`is_semiprime`
(`cinder/builtins.py`) all test membership in various prime-adjacent
categories, and `prime_factors` lists an integer's own factors, but
nothing in Cinder answers the complementary "which prime" question:
given a 1-indexed position, what prime is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_prime(1));'
# -> CinderRuntimeError: undefined name 'nth_prime'
```

Add to `cinder/builtins.py`, registered right after `_is_prime` (search
`def _is_prime`, immediately before `_is_composite`):
```python
def _nth_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_prime", arguments, 1, line, column)
    value = _require_int("nth_prime", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_prime() requires a positive integer, domain error", line, column
        )
    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        is_prime = True
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return candidate
```
This mirrors `_is_circular_prime`'s own locally-scoped trial-division
style (search `def _is_circular_prime`) — a plain nested loop, not a
call out to `_is_prime` itself — rather than reusing `_is_prime`
directly, since `_is_prime` takes the CLI-facing `(arguments, line,
column)` shape, not a plain `int -> bool` one; every other builtin that
needs a bare primality check inline already makes this same choice.
`1`-indexed like ordinal position is described everywhere else in the
language, so `nth_prime(1) = 2` (no `0`th prime). A domain error (not a
count of `false`) for `value < 1` matches `collatz_length`'s own
convention for its own "not a valid input" case, since this is a
value-returning function, not a predicate — there is no sensible prime
to return for position `0` or a negative position, unlike the
figurate-number predicates' "closed domain, just answer false"
convention. Also register the new dict entry (search `"is_prime":
_is_prime,`, add `"nth_prime": _nth_prime,` directly after it).

Acceptance criteria:
- `nth_prime(1);` is `2`, `nth_prime(2);` is `3`, `nth_prime(3);` is `5`,
  `nth_prime(4);` is `7`, `nth_prime(5);` is `11` — the first five
  primes by position.
- `nth_prime(10);` is `29`.
- `nth_prime(100);` is `541` — confirms the check holds well beyond
  small brute-forced cases.
- `nth_prime(0);` and `nth_prime(-3);` both raise `CinderRuntimeError`
  matching `"nth_prime() requires a positive integer, domain error"`.
- `nth_prime(2.0);` raises `CinderRuntimeError` matching `"nth_prime()
  requires an int, got float"`.
- `nth_prime(true);` raises `CinderRuntimeError` matching `"nth_prime()
  requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_prime`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsPrime`, search that
name, for the arity/type-error test shapes — the domain-error test
shape instead mirrors `class TestCollatzLength`, search that name,
since `nth_prime` raises rather than returning `false` for an invalid
position). Once merged, `README.md`'s Builtins bullet needs `nth_prime`
added near `is_prime`/`prime_factors`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `nth_fibonacci` — the k-th Fibonacci number by position

Build: the breadth task restocking the backlog after a list pattern
nested inside a map pattern landed via PR #299, per `PROJECT.md`'s
breadth-vs-depth policy (the `match` expression task, merged as PR #304,
was this pass's depth task; alternation resumes with breadth here).
`is_fibonacci`/`is_lucas_number` (`cinder/builtins.py`) both test membership in their
respective sequences, and `nth_prime` (task 1 above) already queues the
same "which position" question for primes, but nothing in Cinder
answers the complementary question for Fibonacci numbers: given a
1-indexed position, what value is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_fibonacci(10));'
# -> CinderRuntimeError: undefined name 'nth_fibonacci'
```

Add to `cinder/builtins.py`, registered right after `_is_lucas_number`
(search `def _is_lucas_number`, immediately before `_is_happy_number`):
```python
def _nth_fibonacci(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_fibonacci", arguments, 1, line, column)
    value = _require_int("nth_fibonacci", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_fibonacci() requires a positive integer, domain error", line, column
        )
    previous, current = 0, 1
    for _ in range(value - 1):
        previous, current = current, previous + current
    return current
```
This mirrors `_is_lucas_number`'s own generate-and-track loop style — a
plain iterative walk up the recurrence, not a closed form — deliberately
avoiding Binet's formula (`(phi**k - psi**k) / sqrt(5)`), which relies
on irrational `sqrt(5)` and loses exact-integer precision for large `k`
under floating point; the iterative walk stays exact at any size, same
tradeoff `is_fibonacci`'s own closed-form membership check avoids by
using `math.isqrt` instead of a literal square root. `1`-indexed like
`nth_prime`'s own convention, so `nth_fibonacci(1) = 1` and
`nth_fibonacci(2) = 1` (the sequence's two seed values), not `nth_fibonacci(1) = 0`.
A domain error (not a sentinel value) for `value < 1` matches
`nth_prime`'s own convention for its own "not a valid input" case, since
this is a value-returning function, not a predicate — there is no
sensible Fibonacci number to return for position `0` or a negative
position. Also register the new dict entry (search `"is_lucas_number":
_is_lucas_number,`, add `"nth_fibonacci": _nth_fibonacci,` directly
after it).

Acceptance criteria:
- `nth_fibonacci(1);` is `1`, `nth_fibonacci(2);` is `1`,
  `nth_fibonacci(3);` is `2`, `nth_fibonacci(4);` is `3`,
  `nth_fibonacci(5);` is `5` — the first five Fibonacci numbers by
  position.
- `nth_fibonacci(10);` is `55`.
- `nth_fibonacci(20);` is `6765` — confirms the check holds well beyond
  small brute-forced cases.
- `nth_fibonacci(0);` and `nth_fibonacci(-3);` both raise
  `CinderRuntimeError` matching `"nth_fibonacci() requires a positive
  integer, domain error"`.
- `nth_fibonacci(2.0);` raises `CinderRuntimeError` matching
  `"nth_fibonacci() requires an int, got float"`.
- `nth_fibonacci(true);` raises `CinderRuntimeError` matching
  `"nth_fibonacci() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_lucas_number`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsFibonacci`, search that
name, for the arity/type-error test shapes — the domain-error test
shape instead mirrors `class TestCollatzLength`, search that name,
since `nth_fibonacci` raises rather than returning `false` for an
invalid position). Once merged, `README.md`'s Builtins bullet needs
`nth_fibonacci` added near `is_fibonacci`/`is_lucas_number`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Language: bare comma multi-target assignment (`a, b = 1, 2;`, swap idiom `a, b = b, a;`)

Build: the depth task restocking the backlog back to 6 tasks now that
`is_heptagonal` landed via PR #300, per `PROJECT.md`'s breadth-vs-depth
policy (tasks 2 and 3 above are both breadth; alternation resumes with
depth here). Cinder already has bracketed list-destructuring assignment
(`[a, b] = expr;`, `cinder/parser.py`'s `_assignment`, the
`isinstance(expr, ListLiteral)` branch) and, since PR #289, allows
comma-separated *independent* statements at expression-statement
position (`a = 1, b = 2;`, `f(), g();`, via `_expr_statement`'s
`DeclSeq` wrapping). Bare comma multi-target assignment — the
unbracketed sugar Python-family languages use for the swap idiom — has
never been added, and the gap is worse than a missing feature: it
*silently misbehaves* rather than raising, because `_expr_statement`'s
existing comma-loop happily reinterprets `a, b = 1, 2;` as three
unrelated statements. Verify the gap:
```sh
python3 -m cinder.cli eval 'let a = 0; let b = 0; a, b = 1, 2; print(a); print(b);'
# -> 0
#    1
# (wrong: should print 1 then 2 — instead `a, b = 1, 2;` silently parses
# as three independent ExprStmts: `a` (no-op), `b = 1` (assignment,
# `2` discarded as its own no-op statement); no error at all)
python3 -m cinder.cli eval 'let a = 1; let b = 2; a, b = b, a; print(a); print(b);'
# -> 1
#    2
# (wrong: should print 2 then 1, the swap — instead it parses as `a`
# (no-op), `b = b` (self-assign), `a` (no-op); nothing swaps)
```

Add a new speculative-parse helper, `_try_multi_assign_statement`, called
from `_expr_statement` (search `def _expr_statement`, `cinder/parser.py`)
before its existing `first = self._assignment()` line:
```python
    def _expr_statement(self) -> Stmt:
        multi_assign = self._try_multi_assign_statement()
        if multi_assign is not None:
            return multi_assign
        first = self._assignment()
        statements = [ExprStmt(first)]
        ...
```
Place the new method near `_try_map_destructure_assign_statement` (search
that name, `cinder/parser.py`), mirroring its speculative-parse-with-
backtrack shape (save `self.pos`, attempt a parse, reset and return `None`
on any `ParseError` so the caller falls through unchanged):
```python
    def _try_multi_assign_statement(self) -> "Stmt | None":
        """Speculatively parses bare comma-separated multi-target
        assignment `a, b = 1, 2;` (including the swap idiom
        `a, b = b, a;`), tried before `_expr_statement`'s existing
        single-target/comma-separated-statements parse. Desugars to the
        same `DestructureAssign` node the bracketed form `[a, b] = expr;`
        already produces (`_assignment`'s `isinstance(expr, ListLiteral)`
        branch), reusing its runtime semantics for free: RHS evaluated
        once, length-checked, assigned left to right — so the RHS is
        evaluated in full (both `b` and `a` in the swap case) before any
        target is written, which is what makes the swap idiom correct.
        Returns `None` on any shape mismatch — fewer than two
        comma-separated identifiers, or no top-level `=` following them —
        leaving `self.pos` untouched so the caller's own `_assignment()`-
        based parse runs unchanged; this keeps `a = 1, 2;` (single target,
        PR #289's DeclSeq form) and `a, b;` (two independent identifier
        statements) parsing exactly as before, since both fail this
        speculative parse (too few names, or no top-level `=`)."""
        start = self.pos
        try:
            names = [self._consume(TokenType.IDENTIFIER, "identifier")]
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._consume(TokenType.IDENTIFIER, "identifier"))
            if len(names) < 2 or not self._check(TokenType.EQ):
                self.pos = start
                return None
            eq_token = self._advance()
            values = [self._assignment()]
            while self._check(TokenType.COMMA):
                self._advance()
                values.append(self._assignment())
        except ParseError:
            self.pos = start
            return None
        self._consume(TokenType.SEMICOLON, "';' after multi-target assignment")
        pattern_names = [(name.lexeme, None) for name in names]
        value = values[0] if len(values) == 1 else ListLiteral(
            values, eq_token.line, eq_token.column
        )
        return ExprStmt(
            DestructureAssign(
                pattern_names, None, value, eq_token.line, eq_token.column, is_map=False
            )
        )
```
The `len(values) == 1` branch matters beyond the literal cases above: it
lets a single RHS expression that itself evaluates to a list (e.g. a
function call) unpack directly — `a, b = pair();` behaves exactly like
`[a, b] = pair();` — rather than wrapping it in a synthetic one-element
list that would only ever fail the length check. Multiple comma-
separated RHS values (`1, 2` or `b, a`) *do* get wrapped in a
`ListLiteral`, since Cinder — unlike Python — has no bare tuple literal;
this is the moral equivalent of Python constructing an implicit tuple
from `a, b = 1, 2`'s right-hand side. No interpreter changes are needed:
`_evaluate_destructure_assign` and `_bind_list_destructure`
(`cinder/interpreter.py`) already evaluate `expr.value` once, require a
list, and raise the existing `"destructuring pattern expects N elements,
got M"` `CinderRuntimeError` on a length mismatch — this task is parser-
only, reusing that machinery unchanged. Out of scope for this first
version, all left as natural follow-ups: a trailing `...rest` element, a
trailing comma before `=`, and nested bracket/brace targets mixed into
the bare form (`a, [b, c] = ...`) — the bracketed form already covers
that need on its own.

Acceptance criteria:
- `let a = 0; let b = 0; a, b = 1, 2; print(a); print(b);` prints `1`
  then `2`.
- `let a = 1; let b = 2; a, b = b, a; print(a); print(b);` prints `2`
  then `1` — the swap idiom, confirming the RHS is fully evaluated
  before either target is written.
- `let a = 0; let b = 0; let c = 0; a, b, c = 1, 2, 3; print(a); print(b); print(c);`
  prints `1`, `2`, `3` — three targets, not just two.
- `fn pair() { return [1, 2]; } let a = 0; let b = 0; a, b = pair(); print(a); print(b);`
  prints `1` then `2` — a single RHS expression that evaluates to a list
  unpacks directly, exactly like `[a, b] = pair();` already does.
- `let a = 0; let b = 0; a, b = 1, 2, 3;` raises `CinderRuntimeError`
  matching `"destructuring pattern expects 2 elements, got 3"` — reusing
  the existing destructuring length-check error verbatim.
- `let a = 0; a = 1, 2;` is unchanged: still parses as PR #289's
  `DeclSeq` of two `ExprStmt`s (`a = 1` then the no-op `2`), `print(a);`
  afterward prints `1` — single-target assignment followed by a
  comma-separated statement is not reinterpreted as multi-assign.
- `let a = 1; let b = 2; a, b;` is unchanged: still two independent
  `ExprStmt`s (bare identifier reads, no-ops), `print(a); print(b);`
  afterward prints `1` then `2` — untouched.
- `f(), g();` (two independent call-expression statements) is unchanged
  — still parses and runs as PR #289 left it, confirming the new
  speculative parse backs out cleanly on any non-identifier-list shape.
- `let a = 0; a, 5 = 1, 2;` raises `ParseError` — a non-identifier in
  target position falls all the way through to the existing "invalid
  assignment target"-style failure once every fallback is exhausted,
  not a silent misparse.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_expr_statement`,
`_try_multi_assign_statement`, placed near
`_try_map_destructure_assign_statement`), `tests/test_parser.py` (add
tests near `test_expr_statement_comma_separated_becomes_decl_seq`,
search that name, and alongside `class TestDestructureAssign`'s parser-
level coverage), `tests/test_interpreter.py` (extend `class
TestDestructureAssign`, search that name, with the swap-idiom and
`pair()`-unpacking end-to-end cases). Once merged, `README.md`'s
"Variables & scope" bullet (the existing `[a, b] = expr;` plain-
assignment mention) needs a note that the bare form is now supported
too, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" bullet needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `is_octagonal` — membership test for the octagonal numbers

Build: the breadth task restocking the backlog back to 6 tasks now that
task 3 (bare comma multi-target assignment) rounds out this pass's
depth work, per `PROJECT.md`'s breadth-vs-depth policy. `is_triangular`,
`is_pentagonal`, `is_hexagonal`, and `is_heptagonal`
(`cinder/builtins.py`) already form a cluster of figurate-number
membership predicates, each using the same closed-form
`math.isqrt`-based identity with a different modular-residue check;
`is_octagonal` is the natural fifth member — octagonal numbers
(`1, 8, 21, 40, 65, 96, ...`) are as standard a figurate family as the
other four and nothing in Cinder tests membership in them yet. Verify
the gap:
```sh
python3 -m cinder.cli eval 'print(is_octagonal(8));'
# -> <eval>:1:7: undefined name 'is_octagonal' (did you mean 'is_pentagonal'?)
```

Add to `cinder/builtins.py`, registered right after `_is_heptagonal`
(search `def _is_heptagonal`, immediately before `_is_prime`):
```python
def _is_octagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_octagonal", arguments, 1, line, column)
    value = _require_int("is_octagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 3 * value + 1
    root = math.isqrt(candidate)
    return root * root == candidate and (1 + root) % 3 == 0
```
The `n`-th octagonal number is `P(n) = n * (3n - 2)`; solving
`3n^2 - 2n - value = 0` for `n` gives
`n = (1 + sqrt(1 + 3 * value)) / 3`, so `value` is octagonal iff
`1 + 3 * value` is a perfect square (`candidate`/`root`, the same
`math.isqrt` technique `is_triangular`/`is_pentagonal`/`is_hexagonal`/
`is_heptagonal` all use) *and* `(1 + root)` is divisible by `3` — the
modular-residue check that rules out roots which solve the algebraic
identity but don't correspond to an integer `n` (the same role
`is_pentagonal`'s `root % 6 == 5`, `is_hexagonal`'s `root % 4 == 3`,
and `is_heptagonal`'s `root % 10 == 7` each play for their own family).
`0` and negative inputs return `false` rather than raising, matching
every sibling predicate's closed-domain convention — this is a
membership test, not a value-returning function, so there is a
sensible (negative) answer for any integer input, unlike `collatz_max`/
`nth_prime`-style functions that raise on an invalid domain. Also
register the new dict entry (search `"is_heptagonal": _is_heptagonal,`,
add `"is_octagonal": _is_octagonal,` directly after it).

Acceptance criteria:
- `is_octagonal(1);` is `true` (`P(1) = 1`).
- `is_octagonal(0);` is `false` — `0` is not in the sequence under this
  cluster's 1-indexed convention (matches `is_heptagonal(0)`, `false`).
- For each of `1, 8, 21, 40, 65, 96` (the first six octagonal numbers,
  `P(1)` through `P(6)`), `is_octagonal(value);` is `true`.
- For each of `2, 5, 9, 20, 50, 100` (non-members interleaved among the
  above), `is_octagonal(value);` is `false`.
- `is_octagonal(29800);` is `true` — `P(100) = 100 * 298 = 29800`,
  confirming the check holds well beyond small brute-forced cases.
- `is_octagonal(-8);` is `false` — negative input, no domain error.
- `is_octagonal(8.0);` raises `CinderRuntimeError` matching
  `"is_octagonal() requires an int, got float"`.
- `is_octagonal(true);` raises `CinderRuntimeError` matching
  `"is_octagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_heptagonal`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsHeptagonal`, search
that name, for both the membership-cluster test shapes and the
arity/type-error test shapes). Once merged, `README.md`'s Builtins
bullet needs `is_octagonal` added right after its `is_heptagonal`
mention, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `binomial` — the binomial coefficient (`n` choose `k`)

Build: restocking the backlog back to 6 tasks now that `collatz_max`
landed via PR #303, per `PROJECT.md`'s breadth-vs-depth policy (task 4
above is breadth; alternation would prefer depth here, but no
well-scoped depth gap survived verification this pass — see the
"Current frontier" note in `PROJECT.md` — so this restocks with a
second breadth task, which the policy explicitly allows
occasionally). `factorial` (`cinder/builtins.py`) computes `n!` but
nothing in Cinder answers the combinatorics question built on top of
it: how many ways to choose `k` items from `n`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(binomial(5, 2));'
# -> <eval>:1:7: undefined name 'binomial'
```

Add to `cinder/builtins.py`, registered right after `_factorial`
(search `def _factorial`, immediately before `_sum`):
```python
def _binomial(arguments: list, line: int, column: int) -> object:
    _require_arity("binomial", arguments, 2, line, column)
    n, k = arguments
    for position, value in (("first", n), ("second", k)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise CinderRuntimeError(
                f"binomial() requires an int as its {position} argument, "
                f"got {type_name(value)}",
                line, column,
            )
    if n < 0 or k < 0:
        raise CinderRuntimeError(
            "binomial() requires non-negative n and k, domain error", line, column
        )
    return math.comb(n, k)
```
This mirrors `_gcd`/`_lcm`'s own two-int-argument style (search
`def _gcd`, immediately above `_factorial`) — a `for position, value in
(...)` loop checking both arguments share the same type-error shape —
and `_factorial`'s own choice to delegate to a stdlib `math` function
rather than a hand-rolled loop, since `math.comb` is exact-integer and
already the standard library's own answer to this exact question. `k >
n` is not a domain error: `math.comb(n, k)` correctly returns `0` for
that case (zero ways to choose more items than exist), matching every
combinatorics textbook's convention, so no extra check is needed beyond
what `math.comb` already enforces. Also register the new dict entry
(search `"factorial": _factorial,`, add `"binomial": _binomial,`
directly after it).

Acceptance criteria:
- `binomial(5, 2);` is `10`, `binomial(5, 0);` is `1`, `binomial(5, 5);`
  is `1` — the standard small cases.
- `binomial(0, 0);` is `1` — the empty-choose-empty edge case.
- `binomial(10, 3);` is `120`.
- `binomial(30, 15);` is `155117520` — confirms the check holds well
  beyond small brute-forced cases.
- `binomial(5, 8);` is `0` — choosing more items than exist returns
  `0`, not a domain error.
- `binomial(-1, 2);` and `binomial(5, -1);` both raise
  `CinderRuntimeError` matching `"binomial() requires non-negative n
  and k, domain error"`.
- `binomial(5.0, 2);` raises `CinderRuntimeError` matching `"binomial()
  requires an int as its first argument, got float"`.
- `binomial(5, true);` raises `CinderRuntimeError` matching
  `"binomial() requires an int as its second argument, got bool"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `factorial`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (add a `class TestBinomial` modeled on `class
TestFactorial`, search that name, for both the combinatorics-value test
shapes and the arity/type/domain-error test shapes, plus `class
TestGcd`, search that name, for the two-argument type-error message
shape). Once merged, `README.md`'s Builtins bullet needs `binomial`
added near `factorial`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `nth_lucas` — the k-th Lucas number by position

Build: restocking the backlog back to 6 tasks now that a `match`
expression with literal patterns and a `_` wildcard landed via PR #304,
per `PROJECT.md`'s breadth-vs-depth policy (that task was depth;
alternation restocks with breadth here). `is_lucas_number`
(`cinder/builtins.py`) tests membership in the Lucas sequence, and task
2 above (`nth_fibonacci`, not yet landed) already queues the same
"which position" question for Fibonacci numbers, but nothing in Cinder
answers the complementary question for Lucas numbers: given a
1-indexed position, what value is found there. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_lucas(5));'
# -> <eval>:1:7: undefined name 'nth_lucas'
```

Add to `cinder/builtins.py`, registered right after `_is_lucas_number`
(search `def _is_lucas_number`, immediately before `_is_happy_number` —
if task 2 has landed first, `_nth_fibonacci` will sit between them;
register `_nth_lucas` after whichever of the two is currently last):
```python
def _nth_lucas(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_lucas", arguments, 1, line, column)
    value = _require_int("nth_lucas", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_lucas() requires a positive integer, domain error", line, column
        )
    previous, current = 1, 3  # L(1), L(2)
    if value == 1:
        return previous
    for _ in range(value - 2):
        previous, current = current, previous + current
    return current
```
This mirrors `_is_lucas_number`'s own indexing convention exactly
(search `def _is_lucas_number`): that predicate's internal loop seeds
`previous, current = 1, 3` and comments them `L(1), L(2)`, i.e. this
cluster's 1-indexed Lucas sequence starts at `L(1) = 1, L(2) = 3, L(3)
= 4, ...` and deliberately omits the standard mathematical `L(0) = 2`
seed — there is no `nth_lucas(0)` any more than there's an
`is_lucas_number` match for the value `2` counted as position `0`.
Getting this seed wrong (e.g. starting from `L(0) = 2, L(1) = 1` like
the textbook definition) would silently desynchronize `nth_lucas` from
`is_lucas_number`'s own notion of position, so `nth_lucas(n)` and
`is_lucas_number`'s internal walk must agree position-for-position —
verified directly in the acceptance criteria below. A domain error (not
a sentinel value) for `value < 1` matches `nth_prime`/`nth_fibonacci`'s
own convention for their own "not a valid input" case, since this is a
value-returning function, not a predicate. Also register the new dict
entry (search `"is_lucas_number": _is_lucas_number,`, add `"nth_lucas":
_nth_lucas,` directly after it).

Acceptance criteria:
- `nth_lucas(1);` is `1`, `nth_lucas(2);` is `3`, `nth_lucas(3);` is
  `4`, `nth_lucas(4);` is `7`, `nth_lucas(5);` is `11` — the first five
  Lucas numbers by this cluster's 1-indexed convention.
- `nth_lucas(10);` is `123`.
- `nth_lucas(15);` is `1364` — confirms the check holds well beyond
  small brute-forced cases.
- For each `n` in `1..15`, `is_lucas_number(nth_lucas(n));` is `true` —
  `nth_lucas` and `is_lucas_number` agree on the same sequence.
- `nth_lucas(0);` and `nth_lucas(-3);` both raise `CinderRuntimeError`
  matching `"nth_lucas() requires a positive integer, domain error"`.
- `nth_lucas(2.0);` raises `CinderRuntimeError` matching `"nth_lucas()
  requires an int, got float"`.
- `nth_lucas(true);` raises `CinderRuntimeError` matching `"nth_lucas()
  requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_lucas_number`,
see current line numbers — shift if earlier tasks this cycle land
first), `tests/test_builtins.py` (model on `class TestIsLucasNumber`,
search that name, for both the sequence-value test shapes and the
arity/type-error test shapes — the domain-error test shape instead
mirrors `class TestCollatzLength`, search that name, since `nth_lucas`
raises rather than returning `false` for an invalid position). Once
merged, `README.md`'s Builtins bullet needs `nth_lucas` added near
`is_lucas_number`/`nth_fibonacci`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
