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

## 1. Standard library: `interpose` — insert a separator between list elements

Build: add `interpose(list, separator)` to `cinder/builtins.py`. `join`
(`cinder/builtins.py`, string builtins section) already does this for
strings — glue a separator between adjacent elements, none before the
first or after the last — but there's no list-level equivalent that
keeps the result a list (e.g. building `[1, ",", 2, ",", 3]` today
means hand-rolling a loop; `interleave` is the nearest existing
builtin but merges *two* lists element-by-element rather than
repeating one separator value between one list's elements). Unlike
`join`, `separator` need not be a string — any value is valid (e.g.
`interpose([1, 2, 3], 0);` is `[1, 0, 2, 0, 3]`), so this is a plain
list builtin, not a string one.

Model directly on `_interleave`'s structure
(`cinder/builtins.py:1434-1442`): single-list arity/type check instead
of `_require_two_lists` (`_require_arity("interpose", arguments, 2,
line, column)` then check `arguments[0]` is a `list`, matching the
message shape `_interleave`/`_union` use — `"interpose() requires a
list as its first argument, got {type_name}"`; the second argument,
the separator, takes no type check since any value is valid), then a
single loop appending `separator` before every element except the
first (`if i > 0: result.append(separator)` then `result.append(element)`,
using `enumerate`). Register it in the builtins dict right after
`"interleave": _interleave,` (`cinder/builtins.py:2636`).

Acceptance criteria:
- `interpose([1, 2, 3], 0);` is `[1, 0, 2, 0, 3]` — the primary case.
- `interpose([1], 0);` is `[1]` — a single element has no gaps to fill,
  matching `join`'s no-separator-needed behavior for a one-element list.
- `interpose([], 0);` is `[]`.
- `interpose([1, 2], "x");` is `[1, "x", 2]` — the separator's type
  need not match the list elements' type.
- `interpose(5, 0);` (non-list first argument) raises
  `CinderRuntimeError` naming `interpose` and `int` in the message
  (`type_name(5)` is `"int"`, not `"number"`).
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `interleave`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `interpose` added near `interleave` — leave that to the
Architect's next grooming pass, not this task.

---

## 2. Standard library: `truncate` — cap a string's length, appending a suffix when cut

Build: add `truncate(string, max_length, suffix)` to `cinder/builtins.py`.
Long strings today have no built-in way to cap their display length —
`pad_start`/`pad_end` (`cinder/builtins.py:825-840`) only grow strings,
never shrink them, and `slice` is list/string-index-based, not
length-aware with an ellipsis-style suffix. This is the shrinking
counterpart to padding: cap a string at `max_length` characters total,
and when it's actually cut, splice `suffix` onto the end so the result
still communicates "there was more here" (the classic `"hello..."`
UI pattern).

Model directly on `_pad_start`/`_pad_end`'s structure
(`cinder/builtins.py:825-840`), including a small shared validation
helper the same way those two share `_check_pad_arguments`
(`cinder/builtins.py:807-822`) — add a `_check_truncate_arguments`
helper (or inline checks directly in `_truncate`, whichever reads
closer to the existing pad helper) that requires: first argument a
`string` else `CinderRuntimeError` matching
`"truncate() requires a string as its first argument, got
{type_name}"`; second argument a non-bool `int` else
`"truncate() requires an int max_length, got {type_name}"`, and
negative else `"truncate() max_length must not be negative, got
{max_length}"` (same shape `_check_pad_arguments` uses for `width`,
`cinder/builtins.py:813-818`); third argument a `string` else
`"truncate() requires a string suffix, got {type_name}"`. Behavior once
validated: if `len(value) <= max_length`, return `value` unchanged (no
suffix appended — nothing was actually cut); otherwise return
`value[:max(0, max_length - len(suffix))] + suffix` — note this can
make the result longer than `max_length` when `suffix` itself is
longer than `max_length` (e.g. a length-1 cap with a 3-character
suffix); that's an accepted edge case, not a bug to guard against,
mirroring how `_pad_start`/`_pad_end` don't guard against a
multi-character `fill` producing an over-wide pad. Register it in the
builtins dict right after `"pad_end": _pad_end,`
(`cinder/builtins.py:2593`).

Acceptance criteria:
- `truncate("hello world", 8, "...");` is `"hello..."` — 5 characters
  of content plus the 3-character suffix, totaling exactly 8.
- `truncate("hello world", 5, "...");` is `"he..."` — 2 characters of
  content plus the suffix, totaling exactly 5.
- `truncate("hello", 10, "...");` is `"hello"` unchanged — shorter than
  `max_length`, no truncation, no suffix appended.
- `truncate("hello", 5, "...");` is `"hello"` unchanged — exactly at
  `max_length` is not "over" it, matching `_pad_start`/`_pad_end`'s own
  `>=` boundary treatment as a no-op.
- `truncate("hello world", 1, "...");` is `"..."` — `max_length` (1) is
  smaller than the suffix alone (3 chars), so content is empty and the
  result (length 3) exceeds `max_length`; pins the accepted edge case
  from the spec above.
- `truncate("hello", 3, "");` is `"hel"` — an empty suffix behaves like
  a plain hard cut.
- `truncate(5, 3, "...");` (non-string first argument) raises
  `CinderRuntimeError` naming `truncate` and `int` in the message
  (`type_name(5)` is `"int"`, not `"number"`).
- `truncate("hello", "3", "...");` (non-int second argument) raises
  `CinderRuntimeError` naming `truncate` and `string` in the message.
- `truncate("hello", -1, "...");` (negative `max_length`) raises
  `CinderRuntimeError` naming `truncate` and `-1` in the message.
- `truncate("hello", 3, 5);` (non-string third argument) raises
  `CinderRuntimeError` naming `truncate` and `int` in the message.
- Wrong arity (not exactly 3 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `pad_start`/
`pad_end`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `truncate` added near `pad_start`/
`pad_end` — leave that to the Architect's next grooming pass, not this
task.

---

## 3. Standard library: `chars` — split a string into a list of its characters

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
right after `"words": _words,` (`cinder/builtins.py:2583`).

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

## 4. Standard library: `is_even`/`is_odd` — integer parity predicates

Build: add `is_even(number)` and `is_odd(number)` to `cinder/builtins.py`.
There is currently no builtin way to test a number's parity — the
existing type predicates (`is_list`, `is_map`, `is_string`, `is_number`,
`is_bool`, `is_nil`, `is_function`, `cinder/builtins.py:2689-2695` in
the dict) all classify a value's *kind*, not a numeric property of it,
and the closest numeric helper, `sign` (`cinder/builtins.py:853-864`),
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
(`cinder/builtins.py:2595`), `is_even` before `is_odd`.

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

## 5. Standard library: `swap_case` — flip each character's case

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
`"title": _title,` (`cinder/builtins.py:2596`).

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
