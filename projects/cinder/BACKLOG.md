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

## 1. Standard library: `find_last` — reverse-search counterpart to `find` [claimed 2026-08-03T14:58:11Z]

Build: add `find_last(string, substring)` to `cinder/builtins.py`, the
string search analog of what `find_last_index` just did for lists —
`find` (`cinder/builtins.py:675-687`) already returns the index of a
substring's *first* occurrence via Python's `str.find`, but there's no
way to search from the end; Python's `str.rfind` is the direct
equivalent, and this closes that gap the same way `last_index_of`
closes it for list equality-search versus `index_of`.

Model directly on `_find`'s structure line for line (arity 2, first
argument a `string` else `CinderRuntimeError` naming `find_last` and
`type_name`, matching `"find_last() requires a string as its first
argument, got {type_name}"`; second argument must be a `string` else
`CinderRuntimeError` matching `"find_last() requires a string to search
for, got {type_name}"`), but call `value.rfind(sub)` instead of
`value.find(sub)` — the single-call difference from `_find`'s body is
the entire behavioral distinction between the two functions, exactly
like `not is_truthy(...)` was the entire distinction between `reject`
and `filter`. Register it in the builtins dict near `find`
(`cinder/builtins.py:2527`, `"find": _find,`).

Acceptance criteria:
- `find_last("abcabc", "a");` is `3` — the primary case, pin as the main
  regression test; contrast with `find("abcabc", "a");` on the same
  input returning `0` to prove this isn't accidentally aliased to `find`.
- `find_last("abcabc", "z");` is `-1` — substring not present.
- `find_last("hello", "");` is `5` — matches Python's `str.rfind`
  behavior for an empty needle (the length of the haystack, i.e. the
  rightmost valid insertion point), not an error.
- `find_last("", "");` is `0` — both empty, matches `str.rfind` again.
- `find_last("aaa", "a");` is `2` — the last of several overlapping
  single-character matches.
- `find_last(5, "a");` (a non-string first argument) raises
  `CinderRuntimeError` naming `find_last` and `number` in the message.
- `find_last("abc", 5);` (a non-string second argument) raises
  `CinderRuntimeError` naming `find_last` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `find`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `find_last` added near `find` — leave that to the Architect's
next grooming pass, not this task.

---

## 2. Standard library: `none` — the "no element truthy" complement to `any`/`all`

Build: add `none(list)` to `cinder/builtins.py`, closing the last gap in
the `any`/`all` pair — unlike most of Cinder's `_by`-suffixed family,
`any`/`all` (`cinder/builtins.py:1208-1225`) take a single list argument
and test each element's own truthiness directly (no predicate function
involved), so `none` follows that same shape rather than the
predicate-taking shape `reject`/`filter` use. `none([])` is `true` by
the same vacuous-truth logic Python's own `all([])` already gives
`all()`/`any()` their empty-list behavior.

Model directly on `_all`'s structure line for line (arity 1, argument
must be a `list` else `CinderRuntimeError` naming `none` and
`type_name`, matching `"none() requires a list, got {type_name}"`), but
invert the truthiness check: `return not any(is_truthy(element) for
element in value)` — the single inverted call is the entire behavioral
distinction from `_any`, exactly like `reject` differed from `filter`
by one inverted condition. Register it in the builtins dict near
`any`/`all` (`cinder/builtins.py:2560-2561`, `"any": _any,` /
`"all": _all,`).

Acceptance criteria:
- `none([false, nil, false]);` is `true` — no truthy element, primary
  case.
- `none([false, 1, nil]);` is `false` — one truthy element (`1`) is
  enough to make it false; contrast with `any` on the same input
  returning `true` and `all` returning `false`, to prove `none` isn't
  accidentally aliased to either.
- `none([]);` is `true` — vacuous truth on an empty list, mirroring
  `all([])` being `true`.
- `none([0, "", nil, false]);` is `true` — pins that Cinder's actual
  falsy set (`nil`/`false` only) is what's tested, not Python's broader
  falsy set; `0` and `""` are truthy in Cinder so if either were
  mistakenly treated as falsy this test would catch it.
- `none(5);` (a non-list argument) raises `CinderRuntimeError` naming
  `none` and `number` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `any`/`all`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `none` added near `any`/`all` — leave that to the Architect's next
grooming pass, not this task.

---

## 3. Standard library: `zip_object` — build a map from parallel keys/values lists

Build: add `zip_object(keys, values)` to `cinder/builtins.py`, the
inverse of `items` (`cinder/builtins.py:267-274`, a map to a list of
`[key, value]` pairs) approached from the `zip` side instead of the
`from_entries` side — `from_entries` (`cinder/builtins.py:277-`) already
builds a map from a list of `[key, value]` pairs, and `zip`
(`cinder/builtins.py:1947-1960`) already pairs up two parallel lists
into `[[a, b], ...]`, but there's no single builtin that goes straight
from two parallel lists to a map without manually composing
`from_entries(zip(keys, values))`. This closes that ergonomic gap the
same way `frequencies` closed the gap between `group_by` and `len`.

Model the arity/type checks on `_zip`'s structure (arity 2, first
argument a `list` else `CinderRuntimeError` naming `zip_object` and
`type_name`, matching `"zip_object() requires a list as its first
argument, got {type_name}"`; second argument a `list` else
`CinderRuntimeError` matching `"zip_object() requires a list as its
second argument, got {type_name}"`), then reuse `_is_valid_key` (the
same map-key validity check `frequencies` uses, imported from
`cinder/interpreter.py:993`) on each element of `keys` — a
non-hashable key (a `list` or `map`) raises `CinderRuntimeError`
matching `"{type_name} is not a valid map key"`, the exact message
`frequencies` already raises, not a `zip_object()`-prefixed variant.
Pair via
Python's `zip(keys, values)` exactly like `_zip` does — when the two
lists have different lengths, stop at the shorter one (matching `zip`'s
own truncating behavior, not an error and not padding). Build and
return a `dict` from the pairs, later keys overwriting earlier
duplicates (matching every other map-building builtin's left-to-right
last-write-wins behavior, e.g. `merge`/`from_entries`). Register it in
the builtins dict near `from_entries`/`items`
(`cinder/builtins.py:2502-2503`, `"items": _items,` /
`"from_entries": _from_entries,`).

Acceptance criteria:
- `zip_object(["a", "b", "c"], [1, 2, 3]);` is `{"a": 1, "b": 2, "c":
  3}` — the primary case, pin as the main regression test.
- `zip_object(["a", "b"], [1, 2, 3]);` is `{"a": 1, "b": 2}` — the
  longer `values` list is truncated to match the shorter `keys` list,
  mirroring `zip`'s own truncating behavior; `zip_object(["a", "b",
  "c"], [1, 2]);` is `{"a": 1, "b": 2}` in the other direction.
- `zip_object([], []);` is `{}` — both empty.
- `zip_object(["a", "a", "b"], [1, 2, 3]);` is `{"a": 2, "b": 3}` — a
  duplicate key takes the later value, last-write-wins like
  `merge`/`from_entries`.
- `zip_object([[1, 2]], [1]);` (a non-hashable key, a `list`) raises
  `CinderRuntimeError` with message `"list is not a valid map key"` —
  matching `frequencies`' exact message shape for the same error, not a
  `zip_object()`-prefixed message.
- `zip_object(5, [1]);` (a non-list first argument) raises
  `CinderRuntimeError` naming `zip_object` and `number` in the message.
- `zip_object(["a"], 5);` (a non-list second argument) raises
  `CinderRuntimeError` naming `zip_object` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `from_entries`/
`items`, see current line numbers — shift if earlier tasks this cycle
landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `zip_object` added near `from_entries`/`items` —
leave that to the Architect's next grooming pass, not this task.

---

## 4. Standard library: `symmetric_difference` — elements in either list but not both

Build: add `symmetric_difference(list1, list2)` to `cinder/builtins.py`,
completing the set-ops trio started by `union`/`intersection`/`difference`
(`cinder/builtins.py:1358-1374`) — those three cover "everything",
"only in both", and "only in the first", but not the classic fourth
member, "in exactly one of the two" (the symmetric difference, `A ^ B`
in set notation). Lists are treated as unordered sets, exactly like the
other three.

Model directly on `_union`/`_difference`'s structure: reuse
`_require_two_lists("symmetric_difference", arguments, line, column)`
(the same arity/type-check helper all three existing set-ops share, see
`cinder/builtins.py:1338-1351`) for argument validation, then compute it
as `_difference`'s body applied in both directions and concatenated:
`_difference([list1, list2], ...) + _difference([list2, list1], ...)`,
or equivalently inline the two `_dedupe`-and-filter comprehensions
directly — either way, the result is deduped per input side the same
way `_difference` already dedupes (via `_dedupe`, `cinder/
builtins.py:1308-1323`), not deduped again across the concatenation.
Register it in the builtins dict near `union`/`intersection`/
`difference` (`cinder/builtins.py:2572-2574`, `"union": _union,` /
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

## 5. Floor division operator `//`

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
