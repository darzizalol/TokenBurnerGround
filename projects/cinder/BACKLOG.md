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

## 1. Language: single-quoted string literals (`'...'` as an alternate delimiter) [claimed 2026-08-16T15:00:34Z]

Build: the depth task after task 5's breadth work (`is_powerful_number`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that optional catch binding has landed via PR #253,
dropping the count to the 5-task floor. Today `cinder/lexer.py`'s
`_string` method only recognizes `"` as a string delimiter — `char ==
'"'` is the sole dispatch in `tokenize`, so a string literal can never
contain a literal `"` without escaping it (`"she said \"hi\""`), even
though the far more common case in real code is a string that quotes
something (contractions, quoted dialogue, shell-ish snippets). Verify
the gap: `python3 -m cinder.cli eval "print('hi');"` currently raises
`LexError` `"unrecognized character \"'\""` — there is no handling for
`'` at all today, it isn't even a partially-supported delimiter.

**Lexing** (`cinder/lexer.py`): make `_string` delimiter-aware instead
of hardcoding `"` twice (as the terminator check and in the opening
dispatch). Change its signature to take the opening quote character,
and use that everywhere `'"'` currently appears inside the method body:

```python
def _string(self, start_line: int, start_col: int, quote: str):
    start_pos = self.pos - 1  # position of the opening quote
    ...
    while True:
        ...
        if self._peek() == quote:
            self._advance()
            break
        ...
```

In `tokenize`, dispatch both quote characters to it:

```python
if char == '"' or char == "'":
    self._string(start_line, start_col, quote=char)
```

Add `'` to `_ESCAPES` alongside the existing `'"'` entry (`_ESCAPES =
{"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}`) so `\'` is a
valid escape inside *either* delimiter, not just inside single-quoted
strings — mirroring how `\"` already works inside both today (it's
just a redundant-but-harmless escape inside a single-quoted string).
This is the only change to `_ESCAPES`; `\n`/`\t`/`\\` stay exactly as
they are, and both delimiters keep sharing the identical escape table
rather than each getting its own.

Everything else about `_string` — the `$` `${...}` interpolation
handling, the `has_interp` / `INTERP_STRING` vs `STRING` token split,
`_interp_placeholder`, unterminated-string detection — is delimiter-
agnostic already and needs no changes; a single-quoted string
interpolates exactly like a double-quoted one. No parser or
interpreter changes at all: both delimiters produce the same
`STRING`/`INTERP_STRING` tokens carrying the same parsed Python `str`
value, so everything downstream (string methods, `+`/`*`, comparisons,
`print`/`format`) is already delimiter-blind by construction.

Acceptance criteria:
- `print('hello');` prints `hello` — single-quoted strings work as a
  plain literal.
- `print('she said "hi"');` prints `she said "hi"` — a single-quoted
  string may contain an unescaped double quote.
- `print("it's fine");` prints `it's fine` — unchanged: a double-quoted
  string may already contain an unescaped single quote (this criterion
  just confirms the new dispatch didn't regress it).
- `print('it\'s fine');` prints `it's fine` — `\'` is a valid escape
  inside a single-quoted string.
- `print("say \"hi\"");` still prints `say "hi"` — `\"` inside a
  double-quoted string is unchanged.
- `print('a\nb');` prints two lines, `a` then `b` — the existing escape
  table (`\n`/`\t`/`\\`) works identically inside single quotes.
- `let name = "world"; print('hello, ${name}!');` prints `hello,
  world!` — `${...}` interpolation works inside single-quoted strings,
  identically to double-quoted ones.
- `print('unterminated);` (no closing `'`) raises `LexError` matching
  `"unterminated string"` — same error shape the double-quoted form
  already raises for a missing closing `"`.
- `print('bad \z escape');` raises `LexError` matching `"invalid escape
  sequence '\\z'"` — same error shape as the double-quoted form for an
  unrecognized escape.
- `print("plain double-quoted still works");` prints unchanged —
  confirms the double-quoted path is untouched by the refactor.
- Full test suite passes.

Likely files: `cinder/lexer.py` (`_string`, `tokenize`'s dispatch,
`_ESCAPES`), `tests/test_lexer.py` (new single-quote tests alongside
`test_string_basic`/`test_string_escapes`, search `class TestStrings`
— mirror each existing double-quoted case with a single-quoted one),
`tests/test_interpreter.py` or `tests/test_lexer.py`'s
`TestStringInterpolation` class (a single-quoted interpolation case).
Once merged, `README.md`'s Values bullet needs a mention that strings
may be single- or double-quoted added near the existing interpolation
description, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 2. Standard library: `is_repdigit` — every decimal digit is the same

Build: the breadth task after task 5's depth work (single-quoted string
literals) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `is_amicable` has landed via PR #254,
dropping the count to the 5-task floor. Add `is_repdigit(n)` to
`cinder/builtins.py`, registered right after `is_palindrome_number`
(search for `def _is_palindrome_number`, immediately before
`is_perfect_square`) — a positive integer is a repdigit when every one
of its decimal digits is the same character (`11`, `222`, `4444`), a
digit-transform predicate joining `is_palindrome_number`/`is_armstrong`/
`is_harshad`/`is_strong_number` rather than a fourth
prime-factorization-flavored predicate: the recently-landed
`is_semiprime` and this backlog's `is_powerful_number` (task 2) already
sit back-to-back in the same trial-division style, so this task
deliberately varies the sub-theme within the breadth slot instead of
extending that run further.
Verify the gap: `python3 -m cinder.cli eval 'print(is_repdigit(222));'`
currently raises `CinderRuntimeError` `"undefined name 'is_repdigit'"` —
no such builtin exists yet.

```python
def _is_repdigit(arguments: list, line: int, column: int) -> object:
    _require_arity("is_repdigit", arguments, 1, line, column)
    value = _require_int("is_repdigit", arguments[0], line, column)
    if value < 0:
        return False
    return len(set(str(value))) == 1
```

Model the arity/type-checking exactly on `is_palindrome_number`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). Negative
inputs return `false` rather than raising, matching the
boolean-predicate cluster's own convention (`is_palindrome_number`,
`is_armstrong`, `is_strong_number`, etc. — *not* the divisor cluster's
type-vs-domain-error convention, since this builtin returns a boolean,
not a number). A single-digit integer, including `0`, is trivially a
repdigit — `str(value)` is one character long, so `set(...)` has exactly
one element — the same "trivially true for the degenerate one-element
case" convention `is_palindrome_number` already establishes (a
one-character string trivially reads the same forwards and backwards).
No trial division or `sqrt` bound is needed here, unlike
`is_semiprime`/`is_powerful_number` — this is a pure string/set check on
the decimal representation, closer in shape to
`is_palindrome_number`/`is_armstrong` than to the prime-factorization
cluster.

Acceptance criteria:
- `is_repdigit(0);` is `true` — single digit, trivially repdigit.
- `is_repdigit(5);` is `true` — single digit.
- `is_repdigit(11);` is `true`.
- `is_repdigit(222);` is `true`.
- `is_repdigit(4444);` is `true`.
- `is_repdigit(99999);` is `true` — five-digit repdigit.
- `is_repdigit(10);` is `false` — two distinct digits.
- `is_repdigit(121);` is `false` — palindrome, but not every digit is
  the same, exercises the distinction from `is_palindrome_number`.
- `is_repdigit(1000);` is `false` — one `1` and three `0`s.
- `is_repdigit(-11);` is `false` — negative input, same convention as
  `is_palindrome_number`.
- `is_repdigit(5.0);` raises `CinderRuntimeError` matching
  `"is_repdigit() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `is_repdigit(true);` raises `CinderRuntimeError` matching
  `"is_repdigit() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_palindrome_number`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestIsPalindromeNumber`
test class, search for `class TestIsPalindromeNumber`). Once merged,
`README.md`'s Builtins bullet needs `is_repdigit` added near
`is_palindrome_number`/`is_armstrong`, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Language: scientific notation for float literals (`1e3`, `1.5e-2`, `2E+10`)

Build: the depth task after task 5's breadth work (`is_repdigit`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that the pipe operator has landed via PR #255, dropping
the count to the 5-task floor. Today `cinder/lexer.py`'s `_number`
only recognizes plain digits and an optional `.`-led fractional part —
there is no handling of an `e`/`E` exponent suffix at all. Verify the
gap: `python3 -m cinder.cli eval 'print(1e3);'` currently raises
`ParseError` `"expected ')' after arguments, found 'e3'"` — the lexer
never attempts to recognize the exponent as part of the number, so
`1e3` lexes as an `INT` token `1` immediately followed by a separate
`IDENTIFIER` token `e3`, which then breaks `print`'s call-argument
parsing.

**Lexing** (`cinder/lexer.py`): in `_number`, after the existing
optional fractional-part block (`if self._peek() == "." and
self._peek_next().isdigit(): ...`), add an optional exponent-suffix
block:

```python
        if self._peek().lower() == "e" and (
            self._peek_next().isdigit() or self._peek_next() in "+-"
        ):
            is_float = True
            digits.append(self._advance())  # consume 'e'/'E'
            if self._peek() in "+-":
                digits.append(self._advance())  # consume sign
            exponent_start = len(digits)
            while self._peek().isdigit() or (
                self._peek() == "_"
                and digits[-1].isdigit()
                and self._peek_next().isdigit()
            ):
                digits.append(self._advance())
            if len(digits) == exponent_start:
                raise LexError(
                    "expected digits after exponent", start_line, start_col
                )
```

Only begin consuming when `e`/`E` is followed by a digit or a `+`/`-`
sign — this avoids misreading a bare trailing `e` (an identifier
glued onto a number with no space, however unlikely) as the start of
an exponent it can never complete. Once committed, the digit run
reuses the exact same underscore-separator condition the integer and
fractional digit runs already use above it in the same method, and an
empty run raises `LexError` with the message `"expected digits after
exponent"` — the same "commit to a suffix, then require what must
follow it" shape `_prefixed_int` already uses for its own `"expected
digits after '0{prefix}'"` error.

An exponent always forces `is_float = True`, even with no `.` present
— `1e3` is the float `1000.0`, matching Python/JS convention, not the
int `1000`. No other change is needed: the existing `value_str =
"".join(c for c in digits if c != "_")` then `float(value_str)`
construction at the bottom of `_number` already handles it, since
Python's own `float()` parses the full `1e3`/`1.5e-2`/`2e+10` exponent
grammar once underscores are stripped — this is the same reason the
existing underscore-stripping already works for the plain
integer/fractional digit runs. No parser or interpreter changes at
all: the result is still an ordinary `FLOAT` token carrying a plain
Python `float`, indistinguishable downstream from one written with a
decimal point.

Acceptance criteria:
- `print(1e3);` prints `1000.0` — a bare integer mantissa with an
  exponent still produces a float.
- `print(1.5e2);` prints `150.0`.
- `print(1.5e-2);` prints `0.015` — a negative exponent.
- `print(2E+3);` prints `2000.0` — uppercase `E` and an explicit `+`
  sign both work.
- `print(1_000e3);` prints `1000000.0` — underscore separators in the
  mantissa keep working alongside an exponent.
- `print(1e1_0);` prints `10000000000.0` — underscore separators also
  work within the exponent digits themselves.
- `print(0e0);` prints `0.0`.
- `tokenize("1e3")` (in a lexer-level test) produces a single `FLOAT`
  token with `literal == 1000.0` and `lexeme == "1e3"`, not an `INT`
  followed by an `IDENTIFIER`.
- `print(1.foo);` (a `.` NOT followed by a digit) still lexes as
  `INT`, `DOT`, `IDENTIFIER` — confirms this task didn't touch the
  pre-existing fractional-part gating, only added a new block after
  it.
- `1e;` (an `e` with nothing usable after it — not a digit, not
  `+`/`-`) lexes as `INT` `1` followed by a separate `IDENTIFIER` `e`,
  same as today — confirms the lookahead gate correctly declines to
  commit when there's no plausible exponent to consume.
- `1e+;` (committed via the `+` sign, but no digit follows) raises
  `LexError` matching `"expected digits after exponent"`.
- `1e+x;` raises the same `LexError` — confirms the error fires even
  when a non-digit token character follows the sign, not just at
  end-of-input.
- Every pre-existing integer/float/hex/binary/octal lexer test
  continues to pass unmodified.
- Full test suite passes.

Likely files: `cinder/lexer.py` (`_number`), `tests/test_lexer.py`
(new tests alongside `test_float`/`test_float_with_underscore_separators`,
search `class TestLiterals`). Once merged, `README.md`'s Values bullet
needs a mention that float literals accept scientific notation added
near the existing underscore-separator mention, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `geometric_mean` — the nth root of a list's product

Build: the breadth task after task 5's depth work (scientific notation
for float literals) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_semiprime` has
landed via PR #256, dropping the count to the 5-task floor. Add
`geometric_mean(list)` to `cinder/builtins.py`, registered right after
`_mean` (search for `def _mean`, immediately before `_median`) — the
statistics cluster (`mean`, `median`, `variance`, `std_dev`, `mode`)
has never grown a second kind of "average" alongside the arithmetic
one already in `mean`; the geometric mean is that natural second
member: the nth root of the product of `n` numbers, rather than their
sum divided by `n`. Verify the gap: `python3 -m cinder.cli eval
'print(geometric_mean([4, 9]));'` currently raises
`CinderRuntimeError` `"undefined name 'geometric_mean'"` — no such
builtin exists yet.

```python
def _geometric_mean(arguments: list, line: int, column: int) -> object:
    _require_arity("geometric_mean", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"geometric_mean() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("geometric_mean() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"geometric_mean() requires a list of numbers, got {type_name(element)}", line, column
            )
        if element <= 0:
            raise CinderRuntimeError(
                "geometric_mean() requires all elements to be positive", line, column
            )
    product = 1
    for element in value:
        product = product * element
    return product ** (1 / len(value))
```

Model the arity/type-checking exactly on `mean`/`median`/`variance`'s
own structure: `_require_arity`, then the same `isinstance(value,
list)` / non-empty / `_is_numeric`-per-element checks that whole
cluster already shares (reusing the shared `_is_numeric` helper — do
**not** hand-roll a separate `isinstance` check). Unlike the rest of
that cluster, this builtin adds one more requirement on top: every
element must be strictly positive, checked only *after* confirming the
element is numeric (so a non-numeric element always reports the
"requires a list of numbers" error, never the positivity one) — a
geometric mean over zero or negative inputs either divides by zero or
requires complex arithmetic to stay mathematically defined, and
Cinder's numeric tower has no complex type, so this domain restriction
is the same "raise a domain error rather than leak a nonsensical or
`nan` result" convention `log()` already applies to its own
positive-input requirement. A single-element list is trivially its own
geometric mean, matching `mean`/`median`'s own single-element
convention.

Acceptance criteria:
- `geometric_mean([4, 9]);` is `6.0` — `sqrt(36)`.
- `geometric_mean([2, 8]);` is `4.0` — `sqrt(16)`.
- `geometric_mean([3, 27]);` is `9.0` — `sqrt(81)`.
- `geometric_mean([5, 5]);` is `5.0` — equal elements collapse to
  themselves.
- `geometric_mean([7]);` is `7.0` — a single-element list is trivially
  its own geometric mean, same convention as `mean`/`median`.
- `geometric_mean([]);` raises `CinderRuntimeError` matching
  `"geometric_mean() requires a non-empty list"`.
- `geometric_mean([1, 0]);` raises `CinderRuntimeError` matching
  `"geometric_mean() requires all elements to be positive"` — zero is
  not allowed.
- `geometric_mean([4, -9]);` raises the same positivity
  `CinderRuntimeError` — a negative element is not allowed even though
  this particular pair's product happens to be positive.
- `geometric_mean([1, "a"]);` raises `CinderRuntimeError` matching
  `"geometric_mean() requires a list of numbers, got string"` — a
  non-numeric element is reported before the positivity check ever
  runs on it.
- `geometric_mean("abc");` raises `CinderRuntimeError` matching
  `"geometric_mean() requires a list, got string"` — wrong argument
  type entirely, not just a bad element.
- `geometric_mean(true);` raises the same not-a-list
  `CinderRuntimeError`, `"got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `mean`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py` (model on the `TestMean`/`TestMedian` test
classes, search `class TestMean`). Once merged, `README.md`'s Builtins
bullet needs `geometric_mean` added near `mean`/`median`/`variance`/
`std_dev`/`mode`, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## 5. Language: postfix `++`/`--` as a first-class assignment expression, not statement-only sugar

Build: the depth task after task 5's breadth work (`geometric_mean`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that uninitialized `let` declarations landed via PR #257,
dropping the count to the 5-task floor. `cinder/parser.py`'s own module
docstring (search for "statement-only sugar", right above
`_assignment`) spells out today's deliberate restriction: `x++`/`x--`
are recognized only by a one-off helper, `_expr_or_incdec`, called from
exactly three places — `_expr_statement` (a bare `x++;` statement) and
the C-style `for` loop's init/step clauses — rather than from
`_assignment` itself, "so they're unreachable from any expression
context." That restriction has become an inconsistency, not a
deliberate language design choice: every *other* assignment-flavored
operator (`=`, `+=`, `-=`, `*=`, `/=`, `%=`, `**=`, `//=`, `&=`, `|=`,
`^=`, `<<=`, `>>=`, `??=`) already *is* reachable as a `let` initializer,
as the RHS of a chained assignment, and inside a parenthesized
sub-expression, because `_assignment` itself recognizes them. `++`/`--`
are the one assignment-flavored form still walled off from all of that.
Verify the gap — every one of these already works today with `+=` in
place of `++`, but fails with `++`:
```sh
python3 -m cinder.cli eval 'let x = 1; let y = x++; print(y);'
# -> ParseError: expected ';' after variable declaration, found '++'
python3 -m cinder.cli eval 'let x = 1; let y = 0; y = x++; print(y);'
# -> ParseError: expected ';' after expression, found '++'
python3 -m cinder.cli eval 'let x = 1; let y = (x++); print(y);'
# -> ParseError: expected ')' after expression, found '++'
python3 -m cinder.cli eval 'let x = 1; let y = x += 1; print(y);'
# -> prints 2, no error — the exact sibling form this task brings ++/-- up to parity with
```

**Parsing** (`cinder/parser.py`): fold `_expr_or_incdec`'s body directly
into `_assignment`, as one more `if` branch alongside the existing
`EQ`/`QQEQ`/`_COMPOUND_ASSIGN_OPS` checks (order among these four
branches doesn't matter — they dispatch on disjoint token types):

```python
    def _assignment(self) -> Expr:
        expr = self._ternary()
        if self._check(TokenType.EQ):
            ...  # unchanged
        if self._check(TokenType.QQEQ):
            ...  # unchanged
        if self._peek().type in _COMPOUND_ASSIGN_OPS:
            ...  # unchanged
        if self._peek().type in _INCREMENT_DECREMENT_OPS:
            op_token = self._advance()
            binary_operator = Token(
                _INCREMENT_DECREMENT_OPS[op_token.type],
                op_token.lexeme[0],
                None,
                op_token.line,
                op_token.column,
            )
            one = Literal(1, op_token.line, op_token.column)
            if isinstance(expr, Identifier):
                return Assign(
                    expr.name,
                    Binary(expr, binary_operator, one),
                    op_token.line,
                    op_token.column,
                )
            if isinstance(expr, Index):
                return IndexCompoundAssign(
                    expr.obj, expr.index, binary_operator, one,
                    op_token.line, op_token.column,
                )
            raise ParseError(
                "invalid assignment target", op_token.line, op_token.column
            )
        return expr
```

This is a straight relocation of the existing body of
`_expr_or_incdec` (currently at the bottom of the file, right above
`_assignment`) — same `Identifier`/`Index` target check, same
`Assign`/`IndexCompoundAssign` desugaring, same "invalid assignment
target" error for anything else (a literal, a call result, a
parenthesized expression, etc. — unchanged, still a `ParseError`).
Once folded in, `_expr_or_incdec` has no remaining callers needing its
own name — delete it, and change its three call sites
(`_expr_statement`, and the `for`-loop init/step clauses in
`_for_c_statement`) to call `self._assignment()` directly instead,
exactly as every other statement-position expression already does.
**No interpreter changes at all**: this task changes only where the
parser is *willing to look* for `++`/`--`, not what AST node it builds
or how that node evaluates — `Assign`/`IndexCompoundAssign` already
evaluate to the new (post-increment) value, the same as every sibling
compound-assign operator already does (confirmed above: `y = x += 1;`
already prints `2`, not `1`), so `x++` used as an expression yields the
incremented value too, not a C-style pre-increment snapshot of the old
one — the natural, zero-extra-code consequence of reusing the exact
same desugaring, not a new design decision this task has to invent.

Out of scope, deliberately: this task does **not** change *precedence*
— `++`/`--` are still recognized at the same (loosest, assignment-level)
point in the grammar as today, just from more call sites. `-x++;`
already raises `"invalid assignment target"` today (`_unary` parses
`-x` into a single `Unary` node before `_expr_or_incdec` ever sees a
trailing `++`, and `Unary` isn't an `Identifier`/`Index`) and must keep
doing so — making postfix `++`/`--` bind tighter than unary prefix
operators (C's actual precedence) is a separate, riskier parser change
this task does not take on. Likewise, `++`/`--` still must not become
reachable from call arguments, index expressions, ternary branches, or
any other `_ternary()`-rooted position — none of the *other*
assignment operators are reachable there either (`print(x = 5)` is
`ParseError` today and must stay that way), so extending only `++`/`--`
into those positions would be a new inconsistency in the opposite
direction, not a fix for this one.

Also update the `cinder/parser.py` module docstring paragraph
(currently: `"x++"/"x--" are statement-only sugar for "x += 1"/"x -=
1" (not an expression form: "let b = a++;" is unparseable), handled in
"_expr_statement" rather than "_assignment" so they're unreachable
from any expression context.'`) to describe the new, corrected
behavior instead of the restriction this task removes; the two
sentences right after it about the lexer's doubled-`-`/doubled-`+`
prefix re-split (`--5`, `++5`) are unaffected and stay as-is.

Acceptance criteria:
- `let x = 1; let y = x++; print(x); print(y);` prints `2` then `2` —
  `x++` works as a `let` initializer, and yields the new value.
- `let x = 1; let y = 0; y = x++; print(x); print(y);` prints `2` then
  `2` — `x++` works as the RHS of a chained assignment.
- `let x = 1; let y = (x++); print(y);` prints `2` — works inside a
  parenthesized sub-expression.
- `let x = 5; let y = x--; print(x); print(y);` prints `4` then `4` —
  `--` gets the same treatment as `++`.
- `let xs = [1]; let y = xs[0]++; print(xs[0]); print(y);` prints `2`
  then `2` — an `Index` target works the same new-value way, via
  `IndexCompoundAssign`.
- `let x = 1; x++; print(x);` still prints `2` — the existing bare-
  statement form is unaffected.
- `for (let i = 0; i < 3; i++) { print(i); }` still prints `0`, `1`,
  `2` — the existing for-loop step-clause form is unaffected.
- `for (let i = 0; i < 3; i = i + 1) { }` (an ordinary assignment step,
  no `++`) still works unchanged — confirms the `_for_c_statement`
  call-site swap to `_assignment()` didn't regress the non-incdec path.
- `5++;` still raises `ParseError` matching `"invalid assignment
  target"` — an invalid target is still rejected, from every call site,
  not just the original one.
- `-x++;` still raises the same `"invalid assignment target"` error —
  confirms this task deliberately left precedence unchanged.
- `print(x++);` still raises `ParseError` (still unreachable from a
  call argument) — confirms `++`/`--` stayed at assignment-expression
  reachability, matching `=`/`+=`'s own existing `print(x = 5)`
  restriction, not creeping further into `_ternary()`-rooted positions.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_assignment`, delete
`_expr_or_incdec`, `_expr_statement`, `_for_c_statement`, the module
docstring), `tests/test_parser.py` and/or `tests/test_interpreter.py`
(wherever the existing statement-form `x++`/for-loop tests live —
search `INCREMENT_DECREMENT` or `x++`  — add the new expression-position
cases alongside them, plus the unchanged-precedence/unchanged-
reachability regression cases). Once merged, `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave that to the
Architect's next grooming pass, not this task.

---

## 6. Standard library: `digit_product` — the multiplicative counterpart to `digit_sum`

Build: the breadth task after task 5's depth work (postfix `++`/`--`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that `is_powerful_number` has landed via PR #258,
dropping the count to the 5-task floor. Add `digit_product(n)` to
`cinder/builtins.py`, registered right after `digit_sum` (search for
`def _digit_sum`, immediately before `_reverse_int`) — `digit_sum`
sums an integer's decimal digits; `digit_product` is its natural
multiplicative sibling, the same relationship `product` already has to
`sum` at the list level. Verify the gap: `python3 -m cinder.cli eval
'print(digit_product(23));'` currently raises `CinderRuntimeError`
`"undefined name 'digit_product'"` — no such builtin exists yet.

```python
def _digit_product(arguments: list, line: int, column: int) -> object:
    _require_arity("digit_product", arguments, 1, line, column)
    value = _require_int("digit_product", arguments[0], line, column)
    product = 1
    for digit in str(abs(value)):
        product *= int(digit)
    return product
```

Model the arity/type-checking exactly on `digit_sum`'s own structure:
`_require_arity`, then `_require_int` (reusing the shared helper — do
**not** hand-roll a separate `isinstance` check), then `abs(value)` to
normalize away the sign before walking digits, mirroring how
`digit_sum` already discards the sign via the same `str(abs(value))`
call rather than raising on negative input or letting a leading `-`
character corrupt the digit walk. A single-digit integer, including
`0`, is trivially its own digit product — the loop runs once and
returns that digit — the same trivial-degenerate-case convention
`digit_sum`/`is_palindrome_number` already establish. Any digit `0`
anywhere in the number collapses the whole product to `0`, which is
the correct mathematical answer, not a special case to guard against.

Acceptance criteria:
- `digit_product(0);` is `0` — single digit, trivially itself.
- `digit_product(5);` is `5` — single digit.
- `digit_product(23);` is `6` — `2 * 3`.
- `digit_product(123);` is `6` — `1 * 2 * 3`.
- `digit_product(999);` is `729` — `9 * 9 * 9`.
- `digit_product(10);` is `0` — a `0` digit collapses the product.
- `digit_product(-23);` is `6` — sign is discarded first, same
  convention as `digit_sum(-23)` returning `5`.
- `digit_product(5.0);` raises `CinderRuntimeError` matching
  `"digit_product() requires an int, got float"` — the same message
  shape `_require_int` already produces for `digit_sum`.
- `digit_product(true);` raises `CinderRuntimeError` matching
  `"digit_product() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_sum`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py` (model on the `TestDigitSum` test class,
search `class TestDigitSum`). Once merged, `README.md`'s Builtins
bullet needs `digit_product` added near `digit_sum`/`reverse_int`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
