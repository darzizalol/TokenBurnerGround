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
  octal (`0o17`)
- **Variables & scope**: `let` declarations, `const` declarations for
  immutable bindings (reassignment or `++`/`--`/compound-assignment on a
  `const` name raises a runtime error; a `let` may still be redeclared as
  `const` and vice versa in the same scope), assignment, blocks with proper
  lexical scoping (inner `let` shadows, outer survives); list destructuring
  in `let` (`let [a, b] = expr;`, flat positional binding, no nesting, plus
  an optional trailing rest element `let [a, b, ...rest] = expr;` that
  collects any remaining elements into a list, empty if none are left) and
  map destructuring (`let {a, b} = expr;`, binds each identifier by
  looking it up as a key, extra unnamed keys ignored)
- **Control flow**: `if`/`else`, `while`, `do { ... } while (cond);`,
  `for NAME in EXPR { ... }` over lists, strings (character-by-character),
  and maps (over keys), plus list-destructuring loop variables
  (`for [k, v] in items(m) { ... }`, same flat positional binding and
  optional trailing rest element as `let` list destructuring), a
  C-style `for (init; cond; step) { ... }` loop
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
  assignment (`+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`;
  all of them, arithmetic and bitwise/shift alike, accept an
  index-expression target too, e.g. `xs[0] += 1`, `m.key &= 3`),
  increment/decrement statement sugar `x++;`/`x--;` (identifier or
  index-expression target, e.g. `xs[0]++;`; statement-only, not usable as a
  value), `*` repetition for `str * int`/`list * int` (Python repetition
  semantics),
  `in` for membership tests (lists, strings, maps), the ternary conditional
  `cond ? then : else`, the nil-coalescing operator `a ?? b` (short-circuits
  like `and`/`or`: evaluates `b` only when `a` is `nil`, unlike `or` which
  falls through on any falsy value) and its compound-assignment sibling
  `a ??= b` (identifier or index/dot-access targets, e.g. `xs[0] ??= 1`,
  `m.key ??= 1`; the RHS is only evaluated, and the target only written,
  when the current value is `nil`), the safe navigation operator `m?.key`
  (short-circuits to `nil` when `m` is `nil` instead of raising, single
  level only, composes with `??` for `m?.key ?? default`), and bitwise
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
  splicing a list's elements into the positional argument list in place
- **Data structures**: lists `[1, 2, 3]` and maps `{"a": 1}`, `expr[expr]`
  indexing for get/set (negative indices supported for list/string reads
  and list writes), plus read-only string indexing, and slicing
  `list[start:end]`/`string[start:end]` (Python-style, out-of-range bounds
  clamp, not assignable); list literals accept spread elements
  (`[...list1, x, ...list2]`), splicing each spread list's elements in place;
  map literals accept spread elements too (`{...map1, "k": v}`), merging
  left to right with later keys/spreads winning on conflict; dot access
  sugar for map string keys (`m.key` as sugar for `m["key"]`, including as
  an assignment/`++`/`--`/compound-assign target (arithmetic and
  bitwise/shift alike, e.g. `m.key += 1`); only identifier-shaped keys
  work, so `m.if` is a `ParseError`)
- **Builtins**: `print`, `len`, `is_empty`, `type`, conversions, `push`, `pop`, `insert`,
  `remove_at`, `first`, `last`, `take`, `drop`, `take_while`, `drop_while`, `take_right`, `drop_right`, `keys`, `values`, `items`,
  `from_entries`, `enumerate`, `merge`, `invert`, `get`, `remove` (by key for maps, by value for lists),
  `copy`, `deep_copy`, `deep_equal`, `contains`, `index_of`, `last_index_of`, `find_index`, `find_last_index`, `count`, `unique`, `distinct_by`, `flatten`, `flatten_deep`, `get_in`,
  `union`, `intersection`, `difference` (lists treated as unordered sets), `interleave`,
  `pluck`, `pick`, `omit`, `pick_by`, `omit_by`,
  `flat_map`, `chunk`, `sliding_window`, `group_consecutive`, `reverse`, `rotate`, `shuffle`, `sample`, `sort`, `sort_by`, `group_by`, `key_by`, `count_by`, `partition`, `range`, `repeat`, `map`,
  `deep_merge`,
  `map_values`, `map_keys`, `filter`, `reduce`, `pipe`, `compose`, `curry`, `memoize`, `slice`, `split_at`, `concat`, `zip`, `zip_longest`, `unzip`, `zip_with`, `min_by`, `max_by`, `assert`, `format`, `sum`, `product`, `mean`, `median`, `variance`, `std_dev`, `mode`, `frequencies`, `compact`,
  `any`, `all`, string methods `upper`, `lower`, `capitalize`, `title`,
  `trim`, `trim_start`, `trim_end`, `split`, `join`, `find`, `starts_with`, `ends_with`, `replace`,
  `strip_prefix`, `strip_suffix`, `lines`, `words`,
  `pad_start`, `pad_end`, `to_fixed`, math builtins `abs`, `sign`, `min`, `max`, `round`, `floor`,
  `ceil`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `log`, `gcd`, `lcm`, `clamp`, `random_int`, `random_choice`,
  `ord`/`chr` for character/code-point
  conversion, `to_hex`/`to_bin`/`to_oct` for integer-to-string base conversion, and type predicates
  `is_list`, `is_map`, `is_string`, `is_number`, `is_bool`, `is_nil`,
  `is_function`
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

The suite (1727+ tests) covers every layer — lexer, parser, interpreter,
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

Actively developed, nightly. Recently landed: the safe-navigation operator
`?.` for map access (`m?.key` is `nil` when `m` is `nil`), `frequencies`
for a list's per-element occurrence counts, a REPL `:load <path>`
meta-command to run a script into the current session, arithmetic *and*
nil-coalescing compound-assign on index/dot-access targets (`xs[0] += 1`,
`m.key ??= 1`), `compact` to drop falsy elements from a list,
`find_last_index` for predicate-based reverse search, the
exponentiation operator `**` (right-associative, tighter than
`*`/`/`/`%`, with the same overflow/complex-result guards as the `pow()`
builtin), and its compound-assign sibling `**=` (accepting index/dot-access
targets like the rest of the arithmetic compound-assign family). Coming
up next (see [`BACKLOG.md`](BACKLOG.md)): `sum_by` to round out the
`min_by`/`max_by`/`sort_by` family, `reject` as `filter`'s
predicate-inverted complement, and `find_last` as `find`'s
reverse-search counterpart for strings.
The backlog mixes language depth with stdlib
breadth over time rather than running either in one long block.
The full vision and non-goals live in [`PROJECT.md`](PROJECT.md).
