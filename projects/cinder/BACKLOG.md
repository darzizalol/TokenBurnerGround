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

## 1. Standard library: `pad_center` — center a string within a width, padding both sides

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

## 2. Standard library: `is_palindrome` — test whether a string reads the same forwards and backwards

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

## 3. Standard library: `is_int`/`is_float` — split `is_number`'s single kind into its two concrete ones

Build: add `is_int(value)` and `is_float(value)` to `cinder/builtins.py`.
`is_number` (`cinder/builtins.py:2594-2596`) already answers "is this
numeric at all," but there is no builtin to tell the two concrete
numeric kinds apart — every Cinder program that wants to know whether
a value is specifically an integer (say, before using it as a list
index) or specifically a float today has no way to ask short of
comparing it to its own `floor()`, which is wrong for non-numeric
input anyway. This is a **kind** predicate, the same family as
`is_list`/`is_map`/`is_string` (`cinder/builtins.py:2579-2591`), not a
**property** predicate like `is_even`/`is_palindrome` — the distinction
matters for error behavior (see below).

Model directly on `_is_list`'s/`_is_map`'s structure
(`cinder/builtins.py:2579-2586`): same arity-1 check via
`_require_arity("is_int"/"is_float", arguments, 1, line, column)`,
then a single `isinstance` check — **no type error on a non-numeric
argument**, just `false`, exactly like `is_list("x")` is `false`
rather than raising. Behavior once validated: `is_int` returns
`isinstance(value, int) and not isinstance(value, bool)` (Python's
`bool` is an `int` subclass — the existing `_is_numeric` helper at
`cinder/builtins.py:39-40` already excludes `bool` for the same
reason, and `_is_number`'s own tests already cover that a raw `true`/
`false` is not numeric, so `is_int(true)` must also be `false`);
`is_float` returns `isinstance(value, float)` (no `bool` wrinkle here
since `bool` is never a `float` subclass). Register both in the
builtins dict right after `"is_number": _is_number,`
(`cinder/builtins.py:2769`), `is_int` before `is_float`.

Acceptance criteria:
- `is_int(4);` is `true`, `is_float(4);` is `false`.
- `is_int(4.0);` is `false`, `is_float(4.0);` is `true` — a
  whole-valued float is still a float, matching `is_even`'s task-1
  treatment of `4.0` as not an int.
- `is_int(-3);` is `true`, `is_float(-3.5);` is `true`.
- `is_int(true);` is `false` and `is_float(true);` is `false` — a
  bool is neither, even though Python's `bool` is an `int` subclass.
- `is_int("4");` is `false`, `is_float("4");` is `false` — no
  coercion, and no error: a non-numeric argument returns `false`
  rather than raising (contrast with `is_even("4")`, which raises,
  since `is_even`/`is_odd` are property predicates that require a
  numeric argument to be meaningful, while `is_int`/`is_float` are
  kind predicates like `is_list`/`is_map` that classify any value).
- `is_int(nil);` is `false`, `is_int([1, 2]);` is `false`,
  `is_int({});` is `false` — same "any value in, bool out, never
  raises" shape as `is_list`/`is_map`/`is_string`.
- `is_int(4) or is_float(4.0);` composes with `is_number` such that
  `is_number(x)` implies exactly one of `is_int(x)`/`is_float(x)` is
  `true` for every numeric `x`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column, for both functions.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_number`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_int`/`is_float` added near the other `is_*` type
predicates — leave that to the Architect's next grooming pass, not
this task.

---

## 4. Standard library: `is_prime` — test whether an integer is prime

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

## 5. Standard library: `is_sorted` — test whether a list is in non-decreasing order

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
