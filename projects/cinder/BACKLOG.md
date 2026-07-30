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

## 1. Standard library: `zip_longest` for lists

Build: add `zip_longest(list1, list2, fill)` to `cinder/builtins.py` —
like `zip` (`_zip` at `cinder/builtins.py:1584-1597`, which truncates to
the shorter list via Python's own `zip`) but pads the shorter list with
`fill` instead of truncating, so the result always has
`max(len(list1), len(list2))` pairs. Reuse the same two-list validation
style `_zip` already uses (a `list` check on each argument, not
`_require_two_lists` since that helper is arity-2 only and this builtin
is arity-3) plus `_require_arity("zip_longest", arguments, 3, line,
column)`. Implement with `itertools.zip_longest(list1, list2,
fillvalue=fill)` (stdlib `itertools` — no new dependency, already usable
via Python's standard library) wrapped in a list comprehension producing
`[a, b]` pairs, mirroring `_zip`'s `[[a, b] for a, b in ...]` shape.

Acceptance criteria:
- `zip_longest([1, 2, 3], ["a", "b"], nil)` is `[[1, "a"], [2, "b"], [3,
  nil]]` — shorter list padded with `fill` (here `nil`) once it runs out.
- `zip_longest([1], [1, 2, 3], 0)` is `[[1, 1], [0, 2], [0, 3]]` — padding
  works symmetrically when the *first* list is shorter.
- `zip_longest([1, 2], [1, 2], "x")` is `[[1, 1], [2, 2]]` — equal-length
  lists behave exactly like `zip`, `fill` unused.
- `zip_longest([], [], 0)` is `[]`.
- `zip_longest([], [1, 2], 0)` is `[[0, 1], [0, 2]]`.
- A non-list first or second argument raises `CinderRuntimeError` with
  line/column (mirror `_zip`'s two separate checks/messages).
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 2. Standard library: `group_consecutive` for lists

Build: add `group_consecutive(list)` to `cinder/builtins.py` — groups
*adjacent* equal elements into sublists, i.e. run-length grouping (the
list-native cousin of `group_by`, which groups by key across the whole
list regardless of position — `_group_by` at
`cinder/builtins.py:1781-...`). Equality between elements uses the same
`==` semantics Cinder's interpreter already applies to values (structural
equality for lists/maps, value equality for numbers/strings/bools/nil) —
implement by iterating once, comparing each element to the last element
of the current run with plain Python `==` (safe here since Cinder values
are plain Python `int`/`float`/`str`/`bool`/`None`/`list`/`dict` at
runtime, same assumption `unique`/`distinct_by` already rely on), and
starting a new run on a mismatch. Validate with
`_require_arity("group_consecutive", arguments, 1, line, column)` then a
`list` check, mirroring `_flatten`'s single-list validation style
(`cinder/builtins.py:1506-...`).

Acceptance criteria:
- `group_consecutive([1, 1, 2, 2, 2, 1])` is `[[1, 1], [2, 2, 2], [1]]` —
  note the trailing `1` is its own group since it's not adjacent to the
  earlier `1, 1` run.
- `group_consecutive([1, 2, 3])` is `[[1], [2], [3]]` — no adjacent
  duplicates means every element is its own singleton group.
- `group_consecutive([])` is `[]`.
- `group_consecutive(["a", "a", "a"])` is `[["a", "a", "a"]]` — a single
  run covering the whole list.
- `group_consecutive([[1, 2], [1, 2], [3]])` is `[[[1, 2], [1, 2]],
  [[3]]]` — structural equality groups equal *list* elements adjacently,
  not just primitives.
- A non-list argument raises `CinderRuntimeError` with line/column.
- Wrong arity raises `CinderRuntimeError` with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py`, `tests/test_builtins.py`.

---

## 3. Nil-coalescing compound assignment: `??=`

Build: add `x ??= expr;` as a compound-assignment sibling to the existing
set (`+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`, handled
via `_COMPOUND_ASSIGN_OPS` in `cinder/parser.py:138-149`) that assigns
`expr` to `x` only when `x` is currently `nil`, mirroring the existing
`??` nil-coalescing operator (`_nullish` in `cinder/parser.py:621-627`,
lexed in `cinder/lexer.py:351-357`'s `_question`, evaluated as a
short-circuiting `Logical` node at `cinder/interpreter.py:577` — `right`
is only evaluated when `left` is `nil`, unlike `or` which short-circuits
on any truthy value). `??=` cannot reuse the existing compound-assign
desugaring path used by `+=`/etc. as-is: that path wraps the target and
value in a `Binary` node (`cinder/parser.py:584`:
`binary = Binary(expr, binary_operator, value)`), but `Binary` always
evaluates both operands eagerly — `x ??= f()` must not call `f()` when
`x` is already non-nil, exactly like `??` doesn't evaluate its right side
unnecessarily. Instead, when the new `QQEQ` token is seen, desugar to
`Assign(expr.name, Logical(expr, qq_operator, value), ...)`, where
`qq_operator` is a synthetic `Token(TokenType.QUESTION_QUESTION, "??",
None, op_token.line, op_token.column)` — mirroring how the existing path
builds `binary_operator` from `op_token` at `cinder/parser.py:576-582`,
but typed `QUESTION_QUESTION` (not `QQEQ`) since `_evaluate_logical`
(`cinder/interpreter.py:567-581`) dispatches on `expr.operator.type` and
only recognizes `OR`/`AND`/`QUESTION_QUESTION` — a `Logical` node
carrying `QQEQ` would hit that function's final `raise TypeError`. This
is the same `Logical` shape `??` itself produces, just constructed
directly in `_assignment()` rather than routed through the generic
`_COMPOUND_ASSIGN_OPS` dict/`Binary` path (since that dict maps each
compound-assign token to a plain binary operator token, which doesn't
fit a short-circuiting `Logical` node).
Add `QQEQ = auto()` to `cinder/tokens.py` (near `QUESTION_QUESTION`), and
teach `cinder/lexer.py`'s `_question` to check for a third `=` after
matching the second `?` (i.e. `??=` scans as one token, not `??` followed
by `=`) — mirror how `_question` already uses `self._match("?")` to
distinguish `?` from `??`, adding a further `self._match("=")` check once
`??` has matched to decide between emitting `QUESTION_QUESTION` and the
new `QQEQ`. Only an `Identifier` target is supported (matching the
arithmetic compound-assign ops' identifier-only restriction noted at
`cinder/parser.py:150-151` — `??=` is not added to
`_INDEX_TARGET_COMPOUND_ASSIGN_OPS`, so `xs[0] ??= 1` is out of scope for
this task and should raise the same "invalid assignment target"
`ParseError` an unsupported index target already raises for e.g. `xs[0]
%= 2`).

Acceptance criteria:
- `let x = nil; x ??= 5; x` is `5`.
- `let x = 1; x ??= 5; x` is `1` — non-nil `x` is left untouched.
- `let x = false; x ??= 5; x` is `false` — `false` is not `nil`, so it is
  *not* replaced (contrast with `x ||= 5`-style truthiness, which this
  language doesn't have; this pins that `??=` checks nil-ness only).
- `let calls = 0; fn bump() { calls = calls + 1; return 99; } let x = 1;
  x ??= bump(); calls` is `0` — the right-hand side is not evaluated when
  the target is already non-nil (short-circuiting, same as `??`).
- `let calls = 0; fn bump() { calls = calls + 1; return 99; } let x = nil;
  x ??= bump(); calls` is `1` and `x` is `99` — the right-hand side *is*
  evaluated exactly once when the target is `nil`.
- `let xs = [nil]; xs[0] ??= 1;` raises a `ParseError` ("invalid
  assignment target") with line/column — index targets are out of scope
  for this task.
- Full test suite passes.

Likely files: `cinder/tokens.py`, `cinder/lexer.py`, `cinder/parser.py`,
`tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_interpreter.py`.

---

## 4. Standard library: `sliding_window` for lists

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

## 5. Standard library: `deep_equal` for structural equality

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

## 6. CLI: `-e`/`--eval` flag to run an inline snippet

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

## 7. "Did you mean...?" suggestions for undefined-name errors

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

## 8. Labeled `break`/`continue` for nested loops

Build: let a loop be prefixed with a label — `outer: while (cond) {
... }`, `outer: for (x in xs) { ... }`, `outer: for (let i = 0; ...; ...)
{ ... }`, `outer: do { ... } while (cond);` — and let `break outer;`/
`continue outer;` target that specific enclosing loop instead of the
innermost one, e.g. to break out of a nested loop from inside it in one
step. Add a `LabelStmt`-style optional field instead of a new
wrapper node: add `label: str | None` to each loop AST node
(`WhileStmt`, `ForStmt`, `ForCStmt`, `DoWhileStmt` — check
`cinder/ast_nodes.py` first for the current set of loop nodes, since
`ForCStmt` is mid-flight on PR #121 as of this writing), defaulting to
`None`
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

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
