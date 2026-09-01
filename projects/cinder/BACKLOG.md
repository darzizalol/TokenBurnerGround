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

## 1. Standard library: `is_trimorphic_number` — cube-ending digit-invariance test

Build: `is_automorphic` (`cinder/builtins.py`, search `def
_is_automorphic`) already tests whether a number's *square* ends in
the number itself (`str(value * value).endswith(str(value))`), but
nothing asks the same question one power up — whether a number's
*cube* ends in the number itself, the classic "trimorphic number"
property (OEIS A033819). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_trimorphic_number(24));'
# -> <eval>:1:7: undefined name 'is_trimorphic_number'
```

This is a direct one-power extension of `is_automorphic`'s own check —
same digit-string-suffix approach, same domain (non-negative integers),
just `value ** 3` instead of `value * value`. Every automorphic number
is automatically trimorphic too (if `n * n` ends in `n` modulo
`10 ** k`, then `n ** 3 = n * n * n` ends in `n * n`'s own ending,
which already ends in `n`, by the same modular idempotence — e.g. `76`
is automorphic, `76 * 76 = 5776` ends in `76`, and indeed `76 ** 3 =
438976` also ends in `76`), but the reverse does not hold: `24` is
trimorphic (`24 ** 3 = 13824` ends in `24`) while *not* automorphic
(`24 * 24 = 576` does not end in `24`), so this is a genuinely broader
predicate, not a trivial alias.

Add to `cinder/builtins.py`, directly after `_is_automorphic` (search
`def _is_automorphic`, immediately before `def _is_kaprekar`) — keeps
it grouped with the other digit-invariance predicates:
```python
def _is_trimorphic_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_trimorphic_number", arguments, 1, line, column)
    value = _require_int("is_trimorphic_number", arguments[0], line, column)
    if value < 0:
        return False
    return str(value ** 3).endswith(str(value))
```
Also register the new dict entry (search `"is_automorphic":
_is_automorphic,`, add `"is_trimorphic_number": _is_trimorphic_number,`
directly after it, before `"is_kaprekar": _is_kaprekar,`).

Acceptance criteria:
- `is_trimorphic_number(0);`, `is_trimorphic_number(1);`,
  `is_trimorphic_number(4);`, `is_trimorphic_number(5);`,
  `is_trimorphic_number(6);`, `is_trimorphic_number(9);` are all
  `true` — the single-digit trimorphic numbers (`4 ** 3 = 64` ends in
  `4`, `5 ** 3 = 125` ends in `5`, `6 ** 3 = 216` ends in `6`, `9 ** 3
  = 729` ends in `9`).
- `is_trimorphic_number(24);` is `true` — `24 ** 3 = 13824`, ends in
  `24`.
- `is_trimorphic_number(125);` is `true` — `125 ** 3 = 1953125`, ends
  in `125`.
- `is_trimorphic_number(2);` is `false` — `2 ** 3 = 8`, does not end
  in `2`.
- `is_trimorphic_number(100);` is `false` — `100 ** 3 = 1000000`, does
  not end in `100`.
- `is_trimorphic_number(76);` is `true` — `76` is automorphic too
  (`76 * 76 = 5776` ends in `76`) and every automorphic number is
  automatically trimorphic (see the Build note above), so this
  regression-guards that overlap rather than treating it as a
  contradiction.
- `is_trimorphic_number(24);` (already asserted `true` above) is the
  predicate's actual non-alias evidence: confirms `is_trimorphic_number`
  is genuinely broader than `is_automorphic`, not just another name for
  it, since `24` is trimorphic but *not* automorphic
  (`24 * 24 = 576` does not end in `24`).
- `is_trimorphic_number(-24);` is `false` — negative numbers are
  excluded (mirrors `is_automorphic`'s own convention).
- `is_trimorphic_number(1.5);` raises `CinderRuntimeError` matching
  `"is_trimorphic_number() requires an int, got float"` (via
  `_require_int`'s existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_automorphic`,
search `def _is_automorphic`), `tests/test_builtins.py` (new `class
TestIsTrimorphicNumber`, modeled directly on `class TestIsAutomorphic`,
search that name, for the true/false/non-alias/negative/type-error test
shapes above). Once merged, `README.md`'s Builtins bullet needs
`is_trimorphic_number` added near `is_automorphic`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Language: `else` clause on `do`-`while` loops (Python-style loop-`else`, the last loop kind)

Build: PR #352 added a Python-style `else { ... }` clause to plain
`while` loops, and task 2 in this file (once it merges) extends the
same clause to the foreach `for`-in form — both explicitly scoped
themselves to leave `DoWhileStmt` (`cinder/ast_nodes.py`, search
`class DoWhileStmt`) untouched. This task closes the last remaining
gap: `do { ... } while (cond)`. Verify the gap:
```sh
python3 -m cinder.cli eval 'do { print(1); } while (false) else { print("done"); }'
# -> <eval>:1:32: expected ';' after 'do ... while (...)', found 'else'
```

Semantics mirror `WhileStmt.else_branch` (see its docstring, search
`class WhileStmt`): the `else` block runs exactly once when control
falls out of the loop with no intervening `break` — `continue` does
not skip it, an uncaught exception/`return`/propagating labeled
`break`/`continue` does, since control never reaches the check in that
case. The one semantic wrinkle specific to `do`-`while` is that its
body always runs at least once (that is the entire point of the
construct — there is no "zero iterations" case the way an empty
`for`-in or an initially-false `while` condition has), so there is no
"else runs with the body never having executed" test case here the way
`while`/`for`-`else` both have; every `do`-`while`-`else` test
necessarily has the body run at least once before the `else` fires or
is skipped.

Grammar wrinkle: `do { ... } while (cond);` currently always ends in a
mandatory `;` (there is no body-shaped construct after the condition
the way `while`'s own body terminates the statement, so the `;` is
what closes it — see `_do_while_statement`, search `def
_do_while_statement`). An `else` clause changes that: if `else`
follows the condition's `)`, the else branch (parsed the same way
`_while_statement` parses its own, via `self._statement()`) is itself
what closes the statement — it already ends in a `}` (block) or a `;`
(single statement), so no separate semicolon is needed or accepted
there; the semicolon stays mandatory only when there is no `else`.
Unlike `while`-`else`, there is no dangling-`else`/if-attachment
concern to introduce: the trailing `else` sits after the `while (cond)`
clause, textually separated from the body by the entire condition —
any unbraced `if` inside the body already resolved its own `else`
while `_do_while_statement` parsed `body = self._statement()`, well
before the parser ever reaches the `while` keyword, let alone this new
`else` check.

Edit three files:

1. `cinder/ast_nodes.py` (search `class DoWhileStmt`), add one field
   at the end, after `label: "str | None" = None`:
```python
    else_branch: "Stmt | None" = None
```

2. `cinder/parser.py`'s `_do_while_statement` (search `def
   _do_while_statement`): replace the unconditional trailing
   `self._consume(TokenType.SEMICOLON, ...)` with an else-or-semicolon
   branch, and thread the result into the constructor call:
```python
    def _do_while_statement(self, label: "str | None" = None) -> Stmt:
        do_token = self._advance()
        self._loop_labels.append(label)
        body = self._statement()
        self._loop_labels.pop()
        self._consume(TokenType.WHILE, "'while' after 'do' body")
        self._consume(TokenType.LPAREN, "'(' after 'while'")
        condition = self._assignment()
        self._consume(TokenType.RPAREN, "')' after while condition")
        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            else_branch = self._statement()
        else:
            self._consume(TokenType.SEMICOLON, "';' after 'do ... while (...)'")
        return DoWhileStmt(
            condition, body, do_token.line, do_token.column, label, else_branch
        )
```

3. `cinder/interpreter.py`'s `DoWhileStmt` handling in `execute`
   (search `if isinstance(stmt, DoWhileStmt):`): track a `broke` flag
   through the existing loop exactly the way `WhileStmt`'s handling
   already does, then check it after the loop ends:
```python
        if isinstance(stmt, DoWhileStmt):
            broke = False
            while True:
                try:
                    self.execute(stmt.body, env)
                except _BreakSignal as signal:
                    if signal.label is not None and signal.label != stmt.label:
                        raise
                    broke = True
                    break
                except _ContinueSignal as signal:
                    if signal.label is not None and signal.label != stmt.label:
                        raise
                if not is_truthy(self.evaluate(stmt.condition, env)):
                    break
            if not broke and stmt.else_branch is not None:
                self.execute(stmt.else_branch, env)
            return
```
(Only the `broke = False` init, the `broke = True` before the `break`
in the `_BreakSignal` handler, and the final `if not broke and
stmt.else_branch is not None:` block are new — everything else is
unchanged, shown in full only so the exact insertion points are
unambiguous.)

Acceptance criteria (mirror `TestWhileElse`/the `test_while_else_*`
methods in `tests/test_interpreter.py`, search
`test_while_else_runs_on_normal_completion`, one-for-one where a
do-while equivalent makes sense):
- `do { x = 1; } while (false) else { done = true; }` runs the `else`
  — the loop completes its one iteration normally, condition then
  false, no `break`.
- `let i = 0; do { i = i + 1; } while (i < 3) else { done = true; }`
  also runs the `else` after all three iterations — normal multi-
  iteration completion.
- `do { break; } while (true) else { ran = true; }` does **not** run
  the `else` — a `break` on the very first iteration skips it.
- `let i = 0; do { i = i + 1; if (i == 1) { continue; } } while (i < 2)
  else { ran = true; }` still runs the `else` — `continue` does not
  skip it, only `break` does.
- `outer: do { do { break outer; } while (true); } while (true) else {
  ran = true; }` does **not** run the outer loop's `else` — a labeled
  `break` targeting the outer loop skips its `else`, exactly like
  `while`'s own labeled-break case.
- `fn f() { do { return 1; } while (false) else { return 2; } } f();`
  returns `1`, not `2` — `return` from the body skips the `else`.
- `do { x = 1; } while (false);` (no `else` at all) still behaves
  exactly as before, including still requiring and accepting the
  trailing `;` — a regression guard mirroring
  `test_while_without_else_still_behaves_as_before`.
- `do { } while (false) else x = 1;` (an unbraced single-statement
  `else`, not a block) parses and runs `x = 1` — confirms the `else`
  branch is parsed via the generic `_statement()` the same way
  `while`-`else`'s is, not hardcoded to require a block.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`DoWhileStmt`, search `class
DoWhileStmt`), `cinder/parser.py` (`_do_while_statement`, search `def
_do_while_statement`), `cinder/interpreter.py` (the `DoWhileStmt`
branch of `execute`, search `if isinstance(stmt, DoWhileStmt):`),
`tests/test_parser.py` (new `class TestDoWhileElse`, modeled on
`class TestWhileElse`, search that name, for the parse-shape
assertions, including the else-vs-semicolon grammar wrinkle above),
`tests/test_interpreter.py` (new `class TestDoWhileElse`, modeled on
the `test_while_else_*` methods inside `TestWhileStatement`, search
`test_while_else_runs_on_normal_completion`, for the runtime behavior
above). Once merged, `README.md`'s Control flow bullet needs a
`do`-`while`-`else` mention next to the existing `while`/`for`-`else`
ones, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_munchausen_number` — digit-to-its-own-power sum test

Build: `is_strong_number` (`cinder/builtins.py`, search `def
_is_strong_number`) already asks whether a number equals the sum of
the *factorial* of each of its digits (e.g. `145 = 1! + 4! + 5!`), and
`is_armstrong`/`is_disarium` already raise each digit to a *fixed*
power (digit count, or digit position) and sum — but nothing raises
each digit to *its own value* and sums, the classic "Munchausen
number" property (named for Baron Munchausen's tall tales of lifting
himself by his own hair — a number "lifting itself" out of its own
digits). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_munchausen_number(3435));'
# -> <eval>:1:7: undefined name 'is_munchausen_number' (did you mean 'is_lucas_number'?)
```

The one domain subtlety: by convention (the definition everyone
publishing a list of Munchausen numbers uses), `0` raised to the power
of itself contributes `0` to the sum, not `1` — even though Python's
own `0 ** 0` evaluates to `1`. Without that override, `10` would
wrongly evaluate its digit sum as `1**1 + 0**0 = 1 + 1 = 2 != 10`
either way (still correctly `false` here), but the override matters
for `0` itself: `0`'s own digit is `0`, and under the `0**0 := 0`
convention its digit-power sum is `0`, which equals the number — so
`0` is a (trivial) Munchausen number, matching every published
reference list. Getting this wrong (using Python's raw `0 ** 0 == 1`)
would make `0` evaluate to `false` instead, silently disagreeing with
the standard definition.

Add to `cinder/builtins.py`, directly after `_is_strong_number` (search
`def _is_strong_number`, immediately before `def _is_leap_year`) —
keeps it grouped with the other digit-power-sum predicates:
```python
def _is_munchausen_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_munchausen_number", arguments, 1, line, column)
    value = _require_int("is_munchausen_number", arguments[0], line, column)
    if value < 0:
        return False
    total = 0
    for digit in str(value):
        d = int(digit)
        total += d ** d if d != 0 else 0
    return total == value
```
Also register the new dict entry (search `"is_strong_number":
_is_strong_number,`, add `"is_munchausen_number":
_is_munchausen_number,` directly after it, before `"is_leap_year":
_is_leap_year,`).

Acceptance criteria:
- `is_munchausen_number(0);` is `true` — the trivial case under the
  `0**0 := 0` convention (see the Build note above).
- `is_munchausen_number(1);` is `true` — `1 ** 1 = 1`.
- `is_munchausen_number(3435);` is `true` — the canonical example:
  `3**3 + 4**4 + 3**3 + 5**5 = 27 + 256 + 27 + 3125 = 3435`.
- `is_munchausen_number(438579088);` is `true` — the other known
  base-10 Munchausen number, confirming the check isn't hardcoded to
  4-digit inputs.
- `is_munchausen_number(2);` is `false` — `2 ** 2 = 4 != 2`.
- `is_munchausen_number(24);` is `false` — `2**2 + 4**4 = 4 + 256 =
  260 != 24`.
- `is_munchausen_number(100);` is `false` — exercises the `0**0 := 0`
  override on a non-trivial multi-digit number: `1**1 + 0**0 + 0**0 =
  1 + 0 + 0 = 1 != 100`.
- `is_munchausen_number(-3435);` is `false` — negative numbers are
  excluded (mirrors `is_strong_number`'s own convention).
- `is_munchausen_number(1.5);` raises `CinderRuntimeError` matching
  `"is_munchausen_number() requires an int, got float"` (via
  `_require_int`'s existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_strong_number`,
search `def _is_strong_number`), `tests/test_builtins.py` (new `class
TestIsMunchausenNumber`, modeled directly on `class
TestIsStrongNumber`, search that name, for the true/false/domain-edge/
type-error test shapes above). Once merged, `README.md`'s Builtins
bullet needs `is_munchausen_number` added near `is_strong_number`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Language: `-` (difference) operator for lists (set-style, mirrors map `-`)

Build: PR #356 gave `-` a map-map branch (key-based removal,
`{"a": 1, "b": 2} - {"a": 1}` is `{"b": 2}`) but explicitly scoped
itself to `map`/`map` only, leaving list-list `-` to fall through to
the numeric-only path and error out — the same gap the map branch
itself closed for maps. Cinder's list builtins already answer this
exact question as a function (`difference()`, `cinder/builtins.py`,
search `def _difference`: dedupes the left list, keeps only elements
not present in the right, both lists treated as unordered sets — the
same convention `union`/`intersection`/`symmetric_difference` already
share). This task gives that same set-style difference an infix `-`
spelling for lists, exactly as `-` is already `difference()`'s
map-shaped sibling operator for maps. Verify the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2, 3] - [2]);'
# -> <eval>:1:17: unsupported operand types for '-': list and list
```

Note `tests/test_interpreter.py`'s existing `TestMapDifference` class
already has `test_list_minus_map_raises` (`[1, 2] - {"a": 1}` errors)
and `test_map_minus_list_raises` (`{"a": 1} - [1, 2]` errors) — those
stay exactly as they are, since this task only adds a list-**list**
branch; mixed list/map operands remain a type error, unchanged.

`cinder/interpreter.py` has no import of `cinder/builtins.py` (checked
— builtins.py is the one that would need to import from interpreter.py
for shared helpers like `values_equal`, not the reverse, to avoid a
circular import), so don't import `_difference`/`_dedupe` from
builtins.py; instead inline the same two-step "dedupe the left list,
then drop anything found in the right" logic using `values_equal`
(already imported and used elsewhere in `interpreter.py`, e.g. the
`EQEQ` branch a few lines above) rather than Python's native `==`/`in`,
matching `_dedupe`/`_contains_value`'s own reasoning (native `==`
would wrongly conflate `1` and `true`, which `values_equal` keeps
distinct).

Edit `cinder/interpreter.py`'s `_apply_binary_operator`, the `MINUS`
branch (search `if op == TokenType.MINUS:`): add a list-list case
alongside the existing dict-dict one, before the branch falls through
to `_numeric_op`:
```python
        if op == TokenType.MINUS:
            if isinstance(left, dict) and isinstance(right, dict):
                return {key: value for key, value in left.items() if key not in right}
            if isinstance(left, list) and isinstance(right, list):
                deduped: list = []
                for element in left:
                    if not any(values_equal(element, kept) for kept in deduped):
                        deduped.append(element)
                return [
                    element
                    for element in deduped
                    if not any(values_equal(element, other) for other in right)
                ]
            return self._numeric_op(operator, left, right, lambda a, b: a - b)
```
(Only the new `isinstance(left, list) and isinstance(right, list)`
block is added — the dict branch above it and the `_numeric_op`
fallback below it are unchanged.)

The compound-assignment desugaring (`-=`) already works for free once
`-` itself handles lists, exactly as `TestMapDifference`'s own
`test_compound_assignment_on_identifier`/`_index_target`/`_dot_target`
tests document for maps — no separate wiring needed.

Acceptance criteria (mirror `TestMapDifference` in
`tests/test_interpreter.py`, search that class, one-for-one where a
list equivalent makes sense):
- `[1, 2, 3] - [2]` is `[1, 3]` — the basic case.
- `[1, 2, 2, 3] - [2]` is `[1, 3]` — the left side is deduped, so a
  repeated element that gets removed leaves only one gap, not one per
  occurrence.
- `[1, 2, 3] - []` is `[1, 2, 3]` — empty right is a no-op (aside from
  deduping the left, matching `difference()`'s own behavior).
- `[] - [1, 2]` is `[]` — empty left stays empty.
- `[1, 2] - [1, 2]` is `[]` — removing every element empties the list.
- `[1, 2] - [3, 4]` is `[1, 2]` — no overlap has no effect (beyond
  dedup).
- Does not mutate inputs: `let a = [1, 2]; let c = a - [1];` leaves `a`
  as `[1, 2]` and `c` as `[2]`.
- Left-associative: `[1, 2, 3] - [1] - [2]` is `[3]`.
- Compound assignment works: `let xs = [1, 2]; xs -= [1];` leaves `xs`
  as `[2]` (identifier target); also test an index target
  (`let xs = [[1, 2]]; xs[0] -= [1];`) and a dot target
  (`let obj = {"l": [1, 2]}; obj.l -= [1];`).
- `[1, true, 2] - [true]` is `[1, 2]` — uses `values_equal`, not
  Python's native `==`/`in`, so `1` and `true` are not conflated (a
  `1` in the left list survives a `[true]` right side).
- `[1, 2] - {"a": 1}` and `{"a": 1} - [1, 2]` still both raise
  `CinderRuntimeError` matching `"unsupported operand types for '-':
  ..."` — regression guards for the two existing
  `test_list_minus_map_raises`/`test_map_minus_list_raises` tests,
  confirming mixed list/map operands are still a type error.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`MINUS` branch, search `if op == TokenType.MINUS:`), `tests/test_interpreter.py`
(new `class TestListDifference`, modeled directly on
`class TestMapDifference`, search that name, for the test shapes
above — or add methods to `TestMapDifference` itself if renaming it to
something like `TestDifferenceOperator` reads better; either is fine,
Engineer's call). Once merged, `README.md`'s language-operators bullet
needs a list-`-` mention next to the existing map-`-` one, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's
next grooming pass, not this task.

---

## 5. Language: `else` clause on C-style `for` loops (closes the loop-`else` arc for all four loop kinds)

Build: `while` (#352), the foreach `for`-in form (#358), and — once task 2
in this file merges — `do`-`while` will all have a trailing Python-style
`else { ... }` clause. The one loop kind left out every time is the
classic three-clause `for (init; cond; step) { ... }` (`ForCStmt`,
`cinder/ast_nodes.py`, search `class ForCStmt`). This task closes that
last gap. Verify it:
```sh
python3 -m cinder.cli eval 'for (let i = 0; i < 3; i = i + 1) { print(i); } else { print("done"); }'
# -> <eval>:1:46: expected ';' after for-loop init  (parses "else" as a
#    fresh statement, i.e. the C-style for loop has no else support at all)
```

Semantics mirror `ForStmt.else_branch` (see its docstring, search `class
ForStmt`) and the C-style loop's own body/exit shape: the `else` block
runs exactly once when the condition clause evaluates false with no
intervening `break` — including immediately, if the condition was
already false before the first iteration (`for (; false;) { ... } else {
ran = true; }` still runs the `else`), and including an omitted
condition clause never being false on its own (`for (;;) { if (x) {
break; } } else { ... }` can only skip the `else` via that `break`, never
by falling out the condition, since an empty condition is always-true —
see `ForCStmt`'s own docstring). `continue` does not skip it; an
uncaught exception, `return`, or a propagating labeled `break`/`continue`
does, since control never reaches the post-loop check in that case.

Grammar wrinkle: exactly like `for`-in (`_for_statement`, search `def
_for_statement`), the C-style form's body is always a brace-delimited
`Block` (`self._block()`, never a bare single statement — see
`_for_c_statement`'s existing `expected '{' before for-loop body` check),
so there is no dangling-`else`/if-attachment ambiguity to resolve: an
`else` immediately following the body's closing `}` unambiguously
belongs to the `for`, the same reasoning `_for_statement` already
documents for its own trailing `else` check.

Edit three files:

1. `cinder/ast_nodes.py` (search `class ForCStmt`), add one field at the
   end, after `label: "str | None" = None`, and extend the docstring:
```python
@dataclass(frozen=True)
class ForCStmt:
    """Classic three-clause `for (init; cond; step) { ... }`, distinct from
    the foreach `ForStmt` above. `init`/`step` are `None` when their clause
    is empty (`for (;;) { ... }` is a valid infinite loop); `condition` is
    `None` when omitted, treated as always-true at execution time.

    `else_branch` is `None` unless the loop carries a trailing
    `else { ... }` clause; when present, it runs exactly once, when the
    condition becomes false *without* an intervening `break` — including
    immediately, if the condition was already false (or omitted, which
    never happens on its own since an omitted condition is always-true) —
    mirroring `ForStmt`/`WhileStmt`'s own `else_branch`. `continue` does
    not skip it (only `break` does); an uncaught exception, `return`, or
    propagating labeled `break`/`continue` from the body also skips it.
    """

    init: "Stmt | None"
    condition: "Expr | None"
    step: "Stmt | None"
    body: "Block"
    line: int
    column: int
    label: "str | None" = None
    else_branch: "Stmt | None" = None
```

2. `cinder/parser.py`'s `_for_c_statement` (search `def
   _for_c_statement`): after the existing `body = self._block()` /
   `self._loop_labels.pop()` lines and before the `return ForCStmt(...)`,
   add the same else-check `_for_statement` already has, and thread it
   into the constructor call:
```python
        self._loop_labels.append(label)
        body = self._block()
        self._loop_labels.pop()
        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            else_branch = self._statement()
        return ForCStmt(
            init,
            condition,
            step,
            body,
            for_token.line,
            for_token.column,
            label,
            else_branch=else_branch,
        )
```
(Only the `else_branch = None` block and the `else_branch=else_branch`
constructor argument are new — everything above is unchanged, shown in
full only so the exact insertion point is unambiguous.)

3. `cinder/interpreter.py`'s `_execute_for_c` (search `def
   _execute_for_c`): track a `broke` flag through the existing loop
   exactly the way `_execute_for` already does, then check it after the
   loop ends:
```python
    def _execute_for_c(self, stmt: ForCStmt, env: Environment) -> None:
        loop_env = Environment(env)
        if stmt.init is not None:
            self.execute(stmt.init, loop_env)
        broke = False
        while True:
            iter_env = Environment(env)
            iter_env._values.update(loop_env._values)
            iter_env._frozen.update(loop_env._frozen)
            if stmt.condition is not None and not is_truthy(
                self.evaluate(stmt.condition, iter_env)
            ):
                break
            try:
                self.execute(stmt.body, iter_env)
            except _BreakSignal as signal:
                if signal.label is not None and signal.label != stmt.label:
                    raise
                broke = True
                break
            except _ContinueSignal as signal:
                if signal.label is not None and signal.label != stmt.label:
                    raise
            loop_env._values.update(iter_env._values)
            loop_env._frozen.update(iter_env._frozen)
            if stmt.step is not None:
                self.execute(stmt.step, loop_env)
        if not broke and stmt.else_branch is not None:
            self.execute(stmt.else_branch, env)
```
(Only the `broke = False` init, the `broke = True` before the `break` in
the `_BreakSignal` handler, and the final `if not broke and
stmt.else_branch is not None:` block are new — everything else, including
the existing docstring-documented per-iteration `Environment` copying, is
unchanged.)

Acceptance criteria (mirror `TestForElse` in `tests/test_interpreter.py`,
search that class, one-for-one where a C-style equivalent makes sense):
- `for (let i = 0; i < 3; i = i + 1) { x = i; } else { done = true; }`
  runs the `else` — all three iterations complete, condition then false,
  no `break`.
- `for (; false;) { x = 1; } else { done = true; }` also runs the `else`
  — the condition is false before the first iteration, body never runs,
  mirrors `for`-in's own empty-iterable case.
- `let i = 0; for (;; i = i + 1) { if (i == 2) { break; } } else { ran =
  true; }` does **not** run the `else` — a `break` skips it even with an
  always-true omitted condition.
- `let i = 0; for (; i < 3; i = i + 1) { if (i == 1) { continue; } }
  else { ran = true; }` still runs the `else` — `continue` does not skip
  it, only `break` does.
- `outer: for (let i = 0; i < 1; i = i + 1) { for (let j = 0; j < 1; j =
  j + 1) { break outer; } } else { ran = true; }` does **not** run the
  outer loop's `else` — a labeled `break` targeting the outer loop skips
  its `else`, exactly like `while`/`for`-in's own labeled-break case.
- `fn f() { for (let i = 0; i < 1; i = i + 1) { return 1; } else { return
  2; } } f();` returns `1`, not `2` — `return` from the body skips the
  `else`.
- `for (let i = 0; i < 2; i = i + 1) { x = i; }` (no `else` at all) still
  behaves exactly as before — a regression guard mirroring
  `test_while_without_else_still_behaves_as_before`/the `for`-in
  equivalent.
- `for (let i = 0; i < 1; i = i + 1) { } else x = 1;` (an unbraced
  single-statement `else`, not a block) parses and runs `x = 1` —
  confirms the `else` branch is parsed via the generic `_statement()` the
  same way `while`/`for`-in's own is, not hardcoded to require a block.
- A closure captured inside the `else` branch still sees the loop's
  final `init`-declared binding value (e.g. `let fns = []; for (let i =
  0; i < 3; i = i + 1) { } else { fns = push(fns, fn() { return i; }); }
  fns[0]();` returns `3`) — the `else` runs in the outer `env`, after
  `loop_env`'s values have been copied back in on the last completed
  iteration, not in a stale `iter_env`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`ForCStmt`, search `class
ForCStmt`), `cinder/parser.py` (`_for_c_statement`, search `def
_for_c_statement`), `cinder/interpreter.py` (`_execute_for_c`, search
`def _execute_for_c`), `tests/test_parser.py` (new `class
TestForCElse`, modeled on `class TestForElse`, search that name, for the
parse-shape assertions), `tests/test_interpreter.py` (new `class
TestForCElse`, modeled on `class TestForElse`, search that name — it
sits right after the existing `class TestForCStatement`, search that
name, for context — for the runtime behavior above). Once merged,
`README.md`'s Control flow bullet needs a C-style-for-else mention next
to the existing `while`/`for`-in/`do`-`while` ones, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 6. Language: `throw`/`catch` carry any value, not just strings

Build: `throw` (`cinder/interpreter.py`, search `if isinstance(stmt,
ThrowStmt):`) currently rejects any thrown value that isn't a `str`, and
`catch (e)` (`_execute_try`, search `def _execute_try`) always binds `e`
to `error.message` — the *string* every `CinderRuntimeError` carries,
whether it came from a user `throw` or an internal type/arity error. This
is more than just a limitation: because the "must be a string" check
itself raises a `CinderRuntimeError`, throwing a non-string value gets
*caught by the surrounding `catch`* with `e` bound to the check's own
error text, not the value the user actually threw — a confusing double
failure, not a clean rejection. Verify the gap:
```sh
python3 -m cinder.cli eval 'try { throw {"kind": "MyError", "msg": "oops"}; } catch (e) { print(e.msg); }'
# -> <eval>:1:70: string index must be an int, got string
#    (e is bound to "throw requires a string message, got map" — the
#    type-check's own message, not the thrown map — so `.msg` tries to
#    index that string and blows up on an unrelated error)
```

This task lets `throw` accept any Cinder value and makes `catch` bind
the original value, not a stringified message — while leaving every
*internal* error (type errors, arity errors, etc., the ~430 other
`CinderRuntimeError(...)` call sites across `cinder/interpreter.py` and
`cinder/builtins.py`) behaving exactly as before, since none of those
call sites pass the new field described below.

Edit two files:

1. `cinder/errors.py`'s `CinderRuntimeError` (search `class
   CinderRuntimeError`): add an optional `value` field, defaulting to
   the error's own `message` when not given. Use a module-level sentinel
   (not `None`) so a genuinely thrown `nil` — which is Python `None` at
   runtime, see `PROJECT.md`'s truthiness note — isn't mistaken for "no
   value supplied":
```python
_UNSET = object()


class CinderRuntimeError(CinderError):
    """Raised by the interpreter for errors detected during evaluation.

    `frames` records the call chain the error passed through on its way out,
    one `(function_name, call_line, call_column)` tuple per call-site,
    innermost call first. Empty for an error raised directly at top level.

    `value` is the original Cinder value a `catch (e)` clause binds `e`
    to. It defaults to `message` itself (every internal engine error is,
    in effect, a string-valued exception) unless explicitly overridden —
    `ThrowStmt` handling is the only caller that does, passing the
    literal value the user threw.
    """

    def __init__(
        self, message: str, line: int, column: int, value: object = _UNSET
    ):
        super().__init__(message, line, column)
        self.frames: list[tuple[str, int, int]] = []
        self.value = message if value is _UNSET else value
```
(Every other one of the ~430 existing `CinderRuntimeError(...)` call
sites is unchanged — none of them pass `value=`, so `error.value ==
error.message` for all of them, exactly matching today's behavior.)

2. `cinder/interpreter.py`, two spots:
   - The `ThrowStmt` branch of `execute` (search `if isinstance(stmt,
     ThrowStmt):`): drop the string-only type check entirely and pass
     the evaluated value straight through, using the module's existing
     `stringify` (search `def stringify`, already used elsewhere in this
     file — no new import needed) to build the display message:
```python
        if isinstance(stmt, ThrowStmt):
            value = self.evaluate(stmt.expression, env)
            raise CinderRuntimeError(
                stringify(value), stmt.line, stmt.column, value=value
            )
```
   - `_execute_try` (search `def _execute_try`): bind the catch name to
     `error.value` instead of `error.message`:
```python
                catch_env = Environment(env)
                if stmt.catch_name is not None:
                    catch_env.define(stmt.catch_name, error.value)
```
(Only the `error.message` → `error.value` change; everything else in
`_execute_try`, including the `finally` handling, is untouched.)

Acceptance criteria:
- `try { throw "boom"; } catch (e) { print(e); }` still prints `boom` —
  regression guard, matches the existing
  `test_thrown_string_is_caught_and_bound`.
- `throw "boom";` uncaught still has `.message == "boom"` at line 1,
  column 1 — regression guard, matches the existing
  `test_uncaught_throw_raises_with_own_line_and_column`.
- `try { throw {"kind": "MyError", "msg": "oops"}; } catch (e) { print(e.msg); }`
  prints `oops` — the exact gap demonstrated above, now fixed cleanly.
- `try { throw 42; } catch (e) { print(e + 1); }` prints `43` — the
  caught value keeps its real type (`int`), not a stringified form.
- `try { throw [1, 2, 3]; } catch (e) { print(e[1]); }` prints `2`.
- `try { throw nil; } catch (e) { print(e == nil); }` prints `true` —
  confirms the sentinel correctly distinguishes "no value" from a
  genuinely thrown `nil` (`None` at the Python level).
- `try { throw false; } catch (e) { print(e); }` prints `false` — a
  second falsy-value regression guard alongside `nil`, since `false`
  must not be confused with "value not supplied" either.
- `throw 42;` uncaught now succeeds (no longer a type error): `.message
  == "42"` and `.value == 42`. Replaces `test_throw_non_string_raises_type_error`
  (delete it — it asserted exactly the restriction this task removes).
- `throw {"a": 1};` uncaught has `.message == '{"a": 1}'` — reuses
  `stringify`'s existing map-rendering format for the display message
  (matches what `print({"a": 1});` already outputs).
- Internal errors are unaffected: `try { 1 + "a"; } catch (e) { print(e); }`
  still prints the exact same type-error string it always has, since
  `_apply_binary_operator`'s `CinderRuntimeError(...)` call (like the
  ~430 others) never passes `value=`, so `error.value` still equals
  `error.message` there.
- `test_throw_inside_nested_call_reports_call_stack` and
  `test_finally_runs_before_throw_propagates_uncaught` still pass
  unmodified — call-stack frames and `finally` ordering are untouched.
- Full test suite passes.

Likely files: `cinder/errors.py` (`CinderRuntimeError`, search `class
CinderRuntimeError`), `cinder/interpreter.py` (`ThrowStmt` branch of
`execute`, search `if isinstance(stmt, ThrowStmt):`; `_execute_try`,
search `def _execute_try`), `tests/test_interpreter.py` (`class
TestThrowStatement`, search that name — delete
`test_throw_non_string_raises_type_error`, add new tests for the
non-string throw/catch cases above). Once merged, `README.md`'s
error-handling bullet needs a mention that `throw`/`catch` carry any
value now (not just strings), its "Status & roadmap" section needs
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
