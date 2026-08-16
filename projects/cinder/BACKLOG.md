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

## 1. Standard library: `is_semiprime` — product of exactly two primes [claimed 2026-08-16T14:18:06Z]

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

## 2. Language: uninitialized `let` declarations (`let x;`, defaults to `nil`)

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

## 3. Standard library: `is_powerful_number` — every prime factor appears with exponent 2 or more

Build: the breadth task after task 5's depth work (uninitialized `let`
declarations) per `PROJECT.md`'s breadth-vs-depth policy, restocking
the backlog back to 6 tasks now that `is_squarefree` has landed via PR
#252, dropping the count to the 5-task floor. Add
`is_powerful_number(n)` to `cinder/builtins.py`, registered right
after `is_squarefree` (search for `def _is_squarefree`, immediately
before `divisors` in the numeric-predicate cluster) — the natural
counterpart to `is_squarefree`: a positive integer is squarefree when
*no* prime factor repeats, and powerful when *every* prime factor
repeats (appears with exponent `2` or higher). Equivalently, `n` is
powerful exactly when it can be written as `a^2 * b^3` for positive
integers `a`, `b` — e.g. `36 = 2^2 * 3^2` is powerful, `12 = 2^2 * 3^1`
isn't (the `3` only appears once). Verify the gap: `python3 -m
cinder.cli eval 'print(is_powerful_number(36));'` currently raises
`CinderRuntimeError` `"undefined name 'is_powerful_number'"` — no such
builtin exists yet.

```python
def _is_powerful_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_powerful_number", arguments, 1, line, column)
    value = _require_int("is_powerful_number", arguments[0], line, column)
    if value < 1:
        return False
    remaining = value
    divisor = 2
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            count = 0
            while remaining % divisor == 0:
                remaining //= divisor
                count += 1
            if count < 2:
                return False
        divisor += 1
    return remaining == 1
```

Model the arity/type-checking exactly on `is_squarefree`/`is_semiprime`'s
own structure: `_require_arity`, then `_require_int` (reusing the
shared helper — do **not** hand-roll a separate `isinstance` check).
`n < 1` returns `false` rather than raising, matching the
boolean-predicate cluster's own convention (`is_squarefree`,
`is_semiprime`, `is_prime`, etc. — **not** the divisor cluster's
type-vs-domain-error convention, since this builtin returns a boolean,
not a number). `is_powerful_number(1)` is `true` — `1` has no prime
factors at all, so the "every prime factor repeats" condition holds
vacuously, the same convention `prime_factors(1) == []` already
establishes for "no factors to violate the rule." The inner `while`
loop peels each prime factor's *full* multiplicity before moving to
the next divisor (unlike `is_semiprime`'s single-division-per-iteration
peel, since counting per-factor multiplicity is exactly the property
being tested here rather than a total factor count), failing fast the
instant any factor's count comes up short of `2` rather than finishing
the factorization first; the trailing `remaining == 1` check catches
the case where a large prime factor above the `sqrt` bound is left
over with only its first power counted, which is the same "peel small
factors, then check what's left" tail case `is_semiprime`/
`prime_factors` already handle.

Acceptance criteria:
- `is_powerful_number(1);` is `true` — vacuously powerful, no prime
  factors to violate the rule.
- `is_powerful_number(4);` is `true` — `4 = 2^2`.
- `is_powerful_number(8);` is `true` — `8 = 2^3`, exponent above `2`
  still counts.
- `is_powerful_number(9);` is `true` — `9 = 3^2`.
- `is_powerful_number(36);` is `true` — `36 = 2^2 * 3^2`, the smallest
  powerful number with two distinct prime factors.
- `is_powerful_number(72);` is `true` — `72 = 2^3 * 3^2`, mixed
  exponents both `>= 2`.
- `is_powerful_number(2);` is `false` — prime, exponent `1`.
- `is_powerful_number(12);` is `false` — `12 = 2^2 * 3^1`, the `3`
  keeps exponent `1` even though `2` doesn't; exercises the fast-fail
  branch.
- `is_powerful_number(4 * 999983);` is `false` — exercises the tail
  `remaining == 1` check: the small part (`2^2`) passes the per-factor
  check, but the large leftover prime factor above the `sqrt` bound
  (`999983`, exponent `1`) fails it.
- `is_powerful_number(0);` is `false` — below the domain floor.
- `is_powerful_number(-4);` is `false` — negative input, same
  convention as `is_squarefree`/`is_semiprime`.
- `is_powerful_number(4.0);` raises `CinderRuntimeError` matching
  `"is_powerful_number() requires an int, got float"` — the same
  message shape `_require_int` already produces for every sibling in
  this cluster.
- `is_powerful_number(true);` raises `CinderRuntimeError` matching
  `"is_powerful_number() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_squarefree`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestIsSquarefree`/
`TestIsSemiprime` test classes). Once merged, `README.md`'s Builtins
bullet needs `is_powerful_number` added near `is_squarefree`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 4. Language: single-quoted string literals (`'...'` as an alternate delimiter)

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

## 5. Standard library: `is_repdigit` — every decimal digit is the same

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
prime-factorization-flavored predicate: this backlog already carries
`is_semiprime` (task 2) and `is_powerful_number` (task 4) back-to-back
in the same trial-division style, so this task deliberately varies the
sub-theme within the breadth slot instead of extending that run further.
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

## 6. Language: scientific notation for float literals (`1e3`, `1.5e-2`, `2E+10`)

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
