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

## 1. Language: ordering comparison operators (`<`/`<=`/`>`/`>=`) for maps [claimed 2026-08-30T15:52:01Z]

Build: `_compare` (`cinder/interpreter.py`, search `def _compare`) already
gives numbers, strings, and — as of PR #349, this project's most recently
merged depth task — lists element-by-element ordering, but maps are the
one comparable-collection type still excluded from the `comparable` check,
even though map *equality* (`==`) already treats two maps with the same
key-value pairs in any order as equal, e.g. `{"a": 1, "b": 2} == {"b": 2,
"a": 1}` is `true` — an ordering rule already has to be consistent with
that existing equality, it just isn't wired up yet. Verify the gap:
```sh
python3 -m cinder.cli eval 'print({"a": 1} < {"a": 2});'
# -> <eval>:1:15: unsupported operand types for comparison: map and map
```

Since Python dicts have no native ordering (unlike lists, which get `<`
for free from Python's own list comparison), this task defines one
explicitly: compare each map's items as a list of `(key, value)` pairs
sorted by key, then compare those two sorted lists the same lexicographic
way list comparison already does — first differing pair wins, and a
shorter list that is a prefix of the other sorts less. This keeps two
`==`-equal maps consistent under the new operators too (their sorted-item
lists are identical, so `<`/`>` are both `false` and `<=`/`>=` are both
`true`, exactly like two equal lists already behave), and it reuses the
same `try`/`except TypeError` pattern `_compare` already has for lists so
a key-type or value-type mismatch raises a clean `CinderRuntimeError`
instead of a raw Python error.

Edit `_compare` (`cinder/interpreter.py`, search `def _compare`):
```python
def _compare(self, operator: Token, left, right, op: TokenType) -> bool:
    comparable = (
        (_is_number(left) and _is_number(right))
        or (isinstance(left, str) and isinstance(right, str))
        or (isinstance(left, list) and isinstance(right, list))
        or (isinstance(left, dict) and isinstance(right, dict))
    )
    if not comparable:
        raise CinderRuntimeError(
            f"unsupported operand types for comparison: "
            f"{type_name(left)} and {type_name(right)}",
            operator.line,
            operator.column,
        )
    is_map_compare = isinstance(left, dict) and isinstance(right, dict)
    try:
        if is_map_compare:
            left = sorted(left.items())
            right = sorted(right.items())
        if op == TokenType.LT:
            return left < right
        if op == TokenType.LTEQ:
            return left <= right
        if op == TokenType.GT:
            return left > right
        return left >= right
    except TypeError:
        message = (
            "unsupported operand types for comparison: map keys or values "
            "are not comparable"
            if is_map_compare
            else "unsupported operand types for comparison: list elements "
            "are not comparable"
        )
        raise CinderRuntimeError(message, operator.line, operator.column) from None
```
`is_map_compare` is captured *before* `left`/`right` get reassigned to
their sorted-items form, so the `except` branch can still tell which of
the two pre-existing messages applies.

**Scope note** (call this out in the PR body): this only makes *direct*
map-vs-map comparison work — a map nested inside a list
(`[{"a": 1}] < [{"a": 2}]`) still raises, because list comparison
delegates to Python's own native list `<`, which tries `dict < dict`
directly on the nested elements rather than routing back through this
method. Making nested comparability recursive is a bigger, separate
change and is out of scope here; lock in the current raise with a
regression test instead of treating it as an accidental gap.

Acceptance criteria:
- `{"a": 1} < {"a": 2};` is `true` — same key, lesser value.
- `{"a": 1} < {"b": 0};` is `true` — keys differ first (`"a" < "b"`), so
  this holds regardless of values.
- `{"a": 1, "b": 2} < {"a": 2};` is `true` — the first differing sorted
  pair is `("a", 1)` vs `("a", 2)`, decided before list length matters.
- `{} < {"a": 1};` is `true` — an empty map is a prefix of any
  non-empty one, mirroring `[] < [1]`.
- `{"a": 1, "b": 2} <= {"b": 2, "a": 1};` and
  `{"a": 1, "b": 2} >= {"b": 2, "a": 1};` are both `true`, and
  `{"a": 1, "b": 2} < {"b": 2, "a": 1};` is `false` — two maps that are
  `==` (same pairs, different insertion order) are never strictly less
  than or greater than each other.
- `{"a": 1} < {"a": "x"};` raises `CinderRuntimeError` matching
  `"unsupported operand types for comparison: map keys or values are not
  comparable"` — same key, incomparable value types.
- `{1: "a"} < {"b": 2};` raises `CinderRuntimeError` with the same
  message — incomparable key types.
- `{"a": 1} < [1];` and `{"a": 1} < 1;` still raise `CinderRuntimeError`
  matching `"unsupported operand types for comparison: map and list"` /
  `"... map and int"` — maps only compare against maps.
- `[{"a": 1}] < [{"a": 2}];` still raises `CinderRuntimeError` (see the
  scope note above — not fixed by this task).
- Chained comparisons compose for free:
  `{"a": 1} < {"a": 2} < {"a": 3};` is `true` (via
  `_evaluate_chained_comparison`, which already calls `_compare` per
  adjacent pair — no changes needed there).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_compare`, search `def
_compare`), `tests/test_interpreter.py` (extend `class TestComparisons`,
search that name, alongside the existing `test_list_ordering_*` cases,
for the map equivalents above). Once merged, `README.md`'s Operators
bullet needs a map-ordering mention next to the list-ordering one added
for PR #349, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_pandigital` — 0-to-9 pandigital number test

Build: `is_disarium` and `is_armstrong` (`cinder/builtins.py`, search `def
_is_disarium`) already test digit-position properties, and `is_undulating`/
`is_repdigit` already test digit-*pattern* properties, but nothing checks
whether a number's digits are a full house of exactly the ten decimal
digits — a classic property (the "0 to 9 pandigital numbers", smallest
`1023456789`, largest `9876543210`) that neither existing digit-set
predicate (`is_repdigit`: all digits the same; `is_unique` operates on
lists, not a number's own digits) answers. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_pandigital(1023456789));'
# -> <eval>:1:7: undefined name 'is_pandigital' (did you mean 'is_digit'?)
```

This task scopes the predicate to the single unambiguous "0 to 9"
definition — a number is pandigital iff its decimal digits are exactly
the multiset `{0,1,2,...,9}`, each appearing once, which forces exactly
10 digits. (The "1 to 9" zeroless variant, and "at least once" variants
with more than 10 digits, are different, looser definitions some sources
also call "pandigital" — deliberately not implemented here to avoid one
name meaning three different things; a future task can add a differently
named builtin for those if ever wanted.)

Add to `cinder/builtins.py`, directly after `_is_disarium` (search `def
_is_disarium`, immediately before `def _is_strong_number`) — keeps it
grouped with the other single-argument digit predicates:
```python
def _is_pandigital(arguments: list, line: int, column: int) -> object:
    _require_arity("is_pandigital", arguments, 1, line, column)
    value = _require_int("is_pandigital", arguments[0], line, column)
    if value < 0:
        return False
    digits = str(value)
    return len(digits) == 10 and set(digits) == set("0123456789")
```
Also register the new dict entry (search `"is_disarium": _is_disarium,`,
add `"is_pandigital": _is_pandigital,` directly after it, before
`"is_strong_number": _is_strong_number,`).

Acceptance criteria:
- `is_pandigital(1023456789);` and `is_pandigital(9876543210);` are both
  `true` — the smallest and largest 0-to-9 pandigital numbers.
- `is_pandigital(5670231849);` is `true` — an arbitrary permutation of
  the ten digits, not just the sorted extremes.
- `is_pandigital(123456789);` is `false` — only 9 digits, missing `0`.
- `is_pandigital(1023456788);` is `false` — 10 digits, but `8` repeats
  and `9` is missing (right length, wrong digit set).
- `is_pandigital(10234567890);` is `false` — 11 digits, `0` repeats.
- `is_pandigital(0);`, `is_pandigital(5);` are `false` — far too short.
- `is_pandigital(-1023456789);` is `false` — negative numbers are
  excluded (mirrors every other `is_*` digit predicate's own convention,
  e.g. `is_disarium`/`is_armstrong`).
- `is_pandigital(1.5);` raises `CinderRuntimeError` matching
  `"is_pandigital() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_disarium`, search
`def _is_disarium`), `tests/test_builtins.py` (new `class
TestIsPandigital`, modeled directly on `class TestIsDisarium`, search
that name, for the true/false/length/domain/type-error test shapes
above). Once merged, `README.md`'s Builtins bullet needs `is_pandigital`
added near `is_disarium`, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 3. Language: difference operator (`-`) for maps

Build: `_apply_binary_operator`'s `PLUS` branch (`cinder/interpreter.py`,
search `if op == TokenType.PLUS:`) already special-cases `dict`/`dict` as
a merge (right-biased on key collision, `{"a": 1} + {"a": 2}` is
`{"a": 2}`), giving the existing `merge()` builtin an infix spelling —
but `MINUS` has no equivalent: it routes straight to `_numeric_op`, which
only knows numbers and rejects everything else, so there is no infix
counterpart to `merge()`'s inverse even though one reads naturally by
direct analogy to `+`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print({"a": 1, "b": 2} - {"a": 1});'
# -> <eval>:1:26: unsupported operand types for '-': map and map
```

This task defines map `-` as key-based removal: a fresh map containing
every pair from the left operand whose key is *not* present in the right
operand (the right operand's own values are irrelevant — only its keys
matter, mirroring `dict.keys() - dict.keys()` set-difference semantics,
not any kind of value subtraction). This is deliberately scoped to
`map`/`map` only, not `list`/`list` — list difference (multiset removal?
set removal? what about duplicates and order?) is a genuinely separate
design question, not a natural extension of the same idea, so bundling
it in would double this task's scope for a feature nobody asked for;
leave list `-` to a future task if one gets proposed, the same way the
`while`-`else` task already in this backlog scoped itself to plain
`while` only.

Edit `_apply_binary_operator` (`cinder/interpreter.py`, search `if op ==
TokenType.MINUS:`):
```python
if op == TokenType.MINUS:
    if isinstance(left, dict) and isinstance(right, dict):
        return {key: value for key, value in left.items() if key not in right}
    return self._numeric_op(operator, left, right, lambda a, b: a - b)
```
A mismatched type (map minus a non-map, or a non-map minus a map) falls
through to `_numeric_op`, which already raises `CinderRuntimeError` with
the standard `"unsupported operand types for '-': ..."` message — no
separate error-handling code is needed here, unlike `PLUS`'s own branch,
which raises explicitly because `_numeric_op` isn't in its fallthrough
path.

Acceptance criteria:
- `{"a": 1, "b": 2} - {"a": 1};` is `{"b": 2}` — key-based removal, the
  removed key's own value on either side is irrelevant.
- `{"a": 1, "b": 2} - {"a": 99};` is `{"b": 2}` — same as above,
  confirming the right operand's *value* is ignored, only its key
  matters.
- `{"a": 1} - {};` is `{"a": 1}` — subtracting an empty map is a no-op.
- `{} - {"a": 1};` is `{}` — nothing to remove from.
- `{"a": 1, "b": 2} - {"a": 1, "b": 2};` is `{}` — removing every key
  empties the map.
- `{"a": 1, "b": 2} - {"c": 3};` is `{"a": 1, "b": 2}` — a key not
  present in the left map has no effect.
- Does not mutate either input:
  `let a = {"a": 1, "b": 2}; let c = a - {"a": 1}; print(a);` still
  prints `{"a": 1, "b": 2}` (mirrors
  `TestMapConcatenation.test_does_not_mutate_inputs`).
- Left-associative and composes with `+`:
  `{"a": 1, "b": 2, "c": 3} - {"a": 1} - {"b": 2};` is `{"c": 3}`.
- Compound assignment works for free through the existing desugaring, on
  all three assignment target kinds (mirroring `TestMapConcatenation`'s
  own three compound-assignment tests for `+=`):
  `let m = {"a": 1, "b": 2}; m -= {"a": 1};` leaves `m` as `{"b": 2}`;
  `let xs = [{"a": 1, "b": 2}]; xs[0] -= {"a": 1};` leaves `xs` as
  `[{"b": 2}]`; `let obj = {"m": {"a": 1, "b": 2}}; obj.m -= {"a": 1};`
  leaves `obj` as `{"m": {"b": 2}}`.
- `{"a": 1} - [1, 2];` raises `CinderRuntimeError` matching
  `"unsupported operand types for '-': map and list"`.
- `{"a": 1} - "x";` raises `CinderRuntimeError` matching
  `"unsupported operand types for '-': map and string"`.
- `[1, 2] - {"a": 1};` raises `CinderRuntimeError` matching
  `"unsupported operand types for '-': list and map"` — the reverse
  order still raises too (list `-` map is not defined either, only map
  `-` map).
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`MINUS` branch, search `if op == TokenType.MINUS:`),
`tests/test_interpreter.py` (new `class TestMapDifference`, modeled
directly on `class TestMapConcatenation`, search that name, for the
compound-assignment/non-mutation/mismatched-type test shapes). Once
merged, `README.md`'s Operators bullet needs a map-`-` mention next to
the map-`+`/list-`+` ones already there, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Standard library: `transpose` — matrix (list-of-lists) transpose

Build: `unzip` (`cinder/builtins.py`, search `def _unzip`) already
transposes the special two-column case (a list of 2-element lists) into
a 2-element list of columns, and `zip`/`zip_longest` go the other
direction for exactly two lists, but nothing generalizes either to an
arbitrary number of columns — a list of same-length rows (a "matrix")
has no way to swap rows and columns in one call. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(transpose([[1,2],[3,4]]));'
# -> <eval>:1:7: undefined name 'transpose'
```

Add to `cinder/builtins.py`, directly after `_unzip` (search `def
_unzip`, immediately before `def _zip_with`) — keeps it grouped with the
other zip-family collection functions:
```python
def _transpose(arguments: list, line: int, column: int) -> object:
    _require_arity("transpose", arguments, 1, line, column)
    matrix = arguments[0]
    if not isinstance(matrix, list):
        raise CinderRuntimeError(
            f"transpose() requires a list, got {type_name(matrix)}",
            line, column,
        )
    if not matrix:
        return []
    width = None
    for i, row in enumerate(matrix):
        if not isinstance(row, list):
            raise CinderRuntimeError(
                f"transpose() requires a list of lists, got "
                f"{type_name(row)} at index {i}",
                line, column,
            )
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise CinderRuntimeError(
                f"transpose() requires all rows to have the same length, "
                f"got length {len(row)} at index {i}, expected {width}",
                line, column,
            )
    return [[row[i] for row in matrix] for i in range(width)]
```
An empty outer list returns `[]` before the row-length check ever runs
(there is no width to derive from zero rows). A non-empty list of empty
rows (`width == 0`) falls through to `range(0)`, correctly returning `[]`
too (a matrix with rows but no columns transposes to no rows). Also
register the new dict entry (search `"unzip": _unzip,`, add
`"transpose": _transpose,` directly after it, before `"zip_with":
_zip_with,`).

Acceptance criteria:
- `transpose([[1, 2], [3, 4], [5, 6]]);` is `[[1, 3, 5], [2, 4, 6]]` —
  3 rows of 2 columns becomes 2 rows of 3 columns.
- `transpose([[1, 2, 3]]);` is `[[1], [2], [3]]` — a single row becomes
  one column per element.
- `transpose([]);` is `[]` — an empty matrix transposes to itself.
- `transpose([[], [], []]);` is `[]` — rows with no columns transpose to
  no rows.
- `transpose(transpose([[1, 2], [3, 4], [5, 6]]));` is
  `[[1, 2], [3, 4], [5, 6]]` — round-trips back to the original for any
  rectangular matrix (mirrors `TestUnzip.test_unzip_round_trips_with_zip`).
- Does not mutate the input: `let m = [[1, 2], [3, 4]]; transpose(m);
  print(m);` still prints `[[1, 2], [3, 4]]`.
- `transpose(5);` raises `CinderRuntimeError` matching `"transpose()
  requires a list, got int"`.
- `transpose([1, 2]);` raises `CinderRuntimeError` matching `"transpose()
  requires a list of lists, got int at index 0"` — an element that isn't
  itself a list.
- `transpose([[1, 2], [3, 4, 5]]);` raises `CinderRuntimeError` matching
  `"transpose() requires all rows to have the same length, got length 3
  at index 1, expected 2"` — a ragged matrix.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_unzip`, search `def
_unzip`), `tests/test_builtins.py` (new `class TestTranspose`, modeled
directly on `class TestUnzip`, search that name, for the
rectangular/single-row/empty/round-trip/mutation/ragged/type-error test
shapes above). Once merged, `README.md`'s Builtins bullet needs
`transpose` added near `unzip`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs refreshing
— leave both to the Architect's next grooming pass, not this task.

---

## 5. Language: `else` clause on `for`-in loops (Python-style loop-`else`)

Build: PR #352 already added an `else { ... }` clause to plain `while`
loops — it runs exactly once, when the loop exits normally (condition
became false, or, for `for`, the iterable ran out) *without* an
intervening `break`, mirroring Python's `while`/`for`-`else` — but that
task explicitly scoped itself to `while` only, leaving the foreach
`for NAME in EXPR { ... }` form (`cinder/ast_nodes.py`'s `ForStmt`) and
the C-style `for (init; cond; step) { ... }` form (`ForCStmt`) both
still without one. This task closes the gap for the foreach form only.
Verify the gap:
```sh
python3 -m cinder.cli eval 'for x in [1, 2, 3] { print(x); } else { print("done"); }'
# -> <eval>:1:34: expected end of statement, found 'else'
```

Semantics mirror `WhileStmt.else_branch` exactly (see its docstring,
`cinder/ast_nodes.py`, search `class WhileStmt`): the `else` block runs
once control falls out of the loop with no intervening `break` —
including immediately, for an empty or already-exhausted iterable, the
`for`-loop equivalent of `while (false) { } else { ... }` running its
else on zero iterations. `continue` does not skip it; an uncaught
exception, `return`, or a propagating labeled `break`/`continue` from
the body does, since control never reaches the check in that case. This
task is scoped to the foreach `for`-in form only — not `ForCStmt` (the
C-style three-clause form) and not `DoWhileStmt` — the same
one-loop-kind-at-a-time scoping `while`-`else` itself used; either of
those is a separate, future task if ever proposed.

Unlike `while`-`else`, there is no dangling-`if`/`else`-attachment
concern to handle here: `_while_statement` parses its body via the
generic `_statement()` (so an unbraced single-statement body like
`while (false) x = 1;` is legal, creating the ambiguity PR #352 had to
resolve), but `_for_statement` already requires a brace-delimited
`_block()` body unconditionally (see the `if not self._check(
TokenType.LBRACE):` guard right before `body = self._block()`) — a
trailing `else` after a `for`'s `{ ... }` body is unambiguous, since a
`for` can never appear as an `if`'s unbraced then-branch and swallow
the `if`'s own `else` the way an unbraced `while` could.

Edit three files:

1. `cinder/ast_nodes.py` (search `class ForStmt`), add one field at the
   end, after `is_map: bool = False`:
```python
    else_branch: "Stmt | None" = None
```

2. `cinder/parser.py`'s `_for_statement` (search `def _for_statement`):
   right after `body = self._block()` / `self._loop_labels.pop()` and
   before the `return ForStmt(` — insert the same else-clause parse
   `_while_statement` already has, then thread it into the constructor
   call:
```python
        body = self._block()
        self._loop_labels.pop()
        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            else_branch = self._statement()
        return ForStmt(
            var_name,
            iterable,
            body,
            for_token.line,
            for_token.column,
            label,
            names=names,
            rest=rest,
            is_map=is_map,
            else_branch=else_branch,
        )
```

3. `cinder/interpreter.py`'s `_execute_for` (search `def _execute_for`):
   track a `broke` flag through the existing iteration loop exactly the
   way `WhileStmt`'s handling already does, then check it after the
   `for item in items:` loop ends:
```python
    def _execute_for(self, stmt: ForStmt, env: Environment) -> None:
        iterable = self.evaluate(stmt.iterable, env)
        if isinstance(iterable, dict):
            items = list(iterable.keys())
        elif isinstance(iterable, (list, str)):
            items = list(iterable)
        else:
            raise CinderRuntimeError(
                f"'for'-in loop requires a list, string, or map, got {type_name(iterable)}",
                stmt.line,
                stmt.column,
            )
        broke = False
        for item in items:
            iter_env = Environment(env)
            if stmt.names is not None:
                if stmt.is_map:
                    self._bind_map_destructure(iter_env, stmt.names, stmt.rest, item, stmt.line, stmt.column)
                else:
                    self._bind_list_destructure(iter_env, stmt.names, stmt.rest, item, stmt.line, stmt.column)
            else:
                iter_env.define(stmt.var_name, item)
            try:
                self.execute(stmt.body, iter_env)
            except _BreakSignal as signal:
                if signal.label is not None and signal.label != stmt.label:
                    raise
                broke = True
                break
            except _ContinueSignal as signal:
                if signal.label is not None and signal.label != stmt.label:
                    raise
                continue
        if not broke and stmt.else_branch is not None:
            self.execute(stmt.else_branch, env)
```
(Only the `broke = False` init, the `broke = True` before the `break`
in the `_BreakSignal` handler, and the final `if not broke and
stmt.else_branch is not None:` block are new — everything else is
unchanged, shown in full only so the exact insertion points are
unambiguous.)

Acceptance criteria (mirror `TestWhileElse` in `tests/test_interpreter.py`,
search that name, one-for-one):
- `for x in [1, 2, 3] { } else { done = true; }` runs the `else` — the
  loop completes normally (iterable exhausted, no `break`).
- `for x in [] { } else { done = true; }` also runs the `else` — zero
  iterations still counts as "exited without a `break`", exactly like
  `while (false) { } else { ... }`.
- `for x in [1, 2, 3] { if (x == 2) { break; } } else { ran = true; }`
  does **not** run the `else` — an intervening `break` skips it.
- `for x in [1, 2, 3] { if (x == 1) { continue; } } else { ran = true; }`
  still runs the `else` — `continue` does not skip it, only `break`
  does.
- `outer: for x in [1] { for y in [1] { break outer; } } else { ran =
  true; }` does **not** run the outer `for`'s `else` — a labeled
  `break` targeting the outer loop skips its `else` exactly like
  `while`'s own labeled-break case.
- `fn f() { for x in [1] { return 1; } else { return 2; } } f();`
  returns `1`, not `2` — `return` from the body skips the `else`
  (control never reaches the post-loop check).
- The `else` clause also runs for a `for`-in loop over a string
  (`for c in "" { } else { done = true; }`) and a map
  (`for k in {} { } else { done = true; }`), and with a
  list-destructuring (`for [a, b] in [] { } else { ... }`) or
  map-destructuring (`for {a} in [] { } else { ... }`) loop variable —
  all share the same `ForStmt`/`_execute_for` path, so one test per
  shape is enough to confirm the `else` wiring doesn't only work for
  the plain-identifier/list case.
- `for x in [1, 2, 3] { }` (no `else` at all) still behaves exactly as
  before — a regression guard mirroring
  `test_while_without_else_still_behaves_as_before`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`ForStmt`, search `class ForStmt`),
`cinder/parser.py` (`_for_statement`, search `def _for_statement`),
`cinder/interpreter.py` (`_execute_for`, search `def _execute_for`),
`tests/test_parser.py` (new `class TestForElse`, modeled on
`class TestWhileElse`, search that name, for the parse-shape
assertions), `tests/test_interpreter.py` (new `class TestForElse`,
modeled on the `test_while_else_*` methods inside `TestWhileStatement`,
search `test_while_else_runs_on_normal_completion`, for the runtime
behavior above). Once merged, `README.md`'s Control flow bullet needs a
`for`-`else` mention next to the existing `while`-`else` one, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" section needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 6. Standard library: `is_vampire_number` — digit-permutation factor pairs

Build: `is_smith_number` (`cinder/builtins.py`, search `def
_is_smith_number`) already asks a digit-vs-factors question (does the
number's own digit sum match its prime factors' combined digit sum),
and `is_kaprekar`/`nth_kaprekar` already split a number's *square* and
recombine the halves by addition — but nothing checks the classic
"vampire number" property: a number whose decimal digits can be
rearranged into two equal-length factors ("fangs") that multiply back
to it. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_vampire_number(1260));'
# -> <eval>:1:7: undefined name 'is_vampire_number'
```

This task scopes the predicate to the standard definition (the one
used by every reference list of vampire numbers, e.g. OEIS A014575):
a number `n` with an even number `2k` of decimal digits (`k >= 2`, so
the smallest possible case is 4 digits — no known 2-digit case exists
under this definition, so it is out of scope rather than special-cased)
qualifies if there exist two factors `a * b == n`, each with exactly
`k` digits (no leading zero, so each fang is at least `10^(k-1)`), such
that the combined multiset of `a`'s and `b`'s digits equals `n`'s own
digit multiset, **and** `a` and `b` are not *both* multiples of 10 (the
standard exclusion that rules out "trivial" fangs like `10 * 10 = 100`
padding zeros onto an otherwise-ordinary factorization — one fang
ending in `0` is fine, e.g. `1260 = 21 * 60`, only *both* ending in `0`
is excluded). Odd digit counts and numbers under 4 digits are `false`
outright — there is no way to split them into two equal-length fangs.

Add to `cinder/builtins.py`, directly after `_is_smith_number` (search
`def _is_smith_number`, immediately before `def _num_divisors`) —
keeps it grouped with the other digit-vs-factorization predicates:
```python
def _is_vampire_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_vampire_number", arguments, 1, line, column)
    value = _require_int("is_vampire_number", arguments[0], line, column)
    if value < 0:
        return False
    digits = str(value)
    digit_count = len(digits)
    if digit_count % 2 != 0 or digit_count < 4:
        return False
    half = digit_count // 2
    lower = 10 ** (half - 1)
    upper = 10 ** half
    target = sorted(digits)
    for fang_a in range(lower, upper):
        if value % fang_a != 0:
            continue
        fang_b = value // fang_a
        if fang_b < lower or fang_b >= upper:
            continue
        if fang_a % 10 == 0 and fang_b % 10 == 0:
            continue
        if sorted(str(fang_a) + str(fang_b)) == target:
            return True
    return False
```
Also register the new dict entry (search `"is_smith_number":
_is_smith_number,`, add `"is_vampire_number": _is_vampire_number,`
directly after it, before `"num_divisors": _num_divisors,`).

Acceptance criteria:
- `is_vampire_number(1260);` is `true` — `1260 = 21 * 60`, digits
  `{1,2,6,0}` match `{2,1}` + `{6,0}`.
- `is_vampire_number(1395);` is `true` — `1395 = 15 * 93`.
- `is_vampire_number(1530);` is `true` — `1530 = 30 * 51`, one fang
  (`30`) ends in `0` but not both, so it still counts.
- `is_vampire_number(6880);` is `true` — `6880 = 80 * 86`, a 4-digit
  case with a different digit multiset than the examples above.
- `is_vampire_number(125460);` is `true` — a 6-digit case,
  `125460 = 204 * 615`, confirming the check isn't hardcoded to 4
  digits.
- `is_vampire_number(1234);` is `false` — a 4-digit number with no
  valid fang pair.
- `is_vampire_number(100);` is `false` — `100 = 10 * 10`, the classic
  *excluded* trivial case: both fangs end in `0`.
- `is_vampire_number(123);` and `is_vampire_number(12345);` are both
  `false` — odd digit counts can never split into two equal-length
  fangs.
- `is_vampire_number(21);`, `is_vampire_number(0);` are `false` — fewer
  than 4 digits, too short to have two 2-digit-or-larger fangs.
- `is_vampire_number(-1260);` is `false` — negative numbers are
  excluded (mirrors every other `is_*` digit predicate's own
  convention, e.g. `is_smith_number`/`is_disarium`).
- `is_vampire_number(1.5);` raises `CinderRuntimeError` matching
  `"is_vampire_number() requires an int, got float"` (via
  `_require_int`'s existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_smith_number`,
search `def _is_smith_number`), `tests/test_builtins.py` (new `class
TestIsVampireNumber`, modeled directly on `class TestIsSmithNumber`,
search that name, for the true/false/length/domain/type-error test
shapes above). Once merged, `README.md`'s Builtins bullet needs
`is_vampire_number` added near `is_smith_number`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

### Language: guards in `match` arms (`n if n > 0 => "positive"`) — PR #314, closed 2026-08-25

Bounced 3x with `VERDICT: CHANGES REQUESTED`, all the same recurring bug:
each fix round patched `_bracket_depth` tracking (used to scope the
bare-arrow/guard `=>` ambiguity fix) for one nested construct — call/list/map
arguments (round 1), `match` expressions (round 2), `fn` expressions (round
3) — while the reviewer kept finding another construct the fix hadn't
threaded depth through, and round 3's review flagged a 4th possible gap
(`_arrow_body`'s bare-expression branch, `_block()`) that was never
confirmed either way. Next attempt should enumerate *every* production that
opens a paren/bracket/brace scope up front (grep `_bracket_depth` usages in
the closed PR's final diff for the list-so-far) rather than fixing gaps
reactively one review round at a time — or consider a structurally
different fix that doesn't need per-construct threading at all (e.g.
resolving the bare-arrow/guard ambiguity by lookahead at the `=>` site
instead of a suppression-depth counter).
