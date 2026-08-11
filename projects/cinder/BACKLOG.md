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

## 1. Standard library: `divisors` — list an integer's positive divisors [claimed 2026-08-11T14:48:18Z]

Build: add `divisors(n)` to `cinder/builtins.py`, registered right
after `_is_deficient` (search for `def _is_deficient`) — it's the
natural value-returning sibling of the `is_perfect_number`/
`is_abundant`/`is_deficient` cluster, all three of which already do
their own trial-division-to-`sqrt(n)` walk over divisor pairs and
discard the individual divisors, keeping only their sum. This is a
fresh breadth task queued after the depth work that just landed
(list/map-destructuring function parameters) per `PROJECT.md`'s
breadth-vs-depth policy.

`divisors(n)` returns the sorted list of every positive integer that
evenly divides `n`, including `1` and `n` itself. Mirror
`_is_perfect_number`'s exact trial-division shape (loop `divisor` from
`2` to `math.isqrt(value)` inclusive, and for each exact divisor
collect both `divisor` and its complement `value // divisor` when they
differ) but collect into a list instead of summing, seed the list with
`1` the same way `_is_perfect_number` seeds `total = 1` (skip that seed
when `value == 1`, since `1`'s only divisor is itself, not `1` twice),
and `sorted(...)` the result before returning — the trial-division walk
does not yield divisors in sorted order (it finds small/large pairs
together), so sorting is required, not cosmetic.

Model the arity/type-checking on `_is_perfect_number`'s structure: reuse
`_require_arity("divisors", arguments, 1, line, column)` and
`_require_int("divisors", arguments[0], line, column)`. Unlike
`is_perfect_number`/`is_abundant`/`is_deficient` (which answer `false`
for `value < 1` or `value < 2`), `n < 1` has no valid divisor list —
`0` is divisible by everything and negative numbers don't fit the
"positive divisors" contract — so raise a domain error instead of
returning an empty list, mirroring `_log`'s own type-vs-domain-error
split (search `def _log`): a non-int argument is a type error via
`_require_int`, but `n < 1` is a separate domain error raised
afterward, `CinderRuntimeError` matching `"divisors() requires a
positive integer, domain error"`.

Acceptance criteria:
- `divisors(6);` is `[1, 2, 3, 6]` — the textbook case.
- `divisors(1);` is `[1]` — the one-element edge case, no doubled `1`.
- `divisors(13);` is `[1, 13]` — a prime has exactly two divisors.
- `divisors(28);` is `[1, 2, 4, 7, 14, 28]` — a perfect number's
  divisors (excluding `28` itself sum to `28`, confirming this shares
  the same divisor set `is_perfect_number(28)` already validates as
  `true`).
- `divisors(100);` is `[1, 2, 4, 5, 10, 20, 25, 50, 100]` — a larger
  composite with several divisor pairs, confirming results come back
  sorted rather than in trial-division-discovery order.
- `divisors(0);` and `divisors(-6);` both raise `CinderRuntimeError`
  matching `"divisors() requires a positive integer, domain error"`.
- `divisors(3.0);` (float) raises `CinderRuntimeError` matching
  `"divisors() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `divisors(true);` (bool) raises `CinderRuntimeError` matching
  `"divisors() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_deficient`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `divisors` added near `is_perfect_number`/`is_abundant`/
`is_deficient`, and `PROJECT.md`'s roadmap paragraph needs it moved
from backlog to landed — leave both to the Architect's next grooming
pass, not this task.

---

## 2. Language: optional call chaining (`f?.(...)`)

Build: extend the existing safe-navigation family — `m?.key` (dot
property access), `obj?.[expr]` (bracket index access), both defined
in `cinder/ast_nodes.py`'s `OptionalIndex` and parsed via
`_finish_optional_dot` in `cinder/parser.py` (search both) — to cover
the one position they still don't: a *call*. Today `let f = nil;
f();` raises `CinderRuntimeError` `"nil is not callable"` (search
`is not callable` in `cinder/interpreter.py`'s `call_value`) with no
way to say "call this only if it isn't nil" short of a manual
`if f != nil { f(); }`. This is the depth task queued after task 1's
breadth work (`divisors`) per `PROJECT.md`'s breadth-vs-depth policy.

Like the rest of the `?.` family, this is single-level only — it does
not make an entire chain nil-safe, just the one call it's written on;
composing multiple `?.`s (`m?.greet?.("Al")`) is how a caller reaches
further, exactly as `m?.a?.b` already requires a `?.` at each level
rather than one `?.` propagating down the whole chain.

In `cinder/ast_nodes.py`: add an `OptionalCall` dataclass right after
`Call` (search `class Call`), same shape as `Call` — `callee: "Expr"`,
`arguments: list`, `line: int`, `column: int` — since it needs no
extra fields, just different evaluation semantics.

In `cinder/parser.py`: `_call()`'s postfix loop (search `def _call`)
dispatches `QUESTION_DOT` to `_finish_optional_dot`, which currently
only branches on `LBRACKET` (bracket index) vs. falling through to an
`IDENTIFIER` (dot property). Add a new `_finish_optional_call(self,
callee: Expr) -> Expr` method mirroring `_finish_call`'s body exactly
(consume `(`, parse zero or more comma-separated `_call_argument()`s,
each of which may itself be a `...expr` `Spread` — reuse
`_call_argument()` unchanged, don't reimplement spread parsing —
consume `)`, return `OptionalCall(callee, arguments, paren.line,
paren.column)` using the `(` token's own position, matching how
`_finish_call` positions `Call` on the paren rather than the callee).
Then in `_finish_optional_dot`, add a check for `self._check
(TokenType.LPAREN)` before the existing `LBRACKET` check, and when it
matches, `return self._finish_optional_call(obj)` instead of
falling through to bracket/property parsing.

In `cinder/interpreter.py`: add `_evaluate_optional_call(self, expr:
OptionalCall, env: Environment) -> object`, mirroring
`_evaluate_optional_index`'s short-circuit shape (evaluate `expr.
callee`; if it's `None`, return `None` immediately *without*
evaluating any argument expressions — same "don't touch the rest of
the expression once nil is seen" rule `_evaluate_optional_index`
already applies to its `index` operand) but for the non-nil path reuse
`_evaluate_call`'s existing argument-evaluation loop (handles plain
arguments and `Spread` arguments identically, raising the same
`"cannot spread {type_name(value)} in a function call"` error) rather
than duplicating it — extract that loop out of `_evaluate_call` into a
small shared helper (e.g. `_evaluate_call_arguments(self, arguments:
list, env: Environment) -> list`) that both `_evaluate_call` and
`_evaluate_optional_call` call, then finish with the same
`call_value(callee, arguments, expr.line, expr.column)` both paths
already use. Wire the dispatch: `evaluate` (search `isinstance(expr,
Call)`) needs a new `isinstance(expr, OptionalCall)` branch calling
the new method, placed near the existing `Call`/`OptionalIndex`
branches.

Acceptance criteria:
- `let f = nil; print(f?.());` prints `nil` — the motivating
  short-circuit case, no `"nil is not callable"` error.
- `fn add(a, b) { return a + b; } print(add?.(1, 2));` prints `3` — a
  non-nil callee calls through normally with arguments intact.
- `let m = {"greet": fn(name) { return "hi " + name; }}; print(m.greet
  ?.("Al"));` prints `hi Al` — composes with a plain (non-optional)
  `.` access on the callee side; only the call itself is optional here.
- `let m = nil; print(m?.greet?.("Al"));` prints `nil` — chains two
  `?.`s: `m?.greet` short-circuits to `nil` (existing single-level
  `OptionalIndex` behavior), then `nil?.("Al")` short-circuits the
  call too, since its callee evaluates to `nil`.
- `let calls = []; fn effect() { push(calls, 1); return 1; } let f =
  nil; f?.(effect()); print(len(calls));` prints `0` — argument
  expressions are not evaluated when the callee is `nil`, matching
  `OptionalIndex` not evaluating its `index` operand when `obj` is
  `nil`.
- `let f = nil; let args = [1, 2]; f?.(...args);` does not raise and
  the spread argument is never evaluated (same non-evaluation rule as
  the plain-argument case above).
- `let f = 5; f?.();` raises `CinderRuntimeError` matching `"int is
  not callable"` — only a `nil` callee short-circuits; any other
  non-callable value still raises exactly like plain `Call` already
  does, since `?.` guards against `nil`, not against "not a function."
- `f?.(` with no closing `)` raises a `ParseError`, matching plain
  `f(`'s own unterminated-argument-list behavior.
- Existing plain `Call` (`f()`, `f(a, b)`, spread arguments
  `f(...args)`) and existing `OptionalIndex` (`m?.key`,
  `obj?.[expr]`) are completely unaffected by the shared-helper
  extraction.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `OptionalCall`),
`cinder/parser.py` (`_finish_optional_dot`, new
`_finish_optional_call`), `cinder/interpreter.py` (`evaluate`
dispatch, new `_evaluate_optional_call`, extracted
`_evaluate_call_arguments` shared with `_evaluate_call`), `tests/
test_parser.py`, `tests/test_interpreter.py`. Once merged, `README.md`'s
safe-navigation bullet needs the call form mentioned, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `is_rotation` — string rotation predicate

Build: add `is_rotation(a, b)` to `cinder/builtins.py`, registered
right after `_is_anagram` (search for `def _is_anagram`) — it's a
natural sibling in the two-string predicate family alongside
`is_anagram`/`is_permutation`, one position more specific than
`is_anagram`'s "same multiset of characters" test. This is a fresh
breadth task queued after task 2's depth work (optional call chaining)
per `PROJECT.md`'s breadth-vs-depth policy.

A string `b` is a **rotation** of string `a` when `b` can be produced
by moving some prefix of `a` to its end (e.g. `"abcd"` rotated by two
positions gives `"cdab"`). This is stricter than `is_anagram`: two
strings can share the exact same character multiset without one being
an actual rotation of the other (e.g. `"abcd"`/`"acbd"` are anagrams
but not rotations).

Model the arity/type-checking on `_is_anagram`'s structure exactly:
`_require_arity("is_rotation", arguments, 2, line, column)`, then
check each argument is a `str` with its own position-specific error
message (mirror `_is_anagram`'s separate "first argument"/"second
argument" messages, don't collapse them into one). For the rotation
test itself, use the standard doubled-string trick rather than
hand-rolling a character-shift loop: two equal-length strings `a`/`b`
are rotations of each other iff `b in (a + a)` (empty strings are a
rotation of themselves — `"" in ("" + "")` is `True`, so no special
case needed there); unequal-length strings are never rotations of each
other, checked before the doubled-string test, not left to fall out of
it.

Acceptance criteria:
- `is_rotation("abcd", "cdab");` is `true` — the motivating case,
  rotated by two positions.
- `is_rotation("abcd", "abcd");` is `true` — a string is trivially a
  rotation of itself (zero-position rotation).
- `is_rotation("", "");` is `true` — both empty is a rotation.
- `is_rotation("aaaa", "aaaa");` is `true` — repeated-character strings
  don't confuse the doubled-string check.
- `is_rotation("abcd", "acbd");` is `false` — same character multiset
  (an anagram) but not an actual rotation, confirming this is stricter
  than `is_anagram`.
- `is_rotation("abc", "abcd");` is `false` — different lengths can
  never be rotations of each other.
- `is_rotation("abc", "cab");` is `true` and `is_rotation("cab",
  "abc");` is `true` — rotation is symmetric.
- `is_rotation(5, "ab");` raises `CinderRuntimeError` matching
  `"is_rotation() requires a string as its first argument, got int"`.
- `is_rotation("ab", 5);` raises `CinderRuntimeError` matching
  `"is_rotation() requires a string as its second argument, got int"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_anagram`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_rotation` added near `is_anagram`/`is_permutation`,
and `PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Language: map-destructuring loop variables in list/map comprehensions (`[k + v for {a, b} in list_of_maps]`)

Build: close the one corner the destructuring-loop-variable matrix
still leaves open. Plain `for`-loops already support both forms of
destructuring loop variable — the list pattern
(`for [k, v] in items(m) { ... }`) and, since the map-destructuring
`for`-loop task landed, the map pattern
(`for {a, b} in list_of_maps { ... }`) — and list/map comprehensions
already gained the list-pattern half
(`[k + v for [k, v] in items(m)]`, `{k: v for [k, v] in items(m)}`).
But `_list_comprehension`/`_map_comprehension` in `cinder/parser.py`
(search both) only ever check `self._check(TokenType.LBRACKET)`
before a comprehension's loop variable, never `TokenType.LBRACE` — so
today `[a + b for {a, b} in list_of_maps]` raises `ParseError`
`"expected loop variable after 'for', found '{'"` instead of
destructuring each map in `list_of_maps` by key. This is the depth task queued after
task 3's breadth work (`is_rotation`) per `PROJECT.md`'s breadth-vs-
depth policy.

This is pure plumbing — every helper it needs already exists and is
already shared across `let`, assignment-destructuring, and `for`-loops;
this task is purely about wiring comprehensions into that same set of
helpers, exactly like the map-destructuring `for`-loop task did for
plain `for`-loops.

In `cinder/ast_nodes.py`: `ListComprehension` and `MapComprehension`
(search both) currently carry `names: "list | None" = None` and
`rest: "str | None" = None` but no `is_map` field. Add
`is_map: bool = False` to both, mirroring `ForStmt`'s own field of the
same name (`ForStmt` already has exactly this three-field shape:
`names`, `rest`, `is_map`).

In `cinder/parser.py`: in `_list_comprehension`, the existing block

```python
if self._check(TokenType.LBRACKET):
    names, rest = self._destructure_list_pattern()
else:
    var_name = self._consume(TokenType.IDENTIFIER, "loop variable after 'for'").lexeme
```

gains an `elif self._check(TokenType.LBRACE):` branch between the two,
calling the existing `_destructure_map_pattern()` helper (the same one
`_for_statement` already calls) and setting a local `is_map = True`
(default `False`), mirroring `_for_statement`'s own three-way branch
exactly (search `_for_statement` for the reference shape — `LBRACKET`
→ list pattern, `LBRACE` → map pattern + `is_map = True`, else → plain
identifier). Thread `is_map` through to the returned
`ListComprehension(...)` call's keyword arguments alongside the
existing `names=names, rest=rest`. Apply the identical change to
`_map_comprehension` (same branch shape, same `is_map` threading into
the returned `MapComprehension(...)` call).

In `cinder/interpreter.py`: `_evaluate_list_comprehension` currently
does

```python
if expr.names is not None:
    self._bind_list_destructure(iter_env, expr.names, expr.rest, item, expr.line, expr.column)
else:
    iter_env.define(expr.var_name, item)
```

change the `if expr.names is not None:` branch to check `expr.is_map`
first: `if expr.is_map: self._bind_map_destructure(iter_env,
expr.names, item, expr.line, expr.column)` else (still under
`expr.names is not None`) keep the existing
`self._bind_list_destructure(...)` call unchanged, else (no pattern at
all) keep the existing `iter_env.define(expr.var_name, item)` — same
three-way shape `_execute_for` already uses for the equivalent
`for`-loop binding (search `_execute_for`, reuse its exact branch
order as the reference). Apply the identical change to
`_evaluate_map_comprehension` (same three-way branch, same helper
calls).

Acceptance criteria:
- `[a + b for {a, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}]];` is
  `[3, 7]` — the motivating list-comprehension case.
- `{a: b for {a, b} in [{"a": 1, "b": 2}, {"a": 3, "b": 4}]};` is
  `{1: 2, 3: 4}` — the motivating map-comprehension case.
- `[a for {a, b} in [{"a": 1, "b": 2}] if b > 1];` is `[1]` — the
  optional `if` filter still works with a map-pattern loop variable,
  same as it already does for the list-pattern and plain-identifier
  forms.
- `[a for {a} in [{"a": 1}, {"b": 2}]];` (a map missing the expected
  key `"a"`) raises the same `CinderRuntimeError` `_bind_map_destructure`
  already raises for `for {a} in [{"b": 2}] { ... }` and
  `let {a} = {"b": 2};` — not a silent skip or crash.
- `[a for {a} in [1, 2]];` (a non-map item where a map pattern was
  declared) raises the same `CinderRuntimeError`
  `_bind_map_destructure` already raises for a non-map value.
- Existing list-pattern comprehension destructuring
  (`[k + v for [k, v] in items(m)]`) and plain-identifier comprehension
  loop variables (`[x * 2 for x in xs]`) are completely unaffected.
- `for {a, b} in list_of_maps { ... }` (the plain-statement form) is
  completely unaffected — this task only touches comprehensions.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`ListComprehension`,
`MapComprehension`), `cinder/parser.py` (`_list_comprehension`,
`_map_comprehension`), `cinder/interpreter.py`
(`_evaluate_list_comprehension`, `_evaluate_map_comprehension`),
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged,
`README.md`'s comprehension bullets need the map-pattern form
mentioned, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 5. Standard library: `is_balanced` — balanced-brackets predicate

Build: add `is_balanced(s)` to `cinder/builtins.py`, registered right
after `_is_pangram` (search for `def _is_pangram`) — a string
predicate, but a different flavor than its neighbors: `is_anagram`/
`is_permutation`/`is_pangram`/`is_palindrome` are all direct
delegations to a multiset/reversal comparison, whereas this is the
project's first stack-based parsing predicate. This is a fresh breadth
task queued after task 4's depth work (map-destructuring loop
variables in comprehensions) per `PROJECT.md`'s breadth-vs-depth
policy, deliberately picked to diversify the string-predicate cluster
rather than add one more delegation-only member to it.

`is_balanced(s)` tests whether every bracket in `s` — the three pairs
`()`, `[]`, `{}` — is properly matched and nested; any other character
(letters, digits, whitespace, punctuation) is ignored entirely, it is
not a "does `s` contain only brackets" check. Implement with a single
left-to-right scan and a Python `list` used as a stack: on an opening
bracket (`(`, `[`, `{`), push it; on a closing bracket (`)`, `]`, `}`),
if the stack is empty or its top does not match the corresponding
opener, return `False` immediately; otherwise pop. After the scan,
the string is balanced iff the stack is empty (a `False` if anything
is still unclosed). A `dict` mapping each closer to its opener (e.g.
`{")": "(", "]": "[", "}": "{"}`) keeps the match check a single
lookup rather than a chain of `if`/`elif`s.

Model the arity/type-checking on `_is_pangram`'s structure: reuse
`_require_arity("is_balanced", arguments, 1, line, column)` and raise
`CinderRuntimeError` matching `"is_balanced() requires a string, got
{type}"` for a non-`str` argument (mirror `_is_pangram`'s own single-
argument type-check message shape, not `_is_anagram`'s two-argument
"first argument"/"second argument" phrasing — there's only one
argument here).

Acceptance criteria:
- `is_balanced("(a[b]{c})");` is `true` — nested, mixed bracket types,
  non-bracket characters ignored.
- `is_balanced("");` is `true` — the empty string has nothing
  unmatched.
- `is_balanced("no brackets here");` is `true` — a string with no
  bracket characters at all is trivially balanced.
- `is_balanced("([)]");` is `false` — both bracket types individually
  appear in matched pairs by count, but interleaved rather than
  properly nested, confirming this is a real nesting check, not a
  per-type count comparison.
- `is_balanced("(");` and `is_balanced(")");` are both `false` — an
  unclosed opener and an opener-less closer.
- `is_balanced("{[()]}");` is `true` — three levels of proper nesting.
- `is_balanced("(a[b)c]");` is `false` — a realistic-looking
  interleaving (crossed pairs), not just a toy adjacent-swap case.
- `is_balanced(5);` raises `CinderRuntimeError` matching
  `"is_balanced() requires a string, got int"`.
- `is_balanced(true);` raises `CinderRuntimeError` matching
  `"is_balanced() requires a string, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_pangram`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_balanced` added near `is_anagram`/`is_permutation`/
`is_pangram`, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
