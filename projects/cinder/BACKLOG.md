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

## 1. Standard library: `is_automorphic` — n² ends with n predicate

Build: add `is_automorphic(n)` to `cinder/builtins.py`, registered
right after `is_deficient` (search for `def _is_deficient`) — the
breadth task after the just-landed chained comparison operators depth
work (PR #233) per `PROJECT.md`'s breadth-vs-depth policy. It joins the
`is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`/
`is_abundant`/`is_deficient` integer-property cluster as one more
digit-based classification: an integer `n` is automorphic when its
square, written in decimal, ends with `n` itself (e.g. `5² = 25` ends
in `5`; `6² = 36` ends in `6`; `25² = 625` ends in `25`; `76² = 5776`
ends in `76`).

Implement as a plain string check rather than modular arithmetic —
`str(n * n).endswith(str(n))` — mirroring how `_is_palindrome_number`
and `_is_armstrong` already work with `str(value)` rather than
digit-by-digit math. Model the arity/type-checking exactly on
`_is_armstrong`'s structure: `_require_arity("is_automorphic",
arguments, 1, line, column)`, then `value = _require_int("is_automorphic",
arguments[0], line, column)` (reusing the shared `_require_int` helper,
same as `_is_perfect_square`/`_is_armstrong`/`_is_leap_year`/
`_is_perfect_number`/`_is_abundant`/`_is_deficient` already do — do
**not** hand-roll a separate `isinstance` check). Negative input
returns `false` without raising, matching every sibling in this
cluster's convention (`is_perfect_square`, `is_armstrong`,
`is_perfect_number`, `is_abundant`, `is_deficient` all answer `false`
on negative input rather than treating it as a domain error) — the
`str(n * n).endswith(str(n))` check would also mishandle a negative
`n`'s leading `-` if allowed through, so guard it the same way those
five already guard theirs, before doing the string check.

Acceptance criteria:
- `is_automorphic(5);` is `true` — `5² = 25` ends in `5`.
- `is_automorphic(6);` is `true` — `6² = 36` ends in `6`.
- `is_automorphic(25);` is `true` — `25² = 625` ends in `25`.
- `is_automorphic(76);` is `true` — `76² = 5776` ends in `76`.
- `is_automorphic(0);` is `true` — `0² = 0` ends in `0`.
- `is_automorphic(1);` is `true` — `1² = 1` ends in `1`.
- `is_automorphic(7);` is `false` — `7² = 49` does not end in `7`.
- `is_automorphic(10);` is `false` — `10² = 100` does not end in `10`.
- `is_automorphic(-5);` is `false` — negative input answers `false`
  without raising, matching the rest of the cluster.
- `is_automorphic(5.0);` raises `CinderRuntimeError` matching
  `"is_automorphic() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_automorphic(true);` raises `CinderRuntimeError` matching
  `"is_automorphic() requires an int, got bool"` — `_require_int`
  already excludes `bool` from passing as an int, same as `is_int`'s
  own bool-exclusion.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_deficient`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_automorphic` added near
`is_perfect_number`/`is_abundant`/`is_deficient`, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Language: slice assignment for lists (`list[start:end] = other_list;`)

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

## 3. Standard library: `hamming_distance` — equal-length string edit distance

Build: add `hamming_distance(a, b)` to `cinder/builtins.py`, registered
right after `levenshtein_distance` (search for `def
_levenshtein_distance`, landed via PR #232) — the breadth task after
task 2's depth work (slice assignment for lists) per `PROJECT.md`'s
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

## 4. Language: extended slice assignment for lists (`list[start:end:step] = other_list;`)

Build: the depth task after task 3's breadth work (`hamming_distance`)
per `PROJECT.md`'s breadth-vs-depth policy, and the direct follow-on to
task 2 (slice assignment): task 2 deliberately scopes `SliceAssign` to
the step-less form only, rejecting a stepped target
(`list[a:b:c] = value;`) with `ParseError` `"invalid assignment
target"` and explicitly deferring the stepped case to "a future task"
since it needs an exact length match rather than task 2's
grow-or-shrink behavior. This task closes that gap. (Once task 2 has
landed, verify the current behavior still matches this description
before starting — `python3 -m cinder.cli eval 'let xs = [1, 2, 3];
xs[0:3:2] = [9];'` should raise that `ParseError`.)

In `cinder/ast_nodes.py`: `SliceAssign` (added by task 2, right after
`SliceExpr`) gains a fourth field, `step: "Expr | None"`, inserted
between `end` and `value` to mirror `SliceExpr`'s own field order
(`obj`, `start`, `end`, `step`).

In `cinder/parser.py`'s `_assignment()`: replace task 2's
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
Every other assignment form stays untouched, same as task 2 left them
— `xs[0:3:2] += y;`, `xs[0:3:2] ??= y;`, and `xs[0:3:2]++;` still raise
`"invalid assignment target"` (their branches only match
`Identifier`/`Index`, never `SliceExpr`, stepped or not).

In `cinder/interpreter.py`, extend `_evaluate_slice_assign` (added by
task 2) to evaluate and validate `step` the same way
`_evaluate_slice`'s read-side logic already does (search for `def
_evaluate_slice`: type-check via `isinstance(step, int) and not
isinstance(step, bool)`, then reject `step == 0`), evaluated in source
order right after `end` and before `value`. Compute
`norm_start, norm_end, norm_step = slice(start, end,
step).indices(len(obj))` (same call task 2 already makes, now passing
the real `step` instead of a hardcoded `None`). Then, instead of task
3's plain `obj[norm_start:norm_end] = value`, assign through the
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
explicit `step=1` both keep task 2's existing grow/shrink behavior
automatically, and only `abs(norm_step) != 1` cases (or any step that
normalizes away from a contiguous run) raise. The rest of
`_evaluate_slice_assign` (the string-immutability check, the
not-a-list check, the bound type checks, the value-must-be-a-list
check) stays exactly as task 2 wrote it.

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
- Task 2's own step-less acceptance criteria (growing, shrinking,
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
  unaffected regression checks, same as task 2.
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
