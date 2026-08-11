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

## 1. Language: map-destructuring loop variables in list/map comprehensions (`[k + v for {a, b} in list_of_maps]`) [claimed 2026-08-11T20:08:18Z]

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
the `is_rotation` breadth work per `PROJECT.md`'s breadth-vs-
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

## 2. Standard library: `is_balanced` — balanced-brackets predicate

Build: add `is_balanced(s)` to `cinder/builtins.py`, registered right
after `_is_pangram` (search for `def _is_pangram`) — a string
predicate, but a different flavor than its neighbors: `is_anagram`/
`is_permutation`/`is_pangram`/`is_palindrome` are all direct
delegations to a multiset/reversal comparison, whereas this is the
project's first stack-based parsing predicate. This is a fresh breadth
task queued after task 1's depth work (map-destructuring loop
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

## 3. Language: rest element in map-destructuring patterns (`let {a, ...rest} = m;`)

Build: close the one gap left between the two destructuring pattern
kinds. List-destructuring patterns (`let [a, ...rest] = expr;`,
`for [k, v, ...rest] in xs { ... }`, `fn f([a, ...rest]) { ... }`)
already accept an optional trailing rest element that collects
whatever wasn't consumed by name, via `_destructure_list_pattern` in
`cinder/parser.py` (search for it) and `_bind_list_destructure` in
`cinder/interpreter.py`. Map-destructuring patterns have no equivalent
today: `let {a, ...rest} = {"a": 1, "b": 2};` currently raises
`ParseError` `"expected identifier in destructuring pattern, found
'...'"` (verified by running `python3 -m cinder.cli eval 'let {a,
...rest} = {"a": 1, "b": 2};'` from this project's directory) — there
is no way to capture "every key I didn't name" the way list patterns
already capture "every element I didn't name". This is the depth task
after task 2's breadth work (`is_balanced`) per `PROJECT.md`'s
breadth-vs-depth policy.

The shared helper `_destructure_map_pattern` in `cinder/parser.py`
(search for `def _destructure_map_pattern`) is called from exactly
three places today — `_destructure_let_statement` (the `is_map`
branch, `let {a, b} = expr;`), `_for_statement` (the `LBRACE` branch,
`for {a, b} in list_of_maps { ... }`), and `_fn_param` (the `LBRACE`
branch, `fn f({a, b}) { ... }`) — and every one of those three already
has a `rest: "str | None" = None` field sitting unused on its AST node
(`DestructureLetStmt.rest`, `ForStmt.rest`, `Param.rest`), since that
field is shared with the list-pattern case and simply always gets
`None` for a map pattern today. Note a fourth, deliberately
out-of-scope caller: `_try_map_destructure_assign_statement` (the
`{a, b} = expr;` plain-assignment form) does *not* call
`_destructure_map_pattern` — it inlines its own speculative
identifier-list parse for backtracking reasons (see its docstring),
so it is untouched by this task; extending the assignment form to
accept `...rest` is left for a future task. If the map-destructuring
loop variables in comprehensions task has landed by the time this is
picked up, `_list_comprehension`/`_map_comprehension`'s `LBRACE`
branch will be a fourth in-scope caller of `_destructure_map_pattern`
— thread it through exactly like the other three, below. If it hasn't
landed yet (still queued, or graveyarded), there is nothing to update
there.

In `cinder/parser.py`: change `_destructure_map_pattern` to return
`tuple[list, "str | None"]` instead of a bare `list`, mirroring
`_destructure_list_pattern`'s existing shape (search for
`def _destructure_list_pattern` and copy its exact
`DOT_DOT_DOT`-checking structure): consume `{`; if the next token is
`...`, parse a rest name via the same helper
`_destructure_list_pattern` already uses for its own rest name
(search `_destructure_rest_name`) and leave `names` empty, otherwise
consume one identifier into `names` as today; then, on each `,`, if
`rest` is already set raise the identical `ParseError`
`f"rest element must be last in destructuring pattern, found
{self._describe(token)}"` `_destructure_list_pattern` already raises
for the equivalent case (verified by running `python3 -m cinder.cli
eval 'let [a, ...rest, b] = [1,2,3];'`, which raises exactly that
message today — reuse the message text verbatim), otherwise parse
either another `...rest` or another identifier the same way; finally
consume `}` and return `(names, rest)`. Update its three current call
sites to unpack the tuple and thread `rest` into the AST node they
build instead of leaving the field at its default `None`:
`_destructure_let_statement`'s `is_map` branch (currently `names =
self._destructure_map_pattern(); rest = None` — becomes `names, rest
= self._destructure_map_pattern()`, then pass `rest=rest` into the
`DestructureLetStmt(...)` call alongside the existing `is_map=True`),
`_for_statement`'s `LBRACE` branch (currently `names =
self._destructure_map_pattern(); is_map = True` — becomes `names,
rest = self._destructure_map_pattern(); is_map = True`, reusing the
`rest` local the function's `LBRACKET` branch already declares), and
`_fn_param`'s `LBRACE` branch (currently `names =
self._destructure_map_pattern()` then `return Param(name=None,
names=names, is_map=True)` — becomes `names, rest =
self._destructure_map_pattern()` then `return Param(name=None,
names=names, rest=rest, is_map=True)`).

In `cinder/interpreter.py`: change `_bind_map_destructure`'s signature
from `(self, env, names, value, line, column, use_assign=False)` to
`(self, env, names, rest, value, line, column, use_assign=False)`,
inserting `rest` in the same position `_bind_list_destructure` already
has it. After the existing per-name loop that binds each named key
(unchanged — still raises `"destructuring pattern expects key {name!r},
not found in map"` for a missing named key, still silently ignores
extra keys when `rest is None`, exactly as today), add: if `rest is
not None`, build a fresh dict of every entry whose key is not in
`names` (`{k: v for k, v in value.items() if k not in names}` — a new
map, not a view onto `value`, mirroring how `_bind_list_destructure`
builds a fresh `list(value[len(names):])` rather than aliasing) and
bind it via the existing `_bind_destructure_name(env, rest, remaining,
line, column, use_assign)` helper, the same one both destructuring
kinds already share. Update the three (or four, per the comprehension
note above) call sites to pass their AST node's `rest` field
positionally where the new parameter now sits: the `for`-loop
call in `_execute_for` (search `self._bind_map_destructure(iter_env,
stmt.names,`), the function-parameter call in the calling machinery
(search `Interpreter()._bind_map_destructure(call_env, param.names,`),
and the assignment-destructure call in `_evaluate_destructure_assign`
(search `self._bind_map_destructure(env, expr.names,` — pass
`expr.rest`, which is always `None` for the map form per
`DestructureAssign`'s own docstring, so this is a signature-only
change with no behavior change for that call site).

Acceptance criteria:
- `let {a, ...rest} = {"a": 1, "b": 2, "c": 3}; print(a); print(rest);`
  prints `1` then `{"b": 2, "c": 3}`.
- `let {a, b, ...rest} = {"a": 1, "b": 2}; print(rest);` prints `{}` —
  no leftover keys still binds `rest` to an empty map, not an error.
- `let {...rest} = {"a": 1, "b": 2}; print(rest);` prints
  `{"a": 1, "b": 2}` — a pattern with only a rest element and no named
  keys at all collects everything, mirroring `let [...rest] = xs;`.
- `let {a} = {"a": 1, "b": 2}; print(a);` (no rest element) still
  prints `1` with `"b"` silently ignored, completely unchanged from
  today — the no-rest behavior must not regress.
- `for {a, ...rest} in [{"a": 1, "b": 2}, {"a": 3, "c": 4}] { print(a);
  print(rest); }` prints `1`, `{"b": 2}`, `3`, `{"c": 4}` — a fresh
  rest map bound per iteration.
- `fn f({a, ...rest}) { return rest; } print(f({"a": 1, "b": 2, "c":
  3}));` prints `{"b": 2, "c": 3}`.
- `let {a, ...rest, b} = {"a": 1};` (rest not last) raises
  `CinderError` — a `ParseError` matching `"rest element must be last
  in destructuring pattern, found 'b'"`, the identical message
  list-pattern rest already raises for the equivalent case.
- `let {a, ...rest} = 5;` (non-map value) still raises the existing
  `CinderRuntimeError` matching `"cannot destructure int as a map"` —
  the domain check runs before any rest logic, unchanged.
- The plain-assignment map-destructuring form (`{a, b} = expr;`) is
  completely unaffected — it does not gain `...rest` support in this
  task (verified today: `{a, ...rest} = {"a": 1};` raises `ParseError`
  `"expected ';' after expression, found ','"`, since it falls through
  to `_block()` parsing rather than being recognized as a
  destructuring pattern at all — that specific error text is
  incidental, not a contract, and may change if a future task adds
  `...rest` support there).
- Existing map-destructuring without a rest element in every position
  (`let {a, b} = m;`, `for {a, b} in maps { ... }`, `fn f({a, b}) { ...
  }`, `{a, b} = m;`) and existing list-pattern rest
  (`let [a, ...rest] = xs;` and friends) are completely unaffected by
  this change.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_map_pattern` and its
three call sites), `cinder/interpreter.py` (`_bind_map_destructure`
and its three call sites), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s destructuring
bullets need the map-pattern rest element mentioned next to the
existing list-pattern rest element, and `PROJECT.md`'s roadmap
paragraph needs it moved from backlog to landed — leave both to the
Architect's next grooming pass, not this task.

---

## 4. Standard library: `is_isogram` — no-repeated-letter predicate

Build: add `is_isogram(s)` to `cinder/builtins.py`, registered right
after `_is_blank` (search for `def _is_blank`) — a fresh breadth task
queued after task 3's depth work (map-destructuring rest element) per
`PROJECT.md`'s breadth-vs-depth policy, and, like `is_balanced`,
deliberately not another `is_anagram`-style multiset delegation:
it's a single-pass character-frequency check instead.

An isogram is a string in which no letter appears more than once,
case-insensitive (`'A'` and `'a'` count as the same letter and
collide). Non-letter characters — spaces, hyphens, digits, punctuation
— are ignored entirely: they neither count toward a collision nor
break one, so `"six-year-old"` is an isogram even though `-` repeats
three times. Implement with a single scan: lowercase the string, keep
only alphabetic characters (`char.isalpha()`), and compare the
filtered length to the length of the `set` built from it — equal
lengths means no letter repeated. No need for an explicit loop with
early exit; the set-length comparison is the whole check, mirroring
how `_is_pangram` reduces to a single `set` comparison rather than a
hand-rolled scan.

Model the arity/type-checking on `_is_blank`'s structure exactly:
`_require_arity("is_isogram", arguments, 1, line, column)`, then a
single non-`str` check raising `CinderRuntimeError` matching
`"is_isogram() requires a string, got {type}"` (same one-argument
message shape `_is_blank`/`_is_pangram` already use, not
`_is_anagram`'s two-argument "first argument"/"second argument"
phrasing — there's only one argument here).

Acceptance criteria:
- `is_isogram("lumberjacks");` is `true` — the motivating case, every
  letter distinct.
- `is_isogram("background");` is `true` and `is_isogram("downstream");`
  is `true` — more all-distinct-letter words.
- `is_isogram("isograms");` is `false` — `'s'` repeats.
- `is_isogram("Alphabet");` is `false` — case-insensitive collision:
  `'A'` and `'a'` count as the same letter.
- `is_isogram("");` is `true` — the empty string has nothing to
  collide.
- `is_isogram("six-year-old");` is `true` — hyphens repeat freely
  without counting as a collision, since only letters are considered.
- `is_isogram("Emma");` is `false` — `'m'` repeats within a single
  short word, not just across a longer one.
- `is_isogram("12 34");` is `true` — a string with no letters at all
  is trivially an isogram (nothing to collide).
- `is_isogram(5);` raises `CinderRuntimeError` matching
  `"is_isogram() requires a string, got int"`.
- `is_isogram(true);` raises `CinderRuntimeError` matching
  `"is_isogram() requires a string, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_blank`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_isogram` added near `is_blank`/`is_pangram`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Language: rest element in plain-assignment map-destructuring (`{a, ...rest} = expr;`)

Build: close the gap task 3 (rest element for map-destructuring
`let`/`for`/`fn` patterns) deliberately left open. That task's own
scope note says it explicitly: "the plain-assignment map-destructuring
form (`{a, b} = expr;`) is completely unaffected — it does not gain
`...rest` support in this task", since that form parses via its own
inlined speculative parser (`_try_map_destructure_assign_statement` in
`cinder/parser.py`, search for it) rather than the shared
`_destructure_map_pattern` helper task 3 changes. This is that
deferred follow-up — the depth task after task 4's breadth work
(`is_isogram`) per `PROJECT.md`'s breadth-vs-depth policy. Verified
today (after task 3 lands): `let a = 1; let rest = 2; {a, ...rest} =
{"a": 1, "b": 2};` raises `ParseError` `"expected ';' after
expression, found ','"` — the pattern parse silently bails out of
`_try_map_destructure_assign_statement` on the unexpected `...` token
and falls through to the `_block()` fallback, which is what actually
raises that (unrelated-looking) error.

In `cinder/parser.py`: `_try_map_destructure_assign_statement`
currently parses its identifier list with a fixed loop — one
`self._consume(TokenType.IDENTIFIER, ...)`, then `while
self._check(TokenType.COMMA): ... consume another IDENTIFIER`. Change
it to accept an optional trailing `...rest`, mirroring
`_destructure_assign_pattern`'s existing `rest = None` /
`Spread`-detection shape (search for it, just above this function) for
the *behavior* to replicate, but built the same speculative,
token-by-token way this function already works (not by parsing a
`ListLiteral`, since there is no map-literal equivalent to inspect):
track a local `rest = None`; where the function currently does its
first unconditional `_consume(TokenType.IDENTIFIER, ...)`, first check
`self._check(TokenType.DOT_DOT_DOT)` — if so, call the existing
`_destructure_rest_name()` helper (the same one
`_destructure_list_pattern`/`_destructure_assign_pattern` already use)
to set `rest` and leave `names` empty, otherwise consume one
identifier into `names` as today; in the `while
self._check(TokenType.COMMA)` loop, on each iteration check
`DOT_DOT_DOT` the same way — if `rest` is already set, raise
`ParseError` (do **not** let it get caught by this function's own
`except ParseError: self.pos = start; return None` — let it propagate
as a real syntax error instead, since by this point the pattern shape
is unambiguous and a bare fallback to `_block()` would just produce a
confusing unrelated error) with message `f"rest element must be last
in destructuring pattern, found {self._describe(token)}"`, the
identical message text `_destructure_list_pattern` and (after task 3)
`_destructure_map_pattern` both already raise for the equivalent case
— reuse it verbatim; otherwise call `_destructure_rest_name()` again.
To make the "let this one specific error propagate, but still catch
everything else for the silent-fallback contract" split clean, raise a
distinct marker or simply move just that one `ParseError` raise
outside the existing `try`/`except ParseError` block's coverage (e.g.
finish the whole speculative pattern parse — identifiers, commas,
`}`, `=` — inside the existing `try`, but only *validate* "rest must
be last" and raise that specific error after the `try` block succeeds,
once the pattern shape is already confirmed well-formed enough to
commit to). Thread `rest` into the returned node: `DestructureAssign(names,
rest, value, eq_token.line, eq_token.column, is_map=True)` (currently
hardcodes `None` in that second position).

In `cinder/ast_nodes.py`: update `DestructureAssign`'s docstring — it
currently says "with `is_map=True` the map-pattern form `{a, b} =
expr;` (no rest element for that form — `rest` is always `None` when
`is_map` is `True`)"; that parenthetical is no longer true once this
task lands, so remove or rewrite it to describe the map form the same
way the list form already is (both may now carry a non-`None` `rest`).

No `cinder/interpreter.py` changes needed: task 3 already threads
`expr.rest` through `_evaluate_destructure_assign`'s `is_map` branch
into `_bind_map_destructure` (verify this is still true when you pick
up this task — if task 3 hasn't landed yet, this task is blocked on
it and should wait).

Acceptance criteria:
- `let a = 1; let rest = 2; {a, ...rest} = {"a": 1, "b": 2, "c": 3};
  print(a); print(rest);` prints `1` then `{"b": 2, "c": 3}`.
- `let a = 1; let b = 2; let rest = 3; {a, b, ...rest} = {"a": 1, "b":
  2}; print(rest);` prints `{}` — no leftover keys still binds `rest`
  to an empty map, not an error.
- `let rest = 1; {...rest} = {"a": 1, "b": 2}; print(rest);` prints
  `{"a": 1, "b": 2}` — a pattern with only a rest element collects
  everything, mirroring `let {...rest} = m;` and `[...rest] = xs;`.
- `let a = 1; let b = 2; {a, b} = {"a": 1, "b": 2, "c": 3}; print(a);`
  (no rest element) still prints `1` with `"c"` silently ignored,
  completely unchanged from today — the no-rest behavior must not
  regress.
- `let a = 1; let rest = 2; {a, ...rest, b} = {"a": 1};` (rest not
  last) raises `ParseError` matching `"rest element must be last in
  destructuring pattern, found 'b'"` — a real syntax error, not a
  silent fallback into `_block()` producing an unrelated message.
- `let rest = 1; {...rest} = 5;` (non-map value) still raises the
  existing `CinderRuntimeError` matching `"cannot destructure int as a
  map"` — the domain check runs before any rest logic, unchanged.
- Existing plain-assignment map-destructuring without a rest element
  (`{a, b} = m;`) and every other destructuring form/position
  (`let`/`for`/`fn` map patterns with and without rest, list-pattern
  assignment rest `[a, ...rest] = xs;`) are completely unaffected by
  this change.
- Full test suite passes.

Likely files: `cinder/parser.py`
(`_try_map_destructure_assign_statement`), `cinder/ast_nodes.py`
(`DestructureAssign` docstring), `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s destructuring
bullets need the plain-assignment map-pattern rest element mentioned,
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
