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

## 1. Standard library: `sliding_window` for lists

Build: add `sliding_window(list, size)` to `cinder/builtins.py` — like
`chunk` (`_chunk` at `cinder/builtins.py:1599-1615`) but windows
*overlap* by `size - 1` elements instead of partitioning the list into
disjoint pieces, i.e. every contiguous run of `size` elements, sliding
forward by one each time (`[list[i:i+size] for i in range(0, len(list) -
size + 1)]`). Mirror `_chunk`'s validation exactly: `_require_arity`,
a `list` check on the first argument, an `int`-and-not-`bool` check on
`size` (`isinstance(size, int) and not isinstance(size, bool)`, following
`cinder/builtins.py:1607`'s existing pattern since Cinder's runtime
booleans are Python `bool`, a subclass of `int`), and a positive-size
check — reusing the exact same error-message phrasing `_chunk` uses with
`sliding_window` substituted for `chunk`. Unlike `chunk`, a `size` larger
than the list's length is not an error: it simply produces zero windows
(`sliding_window([1, 2], 5)` is `[]`), matching what the range-based
comprehension above naturally does when `len(list) - size + 1 <= 0` —
add an explicit test pinning this rather than special-casing it as an
error.

Acceptance criteria:
- `sliding_window([1, 2, 3, 4], 2)` is `[[1, 2], [2, 3], [3, 4]]`.
- `sliding_window([1, 2, 3, 4], 3)` is `[[1, 2, 3], [2, 3, 4]]`.
- `sliding_window([1, 2, 3], 1)` is `[[1], [2], [3]]`.
- `sliding_window([1, 2], 5)` is `[]` — window larger than the list
  produces no windows, not an error.
- `sliding_window([], 1)` is `[]`.
- A non-list first argument raises `CinderRuntimeError` with line/column.
- A non-int, or int-but-`bool`, `size` raises `CinderRuntimeError` with
  line/column.
- A zero or negative `size` raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 2. Standard library: `deep_equal` for structural equality

Build: add `deep_equal(a, b)` to `cinder/builtins.py` — recursive
structural equality for lists and maps, unlike plain `==` which (per
Cinder's runtime representation of lists/maps as Python `list`/`dict`)
already recurses correctly for *value* equality but this builtin exists
to give scripts an explicit, self-documenting name for that comparison
rather than relying on `==`'s incidental behavior, and to nail down
edge cases `==` leaves ambiguous. Validate with `_require_arity
("deep_equal", arguments, 2, line, column)` — no type restriction on
`a`/`b`, any two values are comparable. Implement recursively: two lists
are equal iff same length and every element is `deep_equal` pairwise
(not Python's `==`, so nested list/map structures recurse through this
same function rather than falling back to `==`'s own recursion); two
maps are equal iff same set of keys and every value is `deep_equal`
pairwise (key order does not matter); two non-collection values
(numbers, strings, bools, `nil`) are equal iff `==` says so, with one
deliberate carve-out: numeric equality does not distinguish `int` from
`float` (`deep_equal(1, 1.0)` is `true`, matching Cinder's own `==`
between numbers), but `bool` is not treated as numeric here even though
Python's `bool` subclasses `int` — `deep_equal(true, 1)` must be `false`
(check `isinstance(x, bool)` before falling into the numeric-equality
branch, mirroring the existing `isinstance(size, int) and not
isinstance(size, bool)` guard style used elsewhere, e.g. `_chunk`).

Acceptance criteria:
- `deep_equal([1, [2, 3]], [1, [2, 3]])` is `true`.
- `deep_equal([1, [2, 3]], [1, [2, 4]])` is `false`.
- `deep_equal({"a": 1, "b": {"c": 2}}, {"b": {"c": 2}, "a": 1})` is
  `true` — key order does not matter, nested map values recurse.
- `deep_equal({"a": 1}, {"a": 1, "b": 2})` is `false` — different key
  sets.
- `deep_equal(1, 1.0)` is `true` — numeric equality ignores int/float.
- `deep_equal(true, 1)` is `false` — bools are never equal to numbers,
  even though `1` is truthy-adjacent.
- `deep_equal([1, 2], [1, 2, 3])` is `false` — different lengths.
- `deep_equal("x", "x")` is `true`; `deep_equal(nil, nil)` is `true`.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. CLI: `-e`/`--eval` flag to run an inline snippet

Build: add an `eval` mode to `cinder/cli.py` so a one-line script can be
run without creating a `.cin` file, e.g. `python3 -m cinder.cli eval
'print(1 + 2);'`. Add a third subparser alongside `run`/`repl` in
`build_parser` (`cinder/cli.py:19-27`): `subparsers.add_parser("eval",
help=...)` taking a single positional `source` argument (the snippet
text itself, not a path). Factor the shared lex/parse/execute pipeline
out of `run_file` (`cinder/cli.py:30-35`) into a helper — e.g.
`_run_source(source: str) -> None` containing exactly `run_file`'s
current body from `tokenize(source)` onward — so `run_file` becomes
`_run_source(open(path).read())` and the new eval path calls
`_run_source(args.source)` directly, without needing a temp file.
Wire the new `"eval"` branch into `main` (`cinder/cli.py:39-53`)
alongside the existing `"run"`/`"repl"` branches, reusing the exact
same `CinderError` catch-and-format block `run` already uses (line/
column formatting) — but the error-message prefix that currently reads
`f"{args.file}:{e.line}:{e.column}: ..."` should read `f"<eval>:
{e.line}:{e.column}: ..."` for the eval path, since there's no file
name to print. `OSError` handling is `run`-only (there's no file to
fail to open in eval mode, so don't wrap `_run_source` in an `OSError`
catch for the eval branch).

Acceptance criteria:
- `python3 -m cinder.cli eval 'print(1 + 2);'` prints `3` and exits 0.
- `python3 -m cinder.cli eval 'let x = 1; x = 2; print(x);'` prints `2`
  — multi-statement snippets work, not just single expressions.
- A runtime error in the snippet (e.g. `eval 'print(undefined_name);'`)
  prints `<eval>:1:7: undefined name 'undefined_name'` (line/column
  matching the snippet's own coordinates, prefix literally `<eval>`)
  to stderr and exits 1 — same formatting `run` uses for `CinderError`,
  minus the filename.
- A parse error in the snippet exits 1 with a `<eval>`-prefixed message,
  matching `run`'s parse-error handling.
- `run_file` against an existing example (e.g. `examples/fizzbuzz.cin`)
  still behaves identically post-refactor — add/keep a regression test
  covering `run` end to end so the `_run_source` extraction didn't
  change its behavior.
- Full test suite passes.

Likely files: `cinder/cli.py`, `tests/test_cli.py` (create if it does
not yet exist — check first).

---

## 4. "Did you mean...?" suggestions for undefined-name errors

Build: when `_evaluate_identifier` or `_evaluate_assign`
(`cinder/interpreter.py:527-543`) raise `undefined name {name!r}` after
an `Environment.get`/`assign` `KeyError`, append a suggestion when a
close match exists among the names currently in scope. Add a method to
`Environment` (`cinder/interpreter.py:129-154`) — e.g. `all_names(self)
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

## 5. Labeled `break`/`continue` for nested loops

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
(`cinder/interpreter.py:88-93`) an optional `label: str | None`
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

## 6. Standard library: `key_by` for lists

Build: add `key_by(list, fn)` to `cinder/builtins.py` — indexes a list
into a map keyed by `fn(item)`, the "one winner per key" counterpart to
`group_by` (`_group_by` at `cinder/builtins.py:1876-1897`, which buckets
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
