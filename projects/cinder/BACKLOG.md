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

## 1. Standard library: `is_prime` — test whether an integer is prime

Build: add `is_prime(value)` to `cinder/builtins.py`. `is_even`/`is_odd`
(`cinder/builtins.py:925-934`) already classify an integer's *parity*;
there is no builtin for its most common other property, primality —
today it requires hand-rolling trial division from scratch in Cinder
itself. This is the same family as `is_even`/`is_odd`: a **property**
predicate on an integer, not a **kind** predicate on any value, so
(like `is_even`/`is_odd`, unlike `is_int`/`is_float` above) a
non-integer argument is a type error, not a `false`.

Model directly on `_is_even`'s/`_is_odd`'s structure
(`cinder/builtins.py:925-934`): same arity-1 check via
`_require_arity("is_prime", arguments, 1, line, column)`, same
`value = _require_int("is_prime", arguments[0], line, column)` (so
`is_prime(true)` raises, not returns `false` — booleans are excluded
by `_require_int` itself the same way they're excluded for
`is_even`/`is_odd`, and a whole-valued float like `4.0` is a type
error rather than silently accepted, matching `is_even`'s task-1
precedent). Behavior once validated: `value < 2` returns `false`
(covers negatives, `0`, and `1` — none are prime); otherwise trial
divide by every integer from `2` up to `int(value ** 0.5)` inclusive,
returning `false` on the first exact divisor found and `true` if none
divide evenly. No need for anything fancier (no Miller-Rabin, no
sieve) — Cinder scripts are not performance-critical and trial
division to `sqrt(n)` is the standard minimal-correct approach.
Register it in the builtins dict right after `"is_odd": _is_odd,`
(`cinder/builtins.py:2686`), keeping the integer-property-predicate
trio (`is_even`/`is_odd`/`is_prime`) contiguous.

Acceptance criteria:
- `is_prime(2);` is `true` — smallest prime, and the only even one.
- `is_prime(17);` is `true`, `is_prime(97);` is `true` — larger primes.
- `is_prime(1);` is `false`, `is_prime(0);` is `false`,
  `is_prime(-7);` is `false` — not prime by definition, no error.
- `is_prime(4);` is `false`, `is_prime(9);` is `false`,
  `is_prime(100);` is `false` — composite numbers correctly rejected,
  including perfect squares (exercises the inclusive `sqrt(n)` bound).
- `is_prime(4.0);` (non-int, whole-valued float) raises
  `CinderRuntimeError` naming `is_prime`, matching `is_even`'s task-1
  treatment of the same case.
- `is_prime(true);` raises `CinderRuntimeError` — a bool is not an
  int, matching `is_even(true)`'s existing behavior via
  `_require_int`.
- `is_prime("4");` (non-numeric string) raises `CinderRuntimeError`
  naming `is_prime` and `string` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_even`/`is_odd`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_prime` added near `is_even`/`is_odd` — leave that to
the Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_sorted` — test whether a list is in non-decreasing order

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

## 3. Standard library: `is_upper`/`is_lower` — string case predicates

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

## 4. Standard library: `is_alpha`/`is_digit`/`is_alnum`/`is_space` — string content predicates

Build: add `is_alpha(string)`, `is_digit(string)`, `is_alnum(string)`,
and `is_space(string)` to `cinder/builtins.py`. Task 3 above
(`is_upper`/`is_lower`) answers "what case is this string in"; there
is still no builtin to answer the more basic "what kind of characters
does this string contain" — today that requires manually walking the
string and checking each character's code point against `ord()`
ranges. Like `is_upper`/`is_lower`, these are property predicates on a
string's existing content, not kind predicates on any value — group
all four with `is_upper`/`is_lower`/`is_palindrome` near `is_string`.

Model directly on `_is_upper`'s/`_is_lower`'s structure (once task 3
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
once task 3 has landed, else near `is_string`, see current line
numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_alpha`/`is_digit`/`is_alnum`/`is_space` added near the other
`is_*` predicates — leave that to the Architect's next grooming pass,
not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
