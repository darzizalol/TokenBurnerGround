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

## 1. Standard library: `is_sorted` — test whether a list is in non-decreasing order [claimed 2026-08-05T14:04:24Z]

Build: add `is_sorted(list)` to `cinder/builtins.py`. `sort`
(`cinder/builtins.py:1707-1722`) already establishes that Cinder lists
are only orderable when every element is numeric or every element is
a string (never mixed); there is currently no way to check whether a
list already satisfies that order without sorting it and comparing
the result by hand. Like `is_palindrome` above, this is a property
predicate over a sequence's existing arrangement, not a kind
predicate — group it with the other `is_*` predicates near
`is_palindrome`/`is_string`, not with `sort`/`sort_by`, the same
"group by predicate family, not by implementation resemblance"
principle `is_palindrome`'s task above already established.

Model the validation on `_sort`'s structure
(`cinder/builtins.py:1707-1722`): same arity-1 check via
`_require_arity("is_sorted", arguments, 1, line, column)`, same
`list` type check (else `CinderRuntimeError` matching `"is_sorted()
requires a list, got {type_name}"`), same empty-list short-circuit
(`_sort` returns `[]` for empty input; `is_sorted` should return
`true` for empty input — vacuously sorted). For a non-empty list,
reuse `_sort`'s own mixed-type rule: if the elements are neither
all-numeric nor all-string, raise `CinderRuntimeError` matching
`"is_sorted() requires a list of all numbers or all strings"` (same
message shape `sort()` uses, `is_sorted` substituted for `sort`).
Behavior once validated: return `value == sorted(value)` — a
single-element list is trivially sorted (`true`), and this is a
**non-decreasing** check (`is_sorted([1, 1, 2])` is `true`; adjacent
equal elements do not violate order), matching how `_sort` itself
treats equal elements as already in order. Register it in the
builtins dict right after `"is_palindrome": _is_palindrome,` once
that task has landed (else after `"is_string": _is_string,` if
`is_sorted` is picked up first — check the current builtins dict for
whichever has landed).

Acceptance criteria:
- `is_sorted([1, 2, 3]);` is `true` — ascending numbers.
- `is_sorted([3, 2, 1]);` is `false` — descending, not sorted.
- `is_sorted([1, 1, 2]);` is `true` — equal adjacent elements do not
  break non-decreasing order.
- `is_sorted(["a", "b", "c"]);` is `true`, `is_sorted(["c", "a"]);` is
  `false` — string lists use lexicographic order, same as `sort()`.
- `is_sorted([]);` is `true` — empty list, vacuously sorted.
- `is_sorted([5]);` is `true` — single element, trivially sorted.
- `is_sorted([1, "a"]);` (mixed numbers and strings) raises
  `CinderRuntimeError` naming `is_sorted`, matching `sort()`'s own
  mixed-type rejection.
- `is_sorted(5);` (non-list argument) raises `CinderRuntimeError`
  naming `is_sorted` and `int` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_palindrome`/the
other `is_*` predicates, see current line numbers — shift if earlier
tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_sorted` added near the
other `is_*` predicates — leave that to the Architect's next grooming
pass, not this task.

---

## 2. Standard library: `is_upper`/`is_lower` — string case predicates

Build: add `is_upper(string)` and `is_lower(string)` to
`cinder/builtins.py`. `swap_case` flips case, `upper`/`lower` force
case, but there is no builtin to ask whether a string is *already*
entirely one case — the same gap `is_even`/`is_odd` fill for parity,
applied to string casing this time. Like `is_palindrome` (already
shipped), this is a property predicate on a string's existing content,
not a kind predicate on any value — group it with `is_palindrome`
near `is_string`, not with the case-manipulation builtins
(`upper`/`lower`/`capitalize`/`title`/`swap_case`) it superficially
resembles, the same "group by predicate family, not by implementation
resemblance" principle `is_palindrome`'s task already established.

Model directly on `_swap_case`'s structure
(`cinder/builtins.py:611-618`): same arity-1 check via
`_require_arity("is_upper"/"is_lower", arguments, 1, line, column)`,
same single type check (argument a `string` else
`CinderRuntimeError` matching `"is_upper() requires a string, got
{type_name}"` / `"is_lower() requires a string, got {type_name}"`).
Behavior once validated: delegate directly to Python's own
`value.isupper()` / `value.islower()` — no reimplementation, matching
how `swap_case` delegates to `str.swapcase()`. This inherits Python's
semantics for free: digits/punctuation/whitespace are case-neutral
and don't affect the result, but at least one cased character must be
present, so a string with no cased characters at all (digits-only,
empty, whitespace-only, punctuation-only) is neither upper nor lower.

Acceptance criteria:
- `is_upper("ABC");` is `true`, `is_lower("abc");` is `true`.
- `is_upper("abc");` is `false`, `is_lower("ABC");` is `false`.
- `is_upper("Abc");` is `false`, `is_lower("Abc");` is `false` — mixed
  case is neither.
- `is_upper("ABC123");` is `true`, `is_lower("abc123");` is `true` —
  digits are case-neutral and don't break an otherwise-uniform-case
  string.
- `is_upper("123");` is `false`, `is_lower("123");` is `false` — no
  cased characters at all, so neither predicate holds (matches
  Python's `str.isupper()`/`str.islower()` on digit-only input).
- `is_upper("");` is `false`, `is_lower("");` is `false` — empty
  string has no cased characters either.
- `is_upper(5);` (non-string argument) raises `CinderRuntimeError`
  naming `is_upper` and `int` in the message; same for `is_lower(5);`
  naming `is_lower`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column, for both functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_palindrome`/the
other `is_*` predicates once that's landed, else near `is_string`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_upper`/`is_lower` added near the other `is_*`
predicates — leave that to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `is_alpha`/`is_digit`/`is_alnum`/`is_space` — string content predicates

Build: add `is_alpha(string)`, `is_digit(string)`, `is_alnum(string)`,
and `is_space(string)` to `cinder/builtins.py`. Task 3 above
(`is_upper`/`is_lower`) answers "what case is this string in"; there
is still no builtin to answer the more basic "what kind of characters
does this string contain" — today that requires manually walking the
string and checking each character's code point against `ord()`
ranges. Like `is_upper`/`is_lower`, these are property predicates on a
string's existing content, not kind predicates on any value — group
all four with `is_upper`/`is_lower`/`is_palindrome` near `is_string`.

Model directly on `_is_upper`'s/`_is_lower`'s structure (once task 2
has landed — same file, same block): same arity-1 check via
`_require_arity(name, arguments, 1, line, column)`, same single type
check (argument a `string` else `CinderRuntimeError` matching
`"is_alpha() requires a string, got {type_name}"` and so on for each
of the other three, name substituted). Behavior once validated:
delegate directly to Python's own `value.isalpha()` / `value.isdigit()`
/ `value.isalnum()` / `value.isspace()` — no reimplementation, the
same "ask, don't force" delegation `is_upper`/`is_lower` already use
for `str.isupper()`/`str.islower()`. This inherits Python's semantics
for free, including that **all four are `false` on the empty string**
(unlike `is_upper`/`is_lower`, which is already documented and tested
behavior for those two — this is the same "no characters means no
category holds" rule, just consistently `false` here for every one of
the four rather than needing per-function exceptions).

Acceptance criteria:
- `is_alpha("abc");` is `true`, `is_alpha("abc123");` is `false` —
  digits break a pure-alphabetic string.
- `is_digit("123");` is `true`, `is_digit("12.3");` is `false` — a
  decimal point is not a digit character.
- `is_alnum("abc123");` is `true`, `is_alnum("abc 123");` is `false`
  — a space is neither alphabetic nor a digit.
- `is_space("   ");` is `true`, `is_space(" a ");` is `false`.
- `is_alpha("");` is `false`, `is_digit("");` is `false`,
  `is_alnum("");` is `false`, `is_space("");` is `false` — empty
  string satisfies none of the four (Python's `str.isalpha()` et al.
  are all `false` on `""`).
- `is_alpha(5);` (non-string argument) raises `CinderRuntimeError`
  naming `is_alpha` and `int` in the message; same pattern for
  `is_digit(5);`, `is_alnum(5);`, `is_space(5);`, each naming itself.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column, for all four functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_upper`/`is_lower`
once task 2 has landed, else near `is_string`, see current line
numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_alpha`/`is_digit`/`is_alnum`/`is_space` added near the other
`is_*` predicates — leave that to the Architect's next grooming pass,
not this task.

---

## 4. Standard library: `is_positive`/`is_negative`/`is_zero` — numeric sign predicates

Build: add `is_positive(value)`, `is_negative(value)`, and
`is_zero(value)` to `cinder/builtins.py`. `sign` (`cinder/builtins.py:940-951`)
already reduces a number to `1`/`-1`/`0`, but every caller who only
cares about one branch has to write `sign(x) == 1` (or worse,
`x > 0`, which silently accepts non-numeric input Cinder would
otherwise reject). This is the same family as `is_even`/`is_odd`:
a **property** predicate on a number, not a **kind** predicate on
any value — so, like `is_even`/`is_odd`/`is_prime` and unlike
`is_int`/`is_float`, a non-numeric argument is a type error, not a
`false`. Unlike `is_even`/`is_odd`/`is_prime`, though, these three
apply to *any* number, not just integers — `is_positive(1.5)` is
`true`, matching `sign`'s own float-inclusive behavior.

Model directly on `_sign`'s structure (`cinder/builtins.py:940-951`):
same arity-1 check via `_require_arity(name, arguments, 1, line,
column)`, same `_is_numeric(value)` check (not `_require_int` — floats
are valid input here, matching `sign`, not `is_even`/`is_odd`) else
`CinderRuntimeError` matching `"is_positive() requires a number, got
{type_name}"` and so on for the other two, name substituted. Behavior
once validated: `is_positive` returns `value > 0`, `is_negative`
returns `value < 0`, `is_zero` returns `value == 0` — plain
delegation to Python's own comparison operators, no reimplementation,
the same "ask, don't force" spirit `is_upper`/`is_lower` (task 2
above) use for Python's `str` predicates. `is_zero(0.0)` is `true`
(Python's `0.0 == 0` is `true`; no special-casing float zero).
Register the trio in the builtins dict right after `"sign": _sign,`,
keeping the numeric-property-predicate family (`sign`/`is_positive`/
`is_negative`/`is_zero`) contiguous, distinct from the integer-only
`is_even`/`is_odd`/`is_prime` trio elsewhere in the file.

Acceptance criteria:
- `is_positive(5);` is `true`, `is_positive(1.5);` is `true`,
  `is_positive(-5);` is `false`, `is_positive(0);` is `false`.
- `is_negative(-5);` is `true`, `is_negative(-1.5);` is `true`,
  `is_negative(5);` is `false`, `is_negative(0);` is `false`.
- `is_zero(0);` is `true`, `is_zero(0.0);` is `true`,
  `is_zero(5);` is `false`, `is_zero(-5);` is `false`.
- Exactly one of the three is `true` for any given number (mutual
  exclusivity), matching `sign`'s own three-way partition.
- `is_positive("5");` (non-numeric string) raises `CinderRuntimeError`
  naming `is_positive` and `string` in the message; same pattern for
  `is_negative("5");` and `is_zero("5");`, each naming itself.
- `is_positive(true);` raises `CinderRuntimeError` — a bool is not a
  number, matching `sign(true)`'s existing behavior via
  `_is_numeric`; same for `is_negative(true);` and `is_zero(true);`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column, for all three functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `sign`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_positive`/`is_negative`/`is_zero` added near `sign` — leave
that to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `is_unique` — test whether a list has no duplicate elements

Build: add `is_unique(list)` to `cinder/builtins.py`. `unique`
(`cinder/builtins.py:1486-1493`) already strips duplicates out of a
list via its `_dedupe` helper, but there is no way to ask *whether* a
list had any duplicates in the first place without discarding that
information — today that requires calling `unique(xs)` and comparing
`len` by hand. This is the same "ask, don't force" gap `is_sorted`
(task 1) fills for ordering, applied to uniqueness instead — a
property predicate on a list's existing contents, not a kind
predicate, so group it with `is_sorted`/`is_palindrome` near
`is_string`, not with `unique`/`distinct_by` themselves.

Model directly on `_unique`'s structure
(`cinder/builtins.py:1486-1493`): same arity-1 check via
`_require_arity("is_unique", arguments, 1, line, column)`, same `list`
type check (else `CinderRuntimeError` matching `"is_unique() requires
a list, got {type_name}"`). Unlike `is_sorted`, there is no
numbers-only-or-strings-only restriction to enforce — `unique()`
itself places none (it dedupes via `values_equal`, which already
handles every Cinder value, including nested lists/maps by deep
equality), so `is_unique` shouldn't either. Behavior once validated:
call the existing `_dedupe(value)` helper and return
`len(_dedupe(value)) == len(value)` — reuse, don't reimplement the
comparison logic, the same delegation spirit `unique`'s own
`_dedupe` helper already embodies. An empty list and a single-element
list are both trivially unique (`true`).

Acceptance criteria:
- `is_unique([1, 2, 3]);` is `true` — all distinct.
- `is_unique([1, 2, 2]);` is `false` — one duplicate.
- `is_unique([]);` is `true` — empty list, vacuously unique.
- `is_unique([5]);` is `true` — single element, trivially unique.
- `is_unique(["a", "b", "a"]);` is `false` — duplicates detected for
  strings too, not just numbers.
- `is_unique([[1, 2], [1, 2]]);` is `false` — duplicate detection uses
  deep equality (via `_dedupe`'s existing `values_equal`), not
  reference identity, so two structurally-equal nested lists count as
  duplicates.
- `is_unique(5);` (non-list argument) raises `CinderRuntimeError`
  naming `is_unique` and `int` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `unique`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_unique` added near the other `is_*` predicates —
leave that to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
