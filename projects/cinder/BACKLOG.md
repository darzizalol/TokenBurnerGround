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

## 1. Language: slice assignment for lists (`list[start:end] = other_list;`) [claimed 2026-08-13T14:07:01Z]

Build: the depth task after task 1's breadth work (`is_automorphic`) per
`PROJECT.md`'s breadth-vs-depth policy. `README.md`'s Data structures
bullet already flags the gap explicitly: slicing
(`list[start:end]`/`string[start:end]`, with an optional third `:step`)
is documented as "not assignable" today. Verify that's still true:
`python3 -m cinder.cli eval 'let xs = [1, 2, 3]; xs[0:1] = [9]; print(xs);'`
raises `ParseError` `"invalid assignment target"` — `_assignment()` in
`cinder/parser.py` (search for `def _assignment`) only recognizes
`Identifier`, `Index`, and `ListLiteral` (for plain-assignment
destructuring) on the left of `=`; a `SliceExpr` (the node
`self._ternary()` already produces for `xs[0:1]`, search for `class
SliceExpr` in `cinder/ast_nodes.py`) falls through to the final `raise
ParseError("invalid assignment target", ...)`.

Scope this to the step-less form only — `list[start:end] = value;` — and
reject a stepped slice target (`list[a:b:c] = value;`) as a parse error,
explicitly deferring extended-slice assignment (which in Python requires
the replacement to match the target's length exactly, a materially
different and more error-prone contract than the simple form) to a
future task. String targets stay immutable — `s[0:1] = "x";` must raise
the same `"strings are immutable and do not support item assignment"`
error plain single-index assignment on a string already raises (search
for that exact message in `cinder/interpreter.py`'s `_index_set`), not a
new/different message.

In `cinder/ast_nodes.py`: add a new frozen dataclass `SliceAssign` right
after `SliceExpr` (search for `class SliceExpr`, just before `Ternary`):
`obj: "Expr"`, `start: "Expr | None"`, `end: "Expr | None"`, `value:
"Expr"`, `line: int`, `column: int` — deliberately no `step` field, since
stepped targets are rejected at parse time and never reach this node.

In `cinder/parser.py`: in `_assignment()` (search for `def _assignment`),
right after the existing `if isinstance(expr, Index): return
IndexAssign(...)` branch and before the `ListLiteral` branch, add:
```python
if isinstance(expr, SliceExpr):
    if expr.step is not None:
        raise ParseError(
            "invalid assignment target", eq_token.line, eq_token.column
        )
    return SliceAssign(
        expr.obj, expr.start, expr.end, value, eq_token.line, eq_token.column
    )
```
Add `SliceAssign` to the `from cinder.ast_nodes import (...)` block
(alphabetical; `SliceExpr` is already imported there). Leave every other
assignment form (`??=`, compound `+=`/etc., `++`/`--`) untouched — none
of their branches match `SliceExpr` today (only `Identifier`/`Index`),
so `xs[1:3] += y;`, `xs[1:3] ??= y;`, and `xs[1:3]++;` keep raising
`"invalid assignment target"` exactly as before this task; extending
those to slice targets is out of scope.

In `cinder/interpreter.py`: add a dispatch arm for `SliceAssign` in
`evaluate()` next to the existing `IndexAssign` arm, calling a new
`_evaluate_slice_assign(expr, env)`. Implement it evaluating in source
order — `obj`, then `start` (if present), then `end` (if present), then
`value` — each exactly once:
```python
def _evaluate_slice_assign(self, expr: SliceAssign, env: Environment) -> object:
    obj = self.evaluate(expr.obj, env)
    start = self.evaluate(expr.start, env) if expr.start is not None else None
    end = self.evaluate(expr.end, env) if expr.end is not None else None
    value = self.evaluate(expr.value, env)
    if isinstance(obj, str):
        raise CinderRuntimeError(
            "strings are immutable and do not support item assignment",
            expr.line, expr.column,
        )
    if not isinstance(obj, list):
        raise CinderRuntimeError(
            f"{type_name(obj)} is not sliceable", expr.line, expr.column
        )
    for bound in (start, end):
        if bound is not None and (
            not isinstance(bound, int) or isinstance(bound, bool)
        ):
            raise CinderRuntimeError(
                f"slice bound must be an int, got {type_name(bound)}",
                expr.line, expr.column,
            )
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"slice assignment requires a list value, got {type_name(value)}",
            expr.line, expr.column,
        )
    norm_start, norm_end, _ = slice(start, end, None).indices(len(obj))
    obj[norm_start:norm_end] = value
    return value
```
The bound-type-check loop and `slice(...).indices(len(obj))` normalization
mirror `_evaluate_slice`'s existing read-side logic verbatim (search for
`def _evaluate_slice`) — reuse that shape, don't invent a different
normalization. `obj[norm_start:norm_end] = value` is a plain Python list
slice assignment, which already grows/shrinks `obj` in place when
`value`'s length differs from the replaced range — no manual splicing
needed. Add `SliceAssign` to `interpreter.py`'s own `from
cinder.ast_nodes import (...)` block (alphabetical).

Acceptance criteria:
- `let xs = [1, 2, 3, 4, 5]; xs[1:3] = [9, 9, 9]; print(xs);` prints
  `[1, 9, 9, 9, 4, 5]` — replacement longer than the replaced range
  grows the list.
- `let xs = [1, 2, 3, 4, 5]; xs[1:3] = []; print(xs);` prints
  `[1, 4, 5]` — an empty replacement deletes the range.
- `let xs = [1, 2, 3]; xs[:] = [9]; print(xs);` prints `[9]` — omitted
  start/end (same as read-side slicing) spans the whole list.
- `let xs = [1, 2, 3]; xs[5:10] = [9]; print(xs);` prints `[1, 2, 3, 9]`
  — out-of-range bounds clamp exactly like read-side slicing, appending
  at the end rather than raising.
- `let xs = [1, 2, 3, 4, 5]; xs[-2:] = [9]; print(xs);` prints
  `[1, 2, 3, 9]` — negative bounds normalize the same way read-side
  slicing already does.
- The assignment expression evaluates to the assigned value, matching
  `xs[i] = v`'s existing return-the-value convention: `let xs = [1, 2,
  3]; let result = (xs[0:1] = [9, 9]); print(result);` prints `[9, 9]`.
- `let xs = [1, 2, 3]; xs[0:1] = 5;` raises `CinderRuntimeError` matching
  `"slice assignment requires a list value, got int"` — no implicit
  coercion of a non-list value, even an iterable-looking one like a
  string.
- `let s = "abc"; s[0:1] = "x";` raises `CinderRuntimeError` matching
  `"strings are immutable and do not support item assignment"` — the
  same message plain single-index string assignment already raises.
- `let xs = [1, 2, 3]; xs[0:1:2] = [9];` raises `ParseError` matching
  `"invalid assignment target"` — a stepped slice target is rejected at
  parse time, never reaching the interpreter.
- `let xs = [1, 2, 3]; xs[0:1] += [9];` and `xs[0:1]++;` both still
  raise `ParseError` matching `"invalid assignment target"` — completely
  unaffected regression checks, same as before this task.
- Read-side slicing (`xs[0:1];` as an expression, not an assignment
  target) is completely unaffected — no `SliceAssign` node is ever built
  for it, same `SliceExpr` AST and behavior as before this task.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `SliceAssign` node),
`cinder/parser.py` (`_assignment` and its import block),
`cinder/interpreter.py` (`evaluate`, new `_evaluate_slice_assign`, and
its import block), `tests/test_parser.py`, `tests/test_interpreter.py`.
Once merged, `README.md`'s Data structures bullet needs its "not
assignable" note updated to describe the step-less assignable form, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `hamming_distance` — equal-length string edit distance

Build: add `hamming_distance(a, b)` to `cinder/builtins.py`, registered
right after `levenshtein_distance` (search for `def
_levenshtein_distance`, landed via PR #232) — the breadth task after
task 1's depth work (slice assignment for lists) per `PROJECT.md`'s
breadth-vs-depth policy.
It joins `levenshtein_distance` as the second member of a
"string-distance" pair sitting next to `is_anagram`/`is_rotation`/
`is_permutation`: both return a number rather than a boolean, but where
`levenshtein_distance` handles strings of *any* length via dynamic
programming, `hamming_distance` is the simpler, stricter metric — the
count of positions at which two *equal-length* strings differ — computed
with a single position-wise scan, no DP table needed. This is
deliberately the "easy" counterpart landing right after the DP one, the
same kind of technique-diversification `is_isogram`'s frequency-set check
was to `is_balanced`'s stack scan.

Unlike `levenshtein_distance` (which accepts strings of any length pair
and always returns *some* distance), Hamming distance is only defined for
equal-length inputs — there is no meaningful pairwise "differs at
position i" comparison once the strings run out of shared positions.
Reject unequal-length input with a domain error, mirroring `divisors`'s
own type-vs-domain-error split (a type check first, a separate
domain-specific `CinderRuntimeError` after once the types are already
confirmed valid) rather than silently truncating to the shorter length
or padding the longer one:

```python
def _hamming_distance(arguments: list, line: int, column: int) -> object:
    _require_arity("hamming_distance", arguments, 2, line, column)
    string1, string2 = arguments
    if not isinstance(string1, str):
        raise CinderRuntimeError(
            f"hamming_distance() requires a string as its first argument, got {type_name(string1)}",
            line, column,
        )
    if not isinstance(string2, str):
        raise CinderRuntimeError(
            f"hamming_distance() requires a string as its second argument, got {type_name(string2)}",
            line, column,
        )
    if len(string1) != len(string2):
        raise CinderRuntimeError(
            f"hamming_distance() requires strings of equal length, got lengths {len(string1)} and {len(string2)}",
            line, column,
        )
    return sum(1 for c1, c2 in zip(string1, string2) if c1 != c2)
```

Model the arity/type-checking exactly on `_is_anagram`'s (and, once
landed, `_levenshtein_distance`'s) two-argument "first argument"/"second
argument" message shape, matching the code above verbatim. The
equal-length check runs after both type checks succeed, so a wrong-type
first argument reports the type error, not a confusing length comparison
against a non-string.

Acceptance criteria:
- `hamming_distance("karolin", "kathrin");` is `3` — the classic textbook
  example, differing at 0-indexed positions 2 (`r` vs `t`), 3 (`o` vs
  `h`), and 4 (`l` vs `r`); every other position matches.
- `hamming_distance("", "");` is `0` — two empty strings have no
  differing positions.
- `hamming_distance("abc", "abc");` is `0` — identical strings.
- `hamming_distance("abc", "abd");` is `1` — a single differing position
  at the end.
- `hamming_distance("aaaa", "bbbb");` is `4` — every position differs.
- Symmetric, matching the metric property: `hamming_distance("abc",
  "xyz");` equals `hamming_distance("xyz", "abc");` (both `3`).
- `hamming_distance("abc", "ab");` raises `CinderRuntimeError` matching
  `"hamming_distance() requires strings of equal length, got lengths 3
  and 2"` — unequal lengths are a domain error, not silent truncation or
  padding.
- `hamming_distance(5, "ab");` raises `CinderRuntimeError` matching
  `"hamming_distance() requires a string as its first argument, got
  int"` — the type check fires before the length check, even though `5`
  has no length to compare.
- `hamming_distance("a", true);` raises `CinderRuntimeError` matching
  `"hamming_distance() requires a string as its second argument, got
  bool"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `levenshtein_distance`/
`is_permutation`, see current line numbers — shift if earlier tasks this
cycle landed first), `tests/test_builtins.py`. Once merged, `README.md`'s
Builtins bullet needs `hamming_distance` added near
`levenshtein_distance`/`is_anagram`/`is_rotation`/`is_permutation`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Language: extended slice assignment for lists (`list[start:end:step] = other_list;`)

Build: the depth task after task 2's breadth work (`hamming_distance`)
per `PROJECT.md`'s breadth-vs-depth policy, and the direct follow-on to
task 1 (slice assignment): task 1 deliberately scopes `SliceAssign` to
the step-less form only, rejecting a stepped target
(`list[a:b:c] = value;`) with `ParseError` `"invalid assignment
target"` and explicitly deferring the stepped case to "a future task"
since it needs an exact length match rather than task 1's
grow-or-shrink behavior. This task closes that gap. (Once task 1 has
landed, verify the current behavior still matches this description
before starting — `python3 -m cinder.cli eval 'let xs = [1, 2, 3];
xs[0:3:2] = [9];'` should raise that `ParseError`.)

In `cinder/ast_nodes.py`: `SliceAssign` (added by task 1, right after
`SliceExpr`) gains a fourth field, `step: "Expr | None"`, inserted
between `end` and `value` to mirror `SliceExpr`'s own field order
(`obj`, `start`, `end`, `step`).

In `cinder/parser.py`'s `_assignment()`: replace task 1's
step-rejection branch —
```python
if isinstance(expr, SliceExpr):
    if expr.step is not None:
        raise ParseError(
            "invalid assignment target", eq_token.line, eq_token.column
        )
    return SliceAssign(
        expr.obj, expr.start, expr.end, value, eq_token.line, eq_token.column
    )
```
— with one that threads `expr.step` through instead of rejecting it:
```python
if isinstance(expr, SliceExpr):
    return SliceAssign(
        expr.obj, expr.start, expr.end, expr.step, value,
        eq_token.line, eq_token.column,
    )
```
Every other assignment form stays untouched, same as task 1 left them
— `xs[0:3:2] += y;`, `xs[0:3:2] ??= y;`, and `xs[0:3:2]++;` still raise
`"invalid assignment target"` (their branches only match
`Identifier`/`Index`, never `SliceExpr`, stepped or not).

In `cinder/interpreter.py`, extend `_evaluate_slice_assign` (added by
task 1) to evaluate and validate `step` the same way
`_evaluate_slice`'s read-side logic already does (search for `def
_evaluate_slice`: type-check via `isinstance(step, int) and not
isinstance(step, bool)`, then reject `step == 0`), evaluated in source
order right after `end` and before `value`. Compute
`norm_start, norm_end, norm_step = slice(start, end,
step).indices(len(obj))` (same call task 1 already makes, now passing
the real `step` instead of a hardcoded `None`). Then, instead of task
2's plain `obj[norm_start:norm_end] = value`, assign through the
3-argument slice and let Python's own extended-slice-assignment
machinery enforce the length match, converting its `ValueError` into a
`CinderRuntimeError`:
```python
try:
    obj[norm_start:norm_end:norm_step] = value
except ValueError:
    target_len = len(range(norm_start, norm_end, norm_step))
    raise CinderRuntimeError(
        f"attempt to assign sequence of size {len(value)} to "
        f"extended slice of size {target_len}",
        expr.line, expr.column,
    ) from None
return value
```
No manual "is this an extended slice" branch is needed — Python's
`list.__setitem__` only enforces the exact-length rule when the
effective step is not `1`, so a step-less call (`step=None`) or an
explicit `step=1` both keep task 1's existing grow/shrink behavior
automatically, and only `abs(norm_step) != 1` cases (or any step that
normalizes away from a contiguous run) raise. The rest of
`_evaluate_slice_assign` (the string-immutability check, the
not-a-list check, the bound type checks, the value-must-be-a-list
check) stays exactly as task 1 wrote it.

Acceptance criteria:
- `let xs = [1, 2, 3, 4, 5, 6]; xs[0:6:2] = [9, 9, 9]; print(xs);`
  prints `[9, 2, 9, 4, 9, 6]` — every other element (indices 0, 2, 4)
  replaced in order.
- `let xs = [1, 2, 3]; xs[::-1] = [7, 8, 9]; print(xs);` prints
  `[9, 8, 7]` — a full-list reverse-order target assigns `7` to index
  2, `8` to index 1, `9` to index 0.
- `let xs = [1, 2, 3, 4]; xs[0:4:2] = [1];` raises `CinderRuntimeError`
  matching `"attempt to assign sequence of size 1 to extended slice of
  size 2"` — a length mismatch on a real extended slice is a domain
  error, not silent truncation/padding or a grow/shrink.
- `let xs = [1, 2, 3]; xs[0:2:1] = [9, 9, 9, 9]; print(xs);` prints
  `[9, 9, 9, 9, 3]` — an *explicit* `step=1` still behaves like the
  step-less form (grows the list), since step `1` is never "extended"
  regardless of how it was spelled.
- Task 1's own step-less acceptance criteria (growing, shrinking,
  omitted bounds, out-of-range clamping, negative bounds, the
  assignment-expression-evaluates-to-the-value convention, the
  non-list-value error, the string-immutability error) all still pass
  unchanged — this task only adds behavior for a non-1 step, it does
  not change the step-less path.
- `let xs = [1, 2, 3, 4, 5]; xs[0:5:2] = "ab";` raises
  `CinderRuntimeError` matching `"slice assignment requires a list
  value, got str"` — the value-must-be-a-list check still fires before
  any length comparison, even though a 2-character string might
  otherwise "fit" the 3-element target by accident of length.
- `let xs = [1, 2, 3]; xs[0:3:"a"] = [1, 2, 3];` raises
  `CinderRuntimeError` matching `"slice step must be an int, got
  str"`.
- `let xs = [1, 2, 3]; xs[0:3:0] = [1, 2, 3];` raises
  `CinderRuntimeError` matching `"slice step must not be zero"`.
- `let s = "abcdef"; s[0:6:2] = "xyz";` raises `CinderRuntimeError`
  matching `"strings are immutable and do not support item
  assignment"` — same message as the step-less string case; a stepped
  slice target on a string is no longer a `ParseError` after this task
  (it's now a legal *parse*, since lists accept it), but it's still
  rejected at runtime once the target's actual type is known.
- `let xs = [1, 2, 3]; xs[0:3:2] += [9];` and `xs[0:3:2]++;` both still
  raise `ParseError` matching `"invalid assignment target"` —
  unaffected regression checks, same as task 1.
- Read-side stepped slicing (`xs[0:6:2];` as an expression, not an
  assignment target) is completely unaffected — no `SliceAssign` node
  is ever built for it, same `SliceExpr` AST and behavior as before
  this task.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`SliceAssign` gains `step`),
`cinder/parser.py` (`_assignment`'s `SliceExpr` branch),
`cinder/interpreter.py` (`_evaluate_slice_assign`), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s Data structures
bullet needs its slice-assignment note extended to mention the stepped
form, and `PROJECT.md`'s roadmap paragraph needs it moved from backlog
to landed — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Standard library: `is_harshad` — digit-sum divisibility predicate

Build: add `is_harshad(n)` to `cinder/builtins.py`, registered right
after `is_automorphic` (search for `def _is_automorphic`, the current
last entry in the integer-property cluster) — the breadth task after
task 3's depth work (extended slice assignment) per
`PROJECT.md`'s breadth-vs-depth policy. A positive integer `n` is a
Harshad (or Niven) number when it is evenly divisible by the sum of
its own decimal digits, e.g. `18` is Harshad since `1 + 8 = 9` and `18
% 9 == 0`; `19` is not, since `1 + 9 = 10` and `19 % 10 != 0`. It joins
the `is_perfect_square`/`is_armstrong`/`is_leap_year`/
`is_perfect_number`/`is_abundant`/`is_deficient`/`is_automorphic`
integer-property cluster as one more digit-based classification.

Compute the digit sum inline with the same plain walk `digit_sum`
already uses internally — `sum(int(digit) for digit in
str(abs(value)))` (search for `def _digit_sum` to copy its exact
expression) — rather than calling the `digit_sum` builtin's own
`(arguments, line, column)` wrapper, since that wrapper expects a
Cinder argument list, not a bare Python int:

```python
def _is_harshad(arguments: list, line: int, column: int) -> object:
    _require_arity("is_harshad", arguments, 1, line, column)
    value = _require_int("is_harshad", arguments[0], line, column)
    if value < 1:
        return False
    digit_total = sum(int(digit) for digit in str(value))
    return value % digit_total == 0
```

Model the arity/type-checking exactly on `_is_automorphic`'s structure:
`_require_arity("is_harshad", arguments, 1, line, column)`, then
`value = _require_int("is_harshad", arguments[0], line, column)`
(reusing the shared `_require_int` helper — do **not** hand-roll a
separate `isinstance` check). The `value < 1` guard matches
`is_abundant`/`is_deficient`'s own convention of answering `false` on
zero and negative input rather than raising a domain error — it also
sidesteps a `ZeroDivisionError` that a bare digit-sum-of-zero would
otherwise cause, since `digit_total` is only ever `0` when `value` is
`0`, which this guard already excludes before the division runs.

Acceptance criteria:
- `is_harshad(18);` is `true` — `1 + 8 = 9`, `18 % 9 == 0`.
- `is_harshad(19);` is `false` — `1 + 9 = 10`, `19 % 10 != 0`.
- `is_harshad(1);` is `true` — every single nonzero digit divides
  itself.
- `is_harshad(12);` is `true` — `1 + 2 = 3`, `12 % 3 == 0`.
- `is_harshad(11);` is `false` — `1 + 1 = 2`, `11 % 2 != 0`.
- `is_harshad(100);` is `true` — `1 + 0 + 0 = 1`, `100 % 1 == 0`
  (every integer is divisible by `1`).
- `is_harshad(0);` is `false` — excluded by the `value < 1` guard
  rather than raising a division-by-zero error.
- `is_harshad(-18);` is `false` — negative input answers `false`
  without raising, matching `is_abundant`/`is_deficient`'s convention.
- `is_harshad(5.0);` raises `CinderRuntimeError` matching
  `"is_harshad() requires an int, got float"` — the same message shape
  `_require_int` already produces for every sibling in this cluster.
- `is_harshad(true);` raises `CinderRuntimeError` matching
  `"is_harshad() requires an int, got bool"` — `_require_int` already
  excludes `bool` from passing as an int.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_deficient`/`is_automorphic`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_harshad` added near
`is_perfect_number`/`is_abundant`/`is_deficient`/`is_automorphic`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 5. Language: map-destructuring key rename (`let {a: x, b} = expr;`)

Build: the depth task after task 4's breadth work (`is_harshad`) per
`PROJECT.md`'s breadth-vs-depth policy. Every map-destructuring form —
`let {a, b} = expr;`, plain assignment `{a, b} = expr;`, `for {a, b} in
list_of_maps { ... }`, function params `fn f({a, b}) { ... }`, and both
comprehension loop-variable forms — currently binds each name to a
variable of the *same* name as the map key it reads (`{a, b}` always
declares `a` and `b`). There is no way to bind under a different local
name, unlike JS destructuring's `const {a: x} = obj`. Verify the gap:
`python3 -m cinder.cli eval 'let {a: x} = {"a": 1}; print(x);'` currently
raises `ParseError` `"'}' after destructuring pattern"` (the parser sees
`IDENTIFIER COLON` where it only expects `IDENTIFIER COMMA`/`RBRACE`).

All five forms share two parser entry points and one interpreter entry
point, so the change is centralized rather than five separate edits:
`_destructure_map_pattern` (search for `def _destructure_map_pattern` in
`cinder/parser.py`) is called by `let`, `for`, params, and both
comprehensions; `_try_map_destructure_assign_statement` (search for that
name, same file) has its own inlined copy of the same identifier-list
loop for the plain-assignment form; both feed `names`/`rest` straight
into `_bind_map_destructure` (search for `def _bind_map_destructure` in
`cinder/interpreter.py`), the single place that actually reads keys out
of the map and binds variables. Changing what `names` holds and how
`_bind_map_destructure` consumes it is the whole feature — none of the
five call sites need their own changes.

Change `names` from a flat `list[str]` (map key doubles as binding name)
to a `list[tuple[str, str]]` of `(key, binding)` pairs, `binding`
defaulting to `key` when no rename is written. Add a shared parsing
helper right above `_destructure_map_pattern`:

```python
def _destructure_map_pattern_entry(self) -> "tuple[str, str]":
    key = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    if self._check(TokenType.COLON):
        self._advance()
        binding = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    else:
        binding = key
    return key, binding
```

In `_destructure_map_pattern`, replace both
`names.append(self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme)`
lines (the initial entry and the one inside the `while COMMA` loop) with
`names.append(self._destructure_map_pattern_entry())`. Do the same for
the two matching lines inside
`_try_map_destructure_assign_statement`'s own `try` block. Nothing else
in either function changes — the rest-element handling, the
rest-must-be-last check (`_RestNotLast` in the assignment form), and the
trailing `}`/`=` consumption are all untouched, since they operate on
`names` as an opaque list either way.

In `_bind_map_destructure`, unpack the pairs and use the *key* for the
map lookup and the *binding* for the environment write, and use a set of
keys (not the tuple list itself) to compute the rest element's leftover
keys:

```python
def _bind_map_destructure(
    self,
    env: Environment,
    names: list,
    rest: "str | None",
    value: object,
    line: int,
    column: int,
    use_assign: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise CinderRuntimeError(
            f"cannot destructure {type_name(value)} as a map",
            line,
            column,
        )
    seen_keys = set()
    for key, binding in names:
        seen_keys.add(key)
        if key not in value:
            raise CinderRuntimeError(
                f"destructuring pattern expects key {key!r}, not found in map",
                line,
                column,
            )
        self._bind_destructure_name(env, binding, value[key], line, column, use_assign)
    if rest is not None:
        remaining = {k: v for k, v in value.items() if k not in seen_keys}
        self._bind_destructure_name(env, rest, remaining, line, column, use_assign)
```

The error message keeps referencing the *key* (what's missing from the
map), not the binding name, since that's what a reader needs to fix.
`DestructureLetStmt`/`DestructureAssign`/`ForStmt`/`Param`/
`ListComprehension`/`MapComprehension` in `cinder/ast_nodes.py` need no
field changes — `names: list` already accepts either shape, and every
consumer of `.names` (grep confirms only `_bind_map_destructure` and
`_bind_list_destructure` read it, dispatched by each node's own `is_map`
flag) already routes map-mode data through the function above.

No rename support is added to *list*-pattern destructuring
(`let [a, b] = expr;`) — list patterns are purely positional, so
"rename" has no meaning there; this task only touches
`_destructure_map_pattern`/`_try_map_destructure_assign_statement`/
`_bind_map_destructure`.

Test-shape ripple: every existing `test_parser.py` assertion that checks
a map-destructure node's `.names` as a flat list of plain strings (e.g.
`["a", "b"]` for `{a, b} = ...;`) now needs updating to the pair form
(`[("a", "a"), ("b", "b")]`) — search `test_parser.py` for
`is_map=True` sites and the surrounding `DestructureLetStmt`/
`DestructureAssign` shape tuples that precede them; the `shape()`/
`stmt_shape()` helpers themselves need no changes since they just
forward whatever `.names` holds. This is a mechanical, no-behavior-change
update for every pre-existing plain-name test; only the *new* rename
tests exercise the actual feature.

Acceptance criteria:
- `let {a: x, b} = {"a": 1, "b": 2}; print(x); print(b);` prints `1`
  then `2` — `a`'s value binds to `x`, `b` binds to itself (no rename).
- `{a: x} = {"a": 5}; print(x);` (plain-assignment form, `x` already
  declared via `let x = 0;` beforehand) prints `5`.
- `for {a: x, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}] { print(x + b); }`
  prints `3` then `7`.
- `fn f({a: x}) { return x; } print(f({"a": 9}));` prints `9`.
- `print([x for {a: x} in [{"a": 1}, {"a": 2}]]);` prints `[1, 2]`.
- `let {a: x, ...rest} = {"a": 1, "b": 2, "c": 3}; print(x); print(rest);`
  prints `1` then `{"b": 2, "c": 3}` — the rest element still collects by
  *key*, unaffected by the earlier rename.
- `let {a: x} = {"b": 1};` raises `CinderRuntimeError` matching
  `"destructuring pattern expects key 'a', not found in map"` — the
  error names the source key, not the binding `x`.
- Plain, non-renamed patterns (`let {a, b} = expr;` and every other
  existing form) behave identically to before this task — this is purely
  additive syntax.
- `let {a: x, a: y} = {"a": 1};` (same key renamed twice) is not
  specially rejected — it parses and runs like any other repeated-name
  destructuring pattern already does today (last binding wins, no new
  validation added for this task).
- Full test suite passes, including the updated `.names` shape
  assertions described above.

Likely files: `cinder/parser.py` (new `_destructure_map_pattern_entry`,
both call sites), `cinder/interpreter.py` (`_bind_map_destructure`),
`tests/test_parser.py` (shape assertions plus new rename tests),
`tests/test_interpreter.py` (new rename tests for `let`/assignment/
`for`/params/comprehensions). Once merged, `README.md`'s destructuring
bullets need a rename mention added to each of the five forms, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `is_perfect_cube` — integer cube-root predicate

Build: the breadth task after task 5's depth work (map-destructuring key
rename) per `PROJECT.md`'s breadth-vs-depth policy. A positive, negative,
or zero integer `n` is a perfect cube when some integer `k` satisfies
`k ** 3 == n` (e.g. `27 = 3**3`, `-8 = (-2)**3`, `0 = 0**3`). It joins the
`is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`/
`is_abundant`/`is_deficient`/`is_automorphic`/`is_harshad`
integer-property cluster as one more digit/root-based classification —
register it right after `is_harshad` (search for `def _is_harshad`, the
current last entry in the cluster once task 4 lands).

Unlike `is_perfect_square` (which excludes negative input, since no real
square root of a negative number is an integer), cube roots of negative
numbers *are* real and integral — `-8`'s cube root is `-2` — so this
predicate must accept negative input rather than short-circuiting to
`false` the way `is_perfect_square` does. There is no `math.icbrt` in the
standard library (unlike `math.isqrt` for squares), and a floating-point
`round(n ** (1/3))` risks exactly the rounding-error problem
`math.isqrt` was chosen to avoid for squares — so compute an exact
integer cube root via binary search on the magnitude, then restore the
sign:

```python
def _integer_cube_root(magnitude: int) -> int:
    if magnitude == 0:
        return 0
    low, high = 0, magnitude
    while low < high:
        mid = (low + high + 1) // 2
        if mid ** 3 <= magnitude:
            low = mid
        else:
            high = mid - 1
    return low


def _is_perfect_cube(arguments: list, line: int, column: int) -> object:
    _require_arity("is_perfect_cube", arguments, 1, line, column)
    value = _require_int("is_perfect_cube", arguments[0], line, column)
    magnitude = abs(value)
    root = _integer_cube_root(magnitude)
    return root ** 3 == magnitude
```

`_integer_cube_root` operates on the non-negative magnitude only, so its
own result is always non-negative; the predicate doesn't need to
reconstruct the signed root at all, since cubing preserves sign
symmetry: `magnitude` is a perfect cube iff `abs(value)` is, for either
sign of `value`. Model the arity/type-checking exactly on
`_is_harshad`/`_is_perfect_square`'s structure: `_require_arity`, then
`_require_int` (reusing the shared helper — do **not** hand-roll a
separate `isinstance` check).

Acceptance criteria:
- `is_perfect_cube(27);` is `true` — `3 ** 3 == 27`.
- `is_perfect_cube(1);` is `true` — `1 ** 3 == 1`.
- `is_perfect_cube(0);` is `true` — `0 ** 3 == 0`.
- `is_perfect_cube(-8);` is `true` — `(-2) ** 3 == -8`, unlike
  `is_perfect_square`, negative input is not automatically `false`.
- `is_perfect_cube(-27);` is `true` — `(-3) ** 3 == -27`.
- `is_perfect_cube(8);` is `true` — `2 ** 3 == 8`.
- `is_perfect_cube(9);` is `false` — no integer cubes to `9`.
- `is_perfect_cube(-9);` is `false` — no integer cubes to `-9` either.
- `is_perfect_cube(1000000);` is `true` — `100 ** 3 == 1000000`, a case
  large enough that a naive `round(n ** (1/3))` float approach could
  plausibly drift off by one, proving the binary-search approach is
  exact.
- `is_perfect_cube(5.0);` raises `CinderRuntimeError` matching
  `"is_perfect_cube() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_perfect_cube(true);` raises `CinderRuntimeError` matching
  `"is_perfect_cube() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`is_harshad`/`is_perfect_square`, see current line numbers — shift if
earlier tasks this cycle landed first), `tests/test_builtins.py`. Once
merged, `README.md`'s Builtins bullet needs `is_perfect_cube` added near
`is_perfect_square`/`is_armstrong`/`is_automorphic`/`is_harshad`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed —
leave both to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
