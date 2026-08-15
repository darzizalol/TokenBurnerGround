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

## 1. Language: default values in map-destructuring patterns (`let {a, b = 5} = expr;`)

Build: the depth task after task 5's breadth work (`num_divisors`) per
`PROJECT.md`'s breadth-vs-depth policy — restocking the backlog back to
6 tasks now that `is_pronic` has landed and dropped the count to the
5-task floor. This is the map-pattern counterpart to task 1 (default
values in *list*-destructuring patterns), explicitly flagged there as
"a separate design decision, left for a future task if wanted" since
map patterns have a different existing "missing key" behavior. Today
every map-destructuring form — `let {a, b} = expr;`, plain assignment
`{a, b} = expr;`, `for {a, b} in list_of_maps { ... }`, function params
`fn f({a, b}) { ... }`, and both comprehension loop-variable forms —
raises when the source map doesn't have one of the pattern's keys; there
is no way to say "use this value if the key wasn't present", unlike list
patterns (once task 1 lands) or function parameters, both of which
support a fallback for "nothing was supplied". Verify the gap:
`python3 -m cinder.cli eval 'let {a, b = 5} = {"a": 1}; print(a); print(b);'`
currently raises `CinderRuntimeError` `"destructuring pattern expects
key 'b', not found in map"` (`cinder/interpreter.py`'s
`_bind_map_destructure` has no concept of an optional entry).

All five in-scope forms — including, notably, the **plain-assignment**
form (`{a, b} = expr;`), unlike task 1's list-pattern version which
explicitly excludes it — share one parser entry point,
`_destructure_map_pattern_entry` (search for `def
_destructure_map_pattern_entry` in `cinder/parser.py`), called both from
`_destructure_map_pattern` (the `let`/`for`/param/comprehension path)
*and* directly from `_try_map_destructure_assign_statement` (the
plain-assignment path, search for `def
_try_map_destructure_assign_statement`) — unlike the list-pattern case,
where the plain-assignment form parses through an unrelated
`ListLiteral`/`_destructure_assign_pattern` path that couldn't accept
`=` inside an element, the map-pattern plain-assignment form already
routes through the exact same entry-parsing helper as every other form.
Adding default parsing to that one helper therefore extends **all five**
forms for free — no additional scoping exclusion needed, and no risky
parser surgery on a different code path. The single interpreter entry
point is `_bind_map_destructure` (search for `def _bind_map_destructure`
in `cinder/interpreter.py`), shared by all five forms including
plain-assignment (`use_assign=True`).

Unlike list patterns, map-pattern entries have **no positional
ordering** — matching is by key, not position — so there is no
`seen_default`-style "a required entry can't follow a defaulted one"
restriction to enforce; a default may appear anywhere among a pattern's
entries in any order, since nothing about pattern-source-position
comparison exists for maps in the first place.

Change `_destructure_map_pattern_entry`'s return type from a flat
`tuple[str, str]` of `(key, binding)` to a `tuple[str, str, "Expr |
None"]` of `(key, binding, default)`, `default` being `None` when no
`= expr` was written, parsed *after* the optional `: binding` rename so
`{a: x = 5}` (rename plus default together) works:

```python
def _destructure_map_pattern_entry(self) -> "tuple[str, str, Expr | None]":
    key = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    if self._check(TokenType.COLON):
        self._advance()
        binding = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern").lexeme
    else:
        binding = key
    default = None
    if self._check(TokenType.EQ):
        self._advance()
        default = self._ternary()
    return key, binding, default
```

`_destructure_map_pattern` and `_try_map_destructure_assign_statement`
need **no changes at all** beyond this — both already just call
`self._destructure_map_pattern_entry()` and append its return value
opaquely to `names`, so they pick up the triple shape automatically.
`_fn_param`'s existing rejection of a *whole-pattern* default (`fn
f({a, b} = {"a": 1})`, the `if self._check(TokenType.EQ): raise
ParseError("destructuring parameter cannot have a default value", ...)`
block right after the `_destructure_map_pattern()` call) stays
completely untouched — that check fires on the `=` *after* the closing
`}`, while this task's per-entry defaults are consumed *inside* the
braces, exactly the same non-interaction task 1 established for list
patterns: `fn f({a, b = 1}) { ... }` (a per-entry default) is accepted
by this task, `fn f({a, b} = {"a": 1, "b": 2}) { ... }` (a whole-pattern
default) still isn't, by design.

In `_bind_map_destructure`, unpack the triples and fill in a missing
key's value from its default when present, evaluated in `env` in
pattern order (so a later default *can* see an earlier pattern name
already bound in the same `env` — e.g. `let {a, b = a + 1} = {"a": 5};`
binds `b` to `6`, mirroring task 1's identical left-to-right rule for
list patterns):

```python
def _bind_map_destructure(
    self,
    env: Environment,
    names: list,
    rest: "str | None",
    value: object,
    line: int,
    column: int,
    use_assign: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise CinderRuntimeError(
            f"cannot destructure {type_name(value)} as a map",
            line,
            column,
        )
    seen_keys = set()
    for key, binding, default in names:
        seen_keys.add(key)
        if key in value:
            item = value[key]
        elif default is not None:
            item = self.evaluate(default, env)
        else:
            raise CinderRuntimeError(
                f"destructuring pattern expects key {key!r}, not found in map",
                line,
                column,
            )
        self._bind_destructure_name(env, binding, item, line, column, use_assign)
    if rest is not None:
        remaining = {k: v for k, v in value.items() if k not in seen_keys}
        self._bind_destructure_name(env, rest, remaining, line, column, use_assign)
```

Note when no entry in the pattern has a default, every `key in value`
check that fails falls straight to the same pre-existing `raise` with
the exact same message text as today — this is purely additive for
every pre-existing pattern. `_bind_destructure_name` itself needs no
changes. `call_value` (search for `def call_value`) needs **no changes
at all** — its existing `Interpreter()._bind_map_destructure(call_env,
param.names, param.rest, value, line, column)` call site already
forwards `param.names` opaquely, exactly like task 1's list-pattern
equivalent.

Acceptance criteria:
- `let {a, b = 5} = {"a": 1}; print(a); print(b);` prints `1` then `5`
  — `b`'s key is absent from the source map, so its default is used.
- `let {a, b = 5} = {"a": 1, "b": 2}; print(b);` prints `2` — a default
  is only used when the source map's key is actually absent, not when
  present with a falsy-looking value.
- `let {a, b = a + 1} = {"a": 5}; print(b);` prints `6` — a later
  default can reference an earlier pattern name already bound in the
  same `let`.
- `let {a: x = 10} = {}; print(x);` prints `10` — key rename and a
  default combine on the same entry.
- `let {a: x = 1, b} = {"b": 2}; print(x); print(b);` prints `1` then
  `2` — a defaulted entry may appear *before* a required one with no
  ordering restriction (map patterns match by key, not position, unlike
  task 1's list-pattern ordering rule).
- `let {a} = {"a": 1};` (no defaults) behaves identically to before this
  task — purely additive syntax.
- `for {a, b = 0} in [{"a": 1}, {"a": 2, "b": 3}] { print(a + b); }`
  prints `1` then `5`.
- `fn f({a, b = 10}) { return a + b; } print(f({"a": 1}));` prints `11`.
- `print([a + b for {a, b = 100} in [{"a": 1}, {"a": 2, "b": 3}]]);`
  prints `[101, 5]`.
- `let {a = 1, ...rest} = {}; print(a); print(rest);` prints `1` then
  `{}` — a default combines with a trailing rest entry; the rest
  collects nothing since the source map was empty.
- `let a = 0; let b = 0; {a, b = 5} = {"a": 1}; print(a); print(b);`
  prints `1` then `5` — the plain-assignment form gains defaults too,
  unlike task 1's list-pattern version, since both share
  `_destructure_map_pattern_entry`.
- `let {a, b = 1} = {};` raises `CinderRuntimeError` matching
  `"destructuring pattern expects key 'a', not found in map"` — `a` has
  no default so it's still required; the exact, unchanged pre-existing
  message text for a required key that's actually missing.
- `fn f({a, b} = {"a": 1, "b": 2}) { ... }` (a whole-pattern default,
  not a per-entry one) still raises `ParseError` matching
  `"destructuring parameter cannot have a default value"` — unaffected
  by this task.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_map_pattern_entry`),
`cinder/interpreter.py` (`_bind_map_destructure`), `tests/test_parser.py`
(shape assertions for every map-pattern site — flip 2-tuples like
`[("a", "a")]` to 3-tuples like `[("a", "a", None)]`; search for
`"DestructureLetStmt"`, `"DestructureAssign"`, `"Param"`, and the raw
`stmt.names`/`node.names` assertions such as `test_for_map_destructure_*`
and `test_map_comprehension_*`, plus new default-value tests),
`tests/test_interpreter.py` (new default-value tests for `let`/plain
assignment/`for`/params/comprehensions). Once merged, `README.md`'s
destructuring bullets need a defaults-for-map-patterns mention added,
and `PROJECT.md`'s roadmap paragraph needs it moved from backlog to
landed — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Standard library: `prime_factors` — an integer's prime factors, with multiplicity

Build: the breadth task after task 5's depth work (default values in
map-destructuring patterns) per `PROJECT.md`'s breadth-vs-depth policy,
restocking the backlog back to 6 tasks now that `is_pronic` (which used
to sit at the top of this file) has landed and dropped the count to the
5-task floor. Add `prime_factors(n)` to `cinder/builtins.py`, registered
right after `aliquot_sum` (search for `def _aliquot_sum`, the current
last entry in the divisor cluster) — the natural neighbor to
`divisors`/`is_prime`/`is_composite`: where `divisors` finds every
factor of `n` and `is_prime`/`is_composite` classify `n` as a whole,
`prime_factors` decomposes `n` into its prime building blocks, with
multiplicity, in ascending order (e.g. `12 -> [2, 2, 3]`, `360 -> [2,
2, 2, 3, 3, 5]`). Unlike `divisors`/`aliquot_sum`/`num_divisors`, which
all pair divisors up to `sqrt(n)` against the fixed original value,
this uses the standard trial-division *factorization* technique:
strip small prime factors out of a shrinking copy of `n` as you find
them, so a repeated factor (like `2` dividing `12` twice) is recorded
each time it divides evenly, not just once:

```python
def _prime_factors(arguments: list, line: int, column: int) -> object:
    _require_arity("prime_factors", arguments, 1, line, column)
    value = _require_int("prime_factors", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "prime_factors() requires a positive integer, domain error", line, column
        )
    result = []
    remaining = value
    divisor = 2
    while divisor * divisor <= remaining:
        while remaining % divisor == 0:
            result.append(divisor)
            remaining //= divisor
        divisor += 1
    if remaining > 1:
        result.append(remaining)
    return result
```

Model the arity/type-checking exactly on `divisors`/`aliquot_sum`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). `n < 1`
raises a domain error rather than returning a list, mirroring
`divisors`/`aliquot_sum`'s own type-vs-domain-error convention.
`prime_factors(1)` is the one case worth calling out explicitly: the
`while divisor * divisor <= remaining` loop never runs (`2 * 2 > 1`)
and the trailing `if remaining > 1` guard is also false (`remaining`
is still `1`), so the function returns `[]` — `1` has no prime
factors, which is mathematically correct, not a bug to guard against
with a special case the way `divisors(1)` special-cases its own `[1]`
result.

Acceptance criteria:
- `prime_factors(1);` is `[]` — `1` has no prime factors.
- `prime_factors(2);` is `[2]` — a prime is its own sole factor.
- `prime_factors(12);` is `[2, 2, 3]` — `2 * 2 * 3 = 12`, `2` appearing
  twice since it divides `12` twice.
- `prime_factors(97);` is `[97]` — `97` is itself prime, caught by the
  trailing `if remaining > 1` guard since the loop's `divisor * divisor`
  never reaches `97` before `divisor` would have to exceed
  `sqrt(97) ≈ 9.8`.
- `prime_factors(360);` is `[2, 2, 2, 3, 3, 5]` — `2**3 * 3**2 * 5 =
  360`, a case with two different repeated prime factors, exercising
  the inner `while` loop's repeat-stripping for more than one prime.
- `prime_factors(0);` raises `CinderRuntimeError` matching
  `"prime_factors() requires a positive integer, domain error"`.
- `prime_factors(-12);` raises `CinderRuntimeError` matching
  `"prime_factors() requires a positive integer, domain error"`.
- `prime_factors(5.0);` raises `CinderRuntimeError` matching
  `"prime_factors() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `prime_factors(true);` raises `CinderRuntimeError` matching
  `"prime_factors() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near
`divisors`/`aliquot_sum`, see current line numbers — shift if earlier
tasks this cycle landed first), `tests/test_builtins.py`. Once merged,
`README.md`'s Builtins bullet needs `prime_factors` added near
`divisors`/`aliquot_sum`, and `PROJECT.md`'s roadmap paragraph needs it
moved from backlog to landed — leave both to the Architect's next
grooming pass, not this task.

---

## 3. Language: hole elements in list-destructuring patterns (`let [a, , c] = expr;`)

Build: the depth task after task 5's breadth work (`prime_factors`) per
`PROJECT.md`'s breadth-vs-depth policy, restocking the backlog back to
6 tasks now that `collatz_length` has landed and dropped the count to
the 5-task floor. This closes the last gap in the destructuring-pattern
cluster: every list-pattern form can already bind a name, collect a
rest (`...rest`), or fall back to a default when the source runs short
(`a = 5`), but there is no way to skip a position outright — `let [a,
b, c] = [1, 2, 3]; ` must bind all three names even if the caller only
wants `a` and `c`, forcing a throwaway binding for `b`. JavaScript's
array-destructuring elision (`const [a, , c] = arr;`) is the model:
an empty slot between commas silently discards that position's value
instead of requiring a name for it. Verify the gap: `python3 -m
cinder.cli eval 'let [a, , c] = [1, 2, 3]; print(a); print(c);'`
currently raises `ParseError` `"expected identifier in destructuring
pattern, found ','"` (`cinder/parser.py`'s `_destructure_list_pattern_entry`,
search for `def _destructure_list_pattern_entry`, unconditionally
consumes an `IDENTIFIER` token with no path for an empty slot).

Not in scope: the plain-assignment form (`[a, , c] = expr;`) — for the
same reason task 1 (default values in list-destructuring patterns,
already landed) excluded it: that form's pattern is parsed by first
parsing an ordinary `ListLiteral` (`_destructure_assign_pattern`,
search for `def _destructure_assign_pattern`), whose elements are
ordinary expressions with no notion of an empty slot at that
precedence — teaching it one would be a materially different, riskier
parser change than this task takes on. Map-destructuring patterns are
also out of scope — they already have no positional concept at all
(matching is by key), so "skip a position" doesn't apply to them the
way it does to list patterns.

**Design — a hole is an empty slot strictly between two commas, or
between the opening `[` and the first comma (a *leading* hole).** A
hole is recognized only when the entry-parsing function is asked to
parse an entry and finds a `COMMA` sitting right there instead of an
`IDENTIFIER` — which, given how the caller loop is structured, can
only happen right after `[` (leading hole) or right after a comma that
was just consumed (interior hole). A comma immediately followed by `]`
(a trailing comma, or the pattern's very last slot) is deliberately
**not** treated as a hole and keeps today's exact behavior — it still
raises the same pre-existing `ParseError` it does today, since the
entry-parsing function only special-cases `COMMA`, never `RBRACKET`.
This sidesteps two ambiguities for free: a trailing hole right before
`]` stays unsupported (no new "does a trailing comma mean anything"
question to answer), and a completely empty pattern `let [] = expr;`
is untouched (it still hits the same pre-existing error it does today,
since the very first entry parse sees `RBRACKET`, not `COMMA`).

**Parsing** (`cinder/parser.py`): change
`_destructure_list_pattern_entry`'s return type from `tuple[str, Expr
| None]` to `tuple[str | None, Expr | None]` — `None` for the name
means a hole. Add the `COMMA` check as the very first thing the
function does, before it tries to consume an `IDENTIFIER`, and — this
is the part worth getting right — keep the *existing* `seen_default`
check active for a hole exactly like it is for a named entry, so a
hole can never sit after a defaulted entry either (a hole is a
no-default entry just like a required name is; letting it skip the
ordering check would let a required position drift past a defaulted
one positionally, which is exactly the bug the ordering check exists
to prevent — the `required = sum(1 for _, default in names if default
is None)` bounds math in `_bind_list_destructure` depends on every
no-default entry, holes included, forming a contiguous prefix):

```python
def _destructure_list_pattern_entry(self, seen_default: bool) -> "tuple[str | None, Expr | None]":
    if self._check(TokenType.COMMA):
        if seen_default:
            token = self._peek()
            raise ParseError(
                "element without a default value follows an element with one "
                "in destructuring pattern",
                token.line,
                token.column,
            )
        return None, None
    name_token = self._consume(TokenType.IDENTIFIER, "identifier in destructuring pattern")
    if self._check(TokenType.EQ):
        self._advance()
        default = self._ternary()
        return name_token.lexeme, default
    if seen_default:
        raise ParseError(
            "element without a default value follows an element with one "
            "in destructuring pattern",
            name_token.line,
            name_token.column,
        )
    return name_token.lexeme, None
```

`_destructure_list_pattern` (search for `def _destructure_list_pattern`,
just above the entry function) needs **no changes at all** — it
already just calls `_destructure_list_pattern_entry(seen_default)` in
three places (the unconditional first-entry call, and the two calls
inside the `while self._check(TokenType.COMMA):` loop body) and
appends the result to `names` opaquely; it already only ever inspects
`names[-1][1]` (the default), never `names[-1][0]` (the name), to
update `seen_default`, so a hole's `None` name flows through untouched.
`_destructure_let_statement`, `_for_statement`, `_fn_param`, and both
comprehension call sites (search for `_destructure_list_pattern()`,
five call sites total) need **no changes at all** either — all five
already forward `names` opaquely to a `DestructureLetStmt`/`ForStmt`/
`Param`/comprehension node, exactly the same "no changes needed"
pattern task 1 (list-destructuring defaults) established for these
same call sites.

**Evaluation** (`cinder/interpreter.py`): in `_bind_list_destructure`
(search for `def _bind_list_destructure`), both binding loops —
the `rest is not None` branch and the plain branch right after it —
currently end with an unconditional
`self._bind_destructure_name(env, name, item, line, column, use_assign)`
call. Guard both with `if name is not None:` so a hole's item is
computed (to advance past its position and keep index arithmetic
correct for later elements) but never bound to anything:

```python
        if rest is not None:
            ...
            for index, (name, default) in enumerate(names):
                item = value[index] if index < len(value) else self.evaluate(default, env)
                if name is not None:
                    self._bind_destructure_name(env, name, item, line, column, use_assign)
            self._bind_destructure_name(
                env, rest, list(value[len(names):]), line, column, use_assign
            )
            return
        ...
        for index, (name, default) in enumerate(names):
            item = value[index] if index < len(value) else self.evaluate(default, env)
            if name is not None:
                self._bind_destructure_name(env, name, item, line, column, use_assign)
```

Because the parser's `seen_default` guard (above) keeps every
no-default entry — holes included — in a contiguous prefix, `required`
(the count of no-default entries) is still exactly the number of
positions that must exist in `value`, so `index < len(value)` is
always `True` whenever `default is None` (hole or otherwise); the
`self.evaluate(default, env)` branch is never reached for a hole, so
there's no risk of ever calling `self.evaluate(None, env)`. No other
function in `_bind_list_destructure`'s vicinity needs changes — the
`required`/`has_defaults`/length-check logic above these loops already
operates purely on `default is None`, agnostic to whether `name` is
also `None`.

Acceptance criteria:
- `let [a, , c] = [1, 2, 3]; print(a); print(c);` prints `1` then `3`
  — the middle position is discarded, no binding created for it.
- `let [, b] = [1, 2]; print(b);` prints `2` — a leading hole.
- `let [a, ...rest] = [1, 2, 3];` (no holes) behaves identically to
  before this task — purely additive syntax.
- `let [a, , ...rest] = [1, 2, 3, 4]; print(a); print(rest);` prints
  `1` then `[3, 4]` — a hole combines with a trailing rest; the
  discarded position is not included in `rest`.
- `for [a, , c] in [[1, 2, 3], [4, 5, 6]] { print(a + c); }` prints `4`
  then `10`.
- `fn f([a, , c]) { return a + c; } print(f([1, 2, 3]));` prints `4`.
- `print([a + c for [a, , c] in [[1, 2, 3]]]);` prints `[4]`.
- `let [a, , c] = [1, 2];` raises `CinderRuntimeError` matching
  `"destructuring pattern expects 3 elements, got 2"` — a hole still
  occupies a required position; the source list must be long enough to
  reach it even though nothing is bound there.
- `let [a = 1, , c] = [9];` raises `ParseError` matching `"element
  without a default value follows an element with one in destructuring
  pattern"` — a hole is a no-default entry, so it cannot follow a
  defaulted one, same ordering rule a named required entry already
  enforces.
- `let [a, b, ] = [1, 2, 3];` still raises the exact same `ParseError`
  it does today (unchanged — a comma immediately before `]` is never
  treated as a hole).
- `let [] = [1];` still raises the exact same `ParseError` it does
  today (unchanged — the first entry parse sees `]`, not a comma).
- `[a, , c] = [1, 2, 3];` (plain-assignment form) still raises
  `ParseError` matching `"invalid assignment target"` (unaffected by
  this task — out of scope, per the Not-in-scope discussion above).
- Every pre-existing list-destructuring test (rest elements, defaults,
  renames are map-only so not applicable here, plain assignment)
  continues to pass unmodified.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_destructure_list_pattern_entry`),
`cinder/interpreter.py` (`_bind_list_destructure`), `tests/test_parser.py`
(shape assertions for `let`/`for`/param/comprehension list patterns —
search for `"DestructureLetStmt"`, `"ForStmt"`, `"Param"`, and the raw
`stmt.names`/`node.names` assertions; flip a few existing 2-tuples to
include a `(None, None)` hole entry, plus new hole-specific shape
tests), `tests/test_interpreter.py` (new hole-binding tests across all
four in-scope forms, plus the ordering-violation `ParseError` test and
the unchanged-trailing-comma/empty-pattern regression tests). Once
merged, `README.md`'s destructuring bullets need a hole-elements
mention added, and `PROJECT.md`'s roadmap paragraph needs it moved from
backlog to landed — leave both to the Architect's next grooming pass,
not this task.

---

## 4. Standard library: `is_squarefree` — no repeated prime factor

Build: the breadth task after task 5's depth work (hole elements in
list-destructuring patterns) per `PROJECT.md`'s breadth-vs-depth
policy, restocking the backlog back to 6 tasks now that
`is_strong_number` has landed and dropped the count to the 5-task
floor. Add `is_squarefree(n)` to `cinder/builtins.py`, registered right
after `is_pronic` (search for `def _is_pronic`, the current last entry
in the integer-property predicate cluster before the divisor cluster
begins) — a positive integer is squarefree when no perfect square
greater than `1` divides it evenly, equivalently when none of its
prime factors repeats (e.g. `6 = 2 * 3` is squarefree, `12 = 2 * 2 * 3`
is not, since `4` divides it). This is the natural predicate neighbor
to `is_prime`/`is_composite` (which classify `n` as a whole) and the
soon-to-land `prime_factors` (task 4, which lists factors with
multiplicity) — `is_squarefree` answers "does any factor repeat?"
without needing to build the full factor list, via the same
`sqrt(n)`-bounded trial-division shape `is_prime`/`is_composite`
already use, checking `divisor * divisor` divisibility directly rather
than a fixed divisor:

```python
def _is_squarefree(arguments: list, line: int, column: int) -> object:
    _require_arity("is_squarefree", arguments, 1, line, column)
    value = _require_int("is_squarefree", arguments[0], line, column)
    if value < 1:
        return False
    for divisor in range(2, math.isqrt(value) + 1):
        if value % (divisor * divisor) == 0:
            return False
    return True
```

Model the arity/type-checking exactly on `is_prime`/`is_pronic`'s own
structure: `_require_arity`, then `_require_int` (reusing the shared
helper — do **not** hand-roll a separate `isinstance` check). `n < 1`
returns `false` rather than raising, matching the boolean-predicate
cluster's own convention (`is_prime`, `is_pronic`, `is_harshad`, etc. —
*not* the divisor cluster's type-vs-domain-error convention, since this
builtin returns a boolean, not a number). `value == 1` is a genuine
`true` case handled for free by the loop: `math.isqrt(1) + 1 == 2`, so
`range(2, 2)` is empty and the function falls through to `return True`
— `1` has no prime factors at all, so vacuously none of them repeats.

Acceptance criteria:
- `is_squarefree(1);` is `true` — vacuously squarefree, the empty-loop
  case above.
- `is_squarefree(6);` is `true` — `6 = 2 * 3`, no repeated factor.
- `is_squarefree(30);` is `true` — `30 = 2 * 3 * 5`.
- `is_squarefree(4);` is `false` — `4 = 2 * 2`, divisible by the
  perfect square `4`.
- `is_squarefree(12);` is `false` — `12 = 2 * 2 * 3`, divisible by `4`.
- `is_squarefree(45);` is `false` — `45 = 3 * 3 * 5`, divisible by `9`.
- `is_squarefree(0);` is `false` — below the domain floor.
- `is_squarefree(-6);` is `false` — negative input, same convention as
  `is_prime`/`is_pronic`.
- `is_squarefree(5.0);` raises `CinderRuntimeError` matching
  `"is_squarefree() requires an int, got float"` — the same message
  shape `_require_int` already produces for every sibling in this
  cluster.
- `is_squarefree(true);` raises `CinderRuntimeError` matching
  `"is_squarefree() requires an int, got bool"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (register near `is_pronic`, see
current line numbers — shift if earlier tasks this cycle landed
first), `tests/test_builtins.py` (model on the `is_pronic` test class,
search for `test_is_pronic_of_`). Once merged, `README.md`'s Builtins
bullet needs `is_squarefree` added near `is_prime`/`is_pronic`, and
`PROJECT.md`'s roadmap paragraph needs it moved from backlog to landed
— leave both to the Architect's next grooming pass, not this task.

---

## 5. Language: optional catch binding (`try { ... } catch { ... }`, no name required)

Build: the depth task after task 5's breadth work (`is_squarefree`) per
`PROJECT.md`'s breadth-vs-depth policy — also restocking the backlog
back to 6 tasks now that unary `+` (the task that used to sit at the
top of this file) has landed and dropped the count to the 5-task
floor. Today `catch` always requires a parenthesized binding name —
`try { ... } catch (name) { ... }` — even when the handler never reads
the caught error message, forcing a throwaway name for the common
"just recover, don't inspect" case. Verify the gap: `python3 -m
cinder.cli eval 'try { throw "boom"; } catch { print("caught"); }'`
currently raises `ParseError` `"expected '(' after 'catch', found
'{'"` (`cinder/parser.py`'s `_try_statement`, search for `def
_try_statement`, unconditionally consumes `(`, an identifier, and `)`
right after the `catch` keyword).

**Parsing** (`cinder/parser.py`): in `_try_statement`, right after
`self._advance()` consumes the `catch` token, only parse the
`(name)` group when the next token is actually `(` — otherwise leave
`catch_name` as `None` and fall straight through to the body-block
check:

```python
        catch_name = None
        catch_block = None
        if self._check(TokenType.CATCH):
            self._advance()
            if self._check(TokenType.LPAREN):
                self._advance()
                name_token = self._consume(
                    TokenType.IDENTIFIER, "identifier after 'catch ('"
                )
                self._consume(TokenType.RPAREN, "')' after catch name")
                catch_name = name_token.lexeme
            if not self._check(TokenType.LBRACE):
                token = self._peek()
                raise ParseError(
                    f"expected '{{' before catch body, found {self._describe(token)}",
                    token.line,
                    token.column,
                )
            catch_block = self._block()
```

No AST change is needed — `TryStmt.catch_name` (`cinder/ast_nodes.py`)
is already typed `str | None`; today's parser just never actually
produces the `None` case. Every other branch of `_try_statement`
(`finally` parsing, the `catch_block is None and finally_block is
None` "expected 'catch' or 'finally'" check, the final `TryStmt(...)`
construction) needs no changes at all.

**Evaluation** (`cinder/interpreter.py`): in `_execute_try` (search for
`def _execute_try`), guard the existing `catch_env.define(...)` call
so it only runs when a name was actually written — the catch block
still gets its own fresh child environment either way (so a `let`
declared inside it doesn't leak into the surrounding scope), it just
has nothing pre-bound when there's no name:

```python
            except CinderRuntimeError as error:
                if stmt.catch_block is None:
                    raise
                catch_env = Environment(env)
                if stmt.catch_name is not None:
                    catch_env.define(stmt.catch_name, error.message)
                self.execute(stmt.catch_block, catch_env)
```

Acceptance criteria:
- `try { throw "boom"; } catch { print("caught"); }` prints `caught` —
  the catch block runs with no name bound.
- `try { throw "boom"; } catch { print("caught"); } finally { print("done"); }`
  prints `caught` then `done` — `finally` still runs afterward,
  unaffected by the missing name.
- `try { throw "boom"; } catch (e) { print(e); }` still prints `boom`
  — the named form is completely unchanged.
- `let ran = 0; try { 1; } catch { ran = 1; }` leaves `ran` at `0` — a
  nameless catch block still only runs when an error was actually
  thrown, same as the named form.
- `try { throw "x"; } catch { let y = 1; } y;` raises
  `CinderRuntimeError` matching `undefined name 'y'` — the catch
  block's own child environment doesn't leak into the surrounding
  scope, same as the named form.
- `try { throw "x"; } catch { e; }` raises `CinderRuntimeError`
  matching `undefined name 'e'` — confirms no binding is created under
  any implicit name when `(name)` is omitted.
- `fn f() { try { throw "x"; } catch { return 1; } return 2; } print(f());`
  prints `1` — `return` inside a nameless catch block still propagates
  out of the function, same as the named form.
- `try { print(1); }` (neither `catch` nor `finally`) still raises the
  exact same `ParseError` it does today, `"expected 'catch' or
  'finally' after try block, found ..."` — unaffected.
- `try { print(1); } catch (e)` (missing body) still raises the exact
  same `ParseError` it does today — unaffected, since the `LBRACE`
  check after the optional `(name)` group is unchanged.
- Every pre-existing try/catch/finally test (nested try/catch, catch
  inside a loop/function, error-inside-catch-not-re-caught, finally
  ordering) continues to pass unmodified.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_try_statement`),
`cinder/interpreter.py` (`_execute_try`), `tests/test_parser.py`
(shape assertions — search for `test_try_catch_shape`,
`test_try_catch_empty_bodies`, `test_try_catch_finally_shape`, plus a
new nameless-catch shape test asserting `catch_name` is `None`),
`tests/test_interpreter.py` (new nameless-catch tests modeled on the
existing `test_catch_binds_error_message_and_recovers`,
`test_catch_block_does_not_run_when_no_error`,
`test_catch_name_not_visible_after_try_catch` cluster, search for
`class ... Try` or `def test_catch_`). Once merged, `README.md`'s
Control flow bullet needs a nameless-catch mention added next to the
existing `try`/`catch`/`finally` description, and `PROJECT.md`'s
roadmap paragraph needs it moved from backlog to landed — leave both
to the Architect's next grooming pass, not this task.

---

## Done

Completed tasks are archived in [`CHANGELOG.md`](CHANGELOG.md), not
kept here — keeps this file short for whoever's claiming the next task.

---

## Graveyard

(none yet)
