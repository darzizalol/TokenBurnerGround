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

## 1. Standard library: `symmetric_difference` — elements in either list but not both [claimed 2026-08-03T19:40:16Z]

Build: add `symmetric_difference(list1, list2)` to `cinder/builtins.py`,
completing the set-ops trio started by `union`/`intersection`/`difference`
(`cinder/builtins.py:1406-1424`) — those three cover "everything",
"only in both", and "only in the first", but not the classic fourth
member, "in exactly one of the two" (the symmetric difference, `A ^ B`
in set notation). Lists are treated as unordered sets, exactly like the
other three.

Model directly on `_union`/`_difference`'s structure: reuse
`_require_two_lists("symmetric_difference", arguments, line, column)`
(the same arity/type-check helper all three existing set-ops share, see
`cinder/builtins.py:1386-1398`) for argument validation, then compute it
as `_difference`'s body applied in both directions and concatenated:
`_difference([list1, list2], ...) + _difference([list2, list1], ...)`,
or equivalently inline the two `_dedupe`-and-filter comprehensions
directly — either way, the result is deduped per input side the same
way `_difference` already dedupes (via `_dedupe`, `cinder/
builtins.py:1356-1372`), not deduped again across the concatenation.
Register it in the builtins dict near `union`/`intersection`/
`difference` (`cinder/builtins.py:2623-2625`, `"union": _union,` /
`"intersection": _intersection,` / `"difference": _difference,`).

Acceptance criteria:
- `symmetric_difference([1, 2, 3], [2, 3, 4]);` is `[1, 4]` — the
  primary case: `1` and `4` are each in only one list, `2`/`3` are in
  both and excluded; order is first list's leftovers before second
  list's leftovers.
- `symmetric_difference([1, 2], [1, 2]);` is `[]` — identical lists
  have no elements unique to either side.
- `symmetric_difference([1, 2], []);` is `[1, 2]` and
  `symmetric_difference([], [1, 2]);` is `[1, 2]` — one side empty
  degenerates to the other side's (deduped) contents, matching
  `difference`'s own empty-list behavior.
- `symmetric_difference([], []);` is `[]`.
- `symmetric_difference([1, 1, 2], [2, 3]);` is `[1, 3]` — duplicates
  within a single input list are deduped exactly like `union`/
  `intersection`/`difference` already dedupe (via `_dedupe`), not
  treated as separate occurrences.
- `symmetric_difference(5, [1]);` (a non-list first argument) raises
  `CinderRuntimeError` naming `symmetric_difference` and `number` in
  the message, matching the exact message shape `_require_two_lists`
  already produces for `union`/`intersection`/`difference`.
- `symmetric_difference([1], 5);` (a non-list second argument) raises
  `CinderRuntimeError` naming `symmetric_difference` and `number` in
  the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `union`/
`intersection`/`difference`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `symmetric_difference`
added near `union`/`intersection`/`difference` — leave that to the
Architect's next grooming pass, not this task.

---

## 2. Floor division operator `//`

Build: add a floor-division binary operator `//` to the language,
closing the gap between `/` (true division, `cinder/interpreter.py:812`)
and the `floor()` builtin — right now getting a floored quotient
requires the awkward `floor(a / b)`, and there's no infix form at all.
This is a language-depth task (lexer + token + parser + interpreter),
the same shape as the recent `**` exponentiation operator, not a
stdlib task like tasks 1-4 above.

Model directly on how `**`/`STARSTAR` was added, reusing the exact same
seams, but at `/`'s existing precedence tier instead of a new one (no
`_power`-style right-associative rung is needed — floor division is
left-associative, same tier as `/` and `%`):
- `cinder/tokens.py`: add `SLASHSLASH = auto()` right after `SLASH = auto()`
  (`cinder/tokens.py:54`). Do not add a `SLASHSLASHEQ` — a `//=`
  compound-assignment form is deliberately out of scope for this task
  (mirroring how `**=` was its own separate follow-up task after `**`
  landed, not bundled into the same PR).
- `cinder/lexer.py`: in `_op_or_compound_assign`
  (`cinder/lexer.py:299-320`), add a branch for `char == "/" and
  self._match("/")` that appends a `SLASHSLASH` token with lexeme
  `"//"`, mirroring the existing `char == "*" and self._match("*")`
  branch (`cinder/lexer.py:301-310`) but simpler — no nested `=` check,
  since there's no `SLASHSLASHEQ`. Place this check before the existing
  `_COMPOUND_ASSIGN_TOKENS[char]` unpacking is used for the plain `/`
  path, exactly where the `*` branch sits relative to `STAR`. This does
  not conflict with the block-comment check in
  `_skip_whitespace_and_comments` (`cinder/lexer.py:132-143`), which
  only special-cases `/*`, never `//` — a `//` in source is never
  ambiguous with a comment starter.
- `cinder/parser.py`: add `TokenType.SLASHSLASH` to the `_FACTOR` set
  (`cinder/parser.py:159`, currently `{TokenType.STAR, TokenType.SLASH,
  TokenType.PERCENT}`) so it's parsed at `_factor`
  (`cinder/parser.py:895-901`) with the same left-associative loop as
  `/`/`%` — no new parser method needed.
- `cinder/interpreter.py`: in `_apply_binary_operator`
  (`cinder/interpreter.py:790-834`), add a branch `if op ==
  TokenType.SLASHSLASH: return self._divide_op(operator, left, right,
  lambda a, b: a // b)` right next to the existing `TokenType.SLASH`
  branch (`cinder/interpreter.py:812-813`) — reusing `_divide_op`
  (`cinder/interpreter.py:909-918`) as-is gives floor division the same
  type-check and division-by-zero guard `/` and `%` already have, for
  free; the only new code is the one-line `a // b` branch, exactly like
  `find_last` differed from `_find` by one call.

Acceptance criteria:
- `7 // 2;` is `3` — the primary case.
- `-7 // 2;` is `-4` — floors toward negative infinity like Python's
  `//`, not toward zero like a naive truncating division would give
  (`-3`); this is the test that would catch an accidental `int(a / b)`
  implementation instead of `a // b`.
- `7.5 // 2;` is `3.0` — floor division on a `float` operand returns a
  `float`, matching Python's own `//` type-promotion rule.
- `6 // 2;` is `3` (exact, no remainder).
- `7 // 0;` raises `CinderRuntimeError` with message `"division by zero
  in '//'"` — same message shape `_divide_op` already produces for `/`
  and `%`, just with `//`'s lexeme.
- `"a" // 2;` (non-number operand) raises `CinderRuntimeError` naming
  `'//'` and the operand types, matching `_divide_op`'s existing
  type-error shape for `/`.
- `2 ** 3 // 2;` is `4` — confirms `//` sits at the same precedence
  tier as `/`/`%` (looser than `**`), evaluated left-to-right with
  `*`/`/`/`%` when mixed, e.g. `8 // 2 * 2;` is `8` not `2`.
- A standalone `//` followed by `=` (e.g. `x //= 1;`) is a `ParseError`,
  not a silently-wrong parse — confirms no `SLASHSLASHEQ` token was
  accidentally introduced.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_lexer.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s Operators
bullet needs `//` added near the existing arithmetic operator list, and
a note that a future `//=` compound-assign task remains open — leave
both to the Architect's next grooming pass, not this task.

---

## 3. Compound assignment `//=` for floor division

**Depends on task 2 (`//`) — do not start this until floor division has
merged**, since this task adds no new evaluation semantics of its own,
only sugar over it (same relationship `**=` had to `**`, see
`CHANGELOG.md`'s entries for PRs #155/#157).

Build: add `TokenType.SLASHSLASHEQ` and wire it in as `//`'s
compound-assignment form, mirroring `**=`'s addition line for line:
- `cinder/tokens.py`: add `SLASHSLASHEQ = auto()` right after the
  `SLASHSLASH` token task 2 adds (mirrors `STARSTAR` immediately
  followed by `STARSTAREQ`, `cinder/tokens.py:52-53`).
- `cinder/lexer.py`: in `_op_or_compound_assign`'s `//` branch that
  task 2 adds (mirroring the existing `char == "*" and
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
  the equivalent of `x = x // 2`, reusing task 2's `SLASHSLASH` binary
  handling unchanged, exactly like `**=` needed zero interpreter
  changes beyond what `**` already provided.

Acceptance criteria:
- `let x = 7; x //= 2; x;` is `3`.
- `let x = -7; x //= 2; x;` is `-4` — floors toward negative infinity,
  matching task 2's `//` behavior, not truncation.
- Index and dot-access targets both work: `let xs = [7]; xs[0] //= 2;
  xs[0];` is `3`, and `let m = {"a": 7}; m.a //= 2; m.a;` is `3`.
- `const x = 7; x //= 2;` raises a `CinderRuntimeError` for assigning to
  a const, matching every other compound-assign operator's const-target
  error.
- `let x = 7; x //= 0;` raises `CinderRuntimeError` with message
  `"division by zero in '//'"`, reusing task 2's `_divide_op` guard
  unchanged.
- A standalone `x /= 2` (plain `/=`, not `//=`) still parses and
  behaves exactly as before — confirms the new token doesn't shadow or
  interfere with the existing `/=` path.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/parser.py`,
`tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.
Once merged, `README.md`'s Operators bullet needs `//=` added next to
`//` — leave that to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `replace_first` — replace only the first occurrence

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

## 5. Standard library: `interpose` — insert a separator between list elements

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
