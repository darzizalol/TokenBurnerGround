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

## 1. Standard library: `is_permutation` — two-list character/element-multiset predicate

Build: add `is_permutation(list1, list2)` to `cinder/builtins.py`. It's
task 1's `is_anagram` generalized from strings to lists: two lists are
permutations of each other when they contain exactly the same elements
the same number of times, regardless of order — the list-oriented sibling
`is_anagram` deliberately doesn't cover (its `Counter`-based approach
needs hashable characters; list elements can be lists/maps, which aren't
hashable). Register right after `is_anagram` (task 1, if merged first) or
right after `is_subset`/`is_superset`/`is_disjoint` otherwise (see current
line numbers, shift if earlier tasks this cycle landed first) — grouping
it with whichever multiset-shaped predicate family lands nearest it.

Model the arity/type-checking on `_is_subset`'s structure
(`cinder/builtins.py:1683-1685`): reuse
`_require_two_lists("is_permutation", arguments, line, column)` for
arity-2 + list-type validation on both arguments (same "requires a list
as its first/second argument, got {type_name}" errors, no new message
shape). For the comparison itself, do **not** use `collections.Counter`
or a `set`/`dict` keyed on the elements directly — unlike `is_anagram`'s
characters, list elements can be unhashable (nested lists/maps), the same
reason `_dedupe` (`cinder/builtins.py:1605-1622`) falls back to an
O(n²) `values_equal` scan when `not all(_is_valid_key(element) for
element in value)`. Take the same approach here, unconditionally (no
need to special-case the hashable case for a predicate — simplicity over
micro-optimization): different lengths short-circuit to `false` (`len(list1)
!= len(list2)`); otherwise copy `list2` into a working list, and for each
element of `list1` find the first remaining element it's `values_equal`
to and remove that one match (not all matches — this is multiset
removal, not filtering); if any element of `list1` has no remaining match,
return `false` immediately; if the loop completes, return `true` (the
length check up front guarantees the working list is exactly emptied,
no need to check it explicitly).

Acceptance criteria:
- `is_permutation([1, 2, 3], [3, 2, 1]);` is `true` — same elements,
  different order.
- `is_permutation([1, 2, 2], [1, 1, 2]);` is `false` — same elements by
  set membership, but different per-element counts (two `2`s vs one).
- `is_permutation([], []);` is `true` — two empty lists share an (empty)
  multiset.
- `is_permutation([1], [1, 2]);` is `false` — different lengths can
  never be permutations (short-circuit, no need to scan).
- `is_permutation([[1, 2]], [[1, 2]]);` is `true` — matching uses deep
  equality (`values_equal`), not reference identity or hashing, so a
  structurally-equal nested list still counts as a match.
- `is_permutation([1, "1"], ["1", 1]);` is `true` — `1` and `"1"` are
  distinct elements under `values_equal`, but each side has exactly one
  of each, matched correctly regardless of order.
- `is_permutation(5, [1, 2]);` / `is_permutation([1, 2], 5);`
  (non-list argument, either position) raises `CinderRuntimeError`
  naming `is_permutation` and which position (first/second) failed.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_permutation` added near
`is_anagram`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass, not
this task.

---

## 2. Standard library: `is_numeric` — string numeric-content predicate

Build: add `is_numeric(string)` to `cinder/builtins.py`, one more member of
the `is_alpha`/`is_digit`/`is_alnum`/`is_space`/`is_ascii` string
content-predicate family (`cinder/builtins.py:651-698`), which all delegate
straight to the matching Python `str.is*()` method with the same
arity/type-check wrapper. `is_numeric` is not redundant with the existing
`is_digit`: Python's `str.isnumeric()` is strictly broader than
`str.isdigit()` — it is `true` for any character with a Unicode numeric
value, which includes not just plain digits but fraction characters
(`"½"`), superscript/subscript digits, and numeral characters from other
scripts (e.g. Roman numeral `"Ⅷ"`, CJK `"一"`), none of which
`str.isdigit()` accepts. Register right after `is_ascii`, keeping the
string-content-predicate family contiguous.

Model directly on `_is_ascii`'s structure (`cinder/builtins.py:691-698`):
reuse `_require_arity("is_numeric", arguments, 1, line, column)`, check
`arguments[0]` is a `str` (raising `CinderRuntimeError` with
`f"is_numeric() requires a string, got {type_name(value)}"` on a
non-string argument, matching the exact wording pattern the rest of this
family uses), and return `value.isnumeric()` directly — no extra logic
needed, this is a pure delegation like its siblings.

**Naming collision, read before writing code**: do NOT name the new
function `_is_numeric` — `cinder/builtins.py:39` already defines
`def _is_numeric(value: object) -> bool` (an unrelated int/float-not-bool
check used internally ~30 times, e.g. `cinder/builtins.py:710`, `:1031`,
and inside `_is_number`'s own body at `:2802`). Every other predicate in
this family names its function to match its registered builtin name
exactly (`_is_ascii` ↔ `"is_ascii"`), but that convention can't be
followed literally here without silently shadowing the existing helper —
Python would accept the redefinition at parse time, then every one of
those ~30 call sites would start passing a single argument to a function
that now requires three (`arguments, line, column`), breaking at call
time far from this diff. Name the new function `_is_numeric_string`
instead; only its registration key (`"is_numeric": _is_numeric_string`)
needs to read `is_numeric` — same pattern `_is_disjoint` uses today for
its own function-name-vs-builtin-name (they happen to match, this one
just can't).

Acceptance criteria:
- `is_numeric("123");` is `true`.
- `is_numeric("12a3");` is `false` — a letter breaks it, same as
  `is_digit`.
- `is_numeric("");` is `false` — empty string, matching how
  `is_alpha`/`is_digit`/`is_alnum`/`is_space`/`is_ascii` all treat the
  empty string.
- `is_numeric("-5");` is `false` — `-` is not a numeric character (falls
  out of `str.isnumeric()` naturally, no special-casing needed).
- `is_numeric("½");` is `true` but `is_digit("½");` is `false` — the
  concrete example distinguishing this predicate from the existing
  `is_digit`, since `str.isnumeric()` accepts fraction characters that
  `str.isdigit()` rejects.
- `is_numeric(5);` (non-string argument) raises `CinderRuntimeError`
  matching `"is_numeric() requires a string, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_ascii`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet needs
`is_numeric` added near `is_alpha`/`is_digit`/`is_alnum`/`is_space`/
`is_ascii`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `is_blank` — whitespace-or-empty string predicate

Build: add `is_blank(string)` to `cinder/builtins.py`, the gap `is_space`
(`cinder/builtins.py:681-688`) deliberately leaves open: `str.isspace()`
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

## 4. Standard library: `factorial` — numeric builtin rounding out `pow`/`gcd`/`lcm`

Build: add `factorial(n)` to `cinder/builtins.py`, a numeric builtin
sitting next to `pow`/`gcd`/`lcm` (`cinder/builtins.py:1222-1330`). Register
it right after `lcm` — it belongs with that small cluster of
number-theoretic builtins, not the string/list families above or below it.

Model the arity/type-checking on `_gcd`/`_lcm`'s structure
(`cinder/builtins.py:1310-1330`): reuse `_require_arity("factorial",
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
