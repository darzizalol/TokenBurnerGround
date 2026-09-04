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

## 1. Standard library: `nth_semiperfect` — semiperfect number found at a 1-indexed position [claimed 2026-09-04T15:57:46Z]

Build: `is_semiperfect` (`cinder/builtins.py`, search `def
_is_semiperfect`: proper-divisor list, then a bounded 0/1 subset-sum
sweep checking whether `value` itself is reachable) landed as PR #385 —
but, like `is_abundant`/`nth_abundant`, `is_deficient`/`nth_deficient`,
and `is_practical_number`/`nth_practical_number` before it, it has no
value-returning `nth_*` sibling yet. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_semiperfect(5));'
# -> <eval>:1:7: undefined name 'nth_semiperfect' (did you mean
#    'is_semiperfect'?)
```

Worked examples: the first ten semiperfect numbers (OEIS A005835) are `6,
12, 18, 20, 24, 28, 30, 36, 40, 42` — note `28` is perfect and so
trivially semiperfect via its own full divisor set, same as `6`; the
20th is `88`.

Add directly after `_is_semiperfect` (search `def _is_semiperfect`,
immediately before `def _is_automorphic`) — keeps the value-returning
helper next to the predicate it mirrors, matching where `nth_deficient`
itself sits right after `is_deficient`:
```python
def _nth_semiperfect(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_semiperfect", arguments, 1, line, column)
    value = _require_int("nth_semiperfect", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_semiperfect() requires a positive integer, domain error",
            line, column,
        )

    def _is_semiperfect_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
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
        return candidate in reachable

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_semiperfect_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`, with the inner candidate
check copied from `_is_semiperfect`'s own body instead of
`_is_practical_number`'s — semiperfect numbers have no closed form
either, so the same bounded sequential scan applies.) Also register the
new dict entry (search `"is_semiperfect": _is_semiperfect,`, add
`"nth_semiperfect": _nth_semiperfect,` directly after it, before
`"is_automorphic": _is_automorphic,`).

Acceptance criteria:
- `nth_semiperfect(1);` through `nth_semiperfect(10);` are `6, 12, 18,
  20, 24, 28, 30, 36, 40, 42` in order — the worked example above.
- `nth_semiperfect(20);` is `88` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`, `is_semiperfect(nth_semiperfect(position))`
  is `true` — the same self-consistency check `nth_practical_number`'s
  own test suite already runs against `is_practical_number`.
- `nth_semiperfect(0);`, `nth_semiperfect(-3);` both raise
  `CinderRuntimeError` matching `"nth_semiperfect\(\) requires a
  positive integer, domain error"`, matching `nth_practical_number`'s
  own non-positive-input convention.
- `nth_semiperfect(true);` raises `CinderRuntimeError` matching
  `"nth_semiperfect\(\) requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `nth_semiperfect("5");` raises `CinderRuntimeError` matching
  `"nth_semiperfect\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_semiperfect`,
search `def _is_semiperfect`), `tests/test_builtins.py` (new `class
TestNthSemiperfect`, modeled on `class TestNthPracticalNumber`, search
that name, for the test shapes above). Once merged, `README.md`'s
Builtins bullet needs `nth_semiperfect` added near
`is_semiperfect`/`nth_practical_number`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `is_decagonal`/`nth_decagonal` — 10-gonal number predicate and its value-returning sibling [claimed 2026-09-04T20:35:02Z]

Build: Cinder's polygonal-number family already covers triangular
(`is_triangular`/`nth_triangular`), pentagonal, hexagonal, heptagonal,
octagonal, and nonagonal (3- through 9-gonal, `cinder/builtins.py`,
search `def _is_nonagonal`/`def _nth_nonagonal`, the last pair in the
family) but stops one short of decagonal (10-gonal). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_decagonal(10));'
# -> <eval>:1:7: undefined name 'is_decagonal' (did you mean 'is_octagonal'?)
python3 -m cinder.cli eval 'print(nth_decagonal(5));'
# -> <eval>:1:7: undefined name 'nth_decagonal' (did you mean 'nth_octagonal'?)
```

Worked examples: the first ten decagonal numbers (OEIS A001107) are `1,
10, 27, 52, 85, 126, 175, 232, 297, 370` — the generalized polygonal
formula for `s` sides is `P(s, n) = ((s - 2) * n^2 - (s - 4) * n) / 2`,
which for `s = 10` simplifies to `P(10, n) = 4n^2 - 3n` (e.g. `n = 4`:
`4 * 16 - 12 = 52`, matching the fourth term above). Every other family
member already uses this same closed form (see `_nth_octagonal`'s
`value * (3 * value - 2)`, `_nth_nonagonal`'s
`value * (7 * value - 5) // 2`, both directly `P(s, n)` for their own
`s`), and every `is_*gonal` predicate already inverts it via the
quadratic formula, testing whether `8 * (s - 2) * x + (s - 4)^2` is a
perfect square whose root satisfies a fixed modular condition — for
`s = 10` that is `candidate = 16 * x + 9`, root must satisfy
`(3 + root) % 8 == 0` (worked by hand from the same derivation
`_is_octagonal`'s `3 * value + 1`/`(1 + root) % 3 == 0` and
`_is_nonagonal`'s `56 * value + 25`/`(root + 5) % 14 == 0` already use
for their own `s`).

Add both directly after `_is_nonagonal`/`_nth_nonagonal` respectively
(search `def _is_nonagonal`, immediately before `def _nth_triangular`;
and search `def _nth_nonagonal`, immediately before `def _is_prime`) —
keeps the new pair as the next member of the existing family, in the
same triangular-through-nonagonal order:
```python
def _is_decagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_decagonal", arguments, 1, line, column)
    value = _require_int("is_decagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 16 * value + 9
    root = math.isqrt(candidate)
    return root * root == candidate and (root + 3) % 8 == 0
```
```python
def _nth_decagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_decagonal", arguments, 1, line, column)
    value = _require_int("nth_decagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_decagonal() requires a positive integer, domain error", line, column
        )
    return value * (4 * value - 3)
```
Also register both new dict entries (search `"is_nonagonal":
_is_nonagonal,`, add `"is_decagonal": _is_decagonal,` directly after
it, before `"nth_triangular": _nth_triangular,`; search `"nth_nonagonal":
_nth_nonagonal,`, add `"nth_decagonal": _nth_decagonal,` directly after
it, before `"is_prime": _is_prime,`).

Acceptance criteria:
- `is_decagonal(1);`, `is_decagonal(10);`, `is_decagonal(27);`,
  `is_decagonal(52);`, `is_decagonal(85);` are all `true` — the worked
  examples above.
- `is_decagonal(0);`, `is_decagonal(2);`, `is_decagonal(11);` are all
  `false` — non-members between/around the worked examples.
- `is_decagonal(-1);` is `false` — negative input is false outright, no
  domain error, matching `is_nonagonal`'s own negative-input convention
  (this is a total predicate, not a `nth_*` scan).
- For every `k` in `1..100`, `is_decagonal(4 * k * k - 3 * k)` is `true`
  — the same direct-construction cross-check `is_nonagonal`'s own test
  suite runs (`k * (7 * k - 5) // 2` there), confirming the predicate
  accepts every value the formula actually produces.
- `nth_decagonal(1);` through `nth_decagonal(10);` are `1, 10, 27, 52,
  85, 126, 175, 232, 297, 370` in order — the worked example above.
- For every `position` in `1..50`, `is_decagonal(nth_decagonal(position))`
  is `true` — the same self-consistency check `nth_practical_number`'s
  test suite runs against `is_practical_number`.
- `nth_decagonal(0);`, `nth_decagonal(-3);` both raise
  `CinderRuntimeError` matching `"nth_decagonal\(\) requires a positive
  integer, domain error"`, matching `nth_triangular`'s own
  non-positive-input convention (every other `nth_*gonal` sibling raises
  rather than returning a sentinel).
- `is_decagonal(true);` / `nth_decagonal(true);` raise
  `CinderRuntimeError` matching `"is_decagonal\(\) requires an int, got
  bool"` / `"nth_decagonal\(\) requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this file
  already relies on).
- `is_decagonal(1.5);` / `nth_decagonal("5");` raise `CinderRuntimeError`
  matching `"is_decagonal\(\) requires an int, got float"` /
  `"nth_decagonal\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column, for both functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_nonagonal` and
`_nth_nonagonal`, search either name), `tests/test_builtins.py` (new
`class TestIsDecagonal` and `class TestNthDecagonal`, modeled on
`class TestIsNonagonal`/`class TestNthNonagonal`, search either name,
for the test shapes above). Once merged, `README.md`'s Builtins bullet
needs `is_decagonal`/`nth_decagonal` added near
`is_nonagonal`/`nth_nonagonal`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 3. Language: hole elements and per-element default values in plain-assignment list destructuring

Build: `let [a, , c] = expr;` (a hole element, skipping a position) and
`let [a, b = 5] = expr;` (a per-element default) both already work for
`let`-style list destructuring (`_destructure_list_pattern`,
`cinder/parser.py`, search `def _destructure_list_pattern`), but neither
works for the plain-assignment form `[a, b] = expr;` for
already-declared names — it only supports plain identifiers, a trailing
`...rest`, and (already, today) arbitrary nesting of further list
patterns. Verify the gap:
```sh
python3 -m cinder.cli eval 'let a; let c; [a, , c] = [1, 2, 3]; print(a); print(c);'
# -> <eval>:1:19: expected an expression, found ','
python3 -m cinder.cli eval 'let a; let b; [a, b = 5] = [1]; print(a); print(b);'
# -> <eval>:1:21: expected ']' after list literal, found '='
```
A third, related gap in the same code path: a nested **map** pattern as
a list-destructuring element (`[a, {b, c}] = [1, {"b": 2, "c": 3}];`,
the list-typed mirror of nesting a list pattern inside a list pattern,
which already works) also fails today:
```sh
python3 -m cinder.cli eval 'let a; let b; let c; [a, {b, c}] = [1, {"b": 2, "c": 3}]; print(a); print(b); print(c);'
# -> <eval>:1:34: invalid assignment target
```

Root cause: `_assignment()` (search `def _assignment`) parses the LHS as
an ordinary expression first (`expr = self._ternary()`), and only
*afterwards*, once it turns out to be a `ListLiteral` followed by `=`,
reinterprets it as a pattern via `_destructure_assign_pattern` (search
`def _destructure_assign_pattern`) — which walks the already-parsed
`ListLiteral.elements` and only recognizes `Identifier`, a trailing
`Spread` (rest), and nested `ListLiteral` shapes, because those are the
only element shapes ordinary list-literal expression grammar can
produce. A hole (`, ,`) and a bare `= expr` are not valid list-literal
*expression* syntax at all — the parse fails before `_assignment` ever
regains control to attempt the pattern reinterpretation — and a
`MapLiteral` element, while valid list-literal syntax, is never
translated into a nested map pattern by `_destructure_assign_pattern`
(it only recurses on `ListLiteral`).

The fix is architectural, not a patch to `_destructure_assign_pattern`:
parse the pattern *speculatively* with the same dedicated grammar `let`
already uses (`_destructure_list_pattern`, which fully supports holes,
defaults, and both nested-list and nested-map elements), *before*
falling back to ordinary expression parsing — exactly the same
speculative-dual-parse technique this codebase already uses for the
map-assignment form (`_try_map_destructure_assign_statement`, search
that name, tried from `_brace_statement`) and for disambiguating a
leading `{` between a map literal and a block (see `PROJECT.md`'s
Design principles: "A leading `{` at statement position is
disambiguated by speculative parse"). Once the speculative parse wins,
build the `DestructureAssign` directly from its output — no
reinterpretation step needed, since `_destructure_list_pattern`'s
`(names, rest)` output shape is already exactly what `DestructureAssign`
stores (a superset of what `_destructure_assign_pattern` could ever
produce). This also means **the interpreter needs no changes at all**:
`_bind_list_destructure` (`cinder/interpreter.py`, search `def
_bind_list_destructure`) already handles a `None` name (hole, `elif
name is not None:` skips it), a per-element `default` (`item =
value[index] if index < len(value) else self.evaluate(default, env)`),
and a 3-tuple nested map pattern (`isinstance(name, tuple) and
len(name) == 3`) generically for both `let`-style `env.define` and
assignment-style `env.assign` (the `use_assign` flag) — it was already
written to support all of this the day map/list nesting first landed,
just never reachable from the plain-assignment parse path.

Replace `_assignment` (search `def _assignment`) — only the opening of
the method changes, everything from `expr = self._ternary()` onward is
unchanged:
```python
def _assignment(self) -> Expr:
    if self._check(TokenType.LBRACKET):
        start = self.pos
        try:
            names, rest = self._destructure_list_pattern()
            if self._check(TokenType.EQ):
                eq_token = self._advance()
                value = self._assignment()
                return DestructureAssign(
                    names, rest, value, eq_token.line, eq_token.column
                )
        except ParseError:
            pass
        self.pos = start
    expr = self._ternary()
    if self._check(TokenType.EQ):
        eq_token = self._advance()
        value = self._assignment()
        if isinstance(expr, Identifier):
            return Assign(expr.name, value, eq_token.line, eq_token.column)
        if isinstance(expr, Index):
            return IndexAssign(
                expr.obj, expr.index, value, eq_token.line, eq_token.column
            )
        if isinstance(expr, SliceExpr):
            return SliceAssign(
                expr.obj, expr.start, expr.end, expr.step, value,
                eq_token.line, eq_token.column,
            )
        raise ParseError(
            "invalid assignment target", eq_token.line, eq_token.column
        )
    # ...rest of the method (QQEQ, compound-assign, increment/decrement
    # branches) is unchanged — leave it exactly as it is today.
```
(Note the `isinstance(expr, ListLiteral)` branch that used to call
`_destructure_assign_pattern` is gone — every `[...] = ...` case that
used to reach it now returns earlier, from the speculative branch, so
this branch was dead code once the speculative parse is in place. Any
`[...] = ...` shape that still shouldn't parse — e.g. `[1, 2] = [3,
4];`, a literal element the pattern grammar rejects — now falls through
to the same `raise ParseError("invalid assignment target", ...)` at
the bottom, just via the ordinary-expression path instead of a
dedicated check, so the end-user error is identical.) Also delete
`_destructure_assign_pattern` itself (search `def
_destructure_assign_pattern`) — after this change it has no callers.

Acceptance criteria:
- `let a; let c; [a, , c] = [1, 2, 3]; print(a); print(c);` prints `1`
  then `3` — the hole worked example above, `b`'s value discarded.
- `let a; let b; [a, b = 5] = [1]; print(a); print(b);` prints `1` then
  `5` — the default worked example above.
- `let a; let b; let c; [a, {b, c}] = [1, {"b": 2, "c": 3}]; print(a);
  print(b); print(c);` prints `1`, `2`, `3` — the nested-map-element
  worked example above.
- `let a; let b; [a, b] = [b, a];` (swap idiom), `let a; let b; let
  rest; [a, b, ...rest] = [1, 2, 3, 4];`, and `let a; let b; let c;
  [[a, b], c] = [[1, 2], 3];` (nested list, already working) all still
  behave exactly as before — regression coverage for
  `TestDestructureAssign.test_swap_idiom`/`test_rest_binds_remaining_elements_as_list`
  and `test_list_destructure_assignment_nested_pattern_parses`.
- `[1, 2] = [3, 4];` and `[] = [1];` still raise `ParseError` — regression
  coverage for `test_list_destructure_assignment_literal_element_raises_parse_error`
  and `test_list_destructure_assignment_empty_pattern_raises_parse_error`
  (search either name in `tests/test_parser.py`), confirming the
  fallback path still rejects genuinely invalid targets.
- `[a, ...rest, b] = [1, 2, 3];` (rest not last) still raises
  `ParseError` — regression coverage for
  `test_list_destructure_assignment_rest_not_last_raises_parse_error`.
- `[a, b] += [1, 2];` and `[a, b] ??= [1, 2];` still raise `ParseError`
  — regression coverage for `test_list_destructure_compound_assign_raises_parse_error`
  and `test_list_destructure_qq_assign_raises_parse_error` (a
  destructuring target is never valid for a compound-assignment
  operator, only plain `=`).
- Update `tests/test_parser.py`'s `test_list_destructure_assignment_default_raises_parse_error`
  (search that name): this is the one existing test whose asserted
  behavior this task deliberately changes (`[a, b = 5] = [1];` used to
  raise `ParseError`, and now must parse) — verified by actually
  applying this task's patch against current `main` and running the
  full suite, which fails exactly this one test, no others. Rewrite it
  into a positive test asserting the parsed shape, modeled on
  `test_map_destructure_assignment_entry_default` (search that name)
  for the map-pattern equivalent's own shape-assertion style.
- Add new tests: `tests/test_parser.py`, parse-shape tests for the hole
  and default and nested-map-element cases above (modeled on
  `test_list_destructure_assignment`/`test_list_destructure_assignment_nested_pattern_parses`);
  `tests/test_interpreter.py`'s `TestDestructureAssign` class (search
  that name), runtime tests for the three worked examples above,
  modeled on that class's existing `test_swap_idiom`/`test_rest_binds_remaining_elements_as_list`.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_assignment`, search `def
_assignment`; delete `_destructure_assign_pattern`, search `def
_destructure_assign_pattern`) — no changes needed to
`cinder/interpreter.py` or `cinder/ast_nodes.py` (though
`ast_nodes.py`'s `DestructureAssign` docstring, search `class
DestructureAssign`, is worth a one-line fix while you're there: it
currently claims "flat patterns only... mirroring `DestructureLetStmt`'s
own 'no nesting' rule", which was already stale before this task since
nested list-in-list plain-assignment destructuring works today — feel
free to correct it in passing, but it's not this task's acceptance
bar). `tests/test_parser.py` and `tests/test_interpreter.py` per the
acceptance criteria above. Once merged, `README.md`'s Variables & scope
bullet needs its "the plain-assignment form `[a, b] = expr;` does not
support defaults" caveat removed/updated, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass,
not this task.

---

## 4. Standard library: `nth_harshad` — Harshad number found at a 1-indexed position

Build: `is_harshad` (`cinder/builtins.py`, search `def _is_harshad`:
whether `n` is divisible by its own digit sum, e.g. `18`'s digits sum
to `9` and `18 % 9 == 0`) has no value-returning sibling that finds the
Harshad number at a given 1-indexed position — the same gap
`nth_abundant`/`nth_deficient` (search either name) already closed for
`is_abundant`/`is_deficient`, and `nth_semiperfect` (task 1 above) is
about to close for `is_semiperfect`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_harshad(1));'
# -> <eval>:1:7: undefined name 'nth_harshad'
```

Worked examples: the first ten Harshad numbers are `1, 2, 3, 4, 5, 6,
7, 8, 9, 10` (every one-digit number is trivially divisible by its own
digit sum), so `nth_harshad(1)` is `1` and `nth_harshad(10)` is `10`.
The next ones are `12, 18, 20, 21, 24, 27, 30, 36, 40, 42` — `11` is
skipped (`11 % (1+1) == 11 % 2 == 1`, not divisible), so `nth_harshad(20)`
is `42`.

Add to `cinder/builtins.py`, directly after `_is_harshad` (search `def
_is_harshad`):
```python
def _nth_harshad(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_harshad", arguments, 1, line, column)
    value = _require_int("nth_harshad", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_harshad() requires a positive integer, domain error", line, column
        )

    def _is_harshad_candidate(candidate: int) -> bool:
        digit_total = sum(int(digit) for digit in str(candidate))
        return candidate % digit_total == 0

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_harshad_candidate(candidate):
            count += 1
    return candidate
```
(The bounded sequential-scan shape mirrors `_nth_abundant`/`_nth_deficient`
exactly — search either name for the precedent — just with `_is_harshad`'s
own digit-sum divisibility check inlined instead of calling `_is_harshad`
directly, the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice those two already made.) Register it in the builtins dict
(search `"is_harshad": _is_harshad,`) right next to the existing entry:
`"nth_harshad": _nth_harshad,`.

Acceptance criteria:
- `nth_harshad(1)` through `nth_harshad(10)` are `1` through `10` — the
  first worked example above.
- `nth_harshad(20)` is `42` — the second worked example above.
- `is_harshad(nth_harshad(n))` is `true` for every `n` from `1` to `50`
  — the value returned is always actually a Harshad number, mirroring
  `test_nth_deficient_agrees_with_is_deficient`'s (search that name)
  cross-check style.
- `nth_harshad(0)` and `nth_harshad(-3)` raise `CinderRuntimeError`
  matching `"nth_harshad() requires a positive integer, domain error"`.
- `nth_harshad(true)` and `nth_harshad("3")` raise `CinderRuntimeError`
  with the standard `_require_int` type-mismatch message, and
  `nth_harshad(1, 2)` raises the standard arity error — regression
  coverage matching `nth_deficient`'s own bool/string/arity tests
  (search `test_nth_deficient_of_bool_raises`/
  `test_nth_deficient_of_string_raises`/`test_nth_deficient_wrong_arity_raises`).
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_harshad`,
search `def _is_harshad`), `tests/test_builtins.py` (new `class
TestNthHarshad`, modeled on `class TestNthDeficient`, search that name,
for the test shapes above — place it near the existing `class
TestIsHarshad`, search that name). Once merged, `README.md`'s Builtins
bullet needs `nth_harshad` added near `is_harshad`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 5. Language: destructuring patterns for `const` declarations

Build: `let` already supports both list-destructuring (`let [a, b] =
expr;`) and map-destructuring (`let {a, b} = expr;`), with full nesting,
rest capture, per-key rename, per-entry defaults, and hole elements
(see the README's "Variables & scope" bullet). `const` has none of this
— only a single plain identifier is accepted after the keyword. Verify
the gap:
```sh
python3 -m cinder.cli eval 'const [a, b] = [1, 2]; print(a); print(b);'
# -> <eval>:1:7: expected identifier after 'const', found '['
python3 -m cinder.cli eval 'const {a, b} = {"a": 1, "b": 2}; print(a); print(b);'
# -> <eval>:1:7: expected identifier after 'const', found '{'
```

Worked examples: `const [a, b] = [1, 2]; print(a); print(b);` should
print `1` then `2`, exactly like the `let` equivalent, but with every
bound name frozen — `const [a, b] = [1, 2]; a = 3;` should raise the
same `CinderRuntimeError` a plain `const a = 1; a = 2;` already raises
today (`"cannot assign to const 'a'"`, see `TestConst
.test_const_reassignment_raises`, search that name). Same shape for map
patterns: `const {a, b} = {"a": 1, "b": 2};` binds both frozen.

Root cause and fix shape: `cinder/parser.py`'s `_const_statement`
(search `def _const_statement`) never checks for a leading `[`/`{`
the way `_let_statement` (search `def _let_statement`) already does —
it goes straight to `_one_const_declaration`, which demands a bare
`IDENTIFIER`. The parsing machinery to fix this already exists and
needs no changes of its own: `_destructure_let_statement` (search `def
_destructure_let_statement`) already parses either pattern kind via
`_destructure_list_pattern`/`_destructure_map_pattern` (search either
name) and builds a `DestructureLetStmt` — the exact same node `let`
produces — so it is a generic "parse a destructuring declaration"
helper in practice, not really `let`-specific despite its name. Give it
one new parameter and thread it through:
```python
def _destructure_let_statement(self, let_token: Token, is_map: bool, is_const: bool = False) -> Stmt:
    if is_map:
        names, rest = self._destructure_map_pattern()
    else:
        names, rest = self._destructure_list_pattern()
    self._consume(TokenType.EQ, "'=' after destructuring pattern")
    initializer = self._assignment()
    self._consume(TokenType.SEMICOLON, "';' after variable declaration")
    return DestructureLetStmt(
        names, initializer, let_token.line, let_token.column,
        is_map=is_map, rest=rest, is_const=is_const,
    )
```
and dispatch to it from `_const_statement` (search `def
_const_statement`) exactly the way `_let_statement` already dispatches
to it, with `is_const=True`:
```python
def _const_statement(self) -> Stmt:
    const_token = self._advance()
    if self._check(TokenType.LBRACKET):
        return self._destructure_let_statement(const_token, is_map=False, is_const=True)
    if self._check(TokenType.LBRACE):
        return self._destructure_let_statement(const_token, is_map=True, is_const=True)
    declarations = [self._one_const_declaration(const_token)]
    while self._check(TokenType.COMMA):
        self._advance()
        declarations.append(self._one_const_declaration(const_token))
    self._consume(TokenType.SEMICOLON, "';' after variable declaration")
    if len(declarations) == 1:
        return declarations[0]
    return DeclSeq(declarations, const_token.line, const_token.column)
```
(Only the first three lines are new; everything from
`declarations = [...]` on is unchanged, included so the replacement is
a drop-in for the whole function.) `DestructureLetStmt` (search `class
DestructureLetStmt` in `cinder/ast_nodes.py`) needs one new field,
defaulted so every existing `let`-produced instance is unaffected:
`is_const: bool = False`.

The interpreter needs `is_const` threaded from the statement down to
wherever a name actually gets bound, since a nested pattern's bindings
(`const [a, {b, c}] = ...;`) and rest/rename bindings must be frozen
too, not just the top-level names. `execute`'s `DestructureLetStmt`
branch (search `if isinstance(stmt, DestructureLetStmt):` in
`cinder/interpreter.py`) already looks up `stmt.is_map` — pass
`stmt.is_const` alongside it:
```python
if isinstance(stmt, DestructureLetStmt):
    value = self.evaluate(stmt.initializer, env)
    if stmt.is_map:
        self._bind_map_destructure(
            env, stmt.names, stmt.rest, value, stmt.line, stmt.column,
            is_const=stmt.is_const,
        )
        return
    self._bind_list_destructure(
        env, stmt.names, stmt.rest, value, stmt.line, stmt.column,
        is_const=stmt.is_const,
    )
    return
```
`_bind_list_destructure` and `_bind_map_destructure` (search either
name) each already carry a `use_assign: bool = False` parameter for
exactly this kind of mode-threading (they use it to pick `env.define`
vs. `env.assign` for the plain-assignment destructuring form) — add a
sibling `is_const: bool = False` parameter to both, and pass it through
every recursive self-call inside their bodies (the nested-list and
nested-map branches in each, plus every `_bind_destructure_name` call
in each — six call sites total across the two functions, all of the
shape `..., line, column, use_assign)` today; append `, is_const)` or
`is_const=is_const` at each, whichever matches the surrounding call's
style) exactly the same way `use_assign` is already threaded through
those same six call sites. Do **not** add it to the two call sites in
`_evaluate_destructure_assign` (search that name) — those are the
plain-assignment form (`[a, b] = expr;`), which reassigns
already-declared names and has no concept of freshly declaring a
const, so they keep relying on the new parameter's default. Finally,
`_bind_destructure_name` (search `def _bind_destructure_name`) gets the
same new parameter, used only on the `not use_assign` (fresh-binding)
path:
```python
def _bind_destructure_name(
    self, env: Environment, name: str, item: object, line: int, column: int,
    use_assign: bool, is_const: bool = False,
) -> None:
    if not use_assign:
        if is_const:
            env.define_const(name, item)
        else:
            env.define(name, item)
        return
    try:
        env.assign(name, item)
    except KeyError:
        raise CinderRuntimeError(
            self._undefined_name_message(name, env), line, column
        ) from None
    except _ConstAssignError:
        raise CinderRuntimeError(
            f"cannot assign to const {name!r}", line, column
        ) from None
```
(Only the signature and the `if not use_assign:` branch change; the
`use_assign` branch below is unchanged, included so the replacement is
a drop-in for the whole function.) No other callers of any of these
four functions (the `for`-loop destructuring, `match` list/map
patterns, and destructuring function parameters) pass `is_const` at
all, so they keep defaulting to `False` and are entirely unaffected —
`const` destructuring is scoped to declarations only, matching plain
`const`'s own scope (there is no `const` loop variable or `const`
function parameter concept in Cinder today, and this task does not add
one).

Acceptance criteria:
- `const [a, b] = [1, 2]; print(a); print(b);` prints `1` then `2` —
  the worked example above.
- `const {a, b} = {"a": 1, "b": 2}; print(a); print(b);` prints `1`
  then `2` — the map worked example above.
- `const [a, b] = [1, 2]; a = 3;` raises `CinderRuntimeError` matching
  `"cannot assign to const 'a'"` — the top-level names are actually
  frozen, not just freshly bound.
- `const {a, b} = {"a": 1, "b": 2}; b = 3;` raises `CinderRuntimeError`
  matching `"cannot assign to const 'b'"` — same for map patterns.
- `const [a, {b, c}] = [1, {"b": 2, "c": 3}]; c = 9;` raises
  `CinderRuntimeError` matching `"cannot assign to const 'c'"` — a
  nested pattern's names are frozen too, confirming `is_const` threads
  through the recursive nested-pattern branches, not just the
  top-level loop.
- `const [a, ...rest] = [1, 2, 3]; rest = [];` raises
  `CinderRuntimeError` matching `"cannot assign to const 'rest'"` — a
  rest-captured binding is frozen too.
- `const {a: x} = {"a": 1}; x = 2;` raises `CinderRuntimeError`
  matching `"cannot assign to const 'x'"` — a per-key-renamed binding
  is frozen under its local name.
- `const [a, b = 5] = [1]; print(b);` is `5` — per-element defaults
  still work, unaffected by the new field.
- `const [a, , c] = [1, 2, 3]; print(a); print(c);` prints `1` then
  `3` — hole elements still work.
- Regression: `let [a, b] = [1, 2]; a = 3; print(a);` still prints `3`
  (a plain `let` destructure stays mutable — `DestructureLetStmt`'s new
  `is_const` field defaults to `False` and `_let_statement`'s existing
  calls never pass it) and every existing destructuring-`let`/nested/
  rest/rename/default/hole test in `tests/test_interpreter.py` still
  passes unmodified.
- New tests in `tests/test_interpreter.py`: a `class
  TestConstDestructure` (modeled on `TestDestructureLet`/
  `TestDestructureLetMap`, search either name, for the binding shapes,
  and on `TestConst.test_const_reassignment_raises`, search that name,
  for the freeze-checking style) covering every acceptance case above.
- New tests in `tests/test_parser.py`: parse-shape tests asserting
  `isinstance(parsed, DestructureLetStmt) and parsed.is_const is True`
  for both `const [a, b] = expr;` and `const {a, b} = expr;` — assert
  the `is_const` attribute directly rather than extending the existing
  `shape()` helper's `DestructureLetStmt` tuple (search `def shape` and
  `"DestructureLetStmt"`), since that tuple is asserted as a fixed
  4-element shape by roughly ten existing tests and extending it would
  require touching all of them for a field this task can verify more
  narrowly.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_const_statement`, search `def
_const_statement`; `_destructure_let_statement`, search that name),
`cinder/ast_nodes.py` (`class DestructureLetStmt`), `cinder/interpreter.py`
(`execute`'s `DestructureLetStmt` branch, `_bind_list_destructure`,
`_bind_map_destructure`, `_bind_destructure_name` — search any name),
`tests/test_parser.py`, `tests/test_interpreter.py` per the acceptance
criteria above. Once merged, `README.md`'s "Variables & scope" bullet
needs a mention that `const` now supports the same destructuring forms
as `let`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `nth_squarefree` — squarefree number found at a 1-indexed position

Build: `is_squarefree` (`cinder/builtins.py`, search `def
_is_squarefree`: no prime factor of `value` appears with exponent 2 or
more, checked by trial division for any `divisor` where
`value % (divisor * divisor) == 0`) has no value-returning `nth_*`
sibling, the same gap `nth_practical_number`/`nth_deficient`/
`nth_harshad` (task 4 above) already close or are about to close for
their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_squarefree(1));'
# -> <eval>:1:7: undefined name 'nth_squarefree' (did you mean
#    'is_squarefree'?)
```

Worked examples: the first ten squarefree numbers (OEIS A005117) are
`1, 2, 3, 5, 6, 7, 10, 11, 13, 14` — `4, 8, 9, 12` are skipped (each
divisible by a perfect square: `4 = 2^2`, `8 = 2^2 * 2`, `9 = 3^2`,
`12 = 2^2 * 3`); the 20th is `31`.

Add directly after `_is_squarefree` (search `def _is_squarefree`,
immediately before `def _is_powerful_number`) — keeps the
value-returning helper next to the predicate it mirrors, matching
where `nth_deficient` itself sits right after `is_deficient`:
```python
def _nth_squarefree(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_squarefree", arguments, 1, line, column)
    value = _require_int("nth_squarefree", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_squarefree() requires a positive integer, domain error",
            line, column,
        )

    def _is_squarefree_candidate(candidate: int) -> bool:
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % (divisor * divisor) == 0:
                return False
        return True

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_squarefree_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`/`_nth_harshad`, with the
inner candidate check copied from `_is_squarefree`'s own body instead
of calling `_is_squarefree` directly — the same "duplicate the tiny
predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice `_nth_harshad` already makes.) Also
register the new dict entry (search `"is_squarefree":
_is_squarefree,`, add `"nth_squarefree": _nth_squarefree,` directly
after it, before `"is_powerful_number": _is_powerful_number,`).

Acceptance criteria:
- `nth_squarefree(1);` through `nth_squarefree(10);` are `1, 2, 3, 5,
  6, 7, 10, 11, 13, 14` in order — the worked example above.
- `nth_squarefree(20);` is `31` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`, `is_squarefree(nth_squarefree(position))`
  is `true` — the same self-consistency check `nth_practical_number`'s
  own test suite already runs against `is_practical_number`.
- `nth_squarefree(0);`, `nth_squarefree(-3);` both raise
  `CinderRuntimeError` matching `"nth_squarefree\(\) requires a
  positive integer, domain error"`, matching `nth_practical_number`'s
  own non-positive-input convention.
- `nth_squarefree(true);` raises `CinderRuntimeError` matching
  `"nth_squarefree\(\) requires an int, got bool"`, since
  `_require_int` rejects `bool` even though Cinder's `bool` is a Python
  `int` subclass (same guard every other int-only predicate in this
  file already relies on).
- `nth_squarefree("5");` raises `CinderRuntimeError` matching
  `"nth_squarefree\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_squarefree`,
search `def _is_squarefree`), `tests/test_builtins.py` (new `class
TestNthSquarefree`, modeled on `class TestNthPracticalNumber`, search
that name, for the test shapes above — place it near the existing
`class TestIsSquarefree`, search that name). Once merged, `README.md`'s
Builtins bullet needs `nth_squarefree` added near `is_squarefree`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

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
