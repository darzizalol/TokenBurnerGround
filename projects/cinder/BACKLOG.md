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

## 1. Language: `else` clause on `while` loops (Python-style loop-`else`)

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

## 2. Standard library: `is_smith_number` — digit-sum-of-n vs digit-sum-of-its-prime-factors test

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

## 3. Language: ordering comparison operators (`<`/`<=`/`>`/`>=`) for maps

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

## 4. Language: difference operator (`-`) for maps

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
