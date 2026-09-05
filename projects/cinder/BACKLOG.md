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

## 1. Standard library: `nth_powerful_number` — powerful number found at a 1-indexed position

Build: `is_powerful_number` (`cinder/builtins.py`, search `def
_is_powerful_number`: whether every prime factor of `n` appears with
exponent `2` or more, e.g. `72 = 2^3 * 3^2`) has no value-returning
`nth_*` sibling, the same gap `nth_practical_number`/`nth_semiperfect`
already closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_powerful_number(1));'
# -> <eval>:1:7: undefined name 'nth_powerful_number' (did you mean
#    'is_powerful_number'?)
```

Worked examples: the first ten powerful numbers are `1, 4, 8, 9, 16, 25,
27, 32, 36, 49` (`1` is trivially powerful — the loop below leaves
`remaining == 1` without ever entering the `if count < 2` branch), so
`nth_powerful_number(1)` is `1` and `nth_powerful_number(10)` is `49`.
The 20th is `169`.

Add directly after `_is_powerful_number` (search `def
_is_powerful_number`, immediately before `def _is_achilles`):
```python
def _nth_powerful_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_powerful_number", arguments, 1, line, column)
    value = _require_int("nth_powerful_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_powerful_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_powerful_candidate(candidate: int) -> bool:
        remaining = candidate
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

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_powerful_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`/`_nth_semiperfect`/
`_nth_refactorable`, with the inner candidate check copied from
`_is_powerful_number`'s own body instead of calling
`_is_powerful_number` directly — the same "duplicate the tiny predicate
body instead of a redundant `_require_arity`/`_require_int` round-trip
per candidate" choice every recent `nth_*` task already makes.) Register
the new dict entry (search `"is_powerful_number": _is_powerful_number,`,
add `"nth_powerful_number": _nth_powerful_number,` directly after it,
before `"is_achilles": _is_achilles,`).

Acceptance criteria:
- `nth_powerful_number(1);` through `nth_powerful_number(10);` are `1,
  4, 8, 9, 16, 25, 27, 32, 36, 49` in order — the worked example above.
- `nth_powerful_number(20);` is `169` — a further worked example
  confirming the scan scales past the first ten.
- For every `position` in `1..50`,
  `is_powerful_number(nth_powerful_number(position))` is `true` — the
  same self-consistency check `nth_practical_number`/`nth_semiperfect`'s
  own test suites already run against their predicates.
- `nth_powerful_number(0);`, `nth_powerful_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_powerful_number\(\) requires a
  positive integer, domain error"`.
- `nth_powerful_number(true);` raises `CinderRuntimeError` matching
  `"nth_powerful_number\(\) requires an int, got bool"`.
- `nth_powerful_number("5");` raises `CinderRuntimeError` matching
  `"nth_powerful_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_powerful_number`,
search `def _is_powerful_number`), `tests/test_builtins.py` (new `class
TestNthPowerfulNumber`, modeled on `class TestNthSemiperfect`, search
that name, for the test shapes above — place it near the existing `class
TestIsPowerfulNumber`, search that name). Once merged, `README.md`'s
Builtins bullet needs `nth_powerful_number` added near
`is_powerful_number`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Language: map patterns nested inside `match` list-pattern elements

Build: `match`'s list patterns can already nest another *list* pattern as
one of their elements (`[a, [b, c]]`), and map patterns can already nest
either a list or a map pattern as one of their *values*
(`{a: [x, y]}`, `{a: {c}}`) — but a list pattern cannot nest a *map*
pattern as one of its elements. Verify the gap:
```sh
python3 -m cinder.cli eval 'let r = match ([1, {"b": 2}]) { [a, {b}] => a + b, _ => 0 }; print(r);'
# -> <eval>:1:37: expected an identifier, '_', or a literal inside list
#    pattern, found '{'
python3 -m cinder.cli eval 'let r = match ([{"a": 1}, 2]) { [{a}, b] => a + b, _ => 0 }; print(r);'
# -> <eval>:1:34: expected an identifier, '_', or a literal inside list
#    pattern, found '{'
```
Meanwhile the symmetric cases already work today:
```sh
python3 -m cinder.cli eval 'let r = match ({"a": [1, 2]}) { {a: [x, y]} => x + y, _ => 0 }; print(r);'
# -> 3
python3 -m cinder.cli eval 'let r = match ([1, [2, 3]]) { [a, [b, c]] => a + b + c, _ => 0 }; print(r);'
# -> 6
```

Worked examples (all currently `ParseError`, all should work after the
fix): `match ([1, {"b": 2}]) { [a, {b}] => a + b, _ => 0 }` is `3`;
`match ([{"a": 1}, 2]) { [{a}, b] => a + b, _ => 0 }` is `3`; a nested
map element composes with rename and rest capture,
`match ([1, {"x": 2, "y": 3}]) { [a, {x: renamed, ...rest}] => a +
renamed, _ => 0 }` is `3`; and nesting goes two levels deep (map inside
list inside list), `match ([1, [2, {"z": 3}]]) { [a, [b, {z}]] => a + b
+ z, _ => 0 }` is `6`.

Root cause: `_match_list_pattern_entry` (search `def
_match_list_pattern_entry`, `cinder/parser.py`) has a branch for
`TokenType.LBRACKET` (nested list pattern, `entry =
self._match_list_pattern()`, a 2-tuple `(nested_entries, nested_rest)`)
but none for `TokenType.LBRACE` — it falls through the `elif` chain to
the final `else: raise ParseError` used for anything that isn't an
identifier/`_`/literal/nested-list/nested-map. On the interpreter side,
`_match_list_entries` (search `def _match_list_entries`,
`cinder/interpreter.py`) already assumes any tuple entry is a nested
*list*: `if isinstance(entry, tuple): nested_entries, nested_rest =
entry; ... self._match_list_entries(...)` — it has no branch for a
nested map.

Fix shape, mirroring the marker convention `_match_map_pattern_entry`
already uses to disambiguate a nested list from a nested map under a map
key (search `def _match_map_pattern_entry`: a nested `[` there returns a
3-tuple `(nested_entries, nested_rest, True)`, a nested `{` returns a
plain 2-tuple, and `_match_map_entries` branches on `len(binding) == 3`
to tell them apart). Add the equivalent branch to
`_match_list_pattern_entry`, directly after its existing `if token.type
== TokenType.LBRACKET:` branch:
```python
elif token.type == TokenType.LBRACE:
    nested_entries, nested_rest = self._match_map_pattern()
    entry = (nested_entries, nested_rest, "map")
```
(A 3-tuple here unambiguously means "nested map" — the *opposite* of what
a 3-tuple means in `_match_map_pattern_entry`'s own convention, since
there a 2-tuple is the map case and this function's existing nested-list
case is already a bare 2-tuple; keep the two conventions independent
rather than trying to unify them, they're read by two different
functions.) Then update `_match_list_entries`'s existing tuple branch to
dispatch on tuple length, the same way `_match_map_entries` already
dispatches on `len(binding) == 3`:
```python
if isinstance(entry, tuple):
    if len(entry) == 3:
        nested_entries, nested_rest, _ = entry
        if not self._match_map_entries(nested_entries, nested_rest, item, env):
            return False
    else:
        nested_entries, nested_rest = entry
        if not self._match_list_entries(nested_entries, nested_rest, item, env):
            return False
    continue
```
No other changes needed: `_match_map_pattern`/`_match_map_entries`
already fully support rename, rest capture, defaults, and further
nesting on their own — a map pattern nested inside a list element gets
all of that for free, exactly as a map pattern nested inside another
map's value already does today.

Acceptance criteria:
- `match ([1, {"b": 2}]) { [a, {b}] => a + b, _ => 0 }` is `3` — the
  first worked example above.
- `match ([{"a": 1}, 2]) { [{a}, b] => a + b, _ => 0 }` is `3` — a
  leading nested-map element, not just a trailing one.
- `match ([1, {"x": 2, "y": 3}]) { [a, {x: renamed, ...rest}] => a +
  renamed, _ => 0 }` is `3` — a nested map element composes with per-key
  rename and rest capture.
- `match ([1, [2, {"z": 3}]]) { [a, [b, {z}]] => a + b + z, _ => 0 }` is
  `6` — a nested map element works two levels deep, inside a nested list
  element.
- `match ([1, {"a": 1}]) { [a, {b}] => 1, _ => -1 }` is `-1` — a nested
  map pattern falls through (not raises) when the map subject is missing
  a required key, exactly like a top-level map pattern already does.
- `match ([1, "not a map"]) { [a, {b}] => 1, _ => -1 }` is `-1` — falls
  through (not raises) when the element isn't a map at all.
- Regression: every existing nested-list-in-list and
  nested-list/map-in-map-value test in `tests/test_parser.py`/
  `tests/test_interpreter.py` (search `class TestMatch` in each) still
  passes unmodified — this task only adds a new accepted nesting
  combination, it changes no existing one.
- New tests in `tests/test_parser.py` and `tests/test_interpreter.py`
  (search `class TestMatch` in each) covering every acceptance case
  above, modeled on the existing nested-list-pattern-in-list-element
  tests.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_list_pattern_entry`, search
that name), `cinder/interpreter.py` (`_match_list_entries`, search that
name), `tests/test_parser.py`, `tests/test_interpreter.py` per the
acceptance criteria above. Once merged, `README.md`'s `match` bullet
needs a clause noting that list patterns also accept a nested map
pattern as an element, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `nth_achilles` — Achilles number found at a 1-indexed position

Build: `is_achilles` (`cinder/builtins.py`, search `def _is_achilles`:
whether `n` is a powerful number — every prime factor's exponent is 2 or
more — whose exponents' gcd is exactly 1, i.e. `n` is not itself a perfect
power, e.g. `72 = 2^3 * 3^2`, `gcd(3, 2) == 1`) has no value-returning
`nth_*` sibling, the same gap `nth_powerful_number`/`nth_sphenic` already
closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_achilles(1));'
# -> <eval>:1:7: undefined name 'nth_achilles' (did you mean
#    'is_achilles'?)
```

Worked examples: the first ten Achilles numbers (OEIS A052486) are `72,
108, 200, 288, 392, 432, 500, 648, 675, 800` (confirmed by scanning with
`is_achilles` directly: `4 = 2^2` is powerful but a perfect square, so
it's excluded; `72 = 2^3 * 3^2` has exponent gcd `gcd(3, 2) == 1`, so
it's the first), so `nth_achilles(1)` is `72` and `nth_achilles(10)` is
`800`. The 20th is `1800`.

Add directly after `_is_achilles` (search `def _is_achilles`, immediately
before `def _integer_kth_root`) — keeps the value-returning helper next
to the predicate it mirrors, matching where `nth_powerful_number` itself
sits right after `is_powerful_number`:
```python
def _nth_achilles(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_achilles", arguments, 1, line, column)
    value = _require_int("nth_achilles", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_achilles() requires a positive integer, domain error",
            line, column,
        )

    def _is_achilles_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        remaining = candidate
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

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_achilles_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_sphenic`/`_nth_powerful_number`, with the inner
candidate check copied from `_is_achilles`'s own body — including its
`math.gcd` use, already imported at module scope since `_is_achilles`
itself uses it — instead of calling `_is_achilles` directly, the same
"duplicate the tiny predicate body instead of a redundant
`_require_arity`/`_require_int` round-trip per candidate" choice every
recent `nth_*` task already makes.) Register the new dict entry (search
`"is_achilles": _is_achilles,`, add `"nth_achilles": _nth_achilles,`
directly after it, before `"is_perfect_power": _is_perfect_power,`).

Acceptance criteria:
- `nth_achilles(1);` through `nth_achilles(10);` are `72, 108, 200, 288,
  392, 432, 500, 648, 675, 800` in order — the worked example above.
- `nth_achilles(20);` is `1800` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`, `is_achilles(nth_achilles(position))`
  is `true` — the same self-consistency check `nth_sphenic`/
  `nth_powerful_number`'s own test suites already run against their
  predicates.
- `nth_achilles(0);`, `nth_achilles(-3);` both raise `CinderRuntimeError`
  matching `"nth_achilles\(\) requires a positive integer, domain
  error"`.
- `nth_achilles(true);` raises `CinderRuntimeError` matching
  `"nth_achilles\(\) requires an int, got bool"`.
- `nth_achilles("5");` raises `CinderRuntimeError` matching
  `"nth_achilles\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_achilles`, search
`def _is_achilles`), `tests/test_builtins.py` (new `class
TestNthAchilles`, modeled on `class TestNthPowerfulNumber`, search that
name, for the test shapes above — place it near the existing `class
TestIsAchilles`, search that name). Once merged, `README.md`'s existing
`is_achilles` bullet (search `` `is_achilles` to test``) needs
`nth_achilles` added right after it, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Language: whole-value `as` binding on literal and range `match` patterns

Build: whole-value `as` binding (`match ([1, 2]) { [a, b] as whole => whole,
_ => nil }`) currently only exists on list-pattern and map-pattern match
arms (landed via PR #348) — a literal pattern, a multi-value literal
pattern, or a range pattern cannot carry `as` at all, even though each of
them has a real use for it that a plain bound-identifier arm can't
replace: a range pattern's bound name is not the subject's actual value
(you'd otherwise have no way to recover it inside the arm body), and a
multi-value literal arm's body has no way to tell *which* of the several
literals matched. Verify the gap:
```sh
python3 -m cinder.cli eval 'let r = match (5) { 1..10 as whole => whole, _ => nil }; print(r);'
# -> <eval>:1:27: expected '=>' after match pattern, found 'as'
python3 -m cinder.cli eval 'let r = match (2) { 1, 2 as whole => whole, _ => nil }; print(r);'
# -> <eval>:1:26: expected '=>' after match pattern, found 'as'
```

Worked examples: `match (5) { 1..10 as whole => whole, _ => nil }` is `5`;
`match (-5) { -10..0 as whole => whole, _ => 0 }` is `-5` (a negative
range bound composes with `as`, same as range patterns already do without
it); `match (2) { 1, 2 as whole => whole, _ => nil }` is `2`, and
`match (1) { 1, 2 as whole => whole, _ => nil }` is `1` — the same arm
answers correctly for either matched literal, which a single shared
`MatchArm` per multi-value entry (see `_match_arm`'s
`for pattern, binding, range_pattern in entries` below) already makes
trivial since `whole_binding` binds to whichever `subject` reached that
arm, not to the pattern literal itself; `match (5) { 5 as whole => whole,
_ => nil }` is `5` — a single literal pattern may carry `as` too, for
symmetry with the multi-value case even though it's less useful there.

The wildcard/bound-identifier arm kind keeps its current restriction —
`match (5) { n as whole => n, _ => 0 }` and `match (5) { _ as whole =>
whole, _ => 0 }` both still raise `ParseError`, since a bound-identifier
arm already binds the whole subject under its own name (`n`) with no
`as` needed, and it would be redundant/confusing to let `_` (whose whole
point is "bind nothing") also carry a name via `as` — the exact rationale
`MatchArm`'s own docstring (search `class MatchArm`, `cinder/ast_nodes.py`)
already gives for excluding it there; this task extends the *literal* and
*range* pattern kinds only, not the wildcard/bound-identifier kind.

Root cause: `_match_arm` (search `def _match_arm`, `cinder/parser.py`)
has two branches that already call `_match_whole_binding()` (search that
name) right after parsing their pattern — the `LBRACKET` (list-pattern)
and `LBRACE` (map-pattern) branches — but its third branch, the flat
literal/range/wildcard/bound-identifier path, goes straight from
collecting `entries` to `self._consume(TokenType.FAT_ARROW, ...)` with no
`as`-parsing step at all. On the interpreter side, `_evaluate_match`
(search `def _evaluate_match`, `cinder/interpreter.py`) mirrors this: its
`arm.range_pattern is not None` branch calls `self.evaluate(arm.body,
env)` directly (plain `env`, no `arm_env`), and its final `if
values_equal(subject, self.evaluate(arm.pattern, env))` branch does the
same — neither ever looks at `arm.whole_binding`, unlike the
list/map-pattern branches just above them which each build a fresh
`arm_env` and `arm_env.define(arm.whole_binding, subject)` when it's set.

Fix shape — in `_match_arm`'s flat-pattern branch, parse the optional
`as` right after collecting `entries` (mirroring where the list/map
branches call it relative to their own pattern), and reject it when
combined with a wildcard/bound-identifier entry the same way the existing
multi-value check already rejects *mixing* those kinds:
```python
first_token = self._peek()
entries = [self._match_pattern()]
while self._check(TokenType.COMMA):
    self._advance()
    entries.append(self._match_pattern())
has_unconditional = any(
    pattern is None and range_pattern is None
    for pattern, _, range_pattern in entries
)
if len(entries) > 1 and has_unconditional:
    raise ParseError(
        "'_' or a bound identifier cannot be combined with other "
        "patterns in a match arm",
        first_token.line,
        first_token.column,
    )
whole_binding = self._match_whole_binding()
if whole_binding is not None and has_unconditional:
    raise ParseError(
        "'as' binding is not valid on a '_' or bound-identifier match "
        "pattern",
        first_token.line,
        first_token.column,
    )
self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
body = self._ternary()
return [
    MatchArm(pattern, body, binding, None, range_pattern, whole_binding=whole_binding)
    for pattern, binding, range_pattern in entries
]
```
(`_match_whole_binding` itself needs no change — it already just parses
an optional `as NAME` and returns the name or `None`, agnostic to which
arm kind calls it.) Then update `_evaluate_match`'s two flat-pattern
branches to honor `whole_binding` the same way the list/map branches
already do:
```python
if arm.range_pattern is not None:
    values = self._evaluate_range(arm.range_pattern, env)
    if contains_value(
        values, subject, arm.range_pattern.line, arm.range_pattern.column
    ):
        arm_env = env
        if arm.whole_binding is not None:
            arm_env = Environment(env)
            arm_env.define(arm.whole_binding, subject)
        return self.evaluate(arm.body, arm_env)
    continue
```
and, for the final literal-pattern branch:
```python
if values_equal(subject, self.evaluate(arm.pattern, env)):
    arm_env = env
    if arm.whole_binding is not None:
        arm_env = Environment(env)
        arm_env.define(arm.whole_binding, subject)
    return self.evaluate(arm.body, arm_env)
```
No changes needed to the wildcard/bound-identifier branch (`arm.pattern
is None`) — it keeps raising via the new parser-side check above, so it
never reaches the interpreter with a non-`None` `whole_binding`.

Acceptance criteria:
- `match (5) { 1..10 as whole => whole, _ => nil }` is `5` — the first
  worked example above.
- `match (-5) { -10..0 as whole => whole, _ => 0 }` is `-5` — a negative
  range bound composes with `as`.
- `match (2) { 1, 2 as whole => whole, _ => nil }` is `2`, and
  `match (1) { 1, 2 as whole => whole, _ => nil }` is `1` — the
  multi-value literal pattern worked example above, both matched values.
- `match (5) { 5 as whole => whole, _ => nil }` is `5` — a single literal
  pattern with `as`.
- `match (5) { n as whole => n, _ => 0 }` and `match (5) { _ as whole =>
  whole, _ => 0 }` both raise `ParseError` matching `"'as' binding is not
  valid on a '_' or bound-identifier match pattern"` — the
  wildcard/bound-identifier kind keeps its current restriction.
- Regression: every existing list-pattern/map-pattern `as`-binding test in
  `tests/test_parser.py`/`tests/test_interpreter.py` (search `whole_binding`
  in each) still passes unmodified — this task only adds `as` to two new
  pattern kinds, it does not change the list/map-pattern behavior.
- New tests in `tests/test_parser.py` (search `class TestMatch`, near the
  existing `test_match_list_pattern_whole_binding`/
  `test_match_map_pattern_whole_binding` tests) asserting `arms[0].whole_binding`
  for a range-pattern arm and a multi-value literal-pattern arm, plus one
  asserting the wildcard/bound-identifier `ParseError` above.
- New tests in `tests/test_interpreter.py` (search `class TestMatch`, near
  the existing `test_list_pattern_whole_binding_holds_original_subject`)
  covering every acceptance case above.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_arm`, search that name),
`cinder/interpreter.py` (`_evaluate_match`, search that name),
`cinder/ast_nodes.py` (`MatchArm`'s docstring, search `class MatchArm` —
its "Not valid on the wildcard/bound-identifier, literal, or
range-pattern arm kinds" sentence needs updating to say only the
wildcard/bound-identifier kind is excluded now), `tests/test_parser.py`,
`tests/test_interpreter.py` per the acceptance criteria above. Once
merged, `README.md`'s `match` bullet needs a clause noting that literal
and range patterns also accept the whole-value `as` binding, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `nth_smith_number` — Smith number found at a 1-indexed position

Build: `is_smith_number` (`cinder/builtins.py`, search `def
_is_smith_number`: a composite number whose decimal digit sum equals the
digit sum of all its prime factors with multiplicity, e.g. `22 = 2 * 11`,
digit sum `4`, factor digit sum `2 + 1 + 1 = 4`) has no value-returning
`nth_*` sibling, the same gap `nth_refactorable`/`nth_sphenic` already
closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_smith_number(1));'
# -> <eval>:1:7: undefined name 'nth_smith_number' (did you mean
#    'is_smith_number'?)
```

Worked examples: the first ten Smith numbers are `4, 22, 27, 58, 85, 94,
121, 166, 202, 265` (confirmed by scanning with `is_smith_number`
directly), so `nth_smith_number(1)` is `4` and `nth_smith_number(10)` is
`265`. The 20th is `483`.

Add directly after `_is_smith_number` (search `def _is_smith_number`,
immediately before `def _is_carmichael_number`) — keeps the
value-returning helper next to the predicate it mirrors, matching where
`nth_refactorable` itself sits right after `is_refactorable`:
```python
def _nth_smith_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_smith_number", arguments, 1, line, column)
    value = _require_int("nth_smith_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_smith_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_smith_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                break
        else:
            return False  # prime, not composite
        factors = []
        remaining = candidate
        divisor = 2
        while divisor * divisor <= remaining:
            while remaining % divisor == 0:
                factors.append(divisor)
                remaining //= divisor
            divisor += 1
        if remaining > 1:
            factors.append(remaining)
        digit_total = sum(int(digit) for digit in str(candidate))
        factor_digit_total = sum(
            sum(int(digit) for digit in str(factor)) for factor in factors
        )
        return digit_total == factor_digit_total

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_smith_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_refactorable`/`_nth_sphenic`, with the inner
candidate check copied verbatim from `_is_smith_number`'s own body
instead of calling `_is_smith_number` directly — the same "duplicate the
tiny predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice every recent `nth_*` task already makes.)
Register the new dict entry (search `"is_smith_number":
_is_smith_number,`, add `"nth_smith_number": _nth_smith_number,` directly
after it, before `"is_carmichael_number": _is_carmichael_number,`).

Acceptance criteria:
- `nth_smith_number(1);` through `nth_smith_number(10);` are `4, 22, 27,
  58, 85, 94, 121, 166, 202, 265` in order — the worked example above.
- `nth_smith_number(20);` is `483` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`,
  `is_smith_number(nth_smith_number(position))` is `true` — the same
  self-consistency check `nth_refactorable`/`nth_sphenic`'s own test
  suites already run against their predicates.
- `nth_smith_number(0);`, `nth_smith_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_smith_number\(\) requires a
  positive integer, domain error"`.
- `nth_smith_number(true);` raises `CinderRuntimeError` matching
  `"nth_smith_number\(\) requires an int, got bool"`.
- `nth_smith_number("5");` raises `CinderRuntimeError` matching
  `"nth_smith_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_smith_number`,
search `def _is_smith_number`), `tests/test_builtins.py` (new `class
TestNthSmithNumber`, modeled on `class TestNthRefactorable`, search that
name, for the test shapes above — place it near the existing `class
TestIsSmithNumber`, search that name). Once merged, `README.md`'s
existing `is_smith_number` bullet needs `nth_smith_number` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 6. Language: `as` binding on a nested list/map sub-pattern inside `match`

Build: whole-value `as` binding (PR #348) lets a `match` arm capture the
entire matched subject (`match ([1, 2]) { [a, b] as whole => whole, _ =>
nil }`), but only at the top of the arm's own pattern — there is no way
to capture an *intermediate* value reached partway through a nested
list/map pattern, even though the nested sub-pattern itself already
binds every leaf name inside it. Verify the gap:
```sh
python3 -m cinder.cli eval 'let r = match ([1, [2, 3]]) { [a, [b, c] as inner] => inner, _ => 0 }; print(r);'
# -> <eval>:1:38: expected ']' after list pattern, found 'as'
python3 -m cinder.cli eval 'let r = match ({"a": {"b": 1}}) { {a: {b} as inner} => inner, _ => 0 }; print(r);'
# -> <eval>:1:41: expected '}' after map pattern, found 'as'
python3 -m cinder.cli eval 'let r = match ({"a": [1, 2]}) { {a: [x, y] as inner} => inner, _ => 0 }; print(r);'
# -> <eval>:1:41: expected '}' after map pattern, found 'as'
```
Meanwhile the same nesting already works today without `as`:
```sh
python3 -m cinder.cli eval 'let r = match ([1, [2, 3]]) { [a, [b, c]] => [a, b, c], _ => 0 }; print(r);'
# -> [1, 2, 3]
python3 -m cinder.cli eval 'let r = match ({"a": {"b": 1}}) { {a: {b}} => b, _ => 0 }; print(r);'
# -> 1
```

Worked examples (all currently `ParseError`, all should work after the
fix): `match ([1, [2, 3]]) { [a, [b, c] as inner] => inner, _ => 0 }` is
`[2, 3]` — a nested *list* pattern element captures its own sub-value;
`match ({"a": {"b": 1}}) { {a: {b} as inner} => inner, _ => 0 }` is
`{"b": 1}` — a nested *map* pattern value does too;
`match ({"a": [1, 2]}) { {a: [x, y] as inner} => inner, _ => 0 }` is
`[1, 2]` — and so does a nested *list* pattern used as a map value;
composes with rest capture at the same nesting level, `match ([1, [2,
3, 4]]) { [a, [b, ...rest] as inner] => [inner, rest], _ => 0 }` is
`[[2, 3, 4], [3, 4]]`; and nests to arbitrary depth, each level with its
own independent binding, `match ([1, [2, [3, 4]]]) { [a, [b, [c, d] as
deep] as mid] => [mid, deep], _ => 0 }` is `[[2, [3, 4]], [3, 4]]`.

The wildcard/bound-identifier, literal, and hole entry kinds keep their
current restriction — `as` stays illegal directly on a plain identifier
or literal list-pattern entry, e.g. `match ([1, 2]) { [a as x, b] => 1,
_ => 0 }` still raises `ParseError` (unchanged, since the fix only adds
`as`-parsing inside the nested-list/nested-map branches, never the
identifier/literal branches) — this task only lets `as` follow a nested
*sub-pattern*, mirroring exactly where the arm-level `as` already sits
relative to the *whole* pattern.

Root cause: three call sites accept a nested sub-pattern and none of
them parse a trailing `as` today. In `cinder/parser.py`:
`_match_list_pattern_entry`'s `TokenType.LBRACKET` branch (search `def
_match_list_pattern_entry`) does `entry = self._match_list_pattern()`
then falls straight into the shared `return entry, None`, with no
`as`-parsing step; `_match_map_pattern_entry` (search `def
_match_map_pattern_entry`) has the same gap in both its `LBRACKET` and
`LBRACE` branches, each returning immediately after the nested
`self._match_list_pattern()`/`self._match_map_pattern()` call. On the
interpreter side, `_match_list_entries`'s tuple branch and
`_match_map_entries`'s two tuple branches (search `def
_match_list_entries`/`def _match_map_entries`, `cinder/interpreter.py`)
recurse into the nested sub-match but never look at (or have anywhere
to put) a captured name for the sub-value.

Fix shape — parse the optional `as` right after each nested sub-pattern,
reusing `_match_whole_binding()` (search that name; it already just
parses an optional `as NAME` and returns the name or `None`, no changes
needed there), and always append the captured name (possibly `None`) as
the last element of that entry's tuple so every tuple has a fixed length
per kind — no length-based ambiguity between "nested list" and "nested
map" markers before and after this change:

In `_match_list_pattern_entry`'s `LBRACKET` branch:
```python
if token.type == TokenType.LBRACKET:
    nested_entries, nested_rest = self._match_list_pattern()
    nested_as = self._match_whole_binding()
    entry = (nested_entries, nested_rest, nested_as)
```
In `_match_map_pattern_entry`'s `LBRACKET` branch (currently returns a
3-tuple marked with a trailing `True` to mean "nested list"; becomes a
4-tuple, `True` stays the discriminator so nothing downstream that
checks for it specifically needs to change how it finds it):
```python
if self._check(TokenType.LBRACKET):
    nested_entries, nested_rest = self._match_list_pattern()
    nested_as = self._match_whole_binding()
    return key, (nested_entries, nested_rest, True, nested_as), None
```
And its `LBRACE` branch (currently a bare 2-tuple; becomes a 3-tuple):
```python
if self._check(TokenType.LBRACE):
    nested_entries, nested_rest = self._match_map_pattern()
    nested_as = self._match_whole_binding()
    return key, (nested_entries, nested_rest, nested_as), None
```

Then, in `cinder/interpreter.py`, update all three tuple consumers to
unpack the extra field and bind it (only once the nested match itself
succeeds, mirroring how `_evaluate_match` already only defines the
arm-level `whole_binding` after its own match succeeds). `_match_list_entries`'s
tuple branch:
```python
if isinstance(entry, tuple):
    nested_entries, nested_rest, nested_as = entry
    if not self._match_list_entries(nested_entries, nested_rest, item, env):
        return False
    if nested_as is not None:
        env.define(nested_as, item)
    continue
```
`_match_map_entries`'s two tuple branches (discriminate on the `True`
marker itself, not tuple length, since length alone no longer tells the
two kinds apart now that both grew by one field):
```python
if isinstance(binding, tuple) and len(binding) == 4:
    nested_entries, nested_rest, _, nested_as = binding
    if not self._match_list_entries(nested_entries, nested_rest, item, env):
        return False
    if nested_as is not None:
        env.define(nested_as, item)
    continue
if isinstance(binding, tuple):
    nested_entries, nested_rest, nested_as = binding
    if not self._match_map_entries(nested_entries, nested_rest, item, env):
        return False
    if nested_as is not None:
        env.define(nested_as, item)
    continue
```
No changes to `_match_whole_binding`, `MatchArm`, or the arm-level
`whole_binding` handling in `_evaluate_match` — this task is entirely
about names captured *inside* a pattern, a different binding from the
arm's own `whole_binding` field, and the two compose freely (an arm can
have both its own `as whole` and a nested `as inner` at the same time,
since they're independent env entries).

Acceptance criteria:
- `match ([1, [2, 3]]) { [a, [b, c] as inner] => inner, _ => 0 }` is
  `[2, 3]` — the first worked example above.
- `match ({"a": {"b": 1}}) { {a: {b} as inner} => inner, _ => 0 }` is
  `{"b": 1}` — a nested map-pattern value.
- `match ({"a": [1, 2]}) { {a: [x, y] as inner} => inner, _ => 0 }` is
  `[1, 2]` — a nested list-pattern value inside a map pattern.
- `match ([1, [2, 3, 4]]) { [a, [b, ...rest] as inner] => [inner, rest],
  _ => 0 }` is `[[2, 3, 4], [3, 4]]` — composes with rest capture at the
  same nesting level.
- `match ([1, [2, [3, 4]]]) { [a, [b, [c, d] as deep] as mid] => [mid,
  deep], _ => 0 }` is `[[2, [3, 4]], [3, 4]]` — two independent `as`
  bindings at two different nesting depths in the same arm.
- `match ([1, "not a list"]) { [a, [b, c] as inner] => 1, _ => -1 }` is
  `-1` — falls through (not raises) when the nested subject's shape
  doesn't match, exactly like nested patterns without `as` already do.
- `match ([1, 2]) { [a as x, b] => 1, _ => 0 }` still raises `ParseError`
  — `as` stays illegal directly on a plain identifier entry, only a
  nested sub-pattern may carry it.
- Regression: every existing arm-level `as whole` test and every
  existing nested-pattern-without-`as` test in `tests/test_parser.py`/
  `tests/test_interpreter.py` (search `whole_binding` and `class
  TestMatch` in each) still passes unmodified.
- New tests in `tests/test_parser.py` (search `class TestMatch`, near
  the existing `test_match_list_pattern_whole_binding`/
  `test_match_map_pattern_whole_binding` tests) asserting the nested
  entry tuple's trailing name field for each of the three nesting
  kinds above, plus one confirming it's `None` when no nested `as` is
  written.
- New tests in `tests/test_interpreter.py` (search `class TestMatch`,
  near the existing `test_list_pattern_whole_binding_holds_original_subject`)
  covering every acceptance case above.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_list_pattern_entry`,
`_match_map_pattern_entry`, search those names — their return-type
string annotations at the top of `_match_list_pattern`/
`_match_map_pattern`/`_match_list_pattern_entry`/`_match_map_pattern_entry`
also need updating to reflect the new tuple shapes), `cinder/interpreter.py`
(`_match_list_entries`, `_match_map_entries`, search those names),
`tests/test_parser.py`, `tests/test_interpreter.py` per the acceptance
criteria above. Once merged, `README.md`'s `match` bullet needs a clause
noting that `as` can also bind a nested sub-pattern's value, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

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
