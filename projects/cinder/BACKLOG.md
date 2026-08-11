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

## 1. Standard library: `is_emirp` — emirp predicate

Build: add `is_emirp(n)` to `cinder/builtins.py`, registered right after
`_is_composite` (search for `def _is_composite`) — it's the natural
third member of that prime-family cluster, alongside `is_prime`/
`is_composite`. This is a fresh breadth task queued after task 3's
depth work (map-destructuring `for`-loop variables) per `PROJECT.md`'s
breadth-vs-depth policy, continuing the same one-breadth-then-depth
alternation task 2 (`lerp`) got after task 1's comprehension-
destructuring depth work.

An **emirp** ("prime" spelled backwards) is a prime number whose
decimal-digit reversal is a *different* prime — palindromic primes
like `11` or `2` don't count, since reversing them gives the same
number back. `13` is the canonical example: it's prime, and its
reversal `31` is also prime and not equal to `13`.

Do not call `_is_prime`/`_reverse_int` directly — both take the
`(arguments, line, column)` builtin-dispatch signature, not a raw
`int`, so reuse isn't a straight function call. Instead inline the same
two techniques already used elsewhere: `_is_composite`'s own
trial-division-to-`sqrt(n)` loop (copy its shape, don't factor a shared
helper — `is_composite` already sits right next to `is_prime` without
one) for primality, and `_reverse_int`'s `str(abs(value))[::-1]`
digit-reversal (sign doesn't matter here since `is_emirp` only ever
considers non-negative primes) to get the reversed value, then check
both the original and reversed values are prime and unequal.

Model the arity/type-checking on `_is_prime`'s structure: reuse
`_require_arity("is_emirp", arguments, 1, line, column)` and
`_require_int("is_emirp", arguments[0], line, column)`. Negative input
is not a separate error case — mirror `is_prime`'s own convention where
any `value < 2` simply answers `false`, which negative input already
satisfies with no extra check needed.

Acceptance criteria:
- `is_emirp(13);` is `true`, `is_emirp(17);` is `true`,
  `is_emirp(31);` is `true`, `is_emirp(79);` is `true`,
  `is_emirp(97);` is `true` — classic emirp pairs in both directions.
- `is_emirp(2);` is `false`, `is_emirp(11);` is `false` — palindromic
  primes are not emirps, since their reversal equals themselves.
- `is_emirp(4);` is `false`, `is_emirp(15);` is `false`,
  `is_emirp(20);` is `false` — non-primes answer `false` regardless of
  what their reversal looks like.
- `is_emirp(0);` is `false`, `is_emirp(1);` is `false` — below the
  prime threshold, matching `is_prime`'s own convention.
- `is_emirp(-13);` is `false` — negative input answers `false` without
  raising, falling out of the same `value < 2` check `is_prime` uses,
  not a special-cased guard.
- `is_emirp(107);` is `true` — a larger three-digit emirp (reversal
  `701`, also prime), confirming the trial-division check scales past
  small hand-checkable cases.
- `is_emirp(3.0);` (float) raises `CinderRuntimeError` matching
  `"is_emirp() requires an int, got float"` — no implicit
  float-to-int coercion, matching the rest of the integer-property
  cluster.
- `is_emirp(true);` (bool) raises `CinderRuntimeError` matching
  `"is_emirp() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_composite`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_emirp` added near `is_prime`/`is_composite`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 2. Language: list/map-destructuring function parameters (`fn f([a, b]) { ... }`, `fn f({a, b}) { ... }`)

Build: extend function-parameter parsing/binding — shared by named
`fn` declarations, anonymous `fn` expressions, and parenthesized arrow
functions alike, since all three route through `_fn_param_list`/
`_fn_param` in `cinder/parser.py` (search both) — to accept a list- or
map-destructuring pattern in place of a plain identifier parameter,
mirroring the patterns `let`, plain assignment, and (after task 3
lands) `for`-loops already accept in every other binding position.
Today a caller passing e.g. a `[x, y]` point or a `{a, b}` options
record must destructure it by hand on the first line of the body
(`fn dist(p) { let [x, y] = p; ... }`); this closes that gap so
`fn dist([x, y]) { ... }` works directly. This is the depth task
queued after task 4's breadth work (`is_emirp`) per `PROJECT.md`'s
breadth-vs-depth policy.

In `cinder/ast_nodes.py`: `FnDecl`/`FnExpr` currently carry
`params: list` of raw `(name: str, default: Expr | None)` tuples
(built by `_fn_param`). Add a `Param` dataclass — the same field shape
`ForStmt` already uses for its own pattern flexibility — with
`name: "str | None"`, `default: "Expr | None" = None`,
`names: "list | None" = None`, `rest: "str | None" = None`, and
`is_map: bool = False`. A plain identifier parameter sets only
`name`/`default` (`names=None`); a list-destructuring parameter sets
`name=None, names=names, rest=rest`; a map-destructuring parameter
sets `name=None, names=names, is_map=True`. Change `FnDecl.params`/
`FnExpr.params`'s annotation from `list` of tuples to `list[Param]`.

In `cinder/parser.py`: change `_fn_param` to check
`self._check(TokenType.LBRACKET)`/`self._check(TokenType.LBRACE)`
before its current unconditional
`self._consume(TokenType.IDENTIFIER, "parameter name")`. On `[`, call
the existing `_destructure_list_pattern()` helper to get `names, rest`
and return `Param(name=None, names=names, rest=rest)` — no default
allowed: a destructuring parameter followed by `=` raises `ParseError`
(e.g. `"destructuring parameter cannot have a default value"`), since
there's no single value to show as a default. On `{`, call
`_destructure_map_pattern()` (the helper task 3 extracts out of
`_destructure_let_statement`) to get `names` and return
`Param(name=None, names=names, is_map=True)`, same no-default
restriction. Otherwise keep the existing identifier-plus-optional-
default path, now returning `Param(name=name_token.lexeme,
default=default)` instead of a bare tuple. A destructuring parameter
counts as "has no default" for the existing `seen_default` tracking in
`_fn_param_list` — no new rule needed, since `seen_default` already
only flips true when a default is actually seen.

In `cinder/interpreter.py`: `CinderFunction.arity` currently does
`sum(1 for _, default in self.decl.params if default is None)` —
change the unpacking to iterate `Param` objects
(`sum(1 for param in self.decl.params if param.default is None)`); a
destructuring parameter's `default` is always `None` so it already
counts as required, no special-case needed. `call_value`'s parameter-
binding loop currently does
`for index, (param_name, default) in enumerate(callee.decl.params):
... call_env.define(param_name, value)` — change to iterate `Param`
objects and, after resolving `value` (argument or evaluated default,
unchanged), branch on `param.names is not None`: if `param.is_map`,
call the existing `self._bind_map_destructure(call_env, param.names,
value, line, column)`; elif list pattern, call
`self._bind_list_destructure(call_env, param.names, param.rest, value,
line, column)`; else keep `call_env.define(param.name, value)`. Reuse
the same errors those helpers already raise (`CinderRuntimeError` for
a non-list/non-map argument or a missing map key) — no new error text
to design.

Acceptance criteria:
- `fn dist([x, y]) { return x * x + y * y; } print(dist([3, 4]));`
  prints `25` — the motivating list-destructuring case.
- `fn describe({name, age}) { return name + " is " + str(age); }
  print(describe({"name": "Al", "age": 30}));` prints `Al is 30` — the
  motivating map-destructuring case.
- `fn f([a, ...rest]) { return rest; } print(f([1, 2, 3]));` prints
  `[2, 3]` — the trailing rest element works in a destructuring
  parameter exactly as it does in `let`/`for`.
- A destructuring parameter combines with a plain trailing rest
  *parameter*: `fn f([a, b], ...more) { return [a, b, more]; }
  print(f([1, 2], 3, 4));` prints `[1, 2, [3, 4]]` — the parameter-
  list-level rest (extra positional arguments) and a pattern-level
  rest (inside one `[...]` parameter) are independent features that
  don't conflict.
- Anonymous `fn` expressions and parenthesized arrow functions accept
  the same patterns: `let f = fn([a, b]) { return a + b; };
  print(f([1, 2]));` and `print((([a, b]) => a + b)([1, 2]));` both
  print `3`.
- `fn f([a, b] = [1, 2]) { return a; }` raises `ParseError` (a
  destructuring parameter cannot have a default value).
- `fn f([a, b]) { return a; } f(5);` (a non-list argument where a list
  pattern was declared) raises the same `CinderRuntimeError`
  `_bind_list_destructure` already raises for `let [a, b] = 5;`, not a
  silent crash.
- `fn f({a, b}) { return a; } f({"a": 1});` (a map argument missing an
  expected key) raises the same `CinderRuntimeError`
  `_bind_map_destructure` already raises for `let {a, b} = {"a": 1};`.
- Existing plain-identifier parameters, defaults, and rest parameters
  (`fn f(a, b = 1, ...rest) { ... }`) are completely unaffected.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`FnDecl`, `FnExpr`, new `Param`),
`cinder/parser.py` (`_fn_param`, `_fn_param_list`),
`cinder/interpreter.py` (`CinderFunction.arity`, `call_value`), `tests/
test_parser.py`, `tests/test_interpreter.py`. Once merged, `README.md`'s
Functions bullet needs the destructuring-parameter form mentioned, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `divisors` — list an integer's positive divisors

Build: add `divisors(n)` to `cinder/builtins.py`, registered right
after `_is_deficient` (search for `def _is_deficient`) — it's the
natural value-returning sibling of the `is_perfect_number`/
`is_abundant`/`is_deficient` cluster, all three of which already do
their own trial-division-to-`sqrt(n)` walk over divisor pairs and
discard the individual divisors, keeping only their sum. This is a
fresh breadth task queued after task 5's depth work (destructuring
function parameters) per `PROJECT.md`'s breadth-vs-depth policy,
restarting the alternation after two depth tasks (3, 5) sandwiched a
single breadth task (4) between them.

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

## 4. Language: optional call chaining (`f?.(...)`)

Build: extend the existing safe-navigation family — `m?.key` (dot
property access), `obj?.[expr]` (bracket index access), both defined
in `cinder/ast_nodes.py`'s `OptionalIndex` and parsed via
`_finish_optional_dot` in `cinder/parser.py` (search both) — to cover
the one position they still don't: a *call*. Today `let f = nil;
f();` raises `CinderRuntimeError` `"nil is not callable"` (search
`is not callable` in `cinder/interpreter.py`'s `call_value`) with no
way to say "call this only if it isn't nil" short of a manual
`if f != nil { f(); }`. This is the depth task queued after task 4's
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

## 5. Standard library: `is_rotation` — string rotation predicate

Build: add `is_rotation(a, b)` to `cinder/builtins.py`, registered
right after `_is_anagram` (search for `def _is_anagram`) — it's a
natural sibling in the two-string predicate family alongside
`is_anagram`/`is_permutation`, one position more specific than
`is_anagram`'s "same multiset of characters" test. This is a fresh
breadth task queued after task 4's depth work (optional call chaining)
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
