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

## 1. Language: trailing commas in list/map literals, call arguments, and function parameter lists [claimed 2026-08-17T18:04:43Z]

Build: the depth task after task 5's breadth work (`digit_product`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that single-quoted string literals landed via PR #259,
dropping the count to the 5-task floor. All four of `cinder/parser.py`'s
comma-separated-list parsers — `_list_literal`, `_map_literal`,
`_finish_call` (call arguments), and `_fn_param_list` (function
parameters) — share the identical shape: parse one element, then `while
self._check(TokenType.COMMA): self._advance(); <parse another element>`,
with no check that a comma might be the *last* thing before the closing
delimiter. A trailing comma — convenient when reordering elements or
diffing cleanly line-per-element, and already how every mainstream
scripting language (JS, Python, Rust) treats these four positions —
today hard-fails instead of being silently accepted. Verify the gap,
one failure per site:
```sh
python3 -m cinder.cli eval 'print([1, 2, 3,]);'
# -> ParseError: expected an expression, found ']'
python3 -m cinder.cli eval 'print({"a": 1, "b": 2,});'
# -> ParseError: expected an expression, found '}'
python3 -m cinder.cli eval 'fn f(a, b) { return a + b; } print(f(1, 2,));'
# -> ParseError: expected an expression, found ')'
python3 -m cinder.cli eval 'fn f(a, b,) { return a + b; } print(f(1, 2));'
# -> ParseError: expected parameter name, found ')'
```

**Parsing** (`cinder/parser.py`): in each of the four comma-loops, after
consuming the comma, check whether the very next token is that site's
closing delimiter and `break` instead of parsing another element — the
same "peek before committing to another element" shape, applied one
token later than usual. For `_list_literal`:
```python
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACKET):
                    break
                elements.append(self._list_element())
```
`_map_literal` takes the identical shape with `TokenType.RBRACE` and
`pairs.append(self._map_entry())`; `_finish_call` with
`TokenType.RPAREN` and `arguments.append(self._call_argument())`
(dropping the `seen_keyword` bookkeeping update for the loop iteration
that never happens — no other change to that function's keyword-arg
ordering check); `_fn_param_list` with `TokenType.RPAREN` and
`params.append(self._fn_param(seen_default))` inside its own
comma-loop. `_fn_param_list`'s rest-parameter branch needs no special
handling: a trailing comma after `...rest` (`fn f(a, ...rest,)`) hits
the same early `RPAREN` check and breaks cleanly before ever reaching
the existing "rest parameter must be the last parameter" guard, so it's
accepted — a comma with genuinely nothing meaningful after it, not a
second parameter smuggled in after the rest one.

Out of scope, deliberately: this task does **not** touch destructuring
patterns (`let [a, b,] = expr;`, `let {a, b,} = expr;`, `for [a, b,] in
...`, destructuring function parameters `fn f([a, b,]) { ... }`) or
list/map comprehension bodies — `_destructure_list_pattern`/
`_destructure_map_pattern` and the comprehension parsers are separate
call sites with their own comma-loops, not shared with the four covered
here, and folding them in would widen this beyond one focused session;
leave them as a candidate for a future, separately-scoped task if
still desired. Single-element trailing commas (`[1,]`, `{"a": 1,}`,
`f(1,)`, `fn f(a,) { ... }`) are in scope and must work the same as the
multi-element case — the `break` fires right after the one comma
regardless of how many elements preceded it.

Acceptance criteria:
- `print([1, 2, 3,]);` prints the list `[1, 2, 3]` — no longer a
  `ParseError`.
- `print([1,]);` prints `[1]` — single-element trailing comma.
- `print([]);` still parses as an empty list (unaffected — no comma at
  all in this case, confirms the empty-literal path wasn't touched).
- `print({"a": 1, "b": 2,});` prints the map `{"a": 1, "b": 2}`.
- `print({"a": 1,});` prints `{"a": 1}` — single-entry trailing comma.
- `print({});` still parses as an empty map (unaffected).
- `fn f(a, b) { return a + b; } print(f(1, 2,));` prints `3`.
- `fn f(a) { return a; } print(f(1,));` prints `1`.
- `fn f(a, b,) { return a + b; } print(f(1, 2));` prints `3` — trailing
  comma in the parameter list, not just the call.
- `fn f(a,) { return a; } print(f(1));` prints `1`.
- `fn f(a, ...rest,) { return rest; } print(f(1, 2, 3));` prints
  `[2, 3]` — trailing comma after a rest parameter is accepted.
- `fn f(a, ...rest, b) { return a; }` still raises `ParseError` matching
  `"rest parameter must be the last parameter"` — confirms a *real*
  parameter after the rest one is still rejected, only a bare trailing
  comma with nothing after it is now accepted.
- `[1, , 3];` (an empty slot between two commas, not a single trailing
  comma) still raises `ParseError` matching `"expected an expression,
  found ','"` — confirms this task only special-cases a comma
  immediately before the closing delimiter, not comma runs in general.
- Every pre-existing list/map-literal, call-argument, and
  function-parameter test continues to pass unmodified, including
  spread elements/arguments/rest parameters and keyword arguments
  without a trailing comma.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_list_literal`, `_map_literal`,
`_finish_call`, `_fn_param_list`), `tests/test_parser.py` (model on
`class TestCalls` and `class TestListsAndMaps`, search both). Once
merged, `README.md`'s Values/Calls-adjacent bullets need a mention that
trailing commas are accepted in these four positions, and `PROJECT.md`'s
roadmap paragraph needs this moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `is_evil` / `is_odious` — binary popcount-parity predicates

Build: the breadth task after task 5's depth work (trailing commas) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to 6
tasks now that `is_repdigit` has landed via PR #260, dropping the count to
the 5-task floor. Add `is_evil(n)`/`is_odious(n)` to `cinder/builtins.py`,
registered right after `is_power_of_two` (search for `def
_is_power_of_two`, immediately before `_is_palindrome_list`) —
`is_power_of_two` is currently the only builtin that reasons about a
number's binary representation rather than its decimal one, via the `n &
(n - 1) == 0` bit trick; evil/odious numbers are the natural next member
of that same "binary bit-trick" family, classifying every non-negative
integer by whether its binary representation has an even ("evil") or odd
("odious") count of `1` bits (its popcount) — together a complete two-way
partition of the non-negative integers, the same "every input lands in
exactly one bucket" shape `is_perfect_number`/`is_abundant`/`is_deficient`
already established for divisor sums. Verify the gap: `python3 -m
cinder.cli eval 'print(is_evil(3));'` currently raises
`CinderRuntimeError` `"undefined name 'is_evil'"` — no such builtin exists
yet.

```python
def _is_evil(arguments: list, line: int, column: int) -> object:
    _require_arity("is_evil", arguments, 1, line, column)
    value = _require_int("is_evil", arguments[0], line, column)
    if value < 0:
        raise CinderRuntimeError(
            "is_evil() requires a non-negative integer, domain error", line, column
        )
    return bin(value).count("1") % 2 == 0


def _is_odious(arguments: list, line: int, column: int) -> object:
    _require_arity("is_odious", arguments, 1, line, column)
    value = _require_int("is_odious", arguments[0], line, column)
    if value < 0:
        raise CinderRuntimeError(
            "is_odious() requires a non-negative integer, domain error", line, column
        )
    return bin(value).count("1") % 2 == 1
```

Model the arity/type-checking exactly on `is_power_of_two`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). Unlike
`is_power_of_two` (which answers `false` for non-positive input rather
than raising), negative input here raises a domain error instead —
popcount parity is only well-defined for a finite non-negative bit
pattern; Python's own two's-complement-style `bin(-5) == '-0b101'` would
silently count the `1`s in the magnitude only, producing a well-typed but
mathematically meaningless answer for a negative input rather than an
honest error, so this follows `divisors`'/`log()`'s "raise a domain error
rather than leak a wrong-looking result" convention instead of
`is_power_of_two`'s "false" one. `0` is a valid input (`bin(0) ==
'0b0'`, zero `1` bits, even, so `is_evil(0)` is `true`) — the trivial
base case, not a domain edge to guard against. Bundle both predicates in
this one task since each is a one-line delegation to the same
`bin(value).count("1") % 2` expression differing only in which parity it
accepts — matching how `is_int`/`is_float` and `is_subset`/`is_superset`
were each bundled as a single task earlier in this backlog's history,
rather than as two separate breadth tasks back to back (which the
breadth-vs-depth policy already treats as a signal to inject a depth
task instead).

Acceptance criteria:
- `is_evil(0);` is `true` — zero `1` bits, even.
- `is_evil(3);` is `true` — `0b11`, two `1` bits.
- `is_evil(5);` is `true` — `0b101`, two `1` bits.
- `is_evil(6);` is `true` — `0b110`, two `1` bits.
- `is_evil(1);` is `false` — `0b1`, one `1` bit (odd).
- `is_odious(1);` is `true`.
- `is_odious(2);` is `true` — `0b10`, one `1` bit.
- `is_odious(4);` is `true` — `0b100`, one `1` bit.
- `is_odious(3);` is `false`.
- For every integer `0` through `31`, `is_evil(n) != is_odious(n)` — the
  two predicates are exact complements over the same domain (test via a
  loop or an explicit list of both buckets).
- `is_evil(1024);` is `false` — `0b10000000000`, one `1` bit (odious).
- `is_evil(-1);` raises `CinderRuntimeError` matching `"is_evil()
  requires a non-negative integer, domain error"`.
- `is_odious(-4);` raises `CinderRuntimeError` matching `"is_odious()
  requires a non-negative integer, domain error"`.
- `is_evil(5.0);` raises `CinderRuntimeError` matching `"is_evil()
  requires an int, got float"` — the same message shape `_require_int`
  already produces elsewhere.
- `is_odious(true);` raises `CinderRuntimeError` matching `"is_odious()
  requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column, for both builtins.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register both near `is_power_of_two`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestIsPowerOfTwo` test
class, search `class TestIsPowerOfTwo`). Once merged, `README.md`'s
Builtins bullet needs `is_evil`/`is_odious` added near `is_power_of_two`,
and `PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 3. Language: list concatenation via `+`, closing the gap between the existing `concat()` builtin and infix syntax

Build: the depth task after task 5's breadth work (`is_evil`/`is_odious`)
per `PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back
to 6 tasks now that scientific notation for float literals has landed
via PR #261, dropping the count to the 5-task floor. `cinder/
interpreter.py`'s `_apply_binary_operator` already special-cases `+` for
two shapes — `_is_number(left) and _is_number(right)` and `isinstance(
left, str) and isinstance(right, str)` — falling through to an
"unsupported operand types" error for everything else, including two
lists. Meanwhile `*` already treats `list * int`/`int * list` as
repetition (`_repeat_op`, right above `_numeric_op` in the same file),
so lists already participate in one infix arithmetic operator; `+` is
the one still missing, even though the `concat()` builtin already does
exactly this as a function call (`cinder/builtins.py`, search `def
_concat`) — the same "builtin already exists, infix syntax doesn't"
gap `**` closed for `pow()`, and pipe closed for chained calls. Verify
the gap:
```sh
python3 -m cinder.cli eval 'print([1, 2] + [3, 4]);'
# -> CinderRuntimeError: unsupported operand types for '+': list and list
python3 -m cinder.cli eval 'print(concat([1, 2], [3, 4]));'
# -> [1, 2, 3, 4] -- the exact same result, only reachable today via the builtin
```

In `_apply_binary_operator`'s `TokenType.PLUS` branch (`cinder/
interpreter.py`, right after the existing `isinstance(left, str) and
isinstance(right, str)` check and before the final `raise`), add one
more branch:
```python
            if isinstance(left, list) and isinstance(right, list):
                return left + right
```
Python's own list `+` already builds a fresh list without mutating
either operand — the same non-mutating convention `_repeat_op` already
established for `list * int` (see `test_list_repetition_does_not_mutate_
input` in `tests/test_interpreter.py`), so no extra copying logic is
needed. Mixed-type operands (`[1, 2] + "a"`, `[1, 2] + 3`, `[1, 2] +
{"a": 1}`) must keep raising the existing "unsupported operand types"
error — this task adds exactly one new accepted shape, list-plus-list,
not a general coercion. Because compound assignment desugars `+=` to an
ordinary `Binary` node with a `PLUS` operator and reuses
`_apply_binary_operator` (confirmed: `cinder/parser.py`'s
`_COMPOUND_ASSIGN_OPS` maps `PLUSEQ` to `PLUS`, no separate evaluation
path), `xs += [3, 4]` starts working the same moment this branch lands
— a zero-extra-code consequence of reusing the same dispatch, not a
second change to make. No parser or lexer changes at all: `+` is
already tokenized and already reaches `_apply_binary_operator` for
every operand type, this only widens what that function accepts.

Acceptance criteria:
- `[1, 2] + [3, 4];` is `[1, 2, 3, 4]`.
- `[] + [1];` is `[1]` and `[1] + [];` is `[1]` — an empty operand on
  either side.
- `[] + [];` is `[]`.
- `let a = [1, 2]; let b = [3, 4]; let c = a + b; print(a); print(b);
  print(c);` prints `[1, 2]`, `[3, 4]`, `[1, 2, 3, 4]` — neither
  original list is mutated, matching `_repeat_op`'s existing
  non-mutating convention.
- `let xs = [1, 2]; xs += [3, 4]; print(xs);` prints `[1, 2, 3, 4]` —
  `+=` on a list works for free via the shared `Binary`/`PLUS`
  desugaring, no separate code path.
- `let xs = [1]; xs = xs + [2] + [3]; print(xs);` is `[1, 2, 3]` — `+`
  stays left-associative for lists, same as it already is for numbers
  and strings.
- `[1, 2] + "a";` still raises `CinderRuntimeError` matching
  `"unsupported operand types for '+': list and string"`.
- `[1, 2] + 3;` still raises the same error shape, `"list and int"` —
  confirms this doesn't get swept into `*`'s repetition behavior.
- `[1, 2] + {"a": 1};` still raises the same error shape, `"list and
  map"`.
- `1 + 2;` is still `3` and `"a" + "b";` is still `"ab"` — the two
  existing `+` shapes are unaffected by the new branch.
- Full test suite passes.

Likely files: `cinder/interpreter.py` (`_apply_binary_operator`'s
`TokenType.PLUS` branch), `tests/test_interpreter.py` (model the new
list-plus-list cases on the existing `TestRepetition` class, which
covers `*`'s analogous list special-casing — search `class
TestRepetition`; add the mixed-type-still-raises cases near the
existing `+` error-shape assertions, search `TestArithmetic`),
`tests/test_errors.py` (existing `"unsupported operand types for
'+'"` assertions there are int/string cases and stay unmodified — no
new error-message assertions needed there since this task doesn't
change any error message, only adds one non-error branch). Once
merged, `README.md`'s Operators bullet needs a mention that `+` also
concatenates two lists (non-mutating, same as `concat()`), alongside
the existing `*` repetition mention, and `PROJECT.md`'s roadmap
paragraph needs this moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `harmonic_mean` — the third Pythagorean mean, completing arithmetic/geometric/harmonic

Build: the breadth task after task 5's depth work (list concatenation
via `+`) per `PROJECT.md`'s breadth-vs-depth policy, restocking the
backlog back to 6 tasks now that `geometric_mean` has landed via
PR #262, dropping the count to the 5-task floor. Add `harmonic_mean`
to `cinder/builtins.py`, registered right after `geometric_mean`
(search for `def _geometric_mean`, immediately before `_median`) — the
statistics cluster (`mean`, `median`, `variance`, `std_dev`, `mode`)
grew a second "kind of average" when `geometric_mean` landed; the
classical Pythagorean means come in threes (arithmetic, geometric,
harmonic), and `harmonic_mean` is the one still missing. Verify the
gap: `python3 -m cinder.cli eval 'print(harmonic_mean([1, 2, 4]));'`
currently raises `CinderRuntimeError` `"undefined name
'harmonic_mean'"` — no such builtin exists yet.

```python
def _harmonic_mean(arguments: list, line: int, column: int) -> object:
    _require_arity("harmonic_mean", arguments, 1, line, column)
    value = arguments[0]
    if not isinstance(value, list):
        raise CinderRuntimeError(
            f"harmonic_mean() requires a list, got {type_name(value)}", line, column
        )
    if not value:
        raise CinderRuntimeError("harmonic_mean() requires a non-empty list", line, column)
    for element in value:
        if not _is_numeric(element):
            raise CinderRuntimeError(
                f"harmonic_mean() requires a list of numbers, got {type_name(element)}", line, column
            )
        if element <= 0:
            raise CinderRuntimeError(
                "harmonic_mean() requires all elements to be positive", line, column
            )
    reciprocal_sum = 0
    for element in value:
        reciprocal_sum = reciprocal_sum + 1 / element
    return len(value) / reciprocal_sum
```

Model this directly on `_geometric_mean`'s own structure: same
`isinstance(value, list)` check, same non-empty check, same per-element
`_is_numeric` check followed by the same strictly-positive domain
check (checked only after confirming an element is numeric, so a
non-numeric element always reports first, exactly as `geometric_mean`
already does) — copy that validation loop verbatim rather than
inventing a new shape for it. The one substantive difference is the
final computation: `geometric_mean` multiplies elements then takes an
nth root, `harmonic_mean` sums reciprocals then divides `len(value)` by
that sum. Positivity is required for the same reason `geometric_mean`
requires it, plus one more: a zero element makes the reciprocal sum
undefined (division by zero on `1 / element`), and a negative element
would make the result not comparable to its arithmetic/geometric
siblings under the AM-GM-HM inequality (`harmonic_mean <=
geometric_mean <= mean` for any list of positive numbers) — so this
follows the exact same "raise a domain error rather than leak a
`ZeroDivisionError` or a sign-confused result" convention
`geometric_mean` already established, not a new decision. A
single-element list is trivially its own harmonic mean (the loop runs
once, `len(value) / (1 / value[0])` reduces to `value[0]`), the same
trivial-degenerate-case convention `mean`/`geometric_mean` already
establish.

Acceptance criteria:
- `harmonic_mean([1]);` is `1` — single-element list, trivially itself.
- `harmonic_mean([2, 2, 2, 2]);` is `2` — a constant list's harmonic
  mean equals the constant, same as `mean`/`geometric_mean` on a
  constant list.
- `harmonic_mean([1, 4]);` is `1.6` — matches the classical two-element
  identity `2ab / (a + b)` (`2 * 1 * 4 / (1 + 4) == 1.6`), a useful
  cross-check independent of the general `n / sum(1/x)` formula.
- `harmonic_mean([1, 2, 4]);` is approximately `1.7142857142857142`
  (`3 / (1 + 0.5 + 0.25)`).
- For `[1, 2, 4]`, `harmonic_mean(...) <= geometric_mean(...) <=
  mean(...)` all hold (`1.714... <= 2.0 <= 2.333...`) — the AM-GM-HM
  inequality, confirming the three statistics-cluster "averages" are
  internally consistent with each other, not just individually correct.
- `harmonic_mean([]);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires a non-empty list"`.
- `harmonic_mean([1, "a"]);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires a list of numbers, got string"`.
- `harmonic_mean([1, 0]);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires all elements to be positive"` — zero
  excluded (undefined via division by zero), not silently treated as
  infinite or skipped.
- `harmonic_mean([1, -2]);` raises the same domain-error message —
  negative excluded, same convention as `geometric_mean`.
- `harmonic_mean(5);` raises `CinderRuntimeError` matching
  `"harmonic_mean() requires a list, got int"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `geometric_mean`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestGeometricMean` test
class, search `class TestGeometricMean`). Once merged, `README.md`'s
Builtins bullet needs `harmonic_mean` added near `mean`/
`geometric_mean`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s roadmap paragraph needs this moved from backlog to
landed — leave all three to the Architect's next grooming pass, not
this task.

---

## 5. Language: trailing commas in destructuring patterns

Build: the depth task after task 5's breadth work (`harmonic_mean`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that postfix `++`/`--` as a first-class assignment
expression has landed via PR #263, dropping the count to the 5-task
floor. Task 2 in this same backlog (trailing commas in list/map
literals, call arguments, and function parameter lists) deliberately
scoped out destructuring patterns and left them "as a candidate for a
future, separately-scoped task if still desired" — this is that task.
`cinder/parser.py`'s `_destructure_list_pattern` (`let`/`for`/function
params/comprehension loop variables, list-pattern half),
`_destructure_map_pattern` (the same forms, map-pattern half), and
`_try_map_destructure_assign_statement` (the plain-assignment map form,
`{a, b} = expr;`) each have their own comma-loop, structurally
identical to the four sites task 2 already fixed, with the same gap: a
comma immediately before the closing delimiter is a hard `ParseError`
instead of being silently accepted. Verify the gap (task 2 must have
landed first, so `_list_literal`/`_map_literal` already accept trailing
commas — every failure below is specifically the destructuring-pattern
parsers, not the literal parsers):
```sh
python3 -m cinder.cli eval 'let [a, b,] = [1, 2]; print(a); print(b);'
# -> ParseError: expected identifier in destructuring pattern, found ']'
python3 -m cinder.cli eval 'let {a, b,} = {"a": 1, "b": 2}; print(a); print(b);'
# -> ParseError: expected identifier in destructuring pattern, found '}'
python3 -m cinder.cli eval 'let a = 0; let b = 0; {a, b,} = {"a": 1, "b": 2}; print(a); print(b);'
# -> ParseError: expected ';' after expression, found ',' (the trailing comma
#    inside `_try_map_destructure_assign_statement` breaks its own
#    try/except ParseError -> return None fallback, so `_brace_statement`
#    falls all the way through to `_block()`, which produces this
#    unrelated-looking error trying to parse `{a, b,} = ...` as statements)
python3 -m cinder.cli eval 'for [k, v,] in items({"a": 1}) { print(k); print(v); }'
# -> ParseError: expected identifier in destructuring pattern, found ']'
python3 -m cinder.cli eval 'fn f([a, b,]) { return a + b; } print(f([1, 2]));'
# -> ParseError: expected identifier in destructuring pattern, found ']'
python3 -m cinder.cli eval 'print([k for [k, v,] in items({"a": 1})]);'
# -> ParseError: expected identifier in destructuring pattern, found ']'
```
Note: the plain-assignment **list**-destructure form (`[a, b,] = expr;`)
is not one of the sites above and needs no change here — it parses its
pattern by first parsing an ordinary `ListLiteral` via `_list_literal`
(task 2's own site) and then validating its elements in
`_destructure_assign_pattern`, so once task 2 lands, `[a, b,] = expr;`
already works for free the same way `xs += [3, 4]` started working for
free once list-plus-`+` landed — nothing to touch in this task.

**Parsing**: in each of the three sites' comma-loops, after consuming
the comma, check whether the very next token is that site's closing
delimiter and `break` instead of trying to parse another pattern
element — the exact same shape task 2 used, placed *before* the
existing "a rest element must be last" check so a trailing comma right
after a rest element (`let [a, ...rest,] = expr;`,
`let {a, ...rest,} = expr;`) breaks cleanly instead of tripping that
check, mirroring how task 2 handled `fn f(a, ...rest,) { ... }` for
`_fn_param_list`. For `_destructure_list_pattern`:
```python
        while self._check(TokenType.COMMA):
            self._advance()
            if self._check(TokenType.RBRACKET):
                break
            if rest is not None:
                token = self._peek()
                raise ParseError(...)
            ...
```
`_destructure_map_pattern` takes the identical shape with
`TokenType.RBRACE`; `_try_map_destructure_assign_statement`'s own
inlined loop (inside its `try` block, alongside the `_RestNotLast`
marker-exception handling already there) gets the same `RBRACE` check
in the same position.

One real edge case to get right, not just a mechanical copy-paste: list
patterns already support a "hole" element (`let [a, , c] = expr;`,
`_destructure_list_pattern_entry` treats a `COMMA` appearing where an
element is expected as an empty slot rather than raising). Because the
new break check runs *before* the next element is parsed, a pattern
ending in "hole then trailing comma" (`let [a, ,] = [1, 2];` — two
commas, nothing named after the second one) is *not* caught by the
break on the first of those two commas (the token right after it is
another `COMMA`, not `]`), so it falls through to the existing hole
logic and registers as an ordinary hole, and *is* caught by the break
on the second comma (the token right after it is `]`). Net effect:
`let [a, ,] = [1, 2];` newly parses successfully as `a` bound to `1`
and a second, skipped position — the same result `let [a, ,] =` would
already give for a *middle* hole, just applied to the last position —
rather than continuing to raise `ParseError` as it does today. This is
an intentional, narrow behavior change (call it out in the PR body) and
is the correct reading: a hole is a hole regardless of position, and
the trailing comma after it is the same optional decoration the rest of
this task adds everywhere else. Map patterns have no hole concept, so
no equivalent case exists on that side.

Acceptance criteria:
- `let [a, b,] = [1, 2]; print(a); print(b);` prints `1` then `2` — no
  longer a `ParseError`.
- `let [a,] = [1]; print(a);` prints `1` — single-element trailing
  comma.
- `let [a, ...rest,] = [1, 2, 3]; print(a); print(rest);` prints `1`
  then `[2, 3]` — trailing comma right after a rest element is
  accepted, not treated as a second element following the rest one.
- `let [a, ...rest, b] = [1, 2, 3];` still raises `ParseError` matching
  `"rest element must be last in destructuring pattern"` — confirms a
  *real* element after the rest one is still rejected, only a bare
  trailing comma with nothing after it is now accepted.
- `let [a, ,] = [1, 2]; print(a);` prints `1` — the hole-then-trailing-
  comma edge case above, now accepted rather than raising.
- `let {a, b,} = {"a": 1, "b": 2}; print(a); print(b);` prints `1` then
  `2`.
- `let {a,} = {"a": 1}; print(a);` prints `1` — single-entry trailing
  comma.
- `let {a, ...rest,} = {"a": 1, "b": 2}; print(a); print(rest);` prints
  `1` then `{"b": 2}` — trailing comma right after a map rest element.
- `let a = 0; let b = 0; {a, b,} = {"a": 1, "b": 2}; print(a); print(b);`
  prints `1` then `2` — the plain-assignment map form.
- `for [k, v,] in items({"a": 1}) { print(k); print(v); }` prints `a`
  then `1`.
- `for {a, b,} in [{"a": 1, "b": 2}] { print(a); print(b); }` prints `1`
  then `2`.
- `fn f([a, b,]) { return a + b; } print(f([1, 2]));` prints `3`.
- `fn f({a, b,}) { return a + b; } print(f({"a": 1, "b": 2}));` prints
  `3`.
- `print([k for [k, v,] in items({"a": 1})]);` prints `["a"]`.
- `print([a for {a, b,} in [{"a": 1, "b": 2}]]);` prints `[1]`.
- `let [a, b,] = [1, 2]; print(a); print(b);` (the plain-list-assignment
  free-ride case from task 2) prints `1` then `2` — confirms it works
  without any change in this task.
- Every pre-existing destructuring test (defaults, holes, rest
  elements, renames, all five forms — `let`, plain assignment, `for`,
  function params, both comprehension loop-variable forms) continues to
  pass unmodified, without a trailing comma.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_list_pattern`,
`_destructure_map_pattern`, `_try_map_destructure_assign_statement`),
`tests/test_parser.py` and `tests/test_interpreter.py` (model on the
existing destructuring test classes — search `class TestDestructureLet`,
`class TestDestructureLetMap`, `class TestDestructureAssignMap`,
`class TestForDestructuring`, `class TestDestructuringParams`). Once
merged, `README.md`'s destructuring bullets don't strictly need a new
sentence (trailing commas are a silent parser acceptance, not a new
capability worth a separate callout, the same treatment task 2's
merge gave `README.md`), but `PROJECT.md`'s roadmap paragraph needs
this moved from backlog to landed — leave that to the Architect's next
grooming pass, not this task.

---

## 6. Standard library: `multiplicative_persistence` — the loop-driven counterpart to `digital_root`

Build: the breadth task after task 5's depth work (trailing commas in
destructuring patterns) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `digit_product` has
landed via PR #264, dropping the count to the 5-task floor. Add
`multiplicative_persistence(n)` to `cinder/builtins.py`, registered
right after `digit_product` (search for `def _digit_product`,
immediately before `_reverse_int`) — the number of times a number's own
decimal digits must be repeatedly multiplied together before the
result drops to a single digit, e.g. `39 -> 27 -> 14 -> 4` is three
multiplications, so `multiplicative_persistence(39)` is `3`. This is
the natural loop-driven counterpart to `digital_root`'s closed-form
*additive* reduction (`1 + (n - 1) % 9`): no closed form exists for the
multiplicative case, so this genuinely needs an iterative loop rather
than a formula — the first builtin in the digit-transform cluster that
does. Verify the gap: `python3 -m cinder.cli eval
'print(multiplicative_persistence(39));'` currently raises
`CinderRuntimeError` `"undefined name 'multiplicative_persistence'"` —
no such builtin exists yet.

```python
def _multiplicative_persistence(arguments: list, line: int, column: int) -> object:
    _require_arity("multiplicative_persistence", arguments, 1, line, column)
    value = _require_int("multiplicative_persistence", arguments[0], line, column)
    value = abs(value)
    steps = 0
    while value >= 10:
        product = 1
        for digit in str(value):
            product *= int(digit)
        value = product
        steps += 1
    return steps
```

Model the arity/type-checking on `digit_product`'s own structure:
`_require_arity`, then `_require_int`. Discard the sign via `abs()`
exactly once, up front — not re-derived every iteration, since the
running product is already non-negative once the first step completes
(matching `digit_sum`/`digit_product`'s own "discard sign once" shape,
just applied before a loop instead of before a single pass). Each
iteration's digit-multiply step inlines the same per-digit walk
`digit_product` itself uses rather than calling the `digit_product`
builtin directly — the established "inline rather than call the
dispatch-signature builtin" approach `is_emirp`/`is_amicable` already
take with `is_composite`/`reverse_int`/`_aliquot_sum`, needed here
because `digit_product`'s registered form takes the builtin-dispatch
`(arguments, line, column)` signature, not a raw `int`. Any `0` digit
inside a step collapses that step's product to `0`, which then
terminates the loop on the very next check (`0 < 10`) — the correct
behavior, not a case needing a guard, mirroring how `digit_product`
itself treats a `0` digit as collapsing the whole product rather than
as an error.

Acceptance criteria:
- `multiplicative_persistence(0);` is `0` — single digit, already
  terminated.
- `multiplicative_persistence(4);` is `0` — any single digit `0`-`9` is
  its own trivial base case.
- `multiplicative_persistence(10);` is `1` — `1 * 0 = 0`, one step (a
  `0` digit collapses the product immediately).
- `multiplicative_persistence(39);` is `3` — `39 -> 27 -> 14 -> 4`.
- `multiplicative_persistence(999);` is `4` — `999 -> 729 -> 126 -> 12
  -> 2`.
- `multiplicative_persistence(77);` is `4` — `77 -> 49 -> 36 -> 18 ->
  8`.
- `multiplicative_persistence(-39);` is `3` — same as `39`, sign
  discarded, matching `digit_sum`/`digit_product`'s own convention.
- `multiplicative_persistence(5.0);` raises `CinderRuntimeError`
  matching `"multiplicative_persistence() requires an int, got float"`
  — the same message shape `_require_int` already produces elsewhere.
- `multiplicative_persistence(true);` raises `CinderRuntimeError`
  matching `"multiplicative_persistence() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `digit_product`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `TestDigitProduct` test
class, search `class TestDigitProduct`). Once merged, `README.md`'s
Builtins bullet needs `multiplicative_persistence` added near
`digit_sum`/`digit_product`/`digital_root`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s roadmap paragraph needs this
moved from backlog to landed — leave all three to the Architect's next
grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
