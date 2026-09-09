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

## 1. Standard library: `nth_perfect_cube` — perfect cube found at a 1-indexed position [claimed 2026-09-09T14:43:47Z]

Build: `is_perfect_cube` (`cinder/builtins.py`, search `def
_is_perfect_cube`: a non-negative integer whose integer cube root,
cubed, equals it back — `root = _integer_cube_root(magnitude); root **
3 == magnitude`) has no value-returning `nth_*` sibling, the same gap
`nth_power_of_two`/`nth_perfect_square` (already-merged siblings)
already close for their own closed-form sequences.
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

## 2. Language: `Set` literal syntax and equality (no builtin interop yet)

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

## 3. Standard library: `nth_leap_year` — leap year found at a 1-indexed position

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

## 4. Standard library: `nth_perfect_power` — perfect power found at a 1-indexed position

Build: `is_perfect_power` (`cinder/builtins.py`, search `def
_is_perfect_power`: true for `-1`, `0`, and `1` outright, otherwise true
when `abs(value)` is `root ** k` for some integer `root` and some `k >=
2`, with negative values only counted when the matching `k` is odd, e.g.
`-8 == -2 ** 3`) has no value-returning `nth_*` sibling. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_perfect_power(1));'
# -> <eval>:1:7: undefined name 'nth_perfect_power' (did you mean
#    'is_perfect_power'?)
```

**Scope: non-negative candidates only.** Unlike every other `nth_*`
builtin in this codebase, `is_perfect_power` accepts negative input
(`-8`, `-27`, ... are perfect powers via odd `k`). A single monotonic
1-indexed position scan can't sensibly interleave negative and
non-negative results in one ordering, and every existing `nth_*`
builtin here already scans non-negative candidates only — so this task
keeps that convention and scans `candidate >= 0` exclusively.
`is_perfect_power`'s negative-domain support stays a predicate-only
feature; document this as a deliberate scope limit in `README.md` when
done, not a bug (mirrors the two-or-more-elements limit already
documented for the `Set`-literal task above).

Worked examples: the first ten non-negative perfect powers (confirmed
by scanning with `is_perfect_power` directly) are `0, 1, 4, 8, 9, 16,
25, 27, 32, 36` — `0` and `1` both satisfy the predicate's `abs(value)
<= 1` shortcut, so both are trivially perfect powers before the
square/cube/... scan ever runs. `nth_perfect_power(1)` is `0` and
`nth_perfect_power(10)` is `36`. The 15th is `121`, the 20th is `196`,
the 50th is `1444`. Perfect powers get sparser as they grow (unlike the
dense `nth_*` sequences merged so far), but still dense enough to reach
the 50th term well under a millisecond in raw Python — confirmed
locally, no performance caveat needed. Unlike `nth_power_of_two`,
`nth_perfect_square`, and `nth_perfect_cube` (queued as task 1 above),
which are each a single sequence with an exact closed form, perfect
powers are the *union* of every `k >= 2` power sequence with no single
closed form — this task needs an actual bounded scan against the
existing predicate, the same shape as `nth_composite`/`nth_evil`, not a
closed-form task.

Like `nth_palindrome_number` (already-merged sibling) and `nth_leap_year`
(queued above, both map position `1` to candidate `0`), the scan starts
at `candidate = -1`
(incremented before the first check) — `0` itself is the very first
perfect power, so there's no off-by-one risk skipping it.

Add directly after `_is_perfect_power` (search `def
_is_perfect_power`, immediately before `def _divisors`) — keeps the
value-returning helper next to the predicate it mirrors:
```python
def _nth_perfect_power(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_perfect_power", arguments, 1, line, column)
    value = _require_int("nth_perfect_power", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_perfect_power() requires a positive integer, domain error",
            line, column,
        )

    def _is_perfect_power_candidate(candidate: int) -> bool:
        if candidate <= 1:
            return True
        for k in range(2, candidate.bit_length() + 1):
            root = _integer_kth_root(candidate, k)
            if root ** k == candidate:
                return True
        return False

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_perfect_power_candidate(candidate):
            count += 1
    return candidate
```
(Inner candidate check reuses the module-level `_integer_kth_root`
helper directly — same function `_is_perfect_power` itself calls, no
duplication — but drops the sign branch entirely since the scan never
visits a negative candidate.) Register the new dict entry (search
`"is_perfect_power": _is_perfect_power,`, add `"nth_perfect_power":
_nth_perfect_power,` directly after it, before `"divisors":
_divisors,`).

Acceptance criteria:
- `nth_perfect_power(1);` through `nth_perfect_power(10);` are `0, 1,
  4, 8, 9, 16, 25, 27, 32, 36` in order — the worked example above.
- `nth_perfect_power(15);` is `121`, `nth_perfect_power(20);` is `196`,
  and `nth_perfect_power(50);` is `1444` — further worked examples
  confirming the scan scales well past the first ten.
- For every `position` in `1..50`,
  `is_perfect_power(nth_perfect_power(position))` is `true` — the same
  self-consistency check every recent `nth_*` task's own test suite
  already runs against its predicate.
- `nth_perfect_power(0);`, `nth_perfect_power(-3);` both raise
  `CinderRuntimeError` matching `"nth_perfect_power\(\) requires a
  positive integer, domain error"`.
- `nth_perfect_power(true);` raises `CinderRuntimeError` matching
  `"nth_perfect_power\(\) requires an int, got bool"`.
- `nth_perfect_power("5");` raises `CinderRuntimeError` matching
  `"nth_perfect_power\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_perfect_power`,
search `def _is_perfect_power`), `tests/test_builtins.py` (new `class
TestNthPerfectPower`, modeled on `class TestNthComposite`, search that
name, for the test shapes above — place it near the existing `class
TestIsPerfectPower`, search that name). Once merged, `README.md`'s
existing `is_perfect_power` bullet needs `nth_perfect_power` added
right after it, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `rot13` — the classic Caesar-cipher string transform

Add a standalone string builtin, not another `is_*`/`nth_*` pair — the
`is_*`-without-`nth_*` gap list is nearly exhausted for now (see this
pass's `PROJECT.md` "Current frontier" note: `is_automorphic`,
`is_keith_number`, and a derived single-arg `is_amicable_number` were
all scouted and rejected this session as too sparse/slow for a bounded
scan, joining `is_armstrong`/`is_disarium`/`is_weird_number`/
`is_strong_number` rejected in earlier passes). `rot13` sits next to
`swap_case` (`cinder/builtins.py`, search `def _swap_case`) as another
simple, total, single-string-argument transform with no domain errors
possible once the type check passes — the same shape `reverse_int`/
`swap_case` themselves already are. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(rot13("hello"));'
# -> <eval>:1:7: undefined name 'rot13'
```

**What it does.** Rotate every ASCII letter 13 places through its own
case's alphabet, wrapping `z`->`m`, `Z`->`M`; leave every non-letter
character (digits, punctuation, spaces, non-ASCII) untouched. Applying
`rot13` twice always returns the original string — it is its own
inverse, since shifting by 13 twice is a shift by 26, a full wrap of a
26-letter alphabet.

Worked examples (confirmed via Python's own `codecs.encode(s, "rot13")`):
- `rot13("hello")` is `"uryyb"`.
- `rot13("Hello, World!")` is `"Uryyb, Jbeyq!"` (case preserved per
  letter, punctuation/space/comma untouched).
- `rot13("")` is `""`.
- `rot13("abcXYZ")` is `"nopKLM"`.
- `rot13("The Quick Brown Fox")` is `"Gur Dhvpx Oebja Sbk"`.
- `rot13(rot13("Hello, World!"))` is `"Hello, World!"` — the
  self-inverse property.

Add directly after `_swap_case` (search `def _swap_case`, immediately
before `def _is_palindrome`) — keeps the new string transform next to
its closest sibling:
```python
def _rot13(arguments: list, line: int, column: int) -> object:
    _require_arity("rot13", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"rot13() requires a string, got {type_name(value)}", line, column
        )
    result = []
    for ch in value:
        if "a" <= ch <= "z":
            result.append(chr((ord(ch) - ord("a") + 13) % 26 + ord("a")))
        elif "A" <= ch <= "Z":
            result.append(chr((ord(ch) - ord("A") + 13) % 26 + ord("A")))
        else:
            result.append(ch)
    return "".join(result)
```
(Same shape as `_swap_case`/`_is_palindrome` — arity check, a single
`isinstance(value, str)` type check with no domain/length restriction,
then a total transform.) Register the new dict entry (search
`"swap_case": _swap_case,`, add `"rot13": _rot13,` directly after it,
before `"trim": _trim,`).

Acceptance criteria:
- `rot13("hello");` is `"uryyb"`, `rot13("abcXYZ");` is `"nopKLM"` — the
  worked examples above.
- `rot13("Hello, World!");` is `"Uryyb, Jbeyq!"` and
  `rot13("The Quick Brown Fox");` is `"Gur Dhvpx Oebja Sbk"` — case and
  non-letter characters both handled correctly in the same string.
- `rot13("");` is `""`.
- For every string in a small worked-example set (at least the five
  above), `rot13(rot13(s))` equals `s` — the self-inverse property.
- `rot13(123);` raises `CinderRuntimeError` matching `"rot13\(\)
  requires a string, got int"` (mirror `swap_case`'s own non-string
  test for the exact message shape).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_swap_case`, search
`def _swap_case`), `tests/test_builtins.py` (new `class TestRot13`,
modeled on `class TestSwapCase`, search that name, for the test shapes
above — place it near the existing `class TestSwapCase`). Once merged,
`README.md`'s existing `swap_case` bullet needs `rot13` added right
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

**Resolved 2026-09-08, merged as `#413`.** Requeued 2026-09-07 with
exactly the alternative strategy this postmortem called for (parse the
guard via the parser's ordinary `_ternary()` entry point instead of any
hand-rolled bracket/token scan) — that fix took two more review rounds
(a call/list/index/grouping leak, then a nested-`match` leak) before
landing clean, but never regressed to the original `_bracket_depth`
bug class this postmortem was about. See `CHANGELOG.md` for the full
three-round history.
