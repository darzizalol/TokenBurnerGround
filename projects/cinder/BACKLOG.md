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

## 1. Standard library: `nth_semiprime` — the k-th semiprime by position

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

## 2. Standard library: `nth_pronic` — the k-th pronic number by position

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

## 3. Language: range case values in `switch` statements (`case 1..10: { ... }`)

Build: `match` expressions support range patterns (`match (5) { 1..10 =>
"small", _ => "large" }`, PR #318) via a dedicated containment check, but
`switch` never got the equivalent — and worse, writing one today doesn't
raise an error, it silently never matches. Verify the gap:
```sh
python3 -m cinder.cli eval 'switch (5) { case 1..10: { print("small"); } default: { print("other"); } }'
# -> other
```
`5` is inside `1..10`, so `"small"` should print, but `"other"` does
instead. The root cause: `case` values already parse through the normal
expression grammar (`_switch_statement`, `cinder/parser.py`, calls
`self._ternary()` for each value, which descends through `_range_expr`,
search `def _range_expr` — the same production `1..5` uses as an ordinary
expression), so `1..10` parses fine as a `RangeExpr` AST node with no
parser change needed. The bug is entirely in evaluation:
`_execute_switch` (`cinder/interpreter.py`, search `def _execute_switch`)
evaluates every case value with plain `self.evaluate(value_expr, env)`
and compares via `values_equal(scrutinee, ...)` — a `RangeExpr` evaluates
to a *materialized list* (via `_evaluate_range`, which calls the `_range`
builtin), so `case 1..10:` today means "case equals the list
`[1, 2, ..., 9]`", which can never equal a scalar scrutinee like `5`.

Fix `_execute_switch` to special-case a `RangeExpr`-typed case value,
mirroring how `_evaluate_match`'s own `range_pattern` branch already
handles this (search `if arm.range_pattern is not None`, uses
`_evaluate_range` + the shared `contains_value` helper rather than
`values_equal`):
```python
    def _execute_switch(self, stmt: SwitchStmt, env: Environment) -> None:
        scrutinee = self.evaluate(stmt.scrutinee, env)
        for case in stmt.cases:
            for value_expr in case.values:
                if isinstance(value_expr, RangeExpr):
                    values = self._evaluate_range(value_expr, env)
                    if contains_value(
                        values, scrutinee, value_expr.line, value_expr.column
                    ):
                        self.execute(case.body, env)
                        return
                elif values_equal(scrutinee, self.evaluate(value_expr, env)):
                    self.execute(case.body, env)
                    return
        if stmt.default is not None:
            self.execute(stmt.default, env)
```
`RangeExpr` and `contains_value` are both already imported/defined in
`cinder/interpreter.py` (search each name to confirm) — no new imports
needed. A range value composes for free with the existing multi-value
`case 1, 2, 3:` syntax, since each entry in `case.values` is checked
independently; a case can freely mix range and non-range values (e.g.
`case 1..5, 100:`).

Acceptance criteria:
- `switch (5) { case 1..10: { print("small"); } default: { print("other"); } }`
  prints `small` (currently prints `other`, per the gap above).
- `switch (10) { case 1..10: { print("in"); } default: { print("out"); } }`
  prints `out` — `..` is exclusive of the end by default, matching every
  other range in the language (e.g. `for (i in 1..3)` visits `1, 2`).
- `switch (10) { case 1..=10: { print("in"); } default: { print("out"); } }`
  prints `in` — `..=` is inclusive, matching the match-pattern range
  syntax exactly.
- `switch (5) { case 100..200: { print("no"); } case 1..10: { print("yes"); } default: { print("neither"); } }`
  prints `yes` — case order still short-circuits on first match, range
  cases included.
- `switch (5) { case 1..3, 5: { print("hit"); } default: { print("miss"); } }`
  prints `hit` — a range value composes with plain values in the same
  multi-value `case`.
- `switch ("x") { case 1..10: { print("no"); } default: { print("ok"); } }`
  prints `ok` — a non-numeric scrutinee against a range case falls
  through to default rather than raising (mirrors `contains_value`'s
  existing list-membership semantics: `"x" in [1, 2, ..., 9]` is simply
  `false`, not an error).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_execute_switch`, search `def
_execute_switch`), `tests/test_interpreter.py` (extend `class
TestSwitchStatement`, search that name, with the range-case cases
above). No parser or `cinder/ast_nodes.py` change needed — `SwitchCase.values`
already holds arbitrary `Expr` nodes, `RangeExpr` included. Once merged,
`README.md`'s `switch` statement bullet needs a mention of range case
values, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" bullet needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `nth_abundant` — the k-th abundant number by position

Build: `is_abundant` (`cinder/builtins.py`, search `def _is_abundant`)
tests membership via a proper-divisor-sum comparison, but has no
value-returning `nth_*` counterpart the way the prime and figurate-number
clusters do (`nth_prime`/`is_prime`, `nth_pronic`/`is_pronic`, etc.) —
abundant numbers have no closed form, so this follows `nth_prime`'s own
shape (search `def _nth_prime`): a sequential candidate scan with a
`count`/`candidate` loop, not an inverse formula. `is_abundant`'s two
siblings in the divisor-sum cluster, `is_deficient` and
`is_perfect_number`, are deliberately skipped for this same treatment:
deficient numbers are the vast majority of integers (a `nth_deficient`
scan would be a trivial "returns roughly k+3", not an interesting
builtin), and perfect numbers are astronomically sparse (the 5th is
33,550,336), which breaks the cross-check-up-to-k=50 acceptance-criteria
convention every other `nth_*` builtin in this file uses. Abundant
numbers are dense enough (12, 18, 20, 24, 30, ...) to scan quickly while
still being a well-known classic (OEIS A005101). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_abundant(5));'
# -> <eval>:1:7: undefined name 'nth_abundant'
```

Add to `cinder/builtins.py`, registered directly after `_is_abundant`
(search `def _is_abundant`, immediately before `def _is_deficient`) —
keeps the divisor-sum cluster together, mirroring how `is_catalan` sits
directly after `nth_catalan`:
```python
def _nth_abundant(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_abundant", arguments, 1, line, column)
    value = _require_int("nth_abundant", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_abundant() requires a positive integer, domain error", line, column
        )

    def _is_abundant_candidate(candidate: int) -> bool:
        total = 1 if candidate > 1 else 0
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                total += divisor
                complement = candidate // divisor
                if complement != divisor:
                    total += complement
        return total > candidate

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_abundant_candidate(candidate):
            count += 1
    return candidate
```
This mirrors `_nth_prime`'s/`_nth_happy_number`'s own `count`/`candidate`
scanning loop exactly, just swapping in `_is_abundant`'s own
divisor-sum logic as a local nested helper (reimplemented locally,
matching how `is_twin_prime`/`nth_happy_number` reimplement their
predicate locally rather than sharing a module-level helper — this
file's existing convention for small local predicates). Also register
the new dict entry (search `"is_abundant": _is_abundant,`, add
`"nth_abundant": _nth_abundant,` directly after it, before
`"is_deficient": _is_deficient,`).

Acceptance criteria:
- `nth_abundant(1);` through `nth_abundant(10);` are `12`, `18`, `20`,
  `24`, `30`, `36`, `40`, `42`, `48`, `54` — the first ten abundant
  numbers by position.
- `nth_abundant(20);` is `90`.
- `nth_abundant(50);` is `216`.
- `is_abundant(nth_abundant(k));` is `true` for every `k` from `1` to
  `50` — cross-check against the existing `is_abundant` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own
  shape.
- `nth_abundant(0);` and `nth_abundant(-1);` raise `CinderRuntimeError`
  matching `"nth_abundant() requires a positive integer, domain error"`.
- `nth_abundant(1.5);` raises `CinderRuntimeError` matching
  `"nth_abundant() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_abundant`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthPrime`, search that name, for the
positive/domain/type-error/cross-check test shapes, and the existing
`is_abundant` test class for the divisor-sum behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_abundant` added near
`is_abundant`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 5. Standard library: `nth_repdigit` — the k-th repdigit by position

Build: `is_repdigit` (`cinder/builtins.py`, search `def _is_repdigit`)
tests membership via `len(set(str(value))) == 1` (every decimal digit the
same — this also makes every single-digit non-negative integer `0`-`9`
trivially a repdigit), but has no value-returning `nth_*` counterpart.
Repdigits have no useful closed form (a d-digit repdigit is `digit *
(10**d - 1) // 9`, but neither `d` nor `digit` is a direct function of
the 1-indexed position), so this follows `nth_prime`'s/`nth_semiprime`'s
own shape (search `def _nth_prime`): a sequential candidate scan with a
`count`/`candidate` loop. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_repdigit(5));'
# -> <eval>:1:7: undefined name 'nth_repdigit'
```

**Performance note:** repdigits are far sparser than semiprimes/abundant
numbers — only 9 exist at each digit-length (`1`-`9`, `11`-`99`,
`111`-`999`, ...), so the candidate scan's cost grows exponentially with
position, not linearly. `nth_repdigit(50)` lands at `555555` (well within
a fast scan), but do not extend any acceptance criterion or test past
`k = 50` — e.g. `nth_repdigit(100)` needs a 12-digit candidate and a scan
past `10**11`, which does not finish in any reasonable test time. This
mirrors why the `nth_abundant` task (above) deliberately excluded
`nth_deficient`/`nth_perfect_number` from this same treatment — stay
inside the range where the established up-to-`k=50` cross-check
convention is actually cheap to run.

Add to `cinder/builtins.py`, registered directly after `_is_repdigit`
(search `def _is_repdigit`, immediately before `def _is_undulating`) —
keeps the repdigit pair together, mirroring how `is_catalan` sits
directly after `nth_catalan`:
```python
def _nth_repdigit(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_repdigit", arguments, 1, line, column)
    value = _require_int("nth_repdigit", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_repdigit() requires a positive integer, domain error", line, column
        )

    def _is_repdigit_candidate(candidate: int) -> bool:
        return len(set(str(candidate))) == 1

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_repdigit_candidate(candidate):
            count += 1
    return candidate
```
This mirrors `_nth_semiprime`'s/`_nth_abundant`'s own `count`/`candidate`
scanning loop exactly, just swapping in `_is_repdigit`'s own
single-distinct-digit check as a local nested helper (reimplemented
locally, matching how `is_twin_prime`/`nth_happy_number` reimplement
their predicate locally rather than sharing a module-level helper — this
file's existing convention for small local predicates). Also register
the new dict entry (search `"is_repdigit": _is_repdigit,`, add
`"nth_repdigit": _nth_repdigit,` directly after it, before
`"is_undulating": _is_undulating,`).

Acceptance criteria:
- `nth_repdigit(1);` through `nth_repdigit(10);` are `1`, `2`, `3`, `4`,
  `5`, `6`, `7`, `8`, `9`, `11` — the nine single digits count as
  one-digit repdigits before the two-digit repdigits begin.
- `nth_repdigit(18);` is `99`, `nth_repdigit(19);` is `111`,
  `nth_repdigit(20);` is `222` — the two-digit group (positions 10-18)
  gives way to the three-digit group at position 19.
- `nth_repdigit(30);` is `3333`, `nth_repdigit(40);` is `44444`.
- `nth_repdigit(50);` is `555555`.
- `is_repdigit(nth_repdigit(k));` is `true` for every `k` from `1` to
  `50` — cross-check against the existing `is_repdigit` builtin directly,
  mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own shape.
  Do not raise this bound past `50` (see the performance note above).
- `nth_repdigit(0);` and `nth_repdigit(-1);` raise `CinderRuntimeError`
  matching `"nth_repdigit() requires a positive integer, domain error"`.
- `nth_repdigit(1.5);` raises `CinderRuntimeError` matching
  `"nth_repdigit() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_repdigit`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthOctagonal`, search that name, for the
positive/domain/type-error/cross-check test shapes, and `class
TestIsRepdigit` for the single-distinct-digit behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_repdigit` added near
`is_repdigit`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

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
