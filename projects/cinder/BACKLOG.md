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

## 1. Standard library: `nth_hexagonal` — the k-th hexagonal number by position

Build: restocking the backlog back to its 6-task, 3-breadth/3-depth
ceiling now that `cartesian_product` (PR #317) landed, dropping the queue
to 5 tasks (2-breadth/3-depth: `nth_pentagonal`, `power_set` vs. range
patterns, negative literal patterns, literal list elements). This
restocks with breadth to restore parity, per `PROJECT.md`'s alternation
policy. `is_hexagonal` already exists as a membership test, but Cinder
has no way to ask "what is the k-th hexagonal number" the way it can for
triangular numbers (`nth_triangular`, PR #313), Fibonacci
(`nth_fibonacci`), primes (`nth_prime`), and Lucas numbers (`nth_lucas`)
— the exact same "value-returning sibling of an `is_*` membership test"
pattern `nth_triangular` and task 2 above (`nth_pentagonal`, still
unclaimed) already establish for the figurate-number cluster, just for
its third member. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_hexagonal(5));'
# -> <eval>:1:7: undefined name 'nth_hexagonal'
```

**Ordering note:** if task 2 (`nth_pentagonal`) has already landed by the
time this task is claimed, register `nth_hexagonal` directly after
`nth_pentagonal` instead of after `nth_triangular` — same adaptive
placement every sibling task in this backlog already uses.

Add to `cinder/builtins.py`, registered right after `_nth_triangular`
(search `def _nth_triangular`, immediately before `_is_prime` — or
directly after `_nth_pentagonal` if task 2 has already landed):
```python
def _nth_hexagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_hexagonal", arguments, 1, line, column)
    value = _require_int("nth_hexagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_hexagonal() requires a positive integer, domain error", line, column
        )
    return value * (2 * value - 1)
```
The closed form `H(k) = k(2k - 1)` is the standard 1-indexed hexagonal
number formula (`H(1) = 1, H(2) = 6, H(3) = 15, ...`), matching
`_is_hexagonal`'s own derivation (`cinder/builtins.py`, search `def
_is_hexagonal`: it tests `8 * value + 1` for a perfect square with an
odd-mod-4 root, the standard membership test for this same closed form).
This mirrors `_nth_triangular`'s and `_nth_pentagonal`'s shape exactly
(arity check, int check, domain check, one-line closed-form return) — a
thin, direct composition, not a new algorithm. Also register the new
dict entry (search `"nth_triangular": _nth_triangular,`, add
`"nth_hexagonal": _nth_hexagonal,` directly after it — or directly after
`"nth_pentagonal": _nth_pentagonal,` if task 2 has already landed).

Acceptance criteria:
- `nth_hexagonal(1);` is `1`, `nth_hexagonal(2);` is `6`,
  `nth_hexagonal(3);` is `15`, `nth_hexagonal(4);` is `28`,
  `nth_hexagonal(5);` is `45` — the first five hexagonal numbers.
- `nth_hexagonal(10);` is `190`.
- `nth_hexagonal(100);` is `19900`.
- `is_hexagonal(nth_hexagonal(n));` is `true` for every `n` from `1` to
  `100` — confirms the closed form agrees with the existing membership
  predicate across a wide range, the same cross-check `nth_triangular`'s
  and `nth_pentagonal`'s own acceptance criteria used.
- `nth_hexagonal(0);` and `nth_hexagonal(-3);` both raise
  `CinderRuntimeError` matching `"nth_hexagonal() requires a positive
  integer, domain error"`.
- `nth_hexagonal(2.0);` raises `CinderRuntimeError` matching
  `"nth_hexagonal() requires an int, got float"`.
- `nth_hexagonal(true);` raises `CinderRuntimeError` matching
  `"nth_hexagonal() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `nth_triangular`/
`nth_pentagonal`, see current line numbers — shift depending on which
sibling tasks land first), `tests/test_builtins.py` (model on `class
TestNthTriangular`, search that name, including its `is_triangular`-
agreement-style cross-check test, adapted to `is_hexagonal`). Once
merged, `README.md`'s Builtins bullet needs `nth_hexagonal` added near
`nth_triangular`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 2. Language: rest capture in list patterns (`[a, ...rest] => ...`)

Build: restocking the sixth and final slot to bring the backlog back to its
6-task, 3-breadth/3-depth ceiling now that range patterns in `match` arms
landed via PR #318 (dropping the queue from 6 to 5: `nth_pentagonal`,
`power_set`, `nth_hexagonal` — breadth, 3 — vs. negative literal patterns,
literal list elements — depth, 2). Restocking with a depth task restores
parity. Flat list patterns (PR #316) can only test a list subject's *exact*
length (`[a, b]` matches only a 2-element list) — Cinder's `let`/assignment
destructuring already has a "rest capture" escape hatch for this same shape
mismatch (`let [a, ...rest] = xs;`, `cinder/parser.py`'s
`_destructure_list_pattern`/`_destructure_rest_name`), but match list
patterns have no equivalent: there is no way to write a list-pattern arm that
matches "at least N elements, bind the first N, capture everything else."
Verify the gap, on current `main`:
```sh
python3 -m cinder.cli eval 'print(match ([1, 2, 3]) { [a, ...rest] => rest, _ => "no" });'
# -> <eval>:1:31: expected an identifier or '_' inside list pattern, found '...'
```

**Scope note:** rest capture must be the last element in a list pattern
(`[a, ...rest]` is valid, `[...rest, a]` is not — matching
`_destructure_list_pattern`'s own "rest element must be last" restriction)
and only one rest element is allowed per pattern. `...rest` binds the
remaining elements as a new list (a copy via slicing, not a view). `..._`
(discarding the captured tail while still requiring "at least N elements")
is valid too, mirroring how a bare element can already be `_` to discard —
unlike a discarded plain element (which parses to `None`), a discarded rest
is kept as the literal name `"_"` so the interpreter can tell "no rest
capture" (`None`) apart from "rest capture, discarded" (`"_"`); see below.
This task does not touch literal list elements (task 4 above, still
unclaimed as of this writing) — if that task has already landed by the time
this one is claimed, follow the **Ordering note** below instead of the code
shown.

**Ordering note:** if literal elements in list patterns (task 4) has already
landed by the time this task is claimed, `_match_list_pattern_entry` (not
`_match_list_pattern_name`) will already exist and return `str | Expr | None`
per element — add the `DOT_DOT_DOT` branch to `_match_list_pattern` (the
caller) exactly as shown below, just calling `_match_list_pattern_entry` in
place of `_match_list_pattern_name` for the non-rest branches; the
interpreter-side length check (`>=` instead of `==` when a rest is present)
and rest-slice binding are unaffected by which element parser is in place.

Today's `_match_list_pattern`/`_match_list_pattern_name`
(`cinder/parser.py`, search `def _match_list_pattern`) only ever parse a
fixed-length list of identifier/`_` entries and never check for
`TokenType.DOT_DOT_DOT`. Widen it to optionally end in a rest capture,
mirroring `_destructure_list_pattern`'s own rest-checking loop shape:
```python
    def _match_list_pattern(self) -> "tuple[list[str | None], str | None]":
        self._advance()  # consume '['
        names: "list[str | None]" = []
        rest: "str | None" = None
        if not self._check(TokenType.RBRACKET):
            if self._check(TokenType.DOT_DOT_DOT):
                rest = self._match_list_pattern_rest_name()
            else:
                names.append(self._match_list_pattern_name())
            while self._check(TokenType.COMMA):
                self._advance()
                if rest is not None:
                    token = self._peek()
                    raise ParseError(
                        f"rest capture must be last in list pattern, found {self._describe(token)}",
                        token.line,
                        token.column,
                    )
                if self._check(TokenType.DOT_DOT_DOT):
                    rest = self._match_list_pattern_rest_name()
                else:
                    names.append(self._match_list_pattern_name())
        self._consume(TokenType.RBRACKET, "']' after list pattern")
        return names, rest

    def _match_list_pattern_rest_name(self) -> str:
        self._advance()  # consume '...'
        token = self._peek()
        if token.type != TokenType.IDENTIFIER:
            raise ParseError(
                f"expected an identifier or '_' after '...' in list pattern, "
                f"found {self._describe(token)}",
                token.line,
                token.column,
            )
        self._advance()
        return token.lexeme  # kept as "_" itself when discarded, see scope note
```
`_match_arm` (`cinder/parser.py`, search `def _match_arm`) currently does
`list_pattern = self._match_list_pattern()` then constructs
`MatchArm(None, body, None, list_pattern, None)` — update to unpack the new
two-tuple and pass the rest name into `MatchArm`'s new field:
```python
        if self._check(TokenType.LBRACKET):
            list_pattern, list_rest = self._match_list_pattern()
            self._consume(TokenType.FAT_ARROW, "'=>' after match pattern")
            body = self._ternary()
            return [MatchArm(None, body, None, list_pattern, None, list_rest)]
```
`MatchArm` (`cinder/ast_nodes.py`, search `class MatchArm`) needs a sixth
field, appended after `range_pattern` (appending, not inserting, keeps every
existing positional `MatchArm(...)` call site elsewhere in the parser valid
without touching them):
```python
    list_rest: "str | None" = None
```
`_evaluate_match` (`cinder/interpreter.py`, search `def _evaluate_match`)'s
`arm.list_pattern is not None` branch currently requires
`len(subject) != len(arm.list_pattern)` to fail the arm; widen it to accept
"at least" when a rest is present, and bind the tail:
```python
            if arm.list_pattern is not None:
                min_len = len(arm.list_pattern)
                length_ok = (
                    len(subject) >= min_len if arm.list_rest is not None
                    else len(subject) == min_len
                )
                if not isinstance(subject, list) or not length_ok:
                    continue
                arm_env = Environment(env)
                for name, item in zip(arm.list_pattern, subject):
                    if name is not None:
                        arm_env.define(name, item)
                if arm.list_rest is not None and arm.list_rest != "_":
                    arm_env.define(arm.list_rest, subject[min_len:])
                return self.evaluate(arm.body, arm_env)
```

Acceptance criteria:
- `match ([1, 2, 3]) { [a, ...rest] => rest, _ => "no" };` is `[2, 3]`.
- `match ([1]) { [a, ...rest] => rest, _ => "no" };` is `[]` — rest captures
  an empty tail when the subject is exactly as long as the fixed prefix.
- `match ([1, 2]) { [a, b, ...rest] => rest, _ => "no" };` is `[]`, and the
  same arm against `[1, 2, 3]` gives `[3]`.
- `match ([]) { [a, ...rest] => "yes", _ => "no" };` is `"no"` — a rest
  pattern still requires at least as many elements as its fixed prefix; it
  does not make the prefix optional.
- `match ([1, 2, 3]) { [a, ..._] => a, _ => "no" };` is `1` — a discarded
  rest (`..._`) still allows the "at least N" match without binding
  anything.
- `match ("ab") { [a, ...rest] => "yes", _ => "no" };` is `"no"` — a
  non-list subject falls through without raising, same as today's
  fixed-length list patterns.
- `match ([1, 2]) { [a, b] => a + b, _ => 0 };` is still `3` — a list
  pattern with no rest capture is unaffected (`arm.list_rest` is `None`, so
  `length_ok` is the same exact-length check as before).
- `match (x) { [a, ...rest, b] => 0, _ => 1 };` (rest not last) raises
  `ParseError` matching `"rest capture must be last in list pattern, found
  'b'"`.
- `match (x) { [...5] => 0, _ => 1 };` (rest not followed by an identifier
  or `_`) raises `ParseError` matching `"expected an identifier or '_'
  after '...' in list pattern, found '5'"`.
- `shape(parse('match (x) { [a, ...rest] => rest, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's 6-tuple ending in `"rest"` —
  confirms `list_rest` threads through to the AST; a plain `[a, b]` pattern's
  shape ends in `None`.
- Full test suite passes.

Likely files: `cinder/ast_nodes.py` (`MatchArm`), `cinder/parser.py`
(`_match_list_pattern`, new `_match_list_pattern_rest_name`, `_match_arm`),
`cinder/interpreter.py` (`_evaluate_match`), `tests/test_parser.py` (the
`shape()` helper's `MatchExpr` branch — search `arm.list_pattern,` inside
it — needs a 6th tuple element, `arm.list_rest`, appended; extend `class
TestMatchExpression`), `tests/test_interpreter.py` (extend `class
TestMatchExpression` with the end-to-end cases above). Once merged,
`README.md`'s `match` expression bullet needs "rest capture" dropped from
its "not supported yet" list and a short description added near the
flat-list-pattern description, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" bullet needs refreshing —
leave both to the Architect's next grooming pass, not this task.

---

## 3. Standard library: `permutations` — every ordering of a list

Build: restocking the backlog back to its 6-task, 3-breadth/3-depth
ceiling now that `nth_pentagonal` (PR #319) landed, dropping the queue
to 5 tasks (2-breadth/3-depth: `power_set`, `nth_hexagonal` vs. negative
literal patterns, literal list elements, rest capture). This restocks
with breadth to restore parity, per `PROJECT.md`'s alternation policy.
Cinder's collection-helper cluster already answers "every ordered
combination of one element from each of N lists" (`cartesian_product`,
PR #317) and, once task 2 above lands, will answer "every subset of one
list, ignoring order" (`power_set`) — but has no way to answer the
adjacent question "every ordering of one list's own elements", the
question `is_permutation` (a predicate testing whether two lists are
reorderings of each other) implies but never answers directly with the
actual orderings, the same predicate-vs-enumerator gap `binomial` has to
`power_set` and `len(cartesian_product(...))` has to `cartesian_product`
itself. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(permutations([1, 2]));'
# -> <eval>:1:7: undefined name 'permutations' (did you mean 'is_permutation'?)
```

Add to `cinder/builtins.py`, registered right after `_cartesian_product`
(search `def _cartesian_product`; `itertools` is already imported at the
top of this module — no new import needed):
```python
def _permutations(arguments: list, line: int, column: int) -> object:
    _require_arity("permutations", arguments, 1, line, column)
    items = arguments[0]
    if not isinstance(items, list):
        raise CinderRuntimeError(
            f"permutations() requires a list, got {type_name(items)}", line, column
        )
    return [list(p) for p in itertools.permutations(items)]
```
`itertools.permutations(items)` (no second argument — full-length
permutations only, see the scope note below) does the actual
enumeration, the same thin-wrapper composition style `cartesian_product`
uses for `itertools.product` and task 2 (`power_set`) uses for
`itertools.combinations`. Also register the new dict entry (search
`"cartesian_product": _cartesian_product,`, add `"permutations":
_permutations,` directly after it — or directly after `"power_set":
_power_set,` if task 2 has already landed, keeping the collection-helper
cluster grouped together in the dict).

**Scope note:** only full-length permutations (`itertools.permutations(items)`,
no `r` argument) are in scope — a `permutations(items, k)` form for
partial-length permutations is a real but separate gap, left for a
future task if it proves needed. `permutations([])` returns `[[]]` (one
empty permutation of the empty list, matching `itertools.permutations([])`'s
own single-empty-tuple result and the same "one canonical empty-input
answer" convention `power_set([])`/`cartesian_product([])` both already
establish). Duplicate elements are not de-duplicated
(`permutations([1, 1])` returns two `[1, 1]` entries, not one) —
`itertools.permutations` treats elements by position, not by value,
matching Python's own behavior and requiring no extra code to preserve.

Acceptance criteria:
- `permutations([]);` is `[[]]`.
- `permutations([1]);` is `[[1]]`.
- `permutations([1, 2]);` is `[[1, 2], [2, 1]]`.
- `permutations([1, 2, 3]);` is `[[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3,
  1], [3, 1, 2], [3, 2, 1]]` — matches `itertools.permutations`'s own
  lexicographic-by-position order.
- `len(permutations(l));` is `factorial(len(l))` for `l` equal to `[]`,
  `[1]`, `[1, 2]`, `[1, 2, 3]`, and `[1, 2, 3, 4]` — the standard
  permutation-count identity, the same closed-form cross-check style
  `power_set`'s and `nth_hexagonal`'s acceptance criteria use.
- `permutations([1, 1]);` is `[[1, 1], [1, 1]]` — duplicate elements are
  not de-duplicated.
- `permutations("ab");` raises `CinderRuntimeError` matching
  `"permutations() requires a list, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `cartesian_product`/
`power_set`, see current line numbers), `tests/test_builtins.py` (model
on `class TestCartesianProduct`, search that name, for the
list-validation and arity-error test shapes). Once merged, `README.md`'s
Builtins bullet needs `permutations` added near `cartesian_product`, its
"Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 4. Language: flat map patterns in `match` arms (`{a, b} => ...`)

Build: restocking the sixth and final slot to bring the backlog back to its
6-task, 3-breadth/3-depth ceiling. Negative literal patterns landed via PR
#320 and were archived to `CHANGELOG.md` without a grooming pass restocking
behind them, dropping the queue to 5 tasks (3-breadth/2-depth: `power_set`,
`nth_hexagonal`, `permutations` vs. literal list elements, rest capture).
Adding one depth task restores 3/3 parity. `match` currently has a flat
*list* pattern (`[a, b] => ...`, PR #316) that destructures a list subject
by shape, but no equivalent for a *map* subject — `let`/assignment
destructuring already has a rich map pattern (`let {a, b} = expr;`, with
nesting, rename, rest, and defaults — `cinder/parser.py`'s
`_destructure_map_pattern`), but `match` arms have no way to test "is this
a map with these keys" and bind their values in one step, the same gap
flat list patterns closed for lists in PR #316. This task closes the
minimal slice of that gap — bare bound-identifier keys only, no nesting,
no rename, no rest, no defaults — mirroring exactly how flat list patterns
themselves started minimal before literal elements and rest capture (tasks
2 and 4 above) extended them incrementally. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 });'
# -> <eval>:1:32: expected a literal, identifier, or '_' in match pattern, found '{'
```

**Scope note:** only bare identifier keys are accepted per entry (`{a, b}`,
where the key name and the bound name are always the same — no `{a: x}`
rename, which is a real but separate follow-up gap, the same "prove the
flat form out first" staging `nth_triangular` → `nth_pentagonal` and flat
list patterns → literal list elements both already used). No nested
patterns (`{a: {b}}` or `{a: [b, c]}`), no rest capture (`{a, ...rest}`),
and no default values (`{a, b = 5}`) — all real gaps, all left for future
tasks once this one proves the form out, matching how task 4 (rest capture
in *list* patterns) is itself staged as a separate task from flat list
patterns. A map pattern matches if the subject is a map (dict) containing
*every* named key — extra unnamed keys in the subject are ignored, and a
missing key or non-map subject falls through to the next arm (does not
raise), the same "falls through, doesn't raise" philosophy flat list
patterns (shape mismatch) and range patterns (non-numeric subject) already
established for pattern-kind mismatches in `match`.

**Ordering note:** if rest capture in list patterns (task 4 above) has
already landed by the time this task is claimed, `MatchArm` will already
have a `list_rest` field as its sixth positional slot — append the new
`map_pattern` field as the *seventh* slot instead of the sixth shown below,
and adjust the one `MatchArm(...)` call site this task touches accordingly
(every other call site in the parser already uses the trailing-default
form and needs no change either way).

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

## 5. Standard library: `combinations` — every r-length combination of a list

Build: restocking the sixth slot to bring the backlog back to its 6-task,
3-breadth/3-depth ceiling now that `power_set` landed via PR #321, dropping
the queue to 5 tasks (2-breadth/3-depth: `nth_hexagonal`, `permutations` vs.
literal list elements, rest capture, flat map patterns). Adding one breadth
task restores parity. `binomial(n, k)` already answers "how many r-length
combinations exist" and `power_set` (PR #321) already enumerates combinations
of *every* size at once — but there is no way to enumerate combinations of one
specific size, the exact "enumerate-vs-count" gap `binomial` has to
`power_set` itself, the same gap task 4 (`permutations`) closes for orderings
against `is_permutation`. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(combinations([1, 2, 3], 2));'
# -> <eval>:1:7: undefined name 'combinations'
```

**Ordering note:** if `permutations` (task 4 above) has already landed by the
time this task is claimed, register `combinations` directly after
`permutations` instead of after `power_set`, keeping the collection-helper
cluster grouped together in the dict, same adaptive placement every sibling
task in this backlog already uses.

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
`permutations` (task 4) uses for `itertools.permutations`. Note
`itertools.combinations` already returns `[]` (not an error) when `size >
len(items)`, matching Python's own convention — no extra domain check needed
for that case. Also register the new dict entry (search `"power_set":
_power_set,`, add `"combinations": _combinations,` directly after it — or
directly after `"permutations": _permutations,` if task 4 has already landed).

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
