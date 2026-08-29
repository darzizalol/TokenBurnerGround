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

## 1. Language: whole-value `as` binding in match list/map patterns

Build: a match list/map pattern destructures a subject into its parts
(`match ([1, 2]) { [a, b] => a + b, _ => 0 }`) but there is no way to
also bind the *whole* matched value alongside the destructured pieces —
today that forces either giving up destructuring (a bound-identifier
arm, `match (v) { whole => ... }`, binds the whole value but can't
destructure it) or re-indexing/re-slicing the subject inside the arm
body by hand. Add an optional trailing `as NAME` after a list or map
pattern (`match ([1, 2]) { [a, b] as whole => a + b + len(whole) }`,
`match ({"a": 1}) { {a} as whole => a + len(keys(whole)) }`) that binds
the entire subject to `NAME` in the arm's own scope, alongside whatever
names the pattern itself destructures. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ([1, 2]) { [a, b] as whole => whole, _ => nil });'
# -> <eval>:1:24: expected '=>' after match pattern, found identifier 'as'
```

This needs a new reserved keyword, `as` — confirmed unused as an
identifier anywhere in `examples/*.cin` or `tests/*.py` today, so
reserving it is safe. Add it in three places:
1. `cinder/tokens.py`: a new `TokenType.AS = auto()` member (add next to
   `TokenType.IN`, search `IN = auto()`), and a `"as": TokenType.AS,`
   entry in the `KEYWORDS` dict (search `KEYWORDS = {`, add next to
   `"in": TokenType.IN,`). No `cinder/lexer.py` change is needed — it
   already looks up every identifier lexeme against `KEYWORDS` generically
   (search `KEYWORDS.get(lexeme, TokenType.IDENTIFIER)`).
2. `cinder/ast_nodes.py`: add one new trailing field to `MatchArm`
   (search `class MatchArm`), `whole_binding: "str | None" = None`,
   after the existing `map_rest` field. Being a defaulted trailing field,
   every existing positional `MatchArm(...)` construction site keeps
   working unchanged. Document it in the class docstring near the
   `list_pattern`/`map_pattern` explanation: `whole_binding` is `None`
   unless a list-pattern or map-pattern arm carries a trailing `as NAME`,
   in which case it holds `NAME` — the subject's whole value is bound to
   this name in the arm's own environment in addition to whatever the
   pattern itself destructures. Not valid on the wildcard/bound-identifier,
   literal, or range-pattern arm kinds (only `list_pattern`/`map_pattern`
   arms may carry it).
3. `cinder/parser.py`: add a small helper next to the other match-pattern
   helpers (search `def _match_list_pattern_rest_name`):
   ```python
   def _match_whole_binding(self) -> "str | None":
       if not self._check(TokenType.AS):
           return None
       self._advance()  # consume 'as'
       token = self._consume(TokenType.IDENTIFIER, "identifier after 'as' in match pattern")
       return token.lexeme
   ```
   Call it from `_match_arm` (search `def _match_arm`) right after each of
   the two pattern-parsing calls, before the existing
   `self._consume(TokenType.FAT_ARROW, ...)`:
   ```python
   if self._check(TokenType.LBRACKET):
       list_pattern, list_rest = self._match_list_pattern()
       whole_binding = self._match_whole_binding()
       self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
       body = self._ternary()
       return [MatchArm(None, body, None, list_pattern, None, list_rest, None, None, whole_binding)]
   if self._check(TokenType.LBRACE):
       map_pattern, map_rest = self._match_map_pattern()
       whole_binding = self._match_whole_binding()
       self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
       body = self._ternary()
       return [MatchArm(None, body, None, None, None, None, map_pattern, map_rest, whole_binding)]
   ```
   The other `_match_arm` branch (literal/wildcard/bound-identifier/range
   entries, search `entries = [self._match_pattern()]`) is untouched — `as`
   binding is scoped to list/map patterns only for this task, mirroring how
   rest capture and defaults were introduced list/map-first too.
4. `cinder/interpreter.py`: in `_evaluate_match` (search
   `def _evaluate_match`), after each pattern successfully matches and
   before evaluating the body, define the whole binding in `arm_env` if
   present:
   ```python
   if arm.list_pattern is not None:
       arm_env = Environment(env)
       if not self._match_list_entries(
           arm.list_pattern, arm.list_rest, subject, arm_env
       ):
           continue
       if arm.whole_binding is not None:
           arm_env.define(arm.whole_binding, subject)
       return self.evaluate(arm.body, arm_env)
   ```
   and the mirror-image insertion in the `arm.map_pattern is not None`
   branch, right before its own `return self.evaluate(arm.body, arm_env)`.

Acceptance criteria:
- `match ([1, 2]) { [a, b] as whole => whole, _ => nil };` evaluates to
  `[1, 2]` — the whole binding holds the original subject.
- `match ([1, 2]) { [a, b] as whole => a + b + len(whole), _ => 0 };` is
  `6` — destructured names (`a`, `b`) and the whole binding (`whole`) are
  both usable in the same body.
- `match ({"a": 1, "b": 2}) { {a, b} as whole => len(keys(whole)), _ => 0 };`
  is `2`.
- `as` composes with rest capture: `match ([1, 2, 3]) { [a, ...rest] as whole => len(whole) - len(rest), _ => 0 };`
  is `1`.
- `as` composes with defaults: `match ([1]) { [a, b = 0] as whole => len(whole), _ => -1 };`
  is `1` (the pattern still matches a shorter subject; `whole` is the
  actual — not the default-padded — subject).
- A non-matching subject still falls through without binding anything:
  `match (5) { [a, b] as whole => whole, _ => "no match" };` is
  `"no match"` (`5` is not a list, so the arm never runs and `whole`
  is never defined).
- `whole` does not leak outside the arm: `let whole = 1; match ([1, 2]) { [a, b] as whole => whole, _ => nil }; print(whole);`
  prints `1` — the arm's `as` binding lives only in the arm's own child
  scope, mirroring every other match-pattern binding's scoping.
- Omitting `as` still parses and behaves exactly as before (no
  regression to any existing list/map pattern test).
- A malformed binding raises a parse error with line/column, e.g.
  `match ([1, 2]) { [a, b] as 5 => a, _ => 0 };` raises `ParseError`
  matching `"identifier after 'as' in match pattern"`.
- Full test suite passes.

Likely files: `cinder/tokens.py` (new `TokenType.AS`, `KEYWORDS` entry),
`cinder/ast_nodes.py` (`MatchArm.whole_binding` field + docstring),
`cinder/parser.py` (`_match_whole_binding` helper, two call sites in
`_match_arm`), `cinder/interpreter.py` (`_evaluate_match`'s
`list_pattern`/`map_pattern` branches), `tests/test_parser.py` (extend
`class TestMatchExpression`, search that name), `tests/test_interpreter.py`
(extend `class TestMatchExpression`, search that name, for the
evaluation/scoping behavior above). Once merged, `README.md`'s match
list/map pattern bullets need an `as`-binding mention, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Language: lexicographic comparison operators for lists (`[1, 2] < [1, 3]`)

Build: `<`/`<=`/`>`/`>=` already work element-by-element for strings via
Python's own string ordering (`_compare`, `cinder/interpreter.py`, search
`def _compare`), but lists are explicitly excluded from the same
`comparable` check — even though Python's own list ordering is exactly
the lexicographic comparison a scripting-language user would expect.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2] < [1, 3]);'
# -> <eval>:1:15: unsupported operand types for comparison: list and list
```
This gap also affects the language's *chained* comparison syntax
(`a < b < c`, `_evaluate_chained_comparison` in the same file, search
`def _evaluate_chained_comparison`), since it calls the exact same
`_compare` method per pair — fixing `_compare` fixes both `[1, 2] <
[1, 3]` and `[1, 2] < [1, 3] < [2, 0]` in one change, no separate
chained-comparison code path to touch.

Extend `_compare`'s `comparable` check (search `def _compare`) to admit
list/list, and wrap the actual comparison in a `try`/`except TypeError`
so a per-element type mismatch inside two otherwise-comparable lists
raises a clean `CinderRuntimeError` instead of leaking a raw Python
`TypeError` — the one case Python's native list ordering doesn't handle
for free, since Python's own `<` between two lists recurses
element-by-element using each element's own `__lt__`, and that recursion
can hit two elements of incompatible type (e.g. a `str` and an `int`)
partway through, well past the point where the outer `comparable` check
already gave the go-ahead on the two *lists* themselves:
```python
    def _compare(self, operator: Token, left, right, op: TokenType) -> bool:
        comparable = (
            (_is_number(left) and _is_number(right))
            or (isinstance(left, str) and isinstance(right, str))
            or (isinstance(left, list) and isinstance(right, list))
        )
        if not comparable:
            raise CinderRuntimeError(
                f"unsupported operand types for comparison: "
                f"{type_name(left)} and {type_name(right)}",
                operator.line,
                operator.column,
            )
        try:
            if op == TokenType.LT:
                return left < right
            if op == TokenType.LTEQ:
                return left <= right
            if op == TokenType.GT:
                return left > right
            return left >= right
        except TypeError:
            raise CinderRuntimeError(
                "unsupported operand types for comparison: list elements are "
                "not comparable",
                operator.line,
                operator.column,
            ) from None
```
Comparison follows the exact same rule Python (and this file's own
existing string comparison) already uses: element-by-element from the
front, first differing pair decides the result, and a list that is a
strict prefix of the other counts as the lesser one (`[1, 2] < [1, 2,
3]` is `true`, mirroring `"ab" < "abc"`). No parser or AST change is
needed — `<`/`<=`/`>`/`>=` already parse against any two operand
expressions; only `_compare`'s runtime type-admission rule changes.

Acceptance criteria:
- `[1, 2] < [1, 3];` is `true`, `[1, 3] < [1, 2];` is `false` — first
  differing element decides.
- `[1, 2] < [1, 2, 3];` is `true`, `[1, 2, 3] < [1, 2];` is `false` — a
  strict prefix is lesser, mirroring string-prefix ordering.
- `[] < [1];` is `true`; `[] < [];` is `false` (equal, not strictly
  less) — same edge case as `"" < "x"` and `"" < "";`.
- `[1, 2] <= [1, 2];` is `true`, `[1, 2] >= [1, 2];` is `true` — the
  equal-length equal-elements case for the inclusive operators.
- `["a", "b"] < ["a", "c"];` is `true` — nested string elements compare
  via their own existing string ordering, not just numbers.
- `[[1, 2]] < [[1, 3]];` is `true` — a list-of-lists recurses through
  the same rule at the nested level too (this falls out of Python's own
  native list comparison for free, no extra recursion code needed).
- `[1, "a"] < [1, 2];` raises `CinderRuntimeError` (mismatched element
  types partway through the comparison — `1 == 1` at index 0, then
  `"a"` vs `2` at index 1 can't be ordered) rather than a raw Python
  `TypeError`.
- `1 < [1, 2];` still raises `CinderRuntimeError` exactly as before
  (mismatched *outer* types, unchanged existing behavior — a number is
  still never comparable to a list).
- Chained comparisons compose for free: `[1] < [2] < [3];` is `true`,
  `[3] < [2] < [1];` is `false` (short-circuits on the first failing
  pair, same as every other chained comparison) — via
  `_evaluate_chained_comparison`, which calls the same `_compare` this
  task changes.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_compare`, search `def
_compare`), `tests/test_interpreter.py` (extend `class TestComparisons`,
search that name, with the list-ordering and mismatched-element cases
above, and `class TestChainedComparisons`, search that name, with the
list chained-comparison case). No `cinder/parser.py` or
`cinder/ast_nodes.py` change needed. Once merged, `README.md`'s
`Operators` bullet needs a mention that list ordering is now supported
(currently silent on list comparison entirely), and `PROJECT.md`'s
"Current frontier" bullet needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_disarium` — digit-position-power sum test

Build: `is_armstrong` (`cinder/builtins.py`, search `def _is_armstrong`)
tests whether a number equals the sum of its own digits each raised to
the *same* fixed exponent (the digit count) — `153 = 1^3 + 5^3 + 3^3`.
A Disarium number is the closely related but distinct variant where
each digit is raised to its own *positional* exponent (1-indexed from
the left) instead of one shared exponent — `89 = 8^1 + 9^2` and
`135 = 1^1 + 3^2 + 5^3` are both Disarium numbers, but neither is an
Armstrong number (`1^3+3^3+5^3=153≠135`) and `153` is Armstrong but not
Disarium (`1^1+5^2+3^3=1+25+27=53≠153`) — the two predicates disagree
on both directions, so this is a genuinely separate check, not a
rename. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_disarium(89));'
# -> <eval>:1:11: undefined name 'is_disarium'
```

Add to `cinder/builtins.py`, registered directly after `_is_armstrong`
(search `def _is_armstrong`, immediately before `def
_is_strong_number`) — keeps the digit-power-sum predicates together:
```python
def _is_disarium(arguments: list, line: int, column: int) -> object:
    _require_arity("is_disarium", arguments, 1, line, column)
    value = _require_int("is_disarium", arguments[0], line, column)
    if value < 0:
        return False
    digits = str(value)
    return (
        sum(int(digit) ** position for position, digit in enumerate(digits, start=1))
        == value
    )
```
This mirrors `_is_armstrong`'s own shape exactly (same negative-input
`return False` convention — no domain error, matching how
`is_armstrong`/`is_strong_number`/`is_harshad` all treat negative input
as simply "not a match" rather than an error — same `str(value)` digit
walk), just swapping the fixed `power = len(digits)` exponent for
`enumerate(..., start=1)`'s per-digit positional exponent. Also
register the new dict entry (search `"is_armstrong": _is_armstrong,`,
add `"is_disarium": _is_disarium,` directly after it, before
`"is_strong_number": _is_strong_number,`).

Acceptance criteria:
- `is_disarium(89);` and `is_disarium(135);` are `true` — the two
  smallest multi-digit Disarium numbers.
- `is_disarium(1);` through `is_disarium(9);` are all `true` — every
  single digit trivially satisfies `d^1 == d`.
- `is_disarium(153);` is `false` — the canonical Armstrong number is
  not Disarium (`1^1 + 5^2 + 3^3 = 53`).
- `is_disarium(175);` and `is_disarium(518);` are `true` — further
  known Disarium numbers (`1^1+7^2+5^3=175`, `5^1+1^2+8^3=518`).
- `is_disarium(10);` is `false` (`1^1 + 0^2 = 1 != 10`).
- `is_disarium(-89);` is `false` — negative input is simply not a
  match, no domain error (mirrors `is_armstrong`'s own convention).
- `is_disarium(1.5);` raises `CinderRuntimeError` matching
  `"is_disarium() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_armstrong`, search for the current line number), `tests/test_builtins.py`
(model on `class TestIsArmstrong`, search that name, for the
true/false/negative/type-error test shapes). Once merged, `README.md`'s
Builtins bullet needs `is_disarium` added near `is_armstrong`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `nth_kaprekar` — the k-th Kaprekar number by position

Build: `is_kaprekar` (`cinder/builtins.py`, search `def _is_kaprekar`)
tests membership by squaring the candidate and checking whether some
split of the square's digits sums back to the candidate (`45^2 = 2025`,
`20 + 25 = 45`), but has no value-returning `nth_*` counterpart the way
the prime and figurate-number clusters do (`nth_prime`/`is_prime`,
`nth_pronic`/`is_pronic`, etc.) — Kaprekar numbers have no closed form,
so this follows `nth_prime`'s own shape (search `def _nth_prime`): a
sequential candidate scan with a `count`/`candidate` loop. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(nth_kaprekar(5));'
# -> <eval>:1:7: undefined name 'nth_kaprekar'
```

**Performance note:** Kaprekar numbers grow much faster than the
abundant/semiprime/pronic clusters' own `nth_*` builtins — the 30th is
already `318682`, more than 1000x the 10th (`2728`) — and unlike those
clusters, the usual `k <= 50` cross-check convention is too slow here:
a fresh scan for every `k` from `1` to `50` takes several seconds
because most of the cost concentrates in the last few, largest `k`
values. Cap acceptance criteria and the cross-check test at `k = 20`
instead (`nth_kaprekar(20)` is `38962`, still a fast scan) — this
mirrors why the `nth_repdigit` task above stayed inside `k = 50` rather
than extending further: stay inside the range where the cross-check is
actually cheap to run, and here that range is narrower still.

Add to `cinder/builtins.py`, registered directly after `_is_kaprekar`
(search `def _is_kaprekar`, immediately before `def _is_harshad`) —
keeps the Kaprekar pair together, mirroring how `is_catalan` sits
directly after `nth_catalan`:
```python
def _nth_kaprekar(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_kaprekar", arguments, 1, line, column)
    value = _require_int("nth_kaprekar", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_kaprekar() requires a positive integer, domain error", line, column
        )

    def _is_kaprekar_candidate(candidate: int) -> bool:
        square = candidate * candidate
        digits = str(square)
        for split in range(1, len(digits) + 1):
            right = square % (10 ** split)
            left = square // (10 ** split)
            if right != 0 and left + right == candidate:
                return True
        return False

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_kaprekar_candidate(candidate):
            count += 1
    return candidate
```
This mirrors `_nth_abundant`'s/`_nth_repdigit`'s own `count`/`candidate`
scanning loop exactly, just swapping in `_is_kaprekar`'s own
split-and-sum check as a local nested helper (reimplemented locally,
matching how `is_twin_prime`/`nth_happy_number` reimplement their
predicate locally rather than sharing a module-level helper — this
file's existing convention for small local predicates). Also register
the new dict entry (search `"is_kaprekar": _is_kaprekar,`, add
`"nth_kaprekar": _nth_kaprekar,` directly after it, before
`"is_harshad": _is_harshad,`).

Acceptance criteria:
- `nth_kaprekar(1);` through `nth_kaprekar(10);` are `1`, `9`, `45`,
  `55`, `99`, `297`, `703`, `999`, `2223`, `2728` — the first ten
  Kaprekar numbers by position.
- `nth_kaprekar(15);` is `7272`.
- `nth_kaprekar(17);` is `9999`.
- `nth_kaprekar(20);` is `38962`.
- `is_kaprekar(nth_kaprekar(k));` is `true` for every `k` from `1` to
  `20` — cross-check against the existing `is_kaprekar` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s
  own shape. Do not raise this bound past `20` (see the performance
  note above).
- `nth_kaprekar(0);` and `nth_kaprekar(-1);` raise `CinderRuntimeError`
  matching `"nth_kaprekar() requires a positive integer, domain error"`.
- `nth_kaprekar(1.5);` raises `CinderRuntimeError` matching
  `"nth_kaprekar() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_kaprekar`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthOctagonal`, search that name, for the
positive/domain/type-error/cross-check test shapes, and the existing
`is_kaprekar` test class for the split-and-sum behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_kaprekar` added near
`is_kaprekar`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

---

## 5. Language: `else` clause on `while` loops (Python-style loop-`else`)

Build: `while` loops have no way to distinguish "the loop ran to normal
completion" from "the loop was cut short by `break`" without a manual
sentinel flag (`let broke = false; while (...) { if (...) { broke = true;
break; } } if (!broke) { ... }`). Python solves this with a loop-attached
`else` clause that runs exactly when the loop's condition becomes false
without an intervening `break` (including the zero-iteration case where
the condition was already false). Cinder already reuses the `else` keyword
for `if`/`else` (`TokenType.ELSE`, `cinder/tokens.py`) but a `while`
statement's own parse never looks for a trailing `else`. Verify the gap:
```sh
python3 -m cinder.cli eval 'let i = 0; while (i < 3) { i = i + 1; } else { print("done"); }'
# -> <eval>:1:41: expected an expression, found 'else'
```
This task scopes the feature to plain `while` loops only — not `do`-`while`
(no Python equivalent; the always-run-once semantics make "did it break"
ambiguous with "ran zero times" in a different way), not the foreach
`for`-in loop, and not the C-style `for (init; cond; step)` loop. Those are
plausible natural follow-ups (mirroring how list patterns landed before map
patterns) but each has its own `_execute_for`/`_execute_for_c` evaluator
method and its own `ForStmt`/`ForCStmt` AST node, so bundling all four loop
kinds into one PR would roughly quadruple this task's diff for no added
insight — leave them to a future task if one gets proposed.

No new token is needed — `TokenType.ELSE` already exists and is already
looked up via `self._check(TokenType.ELSE)` in `_if_statement` (search
`def _if_statement`, `cinder/parser.py`). Three changes:

1. `cinder/ast_nodes.py`: add one new trailing field to `WhileStmt` (search
   `class WhileStmt`), `else_branch: "Stmt | None" = None`, after the
   existing `label` field. Being a defaulted trailing field, the one
   existing `WhileStmt(...)` construction site (`cinder/parser.py`,
   currently 5 positional arguments) keeps working once it's updated to
   pass a 6th. Add a short docstring to the class (it currently has none):
   `else_branch` is `None` unless the loop carries a trailing
   `else { ... }` clause; when present, it runs exactly once, when the
   loop's condition becomes false *without* an intervening `break` —
   including immediately, if the condition was already false on the first
   check — mirroring Python's `while`/`for`-`else`. `continue` does not
   skip it (only `break` does); an uncaught exception, `return`, or
   propagating labeled `break`/`continue` from the body also skips it,
   since control never reaches the check in that case.

2. `cinder/parser.py`, `_while_statement` (search `def _while_statement`):
   after the existing `body = self._statement()` / `self._loop_labels.pop()`
   pair, add the same `else`-lookahead `_if_statement` already does:
   ```python
   def _while_statement(self, label: "str | None" = None) -> Stmt:
       while_token = self._advance()
       self._consume(TokenType.LPAREN, "'(' after 'while'")
       condition = self._assignment()
       self._consume(TokenType.RPAREN, "')' after while condition")
       self._loop_labels.append(label)
       body = self._statement()
       self._loop_labels.pop()
       else_branch = None
       if self._check(TokenType.ELSE):
           self._advance()
           else_branch = self._statement()
       return WhileStmt(
           condition, body, while_token.line, while_token.column, label, else_branch
       )
   ```
   **Dangling-attachment note** (call this out in the PR body, it's the
   one subtle part of this task): because `_while_statement` now consumes
   a trailing `else` itself, a `while` loop that is itself the unbraced
   `then_branch` of an `if` — `if (cond) while (x) { a; } else { b; }` —
   changes which construct the `else` binds to. Today (before this
   change) `_while_statement` never looks past its own body, so the
   `else` token is left for `_if_statement`'s own lookahead to claim,
   and `b` runs only when `cond` is falsy. After this change,
   `_while_statement` claims the `else` first (it runs its own lookahead
   before returning control to the caller), so `b` becomes the *while
   loop's* else-clause instead, running whenever the `while` loop exits
   without `break` — regardless of `cond`. This is the same
   nearest-currently-open-construct precedent ordinary dangling
   `if`/`else` already resolves by (an unbraced nested `if` without its
   own `else` "steals" a following `else` from an outer construct); it's
   a deliberate, if subtle, behavior change for that one specific
   unbraced combination, and needs a regression test locking in the new
   direction (acceptance criterion below) rather than being treated as
   an accidental regression.

3. `cinder/interpreter.py`, the `WhileStmt` branch inside `execute` (search
   `if isinstance(stmt, WhileStmt):`): track whether the loop exited via
   `break` and skip the run of `else_branch` when it did:
   ```python
   if isinstance(stmt, WhileStmt):
       broke = False
       while is_truthy(self.evaluate(stmt.condition, env)):
           try:
               self.execute(stmt.body, env)
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
       return
   ```
   `self.execute(stmt.else_branch, env)` runs in the same `env` the loop
   itself ran in (matching `IfStmt`'s own `self.execute(stmt.else_branch,
   env)`, not a fresh child scope) — if `else_branch` is a `Block`, the
   `Block` branch already creates its own child `Environment`, exactly
   like an ordinary `if`'s `else { ... }`.

Acceptance criteria:
- `let i = 0; while (i < 3) { i = i + 1; } else { print("done"); }`
  prints `done` — normal completion (condition goes false) runs the
  `else` clause.
- `let ran = false; while (true) { break; } else { ran = true; } print(ran);`
  is `false` — `break` skips the `else` clause entirely.
- `let ran = false; while (false) { } else { ran = true; } print(ran);`
  is `true` — a loop whose condition is false from the start (zero
  iterations) still counts as "completed without breaking".
- `let i = 0; let ran = false; while (i < 3) { i = i + 1; if (i == 1) { continue; } } else { ran = true; } print(ran);`
  is `true` — `continue` does not skip the `else` clause, only `break`
  does.
- `let ran = false; outer: while (true) { break outer; } else { ran = true; } print(ran);`
  is `false` — a labeled `break` targeting this loop still counts as a
  `break` for `else`-skipping purposes, same as an unlabeled one.
- Dangling-attachment regression test (see the parser note above):
  `if (true) while (false) { } else { print("attached-to-while"); }`
  prints `attached-to-while` — the `else` binds to the `while`, not the
  `if` (the `if`'s own condition is `true`, so if the `else` had instead
  bound to the `if`, nothing would print).
- Omitting `else` still parses and behaves exactly as before — no
  regression to any existing `while`/labeled-`while` test;
  `while (true) { break; }` with no trailing `else` still parses and
  runs fine (`else_branch` defaults to `None`).
- `do { ... } while (cond) else { ... };`, `for x in xs { ... } else { ... }`,
  and `for (;;) { ... } else { ... }` all still raise `ParseError` matching
  `"expected an expression, found 'else'"` — this task deliberately does
  not extend `else` support to `do`-`while`, foreach `for`, or C-style
  `for` (see the Build note above).
- A `while`-`else` clause composes with an enclosing function's `return`:
  a `return` inside the loop body still skips the `else` clause and
  propagates immediately, same as it already does for the loop body
  itself — `fn f() { while (true) { return 1; } else { return 2; } } print(f());`
  is `1`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`WhileStmt.else_branch` field +
docstring, search `class WhileStmt`), `cinder/parser.py`
(`_while_statement`, search `def _while_statement`), `cinder/interpreter.py`
(the `WhileStmt` branch in `execute`, search `if isinstance(stmt,
WhileStmt):`), `tests/test_parser.py` (extend `class TestDoWhileStatement`
around `test_plain_while_still_parses_unaffected`, search that name, plus
a new dangling-attachment parse test, and `class TestLabeledLoops`, search
that name, if a labeled-loop-else parse shape test is wanted),
`tests/test_interpreter.py` (extend `class TestWhileStatement`, search
that name, with the completion/break/continue/label/dangling-attachment
cases above). Once merged, `README.md`'s Control flow bullet needs a
`while`-`else` mention, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 6. Standard library: `is_smith_number` — digit-sum-of-n vs digit-sum-of-its-prime-factors test

Build: `prime_factors` (`cinder/builtins.py`, search `def _prime_factors`)
already lists an integer's prime factors with multiplicity, and
`is_harshad` already sums an integer's own digits for a divisibility
check, but nothing compares an integer's digit sum against the combined
digit sum of its prime factors — the defining property of a Smith
number (named after Harold Smith, whose phone number `4937775` happens
to have this property): a composite integer where `digit_sum(n) ==
sum(digit_sum(f) for f in prime_factors(n))`, e.g. `4 = 2 * 2`,
`digit_sum(4) = 4`, `digit_sum(2) + digit_sum(2) = 2 + 2 = 4`. Verify
the gap:
```sh
python3 -m cinder.cli eval 'print(is_smith_number(4));'
# -> <eval>:1:11: undefined name 'is_smith_number'
```

Primes are excluded by definition (a prime's only prime factor is
itself, so the digit sums trivially match every prime — the interesting
case is composites where factoring actually changes the digit sum), and
`1` and every non-positive integer are excluded too (neither prime nor
composite). This mirrors `is_composite`'s own domain (`value < 4` is an
automatic `False`, since `4` is the smallest composite), tightened
further by the primality check.

Add to `cinder/builtins.py`, registered directly after `_prime_factors`
(search `def _prime_factors`, immediately before `def _num_divisors`) —
keeps the two prime-factorization-based functions together:
```python
def _is_smith_number(arguments: list, line: int, column: int) -> object:
    _require_arity("is_smith_number", arguments, 1, line, column)
    value = _require_int("is_smith_number", arguments[0], line, column)
    if value < 2:
        return False
    for divisor in range(2, int(value ** 0.5) + 1):
        if value % divisor == 0:
            break
    else:
        return False  # prime, not composite
    factors = []
    remaining = value
    divisor = 2
    while divisor * divisor <= remaining:
        while remaining % divisor == 0:
            factors.append(divisor)
            remaining //= divisor
        divisor += 1
    if remaining > 1:
        factors.append(remaining)
    digit_total = sum(int(digit) for digit in str(value))
    factor_digit_total = sum(
        sum(int(digit) for digit in str(factor)) for factor in factors
    )
    return digit_total == factor_digit_total
```
The primality pre-check is reimplemented locally (the same `for
divisor in range(2, int(value ** 0.5) + 1)` / `else: return False`
shape `_is_prime` already uses) rather than calling `_is_prime`
directly, and the factorization loop is reimplemented locally too (the
same trial-division shape `_prime_factors` already uses) rather than
calling `_prime_factors` directly — matching how `_nth_semiprime`/
`_is_sphenic` already reimplement `_is_prime`-shaped and
factorization-shaped checks locally rather than sharing a module-level
helper, this file's existing convention for small local predicates
built from a bigger builtin's own logic. Also register the new dict
entry (search `"prime_factors": _prime_factors,`, add
`"is_smith_number": _is_smith_number,` directly after it, before
`"num_divisors": _num_divisors,`).

Acceptance criteria:
- `is_smith_number(4);`, `is_smith_number(22);`, `is_smith_number(27);`,
  `is_smith_number(58);`, `is_smith_number(85);`, `is_smith_number(94);`,
  `is_smith_number(121);` are all `true` — the first seven known Smith
  numbers.
- `is_smith_number(9);` is `false` (`digit_sum(9) = 9`, but `9 = 3 * 3`
  gives `digit_sum(3) + digit_sum(3) = 6`, and `9 != 6`) — a composite
  whose digit sums simply don't match.
- `is_smith_number(2);`, `is_smith_number(3);`, `is_smith_number(13);`
  are all `false` — primes are excluded by definition, even though
  their own digit sum trivially "matches" (a prime has exactly one
  prime factor: itself).
- `is_smith_number(1);`, `is_smith_number(0);`, `is_smith_number(-4);`
  are all `false` — neither prime nor composite.
- `is_smith_number(1.5);` raises `CinderRuntimeError` matching
  `"is_smith_number() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`prime_factors`, search for the current line number), `tests/test_builtins.py`
(extend near `class TestPrimeFactors`, search that name, for the
true/false/prime-exclusion/domain/type-error test shapes above). Once
merged, `README.md`'s Builtins bullet needs `is_smith_number` added near
`prime_factors`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both
to the Architect's next grooming pass, not this task.

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
