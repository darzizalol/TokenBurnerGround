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

## 1. Standard library: `nth_perfect_square` — perfect square found at a 1-indexed position

Build: `is_perfect_square` (`cinder/builtins.py`, search `def
_is_perfect_square`: a non-negative integer whose integer square root,
squared, equals it back — `math.isqrt(value) ** 2 == value`, negative
input returns `false` outright) has no value-returning `nth_*` sibling,
the same gap `nth_power_of_two`/`nth_pronic`/
`nth_decagonal` (already-merged siblings) already close for their own
closed-form sequences. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_perfect_square(1));'
# -> <eval>:1:7: undefined name 'nth_perfect_square' (did you mean
#    'is_perfect_square'?)
```

Unlike `nth_evil`/`nth_odious`/`nth_composite`/`nth_pernicious` (all merged,
all sequential scans), perfect
squares have an exact closed form — position `k` is `(k - 1) ** 2`, the
same shape `nth_power_of_two`/`nth_pronic`/`nth_octagonal`/`nth_nonagonal`/
`nth_decagonal` (search `def _nth_pronic` for the pattern to copy, it's
the closest sibling: also a "closed form starting at candidate 0"
figurate-adjacent sequence) already use for their own closed-form
sequences, so there is no candidate scan and no performance caveat:
`nth_perfect_square(1)` is `0`, `nth_perfect_square(2)` is `1`,
`nth_perfect_square(5)` is `16`, `nth_perfect_square(10)` is `81`,
`nth_perfect_square(20)` is `361`, and `nth_perfect_square(50)` is
`2401` (all six confirmed by direct computation of `(k - 1) ** 2`).

Add directly after `_is_perfect_square` (search `def
_is_perfect_square`, immediately before `def _is_armstrong`) — keeps
the value-returning helper next to the predicate it mirrors:
```python
def _nth_perfect_square(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_perfect_square", arguments, 1, line, column)
    value = _require_int("nth_perfect_square", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_perfect_square() requires a positive integer, domain error",
            line, column,
        )
    return (value - 1) ** 2
```
(Same shape as `_nth_pronic`/`_nth_octagonal`/`_nth_nonagonal`/
`_nth_decagonal` — a direct closed-form return, no loop, no inner
candidate-check helper, since there's nothing to scan.) Register the
new dict entry (search `"is_perfect_square": _is_perfect_square,`, add
`"nth_perfect_square": _nth_perfect_square,` directly after it, before
`"is_armstrong": _is_armstrong,`).

Acceptance criteria:
- `nth_perfect_square(1);` through `nth_perfect_square(5);` are `0, 1,
  4, 9, 16` in order — the closed-form squaring sequence.
- `nth_perfect_square(10);` is `81`, `nth_perfect_square(20);` is `361`,
  and `nth_perfect_square(50);` is `2401` — further worked examples
  confirming the closed form holds at larger positions.
- For every `position` in `1..50`,
  `is_perfect_square(nth_perfect_square(position))` is `true` — the
  same self-consistency check every recent `nth_*` task's own test
  suite already runs against its predicate.
- `nth_perfect_square(0);`, `nth_perfect_square(-3);` both raise
  `CinderRuntimeError` matching `"nth_perfect_square\(\) requires a
  positive integer, domain error"`.
- `nth_perfect_square(true);` raises `CinderRuntimeError` matching
  `"nth_perfect_square\(\) requires an int, got bool"`.
- `nth_perfect_square("5");` raises `CinderRuntimeError` matching
  `"nth_perfect_square\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_perfect_square`,
search `def _is_perfect_square`), `tests/test_builtins.py` (new `class
TestNthPerfectSquare`, modeled on `class TestNthPronic`, search that
name, for the test shapes above — place it near the existing `class
TestIsPerfectSquare`, search that name). Once merged, `README.md`'s
existing `is_perfect_square` bullet needs `nth_perfect_square` added
right after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `nth_palindrome_number` — numeric palindrome found at a 1-indexed position

Build: `is_palindrome_number` (`cinder/builtins.py`, search `def
_is_palindrome_number`: a non-negative integer whose decimal digits read
the same forwards and backwards, `str(value) == str(value)[::-1]`,
negative input returns `false` outright) has no value-returning `nth_*`
sibling. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_palindrome_number(1));'
# -> <eval>:1:7: undefined name 'nth_palindrome_number' (did you mean
#    'is_palindrome_number'?)
```

Worked examples: the first ten numeric palindromes (confirmed by
scanning with `is_palindrome_number` directly) are `0, 1, 2, 3, 4, 5, 6,
7, 8, 9` — every single digit is trivially its own reverse — so
`nth_palindrome_number(1)` is `0` and `nth_palindrome_number(10)` is
`9`. The 15th is `55`, the 20th is `101`, the 50th is `404`. Numeric
palindromes are dense (every 1- and 2-digit number, one in ten 3-digit
numbers, etc.), so the scan stays fast at every position — confirmed
locally: scanning to the 50th takes well under a millisecond in raw
Python, no performance caveat needed.

Like `nth_sad_number` and `nth_trimorphic_number` (both merged, both
map position `1` to candidate `0`), the scan starts at `candidate = -1`
(incremented before the first check) — `0` itself is the very first
palindrome, so there's no off-by-one risk skipping it.

Add directly after `_is_palindrome_number` (search `def
_is_palindrome_number`, immediately before `def _is_repdigit`) — keeps
the value-returning helper next to the predicate it mirrors:
```python
def _nth_palindrome_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_palindrome_number", arguments, 1, line, column)
    value = _require_int("nth_palindrome_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_palindrome_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_palindrome_number_candidate(candidate: int) -> bool:
        return str(candidate) == str(candidate)[::-1]

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_palindrome_number_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_palindrome_number`'s
own body minus its `value < 0` guard, since the scan never visits a
negative candidate — the same "duplicate the tiny predicate body
instead of a redundant `_require_arity`/`_require_int` round-trip per
candidate" choice every recent `nth_*` task already makes.) Register
the new dict entry (search `"is_palindrome_number":
_is_palindrome_number,`, add `"nth_palindrome_number":
_nth_palindrome_number,` directly after it, before `"is_repdigit":
_is_repdigit,`).

Acceptance criteria:
- `nth_palindrome_number(1);` through `nth_palindrome_number(10);` are
  `0, 1, 2, 3, 4, 5, 6, 7, 8, 9` in order — the worked example above.
- `nth_palindrome_number(15);` is `55`, `nth_palindrome_number(20);` is
  `101`, and `nth_palindrome_number(50);` is `404` — further worked
  examples confirming the scan scales well past the first ten.
- For every `position` in `1..50`,
  `is_palindrome_number(nth_palindrome_number(position))` is `true` —
  the same self-consistency check every recent `nth_*` task's own test
  suite already runs against its predicate.
- `nth_palindrome_number(0);`, `nth_palindrome_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_palindrome_number\(\) requires a
  positive integer, domain error"`.
- `nth_palindrome_number(true);` raises `CinderRuntimeError` matching
  `"nth_palindrome_number\(\) requires an int, got bool"`.
- `nth_palindrome_number("5");` raises `CinderRuntimeError` matching
  `"nth_palindrome_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after
`_is_palindrome_number`, search `def _is_palindrome_number`),
`tests/test_builtins.py` (new `class TestNthPalindromeNumber`, modeled
on `class TestNthRepdigit`, search that name, for the test shapes
above — place it near the existing `class TestIsPalindromeNumber`,
search that name). Once merged, `README.md`'s existing
`is_palindrome_number` bullet needs `nth_palindrome_number` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_undulating` — undulating number found at a 1-indexed position

Build: `is_undulating` (`cinder/builtins.py`, search `def
_is_undulating`: a non-negative integer whose decimal digits strictly
alternate between exactly two distinct values across at least three
digits — `len(digits) >= 3`, `digits[0] != digits[1]`, and every digit
matches the one two positions back — negative input, and anything under
three digits or with equal first two digits, returns `false`) has no
value-returning `nth_*` sibling. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_undulating(1));'
# -> <eval>:1:7: undefined name 'nth_undulating' (did you mean
#    'is_undulating'?)
```

Worked examples: the first ten undulating numbers (confirmed by
scanning with `is_undulating` directly) are `101, 121, 131, 141, 151,
161, 171, 181, 191, 202`, so `nth_undulating(1)` is `101` and
`nth_undulating(10)` is `202`. The 15th is `262`, the 20th is `313`,
the 50th is `646`. Undulating numbers are dense enough within the
three-digit range (every `aba` pattern with `a != b` qualifies) that
the scan stays fast at every position — confirmed locally: scanning to
the 50th takes well under a millisecond in raw Python, no performance
caveat needed.

Unlike `nth_palindrome_number` (task 2 above) or `nth_sad_number`
(position `1` maps to candidate `0`), position `1` maps to candidate
`101` here — nothing under 100 has three digits, so the scan can still
start from `candidate = -1` (incremented before the first check, the
same shape every other dense-scan `nth_*` task uses) — it will simply
reject every candidate under `101` before finding it, which is harmless
and keeps this implementation structurally identical to its siblings
for anyone reading them side by side.

Add directly after `_is_undulating` (search `def _is_undulating`,
immediately before `def _is_perfect_square`) — keeps the
value-returning helper next to the predicate it mirrors:
```python
def _nth_undulating(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_undulating", arguments, 1, line, column)
    value = _require_int("nth_undulating", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_undulating() requires a positive integer, domain error",
            line, column,
        )

    def _is_undulating_candidate(candidate: int) -> bool:
        digits = str(candidate)
        if len(digits) < 3 or digits[0] == digits[1]:
            return False
        return all(digit == digits[i % 2] for i, digit in enumerate(digits))

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_undulating_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_undulating`'s own body
minus its `value < 0` guard, since the scan never visits a negative
candidate — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice every recent `nth_*` task already makes.) Register the new dict
entry (search `"is_undulating": _is_undulating,`, add `"nth_undulating":
_nth_undulating,` directly after it, before `"is_perfect_square":
_is_perfect_square,`).

Acceptance criteria:
- `nth_undulating(1);` through `nth_undulating(10);` are `101, 121,
  131, 141, 151, 161, 171, 181, 191, 202` in order — the worked example
  above.
- `nth_undulating(15);` is `262`, `nth_undulating(20);` is `313`, and
  `nth_undulating(50);` is `646` — further worked examples confirming
  the scan scales well past the first ten.
- For every `position` in `1..50`,
  `is_undulating(nth_undulating(position))` is `true` — the same
  self-consistency check every recent `nth_*` task's own test suite
  already runs against its predicate.
- `nth_undulating(0);`, `nth_undulating(-3);` both raise
  `CinderRuntimeError` matching `"nth_undulating\(\) requires a
  positive integer, domain error"`.
- `nth_undulating(true);` raises `CinderRuntimeError` matching
  `"nth_undulating\(\) requires an int, got bool"`.
- `nth_undulating("5");` raises `CinderRuntimeError` matching
  `"nth_undulating\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_undulating`,
search `def _is_undulating`), `tests/test_builtins.py` (new `class
TestNthUndulating`, modeled on `class TestNthRepdigit`, search that
name, for the test shapes above — place it near the existing `class
TestIsUndulating`, search that name). Once merged, `README.md`'s
existing `is_undulating` bullet needs `nth_undulating` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `nth_perfect_cube` — perfect cube found at a 1-indexed position

Build: `is_perfect_cube` (`cinder/builtins.py`, search `def
_is_perfect_cube`: a non-negative integer whose integer cube root,
cubed, equals it back — `root = _integer_cube_root(magnitude); root **
3 == magnitude`) has no value-returning `nth_*` sibling, the same gap
`nth_power_of_two` (already-merged sibling) and `nth_perfect_square`
(task 1 above) already close for their own closed-form sequences.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_perfect_cube(1));'
# -> <eval>:1:7: undefined name 'nth_perfect_cube' (did you mean
#    'is_perfect_cube'?)
```

Perfect cubes have an exact closed form — position `k` is `(k - 1) **
3`, the same shape `nth_perfect_square` (search `def
_nth_perfect_square` for the pattern to copy, it's the closest
sibling: same "closed form starting at candidate 0" cube-vs-square
pairing) already uses for its own closed-form sequence, so there is no
candidate scan and no performance caveat: `nth_perfect_cube(1)` is `0`,
`nth_perfect_cube(2)` is `1`, `nth_perfect_cube(5)` is `64`,
`nth_perfect_cube(10)` is `729`, `nth_perfect_cube(20)` is `6859`, and
`nth_perfect_cube(50)` is `117649` (all six confirmed by direct
computation of `(k - 1) ** 3`).

Add directly after `_is_perfect_cube` (search `def _is_perfect_cube`,
immediately before `def _is_pronic`) — keeps the value-returning
helper next to the predicate it mirrors:
```python
def _nth_perfect_cube(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_perfect_cube", arguments, 1, line, column)
    value = _require_int("nth_perfect_cube", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_perfect_cube() requires a positive integer, domain error",
            line, column,
        )
    return (value - 1) ** 3
```
(Same shape as `_nth_perfect_square`/`_nth_pronic`/`_nth_octagonal` — a
direct closed-form return, no loop, no inner candidate-check helper,
since there's nothing to scan.) Register the new dict entry (search
`"is_perfect_cube": _is_perfect_cube,`, add `"nth_perfect_cube":
_nth_perfect_cube,` directly after it, before `"is_pronic":
_is_pronic,`).

Acceptance criteria:
- `nth_perfect_cube(1);` through `nth_perfect_cube(5);` are `0, 1, 8,
  27, 64` in order — the closed-form cubing sequence.
- `nth_perfect_cube(10);` is `729`, `nth_perfect_cube(20);` is `6859`,
  and `nth_perfect_cube(50);` is `117649` — further worked examples
  confirming the closed form holds at larger positions.
- For every `position` in `1..50`,
  `is_perfect_cube(nth_perfect_cube(position))` is `true` — the same
  self-consistency check every recent `nth_*` task's own test suite
  already runs against its predicate.
- `nth_perfect_cube(0);`, `nth_perfect_cube(-3);` both raise
  `CinderRuntimeError` matching `"nth_perfect_cube\(\) requires a
  positive integer, domain error"`.
- `nth_perfect_cube(true);` raises `CinderRuntimeError` matching
  `"nth_perfect_cube\(\) requires an int, got bool"`.
- `nth_perfect_cube("5");` raises `CinderRuntimeError` matching
  `"nth_perfect_cube\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_perfect_cube`,
search `def _is_perfect_cube`), `tests/test_builtins.py` (new `class
TestNthPerfectCube`, modeled on `class TestNthPronic`, search that
name, for the test shapes above — place it near the existing `class
TestIsPerfectCube`, search that name). Once merged, `README.md`'s
existing `is_perfect_cube` bullet needs `nth_perfect_cube` added right
after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Language: `Set` literal syntax and equality (no builtin interop yet)

Build the first slice of `Set` — a genuinely new collection type, not
another `nth_*`/`is_*` builtin. Scope is deliberately narrow: **literal
syntax and `==`/`!=` equality only.** Out of scope for this task (do
not implement): `is_set`/`to_set` or any other builtin, `for`
iteration over a set, comprehensions, spread (`...`) inside a set
literal, and any mutation (no add/remove). Those are follow-up tasks
once this slice lands. Verify the gap first:
```sh
python3 -m cinder.cli eval 'print({1, 2, 3});'
# -> <eval>:1:8: ':' after map key   (bare-value `{...}` is a hard
#    parse error today — confirmed by reading `_map_pair` in
#    cinder/parser.py, which unconditionally consumes a `:` after the
#    first expression inside `{...}`)
```

**Why braces, and the one real ambiguity to resolve.** `{` is already
heavily overloaded: `cinder/parser.py`'s `_brace_statement` (search
`def _brace_statement`) treats a bare `{}` as always an empty `Block`
(never a literal), and `_map_entry` (search `def _map_entry`) has an
existing shorthand where a single bare *identifier* immediately
followed by `,` or `}` — e.g. `{x}` — parses as the map shorthand
`{x: x}`, not a one-element anything-else. Both of those are
already-shipped, tested behavior and must not change. The consequence:
**a Set literal with a single bare-identifier element (`{x}`) cannot
be added in this pass** — it's unrecoverably claimed by the map
shorthand. Resolve this the simple way, not by chasing the ambiguity:
require Set literals to have **two or more elements** in this slice
(`{1, 2}`, `{1, 2, 3}`, ...). A trailing comma is not required to force
disambiguation and single-element/empty Set literals are explicitly
out of scope — document this as a known, deliberate limitation in
`README.md`/`PROJECT.md` when done, not as a bug. (This mirrors why
the `match`-guard task in `## Graveyard` below bounced three times:
chasing one bracket-depth edge case at a time. Don't do that here —
the two-or-more-elements rule sidesteps the single ambiguous case
entirely instead of trying to disambiguate it.)

**Parser disambiguation algorithm.** Everything currently funnels
through `_map_pair` (search `def _map_pair` in `cinder/parser.py`),
which does `key = self._or()` then unconditionally consumes a `:`.
Change the first-entry parse (only — not the identifier-shorthand
branch in `_map_entry`, which stays untouched) to *peek* instead of
consume-or-throw: parse the key expression via `self._or()`, then
check whether the next token is `COLON` or not. If `COLON`: this
brace is a Map, proceed exactly as `_map_literal` does today (existing
behavior, zero regressions). If not `COLON` (i.e. `COMMA` or `RBRACE`):
this brace is a Set, and it must stay a Set — every subsequent entry
in the same `{...}` should be parsed as a bare element, and hitting a
`:` partway through (e.g. `{1, "a": 2}`) is a real `ParseError`
("mixed set/map literal" or similar), not a silent fallback. Symmetric
rule: once a brace has committed to Map (first entry had a `:` or was
the identifier shorthand), a later bare element with no `:` is also a
`ParseError`. This keeps the two literal kinds structurally
distinguishable from their very first entry, so there's no
backtracking or lookahead-N needed beyond the one-token peek after the
first key expression.

**AST + runtime.** Add `SetLiteral(elements: list, line: int, column:
int)` to `cinder/ast_nodes.py` next to `MapLiteral` (search `class
MapLiteral`). Dispatch it in `cinder/interpreter.py`'s `evaluate()`
next to the existing `isinstance(expr, MapLiteral)` branch (search
`if isinstance(expr, MapLiteral)`), calling a new
`_evaluate_set_literal`. For the runtime value backing a `Set`,
**use a `class CinderSet(dict)` wrapper** (elements become dict keys,
values unused/ignored) rather than a Python `set` — this gets you
three things for free that a raw `set` would not: (1) insertion-order
iteration/stringify, since Python `dict` preserves insertion order but
`set` does not, so output is deterministic and matches literal source
order; (2) order-insensitive equality *and* automatic de-duplication,
both via inherited `dict.__eq__`/construction semantics; (3) correct
interaction with the existing `values_equal` (`cinder/interpreter.py`,
search `def values_equal`) with no changes needed there — it already
does `type(left) is not type(right)` before comparing, so a
`CinderSet` correctly never equals a plain Map `dict` with the same
elements-as-keys, and two `CinderSet`s compare correctly via the
inherited `==`. Elements must be hashable exactly like map keys: reuse
`_is_valid_key` (search `def _is_valid_key`) and raise the same shape
of `CinderRuntimeError` as `_evaluate_map_literal` does for an invalid
key (search `is not a valid map key`), adapted to say "is not a valid
set element". Building the `CinderSet` naturally de-duplicates (`{1,
1, 2}` becomes a two-element set) — that's correct, expected behavior,
not a bug to guard against.

**`type_name`/`stringify`.** Both (`cinder/interpreter.py`, search `def
type_name` and `def stringify`) currently do `isinstance(value,
dict)` to detect maps — since `CinderSet` subclasses `dict`, that
check will wrongly catch it too unless you add an `isinstance(value,
CinderSet)` branch **before** the existing `dict` branch in both
functions. `type_name` should return `"set"`. `stringify` should
render as `{1, 2, 3}` (bare elements, comma-separated, no colons —
mirror the existing list-rendering line, not the map-rendering line).

Acceptance criteria:
- `{1, 2};`, `{1, 2, 3};`, `{"a", "b"};` parse and evaluate without
  error; `print({1, 2, 3});` outputs `{1, 2, 3}`.
- `{1, 2} == {2, 1};` is `true` (order-insensitive equality) and
  `{1, 1, 2} == {1, 2};` is `true` (de-dup on construction).
- `{1, 2} == {1, 2, 3};` is `false`; `{1, 2} != {1, 3};` is `true`.
- A Set and a Map with matching elements-as-keys are never equal:
  `{1, 2} == {1: true, 2: true};` is `false`.
- Existing behavior is unchanged (regression checks): `{}` is still an
  empty `Block` statement, not a literal; `{x}` for a bound identifier
  `x` is still the map shorthand `{x: x}`; `{"a": 1}` is still an
  ordinary map literal; `{1, "a": 2}` and `{"a": 1, 2}` (mixed
  set/map-shaped entries in one literal) both raise `ParseError`.
- Elements must be hashable: `{1, [1, 2]};` and `{1, {"a": 1}};` both
  raise `CinderRuntimeError` matching something like `"is not a valid
  set element"`.
- `type({1, 2});` (or however the language exposes `type_name`, check
  existing `type()`-builtin tests for the calling convention) is
  `"set"`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `SetLiteral`, next to
`MapLiteral`), `cinder/parser.py` (`_map_pair`/`_map_entry`/
`_map_literal`, search those names — the peek-based disambiguation
described above), `cinder/interpreter.py` (`evaluate()` dispatch,
new `_evaluate_set_literal`, new `CinderSet(dict)` class, `type_name`,
`stringify`, all searched above), `tests/test_parser.py` and
`tests/test_interpreter.py` (new test classes for parsing and
evaluating Set literals, modeled on the existing `MapLiteral` test
classes — search `TestMapLiteral` or similar for the shape). Once
merged, `README.md` needs a new `Set` entry in its features list and
`PROJECT.md`'s "Current frontier" needs refreshing, including a note
that the single-element-Set gap is a deliberate, documented limitation
of this slice — leave both to the Architect's next grooming pass, not
this task.

---

## 6. Standard library: `nth_leap_year` — leap year found at a 1-indexed position

Build: `is_leap_year` (`cinder/builtins.py`, search `def _is_leap_year`: the
Gregorian rule, `value % 4 == 0 and (value % 100 != 0 or value % 400 == 0)`,
with no lower bound — any integer, including `0` and negatives, is a valid
input) has no value-returning `nth_*` sibling. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_leap_year(1));'
# -> <eval>:1:7: undefined name 'nth_leap_year' (did you mean
#    'is_leap_year'?)
```

Worked examples: the first ten leap years under the proleptic Gregorian rule
(confirmed by scanning with `is_leap_year` directly) are `0, 4, 8, 12, 16,
20, 24, 28, 32, 36` — year `0` is itself a leap year (`0 % 100 == 0` and
`0 % 400 == 0`, same as `is_leap_year`'s own existing test coverage already
confirms via `test_is_leap_year_of_zero`), so `nth_leap_year(1)` is `0` and
`nth_leap_year(10)` is `36`. The 15th is `56`, the 20th is `76`, the 50th is
`204`. Leap years are dense (roughly one in four integers), so the scan
stays fast at every position — confirmed locally: scanning to the 50th
takes well under a millisecond in raw Python, no performance caveat needed.

Like `nth_palindrome_number` and `nth_sad_number` (both merged, both map
position `1` to candidate `0`), the scan starts at `candidate = -1`
(incremented before the first check) — `0` itself is the first leap year,
so there's no off-by-one risk skipping it.

Add directly after `_is_leap_year` (search `def _is_leap_year`, immediately
before `def _is_perfect_number`) — keeps the value-returning helper next to
the predicate it mirrors:
```python
def _nth_leap_year(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_leap_year", arguments, 1, line, column)
    value = _require_int("nth_leap_year", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_leap_year() requires a positive integer, domain error",
            line, column,
        )

    def _is_leap_year_candidate(candidate: int) -> bool:
        return candidate % 4 == 0 and (candidate % 100 != 0 or candidate % 400 == 0)

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_leap_year_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check copied verbatim from `_is_leap_year`'s own body,
since — unlike most other `nth_*` siblings here — `is_leap_year` has no
negative-input guard to strip; the scan just never needs to visit a
candidate below `0`.) Register the new dict entry (search `"is_leap_year":
_is_leap_year,`, add `"nth_leap_year": _nth_leap_year,` directly after it,
before `"is_perfect_number": _is_perfect_number,`).

Acceptance criteria:
- `nth_leap_year(1);` through `nth_leap_year(10);` are `0, 4, 8, 12, 16, 20,
  24, 28, 32, 36` in order — the worked example above.
- `nth_leap_year(15);` is `56`, `nth_leap_year(20);` is `76`, and
  `nth_leap_year(50);` is `204` — further worked examples confirming the
  scan scales well past the first ten.
- For every `position` in `1..50`, `is_leap_year(nth_leap_year(position))`
  is `true` — the same self-consistency check every recent `nth_*` task's
  own test suite already runs against its predicate.
- `nth_leap_year(0);`, `nth_leap_year(-3);` both raise `CinderRuntimeError`
  matching `"nth_leap_year\(\) requires a positive integer, domain error"`.
- `nth_leap_year(true);` raises `CinderRuntimeError` matching
  `"nth_leap_year\(\) requires an int, got bool"`.
- `nth_leap_year("5");` raises `CinderRuntimeError` matching
  `"nth_leap_year\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_leap_year`, search
`def _is_leap_year`), `tests/test_builtins.py` (new `class TestNthLeapYear`,
modeled on `class TestNthUndulating`, search that name, for the test shapes
above — place it near the existing `class TestIsLeapYear`, search that
name). Once merged, `README.md`'s existing `is_leap_year` bullet needs
`nth_leap_year` added right after it, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs refreshing —
leave both to the Architect's next grooming pass, not this task.

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

**Resolved 2026-09-08, merged as `#413`.** Requeued 2026-09-07 with
exactly the alternative strategy this postmortem called for (parse the
guard via the parser's ordinary `_ternary()` entry point instead of any
hand-rolled bracket/token scan) — that fix took two more review rounds
(a call/list/index/grouping leak, then a nested-`match` leak) before
landing clean, but never regressed to the original `_bracket_depth`
bug class this postmortem was about. See `CHANGELOG.md` for the full
three-round history.
