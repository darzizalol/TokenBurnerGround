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

## 1. Standard library: `is_twin_prime` — membership test for primes with a twin partner [claimed 2026-08-29T14:57:47Z]

Build: the prime-relationship cluster in `cinder/builtins.py` already
covers several adjacency/structure predicates built on trial-division
primality (`is_semiprime`, `is_sphenic`, `is_emirp`, `is_circular_prime`),
but none test the classic "twin prime" relationship — whether a prime `p`
has another prime exactly 2 away (`p - 2` or `p + 2`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_twin_prime(5));'
# -> <eval>:1:7: undefined name 'is_twin_prime'
```

`is_twin_prime(n)` is `true` when `n` itself is prime and at least one of
`n - 2`/`n + 2` is also prime (covers both "lower twin", e.g. `3` paired
with `5`, and "upper twin", e.g. `5` paired with `3` or `7` paired with
`5`). Add to `cinder/builtins.py`, registered directly after
`_is_circular_prime` (search `def _is_circular_prime`, immediately before
`def _is_power_of_two`), following `_is_circular_prime`'s own shape of a
local nested trial-division helper rather than a shared module-level one
(matching this file's existing convention — each prime-relationship
predicate reimplements trial division inline):
```python
def _is_twin_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("is_twin_prime", arguments, 1, line, column)
    value = _require_int("is_twin_prime", arguments[0], line, column)
    if value < 2:
        return False

    def _trial_division_is_prime(candidate: int) -> bool:
        if candidate < 2:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return False
        return True

    if not _trial_division_is_prime(value):
        return False
    return _trial_division_is_prime(value - 2) or _trial_division_is_prime(value + 2)
```
Also register the new dict entry (search `"is_circular_prime":
_is_circular_prime,`, add `"is_twin_prime": _is_twin_prime,` directly
after it).

Acceptance criteria:
- `is_twin_prime(3);`, `is_twin_prime(5);`, `is_twin_prime(7);`,
  `is_twin_prime(11);`, `is_twin_prime(13);` are all `true` — each has a
  prime partner exactly 2 away (`3`/`5`, `5`/`3` or `5`/`7`, `7`/`5`,
  `11`/`13`, `13`/`11`).
- `is_twin_prime(2);` is `false` — prime, but neither `0` nor `4` is
  prime.
- `is_twin_prime(23);` is `false` — prime, but neither `21` nor `25` is
  prime.
- `is_twin_prime(9);`, `is_twin_prime(0);`, `is_twin_prime(1);`,
  `is_twin_prime(-5);` are all `false` — not prime to begin with (domain-
  open, matching `is_semiprime`/`is_circular_prime`'s own `value < 2`
  early-`False` convention, no raising on out-of-range input).
- `is_twin_prime(k);` matches a direct trial-division cross-check
  (`is_prime(k) and (is_prime(k - 2) or is_prime(k + 2))`) for every `k`
  from `0` to `200`.
- `is_twin_prime(5.0);` raises `CinderRuntimeError` matching
  `"is_twin_prime() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_circular_prime`,
search for the current line number), `tests/test_builtins.py` (model on
`class TestIsCircularPrime`, search that name, for the domain, type-
error, and cross-check test shapes). Once merged, `README.md`'s Builtins
bullet needs `is_twin_prime` added near `is_circular_prime`, its "Status
& roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Standard library: `nth_nonagonal` — the k-th nonagonal number by position

Build: `is_nonagonal` (PR #334) just closed the triangular..nonagonal
`is_*` cluster, but it left a new, smaller gap behind it —
`nth_triangular` through `nth_octagonal` all have a matching `nth_*`
closed-form sibling (`nth_pentagonal`/`nth_hexagonal`/`nth_heptagonal`/
`nth_octagonal`), and `nth_catalan`/`is_catalan` established the same
`nth_*`-needs-`is_*`-and-vice-versa convention for a different cluster,
but nonagonal is the one figurate shape with an `is_*` predicate and no
`nth_*` value-returning counterpart. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_nonagonal(5));'
# -> <eval>:1:7: undefined name 'nth_nonagonal'
```

Nonagonal numbers follow the same closed form as their pentagonal/
hexagonal/heptagonal/octagonal siblings, `N(k) = k(7k - 5)/2` — this is
exactly the formula `_is_nonagonal`'s own membership check already
verifies against (search `def _is_nonagonal`, `cinder/builtins.py`:
`candidate = 56 * value + 25`, `root = math.isqrt(candidate)`,
`root * root == candidate and (root + 5) % 14 == 0`, which is the
perfect-square/modular-residue test derived from solving `N(k) = n` for
`k`). Add to `cinder/builtins.py`, registered directly after
`_nth_octagonal` (search `def _nth_octagonal`, immediately before
`def _is_prime`), mirroring `_nth_octagonal`'s own shape exactly:
```python
def _nth_nonagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_nonagonal", arguments, 1, line, column)
    value = _require_int("nth_nonagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_nonagonal() requires a positive integer, domain error", line, column
        )
    return value * (7 * value - 5) // 2
```
Also register the new dict entry (search `"nth_octagonal":
_nth_octagonal,`, add `"nth_nonagonal": _nth_nonagonal,` directly after
it, before `"is_prime": _is_prime,`).

Acceptance criteria:
- `nth_nonagonal(1);`, `nth_nonagonal(2);`, `nth_nonagonal(3);`,
  `nth_nonagonal(4);` are `1`, `9`, `24`, `46` — the first four nonagonal
  numbers.
- `nth_nonagonal(10);` is `325`.
- `nth_nonagonal(100);` is `34750` (`100 * (700 - 5) / 2`).
- `is_nonagonal(nth_nonagonal(k));` is `true` for every `k` from `1` to
  `100` — cross-check against the existing `is_nonagonal` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own
  shape.
- `nth_nonagonal(0);` and `nth_nonagonal(-1);` raise `CinderRuntimeError`
  matching `"nth_nonagonal() requires a positive integer, domain error"`.
- `nth_nonagonal(1.5);` raises `CinderRuntimeError` matching
  `"nth_nonagonal() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`nth_octagonal`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthOctagonal`, search that name, for the
positive/domain/type-error/cross-check test shapes). Once merged,
`README.md`'s Builtins bullet needs `nth_nonagonal` added near
`is_nonagonal`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_happy_number` — the k-th happy number by position

Build: `is_happy_number`/`is_sad_number` (`cinder/builtins.py`) test
membership via the digit-square-sum cycle, but neither has a
value-returning `nth_*` counterpart the way the figurate-number and prime
clusters do (`nth_prime`/`is_prime`, `nth_triangular`/`is_triangular`,
etc.) — happy numbers have no closed form, so this follows `nth_prime`'s
own shape (search `def _nth_prime`): a sequential candidate scan with a
`count`/`candidate` loop, not an inverse formula. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_happy_number(5));'
# -> <eval>:1:7: undefined name 'nth_happy_number'
```

Add to `cinder/builtins.py`, registered directly after `_is_sad_number`
(search `def _is_sad_number`, immediately before `def _collatz_length`)
— keeps the happy/sad-number cluster together, mirroring how
`is_catalan` sits directly after `nth_catalan`:
```python
def _nth_happy_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_happy_number", arguments, 1, line, column)
    value = _require_int("nth_happy_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_happy_number() requires a positive integer, domain error", line, column
        )

    def _is_happy(candidate: int) -> bool:
        seen = set()
        while candidate != 1:
            if candidate in seen:
                return False
            seen.add(candidate)
            candidate = sum(int(digit) ** 2 for digit in str(candidate))
        return True

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_happy(candidate):
            count += 1
    return candidate
```
This mirrors `_nth_prime`'s own `count`/`candidate` scanning loop exactly,
just swapping the primality check for `_is_happy_number`'s cycle-detection
logic (reimplemented locally as a nested helper, matching how
`is_twin_prime`/`is_circular_prime` reimplement trial division locally
rather than sharing a module-level helper — this file's existing
convention for small local predicates). Also register the new dict entry
(search `"is_sad_number": _is_sad_number,`, add `"nth_happy_number":
_nth_happy_number,` directly after it, before `"collatz_length":
_collatz_length,`).

Acceptance criteria:
- `nth_happy_number(1);`, `nth_happy_number(2);`, `nth_happy_number(3);`,
  `nth_happy_number(4);`, `nth_happy_number(5);` are `1`, `7`, `10`, `13`,
  `19` — the first five happy numbers by position.
- `nth_happy_number(10);` is `44`.
- `nth_happy_number(20);` is `100`.
- `is_happy_number(nth_happy_number(k));` is `true` for every `k` from `1`
  to `20` — cross-check against the existing `is_happy_number` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own
  shape.
- `nth_happy_number(0);` and `nth_happy_number(-1);` raise
  `CinderRuntimeError` matching `"nth_happy_number() requires a positive
  integer, domain error"`.
- `nth_happy_number(1.5);` raises `CinderRuntimeError` matching
  `"nth_happy_number() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_sad_number`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthPrime`, search that name, for the
positive/domain/type-error/cross-check test shapes, and `class
TestIsHappyNumber` for the happy-number cycle behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_happy_number` added near
`is_happy_number`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 4. Language: default values in match map patterns (`{a, b = 0} => ...`)

Build: match list patterns already support trailing defaults via `[a, b
= 0] => ...` (PR #338, already merged — its task explicitly flagged map-
pattern defaults as "a separate, not-yet-queued task"), and `let` map
destructuring has supported per-key defaults for a long time (`let {a, b
= 5} = expr;`, PR #244) — a map missing a key still binds successfully,
falling back to the default. Match map patterns never got the
equivalent: today a subject map missing a pattern's key just falls
through the arm entirely, with no way to supply a fallback value.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1}) { {a, b = 0} => a + b, _ => -1 });'
# -> <eval>:1:31: expected '}' after map pattern, found '='
```

**Ordering note:** this task builds on rest capture (PR #335, already
landed) — it widens the same `_match_map_pattern_entry`/`_match_map_pattern`
production and the same interpreter `map_pattern` match branch rest
capture touches (`arm.map_rest` handling).
Unlike list-pattern defaults (PR #338), this task does **not** need to check
whether all pattern keys are present up front the way list patterns check
length — map patterns already match on a key subset (extra keys in the
subject beyond the pattern are always fine, no rest needed), so adding
defaults only relaxes which keys are *required*.

**Scope note:** only a bare identifier or renamed binding (`a` or `a: x`)
may carry a default — mirroring list-pattern defaults' (PR #338)
"flat-capability-first" scope
restriction exactly. Nested patterns as map-pattern values have already
landed (PR #337) — a nested `{...}`/`[...]` binding carrying a default
stays out of scope; only add the `= expr` check in the plain-identifier
branch of `_match_map_pattern_entry`, not after a recursive
nested-pattern call.

Widen `_match_map_pattern_entry` (`cinder/parser.py`, search `def
_match_map_pattern_entry`) to return a third element, mirroring
`_destructure_map_pattern_entry`'s own trailing `default` return:
```python
    def _match_map_pattern_entry(self) -> "tuple[str, str, Expr | None]":
        key = self._consume(
            TokenType.IDENTIFIER, "identifier inside map pattern"
        ).lexeme
        if self._check(TokenType.COLON):
            self._advance()
            binding = self._consume(
                TokenType.IDENTIFIER, "identifier after ':' in map pattern"
            ).lexeme
        else:
            binding = key
        default = None
        if self._check(TokenType.EQ):
            self._advance()
            default = self._ternary()
        return key, binding, default
```
`_match_map_pattern`'s entries list is now `list[tuple[str, str, Expr |
None]]`; no other change needed there since map-pattern entries have no
ordering constraint the way list-pattern defaults do (a required key can
follow a defaulted one with no ambiguity — each entry is looked up by
name, not position).

In `cinder/interpreter.py`, widen the `map_pattern` branch (search `if
arm.map_pattern is not None`) to unpack the 3-tuple and evaluate a
default when a key is missing, mirroring `_bind_map_destructure`'s own
`key in value` / `default is not None` check:
```python
            if arm.map_pattern is not None:
                if not isinstance(subject, dict) or not all(
                    key in subject or default is not None
                    for key, _, default in arm.map_pattern
                ):
                    continue
                arm_env = Environment(env)
                seen_keys = set()
                for key, binding, default in arm.map_pattern:
                    item = subject[key] if key in subject else self.evaluate(default, arm_env)
                    arm_env.define(binding, item)
                    seen_keys.add(key)
                if arm.map_rest is not None and arm.map_rest != "_":
                    arm_env.define(
                        arm.map_rest,
                        {k: v for k, v in subject.items() if k not in seen_keys},
                    )
                return self.evaluate(arm.body, arm_env)
```
Default expressions are evaluated in `arm_env`, left-to-right in
`arm.map_pattern` order, so an earlier binding in the same pattern is
visible to a later default — mirroring `_bind_map_destructure`'s own
progressive-`env` evaluation and list-pattern defaults' (PR #338)
identical left-to-right convention.

Acceptance criteria:
- `match ({"a": 1}) { {a, b = 0} => a + b, _ => -1 };` is `1` — the
  default fires when the subject is missing the key.
- `match ({"a": 1, "b": 2}) { {a, b = 0} => a + b, _ => -1 };` is `3` —
  the default is not used when the subject supplies the key.
- `match ({}) { {a = 1, b = 2} => a + b, _ => -1 };` is `3` — multiple
  defaults, subject missing every key.
- `match ({"a": 1}) { {a, b = a + 1} => b, _ => -1 };` is `2` — a default
  expression may reference an earlier binding in the same pattern.
- `match ({"b": 2}) { {a: x = 0, b} => x + b, _ => -1 };` is `2` — a
  default composes with per-key rename (PR #332) in the same pattern.
- `match ({"a": 1, "c": 3}) { {a, b = 0, ...rest} => [a, b, rest], _ =>
  "no" };` is `[1, 0, {"c": 3}]` — a default composes with rest capture
  (PR #335) in the same pattern; the missing, defaulted key `b` is not
  spuriously included in `rest`.
- `match ({}) { {a} => a, _ => "no" };` is `"no"` — a key without a
  default is still required; missing it still falls through, unaffected
  by this task.
- `match ([1]) { {a = 1} => a, _ => "no" };` is `"no"` — a non-map
  subject still falls through, defaults included.
- `shape(parse('match (x) { {a, b = 0} => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `map_pattern` with `b`'s
  entry as a `(key, binding, default_expr)` triple rather than a
  `(key, binding)` pair.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_map_pattern_entry`),
`cinder/ast_nodes.py` (`MatchArm.map_pattern` docstring, widened for the
new 3-tuple entry shape), `cinder/interpreter.py` (`_evaluate_match`'s
`map_pattern` branch), `tests/test_parser.py` (extend the map-pattern
shape tests, search `test_match_map_pattern_shape`),
`tests/test_interpreter.py` (extend `class TestMatchExpression`, search
`test_map_pattern_binds_named_keys`, with the default cases above). Once
merged, `README.md`'s `match` expression bullet needs its map-pattern
description widened to mention defaults, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Standard library: `nth_semiprime` — the k-th semiprime by position

Build: `is_semiprime` (`cinder/builtins.py`) tests membership via a
factor-count trial division, but has no value-returning `nth_*`
counterpart the way `nth_catalan`/`is_catalan` and the figurate-number
clusters do — semiprimes have no closed form, so this follows
`nth_prime`'s/`nth_happy_number`'s own shape (search `def _nth_prime`): a
sequential candidate scan with a `count`/`candidate` loop, not an inverse
formula. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_semiprime(5));'
# -> <eval>:1:7: undefined name 'nth_semiprime'
```

Add to `cinder/builtins.py`, registered directly after `_is_semiprime`
(search `def _is_semiprime`, immediately before `def _is_sphenic`) —
keeps the semiprime pair together, mirroring how `is_catalan` sits
directly after `nth_catalan`:
```python
def _nth_semiprime(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_semiprime", arguments, 1, line, column)
    value = _require_int("nth_semiprime", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_semiprime() requires a positive integer, domain error", line, column
        )

    def _is_semiprime_candidate(candidate: int) -> bool:
        remaining = candidate
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

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_semiprime_candidate(candidate):
            count += 1
    return candidate
```
This mirrors `_nth_prime`'s/`_nth_happy_number`'s own `count`/`candidate`
scanning loop exactly, just swapping in `_is_semiprime`'s own factor-count
logic as a local nested helper (reimplemented locally, matching how
`is_twin_prime`/`nth_happy_number` reimplement their predicate locally
rather than sharing a module-level helper — this file's existing
convention for small local predicates). Also register the new dict entry
(search `"is_semiprime": _is_semiprime,`, add `"nth_semiprime":
_nth_semiprime,` directly after it, before `"is_sphenic": _is_sphenic,`).

Acceptance criteria:
- `nth_semiprime(1);` through `nth_semiprime(6);` are `4`, `6`, `9`, `10`,
  `14`, `15` — the first six semiprimes by position.
- `nth_semiprime(20);` is `57`.
- `nth_semiprime(50);` is `146`.
- `is_semiprime(nth_semiprime(k));` is `true` for every `k` from `1` to
  `50` — cross-check against the existing `is_semiprime` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own
  shape.
- `nth_semiprime(0);` and `nth_semiprime(-1);` raise `CinderRuntimeError`
  matching `"nth_semiprime() requires a positive integer, domain error"`.
- `nth_semiprime(1.5);` raises `CinderRuntimeError` matching
  `"nth_semiprime() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_semiprime`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthPrime`, search that name, for the
positive/domain/type-error/cross-check test shapes, and `class
TestIsSemiprime` for the semiprime factor-count behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_semiprime` added near
`is_semiprime`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 6. Standard library: `nth_pronic` — the k-th pronic number by position

Build: `is_pronic` (`cinder/builtins.py`) tests membership via a
perfect-square-adjacent check, but has no value-returning `nth_*`
counterpart the way `nth_octagonal`/`is_octagonal` and the other
closed-form clusters do. Pronic numbers (also called oblong or
heteromecic numbers) do have a simple closed form, so this follows
`nth_octagonal`'s shape (search `def _nth_octagonal`) rather than a
sequential scan. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_pronic(5));'
# -> <eval>:1:7: undefined name 'nth_pronic'
```

Pronic numbers follow `N(k) = k * (k + 1)` — this is exactly the
relationship `_is_pronic`'s own membership check already verifies
against (search `def _is_pronic`, `cinder/builtins.py`:
`root = math.isqrt(value)`, `root * (root + 1) == value`). Add to
`cinder/builtins.py`, registered directly after `_is_pronic` (search
`def _is_pronic`, immediately before `def _is_squarefree`), mirroring
`_nth_octagonal`'s own one-line shape:
```python
def _nth_pronic(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_pronic", arguments, 1, line, column)
    value = _require_int("nth_pronic", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_pronic() requires a positive integer, domain error", line, column
        )
    return value * (value + 1)
```
Also register the new dict entry (search `"is_pronic": _is_pronic,`, add
`"nth_pronic": _nth_pronic,` directly after it, before `"is_squarefree":
_is_squarefree,`).

Note: this convention starts at `k = 1` giving `2` (skipping the trivial
`k = 0` case, `0 * 1 = 0`), the same way `nth_triangular(1)` is `1` and
skips `T(0) = 0` even though `is_triangular(0)` is also `true` — matching
every other figurate `nth_*`/`is_*` pair in this file.

Acceptance criteria:
- `nth_pronic(1);`, `nth_pronic(2);`, `nth_pronic(3);`, `nth_pronic(4);`
  are `2`, `6`, `12`, `20` — the first four positive pronic numbers.
- `nth_pronic(10);` is `110` (`10 * 11`).
- `nth_pronic(100);` is `10100` (`100 * 101`).
- `is_pronic(nth_pronic(k));` is `true` for every `k` from `1` to `100`
  — cross-check against the existing `is_pronic` builtin directly,
  mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own shape.
- `nth_pronic(0);` and `nth_pronic(-1);` raise `CinderRuntimeError`
  matching `"nth_pronic() requires a positive integer, domain error"`.
- `nth_pronic(1.5);` raises `CinderRuntimeError` matching
  `"nth_pronic() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after `is_pronic`,
search for the current line number), `tests/test_builtins.py` (model on
`class TestNthOctagonal`, search that name, for the
positive/domain/type-error/cross-check test shapes, and `class
TestIsPronic` for the pronic-number membership behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_pronic` added near `is_pronic`,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" bullet needs refreshing — leave both to the
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
