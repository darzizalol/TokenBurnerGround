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

## 1. Standard library: `is_undulating` — digit-alternation classification

Build: the breadth task after task 5's depth work (raw string literals)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that `multiplicative_persistence` has landed via PR
#270, dropping the count to the 5-task floor. The digit-pattern cluster
in `cinder/builtins.py` (`is_repdigit`, `is_palindrome_number`,
`is_armstrong`, `is_harshad`, `is_automorphic`) has no test for
*alternation* — a number whose decimal digits strictly alternate
between exactly two distinct values, like `121` or `2323`, sometimes
called an "undulating number". Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_undulating(121));'
# -> CinderRuntimeError: undefined name 'is_undulating'
```

Add to `cinder/builtins.py`, registered right after `is_repdigit`
(search `def _is_repdigit`, immediately before `_is_perfect_square`):

```python
def _is_undulating(arguments: list, line: int, column: int) -> object:
    _require_arity("is_undulating", arguments, 1, line, column)
    value = _require_int("is_undulating", arguments[0], line, column)
    if value < 0:
        return False
    digits = str(value)
    if len(digits) < 3 or digits[0] == digits[1]:
        return False
    return all(digit == digits[i % 2] for i, digit in enumerate(digits))
```

**The two things that make this well-defined, not ambiguous**: a
genuine undulation needs at least three digits (`11` merely repeats one
digit twice — it is not "alternating" in any meaningful sense, and
`is_repdigit` already covers the same-digit case), and the two digits
in the pattern must actually be distinct (`111` is a repdigit, not an
undulation, even though it trivially "alternates" between one value and
itself). Both are checked up front (`len(digits) < 3 or digits[0] ==
digits[1]`) before the alternation scan runs, so a short or
constant-digit input returns `false` in one step rather than the scan
vacuously succeeding. Negative input returns `false` rather than
raising, the same convention `is_palindrome_number`/`is_repdigit`/
`is_armstrong`/`is_strong_number` already use for this digit-pattern
cluster (unlike `is_perfect_cube`/`is_perfect_power`, where a negative
result is sometimes legitimately `true` — a digit-pattern property has
no comparable negative case worth special-casing).

Acceptance criteria:
- `is_undulating(121);` is `true` — three digits, alternating 1-2-1.
- `is_undulating(2323);` is `true` — four digits, alternating 2-3-2-3.
- `is_undulating(12121);` is `true` — five digits, longer alternation.
- `is_undulating(101);` is `true` — alternating 1-0-1; zero is a valid
  alternating digit.
- `is_undulating(111);` is `false` — three digits but only one distinct
  value (a repdigit, not an undulation).
- `is_undulating(11);` is `false` — only two digits, below the
  three-digit minimum.
- `is_undulating(1);` is `false` — single digit.
- `is_undulating(0);` is `false` — single digit.
- `is_undulating(123);` is `false` — three digits, none repeat, not an
  alternating pattern.
- `is_undulating(1210);` is `false` — four digits, matches the
  alternating pattern for the first three (1-2-1) then breaks at the
  fourth (`0`, not `2`).
- `is_undulating(-121);` is `false` — negative input, following the
  cluster's existing convention rather than raising.
- `is_undulating(5.0);` raises `CinderRuntimeError` matching
  `"is_undulating() requires an int, got float"`.
- `is_undulating(true);` raises `CinderRuntimeError` matching
  `"is_undulating() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_repdigit`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py` (model on `class TestIsRepdigit` and `class
TestIsPalindromeNumber`, search either name). Once merged, `README.md`'s
Builtins bullet needs `is_undulating` added near `is_repdigit`/
`is_palindrome_number`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 2. Language: range literal `a..b` — sugar over the existing `range()` builtin

Build: the depth task after task 4's breadth work (`is_undulating`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that comma-separated `let`/`const` declarations and `cbrt` have
both landed via PR #271 and PR #272, dropping the count from 6 to 4 in
one stretch (two merges, no grooming pass in between). The `range()`
builtin (`cinder/builtins.py`) already builds `[start, start+1, ...,
stop-1]` from two int arguments, but there is no literal syntax for it —
every bounded `for` loop over a numeric range needs the clunky
`for i in range(1, 5) { ... }` rather than a direct `for i in 1..5 {
... }`. Verify the gap:
```sh
python3 -m cinder.cli eval 'for i in 1..5 { print(i); }'
# -> ParseError: expected ')' after arguments, found '.'
```
(the `1` parses fine as the `for`-loop's iterable expression, then `..`
is unrecognized — today `.` only ever starts an ordinary single-dot
member access or, when immediately followed by two more dots, an
existing `...` spread/rest token; nothing currently recognizes exactly
two dots in a row.)

**Lexing** (`cinder/lexer.py`): `_dot` currently distinguishes only `.`
(single) from `...` (three, spread/rest) — nothing else reaches this
method, since `tokenize()`'s dispatch only calls `_dot` when the just-
consumed character was itself a single `.`. Add a middle branch, checked
after the existing three-dot check and before the plain-`.` fallback,
for exactly two dots:
```python
    def _dot(self, start_line: int, start_col: int):
        if self._peek() == "." and self._peek_next() == ".":
            self._advance()
            self._advance()
            self.tokens.append(
                Token(TokenType.DOT_DOT_DOT, "...", None, start_line, start_col)
            )
        elif self._peek() == ".":
            self._advance()
            self.tokens.append(
                Token(TokenType.DOT_DOT, "..", None, start_line, start_col)
            )
        else:
            self.tokens.append(Token(TokenType.DOT, ".", None, start_line, start_col))
```
No existing valid program changes meaning: two dots in a row (`1..5`)
was already a guaranteed `ParseError` before this task (an ordinary
`.` member-access immediately followed by another `.` with no property
name between them), so claiming that exact adjacency for a new token is
safe. Add `DOT_DOT = auto()` to `cinder/tokens.py`, next to `DOT`/
`DOT_DOT_DOT`.

**Parsing** (`cinder/parser.py`): add a new AST node `RangeExpr` in
`cinder/ast_nodes.py`, sibling to `SliceExpr` (same frozen-dataclass
shape, no `step`/`obj` — just the two bounds):
```python
@dataclass(frozen=True)
class RangeExpr:
    start: "Expr"
    end: "Expr"
    line: int
    column: int
```
Register it in the `Expr` union alongside `SliceExpr`. Insert a new
precedence level between `_membership` and `_comparison` — `_membership`
already calls `_comparison()` for both its operands, so no change is
needed there; `_comparison()` itself currently calls `self._bitor()` in
two places (building its `operands` list) — change both to
`self._range_expr()`, and add:
```python
    def _range_expr(self) -> Expr:
        expr = self._bitor()
        if self._check(TokenType.DOT_DOT):
            dots = self._advance()
            end = self._bitor()
            return RangeExpr(expr, end, dots.line, dots.column)
        return expr
```
Non-associative (an `if`, not a `while`) — `1..5..10` is deliberately a
`ParseError` (`"expected end of input, found '..'"` at the second
`..`), the same way a bare `1 < 2 < 3` would be were it not for
`ChainedComparison`'s special handling elsewhere; ranges get no
equivalent chaining. This placement makes `..` bind looser than
arithmetic/bitwise operators (so `1 + 1..5 * 2` is `2..10`) but tighter
than comparisons, `in`, `and`/`or`, and assignment — so
`for i in 1..5 { ... }` parses `1..5` as one range expression before
`in`'s membership-loop machinery ever sees it (the `for`-loop's iterable
expression is parsed via the ordinary top-level expression chain, same
as any other expression), and `x in 1..5` (testing whether `x` falls in
the range) works too, since `_membership` parses its right operand via
`_comparison()`, which now includes the new range level.

**Interpreter** (`cinder/interpreter.py`): add a dispatch branch in
`evaluate()`, alongside the existing `SliceExpr` branch:
```python
        if isinstance(expr, RangeExpr):
            return self._evaluate_range(expr, env)
```
And the method itself, reusing the exact int-validation and
list-construction `_range` (`cinder/builtins.py`) already does rather
than duplicating it — call `_range` directly with the evaluated bounds
as its `arguments` list, so both spellings share one implementation and
one error message:
```python
    def _evaluate_range(self, expr: RangeExpr, env: Environment) -> object:
        start = self.evaluate(expr.start, env)
        end = self.evaluate(expr.end, env)
        from cinder.builtins import _range  # local: builtins.py imports
        # from interpreter.py at module level already, so a top-level
        # import the other way round here would be circular; importing
        # inside the method instead defers it until both modules have
        # finished loading, which is safe.
        return _range([start, end], expr.line, expr.column)
```
`cinder/interpreter.py` does not import `cinder/builtins.py` today —
confirm this is still true before writing the import (`grep -n "^from
cinder.builtins\|^import cinder.builtins" cinder/interpreter.py`
should currently print nothing); if some other task already added a
top-level import in the meantime, reuse it instead of adding a second,
local one, but check it isn't circular first. This means `1..5` and
`range(1, 5)` are exactly equivalent, including
identical error messages (`"range() requires int arguments, got
{type}"`) on a non-int bound — deliberate, since introducing a second,
subtly-different error message for the same underlying operation would
be a maintenance trap, not a feature.

Acceptance criteria:
- `print(1..5);` prints `[1, 2, 3, 4]` — same as `range(1, 5)`, end
  exclusive.
- `for i in 1..5 { print(i); }` prints `1`, `2`, `3`, `4`, one per line.
- `print(0..0);` prints `[]` — empty range, same as `range(0, 0)`.
- `print(x in 1..5);` with `let x = 3;` prints `true`; with `let x =
  5;` prints `false` (end exclusive, matching `range()`).
- `print(1 + 1..5 * 2);` prints `[2, 3, ..., 9]` (i.e. `range(2, 10)`)
  — arithmetic on both bounds evaluates before `..` is applied.
- `print(5..1);` prints `[]` — descending bounds produce an empty list,
  same as `range(5, 1)` (no implicit reversal).
- `1..2.5;` raises `CinderRuntimeError` matching `"range() requires int
  arguments, got float"` — same error `range(1, 2.5)` already raises.
- `1..5..10;` raises `ParseError` — ranges do not chain.
- `let xs = [x for x in 1..5]; print(xs);` prints `[1, 2, 3, 4]` — usable
  as a comprehension source, since it's just an ordinary expression
  producing a list.
- `print(range(1, 5) == 1..5);` prints `true` (or the language's
  existing list-equality behavior — confirm which comparison operator
  the test suite already uses for list equality and match it) — the two
  spellings are the same value.
- A single dot (`m.key`) and a real spread/rest (`...rest`, `f(...args)`)
  are both completely unaffected — every existing dot-access and
  spread/rest test continues to pass unmodified.
- Full test suite passes.

Likely files: `cinder/tokens.py` (`DOT_DOT`), `cinder/lexer.py`
(`_dot`), `cinder/ast_nodes.py` (`RangeExpr`), `cinder/parser.py`
(`_comparison`, new `_range_expr`), `cinder/interpreter.py` (`evaluate`,
new `_evaluate_range`), `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_interpreter.py` (model on whatever test classes cover
`SliceExpr`/slicing, search `class TestSlic`). Once merged, `README.md`'s
Operators bullet needs a mention of the range literal near the existing
`in`/slicing operators, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not this
task.

---

## 3. Standard library: `is_kaprekar` — numbers whose square splits back into themselves

Build: the breadth task after task 5's depth work (range literal `a..b`)
per `PROJECT.md`'s breadth-vs-depth policy, continuing the two-tasks-
at-once restock started by task 5 (see task 5's own restock note — two
merges, comma-separated `let`/`const` declarations and `cbrt`, dropped
the backlog from 6 to 4 in one stretch with no grooming pass in
between, so this pass adds both a depth and a breadth task to get back
to 6). A Kaprekar number is a positive integer `n` whose square, when
split into a right part and a left part at some digit boundary, sums
back to `n` — e.g. `45`: `45 ** 2 == 2025`, split as `20` and `25`,
`20 + 25 == 45`. Nothing in the existing digit-pattern/number-theory
cluster (`is_automorphic`, `is_harshad`, `is_perfect_cube`, ...) tests
this; `is_automorphic` (`str(value * value).endswith(str(value))`) is
actually the fixed special case of a Kaprekar split at the boundary
where the right part has exactly as many digits as `n` itself, so this
task is a natural generalization sitting right next to it. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(is_kaprekar(45));'
# -> CinderRuntimeError: undefined name 'is_kaprekar'
```

Add to `cinder/builtins.py`, registered right after `_is_automorphic`
(search `def _is_automorphic`, immediately before `_is_harshad`):
```python
def _is_kaprekar(arguments: list, line: int, column: int) -> object:
    _require_arity("is_kaprekar", arguments, 1, line, column)
    value = _require_int("is_kaprekar", arguments[0], line, column)
    if value < 1:
        return False
    square = value * value
    digits = str(square)
    for split in range(1, len(digits) + 1):
        right = square % (10 ** split)
        left = square // (10 ** split)
        if right != 0 and left + right == value:
            return True
    return False
```
The `right != 0` guard skips vacuous splits (a leading-zero right part,
e.g. `n=10`, `square=100`: the `split=2` boundary gives `right=0,
left=1`, which is not a real two-part split); the loop runs `split` up
to and including `len(digits)` (not stopping one short) so the
whole-square/zero-left split is reachable too — this is what makes `1`
qualify (`1 ** 2 == 1`, `split=1` gives `right=1, left=0`,
`0 + 1 == 1`) without a separate trivial-case branch, matching the
standard sequence (OEIS A006886: `1, 9, 45, 55, 99, 297, 703, 999,
...`). `value < 1` returns `false` up front rather than raising,
matching the digit-pattern cluster's existing convention for `0`/
negative input (`is_repdigit`, `is_palindrome_number`, `is_harshad`
all do the same) rather than the "negative can legitimately be true"
convention `is_perfect_cube`/`is_perfect_power` use — a Kaprekar split
has no meaningful negative case, the same reasoning `is_undulating`
(task 4 elsewhere in this file) already used for the same choice.

Acceptance criteria:
- `is_kaprekar(1);` is `true` — trivial split (`0 + 1 == 1`).
- `is_kaprekar(9);` is `true` (`81` → `8 + 1 == 9`).
- `is_kaprekar(45);` is `true` (`2025` → `20 + 25 == 45`).
- `is_kaprekar(55);` is `true` (`3025` → `30 + 25 == 55`).
- `is_kaprekar(99);` is `true` (`9801` → `98 + 01 == 99`).
- `is_kaprekar(297);` is `true` (`88209` → `88 + 209 == 297`).
- `is_kaprekar(703);` is `true` (`494209` → `494 + 209 == 703`).
- `is_kaprekar(999);` is `true` (`998001` → `998 + 001 == 999`).
- `is_kaprekar(2223);` is `true` (`4941729` → `494 + 1729 == 2223`).
- `is_kaprekar(0);` is `false` — below the `n >= 1` floor.
- `is_kaprekar(10);` is `false` — `100`'s only nontrivial split has a
  zero right part.
- `is_kaprekar(2);` is `false` (`4`, no split sums to `2`).
- `is_kaprekar(100);` is `false`.
- `is_kaprekar(-45);` is `false` — negative input, following the
  cluster's existing convention rather than raising.
- `is_kaprekar(5.0);` raises `CinderRuntimeError` matching
  `"is_kaprekar() requires an int, got float"`.
- `is_kaprekar(true);` raises `CinderRuntimeError` matching
  `"is_kaprekar() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_automorphic`, see
current line numbers — shift if task 5 lands first this cycle),
`tests/test_builtins.py` (model on `class TestIsAutomorphic` and `class
TestIsHarshad`, search either name). Once merged, `README.md`'s
Builtins bullet needs `is_kaprekar` added near `is_automorphic`/
`is_harshad`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 4. Language: map literal shorthand properties `{a, b}` as sugar for `{"a": a, "b": b}`

Build: the depth task after task 5's breadth work (`is_kaprekar`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that nested list-in-list destructuring patterns landed via PR
#273, dropping the count to the 5-task floor. Map-pattern *destructuring*
already has a shorthand — `let {a, b} = expr;` binds `a`/`b` by looking
up those keys — but *constructing* a map has no equivalent inverse: today
`{a, b}` (an existing local `a`/`b` you want keyed by their own names) is
always a `ParseError`, forcing the verbose `{"a": a, "b": b}` every time.
Verify the gap:
```sh
python3 -m cinder.cli eval 'let a = 1; let b = 2; print({a, b});'
# -> ParseError: expected ':' after map key, found ','
```
Confirm this exact program was already a guaranteed `ParseError` before
this task in both ways the parser could read it: at statement position
`{a, b};` fails the same way (map-literal attempt hits the same missing
colon; the block-statement fallback then also fails, since `a` isn't
followed by `;`), and inside a call/expression position like
`print({a, b})` there is no block-vs-map ambiguity to fall back to at
all — `{a, b}` there is unconditionally the map-literal attempt, and it
already raises the identical `"expected ':' after map key"` error. So no
currently-valid Cinder program's meaning changes.

**Important existing behavior to build on top of, not around**: an
ordinary map literal's key position is a full expression, evaluated at
runtime — `{a: 5}` with `let a = 1;` already produces `{1: 5}` (an
*integer* key `1`, `a`'s value, not the string `"a"`). Shorthand `{a}` is
therefore genuinely new sugar, not a restatement of existing behavior: it
uses the identifier's own *name* as a string key while still reading its
*value* for the map value — the same name-as-key/value-as-value split
`let {a, b} = expr;` already uses in the destructuring direction, just
inverted.

Add the shorthand branch to `_map_entry` in `cinder/parser.py` (the
`_map_pair`/`_map_comprehension`/`_map_literal` trio right after it are
unchanged):
```python
    def _map_entry(self):
        if self._check(TokenType.DOT_DOT_DOT):
            dots = self._advance()
            return Spread(self._ternary(), dots.line, dots.column)
        if self._check(TokenType.IDENTIFIER) and self._peek_next().type in (
            TokenType.COMMA,
            TokenType.RBRACE,
        ):
            name = self._advance()
            key = Literal(name.lexeme, name.line, name.column)
            value = Identifier(name.lexeme, name.line, name.column)
            return (key, value)
        return self._map_pair()
```
`Literal`/`Identifier` are both already imported in `cinder/parser.py`
(used throughout). This is the same "identifier immediately followed by
a specific lookahead token" technique `_call_argument` already uses to
recognize keyword arguments (`self._check(TokenType.IDENTIFIER) and
self._peek_next().type == TokenType.COLON`), just checking for
`COMMA`/`RBRACE` instead of `COLON` — and checking those specific two
tokens, not "anything but `:`", is what keeps this from misfiring: an
identifier followed by `for` (map comprehension source, `{a for a in
xs}`) or anything else falls straight through to the existing
`_map_pair()` path unchanged, so map comprehensions need no exclusion
logic of their own — the lookahead condition already keeps this scoped
to plain map literals only, for free. `_evaluate_map_literal`
(`cinder/interpreter.py`) needs no changes at all: it already evaluates
each pair's `key_expr`/`value_expr` generically, so a shorthand pair's
`Literal`/`Identifier` nodes are indistinguishable at runtime from any
other map entry.

Acceptance criteria:
- `let a = 1; let b = 2; print({a, b});` prints `{"a": 1, "b": 2}`.
- `let a = 1; print({a});` prints `{"a": 1}` — single shorthand entry.
- `let a = 1; print({a,});` prints `{"a": 1}` — shorthand plus trailing
  comma still works (existing trailing-comma handling is untouched).
- `let a = 1; print({a: 5});` still prints `{1: 5}` — an identifier
  immediately followed by `:` is completely unaffected, still an
  ordinary key expression (`a`'s *value*, not its name).
- `let a = 1; let b = 2; print({a, "c": 3, b});` prints
  `{"a": 1, "c": 3, "b": 2}` — shorthand and ordinary `key: value` pairs
  freely mix in one literal, in either order.
- `let a = 1; print({a, ...{"b": 2}});` prints `{"a": 1, "b": 2}` —
  shorthand composes with the existing spread entry.
- `let a = 1; print({["b" for b in [a]]: 1});` — not a real case, skip;
  instead confirm `[a for a in [1, 2]]` (list comprehension) still
  parses unaffected, and `{a for a in [1, 2]}`
  raises the same `ParseError` it already did (`"expected ':' after map
  key, found 'for'"` or equivalent) — map comprehensions are untouched,
  since `for` fails the `COMMA`/`RBRACE` lookahead.
- `print({});` still prints `{}` — empty map literal unaffected (no
  identifier to even reach the new branch).
- `{a, b};` — a shorthand map literal used as a bare statement — prints
  nothing but does not raise (same as any other map-literal-expression
  statement today, e.g. `{"a": 1};`).
- An undefined shorthand name raises the ordinary `"undefined name"`
  `CinderRuntimeError`, e.g. `{undefined_var};` — no special-cased error
  message, since the value side is an ordinary `Identifier` evaluation.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_map_entry`), `tests/test_parser.py`
(model on `class` containing `test_map_literal_with_spread`/
`test_map_literal`, search either name, plus add shorthand-vs-comprehension
and shorthand-vs-explicit-key regression cases near
`test_plain_map_literal_still_parses_after_comprehension_added`),
`tests/test_interpreter.py` (model on whatever covers
`test_map_literal_statement_unaffected`, search that name, for an
end-to-end `eval` case). Once merged, `README.md`'s map-literal
description needs a mention of the shorthand near the existing spread
entry (`{...m}`) description, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s roadmap paragraph needs this moved from
backlog to landed — leave all three to the Architect's next grooming
pass, not this task.

---

## 5. Standard library: `is_achilles` — powerful but not itself a perfect power

Build: the breadth task after task 5's depth work (map literal shorthand
properties) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `is_perfect_power` has landed via PR
#274, dropping the count to the 5-task floor. `is_powerful_number`
(`cinder/builtins.py`) tests whether every prime factor of an integer
appears with exponent `2` or more; `is_perfect_power` tests whether an
integer is `m ** k` for some base `m` and exponent `k >= 2`. Every
perfect power greater than 1 is powerful, but not every powerful number
is a perfect power — `72 = 2^3 * 3^2` is powerful (both exponents `>=
2`) yet no single base/exponent pair produces it (it is not a perfect
square, cube, or any higher power). Numbers in exactly this gap are
called Achilles numbers (OEIS A052486), and nothing in the existing
cluster tests it. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_achilles(72));'
# -> CinderRuntimeError: undefined name 'is_achilles'
```

Add to `cinder/builtins.py`, registered right after `_is_powerful_number`
(search `def _is_powerful_number`, immediately before `_integer_kth_root`):
```python
def _is_achilles(arguments: list, line: int, column: int) -> object:
    _require_arity("is_achilles", arguments, 1, line, column)
    value = _require_int("is_achilles", arguments[0], line, column)
    if value < 2:
        return False
    remaining = value
    divisor = 2
    exponent_gcd = 0
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            count = 0
            while remaining % divisor == 0:
                remaining //= divisor
                count += 1
            if count < 2:
                return False
            exponent_gcd = math.gcd(exponent_gcd, count)
        divisor += 1
    if remaining > 1:
        return False
    return exponent_gcd == 1
```
This is `_is_powerful_number`'s own factorization loop (same structure,
same `count < 2: return False` powerful-check) with one addition: the
running `math.gcd` of every prime's exponent. A number is a perfect
power exactly when the `gcd` of its prime-factorization exponents
exceeds `1` (it then equals that `gcd`-th power of the product of each
prime raised to `exponent / gcd`) — so `exponent_gcd == 1` after the
powerful check both confirms "not a perfect power" and naturally
excludes single-prime-factor powers like `8 = 2^3` for free, since a
lone prime's own exponent becomes the `gcd` outright (`math.gcd(0, 3) ==
3`, not `1`). No need to call `_is_perfect_power` as a separate second
pass — the same loop and the same intermediate state (each prime's
exponent) answer both questions at once, avoiding factoring `value`
twice. `math.gcd` is already imported in `cinder/builtins.py` (used
throughout the number-theory cluster, e.g. `gcd`/`lcm`). `value < 2`
returns `false` up front rather than raising, matching
`is_powerful_number`'s own convention for non-positive input (`0`, `1`,
and negatives all fail the "has any prime factorization" precondition
the same way).

Acceptance criteria:
- `is_achilles(72);` is `true` — `2^3 * 3^2`, `gcd(3, 2) == 1`.
- `is_achilles(108);` is `true` — `2^2 * 3^3`, `gcd(2, 3) == 1`.
- `is_achilles(200);` is `true` — `2^3 * 5^2`, `gcd(3, 2) == 1`.
- `is_achilles(500);` is `true` — `2^2 * 5^3`, `gcd(2, 3) == 1`.
- `is_achilles(8);` is `false` — `2^3`, a single prime factor, so
  `exponent_gcd == 3` (a perfect cube, not an Achilles number).
- `is_achilles(36);` is `false` — `2^2 * 3^2`, `gcd(2, 2) == 2` (a
  perfect square).
- `is_achilles(4);` is `false` — `2^2`, single prime factor, perfect
  square.
- `is_achilles(12);` is `false` — `2^2 * 3^1`, exponent `1` on `3` fails
  the powerful check.
- `is_achilles(1);` is `false` — below the `n >= 2` floor.
- `is_achilles(0);` is `false`.
- `is_achilles(-72);` is `false` — negative input, following
  `is_powerful_number`'s existing convention rather than raising.
- `is_achilles(30);` is `false` — squarefree, no exponent reaches `2` at
  all (fails on the very first prime factor).
- `is_achilles(5.0);` raises `CinderRuntimeError` matching
  `"is_achilles() requires an int, got float"`.
- `is_achilles(true);` raises `CinderRuntimeError` matching
  `"is_achilles() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_powerful_number`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on `class TestIsPowerfulNumber`
and `class TestIsPerfectPower`, search either name). Once merged,
`README.md`'s Builtins bullet needs `is_achilles` added near
`is_powerful_number`/`is_perfect_power`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s roadmap paragraph needs this moved
from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
