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

## 1. Language: destructuring assignment — `[a, b] = expr;`

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

## 2. Standard library: `is_disjoint` — no-common-elements predicate for lists

Build: add `is_disjoint(list1, list2)` to `cinder/builtins.py`.
`union`/`intersection`/`difference`/`symmetric_difference`/`is_subset`/
`is_superset` (`cinder/builtins.py:1613-1661` roughly, see current line
numbers) already treat lists as unordered sets, but there is still no
direct way to ask "do these two lists share *any* element at all" without
computing `intersection(a, b)` and checking the result is empty by hand.
This is the one predicate that set-ops family still leaves implicit —
group it right after `is_superset` (task 1, if merged first) or right
after `symmetric_difference` otherwise.

Model directly on `_is_subset`'s structure (from task 1, or `_difference`'s
at `cinder/builtins.py:1636-1640` if task 1 hasn't merged yet): reuse
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
`is_superset` if task 1 already landed, else near `symmetric_difference`
— see current line numbers, shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_disjoint` added near `union`/`intersection`/`difference`/
`symmetric_difference`/`is_subset`/`is_superset` — leave that to the
Architect's next grooming pass, not this task.

---

## 3. Language: map-pattern destructuring assignment — `{a, b} = expr;`

Build: extend map-pattern destructuring to plain assignment, the map-shaped
counterpart to task 2's list-pattern assignment. Today `let {a, b} = expr;`
binds fresh names via `DestructureLetStmt(is_map=True)` — handled inline in
`Interpreter.execute()` (`cinder/interpreter.py:266-283`: checks `isinstance(value,
dict)`, then for each name raises `"cannot destructure {type_name} as a map"` or
`"destructuring pattern expects key {name!r}, not found in map"` before
`env.define(name, value[name])`) — but there is no way to destructure into
*already-declared* bindings the way task 2 adds for list patterns. Depends on
task 2 landing first (reuses the `DestructureAssign` AST node it introduces);
do not start this before task 2 merges.

Scope: **flat map patterns only** — bare identifiers naming keys to pull out,
exactly like `let {a, b} = expr;` today (no renaming, no nesting, no rest
element — none of those exist for `let`'s map form either, so don't add them
here).

The hard part is grammar, not evaluation. Unlike `[a, b]`, which already
parses as an ordinary `ListLiteral` before task 2 ever looks at it, `{a, b}`
does **not** parse as a `MapLiteral` (no `:` pairs) — so it cannot simply be
recognized after the fact by inspecting an already-parsed expression the way
task 2's `_assignment` check does. `_brace_statement`
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
dataclass task 2 introduces (`cinder/ast_nodes.py`), mirroring
`DestructureLetStmt`'s own `is_map` flag.

Evaluator: in `_evaluate_destructure_assign` (task 2's new method in
`cinder/interpreter.py`), branch on `expr.is_map` the same way `execute()`
already branches on `stmt.is_map` for `DestructureLetStmt` (lines 268-283) —
but `assign` instead of `define`: validate `value` is a `dict` (else
`CinderRuntimeError` matching `"cannot destructure {type_name} as a map"`),
then for each name in `expr.names`, raise `"destructuring pattern expects
key {name!r}, not found in map"` if absent, else `env.assign(name,
value[name])` — translating a `KeyError` (undefined name) to
`CinderRuntimeError(self._undefined_name_message(name, env), ...)` and a
`_ConstAssignError` to `CinderRuntimeError(f"cannot assign to const
{name!r}", ...)`, exactly like task 2's list-pattern path already does for
its own per-name assign errors. Return the assigned map value (same
"assignment is an expression" behavior task 2 establishes).

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

## 4. Standard library: `is_anagram` — two-string character-multiset predicate

Build: add `is_anagram(string1, string2)` to `cinder/builtins.py`. It's the
two-string sibling to `_is_palindrome`'s (`cinder/builtins.py:620-627`)
single-string "reads the same both ways" check: two strings are anagrams
of each other when they contain exactly the same characters the same
number of times, regardless of order. Group it right after
`is_palindrome`, ahead of `is_upper` — keeping the string-content-predicate
family contiguous the same way `is_positive`/`is_negative`/`is_zero` sit
together next to `sign`.

Model the arity/type-checking on `_is_palindrome`'s structure, but for two
arguments: reuse `_require_arity("is_anagram", arguments, 2, line, column)`,
then check each of `arguments[0]`/`arguments[1]` is a `str`, raising
`CinderRuntimeError` naming `is_anagram` and which position (first/second)
failed on a non-string argument — mirror `_require_two_lists`'s two-argument
error-naming pattern (`cinder/builtins.py`, used by `union`/`intersection`/
etc.) rather than inventing new wording. For the comparison itself, use
`collections.Counter` (`from collections import Counter` at the top of
`builtins.py` if not already imported — check first) rather than a
hand-rolled sort-and-compare or dict-tally: `Counter(string1) ==
Counter(string2)`. Case-sensitive, no normalization — the same
minimal-behavior spirit `is_palindrome`/`chars`/`swap_case` already follow
(don't strip whitespace or ignore case unless a caller does that
explicitly first, e.g. `is_anagram(lower(a), lower(b))`).

Acceptance criteria:
- `is_anagram("listen", "silent");` is `true`.
- `is_anagram("hello", "world");` is `false`.
- `is_anagram("", "");` is `true` — two empty strings share an (empty)
  multiset of characters.
- `is_anagram("a", "");` is `false` — different lengths can never be
  anagrams (falls out of the `Counter` comparison naturally, no separate
  length check needed).
- `is_anagram("aabb", "abab");` is `true` — order doesn't matter, only
  per-character counts.
- `is_anagram("Listen", "Silent");` is `false` — case-sensitive, `L` and
  `l` are different characters.
- `is_anagram("dormitory", "dirty room");` is `false` — no whitespace
  stripping; the space in `"dirty room"` has no counterpart in
  `"dormitory"`.
- `is_anagram(5, "abc");` / `is_anagram("abc", 5);` (non-string argument,
  either position) raises `CinderRuntimeError` naming `is_anagram` and
  which position (first/second) failed.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_palindrome`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet needs
`is_anagram` added near `is_palindrome`, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 5. Standard library: `is_permutation` — two-list character/element-multiset predicate

Build: add `is_permutation(list1, list2)` to `cinder/builtins.py`. It's
task 4's `is_anagram` generalized from strings to lists: two lists are
permutations of each other when they contain exactly the same elements
the same number of times, regardless of order — the list-oriented sibling
`is_anagram` deliberately doesn't cover (its `Counter`-based approach
needs hashable characters; list elements can be lists/maps, which aren't
hashable). Register right after `is_anagram` (task 4, if merged first) or
right after `is_subset`/`is_superset`/`is_disjoint` otherwise (see current
line numbers, shift if earlier tasks this cycle landed first) — grouping
it with whichever multiset-shaped predicate family lands nearest it.

Model the arity/type-checking on `_is_subset`'s structure
(`cinder/builtins.py:1683-1685`): reuse
`_require_two_lists("is_permutation", arguments, line, column)` for
arity-2 + list-type validation on both arguments (same "requires a list
as its first/second argument, got {type_name}" errors, no new message
shape). For the comparison itself, do **not** use `collections.Counter`
or a `set`/`dict` keyed on the elements directly — unlike `is_anagram`'s
characters, list elements can be unhashable (nested lists/maps), the same
reason `_dedupe` (`cinder/builtins.py:1605-1622`) falls back to an
O(n²) `values_equal` scan when `not all(_is_valid_key(element) for
element in value)`. Take the same approach here, unconditionally (no
need to special-case the hashable case for a predicate — simplicity over
micro-optimization): different lengths short-circuit to `false` (`len(list1)
!= len(list2)`); otherwise copy `list2` into a working list, and for each
element of `list1` find the first remaining element it's `values_equal`
to and remove that one match (not all matches — this is multiset
removal, not filtering); if any element of `list1` has no remaining match,
return `false` immediately; if the loop completes, return `true` (the
length check up front guarantees the working list is exactly emptied,
no need to check it explicitly).

Acceptance criteria:
- `is_permutation([1, 2, 3], [3, 2, 1]);` is `true` — same elements,
  different order.
- `is_permutation([1, 2, 2], [1, 1, 2]);` is `false` — same elements by
  set membership, but different per-element counts (two `2`s vs one).
- `is_permutation([], []);` is `true` — two empty lists share an (empty)
  multiset.
- `is_permutation([1], [1, 2]);` is `false` — different lengths can
  never be permutations (short-circuit, no need to scan).
- `is_permutation([[1, 2]], [[1, 2]]);` is `true` — matching uses deep
  equality (`values_equal`), not reference identity or hashing, so a
  structurally-equal nested list still counts as a match.
- `is_permutation([1, "1"], ["1", 1]);` is `true` — `1` and `"1"` are
  distinct elements under `values_equal`, but each side has exactly one
  of each, matched correctly regardless of order.
- `is_permutation(5, [1, 2]);` / `is_permutation([1, 2], 5);`
  (non-list argument, either position) raises `CinderRuntimeError`
  naming `is_permutation` and which position (first/second) failed.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_permutation` added near
`is_anagram`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass, not
this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
