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

## 1. Standard library: `is_blank` — whitespace-or-empty string predicate

Build: add `is_blank(string)` to `cinder/builtins.py`, the gap `is_space`
(`cinder/builtins.py:713-720`) deliberately leaves open: `str.isspace()`
(what `is_space` delegates to) is `false` on the empty string, the same
"empty string is false" rule every member of the content-predicate family
(`is_alpha`/`is_digit`/`is_alnum`/`is_space`/`is_ascii`) follows on purpose
— so today there is no single builtin call that answers "is this string
either empty or nothing but whitespace", a common pre-validation check
(e.g. rejecting blank form input) that currently needs
`is_empty(s) or is_space(s)` spelled out by hand every time. Register
right after `is_space`, ahead of `is_ascii` — it belongs next to the
predicate whose blind spot it fills, not at the end of the family.

Model the arity/type-checking on `_is_space`'s structure exactly (same
`_require_arity("is_blank", arguments, 1, line, column)` and
`f"is_blank() requires a string, got {type_name(value)}"` non-string
error), but the body is `value == "" or value.isspace()` — not a bare
delegation to a single Python `str` method the way every other member of
this family is, since no single `str.is*()` method covers "empty or
whitespace" on its own.

Acceptance criteria:
- `is_blank("");` is `true` — the one case that makes this predicate not
  redundant with `is_space`.
- `is_blank("   ");` is `true` — spaces only.
- `is_blank("\t\n");` is `true` — other whitespace characters, same set
  `str.isspace()` already recognizes.
- `is_blank("a");` is `false`.
- `is_blank(" a ");` is `false` — whitespace padding a non-whitespace
  character still fails.
- `is_blank(5);` (non-string argument) raises `CinderRuntimeError`
  matching `"is_blank() requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_space`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet needs
`is_blank` added near `is_space`, and `PROJECT.md`'s roadmap paragraph
needs it moved from backlog to landed — leave both to the Architect's
next grooming pass, not this task.

---

## 2. Standard library: `factorial` — numeric builtin rounding out `pow`/`gcd`/`lcm`

Build: add `factorial(n)` to `cinder/builtins.py`, a numeric builtin
sitting next to `pow`/`gcd`/`lcm` (`cinder/builtins.py:1254-1363`). Register
it right after `lcm` — it belongs with that small cluster of
number-theoretic builtins, not the string/list families above or below it.

Model the arity/type-checking on `_gcd`/`_lcm`'s structure
(`cinder/builtins.py:1342-1363`): reuse `_require_arity("factorial",
arguments, 1, line, column)`, then check `arguments[0]` is an `int` and
not a `bool` (same `isinstance(value, int) and not isinstance(value,
bool)` guard `_gcd`/`_lcm` use per-argument), raising `CinderRuntimeError`
with `f"factorial() requires an int, got {type_name(value)}"` on failure.
Separately, negative input is a domain error, not a type error — mirror
`_log`'s own "requires a number" vs. "requires a positive number, domain
error" split (`cinder/builtins.py` around `_log`, two distinct checks, two
distinct messages): raise `CinderRuntimeError` with
`"factorial() requires a non-negative int, domain error"` when
`value < 0`. For the computation itself, delegate directly to Python's
`math.factorial(value)` (already imported — `builtins.py:17` has `import
math`) rather than hand-rolling a loop; Cinder ints are Python ints, so
there's no overflow to guard (unlike `pow()`, which does need its own
overflow/complex-result guards for float bases/exponents — `factorial`
only ever takes a non-negative int, so none of that machinery applies
here).

Acceptance criteria:
- `factorial(0);` is `1`.
- `factorial(1);` is `1`.
- `factorial(5);` is `120`.
- `factorial(10);` is `3628800`.
- `factorial(20);` is `2432902008176640000` — confirms no overflow/precision
  loss on a result too large for a 64-bit float to represent exactly.
- `factorial(-1);` raises `CinderRuntimeError` matching
  `"factorial() requires a non-negative int, domain error"`.
- `factorial(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"factorial() requires an int, got
  float"` — no implicit float-to-int coercion, matching how `gcd`/`lcm`
  reject floats today.
- `factorial(true);` (bool, which is a Python `int` subclass) raises
  `CinderRuntimeError` matching `"factorial() requires an int, got
  bool"` — same bool-exclusion `gcd`/`lcm`/`is_even`/`is_odd` already
  apply.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `gcd`/`lcm`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet needs
`factorial` added near `pow`/`gcd`/`lcm`, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_pangram` — alphabet-coverage string predicate

Build: add `is_pangram(string)` to `cinder/builtins.py`, a string
predicate testing whether `string` contains every letter of the English
alphabet at least once (case-insensitive — `"a"` and `"A"` both count
toward the same letter), sitting near `is_palindrome`/`is_anagram`/
`is_permutation` (`cinder/builtins.py:622-660`) in the string/list
multiset-predicate cluster rather than the `is_alpha`/`is_digit`/.../
`is_ascii` content-predicate family (`:683-731`): unlike that family,
`is_pangram` isn't a bare delegation to a single `str.is*()` Python
method — Python has no built-in for this, so the body needs actual
logic. Register right after `is_permutation` (which now sits right
after `is_anagram`, having landed since this task was first scoped),
ahead of `is_upper`.

Model the arity/type-checking on `_is_palindrome`'s structure
(`cinder/builtins.py:622-629`): reuse `_require_arity("is_pangram",
arguments, 1, line, column)`, check `arguments[0]` is a `str` (raising
`CinderRuntimeError` with `f"is_pangram() requires a string, got
{type_name(value)}"` on a non-string argument, matching the exact
wording pattern `is_palindrome`/`is_alpha`/etc. all use), then compute
the body as `set(string.ascii_lowercase) <= set(value.lower())` (`string`
module already imported for `ascii_lowercase`/`ascii_uppercase` elsewhere
in this file — check the existing `import string` at the top before
adding a duplicate; if absent, `set("abcdefghijklmnopqrstuvwxyz")` is an
equally fine literal, no need to add a new import for one character
class). Non-letter characters (digits, punctuation, whitespace) are
simply ignored by the set-membership check — no special-casing needed.

Acceptance criteria:
- `is_pangram("The quick brown fox jumps over the lazy dog");` is
  `true` — the canonical English pangram.
- `is_pangram("Pack my box with five dozen liquor jugs");` is `true` —
  a second, shorter canonical pangram, confirming the check isn't
  accidentally tied to the first example's specific length/casing.
- `is_pangram("hello world");` is `false` — missing most letters.
- `is_pangram("");` is `false` — empty string, matching the "empty is
  false" rule every other content-style predicate in this file follows.
- `is_pangram("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG");` is
  `true` — all-uppercase input, confirming the check is
  case-insensitive.
- `is_pangram("abcdefghijklmnopqrstuvwxyz");` is `true` — exactly the
  26 letters, no repeats, no filler text.
- `is_pangram(5);` (non-string argument) raises `CinderRuntimeError`
  matching `"is_pangram() requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_anagram`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_pangram` added near `is_palindrome`/`is_anagram`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `digit_sum` — sum of an integer's decimal digits

Build: add `digit_sum(n)` to `cinder/builtins.py`, a numeric builtin
sitting right after `is_prime` (`cinder/builtins.py:1137-1145`) in the
integer-property predicate cluster (`is_even`/`is_odd`/`is_divisible`/
`is_prime`, `cinder/builtins.py:1114-1145`) — it isn't itself a
predicate (it returns a number, not `true`/`false`), but it belongs
next to that cluster rather than next to `pow`/`gcd`/`lcm`/`factorial`
further down the file, since it shares their "one property of a single
int" shape rather than the two-argument number-theoretic shape of that
farther-down group.

Model the arity/type-checking on `_is_prime`'s structure
(`cinder/builtins.py:1137-1139`): reuse `_require_arity("digit_sum",
arguments, 1, line, column)` and `_require_int("digit_sum",
arguments[0], line, column)` (the same helper `is_even`/`is_odd`/
`is_divisible`/`is_prime` already use — defined at
`cinder/builtins.py:157-162`, raises `CinderRuntimeError` with
`f"{name}() requires an int, got {type_name(value)}"` and rejects `bool`
since `bool` is a Python `int` subclass, so no separate bool-exclusion
check is needed here). For the computation, take the absolute value
first (`digit_sum` is a property of a number's magnitude, not its sign —
matching how `factorial`'s task above treats domain errors as distinct
from type errors, `digit_sum` sidesteps the question entirely by
normalizing sign away rather than rejecting negative input), then sum
the digits: `sum(int(digit) for digit in str(abs(value)))` is sufficient
— no need for a hand-rolled `% 10` / `// 10` loop.

Acceptance criteria:
- `digit_sum(0);` is `0`.
- `digit_sum(5);` is `5`.
- `digit_sum(123);` is `6`.
- `digit_sum(999);` is `27`.
- `digit_sum(-123);` is `6` — sign is ignored, same magnitude as `123`.
- `digit_sum(3.0);` (float, even though numerically whole) raises
  `CinderRuntimeError` matching `"digit_sum() requires an int, got
  float"` — no implicit float-to-int coercion, matching `is_even`/
  `is_odd`/`is_prime`.
- `digit_sum(true);` (bool) raises `CinderRuntimeError` matching
  `"digit_sum() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_prime`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `digit_sum` added near `is_even`/`is_odd`/`is_divisible`/
`is_prime`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
