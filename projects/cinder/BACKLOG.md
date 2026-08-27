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

## 1. Standard library: `combinations_with_replacement` — r-length selections that allow repeats

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

## 2. Standard library: `is_nonagonal` — the sixth figurate-number membership test

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

## 3. Language: rest capture in match map patterns (`{a, ...rest} => ...`)

Build: flat map patterns (PR #326) and per-key rename (PR #332) give match
map patterns everything list patterns have except rest capture — list
patterns already support `[a, ...rest] => ...` (PR #324), binding leftover
elements into a list, and `let` map destructuring already supports the
map-shaped equivalent (`let {a, ...rest} = expr;`, binding leftover *keys*
into a dict, `_bind_map_destructure`/`cinder/interpreter.py`, search
`remaining = {k: v for k, v in value.items()`). Match map patterns are the
last place this specific capability is still missing. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": 2, "c": 3}) { {a, ...rest} => rest, _ => 0 });'
# -> <eval>:1:27: expected '}' after map pattern, found '...'
```
Per-key rename has already landed (PR #332), so `_match_map_pattern`
already returns `list[tuple[str, str]]` — the parser sketch below assumes
that shape.

**Scope note:** only a bare `...rest` (or `..._` to discard) is in scope,
mirroring list pattern rest capture exactly — no combining rest with
nested patterns beyond what task 3 already allows. This is the same
"flat form first" staging every other match-pattern extension in this
backlog has used.

`_match_map_pattern` (`cinder/parser.py`, search `def _match_map_pattern`)
currently loops entries with no `DOT_DOT_DOT` handling and no rest slot.
Widen it to return `tuple[list[tuple[str, str]], str | None]`, mirroring
`_match_list_pattern`'s own `(entries, rest)` shape and
`_destructure_map_pattern`'s `DOT_DOT_DOT`/rest-must-be-last handling:
```python
    def _match_map_pattern(self) -> "tuple[list[tuple[str, str]], str | None]":
        self._advance()  # consume '{'
        entries: "list[tuple[str, str]]" = []
        rest: "str | None" = None
        if not self._check(TokenType.RBRACE):
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._match_map_pattern_rest_name()
            else:
                entries.append(self._match_map_pattern_entry())
            while self._check(TokenType.COMMA):
                self._advance()
                if rest is not None:
                    token = self._peek()
                    raise ParseError(
                        f"rest capture must be last in map pattern, found {self._describe(token)}",
                        token.line,
                        token.column,
                    )
                if self._check(TokenType.DOT_DOT_DOT):
                    rest = self._match_map_pattern_rest_name()
                else:
                    entries.append(self._match_map_pattern_entry())
        self._consume(TokenType.RBRACE, "'}' after map pattern")
        return entries, rest

    def _match_map_pattern_rest_name(self) -> str:
        self._advance()  # consume '...'
        token = self._peek()
        if token.type != TokenType.IDENTIFIER:
            raise ParseError(
                f"expected an identifier or '_' after '...' in map pattern, "
                f"found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._advance()
        return token.lexeme
```
This mirrors `_match_list_pattern_rest_name` exactly. The call site
(`_match_pattern`, search `map_pattern = self._match_map_pattern()`) now
unpacks `map_pattern, map_rest = self._match_map_pattern()` and passes both
into `MatchArm` — add a new `map_rest: "str | None" = None` field to
`MatchArm` (`cinder/ast_nodes.py`, next to `map_pattern`), mirroring
`list_rest` next to `list_pattern`.

In `cinder/interpreter.py`, extend the `map_pattern` branch (search `if
arm.map_pattern is not None`):
```python
            if arm.map_pattern is not None:
                if not isinstance(subject, dict) or not all(
                    key in subject for key, _ in arm.map_pattern
                ):
                    continue
                arm_env = Environment(env)
                seen_keys = set()
                for key, binding in arm.map_pattern:
                    arm_env.define(binding, subject[key])
                    seen_keys.add(key)
                if arm.map_rest is not None and arm.map_rest != "_":
                    arm_env.define(
                        arm.map_rest,
                        {k: v for k, v in subject.items() if k not in seen_keys},
                    )
                return self.evaluate(arm.body, arm_env)
```
This mirrors `_bind_map_destructure`'s own leftover-keys dict construction
and the list-pattern match branch's `rest != "_"` discard convention
exactly.

Acceptance criteria:
- `match ({"a": 1, "b": 2, "c": 3}) { {a, ...rest} => rest, _ => 0 };` is
  `{"b": 2, "c": 3}`.
- `match ({"a": 1}) { {a, ...rest} => rest, _ => 0 };` is `{}` — rest
  captures an empty dict when nothing is left over.
- `match ({"a": 1, "b": 2}) { {a, ..._} => a, _ => 0 };` is `1` — `..._`
  discards the rest binding without raising or leaking a variable.
- `match ({"a": 1, "b": 2}) { {a} => a, _ => 0 };` is still `1` — patterns
  with no rest are unaffected.
- `match ({"a": 1, "b": 2, "c": 3}) { {a: x, ...rest} => [x, rest], _ => 0 };`
  is `[1, {"b": 2, "c": 3}]` — rest capture composes with per-key rename
  (PR #332) in the same pattern.
- `match ([1, 2]) { {a, ...rest} => rest, _ => "no" };` is `"no"` — a
  non-map subject still falls through, rest capture included.
- A rest capture is scoped to its arm's body only, same as every other
  match-pattern binding.
- `match (x) { {a, ...5} => a, _ => 0 };` (non-identifier after `...`)
  raises `ParseError` matching `"expected an identifier or '_' after '...'
  in map pattern"`.
- `match (x) { {a, ...rest, b} => a, _ => 0 };` (rest not last) raises
  `ParseError` matching `"rest capture must be last in map pattern"`.
- `shape(parse('match (x) { {a, ...rest} => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `map_pattern`/`map_rest`
  fields with `map_rest` set to `"rest"`.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_map_pattern`, new
`_match_map_pattern_rest_name`, the `_match_pattern` call site),
`cinder/ast_nodes.py` (new `MatchArm.map_rest` field), `cinder/interpreter.py`
(`_evaluate_match`'s `map_pattern` branch), `tests/test_parser.py` (extend
the map-pattern shape tests alongside task 3's, search
`test_match_map_pattern_shape`), `tests/test_interpreter.py` (extend `class
TestMatchExpression`, search `test_map_pattern_binds_named_keys`, with the
rest-capture cases above). Once merged, `README.md`'s `match` expression
bullet needs its map-pattern description widened to mention rest capture,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Standard library: `is_catalan` — membership test for `nth_catalan`'s existing sibling

Build: `nth_catalan` (`cinder/builtins.py`) returns the k-th Catalan number
by position, but every other `nth_*` builtin in Cinder has a matching
`is_*` membership predicate (`is_fibonacci`/`nth_fibonacci`,
`is_lucas_number`/`nth_lucas`, `is_triangular` through `is_octagonal`
paired with their `nth_*` siblings) — `nth_catalan` is the one `nth_*`
builtin with no `is_*` counterpart. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_catalan(14));'
# -> <eval>:1:7: undefined name 'is_catalan'
```

Unlike the figurate-number cluster, Catalan numbers have no closed-form
perfect-square-style membership test, so this follows a different
existing shape instead: `is_perfect_power`'s bounded iterative search
(search `def _is_perfect_power`, `cinder/builtins.py`) — grow candidates
until they meet or exceed the target, an early terminating loop rather
than an inverse formula. Catalan numbers grow fast (`C(15)` is already
over 2.6 million, per `test_nth_catalan_of_fifteen`), so the loop
terminates quickly for any realistic input. Add to `cinder/builtins.py`,
registered directly after `_nth_catalan` (search `def _nth_catalan`,
immediately before `def _sum`):
```python
def _is_catalan(arguments: list, line: int, column: int) -> object:
    _require_arity("is_catalan", arguments, 1, line, column)
    value = _require_int("is_catalan", arguments[0], line, column)
    if value < 1:
        return False
    index = 0
    while True:
        candidate = math.comb(2 * index, index) // (index + 1)
        if candidate == value:
            return True
        if candidate > value:
            return False
        index += 1
```
This mirrors `_nth_catalan`'s own `math.comb(2 * index, index) // (index
+ 1)` formula exactly, just iterated upward and compared instead of
computed once at a fixed position — same arity/int-check shape every
other predicate here uses, early `False` on `value < 1` since every
Catalan number is positive (mirroring `_is_perfect_power`'s domain-open,
non-raising convention for out-of-range input). Also register the new
dict entry (search `"nth_catalan": _nth_catalan,`, add `"is_catalan":
_is_catalan,` directly after it).

Acceptance criteria:
- `is_catalan(1);`, `is_catalan(2);`, `is_catalan(5);`, `is_catalan(14);`,
  `is_catalan(42);`, `is_catalan(4862);` are all `true` — the first six
  distinct Catalan numbers (`C(0)` through `C(9)`, using `nth_catalan`'s
  own position-1-indexed values from `test_nth_catalan_of_first_six_positions`
  and `test_nth_catalan_of_ten`).
- `is_catalan(1);` is `true` via a single index-0 hit even though `C(0)
  == C(1) == 1` — the loop returns on the first match, no duplicate-value
  ambiguity to handle.
- `is_catalan(0);`, `is_catalan(3);`, `is_catalan(4);`, `is_catalan(-1);`
  are all `false` — `0` and negative values are domain-open (`false`, not
  raised, matching every other `is_*` predicate here), `3`/`4` are
  between consecutive Catalan numbers (`2` and `5`).
- `is_catalan(nth_catalan(k));` is `true` for every `k` from `1` to `15`
  — cross-check against the existing `nth_catalan` builtin directly.
- `is_catalan(1.5);` raises `CinderRuntimeError` matching `"is_catalan()
  requires an int, got float"` (via `_require_int`'s existing message
  format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`nth_catalan`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthCatalan`, search that name, for the
positive/domain/type-error/cross-check test shapes). Once merged,
`README.md`'s Builtins bullet needs `is_catalan` added near
`nth_catalan`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 5. Language: nested patterns as map pattern values (`{a: {b, c}} => ...`, `{a: [x, y]} => ...`)

Build: nested list patterns (PR #330) closed the flat-vs-nested gap for
list-pattern elements — an element can now itself be a list pattern to
arbitrary depth. Map patterns have no equivalent yet: a map pattern's
value slot only ever binds a plain identifier (optionally renamed, PR
#332) or captures rest (once task 3 above lands), never another list/map
pattern. `let` destructuring already supports this for maps
(`let {a, b: [c, d]} = ...`, `let {a: {b}} = ...` —
`_destructure_map_pattern_entry`, `cinder/parser.py`, recurses into
`_destructure_list_pattern`/`_destructure_map_pattern` on a nested
value), so this is the last flat-vs-nested gap between match map patterns
and everything else in Cinder that already destructures maps. Verify the
gap (assumes per-key rename (PR #332) and task 3's rest capture have
landed — see Ordering note):
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": {"c": 2}}) { {a, b: {c}} => a + c, _ => 0 });'
# -> <eval>:1:24: expected identifier after ':' in map pattern, found '{'
```

**Ordering note:** this task depends on per-key rename (PR #332, already
landed — `_match_map_pattern_entry` returns `(key, binding)` pairs) and
task 3 (rest capture, `_match_map_pattern` returning `(entries, rest)`)
having landed — it widens the same `_match_map_pattern_entry` one more
time, to let `binding` be a nested pattern instead of only a plain name.
If task 3 hasn't landed yet when this is claimed, do that task's shape
change first (this task is not a substitute for it).

**Scope note:** only list-pattern and map-pattern nesting as a map
pattern's *value* is in scope, mirroring what `let` destructuring
already allows in the same position — no defaults inside the nested
pattern (that stays a `let`-only feature), no nesting on the *key* side
(map keys are always plain strings, unaffected).

Widen `_match_map_pattern_entry`'s `binding` slot
(`cinder/parser.py`, search `def _match_map_pattern_entry`) to recurse
into `_match_list_pattern`/`_match_map_pattern` on a nested `[`/`{`,
mirroring `_destructure_map_pattern_entry`'s own nested-value branch:
```python
    def _match_map_pattern_entry(self) -> "tuple[str, object]":
        key = self._consume(
            TokenType.IDENTIFIER, "identifier inside map pattern"
        ).lexeme
        if self._check(TokenType.COLON):
            self._advance()
            if self._check(TokenType.LBRACKET):
                return key, self._match_list_pattern()
            if self._check(TokenType.LBRACE):
                return key, self._match_map_pattern()
            binding = self._consume(
                TokenType.IDENTIFIER, "identifier after ':' in map pattern"
            ).lexeme
            return key, binding
        return key, key
```
The `binding` slot in each `(key, binding)` pair returned by
`_match_map_pattern` is now `str | tuple[list, str | None] | tuple[list,
str | None]` (a plain name, a list-pattern `(entries, rest)` pair, or a
map-pattern `(entries, rest)` pair) — same three-way shape
`_match_list_pattern_entry` already returns for list-pattern elements.
In `cinder/interpreter.py`, extend the `map_pattern` branch (search `if
arm.map_pattern is not None`) to dispatch on `binding`'s shape the same
way `_match_list_entries` already dispatches on list-pattern entries:
```python
            if arm.map_pattern is not None:
                if not isinstance(subject, dict) or not all(
                    key in subject for key, _ in arm.map_pattern
                ):
                    continue
                arm_env = Environment(env)
                seen_keys = set()
                matched = True
                for key, binding in arm.map_pattern:
                    seen_keys.add(key)
                    if isinstance(binding, tuple):
                        nested_entries, nested_rest = binding
                        if isinstance(nested_entries, list) and all(
                            isinstance(e, tuple) and len(e) == 2 and isinstance(e[0], str)
                            for e in nested_entries
                        ) and _looks_like_map_entries(nested_entries):
                            if not self._match_map_entries(
                                nested_entries, nested_rest, subject[key], arm_env
                            ):
                                matched = False
                                break
                        elif not self._match_list_entries(
                            nested_entries, nested_rest, subject[key], arm_env
                        ):
                            matched = False
                            break
                    else:
                        arm_env.define(binding, subject[key])
                if not matched:
                    continue
                if arm.map_rest is not None and arm.map_rest != "_":
                    arm_env.define(
                        arm.map_rest,
                        {k: v for k, v in subject.items() if k not in seen_keys},
                    )
                return self.evaluate(arm.body, arm_env)
```
The list-vs-map ambiguity in the sketch above (`_looks_like_map_entries`)
is a placeholder, not a real function to add as-is — both nested
list-pattern and nested map-pattern entries end up as a `(entries, rest)`
tuple from the parser, so the interpreter cannot tell them apart by shape
alone once it reaches this branch. Resolve this cleanly instead by having
the parser tag which kind it produced (e.g. wrap `_match_map_pattern`'s
recursive-value result so the interpreter branch can dispatch on an
unambiguous marker, such as a small tagged tuple/dataclass distinguishing
"nested list" from "nested map", or by factoring a shared recursive
`_match_map_entries` helper analogous to `_match_list_entries` and having
the parser emit that instead of raw tuples) rather than the ad hoc shape
sniffing above — this is a real design decision for whoever implements
this task, not settled by this sketch.

Acceptance criteria:
- `match ({"a": 1, "b": {"c": 2}}) { {a, b: {c}} => a + c, _ => 0 };` is
  `3`.
- `match ({"a": 1, "b": [2, 3]}) { {a, b: [x, y]} => a + x + y, _ => 0 };`
  is `6`.
- `match ({"a": {"b": {"c": 1}}}) { {a: {b: {c}}} => c, _ => 0 };` is `1`
  — nesting works to arbitrary depth, mirroring nested list patterns.
- `match ({"a": 1, "b": {"c": 2}}) { {a, b: {c: x}} => a + x, _ => 0 };`
  is `3` — nested map-pattern values compose with per-key rename (PR #332)
  in the same pattern.
- `match ({"a": 1, "b": {"c": 2, "d": 3}}) { {a, b: {c, ...rest}} => rest,
  _ => 0 };` is `{"d": 3}` — nested map-pattern values compose with rest
  capture (task 3) in the same pattern.
- `match ({"a": 1, "b": {"c": 2}}) { {a, b: {d}} => 0, _ => "no match" };`
  is `"no match"` — a nested pattern that doesn't match its nested
  subject falls through the whole arm, not just the nested part.
- `match ({"a": 1, "b": 2}) { {a, b: {c}} => c, _ => "no" };` is `"no"` —
  a nested map pattern whose nested subject is not itself a map falls
  through (subject's `b` is an int, not a map).
- `match ({"a": 1, "b": [1, 2]}) { {a, b: {c}} => c, _ => "no" };` is
  `"no"` — a nested map pattern whose nested subject is a list, not a
  map, falls through the same way.
- Bindings from a nested pattern are scoped to the arm's body only, same
  as every other match-pattern binding.
- `shape(parse('match (x) { {a, b: {c}} => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `map_pattern` with `b`'s
  binding as a nested `(entries, rest)` pair rather than a plain string.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_map_pattern_entry`, and
whatever tagging/helper the design decision above settles on),
`cinder/ast_nodes.py` (`MatchArm.map_pattern` docstring, widened for the
new value shape), `cinder/interpreter.py` (`_evaluate_match`'s
`map_pattern` branch, likely a new `_match_map_entries` helper mirroring
`_match_list_entries`), `tests/test_parser.py` (extend the map-pattern
shape tests, search `test_match_map_pattern_shape`),
`tests/test_interpreter.py` (extend `class TestMatchExpression`, search
`test_map_pattern_binds_named_keys`, with the nesting cases above). Once
merged, `README.md`'s `match` expression bullet needs its map-pattern
description widened to mention value nesting, its "Status & roadmap"
section needs updating, and `PROJECT.md`'s "Current frontier" bullet
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 6. Language: default values for trailing elements in match list patterns (`[a, b = 0] => ...`)

Build: `let`/`for`/function-param/comprehension list destructuring has
supported trailing default values for a long time (`let [a, b = 5] =
expr;`, PR #244) — a shorter-than-the-pattern list still binds
successfully, falling back to the default for missing trailing elements.
Match list patterns never got the equivalent: today a subject list
shorter than the pattern just falls through the arm entirely, with no
way to supply a fallback value for a missing trailing element. This is
the last capability `let` list destructuring has that match list
patterns still lack — flat elements, literal elements (#322), rest
capture (#324), and nesting (#330) have all already landed. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(match ([1]) { [a, b = 0] => a + b, _ => -1 });'
# -> <eval>:1:33: expected ']' after list pattern, found '='
```

**Scope note:** only a bare identifier element may carry a default —
mirroring the "flat-capability-first" staging every other match-pattern
extension in this backlog has used, and matching how rename/rest were
each first proven out on the simple case before any further extension
was considered. A literal element (`1 = 0`), a `_` wildcard, or a nested
list-pattern element carrying a default is out of scope for this task;
the parser should reject a `=` in those positions the same way it
already rejects any other unexpected token there (no special-casing
needed — the `_match_list_pattern`/`_consume(RBRACKET, ...)` machinery
already errors cleanly on a stray `=`). Defaults on match *map*
patterns are a separate, not-yet-queued task — out of scope here.

`_match_list_pattern_entry` (`cinder/parser.py`, search `def
_match_list_pattern_entry`) currently returns a single value per entry
(`str | Expr | None | tuple[list, str | None]`) with no default. Widen
it to return `tuple[entry, Expr | None]` for every entry kind (mirroring
`_destructure_list_pattern_entry`'s own `(pattern, default)` return
shape, search `def _destructure_list_pattern_entry` for the ordering
check to copy), take a `seen_default: bool` parameter, and only offer a
trailing `= expr` after a plain (non-`_`) identifier:
```python
    def _match_list_pattern_entry(
        self, seen_default: bool
    ) -> "tuple[str | Expr | None | tuple[list, str | None], Expr | None]":
        token = self._peek()
        if token.type == TokenType.LBRACKET:
            entry = self._match_list_pattern()
        elif token.type == TokenType.IDENTIFIER:
            self._advance()
            entry = None if token.lexeme == "_" else token.lexeme
            if entry is not None and self._check(TokenType.EQ):
                self._advance()
                default = self._ternary()
                return entry, default
        elif token.type in (TokenType.INT, TokenType.FLOAT, TokenType.STRING):
            self._advance()
            entry = Literal(token.literal, token.line, token.column)
        elif token.type == TokenType.TRUE:
            self._advance()
            entry = Literal(True, token.line, token.column)
        elif token.type == TokenType.FALSE:
            self._advance()
            entry = Literal(False, token.line, token.column)
        elif token.type == TokenType.NIL:
            self._advance()
            entry = Literal(None, token.line, token.column)
        else:
            raise ParseError(
                f"expected an identifier, '_', or a literal inside list "
                f"pattern, found {self._describe(token)}",
                token.line,
                token.column,
            )
        if seen_default:
            raise ParseError(
                "element without a default value follows an element with "
                "one in list pattern",
                token.line,
                token.column,
            )
        return entry, None
```
Update `_match_list_pattern` (search `def _match_list_pattern`) to
thread `seen_default` through both call sites the same way
`_destructure_list_pattern` already does, e.g. `entries.append(...);
seen_default = seen_default or entries[-1][1] is not None`. Nested list
patterns get default support for free — they parse via the same
`_match_list_pattern` production recursively.

In `cinder/interpreter.py`, widen `_match_list_entries` (search `def
_match_list_entries`) to unpack `(entry, default)` pairs and evaluate a
default when the subject runs out of elements, mirroring
`_bind_list_destructure`'s own `required`/`has_defaults` length check
(search `def _bind_list_destructure`):
```python
    def _match_list_entries(
        self, entries: list, rest: "str | None", subject: object, env: Environment
    ) -> bool:
        if not isinstance(subject, list):
            return False
        required = sum(1 for _, default in entries if default is None)
        if rest is not None:
            length_ok = len(subject) >= required
        else:
            length_ok = required <= len(subject) <= len(entries)
        if not length_ok:
            return False
        for index, (entry, default) in enumerate(entries):
            item = subject[index] if index < len(subject) else self.evaluate(default, env)
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
            env.define(rest, subject[len(entries):])
        return True
```
Default expressions are evaluated in `env` (the arm's own child
environment), left-to-right in `enumerate(entries)` order, so an earlier
element bound in the same pattern is visible to a later default —
mirroring `_bind_list_destructure`'s own left-to-right evaluation (e.g.
`let [a, b = a + 1] = [5];`).

Acceptance criteria:
- `match ([1]) { [a, b = 0] => a + b, _ => -1 };` is `1` — the trailing
  default fires when the subject is exactly one element short.
- `match ([1, 2]) { [a, b = 0] => a + b, _ => -1 };` is `3` — the default
  is not used when the subject supplies the value.
- `match ([]) { [a = 1, b = 2] => a + b, _ => -1 };` is `3` — multiple
  trailing defaults, subject with zero required elements.
- `match ([1, 2, 3]) { [a, b = 0] => a + b, _ => -1 };` is `-1` — a
  subject longer than the pattern's max length (2, with no rest) still
  falls through; defaults widen the minimum matchable length, not the
  maximum, same as `let` destructuring.
- `match ([1]) { [a, b = a + 1] => b, _ => -1 };` is `2` — a default
  expression may reference an earlier element bound in the same pattern.
- `match ([1]) { [a, b = 0, ...rest] => [a, b, rest], _ => "no" };` is
  `[1, 0, []]` — defaults compose with rest capture in the same pattern.
- `match ([[1]]) { [[a, b = 0]] => a + b, _ => -1 };` is `1` — a nested
  list-pattern element gets default support for free via the shared
  recursive production.
- `match ({"a": 1}) { [a, b = 0] => a + b, _ => "no" };` is `"no"` — a
  non-list subject still falls through, defaults included.
- `match (x) { [a = 1, b] => a, _ => 0 };` (an element without a default
  follows one with a default) raises `ParseError` matching `"element
  without a default value follows an element with one in list pattern"`.
- `shape(parse('match (x) { [a, b = 0] => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `list_pattern` with `b`'s
  entry as a `(name, default_expr)` pair rather than a bare string.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_list_pattern`,
`_match_list_pattern_entry`), `cinder/interpreter.py`
(`_match_list_entries`), `tests/test_parser.py` (extend the list-pattern
shape tests, search `test_match_list_pattern_shape`),
`tests/test_interpreter.py` (extend `class TestMatchExpression`, search
`test_list_pattern_binds_elements`, with the default cases above). Once
merged, `README.md`'s `match` expression bullet needs a mention of list-
pattern defaults, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

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
