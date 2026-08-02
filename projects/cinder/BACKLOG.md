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

## 1. Exponentiation operator `**` [claimed 2026-08-02T20:26:44Z]

Build: a new binary operator `**` for exponentiation, right-associative,
binding tighter than `*`/`/`/`%` and looser than unary (`-`/`not`/`~`) —
Cinder has had a `pow()` builtin all along but no infix syntax for it,
the same kind of gap `product`/`sum` closed on the stdlib side. Scope
this as the operator only: **no** `**=` compound-assignment form in this
task (every other arithmetic operator's `**=`-shaped sibling was added
in lockstep with its base operator, but bundling that here as well would
make this a two-feature task — leave `**=` as a natural, separately-
scoped follow-up once `**` itself exists, the same deferral reasoning
the safe-navigation task used for full-chain propagation).

Lexer (`cinder/lexer.py`): `*` currently goes through
`_op_or_compound_assign` (`cinder/lexer.py:299-310`), which handles the
doubled-character case only for `+`/`-` via `_INCREMENT_DECREMENT_TOKENS`
(`cinder/lexer.py:32-35`) — `*` isn't in that dict, so a second `*` is
presently unreachable from that function and would fall through to
`_match("=")`, then emit a lone `STAR` and leave the second `*` for the
next iteration (wrong: `2**3` would lex as `STAR STAR` two separate
tokens, then `_op_or_compound_assign` would run again for the second
`*`). Add a dedicated branch at the top of `_op_or_compound_assign`,
before the existing `if char in _INCREMENT_DECREMENT_TOKENS` check:
`if char == "*" and self._match("*"): self.tokens.append(Token(TokenType.STARSTAR, "**", None, start_line, start_col)); return` —
mirrors the shape of the existing doubled-token branch just below it.
Add `STARSTAR = auto()` to `TokenType` in `cinder/tokens.py`, near `STAR`
(`cinder/tokens.py:51`).

Parser (`cinder/parser.py`): insert a new `_power` precedence level
between `_factor` (`cinder/parser.py:892-898`) and `_unary`
(`cinder/parser.py:900-914`) — right-associative, unlike every other
binary level in this chain (`_term`/`_factor`/`_bitand`/etc. are all
left-associative loops):
```python
def _power(self) -> Expr:
    expr = self._unary()
    if self._check(TokenType.STARSTAR):
        operator = self._advance()
        right = self._power()  # right-associative: 2 ** 3 ** 2 == 2 ** (3 ** 2)
        expr = Binary(expr, operator, right)
    return expr
```
Change `_factor` (`cinder/parser.py:892-898`) to call `self._power()`
instead of `self._unary()` on both its initial `expr` line and inside
its `while` loop's `right = self._unary()` line — this makes `**` bind
tighter than `*`/`/`/`%` (`_FACTOR`, `cinder/parser.py:158`) and looser
than unary, which deliberately means `-2 ** 2` parses as `(-2) ** 2`
(`4`), **not** Python's special-cased `-(2 ** 2)` (`-4`) — pin this
explicitly as a test rather than silently inheriting whichever behavior
falls out, since it's the one place this feature knowingly diverges from
Python's operator precedence table.

Interpreter (`cinder/interpreter.py`): in `_apply_binary_operator`
(`cinder/interpreter.py:780-822`), add a branch alongside `STAR`
(`cinder/interpreter.py:795-799`): `if op == TokenType.STARSTAR: return
self._numeric_op(operator, left, right, lambda a, b: a ** b)` — reuses
`_numeric_op` (`cinder/interpreter.py:856-864`) exactly like `MINUS`
does (`cinder/interpreter.py:793-794`), which already raises
`CinderRuntimeError` naming both operand types via `type_name` and the
operator's own `lexeme` (`"**"`) when either side isn't a number; no
`_repeat_op`-style special case is needed since `**` has no string/list
repetition meaning the way `*` does.

Acceptance criteria:
- `2 ** 10;` is `1024` — the primary case, pin as the main regression
  test.
- `2 ** 3 ** 2;` is `512` (right-associative: `2 ** (3 ** 2)`, not
  `(2 ** 2) ** 3 == 64`) — the case that specifically distinguishes this
  from every other binary operator in the language, all of which are
  left-associative.
- `(-2) ** 2;` is `4` and `-2 ** 2;` is also `4` (not `-4`) — pins the
  deliberate divergence from Python's precedence table where unary minus
  binds *looser* than `**`; here it binds *tighter*, matching every other
  unary-vs-binary interaction already in the language.
- `2 ** -1;` is `0.5` — a negative exponent on the right works via plain
  Python `**` semantics (the right operand is parsed through `_unary`,
  so `-1` is a valid right-hand operand).
- `2.5 ** 2;` is `6.25` — floats work, not just ints.
- `2 ** 0;` is `1` and `0 ** 0;` is `1` — the zero-exponent and
  zero-base-zero-exponent edge cases match Python's own `**` behavior
  (no special-casing needed, just don't accidentally guard against them).
- `"a" ** 2;` and `2 ** "a"` both raise `CinderRuntimeError` naming `**`
  and the non-number operand's type, matching `_numeric_op`'s existing
  message shape for `MINUS`/other numeric-only operators.
- `2 ** 3 * 4;` is `32` (`(2 ** 3) * 4`, i.e. `**` binds tighter than
  `*`) and `2 * 3 ** 2;` is `18` (`2 * (3 ** 2)`) — pins precedence
  relative to `_factor`'s operators from both sides.
- Lexer-level test: `**` tokenizes as a single `STARSTAR`, and `2 * *3`
  (a `*` then whitespace then another `*`, if that's even reachable —
  otherwise skip) and existing single-`*`/`*=` tokenization are
  unaffected — full existing `tests/test_lexer.py` suite still passes
  unmodified alongside the new test.
- `**=` is not implemented in this task: `x **= 2;` raises `ParseError`
  (there is no `STARSTAREQ` token) — add one test pinning that it's a
  parse error, not a silent no-op or crash, so a future task adding
  `**=` has a clear "this used to error" baseline.
- Full test suite passes.

Likely files: `cinder/tokens.py` (new `STARSTAR`, near
`cinder/tokens.py:51`), `cinder/lexer.py` (`_op_or_compound_assign`,
`cinder/lexer.py:299-310`), `cinder/parser.py` (new `_power`, and
`_factor`'s two call sites, near `cinder/parser.py:892-898`),
`cinder/interpreter.py` (`_apply_binary_operator`, near
`cinder/interpreter.py:795-799`), `tests/test_lexer.py`,
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged,
`README.md`'s Operators bullet needs a `**` mention — leave that to the
Architect's next grooming pass, not this task.

---

## 2. Compound assignment `**=` for exponentiation

Build: once task 1 (`**`) lands, add its compound-assignment sibling
`**=`, mirroring every other arithmetic operator's `+=`/`-=`/`*=`/`/=`/
`%=` pattern — the natural follow-up `PROJECT.md`'s roadmap already
flags as deferred out of task 1 to keep that task single-feature.
`x **= 2;` desugars to `x = x ** 2;` for identifier targets, and (like
the other arithmetic compound-assign ops, not the bitwise/shift-only
ones) also accepts index/dot-access targets: `xs[0] **= 2;`,
`m.key **= 2;`.

Lexer (`cinder/tokens.py`, `cinder/lexer.py`): add `STARSTAREQ =
auto()` to `TokenType` in `cinder/tokens.py`, next to wherever task 1
placed `STARSTAR` (near `STAR`). Task 2 adds a dedicated branch at the
top of `_op_or_compound_assign` (`cinder/lexer.py`, currently around
line 299): `if char == "*" and self._match("*"): ... emit STARSTAR
...`, returning immediately after consuming the second `*` — task 1
deliberately pins `2 **= 3` as lexing to `STARSTAR` then `EQ` (a later
`ParseError`) as its baseline. Extend that branch: after consuming the
second `*`, also check `self._match("=")`; if it matches, emit
`STARSTAREQ` (lexeme `"**="`) instead of `STARSTAR`; otherwise emit
`STARSTAR` as before — mirrors how `_lt`'s `<`/`<=`/`<<`/`<<=` cascade
checks for a further `=` after already matching a doubled character.

Parser (`cinder/parser.py`): this codebase's compound-assign machinery
is fully dict-driven — `_COMPOUND_ASSIGN_OPS` (`cinder/parser.py:161-
171`) maps each compound token to its base binary-operator token, and
`_INDEX_TARGET_COMPOUND_ASSIGN_OPS` (`cinder/parser.py:177-188`) is the
set of compound tokens that may also target an `Index`/dot-access
expression (not just a plain `Identifier`) — no new AST node or
dispatch branch is needed. Add `TokenType.STARSTAREQ:
TokenType.STARSTAR` to `_COMPOUND_ASSIGN_OPS`, and add
`TokenType.STARSTAREQ` to the `_INDEX_TARGET_COMPOUND_ASSIGN_OPS` set
(every existing arithmetic compound-assign op already accepts index
targets, so `**=` belongs in that family, not excluded from it like
`??=` is scoped separately).

Interpreter (`cinder/interpreter.py`): no changes needed. `_assignment`'s
existing desugaring (`cinder/parser.py:764-793`) turns `x **= 2` into
`Assign(x, Binary(Identifier(x), Token(STARSTAR, "**", ...), Literal(2)))`
(the compound token's lexeme sliced `[:-1]` becomes the base operator's
lexeme: `"**="[:-1] == "**"`), and `Binary` nodes with a `STARSTAR`
operator already evaluate correctly via task 1's `_apply_binary_operator`
branch; `xs[0] **= 2` similarly reuses the existing `IndexCompoundAssign`
evaluator unchanged.

Acceptance criteria:
- `let x = 2; x **= 10; x;` is `1024` — the primary case, pin as the
  main regression test.
- `let xs = [2]; xs[0] **= 3; xs[0];` is `8` — index-target compound
  assign works.
- `let m = {"a": 2}; m.a **= 3; m.a;` is `8` — dot-access target
  compound assign works (dot access desugars to `Index`, same path).
- `let x = 2; x **= -1; x;` is `0.5` — a negative-exponent RHS still
  works through the compound-assign desugaring.
- `const x = 2; x **= 2;` raises `CinderRuntimeError` and leaves `x`
  unchanged — mirrors the existing `test_const_compound_assignment_*`
  pair for `+=` in `tests/test_interpreter.py:504-514`.
- `"a" **= 2;`-shaped type errors: `let x = "a"; x **= 2;` raises
  `CinderRuntimeError` naming `**` and the non-number operand's type,
  matching task 1's `**` error message shape (the desugared `Binary`
  reuses the same `_numeric_op` path).
- Lexer-level test: `**=` tokenizes as a single `STARSTAREQ`, and `**`
  (no trailing `=`) still tokenizes as `STARSTAR` unaffected — full
  existing `tests/test_lexer.py` suite (including task 1's new `**`
  tests) still passes unmodified alongside the new test.
- Full test suite passes.

Likely files: `cinder/tokens.py` (new `STARSTAREQ`, near `STARSTAR`),
`cinder/lexer.py` (extend task 1's `_op_or_compound_assign` branch),
`cinder/parser.py` (`_COMPOUND_ASSIGN_OPS` and
`_INDEX_TARGET_COMPOUND_ASSIGN_OPS`, `cinder/parser.py:161-188`),
`tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.
Once merged, `README.md`'s Operators bullet needs a `**=` mention
alongside the other compound-assignment operators — leave that to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `sum_by` — sum of a function applied to each element

Build: add `sum_by(list, fn)` to `cinder/builtins.py`, the numeric
fold-by-key counterpart that closes the last gap in the
`min_by`/`max_by`/`sort_by`/`group_by`/`count_by`/`distinct_by` family —
all of those already take a list plus a key/predicate function, but
there's no by-key equivalent of `sum`. Unlike `min_by`/`max_by`
(`cinder/builtins.py:1605-1637`), which accept a function returning all
numbers *or* all strings (since min/max are well-defined on either),
`sum_by` is numbers-only, matching `sum` itself
(`cinder/builtins.py:1047-1061`) — summing strings isn't well-defined
the way `+` isn't string concatenation via `sum`.

Model the arity/type checks on `_min_max_by`'s structure (arity 2, first
argument a `list` else `CinderRuntimeError` naming `sum_by` and
`type_name`, matching `"sum_by() requires a list as its first argument,
got {type_name}"`; second argument must be `_is_callable` else
`CinderRuntimeError` matching `"sum_by() requires a function as its
second argument, got {type_name}"`), but fold like `_sum` does: call
`call_value(fn, [item], line, column)` for each element, check
`_is_numeric` on each result (else `CinderRuntimeError` matching
`"sum_by() requires a function returning numbers, got {type_name}"`),
and accumulate starting from `0`. Unlike `min_by`/`max_by`, an empty
list is well-defined (mirrors `sum([])` being `0`, not an error) — do
not add a non-empty check. Register it in the builtins dict near `sum`/
`product` (`cinder/builtins.py:2511-2512`, `"sum": _sum,` /
`"product": _product,`).

Acceptance criteria:
- `sum_by([1, 2, 3], fn(n) { return n * 2; });` is `12` — the primary
  case, pin as the main regression test.
- `sum_by([], fn(n) { return n; });` is `0` and the function is never
  called — mirrors `sum([])`'s well-defined empty case, not an error
  (contrast with `min_by`/`max_by`, which do error on empty lists).
- `sum_by(["a", "bb", "ccc"], fn(s) { return len(s); });` is `6` — the
  function's return value, not the element itself, is what's summed.
- `sum_by([1, 2], fn(n) { return "x"; });` (function returns a
  non-number) raises `CinderRuntimeError` naming `sum_by` and `string`
  in the message — contrast with `min_by`/`max_by`, which would accept
  an all-string result; `sum_by` never does.
- `sum_by(5, fn(n) { return n; });` (a non-list first argument) raises
  `CinderRuntimeError` naming `sum_by` and `number` in the message.
- `sum_by([1, 2], 5);` (a non-function second argument) raises
  `CinderRuntimeError` naming `sum_by` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `sum`/`product`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `sum_by` added near `sum`/`product` — leave that to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `reject` — `filter`'s inverse

Build: add `reject(list, fn)` to `cinder/builtins.py`, the predicate
complement of `filter` (`cinder/builtins.py:2127-2140`) — keeps every
element the predicate is falsy for instead of truthy for, closing the
same "opposite of an existing predicate combinator" gap that
`omit`/`omit_by` already closed for `pick`/`pick_by`, but `filter` has
never had one. Model directly on `_filter`'s structure line for line
(arity 2, first argument a `list` else `CinderRuntimeError` naming
`reject` and `type_name`, matching `"reject() requires a list as its
first argument, got {type_name}"`; second argument must be
`_is_callable` else `CinderRuntimeError` matching `"reject() requires a
function as its second argument, got {type_name}"`), but invert the
truthiness check in the comprehension: `[item for item in items if not
is_truthy(call_value(fn, [item], line, column))]` — the single-character
difference from `_filter`'s body (`not is_truthy(...)` instead of
`is_truthy(...)`) is the entire behavioral distinction between the two
functions. Register it in the builtins dict near `filter`
(`cinder/builtins.py:2551`, `"filter": _filter,`).

Acceptance criteria:
- `reject([1, 2, 3, 4], fn(n) { return n % 2 == 0; });` is `[1, 3]` —
  the primary case, pin as the main regression test; contrast with
  `filter` on the same input/predicate returning `[2, 4]` to prove this
  isn't accidentally aliased to `filter`.
- `reject([], fn(n) { return true; });` is `[]` and the function is
  never called — mirrors `filter`'s existing "on empty list returns []
  and never calls fn" test shape.
- `reject([1, 2, 3], fn(n) { return false; });` is `[1, 2, 3]` (the
  predicate is always falsy, so every element is kept) and
  `reject([1, 2, 3], fn(n) { return true; });` is `[]` (always truthy,
  so nothing is kept) — the two boundary cases.
- `reject([0, 1, nil, 2, false], fn(n) { return n == 1; });` is
  `[0, nil, 2, false]` — pins that `reject` only removes elements where
  the predicate itself returns truthy, not elements that are themselves
  falsy (that's `compact`'s job, a different builtin); the predicate's
  return value truthiness is what's inverted, not the element's.
- `reject(5, fn(n) { return true; });` (a non-list first argument)
  raises `CinderRuntimeError` naming `reject` and `number` in the
  message.
- `reject([1, 2], 5);` (a non-function second argument) raises
  `CinderRuntimeError` naming `reject` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `filter`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `reject` added near `filter` — leave that to the Architect's next
grooming pass, not this task.

---

## 5. Standard library: `find_last` — reverse-search counterpart to `find`

Build: add `find_last(string, substring)` to `cinder/builtins.py`, the
string search analog of what `find_last_index` just did for lists —
`find` (`cinder/builtins.py:675-687`) already returns the index of a
substring's *first* occurrence via Python's `str.find`, but there's no
way to search from the end; Python's `str.rfind` is the direct
equivalent, and this closes that gap the same way `last_index_of`
closes it for list equality-search versus `index_of`.

Model directly on `_find`'s structure line for line (arity 2, first
argument a `string` else `CinderRuntimeError` naming `find_last` and
`type_name`, matching `"find_last() requires a string as its first
argument, got {type_name}"`; second argument must be a `string` else
`CinderRuntimeError` matching `"find_last() requires a string to search
for, got {type_name}"`), but call `value.rfind(sub)` instead of
`value.find(sub)` — the single-call difference from `_find`'s body is
the entire behavioral distinction between the two functions, exactly
like `not is_truthy(...)` was the entire distinction between `reject`
and `filter` in task 4. Register it in the builtins dict near `find`
(`cinder/builtins.py:2483`, `"find": _find,`).

Acceptance criteria:
- `find_last("abcabc", "a");` is `3` — the primary case, pin as the main
  regression test; contrast with `find("abcabc", "a");` on the same
  input returning `0` to prove this isn't accidentally aliased to `find`.
- `find_last("abcabc", "z");` is `-1` — substring not present.
- `find_last("hello", "");` is `5` — matches Python's `str.rfind`
  behavior for an empty needle (the length of the haystack, i.e. the
  rightmost valid insertion point), not an error.
- `find_last("", "");` is `0` — both empty, matches `str.rfind` again.
- `find_last("aaa", "a");` is `2` — the last of several overlapping
  single-character matches.
- `find_last(5, "a");` (a non-string first argument) raises
  `CinderRuntimeError` naming `find_last` and `number` in the message.
- `find_last("abc", 5);` (a non-string second argument) raises
  `CinderRuntimeError` naming `find_last` and `number` in the message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `find`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `find_last` added near `find` — leave that to the Architect's
next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
