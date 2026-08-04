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

## 1. Standard library: `chars` — split a string into a list of its characters

Build: add `chars(string)` to `cinder/builtins.py`. `split` deliberately
raises `CinderRuntimeError` on an empty separator
(`cinder/builtins.py:653-654`, `"split() separator must not be empty"`)
rather than falling back to Python's `list(s)`-style per-character
split, so there is currently no builtin way to turn a string into a
list of its individual characters — needed to run any of the existing
list builtins (`map`, `filter`, `reverse`, `sort`, ...) character-by-
character over a string, today only reachable by hand-rolling a `for`
loop and `push`-ing into a fresh list.

Model directly on `_lines`/`_words`'s structure
(`cinder/builtins.py:658-675`): same arity-1 check via
`_require_arity("chars", arguments, 1, line, column)`, same single
type check (the argument a `string` else `CinderRuntimeError` matching
`"chars() requires a string, got {type_name}"`, same message shape
`_lines`/`_words` use). Behavior once validated: return `list(value)`
— Python's built-in per-character split, which already does the right
thing for `""` (`list("")` is `[]`). Register it in the builtins dict
right after `"words": _words,` (`cinder/builtins.py:2647`).

Acceptance criteria:
- `chars("abc");` is `["a", "b", "c"]`.
- `chars("");` is `[]` — empty string, no characters.
- `chars("a");` is `["a"]` — single character.
- `chars(" a ");` is `[" ", "a", " "]` — whitespace is a character
  too, not trimmed (contrast with `words`, which splits on and
  discards whitespace).
- `chars(5);` (non-string argument) raises `CinderRuntimeError` naming
  `chars` and `int` in the message (`type_name(5)` is `"int"`, not
  `"number"`).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `lines`/`words`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `chars` added near `lines`/`words` — leave that to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_even`/`is_odd` — integer parity predicates

Build: add `is_even(number)` and `is_odd(number)` to `cinder/builtins.py`.
There is currently no builtin way to test a number's parity — the
existing type predicates (`is_list`, `is_map`, `is_string`, `is_number`,
`is_bool`, `is_nil`, `is_function`, `cinder/builtins.py:2756-2762` in
the dict) all classify a value's *kind*, not a numeric property of it,
and the closest numeric helper, `sign` (`cinder/builtins.py:901-912`),
classifies a number's sign, not its parity — every Cinder program that
wants "is this number even" today hand-rolls `n % 2 == 0`. This adds
the pair the same way `sign` already sits next to `abs` as a small,
self-contained numeric predicate.

Model both on `_sign`'s structure (`cinder/builtins.py:853-864`): same
arity-1 check via `_require_arity("is_even"/"is_odd", arguments, 1,
line, column)`, but reuse `_require_int` (`cinder/builtins.py:156-161`,
already used by `to_hex`/`to_bin`/`to_oct`) instead of `_is_numeric`
for the type check — parity is only meaningful for integers, so a
`float` argument (even a whole-valued one like `4.0`) is a type error,
not silently truncated; `_require_int`'s existing message shape
(`"{name}() requires an int, got {type_name}"`) applies unchanged, no
new message text to invent. Behavior once validated: `is_even` returns
`value % 2 == 0`; `is_odd` returns `value % 2 != 0` (correct for
negative integers too, since Python's `%` on ints always returns a
non-negative result when the divisor is positive: `-3 % 2 == 1`).
Register both in the builtins dict right after `"sign": _sign,`
(`cinder/builtins.py:2661`), `is_even` before `is_odd`.

Acceptance criteria:
- `is_even(4);` is `true`, `is_odd(4);` is `false`.
- `is_even(3);` is `false`, `is_odd(3);` is `true`.
- `is_even(0);` is `true` — zero is even.
- `is_even(-4);` is `true`, `is_odd(-3);` is `true` — negative integers
  use the same parity rule as positive ones.
- `is_even(4.0);` (float, even though whole-valued) raises
  `CinderRuntimeError` naming `is_even` and `float` in the message
  (`type_name(4.0)` is `"float"`); same for `is_odd(4.0);` naming
  `is_odd`.
- `is_even("4");` (non-numeric argument) raises `CinderRuntimeError`
  naming `is_even` and `string` in the message; same for `is_odd`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column, for both functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `sign`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_even`/`is_odd` added near the other type predicates
(`is_list`/`is_map`/... ) or near `sign` — leave that to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `swap_case` — flip each character's case

Build: add `swap_case(string)` to `cinder/builtins.py`. The existing case
builtins (`upper`, `lower`, `capitalize`, `title`,
`cinder/builtins.py:558-609`) only ever push a string toward one
direction — all upper, all lower, or capitalized at word starts —
there is no builtin that flips each character's existing case in
place (`"Hello World"` → `"hELLO wORLD"`), a common text-processing
operation and the natural fourth member alongside `upper`/`lower`/
`capitalize`/`title` since none of those touch already-correct casing
symmetrically.

Model directly on `_capitalize`'s structure
(`cinder/builtins.py:578-587`): same arity-1 check via
`_require_arity("swap_case", arguments, 1, line, column)`, same single
type check (the argument a `string` else `CinderRuntimeError` matching
`"swap_case() requires a string, got {type_name}"`, same message
shape `_capitalize`/`_title` use). Behavior once validated: return
`value.swapcase()` — Python's built-in per-character case flip, which
already leaves non-alphabetic characters untouched and handles the
empty string correctly. Register it in the builtins dict right after
`"title": _title,` (`cinder/builtins.py:2641`).

Acceptance criteria:
- `swap_case("Hello World");` is `"hELLO wORLD"` — the primary case.
- `swap_case("");` is `""` — empty string, no-op.
- `swap_case("123 abc XYZ");` is `"123 ABC xyz"` — digits/spaces
  untouched, only letters flip.
- `swap_case("ABC");` is `"abc"`, `swap_case("abc");` is `"ABC"` —
  fully-uppercase and fully-lowercase inputs invert cleanly.
- `swap_case(5);` (non-string argument) raises `CinderRuntimeError`
  naming `swap_case` and `int` in the message (`type_name(5)` is
  `"int"`, not `"number"`).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `capitalize`/
`title`, see current line numbers — shift if earlier tasks this cycle
landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `swap_case` added near `capitalize`/`title` —
leave that to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `pad_center` — center a string within a width, padding both sides

Build: add `pad_center(string, width, fill)` to `cinder/builtins.py`.
`pad_start`/`pad_end` (`cinder/builtins.py:844-859`) only ever pad on
one side — the natural third member is centering, padding both sides
so the original content sits in the middle, the same relationship
Python's `str.center` has to `str.ljust`/`str.rjust`.

Model directly on `_pad_start`/`_pad_end`'s structure
(`cinder/builtins.py:844-859`), reusing the existing
`_check_pad_arguments` helper unchanged (`cinder/builtins.py:826-841`)
— same three checks it already runs for `pad_start`/`pad_end`: first
argument a `string` else `CinderRuntimeError` matching `"pad_center()
requires a string as its first argument, got {type_name}"`, second
argument a non-bool, non-negative `int` else `"pad_center() requires
an int width, got {type_name}"` / `"pad_center() width must not be
negative, got {width}"`, third argument a single-character `string`
else `"pad_center() requires a single-character fill string, got
{fill!r}"` (call it as `_check_pad_arguments("pad_center", value,
width, fill, line, column)` — the message text swaps in automatically
via the `name` parameter, no new strings to write). Behavior once
validated: if `len(value) >= width`, return `value` unchanged (same
no-op boundary `pad_start`/`pad_end` use); otherwise return
`value.center(width, fill)` — Python's built-in centering, which puts
any extra (odd) padding character on the left, e.g. `"ab".center(5,
"*")` is `"**ab*"`. Register it in the builtins dict right after
`"pad_end": _pad_end,` (`cinder/builtins.py:2658`, immediately before
`"truncate": _truncate,` — keep the `pad_start`/`pad_end`/`pad_center`
trio contiguous rather than appending after `truncate`).

Acceptance criteria:
- `pad_center("ab", 5, "*");` is `"**ab*"` — odd padding (3 extra
  chars) splits 2 left / 1 right, matching Python's `str.center`.
- `pad_center("ab", 6, "*");` is `"**ab**"` — even padding splits
  evenly.
- `pad_center("hello", 3, "*");` is `"hello"` unchanged — `width`
  smaller than the string, no-op.
- `pad_center("hello", 5, "*");` is `"hello"` unchanged — exactly at
  `width` is not "under" it, matching `_pad_start`/`_pad_end`'s own
  `>=` boundary treatment as a no-op.
- `pad_center("", 3, "*");` is `"***"` — empty string, pure fill.
- `pad_center(5, 3, "*");` (non-string first argument) raises
  `CinderRuntimeError` naming `pad_center` and `int` in the message.
- `pad_center("ab", "3", "*");` (non-int second argument) raises
  `CinderRuntimeError` naming `pad_center` and `string` in the
  message.
- `pad_center("ab", -1, "*");` (negative `width`) raises
  `CinderRuntimeError` naming `pad_center` and `-1` in the message.
- `pad_center("ab", 5, "**");` (multi-character fill) raises
  `CinderRuntimeError` naming `pad_center` and mentioning the
  two-character fill string.
- Wrong arity (not exactly 3 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `pad_start`/
`pad_end`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `pad_center` added near
`pad_start`/`pad_end` — leave that to the Architect's next grooming
pass, not this task.

---

## 5. Standard library: `is_palindrome` — test whether a string reads the same forwards and backwards

Build: add `is_palindrome(string)` to `cinder/builtins.py`. There is
currently no builtin way to test this common string property directly
— today it requires hand-rolling `value == value[::-1]`-equivalent
logic with a manual reverse loop (Cinder has no slice-reversal
shorthand), even though the language already has string
predicates elsewhere (`is_string` et al. classify a value's *kind*;
this one, like `is_even`/`is_odd` above, classifies a property of the
value itself).

Model directly on `_capitalize`'s/`_title`'s structure
(`cinder/builtins.py:578-606`): same arity-1 check via
`_require_arity("is_palindrome", arguments, 1, line, column)`, same
single type check (the argument a `string` else `CinderRuntimeError`
matching `"is_palindrome() requires a string, got {type_name}"`, same
message shape `_capitalize`/`_title`/`swap_case` use — reuse whichever
of those has landed by the time this task is picked up as the
template, since they're structurally identical). Behavior once
validated: return `value == value[::-1]`. Deliberately no
normalization — do not strip whitespace/punctuation and do not
case-fold; this is a literal character-for-character check, matching
the minimal-behavior spirit `chars`/`swap_case` above already follow
rather than guessing at what a caller wants ignored. Register it in
the builtins dict right after `"is_string": _is_string,`
(`cinder/builtins.py:2758`), grouping it with the other `is_*`
predicates rather than with the case-manipulation builtins its
implementation resembles.

Acceptance criteria:
- `is_palindrome("racecar");` is `true` — odd-length palindrome.
- `is_palindrome("noon");` is `true` — even-length palindrome.
- `is_palindrome("hello");` is `false` — not a palindrome.
- `is_palindrome("");` is `true` — empty string, vacuously a
  palindrome.
- `is_palindrome("a");` is `true` — single character.
- `is_palindrome("Racecar");` is `false` — no case-folding; the
  mismatched `R`/`r` at the ends makes this not a literal palindrome.
- `is_palindrome("a man a");` is `false` — no whitespace stripping;
  contrast with the classic "a man a plan a canal panama" phrasing,
  which is out of scope here.
- `is_palindrome(5);` (non-string argument) raises
  `CinderRuntimeError` naming `is_palindrome` and `int` in the message
  (`type_name(5)` is `"int"`, not `"number"`).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_string`/the
other `is_*` predicates, see current line numbers — shift if earlier
tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_palindrome` added near
the other `is_*` type predicates — leave that to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
