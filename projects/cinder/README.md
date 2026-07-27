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
- **Variables & scope**: `let` declarations, assignment, blocks with proper
  lexical scoping (inner `let` shadows, outer survives); list destructuring
  in `let` (`let [a, b] = expr;`, flat positional binding, no nesting/rest)
  and map destructuring (`let {a, b} = expr;`, binds each identifier by
  looking it up as a key, extra unnamed keys ignored)
- **Control flow**: `if`/`else`, `while`, `for NAME in EXPR { ... }` over
  lists, strings (character-by-character), and maps (over keys),
  `break`/`continue` in both loop kinds, `try { ... } catch (name) { ... }`
  for recovering from runtime errors (the caught message binds to `name`;
  `break`/`continue`/`return` still propagate through uncaught), `switch`
  statements with `case`/`default` (no fallthrough, first match wins)
- **Operators**: full arithmetic/comparison/logical set, compound
  assignment (`+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`;
  the bitwise/shift set also accepts an index-expression target, e.g.
  `xs[0] &= 3`, unlike the arithmetic set which is identifier-only), `*`
  repetition for `str * int`/`list * int` (Python repetition semantics),
  `in` for membership tests (lists, strings, maps), the ternary conditional
  `cond ? then : else`, the nil-coalescing operator `a ?? b` (short-circuits
  like `and`/`or`: evaluates `b` only when `a` is `nil`, unlike `or` which
  falls through on any falsy value), and bitwise operators `&`, `|`, `^`,
  `~`, `<<`, `>>` (int-only, with a clean runtime error on a negative shift
  count)
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
  clamp, not assignable); list literals also accept spread elements
  (`[...list1, x, ...list2]`), splicing each spread list's elements in place
  (map literals don't support spread)
- **Builtins**: `print`, `len`, `is_empty`, `type`, conversions, `push`, `pop`, `insert`,
  `remove_at`, `first`, `last`, `take`, `drop`, `take_while`, `drop_while`, `keys`, `values`, `items`,
  `enumerate`, `merge`, `invert`, `get`, `remove` (by key for maps, by value for lists),
  `copy`, `deep_copy`, `contains`, `index_of`, `last_index_of`, `find_index`, `count`, `unique`, `distinct_by`, `flatten`, `flatten_deep`,
  `union`, `intersection`, `difference` (lists treated as unordered sets),
  `pluck`, `pick`, `omit`,
  `flat_map`, `chunk`, `reverse`, `shuffle`, `sample`, `sort`, `sort_by`, `group_by`, `count_by`, `partition`, `range`, `repeat`, `map`,
  `map_values`, `filter`, `reduce`, `slice`, `concat`, `zip`, `zip_with`, `min_by`, `max_by`, `assert`, `format`, `sum`, `mean`, `median`,
  `any`, `all`, string methods `upper`, `lower`, `capitalize`,
  `trim`, `split`, `join`, `find`, `starts_with`, `ends_with`, `replace`,
  `strip_prefix`, `strip_suffix`, `lines`, `words`,
  `pad_start`, `pad_end`, math builtins `abs`, `min`, `max`, `round`, `floor`,
  `ceil`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `log`, `gcd`, `lcm`, `clamp`, `ord`/`chr` for character/code-point
  conversion, and type predicates
  `is_list`, `is_map`, `is_string`, `is_number`, `is_bool`, `is_nil`,
  `is_function`
- **Errors**: parse and runtime errors carry line/column info — no raw Python
  tracebacks; runtime errors raised inside nested function calls also report
  the full call stack (`  at name (line:col)` per frame, innermost first)
- **Two front ends**: run `.cin` script files, or an interactive REPL with
  `readline`-backed command history (up-arrow to recall, when available),
  persisted across sessions in a gitignored `.cinder_history` file
- **Comments**: `# line comments` and `/* block comments */` (non-nesting),
  both skipped by the lexer wherever whitespace is allowed

## Quickstart

```sh
cd projects/cinder

# Run an example script
python3 -m cinder.cli run examples/fizzbuzz.cin

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

The suite (1195+ tests) covers every layer — lexer, parser, interpreter,
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
│   └── cli.py        #   `run` / `repl` entrypoints
├── tests/            # unit + end-to-end tests
├── examples/         # sample programs with expected output
├── PROJECT.md        # vision, spec, and roadmap (Architect-owned)
└── BACKLOG.md        # prioritized task list for upcoming nights
```

## Status & roadmap

Actively developed, nightly. Recently landed: bitwise/shift compound
assignment (`&=`, `|=`, `^=`, `<<=`, `>>=`), including index-expression
targets (`xs[0] &= 3`). Coming up next (see [`BACKLOG.md`](BACKLOG.md)): a
run of standard-library additions (`map_keys`, `title`, `trim_start`/
`trim_end`, `sign`, `random_int`/`random_choice`, `round` with a `digits`
argument, `to_fixed`), then two language features — increment/decrement
statement operators (`++`/`--`) and a `finally` block for `try`/`catch` —
with more stdlib breadth after. The backlog mixes language depth with
stdlib breadth over time rather than running either in one long block. The
full vision and non-goals live in [`PROJECT.md`](PROJECT.md).
