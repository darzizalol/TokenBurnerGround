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

## 1. Language: flat map patterns in `match` arms (`{a, b} => ...`)

Build: `match` currently has a flat *list* pattern (`[a, b] => ...`, PR
#316) that destructures a list subject by shape, but no equivalent for a
*map* subject — `let`/assignment destructuring already has a rich map
pattern (`let {a, b} = expr;`, with nesting, rename, rest, and defaults —
`cinder/parser.py`'s `_destructure_map_pattern`), but `match` arms have no
way to test "is this a map with these keys" and bind their values in one
step, the same gap flat list patterns closed for lists in PR #316. This
task closes the minimal slice of that gap — bare bound-identifier keys
only, no nesting, no rename, no rest, no defaults — mirroring exactly how
flat list patterns themselves started minimal before literal elements and
rest capture extended them incrementally. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 });'
# -> <eval>:1:34: expected a literal, identifier, or '_' in match pattern, found '{'
```

**Scope note:** only bare identifier keys are accepted per entry (`{a, b}`,
where the key name and the bound name are always the same — no `{a: x}`
rename, which is a real but separate follow-up gap, the same "prove the
flat form out first" staging `nth_triangular` → `nth_pentagonal` and flat
list patterns → literal list elements both already used). No nested
patterns (`{a: {b}}` or `{a: [b, c]}`), no rest capture (`{a, ...rest}`),
and no default values (`{a, b = 5}`) — all real gaps, all left for future
tasks once this one proves the form out, matching how rest capture in
*list* patterns (PR #324) was itself staged as a separate task from
flat list patterns. A map pattern matches if the subject is a map (dict)
containing *every* named key — extra unnamed keys in the subject are
ignored, and a missing key or non-map subject falls through to the next
arm (does not raise), the same "falls through, doesn't raise" philosophy
flat list patterns (shape mismatch) and range patterns (non-numeric
subject) already established for pattern-kind mismatches in `match`.

**Ordering note:** rest capture in list patterns (PR #324) has already
landed — `MatchArm` already has a `list_rest` field as its fifth
positional slot, so append the new `map_pattern` field as the *sixth*
slot, not the fifth shown below, and adjust the one `MatchArm(...)` call
site this task touches accordingly (every other call site in the parser
already uses the trailing-default form and needs no change either way).

Today's `_match_arm` (`cinder/parser.py`, search `def _match_arm`) checks
`TokenType.LBRACKET` for a list pattern before falling through to
`_match_pattern`; widen it to also check `TokenType.LBRACE` for a map
pattern, mirroring the list-pattern branch exactly:
```python
    def _match_arm(self) -> "list[MatchArm]":
        if self._check(TokenType.LBRACKET):
            list_pattern = self._match_list_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return [MatchArm(None, body, None, list_pattern, None)]
        if self._check(TokenType.LBRACE):
            map_pattern = self._match_map_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return [MatchArm(None, body, None, None, None, map_pattern)]
        ...  # unchanged below

    def _match_map_pattern(self) -> "list[str]":
        self._advance()  # consume '{'
        names: "list[str]" = []
        if not self._check(TokenType.RBRACE):
            names.append(self._match_map_pattern_name())
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._match_map_pattern_name())
        self._consume(TokenType.RBRACE, "'}' after map pattern")
        return names

    def _match_map_pattern_name(self) -> str:
        token = self._consume(
            TokenType.IDENTIFIER, "identifier inside map pattern"
        )
        return token.lexeme
```
`{` is unambiguous at this position — no other `_match_arm` production
starts with `{`, so no lookahead conflict with the enclosing `match { ...
}` block itself (already consumed before `_match_arm` is ever called).

`MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) needs a new
field appended after `range_pattern` (appending, not inserting, keeps
every existing positional `MatchArm(...)` call site valid — see the
Ordering note above for the one exception):
```python
    map_pattern: "list[str] | None" = None
```

`_evaluate_match` (`cinder/interpreter.py`, search `def _evaluate_match`)
needs a new branch, modeled directly on the existing `list_pattern`
branch but testing key presence instead of length:
```python
            if arm.map_pattern is not None:
                if not isinstance(subject, dict) or not all(
                    key in subject for key in arm.map_pattern
                ):
                    continue
                arm_env = Environment(env)
                for key in arm.map_pattern:
                    arm_env.define(key, subject[key])
                return self.evaluate(arm.body, arm_env)
```
Place it alongside the existing `list_pattern`/`range_pattern` branches,
before the `arm.pattern is None` branch (order among the four branches
doesn't matter — they're mutually exclusive per arm).

Acceptance criteria:
- `match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 };` is `3`.
- `match ({"a": 1}) { {a, b} => a + b, _ => 0 };` is `0` — a missing key
  falls through without raising.
- `match ({"a": 1, "b": 2, "c": 3}) { {a, b} => a + b, _ => 0 };` is `3` —
  extra unnamed keys in the subject are ignored.
- `match ([1, 2]) { {a} => a, _ => "no" };` is `"no"` — a non-map subject
  falls through without raising.
- `match ({"a": 1}) { {a} => a, _ => 0 };` is `1` — a single-key pattern
  works too.
- `match ({}) { {} => "empty", _ => "no" };` is `"empty"` — an empty map
  pattern matches any map subject (vacuously, every key of the empty set
  is present).
- `match ({"a": 1, "b": 2}) { [a, b] => "list", {a, b} => a + b, _ => 0 };`
  is `3` — list and map patterns coexist as separate arms without
  interfering.
- `shape(parse('match (x) { {a, b} => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `map_pattern` as
  `["a", "b"]`.
- `match (x) { {1} => 0 };` (non-identifier inside a map pattern) raises
  `ParseError` matching `"expected identifier inside map pattern..."`
  (exact message per whatever `_consume`'s own error formatting produces).
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`), `cinder/parser.py`
(`_match_arm`, new `_match_map_pattern`/`_match_map_pattern_name`),
`cinder/interpreter.py` (`_evaluate_match`), `tests/test_parser.py` (the
`shape()` helper's `MatchExpr` branch needs `arm.map_pattern` added to its
output tuple; extend `class TestMatchExpression`), `tests/test_interpreter.py`
(extend `class TestMatchExpression` with the end-to-end cases above). Once
merged, `README.md`'s `match` expression bullet needs a map-pattern
description added near the flat-list-pattern one, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `combinations` — every r-length combination of a list

Build: `binomial(n, k)` already answers "how many r-length combinations
exist" and `power_set` (PR #321) already enumerates combinations of *every*
size at once — but there is no way to enumerate combinations of one
specific size, the exact "enumerate-vs-count" gap `binomial` has to
`power_set` itself, the same gap `permutations` (PR #325) closes for
orderings against `is_permutation`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(combinations([1, 2, 3], 2));'
# -> <eval>:1:7: undefined name 'combinations'
```

**Ordering note:** `permutations` (PR #325) has already landed — register
`combinations` directly after `permutations` instead of after `power_set`,
keeping the collection-helper cluster grouped together in the dict, same
adaptive placement every sibling task in this backlog already uses.

Add to `cinder/builtins.py`, registered right after `_power_set` (search `def
_power_set`; `itertools` is already imported at the top of this module — no
new import needed):
```python
def _combinations(arguments: list, line: int, column: int) -> object:
    _require_arity("combinations", arguments, 2, line, column)
    items, size = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"combinations() requires a list, got {type_name(items)}", line, column
        )
    if not isinstance(size, int) or isinstance(size, bool):
        raise CinderRuntimeError(
            f"combinations() requires an int size, got {type_name(size)}", line, column
        )
    if size < 0:
        raise CinderRuntimeError(
            "combinations() requires a non-negative size, domain error", line, column
        )
    return [list(combo) for combo in itertools.combinations(items, size)]
```
`itertools.combinations(items, size)` does the actual enumeration — the same
thin-wrapper composition style `power_set` uses for its own all-sizes loop and
`permutations` (PR #325) uses for `itertools.permutations`. Note
`itertools.combinations` already returns `[]` (not an error) when `size >
len(items)`, matching Python's own convention — no extra domain check needed
for that case. Also register the new dict entry (search `"power_set":
_power_set,`, add `"combinations": _combinations,` directly after it — or
directly after `"permutations": _permutations,`, which has already landed).

Acceptance criteria:
- `combinations([1, 2, 3], 2);` is `[[1, 2], [1, 3], [2, 3]]`.
- `combinations([1, 2, 3], 0);` is `[[]]`.
- `combinations([1, 2, 3], 3);` is `[[1, 2, 3]]`.
- `combinations([1, 2, 3], 4);` is `[]` — size greater than the list's length
  yields no combinations, not an error.
- `combinations([], 0);` is `[[]]`.
- `len(combinations(l, k));` is `binomial(len(l), k)` for `l` equal to
  `[1, 2, 3, 4, 5]` and every `k` from `0` to `5` — the standard
  combination-count identity, the same closed-form cross-check style
  `power_set`'s and `nth_hexagonal`'s acceptance criteria use.
- `combinations([1, 1], 1);` is `[[1], [1]]` — duplicate elements are not
  de-duplicated, matching `itertools.combinations`'s own by-position
  behavior (the same convention `permutations`' acceptance criteria uses).
- `combinations("ab", 1);` raises `CinderRuntimeError` matching
  `"combinations() requires a list, got string"`.
- `combinations([1, 2], "1");` raises `CinderRuntimeError` matching
  `"combinations() requires an int size, got string"`.
- `combinations([1, 2], -1);` raises `CinderRuntimeError` matching
  `"combinations() requires a non-negative size, domain error"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `power_set`/`permutations`,
see current line numbers — shift depending on which sibling tasks land
first), `tests/test_builtins.py` (model on `class TestPowerSet`, search that
name, for the list-validation, arity-error, and closed-form cross-check test
shapes). Once merged, `README.md`'s Builtins bullet needs `combinations`
added near `power_set`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to the
Architect's next grooming pass, not this task.

---

## 3. Standard library: `nth_heptagonal` — the k-th heptagonal number by position

Build: `is_heptagonal` already exists as a membership test, but Cinder has
no way to ask "what is the k-th heptagonal number" the way it can for
triangular numbers (`nth_triangular`, PR #313), pentagonal numbers
(`nth_pentagonal`, PR #319), and hexagonal numbers (`nth_hexagonal`, PR
#323) — the exact same "value-returning sibling of an `is_*` membership
test" pattern the figurate-number cluster's first three `nth_*` members
already establish, just for its fourth. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_heptagonal(5));'
# -> <eval>:1:7: undefined name 'nth_heptagonal'
```

Add to `cinder/builtins.py`, registered right after `_nth_hexagonal` (search
`def _nth_hexagonal`, immediately before `_is_prime`):
```python
def _nth_heptagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_heptagonal", arguments, 1, line, column)
    value = _require_int("nth_heptagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_heptagonal() requires a positive integer, domain error", line, column
        )
    return value * (5 * value - 3) // 2
```
`H(k) = k(5k - 3) / 2` is the standard closed form for the k-th heptagonal
number (cross-check: `_is_heptagonal` tests `40 * value + 9` for a perfect
square whose root is `≡ 7 (mod 10)`, the standard membership test derived
from this same closed form). This mirrors `_nth_triangular`'s,
`_nth_pentagonal`'s, and `_nth_hexagonal`'s shape exactly (arity check, int
check, domain check, one-line closed-form return) — a thin, direct
composition, not a new algorithm. Also register the new dict entry (search
`"nth_hexagonal": _nth_hexagonal,`, add `"nth_heptagonal":
_nth_heptagonal,` directly after it).

Acceptance criteria:
- `nth_heptagonal(1);` is `1`, `nth_heptagonal(2);` is `7`,
  `nth_heptagonal(3);` is `18`, `nth_heptagonal(4);` is `34` — the first
  four heptagonal numbers.
- `is_heptagonal(nth_heptagonal(k));` is `true` for every `k` from `1` to
  `100` — cross-checks the closed form against the existing membership
  test, the same style `nth_pentagonal`'s and `nth_hexagonal`'s acceptance
  criteria use.
- `nth_heptagonal(0);` and `nth_heptagonal(-1);` both raise
  `CinderRuntimeError` matching `"nth_heptagonal() requires a positive
  integer, domain error"`.
- `nth_heptagonal(1.5);` raises `CinderRuntimeError` matching
  `"nth_heptagonal() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `nth_hexagonal`, search
that name for the current line number), `tests/test_builtins.py` (model on
`class TestNthHexagonal`, search that name, for the domain-error, type-error,
and cross-check test shapes). Once merged, `README.md`'s Builtins bullet
needs `nth_heptagonal` added near `nth_hexagonal`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" bullet needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Language: negative bounds in range patterns (`-10..0 => "neg"`)

Build: negative literal patterns (PR #320) let a plain literal pattern be
negated (`match (-5) { -5 => "neg", _ => "pos" }`), but range patterns
(`1..10 => "small"`, PR #318) still can't — a range pattern's bounds are
parsed only from the `INT` branch of `_match_pattern`, which the `MINUS`
branch (added for negative literals) never falls into, so a range with a
negative start bound raises a `ParseError` at the following `..` instead of
parsing the range. Verify the gap, on current `main`:
```sh
python3 -m cinder.cli eval 'print(match (-5) { -10..0 => "neg", _ => "other" });'
# -> <eval>:1:23: expected '=>' after match pattern, found '..'
```

**Scope note:** only the numeric bounds themselves can be negative
(`-10..0`, `-10..=0`, `-10..-1`, `0..-1`) — this does not touch general
unary-minus *expressions* as bounds (only literal `INT`/`FLOAT` tokens
after a `-`, matching negative literal patterns' own restriction) and does
not touch multi-value combination with other pattern kinds, which is
already handled generically by `_match_arm`'s entry list.

Today's `_match_pattern` (`cinder/parser.py`, search `def _match_pattern`)
has a `MINUS` branch that consumes `-` then an `INT`/`FLOAT` literal and
returns immediately as a negated `Literal` pattern — it never checks for a
following `..`/`..=`. The `INT` branch (further down) is the only one that
checks for a range, and only ever builds an unnegated `Literal` start bound.
Refactor both branches to share a single "parse an optionally-negated
int-literal bound" helper, then have each check for a following range
operator:
```python
    def _match_pattern(self) -> "tuple[Expr | None, str | None, RangeExpr | None]":
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            self._advance()
            if token.lexeme == "_":
                return None, None, None
            return None, token.lexeme, None
        if token.type == TokenType.MINUS or token.type == TokenType.INT:
            start = self._match_pattern_bound()
            if self._check(TokenType.DOT_DOT) or self._check(TokenType.DOT_DOT_EQ):
                dots = self._advance()
                inclusive = dots.type is TokenType.DOT_DOT_EQ
                end = self._match_pattern_bound()
                return None, None, RangeExpr(start, end, dots.line, dots.column, inclusive)
            return start, None, None
        if token.type in (TokenType.FLOAT, TokenType.STRING):
            self._advance()
            return Literal(token.literal, token.line, token.column), None, None
        ...  # TRUE/FALSE/NIL branches unchanged below

    def _match_pattern_bound(self) -> Expr:
        token = self._peek()
        if token.type == TokenType.MINUS:
            minus = self._advance()
            value_token = self._peek()
            if value_token.type != TokenType.INT:
                raise ParseError(
                    "expected an int after '-' in match range pattern, "
                    f"found {self._describe(value_token)}",
                    value_token.line,
                    value_token.column,
                )
            self._advance()
            return Literal(-value_token.literal, minus.line, minus.column)
        if token.type == TokenType.INT:
            self._advance()
            return Literal(token.literal, token.line, token.column)
        raise ParseError(
            f"expected an int in match range pattern, found {self._describe(token)}",
            token.line,
            token.column,
        )
```
Note the merged `MINUS`/`INT` branch drops float support for negative
*literal* patterns' `-5.5 => ...` shape — preserve that by keeping
`_match_pattern_bound`'s int-only restriction for range bounds (matching
today's unnegated range bounds, which are already `INT`-only) while still
letting a bare negative literal pattern (no following `..`) accept a float:
adjust `_match_pattern_bound`'s `value_token.type != TokenType.INT` check
to also accept `TokenType.FLOAT` when called from the non-range path, or
(simpler) keep the original `MINUS` branch's float-accepting literal parse
inline in `_match_pattern` and only extract a narrower int-only bound
parser for use after `-` is confirmed to lead into a range — verify against
the acceptance criteria below either way; the exact refactor shape is an
implementation detail, not a fixed interface.

No `RangeExpr` construction (`cinder/ast_nodes.py`), `_evaluate_range`
(`cinder/interpreter.py`), or `contains_value` changes are needed — a
negative-bound `RangeExpr` is structurally identical to a positive-bound
one; only the *bound expressions themselves* need to support a leading
`-`, and evaluation of `Literal(-10, ...)` already works today (that's how
negative literal patterns evaluate).

Acceptance criteria:
- `match (-5) { -10..0 => "neg", _ => "other" };` is `"neg"`.
- `match (5) { -10..0 => "neg", _ => "other" };` is `"other"` — `5` is
  outside `-10..0`.
- `match (0) { -10..0 => "neg", _ => "other" };` is `"other"` — exclusive
  upper bound still excludes `0`.
- `match (0) { -10..=0 => "neg", _ => "other" };` is `"neg"` — inclusive
  upper bound now includes `0`.
- `match (-1) { -10..-1 => "neg", _ => "other" };` is `"other"` — exclusive
  upper bound with two negative bounds.
- `match (5) { 0..-1 => "empty", _ => "other" };` is `"other"` — a
  start-greater-than-end range with a negative end bound still matches
  nothing, same as today's empty-range convention.
- `match (-5) { -5 => "neg", _ => "pos" };` is still `"neg"` — a bare
  negative literal pattern (no range) is unaffected.
- `match (x) { -"a"..0 => 0, _ => 1 };` (non-numeric after `-` in a range
  bound) raises `ParseError`.
- `shape(parse('match (x) { -10..0 => 0, _ => 1 }'))` (see
  `tests/test_parser.py`) shows the first arm's `range_pattern` with a
  negated start bound.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_pattern`, new
`_match_pattern_bound` or equivalent), `tests/test_parser.py` (extend
`class TestMatchExpression` or the range-pattern-specific test class —
search `range_pattern` for existing shape assertions),
`tests/test_interpreter.py` (extend the range-pattern match tests with the
negative-bound cases above). Once merged, `README.md`'s `match` expression
bullet needs its negative-literal-patterns description widened to mention
range bounds, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing (it currently
calls this out explicitly as "unaddressed, a real but separate gap") —
leave both to the Architect's next grooming pass, not this task.

---

## 5. Language: nested list patterns in `match` arms (`[a, [b, c]] => ...`)

Build: flat list patterns (`[a, b] => ...`, PR #316), literal elements (PR
#322), and rest capture (`[a, ...rest] => ...`, PR #324) all landed, but a
list-pattern element still can't itself be a list pattern — `let`
destructuring already supports this (`let [a, [b, c]] = [1, [2, 3]];`,
`_destructure_list_pattern_entry`/`cinder/parser.py`), the same
destructuring-vs-match gap flat map patterns (task 1 above) closed for maps
one level down. This is the last flat-vs-nested gap left in list patterns.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ([1, [2, 3]]) { [a, [b, c]] => a + b + c, _ => 0 });'
# -> <eval>:1:33: expected an identifier, '_', or a literal inside list pattern, found '['
```

**Ordering note:** if flat map patterns (task 1 above) have already landed by
the time this task is claimed, this task only touches list patterns — map
patterns nesting inside list patterns or vice versa is a real but separate
future gap, not in scope here either way.

`_match_list_pattern_entry` (`cinder/parser.py`, search `def
_match_list_pattern_entry`) currently only recognizes an identifier, `_`, or
a literal at each position and raises `ParseError` on anything else,
including `[`. Add one branch at the top, before the identifier check, that
recurses into `_match_list_pattern` itself when the next token is `[`:
```python
    def _match_list_pattern_entry(self) -> "str | Expr | None | tuple[list, str | None]":
        token = self._peek()
        if token.type == TokenType.LBRACKET:
            return self._match_list_pattern()
        if token.type == TokenType.IDENTIFIER:
            ...  # unchanged below
```
`_match_list_pattern()` already returns `tuple[list[str | Expr | None], str |
None]` (entries, rest) and already consumes its own `[`...`]` — calling it
recursively here means nesting to arbitrary depth, and rest capture at any
nested level (`[a, [b, ...rest]] => ...`), work for free with no extra code:
the recursive call *is* the same production, entries included. No change is
needed to `_match_list_pattern` itself, `MatchArm`
(`cinder/ast_nodes.py`), or the arity/rest-not-last/rest-needs-identifier
error paths — they already apply correctly to the nested call by construction.

`_evaluate_match`'s `list_pattern` branch (`cinder/interpreter.py`, search
`def _evaluate_match`) currently inlines the length check, per-entry loop,
and rest binding directly in the arm loop. Factor that inline logic into a
new recursive helper so a nested tuple entry can call back into the same
matching logic:
```python
    def _match_list_entries(
        self, entries: list, rest: "str | None", subject: object, env: Environment
    ) -> bool:
        if not isinstance(subject, list):
            return False
        min_len = len(entries)
        length_ok = (
            len(subject) >= min_len if rest is not None else len(subject) == min_len
        )
        if not length_ok:
            return False
        for entry, item in zip(entries, subject):
            if isinstance(entry, tuple):
                nested_entries, nested_rest = entry
                if not self._match_list_entries(nested_entries, nested_rest, item, env):
                    return False
                continue
            if isinstance(entry, Literal):
                if not values_equal(item, self.evaluate(entry, env)):
                    return False
                continue
            if entry is not None:
                env.define(entry, item)
        if rest is not None and rest != "_":
            env.define(rest, subject[min_len:])
        return True
```
Then replace the `arm.list_pattern is not None` branch's body with:
```python
            if arm.list_pattern is not None:
                arm_env = Environment(env)
                if not self._match_list_entries(
                    arm.list_pattern, arm.list_rest, subject, arm_env
                ):
                    continue
                return self.evaluate(arm.body, arm_env)
```
This is a pure refactor of the existing top-level logic into a recursive
helper — behavior for non-nested patterns is unchanged, verify the existing
list-pattern tests still pass unmodified.

Acceptance criteria:
- `match ([1, [2, 3]]) { [a, [b, c]] => a + b + c, _ => 0 };` is `6`.
- `match ([1, [2, 3]]) { [a, [b, c, d]] => 0, _ => "no" };` is `"no"` —
  nested length mismatch falls through, does not raise.
- `match ([1, "x"]) { [a, [b, c]] => "yes", _ => "no" };` is `"no"` — a
  non-list subject at a nested position falls through, does not raise.
- `match ([[1, 2], [3, 4]]) { [[a, b], [c, d]] => a + b + c + d, _ => 0 };`
  is `10` — nesting at every top-level position, not just one.
- `match ([1, [2, [3, 4]]]) { [a, [b, [c, d]]] => a + b + c + d, _ => 0 };`
  is `10` — two levels of nesting, confirming the recursion isn't
  hardcoded to one level.
- `match ([1, [2, 3]]) { [1, [b, c]] => b + c, _ => 0 };` is `5` — a literal
  element and a nested pattern coexist in the same arm.
- `match ([1, [2, 3]]) { [a, [_, c]] => a + c, _ => 0 };` is `4` — `_`
  inside a nested pattern still discards.
- `match ([1, [2, 3, 4]]) { [a, [b, ...rest]] => rest, _ => [] };` is
  `[3, 4]` — rest capture works inside a nested pattern too (falls out of
  the recursive reuse of `_match_list_pattern`, not extra code).
- `match ([1, 2]) { [a, b] => a + b, _ => 0 };` is still `3` and
  `match ([1, 2, 3]) { [a, ...rest] => rest, _ => [] };` is still `[2, 3]`
  — existing flat and rest-capture behavior is unaffected by the refactor.
- `shape(parse('match (x) { [a, [b, c]] => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `list_pattern` with a nested
  tuple entry at index 1.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_list_pattern_entry`),
`cinder/interpreter.py` (new `_match_list_entries` helper, `_evaluate_match`),
`tests/test_parser.py` (extend the list-pattern shape tests around
`test_match_list_pattern_literal_element_shape`/
`test_match_list_pattern_rest_capture_shape`, search those names — note the
`shape()` helper's list_pattern entry line, search `for entry in
arm.list_pattern`, only shapes `Expr` instances today and needs a small
recursive helper to also shape entries inside a nested tuple, e.g.:
```python
def _shape_list_pattern_entry(entry):
    if isinstance(entry, Expr):
        return shape(entry)
    if isinstance(entry, tuple):
        nested_entries, nested_rest = entry
        return ([_shape_list_pattern_entry(e) for e in nested_entries], nested_rest)
    return entry
```
used in place of the current `shape(entry) if isinstance(entry, Expr) else
entry` list comprehension), `tests/test_interpreter.py` (extend
`class TestMatchExpression`, search that name, with the end-to-end cases
above). Once merged, `README.md`'s `match` expression bullet needs its
"no nested list patterns" caveat removed, its "Status & roadmap" section
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
