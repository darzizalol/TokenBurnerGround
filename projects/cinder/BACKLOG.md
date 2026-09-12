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

## 1. Standard library: `nth_armstrong` — the k-th Armstrong (narcissistic) number [claimed 2026-09-12T19:56:19Z, bounced once on QA — see note below]

Add directly after `_is_armstrong` (`cinder/builtins.py`, search `def
_is_armstrong`, immediately before `def _is_disarium`) — the same
value-returning-sibling gap `nth_weird_number` (shipped) closed for
`is_weird_number` (and `nth_perfect_number`, shipped, already closed for
`is_perfect_number`), here for `is_armstrong`: a
positive integer equal to the sum of its own digits each raised to the
power of the digit count (`153 = 1^3 + 5^3 + 3^3`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_armstrong(1));'
# -> <eval>:1:7: undefined name 'nth_armstrong' (did you mean 'is_armstrong'?)
```

**QA finding on PR #456 (open, one bounce so far):** the straightforward
linear-scan implementation originally suggested below (still shown
first, for context) passed review and the tested worked examples
(`k <= 15`) but got `QA: FAIL` — Armstrong numbers thin out fast per
digit length (most digit-lengths have zero of them), so incrementing
candidate-by-candidate degrades badly once `k` grows: `nth_armstrong(25)`
took 11.6s and `nth_armstrong(30)` didn't finish in a 15s timeout, well
within the function's documented domain of "any positive integer, no
upper bound." The fix below (verified directly in Python against the
QA-reported values) generates candidates per digit-length from digit
*multisets* (`itertools.combinations_with_replacement`, already imported
in this module) instead of scanning every integer — this shrinks the
search from "every integer up to the answer" to "every combination of
`length` digits," which is astronomically smaller (e.g. length 8 is
`C(17, 9) = 24310` combinations, not `10^8` integers) while still
reusing `_is_armstrong_candidate` as the authoritative check, so the two
functions' notion of "Armstrong" still can't drift apart. Confirmed:
`nth_armstrong(25)` still returns `9926315` (matching QA's own number,
now in well under a second) and `nth_armstrong(30)` returns
`472335975` in ~0.2s instead of timing out. The next Engineer session
reworking PR #456 should replace the implementation with this one
rather than patching the linear scan.

**What it does.** Given a positive integer `k`, return the `k`-th
Armstrong number (1-indexed, starting from `0`) — the same condition
`_is_armstrong` already checks, applied here as a sequential scan
exactly like `_nth_perfect_number` and `_nth_weird_number` (both
shipped) already do, for their own predicates. Unlike
`nth_perfect_number`'s perfect numbers, Armstrong numbers are cheap to test (a digit-sum-of-powers check, not trial
division) and stay dense enough through this task's range for a plain
scan to finish instantly — the single-digit numbers `0`-`9` are all
trivially Armstrong numbers (any one digit raised to the power `1` is
itself), then the next one doesn't appear until `153`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `nth_armstrong(1)` is `0`.
- `nth_armstrong(2)` is `1`.
- `nth_armstrong(10)` is `9` — the last of the ten trivial single-digit
  Armstrong numbers.
- `nth_armstrong(11)` is `153` — the first multi-digit Armstrong
  number.
- `nth_armstrong(12)` is `370`.
- `nth_armstrong(13)` is `371`.
- `nth_armstrong(14)` is `407`.
- `nth_armstrong(15)` is `1634`.
- `nth_armstrong(0);` raises `CinderRuntimeError` — domain error, same
  convention `nth_perfect_number(0)`/`nth_weird_number(0)` already use.
- `nth_armstrong(-1);` raises `CinderRuntimeError` — domain error.
- `nth_armstrong(1.5);` raises `CinderRuntimeError` — not an int.
- `nth_armstrong("a");` raises `CinderRuntimeError` — not an int.

Add directly after `_is_armstrong` (search `def _is_armstrong`,
immediately before `def _is_disarium`) — this is the fixed version; see
the QA note above for why the original plain-scan version (kept out of
this spec now) isn't good enough:
```python
def _nth_armstrong(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_armstrong", arguments, 1, line, column)
    value = _require_int("nth_armstrong", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_armstrong() requires a positive integer, domain error", line, column
        )

    def _is_armstrong_candidate(candidate: int) -> bool:
        digits = str(candidate)
        power = len(digits)
        return sum(int(digit) ** power for digit in digits) == candidate

    def _armstrong_numbers_with_digit_count(length: int) -> list:
        lower = 0 if length == 1 else 10 ** (length - 1)
        upper = 10 ** length - 1
        found = set()
        for combo in itertools.combinations_with_replacement(range(10), length):
            power_sum = sum(digit ** length for digit in combo)
            if lower <= power_sum <= upper and _is_armstrong_candidate(power_sum):
                found.add(power_sum)
        return sorted(found)

    count = 0
    length = 1
    while True:
        for candidate in _armstrong_numbers_with_digit_count(length):
            count += 1
            if count == value:
                return candidate
        length += 1
```
(`_is_armstrong_candidate` mirrors `_is_armstrong`'s own digit-power-sum
check exactly — including counting `0` as the first Armstrong number,
same as `_is_armstrong(0)` already returns `True` — so the two
functions' notion of "Armstrong" can't silently drift apart; same
reuse-the-sibling-predicate's-exact-logic discipline `_nth_perfect_number`
and `_nth_weird_number` (both shipped) use for
`_is_perfect_number`/`_is_weird_number`. Every candidate this generates
is still verified through `_is_armstrong_candidate` before being
counted — the multiset generation only changes *which integers get
tested*, not the definition of "Armstrong" itself, and the `set()`
guards against the same power sum theoretically being reachable from
more than one digit combination. `itertools` is already imported at the
top of this module, used by other builtins.) Register the new dict
entry (search `"is_armstrong": _is_armstrong,`, add `"nth_armstrong":
_nth_armstrong,` directly after it, before `"is_disarium":
_is_disarium,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `nth_armstrong(1)` is `0`, `nth_armstrong(10)` is `9`, and
  `nth_armstrong(15)` is `1634`.
- `nth_armstrong(0);` and `nth_armstrong(-1);` both raise
  `CinderRuntimeError` matching `"nth_armstrong\(\) requires a
  positive integer, domain error"`.
- `nth_armstrong(1.5);` and `nth_armstrong("a");` both raise
  `CinderRuntimeError` matching `"nth_armstrong\(\) requires an int,
  got (float|string)"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- **Performance (added after PR #456's QA bounce):** `nth_armstrong(30)`
  must return `472335975` in well under a second, and `nth_armstrong(25)`
  must return `9926315` — both trivial for the digit-multiset
  implementation above, both the exact cases that timed out (`30`) or
  took 11.6s (`25`) under the original plain-scan version. Add a test
  asserting `nth_armstrong(30)` specifically, so a future regression
  back to a linear scan gets caught by the test suite, not QA.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_armstrong`,
search `def _is_armstrong`), `tests/test_builtins.py` (new `class
TestNthArmstrong`, modeled on `class TestNthPerfectNumber`/`class
TestNthWeirdNumber` (both shipped), search either name, for the
test shapes above — place it near the existing `class
TestIsArmstrong`). Once merged, `README.md`'s builtins quick-reference
list (search `is_armstrong`) needs `nth_armstrong` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `percentile` — p-th percentile of a numeric list (linear interpolation)

Add directly after `_midrange` (`cinder/builtins.py`, search `def
_midrange`, immediately before `def _population_variance`) — a real
gap in the `mean`/`median`/`midrange`/`variance`/`std_dev`/`mode`
statistics cluster: none of those existing builtins let a caller ask
for an arbitrary rank between minimum and maximum, only the fixed 0th/
50th/100th-percentile-shaped ones (`min`/`max` from elsewhere,
`median`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(percentile([1, 2, 3, 4, 5], 50));'
# -> <eval>:1:7: undefined name 'percentile' (did you mean 'midrange'?)
```

**What it does.** Given a non-empty list of numbers and a rank `p` in
`[0, 100]`, return the `p`-th percentile using linear interpolation
between the two nearest ranks (the same method `numpy.percentile`
calls `"linear"`, its default): sort the list, compute `index = (p /
100) * (n - 1)` (0-indexed, `n` = list length), then if `index` lands
exactly on an element return it directly, otherwise linearly
interpolate between `ordered[floor(index)]` and `ordered[ceil(index)]`
by the fractional part of `index`. This makes `percentile(list, 50)`
always exactly equal `median(list)`, for both odd- and even-length
lists — a useful cross-check when testing.

Worked examples (confirmed via direct computation of the algorithm
below):
- `percentile([1, 2, 3, 4, 5], 50)` is `3` — `index = 2`, lands exactly
  on `ordered[2]`.
- `percentile([1, 2, 3, 4, 5], 25)` is `2` — `index = 1`.
- `percentile([1, 2, 3, 4, 5], 75)` is `4` — `index = 3`.
- `percentile([1, 2, 3, 4, 5], 0)` is `1` and `percentile([1, 2, 3, 4,
  5], 100)` is `5` — the endpoints.
- `percentile([1, 2, 3, 4], 50)` is `2.5` — `index = 1.5`, interpolates
  halfway between `ordered[1] = 2` and `ordered[2] = 3`; matches
  `median([1, 2, 3, 4])` exactly, as the cross-check above predicts.
- `percentile([5], 37)` is `5` — single-element list, every percentile
  returns the one element; not a division-by-zero case (`n - 1 = 0`
  makes `index` always `0` regardless of `p`).
- `percentile([], 50);` raises `CinderRuntimeError` — no elements.
- `percentile([1, 2, 3], 150);` and `percentile([1, 2, 3], -5);` both
  raise `CinderRuntimeError` — `p` outside `[0, 100]` is a domain
  error, not clamped.

Add directly after `_midrange` (search `def _midrange`, immediately
before `def _population_variance`):
```python
def _percentile(arguments: list, line: int, column: int) -> object:
    _require_arity("percentile", arguments, 2, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"percentile() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("percentile() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"percentile() requires a list of numbers, got {type_name(element)}", line, column
            )
    rank = arguments[1]
    if not _is_numeric(rank):
        raise CinderRuntimeError(
            f"percentile() requires a number for its second argument, got {type_name(rank)}",
            line, column,
        )
    if rank < 0 or rank > 100:
        raise CinderRuntimeError(
            "percentile() requires a number between 0 and 100 for its second argument, domain error",
            line, column,
        )
    ordered = sorted(value)
    index = (rank / 100) * (len(ordered) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
```
(Reuses `_is_numeric`/`type_name`/`_require_arity` the same way every
sibling statistics builtin does; `math.floor`/`math.ceil` are already
imported in this module for `nth_perfect_number`/`nth_weird_number`.)
Register the new dict entry (search `"midrange": _midrange,`, add
`"percentile": _percentile,` directly after it, before `"variance":
_variance,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `percentile([1, 2, 3, 4], 50)` is `2.5` and `percentile([5], 37)` is
  `5`.
- `percentile(list, 50)` equals `median(list)` exactly for at least one
  odd-length and one even-length list (the cross-check above).
- `percentile([]` , `50);` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a non-empty list"`.
- `percentile(123, 50);` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a list, got int"`.
- `percentile([1, "a"], 50);` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a list of numbers, got string"`.
- `percentile([1, 2, 3], "a");` raises `CinderRuntimeError` matching
  `"percentile\(\) requires a number for its second argument, got
  string"`.
- `percentile([1, 2, 3], 150);` and `percentile([1, 2, 3], -5);` both
  raise `CinderRuntimeError` matching `"percentile\(\) requires a
  number between 0 and 100.*domain error"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_midrange`, search
`def _midrange`), `tests/test_builtins.py` (new `class TestPercentile`,
modeled on `class TestMedian`/`class TestMidrange`, search either name,
for the test shapes above — place it near the existing `class
TestMidrange`). Once merged, `README.md`'s builtins quick-reference
list (search `midrange`) needs `percentile` added right after it, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's
next grooming pass, not this task.

---

## 3. Standard library: `nth_automorphic` — the k-th automorphic number

Add directly after `_is_automorphic` (`cinder/builtins.py`, search `def
_is_automorphic`, immediately before `def _is_trimorphic_number`) — the
same value-returning-sibling gap `nth_perfect_number` and
`nth_weird_number` (both shipped) close for
`is_perfect_number`/`is_weird_number`, and task 1 above
(`nth_armstrong`) will close for `is_armstrong`, here for
`is_automorphic`, the one member of the automorphic/trimorphic pair
still missing it (`is_trimorphic_number` already has
`nth_trimorphic_number`, immediately below `_is_automorphic` in the
file — same shape, `value * value` instead of `value ** 3`). Verify
the gap:
```sh
python3 -m cinder.cli eval 'print(nth_automorphic(1));'
# -> <eval>:1:7: undefined name 'nth_automorphic' (did you mean 'is_automorphic'?)
```

**What it does.** Given a positive integer `k`, return the `k`-th
automorphic number (1-indexed, starting from `0`) — a non-negative
integer whose square ends with the integer itself in decimal (e.g.
`25` is automorphic since `25 ** 2 == 625`, which ends with `25`) —
the same condition `_is_automorphic` already checks, applied here as a
sequential scan exactly like `_nth_trimorphic_number` already does for
its own predicate. Checking a candidate is a single squaring plus a
string-suffix check (no trial division), so unlike `nth_perfect_number`'s
perfect numbers this stays cheap indefinitely — no test-scope cap is needed.

Worked examples (confirmed via direct computation of the algorithm
below):
- `nth_automorphic(1)` is `0`.
- `nth_automorphic(2)` is `1`.
- `nth_automorphic(3)` is `5`.
- `nth_automorphic(4)` is `6`.
- `nth_automorphic(5)` is `25`.
- `nth_automorphic(6)` is `76`.
- `nth_automorphic(7)` is `376`.
- `nth_automorphic(8)` is `625`.
- `nth_automorphic(9)` is `9376`.
- `nth_automorphic(10)` is `90625`.
- `nth_automorphic(0);` raises `CinderRuntimeError` — domain error, same
  convention `nth_trimorphic_number(0)` already uses.
- `nth_automorphic(-1);` raises `CinderRuntimeError` — domain error.
- `nth_automorphic(1.5);` raises `CinderRuntimeError` — not an int.
- `nth_automorphic("a");` raises `CinderRuntimeError` — not an int.

Add directly after `_is_automorphic` (search `def _is_automorphic`,
immediately before `def _is_trimorphic_number`):
```python
def _nth_automorphic(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_automorphic", arguments, 1, line, column)
    value = _require_int("nth_automorphic", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_automorphic() requires a positive integer, domain error",
            line, column,
        )

    def _is_automorphic_candidate(candidate: int) -> bool:
        return str(candidate * candidate).endswith(str(candidate))

    count = 0
    candidate = -1
    while count < value:
        candidate += 1
        if _is_automorphic_candidate(candidate):
            count += 1
    return candidate
```
(`_is_automorphic_candidate` mirrors `_is_automorphic`'s own
square-and-check-suffix logic exactly, so the two functions' notion of
"automorphic" can't silently drift apart — same
reuse-the-sibling-predicate's-exact-logic discipline `_nth_perfect_number`/
`_nth_weird_number` (both shipped) and task 1's `_nth_armstrong` use,
and the same `candidate` starting at `-1`
that `_nth_trimorphic_number`
already uses, since `0` itself is a valid automorphic number here and
must be reachable as `nth_automorphic(1)`.) Register the new dict
entry (search `"is_automorphic": _is_automorphic,`, add
`"nth_automorphic": _nth_automorphic,` directly after it, before
`"is_trimorphic_number": _is_trimorphic_number,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `nth_automorphic(1)` is `0` through `nth_automorphic(10)` is `90625`.
- `nth_automorphic(0);` and `nth_automorphic(-1);` both raise
  `CinderRuntimeError` matching `"nth_automorphic\(\) requires a
  positive integer, domain error"`.
- `nth_automorphic(1.5);` and `nth_automorphic("a");` both raise
  `CinderRuntimeError` matching `"nth_automorphic\(\) requires an int,
  got (float|string)"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_automorphic`,
search `def _is_automorphic`), `tests/test_builtins.py` (new `class
TestNthAutomorphic`, modeled on `class TestNthTrimorphicNumber`, search
that name, for the test shapes above — place it near the existing
`class TestIsAutomorphic`). Once merged, `README.md`'s builtins
quick-reference list (search `is_automorphic`) needs `nth_automorphic`
added right after it, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" section needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `to_snake_case` — convert a string to `snake_case`

Add directly after `_caesar_cipher` (`cinder/builtins.py`, search `def
_caesar_cipher`, immediately before `def _is_palindrome`) — a real gap
in the case-conversion cluster: `capitalize`/`title`/`swap_case`/
`upper`/`lower` all transform character casing in place, but none of
them re-tokenize a string into words and rejoin it in a different case
convention. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(to_snake_case("helloWorld"));'
# -> <eval>:1:7: undefined name 'to_snake_case' (did you mean 'is_lower'?)
```

**What it does.** Given a string, split it into words on three kinds
of boundary — existing whitespace/hyphen/underscore runs, a lowercase-
or-digit-to-uppercase transition (`helloWorld` -> `hello`/`World`), and
an acronym-to-word transition (`HTTPServer` -> `HTTP`/`Server`) — then
lowercase every word and join them with single underscores, trimming
any leading/trailing underscore. This is the standard "words" tokenizer
lodash-style case-conversion helpers use, generalized to handle
already-separated input (spaces, hyphens, underscores) and camelCase/
PascalCase/acronym input uniformly.

Worked examples (confirmed via direct computation of the algorithm
below):
- `to_snake_case("hello world")` is `"hello_world"`.
- `to_snake_case("helloWorld")` is `"hello_world"`.
- `to_snake_case("HelloWorld")` is `"hello_world"`.
- `to_snake_case("HTTPServer")` is `"http_server"` — the acronym
  boundary lands between `HTTP` and `Server`, not after every letter.
- `to_snake_case("already_snake")` is `"already_snake"` — idempotent.
- `to_snake_case("kebab-case-str")` is `"kebab_case_str"`.
- `to_snake_case("  extra   spaces  ")` is `"extra_spaces"` — runs of
  whitespace collapse to one underscore, leading/trailing trimmed.
- `to_snake_case("")` is `""`.
- `to_snake_case("A")` is `"a"` and `to_snake_case("a")` is `"a"`.
- `to_snake_case(123);` raises `CinderRuntimeError` — not a string.

Add `import re` to the top of `cinder/builtins.py` (search `import
random`, add `import re` directly after it, before `from collections
import Counter` — alphabetical order among the stdlib imports). Add
directly after `_caesar_cipher` (search `def _caesar_cipher`,
immediately before `def _is_palindrome`):
```python
def _split_case_words(value: str) -> list:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"[\s\-_]+", "_", value)
    return [word for word in value.strip("_").lower().split("_") if word]


def _to_snake_case(arguments: list, line: int, column: int) -> object:
    _require_arity("to_snake_case", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"to_snake_case() requires a string, got {type_name(value)}", line, column
        )
    return "_".join(_split_case_words(value))
```
(`_split_case_words` is a private module-level helper, not registered
in the builtins dict — it exists so `to_camel_case` and `to_kebab_case`
(tasks 5 and 6 below) can reuse the exact same word-boundary logic instead of
reimplementing it, the same shared-helper discipline `_ROMAN_VALUES`
already uses for `to_roman`/`from_roman`.) Register the new dict entry
(search `"caesar_cipher": _caesar_cipher,`, add `"to_snake_case":
_to_snake_case,` directly after it, before `"is_palindrome":
_is_palindrome,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `to_snake_case("HTTPServer")` is `"http_server"`.
- `to_snake_case(123);` raises `CinderRuntimeError` matching
  `"to_snake_case\(\) requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (top-of-file `import re`, then
directly after `_caesar_cipher`, search `def _caesar_cipher`),
`tests/test_builtins.py` (new `class TestToSnakeCase`, modeled on
`class TestRot13`/`class TestCaesarCipher`, search either name, for the
test shapes above — place it near the existing `class
TestCaesarCipher`). Once merged, `README.md`'s builtins quick-reference
list (search `swap_case`) needs `to_snake_case` added right after it,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 5. Standard library: `to_camel_case` — convert a string to `camelCase`

Depends on task 4 (`to_snake_case`) merging first — reuses its private
`_split_case_words` helper directly, the same same-file-dependency
shape `from_roman` already has on `to_roman`'s `_ROMAN_VALUES`. The
strict top-to-bottom claiming order this file's header already
enforces guarantees task 4 lands first. Add directly after
`_to_snake_case` (`cinder/builtins.py`, search `def _to_snake_case`,
immediately before `def _is_palindrome`) — the other standard case-
conversion target `to_snake_case` doesn't cover. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(to_camel_case("hello_world"));'
# -> <eval>:1:7: undefined name 'to_camel_case' (did you mean 'to_snake_case'?)
```

**What it does.** Given a string, split it into words with the exact
same `_split_case_words` boundary rules `to_snake_case` uses (so the
two builtins' notion of "word" can't drift apart), then join them back
as lowerCamelCase: the first word lowercase as-is, every subsequent
word capitalized (first letter upper, rest lower) and concatenated with
no separator.

Worked examples (confirmed via direct computation of the algorithm
below):
- `to_camel_case("hello world")` is `"helloWorld"`.
- `to_camel_case("helloWorld")` is `"helloWorld"` — idempotent.
- `to_camel_case("HelloWorld")` is `"helloWorld"`.
- `to_camel_case("HTTPServer")` is `"httpServer"`.
- `to_camel_case("already_snake")` is `"alreadySnake"`.
- `to_camel_case("kebab-case-str")` is `"kebabCaseStr"`.
- `to_camel_case("  extra   spaces  ")` is `"extraSpaces"`.
- `to_camel_case("")` is `""` — no words, nothing to join.
- `to_camel_case("A")` is `"a"` and `to_camel_case("a")` is `"a"`.
- `to_camel_case(123);` raises `CinderRuntimeError` — not a string.

Add directly after `_to_snake_case` (search `def _to_snake_case`,
immediately before `def _is_palindrome`):
```python
def _to_camel_case(arguments: list, line: int, column: int) -> object:
    _require_arity("to_camel_case", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"to_camel_case() requires a string, got {type_name(value)}", line, column
        )
    words = _split_case_words(value)
    if not words:
        return ""
    return words[0] + "".join(word.capitalize() for word in words[1:])
```
Register the new dict entry (search `"to_snake_case": _to_snake_case,`,
add `"to_camel_case": _to_camel_case,` directly after it, before
`"is_palindrome": _is_palindrome,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `to_camel_case("HTTPServer")` is `"httpServer"`.
- `to_camel_case(123);` raises `CinderRuntimeError` matching
  `"to_camel_case\(\) requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_to_snake_case`,
search `def _to_snake_case`), `tests/test_builtins.py` (new `class
TestToCamelCase`, modeled on `class TestToSnakeCase` from task 4 above,
for the test shapes above — place it near the existing `class
TestToSnakeCase`). Once merged, `README.md`'s builtins quick-reference
list (search `to_snake_case`) needs `to_camel_case` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
"Current frontier" section needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 6. Standard library: `to_kebab_case` — convert a string to `kebab-case`

Depends on task 4 (`to_snake_case`) merging first — reuses its private
`_split_case_words` helper directly, the same same-file-dependency
shape `to_camel_case` (task 5) already has on it too. The strict
top-to-bottom claiming order this file's header already enforces
guarantees task 4 lands first. Add directly after `_to_camel_case`
(`cinder/builtins.py`, search `def _to_camel_case`, immediately before
`def _is_palindrome`) — the third standard case-conversion target,
completing the trio `to_snake_case`/`to_camel_case` start. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(to_kebab_case("helloWorld"));'
# -> <eval>:1:7: undefined name 'to_kebab_case' (did you mean 'to_camel_case'?)
```

**What it does.** Given a string, split it into words with the exact
same `_split_case_words` boundary rules `to_snake_case`/`to_camel_case`
use (so all three builtins' notion of "word" can't drift apart), then
lowercase every word and join them with single hyphens instead of
underscores — the same output `to_snake_case` produces with `-` in
place of `_`.

Worked examples (confirmed via direct computation of the algorithm
below):
- `to_kebab_case("hello world")` is `"hello-world"`.
- `to_kebab_case("helloWorld")` is `"hello-world"`.
- `to_kebab_case("HelloWorld")` is `"hello-world"`.
- `to_kebab_case("HTTPServer")` is `"http-server"` — same acronym
  boundary `to_snake_case("HTTPServer")` uses.
- `to_kebab_case("already_snake")` is `"already-snake"`.
- `to_kebab_case("kebab-case-str")` is `"kebab-case-str"` — idempotent.
- `to_kebab_case("  extra   spaces  ")` is `"extra-spaces"`.
- `to_kebab_case("")` is `""`.
- `to_kebab_case("A")` is `"a"` and `to_kebab_case("a")` is `"a"`.
- `to_kebab_case(123);` raises `CinderRuntimeError` — not a string.

Add directly after `_to_camel_case` (search `def _to_camel_case`,
immediately before `def _is_palindrome`):
```python
def _to_kebab_case(arguments: list, line: int, column: int) -> object:
    _require_arity("to_kebab_case", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, str):
        raise CinderRuntimeError(
            f"to_kebab_case() requires a string, got {type_name(value)}", line, column
        )
    return "-".join(_split_case_words(value))
```
Register the new dict entry (search `"to_camel_case": _to_camel_case,`,
add `"to_kebab_case": _to_kebab_case,` directly after it, before
`"is_palindrome": _is_palindrome,`).

Acceptance criteria:
- Every worked example above holds exactly, including
  `to_kebab_case("HTTPServer")` is `"http-server"` and
  `to_kebab_case("kebab-case-str")` is `"kebab-case-str"`.
- `to_kebab_case(123);` raises `CinderRuntimeError` matching
  `"to_kebab_case\(\) requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_to_camel_case`,
search `def _to_camel_case`), `tests/test_builtins.py` (new `class
TestToKebabCase`, modeled on `class TestToCamelCase` from task 5
above, for the test shapes above — place it near the existing `class
TestToCamelCase`). Once merged, `README.md`'s builtins quick-reference
list (search `to_camel_case`) needs `to_kebab_case` added right after
it, its "Status & roadmap" section needs updating, and `PROJECT.md`'s
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

**Resolved 2026-09-08, merged as `#413`.** Requeued 2026-09-07 with
exactly the alternative strategy this postmortem called for (parse the
guard via the parser's ordinary `_ternary()` entry point instead of any
hand-rolled bracket/token scan) — that fix took two more review rounds
(a call/list/index/grouping leak, then a nested-`match` leak) before
landing clean, but never regressed to the original `_bracket_depth`
bug class this postmortem was about. See `CHANGELOG.md` for the full
three-round history.
