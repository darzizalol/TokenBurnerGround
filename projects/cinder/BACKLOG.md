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

## 1. Language: `as` binding on a nested list/map sub-pattern inside `match`

Build: whole-value `as` binding (PR #348) lets a `match` arm capture the
entire matched subject (`match ([1, 2]) { [a, b] as whole => whole, _ =>
nil }`), but only at the top of the arm's own pattern — there is no way
to capture an *intermediate* value reached partway through a nested
list/map pattern, even though the nested sub-pattern itself already
binds every leaf name inside it. Verify the gap:
```sh
python3 -m cinder.cli eval 'let r = match ([1, [2, 3]]) { [a, [b, c] as inner] => inner, _ => 0 }; print(r);'
# -> <eval>:1:38: expected ']' after list pattern, found 'as'
python3 -m cinder.cli eval 'let r = match ([1, {"b": 1}]) { [a, {b} as inner] => inner, _ => 0 }; print(r);'
# -> <eval>:1:41: expected ']' after list pattern, found 'as'
python3 -m cinder.cli eval 'let r = match ({"a": {"b": 1}}) { {a: {b} as inner} => inner, _ => 0 }; print(r);'
# -> <eval>:1:41: expected '}' after map pattern, found 'as'
python3 -m cinder.cli eval 'let r = match ({"a": [1, 2]}) { {a: [x, y] as inner} => inner, _ => 0 }; print(r);'
# -> <eval>:1:41: expected '}' after map pattern, found 'as'
```
Meanwhile the same nesting already works today without `as` — including
the map-pattern-nested-inside-a-list-pattern-element shape PR #403 just
added:
```sh
python3 -m cinder.cli eval 'let r = match ([1, [2, 3]]) { [a, [b, c]] => [a, b, c], _ => 0 }; print(r);'
# -> [1, 2, 3]
python3 -m cinder.cli eval 'let r = match ([1, {"b": 1}]) { [a, {b}] => b, _ => 0 }; print(r);'
# -> 1
python3 -m cinder.cli eval 'let r = match ({"a": {"b": 1}}) { {a: {b}} => b, _ => 0 }; print(r);'
# -> 1
```

Worked examples (all currently `ParseError`, all should work after the
fix): `match ([1, [2, 3]]) { [a, [b, c] as inner] => inner, _ => 0 }` is
`[2, 3]` — a nested *list* pattern element captures its own sub-value;
`match ([1, {"b": 1}]) { [a, {b} as inner] => inner, _ => 0 }` is
`{"b": 1}` — a nested *map* pattern element (PR #403's shape, landed
after this task's gap was first identified) captures its own sub-value
too; `match ({"a": {"b": 1}}) { {a: {b} as inner} => inner, _ => 0 }` is
`{"b": 1}` — a nested *map* pattern used as a map value does too;
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

Root cause: four call sites accept a nested sub-pattern and none of
them parse a trailing `as` today. In `cinder/parser.py`:
`_match_list_pattern_entry`'s `TokenType.LBRACKET` branch (search `def
_match_list_pattern_entry`) does `entry = self._match_list_pattern()`
with no `as`-parsing step; the same function's `TokenType.LBRACE` branch
(added by PR #403, right below the `LBRACKET` one) does `entry =
(nested_entries, nested_rest, "map")` — already a 3-tuple tagged with
the `"map"` string so `_match_list_entries` can tell it apart from the
plain-list 2-tuple, but with no `as`-parsing step either;
`_match_map_pattern_entry` (search `def _match_map_pattern_entry`) has
the same gap in both its `LBRACKET` and `LBRACE` branches, each
returning immediately after the nested
`self._match_list_pattern()`/`self._match_map_pattern()` call. On the
interpreter side, `_match_list_entries`'s tuple branch (search `def
_match_list_entries`, `cinder/interpreter.py` — it already dispatches
on `len(entry) == 3` vs. not, to tell the PR #403 nested-map case apart
from the plain nested-list case) and `_match_map_entries`'s two tuple
branches recurse into the nested sub-match but never look at (or have
anywhere to put) a captured name for the sub-value.

Fix shape — parse the optional `as` right after each nested sub-pattern,
reusing `_match_whole_binding()` (search that name; it already just
parses an optional `as NAME` and returns the name or `None`, no changes
needed there), and always append the captured name (possibly `None`) as
the last element of that entry's tuple so every tuple has a fixed length
per kind — no length-based ambiguity between "nested list" and "nested
map" markers before and after this change:

In `_match_list_pattern_entry`'s `LBRACKET` branch (currently a bare
2-tuple from `self._match_list_pattern()`; becomes a 3-tuple, `len ==
3` with no string third element, so it stays distinguishable from the
`LBRACE` branch's tagged 4-tuple below purely by what that third element
is):
```python
if token.type == TokenType.LBRACKET:
    nested_entries, nested_rest = self._match_list_pattern()
    nested_as = self._match_whole_binding()
    entry = (nested_entries, nested_rest, nested_as)
```
And its `LBRACE` branch (currently a 3-tuple tagged `"map"`; becomes a
4-tuple, keeping `"map"` as the third element so the discriminator stays
where callers already look for it):
```python
elif token.type == TokenType.LBRACE:
    nested_entries, nested_rest = self._match_map_pattern()
    nested_as = self._match_whole_binding()
    entry = (nested_entries, nested_rest, "map", nested_as)
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
tuple branch (discriminate on length exactly as it already does today —
`4` now means the PR #403 nested-map case, since it grew from `3` to
`4`; anything else is the plain nested-list case, which grew from `2` to
`3`):
```python
if isinstance(entry, tuple):
    if len(entry) == 4:
        nested_entries, nested_rest, _, nested_as = entry
        if not self._match_map_entries(nested_entries, nested_rest, item, env):
            return False
    else:
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
- `match ([1, {"b": 1}]) { [a, {b} as inner] => inner, _ => 0 }` is
  `{"b": 1}` — a nested map-pattern element inside a list pattern (PR
  #403's nesting shape).
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
  TestMatch` in each) still passes unmodified — including PR #403's own
  nested-map-in-list tests, which predate this task and must keep
  passing with `nested_as` simply `None`.
- New tests in `tests/test_parser.py` (search `class TestMatch`, near
  the existing `test_match_list_pattern_whole_binding`/
  `test_match_map_pattern_whole_binding` tests) asserting the nested
  entry tuple's trailing name field for each of the four nesting
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

## 2. Standard library: `nth_carmichael_number` — Carmichael number found at a 1-indexed position

Build: `is_carmichael_number` (`cinder/builtins.py`, search `def
_is_carmichael_number`: a composite, squarefree number `n` where every
prime factor `p` of `n` satisfies `(p - 1) | (n - 1)`, e.g. `561 = 3 *
11 * 17`, and `560` is divisible by `2`, `10`, and `16`) has no
value-returning `nth_*` sibling, the same gap `nth_smith_number`/
`nth_achilles` already closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_carmichael_number(1));'
# -> <eval>:1:7: undefined name 'nth_carmichael_number' (did you mean
#    'is_carmichael_number'?)
```

Worked examples: the first ten Carmichael numbers (OEIS A002997) are
`561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341` (confirmed
by scanning with `is_carmichael_number` directly), so
`nth_carmichael_number(1)` is `561` and `nth_carmichael_number(10)` is
`29341`. The 20th is `162401`.

Add directly after `_is_carmichael_number` (search `def
_is_carmichael_number`, immediately before `def _is_vampire_number`) —
keeps the value-returning helper next to the predicate it mirrors,
matching where `nth_smith_number` itself sits right after
`is_smith_number`:
```python
def _nth_carmichael_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_carmichael_number", arguments, 1, line, column)
    value = _require_int("nth_carmichael_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_carmichael_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_carmichael_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
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
        if len(factors) < 2:
            return False  # prime, not composite
        if len(factors) != len(set(factors)):
            return False  # not squarefree
        return all(
            (prime - 1) != 0 and (candidate - 1) % (prime - 1) == 0
            for prime in factors
        )

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_carmichael_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_smith_number`/`_nth_achilles`, with the inner
candidate check copied verbatim from `_is_carmichael_number`'s own body
instead of calling `_is_carmichael_number` directly — the same "duplicate
the tiny predicate body instead of a redundant `_require_arity`/
`_require_int` round-trip per candidate" choice every recent `nth_*` task
already makes.) Register the new dict entry (search `"is_carmichael_number":
_is_carmichael_number,`, add `"nth_carmichael_number":
_nth_carmichael_number,` directly after it, before `"is_vampire_number":
_is_vampire_number,`).

Acceptance criteria:
- `nth_carmichael_number(1);` through `nth_carmichael_number(10);` are
  `561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341` in
  order — the worked example above.
- `nth_carmichael_number(20);` is `162401` — a further worked example
  confirming the scan scales past the first ten.
- For every `position` in `1..15`,
  `is_carmichael_number(nth_carmichael_number(position))` is `true` —
  the same self-consistency check `nth_smith_number`/`nth_achilles`'s own
  test suites already run against their predicates (capped at `15`
  rather than the usual `50` since Carmichael numbers thin out fast
  enough by the 20th that a `1..50` scan would run needlessly long for a
  test suite).
- `nth_carmichael_number(0);`, `nth_carmichael_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_carmichael_number\(\) requires a
  positive integer, domain error"`.
- `nth_carmichael_number(true);` raises `CinderRuntimeError` matching
  `"nth_carmichael_number\(\) requires an int, got bool"`.
- `nth_carmichael_number("5");` raises `CinderRuntimeError` matching
  `"nth_carmichael_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_carmichael_number`,
search `def _is_carmichael_number`), `tests/test_builtins.py` (new `class
TestNthCarmichaelNumber`, modeled on `class TestNthSmithNumber`, search
that name, for the test shapes above — place it near the existing `class
TestIsCarmichaelNumber`, search that name). Once merged, `README.md`'s
existing `is_carmichael_number` bullet needs `nth_carmichael_number`
added right after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 3. Language: multiple chained `if` filter clauses in list/map comprehensions

Build: a list/map comprehension's `for` clause accepts at most one `if`
filter today — a second `if` is a `ParseError`, even though chaining two
independent filters (rather than combining them into one `&&`-style
expression) is common and reads more naturally clause-by-clause, exactly
how Python's own comprehensions allow it. Verify the gap:
```sh
python3 -m cinder.cli eval 'let r = [x for x in 1..20 if x % 2 == 0 if x % 3 == 0]; print(r);'
# -> <eval>:1:41: expected ']' after list comprehension, found 'if'
python3 -m cinder.cli eval 'let r = {x: x for x in 1..20 if x % 2 == 0 if x % 3 == 0}; print(r);'
# -> <eval>:1:47: expected '}' after map comprehension, found 'if'
```
Meanwhile a single `if`, and multiple chained `for` clauses, already work:
```sh
python3 -m cinder.cli eval 'let r = [x for x in 1..20 if x % 2 == 0]; print(r);'
# -> [2, 4, 6, 8, 10, 12, 14, 16, 18]
python3 -m cinder.cli eval 'let r = [x + y for x in 1..3 for y in 1..3 if x != y]; print(r);'
# -> [3, 4, 3, 5, 4, 5]
```

Worked examples: `[x for x in 1..20 if x % 2 == 0 if x % 3 == 0]` is `[6,
12, 18]` — equivalent to combining both conditions with `&&`/`and`;
`{x: x * x for x in 1..20 if x % 2 == 0 if x % 3 == 0}` is `{6: 36, 12:
144, 18: 324}` — the map-comprehension sibling; a third chained `if`
composes too, `[x for x in 1..50 if x % 2 == 0 if x % 3 == 0 if x % 5 ==
0]` is `[30]`; and chained `if`s compose with chained `for` clauses in
either order, `[x + y for x in 1..5 if x % 2 == 0 for y in 1..5 if y %
2 == 0]` is `[4, 6, 6, 8]` (`x` in `{2, 4}`, `y` in `{2, 4}`, every pair).

Root cause: `_comprehension_clause` (search `def _comprehension_clause`,
`cinder/parser.py`) parses at most one optional `if` — `if
self._check(TokenType.IF): ... condition = self._ternary()` — with no
loop, so a second `if` token is left unconsumed and the caller's
`self._consume(TokenType.RBRACKET/RBRACE, ...)` right after rejects it.

Fix shape — change the single `if self._check(...)` into a `while`, and
AND-combine every chained condition into one `Logical` expression as they're
parsed, reusing the exact `Logical`/`Token` construction the real `and`
operator's own parsing (`_and`, search that name a few dozen lines above)
already does — no AST node or interpreter change needed at all, since a
chain of `if`s becomes indistinguishable from a single `if` with `&&`
between them by the time parsing finishes:
```python
condition = None
while self._check(TokenType.IF):
    if_token = self._advance()
    next_condition = self._ternary()
    if condition is None:
        condition = next_condition
    else:
        and_token = Token(TokenType.AND, "and", None, if_token.line, if_token.column)
        condition = Logical(condition, and_token, next_condition)
```
(`Logical` and `Token` are both already imported in `cinder/parser.py` —
`Logical` for `ast_nodes`, `Token` from `cinder.tokens` — so no new
imports are needed.) This is the entire fix: `ComprehensionClause`,
`ListComprehension`, `MapComprehension` (`cinder/ast_nodes.py`) keep
their existing single `condition: Expr | None` field unchanged, and
`_run_comprehension_clauses`/`_evaluate_list_comprehension`/
`_evaluate_map_comprehension` (`cinder/interpreter.py`) need no changes
either — they already just do `is_truthy(self.evaluate(clause.condition,
iter_env))` on whatever single expression tree the parser hands them,
and short-circuit evaluation of the resulting `Logical` AND-chain gives
the same left-to-right stop-on-first-`false` behavior a real hand-written
`if a if b if c` chain should have.

Acceptance criteria:
- `[x for x in 1..20 if x % 2 == 0 if x % 3 == 0]` is `[6, 12, 18]` — the
  first worked example above.
- `{x: x * x for x in 1..20 if x % 2 == 0 if x % 3 == 0}` is `{6: 36, 12:
  144, 18: 324}` — the map-comprehension sibling.
- `[x for x in 1..50 if x % 2 == 0 if x % 3 == 0 if x % 5 == 0]` is
  `[30]` — a third chained `if`.
- `[x + y for x in 1..5 if x % 2 == 0 for y in 1..5 if y % 2 == 0]` is
  `[4, 6, 6, 8]` — chained `if`s compose with chained `for` clauses.
- Regression: every existing single-`if`/no-`if`/chained-`for` comprehension
  test in `tests/test_parser.py`/`tests/test_interpreter.py` (search
  `Comprehension` in each) still passes unmodified.
- New tests in `tests/test_parser.py` (near `test_list_comprehension_with_filter`,
  search that name) asserting the parsed `condition` field's `shape()` is a
  `Logical`/`TokenType.AND` node for a chained-`if` list comprehension and
  a chained-`if` map comprehension.
- New tests in `tests/test_interpreter.py` (in `class TestListComprehension`/
  `class TestMapComprehension`, search those names) covering every
  acceptance case above.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_comprehension_clause`, search that
name), `tests/test_parser.py`, `tests/test_interpreter.py` per the
acceptance criteria above. Once merged, `README.md`'s comprehension
bullets need a clause noting that multiple chained `if` filters are
supported, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Standard library: `nth_twin_prime` — twin prime found at a 1-indexed position

Build: `is_twin_prime` (`cinder/builtins.py`, search `def
_is_twin_prime`: prime `n` with a prime at `n - 2` or `n + 2`, e.g. `41` is
a twin prime via `43`) has no value-returning `nth_*` sibling, the same
gap `nth_smith_number`/`nth_carmichael_number` (the latter task 2 above)
already close for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_twin_prime(1));'
# -> <eval>:1:7: undefined name 'nth_twin_prime' (did you mean
#    'is_twin_prime'?)
```

Worked examples: the first fifteen twin primes by `is_twin_prime`'s own
membership definition (every prime with a prime neighbor at distance 2 —
not one entry per pair, so both `3` and `5` count separately even though
they're the same pair) are `3, 5, 7, 11, 13, 17, 19, 29, 31, 41, 43, 59,
61, 71, 73` (confirmed by scanning with `is_twin_prime` directly), so
`nth_twin_prime(1)` is `3` and `nth_twin_prime(15)` is `73`. The 20th is
`137`.

Add directly after `_is_twin_prime` (search `def _is_twin_prime`,
immediately before `def _is_power_of_two`) — keeps the value-returning
helper next to the predicate it mirrors, matching where
`nth_carmichael_number` itself sits right after `is_carmichael_number`:
```python
def _nth_twin_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_twin_prime", arguments, 1, line, column)
    value = _require_int("nth_twin_prime", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_twin_prime() requires a positive integer, domain error",
            line, column,
        )

    def _trial_division_is_prime(candidate: int) -> bool:
        if candidate < 2:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return False
        return True

    def _is_twin_prime_candidate(candidate: int) -> bool:
        if candidate < 2:
            return False
        if not _trial_division_is_prime(candidate):
            return False
        return (
            _trial_division_is_prime(candidate - 2)
            or _trial_division_is_prime(candidate + 2)
        )

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_twin_prime_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_smith_number`/`_nth_carmichael_number`, with the
inner candidate check copied verbatim from `_is_twin_prime`'s own body
instead of calling `_is_twin_prime` directly — the same "duplicate the
tiny predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice every recent `nth_*` task already makes.)
Register the new dict entry (search `"is_twin_prime": _is_twin_prime,`,
add `"nth_twin_prime": _nth_twin_prime,` directly after it, before
`"is_power_of_two": _is_power_of_two,`).

Acceptance criteria:
- `nth_twin_prime(1);` through `nth_twin_prime(15);` are `3, 5, 7, 11,
  13, 17, 19, 29, 31, 41, 43, 59, 61, 71, 73` in order — the worked
  example above.
- `nth_twin_prime(20);` is `137` — a further worked example confirming
  the scan scales past the first fifteen.
- For every `position` in `1..50`, `is_twin_prime(nth_twin_prime(position))`
  is `true` — the same self-consistency check `nth_smith_number`/
  `nth_carmichael_number`'s own test suites already run against their
  predicates.
- `nth_twin_prime(0);`, `nth_twin_prime(-3);` both raise
  `CinderRuntimeError` matching `"nth_twin_prime\(\) requires a positive
  integer, domain error"`.
- `nth_twin_prime(true);` raises `CinderRuntimeError` matching
  `"nth_twin_prime\(\) requires an int, got bool"`.
- `nth_twin_prime("5");` raises `CinderRuntimeError` matching
  `"nth_twin_prime\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_twin_prime`,
search `def _is_twin_prime`), `tests/test_builtins.py` (new `class
TestNthTwinPrime`, modeled on `class TestNthSphenic`, search that name,
for the test shapes above — place it near the existing `class
TestIsTwinPrime`, search that name). Once merged, `README.md`'s existing
`is_twin_prime` bullet needs `nth_twin_prime` added right after it, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 5. Standard library: `nth_self_number` — self (Colombian) number found at a 1-indexed position

Build: `is_self_number` (`cinder/builtins.py`, search `def
_is_self_number`: a non-negative integer with no "generator" — no
`candidate` such that `candidate + digit_sum(candidate) == value` — e.g.
`20` is a self number since no smaller number's digit-sum-added value
reaches it) has no value-returning `nth_*` sibling, the same gap
`nth_smith_number`/`nth_carmichael_number`/`nth_twin_prime` (the latter
two tasks 2 and 4 above) already close for their own predicates. Verify
the gap:
```sh
python3 -m cinder.cli eval 'print(nth_self_number(1));'
# -> <eval>:1:7: undefined name 'nth_self_number' (did you mean
#    'is_self_number'?)
```

Worked examples: the first twenty self numbers (confirmed by scanning
with `is_self_number` directly) are `0, 1, 3, 5, 7, 9, 20, 31, 42, 53,
64, 75, 86, 97, 108, 110, 121, 132, 143, 154`, so `nth_self_number(1)` is
`0` and `nth_self_number(10)` is `53`. The 20th is `154`, the 50th is
`457`.

Unlike every other `nth_*` in this backlog, position `1` maps to
candidate `0`, not `1` — `is_self_number(0)` is `true` (`digit_count =
1`, `lower_bound = max(0, 0 - 9) = 0`, the `range(0, 0)` scan is empty so
nothing disproves it), and `0` is the smallest value `is_self_number`
ever accepts (it returns `false` outright for negative input, per its
own `if value < 0: return False` guard), so the scan must start
*before* `0` (`candidate = -1`, incremented before the first check) to
avoid silently excluding it from the sequence forever.

Add directly after `_is_self_number` (search `def _is_self_number`,
immediately before `def _nth_happy_number`) — keeps the value-returning
helper next to the predicate it mirrors:
```python
def _nth_self_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_self_number", arguments, 1, line, column)
    value = _require_int("nth_self_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_self_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_self_number_candidate(candidate: int) -> bool:
        digit_count = len(str(candidate))
        lower_bound = max(0, candidate - 9 * digit_count)
        for lower_candidate in range(lower_bound, candidate):
            if (
                lower_candidate
                + sum(int(digit) for digit in str(lower_candidate))
                == candidate
            ):
                return False
        return True

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_self_number_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_self_number`'s own body
minus its `value < 0` guard, since the scan never visits a negative
candidate — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice every recent `nth_*` task already makes.) Register the new dict
entry (search `"is_self_number": _is_self_number,`, add
`"nth_self_number": _nth_self_number,` directly after it, before
`"nth_happy_number": _nth_happy_number,`).

Acceptance criteria:
- `nth_self_number(1);` through `nth_self_number(10);` are `0, 1, 3, 5,
  7, 9, 20, 31, 42, 53` in order — the worked example above.
- `nth_self_number(20);` is `154` and `nth_self_number(50);` is `457` —
  further worked examples confirming the scan scales past the first ten.
- For every `position` in `1..50`,
  `is_self_number(nth_self_number(position))` is `true` — the same
  self-consistency check `nth_smith_number`/`nth_carmichael_number`/
  `nth_twin_prime`'s own test suites already run against their
  predicates.
- `nth_self_number(0);`, `nth_self_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_self_number\(\) requires a
  positive integer, domain error"` — note this domain check is on the
  *position* argument, unrelated to `0` being a valid *self number*
  itself (`nth_self_number(1)` legitimately returns `0`).
- `nth_self_number(true);` raises `CinderRuntimeError` matching
  `"nth_self_number\(\) requires an int, got bool"`.
- `nth_self_number("5");` raises `CinderRuntimeError` matching
  `"nth_self_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_self_number`,
search `def _is_self_number`), `tests/test_builtins.py` (new `class
TestNthSelfNumber`, modeled on `class TestNthHappyNumber`, search that
name, for the test shapes above — place it near the existing `class
TestIsSelfNumber`, search that name). Once merged, `README.md`'s
existing `is_self_number` bullet needs `nth_self_number` added right
after it, its "Status & roadmap" section needs updating, and
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
