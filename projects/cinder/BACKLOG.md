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

## 1. Language: rest capture in match map patterns (`{a, ...rest} => ...`) [claimed 2026-08-27T20:15:59Z]

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
nested patterns beyond what task 1 already allows. This is the same
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
the map-pattern shape tests alongside task 1's, search
`test_match_map_pattern_shape`), `tests/test_interpreter.py` (extend `class
TestMatchExpression`, search `test_map_pattern_binds_named_keys`, with the
rest-capture cases above). Once merged, `README.md`'s `match` expression
bullet needs its map-pattern description widened to mention rest capture,
its "Status & roadmap" section needs updating, and `PROJECT.md`'s "Current
frontier" bullet needs refreshing — leave both to the Architect's next
grooming pass, not this task.

---

## 2. Standard library: `is_catalan` — membership test for `nth_catalan`'s existing sibling

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

## 3. Language: nested patterns as map pattern values (`{a: {b, c}} => ...`, `{a: [x, y]} => ...`)

Build: nested list patterns (PR #330) closed the flat-vs-nested gap for
list-pattern elements — an element can now itself be a list pattern to
arbitrary depth. Map patterns have no equivalent yet: a map pattern's
value slot only ever binds a plain identifier (optionally renamed, PR
#332) or captures rest (once task 1 above lands), never another list/map
pattern. `let` destructuring already supports this for maps
(`let {a, b: [c, d]} = ...`, `let {a: {b}} = ...` —
`_destructure_map_pattern_entry`, `cinder/parser.py`, recurses into
`_destructure_list_pattern`/`_destructure_map_pattern` on a nested
value), so this is the last flat-vs-nested gap between match map patterns
and everything else in Cinder that already destructures maps. Verify the
gap (assumes per-key rename (PR #332) and task 1's rest capture have
landed — see Ordering note):
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1, "b": {"c": 2}}) { {a, b: {c}} => a + c, _ => 0 });'
# -> <eval>:1:24: expected identifier after ':' in map pattern, found '{'
```

**Ordering note:** this task depends on per-key rename (PR #332, already
landed — `_match_map_pattern_entry` returns `(key, binding)` pairs) and
task 1 (rest capture, `_match_map_pattern` returning `(entries, rest)`)
having landed — it widens the same `_match_map_pattern_entry` one more
time, to let `binding` be a nested pattern instead of only a plain name.
If task 1 hasn't landed yet when this is claimed, do that task's shape
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
  capture (task 1) in the same pattern.
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

## 4. Language: default values for trailing elements in match list patterns (`[a, b = 0] => ...`)

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
patterns are a separate task (task 8 below) — out of scope here.

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

## 5. Standard library: `is_twin_prime` — membership test for primes with a twin partner

Build: the prime-relationship cluster in `cinder/builtins.py` already
covers several adjacency/structure predicates built on trial-division
primality (`is_semiprime`, `is_sphenic`, `is_emirp`, `is_circular_prime`),
but none test the classic "twin prime" relationship — whether a prime `p`
has another prime exactly 2 away (`p - 2` or `p + 2`). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(is_twin_prime(5));'
# -> <eval>:1:7: undefined name 'is_twin_prime'
```

`is_twin_prime(n)` is `true` when `n` itself is prime and at least one of
`n - 2`/`n + 2` is also prime (covers both "lower twin", e.g. `3` paired
with `5`, and "upper twin", e.g. `5` paired with `3` or `7` paired with
`5`). Add to `cinder/builtins.py`, registered directly after
`_is_circular_prime` (search `def _is_circular_prime`, immediately before
`def _is_power_of_two`), following `_is_circular_prime`'s own shape of a
local nested trial-division helper rather than a shared module-level one
(matching this file's existing convention — each prime-relationship
predicate reimplements trial division inline):
```python
def _is_twin_prime(arguments: list, line: int, column: int) -> object:
    _require_arity("is_twin_prime", arguments, 1, line, column)
    value = _require_int("is_twin_prime", arguments[0], line, column)
    if value < 2:
        return False

    def _trial_division_is_prime(candidate: int) -> bool:
        if candidate < 2:
            return False
        for divisor in range(2, int(candidate ** 0.5) + 1):
            if candidate % divisor == 0:
                return False
        return True

    if not _trial_division_is_prime(value):
        return False
    return _trial_division_is_prime(value - 2) or _trial_division_is_prime(value + 2)
```
Also register the new dict entry (search `"is_circular_prime":
_is_circular_prime,`, add `"is_twin_prime": _is_twin_prime,` directly
after it).

Acceptance criteria:
- `is_twin_prime(3);`, `is_twin_prime(5);`, `is_twin_prime(7);`,
  `is_twin_prime(11);`, `is_twin_prime(13);` are all `true` — each has a
  prime partner exactly 2 away (`3`/`5`, `5`/`3` or `5`/`7`, `7`/`5`,
  `11`/`13`, `13`/`11`).
- `is_twin_prime(2);` is `false` — prime, but neither `0` nor `4` is
  prime.
- `is_twin_prime(23);` is `false` — prime, but neither `21` nor `25` is
  prime.
- `is_twin_prime(9);`, `is_twin_prime(0);`, `is_twin_prime(1);`,
  `is_twin_prime(-5);` are all `false` — not prime to begin with (domain-
  open, matching `is_semiprime`/`is_circular_prime`'s own `value < 2`
  early-`False` convention, no raising on out-of-range input).
- `is_twin_prime(k);` matches a direct trial-division cross-check
  (`is_prime(k) and (is_prime(k - 2) or is_prime(k + 2))`) for every `k`
  from `0` to `200`.
- `is_twin_prime(5.0);` raises `CinderRuntimeError` matching
  `"is_twin_prime() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_circular_prime`,
search for the current line number), `tests/test_builtins.py` (model on
`class TestIsCircularPrime`, search that name, for the domain, type-
error, and cross-check test shapes). Once merged, `README.md`'s Builtins
bullet needs `is_twin_prime` added near `is_circular_prime`, its "Status
& roadmap" section needs updating, and `PROJECT.md`'s "Current frontier"
bullet needs refreshing — leave both to the Architect's next grooming
pass, not this task.

---

## 6. Standard library: `nth_nonagonal` — the k-th nonagonal number by position

Build: `is_nonagonal` (PR #334) just closed the triangular..nonagonal
`is_*` cluster, but it left a new, smaller gap behind it —
`nth_triangular` through `nth_octagonal` all have a matching `nth_*`
closed-form sibling (`nth_pentagonal`/`nth_hexagonal`/`nth_heptagonal`/
`nth_octagonal`), and `nth_catalan`/`is_catalan` established the same
`nth_*`-needs-`is_*`-and-vice-versa convention for a different cluster,
but nonagonal is the one figurate shape with an `is_*` predicate and no
`nth_*` value-returning counterpart. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_nonagonal(5));'
# -> <eval>:1:7: undefined name 'nth_nonagonal'
```

Nonagonal numbers follow the same closed form as their pentagonal/
hexagonal/heptagonal/octagonal siblings, `N(k) = k(7k - 5)/2` — this is
exactly the formula `_is_nonagonal`'s own membership check already
verifies against (search `def _is_nonagonal`, `cinder/builtins.py`:
`candidate = 56 * value + 25`, `root = math.isqrt(candidate)`,
`root * root == candidate and (root + 5) % 14 == 0`, which is the
perfect-square/modular-residue test derived from solving `N(k) = n` for
`k`). Add to `cinder/builtins.py`, registered directly after
`_nth_octagonal` (search `def _nth_octagonal`, immediately before
`def _is_prime`), mirroring `_nth_octagonal`'s own shape exactly:
```python
def _nth_nonagonal(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_nonagonal", arguments, 1, line, column)
    value = _require_int("nth_nonagonal", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_nonagonal() requires a positive integer, domain error", line, column
        )
    return value * (7 * value - 5) // 2
```
Also register the new dict entry (search `"nth_octagonal":
_nth_octagonal,`, add `"nth_nonagonal": _nth_nonagonal,` directly after
it, before `"is_prime": _is_prime,`).

Acceptance criteria:
- `nth_nonagonal(1);`, `nth_nonagonal(2);`, `nth_nonagonal(3);`,
  `nth_nonagonal(4);` are `1`, `9`, `24`, `46` — the first four nonagonal
  numbers.
- `nth_nonagonal(10);` is `325`.
- `nth_nonagonal(100);` is `34750` (`100 * (700 - 5) / 2`).
- `is_nonagonal(nth_nonagonal(k));` is `true` for every `k` from `1` to
  `100` — cross-check against the existing `is_nonagonal` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own
  shape.
- `nth_nonagonal(0);` and `nth_nonagonal(-1);` raise `CinderRuntimeError`
  matching `"nth_nonagonal() requires a positive integer, domain error"`.
- `nth_nonagonal(1.5);` raises `CinderRuntimeError` matching
  `"nth_nonagonal() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`nth_octagonal`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthOctagonal`, search that name, for the
positive/domain/type-error/cross-check test shapes). Once merged,
`README.md`'s Builtins bullet needs `nth_nonagonal` added near
`is_nonagonal`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 7. Standard library: `nth_happy_number` — the k-th happy number by position

Build: `is_happy_number`/`is_sad_number` (`cinder/builtins.py`) test
membership via the digit-square-sum cycle, but neither has a
value-returning `nth_*` counterpart the way the figurate-number and prime
clusters do (`nth_prime`/`is_prime`, `nth_triangular`/`is_triangular`,
etc.) — happy numbers have no closed form, so this follows `nth_prime`'s
own shape (search `def _nth_prime`): a sequential candidate scan with a
`count`/`candidate` loop, not an inverse formula. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_happy_number(5));'
# -> <eval>:1:7: undefined name 'nth_happy_number'
```

Add to `cinder/builtins.py`, registered directly after `_is_sad_number`
(search `def _is_sad_number`, immediately before `def _collatz_length`)
— keeps the happy/sad-number cluster together, mirroring how
`is_catalan` sits directly after `nth_catalan`:
```python
def _nth_happy_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_happy_number", arguments, 1, line, column)
    value = _require_int("nth_happy_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_happy_number() requires a positive integer, domain error", line, column
        )

    def _is_happy(candidate: int) -> bool:
        seen = set()
        while candidate != 1:
            if candidate in seen:
                return False
            seen.add(candidate)
            candidate = sum(int(digit) ** 2 for digit in str(candidate))
        return True

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_happy(candidate):
            count += 1
    return candidate
```
This mirrors `_nth_prime`'s own `count`/`candidate` scanning loop exactly,
just swapping the primality check for `_is_happy_number`'s cycle-detection
logic (reimplemented locally as a nested helper, matching how
`is_twin_prime`/`is_circular_prime` reimplement trial division locally
rather than sharing a module-level helper — this file's existing
convention for small local predicates). Also register the new dict entry
(search `"is_sad_number": _is_sad_number,`, add `"nth_happy_number":
_nth_happy_number,` directly after it, before `"collatz_length":
_collatz_length,`).

Acceptance criteria:
- `nth_happy_number(1);`, `nth_happy_number(2);`, `nth_happy_number(3);`,
  `nth_happy_number(4);`, `nth_happy_number(5);` are `1`, `7`, `10`, `13`,
  `19` — the first five happy numbers by position.
- `nth_happy_number(10);` is `44`.
- `nth_happy_number(20);` is `100`.
- `is_happy_number(nth_happy_number(k));` is `true` for every `k` from `1`
  to `20` — cross-check against the existing `is_happy_number` builtin
  directly, mirroring `test_nth_octagonal_agrees_with_is_octagonal`'s own
  shape.
- `nth_happy_number(0);` and `nth_happy_number(-1);` raise
  `CinderRuntimeError` matching `"nth_happy_number() requires a positive
  integer, domain error"`.
- `nth_happy_number(1.5);` raises `CinderRuntimeError` matching
  `"nth_happy_number() requires an int, got float"` (via `_require_int`'s
  existing message format).
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register directly after
`is_sad_number`, search for the current line number), `tests/test_builtins.py`
(model on `class TestNthPrime`, search that name, for the
positive/domain/type-error/cross-check test shapes, and `class
TestIsHappyNumber` for the happy-number cycle behavior). Once merged,
`README.md`'s Builtins bullet needs `nth_happy_number` added near
`is_happy_number`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" bullet needs refreshing — leave both to
the Architect's next grooming pass, not this task.

---

## 8. Language: default values in match map patterns (`{a, b = 0} => ...`)

Build: match list patterns already support trailing defaults via `[a, b
= 0] => ...` (see task 4 in this backlog, which explicitly flags map-
pattern defaults as "a separate, not-yet-queued task"), and `let` map
destructuring has supported per-key defaults for a long time (`let {a, b
= 5} = expr;`, PR #244) — a map missing a key still binds successfully,
falling back to the default. Match map patterns never got the
equivalent: today a subject map missing a pattern's key just falls
through the arm entirely, with no way to supply a fallback value.
Verify the gap:
```sh
python3 -m cinder.cli eval 'print(match ({"a": 1}) { {a, b = 0} => a + b, _ => -1 });'
# -> <eval>:1:31: expected '}' after map pattern, found '='
```

**Ordering note:** this task depends on task 1 (rest capture) having
landed — it widens the same `_match_map_pattern_entry`/`_match_map_pattern`
production and the same interpreter `map_pattern` match branch task 1
touches (`arm.map_rest` handling). If task 1 hasn't landed yet when this
is claimed, do that task first (this task is not a substitute for it).
Unlike task 4 (list defaults), this task does **not** need to check
whether all pattern keys are present up front the way list patterns check
length — map patterns already match on a key subset (extra keys in the
subject beyond the pattern are always fine, no rest needed), so adding
defaults only relaxes which keys are *required*.

**Scope note:** only a bare identifier or renamed binding (`a` or `a: x`)
may carry a default — mirroring task 4's "flat-capability-first" scope
restriction exactly. If task 3 (nested map-pattern values) has also
landed by the time this is claimed, a nested `{...}`/`[...]` binding
carrying a default stays out of scope; only add the `= expr` check in
the plain-identifier branch of `_match_map_pattern_entry`, not after a
recursive nested-pattern call.

Widen `_match_map_pattern_entry` (`cinder/parser.py`, search `def
_match_map_pattern_entry`) to return a third element, mirroring
`_destructure_map_pattern_entry`'s own trailing `default` return:
```python
    def _match_map_pattern_entry(self) -> "tuple[str, str, Expr | None]":
        key = self._consume(
            TokenType.IDENTIFIER, "identifier inside map pattern"
        ).lexeme
        if self._check(TokenType.COLON):
            self._advance()
            binding = self._consume(
                TokenType.IDENTIFIER, "identifier after ':' in map pattern"
            ).lexeme
        else:
            binding = key
        default = None
        if self._check(TokenType.EQ):
            self._advance()
            default = self._ternary()
        return key, binding, default
```
`_match_map_pattern`'s entries list is now `list[tuple[str, str, Expr |
None]]`; no other change needed there since map-pattern entries have no
ordering constraint the way list-pattern defaults do (a required key can
follow a defaulted one with no ambiguity — each entry is looked up by
name, not position).

In `cinder/interpreter.py`, widen the `map_pattern` branch (search `if
arm.map_pattern is not None`) to unpack the 3-tuple and evaluate a
default when a key is missing, mirroring `_bind_map_destructure`'s own
`key in value` / `default is not None` check:
```python
            if arm.map_pattern is not None:
                if not isinstance(subject, dict) or not all(
                    key in subject or default is not None
                    for key, _, default in arm.map_pattern
                ):
                    continue
                arm_env = Environment(env)
                seen_keys = set()
                for key, binding, default in arm.map_pattern:
                    item = subject[key] if key in subject else self.evaluate(default, arm_env)
                    arm_env.define(binding, item)
                    seen_keys.add(key)
                if arm.map_rest is not None and arm.map_rest != "_":
                    arm_env.define(
                        arm.map_rest,
                        {k: v for k, v in subject.items() if k not in seen_keys},
                    )
                return self.evaluate(arm.body, arm_env)
```
Default expressions are evaluated in `arm_env`, left-to-right in
`arm.map_pattern` order, so an earlier binding in the same pattern is
visible to a later default — mirroring `_bind_map_destructure`'s own
progressive-`env` evaluation and task 4's identical left-to-right
convention for list-pattern defaults.

Acceptance criteria:
- `match ({"a": 1}) { {a, b = 0} => a + b, _ => -1 };` is `1` — the
  default fires when the subject is missing the key.
- `match ({"a": 1, "b": 2}) { {a, b = 0} => a + b, _ => -1 };` is `3` —
  the default is not used when the subject supplies the key.
- `match ({}) { {a = 1, b = 2} => a + b, _ => -1 };` is `3` — multiple
  defaults, subject missing every key.
- `match ({"a": 1}) { {a, b = a + 1} => b, _ => -1 };` is `2` — a default
  expression may reference an earlier binding in the same pattern.
- `match ({"b": 2}) { {a: x = 0, b} => x + b, _ => -1 };` is `2` — a
  default composes with per-key rename (PR #332) in the same pattern.
- `match ({"a": 1, "c": 3}) { {a, b = 0, ...rest} => [a, b, rest], _ =>
  "no" };` is `[1, 0, {"c": 3}]` — a default composes with rest capture
  (task 1) in the same pattern; the missing, defaulted key `b` is not
  spuriously included in `rest`.
- `match ({}) { {a} => a, _ => "no" };` is `"no"` — a key without a
  default is still required; missing it still falls through, unaffected
  by this task.
- `match ([1]) { {a = 1} => a, _ => "no" };` is `"no"` — a non-map
  subject still falls through, defaults included.
- `shape(parse('match (x) { {a, b = 0} => a, _ => 0 }'))` (see
  `tests/test_parser.py`) shows the first arm's `map_pattern` with `b`'s
  entry as a `(key, binding, default_expr)` triple rather than a
  `(key, binding)` pair.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_map_pattern_entry`),
`cinder/ast_nodes.py` (`MatchArm.map_pattern` docstring, widened for the
new 3-tuple entry shape), `cinder/interpreter.py` (`_evaluate_match`'s
`map_pattern` branch), `tests/test_parser.py` (extend the map-pattern
shape tests, search `test_match_map_pattern_shape`),
`tests/test_interpreter.py` (extend `class TestMatchExpression`, search
`test_map_pattern_binds_named_keys`, with the default cases above). Once
merged, `README.md`'s `match` expression bullet needs its map-pattern
description widened to mention defaults, its "Status & roadmap" section
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
