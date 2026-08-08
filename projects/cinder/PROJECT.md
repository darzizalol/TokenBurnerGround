# PROJECT.md — Cinder

## Vision

**Cinder** is a small, dynamically-typed scripting language with a
tree-walking interpreter, built entirely from scratch in pure Python (stdlib
only — no parser generators, no third-party packages). It is the product this
repo builds, night after night: lexer, parser, evaluator, standard library,
error diagnostics, and eventually a REPL good enough to actually enjoy using.

The point is depth over breadth. Every night adds one real, tested piece —
never a stub. By the time Cinder is "done" (there is no fixed end; see
Roadmap) it should be a small but complete language: variables, control flow,
functions with closures, lists and maps, a minimal standard library, and
error messages with line/column info that don't embarrass us.

Why a language interpreter: it decomposes naturally into independently
testable, strictly-ordered layers (you cannot parse before you can lex, you
cannot evaluate before you can parse), each layer has an unambiguous
correctness bar (does it produce the right tokens/AST/value?), and it scales
from a one-night task ("add the `%` operator") to a multi-night one ("add
closures") without ever needing paid services, secrets, or deployment.

## Scope & non-goals

In scope: lexer, recursive-descent/Pratt parser, tree-walking evaluator,
scoping, functions/closures, lists/maps, a small builtin standard library,
structured runtime/parse errors, a CLI for running `.cin` scripts, a REPL,
example programs, unit tests for every layer.

Out of scope (do not attempt unless PROJECT.md is amended first): bytecode
VM / JIT, package manager, file I/O or networking builtins, type checker,
LSP/editor tooling, self-hosting Cinder-in-Cinder. These are plausible *future*
directions once the tree-walking interpreter is solid, but they are not
current backlog and must not be started speculatively.

## Architecture

```
cinder/
  __init__.py
  lexer.py        # source text -> list[Token]
  tokens.py        # Token, TokenType definitions
  ast_nodes.py     # AST node dataclasses (Expr, Stmt subclasses)
  parser.py        # list[Token] -> AST (Pratt parsing for expressions)
  errors.py        # CinderError hierarchy: LexError, ParseError, RuntimeError
  interpreter.py    # tree-walking evaluator, Environment (scoping)
  builtins.py       # standard library functions (print, len, type, ...)
  cli.py           # argparse entrypoint: run a script or launch REPL
  repl.py          # interactive read-eval-print loop
tests/
  test_lexer.py
  test_parser.py
  test_interpreter.py
  test_builtins.py
  test_errors.py
  ... (mirrors cinder/ package, one test module per source module)
examples/
  *.cin            # sample programs (fizzbuzz, fibonacci, etc.)
```

Design principles:
- **No dependencies beyond the Python 3 standard library.** `argparse` for
  the CLI, `unittest` for tests, `dataclasses` for AST nodes.
- **Every layer is independently unit-tested.** The lexer is tested without
  the parser; the parser is tested against token lists or AST shape, not by
  round-tripping through the interpreter.
- **Errors are structured, not stringly-typed.** `CinderError` subclasses
  carry line/column; the CLI formats them for humans, tests assert on the
  structured fields.
- **AST nodes are immutable dataclasses**, one class per grammar production.
- **Truthiness is fixed and narrow**: `false` and `nil` are falsy; every other
  value — including `0`, `0.0`, and `""` — is truthy. This governs `if`,
  `while`, `and`/`or` short-circuiting, and `not`, and must not change without
  amending this document.
- **A leading `{` at statement position is disambiguated by speculative
  parse**: the parser first attempts a full expression parse rooted in a
  map literal (covering postfix indexing/calls and binary operators applied
  to it, e.g. `{"a": 1};`, `{"a": 1}["a"];`, `{"a": 1} == {"a": 1};`); if
  that fails, it falls back to parsing a `{ <statement>* }` block. Empty
  `{}` is always an empty Block, never an empty map literal.

## Tech stack

- Python 3.14 (stdlib only — see Dependencies rule in `CLAUDE.md`)
- `unittest` for tests (`python3 -m unittest discover -s tests`)
- `argparse` for the CLI

## How to run

```sh
# All commands run from this project's directory: projects/cinder/
cd projects/cinder

# Run a script
python3 -m cinder.cli run examples/fizzbuzz.cin

# Start the REPL
python3 -m cinder.cli repl
```

(The exact CLI subcommands/entrypoint may be refined by the scaffolding task
— treat the above as intent, not a locked interface.)

## How to test

```sh
cd projects/cinder
python3 -m unittest discover -s tests -v
```

`main` must always be green under this command. QA runs this in full for
every PR, not just tests touching the new code.

## Roadmap (beyond current backlog)

The core interpreter (lexer through error handling) has been solid for many
nights now, and REPL ergonomics (multiline input, persistent history),
source-mapped call-stack traces for nested calls, `do`/`while` loops,
`const` bindings, a C-style `for` loop, the nil-coalescing compound
assignment `??=`, an `-e`/`--eval` CLI flag, "did you mean...?" suggestions
for undefined names, labeled `break`/`continue` for nested loops, function
composition (`pipe`/`compose`), user-raised errors (`throw`), rest elements
in list destructuring, safe nested access/currying (`get_in`, `curry`),
`memoize` for caching pure functions, multiple values per `switch`
case (`case 1, 2, 3: { ... }`), list-pattern destructuring in
`for`-loop variables (`for [k, v] in items(m) { ... }`), dot-access
sugar for map string keys (`m.key` as sugar for `m["key"]`),
predicate-based map filtering (`pick_by`/`omit_by`), end-anchored
`take_right`/`drop_right`, population `variance`/`std_dev`, Tab
completion for builtins/variables in the REPL, `mode` for a list's
most frequent value, arithmetic compound-assign on `Index`/
dot-access targets (`xs[0] += 1`, `m.key += 1`, closing the last gap
that family had versus the bitwise/shift set, which already accepted
those targets), `product` as `sum`'s multiplicative counterpart,
nil-coalescing compound-assign on `Index`/dot-access targets
(`xs[0] ??= 1`, `m.key ??= 1`, closing that family's matching gap), a
REPL `:load <path>` meta-command to run a script into the current
session's persistent environment, `frequencies` for a list's
per-element occurrence counts, a safe-navigation operator `?.` for
map access (`m?.key` is `nil` when `m` is `nil`, pairing with the
existing `??`/`??=` nil-coalescing family; scoped as a single-level
short-circuit, not JS-style full-chain propagation), `compact` to
drop falsy elements from a list, `find_last_index` as `find_index`'s
reverse-search counterpart (mirroring how `last_index_of` already
closed that gap for equality-based search), and an exponentiation
operator `**` (right-associative, binding tighter than `*`/`/`/`%` and
looser than unary — closing the gap between the existing `pow()`
builtin and infix syntax, deliberately *not* matching Python's
special-cased unary-minus-vs-`**` precedence, and guarding the same
overflow/complex-result edge cases the `pow()` builtin already does),
and its compound-assignment sibling `**=` (`x **= 2`, accepting
index/dot-access targets like the rest of the arithmetic
compound-assign family), `sum_by` as the
`min_by`/`max_by`/`sort_by`/`group_by`/`count_by`/`distinct_by` family's
fold-by-key member (sum of `fn(item)` over a list, numbers-only like
`sum` rather than `min_by`/`max_by`'s number-or-string key), and
`reject` as `filter`'s predicate-inverted complement (mirroring how
`omit`/`omit_by` already closed that same gap for `pick`/`pick_by`),
`find_last` as `find`'s reverse-search counterpart for strings (the same
kind of gap `find_last_index` just closed for lists, but via Python's
`str.rfind`), `none` as the "no element truthy" complement to the
existing `any`/`all` pair, `zip_object` to build a map straight
from two parallel keys/values lists (the `zip`-side inverse of
`from_entries`/`items`, without manually composing
`from_entries(zip(keys, values))`), and `symmetric_difference` as the
fourth member of the `union`/`intersection`/`difference` set-ops trio
(elements in exactly one of the two lists) — all once listed here as
future work — have since landed.
`is_divisible(a, b)` as a two-argument numeric predicate testing
`a % b == 0`, generalizing the fixed divisor of `2` that `is_even`/
`is_odd` already special-case (raising the same "not an int" error
either does for either argument, plus a distinct "divisor must not be
zero" error, matching the `%` operator's own division-by-zero guard),
has since landed too.
A floor-division operator `//` (same precedence tier as `/`/`%`,
closing the gap between true division and the awkward `floor(a / b)`)
and its compound-assignment sibling `//=` (mirroring how `**=` followed
`**`), `replace_first` as `replace`'s first-occurrence-only
counterpart, `interpose` to insert a separator between a list's
elements (the list-level sibling of `join`, but separator
type-agnostic), `truncate` to cap a string's length with an
appended suffix when cut (the shrinking counterpart to
`pad_start`/`pad_end`), a negated membership operator `not in`
(sugar for `not (x in y)`, but parsed as a single operator at `in`'s
own precedence tier rather than through the looser,
unary-`not`-then-`in` reading that adjacent keywords would otherwise
get — that looser reading was previously dead syntax, now a fixed
regression case), `chars` to split a string into a list of its
characters (the gap `split` deliberately leaves open by rejecting an
empty separator), `is_even`/`is_odd` as integer parity predicates
(sitting next to `sign` the same way that already classifies a
number's sign), `swap_case` to flip each character's case (the
symmetric fourth member alongside `upper`/`lower`/`capitalize`/
`title`), and `pad_center` to center a string within a width, padding
both sides (the third member alongside `pad_start`/`pad_end`,
mirroring how `str.center` relates to `str.ljust`/`str.rjust`), and
`is_palindrome` to test whether a string reads the same forwards and
backwards (a case-sensitive, no-normalization predicate — no
stripping of spaces/punctuation — the same minimal-behavior spirit
`chars`/`swap_case` already follow rather than guessing at what a
caller wants stripped), and `is_int`/`is_float` splitting
`is_number`'s single "numeric" kind into its two concrete ones
(sitting next to `is_number` the same way `is_list`/`is_map`/
`is_string` already classify a value's kind rather than a property of
it, so — unlike `is_even`/`is_palindrome` — neither raises on a
non-numeric argument, just returns `false`), `is_prime` as
`is_even`/`is_odd`'s natural sibling integer-property predicate
(trial division to `sqrt(n)`, no need for anything fancier at
Cinder's scale), and `is_sorted` to test whether a list is already in
non-decreasing order without sorting it first and comparing by hand
(reusing `sort`'s own numbers-only-or-strings-only ordering rule), and
`is_upper`/`is_lower` as string case predicates delegating straight to
Python's own `str.isupper()`/`str.islower()` (the same "ask, don't
force" gap `is_sorted` fills for ordering, applied to casing instead),
and `is_alpha`/`is_digit`/`is_alnum`/`is_space` as string content
predicates delegating to Python's `str.isalpha()`/`str.isdigit()`/
`str.isalnum()`/`str.isspace()` (the same delegation `is_upper`/
`is_lower` use, one layer more basic — content rather than case), and
`is_positive`/`is_negative`/`is_zero` as numeric sign predicates
sitting next to `sign` the same way `is_even`/`is_odd` already sit
next to it for parity (a property predicate on any number, int or
float alike, raising on a non-numeric argument the same way `sign`
itself does — unlike the kind predicates `is_int`/`is_float`)
have since landed too, along with `is_unique` to test whether a list
has no duplicate elements without discarding that information the way
`unique` itself does (reusing `unique`'s own `_dedupe`/`values_equal`
deep-equality machinery rather than reimplementing duplicate detection),
and a slice step — `list[start:end:step]`/`string[start:end:step]` —
extending the existing two-colon slice syntax with a third, optional
component for skipping elements or reversing a sequence (`xs[::-1]`),
the one language-depth entry mixed in among that run's stdlib-breadth
predicates, and `is_ascii` as a string content predicate delegating
to Python's `str.isascii()` — one more member of the
`is_alpha`/`is_digit`/`is_alnum`/`is_space` content-predicate family —
and `is_subset`/`is_superset` as the predicate half of the
`union`/`intersection`/`difference`/`symmetric_difference` set-ops
family (today asking whether one list's elements are all contained in
another requires computing `difference` and checking it's empty by
hand; these reuse that family's own `_require_two_lists`/
`_contains_value` helpers directly, `is_superset(a, b)` simply
`is_subset(b, a)` with the arguments flipped) have since landed too.
Destructuring assignment — `[a, b] = expr;`, reassigning
already-declared bindings the same flat, no-nesting way
`let [a, b] = expr;` declares them (parsed only when a bracketed list
literal sits on an assignment's left-hand side, so no ambiguity with
list-literal expressions used elsewhere) — has since landed too, along
with `is_disjoint(list1, list2)` as the one predicate the
`union`/`intersection`/`difference`/`symmetric_difference`/`is_subset`/
`is_superset` set-ops family had still left implicit (no elements in
common at all, the complement of a non-empty `intersection`), and its
map-pattern counterpart — `{a, b} = expr;` reassigning already-declared
bindings the same flat way `let {a, b} = expr;` declares them, taught to
the statement-level `{`-disambiguation logic (see Design principles
above) as a third speculative-parse outcome tried only after both "map
literal expression" and "block" fail — have since landed too, along with
`is_anagram(a, b)` as the two-string sibling to `is_palindrome`'s
single-string "reads the same both ways" check (same case-sensitive,
no-normalization spirit: two strings are anagrams when they have the
same multiset of characters, counting whitespace/punctuation like any
other character, via `collections.Counter` rather than a hand-rolled
sort-and-compare), and `is_permutation(list1, list2)` as `is_anagram`'s
list-oriented sibling (the same multiset-equality check, but since list
elements can be unhashable nested lists/maps, matched via `_dedupe`'s
O(n²) `values_equal` fallback strategy rather than `Counter`), and
`is_numeric(string)` as one more member of the
`is_alpha`/`is_digit`/`is_alnum`/`is_space`/`is_ascii` string
content-predicate family, delegating to Python's own `str.isnumeric()`
the same way `is_ascii` delegates to `str.isascii()` (named
`_is_numeric_string` internally, not `_is_numeric` — that name was
already taken by an unrelated int/float helper used throughout
`builtins.py`), and `is_blank(string)`, filling the one gap `is_space`
deliberately leaves open (`str.isspace()` is `false` on the empty string,
matching every other content predicate's "empty is false" rule, so
`is_blank` is the first member of that family that is *not* a bare
delegation to a single `str.is*()` method: `value == "" or
value.isspace()`), and `factorial(n)` as a numeric builtin sitting
next to `pow`/`gcd`/`lcm` (delegating to Python's own `math.factorial`,
already imported, with a domain-error split for negative input
mirroring `log()`'s own type-vs-domain-error convention for its
positive-input requirement), and `is_pangram(string)` as a
case-insensitive alphabet-coverage predicate sitting next to
`is_palindrome`/`is_anagram`/`is_permutation` rather than the
`is_alpha`/.../`is_ascii` content-predicate family, since it isn't a
bare delegation to a single `str.is*()` method (checking that a
lowercased string's character set is a superset of the English
alphabet), and `digit_sum(n)` — a numeric builtin sitting next to
`is_even`/`is_odd`/`is_divisible`/`is_prime` (the integer-property
cluster, not the two-argument `pow`/`gcd`/`lcm`/`factorial` group)
that sums an integer's decimal digits after normalizing away its sign
via `abs()`, and list comprehensions — `[expr for x in iterable]` and
`[expr for x in iterable if cond]`, the first language-depth task
queued in seven cycles after a long run of stdlib-only additions,
scoped narrowly to a single non-destructuring loop variable, one
optional `if` filter, and no nesting, mirroring `_execute_for`'s own
iteration/closure-per-iteration shape rather than introducing a second
one, and its map-literal counterpart — map comprehensions (`{k: v for x
in iterable}`, same optional `if` filter, mirroring list comprehensions'
grammar/AST/interpreter shape rather than inventing a second one) —
have since landed too.
and `is_perfect_square(n)` — the same integer-property cluster
`digit_sum`/`is_prime`/`is_even`/`is_odd`/`is_divisible` sit in, testing
whether `n` is a perfect square via Python's own `math.isqrt` (exact
integer square root, no floating-point `sqrt`-then-round rounding-error
risk) rather than a hand-rolled Newton's-method loop, and
`is_armstrong(n)` — one more member of that same integer-property
cluster, testing whether `n` equals the sum of its own decimal digits
each raised to the power of the digit count (e.g. `153 = 1^3 + 5^3 +
3^3`), landed right after `digit_sum` since it does its own
digit-by-digit walk rather than reusing `digit_sum`'s sum directly (the
exponent depends on digit *count*, not a plain sum) — have since landed
too, as has `is_leap_year(year)` — the Gregorian calendar rule
(divisible by 4, except century years unless also divisible by 400),
one more integer-property predicate that deliberately answers on
zero/negative input rather than raising a domain error, matching
`is_perfect_square`/`is_armstrong`'s own convention, as has
`reverse_int(n)` — the digit-reversal sibling to `digit_sum`, returning
a number rather than a boolean (so it sits beside `digit_sum` rather
than in the boolean predicate cluster proper) and, unlike `digit_sum`,
preserving the input's sign rather than discarding it, as has
`is_perfect_number(n)` — one more member of the integer-property
cluster, testing whether `n` equals the sum of its own proper divisors
(e.g. `6 = 1 + 2 + 3`) via the same `math.isqrt`-bounded trial-division
approach `is_prime` already uses, pairing each divisor with its
complement rather than a naive `O(n)` scan, as has `is_abundant(n)` —
the next divisor-sum classification after `is_perfect_number`, testing
whether `n`'s proper divisors sum to more than `n` itself (e.g. `12 <
1 + 2 + 3 + 4 + 6 = 16`), reusing the same trial-division shape inline
rather than factoring a shared helper — and, as has `is_deficient(n)`
— the third and final divisor-sum classification, testing whether
`n`'s proper divisors sum to less than `n` itself (e.g. `8 > 1 + 2 + 4
= 7`), completing the perfect/abundant/deficient trio so every
positive integer lands in exactly one of the three, and, as has arrow
function expressions (`(x) => x * 2`, `(a, b) => a + b`) as sugar for
the existing anonymous `fn` expression, desugaring purely at parse
time into the same `FnExpr` AST node (no interpreter changes),
disambiguated from ordinary parenthesized grouping via the same
speculative-parse-and-backtrack technique `_brace_statement` already
uses for the `{`-disambiguation problem — a deliberate course-
correction after a seven-cycle run of stdlib-only integer-property
predicates (`is_perfect_square`, `is_armstrong`, `is_leap_year`,
`reverse_int`, `is_perfect_number`, `is_abundant`, `is_deficient`),
scoped to expression-bodied and parenthesized-parameter-list only (no
bare single-identifier form, no block body, both left for future
tasks) to keep the disambiguation logic tractable — and, as has
`is_palindrome_number(n)` — a numeric palindrome predicate, testing
whether `n`'s decimal digits read the same forwards and backwards
(e.g. `121`, `12321`), the natural closing member of the
digit-property cluster now that `reverse_int` exists to build it on
top of (`reverse_int(n) == n` for non-negative `n`; negative `n` is
always `false` since the leading `-` breaks the symmetry) — and, as
has `digital_root(n)` — the repeated-digit-sum-to-single-digit
reduction (e.g. `38 -> 11 -> 2`), sitting next to
`digit_sum`/`reverse_int` and, like `digit_sum`, ignoring sign,
computed via the closed-form `1 + (n - 1) % 9` identity rather than a
repeated-summing loop so arbitrary-precision Cinder ints don't force
many passes, and, as has bare single-identifier arrow functions
(`x => x * 2`, no parens around the one parameter) — the form the
parenthesized-arrow task explicitly deferred, needing no speculative
parse/backtrack at all since `IDENTIFIER` immediately followed by
`FAT_ARROW` is unambiguous with one token of lookahead
(`_peek_next()`) in `_primary`'s existing `IDENTIFIER` branch, and, as
has `is_composite(n)` — `is_prime`'s natural complement (an integer
greater than 1 that is *not* prime, e.g. `4`, `6`, `8`, `9`),
completing the classical prime/composite/neither (`0`, `1`, negatives)
three-way split the same way perfect/abundant/deficient already covers
divisor sums, and, as has `is_power_of_two(n)` — a bit-trick predicate
(`n & (n - 1) == 0` for positive `n`), the first integer-property
builtin to lean on Cinder's own bitwise operators rather than pure
arithmetic or a trial-division loop — have since landed too.
What remains plausible, not yet scoped beyond current `BACKLOG.md`:
as task 1, block-bodied arrow functions (`(params) => { ... }` and `x => { ... }`)
— previously left deferred pending "a concrete reason to want
statements in an arrow body"; that reason is now concrete: any arrow
callback needing more than one statement currently has no option but
the verbose `fn` form, defeating the sugar's purpose. Extends both
arrow forms to accept a `{ ... }` body via ordinary block-statement
parsing, reusing `_fn_params_and_body`'s own `_fn_depth`/
`_loop_labels` bookkeeping rather than inventing new scoping rules,
and deliberately *not* adding implicit-return-of-last-expression —
`return` stays explicit, matching every other block in the language.
This is the depth task the same breadth-vs-depth policy below calls
for once `is_composite`/`is_power_of_two` queued two predicates
back-to-back, and it depends on bare single-identifier arrows (landed)
since it touches both call sites. Then, as task 2, `is_palindrome_list(list)`
— extending the "reads the same forwards and backwards" predicate
family (`is_palindrome` for strings, `is_palindrome_number` for
integers) to its third and final natural domain, lists:
`is_palindrome_list([1, 2, 1]);` is `true`. Since list elements can be
unhashable nested lists/maps, this compares element-by-element from
both ends using `values_equal` (the same deep-equality helper
`is_unique`/`is_permutation` already import from `cinder.interpreter`)
rather than a bare `list == list[::-1]`, which would silently fall back
to Python's own (potentially wrong) equality on nested structures.
Queued as breadth after the depth task 1 lands, per the same balance
policy. Then, as task 3, `is_coprime(a, b)` — the other two-argument
member of the integer-property predicate cluster alongside
`is_divisible`, testing whether two integers share no common divisor
but `1` (`gcd(a, b) == 1`, via `math.gcd` directly rather than routing
through the existing `gcd()` builtin's own validation). This is a
second breadth task queued back-to-back with task 2
(`is_palindrome_list`), which the breadth-vs-depth policy below flags as
the point to line up a depth task next rather than let a third predicate
follow immediately. So, as task 4, safe navigation bracket indexing
(`obj?.[expr]`) — extending the existing dot-only safe navigation
operator (`m?.key`, short-circuits to `nil` on a `nil` receiver) to a
bracket form, closing the two gaps the dot form structurally can't reach:
a computed/non-identifier key (`m?.[key_var]`) and list access
(`xs?.[0]`, since `xs?.1` isn't valid syntax). Notably a parser-only
change — `OptionalIndex` already carries an arbitrary index expression
and `_evaluate_optional_index` already delegates to the same
`_index_get` plain indexing uses, so the interpreter needs no changes at
all; `_finish_optional_dot` just needs a bracket branch alongside its
existing identifier branch. Then, as task 5, `is_fibonacci(n)` — a
fresh breadth task after task 4's depth work, testing whether a
non-negative integer appears in the Fibonacci sequence via the closed-form
perfect-square test (`n` is Fibonacci iff `5n² + 4` or `5n² - 4` is a
perfect square), reusing `math.isqrt` the same exact-integer way
`is_perfect_square` already does rather than iterating the sequence up
to `n`. And only much later, a bytecode VM if performance ever actually
matters.
The Architect should keep scoping these into `BACKLOG.md` incrementally —
do not jump ahead of the current layer, and should keep watching this
same breadth-vs-depth balance: two or more single-builtin predicate
tasks queued back-to-back is a signal to inject another language-depth
task rather than just extending the streak further, the same threshold
that placed task 4 above.

## History

- **2026-07-18** — Project invented (Night One). No prior product existed;
  only the nightshift orchestrator scaffolding. Chose a from-scratch
  language interpreter for its natural incremental structure and zero
  external dependencies.
