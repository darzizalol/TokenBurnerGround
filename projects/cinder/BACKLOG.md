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

## 1. Standard library: `is_harshad` — digit-sum divisibility predicate

Build: add `is_harshad(n)` to `cinder/builtins.py`, registered right
after `is_automorphic` (search for `def _is_automorphic`, the current
last entry in the integer-property cluster) — the breadth task after
extended slice assignment for lists' depth work (landed via PR #237) per
`PROJECT.md`'s breadth-vs-depth policy. A positive integer `n` is a
Harshad (or Niven) number when it is evenly divisible by the sum of
its own decimal digits, e.g. `18` is Harshad since `1 + 8 = 9` and `18
% 9 == 0`; `19` is not, since `1 + 9 = 10` and `19 % 10 != 0`. It joins
the `is_perfect_square`/`is_armstrong`/`is_leap_year`/
`is_perfect_number`/`is_abundant`/`is_deficient`/`is_automorphic`
integer-property cluster as one more digit-based classification.

Compute the digit sum inline with the same plain walk `digit_sum`
already uses internally — `sum(int(digit) for digit in
str(abs(value)))` (search for `def _digit_sum` to copy its exact
expression) — rather than calling the `digit_sum` builtin's own
`(arguments, line, column)` wrapper, since that wrapper expects a
Cinder argument list, not a bare Python int:

```python
def _is_harshad(arguments: list, line: int, column: int) -> object:
    _require_arity("is_harshad", arguments, 1, line, column)
    value = _require_int("is_harshad", arguments[0], line, column)
    if value < 1:
        return False
    digit_total = sum(int(digit) for digit in str(value))
    return value % digit_total == 0
```

Model the arity/type-checking exactly on `_is_automorphic`'s structure:
`_require_arity("is_harshad", arguments, 1, line, column)`, then
`value = _require_int("is_harshad", arguments[0], line, column)`
(reusing the shared `_require_int` helper — do **not** hand-roll a
separate `isinstance` check). The `value < 1` guard matches
`is_abundant`/`is_deficient`'s own convention of answering `false` on
zero and negative input rather than raising a domain error — it also
sidesteps a `ZeroDivisionError` that a bare digit-sum-of-zero would
otherwise cause, since `digit_total` is only ever `0` when `value` is
`0`, which this guard already excludes before the division runs.

Acceptance criteria:
- `is_harshad(18);` is `true` — `1 + 8 = 9`, `18 % 9 == 0`.
- `is_harshad(19);` is `false` — `1 + 9 = 10`, `19 % 10 != 0`.
- `is_harshad(1);` is `true` — every single nonzero digit divides
  itself.
- `is_harshad(12);` is `true` — `1 + 2 = 3`, `12 % 3 == 0`.
- `is_harshad(11);` is `false` — `1 + 1 = 2`, `11 % 2 != 0`.
- `is_harshad(100);` is `true` — `1 + 0 + 0 = 1`, `100 % 1 == 0`
  (every integer is divisible by `1`).
- `is_harshad(0);` is `false` — excluded by the `value < 1` guard
  rather than raising a division-by-zero error.
- `is_harshad(-18);` is `false` — negative input answers `false`
  without raising, matching `is_abundant`/`is_deficient`'s convention.
- `is_harshad(5.0);` raises `CinderRuntimeError` matching
  `"is_harshad() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `is_harshad(true);` raises `CinderRuntimeError` matching
  `"is_harshad() requires an int, got bool"` — `_require_int` already
  excludes `bool` from passing as an int.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_deficient`/`is_automorphic`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_harshad` added near
`is_perfect_number`/`is_abundant`/`is_deficient`/`is_automorphic`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 2. Language: map-destructuring key rename (`let {a: x, b} = expr;`)

Build: the depth task after task 1's breadth work (`is_harshad`) per
`PROJECT.md`'s breadth-vs-depth policy. Every map-destructuring form —
`let {a, b} = expr;`, plain assignment `{a, b} = expr;`, `for {a, b} in
list_of_maps { ... }`, function params `fn f({a, b}) { ... }`, and both
comprehension loop-variable forms — currently binds each name to a
variable of the *same* name as the map key it reads (`{a, b}` always
declares `a` and `b`). There is no way to bind under a different local
name, unlike JS destructuring's `const {a: x} = obj`. Verify the gap:
`python3 -m cinder.cli eval 'let {a: x} = {"a": 1}; print(x);'` currently
raises `ParseError` `"'}' after destructuring pattern"` (the parser sees
`IDENTIFIER COLON` where it only expects `IDENTIFIER COMMA`/`RBRACE`).

All five forms share two parser entry points and one interpreter entry
point, so the change is centralized rather than five separate edits:
`_destructure_map_pattern` (search for `def _destructure_map_pattern` in
`cinder/parser.py`) is called by `let`, `for`, params, and both
comprehensions; `_try_map_destructure_assign_statement` (search for that
name, same file) has its own inlined copy of the same identifier-list
loop for the plain-assignment form; both feed `names`/`rest` straight
into `_bind_map_destructure` (search for `def _bind_map_destructure` in
`cinder/interpreter.py`), the single place that actually reads keys out
of the map and binds variables. Changing what `names` holds and how
`_bind_map_destructure` consumes it is the whole feature — none of the
five call sites need their own changes.

Change `names` from a flat `list[str]` (map key doubles as binding name)
to a `list[tuple[str, str]]` of `(key, binding)` pairs, `binding`
defaulting to `key` when no rename is written. Add a shared parsing
helper right above `_destructure_map_pattern`:

```python
def _destructure_map_pattern_entry(self) -> "tuple[str, str]":
    key = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    if self._check(TokenType.COLON):
        self._advance()
        binding = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    else:
        binding = key
    return key, binding
```

In `_destructure_map_pattern`, replace both
`names.append(self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme)`
lines (the initial entry and the one inside the `while COMMA` loop) with
`names.append(self._destructure_map_pattern_entry())`. Do the same for
the two matching lines inside
`_try_map_destructure_assign_statement`'s own `try` block. Nothing else
in either function changes — the rest-element handling, the
rest-must-be-last check (`_RestNotLast` in the assignment form), and the
trailing `}`/`=` consumption are all untouched, since they operate on
`names` as an opaque list either way.

In `_bind_map_destructure`, unpack the pairs and use the *key* for the
map lookup and the *binding* for the environment write, and use a set of
keys (not the tuple list itself) to compute the rest element's leftover
keys:

```python
def _bind_map_destructure(
    self,
    env: Environment,
    names: list,
    rest: "str | None",
    value: object,
    line: int,
    column: int,
    use_assign: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise CinderRuntimeError(
            f"cannot destructure {type_name(value)} as a map",
            line,
            column,
        )
    seen_keys = set()
    for key, binding in names:
        seen_keys.add(key)
        if key not in value:
            raise CinderRuntimeError(
                f"destructuring pattern expects key {key!r}, not found in map",
                line,
                column,
            )
        self._bind_destructure_name(env, binding, value[key], line, column, use_assign)
    if rest is not None:
        remaining = {k: v for k, v in value.items() if k not in seen_keys}
        self._bind_destructure_name(env, rest, remaining, line, column, use_assign)
```

The error message keeps referencing the *key* (what's missing from the
map), not the binding name, since that's what a reader needs to fix.
`DestructureLetStmt`/`DestructureAssign`/`ForStmt`/`Param`/
`ListComprehension`/`MapComprehension` in `cinder/ast_nodes.py` need no
field changes — `names: list` already accepts either shape, and every
consumer of `.names` (grep confirms only `_bind_map_destructure` and
`_bind_list_destructure` read it, dispatched by each node's own `is_map`
flag) already routes map-mode data through the function above.

No rename support is added to *list*-pattern destructuring
(`let [a, b] = expr;`) — list patterns are purely positional, so
"rename" has no meaning there; this task only touches
`_destructure_map_pattern`/`_try_map_destructure_assign_statement`/
`_bind_map_destructure`.

Test-shape ripple: every existing `test_parser.py` assertion that checks
a map-destructure node's `.names` as a flat list of plain strings (e.g.
`["a", "b"]` for `{a, b} = ...;`) now needs updating to the pair form
(`[("a", "a"), ("b", "b")]`) — search `test_parser.py` for
`is_map=True` sites and the surrounding `DestructureLetStmt`/
`DestructureAssign` shape tuples that precede them; the `shape()`/
`stmt_shape()` helpers themselves need no changes since they just
forward whatever `.names` holds. This is a mechanical, no-behavior-change
update for every pre-existing plain-name test; only the *new* rename
tests exercise the actual feature.

Acceptance criteria:
- `let {a: x, b} = {"a": 1, "b": 2}; print(x); print(b);` prints `1`
  then `2` — `a`'s value binds to `x`, `b` binds to itself (no rename).
- `{a: x} = {"a": 5}; print(x);` (plain-assignment form, `x` already
  declared via `let x = 0;` beforehand) prints `5`.
- `for {a: x, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}] { print(x + b); }`
  prints `3` then `7`.
- `fn f({a: x}) { return x; } print(f({"a": 9}));` prints `9`.
- `print([x for {a: x} in [{"a": 1}, {"a": 2}]]);` prints `[1, 2]`.
- `let {a: x, ...rest} = {"a": 1, "b": 2, "c": 3}; print(x); print(rest);`
  prints `1` then `{"b": 2, "c": 3}` — the rest element still collects by
  *key*, unaffected by the earlier rename.
- `let {a: x} = {"b": 1};` raises `CinderRuntimeError` matching
  `"destructuring pattern expects key 'a', not found in map"` — the
  error names the source key, not the binding `x`.
- Plain, non-renamed patterns (`let {a, b} = expr;` and every other
  existing form) behave identically to before this task — this is purely
  additive syntax.
- `let {a: x, a: y} = {"a": 1};` (same key renamed twice) is not
  specially rejected — it parses and runs like any other repeated-name
  destructuring pattern already does today (last binding wins, no new
  validation added for this task).
- Full test suite passes, including the updated `.names` shape
  assertions described above.

Likely files: `cinder/parser.py` (new `_destructure_map_pattern_entry`,
both call sites), `cinder/interpreter.py` (`_bind_map_destructure`),
`tests/test_parser.py` (shape assertions plus new rename tests),
`tests/test_interpreter.py` (new rename tests for `let`/assignment/
`for`/params/comprehensions). Once merged, `README.md`'s destructuring
bullets need a rename mention added to each of the five forms, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_perfect_cube` — integer cube-root predicate

Build: the breadth task after task 2's depth work (map-destructuring key
rename) per `PROJECT.md`'s breadth-vs-depth policy. A positive, negative,
or zero integer `n` is a perfect cube when some integer `k` satisfies
`k ** 3 == n` (e.g. `27 = 3**3`, `-8 = (-2)**3`, `0 = 0**3`). It joins the
`is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`/
`is_abundant`/`is_deficient`/`is_automorphic`/`is_harshad`
integer-property cluster as one more digit/root-based classification —
register it right after `is_harshad` (search for `def _is_harshad`, the
current last entry in the cluster once task 1 lands).

Unlike `is_perfect_square` (which excludes negative input, since no real
square root of a negative number is an integer), cube roots of negative
numbers *are* real and integral — `-8`'s cube root is `-2` — so this
predicate must accept negative input rather than short-circuiting to
`false` the way `is_perfect_square` does. There is no `math.icbrt` in the
standard library (unlike `math.isqrt` for squares), and a floating-point
`round(n ** (1/3))` risks exactly the rounding-error problem
`math.isqrt` was chosen to avoid for squares — so compute an exact
integer cube root via binary search on the magnitude, then restore the
sign:

```python
def _integer_cube_root(magnitude: int) -> int:
    if magnitude == 0:
        return 0
    low, high = 0, magnitude
    while low < high:
        mid = (low + high + 1) // 2
        if mid ** 3 <= magnitude:
            low = mid
        else:
            high = mid - 1
    return low


def _is_perfect_cube(arguments: list, line: int, column: int) -> object:
    _require_arity("is_perfect_cube", arguments, 1, line, column)
    value = _require_int("is_perfect_cube", arguments[0], line, column)
    magnitude = abs(value)
    root = _integer_cube_root(magnitude)
    return root ** 3 == magnitude
```

`_integer_cube_root` operates on the non-negative magnitude only, so its
own result is always non-negative; the predicate doesn't need to
reconstruct the signed root at all, since cubing preserves sign
symmetry: `magnitude` is a perfect cube iff `abs(value)` is, for either
sign of `value`. Model the arity/type-checking exactly on
`_is_harshad`/`_is_perfect_square`'s structure: `_require_arity`, then
`_require_int` (reusing the shared helper — do **not** hand-roll a
separate `isinstance` check).

Acceptance criteria:
- `is_perfect_cube(27);` is `true` — `3 ** 3 == 27`.
- `is_perfect_cube(1);` is `true` — `1 ** 3 == 1`.
- `is_perfect_cube(0);` is `true` — `0 ** 3 == 0`.
- `is_perfect_cube(-8);` is `true` — `(-2) ** 3 == -8`, unlike
  `is_perfect_square`, negative input is not automatically `false`.
- `is_perfect_cube(-27);` is `true` — `(-3) ** 3 == -27`.
- `is_perfect_cube(8);` is `true` — `2 ** 3 == 8`.
- `is_perfect_cube(9);` is `false` — no integer cubes to `9`.
- `is_perfect_cube(-9);` is `false` — no integer cubes to `-9` either.
- `is_perfect_cube(1000000);` is `true` — `100 ** 3 == 1000000`, a case
  large enough that a naive `round(n ** (1/3))` float approach could
  plausibly drift off by one, proving the binary-search approach is
  exact.
- `is_perfect_cube(5.0);` raises `CinderRuntimeError` matching
  `"is_perfect_cube() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_perfect_cube(true);` raises `CinderRuntimeError` matching
  `"is_perfect_cube() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_harshad`/`is_perfect_square`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_perfect_cube` added near
`is_perfect_square`/`is_armstrong`/`is_automorphic`/`is_harshad`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `aliquot_sum` — sum of an integer's proper divisors

Build: a fresh breadth task after task 2's depth work (map-destructuring
key rename), added this grooming pass to keep the backlog stocked ahead
of tonight's pace. Add `aliquot_sum(n)` to `cinder/builtins.py`,
registered right after `divisors` (search for `def _divisors`) — the
number-returning sibling of `divisors`'s list-returning trial-division
walk, and the value-returning counterpart to the
`is_perfect_number`/`is_abundant`/`is_deficient` cluster, all four of
which already trial-divide to `sqrt(n)` and differ only in what they do
with the divisors found (sum-and-compare for the three predicates,
collect-and-sort for `divisors`, sum-and-return here). The proper
divisors of `n` are every positive divisor of `n` except `n` itself
(e.g. `6`'s proper divisors are `1, 2, 3`, summing to `6`; `n` is
perfect/abundant/deficient exactly when `aliquot_sum(n)` is equal
to/greater than/less than `n`, so this builtin makes that comparison
inspectable instead of only answerable as a boolean):

```python
def _aliquot_sum(arguments: list, line: int, column: int) -> object:
    _require_arity("aliquot_sum", arguments, 1, line, column)
    value = _require_int("aliquot_sum", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "aliquot_sum() requires a positive integer, domain error", line, column
        )
    if value == 1:
        return 0
    total = 1
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            total += divisor
            complement = value // divisor
            if complement != divisor:
                total += complement
    return total
```

Model the arity/type-checking and the domain-error-on-`n < 1` split
exactly on `divisors`'s own structure (search for `def _divisors`) —
not the predicate cluster's "answer `false` on out-of-domain input"
convention, since there is no sensible "aliquot sum of a non-positive
number" answer, matching `divisors`'s own reasoning for the same choice.
Note the loop starts `total` at `1` (since `1` always divides `value`
for `value > 1`) and special-cases `value == 1` to return `0` directly
(the loop's `range(2, math.isqrt(1) + 1)` is empty and `1`'s only
positive divisor is itself, which is excluded — a proper divisor sum of
`0`, not `1`), mirroring `is_perfect_number`/`is_abundant`/
`is_deficient`'s own `total = 1 if value > 1 else 0` guard against
double-counting `1` as its own proper divisor.

Acceptance criteria:
- `aliquot_sum(6);` is `6` — `1 + 2 + 3 = 6`, confirming `6` is perfect
  (matches `is_perfect_number(6)` being `true`).
- `aliquot_sum(12);` is `16` — `1 + 2 + 3 + 4 + 6 = 16`, confirming `12`
  is abundant (matches `is_abundant(12)` being `true`).
- `aliquot_sum(8);` is `7` — `1 + 2 + 4 = 7`, confirming `8` is
  deficient (matches `is_deficient(8)` being `true`).
- `aliquot_sum(1);` is `0` — `1` has no proper divisors other than
  itself, which is excluded.
- `aliquot_sum(2);` is `1` — every prime's proper-divisor sum is `1`.
- `aliquot_sum(28);` is `28` — `1 + 2 + 4 + 7 + 14 = 28`, the next
  perfect number after `6`.
- `aliquot_sum(0);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires a positive integer, domain error"` — same
  message shape `divisors()` already produces for the same input.
- `aliquot_sum(-6);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires a positive integer, domain error"`.
- `aliquot_sum(5.0);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `aliquot_sum(true);` raises `CinderRuntimeError` matching
  `"aliquot_sum() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`divisors`/`is_perfect_number`/`is_abundant`/`is_deficient`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `aliquot_sum` added near `divisors`/`is_perfect_number`/
`is_abundant`/`is_deficient`, and `PROJECT.md`'s roadmap paragraph needs
it moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
