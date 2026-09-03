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

## 1. Standard library: `nth_deficient` — deficient number found at a 1-indexed position

Build: Cinder already has `is_deficient` (`cinder/builtins.py`, search `def
_is_deficient`: proper-divisor sum less than the number itself) and its
abundant-number sibling already has a value-returning counterpart,
`nth_abundant` (search `def _nth_abundant`: a sequential candidate scan
using a private nested `_is_abundant_candidate` helper, since abundant
numbers have no closed form) — but there is no equivalent for the
deficient side, the value-returning sibling `is_deficient` itself is
missing. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_deficient(3));'
# -> <eval>:1:7: undefined name 'nth_deficient' (did you mean 'is_deficient'?)
```

Worked examples: the first ten deficient numbers (proper-divisor sum less
than the number, OEIS A005100) are `1, 2, 3, 4, 5, 7, 8, 9, 10, 11` — note
`6` is skipped (a perfect number, proper divisors `1+2+3=6`) and so is any
multiple of 6 that happens to be perfect/abundant; the 20th is `25`. Every
prime is deficient (proper-divisor sum is always `1 < p`), so deficient
numbers are far denser than abundant numbers — `nth_deficient` needs no
special-casing for that, the same bounded sequential scan `nth_abundant`
already uses just finds matches sooner.

Add directly after `_nth_abundant` (search `def _nth_abundant`, immediately
before `def _is_deficient`) — keeps the value-returning helper next to the
`is_abundant`/`nth_abundant` pair it mirrors:
```python
def _nth_deficient(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_deficient", arguments, 1, line, column)
    value = _require_int("nth_deficient", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_deficient() requires a positive integer, domain error", line, column
        )

    def _is_deficient_candidate(candidate: int) -> bool:
        total = 1 if candidate > 1 else 0
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                total += divisor
                complement = candidate // divisor
                if complement != divisor:
                    total += complement
        return total < candidate

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_deficient_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_abundant`, only the comparison flips from `>` to
`<`, matching `_is_abundant`/`_is_deficient`'s own relationship.) Also
register the new dict entry (search `"is_deficient": _is_deficient,`, add
`"nth_deficient": _nth_deficient,` directly before it, next to
`"nth_abundant": _nth_abundant,` which already sits right above
`"is_deficient"` in the dict).

Acceptance criteria:
- `nth_deficient(1);` through `nth_deficient(10);` are `1, 2, 3, 4, 5, 7,
  8, 9, 10, 11` in order — the worked example above (note the gap at `6`).
- `nth_deficient(20);` is `25` — a further worked example confirming the
  scan scales past the first ten.
- For every `position` in `1..50`, `is_deficient(nth_deficient(position))`
  is `true` — the same self-consistency check `nth_abundant`'s own test
  suite already runs against `is_abundant`.
- `nth_deficient(0);`, `nth_deficient(-3);` both raise `CinderRuntimeError`
  matching `"nth_deficient\(\) requires a positive integer, domain
  error"`, matching `nth_abundant`'s own non-positive-input convention.
- `nth_deficient(true);` raises `CinderRuntimeError` matching
  `"nth_deficient\(\) requires an int, got bool"`, since `_require_int`
  rejects `bool` even though Cinder's `bool` is a Python `int` subclass
  (same guard every other int-only predicate in this file already relies
  on).
- `nth_deficient("3");` raises `CinderRuntimeError` matching
  `"nth_deficient\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_nth_abundant`, search
`def _nth_abundant`), `tests/test_builtins.py` (new `class
TestNthDeficient`, modeled on `class TestNthAbundant`, search that name,
for the test shapes above). Once merged, `README.md`'s Builtins bullet
needs `nth_deficient` added near `is_deficient`/`nth_abundant`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 2. Standard library: `is_semiperfect` — n equals a sum of some subset of its own proper divisors

Build: Cinder's `is_weird_number` (`cinder/builtins.py`, search `def
_is_weird_number`) is defined as "abundant but not semiperfect" and
already computes both halves internally — a proper-divisor list, then a
bounded 0/1 subset-sum sweep (`reachable`) checking whether `value`
itself turns up as some subset's sum — but only the *negation* of that
second half is exposed, folded into `is_weird_number`'s combined abundant
check. There is no standalone way to ask the semiperfect (a.k.a.
pseudoperfect) question on its own, independent of abundance. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(is_semiperfect(12));'
# -> <eval>:1:7: undefined name 'is_semiperfect' (did you mean 'is_semiprime'?)
```

Worked examples: `6`'s proper divisors are `1, 2, 3` — the full set sums
to exactly `6`, so `6` is semiperfect (it is also perfect: every perfect
number is trivially semiperfect via its complete divisor set). `12`'s
proper divisors are `1, 2, 3, 4, 6` — the subset `{2, 4, 6}` sums to
`12` (so does `{1, 2, 3, 6}`), so `12` is semiperfect despite not being
perfect. `18`'s proper divisors are `1, 2, 3, 6, 9` — `{3, 6, 9}` sums to
`18`. Contrast `16`: proper divisors `1, 2, 4, 8` sum to only `15 < 16`
(deficient), so no subset can possibly reach `16` — not semiperfect.
Contrast `70`, Cinder's own `is_weird_number` worked example: proper
divisors `1, 2, 5, 7, 10, 14, 35` sum to `74 > 70` (abundant) yet no
subset of them sums to exactly `70` — abundant but not semiperfect is
precisely *why* `70` is weird, so `is_semiperfect(70)` must be `false`
even though the number is abundant. This gives a direct cross-check:
for every `n`, `is_weird_number(n)` must equal `is_abundant(n) and not
is_semiperfect(n)`.

Add to `cinder/builtins.py`, directly after `_is_weird_number` (search
`def _is_weird_number`, immediately before `def _is_automorphic`) — keeps
it grouped with the divisor-sum family it factors apart:
```python
def _is_semiperfect(arguments: list, line: int, column: int) -> object:
    _require_arity("is_semiperfect", arguments, 1, line, column)
    value = _require_int("is_semiperfect", arguments[0], line, column)
    if value < 2:
        return False
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
    return value in reachable
```
(Identical subset-sum shape to `_is_weird_number`'s own `reachable`
sweep, just asking directly whether `value` itself is reachable instead
of checking abundance first and negating reachability second — the two
functions will necessarily duplicate this block, which is fine: factoring
it into a shared helper is out of scope for this task and not requested.)
Also register the new dict entry (search `"is_weird_number":
_is_weird_number,`, add `"is_semiperfect": _is_semiperfect,` directly
after it, before `"is_automorphic": _is_automorphic,`).

Acceptance criteria:
- `is_semiperfect(6);`, `is_semiperfect(12);`, `is_semiperfect(18);`,
  `is_semiperfect(20);`, `is_semiperfect(28);` are all `true` — the
  worked examples above plus further OEIS A005835 terms (`28` is
  perfect, trivially semiperfect via its full divisor set).
- `is_semiperfect(1);`, `is_semiperfect(2);`, `is_semiperfect(4);`,
  `is_semiperfect(16);` are all `false` — too few/small proper divisors
  to reach the target, the `16` contrast above.
- `is_semiperfect(70);` is `false` — the `is_weird_number` worked
  example: abundant but not semiperfect.
- For every `n` in `2..200`, `is_weird_number(n)` equals
  `(is_abundant(n) and not is_semiperfect(n))` — the direct cross-check
  derived above, confirming this task's extraction matches
  `is_weird_number`'s existing internal logic exactly rather than
  drifting from it.
- `is_semiperfect(0);`, `is_semiperfect(-6);` are both `false` —
  non-positive numbers return `false` outright, matching
  `is_weird_number`'s own `value < 2` guard.
- `is_semiperfect(true);` raises `CinderRuntimeError` matching
  `"is_semiperfect() requires an int, got bool"`, since `_require_int`
  rejects `bool` even though Cinder's `bool` is a Python `int` subclass
  (same guard every other int-only predicate in this file already relies
  on).
- `is_semiperfect("6");` raises `CinderRuntimeError` matching
  `"is_semiperfect() requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_weird_number`,
search `def _is_weird_number`), `tests/test_builtins.py` (new `class
TestIsSemiperfect`, modeled on `class TestIsWeirdNumber`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `is_semiperfect` added near `is_weird_number`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 3. Language: `*` marker for keyword-only function parameters

Build: Cinder function parameters (`cinder/parser.py`, search `def
_fn_param_list`/`def _fn_param`) can already carry defaults (`fn f(a, b =
1)`), a single trailing rest parameter (`fn f(a, ...rest)`), and
destructuring shapes (`fn f([a, b])`/`fn f({a, b})`) — and every named
parameter can already be passed either positionally or by name (`f(1, 2)`
and `f(a: 1, b: 2)` both work via the existing keyword-argument machinery
in `cinder/interpreter.py`'s `call_value`, search `def call_value`). There
is no way to *force* a parameter to be passed by name only — a caller can
always sneak a value in positionally even when the author intended a
trailing flag/option-style parameter to always be self-documenting at the
call site. Verify the gap:
```sh
python3 -m cinder.cli eval 'fn f(a, *, b) { return a + b; } print(f(1, 2));'
# -> currently PARSES (bare '*' is not recognized in a parameter list at
#    all, so this fails elsewhere) - run this first to see today's error:
python3 -m cinder.cli eval 'fn greet(name, *, loud) { return loud ? name + "!" : name; } print(greet("Ada", loud: true));'
# -> <eval>:1:19: expected parameter name, found '*'
```

Worked examples: `fn greet(name, *, loud) { ... }` declares `name` as an
ordinary positional-or-keyword parameter and `loud` as keyword-only — the
bare `*` is not itself a parameter, it is a marker after which every
parameter must be supplied by name. `greet("Ada", loud: true)` works;
`greet("Ada", true)` must raise the same shape of arity error Cinder
already raises for too many positional arguments, since `true` has no
positional slot to land in. Keyword-only parameters may have defaults
(`fn f(a, *, b = 1) { ... }`) and, unlike positional parameters, are not
subject to the existing "no-default parameter cannot follow a
default parameter" ordering rule — `fn f(a, *, b = 1, c) { ... }` is
legal even though `c` (no default) comes after `b` (has one), because
neither can be filled positionally, so ordering between them is
irrelevant; call `f(1, c: 2)` and `b` falls back to its default. A bare
trailing `*` with nothing keyword-only after it (`fn f(a, *) { ... }`) is
a `ParseError`, mirroring Python's identical restriction on its own `*`
marker.

Add a `keyword_only: bool = False` field to `Param` (`cinder/ast_nodes.py`,
search `class Param`, directly after the existing `is_map: bool = False`
field) — the same "one more optional field on the shared dataclass"
shape `is_map` itself already added for map-destructuring parameters.

Rewrite `_fn_param_list` (`cinder/parser.py`, search `def
_fn_param_list`) to recognize a bare `TokenType.STAR` (the existing
multiplication-operator token — unambiguous here since expression syntax
never appears at parameter-list position) as the keyword-only marker,
restructured into one loop so the marker can appear before the first
parameter too (`fn f(*, a) { ... }`):
```python
def _fn_param_list(self) -> tuple:
    params = []
    rest_param = None
    seen_default = False
    seen_star = False
    star_token = None
    if not self._check(TokenType.RPAREN):
        while True:
            if self._check(TokenType.STAR):
                token = self._peek()
                if seen_star:
                    raise ParseError("duplicate '*' in parameter list", token.line, token.column)
                if rest_param is not None:
                    raise ParseError(
                        "cannot combine keyword-only parameters with a rest parameter",
                        token.line, token.column,
                    )
                star_token = self._advance()
                seen_star = True
                seen_default = False
            elif self._check(TokenType.DOT_DOT_DOT):
                token = self._peek()
                if rest_param is not None:
                    raise ParseError("rest parameter must be the last parameter", token.line, token.column)
                if seen_star:
                    raise ParseError(
                        "cannot combine keyword-only parameters with a rest parameter",
                        token.line, token.column,
                    )
                rest_param = self._fn_rest_param()
            else:
                if rest_param is not None:
                    token = self._peek()
                    raise ParseError("rest parameter must be the last parameter", token.line, token.column)
                if seen_star and (self._check(TokenType.LBRACKET) or self._check(TokenType.LBRACE)):
                    token = self._peek()
                    raise ParseError(
                        "keyword-only parameter cannot use destructuring", token.line, token.column
                    )
                param = self._fn_param(seen_default, keyword_only=seen_star)
                params.append(param)
                if not seen_star:
                    seen_default = seen_default or param.default is not None
            if self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RPAREN):
                    break
                continue
            break
    if seen_star and not any(param.keyword_only for param in params):
        raise ParseError("named parameter required after '*'", star_token.line, star_token.column)
    return params, rest_param
```
(Preserves every existing error message verbatim — `"rest parameter must
be the last parameter"` still fires in the same cases as today's
while-loop version, just reached from the restructured single loop.)
`_fn_param` (search `def _fn_param`) gains a `keyword_only: bool = False`
parameter, threaded only into the final plain-identifier `return
Param(name=name_token.lexeme, default=default, keyword_only=keyword_only)`
— its internal `elif seen_default:` ordering check needs no change,
since the caller above never sets `seen_default` while inside the
keyword-only section, so that branch is simply never true there.

Two small `cinder/interpreter.py` changes (both already exercise the
exact same fields, just filtering out `keyword_only` params from the
*positional* counts):
```python
@property
def arity(self) -> int:
    """Minimum arity: the count of required positional parameters
    (no default, not keyword-only)."""
    return sum(
        1 for param in self.decl.params if not param.keyword_only and param.default is None
    )
```
and in `call_value` (search `min_arity = callee.arity`), change
`max_arity = None if callee.decl.rest_param else len(callee.decl.params)`
to
`max_arity = None if callee.decl.rest_param else sum(1 for p in callee.decl.params if not p.keyword_only)`,
then immediately after the existing `if not keywords:` branch's
arity-bound check (the block raising `"{name}() expects ... argument(s),
got ..."`), add:
```python
missing_keyword_only = [
    p.name for p in callee.decl.params if p.keyword_only and p.default is None
]
if missing_keyword_only:
    names = ", ".join(repr(name) for name in missing_keyword_only)
    raise CinderRuntimeError(
        f"{callee.name}() missing required argument(s): {names}", line, column
    )
```
No other change is needed: the `else` (keywords-present) branch's
existing `missing`/`unexpected`/`multiple values` checks and the argument
-binding loop already do the right thing once `max_arity` excludes
keyword-only params from the positional count — a keyword-only
parameter's `index` can then never be `< len(arguments)` (since
`len(arguments) <= max_arity <= index` for any keyword-only param, whose
index always comes after every positional one), so it is always filled
from `keywords` or its default, never positionally, with no extra
bookkeeping.

Acceptance criteria:
- `fn greet(name, *, loud) { return loud ? name + "!" : name; }
  greet("Ada", loud: true);` is `"Ada!"` — the worked example above.
- `fn greet(name, *, loud) { return loud ? name + "!" : name; }
  greet("Ada", true);` raises `CinderRuntimeError` matching
  `"greet\(\) expects 1 argument\(s\), got 2"` — `loud` has no positional
  slot, so the second positional argument overflows.
- `fn f(a, *, b = 1) { return a + b; } f(1);` is `2` and `f(1, b: 5);` is
  `6` — a keyword-only parameter's default still applies when omitted.
- `fn f(a, *, b = 1, c) { return a + c; } f(1, c: 2);` is `3` — a
  defaulted keyword-only parameter followed by a non-defaulted one is
  legal (the existing default-ordering rule does not apply past `*`).
- `fn f(*, a) { return a; } f(a: 1);` is `1` — `*` as the very first
  entry in the parameter list, making every parameter keyword-only.
- `fn f(a, *, b) { return a; } f(1);` raises `CinderRuntimeError` matching
  `"f\(\) missing required argument\(s\): 'b'"` — a required keyword-only
  parameter omitted with no other keyword arguments supplied at all
  (exercises the `if not keywords:` branch's new check, not just the
  keywords-present branch).
- `fn f(a) { return a; } f(*);` and `fn f(a, *) { return a; } f(1);` both
  raise `ParseError` matching `"named parameter required after '\*'"` at
  parse time — a bare trailing `*` with nothing keyword-only after it.
- `fn f(*, a, *, b) { return a; }` raises `ParseError` matching
  `"duplicate '\*' in parameter list"`.
- `fn f(a, ...rest, *, b) { return a; }` and `fn f(a, *, b, ...rest) {
  return a; }` both raise `ParseError` matching `"cannot combine
  keyword-only parameters with a rest parameter"` — in either order.
- `fn f(*, [a, b]) { return a; }` raises `ParseError` matching
  `"keyword-only parameter cannot use destructuring"`.
- Regression: `fn f(a, b = 1) { return a + b; } f(1);` is `2` and
  `fn f(a, ...rest) { return rest; } f(1, 2, 3);` is `[2, 3]` — ordinary
  defaults and rest parameters (no `*` involved) are completely
  unaffected.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`Param`, search `class Param`),
`cinder/parser.py` (`_fn_param_list`/`_fn_param`, search `def
_fn_param_list`), `cinder/interpreter.py` (`CinderFunction.arity` and
`call_value`, search `def call_value`), `tests/test_parser.py` (new
`class TestKeywordOnlyParameters` for the `ParseError` cases, modeled on
existing rest-parameter parse-error tests — search `rest parameter must
be the last parameter` there for the pattern), `tests/test_interpreter.py`
(new `class TestKeywordOnlyParameters`, modeled on the existing keyword-
argument test classes, search `class TestKeywordCallArguments`, for the
runtime shapes above). Once merged, `README.md`'s function-parameters
bullet needs a mention of `*` keyword-only parameters alongside the
existing defaults/rest-parameter/destructuring text, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 4. Standard library: `euler_totient` — count of integers up to n coprime with n

Build: Cinder's number-theory builtins already include `prime_factors`
(`cinder/builtins.py`, search `def _prime_factors`: trial-division
factoring returning every prime factor with multiplicity, e.g.
`prime_factors(12)` is `[2, 2, 3]`) and `gcd`/`is_coprime`, but nothing
computes Euler's totient function — the count of integers in `1..n` that
share no common factor with `n`, the building block `is_coprime` checks
pairwise but has no aggregate counterpart. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(euler_totient(9));'
# -> <eval>:1:7: undefined name 'euler_totient'
```

Worked examples: `euler_totient(9)` is `6` — of `1..9`, everything except
the multiples of `3` (`3, 6, 9`) is coprime with `9`, leaving `1, 2, 4, 5,
7, 8`. `euler_totient(1)` is `1` by convention (the empty product / only
`1` itself, coprime with everything trivially). For any prime `p`,
`euler_totient(p)` is `p - 1` (every smaller positive integer is
coprime with a prime) — `euler_totient(13)` is `12`. `euler_totient(36)`
is `12` (`36 = 2^2 * 3^2`, formula below gives `36 * (1/2) * (2/3) =
12`). The standard closed form is `n * product over each distinct prime
factor p of n of (1 - 1/p)`, computed here with pure integer arithmetic
(no floats) by repeatedly dividing out one factor of exact multiplicity
`result // p` at a time — the same "well-known, exact" shape as the
textbook `phi(n)` sieve-free algorithm, not a novel derivation.

Add to `cinder/builtins.py`, directly after `_prime_factors` (search `def
_prime_factors`, immediately before `def _is_smith_number`) — keeps it
grouped with the other prime-factorization-based builtins:
```python
def _euler_totient(arguments: list, line: int, column: int) -> object:
    _require_arity("euler_totient", arguments, 1, line, column)
    value = _require_int("euler_totient", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "euler_totient() requires a positive integer, domain error", line, column
        )
    result = value
    remaining = value
    divisor = 2
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            while remaining % divisor == 0:
                remaining //= divisor
            result -= result // divisor
        divisor += 1
    if remaining > 1:
        result -= result // remaining
    return result
```
(Each `result -= result // p` step is exact integer division precisely
because `p` still divides `result` at that point — `result` starts as
`n`, a multiple of every one of its own prime factors, and each step
only removes factors for primes already confirmed to divide the
original `n`.) Also register the new dict entry (search `"prime_factors":
_prime_factors,`, add `"euler_totient": _euler_totient,` directly after
it, before `"is_smith_number": _is_smith_number,`).

Acceptance criteria:
- `euler_totient(1);` is `1`, `euler_totient(9);` is `6` — the worked
  examples above.
- `euler_totient(2);`, `euler_totient(3);`, `euler_totient(13);` are `1,
  2, 12` — every prime `p` gives `p - 1`.
- `euler_totient(36);` is `12`, `euler_totient(100);` is `40` — further
  worked examples confirming the multi-prime-factor case.
- For every `n` in `1..100`, `euler_totient(n)` equals
  `len([m for m in 1..n where is_coprime(m, n)])` computed independently
  via a brute-force loop in the test itself (not calling
  `euler_totient` to check itself) — a direct cross-check against the
  function's own definition, the same shape `nth_abundant`'s test suite
  uses to cross-check against `is_abundant`.
- `euler_totient(0);`, `euler_totient(-9);` both raise
  `CinderRuntimeError` matching `"euler_totient\(\) requires a positive
  integer, domain error"`, matching `prime_factors`' own non-positive-
  input convention.
- `euler_totient(true);` raises `CinderRuntimeError` matching
  `"euler_totient\(\) requires an int, got bool"`, since `_require_int`
  rejects `bool` even though Cinder's `bool` is a Python `int` subclass
  (same guard every other int-only predicate in this file already relies
  on).
- `euler_totient("9");` raises `CinderRuntimeError` matching
  `"euler_totient\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_prime_factors`,
search `def _prime_factors`), `tests/test_builtins.py` (new `class
TestEulerTotient`, modeled on `class TestPrimeFactors`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `euler_totient` added near `prime_factors`/`is_coprime`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Standard library: `nth_practical_number` — practical number found at a 1-indexed position

Build: Cinder's `is_practical_number` (`cinder/builtins.py`, search `def
_is_practical_number`: proper-divisor list, then a bounded 0/1 subset-sum
sweep checking every integer `1..n-1` is reachable) landed as PR #382 —
but, like `is_abundant`/`nth_abundant` and `is_deficient`/`nth_deficient`
(already queued as task 2 above) before it, it has no value-returning
`nth_*` sibling yet. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_practical_number(5));'
# -> <eval>:1:7: undefined name 'nth_practical_number' (did you mean
#    'is_practical_number'?)
```

Worked examples: the first ten practical numbers (OEIS A005153) are `1,
2, 4, 6, 8, 12, 16, 18, 20, 24` — note the gaps at `3`, `5`, `7`, etc.
(every odd number other than `1` is non-practical, since an odd
number's divisors are all odd and so can never sum to the even targets
among `1..n-1`); the 20th is `60`.

Add directly after `_is_practical_number` (search `def
_is_practical_number`, immediately before `def _is_abundant`) — keeps
the value-returning helper next to the predicate it mirrors, matching
where `nth_abundant` itself sits right after `is_abundant`:
```python
def _nth_practical_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_practical_number", arguments, 1, line, column)
    value = _require_int("nth_practical_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_practical_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_practical_candidate(candidate: int) -> bool:
        if candidate == 1:
            return True
        divisors = [1]
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                divisors.append(divisor)
                complement = candidate // divisor
                if complement != divisor:
                    divisors.append(complement)
        reachable = {0}
        for divisor in divisors:
            reachable |= {
                total + divisor for total in reachable if total + divisor <= candidate
            }
        return all(target in reachable for target in range(1, candidate))

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_practical_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_abundant`, with the inner candidate check
copied from `_is_practical_number`'s own body instead of
`_is_abundant`'s single sum comparison — practical numbers have no
closed form either, so the same bounded sequential scan applies.) Also
register the new dict entry (search `"is_practical_number":
_is_practical_number,`, add `"nth_practical_number":
_nth_practical_number,` directly after it, before `"is_abundant":
_is_abundant,`).

Acceptance criteria:
- `nth_practical_number(1);` through `nth_practical_number(10);` are
  `1, 2, 4, 6, 8, 12, 16, 18, 20, 24` in order — the worked example
  above.
- `nth_practical_number(20);` is `60` — a further worked example
  confirming the scan scales past the first ten.
- For every `position` in `1..50`,
  `is_practical_number(nth_practical_number(position))` is `true` —
  the same self-consistency check `nth_abundant`'s own test suite
  already runs against `is_abundant`.
- `nth_practical_number(0);`, `nth_practical_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_practical_number\(\) requires a
  positive integer, domain error"`, matching `nth_abundant`'s own
  non-positive-input convention.
- `nth_practical_number(true);` raises `CinderRuntimeError` matching
  `"nth_practical_number\(\) requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `nth_practical_number("5");` raises `CinderRuntimeError` matching
  `"nth_practical_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_practical_number`,
search `def _is_practical_number`), `tests/test_builtins.py` (new `class
TestNthPracticalNumber`, modeled on `class TestNthAbundant`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `nth_practical_number` added near `is_practical_number`,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 6. Standard library: `is_refactorable` — divisor count divides the number itself

Build: Cinder's `num_divisors` (`cinder/builtins.py`, search `def
_num_divisors`: counts divisors via a bounded `math.isqrt` sweep,
pairing each divisor found up to the square root with its complement)
has no predicate built on top of it that asks whether that count itself
divides back into the original number — the same "count something about
n, then ask if it divides n" shape `is_harshad` already has for digit
sum, just for divisor count instead. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_refactorable(12));'
# -> <eval>:1:7: undefined name 'is_refactorable'
```

Worked examples (refactorable numbers, a.k.a. tau numbers, OEIS
A033950): `1` is refactorable by convention (`num_divisors(1)` is `1`,
and `1 % 1` is `0`). `8`'s divisors are `1, 2, 4, 8` — `num_divisors(8)`
is `4`, and `8 % 4` is `0`, so `8` is refactorable. `9`'s divisors are
`1, 3, 9` — `num_divisors(9)` is `3`, and `9 % 3` is `0`, refactorable.
`12`'s divisors are `1, 2, 3, 4, 6, 12` — `num_divisors(12)` is `6`,
and `12 % 6` is `0`, refactorable. Contrast `6`: divisors `1, 2, 3, 6`,
`num_divisors(6)` is `4`, and `6 % 4` is `2 != 0` — not refactorable,
even though `6` is a perfect number, showing refactorable-ness is
unrelated to perfection/abundance. The first ten refactorable numbers
are `1, 2, 8, 9, 12, 18, 24, 36, 40, 56`.

Add to `cinder/builtins.py`, directly after `_num_divisors` (search `def
_num_divisors`, immediately before `def _is_amicable`) — keeps it next
to the divisor-count builtin it mirrors the shape of:
```python
def _is_refactorable(arguments: list, line: int, column: int) -> object:
    _require_arity("is_refactorable", arguments, 1, line, column)
    value = _require_int("is_refactorable", arguments[0], line, column)
    if value < 1:
        return False
    if value == 1:
        return True
    count = 2  # 1 and value itself
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            count += 1
            complement = value // divisor
            if complement != divisor:
                count += 1
    return value % count == 0
```
(Duplicates `_num_divisors`'s own counting loop rather than calling it —
`_num_divisors` takes the interpreter-facing `arguments`/`line`/`column`
signature and returns a validated result, not a plain int helper other
builtins can call directly; the same "duplicate the small counting
block" tradeoff `_is_semiperfect`/`_is_weird_number` already made, and
is fine for the same reason: factoring a shared helper is out of scope
for this task and not requested.) Also register the new dict entry
(search `"num_divisors": _num_divisors,`, add `"is_refactorable":
_is_refactorable,` directly after it, before `"is_amicable":
_is_amicable,`).

Acceptance criteria:
- `is_refactorable(1);`, `is_refactorable(8);`, `is_refactorable(9);`,
  `is_refactorable(12);`, `is_refactorable(18);`, `is_refactorable(24);`
  are all `true` — the worked examples above plus further OEIS A033950
  terms.
- `is_refactorable(6);`, `is_refactorable(3);`, `is_refactorable(5);`,
  `is_refactorable(7);` are all `false` — `6`'s contrast above (a
  perfect number that is still not refactorable) plus primes, whose
  divisor count is always `2` and so only divide back in when the
  prime itself is `2`.
- For every `n` in `1..100`, `is_refactorable(n)` equals `n %
  num_divisors(n) == 0` computed independently in the test itself
  (calling both builtins, not reimplementing either) — a direct
  cross-check against the definition, the same shape `nth_abundant`'s
  test suite uses to cross-check against `is_abundant`.
- `is_refactorable(0);`, `is_refactorable(-8);` are both `false` —
  non-positive numbers return `false` outright, matching
  `is_weird_number`'s own non-positive guard convention (no domain
  error, since refactorable-ness is a total predicate over all integers
  under this convention, not restricted to positive ones the way
  `nth_*` scans are).
- `is_refactorable(true);` raises `CinderRuntimeError` matching
  `"is_refactorable\(\) requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `is_refactorable("8");` raises `CinderRuntimeError` matching
  `"is_refactorable\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_num_divisors`,
search `def _num_divisors`), `tests/test_builtins.py` (new `class
TestIsRefactorable`, modeled on `class TestIsHarshad`, search that
name, for the test shapes above). Once merged, `README.md`'s Builtins
bullet needs `is_refactorable` added near `num_divisors`/`is_harshad`,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

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
