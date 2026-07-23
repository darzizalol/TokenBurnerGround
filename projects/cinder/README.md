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
  everything else (including `0` and `""`) is truthy
- **Variables & scope**: `let` declarations, assignment, blocks with proper
  lexical scoping (inner `let` shadows, outer survives)
- **Control flow**: `if`/`else`, `while`, `for NAME in EXPR { ... }` over
  lists, strings (character-by-character), and maps (over keys),
  `break`/`continue` in both loop kinds
- **Operators**: full arithmetic/comparison/logical set, compound
  assignment (`+=`, `-=`, `*=`, `/=`, `%=`), `*` repetition for
  `str * int`/`list * int` (Python repetition semantics), `in` for
  membership tests (lists, strings, maps), the ternary conditional
  `cond ? then : else`, and bitwise operators `&`, `|`, `^`, `~`, `<<`, `>>`
  (int-only, with a clean runtime error on a negative shift count)
- **Functions**: `fn name(a, b) { ... }` — first-class, arity-checked, with
  recursion, `return`, and real closures (functions capture their defining
  environment); also anonymous function *expressions* `fn(a, b) { ... }` usable
  anywhere a value is expected (e.g. passed straight to `map`/`filter`)
- **Data structures**: lists `[1, 2, 3]` and maps `{"a": 1}`, `expr[expr]`
  indexing for get/set (negative indices supported for list/string reads
  and list writes), plus read-only string indexing
- **Builtins**: `print`, `len`, `type`, conversions, `push`, `pop`, `keys`,
  `values`, `items`, `enumerate`, `merge`, `get`, `remove`, `copy`, `contains`,
  `index_of`, `unique`, `reverse`, `sort`, `sort_by`, `range`, `map`, `filter`, `reduce`, `slice`, `concat`,
  `zip`, `assert`, `sum`, `any`, `all`, string methods `upper`, `lower`,
  `trim`, `split`, `join`, `find`, `starts_with`, `ends_with`, `replace`,
  math builtins `abs`, `min`, `max`, `round`, `floor`, `ceil`, `pow`, `sqrt`,
  and type predicates `is_list`, `is_map`, `is_string`, `is_number`,
  `is_bool`, `is_nil`, `is_function`
- **Errors**: parse and runtime errors carry line/column info — no raw Python
  tracebacks; runtime errors raised inside nested function calls also report
  the full call stack (`  at name (line:col)` per frame, innermost first)
- **Two front ends**: run `.cin` script files, or an interactive REPL with
  `readline`-backed command history (up-arrow to recall, when available)

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

The suite (570+ tests) covers every layer — lexer, parser, interpreter,
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

Actively developed, nightly. Recently landed: a fix for
`contains`/`index_of`/`in` wrongly treating `bool` and `int` as equal (the
same bug `unique` had already been fixed for). Coming up next (see
[`BACKLOG.md`](BACKLOG.md)): `count`/`flatten` for lists, a `format`
string templating builtin, persistent REPL command history, list slicing
syntax (`list[a:b]`), `group_by`, and `try`/`catch` error recovery. The
full vision and non-goals live in [`PROJECT.md`](PROJECT.md).
