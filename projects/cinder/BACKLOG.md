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

## 1. Standard library: `reject` — `filter`'s inverse

Build: add `reject(list, fn)` to `cinder/builtins.py`, the predicate
complement of `filter` (`cinder/builtins.py:2127-2140`) — keeps every
element the predicate is falsy for instead of truthy for, closing the
same "opposite of an existing predicate combinator" gap that
`omit`/`omit_by` already closed for `pick`/`pick_by`, but `filter` has
never had one. Model directly on `_filter`'s structure line for line
(arity 2, first argument a `list` else `CinderRuntimeError` naming
`reject` and `type_name`, matching `"reject() requires a list as its
first argument, got {type_name}"`; second argument must be
`_is_callable` else `CinderRuntimeError` matching `"reject() requires a
function as its second argument, got {type_name}"`), but invert the
truthiness check in the comprehension: `[item for item in items if not
is_truthy(call_value(fn, [item], line, column))]` — the single-character
difference from `_filter`'s body (`not is_truthy(...)` instead of
`is_truthy(...)`) is the entire behavioral distinction between the two
functions. Register it in the builtins dict near `filter`
(`cinder/builtins.py:2551`, `"filter": _filter,`).

Acceptance criteria:
- `reject([1, 2, 3, 4], fn(n) { return n % 2 == 0; });` is `[1, 3]` —
  the primary case, pin as the main regression test; contrast with
  `filter` on the same input/predicate returning `[2, 4]` to prove this
  isn't accidentally aliased to `filter`.
- `reject([], fn(n) { return true; });` is `[]` and the function is
  never called — mirrors `filter`'s existing "on empty list returns []
  and never calls fn" test shape.
- `reject([1, 2, 3], fn(n) { return false; });` is `[1, 2, 3]` (the
  predicate is always falsy, so every element is kept) and
  `reject([1, 2, 3], fn(n) { return true; });` is `[]` (always truthy,
  so nothing is kept) — the two boundary cases.
- `reject([0, 1, nil, 2, false], fn(n) { return n == 1; });` is
  `[0, nil, 2, false]` — pins that `reject` only removes elements where
  the predicate itself returns truthy, not elements that are themselves
  falsy (that's `compact`'s job, a different builtin); the predicate's
  return value truthiness is what's inverted, not the element's.
- `reject(5, fn(n) { return true; });` (a non-list first argument)
  raises `CinderRuntimeError` naming `reject` and `number` in the
  message.
- `reject([1, 2], 5);` (a non-function second argument) raises
  `CinderRuntimeError` naming `reject` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `filter`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `reject` added near `filter` — leave that to the Architect's next
grooming pass, not this task.

---

## 2. Standard library: `find_last` — reverse-search counterpart to `find`

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
and `filter` in task 1. Register it in the builtins dict near `find`
(`cinder/builtins.py:2483`, `"find": _find,`).

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

## 3. Standard library: `none` — the "no element truthy" complement to `any`/`all`

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
`any`/`all` (`cinder/builtins.py:2518-2519`, `"any": _any,` /
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

## 4. Standard library: `zip_object` — build a map from parallel keys/values lists

Build: add `zip_object(keys, values)` to `cinder/builtins.py`, the
inverse of `items` (`cinder/builtins.py:267-274`, a map to a list of
`[key, value]` pairs) approached from the `zip` side instead of the
`from_entries` side — `from_entries` (`cinder/builtins.py:277-`) already
builds a map from a list of `[key, value]` pairs, and `zip`
(`cinder/builtins.py:1922-1935`) already pairs up two parallel lists
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
same map-key validity check `frequencies` uses, see
`cinder/builtins.py:2349-2352`) on each element of `keys` — a
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
(`cinder/builtins.py:2461-2462`, `"items": _items,` /
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
