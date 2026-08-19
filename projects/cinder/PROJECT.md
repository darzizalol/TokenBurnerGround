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
arithmetic or a trial-division loop, as has block-bodied arrow
functions (`(params) => { ... }` and `x => { ... }`) — previously left
deferred pending "a concrete reason to want statements in an arrow
body"; that reason became concrete once any arrow callback needing more
than one statement had no option but the verbose `fn` form, defeating
the sugar's purpose. Extends both arrow forms to accept a `{ ... }`
body via ordinary block-statement parsing, reusing
`_fn_params_and_body`'s own `_fn_depth`/`_loop_labels` bookkeeping
rather than inventing new scoping rules, and deliberately *not* adding
implicit-return-of-last-expression — `return` stays explicit, matching
every other block in the language. This was the depth task the same
breadth-vs-depth policy below calls for once `is_composite`/
`is_power_of_two` queued two predicates back-to-back, and, as has
`is_palindrome_list(list)` — extending the "reads the same forwards
and backwards" predicate family (`is_palindrome` for strings,
`is_palindrome_number` for integers) to its third and final natural
domain, lists, comparing element-by-element from both ends using
`values_equal` (the same deep-equality helper `is_unique`/
`is_permutation` already import from `cinder.interpreter`) rather than
a bare `list == list[::-1]`, which would silently fall back to
Python's own (potentially wrong) equality on nested structures, and
`is_coprime(a, b)` — the other two-argument member of the
integer-property predicate cluster alongside `is_divisible`, testing
whether two integers share no common divisor but `1` (`gcd(a, b) ==
1`, via `math.gcd` directly rather than routing through the existing
`gcd()` builtin's own validation) — have since landed too, as has
safe navigation bracket indexing (`obj?.[expr]`) — extending the
existing dot-only safe navigation operator (`m?.key`, short-circuits to
`nil` on a `nil` receiver) to a bracket form, closing the two gaps the
dot form structurally can't reach: a computed/non-identifier key
(`m?.[key_var]`) and list access (`xs?.[0]`, since `xs?.1` isn't valid
syntax). A parser-only change — `OptionalIndex` already carried an
arbitrary index expression and `_evaluate_optional_index` already
delegated to the same `_index_get` plain indexing uses, so the
interpreter needed no changes at all; `_finish_optional_dot` just
gained a bracket branch alongside its existing identifier branch. This
was the depth task the policy calls for right after a single breadth
task (`is_coprime`), rather than waiting for a second one to stack up,
as has `is_fibonacci(n)` — a fresh breadth task after the safe
navigation bracket indexing depth work, testing whether a non-negative
integer appears in the Fibonacci sequence via the closed-form
perfect-square test (`n` is Fibonacci iff `5n² + 4` or `5n² - 4` is a
perfect square), reusing `math.isqrt` the same exact-integer way
`is_perfect_square` already does rather than iterating the sequence up
to `n`, and `is_happy_number(n)` — a second breadth task queued
back-to-back with `is_fibonacci`, testing the "happy number" recurrence:
repeatedly replace `n` with the sum of the squares of its decimal
digits; `n` is happy if that process reaches `1`, unhappy if it instead
falls into a cycle that never includes `1` (e.g.
`4 -> 16 -> 37 -> 58 -> 89 -> 145 -> 42 -> 20 -> 4`, repeating forever
without hitting `1`), detected by tracking seen values in a set and
stopping the moment either `1` appears (happy) or a value repeats
(unhappy) — never by iterating a fixed number of steps, which could
misclassify a slow-converging happy number as unhappy; negative input
answers `false` without raising, mirroring `is_perfect_square`'s own
convention, as has numeric literal underscores for readability
(`1_000_000`, `0xFF_FF`, `3.14_159`) — the depth task the breadth-vs-
depth policy below called for after two breadth tasks (`is_fibonacci`,
`is_happy_number`) landed back-to-back: taught `_lexer.py`'s
`_number`/`_prefixed_int` to accept `_` as a digit-group separator,
stripped before constructing the `int`/`float` value, the same
convenience Python's own literal syntax offers. An underscore is only
consumed into the literal strictly between two digits of the same
group — a leading (`_1`), trailing (`1_`), doubled (`1__0`),
decimal-point-adjacent (`1_.5`, `1._5`), or post-prefix (`0x_FF`)
underscore simply isn't consumed, so scanning stops there and the
leftover `_...` lexes as a separate token the usual way (no new
`LexError` case needed), as has `is_triangular(n)` — one more
integer-property predicate, testing whether `n` is a triangular number
(`0, 1, 3, 6, 10, 15, ...`, the sum `1 + 2 + ... + k`) via the
closed-form test `8n + 1` is a perfect square, the same
`math.isqrt`-based exact-integer technique `is_fibonacci`/
`is_perfect_square` already use rather than an accumulating loop;
negative input answers `false` without raising, matching the rest of
the cluster's convention — this was the breadth task after the
numeric-literal-underscores depth work, restarting the same
alternation the policy below describes — and, as has destructuring loop
variables in list/map comprehensions (`[k + v for [k, v] in items(m)]`,
`{k: v for [k, v] in items(m)}`) — the comprehension-form gap left over
from when plain `for`-loops gained list-destructuring loop variables:
`ListComprehension`/`MapComprehension` gained the same `names`/`rest`
fields `ForStmt` already had, reusing the exact same
`_destructure_list_pattern` (parser) and `_bind_list_destructure`
(interpreter) helpers `ForStmt` already called, so this was pure
plumbing with no new binding logic. This was the depth task the policy
calls for right after a single breadth task (`is_triangular`), the same
one-breadth-then-depth placement the safe navigation bracket indexing
task got after `is_coprime`, as has `lerp(a, b, t)` — a fresh breadth
task after the destructuring-comprehension depth work, linear
interpolation between two numbers (`a + (b - a) * t`, unclamped — `t`
outside `[0, 1]` extrapolates, matching the conventional graphics/
game-math `lerp` rather than `clamp`'s bounded behavior), sitting next
to `clamp` as a simple numeric-range helper rather than joining the
integer-property predicate cluster, and, as has map-destructuring
`for`-loop variables (`for {a, b} in list_of_maps { ... }`) — the depth
task after `lerp`'s breadth work, closing the other half of the gap
`for`-loop destructuring left open: `let` already supports both list-
and map-destructuring patterns, and plain `for`-loops already
supported the list-pattern half (`for [k, v] in items(m) { ... }`), but
there was no map-pattern `for`-loop to destructure an iterable of maps
by key. `ForStmt` gained an `is_map` field (mirroring
`DestructureLetStmt`'s own field of the same name), and the map-pattern
parsing previously inlined in `_destructure_let_statement` was
extracted into a shared `_destructure_map_pattern` helper so both call
sites use it — reusing the existing `_bind_map_destructure` interpreter
helper for the actual binding, the same one `let`/assignment-
destructuring already called, so again pure plumbing with no new
binding logic, and, as has `is_emirp(n)` — a fresh breadth task after
the map-destructuring `for`-loop depth work, testing whether `n` is
prime and its decimal-digit reversal is a *different* prime (e.g.
`13`/`31`), sitting next to `is_prime`/`is_composite` as the third
member of that cluster; inlines `is_composite`'s own trial-division
loop and `reverse_int`'s digit-reversal rather than calling either
function directly, since both take the builtin-dispatch `(arguments,
line, column)` signature rather than a raw `int`, and, as has
list/map-destructuring function parameters (`fn f([a, b]) { ... }`,
`fn f({a, b}) { ... }`) — the depth task after `is_emirp`'s breadth
work, extending the same destructuring patterns `let`, plain
assignment, and `for`-loops already accept to one more binding
position: a function parameter, so `fn dist([x, y]) { ... }` works
directly instead of requiring a manual `let [x, y] = p;` as the first
line of the body. A new `Param` dataclass generalizes `FnDecl`/
`FnExpr`'s old `(name, default)` tuple params to also carry `names`/
`rest`/`is_map`, reusing the same `_destructure_list_pattern`/
`_destructure_map_pattern` (parser) and `_bind_list_destructure`/
`_bind_map_destructure` (interpreter) helpers the for-loop task
already shares across `let`/assignment/`for` — plumbing, plus one
real fix along the way: the first review round caught the new
destructuring parameter branches skipping the `seen_default` ordering
check plain identifier parameters already enforce, letting a
defaulted parameter followed by a destructuring one parse and then
crash at call time instead of failing cleanly at parse time, and
`divisors(n)` — a breadth task after the destructuring-function-parameters
depth work, returning the sorted list of `n`'s positive divisors; sits next
to `is_perfect_number`/`is_abundant`/`is_deficient` as the value-returning
sibling of that cluster, all three of which already trial-divide to
`sqrt(n)` and discard the individual divisors, keeping only their sum —
`divisors` reuses that same walk but collects instead of summing. Unlike
that cluster (which answers `false` for out-of-domain input), `n < 1`
raises a domain error rather than returning an empty list, since there's
no sensible "positive divisors of a non-positive number" answer, mirroring
`log()`'s own type-vs-domain-error split, and optional call chaining
(`f?.(...)`) — the depth task after `divisors`' breadth work, closing the
one position the existing `?.`/`??`/`?.[` safe-navigation family still
doesn't cover: calling a possibly-`nil` value. `let f = nil; f();`
used to raise `"nil is not callable"` with no nil-safe alternative short
of a manual `if f != nil { f(); }`. Added an `OptionalCall` AST node
mirroring `Call`, parsed via a new `_finish_optional_call` and evaluated
by an interpreter path that short-circuits to `nil` the moment the
callee evaluates to `nil` — without evaluating any argument
expressions, the same "stop the instant nil is seen" rule
`_evaluate_optional_index` already applies to its own operand — sharing
argument evaluation with plain `Call` through a new
`_evaluate_call_arguments` helper. Single-level only, exactly like the
rest of the `?.` family: it makes one call nil-safe, not an entire
chain, so reaching further still means composing `?.`s
(`m?.greet?.("Al")`), and `is_rotation(a, b)` — a fresh breadth task
after the optional call chaining depth work, testing whether string
`b` can be produced by rotating string `a` (moving some prefix to its
end, e.g. `"abcd"` -> `"cdab"`), sitting next to
`is_anagram`/`is_permutation` as a stricter two-string predicate than
`is_anagram`'s "same character multiset" test (two strings can be
anagrams without one being an actual rotation of the other); uses the
standard doubled-string trick (`b in (a + a)` for equal-length `a`/`b`)
rather than a hand-rolled character-shift loop, and destructuring loop
variables in list/map comprehensions (`[k + v for {a, b} in
list_of_maps]`, `{a: b for {a, b} in list_of_maps}`) — the depth task
after `is_rotation`'s breadth work, closing the last corner the
destructuring-loop-variable matrix left open: plain `for`-loops already
supported both the list-pattern (`for [k, v] in items(m) { ... }`) and
map-pattern (`for {a, b} in list_of_maps { ... }`) loop variable, and
comprehensions already had the list-pattern half (`[k + v for [k, v] in
items(m)]`), but `_list_comprehension`/`_map_comprehension` in
`cinder/parser.py` only ever checked `TokenType.LBRACKET` before a loop
variable, never `TokenType.LBRACE`. Added an `is_map` field to
`ListComprehension`/`MapComprehension` (mirroring `ForStmt`'s own field
of the same name), branching on `LBRACE` to reuse the existing
`_destructure_map_pattern` (parser) and `_bind_map_destructure`
(interpreter) helpers every other destructuring position already
shares — pure plumbing, no new binding logic — have since
landed too, as has `is_balanced(s)` — a breadth task testing whether a
string's `()`/`[]`/`{}` brackets are all properly matched and nested
(non-bracket characters ignored), via a single left-to-right scan with
a stack — the project's first stack-based parsing predicate,
deliberately chosen to diversify the string-predicate cluster rather
than add one more multiset/reversal delegation next to
`is_anagram`/`is_permutation`/`is_pangram` — and a rest element for
map-destructuring patterns (`let {a, ...rest} = m;`, `for {a, ...rest}
in list_of_maps { ... }`, `fn f({a, ...rest}) { ... }`, and the
list/map-comprehension loop-variable forms) — the depth task right
after `is_balanced`'s breadth work, closing the gap between the two
destructuring pattern kinds: list patterns already accepted an
optional trailing `...rest` that collects whatever wasn't consumed by
name, but map patterns had no equivalent, silently discarding every
key that isn't explicitly named instead of offering a way to capture
them. Every AST node a map pattern reaches (`DestructureLetStmt`,
`ForStmt`, `Param`, `ListComprehension`, `MapComprehension`) already
carried an unused `rest` field shared with the list-pattern case, so
this was mostly plumbing: `_destructure_map_pattern` grew the same
`DOT_DOT_DOT`-checking shape `_destructure_list_pattern` already had,
and `_bind_map_destructure` grew the same trailing-rest-collection
step `_bind_list_destructure` already had. Deliberately scoped to
exclude the plain-assignment map-destructuring form (`{a, b} = expr;`)
since that form parses via its own inlined speculative parser rather
than the shared helper this task changed — that form's own rest
element is separate future work, queued below — have since landed too,
as has `is_isogram(s)` — a breadth task testing whether a string has no
letter repeated (case-insensitive, non-letter characters ignored
entirely so they neither collide nor prevent one), sitting next to
`is_blank`/`is_pangram` as a single-pass character-frequency check
rather than another multiset-comparison delegation — like `is_balanced`,
deliberately picked to keep diversifying the string-predicate cluster's
implementation techniques instead of stacking more `is_anagram`-shaped
siblings, and a rest element for the plain-assignment map-destructuring
form (`{a, ...rest} = expr;`) — the depth task after `is_isogram`'s
breadth work, closing the one gap the earlier
map-destructuring-rest-element task deliberately left open:
`let`/`for`/`fn`/comprehension map patterns already had a rest
element, but the plain-assignment form (`{a, b} = expr;`) parsed via
its own inlined speculative parser
(`_try_map_destructure_assign_statement`) rather than the shared
`_destructure_map_pattern` helper that task changed, so it needed its
own (smaller) grammar change to accept the same trailing `...rest`.
First review round caught the deferred rest-violation raise could be
swallowed by the function's own blanket `except ParseError: return
None` handler when a non-identifier token followed a misplaced rest
(e.g. `{a, ...rest, 5} = {};`), reproducing the exact confusing
`_block()` fallback error the task claimed to eliminate — fixed by
switching to an eager raise via a `_RestNotLast` marker exception (not
a `ParseError` subclass, so it can't be caught by that same handler),
mirroring the sibling `_destructure_map_pattern`/
`_destructure_list_pattern` eager-raise approach, have since landed
too, as has `levenshtein_distance(a, b)` — a breadth task after the
plain-assignment map-destructuring rest element's depth work, computing
the classic edit distance between two
strings (minimum single-character insertions/deletions/substitutions
to turn one into the other, e.g. `levenshtein_distance("kitten",
"sitting")` is `3`), sitting next to `is_anagram`/`is_rotation`/
`is_permutation` as one more two-string comparison but, unlike that
whole cluster, returning a number rather than a boolean — the
project's first dynamic-programming builtin, and a third distinct
implementation technique for the string-comparison family alongside
`is_balanced`'s stack scan and `is_isogram`'s frequency-set check, and
chained comparison operators (`a < b < c`, evaluating as `a < b and b
< c` with each operand read exactly once and the whole chain
short-circuiting) — the depth task after `levenshtein_distance`'s
breadth work, closing a real gap rather than adding sugar for its own
sake: before this landed, `_comparison()` left-folded any run of
comparison operators into nested `Binary` nodes, so `1 < 2 < 3`
evaluated as `(1 < 2) < 3` = `true < 3`, which always raised
`CinderRuntimeError` since `_compare` never accepts a `bool` operand
— every existing 2-or-more ordering-operator chain had exactly one
possible outcome (a guaranteed error), so this was strictly additive,
not a behavior change any program could have been relying on. Scoped
to the four ordering operators (`<`/`<=`/`>`/`>=`) only; runs that mix
in `==`/`!=` kept the left-fold behavior completely unchanged (chained
equality, e.g. `1 == 1 == 1`, was already well-defined, just not
obviously useful, and didn't need touching to fix the
ordering-operator gap), have since landed too, as has `is_automorphic(n)`
— a breadth task after the chained comparison operators' depth work,
testing whether an integer's square ends with the integer itself in
decimal (e.g. `5 * 5 = 25` ends in `5`; `76 * 76 = 5776` ends in `76`),
joining the `is_perfect_square`/`is_armstrong`/`is_leap_year`/
`is_perfect_number`/`is_abundant`/`is_deficient` integer-property cluster
as one more digit-based classification, implemented as a plain string
check (`str(n * n).endswith(str(n))`) rather than modular arithmetic, the
same style `is_palindrome_number`/`is_armstrong` already use, and, as has
slice assignment for lists (`list[start:end] = other_list;`) — the depth
task after `is_automorphic`'s breadth work, closing a gap `README.md`'s
Data structures bullet used to flag explicitly ("not assignable"): a
`SliceExpr` on the left of `=` used to fall through `_assignment()`'s
target checks straight to `"invalid assignment target"`. Scoped to the
step-less form only — a stepped target (`list[a:b:c] = value;`) still
stays a parse error, since Python-style extended-slice assignment
requires an exact length match between target and replacement, a
materially different contract than the simple form; string targets stay
immutable, raising the same message plain single-index string assignment
already does. The replacement value must itself be a list (no implicit
coercion), and Python's own `obj[start:end] = value` list-slice-assignment
semantics handle the length change (grow or shrink) once the normalized
bounds are computed the same way `_evaluate_slice`'s read-side logic
already does, have since landed too, as has `is_perfect_cube(n)` — a
breadth task testing whether an integer is a perfect cube (`k ** 3 ==
n` for some integer `k`, e.g. `27 = 3**3`), one more member of the
integer-property cluster sitting next to `is_perfect_square`, but —
unlike `is_perfect_square` — accepting negative input as potentially
`true` (`-8 = (-2)**3`), since cube roots of negative numbers are real
and integral where square roots aren't; computed via a hand-rolled
exact-integer binary-search cube root (no `math.icbrt` exists in the
standard library, and a floating-point `round(n ** (1/3))` risks the
same rounding-error problem `math.isqrt` was chosen to avoid for
squares) rather than a float approximation, have since landed too, as
has `aliquot_sum(n)` — a breadth task, the number-returning sibling of
`divisors`'s list-returning walk and the value-returning counterpart to
the `is_perfect_number`/`is_abundant`/`is_deficient` predicate cluster:
the sum of `n`'s own proper divisors (e.g. `6`'s sum to `6`, confirming
it's perfect), reusing the same `sqrt(n)`-bounded trial-division shape
that whole cluster already shares, with a domain error on `n < 1`
mirroring `divisors`'s own convention rather than the predicate
cluster's answer-`false` one, and, as has keyword arguments in function
calls (`f(a: 1, b: 2)`) — the depth task queued after `aliquot_sum` and
`is_perfect_cube` stacked two breadth builtins in a row. Every call
today binds purely positionally; this adds trailing keyword arguments
matched by parameter name, Python-style, scoped to user-defined
`CinderFunction`s only — builtins stay positional-only and raise
cleanly if handed one. A keyword argument can target only a plain named
parameter, never a list/map-destructuring parameter or the trailing
rest parameter, both of which simply have no name a caller could
address; that restriction falls out for free from matching against
parameter names rather than needing its own check, and, as has
`is_pronic(n)` — a breadth task after the keyword-arguments depth work,
testing whether an integer is expressible as `k * (k + 1)` for some
non-negative integer `k` (a pronic/oblong number, e.g. `6 = 2 * 3`,
`12 = 3 * 4`), one more root-based classification sitting next to
`is_perfect_square`/`is_perfect_cube`, computed the same exact-integer
`math.isqrt` way `is_perfect_square` already does rather than a
floating-point approximation, and, as has default values in
list-destructuring patterns (`let [a, b = 5] = expr;`) — the depth task
after `is_pronic`'s breadth work, extending the same "use a fallback
when nothing was supplied" convention function parameters already have
(`fn f(a, b = 1) { ... }`) down into list-destructuring patterns
themselves: every list-pattern form (`let`, `for`, function params,
both comprehension loop-variable forms) used to require the source
list to have exactly as many elements as the pattern (or, with a
`...rest`, at least that many), with no way to supply a fallback for a
position the source list didn't reach. Scoped to list patterns only
(map patterns already had a distinct, meaningful "missing key" domain
error, not an obvious gap to fill the same way — see the
map-pattern-defaults task below, which extends map patterns too, once
this task had established the convention) and to the
`let`/`for`/param/comprehension forms only, not the plain-assignment
form (`[a, b] = expr;`), since that form's pattern is parsed by first
parsing an ordinary list literal, whose elements never accept `=` at
that precedence — teaching it to would have been a materially
different, riskier parser change than this task took on, and, as has
`collatz_length(n)` — a breadth task after list-destructuring defaults'
depth work, counting the number of steps the Collatz (3n+1) recurrence
takes to reach `1` from a positive integer `n` (repeatedly halving `n`
if even, or replacing it with `3n + 1` if odd), sitting next to
`is_happy_number` as the same iterate-a-recurrence-and-count technique,
but returning a step count rather than a boolean, so no cycle detection
is needed (unlike `is_happy_number`, the Collatz conjecture — unproven
in general, but true for every integer ever checked, well within
Cinder int range — is that this process always terminates at `1`), and
`is_strong_number(n)` — a second breadth task stacked right after
`collatz_length`, restocking the backlog back past its 5-task floor
rather than alternating into a depth task that time (the same
restocking rationale that placed `aliquot_sum` alongside
`is_perfect_cube` earlier): a positive integer equal to the sum of the
factorials of its own decimal digits (a factorion, e.g. `145 = 1! + 4!
+ 5!`), joining `is_armstrong` in the digit-transform-and-sum-and-compare
cluster but using `factorial` per digit instead of a fixed power, and
reusing the already-registered `factorial` builtin's `math.factorial`
rather than reimplementing it, and, as has unary `+` (`+expr`) — the
depth task after two breadth builtins stacked in a row (`collatz_length`,
`is_strong_number`), closing a real asymmetry in the unary operator
set: `-`/`not`/`~` were all implemented but plain unary `+` wasn't
(`_UNARY` in `cinder/parser.py` simply never included
`TokenType.PLUS`), and the doubled-token case was asymmetric too —
`--5` already evaluated to `5` via an explicit `MINUSMINUS` re-split,
but `++5` had no equivalent `PLUSPLUS` handling. No new AST node was
needed (`Unary` already carries an arbitrary operator token), so it
was a small, self-contained change confined to `_UNARY`/`_unary` in
the parser and one new branch in `_evaluate_unary`, and, as has
`num_divisors(n)` — a breadth task after unary `+`'s depth work,
counting an integer's positive divisors via the same
`sqrt(n)`-bounded trial-division shape `divisors`/`aliquot_sum` already
share, sitting next to both as the count-returning sibling of that
trio (`divisors` collects them, `aliquot_sum` sums the proper ones,
`num_divisors` counts them all including `n` itself), have since
landed too, as has default values in map-destructuring patterns
(`let {a, b = 5} = expr;`) — the depth task after `num_divisors`'s
breadth work, the map-pattern counterpart to the
list-destructuring-defaults task: every map-pattern form used to raise
when a key was absent rather than falling back to a default. Unlike
the list-pattern version, this one *does* reach the plain-assignment
form (`{a, b} = expr;`) for free — the map-pattern plain-assignment
path already reuses the same `_destructure_map_pattern_entry` parser
helper as every other form, unlike the list-pattern plain-assignment
path, which parses through an unrelated `ListLiteral` route.
Map-pattern entries also have no positional ordering (matching is by
key, not position), so unlike the list-pattern version's ordering rule
there is no "a required entry can't follow a defaulted one" restriction
to enforce, and, as has `prime_factors(n)` — a breadth task after the
map-pattern defaults' depth work, listing an integer's prime factors
with multiplicity in ascending order (e.g. `12 -> [2, 2, 3]`,
`360 -> [2, 2, 2, 3, 3, 5]`), the natural neighbor to
`divisors`/`is_prime`/`is_composite` — where `divisors` finds every
factor of `n` and `is_prime`/`is_composite` classify `n` as a whole,
this decomposes `n` into its prime building blocks, walking the
standard trial-division *factorization* technique (stripping small
prime factors out of a shrinking copy of `n`) rather than the
sqrt-bounded divisor-pairing shape `divisors`/`aliquot_sum`/
`num_divisors` share, since factorization needs to record a repeated
factor (like `2` dividing `12` twice) each time it divides evenly, not
just once. `prime_factors(1)` is `[]` — `1` has no prime factors,
mathematically, not a case needing a special-cased guard the way
`divisors(1)`'s own `[1]` result does, hole elements in
list-destructuring patterns (`let [a, , c] = expr;`) — the depth task
after `prime_factors`'s breadth work, closing the last gap in the
destructuring-pattern cluster: every list-pattern form could already
bind a name, rename nothing (list patterns have no rename syntax),
collect a rest, or fall back to a default, but there was no way to
skip an unwanted position outright the way JavaScript's
array-destructuring elision does. Scoped, like the
list-destructuring-defaults task before it, to the
`let`/`for`/param/comprehension forms only (via
`_destructure_list_pattern_entry`), not the plain-assignment form, for
the identical reason: that form's pattern is parsed through an
ordinary `ListLiteral`, which has no notion of an empty element, and
`is_squarefree(n)` — a breadth task after the hole-elements depth
work, testing whether `n` has no repeated prime factor (equivalently,
is not divisible by any perfect square greater than `1`, e.g. `6 = 2 *
3` is squarefree, `12 = 2 * 2 * 3` isn't), the natural predicate
neighbor to `is_prime`/`is_composite` and `prime_factors` — answering
"does any factor repeat?" via the same `sqrt(n)`-bounded
trial-division shape `is_prime`/`is_composite` already use, checking
`divisor * divisor` divisibility directly rather than building the
full factor list, and optional catch bindings (`try { ... } catch { ... }`,
no `(name)` required) — the depth task after `is_squarefree`'s breadth
work: today `catch` always required a parenthesized binding name
(`catch (err) { ... }`) even when the handler never reads the error
message, forcing a throwaway name for the common "just recover, don't
inspect" case. `_try_statement` in `cinder/parser.py` now treats the
`(name)` after `catch` as optional — parsed only when the next token is
`(`, leaving `TryStmt.catch_name` `None` otherwise (the field was
already typed `str | None`, so no AST change was needed) — and
`_execute_try` in `cinder/interpreter.py` only calls
`catch_env.define(...)` when `catch_name` isn't `None`, running the
catch block in a plain child environment otherwise, and `is_amicable(a,
b)` — a breadth task after optional catch bindings' depth work, the
two-argument predicate sibling to
`is_perfect_number`/`is_abundant`/`is_deficient` (the same way
`is_coprime`/`is_divisible` are the two-argument siblings of the
single-argument `is_prime`/`is_even`/`is_odd` cluster), testing
whether two distinct positive integers' proper-divisor sums point at
each other (e.g. `220`'s proper divisors sum to `284`, and `284`'s sum
back to `220`) — the classical two-number generalization of a perfect
number, where a single number's proper-divisor sum loops back to
itself. Inlines its own private aliquot-sum helper mirroring
`_aliquot_sum`'s trial-division body exactly (the same "inline rather
than call the dispatch-signature builtin" approach `is_emirp` already
takes with `is_composite`/`reverse_int`), and explicitly excludes
`a == b` even though a perfect number would otherwise trivially pass —
amicability is defined only between two *distinct* integers — and a
pipe operator (`a |> f` as sugar for `f(a)`) — the depth task after
`is_amicable`'s breadth work: Cinder already ships `pipe(f, g, h)`/
`compose(f, g, h)` builtins that thread a value through a *fixed list*
of unary functions, but had no operator-level sugar for the common
one-shot or ad-hoc-chain case, forcing either inside-out nesting
(`g(f(a))`) or a throwaway `pipe(f, g)(a)` call built just to be
invoked once. `a |> f` evaluates both sides as ordinary expressions and
calls the right's value with the left's value as its sole argument —
deliberately not Elixir-style argument insertion, so `a |> f(1)` calls
`f(1)` first and calls *that result* with `a`, composing naturally with
`curry` (`3 |> curry(add, 2)(5)`). Slots into the precedence chain
between `_ternary` and `_nullish` (looser than every value-producing
binary operator, tighter than `? :`/assignment), left-associative like
`_or`/`_and`, reusing the existing `Binary` AST node and the
already-shared `call_value` helper rather than adding a new node or a
bespoke call path — the new `PIPE_ARROW` token for `|>` was the only
genuinely new piece, checked in the lexer before the existing `|=`/`|`
fallback so bitwise-or and its compound assignment stay unaffected —
and `is_semiprime(n)` — a breadth task after the pipe operator's depth
work: testing whether `n` is the product of exactly two primes counted
with multiplicity (`4 = 2 * 2`, `6 = 2 * 3`, `15 = 3 * 5`), the third
member of the `is_prime`/`is_composite`/`is_semiprime` classification
trio — `is_prime` answers "exactly one prime factor", `is_semiprime`
answers "exactly two", `is_composite` answers "more than one" (a strict
superset `is_semiprime` narrows). Walks the same "peel small factors,
then check what's left" shape `prime_factors` already uses, but counts
instead of collecting, bailing out early once the count exceeds two so
highly composite inputs stay cheap, and uninitialized `let`
declarations (`let x;`, defaulting to `nil`) — the depth task after
`is_semiprime`'s breadth work: today every `let` requires an
initializer (`cinder/parser.py`'s `_let_statement` unconditionally
consumes `=` right after the identifier), forcing a throwaway
placeholder value (`let x = nil;`) purely to satisfy the parser even
when the real value is only known conditionally, e.g. set inside a
following `if`/`else`. Only requires `=` and an initializer expression
when the token right after the identifier isn't `;` — otherwise
defaults the initializer to a bare `Literal(None, ...)` node, exactly
what the parser already builds for the `nil` keyword itself, so the
interpreter's existing `LetStmt` evaluation path needs no changes.
`const` is deliberately untouched — an immutable binding that starts
out unassigned would defeat the purpose of `const`, and
`_for_statement`'s C-style init clause already reuses `_let_statement`,
so `for (let i; i < 3; i++) { ... }` becomes parseable for free too,
though it correctly raises a runtime type error on the first comparison
rather than being a useful thing to write — have since landed too, as
has `is_powerful_number(n)` — testing whether every prime factor of `n`
appears with exponent `2` or more (equivalently, `n` can be written as
`a^2 * b^3`), the natural counterpart to `is_squarefree` — where
`is_squarefree` rejects any repeated prime factor, `is_powerful_number`
requires every prime factor to repeat, walking the same
`sqrt(remaining)`-bounded trial-division shape `is_semiprime`/
`prime_factors` already use, peeling each prime factor's full
multiplicity in an inner loop and failing fast the moment any factor's
count comes up short of `2`, then checking that nothing above the
`sqrt` bound was left over uncounted, as has single-quoted string
literals (`'...'` as an alternate delimiter to double quotes) —
generalizing `cinder/lexer.py`'s `_string` to take the opening quote
character as a parameter instead of hardcoding `"`, dispatching both
`"` and `'` to it from `tokenize`, and adding `'` to the shared
`_ESCAPES` table alongside the existing `"` entry so `\'` is a valid
escape inside either delimiter; the `${...}` interpolation machinery,
`has_interp`/`INTERP_STRING` split, and unterminated-string detection
were already delimiter-agnostic and needed no changes, nor did the
parser or interpreter, since both delimiters produce the same
`STRING`/`INTERP_STRING` tokens carrying the same parsed Python `str`
value, and `is_repdigit(n)` — testing whether every decimal digit of a
non-negative integer is the same (`11`, `222`, `4444`), a digit-based
predicate joining `is_palindrome_number`/`is_armstrong`/`is_harshad`/
`is_strong_number` in the digit-transform cluster rather than extending
the prime-factorization run (`is_semiprime`, `is_powerful_number`) a
third time; a single-digit integer (including `0`) counts as trivially
repdigit, matching `is_palindrome_number`'s own single-digit convention,
negative inputs return `false` rather than raising, and the
implementation is a one-liner once the sign is handled:
`len(set(str(value))) == 1`, no trial division or `sqrt` bound needed,
and scientific notation for float literals (`1e3`, `1.5e-2`, `2E+10`) —
`cinder/lexer.py`'s `_number` gained an optional exponent-suffix block
after the existing fractional-part handling, following the same "peek,
commit, then require what must follow" shape `_prefixed_int` already
uses: only begins consuming when `self._peek().lower() == "e"` and the
following character is a digit or `+`/`-`, then unconditionally
consumes the `e`/`E`, an optional sign, and a digit run reusing the
mantissa/fraction digit runs' own underscore-separator condition,
raising `LexError` "expected digits after exponent" if that run comes
up empty; an exponent always forces `is_float = True` even with no `.`
present, and `float(value_str)` needed no changes since Python's own
parser already handles the full exponent grammar once underscores are
stripped, and `geometric_mean(list)` — the nth root of a list's
product, joining `mean`/`median`/`variance`/`std_dev`/`mode` as the
statistics cluster's first non-arithmetic-mean member, reusing the
exact same `isinstance`/non-empty/`_is_numeric`-per-element validation
shape those four already share plus one added domain restriction
(every element must be strictly positive, checked only after
confirming numeric-ness, raising a domain error rather than leaking a
non-real result for zero or negative input, the same convention
`log()` already applies to its own positive-input requirement) — have
since landed too, as has postfix `++`/`--` as a first-class assignment
expression — the depth task after `geometric_mean`'s breadth work:
`++`/`--` used to be recognized only by a one-off parser helper
(`_expr_or_incdec`) reachable from exactly three places — a bare
`x++;` statement and the `for`-loop's init/step clauses — while every
*other* assignment-flavored operator (`=`, the compound-assign family,
`??=`) was recognized directly inside `_assignment` itself and so was
already usable as a `let` initializer, a chained-assignment RHS, or a
parenthesized sub-expression; `let y = x++;` used to be a `ParseError`
even though the exactly analogous `let y = x += 1;` already worked.
Folded `_expr_or_incdec`'s existing `Identifier`/`Index`-target check
and `Assign`/`IndexCompoundAssign` desugaring directly into
`_assignment` as one more branch alongside the
`EQ`/`QQEQ`/`_COMPOUND_ASSIGN_OPS` checks already there, then deleted
`_expr_or_incdec` and pointed its three former call sites at
`_assignment` directly — no interpreter changes, since the reused
desugaring already evaluates to the new (post-increment) value, the
same as every compound-assign sibling. Deliberately left precedence
unchanged (`-x++;` still a `ParseError`) and reachability from
`_ternary()`-rooted positions like call arguments (`print(x++)` still
a `ParseError`, matching `print(x = 5)`'s own existing restriction) —
only closed the one gap where `++`/`--` uniquely lagged behind every
sibling assignment operator, and `digit_product(n)` — a breadth task
after postfix `++`/`--`'s depth work, the multiplicative counterpart to
`digit_sum`, the same relationship `product` already has to `sum` at
the list level: sits right next to `digit_sum` in `cinder/builtins.py`,
reusing the exact same `abs(value)`-then-walk-digits shape to discard
the sign before iterating, so it needs no new domain-handling decision
of its own. A single-digit integer (including `0`) is trivially its own
digit product; any `0` digit anywhere in the number collapses the
whole product to `0`, which is the correct answer, not a case to guard
against, and trailing commas in list/map literals, call arguments, and
function parameter lists (`[1, 2,]`, `{"a": 1,}`, `f(1, 2,)`, `fn f(a,
b,) { ... }`) — the depth task after `digit_product`'s breadth work,
closing an ergonomics gap in all four of `cinder/parser.py`'s
comma-separated-list parsers at once, since they share the identical
"parse an element, then loop while a comma follows" shape: a comma
immediately before the closing delimiter used to be a hard `ParseError`
rather than being silently accepted, unlike every mainstream scripting
language's take on these same four positions. Each site got the same
one-line fix — after consuming the comma, check whether the next token
is that site's own closing delimiter and break instead of trying to
parse another element — with no interpreter changes at all, since this
only widened what the parser was willing to accept, not what AST shape
it produces. Deliberately scoped to just those four sites, not
destructuring patterns or comprehension bodies, which are separate call
sites with their own comma-loops and were left for a future task
(trailing commas in destructuring patterns, covered further below), and
`is_evil(n)`/`is_odious(n)` — a breadth task after that depth work:
binary popcount-parity predicates, classifying every non-negative
integer by whether its binary representation has an even ("evil") or
odd ("odious") count of `1` bits, sitting next to `is_power_of_two` as
the second member of the "reasons about binary representation" family
rather than the decimal digit-transform cluster `is_repdigit`/
`digit_product` belong to. Each is a one-line delegation to
`bin(value).count("1") % 2`, bundled as one task since they're exact
complements of the same expression differing only in which parity is
accepted — the same bundling `is_int`/`is_float` and `is_subset`/
`is_superset` already got — and negative input raises a domain error
rather than answering `false`, since Python's two's-complement `bin()`
output on a negative number would silently count the wrong thing
rather than answering honestly, and list concatenation via `+`
(`[1, 2] + [3, 4]` is `[1, 2, 3, 4]`): one new
`isinstance(left, list) and isinstance(right, list): return left +
right` branch in `_apply_binary_operator`'s `PLUS` case
(`cinder/interpreter.py`), reusing Python's own non-mutating list `+`,
matching `_repeat_op`'s existing non-mutating convention for `*` —
the same "builtin exists, infix syntax doesn't" gap `**` closed for
`pow()`, since `concat()` already did list-plus-list as a function call
and `*` already treated `list * int` as repetition in the very same
function. Because compound assignment desugars `+=` to an ordinary
`Binary`/`PLUS` node and reuses this same function, `xs += [3, 4]`
started working for free the moment this branch landed, no separate
change needed — have since landed too. `harmonic_mean(list)` — the
third member of the classical Pythagorean means trio (arithmetic,
geometric, harmonic), completing the statistics cluster's "kinds of
average" alongside `mean`/`geometric_mean`: `n / sum(1/x for x in
list)`, reusing the exact same `isinstance`/non-empty/`_is_numeric`-
per-element validation shape `mean`/`geometric_mean` already share,
plus the identical strictly-positive domain restriction
`geometric_mean` already enforces — has since landed via PR #268 too.
Trailing commas in destructuring patterns (`let [a, b,] = expr;`,
`let {a, b,} = expr;`, `for [a, b,] in ...`, `for {a, b,} in ...`,
destructuring function parameters, both comprehension loop-variable
forms, and the plain-assignment map form `{a, b,} = expr;`) — closing
each of `_destructure_list_pattern`'s/`_destructure_map_pattern`'s/
`_try_map_destructure_assign_statement`'s own comma-loops with the same
"peek the closing delimiter after the comma, break" fix the earlier
literals/calls/params trailing-commas task used, including the
documented side effect that a hole immediately before the closing
delimiter (`let [a, ,] = [1, 2];`) is now accepted the same way a
trailing comma after a real element is — has since landed via PR #269
too. `multiplicative_persistence(n)` — the number of times a number's
own decimal digits must be repeatedly multiplied together before the
result drops to a single digit (e.g. `39 -> 27 -> 14 -> 4`, three
multiplications, so `multiplicative_persistence(39)` is `3`), the
natural loop-driven counterpart to `digital_root`'s closed-form
additive reduction — unlike `digital_root`'s `1 + (n - 1) % 9`
shortcut, no closed form exists for the multiplicative case, so this
genuinely needed an iterative loop, not a formula. Inlines its own
per-digit-multiply step (the same `abs(value)`-then-walk-digits shape
`digit_product` itself uses) rather than calling the `digit_product`
builtin directly, the same "inline rather than call the
dispatch-signature builtin" approach `is_emirp`/`is_amicable` already
take with `is_composite`/`reverse_int`/`_aliquot_sum`. Sign is discarded
via `abs()` once up front, matching `digit_sum`/`digit_product`'s own
convention (not re-derived every step, since the running product is
already non-negative once the first step completes); any single-digit
input (`-9` through `9` after the sign is dropped) has persistence `0`
— the loop's trivial already-terminated base case, not a domain edge to
guard against — has since landed via PR #270 too. Comma-separated
multiple variable declarations in a single `let`/`const` statement
(`let a = 1, b = 2;`, `const x = 1, y = 2;`) — the depth task after
`multiplicative_persistence`'s breadth work: `_let_statement`/
`_const_statement` (`cinder/parser.py`) each parse one declaration, then
loop on a trailing `COMMA` to parse more, wrapping more than one into a
new `DeclSeq` statement node (`cinder/ast_nodes.py`) that the
interpreter executes by running each declaration in turn against the
current environment — no change needed to `LetStmt`/`ConstStmt`
themselves, since `DeclSeq` is purely a thin sequencing wrapper around
the existing per-declaration node, and a single declaration (the
overwhelmingly common case) still produces a bare `LetStmt`/`ConstStmt`
with no wrapper at all, so no existing test needed updating — has since
landed via PR #271 too. `cbrt(x)` — the domain-unrestricted sibling to
`sqrt`, a breadth task after comma-separated declarations' depth work:
unlike `sqrt`, which raises on negative input to avoid a complex result,
a real cube root exists for every real number, so `cbrt(-8)` returns
`-2.0` rather than raising — `math.copysign(abs(value) ** (1 / 3),
value)`, computing the root of the magnitude and reapplying the original
sign, since Python's own `** (1/3)` on a negative base would otherwise
raise or return a complex result depending on type — has since landed
via PR #272 too. Nested list-in-list destructuring patterns (`let [a,
[b, c]] = [1, [2, 3]];`) — the depth task after `cbrt`'s breadth work,
scoped to list-in-list nesting only (map nesting either direction stays
out of scope, still a `ParseError`): added a nested-pattern branch to
`_destructure_list_pattern_entry`/`_destructure_assign_pattern`
(`cinder/parser.py`) and a matching `isinstance(name, tuple)` branch in
both loops of `_bind_list_destructure` (`cinder/interpreter.py`) —
nesting works for free across all five list-pattern call sites (`let`,
plain assignment, `for`, function params, both comprehension forms)
since they all funnel through the same shared helpers, and composes
correctly with existing rest/default/hole handling at any nesting depth
— has since landed via PR #273 too. `is_perfect_power(n)` — the general
closure of `is_perfect_square`/`is_perfect_cube`/`is_powerful_number`,
answering "is there any integer exponent `k >= 2` and base `m` with
`m ** k == n`" via a new general `_integer_kth_root` binary-search helper
(generalizing the existing `_integer_cube_root` from a fixed `** 3` to a
parameter `k`, added alongside rather than refactored in place) and a
bit-length-bounded search over candidate exponents, admitting negative
input only through odd exponents the same way `is_perfect_cube` already
does — has since landed via PR #274 too.
What remains plausible, not yet scoped beyond current `BACKLOG.md`
(numbering here matches `BACKLOG.md` tasks 1-6 — the tasks that used to
occupy slots 1-2 here, raw string literals and `is_undulating`, have
since landed via PR #275 and PR #276 and are covered in the "have since
landed" history immediately above; this grooming pass dropped their now-
redundant descriptions from this section.
Tasks 1-6 — a range literal `a..b` (claimed, in progress as PR #277),
`is_kaprekar`, map literal shorthand properties `{a, b}` as sugar for
`{"a": a, "b": b}`, `is_achilles` (powerful but not itself a perfect
power), named function expressions (`fn name(params) { ... }`), and
`is_pernicious` (a number whose binary popcount is itself prime) — are
fully scoped in `BACKLOG.md` itself and are not duplicated here, the
same treatment tasks past slot 1 have gotten since this section stopped
trying to keep prose in lockstep with every backlog slot). And only much
later, a bytecode VM if performance ever actually matters. The
Architect should keep scoping these into `BACKLOG.md` incrementally —
do not jump ahead of the current layer, and should keep watching the
same breadth-vs-depth balance that has governed every grooming pass so
far: two or more single-builtin predicate tasks queued back-to-back is
a signal to inject a language-depth task rather than extending the
streak further (most recently, this is what placed unary `+` right
after `collatz_length`/`is_strong_number` stacked two breadth builtins
in a row), and a depth task landing is usually followed by one breadth
task before the next depth task is queued, occasionally two in a row
when the backlog needs restocking faster than strict alternation would
otherwise allow (as happened when `aliquot_sum` was added alongside
`is_perfect_cube`, and again when `is_strong_number` was added
alongside `collatz_length`). The previous pass found the backlog back
down to its 5-task floor again (scientific notation having landed via
PR #261, dropping the count from 6 to 5, dropping its now-landed
description from the "what remains plausible" section above into the
"have since landed" history, and renumbering the remaining five tasks
from 2-6 down to 1-5, with `is_evil`/`is_odious` renumbered from 6 to
5) and restocked it to 6 by adding task 6, list concatenation via `+`,
continuing alternation with a depth task after task 5's breadth work
(`is_evil`/`is_odious`) rather than stacking a second breadth task,
per the policy above. This pass found the backlog back down to its
5-task floor again (`geometric_mean` having landed via PR #262,
dropping the count from 6 to 5, dropping its now-landed description
from the "what remains plausible" section above into the "have since
landed" history, and renumbering the remaining five tasks from 2-6
down to 1-5, with list concatenation via `+` renumbered from 6 to 5)
and restocked it to 6 by adding task 6, `harmonic_mean`, continuing
alternation with a breadth task after task 5's depth work (list
concatenation via `+`) rather than stacking a second breadth task,
per the policy above. This pass found the backlog back down to its
5-task floor again (postfix `++`/`--` as a first-class assignment
expression having landed via PR #263, dropping the count from 6 to 5,
dropping its now-landed description from the "what remains plausible"
section above into the "have since landed" history, and renumbering
the remaining five tasks from 2-6 down to 1-5, with `harmonic_mean`
renumbered from 6 to 5) and restocked it to 6 by adding task 6,
trailing commas in destructuring patterns, continuing alternation with
a depth task after task 5's breadth work (`harmonic_mean`) rather than
stacking a second breadth task, per the policy above — and, unlike
every other task added by a grooming pass so far, this one didn't need
inventing from scratch: task 2 (trailing commas in list/map literals,
call arguments, and function parameter lists) explicitly named it as
deferred future work when it landed, so this pass just picked that
thread back up now that task 2 itself has shipped. This pass found the
backlog back down to its 5-task floor again (`digit_product` having
landed via PR #264, dropping the count from 6 to 5, dropping its
now-landed description from the "what remains plausible" section above
into the "have since landed" history, and renumbering the remaining
five tasks from 2-6 down to 1-5, with trailing commas in destructuring
patterns renumbered from 6 to 5) and restocked it to 6 by adding task
6, `multiplicative_persistence`, continuing alternation with a breadth
task after task 5's depth work (trailing commas in destructuring
patterns) rather than stacking a second depth task, per the policy
above. This pass found the backlog down past its 5-task floor to just 4
(both trailing commas in list/map literals/calls/params and
`is_evil`/`is_odious` landed via PR #265 and PR #266 in the same cycle,
dropping the count from 6 to 4 in one jump, dropping both their
now-landed descriptions from the "what remains plausible" section above
into the "have since landed" history, and renumbering the remaining
four tasks from 3-6 down to 1-4, with list concatenation via `+`
renumbered from 3 to 1, `harmonic_mean` from 4 to 2, trailing commas in
destructuring patterns from 5 to 3, and `multiplicative_persistence`
from 6 to 4) and restocked it the rest of the way to 6 by adding two
tasks at once — the same "restock faster than strict alternation"
move `aliquot_sum`/`is_perfect_cube` and `collatz_length`/
`is_strong_number` already used when a single merge dropped the count
by more than one: task 5, comma-separated multiple variable
declarations in a single `let`/`const` statement (`let a = 1, b = 2;`),
a depth task continuing alternation after task 4's breadth work
(`multiplicative_persistence`), and task 6, `cbrt`, a breadth task
after task 5's depth work, per the same alternation policy. This pass
found the backlog back down to its 5-task floor again (list
concatenation via `+` having landed via PR #267, dropping the count
from 6 to 5, dropping its now-landed description from the "what
remains plausible" section above into the "have since landed" history,
and renumbering the remaining five tasks from 2-6 down to 1-5, with
comma-separated `let`/`const` declarations renumbered from 5 to 4 and
`cbrt` from 6 to 5) and restocked it to 6 by adding task 6, nested
list-in-list destructuring patterns (`let [a, [b, c]] = [1, [2, 3]];`),
continuing alternation with a depth task after task 5's breadth work
(`cbrt`) rather than stacking a second breadth task, per the policy
above — scoped to list-in-list nesting only (not map nesting either
direction), reusing the same two shared-helper functions
(`_destructure_list_pattern_entry`/`_bind_list_destructure`) every
prior list-pattern extension (rest elements, defaults, holes) already
changed, so it lands "for free" across every list-pattern call site
(`let`, plain assignment, `for`, function params, both comprehension
forms) the same way those did. The next grooming pass should continue
alternating breadth/depth, restocking toward 6-7 tasks whenever a merge
drops the count within reach of the 5-task floor. This pass found the
backlog back down to its 5-task floor again (`harmonic_mean` having
landed via PR #268, dropping the count from 6 to 5, dropping its
now-landed description from the "what remains plausible" section above
into the "have since landed" history, and renumbering the remaining
five tasks from 2-6 down to 1-5, with trailing commas in destructuring
patterns renumbered from 2 to 1, `multiplicative_persistence` from 3 to
2, comma-separated `let`/`const` declarations from 4 to 3, `cbrt` from 5
to 4, and nested list-in-list destructuring patterns from 6 to 5) and
restocked it to 6 by adding task 6, `is_perfect_power`, continuing
alternation with a breadth task after task 5's depth work (nested
list-in-list destructuring patterns) rather than stacking a second
depth task, per the policy above — the general closure of
`is_perfect_square`/`is_perfect_cube`/`is_powerful_number`, answering
"is there any integer exponent `k >= 2` and base `m` with `m ** k ==
n`" via a new general `_integer_kth_root` binary-search helper
(generalizing the existing `_integer_cube_root` from a fixed `** 3` to
a parameter `k`, added alongside rather than refactored in place) and a
bit-length-bounded search over candidate exponents, admitting negative
input only through odd exponents the same way `is_perfect_cube` already
does. The next grooming pass should continue alternating breadth/depth,
restocking toward 6-7 tasks whenever a merge drops the count within
reach of the 5-task floor. This pass found the backlog back down to its
5-task floor again (trailing commas in destructuring patterns having
landed via PR #269, dropping the count from 6 to 5, dropping its
now-landed description from the "what remains plausible" section above
into the "have since landed" history, and renumbering the remaining
five tasks from 2-6 down to 1-5, with `multiplicative_persistence`
renumbered from 2 to 1, comma-separated `let`/`const` declarations from
3 to 2, `cbrt` from 4 to 3, nested list-in-list destructuring patterns
from 5 to 4, and `is_perfect_power` from 6 to 5) and restocked it to 6
by adding task 6, raw string literals `r"..."`/`r'...'`, continuing
alternation with a depth task after task 5's breadth work
(`is_perfect_power`) rather than stacking a second breadth task, per the
policy above — a new lexer dispatch branch recognizing an `r` prefix
immediately followed by a quote (safe because that exact adjacency is
already a guaranteed syntax error today, so no currently-valid program
changes meaning) and a new `_raw_string` scanning method, sibling to the
existing `_string`, that skips escape and `${...}`-interpolation
processing entirely, closing the gap for patterns and Windows-style
paths that would otherwise need every backslash doubled. The next
grooming pass should continue alternating breadth/depth, restocking
toward 6-7 tasks whenever a merge drops the count within reach of the
5-task floor. This pass found the backlog back down to its 5-task floor
again (`multiplicative_persistence` having landed via PR #270, dropping
the count from 6 to 5, dropping its now-landed description from the
"what remains plausible" section above into the "have since landed"
history, and renumbering the remaining five tasks from 2-6 down to 1-5,
with comma-separated `let`/`const` declarations renumbered from 2 to 1,
`cbrt` from 3 to 2, nested list-in-list destructuring patterns from 4
to 3, `is_perfect_power` from 5 to 4, and raw string literals from 6 to
5) and restocked it to 6 by adding task 6, `is_undulating`, continuing
alternation with a breadth task after task 5's depth work (raw string
literals) rather than stacking a second depth task, per the policy
above — testing whether an integer's decimal digits strictly alternate
between exactly two distinct values (e.g. `121`, `2323`), one more
digit-pattern classification sitting next to `is_repdigit`/
`is_palindrome_number`, requiring at least three digits and two
distinct digits so that neither a too-short number nor a repdigit can
qualify. The next grooming pass should continue alternating
breadth/depth, restocking toward 6-7 tasks whenever a merge drops the
count within reach of the 5-task floor. This pass found the backlog
down past its 5-task floor to just 4 (comma-separated `let`/`const`
declarations and `cbrt` landed via PR #271 and PR #272 in two separate
cycles with no grooming pass in between, dropping the count from 6 to 4
one task at a time, dropping both their now-landed descriptions from
the "what remains plausible" section above into the "have since landed"
history, and renumbering the remaining four tasks from 3-6 down to 1-4,
with nested list-in-list destructuring patterns renumbered from 3 to 1,
`is_perfect_power` from 4 to 2, raw string literals from 5 to 3, and
`is_undulating` from 6 to 4) and restocked it the rest of the way to 6
by adding two tasks at once — the same "restock faster than strict
alternation" move used before whenever a gap of more than one task
opened up: task 5, a range literal `a..b` (sugar over the existing
`range()` builtin, e.g. `for i in 1..5 { ... }` instead of `for i in
range(1, 5) { ... }`), a depth task continuing alternation after task
4's breadth work (`is_undulating`), reusing `range()`'s own int
validation and list construction rather than duplicating it so both
spellings share one error message; and task 6, `is_kaprekar` (a number
whose square splits into two parts that sum back to itself, e.g. `45`:
`2025` → `20 + 25 == 45`), a breadth task after task 5's depth work,
placed next to `is_automorphic` in `cinder/builtins.py` since automorphic
numbers are the fixed special case of a Kaprekar split at the digit
boundary matching `n`'s own length. This pass found the backlog back
down to its 5-task floor again (nested list-in-list destructuring
patterns having landed via PR #273, dropping the count from 6 to 5,
dropping its now-landed description from the "what remains plausible"
section above into the "have since landed" history, and renumbering the
remaining five tasks from 2-6 down to 1-5, with `is_perfect_power`
renumbered from 2 to 1, raw string literals from 3 to 2, `is_undulating`
from 4 to 3, the range literal from 5 to 4, and `is_kaprekar` from 6 to
5) and restocked it to 6 by adding task 6, map literal shorthand
properties `{a, b}` as sugar for `{"a": a, "b": b}`, continuing
alternation with a depth task after task 5's breadth work (`is_kaprekar`)
rather than stacking a second breadth task, per the policy above — the
construction-side inverse of the map-destructuring shorthand `let {a, b}
= expr;` already has, recognized in `_map_entry` via the same
identifier-plus-lookahead technique `_call_argument` already uses for
keyword arguments, scoped away from map comprehensions for free since
`for` fails the same `COMMA`/`RBRACE` lookahead that triggers the
shorthand branch. The next grooming pass should continue alternating
breadth/depth, restocking toward 6-7 tasks whenever a merge drops the
count within reach of the 5-task floor. This pass found the backlog back
down to its 5-task floor again (`is_perfect_power` having landed via PR
#274, dropping the count from 6 to 5, dropping its now-landed
description from the "what remains plausible" section above into the
"have since landed" history, and renumbering the remaining five tasks
from 2-6 down to 1-5, with raw string literals renumbered from 2 to 1,
`is_undulating` from 3 to 2, the range literal from 4 to 3, `is_kaprekar`
from 5 to 4, and map literal shorthand properties from 6 to 5) and
restocked it to 6 by adding task 6, `is_achilles`, continuing alternation
with a breadth task after task 5's depth work (map literal shorthand
properties) rather than stacking a second depth task, per the policy
above — the gap between `is_powerful_number` and `is_perfect_power`:
powerful (every prime factor's exponent `>= 2`) but *not* itself a
perfect power of any single base/exponent pair (e.g. `72 = 2^3 * 3^2`,
exponents `3` and `2`, `gcd(3, 2) == 1`). Reuses the exact factorization
loop `is_powerful_number` already has, tracking the running `gcd` of
each prime's exponent alongside the existing "every exponent `>= 2`"
check rather than calling `is_perfect_power` as a second pass — a number
is a perfect power exactly when the `gcd` of its prime exponents exceeds
`1` (the number is then that `gcd`-th power of the product of each prime
raised to `exponent / gcd`), so checking `gcd == 1` after the powerful
check both closes the gap and naturally excludes single-prime-factor
powers (`8 = 2^3`) for free, since a lone prime's own exponent becomes
the `gcd` outright. The next grooming pass should continue alternating
breadth/depth, restocking toward 6-7 tasks whenever a merge drops the
count within reach of the 5-task floor. This pass found the backlog back
down to its 5-task floor again (raw string literals `r"..."`/`r'...'`
having landed via PR #275, dropping the count from 6 to 5, dropping its
now-landed description from the "what remains plausible" section above
into the "have since landed" history, and renumbering the remaining five
tasks from 2-6 down to 1-5, with `is_undulating` renumbered from 2 to 1,
the range literal from 3 to 2, `is_kaprekar` from 4 to 3, map literal
shorthand properties from 5 to 4, and `is_achilles` from 6 to 5) and
restocked it to 6 by adding task 6, named function expressions (`fn
name(params) { ... }`), continuing alternation with a depth task after
task 5's breadth work (`is_achilles`) rather than stacking a second
breadth task, per the policy above — closing the self-reference gap
anonymous `fn` expressions have always had: today a recursive anonymous
function can only call itself by closing over whatever outer variable it
happens to be assigned to (`let f = fn(n) { ... f(n - 1) ... };`, which
works only as long as that specific outer binding is never reassigned or
skipped, e.g. when the function is passed straight into a call argument).
An identifier immediately after `fn` at expression position was already
a guaranteed `ParseError` before this task, so the new `fn name(params)
{ ... }` syntax claims previously-invalid territory only; the name is
bound fresh into each call's own environment (not the enclosing scope),
so it never leaks outside calls to that specific function value, mirroring
how a same-named parameter can shadow it within one call. The next
grooming pass should continue alternating breadth/depth, restocking
toward 6-7 tasks whenever a merge drops the count within reach of the
5-task floor. This pass found the backlog back down to its 5-task floor
again (`is_undulating` having landed via PR #276, dropping the count
from 6 to 5, dropping its now-landed description from the "what remains
plausible" section above into the "have since landed" history, and
renumbering the remaining five tasks from 2-6 down to 1-5, with the
range literal renumbered from 3 to 1, `is_kaprekar` from 4 to 2, map
literal shorthand properties from 5 to 3, `is_achilles` from 6 to 4, and
named function expressions from 7 to 5) and restocked it to 6 by adding
task 6, `is_pernicious`, continuing alternation with a breadth task
after task 5's depth work (named function expressions) rather than
stacking a second depth task, per the policy above — a bit-pattern
classification sitting right next to `is_evil`/`is_odious`: those two
already test the *parity* of an integer's binary popcount (count of `1`
bits), and this asks a different question of the same popcount, whether
it is itself *prime* (e.g. `7` is `111` in binary, popcount `3`, and `3`
is prime, so `is_pernicious(7)` is `true`). Reuses `_is_prime`'s own
trial-division loop shape, applied to the popcount rather than the input
value directly, and follows `is_evil`/`is_odious`'s convention of
raising a domain error on negative input (a popcount is only meaningful
for a non-negative integer) rather than the "return false" convention
most other digit/bit predicates use. Also noted while grooming: task 1
(the range literal) has been claimed since 2026-08-19T14:02:47Z and has
an open PR (#277) that picked up one round of `CHANGES REQUESTED` this
cycle for a misplaced test-class insertion point — that is an Engineer/
Reviewer-cycle matter, not a backlog-grooming one, so it is left as-is;
the top of `BACKLOG.md` stays task 1 until that PR lands or is closed.
The next grooming pass should continue alternating breadth/depth,
restocking toward 6-7 tasks whenever a merge drops the count within
reach of the 5-task floor.

## History

- **2026-07-18** — Project invented (Night One). No prior product existed;
  only the nightshift orchestrator scaffolding. Chose a from-scratch
  language interpreter for its natural incremental structure and zero
  external dependencies.
