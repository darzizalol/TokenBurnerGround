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

## 1. "Did you mean...?" suggestions for undefined-name errors [claimed 2026-07-31T14:34:36Z]

Build: when `_evaluate_identifier` or `_evaluate_assign`
(`cinder/interpreter.py:588-606`) raise `undefined name {name!r}` after
an `Environment.get`/`assign` `KeyError`, append a suggestion when a
close match exists among the names currently in scope. Add a method to
`Environment` (`cinder/interpreter.py:146-177`) — e.g. `all_names(self)
-> set[str]` — that walks `self` and every `parent` up the chain,
unioning each level's `self._values.keys()` (this naturally includes
global builtins, since `create_global_environment` populates the
outermost `Environment` the same way). In both call sites, on
`KeyError`, use `difflib.get_close_matches(expr.name, env.all_names(),
n=1, cutoff=0.6)` (stdlib `difflib`, no new dependency) to find the
single closest match; if one is found, append `f" (did you mean
{match!r}?)"` to the existing message, otherwise leave the message
exactly as it is today (no trailing text) — do not change the exception
type, line/column, or the no-match message wording, only append the
suggestion when one exists, so every existing test asserting the exact
current message on a genuinely-unmatched name keeps passing.

Acceptance criteria:
- `let cost = 1; print(costt);` raises `CinderRuntimeError` with message
  `"undefined name 'costt' (did you mean 'cost'?)"`.
- `let cost = 1; costt = 2;` (assignment path) raises the same
  suggestion form via `_evaluate_assign`.
- A name with no close match in scope (e.g. `print(zzzzzzz_no_match);`
  with nothing similar defined) raises the exact unchanged message
  `"undefined name 'zzzzzzz_no_match'"`, with no `(did you mean...?)`
  suffix — pin this as an explicit regression test.
- A builtin name typo suggests the builtin, e.g. `pritn(1);` (missing
  `print`) suggests `'print'` — since builtins live in the outermost
  `Environment`, `all_names()` must include them.
- Line/column on the raised error are unchanged (still `expr.line`/
  `expr.column`) — the suggestion only changes the message text.
- Full test suite passes.

Likely files: `cinder/interpreter.py`, `tests/test_interpreter.py`.

---

## 2. Labeled `break`/`continue` for nested loops

Build: let a loop be prefixed with a label — `outer: while (cond) {
... }`, `outer: for (x in xs) { ... }`, `outer: for (let i = 0; ...; ...)
{ ... }`, `outer: do { ... } while (cond);` — and let `break outer;`/
`continue outer;` target that specific enclosing loop instead of the
innermost one, e.g. to break out of a nested loop from inside it in one
step. Add a `LabelStmt`-style optional field instead of a new
wrapper node: add `label: str | None` to each loop AST node —
`WhileStmt` (`cinder/ast_nodes.py:239`), `DoWhileStmt` (:247), `ForStmt`
(:255), and `ForCStmt` (:264, merged via PR #121) — defaulting to `None`
for unlabeled loops, and `label: str | None` on `BreakStmt`/
`ContinueStmt` (defaulting to `None` for the existing unlabeled form).
Lex: no new token type needed — a label is just an `IDENTIFIER` followed
by `:` at statement position, immediately before one of the loop
keywords; in the parser's statement dispatcher, peek for
`IDENTIFIER` + `:` before falling into the existing loop-keyword
dispatch, consume both, parse the loop as normal, and attach the label.
`break`/`continue` parsing optionally consumes a trailing `IDENTIFIER`
before the `;` (only when the next token is an identifier, not `;` —
don't require one, preserving today's unlabeled `break;`/`continue;`).
Interpreter: give `_BreakSignal`/`_ContinueSignal`
(`cinder/interpreter.py:96-101`) an optional `label: str | None`
constructor arg; when a loop's execution catches one of these signals,
if the signal's label is `None` or matches the loop's own label, handle
it as today (stop/skip-to-step), otherwise **re-raise it unchanged**
so it propagates to the next enclosing loop up the Python call stack —
this is the entire mechanism, no explicit "loop registry" needed since
Python's own exception propagation through nested `execute` calls does
the targeting. A labeled `break`/`continue` naming a label that matches
no enclosing loop should be a parse-time error if staticaly detectable,
but since loop nesting is only fully known at parse time via a simple
stack of in-scope labels the parser is already tracking for
break/continue-outside-loop validation (find that existing check — it
validates break/continue only appear inside a loop) extend the same
stack to carry labels and validate the named label is currently open,
raising `ParseError` with line/column if not.

Acceptance criteria:
- ```
  let log = [];
  outer: for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
          if (j == 1) { continue outer; }
          push(log, [i, j]);
      }
  }
  log
  ```
  is `[[0, 0], [1, 0], [2, 0]]` — `continue outer` skips the rest of
  the inner loop *and* the rest of the outer iteration's remaining
  inner-loop work, advancing the outer loop's own step.
- Same shape with `break outer;` instead stops the entire nested
  structure after the first `j == 1` hit: `log` is `[[0, 0]]`.
- Unlabeled `break;`/`continue;` inside a labeled loop still target the
  innermost loop exactly as before (regression test) — labels don't
  change default behavior.
- A label on each of `while`, `do`/`while`, and both `for` forms all
  work with `break <label>;` (one test per loop kind naming its own
  label).
- `break nonexistent;` (naming a label with no matching enclosing loop)
  raises `ParseError` with line/column.
- `break;`/`continue;` outside any loop still raises the existing
  `ParseError` this already raises today (regression test — labels must
  not weaken that check).
- Full test suite passes.

Likely files: `cinder/tokens.py` (only if a dedicated check is easiest
via a new helper — likely no new `TokenType` needed), `cinder/ast_nodes.py`,
`cinder/parser.py`, `cinder/interpreter.py`, `tests/test_lexer.py` (only
if untouched regression coverage is missing), `tests/test_parser.py`,
`tests/test_interpreter.py`.

---

## 3. Standard library: `key_by` for lists

Build: add `key_by(list, fn)` to `cinder/builtins.py` — indexes a list
into a map keyed by `fn(item)`, the "one winner per key" counterpart to
`group_by` (`_group_by` at `cinder/builtins.py:1915-1935`, which buckets
into lists instead). Mirror `_group_by`'s validation exactly:
`_require_arity("key_by", arguments, 2, line, column)`, a `list` check
on the first argument (same error-message phrasing as `_group_by`'s,
`key_by` substituted for `group_by`), an `_is_callable` check on `fn`
(same phrasing), and the same `_is_valid_key` check on each computed key
raising the same `"{type_name(key)} is not a valid map key"` error
`_group_by`/`_count_by` already raise. Unlike `group_by`, each key maps
directly to the *item itself*, not a list of items; when two items
produce the same key, the later item wins (plain last-write-wins via
`result[key] = item` in iteration order — same overwrite semantics
Python dict assignment gives for free, no special-casing needed).

Acceptance criteria:
- `key_by([{"id": 1, "n": "a"}, {"id": 2, "n": "b"}], fn(x) { return
  x["id"]; })` is `{1: {"id": 1, "n": "a"}, 2: {"id": 2, "n": "b"}}`.
- Duplicate keys: `key_by([{"id": 1, "n": "a"}, {"id": 1, "n": "b"}],
  fn(x) { return x["id"]; })` is `{1: {"id": 1, "n": "b"}}` — the later
  item wins, pin this as an explicit regression test.
- `key_by([], fn(x) { return x; })` is `{}`.
- A key function returning a non-hashable value (e.g. a list) raises
  `CinderRuntimeError` with the same `"... is not a valid map key"`
  message `group_by`/`count_by` use, with line/column.
- A non-list first argument raises `CinderRuntimeError` with line/column.
- A non-function second argument raises `CinderRuntimeError` with
  line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 4. Standard library: `deep_merge` for maps

Build: add `deep_merge(map1, map2)` to `cinder/builtins.py` — the
recursive counterpart to `merge` (`_merge` at `cinder/builtins.py:363-376`,
which does a shallow `dict(map1); result.update(map2)`). Mirror `_merge`'s
validation exactly: `_require_arity("deep_merge", arguments, 2, line,
column)`, then a `dict` check on each of `map1`/`map2` with the same
error-message phrasing as `_merge`'s (`"deep_merge() requires a map, got
{type_name(...)}"`, substituting `deep_merge` for `merge`). Merge
semantics: for each key present in either map, if the key exists in both
*and* both values are `dict` (use plain `isinstance(x, dict)`, matching
how `_merge`/`_group_by` already test map-ness), recursively
`deep_merge` those two nested values; otherwise (key only in one map, or
present in both but at least one side is not a map) `map2`'s value wins
if the key is in `map2`, otherwise `map1`'s value is kept — i.e. exactly
`merge`'s existing last-write-wins behavior, just applied key-by-key
instead of via a single top-level `dict.update`. Lists are never merged
element-wise — a list value on either side is treated as an opaque
non-map value subject to the same override rule as any other scalar.
Neither input map is mutated; build and return a new `dict` (recursive
calls naturally do this already since `deep_merge` itself returns a new
dict, but the top-level result must not be `map1` or `map2` by
reference — construct it fresh, e.g. starting from `dict(map1)` only at
each recursion level the same way `_merge` does today, then overwriting/
recursing per key from `map2`).

Acceptance criteria:
- `deep_merge({"a": 1}, {"b": 2})` is `{"a": 1, "b": 2}` — disjoint keys
  from both sides survive, matching flat `merge`.
- `deep_merge({"a": {"x": 1}}, {"a": {"y": 2}})` is `{"a": {"x": 1, "y":
  2}}` — nested maps merge recursively instead of the inner map from
  `map2` clobbering the inner map from `map1` wholesale (this is the
  behavior that distinguishes it from plain `merge`, pin as the primary
  regression test).
- `deep_merge({"a": {"x": 1}}, {"a": {"x": 2}})` is `{"a": {"x": 2}}` —
  conflicting leaf keys still follow last-write-wins (`map2` wins).
- `deep_merge({"a": [1, 2]}, {"a": [3]})` is `{"a": [3]}` — a list value
  is overwritten wholesale by `map2`'s list, not concatenated or merged
  index-wise, pin this as an explicit regression test since it's the
  easiest behavior to get wrong by analogy with recursive-map merging.
- `deep_merge({"a": {"x": 1}}, {"a": 5})` is `{"a": 5}` — when one side's
  value at a shared key isn't a map, `map2`'s value wins outright rather
  than attempting a partial merge.
- Three levels of nesting merge correctly (e.g.
  `deep_merge({"a": {"b": {"c": 1}}}, {"a": {"b": {"d": 2}}})` is
  `{"a": {"b": {"c": 1, "d": 2}}}`).
- Neither input map is mutated by the call (assert both original maps
  are unchanged after `deep_merge` runs on them).
- `deep_merge({}, {})` is `{}`.
- A non-map first or second argument raises `CinderRuntimeError` with
  line/column, same phrasing pattern as `merge`'s own type-check errors.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 5. Spread elements in map literals: `{...map1, "k": v}`

Build: extend the spread operator, currently only accepted inside list
literals and call arguments (`Spread` node, `cinder/ast_nodes.py:69-76`;
parsed at `_list_element`, `cinder/parser.py:888-892`; evaluated in
`_evaluate_list_literal`, `cinder/interpreter.py:415-429`), to also work
inside map literals. `MapLiteral.pairs` (`cinder/ast_nodes.py:87-90`) is
currently `list[tuple[Expr, Expr]]`; change its contents to mix `tuple`
entries (plain `key: value` pairs, as today) with `Spread` entries,
mirroring how `ListLiteral.elements` already mixes plain `Expr` and
`Spread`. Parser: add a `_map_entry()` method mirroring `_list_element()`
— if the next token is `DOT_DOT_DOT`, consume it and return
`Spread(self._ternary(), dots.line, dots.column)`; otherwise delegate to
the existing `_map_pair()` and return its `(key, value)` tuple unchanged.
Update `_map_literal()` (`cinder/parser.py:894-903`) to call
`_map_entry()` in both places it currently calls `_map_pair()` directly
(the first entry and each comma-separated one). Interpreter: in
`_evaluate_map_literal` (`cinder/interpreter.py:431-441`), iterate
`expr.pairs` and branch on `isinstance(entry, Spread)`: if so, evaluate
`entry.expression`, require the result is a `dict` (else
`CinderRuntimeError` `f"cannot spread {type_name(value)} in a map
literal"` at `entry.line`/`entry.column`, matching the phrasing pattern
`_evaluate_list_literal`/`_evaluate_call` already use for their own kind
of literal/call), then `result.update(value)`; otherwise keep today's
per-pair logic (evaluate key, `_is_valid_key` check, evaluate value,
assign) unchanged. Splicing order follows plain iteration/last-write-wins
— no special-casing needed since `dict.update`/assignment already give
"later entry wins" for free, whether the later entry is a spread or an
explicit key.

Acceptance criteria:
- `{"a": 1, ...{"b": 2}}` is `{"a": 1, "b": 2}`.
- `{...{"a": 1}, "a": 2}` is `{"a": 2}` — an explicit key after a spread
  overrides the spread's value for that key.
- `{...{"a": 1}, ...{"a": 2, "b": 3}}` is `{"a": 2, "b": 3}` — a later
  spread overrides an earlier one key-by-key, not wholesale.
- `{...{}}` is `{}`; `{}` (no spread at all) still parses as today's
  empty map literal, not a block (regression test — don't disturb the
  existing empty-`{}`-is-a-map disambiguation).
- Spreading a non-map value, e.g. `{...[1, 2]}` or `{...5}`, raises
  `CinderRuntimeError` with the message `"cannot spread {type} in a map
  literal"` and the spread expression's line/column.
- A map literal mixing multiple spreads and explicit keys in any order
  (e.g. `{"x": 0, ...{"a": 1}, "y": 2, ...{"a": 3}}`) evaluates left to
  right with strict last-write-wins: `{"x": 0, "a": 3, "y": 2}`.
- List-literal spread and call-argument spread both still behave exactly
  as before (regression tests) — this task only adds a new place spread
  is accepted, it must not change existing behavior.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py`, `cinder/parser.py`,
`cinder/interpreter.py`, `tests/test_parser.py`,
`tests/test_interpreter.py`. Once merged, `README.md`'s Data Structures
bullet ("map literals don't support spread") will need updating too —
leave that to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
