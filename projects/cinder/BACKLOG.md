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

## 1. Standard library: `is_carmichael_number` — Korselt's-criterion pseudoprime predicate

Build: Cinder already has `is_prime`/`prime_factors`/`is_squarefree`
(`cinder/builtins.py`, search `def _prime_factors`: trial-divides up to
`math.isqrt` to build a factor list with repetition) but nothing that
tests the classic Fermat-pseudoprime family — a Carmichael number is a
*composite* integer `n` that nonetheless passes every Fermat primality
test (`a^n ≡ a (mod n)` for every integer `a`), which by Korselt's
criterion (1899) is exactly the set of composite, squarefree integers
`n` where `(p - 1)` divides `(n - 1)` for every prime factor `p` of
`n` — no modular exponentiation loop over `a` needed, just the
factorization. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_carmichael_number(561));'
# -> <eval>:1:7: undefined name 'is_carmichael_number'
```

Worked examples: `561 = 3 * 11 * 17` is the smallest Carmichael number
— squarefree, composite, and `(3-1)=2 | 560`, `(11-1)=10 | 560`,
`(17-1)=16 | 560` all hold (`560 = 561 - 1`). Contrast `562 = 2 * 281`:
squarefree and composite, but `(2-1)=1 | 561` holds while
`(281-1)=280 | 561` does not (`561 / 280` is not an integer), so `562`
is not Carmichael. `9 = 3^2` is composite but not squarefree (the
prime `3` repeats), so it fails before the divisibility check even
runs. Primes themselves are excluded outright (Korselt's criterion
only applies to composites). The next few Carmichael numbers after
`561` are `1105`, `1729`, `2465`, `2821`, `6601`, `8911` (OEIS A002997)
— `1729` is also the Hardy-Ramanujan taxicab number, a fun aside worth
no more than a passing comment if any.

Algorithm — factor via the same trial-division shape `_prime_factors`
already uses (build a list with repetition, not a set, so squarefree-ness
falls out of a length check against the deduped set), then apply
Korselt's criterion:
```python
def _is_carmichael_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_carmichael_number", arguments, 1, line, column)
    value = _require_int("is_carmichael_number", arguments[0], line, column)
    if value < 2:
        return False
    factors = []
    remaining = value
    divisor = 2
    while divisor * divisor <= remaining:
        while remaining % divisor == 0:
            factors.append(divisor)
            remaining //= divisor
        divisor += 1
    if remaining > 1:
        factors.append(remaining)
    if len(factors) < 2:
        return False  # prime, not composite
    if len(factors) != len(set(factors)):
        return False  # not squarefree
    return all((prime - 1) != 0 and (value - 1) % (prime - 1) == 0 for prime in factors)
```
Add this directly after `_is_smith_number` (search `def
_is_smith_number`, insert right after its closing `return` statement,
ahead of whatever function happens to follow it — this task's own diff
only adds the new function and its dict entry, nothing else moves) —
keeps it grouped with the file's other prime-factorization predicates.
Also register the new dict entry (search `"is_smith_number":
_is_smith_number,`, add `"is_carmichael_number":
_is_carmichael_number,` directly after it).

Acceptance criteria:
- `is_carmichael_number(561);` is `true` — the smallest Carmichael
  number, the worked example above.
- `is_carmichael_number(1105);`, `is_carmichael_number(1729);`,
  `is_carmichael_number(2465);`, `is_carmichael_number(2821);` are all
  `true` — further OEIS A002997 terms, confirming the check scales
  past the smallest instance.
- `is_carmichael_number(562);` is `false` — squarefree and composite
  but fails Korselt's divisibility check, the contrasting worked
  example above.
- `is_carmichael_number(9);` is `false` — composite but not squarefree
  (`3^2`), fails before the divisibility check runs.
- `is_carmichael_number(17);` is `false` — prime, not composite,
  `len(factors) < 2` short-circuits before either the squarefree or
  divisibility check.
- `is_carmichael_number(1);`, `is_carmichael_number(0);` are both
  `false` — trivially not composite.
- `is_carmichael_number(-561);` is `false` — negative numbers return
  `false` outright, matching `is_smith_number`/`is_weird_number`'s own
  negative-number convention in this file, not a domain error.
- `is_carmichael_number(true);` raises `CinderRuntimeError` matching
  `"is_carmichael_number() requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a
  Python `int` subclass (same guard every other int-only predicate in
  this file already relies on).
- `is_carmichael_number("561");` raises `CinderRuntimeError` matching
  `"is_carmichael_number() requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (near `_is_smith_number`, search
`def _is_smith_number`), `tests/test_builtins.py` (new `class
TestIsCarmichaelNumber`, modeled on `class TestIsSmithNumber`, search
that name, for the test shapes above). Once merged, `README.md`'s
Builtins bullet needs `is_carmichael_number` added near
`is_smith_number`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 2. Language: `<=>` (spaceship / three-way comparison) operator

Build: Cinder already has `<`/`<=`/`>`/`>=` working consistently across
numbers, strings, lists (lexicographic), and maps (key-sorted item
comparison) via a single shared helper (`cinder/interpreter.py`, search
`def _compare`), plus order-independent equality via `values_equal`
(used by `==`/`!=`). There is no three-way comparison operator that
combines both into a single `-1`/`0`/`1` result the way Ruby/Perl/PHP's
`<=>` does — useful as a comparator building block once user-defined
sort comparators exist, and a natural small addition given the
comparison machinery it needs already exists end-to-end. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(1 <=> 2);'
# -> <eval>:1:11: expected an expression, found '>'
```
(The lexer currently emits `<=` then leaves a bare `>` for the parser,
which cannot start an expression with it.)

Three-layer change, all straightforward extensions of existing code:

1. **Token** (`cinder/tokens.py`): add `SPACESHIP = auto()` directly
   after `GTEQ = auto()`.

2. **Lexer** (`cinder/lexer.py`, search `def _lt`): currently
   `_lt` matches `=` and immediately emits `LTEQ`. Change it to look
   one character further for `<=>`:
   ```python
   def _lt(self, start_line: int, start_col: int):
       if self._match("="):
           if self._match(">"):
               self.tokens.append(
                   Token(TokenType.SPACESHIP, "<=>", None, start_line, start_col)
               )
           else:
               self.tokens.append(Token(TokenType.LTEQ, "<=", None, start_line, start_col))
       elif self._match("<"):
           ...  # LSHIFT/LSHIFTEQ handling unchanged
       else:
           self.tokens.append(Token(TokenType.LT, "<", None, start_line, start_col))
   ```
   Only the `if self._match("=")` branch changes; the `<<`/`<<=`/`<`
   branches are untouched.

3. **Parser** (`cinder/parser.py`, search `_COMPARISON = {`): add
   `TokenType.SPACESHIP` to the `_COMPARISON` set but **not** to
   `_ORDERING` — this puts `<=>` at the same precedence tier as
   `==`/`!=`/`<`/`<=`/`>`/`>=` (so `1 <=> 2 == -1` parses as
   `(1 <=> 2) == -1`) without making it chainable the way `a < b < c`
   is: `_comparison()`'s chaining check (`all(op.type in _ORDERING for
   op in operators)`) only fires when every operator in a run is a pure
   ordering operator, so a `<=>` in the mix falls through to sequential
   left-to-right `Binary` application — exactly how `==`/`!=` already
   behave when mixed with `<`, no new logic needed.

4. **Interpreter** (`cinder/interpreter.py`, search `if op in
   (TokenType.LT, TokenType.LTEQ, TokenType.GT, TokenType.GTEQ):`):
   add a branch immediately after it, reusing `_compare` and
   `values_equal` rather than duplicating their type/error handling:
   ```python
   if op == TokenType.SPACESHIP:
       if self._compare(operator, left, right, TokenType.LT):
           return -1
       if values_equal(left, right):
           return 0
       return 1
   ```
   `_compare(operator, left, right, TokenType.LT)` already raises
   `CinderRuntimeError` for uncomparable types (e.g. int vs string, int
   vs bool) before this branch would ever reach `values_equal`, so
   `<=>` inherits `<`'s exact comparability rules and error messages
   for free.

Scope: comparison only, no compound-assignment form (`<`/`>`/`==` have
none either — a "spaceship-assign" has no sensible meaning). Every
comparable pair `<`/`==` already handle (numbers including cross
int/float, strings, lists, maps) is automatically comparable via `<=>`
too, since it is built entirely from those two existing operations.

Acceptance criteria:
- `1 <=> 2;` is `-1`, `2 <=> 2;` is `0`, `3 <=> 2;` is `1`.
- `"a" <=> "b";` is `-1`, `"b" <=> "a";` is `1`, `"a" <=> "a";` is `0`.
- `[1, 2] <=> [1, 3];` is `-1` — lexicographic, matching list `<`.
- `[1, 2] <=> [1, 2];` is `0`.
- `{"a": 1} <=> {"a": 2};` is `-1` — key-sorted item comparison,
  matching map `<`.
- `{"a": 1, "b": 2} <=> {"b": 2, "a": 1};` is `0` — map equality is
  order-independent via `values_equal`, consistent with `==`, even
  though the two maps' key-sorted item lists happen to already agree
  here too.
- `1 <=> 1.0;` is `0` — cross int/float equality already holds for
  `==`, inherited here via `values_equal`.
- `1.5 <=> 1;` is `1` — cross int/float ordering already holds for
  `<`, inherited here via `_compare`.
- `1 <=> "a";` raises `CinderRuntimeError` matching `"unsupported
  operand types for comparison: int and string"` — the exact message
  `_compare` already raises for `1 < "a"`.
- `1 <=> true;` raises `CinderRuntimeError` matching `"unsupported
  operand types for comparison: int and bool"` — `_compare` already
  rejects `int`/`bool` pairs the same way for `<`, since Cinder's
  `bool` is excluded from `_is_number`'s numeric-comparability check.
- `(1 <=> 1) == 0;` is `true` and `(2 <=> 1) == 1;` is `true` —
  confirms `<=>`'s result composes as an ordinary int with `==` at the
  same precedence tier, non-chained (mirrors how `1 == 2 == 3` already
  evaluates sequentially rather than chaining, since `_ORDERING`
  excludes `EQEQ`/`BANGEQ` today).
- Lexer regression: `1 << 2;` (`LSHIFT`) and `1 <= 2;` (`LTEQ`) are
  both unaffected — only a literal `<=>` sequence produces the new
  token.
- Full test suite passes.

Likely files: `cinder/tokens.py` (new `SPACESHIP` token, next to
`GTEQ`), `cinder/lexer.py` (`_lt`, search `def _lt`), `cinder/parser.py`
(`_COMPARISON`, search `_COMPARISON = {`), `cinder/interpreter.py`
(`_apply_binary_operator`, search `if op in (TokenType.LT,
TokenType.LTEQ, TokenType.GT, TokenType.GTEQ):`), `tests/test_lexer.py`
(new token-emission cases near the existing `<<`/`<=` tests),
`tests/test_parser.py` (a case confirming `<=>` doesn't trigger
`ChainedComparison`), `tests/test_interpreter.py` (new `class
TestSpaceshipOperator`, modeled on `class TestComparisons`, search that
name, for the test shapes above). Once merged, `README.md`'s
language-operators bullet needs a `<=>` mention, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass,
not this task.

---

## 3. Standard library: `is_palindrome_permutation` — can a string's characters be rearranged into a palindrome?

Build: Cinder already has `is_anagram` (`cinder/builtins.py`, search `def
_is_anagram`: two strings share the same character multiset, via
`Counter(string1) == Counter(string2)`) and `is_palindrome` (search `def
_is_palindrome`: a single string already reads the same forwards and
backwards), but nothing that answers the question in between — whether a
*single* string's characters could be *rearranged* into some palindrome,
without actually needing to be one already. A string can be permuted into
a palindrome iff at most one distinct character has an odd count in its
multiset (that one odd-count character, if any, sits in the middle; every
other character must pair up on both sides). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_palindrome_permutation("carrace"));'
# -> <eval>:1:7: undefined name 'is_palindrome_permutation' (did you mean 'is_permutation'?)
```

Worked examples: `"carrace"` has counts `c:2, a:2, r:2, e:1` — exactly one
odd count (`e`), so it permutes to a palindrome (e.g. `"racecar"`).
`"aabbcc"` has all-even counts (`a:2, b:2, c:2`) — zero odd counts, still
permutable (e.g. `"abccba"`). `"aabbc"` has counts `a:2, b:2, c:1` — one
odd count, permutable (`"abcba"`). `"abc"` has counts `a:1, b:1, c:1` —
three odd counts, not permutable. Exact-character convention throughout
(case-sensitive, no whitespace/punctuation stripping), matching
`is_anagram`'s own exact-`Counter`-equality convention rather than
`is_isogram`'s case-folded/letters-only one — so `"Aa"` (counts `A:1, a:1`,
two distinct odd-count characters since `A` and `a` are different
characters here) is not permutable, and a space counts like any other
character (`"ab a"` has counts `a:2, b:1, " ":1` — two odd counts, not
permutable).

Add to `cinder/builtins.py`, directly after `_is_anagram` (search `def
_is_anagram`, immediately before `def _is_rotation`) — keeps it grouped
with the other character-multiset string predicates:
```python
def _is_palindrome_permutation(arguments: list, line: int, column: int) -> object:
    _require_arity("is_palindrome_permutation", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"is_palindrome_permutation() requires a string, got {type_name(value)}",
            line, column,
        )
    odd_counts = sum(1 for count in Counter(value).values() if count % 2 == 1)
    return odd_counts <= 1
```
(`Counter` is already imported at module level for `_is_anagram`'s own
use — no new import needed.) Also register the new dict entry (search
`"is_anagram": _is_anagram,`, add `"is_palindrome_permutation":
_is_palindrome_permutation,` directly after it, before `"is_rotation":
_is_rotation,`).

Acceptance criteria:
- `is_palindrome_permutation("carrace");` is `true` — one odd count
  (`e`), the worked example above.
- `is_palindrome_permutation("aabbcc");` is `true` — zero odd counts.
- `is_palindrome_permutation("aabbc");` is `true` — one odd count (`c`).
- `is_palindrome_permutation("abc");` is `false` — three odd counts, the
  contrasting worked example above.
- `is_palindrome_permutation("");` is `true` — the empty string vacuously
  permutes into itself, a palindrome.
- `is_palindrome_permutation("a");` is `true` — a single character is
  always already a palindrome.
- `is_palindrome_permutation("Aa");` is `false` — case-sensitive, `A` and
  `a` are distinct characters each with an odd count of 1.
- `is_palindrome_permutation("ab a");` is `false` — a space counts like
  any other character, giving two odd counts (`a:2` even, `b:1` and
  `" ":1` both odd).
- `is_palindrome_permutation("racecar");` is `true` — already a
  palindrome, which is always trivially permutable into one (zero odd
  counts here since every character but the middle `e` pairs up, and `e`
  itself is the one allowed odd count).
- `is_palindrome_permutation(5);` raises `CinderRuntimeError` matching
  `"is_palindrome_permutation() requires a string, got int"`, matching
  `is_anagram`/`is_palindrome`'s own non-string-argument convention in
  this file.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_anagram`, search
`def _is_anagram`), `tests/test_builtins.py` (new `class
TestIsPalindromePermutation`, modeled on `class TestIsAnagram`, search
that name, for the test shapes above). Once merged, `README.md`'s
Builtins bullet needs `is_palindrome_permutation` added near
`is_anagram`/`is_palindrome`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Standard library: `is_practical_number` — every smaller value is a divisor-subset sum

Build: Cinder already has the perfect/abundant/deficient divisor-sum family
(`cinder/builtins.py`, search `def _is_perfect_number`: sums a number's
proper divisors via trial division up to `math.isqrt(value)` and compares
to the number) but nothing that asks the stronger question practical
numbers pose: not just whether the proper divisors sum to at least `n`,
but whether *every* integer from `1` to `n - 1` can individually be built
as a sum of distinct proper divisors of `n`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_practical_number(6));'
# -> <eval>:1:7: undefined name 'is_practical_number'
```

Worked examples: `6`'s proper divisors are `1, 2, 3`; every value `1..5`
is reachable (`1`, `2`, `3`, `1+3=4`, `2+3=5`), so `6` is practical.
Contrast `10`: proper divisors `1, 2, 5`; `1, 2, 3(1+2), 5, 6(1+5),
7(2+5), 8(1+2+5)` are reachable but `4` is not — no subset of `{1, 2,
5}` sums to `4` — so `10` is *not* practical despite being abundant-ish
in divisor count. `4`'s proper divisors are `1, 2` (sum `3 < 4`, so `4`
isn't even abundant), yet `4` **is** practical: only `1` and `2` need
checking (`m` ranges up to `n - 1 = 3`, not `n` itself, since `n` is
always trivially reachable via the improper divisor `n` alone), and
`1, 2, 1+2=3` are all reachable. This `m < n` (not `m <= n`) bound is
the detail every other divisor-sum predicate in this file (`is_perfect_number`/
`is_abundant`/`is_deficient`) doesn't need, since none of them do a
per-value reachability sweep — get this off by one and `4` wrongly comes
out non-practical. `1` is practical by convention (there is no `m` in
`1..0` to check, vacuously true). The next few practical numbers after
`1, 2, 4, 6` are `8, 12, 16, 18, 20, 24, 28` (OEIS A005153).

Add to `cinder/builtins.py`, directly after `_is_perfect_number` (search
`def _is_perfect_number`, immediately before `def _is_abundant`) — keeps
it grouped with the other proper-divisor-sum predicates:
```python
def _is_practical_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_practical_number", arguments, 1, line, column)
    value = _require_int("is_practical_number", arguments[0], line, column)
    if value < 1:
        return False
    if value == 1:
        return True
    divisors = [1]
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            divisors.append(divisor)
            complement = value // divisor
            if complement != divisor:
                divisors.append(complement)
    reachable = {0}
    for divisor in divisors:
        reachable |= {total + divisor for total in reachable if total + divisor <= value}
    return all(target in reachable for target in range(1, value))
```
(`complement` can never equal `value` here since the loop starts at
`divisor = 2`, so every entry added to `divisors` is a genuine proper
divisor — no `complement != value` guard needed, unlike `_is_perfect_number`'s
own loop just above it. The `reachable` sweep is the same bounded
subset-sum shape `is_weird_number` (PR #377) uses,
capped at `value` at every step so it stays fast even for numbers with
many divisors.) Also register the new dict entry (search
`"is_perfect_number": _is_perfect_number,`, add `"is_practical_number":
_is_practical_number,` directly after it, before `"is_abundant":
_is_abundant,`).

Acceptance criteria:
- `is_practical_number(1);`, `is_practical_number(2);`,
  `is_practical_number(4);`, `is_practical_number(6);` are all `true` —
  the worked examples above, including the `m < n` edge case at `4`.
- `is_practical_number(8);`, `is_practical_number(12);`,
  `is_practical_number(16);`, `is_practical_number(18);`,
  `is_practical_number(20);` are all `true` — further OEIS A005153
  terms, confirming the check scales past the smallest instances.
- `is_practical_number(3);`, `is_practical_number(5);`,
  `is_practical_number(10);` are all `false` — `3`/`5` are prime (proper
  divisors sum to `1`, too small to reach `2`), `10` is the contrasting
  worked example above (misses `4`).
- `is_practical_number(0);` is `false` — trivially not practical.
- `is_practical_number(-6);` is `false` — negative numbers return
  `false` outright, matching `is_abundant`/`is_deficient`'s own
  negative-number convention in this file, not a domain error.
- `is_practical_number(true);` raises `CinderRuntimeError` matching
  `"is_practical_number() requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `is_practical_number("6");` raises `CinderRuntimeError` matching
  `"is_practical_number() requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_perfect_number`,
search `def _is_perfect_number`), `tests/test_builtins.py` (new `class
TestIsPracticalNumber`, modeled on `class TestIsPerfectNumber`, search
that name, for the test shapes above). Once merged, `README.md`'s
Builtins bullet needs `is_practical_number` added near
`is_perfect_number`/`is_abundant`/`is_deficient`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

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
