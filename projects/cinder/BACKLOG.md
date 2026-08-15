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

## 1. Standard library: `is_squarefree` — no repeated prime factor

Build: the breadth task after task 5's depth work (hole elements in
list-destructuring patterns) per `PROJECT.md`'s breadth-vs-depth
policy, restocking the backlog back to 6 tasks now that
`is_strong_number` has landed and dropped the count to the 5-task
floor. Add `is_squarefree(n)` to `cinder/builtins.py`, registered right
after `is_pronic` (search for `def _is_pronic`, the current last entry
in the integer-property predicate cluster before the divisor cluster
begins) — a positive integer is squarefree when no perfect square
greater than `1` divides it evenly, equivalently when none of its
prime factors repeats (e.g. `6 = 2 * 3` is squarefree, `12 = 2 * 2 * 3`
is not, since `4` divides it). This is the natural predicate neighbor
to `is_prime`/`is_composite` (which classify `n` as a whole) and the
soon-to-land `prime_factors` (task 4, which lists factors with
multiplicity) — `is_squarefree` answers "does any factor repeat?"
without needing to build the full factor list, via the same
`sqrt(n)`-bounded trial-division shape `is_prime`/`is_composite`
already use, checking `divisor * divisor` divisibility directly rather
than a fixed divisor:

```python
def _is_squarefree(arguments: list, line: int, column: int) -> object:
    _require_arity("is_squarefree", arguments, 1, line, column)
    value = _require_int("is_squarefree", arguments[0], line, column)
    if value < 1:
        return False
    for divisor in range(2, math.isqrt(value) + 1):
        if value % (divisor * divisor) == 0:
            return False
    return True
```

Model the arity/type-checking exactly on `is_prime`/`is_pronic`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). `n < 1`
returns `false` rather than raising, matching the boolean-predicate
cluster's own convention (`is_prime`, `is_pronic`, `is_harshad`, etc. —
*not* the divisor cluster's type-vs-domain-error convention, since this
builtin returns a boolean, not a number). `value == 1` is a genuine
`true` case handled for free by the loop: `math.isqrt(1) + 1 == 2`, so
`range(2, 2)` is empty and the function falls through to `return True`
— `1` has no prime factors at all, so vacuously none of them repeats.

Acceptance criteria:
- `is_squarefree(1);` is `true` — vacuously squarefree, the empty-loop
  case above.
- `is_squarefree(6);` is `true` — `6 = 2 * 3`, no repeated factor.
- `is_squarefree(30);` is `true` — `30 = 2 * 3 * 5`.
- `is_squarefree(4);` is `false` — `4 = 2 * 2`, divisible by the
  perfect square `4`.
- `is_squarefree(12);` is `false` — `12 = 2 * 2 * 3`, divisible by `4`.
- `is_squarefree(45);` is `false` — `45 = 3 * 3 * 5`, divisible by `9`.
- `is_squarefree(0);` is `false` — below the domain floor.
- `is_squarefree(-6);` is `false` — negative input, same convention as
  `is_prime`/`is_pronic`.
- `is_squarefree(5.0);` raises `CinderRuntimeError` matching
  `"is_squarefree() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_squarefree(true);` raises `CinderRuntimeError` matching
  `"is_squarefree() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_pronic`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `is_pronic` test class,
search for `test_is_pronic_of_`). Once merged, `README.md`'s Builtins
bullet needs `is_squarefree` added near `is_prime`/`is_pronic`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 2. Language: optional catch binding (`try { ... } catch { ... }`, no name required)

Build: the depth task after task 5's breadth work (`is_squarefree`) per
`PROJECT.md`'s breadth-vs-depth policy — also restocking the backlog
back to 6 tasks now that unary `+` (the task that used to sit at the
top of this file) has landed and dropped the count to the 5-task
floor. Today `catch` always requires a parenthesized binding name —
`try { ... } catch (name) { ... }` — even when the handler never reads
the caught error message, forcing a throwaway name for the common
"just recover, don't inspect" case. Verify the gap: `python3 -m
cinder.cli eval 'try { throw "boom"; } catch { print("caught"); }'`
currently raises `ParseError` `"expected '(' after 'catch', found
'{'"` (`cinder/parser.py`'s `_try_statement`, search for `def
_try_statement`, unconditionally consumes `(`, an identifier, and `)`
right after the `catch` keyword).

**Parsing** (`cinder/parser.py`): in `_try_statement`, right after
`self._advance()` consumes the `catch` token, only parse the
`(name)` group when the next token is actually `(` — otherwise leave
`catch_name` as `None` and fall straight through to the body-block
check:

```python
        catch_name = None
        catch_block = None
        if self._check(TokenType.CATCH):
            self._advance()
            if self._check(TokenType.LPAREN):
                self._advance()
                name_token = self._consume(
                    TokenType.IDENTIFIER, "identifier after 'catch ('"
                )
                self._consume(TokenType.RPAREN, "')' after catch name")
                catch_name = name_token.lexeme
            if not self._check(TokenType.LBRACE):
                token = self._peek()
                raise ParseError(
                    f"expected '{{' before catch body, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            catch_block = self._block()
```

No AST change is needed — `TryStmt.catch_name` (`cinder/ast_nodes.py`)
is already typed `str | None`; today's parser just never actually
produces the `None` case. Every other branch of `_try_statement`
(`finally` parsing, the `catch_block is None and finally_block is
None` "expected 'catch' or 'finally'" check, the final `TryStmt(...)`
construction) needs no changes at all.

**Evaluation** (`cinder/interpreter.py`): in `_execute_try` (search for
`def _execute_try`), guard the existing `catch_env.define(...)` call
so it only runs when a name was actually written — the catch block
still gets its own fresh child environment either way (so a `let`
declared inside it doesn't leak into the surrounding scope), it just
has nothing pre-bound when there's no name:

```python
            except CinderRuntimeError as error:
                if stmt.catch_block is None:
                    raise
                catch_env = Environment(env)
                if stmt.catch_name is not None:
                    catch_env.define(stmt.catch_name, error.message)
                self.execute(stmt.catch_block, catch_env)
```

Acceptance criteria:
- `try { throw "boom"; } catch { print("caught"); }` prints `caught` —
  the catch block runs with no name bound.
- `try { throw "boom"; } catch { print("caught"); } finally { print("done"); }`
  prints `caught` then `done` — `finally` still runs afterward,
  unaffected by the missing name.
- `try { throw "boom"; } catch (e) { print(e); }` still prints `boom`
  — the named form is completely unchanged.
- `let ran = 0; try { 1; } catch { ran = 1; }` leaves `ran` at `0` — a
  nameless catch block still only runs when an error was actually
  thrown, same as the named form.
- `try { throw "x"; } catch { let y = 1; } y;` raises
  `CinderRuntimeError` matching `undefined name 'y'` — the catch
  block's own child environment doesn't leak into the surrounding
  scope, same as the named form.
- `try { throw "x"; } catch { e; }` raises `CinderRuntimeError`
  matching `undefined name 'e'` — confirms no binding is created under
  any implicit name when `(name)` is omitted.
- `fn f() { try { throw "x"; } catch { return 1; } return 2; } print(f());`
  prints `1` — `return` inside a nameless catch block still propagates
  out of the function, same as the named form.
- `try { print(1); }` (neither `catch` nor `finally`) still raises the
  exact same `ParseError` it does today, `"expected 'catch' or
  'finally' after try block, found ..."` — unaffected.
- `try { print(1); } catch (e)` (missing body) still raises the exact
  same `ParseError` it does today — unaffected, since the `LBRACE`
  check after the optional `(name)` group is unchanged.
- Every pre-existing try/catch/finally test (nested try/catch, catch
  inside a loop/function, error-inside-catch-not-re-caught, finally
  ordering) continues to pass unmodified.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_try_statement`),
`cinder/interpreter.py` (`_execute_try`), `tests/test_parser.py`
(shape assertions — search for `test_try_catch_shape`,
`test_try_catch_empty_bodies`, `test_try_catch_finally_shape`, plus a
new nameless-catch shape test asserting `catch_name` is `None`),
`tests/test_interpreter.py` (new nameless-catch tests modeled on the
existing `test_catch_binds_error_message_and_recovers`,
`test_catch_block_does_not_run_when_no_error`,
`test_catch_name_not_visible_after_try_catch` cluster, search for
`class ... Try` or `def test_catch_`). Once merged, `README.md`'s
Control flow bullet needs a nameless-catch mention added next to the
existing `try`/`catch`/`finally` description, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_amicable` — two integers whose proper-divisor sums point at each other

Build: the breadth task after task 5's depth work (optional catch
binding) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `num_divisors` has landed and dropped
the count to the 5-task floor. Add `is_amicable(a, b)` to
`cinder/builtins.py`, registered right after `num_divisors` (search for
`def _num_divisors`, the current last entry in the divisor cluster) —
the two-argument predicate sibling to `is_perfect_number`/`is_abundant`/
`is_deficient`, the same way `is_coprime`/`is_divisible` are the
two-argument siblings of the single-argument `is_prime`/`is_even`/
`is_odd` cluster. Two positive integers `a != b` are an *amicable pair*
when each one's own proper-divisor sum equals the other (e.g. `220`'s
proper divisors sum to `284`, and `284`'s proper divisors sum back to
`220`) — the classical two-number generalization of a perfect number
(where a single number's proper-divisor sum equals *itself*).

Like `is_emirp` (which inlines `is_composite`'s trial-division loop and
`reverse_int`'s digit reversal rather than calling either builtin
directly, since both take the `(arguments, line, column)` dispatch
signature, not a raw `int`), this needs its own private
`int -> int` helper mirroring `_aliquot_sum`'s trial-division body
exactly (including its `value == 1 -> 0` special case, since the
general `range(2, math.isqrt(value) + 1)` loop alone would wrongly
leave the running total at its seed value of `1` for that input),
called twice — once per argument:

```python
def _is_amicable(arguments: list, line: int, column: int) -> object:
    _require_arity("is_amicable", arguments, 2, line, column)
    a = _require_int("is_amicable", arguments[0], line, column)
    b = _require_int("is_amicable", arguments[1], line, column)
    if a < 1 or b < 1 or a == b:
        return False

    def _aliquot_sum_value(value: int) -> int:
        if value == 1:
            return 0
        total = 1
        for divisor in range(2, math.isqrt(value) + 1):
            if value % divisor == 0:
                total += divisor
                complement = value // divisor
                if complement != divisor:
                    total += complement
        return total

    return _aliquot_sum_value(a) == b and _aliquot_sum_value(b) == a
```

Model the arity/type-checking exactly on `is_coprime`/`is_divisible`'s
own two-argument structure: `_require_arity` with `2`, then
`_require_int` on each argument in order (reusing the shared helper —
do **not** hand-roll a separate `isinstance` check). Domain handling
follows the *predicate* cluster's convention (`is_perfect_number`/
`is_abundant`/`is_deficient`, all of which return `false` for `value <
1` rather than raising) — **not** the divisor cluster's
type-vs-domain-error convention (`divisors`/`aliquot_sum`/
`num_divisors`, which raise on `n < 1`) — since `is_amicable` returns a
boolean, not a number. The `a == b` short-circuit is deliberate: a
perfect number like `6` trivially satisfies
`_aliquot_sum_value(6) == 6` in both directions, but the classical
definition of an amicable pair requires two *distinct* integers, so a
number is never amicable with itself even when its own proper-divisor
sum loops back to itself.

Acceptance criteria:
- `is_amicable(220, 284);` is `true` — the smallest known amicable
  pair: `220`'s proper divisors (`1, 2, 4, 5, 10, 11, 20, 22, 44, 55,
  110`) sum to `284`, and `284`'s proper divisors (`1, 2, 4, 71, 142`)
  sum to `220`.
- `is_amicable(284, 220);` is `true` — order-independent, since the
  check is symmetric in its two arguments.
- `is_amicable(1184, 1210);` is `true` — the second-smallest known
  amicable pair, exercising a second concrete case beyond `220`/`284`.
- `is_amicable(6, 6);` is `false` — `6` is a perfect number
  (`_aliquot_sum_value(6) == 6`), but the `a == b` guard rejects it
  before either sum is even computed: a number is never amicable with
  itself.
- `is_amicable(220, 100);` is `false` — `220`'s proper-divisor sum is
  `284`, not `100`.
- `is_amicable(0, 5);` is `false` — below the domain floor.
- `is_amicable(-6, 5);` is `false` — negative input, same convention as
  `is_perfect_number`/`is_abundant`/`is_deficient`.
- `is_amicable(220, 5.0);` raises `CinderRuntimeError` matching
  `"is_amicable() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `is_amicable(true, 220);` raises `CinderRuntimeError` matching
  `"is_amicable() requires an int, got bool"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `num_divisors`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py` (model on the `is_perfect_number`/`is_coprime`
test classes). Once merged, `README.md`'s Builtins bullet needs
`is_amicable` added near `divisors`/`aliquot_sum`/`num_divisors`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 4. Language: pipe operator (`a |> f` as sugar for `f(a)`)

Build: the depth task after task 5's breadth work (`is_amicable`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that default values in map-destructuring patterns has
landed via PR #249, dropping the count to the 5-task floor. Cinder
already ships `pipe(f, g, h)` and `compose(f, g, h)` builtins that
return a new function threading a single value left-to-right (`pipe`)
or right-to-left (`compose`) through a fixed list of unary functions,
but there is no operator-level sugar for the common one-shot case: to
pipe a value through a single function today you write `f(a)`, and to
chain two calls you either nest them (`g(f(a))`, reading
inside-out) or build a throwaway piped function
(`pipe(f, g)(a)`) just to call it once. Verify the gap: `python3 -m
cinder.cli eval 'fn double(x) { return x * 2; } print(5 |> double);'`
currently raises `ParseError` `"expected an expression, found '>'"` —
the lexer has no `|>` token, so `|` lexes as the bitwise-or `PIPE`
token and `>` is left dangling where an expression was expected.

**Semantics**: `a |> f` evaluates `a`, evaluates `f`, then calls the
result of `f` with the result of `a` as its sole argument — exactly
`f(a)`, but written left-to-right. Both sides are ordinary expressions,
evaluated exactly once each, so `a |> f(1)` is **not** `f(1, a)`
Elixir-style — `f(1)` evaluates first (calling `f` with just `1`), and
*its return value* is what gets called with `a`. This is a deliberate,
useful consequence of reusing plain expression evaluation on the right
rather than restricting it to a bare function reference: it composes
naturally with `curry`, e.g. `3 |> curry(add, 2)(5)` evaluates
`curry(add, 2)(5)` to a partially-applied one-argument function first,
then calls it with `3`. Chaining is left-associative:
`a |> f |> g` is `(a |> f) |> g`, i.e. `g(f(a))` — matching `pipe`'s
own left-to-right order, not `compose`'s right-to-left one (the name
`|>` unambiguously suggests "pipe," not "compose").

**Precedence**: `|>` binds looser than every operator from `??`
(nullish-coalescing) down through the bitwise/arithmetic tiers, but
tighter than the ternary `? :` and assignment — the loosest of the
"value-producing" binary operators, just above the two forms that
build a whole expression around another expression. This lets a
piped chain be used directly as a condition or assigned value without
parentheses: `let y = a |> f;`, `cond ? a |> f : b`. Left-associative,
via a `while`-loop entry exactly like `_or`/`_and`, not a
right-recursive one like `??`.

**Lexing** (`cinder/lexer.py`): add `PIPE_ARROW` to `TokenType` in
`cinder/tokens.py` (near `PIPE`/`PIPEEQ`, following the descriptive-name
convention `FAT_ARROW`/`QUESTION_DOT` already use rather than a
char-concatenated one). In `_op_or_compound_assign`, add a check for
`char == "|" and self._match(">")` alongside the existing `char == "*"`/
`char == "/"` two-char special cases at the top of the function, before
the generic compound-assign (`|=`) and simple (`|`) fallback paths:

```python
if char == "|" and self._match(">"):
    self.tokens.append(Token(TokenType.PIPE_ARROW, "|>", None, start_line, start_col))
    return
```

No change needed to `_COMPOUND_ASSIGN_TOKENS` or the `_match("=")`/`else`
fallback below it — `|=` and bare `|` still reach those unchanged for
every input that isn't `|>`.

**Parsing** (`cinder/parser.py`): no new AST node — `|>` reuses `Binary`
exactly like `IN`/`NOT_IN` already do, dispatched purely by
`operator.type` at evaluation time. Add a new precedence level between
`_ternary` and `_nullish`:

```python
def _pipe(self) -> Expr:
    expr = self._nullish()
    while self._check(TokenType.PIPE_ARROW):
        operator = self._advance()
        right = self._nullish()
        expr = Binary(expr, operator, right)
    return expr
```

and change `_ternary`'s first line from `expr = self._nullish()` to
`expr = self._pipe()` (search for `def _ternary`, right at the top of
the method) — its two recursive `self._ternary()` calls for the `then`/
`else` branches need no changes, since they already route through the
new level for free. No other precedence method changes.

**Evaluation** (`cinder/interpreter.py`): in `_apply_binary_operator`
(search for `def _apply_binary_operator`), add a branch dispatching to
the module-level `call_value` helper (already used by `_evaluate_call`
and by builtins like `map`/`filter`/`pipe`/`compose` to invoke a Cinder
function value from Python):

```python
if op == TokenType.PIPE_ARROW:
    return call_value(right, [left], operator.line, operator.column)
```

Placed anywhere in the `if`/`elif` chain (order doesn't matter — each
branch checks a distinct `op` value); grouping it near the top by the
other non-arithmetic operators (`IN`/`NOT_IN`) reads best. `left`/
`right` are already evaluated by `_evaluate_binary` before
`_apply_binary_operator` is called (line ~1055-1057), exactly like
every other operator — no special-casing needed there. `call_value`
already raises `"<type> is not callable"` when `right` isn't callable
and the normal arity-mismatch message when it doesn't accept exactly
one argument, so both error paths are free.

Acceptance criteria:
- `fn double(x) { return x * 2; } print(5 |> double);` prints `10`.
- `fn double(x) { return x * 2; } fn inc(x) { return x + 1; }
  print(5 |> double |> inc);` prints `11` — `double(5)` is `10`,
  `inc(10)` is `11`; confirms left-associative, left-to-right chaining
  (matching `pipe`, not `compose`).
- `print(-5 |> abs);` prints `5` — works with a builtin, not just
  user-defined functions.
- `fn add(a, b) { return a + b; } print(3 |> curry(add, 2)(5));`
  prints `8` — the right side is evaluated as a full expression first
  (`curry(add, 2)(5)` produces a one-argument partial application),
  *then* called with the left side; not Elixir-style argument
  insertion.
- `let y = 5 |> abs; print(y);` prints `5` — usable directly as a `let`
  initializer with no parentheses needed, confirming the precedence
  sits above assignment's right-hand side.
- `print(true ? 5 |> abs : 0);` prints `5` — usable directly inside a
  ternary branch with no parentheses, confirming the precedence sits
  below `? :`.
- `print(5());` (unrelated call-on-a-non-function case) still raises
  `CinderRuntimeError` matching `"int is not callable"`, unchanged —
  confirms `call_value`'s existing error path is untouched, only
  reused.
- `print(5 |> 3);` raises `CinderRuntimeError` matching
  `"int is not callable"` — the same message, reached via the new
  operator instead of a direct call.
- `fn one() { return 1; } print(5 |> one);` raises `CinderRuntimeError`
  matching `"one() expects 0 argument(s), got 1"` — ordinary arity
  checking still applies to the implicit one-argument call.
- `print(5 |>);` raises `ParseError` (missing right operand) — the
  same "expected an expression" family of error every other binary
  operator already raises when its right side is missing, not a crash.
- `let x = 5; x |= 3; print(x);` prints `7` — bitwise-or compound
  assignment (`|=`) is completely unaffected, confirming the lexer's
  new `|>` branch doesn't shadow the existing `|=`/`|` paths for any
  input that isn't literally `|>`.
- `print(5 | 3);` prints `7` — bare bitwise-or is unaffected.
- Full test suite passes.

Likely files: `cinder/tokens.py` (`PIPE_ARROW`), `cinder/lexer.py`
(`_op_or_compound_assign`), `cinder/parser.py` (new `_pipe`, one-line
change in `_ternary`), `cinder/interpreter.py`
(`_apply_binary_operator`), `tests/test_lexer.py` (new `|>` tokenizing
tests alongside the existing `|`/`|=` ones), `tests/test_parser.py`
(shape assertions for the new precedence level, search for
`test_ternary` / `test_nullish` for the sibling pattern to follow),
`tests/test_interpreter.py` (the pipe/chaining/error-path tests above).
Once merged, `README.md`'s Operators bullet needs a `|>` mention added
near the `pipe`/`compose` builtins it complements, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `is_semiprime` — product of exactly two primes

Build: the breadth task after task 5's depth work (pipe operator) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that `prime_factors` has landed via PR #250, dropping the
count to the 5-task floor. Add `is_semiprime(n)` to `cinder/builtins.py`,
registered right after `is_composite` (search for `def _is_composite`,
immediately before `is_emirp` in the prime-classification cluster) — a
positive integer is semiprime when it is the product of exactly two
primes, counted **with multiplicity** (so `4 = 2 * 2` counts, same as
`6 = 2 * 3`), the natural third member of the `is_prime`/`is_composite`
classification trio: `is_prime` answers "exactly one prime factor",
`is_semiprime` answers "exactly two", `is_composite` answers "more than
one" (a strict superset that `is_semiprime` narrows). Verify the gap:
`python3 -m cinder.cli eval 'print(is_semiprime(4));'` currently raises
`CinderRuntimeError` `"undefined name 'is_semiprime'"` — no such builtin
exists yet.

```python
def _is_semiprime(arguments: list, line: int, column: int) -> object:
    _require_arity("is_semiprime", arguments, 1, line, column)
    value = _require_int("is_semiprime", arguments[0], line, column)
    if value < 2:
        return False
    remaining = value
    factor_count = 0
    divisor = 2
    while divisor * divisor <= remaining:
        while remaining % divisor == 0:
            remaining //= divisor
            factor_count += 1
            if factor_count > 2:
                return False
        divisor += 1
    if remaining > 1:
        factor_count += 1
    return factor_count == 2
```

Model the arity/type-checking exactly on `is_prime`/`is_composite`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). `n < 2`
returns `false` rather than raising, matching the boolean-predicate
cluster's own convention (`is_prime`, `is_composite`, `is_pronic`, etc. —
*not* the divisor cluster's type-vs-domain-error convention, since this
builtin returns a boolean, not a number). The early `factor_count > 2`
return keeps the loop cheap for highly composite inputs (e.g. a large
power of two bails after the third factor rather than fully
factoring); trial division only needs to go up to `sqrt(remaining)`
because once `remaining` itself is prime and larger than that bound,
the final `if remaining > 1: factor_count += 1` step accounts for it as
one last factor — this is the same "peel small factors, then check what's
left" shape `prime_factors` already uses, just counting instead of
collecting.

Acceptance criteria:
- `is_semiprime(4);` is `true` — `4 = 2 * 2`, two prime factors with
  multiplicity.
- `is_semiprime(6);` is `true` — `6 = 2 * 3`.
- `is_semiprime(9);` is `true` — `9 = 3 * 3`.
- `is_semiprime(25);` is `true` — `25 = 5 * 5`.
- `is_semiprime(15);` is `true` — `15 = 3 * 5`.
- `is_semiprime(2);` is `false` — prime, only one factor.
- `is_semiprime(12);` is `false` — `12 = 2 * 2 * 3`, three factors with
  multiplicity, exercises the early `factor_count > 2` bailout.
- `is_semiprime(1);` is `false` — no prime factors at all.
- `is_semiprime(0);` is `false` — below the domain floor.
- `is_semiprime(-6);` is `false` — negative input, same convention as
  `is_prime`/`is_composite`.
- `is_semiprime(999983 * 999979);` is `true` — a large product of two
  distinct large primes, exercising the `remaining > 1` tail branch
  where `remaining` itself ends up prime and above the `sqrt` bound.
- `is_semiprime(5.0);` raises `CinderRuntimeError` matching
  `"is_semiprime() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_semiprime(true);` raises `CinderRuntimeError` matching
  `"is_semiprime() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_composite`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestIsComposite` test
class, search for `class TestIsComposite`). Once merged, `README.md`'s
Builtins bullet needs `is_semiprime` added near `is_prime`/
`is_composite`, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## 6. Language: uninitialized `let` declarations (`let x;`, defaults to `nil`)

Build: the depth task after task 5's breadth work (`is_semiprime`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that hole elements in list-destructuring patterns has
landed via PR #251, dropping the count to the 5-task floor. Today
every `let` declaration requires an initializer —
`cinder/parser.py`'s `_let_statement` unconditionally calls
`self._consume(TokenType.EQ, "'=' after variable name")` right after
the identifier — so there is no way to declare a variable and assign
it later, forcing a throwaway placeholder value (`let x = nil;`,
`let total = 0;`) purely to satisfy the parser even when the real
initial value is only known conditionally (e.g. set inside a following
`if`/`else`). Verify the gap: `python3 -m cinder.cli eval 'let x;
print(x);'` currently raises `ParseError` `"expected '=' after
variable name, found ';'"`.

**Parsing** (`cinder/parser.py`): in `_let_statement`, after consuming
the identifier, only require `=` plus an initializer expression when
the next token isn't `;` — otherwise default the initializer to a
bare `nil` literal:

```python
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'let'")
        if self._check(TokenType.SEMICOLON):
            initializer: Expr = Literal(None, name_token.line, name_token.column)
        else:
            self._consume(TokenType.EQ, "'=' after variable name")
            initializer = self._assignment()
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        return LetStmt(name_token.lexeme, initializer, let_token.line, let_token.column)
```

No AST change is needed — `LetStmt.initializer` is already a plain
`Expr`, and `Literal(None, ...)` is exactly the node the parser
already builds for the `nil` keyword itself (search `token.type ==
TokenType.NIL` in `_primary`), so the interpreter's existing `LetStmt`
branch in `execute` (`env.define(stmt.name, self.evaluate(stmt.initializer,
env))`) needs no changes at all.

`const` is deliberately **not** touched — `_const_statement` keeps
requiring an initializer unconditionally, since an immutable binding
that starts out unassigned would defeat the purpose of `const` (there
would be no way to ever give it a real value); this is already locked
in by the existing `test_const_missing_initializer_raises` test, which
must keep passing unmodified.

This also affects the C-style `for` loop's init clause for free, since
`_for_statement` already calls `self._let_statement()` to parse it
(search `init = self._let_statement()  # consumes its own trailing
';'`) — `for (let i; i < 3; i++) { ... }` becomes parseable, though it
correctly raises a runtime type error on the first comparison (`nil <
3`) rather than being a useful thing to write; no special-casing is
needed for this to behave correctly.

Acceptance criteria:
- `let x; print(x);` prints `nil` — a bare `let x;` binds `x` to
  `nil`.
- `let x; x = 5; print(x);` prints `5` — the binding is mutable and
  assignable afterward, same as any other `let`.
- `let x = 1; print(x);` still prints `1` — the initialized form is
  completely unchanged.
- `let ran = false; if (true) { let x; x = 1; ran = x == 1; }
  print(ran);` prints `true` — a realistic use case: declare, then
  conditionally assign inside a branch.
- `fn f() { let x; return x; } print(f());` prints `nil` — works
  inside function bodies too, not just top-level.
- `const x;` still raises `ParseError` — unaffected, confirms `const`
  did not accidentally inherit the optional-initializer behavior.
- `let x 1;` (a genuinely missing `=` before a non-`;` token) still
  raises the same `ParseError` ("expected '=' after variable name") it
  does today — confirms this isn't silently accepted.
- `let x = 1` (missing trailing `;`) still raises `ParseError` —
  unaffected.
- Every pre-existing `let`/destructuring-`let` test continues to pass
  unmodified.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_let_statement`),
`tests/test_parser.py` (search `test_let_statement`,
`test_let_missing_equals_raises` — add a new shape test for the bare
`let x;` form asserting the initializer is `("Literal", None)`),
`tests/test_interpreter.py` (new tests modeled on the acceptance
criteria above, search for `def test_let_` or `class ... Let`). Once
merged, `README.md`'s Variables & scope bullet needs a mention of
uninitialized `let` declarations added near the existing `let`/`const`
description, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
