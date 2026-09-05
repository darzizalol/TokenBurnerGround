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

## 1. Standard library: `nth_refactorable` — refactorable number found at a 1-indexed position

Build: `is_refactorable` (`cinder/builtins.py`, search `def
_is_refactorable`: whether `n`'s own divisor count divides back into
`n`, e.g. `8` has 4 divisors and `8 % 4 == 0`) has no value-returning
`nth_*` sibling, the same gap `nth_practical_number`/`nth_semiperfect`
already closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_refactorable(1));'
# -> <eval>:1:7: undefined name 'nth_refactorable' (did you mean
#    'is_refactorable'?)
```

Worked examples: the first ten refactorable numbers are `1, 2, 8, 9, 12,
18, 24, 36, 40, 56` (`1` is trivially refactorable — `_is_refactorable`
special-cases it to `True` — and `2` has 2 divisors, `2 % 2 == 0`), so
`nth_refactorable(1)` is `1` and `nth_refactorable(10)` is `56`. The 20th
is `132`.

Add directly after `_is_refactorable` (search `def _is_refactorable`,
immediately before `def _is_amicable`):
```python
def _nth_refactorable(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_refactorable", arguments, 1, line, column)
    value = _require_int("nth_refactorable", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_refactorable() requires a positive integer, domain error",
            line, column,
        )

    def _is_refactorable_candidate(candidate: int) -> bool:
        if candidate == 1:
            return True
        count = 2
        for divisor in range(2, math.isqrt(candidate) + 1):
            if candidate % divisor == 0:
                count += 1
                complement = candidate // divisor
                if complement != divisor:
                    count += 1
        return candidate % count == 0

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_refactorable_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`/`_nth_semiperfect`, with the
inner candidate check copied from `_is_refactorable`'s own body instead
of calling `_is_refactorable` directly — the same "duplicate the tiny
predicate body instead of a redundant `_require_arity`/`_require_int`
round-trip per candidate" choice `_nth_harshad`/`_nth_squarefree`
already make.) Register the new dict entry (search
`"is_refactorable": _is_refactorable,`, add `"nth_refactorable":
_nth_refactorable,` directly after it).

Acceptance criteria:
- `nth_refactorable(1);` through `nth_refactorable(10);` are `1, 2, 8, 9,
  12, 18, 24, 36, 40, 56` in order — the worked example above.
- `nth_refactorable(20);` is `132` — a further worked example confirming
  the scan scales past the first ten.
- For every `position` in `1..50`, `is_refactorable(nth_refactorable(position))`
  is `true` — the same self-consistency check `nth_practical_number`/
  `nth_semiperfect`'s own test suites already run against their
  predicates.
- `nth_refactorable(0);`, `nth_refactorable(-3);` both raise
  `CinderRuntimeError` matching `"nth_refactorable\(\) requires a
  positive integer, domain error"`.
- `nth_refactorable(true);` raises `CinderRuntimeError` matching
  `"nth_refactorable\(\) requires an int, got bool"`.
- `nth_refactorable("5");` raises `CinderRuntimeError` matching
  `"nth_refactorable\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_refactorable`,
search `def _is_refactorable`), `tests/test_builtins.py` (new `class
TestNthRefactorable`, modeled on `class TestNthPracticalNumber`/`class
TestNthSemiperfect`, search either name, for the test shapes above —
place it near the existing `class TestIsRefactorable`, search that
name). Once merged, `README.md`'s Builtins bullet needs `nth_refactorable`
added near `is_refactorable`, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 2. Language: bare hole-element spelling (`[a, , c]`) in `match` list patterns

Build: `let`/`for`/function-param/comprehension list-destructuring patterns
all accept a bare comma-comma hole to skip an unwanted position
(`let [a, , c] = expr;` — see the README's "Variables & scope" bullet), but
`match`'s own list patterns only offer the equivalent via an explicit `_`
placeholder (`match ([1, 2, 3]) { [a, _, c] => a + c, _ => 0 }`, which
already works today) — the bare comma spelling raises a `ParseError`
instead of being treated the same way. Verify the gap:
```sh
python3 -m cinder.cli eval 'let r = match ([1, 2, 3]) { [a, , c] => a + c, _ => 0 }; print(r);'
# -> <eval>:1:31: expected an identifier, '_', or a literal inside list pattern, found ','
python3 -m cinder.cli eval 'let r = match ([1, 2, 3]) { [, b, c] => b + c, _ => 0 }; print(r);'
# -> <eval>:1:28: expected an identifier, '_', or a literal inside list pattern, found ','
```

Worked examples: `match ([1, 2, 3]) { [a, , c] => a + c, _ => 0 }` should
evaluate to `4`, exactly like the already-working `[a, _, c]` spelling
(confirmed: `match ([1, 2, 3]) { [a, _, c] => a + c, _ => 0 }` is already
`4` today). `match ([1, 2, 3]) { [, b, c] => b + c, _ => 0 }` (leading
hole) should be `5`, exactly like `[_, b, c]` (confirmed already `5`
today).

Root cause and fix shape: `_match_list_pattern_entry` (search `def
_match_list_pattern_entry`, `cinder/parser.py`) has no branch for a
`COMMA` token — it falls straight to the final `else: raise ParseError`
for anything that isn't an identifier/`_`/literal/nested pattern. The
`let`-destructuring equivalent, `_destructure_list_pattern_entry` (search
that name), already solves exactly this: its very first check is
```python
if self._check(TokenType.COMMA):
    if seen_default:
        raise _DestructurePatternCommittedError(...)
    return None, None
```
— a comma at entry-parsing position, *without consuming it*, means "this
slot is empty," and the caller's own comma-handling loop advances past it
on the next iteration. Add the equivalent branch as the first check in
`_match_list_pattern_entry`, right after its existing `token = self._peek()`
line:
```python
if token.type == TokenType.COMMA:
    if seen_default:
        raise ParseError(
            "element without a default value follows an element with "
            "one in list pattern",
            token.line,
            token.column,
        )
    return None, None
```
Use plain `ParseError` here, not `_DestructurePatternCommittedError` —
that marker class exists solely to survive `_assignment`'s speculative
list-literal-vs-destructure-assign fallback (see PR #393's postmortem in
`CHANGELOG.md`), and `_match_arm` (search `def _match_arm`) calls
`_match_list_pattern` directly with no surrounding `try`/`except
ParseError` to swallow it, so a plain `ParseError` already propagates
uncaught — confirmed by every other error path already in this function
(e.g. its own existing "element without a default value follows..." raise
a few lines down) using plain `ParseError` too.

No interpreter changes are needed at all: `_match_list_pattern_entry`'s
`_` handling already produces the exact same `entry = None` value
(search `entry = None if token.lexeme == "_" else token.lexeme`) that
this task's hole branch also returns, so every consumer downstream
(list-pattern binding, rest capture, nesting) already treats `None`
generically as "match this position but bind nothing" — confirmed
working today via `_` for wildcard-plus-rest (`match ([1,2,3,4]) { [a,
_, ...rest] => rest, _ => 0 }` is already `[3, 4]`) and leading-wildcard
(`match ([1,2,3]) { [_, b, c] => b + c, _ => 0 }` is already `5`).

Acceptance criteria:
- `match ([1, 2, 3]) { [a, , c] => a + c, _ => 0 }` is `4` — the first
  worked example above.
- `match ([1, 2, 3]) { [, b, c] => b + c, _ => 0 }` is `5` — the leading
  bare-hole worked example above.
- `match ([1, 2, 3, 4]) { [a, , ...rest] => rest, _ => 0 }` is `[3, 4]`
  — a bare hole composes with rest capture, mirroring the already-working
  `_`-plus-rest case above.
- `match ([1, [2, 3]]) { [a, [, c]] => a + c, _ => 0 }` is `4` — a bare
  hole works inside a nested list pattern too.
- `match ([1]) { [a = 1, ] => 0, _ => -1 }`-style ordering check:
  `match ([1]) { [a = 1, , c] => 0, _ => -1 }` raises `ParseError`
  matching `"element without a default value follows an element with one
  in list pattern"` — a bare hole is "no default," so it still triggers
  the existing ordering rule, exactly like a bare identifier would
  (confirmed today: `[a = 1, _]` already raises the same message).
- Regression: every existing `_`-wildcard test in
  `tests/test_interpreter.py`/`tests/test_parser.py` (search `TestMatch`)
  still passes unmodified — this task only adds a new accepted spelling,
  it does not change `_`'s own behavior.
- New tests in `tests/test_parser.py` and `tests/test_interpreter.py`
  (search `class TestMatch` in each) covering every acceptance case
  above, modeled on the existing `_`-wildcard match-pattern tests.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_match_list_pattern_entry`, search
that name), `tests/test_parser.py`, `tests/test_interpreter.py` per the
acceptance criteria above. Once merged, `README.md`'s `match` bullet
needs a one-clause mention that list patterns also accept the bare hole
spelling alongside `_`, and `PROJECT.md`'s "Current frontier" section
needs refreshing — leave both to the Architect's next grooming pass, not
this task.

---

## 3. Standard library: `nth_sphenic` — sphenic number found at a 1-indexed position

Build: `is_sphenic` (`cinder/builtins.py`, search `def _is_sphenic`:
whether `n` is the product of exactly three distinct primes, e.g.
`30 = 2 * 3 * 5`) has no value-returning `nth_*` sibling, the same gap
`nth_semiprime` already closed for `is_semiprime` (its own "product of
exactly two distinct primes" sibling). Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_sphenic(1));'
# -> <eval>:1:7: undefined name 'nth_sphenic' (did you mean
#    'is_sphenic'?)
```

Worked examples: the first ten sphenic numbers (OEIS A007304) are `30,
42, 66, 70, 78, 102, 105, 110, 114, 130` (`60 = 2^2 * 3 * 5` is skipped
— one prime factor appears with exponent 2, so only 2 *distinct* primes
count even though 4 prime factors appear with multiplicity), so
`nth_sphenic(1)` is `30` and `nth_sphenic(10)` is `130`. The 20th is
`222`.

Add directly after `_is_sphenic` (search `def _is_sphenic`, immediately
before `def _is_emirp`) — keeps the value-returning helper next to the
predicate it mirrors, matching where `nth_semiprime` itself sits right
after `is_semiprime`:
```python
def _nth_sphenic(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_sphenic", arguments, 1, line, column)
    value = _require_int("nth_sphenic", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_sphenic() requires a positive integer, domain error",
            line, column,
        )

    def _is_sphenic_candidate(candidate: int) -> bool:
        remaining = candidate
        distinct_count = 0
        divisor = 2
        while divisor * divisor <= remaining:
            if remaining % divisor == 0:
                count = 0
                while remaining % divisor == 0:
                    remaining //= divisor
                    count += 1
                if count != 1:
                    return False
                distinct_count += 1
                if distinct_count > 3:
                    return False
            divisor += 1
        if remaining > 1:
            distinct_count += 1
        return distinct_count == 3

    count = 0
    candidate = 1
    while count < value:
        candidate += 1
        if _is_sphenic_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_semiprime`, with the inner candidate check
copied from `_is_sphenic`'s own body instead of calling `_is_sphenic`
directly — the same "duplicate the tiny predicate body instead of a
redundant `_require_arity`/`_require_int` round-trip per candidate"
choice `_nth_semiprime`/`_nth_harshad`/`_nth_refactorable` already
make.) Register the new dict entry (search `"is_sphenic": _is_sphenic,`,
add `"nth_sphenic": _nth_sphenic,` directly after it, before `"is_emirp":
_is_emirp,`).

Acceptance criteria:
- `nth_sphenic(1);` through `nth_sphenic(10);` are `30, 42, 66, 70, 78,
  102, 105, 110, 114, 130` in order — the worked example above.
- `nth_sphenic(20);` is `222` — a further worked example confirming the
  scan scales past the first ten.
- For every `position` in `1..50`, `is_sphenic(nth_sphenic(position))`
  is `true` — the same self-consistency check `nth_semiprime`'s own
  test suite already runs against `is_semiprime`.
- `nth_sphenic(0);`, `nth_sphenic(-3);` both raise `CinderRuntimeError`
  matching `"nth_sphenic\(\) requires a positive integer, domain
  error"`.
- `nth_sphenic(true);` raises `CinderRuntimeError` matching
  `"nth_sphenic\(\) requires an int, got bool"`.
- `nth_sphenic("5");` raises `CinderRuntimeError` matching
  `"nth_sphenic\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_sphenic`, search
`def _is_sphenic`), `tests/test_builtins.py` (new `class TestNthSphenic`,
modeled on `class TestNthSemiprime`, search that name, for the test
shapes above — place it near the existing `class TestIsSphenic`, search
that name). Once merged, `README.md`'s Builtins bullet needs
`nth_sphenic` added near `is_sphenic`, its "Status & roadmap" section
needs updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 4. Language: destructuring patterns inside comma-separated `let`/`const` sequences

Build: `let a = 1, b = 2;` (comma-separated multiple declarations, each
with its own initializer, later ones seeing earlier-bound names — see
the README's "Variables & scope" bullet) and `let [a, b] = expr;`
(destructuring, now also on `const` per PR #395) each work fine on
their own, but a comma sequence can't mix the two: putting a
destructuring pattern anywhere in a `let`/`const` comma chain is a
`ParseError`. Verify the gap:
```sh
python3 -m cinder.cli eval 'let a = 1, [b, c] = [2, 3]; print(a); print(b); print(c);'
# -> <eval>:1:12: expected identifier after 'let', found '['
python3 -m cinder.cli eval 'let [a, b] = [1, 2], c = 3; print(a); print(b); print(c);'
# -> <eval>:1:20: expected ';' after variable declaration, found ','
python3 -m cinder.cli eval 'const a = 1, [b, c] = [2, 3]; print(a);'
# -> <eval>:1:14: expected identifier after 'const', found '['
python3 -m cinder.cli eval 'const [a, b] = [1, 2], c = 3; print(a);'
# -> <eval>:1:22: expected ';' after variable declaration, found ','
```

Root cause: `_let_statement`/`_const_statement` (search either name,
`cinder/parser.py`) each start with a single up-front check — `if
self._check(TokenType.LBRACKET)`/`LBRACE`, delegate the *entire*
statement (pattern, `=`, initializer, **and its own trailing `;`**) to
`_destructure_let_statement`, and `return` immediately — before ever
reaching the comma-chaining loop a few lines below
(`while self._check(TokenType.COMMA): ... declarations.append(...)`),
which itself only calls `_one_let_declaration`/`_one_const_declaration`
(plain-identifier-only, via `self._consume(TokenType.IDENTIFIER, ...)`)
per iteration. So a leading pattern short-circuits into the
single-declaration destructure path and never sees the comma loop
(second/fourth repro above: the destructure path's own `;` consume
fails on the following `,`), and a leading plain name enters the comma
loop but that loop's per-item helper has no pattern branch (first/third
repro above: `_one_let_declaration` demands an `IDENTIFIER` unconditionally).

Fix shape: make each comma-loop iteration dispatch on the next token the
same way the statement-level check already does, instead of assuming
`IDENTIFIER`. Split `_destructure_let_statement`'s body into a
per-declarator piece with **no semicolon consumption** (the semicolon
belongs to the whole sequence, not to one item), and route every
declarator — plain or destructured — through the comma loop uniformly:
```python
def _let_statement(self) -> Stmt:
    let_token = self._advance()
    declarations = [self._one_let_declarator(let_token)]
    while self._check(TokenType.COMMA):
        self._advance()
        declarations.append(self._one_let_declarator(let_token))
    self._consume(TokenType.SEMICOLON, "';' after variable declaration")
    if len(declarations) == 1:
        return declarations[0]
    return DeclSeq(declarations, let_token.line, let_token.column)

def _one_let_declarator(self, let_token: Token) -> Stmt:
    if self._check(TokenType.LBRACKET):
        return self._destructure_declarator(let_token, is_map=False, is_const=False)
    if self._check(TokenType.LBRACE):
        return self._destructure_declarator(let_token, is_map=True, is_const=False)
    return self._one_let_declaration(let_token)
```
(`_const_statement`/`_one_const_declarator` mirror this exactly, calling
`_one_const_declaration` in the fallback branch and passing
`is_const=True`.) Replace `_destructure_let_statement` with a shared
per-declarator helper used by both:
```python
def _destructure_declarator(self, let_token: Token, is_map: bool, is_const: bool) -> "DestructureLetStmt":
    if is_map:
        names, rest = self._destructure_map_pattern()
    else:
        names, rest = self._destructure_list_pattern()
    self._consume(TokenType.EQ, "'=' after destructuring pattern")
    initializer = self._assignment()
    return DestructureLetStmt(
        names, initializer, let_token.line, let_token.column,
        is_map=is_map, rest=rest, is_const=is_const,
    )
```
No changes needed anywhere else: `DeclSeq.execute` (search `isinstance(stmt,
DeclSeq)`, `cinder/interpreter.py`) already just executes each
declaration in `stmt.declarations` against the same `env` in order,
generic over which `Stmt` subclass each one is — it doesn't know or
care that this task makes that list able to mix `LetStmt`/`ConstStmt`
and `DestructureLetStmt` for the first time, so "later declarator sees
an earlier-bound name" and "declarations land in the caller's scope"
both fall out for free, exactly as they already do for today's
plain-only sequences. `shape()`'s existing `DestructureLetStmt` case
(`tests/test_parser.py`, search `"DestructureLetStmt"`) also needs no
change — it already renders any `DestructureLetStmt` node the same way
regardless of whether it sits alone or inside a `DeclSeq`. The C-style
`for (...)` init clause (search `init = self._let_statement()` in
`_for_c_statement`) calls `_let_statement()` wholesale and therefore
gains this too as a side effect — worth a quick manual check, not a
required acceptance item below.

Acceptance criteria:
- `let a = 1, [b, c] = [2, 3]; print(a); print(b); print(c);` prints
  `1`, `2`, `3` — the first repro above, now working.
- `let [a, b] = [1, 2], c = 3; print(a); print(b); print(c);` prints
  `1`, `2`, `3` — the second repro above, now working.
- `const a = 1, [b, c] = [2, 3];` then reassigning `b` (`b = 9;`) raises
  `CinderRuntimeError` for reassigning a `const` — the whole sequence
  inherits `const`'s freeze semantics per declarator, matching how a
  lone `const [b, c] = [2, 3];` already freezes `b`/`c` today.
- `let a = 1, [b, c] = [a, a + 1]; print(b); print(c);` prints `2`, `3`
  — a destructuring declarator's initializer sees an earlier plain
  declarator's bound name, the same left-to-right visibility
  `test_let_comma_separated_later_sees_earlier` already pins for two
  plain declarators.
- `let [a, b] = [1, 2], {c, d} = {"c": 3, "d": 4}; print(c); print(d);`
  prints `3`, `4` — two destructuring declarators (list then map) chain
  in one sequence.
- Regression: every existing test in `TestStatements`
  (`tests/test_interpreter.py`, search that name — the
  `test_let_comma_separated_*` tests) and `TestConst`,
  `TestDestructureLet`, `TestConstDestructure` (search each name) still
  passes unmodified — this task only adds a new *combination*, it
  changes no existing single-form behavior.
- New tests in `tests/test_parser.py`: shape assertions for
  `let a = 1, [b, c] = [2, 3];` and `let [a, b] = [1, 2], c = 3;`
  parsing to a `DeclSeq` containing the expected mix of `LetStmt`/
  `DestructureLetStmt` shapes (modeled on
  `test_expr_statement_comma_separated_becomes_decl_seq`, search that
  name), plus one asserting `is_const` directly on the
  `DestructureLetStmt` node for a `const` sequence (same "assert the
  field directly, don't extend the fixed-shape tuple" choice PR #395
  made for `is_const`, since `shape()` doesn't carry it).
- New tests in `tests/test_interpreter.py`: add to `TestStatements`
  (search that name) covering every acceptance case above.
- Full test suite passes.

Likely files: `cinder/parser.py` (`_let_statement`, `_const_statement`,
`_destructure_let_statement` — search each name), `tests/test_parser.py`,
`tests/test_interpreter.py` per the acceptance criteria above. Once
merged, `README.md`'s "Variables & scope" bullet needs a clause noting
that comma-separated `let`/`const` sequences may mix plain and
destructuring declarators, its "Status & roadmap" section needs
updating, and `PROJECT.md`'s "Current frontier" section needs
refreshing — leave both to the Architect's next grooming pass, not this
task.

---

## 5. Standard library: `nth_powerful_number` — powerful number found at a 1-indexed position

Build: `is_powerful_number` (`cinder/builtins.py`, search `def
_is_powerful_number`: whether every prime factor of `n` appears with
exponent `2` or more, e.g. `72 = 2^3 * 3^2`) has no value-returning
`nth_*` sibling, the same gap `nth_practical_number`/`nth_semiperfect`
already closed for their own predicates. Verify the gap:
```sh
python3 -m cinder.cli eval 'print(nth_powerful_number(1));'
# -> <eval>:1:7: undefined name 'nth_powerful_number' (did you mean
#    'is_powerful_number'?)
```

Worked examples: the first ten powerful numbers are `1, 4, 8, 9, 16, 25,
27, 32, 36, 49` (`1` is trivially powerful — the loop below leaves
`remaining == 1` without ever entering the `if count < 2` branch), so
`nth_powerful_number(1)` is `1` and `nth_powerful_number(10)` is `49`.
The 20th is `169`.

Add directly after `_is_powerful_number` (search `def
_is_powerful_number`, immediately before `def _is_achilles`):
```python
def _nth_powerful_number(arguments: list, line: int, column: int) -> object:
    _require_arity("nth_powerful_number", arguments, 1, line, column)
    value = _require_int("nth_powerful_number", arguments[0], line, column)
    if value < 1:
        raise CinderRuntimeError(
            "nth_powerful_number() requires a positive integer, domain error",
            line, column,
        )

    def _is_powerful_candidate(candidate: int) -> bool:
        remaining = candidate
        divisor = 2
        while divisor * divisor <= remaining:
            if remaining % divisor == 0:
                count = 0
                while remaining % divisor == 0:
                    remaining //= divisor
                    count += 1
                if count < 2:
                    return False
            divisor += 1
        return remaining == 1

    count = 0
    candidate = 0
    while count < value:
        candidate += 1
        if _is_powerful_candidate(candidate):
            count += 1
    return candidate
```
(Identical shape to `_nth_practical_number`/`_nth_semiperfect`/
`_nth_refactorable`, with the inner candidate check copied from
`_is_powerful_number`'s own body instead of calling
`_is_powerful_number` directly — the same "duplicate the tiny predicate
body instead of a redundant `_require_arity`/`_require_int` round-trip
per candidate" choice every recent `nth_*` task already makes.) Register
the new dict entry (search `"is_powerful_number": _is_powerful_number,`,
add `"nth_powerful_number": _nth_powerful_number,` directly after it,
before `"is_achilles": _is_achilles,`).

Acceptance criteria:
- `nth_powerful_number(1);` through `nth_powerful_number(10);` are `1,
  4, 8, 9, 16, 25, 27, 32, 36, 49` in order — the worked example above.
- `nth_powerful_number(20);` is `169` — a further worked example
  confirming the scan scales past the first ten.
- For every `position` in `1..50`,
  `is_powerful_number(nth_powerful_number(position))` is `true` — the
  same self-consistency check `nth_practical_number`/`nth_semiperfect`'s
  own test suites already run against their predicates.
- `nth_powerful_number(0);`, `nth_powerful_number(-3);` both raise
  `CinderRuntimeError` matching `"nth_powerful_number\(\) requires a
  positive integer, domain error"`.
- `nth_powerful_number(true);` raises `CinderRuntimeError` matching
  `"nth_powerful_number\(\) requires an int, got bool"`.
- `nth_powerful_number("5");` raises `CinderRuntimeError` matching
  `"nth_powerful_number\(\) requires an int, got string"`.
- Wrong arity (not exactly 1 argument) raises `CinderRuntimeError` with
  line/column.
- Full test suite passes.

Likely files: `cinder/builtins.py` (directly after `_is_powerful_number`,
search `def _is_powerful_number`), `tests/test_builtins.py` (new `class
TestNthPowerfulNumber`, modeled on `class TestNthSemiperfect`, search
that name, for the test shapes above — place it near the existing `class
TestIsPowerfulNumber`, search that name). Once merged, `README.md`'s
Builtins bullet needs `nth_powerful_number` added near
`is_powerful_number`, its "Status & roadmap" section needs updating, and
`PROJECT.md`'s "Current frontier" section needs refreshing — leave both
to the Architect's next grooming pass, not this task.

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
