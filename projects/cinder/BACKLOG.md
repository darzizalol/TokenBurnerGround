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

## 1. Standard library: `nth_harshad` — Harshad number found at a 1-indexed position

Build: `is_harshad` (`cinder/builtins.py`, search `def _is_harshad`:
whether `n` is divisible by its own digit sum, e.g. `18`'s digits sum
to `9` and `18 % 9 == 0`) has no value-returning sibling that finds the
Harshad number at a given 1-indexed position — the same gap
`nth_abundant`/`nth_deficient` (search either name) already closed for
`is_abundant`/`is_deficient`, and `nth_semiperfect` already closed for
`is_semiperfect`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_harshad(1));'
# -> <eval>:1:7: undefined name 'nth_harshad'
```

Worked examples: the first ten Harshad numbers are `1, 2, 3, 4, 5, 6,
7, 8, 9, 10` (every one-digit number is trivially divisible by its own
digit sum), so `nth_harshad(1)` is `1` and `nth_harshad(10)` is `10`.
The next ones are `12, 18, 20, 21, 24, 27, 30, 36, 40, 42` — `11` is
skipped (`11 % (1+1) == 11 % 2 == 1`, not divisible), so `nth_harshad(20)`
is `42`.

Add to `cinder/builtins.py`, directly after `_is_harshad` (search `def
_is_harshad`):
```python
def _nth_harshad(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_harshad", arguments, 1, line, column)
    value = _require_int("nth_harshad", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_harshad() requires a positive integer, domain error", line, column
        )

    def _is_harshad_candidate(candidate: int) -> bool:
        digit_total = sum(int(digit) for digit in str(candidate))
        return candidate % digit_total == 0

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_harshad_candidate(candidate):
            count += 1
    return candidate
```
(The bounded sequential-scan shape mirrors `_nth_abundant`/`_nth_deficient`
exactly — search either name for the precedent — just with `_is_harshad`'s
own digit-sum divisibility check inlined instead of calling `_is_harshad`
directly, the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice those two already made.) Register it in the builtins dict
(search `"is_harshad": _is_harshad,`) right next to the existing entry:
`"nth_harshad": _nth_harshad,`.

Acceptance criteria:
- `nth_harshad(1)` through `nth_harshad(10)` are `1` through `10` — the
  first worked example above.
- `nth_harshad(20)` is `42` — the second worked example above.
- `is_harshad(nth_harshad(n))` is `true` for every `n` from `1` to `50`
  — the value returned is always actually a Harshad number, mirroring
  `test_nth_deficient_agrees_with_is_deficient`'s (search that name)
  cross-check style.
- `nth_harshad(0)` and `nth_harshad(-3)` raise `CinderRuntimeError`
  matching `"nth_harshad() requires a positive integer, domain error"`.
- `nth_harshad(true)` and `nth_harshad("3")` raise `CinderRuntimeError`
  with the standard `_require_int` type-mismatch message, and
  `nth_harshad(1, 2)` raises the standard arity error — regression
  coverage matching `nth_deficient`'s own bool/string/arity tests
  (search `test_nth_deficient_of_bool_raises`/
  `test_nth_deficient_of_string_raises`/`test_nth_deficient_wrong_arity_raises`).
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_harshad`,
search `def _is_harshad`), `tests/test_builtins.py` (new `class
TestNthHarshad`, modeled on `class TestNthDeficient`, search that name,
for the test shapes above — place it near the existing `class
TestIsHarshad`, search that name). Once merged, `README.md`'s Builtins
bullet needs `nth_harshad` added near `is_harshad`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Language: destructuring patterns for `const` declarations

Build: `let` already supports both list-destructuring (`let [a, b] =
expr;`) and map-destructuring (`let {a, b} = expr;`), with full nesting,
rest capture, per-key rename, per-entry defaults, and hole elements
(see the README's "Variables & scope" bullet). `const` has none of this
— only a single plain identifier is accepted after the keyword. Verify
the gap:
```sh
python3 -m cinder.cli eval 'const [a, b] = [1, 2]; print(a); print(b);'
# -> <eval>:1:7: expected identifier after 'const', found '['
python3 -m cinder.cli eval 'const {a, b} = {"a": 1, "b": 2}; print(a); print(b);'
# -> <eval>:1:7: expected identifier after 'const', found '{'
```

Worked examples: `const [a, b] = [1, 2]; print(a); print(b);` should
print `1` then `2`, exactly like the `let` equivalent, but with every
bound name frozen — `const [a, b] = [1, 2]; a = 3;` should raise the
same `CinderRuntimeError` a plain `const a = 1; a = 2;` already raises
today (`"cannot assign to const 'a'"`, see `TestConst
.test_const_reassignment_raises`, search that name). Same shape for map
patterns: `const {a, b} = {"a": 1, "b": 2};` binds both frozen.

Root cause and fix shape: `cinder/parser.py`'s `_const_statement`
(search `def _const_statement`) never checks for a leading `[`/`{`
the way `_let_statement` (search `def _let_statement`) already does —
it goes straight to `_one_const_declaration`, which demands a bare
`IDENTIFIER`. The parsing machinery to fix this already exists and
needs no changes of its own: `_destructure_let_statement` (search `def
_destructure_let_statement`) already parses either pattern kind via
`_destructure_list_pattern`/`_destructure_map_pattern` (search either
name) and builds a `DestructureLetStmt` — the exact same node `let`
produces — so it is a generic "parse a destructuring declaration"
helper in practice, not really `let`-specific despite its name. Give it
one new parameter and thread it through:
```python
def _destructure_let_statement(self, let_token: Token, is_map: bool, is_const: bool = False) -> Stmt:
    if is_map:
        names, rest = self._destructure_map_pattern()
    else:
        names, rest = self._destructure_list_pattern()
    self._consume(TokenType.EQ, "'=' after destructuring pattern")
    initializer = self._assignment()
    self._consume(TokenType.SEMICOLON, "';' after variable declaration")
    return DestructureLetStmt(
        names, initializer, let_token.line, let_token.column,
        is_map=is_map, rest=rest, is_const=is_const,
    )
```
and dispatch to it from `_const_statement` (search `def
_const_statement`) exactly the way `_let_statement` already dispatches
to it, with `is_const=True`:
```python
def _const_statement(self) -> Stmt:
    const_token = self._advance()
    if self._check(TokenType.LBRACKET):
        return self._destructure_let_statement(const_token, is_map=False, is_const=True)
    if self._check(TokenType.LBRACE):
        return self._destructure_let_statement(const_token, is_map=True, is_const=True)
    declarations = [self._one_const_declaration(const_token)]
    while self._check(TokenType.COMMA):
        self._advance()
        declarations.append(self._one_const_declaration(const_token))
    self._consume(TokenType.SEMICOLON, "';' after variable declaration")
    if len(declarations) == 1:
        return declarations[0]
    return DeclSeq(declarations, const_token.line, const_token.column)
```
(Only the first three lines are new; everything from
`declarations = [...]` on is unchanged, included so the replacement is
a drop-in for the whole function.) `DestructureLetStmt` (search `class
DestructureLetStmt` in `cinder/ast_nodes.py`) needs one new field,
defaulted so every existing `let`-produced instance is unaffected:
`is_const: bool = False`.

The interpreter needs `is_const` threaded from the statement down to
wherever a name actually gets bound, since a nested pattern's bindings
(`const [a, {b, c}] = ...;`) and rest/rename bindings must be frozen
too, not just the top-level names. `execute`'s `DestructureLetStmt`
branch (search `if isinstance(stmt, DestructureLetStmt):` in
`cinder/interpreter.py`) already looks up `stmt.is_map` — pass
`stmt.is_const` alongside it:
```python
if isinstance(stmt, DestructureLetStmt):
    value = self.evaluate(stmt.initializer, env)
    if stmt.is_map:
        self._bind_map_destructure(
            env, stmt.names, stmt.rest, value, stmt.line, stmt.column,
            is_const=stmt.is_const,
        )
        return
    self._bind_list_destructure(
        env, stmt.names, stmt.rest, value, stmt.line, stmt.column,
        is_const=stmt.is_const,
    )
    return
```
`_bind_list_destructure` and `_bind_map_destructure` (search either
name) each already carry a `use_assign: bool = False` parameter for
exactly this kind of mode-threading (they use it to pick `env.define`
vs. `env.assign` for the plain-assignment destructuring form) — add a
sibling `is_const: bool = False` parameter to both, and pass it through
every recursive self-call inside their bodies (the nested-list and
nested-map branches in each, plus every `_bind_destructure_name` call
in each — six call sites total across the two functions, all of the
shape `..., line, column, use_assign)` today; append `, is_const)` or
`is_const=is_const` at each, whichever matches the surrounding call's
style) exactly the same way `use_assign` is already threaded through
those same six call sites. Do **not** add it to the two call sites in
`_evaluate_destructure_assign` (search that name) — those are the
plain-assignment form (`[a, b] = expr;`), which reassigns
already-declared names and has no concept of freshly declaring a
const, so they keep relying on the new parameter's default. Finally,
`_bind_destructure_name` (search `def _bind_destructure_name`) gets the
same new parameter, used only on the `not use_assign` (fresh-binding)
path:
```python
def _bind_destructure_name(
    self, env: Environment, name: str, item: object, line: int, column: int,
    use_assign: bool, is_const: bool = False,
) -> None:
    if not use_assign:
        if is_const:
            env.define_const(name, item)
        else:
            env.define(name, item)
        return
    try:
        env.assign(name, item)
    except KeyError:
        raise CinderRuntimeError(
            self._undefined_name_message(name, env), line, column
        ) from None
    except _ConstAssignError:
        raise CinderRuntimeError(
            f"cannot assign to const {name!r}", line, column
        ) from None
```
(Only the signature and the `if not use_assign:` branch change; the
`use_assign` branch below is unchanged, included so the replacement is
a drop-in for the whole function.) No other callers of any of these
four functions (the `for`-loop destructuring, `match` list/map
patterns, and destructuring function parameters) pass `is_const` at
all, so they keep defaulting to `False` and are entirely unaffected —
`const` destructuring is scoped to declarations only, matching plain
`const`'s own scope (there is no `const` loop variable or `const`
function parameter concept in Cinder today, and this task does not add
one).

Acceptance criteria:
- `const [a, b] = [1, 2]; print(a); print(b);` prints `1` then `2` —
  the worked example above.
- `const {a, b} = {"a": 1, "b": 2}; print(a); print(b);` prints `1`
  then `2` — the map worked example above.
- `const [a, b] = [1, 2]; a = 3;` raises `CinderRuntimeError` matching
  `"cannot assign to const 'a'"` — the top-level names are actually
  frozen, not just freshly bound.
- `const {a, b} = {"a": 1, "b": 2}; b = 3;` raises `CinderRuntimeError`
  matching `"cannot assign to const 'b'"` — same for map patterns.
- `const [a, {b, c}] = [1, {"b": 2, "c": 3}]; c = 9;` raises
  `CinderRuntimeError` matching `"cannot assign to const 'c'"` — a
  nested pattern's names are frozen too, confirming `is_const` threads
  through the recursive nested-pattern branches, not just the
  top-level loop.
- `const [a, ...rest] = [1, 2, 3]; rest = [];` raises
  `CinderRuntimeError` matching `"cannot assign to const 'rest'"` — a
  rest-captured binding is frozen too.
- `const {a: x} = {"a": 1}; x = 2;` raises `CinderRuntimeError`
  matching `"cannot assign to const 'x'"` — a per-key-renamed binding
  is frozen under its local name.
- `const [a, b = 5] = [1]; print(b);` is `5` — per-element defaults
  still work, unaffected by the new field.
- `const [a, , c] = [1, 2, 3]; print(a); print(c);` prints `1` then
  `3` — hole elements still work.
- Regression: `let [a, b] = [1, 2]; a = 3; print(a);` still prints `3`
  (a plain `let` destructure stays mutable — `DestructureLetStmt`'s new
  `is_const` field defaults to `False` and `_let_statement`'s existing
  calls never pass it) and every existing destructuring-`let`/nested/
  rest/rename/default/hole test in `tests/test_interpreter.py` still
  passes unmodified.
- New tests in `tests/test_interpreter.py`: a `class
  TestConstDestructure` (modeled on `TestDestructureLet`/
  `TestDestructureLetMap`, search either name, for the binding shapes,
  and on `TestConst.test_const_reassignment_raises`, search that name,
  for the freeze-checking style) covering every acceptance case above.
- New tests in `tests/test_parser.py`: parse-shape tests asserting
  `isinstance(parsed, DestructureLetStmt) and parsed.is_const is True`
  for both `const [a, b] = expr;` and `const {a, b} = expr;` — assert
  the `is_const` attribute directly rather than extending the existing
  `shape()` helper's `DestructureLetStmt` tuple (search `def shape` and
  `"DestructureLetStmt"`), since that tuple is asserted as a fixed
  4-element shape by roughly ten existing tests and extending it would
  require touching all of them for a field this task can verify more
  narrowly.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_const_statement`, search `def
_const_statement`; `_destructure_let_statement`, search that name),
`cinder/ast_nodes.py` (`class DestructureLetStmt`), `cinder/interpreter.py`
(`execute`'s `DestructureLetStmt` branch, `_bind_list_destructure`,
`_bind_map_destructure`, `_bind_destructure_name` — search any name),
`tests/test_parser.py`, `tests/test_interpreter.py` per the acceptance
criteria above. Once merged, `README.md`'s "Variables & scope" bullet
needs a mention that `const` now supports the same destructuring forms
as `let`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_squarefree` — squarefree number found at a 1-indexed position

Build: `is_squarefree` (`cinder/builtins.py`, search `def
_is_squarefree`: no prime factor of `value` appears with exponent 2 or
more, checked by trial division for any `divisor` where
`value % (divisor * divisor) == 0`) has no value-returning `nth_*`
sibling, the same gap `nth_practical_number`/`nth_deficient`/
`nth_harshad` (task 1 above) already close or are about to close for
their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_squarefree(1));'
# -> <eval>:1:7: undefined name 'nth_squarefree' (did you mean
#    'is_squarefree'?)
```

Worked examples: the first ten squarefree numbers (OEIS A005117) are
`1, 2, 3, 5, 6, 7, 10, 11, 13, 14` — `4, 8, 9, 12` are skipped (each
divisible by a perfect square: `4 = 2^2`, `8 = 2^2 * 2`, `9 = 3^2`,
`12 = 2^2 * 3`); the 20th is `31`.

Add directly after `_is_squarefree` (search `def _is_squarefree`,
immediately before `def _is_powerful_number`) — keeps the
value-returning helper next to the predicate it mirrors, matching
where `nth_deficient` itself sits right after `is_deficient`:
```python
def _nth_squarefree(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_squarefree", arguments, 1, line, column)
    value = _require_int("nth_squarefree", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_squarefree() requires a positive integer, domain error",
            line, column,
        )

    def _is_squarefree_candidate(candidate: int) -> bool:
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % (divisor * divisor) == 0:
                return False
        return True

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_squarefree_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`/`_nth_harshad`, with the
inner candidate check copied from `_is_squarefree`'s own body instead
of calling `_is_squarefree` directly — the same "duplicate the tiny
predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice `_nth_harshad` already makes.) Also
register the new dict entry (search `"is_squarefree":
_is_squarefree,`, add `"nth_squarefree": _nth_squarefree,` directly
after it, before `"is_powerful_number": _is_powerful_number,`).

Acceptance criteria:
- `nth_squarefree(1);` through `nth_squarefree(10);` are `1, 2, 3, 5,
  6, 7, 10, 11, 13, 14` in order — the worked example above.
- `nth_squarefree(20);` is `31` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`, `is_squarefree(nth_squarefree(position))`
  is `true` — the same self-consistency check `nth_practical_number`'s
  own test suite already runs against `is_practical_number`.
- `nth_squarefree(0);`, `nth_squarefree(-3);` both raise
  `CinderRuntimeError` matching `"nth_squarefree\(\) requires a
  positive integer, domain error"`, matching `nth_practical_number`'s
  own non-positive-input convention.
- `nth_squarefree(true);` raises `CinderRuntimeError` matching
  `"nth_squarefree\(\) requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `nth_squarefree("5");` raises `CinderRuntimeError` matching
  `"nth_squarefree\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_squarefree`,
search `def _is_squarefree`), `tests/test_builtins.py` (new `class
TestNthSquarefree`, modeled on `class TestNthPracticalNumber`, search
that name, for the test shapes above — place it near the existing
`class TestIsSquarefree`, search that name). Once merged, `README.md`'s
Builtins bullet needs `nth_squarefree` added near `is_squarefree`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Language: destructuring patterns for `try`/`catch` clauses

Build: `let`/`for`/function params/comprehension loop variables all accept
list- and map-destructuring patterns (with rest, per-key rename, defaults,
holes, and nesting — see the README's "Variables & scope" bullet), but
`catch (...)` only ever accepts a single plain identifier or nothing at
all. Since `throw` can raise any Cinder value, not just a string (`throw
{"code": 404};`, `throw [1, 2];` — see the README's Control flow bullet),
catch handlers that want to pull fields out of a thrown list/map today
must bind the whole value under one name and manually index into it.
Verify the gap:
```sh
python3 -m cinder.cli eval 'try { throw [1, 2]; } catch ([a, b]) { print(a); print(b); }'
# -> <eval>:1:29: expected identifier after 'catch (', found '['
python3 -m cinder.cli eval 'try { throw {"a": 1, "b": 2}; } catch ({a, b}) { print(a); print(b); }'
# -> <eval>:1:40: expected identifier after 'catch (', found '{'
```

Root cause: `_try_statement` (search `def _try_statement`,
`cinder/parser.py`) only ever calls `self._consume(TokenType.IDENTIFIER,
"identifier after 'catch ('")` inside the `catch (...)` branch — it never
checks for a leading `[`/`{` the way `_let_statement`/`_for_statement`
already do. The pattern-parsing machinery itself needs no changes:
`_destructure_list_pattern`/`_destructure_map_pattern` (search either
name) already produce the `(names, rest)` shape every other destructuring
site consumes, and `_bind_list_destructure`/`_bind_map_destructure`
(`cinder/interpreter.py`, search either name) already bind that shape
into an `Environment` generically — they don't know or care that the
value being destructured came from a caught error rather than a `let`
initializer or a `for`-loop iterable.

`TryStmt` (search `class TryStmt` in `cinder/ast_nodes.py`) needs three
new fields, each defaulted so every existing plain-identifier/nameless
`TryStmt` is unaffected:
```python
catch_names: "list | None" = None
catch_rest: "str | None" = None
catch_is_map: bool = False
```
Change the `catch (...)` branch of `_try_statement` (search `def
_try_statement`) to try a pattern first:
```python
if self._check(TokenType.LPAREN):
    self._advance()
    if self._check(TokenType.LBRACKET):
        catch_names, catch_rest = self._destructure_list_pattern()
    elif self._check(TokenType.LBRACE):
        catch_names, catch_rest = self._destructure_map_pattern()
        catch_is_map = True
    else:
        name_token = self._consume(TokenType.IDENTIFIER, "identifier after 'catch ('")
        catch_name = name_token.lexeme
    self._consume(TokenType.RPAREN, "')' after catch name")
```
(`catch_names = None`, `catch_rest = None`, `catch_is_map = False`,
`catch_name = None` need declaring above this block, same as the
existing `catch_name = None` initialization already does today — only
the body of the `if self._check(TokenType.LPAREN):` branch changes.)
Thread the three new fields into the `TryStmt(...)` construction at the
bottom of the method alongside the existing `catch_name`.

In `cinder/interpreter.py`, `_execute_try`'s catch branch (search `def
_execute_try`) currently does:
```python
catch_env = Environment(env)
if stmt.catch_name is not None:
    catch_env.define(stmt.catch_name, error.value)
```
Extend it to check the pattern fields first:
```python
catch_env = Environment(env)
if stmt.catch_names is not None:
    if stmt.catch_is_map:
        self._bind_map_destructure(
            catch_env, stmt.catch_names, stmt.catch_rest, error.value,
            stmt.line, stmt.column,
        )
    else:
        self._bind_list_destructure(
            catch_env, stmt.catch_names, stmt.catch_rest, error.value,
            stmt.line, stmt.column,
        )
elif stmt.catch_name is not None:
    catch_env.define(stmt.catch_name, error.value)
```
No change needed to `_bind_list_destructure`/`_bind_map_destructure`
themselves — a non-list/non-map `error.value` against a destructuring
catch pattern (e.g. `catch ([a]) { }` when the thrown value was an int)
should raise `CinderRuntimeError` exactly the way it already does for a
`let`/`for` mismatch (`"cannot destructure int as a list"`), and since
that raise happens inside the same `except CinderRuntimeError as error:`
block rather than a nested `try`, it propagates uncaught — consistent
with the existing `test_error_raised_inside_catch_block_is_not_re_caught`
precedent (an error while entering/running the catch handler is never
silently re-caught by its own `try`).

Acceptance criteria:
- `try { throw [1, 2]; } catch ([a, b]) { print(a); print(b); }` prints
  `1` then `2` — the list worked example above.
- `try { throw {"a": 1, "b": 2}; } catch ({a, b}) { print(a); print(b); }`
  prints `1` then `2` — the map worked example above.
- `try { throw [1, 2, 3]; } catch ([a, ...rest]) { print(rest); }` prints
  `[2, 3]` — rest capture works in a catch pattern.
- `try { throw {"a": 1}; } catch ({a, b = 5}) { print(b); }` prints `5`
  — per-key default works in a catch pattern.
- `try { throw {"a": 1}; } catch ({a: x}) { print(x); }` prints `1` —
  per-key rename works in a catch pattern.
- `try { throw 5; } catch ([a]) { }` raises `CinderRuntimeError` matching
  `"cannot destructure int as a list"`, uncaught by its own `try` —
  regression coverage matching `test_error_raised_inside_catch_block_is_not_re_caught`'s
  style, confirming a pattern/value mismatch during binding propagates
  rather than being silently swallowed.
- Regression: `try { let x = 1 / 0; } catch (e) { ... }` (plain
  identifier) and `try { let x = 1 / 0; } catch { ... }` (nameless) both
  still behave exactly as before — every existing test in
  `TestTryCatch`/`TestTryFinally` (`tests/test_interpreter.py`) and
  `TestTryCatch` (`tests/test_parser.py`) still passes unmodified.
- Catch pattern bindings are scoped to the catch block only, same as a
  plain catch name — `try { throw [1]; } catch ([a]) {} a;` raises
  `CinderRuntimeError` (undefined name), matching
  `test_catch_name_not_visible_after_try_catch`'s style.
- New tests in `tests/test_interpreter.py`: add to `class TestTryCatch`
  (search that name), covering every acceptance case above.
- New tests in `tests/test_parser.py`: parse-shape tests for
  `try {} catch ([a, b]) {}` and `try {} catch ({a, b}) {}` asserting
  `catch_names`/`catch_rest`/`catch_is_map` directly on the parsed
  `TryStmt` node, the same "assert the new field directly rather than
  extending the fixed-shape tuple" choice task 2's `const`-destructure
  work already made for `DestructureLetStmt`'s `is_const` field — `shape()`'s
  existing `TryStmt` tuple (search `"TryStmt"`) is a fixed 5-element shape
  asserted by roughly six existing tests and only reads `catch_name`
  (which stays `None` for a destructuring catch), so extending it is
  unnecessary churn for fields this task can verify more narrowly.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_try_statement`, search `def
_try_statement` — while there, the method's grammar-summary docstring
comment near the top of the file, search `catch (IDENTIFIER)`, is worth
a one-line fix too: it currently claims "the parenthesized catch name is
required", which was already stale before this task since nameless
`catch { ... }` has worked for a while — feel free to correct it in
passing, but it's not this task's acceptance bar), `cinder/ast_nodes.py`
(`class TryStmt`), `cinder/interpreter.py` (`_execute_try`, search that
name — no changes needed to `_bind_list_destructure`/
`_bind_map_destructure` themselves), `tests/test_parser.py`,
`tests/test_interpreter.py` per the acceptance criteria above. Once
merged, `README.md`'s Control flow bullet needs a mention that `catch`
now accepts the same destructuring patterns as `let`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 5. Standard library: `nth_refactorable` — refactorable number found at a 1-indexed position

Build: `is_refactorable` (`cinder/builtins.py`, search `def
_is_refactorable`: whether `n`'s own divisor count divides back into
`n`, e.g. `8` has 4 divisors and `8 % 4 == 0`) has no value-returning
`nth_*` sibling, the same gap `nth_practical_number`/`nth_semiperfect`
already closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_refactorable(1));'
# -> <eval>:1:7: undefined name 'nth_refactorable' (did you mean
#    'is_refactorable'?)
```

Worked examples: the first ten refactorable numbers are `1, 2, 8, 9, 12,
18, 24, 36, 40, 56` (`1` is trivially refactorable — `_is_refactorable`
special-cases it to `True` — and `2` has 2 divisors, `2 % 2 == 0`), so
`nth_refactorable(1)` is `1` and `nth_refactorable(10)` is `56`. The 20th
is `132`.

Add directly after `_is_refactorable` (search `def _is_refactorable`,
immediately before `def _is_amicable`):
```python
def _nth_refactorable(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_refactorable", arguments, 1, line, column)
    value = _require_int("nth_refactorable", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_refactorable() requires a positive integer, domain error",
            line, column,
        )

    def _is_refactorable_candidate(candidate: int) -> bool:
        if candidate == 1:
            return True
        count = 2
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                count += 1
                complement = candidate // divisor
                if complement != divisor:
                    count += 1
        return candidate % count == 0

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_refactorable_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`/`_nth_semiperfect`, with the
inner candidate check copied from `_is_refactorable`'s own body instead
of calling `_is_refactorable` directly — the same "duplicate the tiny
predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice `_nth_harshad`/`_nth_squarefree` (tasks
2 and 4 above) already make.) Register the new dict entry (search
`"is_refactorable": _is_refactorable,`, add `"nth_refactorable":
_nth_refactorable,` directly after it).

Acceptance criteria:
- `nth_refactorable(1);` through `nth_refactorable(10);` are `1, 2, 8, 9,
  12, 18, 24, 36, 40, 56` in order — the worked example above.
- `nth_refactorable(20);` is `132` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`, `is_refactorable(nth_refactorable(position))`
  is `true` — the same self-consistency check `nth_practical_number`/
  `nth_semiperfect`'s own test suites already run against their
  predicates.
- `nth_refactorable(0);`, `nth_refactorable(-3);` both raise
  `CinderRuntimeError` matching `"nth_refactorable\(\) requires a
  positive integer, domain error"`.
- `nth_refactorable(true);` raises `CinderRuntimeError` matching
  `"nth_refactorable\(\) requires an int, got bool"`.
- `nth_refactorable("5");` raises `CinderRuntimeError` matching
  `"nth_refactorable\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_refactorable`,
search `def _is_refactorable`), `tests/test_builtins.py` (new `class
TestNthRefactorable`, modeled on `class TestNthPracticalNumber`/`class
TestNthSemiperfect`, search either name, for the test shapes above —
place it near the existing `class TestIsRefactorable`, search that
name). Once merged, `README.md`'s Builtins bullet needs `nth_refactorable`
added near `is_refactorable`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

### Language: guards in `match` arms (`n if n > 0 => "positive"`) — PR #314, closed 2026-08-25

Bounced 3x with `VERDICT: CHANGES REQUESTED`, all the same recurring bug:
each fix round patched `_bracket_depth` tracking (used to scope the
bare-arrow/guard `=>` ambiguity fix) for one nested construct — call/list/map
arguments (round 1), `match` expressions (round 2), `fn` expressions (round
3) — while the reviewer kept finding another construct the fix hadn't
threaded depth through, and round 3's review flagged a 4th possible gap
(`_arrow_body`'s bare-expression branch, `_block()`) that was never
confirmed either way. Next attempt should enumerate *every* production that
opens a paren/bracket/brace scope up front (grep `_bracket_depth` usages in
the closed PR's final diff for the list-so-far) rather than fixing gaps
reactively one review round at a time — or consider a structurally
different fix that doesn't need per-construct threading at all (e.g.
resolving the bare-arrow/guard ambiguity by lookahead at the `=>` site
instead of a suppression-depth counter).
