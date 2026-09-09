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

## 1. Language: `Set` literal syntax and equality (no builtin interop yet) [claimed 2026-09-09T19:34:10Z]

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

## 2. Standard library: `nth_leap_year` — leap year found at a 1-indexed position

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

## 3. Standard library: `nth_perfect_power` — perfect power found at a 1-indexed position

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
`nth_perfect_square`, and `nth_perfect_cube` (already-merged siblings),
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

## 4. Standard library: `rot13` — the classic Caesar-cipher string transform

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

## 5. Standard library: `to_roman` — convert an integer to a Roman numeral string

Add a standalone conversion builtin, not another `is_*`/`nth_*` pair —
that gap list stayed exhausted this pass too (re-audited the full
`is_*`-without-`nth_*` diff programmatically: every unpaired name is
still one of the already-rejected categories — multi-arg, string/list-
shaped with no integer ordering, a type predicate, or one of the
confirmed-too-sparse-or-slow names from earlier passes' History
entries — nothing new). `to_roman` sits next to `to_hex`/`to_bin`/
`to_oct` (`cinder/builtins.py`, search `def _to_oct`) as another
base-conversion-flavored single-int-argument transform, but with a
bounded domain (traditional Roman numerals only cover 1-3999) instead
of those three's unbounded one. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(to_roman(2026));'
# -> <eval>:1:7: undefined name 'to_roman'
```

**What it does.** Greedily subtract the largest Roman value/symbol
pair (including the six subtractive pairs `CM`, `CD`, `XC`, `XL`,
`IX`, `IV`) that still fits, appending its symbol each time, until the
input reaches zero — the standard greedy algorithm, which is optimal
for the fixed set of Roman symbols (always produces the canonical
minimal-length numeral, no backtracking needed). No reverse direction
(`from_roman`) in this task — mirrors `rot13`/`to_hex`/`to_bin`/`to_oct`,
which are all one-directional too; a `from_roman` parser is a natural
follow-up once this lands, left for a future pass.

**Scope: 1 to 3999 inclusive.** Roman numerals have no symbol for zero
or negative numbers, and the standard 7-symbol system (`I V X L C D M`)
cannot represent 4000 or above without inventing a non-standard
extension (e.g. overline/vinculum notation) — out of scope. `0`,
negative integers, and any integer `>= 4000` are all domain errors.

Worked examples (confirmed via direct computation of the greedy
algorithm below):
- `to_roman(1)` is `"I"`, `to_roman(4)` is `"IV"`, `to_roman(9)` is
  `"IX"`.
- `to_roman(14)` is `"XIV"`, `to_roman(40)` is `"XL"`, `to_roman(49)`
  is `"XLIX"`, `to_roman(90)` is `"XC"`.
- `to_roman(444)` is `"CDXLIV"`, `to_roman(499)` is `"CDXCIX"`,
  `to_roman(900)` is `"CM"`, `to_roman(944)` is `"CMXLIV"`.
- `to_roman(1994)` is `"MCMXCIV"` (the canonical "year" example every
  Roman-numeral kata uses).
- `to_roman(2026)` is `"MMXXVI"` (this project's current year, a nice
  sanity check).
- `to_roman(3999)` is `"MMMCMXCIX"` — the largest representable value.

Add directly after `_to_oct` (search `def _to_oct`, immediately before
`def _push`) — keeps the new conversion builtin next to its closest
siblings:
```python
_ROMAN_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def _to_roman(arguments: list, line: int, column: int) -> object:
    _require_arity("to_roman", arguments, 1, line, column)
    value = _require_int("to_roman", arguments[0], line, column)
    if value < 1 or value > 3999:
        raise CinderRuntimeError(
            "to_roman() requires an integer between 1 and 3999, domain error",
            line, column,
        )
    result = []
    remaining = value
    for amount, symbol in _ROMAN_VALUES:
        while remaining >= amount:
            result.append(symbol)
            remaining -= amount
    return "".join(result)
```
Register the new dict entry (search `"to_oct": _to_oct,`, add
`"to_roman": _to_roman,` directly after it, before `"push": _push,`).

Acceptance criteria:
- Every worked example above holds exactly, including `to_roman(1994)`
  is `"MCMXCIV"` and `to_roman(2026)` is `"MMXXVI"`.
- `to_roman(1);` is `"I"` and `to_roman(3999);` is `"MMMCMXCIX"` — the
  domain's two boundary values.
- All six subtractive pairs appear correctly across the worked
  examples: `IV`, `IX`, `XL`, `XC`, `CD`, `CM`.
- `to_roman(0);`, `to_roman(-1);`, and `to_roman(4000);` all raise
  `CinderRuntimeError` matching `"to_roman\(\) requires an integer
  between 1 and 3999, domain error"`.
- `to_roman(1.5);` raises `CinderRuntimeError` matching `"to_roman\(\)
  requires an int, got float"` (mirror `to_hex`'s own non-int test for
  the exact message shape).
- `to_roman("5");` raises `CinderRuntimeError` matching `"to_roman\(\)
  requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_to_oct`, search
`def _to_oct`), `tests/test_builtins.py` (new `class TestToRoman`,
modeled on `class TestToHex`, search that name, for the test shapes
above — place it near the existing `class TestToHex`/`class
TestToBin`/`class TestToOct`). Once merged, `README.md`'s existing
`to_oct` bullet needs `to_roman` added right after it, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
section needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 6. Standard library: `from_roman` — parse a Roman numeral string back to an integer

Add the natural inverse of `to_roman` (task 5 above, must merge first —
this task reuses its `_ROMAN_VALUES` table). Verify the gap once task 5
has landed:
```sh
python3 -m cinder.cli eval 'print(from_roman("MMXXVI"));'
# -> <eval>:1:7: undefined name 'from_roman'
```

**What it does.** Greedily strip the largest matching symbol/pair from
the front of the string (same `_ROMAN_VALUES` list `to_roman` walks,
search `_ROMAN_VALUES`), accumulating its value, until the string is
exhausted or nothing more matches. **Canonical numerals only**: reject
anything that isn't exactly what `to_roman` itself would have produced.
The simplest correct way to enforce that is a round-trip check —
after decoding, re-encode the total with `_to_roman` and require it to
equal the original input verbatim — rather than writing a separate
validation pass. This single check catches every malformed case for
free: leftover unconsumed characters (out-of-order symbols like `"VX"`
or `"IC"`), non-canonical repetition (`"IIII"` decodes to `4` but
re-encodes to `"IV"`, not `"IIII"`), lowercase input, and empty input
(decodes to `0`, outside the `1..3999` domain).

Worked examples (inverse of `to_roman`'s own worked examples, confirmed
by direct computation of the algorithm below, including a full
round-trip check of every integer `1..3999` through `to_roman` then
back through `from_roman`):
- `from_roman("I")` is `1`, `from_roman("IV")` is `4`, `from_roman("IX")`
  is `9`.
- `from_roman("XIV")` is `14`, `from_roman("XL")` is `40`,
  `from_roman("XLIX")` is `49`, `from_roman("XC")` is `90`.
- `from_roman("CDXLIV")` is `444`, `from_roman("CDXCIX")` is `499`,
  `from_roman("CM")` is `900`, `from_roman("CMXLIV")` is `944`.
- `from_roman("MCMXCIV")` is `1994`, `from_roman("MMXXVI")` is `2026`,
  `from_roman("MMMCMXCIX")` is `3999`.
- `from_roman(to_roman(n))` equals `n` for every `n` in `1..3999`.

Add directly after `_to_roman` (search `def _to_roman`, immediately
before `def _push`) — keeps the inverse next to its sibling:
```python
def _from_roman(arguments: list, line: int, column: int) -> object:
    _require_arity("from_roman", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"from_roman() requires a string, got {type_name(value)}", line, column
        )
    remaining = value
    total = 0
    for amount, symbol in _ROMAN_VALUES:
        while remaining.startswith(symbol):
            total += amount
            remaining = remaining[len(symbol):]
    valid = (
        not remaining
        and 1 <= total <= 3999
        and _to_roman([total], line, column) == value
    )
    if not valid:
        raise CinderRuntimeError(
            f"from_roman() '{value}' is not a valid canonical Roman numeral, "
            "domain error",
            line, column,
        )
    return total
```
(The `and`-chain short-circuits, so `_to_roman([total], ...)` — which
itself raises outside the `1..3999` domain — is only called once
`total` is already known to be in range.) Register the new dict entry
(search `"to_roman": _to_roman,`, add `"from_roman": _from_roman,`
directly after it, before `"push": _push,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `from_roman("MCMXCIV")` is `1994` and `from_roman("MMXXVI")` is `2026`.
- `from_roman("I");` is `1` and `from_roman("MMMCMXCIX");` is `3999` —
  the domain's two boundary values.
- `from_roman(to_roman(n));` equals `n` for at least a representative
  spread of `n` (e.g. `1, 4, 9, 40, 49, 90, 444, 900, 1994, 2026, 3999`)
  — the round-trip property.
- Non-canonical strings that a naive symbol-sum would wrongly accept
  all raise `CinderRuntimeError` matching `"from_roman\(\) '.*' is not
  a valid canonical Roman numeral, domain error"`: `from_roman("IIII")`
  (non-canonical `4`), `from_roman("VX")` and `from_roman("IC")`
  (out-of-order symbols), `from_roman("");` (empty).
- `from_roman("mmxxvi");` (lowercase) also raises the same domain error.
- `from_roman(2026);` raises `CinderRuntimeError` matching
  `"from_roman\(\) requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_to_roman`, search
`def _to_roman`), `tests/test_builtins.py` (new `class TestFromRoman`,
modeled on `class TestToRoman`, search that name, for the test shapes
above — place it near the existing `class TestToRoman`). Once merged,
`README.md`'s existing `to_roman` bullet needs `from_roman` added right
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
