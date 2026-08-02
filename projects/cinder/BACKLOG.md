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

## 1. REPL `:load <path>` command to run a script into the current session [claimed 2026-08-02T15:15:42Z]

Build: add a `:load <path>` REPL meta-command, the natural next REPL
ergonomics step after tab completion (`cinder/repl.py`) — lets a session
pull in helper functions/data from a `.cin` file without retyping them,
then keep interacting with them at the prompt. Model the trigger on the
existing `EXIT_COMMAND` check at `cinder/repl.py:114-115` (`if not
buffered_lines and line.strip() == EXIT_COMMAND: return`): add a sibling
check, only when `buffered_lines` is empty (so `:load` can't appear
mid-continuation), for a line whose `.strip()` starts with `":load "`
(a bare `:load` with no path is a usage error, not a crash — see below).
On match, don't fall through to the normal tokenize/parse/execute path
for that line; instead read the path (`line.strip()[len(":load "):]
.strip()`), resolve it relative to the process's current working
directory (`Path(path)`, not relative to `cinder/repl.py`'s own
location — the user is loading *their* script, not a package-internal
one), and:
- If the file doesn't exist or can't be read, `write(...)` a one-line
  error (e.g. `f"could not read {path}: {exc}"`) and continue the loop —
  do not crash the REPL, matching how `CinderError` is already caught
  per-statement without killing the session (`cinder/repl.py:132-133`).
- Otherwise, tokenize + `parse_program` the file's contents and execute
  each statement against the *same* persistent `env`/`interpreter` the
  REPL prompt itself uses (so `let`/`fn`/`const` bindings from the file
  are visible at the prompt afterward) — reuse the exact same per-
  statement loop body already in `run_repl` (`cinder/repl.py:125-131`:
  `ExprStmt` echoes its value via `stringify`, everything else just
  `execute`s) rather than writing a second, diverging copy of it; the
  cleanest way is to factor that loop body into a small helper (e.g.
  `_run_statements(statements, interpreter, env, write)`) called from
  both the main loop and the `:load` handler, rather than duplicating
  the `isinstance(statement, ExprStmt)` branch inline in two places.
- A `LexError`/`ParseError`/`CinderRuntimeError` raised while
  tokenizing/parsing/executing the loaded file is caught the same way
  the main loop catches `CinderError` (`cinder/repl.py:132-133`), but
  the diagnostic's source label must be the loaded file's path, not the
  literal string `<repl>` (`REPL_SOURCE_NAME`, `cinder/repl.py:23`) —
  e.g. `f"{path}:{e.line}:{e.column}: {e.message}"` — so a user can tell
  a `:load`-time error apart from a prompt-time one. One bad statement
  in the loaded file should not prevent later statements in the *same*
  file from running, matching the main loop's existing per-statement
  isolation — catch per-statement inside the `:load` handler's loop,
  same as `cinder/repl.py:123-133` already does for prompt input, not
  one `try` wrapping the whole file.
- After a successful (or partially-successful) `:load`, tab completion
  must see the newly bound names immediately: no extra wiring should be
  needed here since `_make_completer` (`cinder/repl.py:34-46`) already
  re-reads `env.all_names()` fresh on every Tab press, but add a test
  proving it (see acceptance criteria).
- `:load` with no path (just `":load"` or `":load "` with nothing after
  it, once stripped) writes a usage error (e.g. `"usage: :load <path>"`)
  and does not attempt to open a file.

Acceptance criteria:
- Given a temp file `helpers.cin` containing `fn double(x) { return x *
  2; } let greeting = "hi";`, running `:load <path-to-helpers.cin>`
  then `double(21);` at the next prompt returns `42`, and `greeting;`
  returns `"hi"` — the primary case, pin as the main regression test.
  Model the temp-file setup on `tempfile`, already imported in
  `tests/test_repl.py` (see its `import tempfile` at the top).
- `:load <path-to-nonexistent-file>` writes one output containing the
  path (or the error message) and does *not* raise — the loop continues
  and a following `1 + 1;` still evaluates to `2` in the same session.
- A `.cin` file with a runtime error partway through (e.g. statement 1
  defines `let a = 1;`, statement 2 is `undefined_name;`, statement 3 is
  `let b = 2;`) still leaves `b` bound afterward — proves per-statement
  isolation inside `:load`, not one `try` around the whole file. The
  error output for statement 2 names the loaded file's path (not
  `<repl>`) in its diagnostic prefix.
- A bare `:load` (no path) writes a usage message and does not attempt a
  file read (no `FileNotFoundError`/traceback surfaces even if cwd has
  no file named `""`).
- `:load` only triggers at the start of a fresh statement (empty
  `buffered_lines`), matching how `EXIT_COMMAND` already behaves — e.g.
  typing `:load` isn't reachable mid-continuation since Cinder has no
  syntax that would put `:load` inside an unbalanced bracket anyway;
  a single test confirming the top-level trigger path is enough, don't
  over-test this edge.
- Existing REPL behavior (bare-expression echoing, multi-statement
  buffering, `CinderError` diagnostics on prompt input, `exit`) is
  unaffected — full existing `tests/test_repl.py` suite still passes
  unmodified alongside the new tests.
- Full test suite passes.

Likely files: `cinder/repl.py` (new `:load` branch near
`cinder/repl.py:114-115`, the extracted `_run_statements` helper
factored out of `cinder/repl.py:123-133`), `tests/test_repl.py`. Once
merged, `README.md`'s REPL section needs a `:load` mention — leave that
to the Architect's next grooming pass, not this task.

---

## 2. Standard library: `frequencies` for a list's per-element occurrence counts

Build: add `frequencies(list)` to `cinder/builtins.py`, returning a map
from each distinct element to the number of times it occurs in the
input list. Model it directly on `_count_by`'s existing structure
(`cinder/builtins.py:2285-2305`) — arity 1, argument a `list` (else
`CinderRuntimeError` naming `frequencies` and `type_name(value)`,
matching `count_by`'s message shape:
`"frequencies() requires a list, got {type_name}"`), building a plain
`dict` by iterating the list and doing `counts[key] = counts.get(key,
0) + 1` for `key = element` (`count_by` does the identical thing except
its key comes from calling a predicate function first — `frequencies`
has no predicate, the element *is* the key) — reuse `_is_valid_key`
(already imported, see its use at `cinder/builtins.py:2301`) to raise
`CinderRuntimeError(f"{type_name(key)} is not a valid map key", line,
column)` for a non-hashable element (a list or map), the exact error
`count_by`/`group_by`/`key_by` already raise for a non-valid-key result
— **do not** reach for `mode`'s `(is_bool, element)`-keyed fast path or
its `values_equal`-based fallback for unhashable elements
(`cinder/builtins.py:1167-1205`): those exist because `mode` only ever
*compares* counts internally and never returns the dict itself, so it
can use a disambiguating internal key shape freely, whereas
`frequencies` must return a real Cinder map, which is bound by the same
`1`/`true`-collide-as-keys behavior every other map-key-producing
builtin already has (`count_by`, `group_by`, `key_by` all use a plain
dict with no bool/int disambiguation — that's the established,
already-shipped convention for this family of builtins, not a bug to
route around here). Preserve first-appearance insertion order (falls
out for free from a plain Python `dict` and a single left-to-right
pass, same as `count_by`).

Acceptance criteria:
- `frequencies([1, 2, 2, 3, 3, 3]);` is `{1: 1, 2: 2, 3: 3}` — the
  primary case, pin as the main regression test.
- `frequencies(["a", "b", "a"]);` is `{"a": 2, "b": 1}` — strings work
  as keys too, not just numbers.
- `frequencies([]);` is `{}` — an empty list is well-defined, not an
  error (matches `count_by([], fn(x) { return x; })`'s behavior on an
  empty list).
- Key order in the result matches first appearance in the input list —
  assert on `keys(frequencies([3, 1, 3, 2]))` being `[3, 1, 2]`, not
  sorted or insertion-via-count order.
- `frequencies([true, false, true]);` is `{true: 2, false: 1}` — bools
  work as keys (and, matching `count_by`'s existing behavior, don't
  need special-casing against ints here).
- `frequencies([[1, 2], [1, 2]]);` (a list of lists, each not a valid
  map key) raises `CinderRuntimeError` naming `frequencies` — or at
  minimum matches whatever exact wording `group_by`'s
  `"{type_name(key)} is not a valid map key"` error produces for the
  same underlying reason, since this reuses that same check.
- `frequencies("abc");` (a string, not a list) raises
  `CinderRuntimeError` naming `frequencies` and `string` in the
  message, matching `count_by`'s equivalent error for the same input.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `count_by`/`mode`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `frequencies` added near `count_by` — leave that to the
Architect's next grooming pass, not this task.

---

## 3. Safe navigation operator `?.` for map access: `m?.key` is `nil` when `m` is `nil`

Build: a new postfix operator `?.` (dot-only, mirroring the existing
`m.key` sugar) that evaluates its left side and, if that value is `nil`,
short-circuits the whole `?.` expression to `nil` **without** attempting
the property access — instead of `m.key` raising `CinderRuntimeError`
("nil is not indexable") when `m` is `nil`, `m?.key` just yields `nil`.
This pairs with the existing nil-coalescing family (`??`, `??=`) already
in the language: a common pattern becomes `m?.key ?? default`. Scope
this as a **single-level** short-circuit only — `a?.b.c` short-circuits
just the `?.b` step to `nil`; the trailing plain `.c` then runs against
that `nil` and still raises normally (full chain-propagating short-
circuit like JS's `?.` would require threading a "short-circuited"
signal through arbitrary subsequent postfix operations in the same
call/index chain, which is materially more complex and not needed for
the common `m?.key ?? default` use case — do not attempt full-chain
propagation in this task).

Lexer (`cinder/tokens.py`, `cinder/lexer.py`): add `QUESTION_DOT = auto()`
to `TokenType` in `cinder/tokens.py` (near `QUESTION_QUESTION`/`QQEQ`,
around `cinder/tokens.py:90-91`). In `cinder/lexer.py`'s `_question`
method (`cinder/lexer.py:351-362`, reached when the lexer sees a `?` —
see the dispatch at `cinder/lexer.py:80`), the current logic is: match a
second `?` first (for `??`/`??=`), else emit a bare `QUESTION` (used by
the ternary `cond ? a : b`). Add a new branch *before* the bare-`QUESTION`
fallback: if the next character is `.`, consume it and emit
`QUESTION_DOT` (`"?."`) instead of `QUESTION`. This is lexically
unambiguous — numbers never start with a bare `.` in this lexer (`_number`
only fires when the first character is already a digit, see
`cinder/lexer.py:244-257`), so `?` followed by `.` can never be a ternary
`?` followed by a `.5`-style float literal; it is always the start of
`?.`.

AST (`cinder/ast_nodes.py`): add a new frozen dataclass `OptionalIndex`
near `Index` (`cinder/ast_nodes.py:94-98`), same shape (`obj: "Expr"`,
`index: "Expr"`, `line: int`, `column: int`) — a distinct class from
`Index`, not a flag on it, so the interpreter dispatch and any future
assignment-target checks can tell them apart by type alone (mirroring
how `IndexCompoundAssign` is its own class rather than a flag on
`IndexAssign`).

Parser (`cinder/parser.py`): in `_call`'s postfix loop
(`cinder/parser.py:911-923`), which already checks
`self._check(TokenType.DOT)` and dispatches to `_finish_dot`, add a
sibling branch `elif self._check(TokenType.QUESTION_DOT): expr =
self._finish_optional_dot(expr)`. Add `_finish_optional_dot`, modeled
directly on `_finish_dot` (`cinder/parser.py:957-961`): consume the
`QUESTION_DOT` token, `_consume(TokenType.IDENTIFIER, "a property name
after '?.'")`, build the same `Literal(name_token.lexeme, ...)` key, and
return `OptionalIndex(obj, key, dot.line, dot.column)` instead of
`Index(...)`. `OptionalIndex` is deliberately not handled anywhere in
`_assignment` (`cinder/parser.py:733-`) — `m?.key = 5` and `m?.key += 1`
etc. must still raise `ParseError("invalid assignment target", ...)`,
the same fallthrough every non-`Identifier`/non-`Index` expression
already gets; add a test pinning this (safe navigation is read-only,
matching how `?.` is also not a valid assignment target in JS).

Interpreter (`cinder/interpreter.py`): add
`_evaluate_optional_index(self, expr: OptionalIndex, env: Environment)`
near `_evaluate_index` (`cinder/interpreter.py:542-546`): evaluate `obj =
self.evaluate(expr.obj, env)`; if `obj is None` (this interpreter's `nil`
representation — see `_evaluate_logical`'s `??` case,
`cinder/interpreter.py:738-741`), return `None` immediately *without*
evaluating `expr.index` (no observable difference here since `expr.index`
is always a `Literal` from the parser, but matches the short-circuit
contract established by `??`/`??=`: skip work you don't need); otherwise
evaluate `index = self.evaluate(expr.index, env)` and delegate to the
existing `self._index_get(obj, index, expr.line, expr.column)`
(`cinder/interpreter.py:547-`), reusing all of its existing error
behavior (e.g. `m?.key` on a non-nil non-map `m` still raises "not
indexable", exactly like `m.key` does today). Wire the dispatch: add
`if isinstance(expr, OptionalIndex): return
self._evaluate_optional_index(expr, env)` to the `evaluate()`
isinstance chain, next to the existing `Index` check
(`cinder/interpreter.py:239-240`).

Acceptance criteria:
- `let m = nil; m?.key;` is `nil` — the primary case, pin as the main
  regression test.
- `let m = {"key": 42}; m?.key;` is `42` — non-nil `m` behaves exactly
  like plain `.key`.
- `let m = nil; m?.key ?? "default";` is `"default"` — composes with the
  existing `??` operator, the main motivating use case.
- `let m = {}; m?.missing;` raises `CinderRuntimeError` ("missing map
  key") — `?.` only guards against `obj` itself being `nil`; a present-
  but-wrong-type `obj` or an absent key still errors exactly as `.`
  already does.
- `let x = 5; x?.key;` raises `CinderRuntimeError` ("not indexable") —
  a non-nil, non-map value is still a normal error under `?.`.
- Single-level scope, pinned explicitly: `let m = nil; m?.a.b;` still
  raises `CinderRuntimeError` ("nil is not indexable") — the `?.a` step
  yields `nil`, then the plain `.b` step on that `nil` errors normally;
  this is the documented, deliberate difference from JS-style full-chain
  optional chaining.
- A side-effecting test proves `expr.index`'s key literal is not
  re-evaluated or otherwise double-evaluated — not very interesting
  here since the key is always a parsed `Literal`, but do add a test
  proving `obj` is evaluated exactly once (a function call as the base
  expression, e.g. `fn m() { push(calls, 1); return nil; } m()?.key;
  len(calls);` is `1`).
- `m?.key = 5;` and `m?.key += 1;` both raise `ParseError` ("invalid
  assignment target") — `?.` is not a valid assignment target.
- Parser-level shape test: `m?.key;` parses to an `OptionalIndex` with
  `obj`/`index` matching, mirroring the existing dot-desugaring shape
  test for plain `Index` (see wherever `_finish_dot`'s desugaring is
  currently pinned in `tests/test_parser.py`).
- Lexer-level test: `?.` tokenizes as a single `QUESTION_DOT`, and
  existing ternary/`??`/`??=` tokenization (`? :`, `??`, `??=`) is
  unaffected — full existing `tests/test_lexer.py` suite still passes
  unmodified alongside the new test.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py` (`_question`,
`cinder/lexer.py:351-362`), `cinder/ast_nodes.py` (new `OptionalIndex`,
near `cinder/ast_nodes.py:94-98`), `cinder/parser.py` (`_call`'s postfix
loop and new `_finish_optional_dot`, near `cinder/parser.py:911-961`),
`cinder/interpreter.py` (new `_evaluate_optional_index`, near
`cinder/interpreter.py:542-546`, plus the dispatch `isinstance` chain
around `cinder/interpreter.py:239-240`), `tests/test_lexer.py`,
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged,
`README.md`'s Operators bullet (the nil-coalescing family description)
needs a `?.` mention — leave that to the Architect's next grooming
pass, not this task.

---

## 4. Standard library: `compact` to drop falsy elements from a list

Build: add `compact(list)` to `cinder/builtins.py`, returning a new list
containing only the elements of the input that are truthy under Cinder's
own truthiness rule — i.e. it drops `nil` and `false` and keeps
everything else, including `0`, `0.0`, and `""` (per PROJECT.md's fixed
truthiness principle: "every other value ... is truthy"). Model it
directly on `_filter`'s existing structure (`cinder/builtins.py:2107-2120`)
but with arity 1 (no predicate argument) and a comprehension gated on the
already-imported `is_truthy` helper (`cinder/builtins.py:29`, the same
helper `_filter`, `_any`, `_all`, `_take_while` etc. already use — see
its uses at `cinder/builtins.py:1215`, `1225`, `2121`): arity 1, argument
a `list` (else `CinderRuntimeError` naming `compact` and
`type_name(value)`, matching `filter`'s message shape:
`"compact() requires a list, got {type_name}"` — note `compact` has no
second argument, so its error message drops the "as its first argument"
phrasing `filter` uses for its two-argument case), returning
`[item for item in items if is_truthy(item)]`. Register it in the
builtins dict near `filter` (`cinder/builtins.py:2502`,
`"filter": _filter,`).

Acceptance criteria:
- `compact([1, nil, 2, false, 3]);` is `[1, 2, 3]` — the primary case,
  pin as the main regression test.
- `compact([0, 0.0, "", nil, false, 1]);` is `[0, 0.0, "", 1]` — falsy
  *values* by Python convention (`0`, `""`) are NOT dropped, only
  Cinder's own falsy set (`nil`, `false`) is; this is the one case worth
  over-testing since it's the whole point of reusing `is_truthy` instead
  of a naive Python truthiness check.
- `compact([]);` is `[]` — an empty list is well-defined, not an error.
- `compact([1, 2, 3]);` is `[1, 2, 3]` unchanged — a list with nothing
  falsy passes through as an equal (but new) list.
- `compact("abc");` (a string, not a list) raises `CinderRuntimeError`
  naming `compact` and `string` in the message.
- Wrong arity (0 or 2+ arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `filter`, see current
line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `compact` added near `filter` — leave that to the Architect's
next grooming pass, not this task.

---

## 5. Standard library: `find_last_index` — index of the last element matching a predicate

Build: add `find_last_index(list, fn)` to `cinder/builtins.py`, the
predicate-based counterpart to `find_index` (`cinder/builtins.py:1260-1276`)
that searches from the end instead of the start — closing the same kind
of gap `take_right`/`drop_right` closed for `take`/`drop`, and
`last_index_of` (`cinder/builtins.py:1247-1257`) already closed for
equality-based search, but no predicate-based reverse search exists yet.
Model the arity/type checks directly on `_find_index`'s existing
structure (arity 2, first argument a `list` else `CinderRuntimeError`
naming `find_last_index` and `type_name`, matching `"find_last_index()
requires a list as its first argument, got {type_name}"`; second
argument must be `_is_callable` else `CinderRuntimeError` matching
`"find_last_index() requires a function as its second argument, got
{type_name}"`), but iterate the list in reverse the same way
`_last_index_of` already does (`for index in range(len(collection) - 1,
-1, -1):`) instead of `find_index`'s forward `enumerate`, calling
`call_value(fn, [item], line, column)` and checking `is_truthy(...)` on
each element, returning the first (i.e. highest) index where it's true,
or `-1` if none match. Note `find` (`cinder/builtins.py:675`) is an
unrelated string-substring-search builtin, not a list predicate
search — do not model on or confuse with it; `find_index`/
`find_last_index` are the list-predicate family.

Acceptance criteria:
- `find_last_index([1, 2, 3, 4], fn(n) { return n > 2; });` is `3` (the
  last index where the predicate holds) — the primary case, pin as the
  main regression test; contrast with `find_index` on the same input
  returning `2` (the first match) to prove this isn't accidentally
  aliased to `find_index`.
- `find_last_index([1, 2, 3], fn(n) { return n > 10; });` is `-1` — no
  match.
- `find_last_index([], fn(n) { return true; });` is `-1` and the
  function is never called (an empty list has no elements to test) —
  mirror `find_index`'s existing "on empty list returns -1 and never
  calls fn" test shape.
- `find_last_index([1, 2, 2, 3], fn(n) { return n == 2; });` is `2` (the
  later of the two matching indices, not the first) — the case that
  specifically distinguishes this from `find_index`.
- `find_last_index(5, fn(n) { return true; });` (a non-list first
  argument) raises `CinderRuntimeError` naming `find_last_index` and
  `number` in the message.
- `find_last_index([1, 2], 5);` (a non-function second argument) raises
  `CinderRuntimeError` naming `find_last_index` and `number` in the
  message.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `find_index`, see
current line numbers — shift if earlier tasks this cycle landed first),
`tests/test_builtins.py`. Once merged, `README.md`'s Builtins bullet
needs `find_last_index` added near `find_index` — leave that to the
Architect's next grooming pass, not this task.

---

## 6. Exponentiation operator `**`

Build: a new binary operator `**` for exponentiation, right-associative,
binding tighter than `*`/`/`/`%` and looser than unary (`-`/`not`/`~`) —
Cinder has had a `pow()` builtin all along but no infix syntax for it,
the same kind of gap `product`/`sum` closed on the stdlib side. Scope
this as the operator only: **no** `**=` compound-assignment form in this
task (every other arithmetic operator's `**=`-shaped sibling was added
in lockstep with its base operator, but bundling that here as well would
make this a two-feature task — leave `**=` as a natural, separately-
scoped follow-up once `**` itself exists, same reasoning the `?.` task
above uses to defer full-chain propagation).

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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
