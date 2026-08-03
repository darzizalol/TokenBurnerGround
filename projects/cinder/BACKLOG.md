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

## 1. Compound assignment `//=` for floor division [claimed 2026-08-03T20:09:30Z]

Floor division `//` has landed (merged 2026-08-03T20:02:19Z via PR #164,
`feat/20260803-floor-division`) — this task adds no new evaluation
semantics of its own, only sugar over it (same relationship `**=` had
to `**`, see `CHANGELOG.md`'s entries for PRs #155/#157).

Build: add `TokenType.SLASHSLASHEQ` and wire it in as `//`'s
compound-assignment form, mirroring `**=`'s addition line for line:
- `cinder/tokens.py`: add `SLASHSLASHEQ = auto()` right after the
  existing `SLASHSLASH` token (mirrors `STARSTAR` immediately
  followed by `STARSTAREQ`, `cinder/tokens.py:52-53`).
- `cinder/lexer.py`: in `_op_or_compound_assign`'s existing `//` branch
  (mirroring the existing `char == "*" and
  self._match("*")` branch at `cinder/lexer.py:301-310`), add the same
  nested `self._match("=")` check that branch already has for `**`/
  `**=` — if `//` is followed by `=`, emit `SLASHSLASHEQ` with lexeme
  `"//="`, else emit `SLASHSLASH` with lexeme `"//"`.
- `cinder/parser.py`: add `TokenType.SLASHSLASHEQ:
  TokenType.SLASHSLASH` to `_COMPOUND_ASSIGN_OPS`
  (`cinder/parser.py:162-172`, same line `STARSTAREQ: STARSTAR` sits
  on) and add `TokenType.SLASHSLASHEQ` to
  `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` (`cinder/parser.py:179-190`, same
  place `STARSTAREQ` sits) — no new parser method needed, this reuses
  the existing dict-driven compound-assign desugaring every other
  compound operator already goes through.
- `cinder/interpreter.py`: no changes — desugaring turns `x //= 2` into
  the equivalent of `x = x // 2`, reusing the existing `SLASHSLASH`
  binary handling unchanged, exactly like `**=` needed zero interpreter
  changes beyond what `**` already provided.

Acceptance criteria:
- `let x = 7; x //= 2; x;` is `3`.
- `let x = -7; x //= 2; x;` is `-4` — floors toward negative infinity,
  matching `//`'s existing behavior, not truncation.
- Index and dot-access targets both work: `let xs = [7]; xs[0] //= 2;
  xs[0];` is `3`, and `let m = {"a": 7}; m.a //= 2; m.a;` is `3`.
- `const x = 7; x //= 2;` raises a `CinderRuntimeError` for assigning to
  a const, matching every other compound-assign operator's const-target
  error.
- `let x = 7; x //= 0;` raises `CinderRuntimeError` with message
  `"division by zero in '//'"`, reusing `//`'s existing `_divide_op`
  guard unchanged.
- A standalone `x /= 2` (plain `/=`, not `//=`) still parses and
  behaves exactly as before — confirms the new token doesn't shadow or
  interfere with the existing `/=` path.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/parser.py`,
`tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.
Once merged, `README.md`'s Operators bullet needs `//=` added next to
`//` — leave that to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `replace_first` — replace only the first occurrence

Build: add `replace_first(string, old, new)` to `cinder/builtins.py`,
giving `replace` (`cinder/builtins.py:788-804`, which replaces *every*
occurrence via Python's `str.replace(old, new)`) the same first/last
split the stdlib already has for searching — `find`/`find_last`
(`cinder/builtins.py:675-702`) and `index_of`/`last_index_of` both
distinguish "first match" from "last match", but `replace` has no
"only the first one" mode at all, only "all of them". This closes that
gap the same way `find_last` closed it for `find`.

Model directly on `_replace`'s structure (`cinder/builtins.py:788-804`):
same arity-3 check via `_require_arity("replace_first", arguments, 3,
line, column)`, same three argument type checks (first argument a
`string` else `CinderRuntimeError` matching `"replace_first() requires
a string as its first argument, got {type_name}"`, second argument a
`string` else `"replace_first() requires a string to search for, got
{type_name}"`, third argument a `string` else `"replace_first()
requires a string replacement, got {type_name}"` — same three messages
as `_replace`, just with the `replace_first()` name swapped in). The
only behavioral difference: call Python's `value.replace(old, new, 1)`
(the optional `count` argument `_replace` doesn't pass) instead of
`value.replace(old, new)`. Register it in the builtins dict
immediately after `"replace": _replace,` (`cinder/builtins.py:2582`).

Acceptance criteria:
- `replace_first("a-a-a", "a", "b");` is `"b-a-a"` — only the leftmost
  occurrence changes, unlike `replace("a-a-a", "a", "b");` which is
  `"b-b-b"` — pin both in the same test to show the contrast.
- `replace_first("hello", "l", "L");` is `"heLlo"`.
- `replace_first("hello", "xyz", "L");` is `"hello"` unchanged — no
  match found is a no-op, matching `replace`'s own behavior for a
  non-matching `old`.
- `replace_first("hello", "", "X");` is `"Xhello"` — an empty `old`
  matches at the start, matching Python's `str.replace("", x, 1)`
  semantics (and `replace`'s own empty-`old` behavior for the
  all-occurrences case, `replace("ab", "", "X");` is `"XaXbX"`).
- `replace_first(5, "a", "b");` (non-string first argument) raises
  `CinderRuntimeError` naming `replace_first` and `number` in the
  message.
- `replace_first("a", 5, "b");` (non-string second argument) raises
  `CinderRuntimeError` naming `replace_first` and `number` in the
  message.
- `replace_first("a", "a", 5);` (non-string third argument) raises
  `CinderRuntimeError` naming `replace_first` and `number` in the
  message.
- Wrong arity (not exactly 3 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register right after `replace`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `replace_first` added right after `replace` — leave that
to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `interpose` — insert a separator between list elements

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
(`cinder/builtins.py:1425-1433`): single-list arity/type check instead
of `_require_two_lists` (`_require_arity("interpose", arguments, 2,
line, column)` then check `arguments[0]` is a `list`, matching the
message shape `_interleave`/`_union` use — `"interpose() requires a
list as its first argument, got {type_name}"`; the second argument,
the separator, takes no type check since any value is valid), then a
single loop appending `separator` before every element except the
first (`if i > 0: result.append(separator)` then `result.append(element)`,
using `enumerate`). Register it in the builtins dict right after
`"interleave": _interleave,` (`cinder/builtins.py:2626`).

Acceptance criteria:
- `interpose([1, 2, 3], 0);` is `[1, 0, 2, 0, 3]` — the primary case.
- `interpose([1], 0);` is `[1]` — a single element has no gaps to fill,
  matching `join`'s no-separator-needed behavior for a one-element list.
- `interpose([], 0);` is `[]`.
- `interpose([1, 2], "x");` is `[1, "x", 2]` — the separator's type
  need not match the list elements' type.
- `interpose(5, 0);` (non-list first argument) raises
  `CinderRuntimeError` naming `interpose` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `interleave`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `interpose` added near `interleave` — leave that to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `truncate` — cap a string's length, appending a suffix when cut

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
  `CinderRuntimeError` naming `truncate` and `number` in the message.
- `truncate("hello", "3", "...");` (non-int second argument) raises
  `CinderRuntimeError` naming `truncate` and `string` in the message.
- `truncate("hello", -1, "...");` (negative `max_length`) raises
  `CinderRuntimeError` naming `truncate` and `-1` in the message.
- `truncate("hello", 3, 5);` (non-string third argument) raises
  `CinderRuntimeError` naming `truncate` and `number` in the message.
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

## 5. Standard library: `chars` — split a string into a list of its characters

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
  `chars` and `number` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `lines`/`words`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `chars` added near `lines`/`words` — leave that to the
Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
