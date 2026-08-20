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

## 1. Standard library: `is_sad_number` — the complement of `is_happy_number`

Build: the breadth task after task 5's depth work (missing string escape
sequences) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `is_pernicious` has landed via PR #282,
dropping the count to the 5-task floor. `is_happy_number` (`cinder/builtins.py`)
already implements the "repeatedly sum the squares of the digits, does it
reach 1?" iteration and returns `false` both for numbers that cycle instead
of reaching 1 (e.g. `4 -> 16 -> 37 -> 58 -> 89 -> 145 -> 42 -> 20 -> 4`, back
where it started) and for out-of-domain input (negative numbers) — collapsing
two different reasons for "not happy" into one boolean. `is_evil`/`is_odious`
already establish the pattern of a same-cycle predicate pair, one asking the
positive question and the other its direct complement over the same domain;
`is_composite` is not that pattern (its own domain floor of 4 makes it *not*
a strict negation of `is_prime`), but `is_sad_number` should be the direct
complement — every non-negative integer is either happy or sad, no third
case. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_sad_number(4));'
# -> CinderRuntimeError: undefined name 'is_sad_number'
```

Add to `cinder/builtins.py`, registered right after `_is_happy_number`
(search `def _is_happy_number`, immediately before `_collatz_length`):
```python
def _is_sad_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_sad_number", arguments, 1, line, column)
    value = _require_int("is_sad_number", arguments[0], line, column)
    if value < 0:
        return False

    seen = set()
    while value != 1:
        if value in seen:
            return True
        seen.add(value)
        value = sum(int(digit) ** 2 for digit in str(value))
    return False
```
This is `_is_happy_number`'s own loop (search `def _is_happy_number`),
inverted at exactly its two exit points — `value in seen` (a cycle found
without ever reaching 1) now returns `True` instead of `False`, and falling
out of the `while` loop by reaching `1` now returns `False` instead of
`True` — rather than computing `not _is_happy_number(...)`, so a negative
argument keeps returning `False` from its own explicit domain guard, the
same "not happy" input handling `is_happy_number` uses, instead of silently
becoming "sad" through blind negation of a function whose own negative-input
convention is invisible from the outside.

Acceptance criteria:
- `is_sad_number(4);` is `true` — `4 -> 16 -> 37 -> 58 -> 89 -> 145 -> 42 ->
  20 -> 4`, cycles without ever reaching `1`.
- `is_sad_number(2);` is `true`, `is_sad_number(3);` is `true` — both
  eventually join the same 8-number cycle `4` belongs to.
- `is_sad_number(1);` is `false` — already `1`.
- `is_sad_number(7);` is `false`, `is_sad_number(19);` is `false`,
  `is_sad_number(97);` is `false` — each is a known happy number
  (`is_happy_number`'s own true-case fixtures), so the complement holds.
- `is_sad_number(0);` is `true` — `0 -> 0`, an immediate one-element cycle
  (mirrors `is_happy_number(0)` being `false`).
- `is_sad_number(-7);` is `false` — negative input, matching
  `is_happy_number`'s own "not a valid domain, answer false rather than
  raise" convention, not a strict boolean negation of it.
- `is_sad_number(5.0);` raises `CinderRuntimeError` matching
  `"is_sad_number() requires an int, got float"`.
- `is_sad_number(true);` raises `CinderRuntimeError` matching
  `"is_sad_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_happy_number`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsHappyNumber`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_sad_number`
added near `is_happy_number`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming pass,
not this task.

---

## 3. Language: comma-separated multiple statements in expression-statement position (`a = 1, b = 2;`)

Build: the depth task after task 5's breadth work (`is_sad_number`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that the inclusive range literal `a..=b` has landed via PR #283,
dropping the count to the 5-task floor. `let`/`const` statements already
support comma-separated multiple declarations in one statement (`let a = 1,
b = 2;`, via `_let_statement`/`_const_statement` looping on `TokenType.COMMA`
and collecting the results into a `DeclSeq`), but plain expression
statements — assignments to already-declared names, or any other bare
expression used as a statement — have no equivalent: each one needs its own
`;`-terminated statement today. Verify the gap:
```sh
python3 -m cinder.cli eval 'let a; let b; a = 1, b = 2; print(a); print(b);'
# -> <eval>:1:20: expected ';' after expression, found ','
```
This is a guaranteed `ParseError` today (a bare top-level comma outside any
bracketed expression context is never valid), so no currently-valid Cinder
program's meaning changes.

**Parser only** (`cinder/parser.py`) — no lexer, AST, or interpreter changes
needed, since this reuses the exact `ExprStmt` and `DeclSeq` nodes that
already exist for exactly this shape (`DeclSeq` is already a generic
"execute each statement in order" node — the interpreter's existing handler,
search `if isinstance(stmt, DeclSeq):` in `cinder/interpreter.py`, has no
assumption that its `declarations` list holds only `LetStmt`/`ConstStmt`; it
just executes each in turn). `_expr_statement` (search `def
_expr_statement`) currently parses exactly one expression and demands `;`
immediately after — extend it to loop on `TokenType.COMMA` the same way
`_let_statement` already does:
```python
    def _expr_statement(self) -> Stmt:
        first = self._assignment()
        statements = [ExprStmt(first)]
        while self._check(TokenType.COMMA):
            self._advance()
            statements.append(ExprStmt(self._assignment()))
        self._consume(TokenType.SEMICOLON, "';' after expression")
        if len(statements) == 1:
            return statements[0]
        return DeclSeq(statements, first.line, first.column)
```
`ExprStmt` and `DeclSeq` are both already imported in `cinder/parser.py`
(used by `_let_statement`/`_const_statement` already), so no new import is
needed either. This is deliberately a sequence of independent statements
executed left to right, not a single composite expression with one overall
value (unlike C's comma *operator*) — the same design choice
`let a = 1, b = 2;` already made by building a `DeclSeq` of statements
rather than one expression, so this task stays consistent with it rather
than introducing a second, differently-shaped kind of comma-sequencing.

Acceptance criteria:
- `let a; let b; a = 1, b = 2; print(a); print(b);` prints `1` then `2` —
  both assignments take effect from one statement.
- `let a = 0, b = 0; a = 1, b = a + 1; print(b);` prints `2` — left-to-right
  evaluation order, so a later item in the sequence sees an earlier one's
  already-updated value (mirrors `let a = 1, b = a + 1;`'s existing
  left-to-right guarantee).
- `let xs = [0, 0]; xs[0] = 1, xs[1] = 2; print(xs);` prints `[1, 2]` —
  index-assignment targets work in the sequence too, not just plain
  identifiers.
- A single expression statement with no comma (`a = 1;`) parses exactly as
  before — plain `ExprStmt`, not wrapped in a `DeclSeq` — confirmed by every
  existing assignment/expression-statement test in `tests/test_parser.py`
  and `tests/test_interpreter.py` staying green with no changes needed to
  any of them.
- A non-assignment expression works as a sequence member too:
  `let calls = []; push(calls, 1), push(calls, 2); print(calls);` prints
  `[1, 2]` — the feature is "comma-separated statements", not specifically
  "comma-separated assignments"; each item is just whatever `_assignment()`
  already accepts as a lone expression statement.
- A trailing comma before `;` (`a = 1, b = 2,;`) still raises `ParseError`
  (`expected identifier`-style message from `_assignment()` failing on the
  `;` it wasn't expecting) — no trailing-comma support here, matching
  `let a = 1, b = 2,;`'s own existing lack of trailing-comma support (the
  `while self._check(TokenType.COMMA)` loop in `_let_statement` has the same
  behavior, so this stays consistent rather than adding a permissiveness
  `let` itself doesn't have).
- Comma-sequencing composes with `for`/`while`/`if` single-statement (no
  braces) bodies, since `DeclSeq` is an ordinary `Stmt` usable anywhere any
  other statement is: `if (true) a = 1, b = 2;` assigns both.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_expr_statement`), `tests/test_parser.py`
(add a small cluster of parser-level tests confirming the single-expression
case still returns a bare `ExprStmt` and the comma case returns a `DeclSeq`
of `ExprStmt`s), `tests/test_interpreter.py` (`class TestStatements`, search
`def test_let_comma_separated_declares_both` for where the comma-sequencing
tests already sit for `let`; add a parallel
`test_expr_statement_comma_separated_*` cluster right after it). Once
merged, `README.md`'s Control flow or Operators bullet needs a mention of
comma-separated expression statements, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming pass,
not this task.

---

## 4. Standard library: `additive_persistence` — steps of repeated digit-summing to reach one digit

Build: the breadth task after task 5's depth work (comma-separated
expression statements) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_sphenic` has landed
via PR #284, dropping the count to the 5-task floor.
`multiplicative_persistence` (`cinder/builtins.py`) already counts the
number of repeated digit-*multiplying* steps needed to reduce `n` to a
single digit; `digital_root` already computes the *value* a number
reduces to under repeated digit-*summing*, but via a closed-form
identity (`1 + (n - 1) % 9`) that never actually counts iterations.
Nothing today answers "how many summing steps does that take?" — the
natural sibling `multiplicative_persistence` is missing on the additive
side. `199` reduces `199 -> 19 -> 10 -> 1`, three steps; `9876` reduces
`9876 -> 30 -> 3`, two steps. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(additive_persistence(199));'
# -> CinderRuntimeError: undefined name 'additive_persistence'
```

Add to `cinder/builtins.py`, registered right after `_multiplicative_persistence`
(search `def _multiplicative_persistence`, immediately before `_reverse_int`):
```python
def _additive_persistence(arguments: list, line: int, column: int) -> object:
    _require_arity("additive_persistence", arguments, 1, line, column)
    value = _require_int("additive_persistence", arguments[0], line, column)
    value = abs(value)
    steps = 0
    while value >= 10:
        value = sum(int(digit) for digit in str(value))
        steps += 1
    return steps
```
This is `_multiplicative_persistence`'s own loop shape (search `def
_multiplicative_persistence`) — `abs()` the input once up front to discard
sign the same way `digit_sum`/`digital_root`/`multiplicative_persistence`
all already do, loop while `value >= 10` incrementing a step counter —
with the loop body's digit-*product* swapped for a digit-*sum*
(`sum(int(digit) for digit in str(value))`, the same summing expression
`digit_sum` itself uses), rather than computing `digital_root` and a step
count as two separate passes over the same reduction.

Acceptance criteria:
- `additive_persistence(0);` is `0`, `additive_persistence(9);` is `0` —
  already single-digit, no steps needed.
- `additive_persistence(99);` is `2` — `99 -> 18 -> 9`.
- `additive_persistence(199);` is `3` — `199 -> 19 -> 10 -> 1`.
- `additive_persistence(9876);` is `2` — `9876 -> 30 -> 3`.
- `additive_persistence(-199);` is `3` — sign discarded via `abs()` up
  front, matching `digit_sum`/`digital_root`/`multiplicative_persistence`'s
  own sign-discarding convention (not `reverse_int`'s sign-preserving
  one, since this returns a step count, not a number built from the
  input's own digits).
- `additive_persistence(5.0);` raises `CinderRuntimeError` matching
  `"additive_persistence() requires an int, got float"`.
- `additive_persistence(true);` raises `CinderRuntimeError` matching
  `"additive_persistence() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`multiplicative_persistence`, see current line numbers — shift if earlier
tasks this cycle land first), `tests/test_builtins.py` (model on `class
TestMultiplicativePersistence`, search that name). Once merged,
`README.md`'s Builtins bullet needs `additive_persistence` added near
`multiplicative_persistence`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming
pass, not this task.

---

## 5. Language: map concatenation via `+` (`{...} + {...}`)

Build: the depth task after task 5's breadth work (`additive_persistence`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that triple-quoted string literals has landed via PR #285,
dropping the count to the 5-task floor. `_apply_binary_operator`'s `PLUS`
branch (`cinder/interpreter.py`, search `if op == TokenType.PLUS:`) already
overloads `+` for three types — numbers, strings, and lists
(`isinstance(left, list) and isinstance(right, list): return left + right`)
— the list case added specifically to close the gap between the existing
`concat()` builtin and infix syntax. Maps are Cinder's fourth container
type and have the exact same kind of gap: `merge()` (`cinder/builtins.py`,
search `def _merge`) already implements right-biased shallow map merging
(`result = dict(map1); result.update(map2); return result`) as a builtin,
but there is no infix spelling for it — every other overloaded operator in
this file has an infix form, merge is the only container-combining builtin
left stuck as call-only syntax. Nothing about maps makes `+` ambiguous or
undesirable here: `merge()`'s semantics (map2's value wins on a key
collision, map1's key order preserved for shared keys, map2-only keys
appended after) are exactly what most languages' informal "dict overlay"
reading of `+` would produce, and Cinder already applies this same "give
the existing builtin an operator form" reasoning to `concat()`.

Verify the gap:
```sh
python3 -m cinder.cli eval 'print({"a": 1} + {"b": 2});'
# -> <eval>:1:16: unsupported operand types for '+': map and map
python3 -m cinder.cli eval 'let m = {"a": 1}; m += {"a": 2}; print(m);'
# -> <eval>:1:21: unsupported operand types for '+': map and map
```
This is a guaranteed `CinderRuntimeError` today for every map-plus-map
expression, so no currently-valid Cinder program's meaning changes.

**Interpreter only** (`cinder/interpreter.py`) — no lexer, parser, or AST
changes needed, since `+` is already a fully general `Binary`/compound-assign
operator and maps are already a first-class value type; this only extends
`_apply_binary_operator`'s existing `PLUS` branch with one more `isinstance`
case, the same shape the `list`/`list` case right above it already has:
```python
        if op == TokenType.PLUS:
            if _is_number(left) and _is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            if isinstance(left, dict) and isinstance(right, dict):
                result = dict(left)
                result.update(right)
                return result
            raise CinderRuntimeError(
                f"unsupported operand types for '+': {type_name(left)} and {type_name(right)}",
                operator.line,
                operator.column,
            )
```
The two-line merge body (`result = dict(left); result.update(right)`) is
`_merge`'s own body verbatim (search `def _merge`, its `result = dict(map1);
result.update(map2); return result` after the type checks) — it can't be
called directly from here since `cinder/builtins.py` imports *from*
`cinder/interpreter.py` (search `from cinder.interpreter import` near the
top of `builtins.py`), not the other way around, so importing `_merge` back
into `interpreter.py` would be a circular import; inlining these two lines
is the same tradeoff the list case already makes by writing `left + right`
directly instead of importing `_concat`. No new type-check branch is needed
either — `left`/`right` are already known to both be `dict` from the
`isinstance` guard, and `dict(left)` always succeeds on a `dict`, so there's
no failure mode requiring its own `CinderRuntimeError` the way, say,
`_bitwise_op`'s int-only guard needs one.

Because this only touches the shared `PLUS` branch, every existing caller of
`+` gets map support automatically, with no separate implementation needed:
plain `m1 + m2` (`_evaluate_binary`), `+=` on an identifier target (parser.py
desugars `PLUSEQ` into `Assign(name, Binary(expr, PLUS, value))`, which
evaluates through this same branch), and `+=` on an index or dot-access
target (`PLUSEQ` is already in `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` in
`cinder/parser.py`, so `xs[0] += {"a": 1}` / `obj.key += {"a": 1}` desugar
into `IndexCompoundAssign`, which also calls `_apply_binary_operator` — see
`cinder/interpreter.py`'s `IndexCompoundAssign` handler, search `result =
self._apply_binary_operator(expr.operator, current, rhs)`) — exactly
mirroring how list `+=` already works for free through the same
desugaring once list `+` landed.

Acceptance criteria:
- `print({"a": 1} + {"b": 2});` prints `{"a": 1, "b": 2}`.
- `print({"a": 1} + {"a": 2});` prints `{"a": 2}` — right map wins on a key
  collision, matching `merge()`'s own conflict rule
  (`test_merge_map2_wins_on_conflict`).
- `print({} + {"a": 1});` prints `{"a": 1}`; `print({"a": 1} + {});` prints
  `{"a": 1}` — either side empty.
- `print(list((({"a": 1, "b": 2} + {"b": 3, "c": 4})).keys()));` (or an
  equivalent `keys()` call) yields `["a", "b", "c"]` — left map's key order
  preserved for shared/left-only keys, right map's new keys appended after,
  matching `merge()`'s own `test_merge_key_order_map1_then_map2_only_keys`.
- `let a = {"a": 1}; let b = {"b": 2}; let c = a + b; print(a); print(b);`
  prints `{"a": 1}` then `{"b": 2}` — neither input is mutated, mirroring
  `TestListConcatenation.test_does_not_mutate_inputs`.
- `let m = {"a": 1}; m += {"b": 2}; print(m);` prints `{"a": 1, "b": 2}` —
  compound assignment on an identifier target.
- `let xs = [{"a": 1}]; xs[0] += {"b": 2}; print(xs[0]);` prints
  `{"a": 1, "b": 2}` — compound assignment on an index target.
- `let obj = {"m": {"a": 1}}; obj.m += {"b": 2}; print(obj.m);` prints
  `{"a": 1, "b": 2}` — compound assignment on a dot-access target (which
  desugars to the same `Index` path).
- `let m = {"a": 1} + {"b": 2} + {"c": 3}; print(m);` prints
  `{"a": 1, "b": 2, "c": 3}` — left-associative chaining, mirroring
  `TestListConcatenation.test_left_associative`.
- `{"a": 1} + [1, 2];` still raises `CinderRuntimeError` matching
  `"unsupported operand types for '+': map and list"` — mixed map/list is
  unaffected.
- `{"a": 1} + "x";` still raises `CinderRuntimeError` matching
  `"unsupported operand types for '+': map and string"` — mixed map/string
  is unaffected.
- `{"a": 1} + 1;` still raises `CinderRuntimeError` matching `"unsupported
  operand types for '+': map and int"` — mixed map/number is unaffected.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s `PLUS`
branch), `tests/test_interpreter.py` (model on `class TestListConcatenation`,
search that name — add a parallel `class TestMapConcatenation` right after
it with the same shape: two maps, empty left/right, non-mutation, compound
assignment, left-associativity, plus the mixed-type error cases). Once
merged, `README.md`'s list-concatenation bullet (search "list concatenation
via") needs a mention of the map case added alongside it, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s roadmap paragraph needs
this moved from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 6. Standard library: `is_pentagonal` — the closed-form figurate-number sibling of `is_triangular`

Build: the breadth task after task 5's depth work (map concatenation via
`+`) per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog
back to 6 tasks now that `is_circular_prime` has landed via PR #286,
dropping the count to the 5-task floor. `is_triangular` (`cinder/builtins.py`)
already tests membership in the triangular numbers (`0, 1, 3, 6, 10, ...`)
via a closed-form perfect-square check (`8n + 1` is a perfect square) rather
than an accumulating loop; `is_fibonacci`/`is_perfect_square` use the same
`math.isqrt`-based exact-integer technique for their own closed forms. The
pentagonal numbers (`1, 5, 12, 22, 35, ...`, generated by `P_k = k * (3k -
1) / 2` for `k = 1, 2, 3, ...`) are the next figurate-number family after
triangular and have an equally clean closed form, but nothing in Cinder
tests membership in it today. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_pentagonal(5));'
# -> CinderRuntimeError: undefined name 'is_pentagonal'
```

Add to `cinder/builtins.py`, registered right after `_is_triangular`
(search `def _is_triangular`, immediately before `_is_prime`):
```python
def _is_pentagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_pentagonal", arguments, 1, line, column)
    value = _require_int("is_pentagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 24 * value + 1
    root = math.isqrt(candidate)
    return root * root == candidate and root % 6 == 5
```
This mirrors `_is_triangular`'s own shape exactly (search `def
_is_triangular`) — solving `P_k = k * (3k - 1) / 2 = value` for `k` via the
quadratic formula gives `k = (1 + sqrt(24 * value + 1)) / 6`, so `k` is a
positive integer exactly when `24 * value + 1` is a perfect square *and*
its integer square root is `≡ 5 (mod 6)` (the `+ 1` in the numerator only
divides evenly by `6` when the root lands on that residue) — the second
condition is the one place this differs from `is_triangular`'s plain
perfect-square check, since triangular numbers' `k = (-1 + sqrt(8n + 1)) /
2` has no equivalent modular constraint. `0` is deliberately *not*
pentagonal under this test (`candidate = 1`, `root = 1`, `1 % 6 == 1`, not
`5`) — unlike `is_triangular(0)` being `true` — because the pentagonal
sequence conventionally starts at `k = 1` (`P_1 = 1`), with no `k = 0`
term the way triangular numbers have `T_0 = 0`; this was verified against
a brute-force `k * (3 * k - 1) // 2 for k in range(1, 1000)` membership
set before writing this task; do not go add a `value == 0` special case.
Also register the new registration-dict entry in the builtins dict (search
`"is_triangular": _is_triangular,`, add `"is_pentagonal": _is_pentagonal,`
directly after it).

Acceptance criteria:
- `is_pentagonal(0);` is `false` — the pentagonal sequence starts at `1`,
  unlike `is_triangular(0)` being `true`.
- `is_pentagonal(1);` is `true`, `is_pentagonal(5);` is `true`,
  `is_pentagonal(12);` is `true`, `is_pentagonal(22);` is `true`,
  `is_pentagonal(35);` is `true` — the first five pentagonal numbers
  (`k = 1..5`).
- `is_pentagonal(2);` is `false`, `is_pentagonal(4);` is `false`,
  `is_pentagonal(10);` is `false`, `is_pentagonal(100);` is `false` — none
  of these are pentagonal.
- `is_pentagonal(-5);` is `false` — negative input, matching
  `is_triangular`/`is_fibonacci`'s own "not a valid domain, answer false
  rather than raise" convention.
- `is_pentagonal(40755);` is `true` — a large pentagonal number
  (`k = 165`), confirming the closed form holds beyond small brute-forced
  cases.
- `is_pentagonal(5.0);` raises `CinderRuntimeError` matching
  `"is_pentagonal() requires an int, got float"`.
- `is_pentagonal(true);` raises `CinderRuntimeError` matching
  `"is_pentagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_triangular`, see
current line numbers — shift if earlier tasks this cycle land first),
`tests/test_builtins.py` (model on `class TestIsTriangular`, search that
name). Once merged, `README.md`'s Builtins bullet needs `is_pentagonal`
added near `is_triangular`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not this
task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
