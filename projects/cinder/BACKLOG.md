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

## 1. Standard library: `is_isogram` — no-repeated-letter predicate [claimed 2026-08-12T14:34:50Z]

Build: add `is_isogram(s)` to `cinder/builtins.py`, registered right
after `_is_blank` (search for `def _is_blank`) — a fresh breadth task
queued after the map-destructuring rest element depth work per
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

## 2. Language: rest element in plain-assignment map-destructuring (`{a, ...rest} = expr;`)

Build: close the gap the map-destructuring rest element task (rest
element for map-destructuring `let`/`for`/`fn` patterns, landed via PR
#229) deliberately left open. That task's own scope note says it
explicitly: "the plain-assignment map-destructuring form (`{a, b} =
expr;`) is completely unaffected — it does not gain `...rest` support
in this task", since that form parses via its own inlined speculative
parser (`_try_map_destructure_assign_statement` in `cinder/parser.py`,
search for it) rather than the shared `_destructure_map_pattern`
helper that task changed. This is that deferred follow-up — the depth
task after task 1's breadth work (`is_isogram`) per `PROJECT.md`'s
breadth-vs-depth policy. Verified today: `let a = 1; let rest = 2;
{a, ...rest} = {"a": 1, "b": 2};` raises `ParseError` `"expected ';'
after expression, found ','"` — the pattern parse silently bails out
of `_try_map_destructure_assign_statement` on the unexpected `...`
token and falls through to the `_block()` fallback, which is what
actually raises that (unrelated-looking) error.

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
identical message text `_destructure_list_pattern` and
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

No `cinder/interpreter.py` changes needed: the map-destructuring rest
element task already threads `expr.rest` through
`_evaluate_destructure_assign`'s `is_map` branch into
`_bind_map_destructure` (verify this is still true when you pick up
this task).

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

## 3. Standard library: `levenshtein_distance` — string edit distance

Build: add `levenshtein_distance(a, b)` to `cinder/builtins.py`,
registered right after `_is_permutation` (search for `def
_is_permutation`) — the breadth task after task 2's depth work
(plain-assignment map-destructuring rest element) per `PROJECT.md`'s
breadth-vs-depth policy. It sits next to `is_anagram`/`is_rotation`/
`is_permutation` as one more two-string comparison, but unlike that
whole boolean-predicate cluster it returns a number: the minimum
count of single-character insertions, deletions, and substitutions
needed to turn `a` into `b` (the classic Levenshtein edit distance).
This is the project's first dynamic-programming builtin, and a third
distinct implementation technique for the string-comparison family
alongside `is_balanced`'s stack scan and `is_isogram`'s frequency-set
check — deliberately picked to keep diversifying rather than add one
more `Counter`/doubled-string delegation.

Implement with the standard row-by-row DP table, kept to a single
rolling 1-D list rather than a full 2-D matrix (no need for the whole
table, only the previous row, to compute the final distance):

```python
def _levenshtein_distance(arguments: list, line: int, column: int) -> object:
    _require_arity("levenshtein_distance", arguments, 2, line, column)
    string1, string2 = arguments
    if not isinstance(string1, str):
        raise CinderRuntimeError(
            f"levenshtein_distance() requires a string as its first argument, got {type_name(string1)}",
            line, column,
        )
    if not isinstance(string2, str):
        raise CinderRuntimeError(
            f"levenshtein_distance() requires a string as its second argument, got {type_name(string2)}",
            line, column,
        )
    previous_row = list(range(len(string2) + 1))
    for i, char1 in enumerate(string1, start=1):
        current_row = [i] + [0] * len(string2)
        for j, char2 in enumerate(string2, start=1):
            current_row[j] = min(
                current_row[j - 1] + 1,
                previous_row[j] + 1,
                previous_row[j - 1] + (0 if char1 == char2 else 1),
            )
        previous_row = current_row
    return previous_row[-1]
```

Model the arity/type-checking exactly on `_is_anagram`'s two-argument
"first argument"/"second argument" message shape (not
`_is_pangram`/`_is_balanced`'s single-argument phrasing — there are
two arguments here), matching the code above verbatim.

Acceptance criteria:
- `levenshtein_distance("kitten", "sitting");` is `3` — the classic
  textbook example (substitute `k`->`s`, `e`->`i`, insert `g`).
- `levenshtein_distance("", "");` is `0` — two empty strings need no
  edits.
- `levenshtein_distance("abc", "");` is `3` and
  `levenshtein_distance("", "abc");` is `3` — turning a string into
  the empty one (or vice versa) costs one deletion/insertion per
  character.
- `levenshtein_distance("abc", "abc");` is `0` — identical strings
  need no edits.
- `levenshtein_distance("a", "b");` is `1` — a single substitution.
- `levenshtein_distance("flaw", "lawn");` is `2` — a second
  well-known example distinct from the textbook one (delete the
  leading `f` to get `"law"`, then insert a trailing `n`).
- `levenshtein_distance("abc", "abx");` is `1` — a single
  substitution in the middle of otherwise-equal strings.
- Not symmetric in general but *is* symmetric for this builtin (edit
  distance is a metric): `levenshtein_distance("abc", "xyz");` equals
  `levenshtein_distance("xyz", "abc");` (both `3`) — worth a test
  since a buggy insert/delete-cost swap could break symmetry silently.
- `levenshtein_distance(5, "a");` raises `CinderRuntimeError` matching
  `"levenshtein_distance() requires a string as its first argument,
  got int"`.
- `levenshtein_distance("a", true);` raises `CinderRuntimeError`
  matching `"levenshtein_distance() requires a string as its second
  argument, got bool"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_permutation`,
see current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `levenshtein_distance` added near
`is_anagram`/`is_rotation`/`is_permutation`, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## 4. Language: chained comparison operators (`a < b < c`)

Build: the depth task after task 3's breadth work (`levenshtein_distance`)
per `PROJECT.md`'s breadth-vs-depth policy. `cinder/parser.py`'s
`_comparison()` (search for `def _comparison`) currently left-folds any
run of comparison operators into nested `Binary` nodes: `1 < 2 < 3`
parses as `Binary(Binary(1, <, 2), <, 3)`, which *evaluates* as
`(1 < 2) < 3` = `true < 3`. Since `_compare` (search for `def
_compare`) never accepts a `bool` operand (`_is_number` explicitly
excludes `bool`, matching `is_int`'s own bool-exclusion), this means
every 2-or-more-operator chain built purely from `<`/`<=`/`>`/`>=`
*always* raises `CinderRuntimeError` `"unsupported operand types for
comparison: bool and {type}"` today, with no exception — verified by
running `python3 -m cinder.cli eval 'print(1 < 2 < 3);'`, which raises
exactly that. There is no existing program this task could break: a
pure ordering-operator chain of length 2+ has exactly one possible
outcome today (a guaranteed runtime error), so turning it into a
meaningful value is strictly additive. (`grep` confirms no test in
`tests/` currently exercises this shape.)

Scope this to the four *ordering* operators only — `<`, `<=`, `>`,
`>=` — and leave `==`/`!=` chaining completely alone. `_COMPARISON`
today bundles `EQEQ`/`BANGEQ` in with the four ordering operators at
the same precedence tier, so e.g. `1 == 1 == 1` already parses via the
same left-fold and today evaluates to `false` (`(1==1)==1` =
`true==1` = `false`, since `values_equal` treats `bool`/`int` as
different types). That outcome is well-defined (not an error) and
`grep`-confirmed untested, but changing it is out of scope for this
task — mixing an equality operator anywhere into a comparison run
must fall back to *exactly* today's left-fold `Binary` chaining,
completely unchanged. Only a run of two-or-more operators drawn
*purely* from `{<, <=, >, >=}` should get new behavior.

New behavior: `a < b < c` (and longer chains, and mixes within the
ordering set like `a < b <= c`) evaluates as `a < b and b < c` —
each operand evaluated **exactly once**, left to right, and the whole
chain **short-circuits** the instant one pairwise comparison is
`false` (later operands are never evaluated at all). This is the same
single-evaluation discipline `IndexCompoundAssign` already documents
at the top of `cinder/parser.py` ("`obj`/`index` are each evaluated
exactly once at runtime... not `IndexAssign` wrapping a `Binary`... that
would evaluate the sub-expressions twice") and the same short-circuit
family `and`/`or`/`??` already belong to.

In `cinder/ast_nodes.py`: add a new frozen dataclass `ChainedComparison`
next to `Binary`/`Logical` (alphabetical placement, matching the file's
existing ordering): `operands: list` (the N+1 sub-expressions),
`operators: list` (the N operator `Token`s between them), `line: int`,
`column: int`.

In `cinder/parser.py`: add `TokenType.LT, TokenType.LTEQ, TokenType.GT,
TokenType.GTEQ` as a new `_ORDERING = {...}` module-level set next to
`_COMPARISON` (mirror its literal-set style). Rewrite `_comparison()`
to first collect the *entire* run of comparison operators (not fold
as it goes): `operands = [self._bitor()]`; `operators = []`; while
the next token's type is in `_COMPARISON`, advance it into `operators`
and parse another `self._bitor()` into `operands`. If `operators` is
empty, return `operands[0]` unchanged (today's no-comparison case). If
`len(operators) >= 2` and every operator's type is in `_ORDERING`,
return `ChainedComparison(operands, operators, operators[0].line,
operators[0].column)`. Otherwise (a single operator of any kind, or a
run that mixes in `EQEQ`/`BANGEQ`), reproduce today's exact left-fold:
`result = operands[0]`; for each `(operator, right)` pair walking
`operators`/`operands[1:]` in lockstep, `result = Binary(result,
operator, right)`; return `result`. Add `ChainedComparison` to the
`from cinder.ast_nodes import (...)` block (alphabetical).

In `cinder/interpreter.py`: add a dispatch arm for `ChainedComparison`
in `evaluate()` next to the existing `Binary`/`Logical` arms, calling a
new `_evaluate_chained_comparison(expr, env)`. Implement it by
evaluating `expr.operands[0]` into `left`, then for each `(operator,
operand)` pair walking `expr.operators`/`expr.operands[1:]` in
lockstep: evaluate `operand` into `right`, call the existing
`self._compare(operator, left, right, operator.type)` (search for `def
_compare` — already returns `bool` and already raises
`CinderRuntimeError` `"unsupported operand types for comparison: ..."`
on incomparable operands, reused verbatim, no new error message
needed), and if it returns `False`, return `False` immediately without
evaluating any further operands (the short-circuit); otherwise set
`left = right` and continue to the next pair. If every pairwise
comparison succeeds, return `True`. Add `ChainedComparison` to
`interpreter.py`'s own `from cinder.ast_nodes import (...)` block
(alphabetical).

Acceptance criteria:
- `print(1 < 2 < 3);` prints `true` — the motivating case that raises
  `CinderRuntimeError` today.
- `print(1 < 2 < 3 < 4);` prints `true` — a three-operator chain.
- `print(3 < 2 < 100);` prints `false` — the first pairwise comparison
  already fails, short-circuiting before the second is even attempted.
- `print(1 < 2 <= 2 < 3);` prints `true` — mixed ordering operators
  within one chain.
- A single-evaluation/short-circuit proof using a side effect: `let
  calls = []; fn track(label, value) { push(calls, label); return
  value; } print(track("a", 5) < track("b", 3) < track("c", 10));
  print(calls);` prints `false` then `["a", "b"]` — `track("c", 10)`
  is never called because `5 < 3` already fails, and each of `a`/`b`
  is evaluated exactly once (not twice, despite `b`'s value
  participating in only one comparison here but potentially two in a
  longer chain).
- `print(1 < "a" < 3);` raises `CinderRuntimeError` matching
  `"unsupported operand types for comparison: int and str"` — the
  existing `_compare` type-check fires mid-chain, same message shape
  chained comparisons reuse verbatim from the unchanged two-operand
  case.
- A single comparison (`print(1 < 2);`) is completely unaffected — no
  `ChainedComparison` node is ever built for it, same `Binary` AST and
  behavior as before this task.
- Chains containing `==`/`!=` are completely unaffected — `print(1 ==
  1 == 1);` still prints `false` and `print(1 != 2 != 3);` still
  prints `true`, exactly today's left-fold behavior, not new
  chained-equality semantics.
- `print(1 < 2 == true);` (a single `<` mixed with a single `==`)
  still parses and evaluates via today's exact left-fold path (`(1 <
  2) == true`, prints `true`) — mixing operator kinds does not trigger
  `ChainedComparison`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (new `ChainedComparison` node),
`cinder/parser.py` (`_comparison` and its import block),
`cinder/interpreter.py` (`evaluate`, new
`_evaluate_chained_comparison`, and its import block),
`tests/test_parser.py`, `tests/test_interpreter.py`. Once merged,
`README.md`'s Operators bullet needs chained comparisons mentioned,
and `PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Standard library: `is_automorphic` — n² ends with n predicate

Build: add `is_automorphic(n)` to `cinder/builtins.py`, registered
right after `is_deficient` (search for `def _is_deficient`) — the
breadth task after task 4's depth work (chained comparison operators)
per `PROJECT.md`'s breadth-vs-depth policy. It joins the
`is_perfect_square`/`is_armstrong`/`is_leap_year`/`is_perfect_number`/
`is_abundant`/`is_deficient` integer-property cluster as one more
digit-based classification: an integer `n` is automorphic when its
square, written in decimal, ends with `n` itself (e.g. `5² = 25` ends
in `5`; `6² = 36` ends in `6`; `25² = 625` ends in `25`; `76² = 5776`
ends in `76`).

Implement as a plain string check rather than modular arithmetic —
`str(n * n).endswith(str(n))` — mirroring how `_is_palindrome_number`
and `_is_armstrong` already work with `str(value)` rather than
digit-by-digit math. Model the arity/type-checking exactly on
`_is_armstrong`'s structure: `_require_arity("is_automorphic",
arguments, 1, line, column)`, then `value = _require_int("is_automorphic",
arguments[0], line, column)` (reusing the shared `_require_int` helper,
same as `_is_perfect_square`/`_is_armstrong`/`_is_leap_year`/
`_is_perfect_number`/`_is_abundant`/`_is_deficient` already do — do
**not** hand-roll a separate `isinstance` check). Negative input
returns `false` without raising, matching every sibling in this
cluster's convention (`is_perfect_square`, `is_armstrong`,
`is_perfect_number`, `is_abundant`, `is_deficient` all answer `false`
on negative input rather than treating it as a domain error) — the
`str(n * n).endswith(str(n))` check would also mishandle a negative
`n`'s leading `-` if allowed through, so guard it the same way those
five already guard theirs, before doing the string check.

Acceptance criteria:
- `is_automorphic(5);` is `true` — `5² = 25` ends in `5`.
- `is_automorphic(6);` is `true` — `6² = 36` ends in `6`.
- `is_automorphic(25);` is `true` — `25² = 625` ends in `25`.
- `is_automorphic(76);` is `true` — `76² = 5776` ends in `76`.
- `is_automorphic(0);` is `true` — `0² = 0` ends in `0`.
- `is_automorphic(1);` is `true` — `1² = 1` ends in `1`.
- `is_automorphic(7);` is `false` — `7² = 49` does not end in `7`.
- `is_automorphic(10);` is `false` — `10² = 100` does not end in `10`.
- `is_automorphic(-5);` is `false` — negative input answers `false`
  without raising, matching the rest of the cluster.
- `is_automorphic(5.0);` raises `CinderRuntimeError` matching
  `"is_automorphic() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_automorphic(true);` raises `CinderRuntimeError` matching
  `"is_automorphic() requires an int, got bool"` — `_require_int`
  already excludes `bool` from passing as an int, same as `is_int`'s
  own bool-exclusion.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError`
  with line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_deficient`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py`. Once merged, `README.md`'s Builtins
bullet needs `is_automorphic` added near
`is_perfect_number`/`is_abundant`/`is_deficient`, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
