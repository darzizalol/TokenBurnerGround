# Cinder

A small, dynamically-typed scripting language with a tree-walking interpreter,
written in pure Python (stdlib only — no parser generators, no dependencies).

Cinder is built by **TokenBurnerGround's autonomous night shift**: every line
of it — the design, the code, the tests, the code reviews, and the merges —
was produced by AI agents working unattended between 22:00 and 07:00. The
human only reads the logs in the morning. See the repo root for how the
studio works.

## A taste of Cinder

```
# fibonacci.cin: recursive function calls
fn fib(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

let i = 0;
while (i < 10) {
    print(fib(i));
    i = i + 1;
}
```

## Features (implemented and tested)

- **Values**: numbers, strings, booleans, `nil`; `nil`/`false` are falsy,
  everything else (including `0` and `""`) is truthy; strings may be
  delimited by either double or single quotes (`"..."`/`'...'`,
  interchangeably, `\"`/`\'` both valid escapes, plus `\n`/`\t`/`\\`/`\r`/
  `\0`/`\b`/`\f`/`\v` and a fixed-width `\uXXXX` Unicode escape) and support
  interpolation (`"hello, ${name}!"`, `"${1 + 2}"`) with arbitrary expressions
  inside `${...}`, stringified the same way `print`/`format` render values;
  raw string literals (`r"..."`/`r'...'`) skip escape and interpolation
  processing entirely — every character up to the matching close quote is
  taken literally, useful for regex-like patterns and Windows-style paths
  that would otherwise need every backslash doubled (a raw string cannot
  contain its own delimiter quote; use the other quote character instead);
  triple-quoted string literals (`"""..."""`/`'''...'''`) end only at
  three consecutive matching quote characters, so quote-heavy or
  multi-line text needs no per-quote escaping, with escapes and
  interpolation still processed exactly as in single-quoted strings;
  integer literals may also be written in hex (`0x1F`), binary (`0b101`), or
  octal (`0o17`); float literals accept scientific notation (`1e3`,
  `1.5e-2`, `2E+10`; an exponent always makes the literal a float, even
  with no `.` present, so `1e3` is `1000.0` not the int `1000`); any
  numeric literal may use `_` as a digit-group separator
  for readability (`1_000_000`, `0xFF_FF`, `3.14_159`, `1_000e1_0`), stripped before the
  value is constructed
- **Variables & scope**: `let` declarations, `const` declarations for
  immutable bindings (reassignment or `++`/`--`/compound-assignment on a
  `const` name raises a runtime error; a `let` may still be redeclared as
  `const` and vice versa in the same scope), comma-separated multiple
  declarations in a single `let`/`const` statement (`let a = 1, b = 2;`,
  `const x = 1, y = 2;`, each with its own initializer, evaluated
  left-to-right so a later initializer can see an earlier declared name,
  e.g. `let a = 1, b = a + 1;` binds `b` to `2`), assignment, comma-separated
  multiple statements in expression-statement position for already-declared
  names or any other bare expression (`a = 1, b = 2;`, `f(), g();`, the
  same left-to-right evaluation and shared `DeclSeq` execution the `let`/
  `const` form already uses), blocks with proper
  lexical scoping (inner `let` shadows, outer survives); list destructuring
  in `let` (`let [a, b] = expr;`, positional binding that may itself nest
  (`let [a, [b, c]] = [1, [2, 3]];`, to any depth, composing with rest/
  default/hole elements at any nesting level; a map pattern may also
  nest inside a list pattern, `let [a, {b, c}] = [1, {"b": 2, "c": 3}];`,
  and vice versa — every corner of the list/map nesting matrix, in any
  combination, is supported), plus
  a hole element to skip an unwanted position (`let [a, , c] = expr;`,
  scoped to `let`, `for`, function params, and comprehension loop
  variables, not the plain-assignment form), an optional trailing rest
  element `let [a, b, ...rest] = expr;` that
  collects any remaining elements into a list, empty if none are left,
  and an optional default value per element `let [a, b = 5] = expr;`,
  used when the source list doesn't reach that position, evaluated
  left-to-right so a later default can see an earlier bound name, e.g.
  `let [a, b = a + 1] = [5];` binds `b` to `6`; scoped to `let`, `for`,
  function params, and comprehension loop variables — the plain-assignment
  form `[a, b] = expr;` does not support defaults) and
  map destructuring (`let {a, b} = expr;`, binds each identifier by
  looking it up as a key, extra unnamed keys ignored, that may itself
  nest (`let {a, b: {c, d}} = {"a": 1, "b": {"c": 2, "d": 3}};`, to any
  depth, composing with rest/rename/default at any nesting level; a list
  pattern may also nest inside a map pattern, `let {a, b: [c, d]} =
  {"a": 1, "b": [2, 3]};`), plus the same kind
  of optional trailing rest element `let {a, ...rest} = expr;` that
  collects every key not already named into a map, empty if none are
  left, an optional per-key rename `let {a: x, b} = expr;` binding
  the value under key `a` to local name `x` instead of `a`, combinable
  with the rest element and freely mixable with un-renamed keys in the
  same pattern, and an optional default value per key
  `let {a, b = 5} = expr;`, used only when the key is missing from the
  source map (a present-but-falsy value does not trigger it), evaluated
  in pattern order so a later default can see an earlier bound name,
  e.g. `let {a, b = a + 1} = {"a": 5};` binds `b` to `6`; combinable
  with rename (`let {a: x = 5} = expr;`) and, unlike the list-pattern
  version, supported on every map-pattern form including plain
  assignment, since all five share one parser entry point), plus plain
  assignment forms of both for already-declared bindings — list
  (`[a, b] = expr;`, same flat positional binding and optional trailing
  rest element as the `let` form, e.g. the swap idiom `[a, b] = [b, a];`)
  and map (`{a, b} = expr;`, same key-lookup binding, rest element,
  per-key rename, and per-key default as the `let` form); every
  destructuring pattern form (`let`, `for`, function params, both
  comprehension loop-variable forms, and the plain-assignment map form)
  accepts an optional trailing comma before its closing `]`/`}`
  (`let [a, b,] = expr;`, `let {a, b,} = expr;`), matching the trailing
  comma already accepted in list/map literals, call arguments, and
  function parameter lists; bare comma multi-target assignment
  (`a, b = 1, 2;`, the unbracketed sibling of `[a, b] = expr;`, same flat
  positional binding, no brackets required — including the swap idiom
  `a, b = b, a;`)
- **Control flow**: `if`/`else`, `while`, `do { ... } while (cond);`,
  `for NAME in EXPR { ... }` over lists, strings (character-by-character),
  maps (over keys), and range literals (`a..b`, sugar over the existing
  `range()` builtin usable directly as a loop source, e.g. `for i in
  1..5 { ... }` instead of `for i in range(1, 5) { ... }`; exclusive of
  `b`, matching `range()`'s own two-argument semantics, plus an inclusive
  spelling `a..=b` for loops that must include their upper bound, e.g.
  `for i in 1..=5 { ... }` to cover `1` through `5` without the
  easy-to-get-wrong `1..6`), an optional step component on either
  spelling (`a..b..step`, `a..=b..step`, mirroring `range()`'s own
  three-argument form, e.g. `for i in 10..0..-2 { ... }` counts down by
  `2`; a step of `0` raises `CinderRuntimeError`), plus
  list-destructuring loop variables
  (`for [k, v] in items(m) { ... }`, same flat positional binding and
  optional trailing rest element as `let` list destructuring) and
  map-destructuring loop variables (`for {a, b} in list_of_maps { ... }`,
  same key-lookup binding as `let` map destructuring, including the same
  optional trailing rest element and per-key rename,
  `for {a: x, b} in list_of_maps { ... }`), a C-style `for (init; cond; step) { ... }` loop
  (each clause optional; the loop variable gets a fresh binding per
  iteration so closures captured in the body see their own iteration's
  value), `break`/`continue` in all loop kinds, including labeled
  `break`/`continue` (`outer: while (...) { for x in y { break outer; } }`)
  to target an enclosing loop from a nested one,
  `try { ... } catch (name) { ... }` for recovering from runtime errors
  (the caught message binds to `name`; `break`/`continue`/`return` still
  propagate through uncaught), an optional catch binding
  (`try { ... } catch { ... }`, no `(name)` required, for handlers that
  don't need to inspect the caught message), an optional `finally { ... }` block (at
  least one of `catch`/`finally` is required) that always runs on the way
  out of the `try`, whether it succeeded, was caught, or is propagating
  uncaught, a `throw expr;` statement for raising user-defined errors
  (the expression must be a string; catchable by an enclosing
  `try`/`catch` exactly like a builtin runtime error), `switch`
  statements with `case`/`default` (no fallthrough, first match wins;
  a single `case` may list multiple values, e.g. `case 1, 2, 3: { ... }`,
  matching if any of them equals the switch expression), a `match`
  expression (`match (n) { 1 => "one", 2 => "two", _ => "other" }`) for
  pattern dispatch that evaluates to a value rather than running
  statements — literal patterns, a `_` wildcard arm, bound-identifier
  patterns (`match (5) { 0 => "zero", n => n + 1 }`, any non-`_`
  identifier matches unconditionally and binds the subject's value for
  the arm's body, in a scope that doesn't leak out), and multi-value
  literal patterns (`match (2) { 1, 2 => "small", _ => "large" }`, one
  arm answering for several literal values without repeating the body),
  flat list patterns (`match ([1, 2]) { [a, b] => a + b, _ => 0 }`,
  a fixed-length list subject destructured element-by-element in a fresh
  child scope, falling through — not raising — on a non-list subject or
  a length mismatch, and each element may itself be a bare literal
  (`match ([1, 2]) { [1, b] => b, _ => 0 }`) instead of only a bound
  identifier or `_`), range patterns (`match (5) { 1..10 => "small",
  _ => "large" }`, `INT`-only bounds, exclusive `..` or inclusive `..=`,
  reusing the same range machinery as `x in 1..5`), and negative literal
  patterns (`match (-5) { -5 => "neg", _ => "pos" }`, `INT`/`FLOAT` only,
  not range-pattern bounds) for now (no nested list patterns, rest
  capture, map patterns, negative range-pattern bounds, or guards yet —
  see `BACKLOG.md`)
- **Operators**: full arithmetic/comparison/logical set, unary `+`
  (`+expr`, numbers only, alongside unary `-`/`not`/`~`; `++5` parses
  as nested unary plus, same doubled-token re-split `--5` already has),
  compound
  assignment (`+=`, `-=`, `*=`, `/=`, `%=`, `**=`, `//=`, `&=`, `|=`, `^=`,
  `<<=`, `>>=`;
  all of them, arithmetic and bitwise/shift alike, accept an
  index-expression target too, e.g. `xs[0] += 1`, `m.key &= 3`),
  postfix `x++`/`x--` as a first-class assignment expression (identifier or
  index-expression target, e.g. `xs[0]++;`; usable anywhere any other
  assignment operator already is — a `let` initializer (`let y = x++;`), a
  chained-assignment RHS, or inside a parenthesized sub-expression —
  evaluating to the post-increment/-decrement value, same as the
  compound-assign family; precedence and reachability from call
  arguments/ternary branches are unchanged, so `-x++;` and `print(x++)`
  still raise, matching `print(x = 5)`'s own restriction), `*` repetition
  for `str * int`/`list * int` (Python repetition
  semantics), list concatenation via `+` (`[1, 2] + [3, 4]` is
  `[1, 2, 3, 4]`, a fresh non-mutating list, closing the gap between the
  existing `concat()` builtin and infix syntax the same way `*` already
  does for repetition; `+=` on a list target works for free through the
  same desugaring), floor division `//` (same precedence tier as `/`/`%`,
  floors toward negative infinity rather than truncating, e.g.
  `-7 // 2` is `-4`),
  `in` for membership tests (lists, strings, maps) and its negated sibling
  `not in` (a single combined operator at `in`'s own precedence tier, not
  unary `not` applied afterward), the ternary conditional
  `cond ? then : else`, the nil-coalescing operator `a ?? b` (short-circuits
  like `and`/`or`: evaluates `b` only when `a` is `nil`, unlike `or` which
  falls through on any falsy value) and its compound-assignment sibling
  `a ??= b` (identifier or index/dot-access targets, e.g. `xs[0] ??= 1`,
  `m.key ??= 1`; the RHS is only evaluated, and the target only written,
  when the current value is `nil`), the safe navigation operator `m?.key`
  (short-circuits to `nil` when `m` is `nil` instead of raising, single
  level only, composes with `??` for `m?.key ?? default`) and its
  bracket form `obj?.[expr]` (same nil short-circuit, but with an
  arbitrary index expression — works for computed map keys, e.g.
  `m?.[key_var]`, and for lists, e.g. `xs?.[0]`/`xs?.[-1]`, neither of
  which the dot form can express; read-only, no slicing), optional call
  chaining `f?.(...)` (same nil short-circuit, applied to a call: yields
  `nil` without evaluating the arguments when `f` is `nil`, single level
  only like the rest of the `?.` family, composes with the others for
  chains like `obj?.method?.()`), and bitwise
  operators `&`, `|`, `^`, `~`, `<<`, `>>` (int-only, with a clean runtime
  error on a negative shift count), and the exponentiation operator `**`
  (right-associative, binds tighter than `*`/`/`/`%` and looser than unary
  minus, so `-2 ** 2` is `4`; guards against the same edge cases the `pow()`
  builtin does, e.g. `0 ** -1` and complex results from a negative base with
  a fractional exponent both raise a clean runtime error instead of leaking
  a raw Python exception or a complex number), map concatenation via `+`
  (`{"a": 1} + {"b": 2}` is `{"a": 1, "b": 2}`, a fresh non-mutating map,
  right-biased on key collision — the map-typed sibling of list
  concatenation, giving the existing `merge()` builtin an infix spelling;
  `+=` on a map target works for free through the same desugaring), and
  the pipe operator
  `a |> f` (sugar for `f(a)`; evaluates both sides as ordinary expressions
  and calls the right's value with the left's value as its sole argument —
  not Elixir-style argument insertion, so `a |> f(1)` calls `f(1)` first
  and calls *that result* with `a`, composing with `curry`, e.g.
  `3 |> curry(add, 2)(5)`; left-associative, looser than every
  value-producing binary operator but tighter than `? :`/assignment)
- **Functions**: `fn name(a, b) { ... }` — first-class, arity-checked, with
  recursion, `return`, and real closures (functions capture their defining
  environment); also anonymous function *expressions* `fn(a, b) { ... }` usable
  anywhere a value is expected (e.g. passed straight to `map`/`filter`); a
  trailing parameter may carry a default value (`fn f(a, b = 1) { ... }`),
  evaluated fresh per call when omitted by the caller; a trailing rest
  parameter collects any extra positional arguments into a list
  (`fn f(a, ...rest) { ... }`), combinable with default parameters; call
  arguments accept the same spread syntax (`f(...args)`, `f(1, ...rest, 2)`),
  splicing a list's elements into the positional argument list in place;
  arrow function expressions `(a, b) => a + b` as expression-bodied sugar
  for anonymous `fn` expressions, desugaring purely at parse time so the
  parenthesized form supports everything anonymous `fn`s do: defaults,
  rest parameters, nesting, and closures; a bare single-identifier
  parameter may skip the parens too (`x => x * 2`, exactly one required
  parameter, no default/rest); both forms also accept a block body
  (`(params) => { ... }` and `x => { ... }`), parsed via ordinary
  block-statement rules with no implicit return of the last
  expression — `return` stays explicit, same as any other block;
  parameters accept list/map destructuring patterns too
  (`fn f([a, b]) { ... }`, `fn f({a, b}) { ... }`), the same flat
  positional/key-lookup binding `let`/`for`-loop destructuring already
  use, including the same optional trailing rest element on either
  pattern kind and the same optional per-key rename on map patterns
  (`fn f({a: x, b}) { ... }`), combinable with default values and a
  trailing rest parameter; calls to user-defined functions accept
  trailing keyword arguments matched by parameter name and
  order-independent (`f(a: 1, b: 2)`), Python-style, usable together
  with leading positional arguments but not before them; builtins stay
  positional-only and reject keyword arguments, and destructuring/rest
  parameters have no name a keyword argument could address; list/map
  literals, call arguments, and function parameter lists all accept an
  optional trailing comma before the closing delimiter (`[1, 2,]`,
  `{"a": 1,}`, `f(1, 2,)`, `fn f(a, b,) { ... }`, including a trailing
  comma right after a rest parameter); named function expressions
  (`fn name(params) { ... }`) let an anonymous function refer to itself by
  name for recursion without depending on whatever outer binding it
  happens to be assigned to — the name is bound fresh into each call's own
  environment, not the enclosing scope, so it never leaks outside calls to
  that specific function value
- **Data structures**: lists `[1, 2, 3]` and maps `{"a": 1}`, `expr[expr]`
  indexing for get/set (negative indices supported for list/string reads
  and list writes), plus read-only string indexing, and slicing
  `list[start:end]`/`string[start:end]` with an optional third `:step`
  component (`list[start:end:step]`/`string[start:end:step]`, Python-style,
  out-of-range bounds clamp, negative step reverses direction); slice
  assignment on lists (`list[start:end] = other_list;`, growing or
  shrinking the list to fit the replacement's length, same bound
  normalization as the read side), including a stepped target
  (`list[start:end:step] = other_list;`, delegating to Python's own
  extended-slice-assignment length enforcement — the replacement must be
  exactly the slice's length for any step other than `1`, raising a clean
  runtime error rather than silently truncating/padding; string targets
  remain immutable); list
  literals accept spread elements
  (`[...list1, x, ...list2]`), splicing each spread list's elements in place;
  list comprehensions `[expr for x in iterable]` and `[expr for x in
  iterable if cond]` (one optional filter clause; a fresh per-iteration
  scope so closures built inside the comprehension capture their own
  iteration's binding), including a
  list-destructuring loop variable (`[k + v for [k, v] in items(m)]`,
  same flat positional binding and optional trailing rest element as a
  `for`-loop's own list-destructuring form), a map-destructuring loop
  variable (`[a + b for {a, b} in list_of_maps]`, same key-lookup
  binding as a `for`-loop's own map-destructuring form, including the
  same optional trailing rest element and per-key rename), and multiple
  chained `for` clauses (`[x + y for x in xs for y in ys]`,
  cartesian-product iteration matching Python's own multi-clause
  comprehension semantics — each clause's own optional `if` filters
  before any later clause runs); map literals accept spread
  elements too (`{...map1, "k": v}`), merging
  left to right with later keys/spreads winning on conflict; shorthand
  properties (`let a = 1, b = 2; print({a, b});` is `{"a": 1, "b": 2}`,
  each bare identifier expanding to `"name": name`, the construction-side
  inverse of the `let {a, b} = expr;` destructuring shorthand), freely
  mixable with explicit `key: value` entries, spread, and trailing commas
  in the same literal; map
  comprehensions `{k: v for x in iterable}` and `{k: v for x in iterable
  if cond}` (same shape as list comprehensions — one optional filter
  clause, no nesting, fresh per-iteration scope, and the same
  list-destructuring and map-destructuring loop variable support;
  colliding keys collapse to the last write, same as a plain map
  literal); dot access
  sugar for map string keys (`m.key` as sugar for `m["key"]`, including as
  an assignment/`++`/`--`/compound-assign target (arithmetic and
  bitwise/shift alike, e.g. `m.key += 1`); only identifier-shaped keys
  work, so `m.if` is a `ParseError`)
- **Builtins**: `print`, `len`, `is_empty`, `type`, conversions, `push`, `pop`, `insert`,
  `remove_at`, `first`, `last`, `take`, `drop`, `take_while`, `drop_while`, `take_right`, `drop_right`, `keys`, `values`, `items`,
  `from_entries`, `enumerate`, `merge`, `invert`, `get`, `remove` (by key for maps, by value for lists),
  `copy`, `deep_copy`, `deep_equal`, `contains`, `index_of`, `last_index_of`, `find_index`, `find_last_index`, `count`, `unique`, `distinct_by`, `flatten`, `flatten_deep`, `get_in`,
  `union`, `intersection`, `difference`, `symmetric_difference`, `is_subset`, `is_superset`, `is_disjoint` (lists treated as unordered sets), `interleave`, `interpose`, `zip_object`,
  `pluck`, `pick`, `omit`, `pick_by`, `omit_by`,
  `flat_map`, `chunk`, `sliding_window`, `group_consecutive`, `reverse`, `rotate`, `shuffle`, `sample`, `sort`, `sort_by`, `group_by`, `key_by`, `count_by`, `partition`, `range`, `repeat`, `map`,
  `deep_merge`,
  `map_values`, `map_keys`, `filter`, `reject`, `reduce`, `pipe`, `compose`, `curry`, `memoize`, `slice`, `split_at`, `concat`, `zip`, `zip_longest`, `unzip`, `zip_with`, `min_by`, `max_by`, `assert`, `format`, `sum`, `sum_by`, `product`, `mean`, `median`, `variance`, `std_dev`, `mode`, `geometric_mean`, `harmonic_mean`, `frequencies`, `compact`,
  `any`, `all`, `none`, string methods `upper`, `lower`, `capitalize`, `title`,
  `trim`, `trim_start`, `trim_end`, `split`, `join`, `find`, `find_last`, `starts_with`, `ends_with`, `replace`, `replace_first`,
  `strip_prefix`, `strip_suffix`, `lines`, `words`, `chars`,
  `pad_start`, `pad_end`, `pad_center`, `truncate`, `to_fixed`, math builtins `abs`, `sign`, `min`, `max`, `round`, `floor`,
  `ceil`, `pow`, `sqrt`, `cbrt` (real cube root, domain-unrestricted unlike `sqrt` — negative input returns a negative
  result instead of raising), `sin`, `cos`, `tan`, `log`, `gcd`, `lcm`, `factorial`, `clamp`, `lerp`, `random_int`, `random_choice`,
  `ord`/`chr` for character/code-point
  conversion, `to_hex`/`to_bin`/`to_oct` for integer-to-string base conversion, `is_even`/`is_odd`/`is_divisible`/`is_prime`/`is_composite`/`is_semiprime`/`is_coprime`
  integer parity/divisibility/primality/coprimality predicates (`is_semiprime` testing whether an integer is the product of exactly two primes counted with multiplicity),
  `nth_prime` to return the prime found at a 1-indexed position, the complementary "which prime" question to `is_prime`/`prime_factors`,
  `nth_fibonacci` to return the Fibonacci number found at a 1-indexed position, the value-returning sibling of `is_fibonacci`'s membership test,
  `nth_lucas` to return the Lucas number found at a 1-indexed position, the same question for the Lucas sequence, the value-returning sibling of `is_lucas_number`'s membership test,
  `binomial` to compute the binomial coefficient (`n` choose `k`), the combinatorics question built on top of `factorial`,
  `nth_catalan` to return the Catalan number found at a 1-indexed position, a thin composition of `binomial` (`C(k) = binomial(2k, k) / (k + 1)`, `k` the 0-indexed Catalan index),
  `is_emirp` to test whether a prime's decimal-digit reversal is a different prime,
  `is_squarefree` to test whether an integer has no repeated prime factor,
  `is_powerful_number` to test whether every prime factor of an integer appears with exponent `2` or more,
  `is_achilles` to test whether an integer is powerful but not itself a perfect power
  (the gap between `is_powerful_number` and `is_perfect_power`, e.g. `72 = 2^3 * 3^2`),
  `is_perfect_power` to test whether an integer equals `m ** k` for some integer base `m` and exponent `k >= 2`
  (the general closure of `is_perfect_square`/`is_perfect_cube`/`is_powerful_number`, negative input admitted only
  through odd exponents),
  `is_fibonacci` to test Fibonacci-sequence membership via a closed-form perfect-square check,
  `is_lucas_number` to test membership in Fibonacci's companion Lucas sequence (same recurrence, seeded `2, 1`
  instead of `0, 1`) via generate-and-compare rather than a closed form,
  `is_happy_number` to test the happy-number digit-square-sum recurrence via set-based cycle detection,
  `is_sad_number` to test the direct complement of `is_happy_number` (cycles forever instead of reaching `1`),
  `is_triangular` to test triangular-number membership via the same closed-form perfect-square technique as `is_fibonacci`,
  `is_pentagonal` to test pentagonal-number membership via the same closed-form technique plus a modular-residue check,
  `is_hexagonal` as the cluster's third member, testing hexagonal-number membership via the same closed-form technique,
  `is_heptagonal` as the cluster's fourth member, testing heptagonal-number membership via the same closed-form technique,
  `is_octagonal` as the cluster's fifth member, testing octagonal-number membership via the same closed-form technique,
  `nth_triangular` to return the triangular number found at a 1-indexed position via the exact closed form `n(n+1)/2`, the value-returning sibling of `is_triangular`'s membership test,
  `nth_pentagonal` to return the pentagonal number found at a 1-indexed position via the exact closed form `k(3k - 1)/2`, the figurate-number cluster's second `nth_*` member alongside `nth_triangular`,
  `nth_hexagonal` to return the hexagonal number found at a 1-indexed position via the exact closed form `k(2k - 1)`, the figurate-number cluster's third `nth_*` member,
  `is_power_of_two` to test whether an integer is a power of two
  via the `n & (n - 1) == 0` bit trick,
  `is_evil`/`is_odious` to test the parity of an integer's binary popcount
  (even/odd count of `1` bits, negative input raises a domain error),
  `is_palindrome` to test whether a string reads the same forwards
  and backwards, `is_sorted` to test whether a list is already in non-decreasing order,
  `is_unique` to test whether a list has no duplicate elements,
  `is_upper`/`is_lower` to test whether a string is entirely upper/lowercase,
  `is_alpha`/`is_digit`/`is_alnum`/`is_space`/`is_ascii`/`is_numeric` to test a string's content
  (letters only, digits only, alphanumeric only, whitespace only, ASCII-only, Unicode-numeric),
  `is_blank` to test whether a string is empty or whitespace-only (the one case `is_space` excludes),
  `digit_sum` to sum an integer's decimal digits (sign ignored),
  `digit_product` to multiply an integer's decimal digits together (sign ignored, any `0` digit collapses the result to `0`),
  `is_perfect_square` to test whether an integer is a perfect square,
  `is_armstrong` to test whether an integer equals the sum of its own digits each raised to the digit count,
  `is_strong_number` to test whether an integer equals the sum of its own digits' factorials,
  `is_leap_year` to test the Gregorian leap-year rule,
  `reverse_int` to reverse an integer's decimal digits (sign preserved),
  `divisors` to list an integer's positive divisors in sorted order,
  `aliquot_sum` to sum an integer's own proper divisors (the value-returning counterpart to
  `is_perfect_number`/`is_abundant`/`is_deficient`),
  `num_divisors` to count an integer's positive divisors including itself
  (the count-returning sibling of `divisors`/`aliquot_sum`),
  `prime_factors` to list an integer's prime factors with multiplicity in
  ascending order,
  `is_perfect_number` to test whether an integer equals the sum of its own proper divisors,
  `is_abundant` to test whether an integer's proper divisors sum to more than itself,
  `is_deficient` to test whether an integer's proper divisors sum to less than itself,
  `is_amicable` to test whether two distinct integers' proper-divisor sums point at each other,
  `is_palindrome_number` to test whether an integer's decimal digits read the same forwards and backwards,
  `digital_root` to reduce an integer to a single digit via repeated digit-summing,
  `multiplicative_persistence` to count how many times an integer's digits must be repeatedly multiplied together before the result drops to a single digit,
  `additive_persistence` as its digit-summing sibling, counting how many repeated digit-sum steps reduce an integer to a single digit,
  `is_anagram` to test whether two strings share the same character multiset,
  `is_rotation` to test whether one string is a rotation of another via the doubled-string trick,
  `is_subsequence` to test whether one string's characters all appear in another in the same
  relative order without needing to be contiguous,
  `is_permutation` as its list-oriented sibling,
  `is_palindrome_list` to test whether a list reads the same forwards and backwards,
  `is_pangram` to test whether a string contains every letter of the alphabet at least once,
  `is_balanced` to test whether a string's `()`/`[]`/`{}` brackets are all properly matched and nested,
  `is_isogram` to test whether a string has no letter repeated (case-insensitive, non-letters ignored),
  `levenshtein_distance` to compute the classic string edit distance (minimum single-character
  insertions/deletions/substitutions to turn one string into another),
  `is_automorphic` to test whether an integer's square ends with the integer itself in decimal,
  `hamming_distance` to count differing positions between two equal-length strings,
  `is_harshad` to test whether an integer is divisible by the sum of its own decimal digits,
  `is_perfect_cube` to test whether an integer is a perfect cube (negative inputs allowed),
  `is_pronic` to test whether an integer is expressible as `k * (k + 1)`,
  `collatz_length` to count the steps the Collatz (3n+1) recurrence takes to reach `1`,
  `collatz_max` to return the peak value that same recurrence reaches before collapsing to `1`,
  `is_kaprekar` to test whether a number's square splits into two parts that sum back to the number,
  `swap_case` to flip each character's case,
  `is_positive`/`is_negative`/`is_zero` to test a number's sign,
  `is_repdigit` to test whether every decimal digit of an integer is the same,
  `is_undulating` to test whether an integer's decimal digits strictly alternate between exactly two distinct values,
  `is_pernicious` to test whether an integer's binary popcount is itself prime (sits next to `is_evil`/`is_odious`
  as the third popcount-based predicate, negative input raises the same domain error they do),
  `is_sphenic` to test whether an integer is the product of three distinct primes (e.g. `30 = 2 * 3 * 5`,
  the natural next member of the "product of primes" family alongside `is_semiprime`'s "product of exactly two"),
  `is_circular_prime` to test whether every rotation of an integer's decimal digits is also prime
  (e.g. `197`/`971`/`719`),
  `cartesian_product` to return every ordered combination of one element from each of N lists
  (an N-list generalization of `zip`, a thin wrapper over `itertools.product`),
  `power_set` to return every subset of a list across all sizes (a thin wrapper over
  `itertools.combinations`, the enumerate-vs-count sibling of `binomial`'s counting question), and
  type predicates `is_list`, `is_map`, `is_string`, `is_number`, `is_bool`, `is_nil`,
  `is_function`, `is_int`, `is_float`
- **Errors**: parse and runtime errors carry line/column info — no raw Python
  tracebacks; runtime errors raised inside nested function calls also report
  the full call stack (`  at name (line:col)` per frame, innermost first);
  an undefined-name error suggests a close match already in scope
  (`undefined name 'lenght' (did you mean 'length'?)`) when one exists
- **Three front ends**: run `.cin` script files, evaluate an inline snippet
  passed on the command line (`-e`/`--eval`, no file needed), or an
  interactive REPL with `readline`-backed command history (up-arrow to
  recall, when available) persisted across sessions in a gitignored
  `.cinder_history` file, Tab completion for builtin names and in-scope
  variables, and a `:load <path>` meta-command to run a script's
  statements into the current REPL session
- **Comments**: `# line comments` and `/* block comments */` (non-nesting),
  both skipped by the lexer wherever whitespace is allowed

## Quickstart

```sh
cd projects/cinder

# Run an example script
python3 -m cinder.cli run examples/fizzbuzz.cin

# Evaluate a snippet inline, no file needed
python3 -m cinder.cli eval 'print(1 + 2);'

# Start the interactive REPL
python3 -m cinder.cli repl
```

## Examples

Each example in [`examples/`](examples/) ships with its expected output
(`*.expected`), so they double as end-to-end tests:

| Script | Shows off |
|--------|-----------|
| `fizzbuzz.cin` | control flow, modulo, printing |
| `fibonacci.cin` | recursion and function calls |
| `collections.cin` | lists, maps, `push`/`pop`/`keys`/`values` |
| `list_ops.cin` | indexing and list manipulation |
| `self_check.cin` | `assert`-driven self-checks |

## Running the tests

```sh
cd projects/cinder
python3 -m unittest discover -s tests -v
```

The suite (3000+ tests) covers every layer — lexer, parser, interpreter,
builtins, CLI, REPL — and `main` is kept green at all times.

## Project layout

```
projects/cinder/
├── cinder/           # the implementation
│   ├── tokens.py     #   token types
│   ├── lexer.py      #   source text → tokens
│   ├── parser.py     #   tokens → AST (recursive descent)
│   ├── ast_nodes.py  #   AST node definitions
│   ├── interpreter.py#   tree-walking evaluator + environments
│   ├── builtins.py   #   standard library
│   ├── errors.py     #   diagnostics with line/column
│   ├── repl.py       #   interactive loop
│   └── cli.py        #   `run` / `eval` / `repl` entrypoints
├── tests/            # unit + end-to-end tests
├── examples/         # sample programs with expected output
├── PROJECT.md        # vision, spec, and roadmap (Architect-owned)
├── BACKLOG.md        # prioritized task list for upcoming nights
└── CHANGELOG.md      # archived history of every merged task
```

## Status & roadmap

Actively developed, nightly. Recently landed: `nth_hexagonal` — the
hexagonal number found at a 1-indexed position via the closed form
`k(2k - 1)`, the figurate-number cluster's third `nth_*` member alongside
`nth_triangular`/`nth_pentagonal` — and before that literal elements in
list patterns (`match ([1, 2]) { [1, b] => b, _ => 0 }`) — a bare literal
now allowed alongside bound identifiers per element, falling through (not
raising) on a mismatch — and before that `power_set` — every subset of a
list across all sizes, the enumerate-vs-count sibling of `binomial`'s
counting question and the single-list analogue to `cartesian_product`'s
N-list combination — and before that negative literal patterns in `match`
arms (`match (-5) { -5 => "neg", _ => "pos" }`) — a `MINUS` branch in the
pattern parser that negates a following `INT`/`FLOAT` literal, not
touching range-pattern bounds. See [`CHANGELOG.md`](CHANGELOG.md) for the
full merge history.
Coming up next (see [`BACKLOG.md`](BACKLOG.md)): rest capture in list
patterns (`match ([1, 2, 3]) { [a, ...rest] => rest, _ => [] }`) —
matching "at least N elements" instead of an exact length, mirroring the
rest capture `let` destructuring already has, `permutations` — every
ordering of a list, the collection-side sibling of
`cartesian_product`/`power_set` rounding out the "enumerate the ways to
arrange/pick/combine elements" cluster, flat map patterns in `match` arms
(`match ({"a": 1, "b": 2}) { {a, b} => a + b, _ => 0 }`) — the map-subject
counterpart to flat list patterns, testing key presence and binding each
key's value in one step, `combinations` — every r-length combination of a
list, the fixed-size sibling of `power_set` (all sizes at once) and the
enumerate-vs-count sibling of `binomial` for one specific size,
`nth_heptagonal` — the k-th heptagonal number by position, the
figurate-number cluster's fourth `nth_*` member, and negative bounds in
range patterns (`match (-5) { -10..0 => "neg", _ => "other" }`) — the
same negation `-5 => "neg"` already gets as a plain literal pattern,
extended to range bounds. The pattern-matching tasks are all steps in the
arc opened by PR #304 and can land in either order relative to their
siblings; each is written to adapt to whichever has already landed by the
time it's claimed. (Guards in `match` arms, `n if n > 0 => "positive"`,
were attempted but closed after three failed review rounds over a
recurring parser bug — see `BACKLOG.md`'s `## Graveyard` for the
postmortem; they're a real gap but not back in the active queue yet.) The
backlog mixes language depth with stdlib breadth over time rather than
running either in one long block. The full vision and non-goals live in
[`PROJECT.md`](PROJECT.md).
