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
  everything else (including `0` and `""`) is truthy; strings support
  interpolation (`"hello, ${name}!"`, `"${1 + 2}"`) with arbitrary expressions
  inside `${...}`, stringified the same way `print`/`format` render values;
  integer literals may also be written in hex (`0x1F`), binary (`0b101`), or
  octal (`0o17`); any numeric literal may use `_` as a digit-group separator
  for readability (`1_000_000`, `0xFF_FF`, `3.14_159`), stripped before the
  value is constructed
- **Variables & scope**: `let` declarations, `const` declarations for
  immutable bindings (reassignment or `++`/`--`/compound-assignment on a
  `const` name raises a runtime error; a `let` may still be redeclared as
  `const` and vice versa in the same scope), assignment, blocks with proper
  lexical scoping (inner `let` shadows, outer survives); list destructuring
  in `let` (`let [a, b] = expr;`, flat positional binding, no nesting, plus
  an optional trailing rest element `let [a, b, ...rest] = expr;` that
  collects any remaining elements into a list, empty if none are left) and
  map destructuring (`let {a, b} = expr;`, binds each identifier by
  looking it up as a key, extra unnamed keys ignored, plus the same kind
  of optional trailing rest element `let {a, ...rest} = expr;` that
  collects every key not already named into a map, empty if none are
  left, and an optional per-key rename `let {a: x, b} = expr;` binding
  the value under key `a` to local name `x` instead of `a`, combinable
  with the rest element and freely mixable with un-renamed keys in the
  same pattern), plus plain assignment forms of both for already-declared
  bindings — list (`[a, b] = expr;`, same flat positional binding and
  optional trailing rest element as the `let` form, e.g. the swap idiom
  `[a, b] = [b, a];`) and map (`{a, b} = expr;`, same key-lookup binding
  as the `let` form, including the same optional trailing rest element
  `{a, ...rest} = expr;` and the same optional per-key rename
  `{a: x, b} = expr;`)
- **Control flow**: `if`/`else`, `while`, `do { ... } while (cond);`,
  `for NAME in EXPR { ... }` over lists, strings (character-by-character),
  and maps (over keys), plus list-destructuring loop variables
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
  propagate through uncaught), an optional `finally { ... }` block (at
  least one of `catch`/`finally` is required) that always runs on the way
  out of the `try`, whether it succeeded, was caught, or is propagating
  uncaught, a `throw expr;` statement for raising user-defined errors
  (the expression must be a string; catchable by an enclosing
  `try`/`catch` exactly like a builtin runtime error), `switch`
  statements with `case`/`default` (no fallthrough, first match wins;
  a single `case` may list multiple values, e.g. `case 1, 2, 3: { ... }`,
  matching if any of them equals the switch expression)
- **Operators**: full arithmetic/comparison/logical set, compound
  assignment (`+=`, `-=`, `*=`, `/=`, `%=`, `**=`, `//=`, `&=`, `|=`, `^=`,
  `<<=`, `>>=`;
  all of them, arithmetic and bitwise/shift alike, accept an
  index-expression target too, e.g. `xs[0] += 1`, `m.key &= 3`),
  increment/decrement statement sugar `x++;`/`x--;` (identifier or
  index-expression target, e.g. `xs[0]++;`; statement-only, not usable as a
  value), `*` repetition for `str * int`/`list * int` (Python repetition
  semantics), floor division `//` (same precedence tier as `/`/`%`,
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
  a raw Python exception or a complex number)
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
  trailing rest parameter
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
  iterable if cond]` (a single loop variable, one optional filter clause,
  no nesting; a fresh per-iteration scope so closures built inside the
  comprehension capture their own iteration's binding), including a
  list-destructuring loop variable (`[k + v for [k, v] in items(m)]`,
  same flat positional binding and optional trailing rest element as a
  `for`-loop's own list-destructuring form) and a map-destructuring loop
  variable (`[a + b for {a, b} in list_of_maps]`, same key-lookup
  binding as a `for`-loop's own map-destructuring form, including the
  same optional trailing rest element and per-key rename); map literals accept spread
  elements too (`{...map1, "k": v}`), merging
  left to right with later keys/spreads winning on conflict; map
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
  `map_values`, `map_keys`, `filter`, `reject`, `reduce`, `pipe`, `compose`, `curry`, `memoize`, `slice`, `split_at`, `concat`, `zip`, `zip_longest`, `unzip`, `zip_with`, `min_by`, `max_by`, `assert`, `format`, `sum`, `sum_by`, `product`, `mean`, `median`, `variance`, `std_dev`, `mode`, `frequencies`, `compact`,
  `any`, `all`, `none`, string methods `upper`, `lower`, `capitalize`, `title`,
  `trim`, `trim_start`, `trim_end`, `split`, `join`, `find`, `find_last`, `starts_with`, `ends_with`, `replace`, `replace_first`,
  `strip_prefix`, `strip_suffix`, `lines`, `words`, `chars`,
  `pad_start`, `pad_end`, `pad_center`, `truncate`, `to_fixed`, math builtins `abs`, `sign`, `min`, `max`, `round`, `floor`,
  `ceil`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `log`, `gcd`, `lcm`, `factorial`, `clamp`, `lerp`, `random_int`, `random_choice`,
  `ord`/`chr` for character/code-point
  conversion, `to_hex`/`to_bin`/`to_oct` for integer-to-string base conversion, `is_even`/`is_odd`/`is_divisible`/`is_prime`/`is_composite`/`is_coprime`
  integer parity/divisibility/primality/coprimality predicates, `is_emirp` to test whether a prime's decimal-digit reversal is a different prime,
  `is_fibonacci` to test Fibonacci-sequence membership via a closed-form perfect-square check,
  `is_happy_number` to test the happy-number digit-square-sum recurrence via set-based cycle detection,
  `is_triangular` to test triangular-number membership via the same closed-form perfect-square technique as `is_fibonacci`,
  `is_power_of_two` to test whether an integer is a power of two
  via the `n & (n - 1) == 0` bit trick, `is_palindrome` to test whether a string reads the same forwards
  and backwards, `is_sorted` to test whether a list is already in non-decreasing order,
  `is_unique` to test whether a list has no duplicate elements,
  `is_upper`/`is_lower` to test whether a string is entirely upper/lowercase,
  `is_alpha`/`is_digit`/`is_alnum`/`is_space`/`is_ascii`/`is_numeric` to test a string's content
  (letters only, digits only, alphanumeric only, whitespace only, ASCII-only, Unicode-numeric),
  `is_blank` to test whether a string is empty or whitespace-only (the one case `is_space` excludes),
  `digit_sum` to sum an integer's decimal digits (sign ignored),
  `is_perfect_square` to test whether an integer is a perfect square,
  `is_armstrong` to test whether an integer equals the sum of its own digits each raised to the digit count,
  `is_leap_year` to test the Gregorian leap-year rule,
  `reverse_int` to reverse an integer's decimal digits (sign preserved),
  `divisors` to list an integer's positive divisors in sorted order,
  `aliquot_sum` to sum an integer's own proper divisors (the value-returning counterpart to
  `is_perfect_number`/`is_abundant`/`is_deficient`),
  `is_perfect_number` to test whether an integer equals the sum of its own proper divisors,
  `is_abundant` to test whether an integer's proper divisors sum to more than itself,
  `is_deficient` to test whether an integer's proper divisors sum to less than itself,
  `is_palindrome_number` to test whether an integer's decimal digits read the same forwards and backwards,
  `digital_root` to reduce an integer to a single digit via repeated digit-summing,
  `is_anagram` to test whether two strings share the same character multiset,
  `is_rotation` to test whether one string is a rotation of another via the doubled-string trick,
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
  `swap_case` to flip each character's case,
  `is_positive`/`is_negative`/`is_zero` to test a number's sign, and type predicates
  `is_list`, `is_map`, `is_string`, `is_number`, `is_bool`, `is_nil`,
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

The suite (2600+ tests) covers every layer — lexer, parser, interpreter,
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

Actively developed, nightly. Recently landed: `is_perfect_cube` to test
whether an integer is a perfect cube (negative inputs allowed), and
`aliquot_sum` to sum an integer's own proper divisors. Coming up next
(see [`BACKLOG.md`](BACKLOG.md)): keyword arguments in function calls
(`f(a: 1, b: 2)`), `is_pronic` to test whether an integer is expressible
as `k * (k + 1)`, default values in list-destructuring patterns
(`let [a, b = 5] = expr;`), `collatz_length` to count the steps the
Collatz recurrence takes to reach `1`, and `is_strong_number` to test
whether an integer equals the sum of its own digits' factorials. The
backlog mixes language depth with stdlib breadth over time rather than
running either in one long block. The full vision and non-goals live in
[`PROJECT.md`](PROJECT.md).
