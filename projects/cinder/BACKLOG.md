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

## 1. Standard library: `cbrt` — real cube root, the domain-unrestricted sibling to `sqrt` [claimed 2026-08-18T19:17:41Z]

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

## 2. Language: nested list-in-list destructuring patterns

Build: the depth task after task 5's breadth work (`cbrt`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that list concatenation via `+` has landed via PR #267,
dropping the count to the 5-task floor. Every list-pattern position
(`let`, plain assignment, `for`, function params, both comprehension
loop-variable forms) currently requires each element to be a plain
identifier (optionally with a rename-free default, or a hole) — nothing
in a list pattern can itself be a nested pattern, so destructuring one
level into a list-of-lists still needs a manual second `let`:
```sh
python3 -m cinder.cli eval 'let [a, [b, c]] = [1, [2, 3]]; print(b);'
# -> ParseError: expected identifier in destructuring pattern, found '['
```
Two functions are shared by every list-pattern call site and are the
only things that need to change — everywhere else picks the fix up for
free, the same "shared helper" shape rest elements/defaults/holes
already exploited:

**Parsing** (`cinder/parser.py`): `_destructure_list_pattern_entry`
currently only accepts `TokenType.IDENTIFIER` (or a bare `COMMA` for a
hole) at the position where a pattern element starts. Add a third
branch, checked before the `IDENTIFIER` consume: if the next token is
`TokenType.LBRACKET`, recursively call `self._destructure_list_pattern()`
to parse a nested pattern (itself capable of nesting further, for free,
since it terminates in the same three cases), then apply the exact same
optional-`= default`/`seen_default` logic the identifier branch already
has, storing the entry's first tuple slot as the nested `(names, rest)`
pair instead of a `str`:
```python
    def _destructure_list_pattern_entry(self, seen_default: bool) -> tuple:
        if self._check(TokenType.COMMA):
            if seen_default:
                raise ParseError(...)  # unchanged
            return None, None
        if self._check(TokenType.LBRACKET):
            nested_names, nested_rest = self._destructure_list_pattern()
            pattern = (nested_names, nested_rest)
            if self._check(TokenType.EQ):
                self._advance()
                return pattern, self._ternary()
            if seen_default:
                raise ParseError(...)  # same message as the identifier branch
            return pattern, None
        name_token = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern")
        ...  # unchanged
```
`_destructure_assign_pattern` (the plain-assignment list form, `[a, b] =
expr;`, which validates an already-parsed `ListLiteral`'s elements
rather than parsing a pattern grammar directly) gets the matching
addition: alongside its existing `isinstance(element, Identifier)` and
`isinstance(element, Spread)` branches, add
`isinstance(element, ListLiteral)`, recursing into
`self._destructure_assign_pattern(element, eq_token)` to validate the
nested literal as a pattern too, and appending `((nested_names,
nested_rest), None)`. Unlike defaults/holes (which needed genuinely new
grammar — a bare `=` or an empty slot inside an ordinary list-literal
expression — and were deliberately left unsupported here for that
reason), a nested `[...]` is already valid, unambiguous `ListLiteral`
expression syntax, so this is a small, safe extension rather than a
"materially different, riskier parser change" the way those two were.

**Binding** (`cinder/interpreter.py`): `_bind_list_destructure`'s two
per-element loops both do `if name is not None:
self._bind_destructure_name(env, name, item, line, column, use_assign)`.
Add a branch ahead of that check: `if isinstance(name, tuple):` — the
nested-pattern case — recurse: `nested_names, nested_rest = name;
self._bind_list_destructure(env, nested_names, nested_rest, item, line,
column, use_assign)`, else fall through to the existing
`_bind_destructure_name` call unchanged. Both loops (the `rest is not
None` branch and the no-rest branch) need the same three-way
`None`/`tuple`/`str` check. No other function needs to change: the
length/arity error messages, default-evaluation, and rest-collection
logic in `_bind_list_destructure` are all unaffected by what a `name`
slot actually contains, and a non-list value reaching the recursive
call naturally raises the existing `"cannot destructure {type} as a
list"` error from the top of the recursive call, with no new check
needed.

Deliberately out of scope: nesting a *map* pattern inside a list
pattern (`let [a, {b, c}] = ...`) or a list pattern inside a *map*
pattern (`let {a: [b, c]} = ...`) — list-in-list only this task, the
same narrow-then-extend scoping the rest-element and default-value
families already used (list side first, map side as separate later
tasks). A `{` at a list-pattern element position keeps raising
`ParseError` exactly as it does today, not silently accepted.

Acceptance criteria:
- `let [a, [b, c]] = [1, [2, 3]]; print(a); print(b); print(c);` prints
  `1`, `2`, `3`.
- `let [[a, b], c] = [[1, 2], 3]; print(a); print(b); print(c);` prints
  `1`, `2`, `3` — nesting in the first position works the same as the
  last.
- `let [a, [b, [c, d]]] = [1, [2, [3, 4]]]; print(d);` prints `4` —
  arbitrary nesting depth, not just one level.
- `let [a, [b, ...brest]] = [1, [2, 3, 4]]; print(brest);` prints
  `[3, 4]` — a rest element inside a nested pattern.
- `let [a, [b, c] = [0, 0]] = [1]; print(b); print(c);` prints `0` then
  `0` — a default value on a nested-pattern slot, itself then
  destructured normally.
- `let [[a, , c]] = [[1, 2, 3]]; print(a); print(c);` prints `1` then
  `3` — a hole inside a nested pattern.
- `let [a, [b, c]] = [1, 2];` raises `CinderRuntimeError` matching
  `"cannot destructure int as a list"` — a non-list value at a nested
  position fails the same way a non-list top-level value already does.
- `[a, [b, c]] = [1, [2, 3]]; print(b);` prints `2` — the plain-assignment
  form (pre-declare `a`, `b`, `c` with `let` first).
- `for [a, [b, c]] in [[1, [2, 3]]] { print(b); }` prints `2`.
- `fn f([a, [b, c]]) { return b + c; } print(f([1, [2, 3]]));` prints `5`.
- `print([b for [a, [b, c]] in [[1, [2, 3]]]]);` prints `[2]`.
- `let [a, {b, c}] = [1, {"b": 2}];` still raises `ParseError` matching
  `"expected identifier in destructuring pattern, found '{'"` — map
  nesting inside a list pattern stays unsupported, not silently broken
  differently.
- Every pre-existing destructuring test (defaults, holes, rest elements,
  all five forms, both list and map patterns) continues to pass
  unmodified, without nesting.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_list_pattern_entry`,
`_destructure_assign_pattern`), `cinder/interpreter.py`
(`_bind_list_destructure`), `tests/test_parser.py` and
`tests/test_interpreter.py` (model on the existing hole-element and
rest-element destructuring test classes). Once merged, `README.md`'s
destructuring bullets need a sentence on nested list patterns, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 3. Standard library: `is_perfect_power` — the general closure of `is_perfect_square`/`is_perfect_cube`

Build: the breadth task after task 5's depth work (nested list-in-list
destructuring patterns), restocking the backlog back to 6 tasks now
that `harmonic_mean` has landed via PR #268, dropping the count to the
5-task floor. `is_perfect_square`/`is_perfect_cube`/`is_powerful_number`
each test a fixed or per-prime-factor exponent; nothing yet answers "is
there *any* integer exponent `k >= 2` and base `m` with `m ** k ==
n`" — the general perfect-power test both narrower predicates are
special cases of. Verify the gap: `python3 -m cinder.cli eval
'print(is_perfect_power(16));'` currently raises `CinderRuntimeError`
`"undefined name 'is_perfect_power'"` — no such builtin exists yet.

Add to `cinder/builtins.py`, registered right after `is_powerful_number`
(search `def _is_powerful_number`, immediately before `_divisors`):

```python
def _integer_kth_root(magnitude: int, k: int) -> int:
    if magnitude == 0:
        return 0
    low, high = 0, magnitude
    while low < high:
        mid = (low + high + 1) // 2
        if mid ** k <= magnitude:
            low = mid
        else:
            high = mid - 1
    return low


def _is_perfect_power(arguments: list, line: int, column: int) -> object:
    _require_arity("is_perfect_power", arguments, 1, line, column)
    value = _require_int("is_perfect_power", arguments[0], line, column)
    if abs(value) <= 1:
        return True
    magnitude = abs(value)
    for k in range(2, magnitude.bit_length() + 1):
        root = _integer_kth_root(magnitude, k)
        if root ** k == magnitude:
            if value > 0:
                return True
            if k % 2 == 1:
                return True
    return False
```

`_integer_kth_root` is a new, general sibling of the existing
`_integer_cube_root` helper (same binary-search shape, generalized from
a fixed `** 3` to a parameter `k`) — leave `_integer_cube_root` and
`_is_perfect_cube` themselves untouched, this task adds a new helper
rather than refactoring the existing one, keeping the diff additive
only. `0` and `±1` are handled as a trivial base case up front (`0 =
0 ** 2`, `1 = 1 ** 2`, `-1 = (-1) ** 3`) since the bit-length-driven `k`
loop below would otherwise produce an empty range for both. For
`magnitude >= 2`, `magnitude.bit_length()` is a safe inclusive upper
bound on `k` to search (`2 ** magnitude.bit_length() > magnitude`
always, so no smaller base than `1` can still satisfy `root ** k ==
magnitude` past that point). A negative `value` can only be produced by
an *odd* `k` (an even power of any integer is non-negative), so the
even-`k` branch is silently skipped rather than returning early —
mirroring how `is_perfect_cube` already accepts negative input
(`-8`) while `is_perfect_square` does not, generalized to "only the
`k`s where a negative result is possible."

Acceptance criteria:
- `is_perfect_power(0);` is `true` — `0 = 0 ** 2`.
- `is_perfect_power(1);` is `true` — `1 = 1 ** 2`.
- `is_perfect_power(-1);` is `true` — `-1 = (-1) ** 3`.
- `is_perfect_power(4);` is `true` (`2 ** 2`).
- `is_perfect_power(8);` is `true` (`2 ** 3`).
- `is_perfect_power(9);` is `true` (`3 ** 2`).
- `is_perfect_power(16);` is `true` (`2 ** 4`, also `4 ** 2`).
- `is_perfect_power(64);` is `true` (`2 ** 6`, `4 ** 3`, `8 ** 2`).
- `is_perfect_power(-8);` is `true` (`(-2) ** 3`).
- `is_perfect_power(-27);` is `true` (`(-3) ** 3`).
- `is_perfect_power(-4);` is `false` — `4` is only reachable via an
  even exponent (`2 ** 2`), which can never produce a negative result.
- `is_perfect_power(-9);` is `false` — same reasoning as `-4`.
- `is_perfect_power(2);` is `false`.
- `is_perfect_power(6);` is `false`.
- `is_perfect_power(17);` is `false`.
- `is_perfect_power(-100);` is `false`.
- `is_perfect_power(5.0);` raises `CinderRuntimeError` matching
  `"is_perfect_power() requires an int, got float"`.
- `is_perfect_power(true);` raises `CinderRuntimeError` matching
  `"is_perfect_power() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_powerful_number`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on `class TestIsPerfectCube` and
`class TestIsPowerfulNumber`, search either name). Once merged,
`README.md`'s Builtins bullet needs `is_perfect_power` added near
`is_powerful_number`/`is_perfect_cube`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s roadmap paragraph needs this moved
from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## 4. Language: raw string literals `r"..."`/`r'...'` — the escape/interpolation-free sibling to ordinary strings

Build: the depth task after task 5's breadth work (`is_perfect_power`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that trailing commas in destructuring patterns has
landed via PR #269, dropping the count to the 5-task floor. Every
string literal today (`cinder/lexer.py`'s `_string`) processes
backslash escapes (`\n`, `\t`, `\\`, `\"`, `\'`) and `${...}`
interpolation, with no way to write a string whose backslashes and
`${` sequences are taken completely literally — exactly the gap a
`r"..."`/`r'...'` raw-string prefix closes in most mainstream
scripting languages, useful for regex-like patterns and Windows-style
paths (`r"C:\Users\name"`) without doubling every backslash. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(r"a\nb");'
# -> ParseError: expected ')' after arguments, found '"a\\nb"'
```
This happens because `Lexer.tokenize()`'s dispatch (search
`char.isalpha() or char == "_"`) sends a leading `r` straight into
`_identifier`, producing an `IDENTIFIER` token `r` immediately followed
by an ordinary `STRING` token — two adjacent tokens with nothing
between them, which the parser then chokes on as if `r` were a
function-call callee, the same failure shape any other
`identifier"string"` juxtaposition already produces today (not a bug
specific to `r`).

**Lexing**: add a new dispatch branch in `Lexer.tokenize()`, checked
*before* the existing `char.isalpha()` branch, that recognizes the raw
string prefix specifically — `char == "r"` immediately followed by `"`
or `'` with no separating whitespace (`self._peek()` is a quote right
after consuming `r`):
```python
            if char == '"' or char == "'":
                self._string(start_line, start_col, quote=char)
            elif char == "r" and self._peek() in ('"', "'"):
                quote = self._advance()
                self._raw_string(start_line, start_col, quote=quote)
            elif char.isdigit():
```
This ordering is safe for ordinary identifiers: `r` can only reach this
branch when the *very next* character is a quote, which is exactly the
case where `r` standing alone as an identifier would already be a
syntax error today (an identifier immediately followed by a string
literal, no operator between them) — so no currently-valid program
changes meaning. An identifier that merely starts with `r`
(`read`, `result`, `r2`) never matches, since its second character
isn't a quote, and a bare variable named `r` (`let r = 5; print(r);`)
is untouched, since nothing there is followed by a quote either.

Add `_raw_string`, a sibling to the existing `_string` (`cinder/lexer.py`,
right after `_string`), reusing the same unterminated-string error and
line/column tracking but with the escape and interpolation handling
stripped out — every character up to the matching close quote is taken
literally, including backslashes and `${`:
```python
    def _raw_string(self, start_line: int, start_col: int, quote: str):
        start_pos = self.pos - 2  # position of the 'r' prefix
        chars = []
        while True:
            if self._at_end():
                raise LexError(
                    "unterminated string", start_line, start_col, unterminated=True
                )
            if self._peek() == quote:
                self._advance()
                break
            chars.append(self._advance())
        lexeme = self.source[start_pos : self.pos]
        self.tokens.append(
            Token(TokenType.STRING, lexeme, "".join(chars), start_line, start_col)
        )
```
Emits the same `TokenType.STRING` ordinary strings use (not a new
token type or a new interpreter-level value kind) since a raw string
is still just a string value once lexed — only how its *source text*
maps to that value differs, mirroring how hex/binary/octal integer
literals (`0x1F`/`0b101`/`0o17`) all still produce a plain `int`, not a
distinct value kind. There is no escape mechanism inside a raw string,
so (like Python's own raw strings) a raw string cannot contain its own
delimiter quote at all — `r"say \"hi\""` is not expressible; the other
quote character can always be used instead (`r'say "hi"'`), which is
an accepted, documented limitation, not a bug to work around this task.

Acceptance criteria:
- `print(r"a\nb");` prints `a\nb` literally — four characters
  (backslash, `n`, not a newline), confirming escapes are not
  processed.
- `print(r'C:\Users\name');` prints `C:\Users\name` literally, single-quoted
  form works the same as double-quoted.
- `print(r"${1 + 2}");` prints `${1 + 2}` literally, confirming
  interpolation is not processed.
- `print(r"");` prints an empty string.
- `let r = 5; print(r + 1);` prints `6` — a bare identifier named `r`
  not immediately followed by a quote is unaffected.
- `print(type(r"abc"));` is `"string"` — same runtime type as an
  ordinary string literal.
- `r"unterminated` (no closing quote) raises `LexError` matching
  `"unterminated string"`, same as an ordinary unterminated string.
- `print("a\nb");` (no `r` prefix) still prints `a`, newline, `b` —
  ordinary string escape processing is completely unaffected.
- Full test suite passes.

Likely files: `cinder/lexer.py` (`tokenize()`'s dispatch, new
`_raw_string` method next to `_string`), `tests/test_lexer.py` (model on
whatever test class covers `class TestStrings`/ordinary string escapes,
search for `_string`/`unterminated string`), possibly
`tests/test_interpreter.py` for one end-to-end `eval` case. Once
merged, `README.md`'s Values bullet needs a mention of raw string
literals near the existing string-escapes/interpolation sentence, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave all three to
the Architect's next grooming pass, not this task.

---

## 5. Standard library: `is_undulating` — digit-alternation classification

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
