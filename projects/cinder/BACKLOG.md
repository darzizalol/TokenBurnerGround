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

## 1. Standard library: `harmonic_mean` — the third Pythagorean mean, completing arithmetic/geometric/harmonic

Build: the breadth task after task 5's depth work (list concatenation
via `+`) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `geometric_mean` has landed via
PR #262, dropping the count to the 5-task floor. Add `harmonic_mean`
to `cinder/builtins.py`, registered right after `geometric_mean`
(search for `def _geometric_mean`, immediately before `_median`) — the
statistics cluster (`mean`, `median`, `variance`, `std_dev`, `mode`)
grew a second "kind of average" when `geometric_mean` landed; the
classical Pythagorean means come in threes (arithmetic, geometric,
harmonic), and `harmonic_mean` is the one still missing. Verify the
gap: `python3 -m cinder.cli eval 'print(harmonic_mean([1, 2, 4]));'`
currently raises `CinderRuntimeError` `"undefined name
'harmonic_mean'"` — no such builtin exists yet.

```python
def _harmonic_mean(arguments: list, line: int, column: int) -> object:
    _require_arity("harmonic_mean", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"harmonic_mean() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("harmonic_mean() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"harmonic_mean() requires a list of numbers, got {type_name(element)}", line, column
            )
        if element <= 0:
            raise CinderRuntimeError(
                "harmonic_mean() requires all elements to be positive", line, column
            )
    reciprocal_sum = 0
    for element in value:
        reciprocal_sum = reciprocal_sum + 1 / element
    return len(value) / reciprocal_sum
```

Model this directly on `_geometric_mean`'s own structure: same
`isinstance(value, list)` check, same non-empty check, same per-element
`_is_numeric` check followed by the same strictly-positive domain
check (checked only after confirming an element is numeric, so a
non-numeric element always reports first, exactly as `geometric_mean`
already does) — copy that validation loop verbatim rather than
inventing a new shape for it. The one substantive difference is the
final computation: `geometric_mean` multiplies elements then takes an
nth root, `harmonic_mean` sums reciprocals then divides `len(value)` by
that sum. Positivity is required for the same reason `geometric_mean`
requires it, plus one more: a zero element makes the reciprocal sum
undefined (division by zero on `1 / element`), and a negative element
would make the result not comparable to its arithmetic/geometric
siblings under the AM-GM-HM inequality (`harmonic_mean <=
geometric_mean <= mean` for any list of positive numbers) — so this
follows the exact same "raise a domain error rather than leak a
`ZeroDivisionError` or a sign-confused result" convention
`geometric_mean` already established, not a new decision. A
single-element list is trivially its own harmonic mean (the loop runs
once, `len(value) / (1 / value[0])` reduces to `value[0]`), the same
trivial-degenerate-case convention `mean`/`geometric_mean` already
establish.

Acceptance criteria:
- `harmonic_mean([1]);` is `1` — single-element list, trivially itself.
- `harmonic_mean([2, 2, 2, 2]);` is `2` — a constant list's harmonic
  mean equals the constant, same as `mean`/`geometric_mean` on a
  constant list.
- `harmonic_mean([1, 4]);` is `1.6` — matches the classical two-element
  identity `2ab / (a + b)` (`2 * 1 * 4 / (1 + 4) == 1.6`), a useful
  cross-check independent of the general `n / sum(1/x)` formula.
- `harmonic_mean([1, 2, 4]);` is approximately `1.7142857142857142`
  (`3 / (1 + 0.5 + 0.25)`).
- For `[1, 2, 4]`, `harmonic_mean(...) <= geometric_mean(...) <=
  mean(...)` all hold (`1.714... <= 2.0 <= 2.333...`) — the AM-GM-HM
  inequality, confirming the three statistics-cluster "averages" are
  internally consistent with each other, not just individually correct.
- `harmonic_mean([]);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires a non-empty list"`.
- `harmonic_mean([1, "a"]);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires a list of numbers, got string"`.
- `harmonic_mean([1, 0]);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires all elements to be positive"` — zero
  excluded (undefined via division by zero), not silently treated as
  infinite or skipped.
- `harmonic_mean([1, -2]);` raises the same domain-error message —
  negative excluded, same convention as `geometric_mean`.
- `harmonic_mean(5);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires a list, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `geometric_mean`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestGeometricMean` test
class, search `class TestGeometricMean`). Once merged, `README.md`'s
Builtins bullet needs `harmonic_mean` added near `mean`/
`geometric_mean`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 2. Language: trailing commas in destructuring patterns

Build: the depth task after task 5's breadth work (`harmonic_mean`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that postfix `++`/`--` as a first-class assignment
expression has landed via PR #263, dropping the count to the 5-task
floor. Task 2 in this same backlog (trailing commas in list/map
literals, call arguments, and function parameter lists) deliberately
scoped out destructuring patterns and left them "as a candidate for a
future, separately-scoped task if still desired" — this is that task.
`cinder/parser.py`'s `_destructure_list_pattern` (`let`/`for`/function
params/comprehension loop variables, list-pattern half),
`_destructure_map_pattern` (the same forms, map-pattern half), and
`_try_map_destructure_assign_statement` (the plain-assignment map form,
`{a, b} = expr;`) each have their own comma-loop, structurally
identical to the four sites task 2 already fixed, with the same gap: a
comma immediately before the closing delimiter is a hard `ParseError`
instead of being silently accepted. Verify the gap (task 2 must have
landed first, so `_list_literal`/`_map_literal` already accept trailing
commas — every failure below is specifically the destructuring-pattern
parsers, not the literal parsers):
```sh
python3 -m cinder.cli eval 'let [a, b,] = [1, 2]; print(a); print(b);'
# -> ParseError: expected identifier in destructuring pattern, found ']'
python3 -m cinder.cli eval 'let {a, b,} = {"a": 1, "b": 2}; print(a); print(b);'
# -> ParseError: expected identifier in destructuring pattern, found '}'
python3 -m cinder.cli eval 'let a = 0; let b = 0; {a, b,} = {"a": 1, "b": 2}; print(a); print(b);'
# -> ParseError: expected ';' after expression, found ',' (the trailing comma
#    inside `_try_map_destructure_assign_statement` breaks its own
#    try/except ParseError -> return None fallback, so `_brace_statement`
#    falls all the way through to `_block()`, which produces this
#    unrelated-looking error trying to parse `{a, b,} = ...` as statements)
python3 -m cinder.cli eval 'for [k, v,] in items({"a": 1}) { print(k); print(v); }'
# -> ParseError: expected identifier in destructuring pattern, found ']'
python3 -m cinder.cli eval 'fn f([a, b,]) { return a + b; } print(f([1, 2]));'
# -> ParseError: expected identifier in destructuring pattern, found ']'
python3 -m cinder.cli eval 'print([k for [k, v,] in items({"a": 1})]);'
# -> ParseError: expected identifier in destructuring pattern, found ']'
```
Note: the plain-assignment **list**-destructure form (`[a, b,] = expr;`)
is not one of the sites above and needs no change here — it parses its
pattern by first parsing an ordinary `ListLiteral` via `_list_literal`
(task 2's own site) and then validating its elements in
`_destructure_assign_pattern`, so once task 2 lands, `[a, b,] = expr;`
already works for free the same way `xs += [3, 4]` started working for
free once list-plus-`+` landed — nothing to touch in this task.

**Parsing**: in each of the three sites' comma-loops, after consuming
the comma, check whether the very next token is that site's closing
delimiter and `break` instead of trying to parse another pattern
element — the exact same shape task 2 used, placed *before* the
existing "a rest element must be last" check so a trailing comma right
after a rest element (`let [a, ...rest,] = expr;`,
`let {a, ...rest,} = expr;`) breaks cleanly instead of tripping that
check, mirroring how task 2 handled `fn f(a, ...rest,) { ... }` for
`_fn_param_list`. For `_destructure_list_pattern`:
```python
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACKET):
                break
            if rest is not None:
                token = self._peek()
                raise ParseError(...)
            ...
```
`_destructure_map_pattern` takes the identical shape with
`TokenType.RBRACE`; `_try_map_destructure_assign_statement`'s own
inlined loop (inside its `try` block, alongside the `_RestNotLast`
marker-exception handling already there) gets the same `RBRACE` check
in the same position.

One real edge case to get right, not just a mechanical copy-paste: list
patterns already support a "hole" element (`let [a, , c] = expr;`,
`_destructure_list_pattern_entry` treats a `COMMA` appearing where an
element is expected as an empty slot rather than raising). Because the
new break check runs *before* the next element is parsed, a pattern
ending in "hole then trailing comma" (`let [a, ,] = [1, 2];` — two
commas, nothing named after the second one) is *not* caught by the
break on the first of those two commas (the token right after it is
another `COMMA`, not `]`), so it falls through to the existing hole
logic and registers as an ordinary hole, and *is* caught by the break
on the second comma (the token right after it is `]`). Net effect:
`let [a, ,] = [1, 2];` newly parses successfully as `a` bound to `1`
and a second, skipped position — the same result `let [a, ,] =` would
already give for a *middle* hole, just applied to the last position —
rather than continuing to raise `ParseError` as it does today. This is
an intentional, narrow behavior change (call it out in the PR body) and
is the correct reading: a hole is a hole regardless of position, and
the trailing comma after it is the same optional decoration the rest of
this task adds everywhere else. Map patterns have no hole concept, so
no equivalent case exists on that side.

Acceptance criteria:
- `let [a, b,] = [1, 2]; print(a); print(b);` prints `1` then `2` — no
  longer a `ParseError`.
- `let [a,] = [1]; print(a);` prints `1` — single-element trailing
  comma.
- `let [a, ...rest,] = [1, 2, 3]; print(a); print(rest);` prints `1`
  then `[2, 3]` — trailing comma right after a rest element is
  accepted, not treated as a second element following the rest one.
- `let [a, ...rest, b] = [1, 2, 3];` still raises `ParseError` matching
  `"rest element must be last in destructuring pattern"` — confirms a
  *real* element after the rest one is still rejected, only a bare
  trailing comma with nothing after it is now accepted.
- `let [a, ,] = [1, 2]; print(a);` prints `1` — the hole-then-trailing-
  comma edge case above, now accepted rather than raising.
- `let {a, b,} = {"a": 1, "b": 2}; print(a); print(b);` prints `1` then
  `2`.
- `let {a,} = {"a": 1}; print(a);` prints `1` — single-entry trailing
  comma.
- `let {a, ...rest,} = {"a": 1, "b": 2}; print(a); print(rest);` prints
  `1` then `{"b": 2}` — trailing comma right after a map rest element.
- `let a = 0; let b = 0; {a, b,} = {"a": 1, "b": 2}; print(a); print(b);`
  prints `1` then `2` — the plain-assignment map form.
- `for [k, v,] in items({"a": 1}) { print(k); print(v); }` prints `a`
  then `1`.
- `for {a, b,} in [{"a": 1, "b": 2}] { print(a); print(b); }` prints `1`
  then `2`.
- `fn f([a, b,]) { return a + b; } print(f([1, 2]));` prints `3`.
- `fn f({a, b,}) { return a + b; } print(f({"a": 1, "b": 2}));` prints
  `3`.
- `print([k for [k, v,] in items({"a": 1})]);` prints `["a"]`.
- `print([a for {a, b,} in [{"a": 1, "b": 2}]]);` prints `[1]`.
- `let [a, b,] = [1, 2]; print(a); print(b);` (the plain-list-assignment
  free-ride case from task 2) prints `1` then `2` — confirms it works
  without any change in this task.
- Every pre-existing destructuring test (defaults, holes, rest
  elements, renames, all five forms — `let`, plain assignment, `for`,
  function params, both comprehension loop-variable forms) continues to
  pass unmodified, without a trailing comma.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_list_pattern`,
`_destructure_map_pattern`, `_try_map_destructure_assign_statement`),
`tests/test_parser.py` and `tests/test_interpreter.py` (model on the
existing destructuring test classes — search `class TestDestructureLet`,
`class TestDestructureLetMap`, `class TestDestructureAssignMap`,
`class TestForDestructuring`, `class TestDestructuringParams`). Once
merged, `README.md`'s destructuring bullets don't strictly need a new
sentence (trailing commas are a silent parser acceptance, not a new
capability worth a separate callout, the same treatment task 2's
merge gave `README.md`), but `PROJECT.md`'s roadmap paragraph needs
this moved from backlog to landed — leave that to the Architect's next
grooming pass, not this task.

---

## 3. Standard library: `multiplicative_persistence` — the loop-driven counterpart to `digital_root`

Build: the breadth task after task 5's depth work (trailing commas in
destructuring patterns) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `digit_product` has
landed via PR #264, dropping the count to the 5-task floor. Add
`multiplicative_persistence(n)` to `cinder/builtins.py`, registered
right after `digit_product` (search for `def _digit_product`,
immediately before `_reverse_int`) — the number of times a number's own
decimal digits must be repeatedly multiplied together before the
result drops to a single digit, e.g. `39 -> 27 -> 14 -> 4` is three
multiplications, so `multiplicative_persistence(39)` is `3`. This is
the natural loop-driven counterpart to `digital_root`'s closed-form
*additive* reduction (`1 + (n - 1) % 9`): no closed form exists for the
multiplicative case, so this genuinely needs an iterative loop rather
than a formula — the first builtin in the digit-transform cluster that
does. Verify the gap: `python3 -m cinder.cli eval
'print(multiplicative_persistence(39));'` currently raises
`CinderRuntimeError` `"undefined name 'multiplicative_persistence'"` —
no such builtin exists yet.

```python
def _multiplicative_persistence(arguments: list, line: int, column: int) -> object:
    _require_arity("multiplicative_persistence", arguments, 1, line, column)
    value = _require_int("multiplicative_persistence", arguments[0], line, column)
    value = abs(value)
    steps = 0
    while value >= 10:
        product = 1
        for digit in str(value):
            product *= int(digit)
        value = product
        steps += 1
    return steps
```

Model the arity/type-checking on `digit_product`'s own structure:
`_require_arity`, then `_require_int`. Discard the sign via `abs()`
exactly once, up front — not re-derived every iteration, since the
running product is already non-negative once the first step completes
(matching `digit_sum`/`digit_product`'s own "discard sign once" shape,
just applied before a loop instead of before a single pass). Each
iteration's digit-multiply step inlines the same per-digit walk
`digit_product` itself uses rather than calling the `digit_product`
builtin directly — the established "inline rather than call the
dispatch-signature builtin" approach `is_emirp`/`is_amicable` already
take with `is_composite`/`reverse_int`/`_aliquot_sum`, needed here
because `digit_product`'s registered form takes the builtin-dispatch
`(arguments, line, column)` signature, not a raw `int`. Any `0` digit
inside a step collapses that step's product to `0`, which then
terminates the loop on the very next check (`0 < 10`) — the correct
behavior, not a case needing a guard, mirroring how `digit_product`
itself treats a `0` digit as collapsing the whole product rather than
as an error.

Acceptance criteria:
- `multiplicative_persistence(0);` is `0` — single digit, already
  terminated.
- `multiplicative_persistence(4);` is `0` — any single digit `0`-`9` is
  its own trivial base case.
- `multiplicative_persistence(10);` is `1` — `1 * 0 = 0`, one step (a
  `0` digit collapses the product immediately).
- `multiplicative_persistence(39);` is `3` — `39 -> 27 -> 14 -> 4`.
- `multiplicative_persistence(999);` is `4` — `999 -> 729 -> 126 -> 12
  -> 2`.
- `multiplicative_persistence(77);` is `4` — `77 -> 49 -> 36 -> 18 ->
  8`.
- `multiplicative_persistence(-39);` is `3` — same as `39`, sign
  discarded, matching `digit_sum`/`digit_product`'s own convention.
- `multiplicative_persistence(5.0);` raises `CinderRuntimeError`
  matching `"multiplicative_persistence() requires an int, got float"`
  — the same message shape `_require_int` already produces elsewhere.
- `multiplicative_persistence(true);` raises `CinderRuntimeError`
  matching `"multiplicative_persistence() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_product`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestDigitProduct` test
class, search `class TestDigitProduct`). Once merged, `README.md`'s
Builtins bullet needs `multiplicative_persistence` added near
`digit_sum`/`digit_product`/`digital_root`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s roadmap paragraph needs this
moved from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 4. Language: comma-separated multiple variable declarations in a single `let`/`const` statement

Build: the depth task after task 4's breadth work
(`multiplicative_persistence`) per `PROJECT.md`'s breadth-vs-depth
policy, restocking the backlog back toward its 6-task target now that
both `feat/20260817-trailing-commas` (PR #265) and
`feat/20260817-is-evil-odious` (PR #266) landed in the same cycle,
dropping the count from 6 to 4 at once — two tasks are being added this
pass to restock past the 5-task floor, the same "restock faster than
strict alternation" move the roadmap history already documents for
`aliquot_sum`/`is_perfect_cube` and `collatz_length`/`is_strong_number`.
Today every `let`/`const` statement declares exactly one name:
`cinder/parser.py`'s `_let_statement`/`_const_statement` each consume
one `IDENTIFIER`, an optional (`let`) or required (`const`) `=
initializer`, then go straight to `;` — a comma there is a hard
`ParseError`, unlike most C-family languages, which let a single `let`/
`var`/`const` introduce several names at once. Verify the gap:
```sh
python3 -m cinder.cli eval 'let a = 1, b = 2; print(a); print(b);'
# -> ParseError: expected ';' after variable declaration, found ','
python3 -m cinder.cli eval 'let a, b; print(a); print(b);'
# -> ParseError: expected '=' after variable name, found ','
python3 -m cinder.cli eval 'const a = 1, b = 2; print(a); print(b);'
# -> ParseError: expected ';' after variable declaration, found ','
```

**The key design constraint**: the two declared names must land in the
*same* scope a single `let a = 1;` would use, not a nested one — so this
cannot be implemented by wrapping multiple `LetStmt`s in the existing
`Block` node, since `execute()`'s `Block` case (`cinder/interpreter.py`)
opens a fresh child `Environment` before running its statements, which
would make `b` invisible the instant the statement ends. Add a new,
narrower AST node instead — `DeclSeq` in `cinder/ast_nodes.py`, next to
`Block`:
```python
@dataclass(frozen=True)
class DeclSeq:
    declarations: list
    line: int
    column: int
```
and one new `execute()` branch in `cinder/interpreter.py`, next to the
existing `Block` case, that deliberately does *not* open a new
`Environment`:
```python
        if isinstance(stmt, DeclSeq):
            for declaration in stmt.declarations:
                self.execute(declaration, env)
            return
```
Since each `declaration` is an ordinary `LetStmt`/`ConstStmt`, and
`execute()`'s existing `LetStmt`/`ConstStmt` cases already call
`env.define(...)`/`env.define_const(...)` directly on whatever `env`
they're given, running them in sequence against the *same* `env` — not
a per-declaration child one — is exactly what makes both names end up
side by side in the caller's scope.

**Parsing**: factor `_let_statement`'s existing single-declaration body
(identifier, optional `=` initializer, defaulting to a `nil` `Literal`
when omitted — the uninitialized-`let` behavior already landed) out
into a small helper, then loop it on a trailing comma:
```python
    def _let_statement(self) -> Stmt:
        let_token = self._advance()
        if self._check(TokenType.LBRACKET):
            return self._destructure_let_statement(let_token, is_map=False)
        if self._check(TokenType.LBRACE):
            return self._destructure_let_statement(let_token, is_map=True)
        declarations = [self._one_let_declaration(let_token)]
        while self._check(TokenType.COMMA):
            self._advance()
            declarations.append(self._one_let_declaration(let_token))
        self._consume(TokenType.SEMICOLON, "';' after variable declaration")
        if len(declarations) == 1:
            return declarations[0]
        return DeclSeq(declarations, let_token.line, let_token.column)

    def _one_let_declaration(self, let_token: Token) -> LetStmt:
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'let'")
        if self._check(TokenType.SEMICOLON) or self._check(TokenType.COMMA):
            initializer: Expr = Literal(None, name_token.line, name_token.column)
        else:
            self._consume(TokenType.EQ, "'=' after variable name")
            initializer = self._assignment()
        return LetStmt(name_token.lexeme, initializer, let_token.line, let_token.column)
```
`_const_statement` gets the identical shape, except its per-declaration
helper unconditionally requires `= initializer` (no `check(COMMA)`/
`check(SEMICOLON)` bypass) — `const` already has no uninitialized form
today, and this task doesn't add one. Returning the lone `LetStmt`/
`ConstStmt` directly when there's exactly one declaration (rather than
always wrapping in `DeclSeq`) keeps every existing single-declaration
call site — including `_for_c_statement`'s `init = self._let_statement()`
— seeing exactly the same `Stmt` shape it does today, so nothing else
needs to change to avoid a regression.

**A verified, free side effect, not extra work**: `_for_c_statement`'s
C-style for-loop init clause already calls `self._let_statement()`
directly, and `_execute_for_c` already runs `self.execute(stmt.init,
loop_env)` generically — it never pattern-matches on `LetStmt`
specifically, it just executes whatever statement `init` is and then
copies the resulting `loop_env._values` wholesale into each iteration's
environment. Since `DeclSeq` is executed by this same generic
`self.execute(...)` dispatch, `for (let i = 0, j = 3; i < j; i = i + 1)
{ ... }` starts working the moment this lands, with no change to
`_execute_for_c` itself — the same "reuses existing generic dispatch,
nothing else to touch" shape `xs += [3, 4]` got for free once list
`+` landed.

Acceptance criteria:
- `let a = 1, b = 2; print(a); print(b);` prints `1` then `2`.
- `let a, b; print(a); print(b);` prints `nil` then `nil` — each
  omitted initializer defaults independently, same as a single
  `let a;` already does.
- `let a = 1, b; print(a); print(b);` prints `1` then `nil` — mixing
  initialized and uninitialized declarations in the same statement.
- `let a = 1, b = a + 1; print(b);` prints `2` — a later initializer in
  the same statement can already see an earlier name, evaluated
  left-to-right, the same convention list/map-destructuring defaults
  already established.
- `let a = 1, b = 2; a = 3; print(a); print(b);` prints `3` then `2` —
  confirms both names land in the *same* scope a single `let` would,
  not a nested `Block` scope, and both stay visible and mutable after
  the statement.
- `const a = 1, b = 2; print(a); print(b);` prints `1` then `2`.
- `const a = 1, b = 2; a = 3;` raises `CinderRuntimeError` matching the
  existing const-reassignment message — confirms both bindings are
  real `const`s, not silently `let`.
- `const a = 1, b;` raises `ParseError` matching `"'=' after variable
  name"` — `const` still requires every declaration to have its own
  initializer, comma-separated or not.
- `for (let i = 0, j = 3; i < j; i = i + 1) { print(i); print(j); }`
  prints `0`/`3`, `1`/`3`, `2`/`3` on three lines — the C-style
  for-loop free side effect above.
- `let [a, b] = [1, 2];` and `let {a, b} = {"a": 1, "b": 2};` still work
  exactly as before, unaffected (the comma-loop only wraps the plain
  single-identifier form; `_destructure_let_statement` returns before
  reaching it).
- Every pre-existing single-declaration `let`/`const`/uninitialized-`let`
  test continues to pass unmodified.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `DeclSeq`), `cinder/parser.py`
(`_let_statement`, `_const_statement`, new `_one_let_declaration`/
equivalent const helper), `cinder/interpreter.py` (`execute()`'s new
`DeclSeq` branch, placed near the `Block` case but explicitly not
opening a new `Environment`), `tests/test_parser.py` and
`tests/test_interpreter.py` (model on `class TestAssignment`, `class
TestForCStatement`, and whatever test currently covers uninitialized
`let`). Once merged, `README.md`'s Variables & scope bullet needs a
mention of comma-separated multi-declaration, and `PROJECT.md`'s
roadmap paragraph needs this moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `cbrt` — real cube root, the domain-unrestricted sibling to `sqrt`

Build: the breadth task after task 5's depth work (comma-separated
`let`/`const` declarations), restocking the backlog the rest of the way
back to its 6-task target in the same pass task 5 started (see task 5's
own build note on why two tasks were added at once this cycle). Add
`cbrt` to `cinder/builtins.py`, registered right after `_sqrt` (search
`def _sqrt`, immediately before `_sin`) — the math-builtins cluster
(`sqrt`, `sin`, `cos`, `tan`, `log`, `pow`, ...) has a square root but no
cube root, even though cube roots are real and defined for *every* real
number, negative ones included, unlike square roots. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(cbrt(27));'
# -> CinderRuntimeError: undefined name 'cbrt'
```

**The one correctness trap, verified directly against Python**: the
naive `value ** (1 / 3)` does *not* give a real result for a negative
base — Python's `**` returns a complex number the moment the base is
negative and the exponent is a non-integer float:
```sh
python3 -c "print((-8) ** (1 / 3))"
# -> (1.0000000000000002+1.7320508075688772j)
```
So `cbrt(-8)` must not be implemented as a bare `value ** (1 / 3)`; it
needs to take the magnitude's cube root and reapply the original sign,
the same `math.copysign` shape already used elsewhere in this file for
sign-preserving math:
```python
def _cbrt(arguments: list, line: int, column: int) -> object:
    _require_arity("cbrt", arguments, 1, line, column)
    value = arguments[0]
    if not _is_numeric(value):
        raise CinderRuntimeError(
            f"cbrt() requires a number, got {type_name(value)}", line, column
        )
    return math.copysign(abs(value) ** (1 / 3), value)
```
Unlike `_sqrt`, there is no domain check to add — every real number has
a real cube root, so `cbrt` accepts negative input the same way
`is_perfect_cube` already treats negative integers as potentially
`true` (`-8 = (-2)**3`), rather than raising the way `sqrt(-1)` does.

Acceptance criteria:
- `cbrt(27);` is `3.0` (a float, matching `sqrt`'s own always-float
  return convention).
- `cbrt(8);` is `2.0`.
- `cbrt(0);` is `0.0`.
- `cbrt(-27);` is `-3.0` — a real, negative result, not a `ParseError`,
  not a complex number, not the positive magnitude.
- `cbrt(2);` is approximately `1.2599210498948732`.
- `cbrt(-2);` is approximately `-1.2599210498948732` — same magnitude
  as `cbrt(2)`, sign flipped.
- `cbrt("a");` raises `CinderRuntimeError` matching `"cbrt() requires a
  number, got string"`.
- `cbrt(true);` raises `CinderRuntimeError` matching `"cbrt() requires
  a number, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `sqrt`, see current
line numbers — shift if task 5 landed first), `tests/test_builtins.py`
(model on `class TestSqrt`, search `class TestSqrt`). Once merged,
`README.md`'s Builtins bullet needs `cbrt` added near `sqrt`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave all three to
the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
