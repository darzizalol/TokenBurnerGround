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

## 1. Language: per-key rename in match map patterns (`{a: x, b} => ...`)

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

## 2. Standard library: `combinations_with_replacement` — r-length selections that allow repeats

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

## 3. Standard library: `is_nonagonal` — the sixth figurate-number membership test

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

## 4. Language: rest capture in match map patterns (`{a, ...rest} => ...`)

Build: flat map patterns (PR #326) and per-key rename (task 3 above, once
merged) give match map patterns everything list patterns have except rest
capture — list patterns already support `[a, ...rest] => ...` (PR #324),
binding leftover elements into a list, and `let` map destructuring already
supports the map-shaped equivalent (`let {a, ...rest} = expr;`, binding
leftover *keys* into a dict, `_bind_map_destructure`/`cinder/interpreter.py`,
search `remaining = {k: v for k, v in value.items()`). Match map patterns
are the last place this specific capability is still missing. Verify the
gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": 2, "c": 3}) { {a, ...rest} => rest, _ => 0 });'
# -> <eval>:1:27: expected '}' after map pattern, found '...'
```
(Assumes task 3's per-key rename above has landed by the time this is
claimed; if not, `_match_map_pattern` still returns a bare `list[str]`
instead of `list[tuple[str, str]]` — adapt the parser sketch below to that
shape, the rest-capture parsing/binding logic itself is unaffected either
way.)

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
  (task 3) in the same pattern.
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
