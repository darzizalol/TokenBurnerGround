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

## 1. Language: slice step — `list[start:end:step]` / `string[start:end:step]` [claimed 2026-08-05T19:48:40Z]

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

## 2. Standard library: `is_divisible` — two-argument numeric divisibility predicate

Build: add `is_divisible(a, b)` to `cinder/builtins.py`. `is_even`
(`cinder/builtins.py:1062-1065`) and `is_odd` (`cinder/builtins.py:1068-1071`)
already answer "is this divisible by 2" (and its complement) for one fixed
divisor, but there is no way to ask the same question for any other
divisor — today that requires the caller to write `x % n == 0` by hand,
sidestepping the `is_even`/`is_odd`-style int validation entirely. This is
the general case those two special-case, so group it in the same block,
immediately after `is_odd`, ahead of `is_prime`.

Model directly on `_is_even`'s/`_is_odd`'s structure
(`cinder/builtins.py:1062-1071`) for the arity and per-argument validation,
and on `_pow`'s two-argument error-message shape
(`cinder/builtins.py:1191-1203`, one message naming "first argument", one
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

## 3. Standard library: `is_ascii` — string ASCII-content predicate

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

## 4. Standard library: `is_subset`/`is_superset` — set-membership predicates for lists

Build: add `is_subset(list1, list2)`/`is_superset(list1, list2)` to
`cinder/builtins.py`. `union`/`intersection`/`difference`/
`symmetric_difference` (`cinder/builtins.py:1624-1649`) already treat
lists as unordered sets via the shared `_require_two_lists`/
`_contains_value` helpers, but there is no way to ask whether one
list's elements are entirely contained in another without computing
`difference(a, b)` and checking the result is empty by hand. This is
the predicate half of that same set-ops family — group it right after
`symmetric_difference`, ahead of `interleave`.

Model directly on `_difference`'s structure
(`cinder/builtins.py:1636-1640`): reuse `_require_two_lists("is_subset",
arguments, line, column)` for arity-2 + list-type validation on both
arguments (already produces "requires a list as its first/second
argument, got {type_name}" errors, matching this family's existing
message shape — no new error strings to invent), and `_contains_value`
for membership checks (deep equality via `values_equal`, consistent
with how `intersection`/`difference` already compare elements). `A is
subset of B` means every element of `A` is found in `B`:
`is_subset(list1, list2)` returns `all(_contains_value(list2, element)
for element in list1)` (no need to `_dedupe` first — a duplicate
element that's present is still present, dedup would only cost cycles
here, not change the answer). `is_superset(list1, list2)` is the
mirror question — every element of `list2` found in `list1` — so
implement it by delegating straight to the same subset check with
arguments flipped, the same reuse-over-reimplementation spirit
`is_odd`/`not is_divisible(x, 2)` already follow elsewhere in this
backlog: validate both arguments as lists under the `is_superset` name
first (so a bad argument is reported as `is_superset`, not `is_subset`,
in the error message), then return the same "every element of the
second list found in the first" check with the roles swapped.

Acceptance criteria:
- `is_subset([1, 2], [1, 2, 3]);` is `true`.
- `is_subset([1, 2, 3], [1, 2]);` is `false` — `3` is missing from the
  second list.
- `is_subset([], [1, 2, 3]);` is `true` — the empty list is a subset of
  everything, including another empty list (`is_subset([], []);` is
  `true`).
- `is_subset([1, 2, 3], []);` is `false`.
- `is_superset([1, 2, 3], [1, 2]);` is `true`; `is_superset([1, 2],
  [1, 2, 3]);` is `false` — exactly the flipped-argument reading of
  `is_subset`.
- `is_subset(a, b);` and `is_superset(b, a);` agree for arbitrary lists
  `a`/`b`.
- `is_subset([1, 1, 2], [1, 2]);` is `true` — duplicates in the first
  list don't require duplicate matches in the second.
- `is_subset([[1, 2]], [[1, 2], [3, 4]]);` is `true` — membership uses
  deep equality (via `_contains_value`'s `values_equal`), not reference
  identity, so a structurally-equal nested list counts as present.
- `is_subset(5, [1, 2]);` / `is_subset([1, 2], 5);` (non-list argument,
  either position) raises `CinderRuntimeError` naming `is_subset` and
  which position (first/second) failed; same pattern for `is_superset`
  naming `is_superset`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column, for both builtins.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `symmetric_difference`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_subset`/`is_superset` added near
`union`/`intersection`/`difference`/`symmetric_difference` — leave that
to the Architect's next grooming pass, not this task.

---

## 5. Language: destructuring assignment — `[a, b] = expr;`

Build: extend list-pattern destructuring to plain assignment, not just
`let`/`for`. Today `let [a, b] = expr;` and `for [k, v] in items(m) { ... }`
both bind fresh names via `DestructureLetStmt` (`cinder/ast_nodes.py:240-246`,
`cinder/interpreter.py:266-284`), but there is no way to destructure into
*already-declared* bindings — `[a, b] = [b, a];` (the classic swap idiom)
today is a `ParseError` ("invalid assignment target"), since `_assignment`
(`cinder/parser.py:739-753`) only recognizes an `Identifier` or `Index` on
the left of `=`. Per `PROJECT.md`'s stated principle of mixing language
depth with stdlib breadth, this is the depth entry to run after this
batch's `is_divisible`/`is_ascii`/`is_subset`/`is_superset` breadth run.

Scope: **list patterns only** — flat, no nesting, mirroring
`let`'s own "no nesting" rule. Map-pattern assignment (`{a, b} = expr;`) is
explicitly out of scope for this task: `{a, b}` isn't valid `MapLiteral`
syntax (no `:` pairs) so making it parse would require touching the
statement-level `{`-disambiguation logic in `PROJECT.md`'s design
principles, a separate and larger change — leave it for a future task.

Grammar: in `_assignment` (`cinder/parser.py:739-753`), `expr = self._ternary()`
already parses a bracketed left-hand side as an ordinary `ListLiteral`
(`cinder/ast_nodes.py:80-84`, `elements: list` mixing plain `Expr`s with
`Spread` wrappers) before the `=` is even seen — so when `self._check(TokenType.EQ)`
and `isinstance(expr, ListLiteral)`, validate its `elements` the same shape
`_destructure_list_pattern` (`cinder/parser.py:307-...`) already enforces:
every element must be a plain `Identifier`, except optionally the *last*
element may be a `Spread` wrapping an `Identifier` (becomes the rest name);
a `Spread` anywhere but last, or any element that isn't an `Identifier`
(nested list, literal, call, etc.), or zero elements, raises the existing
`ParseError("invalid assignment target", ...)` at the `=` token's
line/column — same message already used for every other invalid target,
no new wording needed. On success, build a new `DestructureAssign` AST
node (add to `cinder/ast_nodes.py`, as an **`Expr`**, not a `Stmt` — unlike
`DestructureLetStmt` this has no leading keyword to disambiguate at
statement level, so it must slot into `_assignment`'s `Expr`-returning
signature): fields `names: list`, `rest: "str | None"`, `value: "Expr"`,
`line: int`, `column: int` (deliberately the same shape as
`DestructureLetStmt` minus `is_map`, since map patterns aren't in scope
here). Only bare `=` triggers this — `[a, b] ??= x` or any compound-assign
op on a `ListLiteral` LHS should keep falling through to the existing
"invalid assignment target" raise unchanged, no new grammar for those.

Evaluator: in `evaluate()` (`cinder/interpreter.py:213-257`), add
`isinstance(expr, DestructureAssign)` dispatching to a new
`_evaluate_destructure_assign`. Evaluate `expr.value`, validate it's a
list and length-check against `names`/`rest` — reuse the exact same
messages `_bind_list_destructure` (`cinder/interpreter.py:384-418`) already
raises ("cannot destructure {type_name} as a list", "destructuring pattern
expects {n} elements, got {m}" / "...at least {n} elements, got {m}") — then
assign (not define) each name via `env.assign(name, item)` instead of
`env.define`, since these must be bindings that already exist. Mirror
`_evaluate_assign`'s (`cinder/interpreter.py:727-739`) exact error
translation for each name: a `KeyError` from `env.assign` (undefined name)
becomes `CinderRuntimeError(self._undefined_name_message(name, env), ...)`;
a `_ConstAssignError` (name is `const`) becomes
`CinderRuntimeError(f"cannot assign to const {name!r}", ...)`. Whether to
extend `_bind_list_destructure` with a mode flag or write a small sibling
method is an implementation detail — either is fine as long as the
length-mismatch messages stay identical to the `let`-destructure path and
the per-name assign errors match `_evaluate_assign`'s shape above. Return
the assigned list value (matching `_evaluate_assign`'s "assignment is an
expression, returns the value" behavior) so `[a, b] = [b, a];` composes
the same way plain `x = y;` does (e.g. usable as an `ExprStmt`, or inside a
C-style `for` loop's init/step clause, though only the `ExprStmt` case
needs a test).

Acceptance criteria:
- `let a = 1; let b = 2; [a, b] = [b, a]; print(a); print(b);` prints `2`
  then `1` — the classic swap idiom.
- `let a = 0; let b = 0; let rest = []; [a, b, ...rest] = [1, 2, 3, 4];`
  gives `a` = `1`, `b` = `2`, `rest` = `[3, 4]`.
- `let a = 0; let b = 0; [a, b] = [1];` raises `CinderRuntimeError`
  matching `"destructuring pattern expects 2 elements, got 1"`.
- `let a = 0; [a] = 5;` (non-list RHS) raises `CinderRuntimeError` matching
  `"cannot destructure int as a list"`.
- `[undefined_a, undefined_b] = [1, 2];` (names never `let`-declared)
  raises `CinderRuntimeError` with the same undefined-name message shape
  `x = 1;` on an undeclared `x` already produces.
- `const a = 1; let b = 2; [a, b] = [3, 4];` raises `CinderRuntimeError`
  matching `"cannot assign to const 'a'"`.
- `[1, 2] = [3, 4];` (literal, not identifier, as a pattern element) and
  `[[a, b], c] = [[1, 2], 3];` (nested pattern) both raise `ParseError`
  ("invalid assignment target") — flat identifiers only, no nesting.
- `[a, ...rest, b] = [1, 2, 3];` (rest not last) raises `ParseError`.
- Plain `let [a, b] = expr;` declarations and `for [k, v] in items(m) { ... }`
  loops are unaffected — this task only adds a new path through
  `_assignment`, it does not touch `_let_statement`/`_destructure_let_statement`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`, `tests/test_interpreter.py`
(grep for `DestructureLetStmt`/`_bind_list_destructure` first for exact
current locations — line numbers above may have shifted if earlier tasks
this cycle landed first). Once merged, README.md's destructuring bullet
needs this new assignment form documented, and PROJECT.md's roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 6. Standard library: `is_disjoint` — no-common-elements predicate for lists

Build: add `is_disjoint(list1, list2)` to `cinder/builtins.py`.
`union`/`intersection`/`difference`/`symmetric_difference`/`is_subset`/
`is_superset` (`cinder/builtins.py:1613-1661` roughly, see current line
numbers) already treat lists as unordered sets, but there is still no
direct way to ask "do these two lists share *any* element at all" without
computing `intersection(a, b)` and checking the result is empty by hand.
This is the one predicate that set-ops family still leaves implicit —
group it right after `is_superset` (task 4, if merged first) or right
after `symmetric_difference` otherwise.

Model directly on `_is_subset`'s structure (from task 4, or `_difference`'s
at `cinder/builtins.py:1636-1640` if task 4 hasn't merged yet): reuse
`_require_two_lists("is_disjoint", arguments, line, column)` for arity-2 +
list-type validation on both arguments (same "requires a list as its
first/second argument, got {type_name}" errors, no new message shape), and
`_contains_value` for membership checks (deep equality via `values_equal`,
consistent with the rest of this family). `is_disjoint(list1, list2)`
returns `not any(_contains_value(list2, element) for element in list1)` —
true when no element of `list1` is found in `list2` (equivalently, their
`intersection` would be empty); no need to `_dedupe` first, a duplicate
element that's present still makes the lists non-disjoint.

Acceptance criteria:
- `is_disjoint([1, 2], [3, 4]);` is `true`.
- `is_disjoint([1, 2], [2, 3]);` is `false` — `2` is shared.
- `is_disjoint([], [1, 2, 3]);` is `true`, `is_disjoint([], []);` is
  `true` — the empty list shares nothing with anything, including itself.
- `is_disjoint(a, b);` and `is_intersection(a, b)` being empty agree for
  arbitrary lists `a`/`b` (i.e. `is_disjoint(a, b)` matches
  `len(intersection(a, b)) == 0` for every case, without literally calling
  `intersection`).
- `is_disjoint([[1, 2]], [[1, 2]]);` is `false` — membership uses deep
  equality (via `_contains_value`'s `values_equal`), not reference
  identity, so a structurally-equal nested list still counts as shared.
- `is_disjoint(5, [1, 2]);` / `is_disjoint([1, 2], 5);` (non-list argument,
  either position) raises `CinderRuntimeError` naming `is_disjoint` and
  which position (first/second) failed.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_subset`/
`is_superset` if task 4 already landed, else near `symmetric_difference`
— see current line numbers, shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_disjoint` added near `union`/`intersection`/`difference`/
`symmetric_difference`/`is_subset`/`is_superset` — leave that to the
Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
