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

## 1. Standard library: `is_ascii` — string ASCII-content predicate

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

## 2. Standard library: `is_subset`/`is_superset` — set-membership predicates for lists

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

## 3. Language: destructuring assignment — `[a, b] = expr;`

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

## 4. Standard library: `is_disjoint` — no-common-elements predicate for lists

Build: add `is_disjoint(list1, list2)` to `cinder/builtins.py`.
`union`/`intersection`/`difference`/`symmetric_difference`/`is_subset`/
`is_superset` (`cinder/builtins.py:1613-1661` roughly, see current line
numbers) already treat lists as unordered sets, but there is still no
direct way to ask "do these two lists share *any* element at all" without
computing `intersection(a, b)` and checking the result is empty by hand.
This is the one predicate that set-ops family still leaves implicit —
group it right after `is_superset` (task 3, if merged first) or right
after `symmetric_difference` otherwise.

Model directly on `_is_subset`'s structure (from task 3, or `_difference`'s
at `cinder/builtins.py:1636-1640` if task 3 hasn't merged yet): reuse
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

## 5. Language: map-pattern destructuring assignment — `{a, b} = expr;`

Build: extend map-pattern destructuring to plain assignment, the map-shaped
counterpart to task 3's list-pattern assignment. Today `let {a, b} = expr;`
binds fresh names via `DestructureLetStmt(is_map=True)` — handled inline in
`Interpreter.execute()` (`cinder/interpreter.py:266-283`: checks `isinstance(value,
dict)`, then for each name raises `"cannot destructure {type_name} as a map"` or
`"destructuring pattern expects key {name!r}, not found in map"` before
`env.define(name, value[name])`) — but there is no way to destructure into
*already-declared* bindings the way task 3 adds for list patterns. Depends on
task 3 landing first (reuses the `DestructureAssign` AST node it introduces);
do not start this before task 3 merges.

Scope: **flat map patterns only** — bare identifiers naming keys to pull out,
exactly like `let {a, b} = expr;` today (no renaming, no nesting, no rest
element — none of those exist for `let`'s map form either, so don't add them
here).

The hard part is grammar, not evaluation. Unlike `[a, b]`, which already
parses as an ordinary `ListLiteral` before task 3 ever looks at it, `{a, b}`
does **not** parse as a `MapLiteral` (no `:` pairs) — so it cannot simply be
recognized after the fact by inspecting an already-parsed expression the way
task 3's `_assignment` check does. `_brace_statement`
(`cinder/parser.py:338-351`) currently handles a leading `{` at statement
position with exactly two outcomes: speculatively parse a full expression
rooted in a map literal (catching `ParseError`), and if that fails, or if it
succeeds but isn't followed by `;`, fall back to `_block()` — which itself
then fails to parse `a, b} = expr;` as statements (a bare `a` isn't followed
by `;`) and raises `ParseError` uncaught. That means `{a, b} = expr;` is
today dead syntax (always a `ParseError`), so there's no existing behavior to
preserve — but adding this pattern means teaching `_brace_statement` a third
speculative attempt, tried after the map-literal-expression parse fails and
before falling back to `_block()`: reset to `start`, try consuming a flat
identifier pattern shaped like `_destructure_let_statement`'s `is_map=True`
branch (`cinder/parser.py:290-298`, minus the leading `let`/`{` already
consumed by the caller there — here `_brace_statement` itself must consume
the `{`) followed by `TokenType.EQ`; if the identifier-list-then-`=` shape
doesn't match (non-identifier token, or no `=` after the closing `}`), reset
to `start` again and fall through to the existing `_block()` fallback
unchanged. On a match, parse the RHS via `self._assignment()`, consume `;`,
and return `ExprStmt(DestructureAssign(names, rest=None, value=..., line,
column, is_map=True))` — add `is_map: bool = False` to the `DestructureAssign`
dataclass task 3 introduces (`cinder/ast_nodes.py`), mirroring
`DestructureLetStmt`'s own `is_map` flag.

Evaluator: in `_evaluate_destructure_assign` (task 3's new method in
`cinder/interpreter.py`), branch on `expr.is_map` the same way `execute()`
already branches on `stmt.is_map` for `DestructureLetStmt` (lines 268-283) —
but `assign` instead of `define`: validate `value` is a `dict` (else
`CinderRuntimeError` matching `"cannot destructure {type_name} as a map"`),
then for each name in `expr.names`, raise `"destructuring pattern expects
key {name!r}, not found in map"` if absent, else `env.assign(name,
value[name])` — translating a `KeyError` (undefined name) to
`CinderRuntimeError(self._undefined_name_message(name, env), ...)` and a
`_ConstAssignError` to `CinderRuntimeError(f"cannot assign to const
{name!r}", ...)`, exactly like task 3's list-pattern path already does for
its own per-name assign errors. Return the assigned map value (same
"assignment is an expression" behavior task 3 establishes).

Acceptance criteria:
- `let a = 0; let b = 0; {a, b} = {"a": 1, "b": 2}; print(a); print(b);`
  prints `1` then `2`.
- `let a = 0; {a} = {"a": 1, "b": 2};` binds `a` to `1`; the unnamed key
  `"b"` is ignored (matches `let {a} = expr;`'s existing "extra unnamed keys
  ignored" behavior).
- `let a = 0; let b = 0; {a, b} = {"a": 1};` (missing key `"b"`) raises
  `CinderRuntimeError` matching `"destructuring pattern expects key 'b', not
  found in map"`.
- `let a = 0; {a} = [1, 2];` (non-map RHS) raises `CinderRuntimeError`
  matching `"cannot destructure list as a map"`.
- `{undefined_a} = {"undefined_a": 1};` (name never `let`-declared) raises
  `CinderRuntimeError` with the same undefined-name message shape `x = 1;`
  on an undeclared `x` already produces.
- `const a = 1; let b = 2; {a, b} = {"a": 3, "b": 4};` raises
  `CinderRuntimeError` matching `"cannot assign to const 'a'"`.
- `{"a": 1};` (an actual map literal statement), `{1, 2};` (non-identifier
  pattern element), and `{}` (empty braces) all keep parsing exactly as
  before — `ExprStmt(MapLiteral)`, `ParseError`, and empty `Block`
  respectively; this task only adds a new fallback path tried between the
  existing map-literal-expression attempt and the existing block fallback,
  it does not change either of those outcomes.
- Plain `let {a, b} = expr;` declarations are unaffected — this task only
  touches `_brace_statement`, not `_let_statement`/`_destructure_let_statement`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`
(`_brace_statement`), `cinder/interpreter.py`
(`_evaluate_destructure_assign`), `tests/test_parser.py`,
`tests/test_interpreter.py` (grep for `DestructureAssign`/`_brace_statement`
first for exact current locations — line numbers above may have shifted if
earlier tasks this cycle landed first). Once merged, README.md's
destructuring bullet needs this new assignment form documented, and
PROJECT.md's roadmap paragraph needs it moved from backlog to landed — leave
both to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
