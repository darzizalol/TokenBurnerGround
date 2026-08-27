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

## 1. Language: negative bounds in range patterns (`-10..0 => "neg"`)

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

## 2. Language: nested list patterns in `match` arms (`[a, [b, c]] => ...`)

Build: flat list patterns (`[a, b] => ...`, PR #316), literal elements (PR
#322), and rest capture (`[a, ...rest] => ...`, PR #324) all landed, but a
list-pattern element still can't itself be a list pattern — `let`
destructuring already supports this (`let [a, [b, c]] = [1, [2, 3]];`,
`_destructure_list_pattern_entry`/`cinder/parser.py`), the same
destructuring-vs-match gap flat map patterns (PR #326) closed for maps
one level down. This is the last flat-vs-nested gap left in list patterns.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ([1, [2, 3]]) { [a, [b, c]] => a + b + c, _ => 0 });'
# -> <eval>:1:33: expected an identifier, '_', or a literal inside list pattern, found '['
```

**Scope note:** flat map patterns (PR #326) already landed; this task only
touches list patterns — map patterns nesting inside list patterns or vice
versa is a real but separate future gap, not in scope here either way.

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

## 3. Standard library: `nth_octagonal` — the k-th octagonal number by position

Build: `is_octagonal` already exists as a membership test, but Cinder has
no way to ask "what is the k-th octagonal number" the way it can for
triangular (`nth_triangular`, PR #313), pentagonal (`nth_pentagonal`, PR
#319), hexagonal (`nth_hexagonal`, PR #323), and heptagonal numbers
(`nth_heptagonal`, PR #328) — the same "value-returning sibling of an
`is_*` membership test" pattern the figurate-number cluster's first four
`nth_*` members already establish, just for its fifth. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_octagonal(5));'
# -> <eval>:1:7: undefined name 'nth_octagonal'
```

Add to `cinder/builtins.py`, registered right after `_nth_heptagonal`
(search `def _nth_heptagonal`, immediately before `_is_prime`):
```python
def _nth_octagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_octagonal", arguments, 1, line, column)
    value = _require_int("nth_octagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_octagonal() requires a positive integer, domain error", line, column
        )
    return value * (3 * value - 2)
```
`O(k) = k(3k - 2)` is the standard closed form for the k-th octagonal
number (cross-check: `_is_octagonal` tests `3 * value + 1` for a perfect
square whose root satisfies `(1 + root) % 3 == 0`, the standard
membership test derived from this same closed form). This mirrors
`_nth_triangular`'s, `_nth_pentagonal`'s, `_nth_hexagonal`'s, and
`_nth_heptagonal`'s shape exactly (arity check, int check, domain check,
one-line closed-form return) — a thin, direct composition, not a new
algorithm. Also register the new dict entry (search `"nth_heptagonal":
_nth_heptagonal,`, add `"nth_octagonal": _nth_octagonal,` directly after
it).

Acceptance criteria:
- `nth_octagonal(1);` is `1`, `nth_octagonal(2);` is `8`,
  `nth_octagonal(3);` is `21`, `nth_octagonal(4);` is `40` — the first
  four octagonal numbers.
- `is_octagonal(nth_octagonal(k));` is `true` for every `k` from `1` to
  `100` — cross-checks the closed form against the existing membership
  test, the same style `nth_pentagonal`'s, `nth_hexagonal`'s, and
  `nth_heptagonal`'s acceptance criteria use.
- `nth_octagonal(0);` and `nth_octagonal(-1);` both raise
  `CinderRuntimeError` matching `"nth_octagonal() requires a positive
  integer, domain error"`.
- `nth_octagonal(1.5);` raises `CinderRuntimeError` matching
  `"nth_octagonal() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `nth_heptagonal`, search
for the current line number), `tests/test_builtins.py`
(model on `class TestNthHexagonal`, search that name, for the domain-error,
type-error, and cross-check test shapes). Once merged, `README.md`'s
Builtins bullet needs `nth_octagonal` added near `nth_heptagonal`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Language: per-key rename in match map patterns (`{a: x, b} => ...`)

Build: flat map patterns (`{a, b} => ...`, PR #326) landed scoped to bare
identifier keys only — each key binds a variable of the *same* name, with
no way to rename. `let` map destructuring already supports per-key rename
(`let {a: x, b} = expr;`, `_destructure_map_pattern_entry`,
`cinder/parser.py`) — the same "prove the flat form out, then extend it"
staging flat list patterns used for literal elements (PR #322) and rest
capture (PR #324). This is the natural next extension now that the flat
form has landed. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": 2}) { {a: x, b} => x + b, _ => 0 });'
# -> <eval>:1:24: expected '}' after map pattern, found ':'
```

**Scope note:** only bare per-key rename (`{a: x, b}`) is in scope — no
nesting (`{a: {b}}`), no rest capture (`{a, ...rest}`), and no default
values (`{a = 5}`); those stay real gaps for later, the same way flat map
patterns themselves were staged.

Today `_match_map_pattern` (`cinder/parser.py`, search `def
_match_map_pattern`) returns a bare `list[str]` of key names, reused
directly as both the map's lookup key and the bound variable's name; the
interpreter's `map_pattern` branch (`cinder/interpreter.py`, search `if
arm.map_pattern is not None`) does the same double duty. Widen both to
carry `(key, binding)` pairs:
```python
    def _match_map_pattern(self) -> "list[tuple[str, str]]":
        self._advance()  # consume '{'
        entries: "list[tuple[str, str]]" = []
        if not self._check(TokenType.RBRACE):
            entries.append(self._match_map_pattern_entry())
            while self._check(TokenType.COMMA):
                self._advance()
                entries.append(self._match_map_pattern_entry())
        self._consume(TokenType.RBRACE, "'}' after map pattern")
        return entries

    def _match_map_pattern_entry(self) -> "tuple[str, str]":
        key = self._consume(
            TokenType.IDENTIFIER, "identifier inside map pattern"
        ).lexeme
        if self._check(TokenType.COLON):
            self._advance()
            binding = self._consume(
                TokenType.IDENTIFIER, "identifier after ':' in map pattern"
            ).lexeme
            return key, binding
        return key, key
```
This mirrors `_destructure_map_pattern_entry`'s own `key`/`binding` split,
just without its nested-pattern/default branches (out of scope here).
Then in `cinder/interpreter.py`, replace the `map_pattern` branch's body:
```python
            if arm.map_pattern is not None:
                if not isinstance(subject, dict) or not all(
                    key in subject for key, _ in arm.map_pattern
                ):
                    continue
                arm_env = Environment(env)
                for key, binding in arm.map_pattern:
                    arm_env.define(binding, subject[key])
                return self.evaluate(arm.body, arm_env)
```
Update `MatchArm`'s `map_pattern` field docstring (`cinder/ast_nodes.py`,
search `map_pattern` is a fifth`) from "a flat list of bound-identifier
keys" to "a flat list of `(key, binding)` pairs, `binding` equal to `key`
when unrenamed" — no field-type or dataclass-shape change beyond the
element type, so nothing else in `ast_nodes.py` needs touching.

Acceptance criteria:
- `match ({"a": 1, "b": 2}) { {a: x, b} => x + b, _ => 0 };` is `3`.
- `match ({"a": 1}) { {a: x} => x, _ => 0 };` is `1`.
- `match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 };` is still `3` —
  unrenamed keys are unaffected by the change.
- `match ({"a": 1}) { {a: x, b: y} => x + y, _ => -1 };` is `-1` — a
  missing key still falls through, not raises, rename or not.
- `match ([1, 2]) { {a: x} => x, _ => "no" };` is `"no"` — a non-map
  subject still falls through.
- `match ({"a": 1, "b": 2}) { {a: x} => x, _ => 0 };` is `1` — extra
  unmatched keys in the subject are still ignored.
- A renamed binding is scoped to its arm's body only, same as unrenamed
  bindings today (does not leak into the enclosing scope).
- `match (x) { {a: 5} => a, _ => 0 };` (non-identifier after `:`) raises
  `ParseError` matching `"identifier after ':' in map pattern"`.
- `shape(parse('match (x) { {a: x, b} => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `map_pattern` as
  `[("a", "x"), ("b", "b")]` — update the existing
  `test_match_map_pattern_shape`/`test_match_empty_map_pattern_shape`/
  `test_match_map_pattern_and_list_pattern_coexist` assertions (search
  those names), which currently expect a bare `["a", "b"]`, to the new
  pair-list shape.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_map_pattern`, new
`_match_map_pattern_entry`), `cinder/interpreter.py` (`_evaluate_match`'s
`map_pattern` branch), `cinder/ast_nodes.py` (`MatchArm` docstring only),
`tests/test_parser.py` (update the three shape tests named above, extend
with a rename case), `tests/test_interpreter.py` (extend
`class TestMatchExpression`, search `test_map_pattern_binds_named_keys`,
with the rename cases above). Once merged, `README.md`'s `match`
expression bullet needs the flat-map-patterns description widened to
mention per-key rename, its "Status & roadmap" section needs updating,
and `PROJECT.md`'s "Current frontier" bullet needs refreshing — leave
both to the Architect's next grooming pass, not this task.

---

## 5. Standard library: `combinations_with_replacement` — r-length selections that allow repeats

Build: `combinations` (PR #327) returns every r-length combination without
reusing an element more than once, but Cinder has no way to ask for
selections that *do* allow repeats (e.g. "every way to pick 2 dice values
from `[1..6]`, repeats allowed") — the third and last member of the
classic itertools "selections" trio (`permutations`, `combinations`,
`combinations_with_replacement`), sitting directly next to `combinations`
the same way `power_set` sits next to `binomial`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(combinations_with_replacement([1, 2], 2));'
# -> <eval>:1:7: undefined name 'combinations_with_replacement'
```

Add to `cinder/builtins.py`, registered directly after `_combinations`
(search `def _combinations`, immediately before `def _permutations`):
```python
def _combinations_with_replacement(arguments: list, line: int, column: int) -> object:
    _require_arity("combinations_with_replacement", arguments, 2, line, column)
    items, size = arguments
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"combinations_with_replacement() requires a list, got {type_name(items)}",
            line,
            column,
        )
    if not isinstance(size, int) or isinstance(size, bool):
        raise CinderRuntimeError(
            f"combinations_with_replacement() requires an int size, got "
            f"{type_name(size)}",
            line,
            column,
        )
    if size < 0:
        raise CinderRuntimeError(
            "combinations_with_replacement() requires a non-negative size, "
            "domain error",
            line,
            column,
        )
    return [
        list(combo)
        for combo in itertools.combinations_with_replacement(items, size)
    ]
```
This mirrors `_combinations`'s shape exactly (arity check, list check, int
check, non-negative-size check, one-line `itertools` wrapper) — the only
behavioral difference from `combinations` is which `itertools` function
does the enumerating, so no new domain logic beyond what `_combinations`
already validates. Unlike `combinations`, `size` may legitimately exceed
`len(items)` here (repeats make that a valid non-empty request, e.g.
`combinations_with_replacement([1], 3)` is `[[1, 1, 1]]`) — do not add a
`size > len(items)` check. Also register the new dict entry (search
`"combinations": _combinations,`, add `"combinations_with_replacement":
_combinations_with_replacement,` directly after it).

Acceptance criteria:
- `combinations_with_replacement([1, 2], 2);` is
  `[[1, 1], [1, 2], [2, 2]]` — order matches `itertools`'s own
  lexicographic-by-input-position order.
- `combinations_with_replacement([1], 3);` is `[[1, 1, 1]]` — `size`
  exceeding `len(items)` is valid (repeats allow it), unlike `combinations`.
- `combinations_with_replacement([1, 2], 0);` is `[[]]`.
- `combinations_with_replacement([], 0);` is `[[]]` and
  `combinations_with_replacement([], 1);` is `[]`.
- `combinations_with_replacement([1, 2], -1);` raises `CinderRuntimeError`
  matching `"combinations_with_replacement() requires a non-negative
  size, domain error"`.
- `combinations_with_replacement(5, 2);` raises `CinderRuntimeError`
  matching `"combinations_with_replacement() requires a list, got int"`.
- `combinations_with_replacement([1, 2], 1.5);` raises `CinderRuntimeError`
  matching `"combinations_with_replacement() requires an int size, got
  float"`.
- Wrong arity (not exactly 2 arguments) raises `CinderRuntimeError` with
  line/column.
- Duplicate elements in the input are not de-duplicated, matching
  `itertools.combinations_with_replacement`'s position-based (not
  value-based) behavior.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`combinations`), `tests/test_builtins.py` (model on `class
TestCombinations`, search that name, for the domain-error, type-error,
and shape test forms). Once merged, `README.md`'s Builtins bullet needs
`combinations_with_replacement` added near `combinations`, its "Status &
roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 6. Standard library: `is_nonagonal` — the sixth figurate-number membership test

Build: the figurate-number membership cluster currently runs
triangular/pentagonal/hexagonal/heptagonal/octagonal (`is_triangular`,
`is_pentagonal`, `is_hexagonal`, `is_heptagonal`, `is_octagonal` — square
numbers are skipped since `is_perfect_square` already covers them), each
a closed-form perfect-square-plus-modular-residue check registered
back-to-back in `cinder/builtins.py`. Nonagonal numbers are the next side
of the polygon and nothing in Cinder can test membership in that sequence
yet. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_nonagonal(9));'
# -> <eval>:1:7: undefined name 'is_nonagonal'
```

The k-th nonagonal number is `N(k) = k(7k - 5) / 2`. Solving for `k` given
a candidate `n` via the quadratic formula gives the same
"perfect-square-plus-modular-residue" shape every sibling in the cluster
already uses: `candidate = 56n + 25` must be a perfect square, and its
integer root must satisfy `(root + 5) % 14 == 0`. Add to
`cinder/builtins.py`, registered directly after `_is_octagonal` (search
`def _is_octagonal`, immediately before `def _nth_triangular`):
```python
def _is_nonagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("is_nonagonal", arguments, 1, line, column)
    value = _require_int("is_nonagonal", arguments[0], line, column)
    if value < 0:
        return False

    candidate = 56 * value + 25
    root = math.isqrt(candidate)
    return root * root == candidate and (root + 5) % 14 == 0
```
This mirrors `_is_heptagonal`'s/`_is_octagonal`'s shape exactly (arity
check, int check, early-`False` on negative, one perfect-square-plus-
modular-residue check) — a derived formula, not a new algorithm shape.
Also register the new dict entry (search `"is_octagonal": _is_octagonal,`,
add `"is_nonagonal": _is_nonagonal,` directly after it).

Acceptance criteria:
- `is_nonagonal(1);`, `is_nonagonal(9);`, `is_nonagonal(24);`,
  `is_nonagonal(46);`, `is_nonagonal(75);` are all `true` — the first five
  nonagonal numbers (`N(k) = k(7k-5)/2` for `k` = 1..5).
- `is_nonagonal(0);`, `is_nonagonal(2);`, `is_nonagonal(10);`,
  `is_nonagonal(-1);` are all `false` — `0` is `false` here (matching
  `is_heptagonal(0)`/`is_octagonal(0)`, not `is_triangular(0)`'s special
  case), and `-1` returns `false` rather than raising, domain-open like
  every other `is_*` membership predicate in the cluster.
- `is_nonagonal(nth_triangular(k));` need not be `true` in general (cross-
  cluster values don't coincide except at small `k`) — instead cross-check
  via direct construction: `is_nonagonal(k * (7 * k - 5) / 2);` is `true`
  for every `k` from `1` to `100`.
- `is_nonagonal(1.5);` raises `CinderRuntimeError` matching
  `"is_nonagonal() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_octagonal`, search
for the current line number), `tests/test_builtins.py` (model on `class
TestIsOctagonal`, search that name, for the domain, type-error, and
cross-check test shapes). Once merged, `README.md`'s Builtins bullet
needs `is_nonagonal` added near `is_octagonal`, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" bullet
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

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
