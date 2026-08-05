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

## 1. Standard library: `is_unique` — test whether a list has no duplicate elements

Build: add `is_unique(list)` to `cinder/builtins.py`. `unique`
(`cinder/builtins.py:1564-1571`) already strips duplicates out of a
list via its `_dedupe` helper, but there is no way to ask *whether* a
list had any duplicates in the first place without discarding that
information — today that requires calling `unique(xs)` and comparing
`len` by hand. This is the same "ask, don't force" gap `is_sorted`
fills for ordering, applied to uniqueness instead — a
property predicate on a list's existing contents, not a kind
predicate, so group it with `is_sorted`/`is_palindrome` near
`is_string`, not with `unique`/`distinct_by` themselves.

Model directly on `_unique`'s structure
(`cinder/builtins.py:1564-1571`): same arity-1 check via
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

## 2. Language: slice step — `list[start:end:step]` / `string[start:end:step]`

Build: extend the slicing syntax to accept an optional third `:step`
component, mirroring Python's extended-slice syntax closely enough to be
familiar without importing all of its edge cases. Today's grammar
(`_finish_index` in `cinder/parser.py:975-987`) stops at `start:end`; there
is no way to skip elements or reverse a sequence via slicing at all, so
whole-sequence `reverse()` and manual index loops are still the only tools
for anything step-based. Tasks 1-3 above are all stdlib-breadth predicates;
per `PROJECT.md`'s stated principle of mixing language depth with stdlib
breadth "rather than running either in one long block," this is the
language-depth entry to run alongside them.

Grammar: after parsing `end` inside `_finish_index`'s existing `if
self._check(TokenType.COLON):` branch, check for a second `COLON` and if
present parse an optional `step` expression before the `]` (same
optional-omit-defaults-to-`None` pattern already used for `start`/`end` —
`xs[::2]`, `xs[1::2]`, `xs[:5:2]`, `xs[::-1]` must all parse; a bare
`xs[start:end]` with no second colon must keep parsing exactly as it does
today, unchanged). Extend `SliceExpr` (`cinder/ast_nodes.py:150-156`) with a
`step: "Expr | None"` field.

Evaluator: in `_evaluate_slice` (`cinder/interpreter.py:607-625`), evaluate
`step` the same way `start`/`end` already are, requiring it to be a non-zero
int else `CinderRuntimeError` ("slice step must be an int" / "slice step
must not be zero", matching the existing "slice bound must be an int"
message shape). `_normalize_slice_bound` (`cinder/interpreter.py:1002-1007`)
assumes a forward, clamping walk that is wrong once a negative step is
allowed (Python's own `slice.indices()` swaps the implicit start/end
defaults when the step is negative) — do not reuse it unmodified for the
step case; simplest correct approach is delegating straight to Python's own
`slice(start, end, step).indices(length)` (or just `obj[start:end:step]`
with Python `None`s substituted for omitted bounds) rather than
hand-rolling the negative-step bound math, the same "ask, don't force"
delegation spirit `is_upper`/`is_lower`/`is_alpha`-family tasks already
follow for Python's `str` predicates.

Acceptance criteria:
- `[1, 2, 3, 4, 5][::2];` is `[1, 3, 5]`.
- `[1, 2, 3, 4, 5][::-1];` is `[5, 4, 3, 2, 1]` — full reversal.
- `[1, 2, 3, 4, 5][1:4:2];` is `[2, 4]`.
- `"abcdef"[::2];` is `"ace"`, `"abcdef"[::-1];` is `"fedcba"`.
- `[1, 2, 3, 4, 5][::1];` (explicit default step) is identical to
  `[1, 2, 3, 4, 5][:];` — no regression for the already-shipped two-colon
  form, and omitting the step entirely (`xs[1:3]`) keeps working exactly as
  it does today (still a two-element `SliceExpr` bound, `step` defaulting to
  `None`/`1` internally).
- `[1, 2, 3][::0];` raises `CinderRuntimeError` ("slice step must not be
  zero").
- `[1, 2, 3]["a"::];`(non-int step) raises `CinderRuntimeError` ("slice step
  must be an int").
- Slicing a non-list/non-string with a step (e.g. `5[::2];`) still raises
  the existing "not sliceable" error.
- Slices remain not assignable regardless of step (unchanged from today —
  `xs[::2] = ...` must fail the same way `xs[1:3] = ...` already does, no
  new grammar should make either form an assignment target).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`, `tests/test_interpreter.py`
(grep for `SliceExpr`/`slice` first for exact current test locations).
Once merged, README.md's slicing bullet (`list[start:end]`/
`string[start:end]`) needs the step form documented, and PROJECT.md's
roadmap paragraph needs slice-step moved from backlog to landed — leave
both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_divisible` — two-argument numeric divisibility predicate

Build: add `is_divisible(a, b)` to `cinder/builtins.py`. `is_even`
(`cinder/builtins.py:1032-1035`) and `is_odd` (`cinder/builtins.py:1038-1041`)
already answer "is this divisible by 2" (and its complement) for one fixed
divisor, but there is no way to ask the same question for any other
divisor — today that requires the caller to write `x % n == 0` by hand,
sidestepping the `is_even`/`is_odd`-style int validation entirely. This is
the general case those two special-case, so group it in the same block,
immediately after `is_odd`, ahead of `is_prime`.

Model directly on `_is_even`'s/`_is_odd`'s structure
(`cinder/builtins.py:1032-1041`) for the arity and per-argument validation,
and on `_pow`'s two-argument error-message shape
(`cinder/builtins.py:1160-1172`, one message naming "first argument", one
naming "second argument") since `is_divisible` also takes two arguments:
arity-2 check via `_require_arity("is_divisible", arguments, 2, line,
column)`, then `_require_int("is_divisible", a, line, column)` and
`_require_int("is_divisible", b, line, column)` for `a` and `b` in turn
(reuses the existing helper, so the error message is already
`"is_divisible() requires an int, got {type_name}"` for whichever argument
fails — no separate "first"/"second" wording needed since `_require_int`
doesn't take a position). Before evaluating, check `b == 0` explicitly and
raise a dedicated `CinderRuntimeError` ("is_divisible() divisor must not be
zero") rather than letting Python's `%` raise `ZeroDivisionError`
uncaught — the same explicit-guard spirit `pow()` uses for its own
zero-base/negative-exponent edge case, but checked up front here instead of
via `except ZeroDivisionError` since the divisibility case doesn't need
`pow()`'s partial-computation try/except shape. Behavior once validated:
return `a % b == 0`.

Acceptance criteria:
- `is_divisible(10, 5);` is `true`, `is_divisible(10, 3);` is `false`.
- `is_divisible(0, 5);` is `true` — zero is divisible by everything nonzero.
- `is_divisible(-10, 5);` is `true`, `is_divisible(10, -5);` is `true` —
  sign of either argument doesn't affect divisibility.
- `is_even(x);` and `is_divisible(x, 2);` agree for every int `x`; same for
  `is_odd(x)` and `not is_divisible(x, 2)`.
- `is_divisible(10, 0);` raises `CinderRuntimeError` matching
  `"is_divisible() divisor must not be zero"`.
- `is_divisible(1.5, 2);` (non-int first argument) raises
  `CinderRuntimeError` naming `is_divisible` and `float`; same pattern for
  `is_divisible(10, 1.5);` (non-int second argument), `is_divisible(true,
  2);`/`is_divisible(10, true);` (bool, matching `_require_int`'s existing
  bool exclusion), and `is_divisible("10", 2);` (string).
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_even`/`is_odd`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, README.md's Builtins bullet needs
`is_divisible` added near `is_even`/`is_odd` — leave that to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `is_ascii` — string ASCII-content predicate

Build: add `is_ascii(string)` to `cinder/builtins.py`. `is_alpha`/`is_digit`/
`is_alnum`/`is_space` (`cinder/builtins.py:651-688`) already cover a
string's *character class*; there is no way to ask whether a string's
content is restricted to the ASCII range at all (relevant before, say,
handing a string to something byte-oriented) without hand-rolling a loop
over `ord(c) < 128`. This is the same family, one more content predicate
delegating straight to a Python `str` method — group it contiguously
with `is_alpha`/`is_digit`/`is_alnum`/`is_space`, right after `is_space`.

Model directly on `_is_space`'s structure (`cinder/builtins.py:681-688`):
same arity-1 check via `_require_arity("is_ascii", arguments, 1, line,
column)`, same string-type check (else `CinderRuntimeError` matching
`"is_ascii() requires a string, got {type_name}"`). Behavior once
validated: return `value.isascii()` — plain delegation to Python's own
`str.isascii()`, no reimplementation, the same "ask, don't force"
delegation spirit the rest of this family already follows. Note Python's
`str.isascii()` (unlike `isalpha`/`isdigit`/etc.) is `true` for the empty
string — keep that behavior, don't special-case it away.

Acceptance criteria:
- `is_ascii("hello");` is `true`, `is_ascii("Hello123 !");` is `true` —
  letters, digits, punctuation, and spaces are all ASCII.
- `is_ascii("héllo");` is `false` — accented character is non-ASCII.
- `is_ascii("日本語");` is `false` — non-ASCII script entirely.
- `is_ascii("");` is `true` — matches Python's own `"".isascii()`.
- `is_ascii(5);` (non-string argument) raises `CinderRuntimeError` naming
  `is_ascii` and `int` in the message.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_space`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `is_ascii` added near the other `is_*` string predicates — leave
that to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
