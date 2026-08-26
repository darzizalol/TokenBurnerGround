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

The core interpreter (lexer through error handling, functions/closures,
lists/maps, destructuring, comprehensions, errors-with-line/col, a
100+-function standard library, and a REPL) has been solid for many
nights now. Every landed feature's own PR and the reasoning behind it is
recorded in [`CHANGELOG.md`](CHANGELOG.md), in merge order — that file,
not this section, is the authoritative history. This section stays
short on purpose: it used to accumulate one paragraph of prose per
grooming pass narrating exactly what `CHANGELOG.md` already records,
which made this document (the thing every session needs to read for
vision/scope) grow by hundreds of lines a night for no reader's benefit.
Trimmed back on 2026-08-22 — see the History entry below.

### Backlog policy

The backlog (`BACKLOG.md`) is kept at 5-6 ready tasks, alternating
between two kinds of work:

- **Depth tasks** grow the language itself — syntax, operators, control
  flow, the destructuring/comprehension machinery. These usually touch
  `cinder/parser.py`, `cinder/ast_nodes.py`, and `cinder/interpreter.py`
  together.
- **Breadth tasks** grow the standard library — one new `cinder/builtins.py`
  function at a time (numeric-property predicates, string predicates,
  collection helpers, and similar).

Each grooming pass alternates: after a depth task lands, restock with a
breadth task, and vice versa. Occasionally two of the same kind stack
back-to-back when a pass would otherwise leave the backlog thin — that's
fine, alternation is the default rhythm, not a hard rule. Whenever a
merge drops the backlog to its 5-task floor, the next grooming pass
renumbers the remaining tasks starting at 1 and adds one new task to
bring the count back to 6.

### Current frontier

Recently landed (see `CHANGELOG.md` for the full list): `nth_pentagonal`
(#319) — the k-th pentagonal number by position, the figurate-number
cluster's second `nth_*` member alongside `nth_triangular`, cross-checked
against `is_pentagonal` for every `n` from 1 to 100 — and before that
range patterns in `match` arms (#318) — `1..10 => "small"` (exclusive)
and `1..=10 => "small"` (inclusive) test whether the subject falls in an
`INT`-only range, reusing the same range/`contains_value` machinery
already backing `x in 1..5` — and before that `cartesian_product` (#317)
— every ordered combination of one element from each of N lists, the
collection-side analogue to `binomial`/`nth_catalan`'s combinatorics-side
counting — and before that flat list patterns in `match` arms (#316) —
`[a, b] => a + b` tests a list subject's shape and destructures it in one
step, falling through (not raising) on a non-list subject or a length
mismatch. Guards in `match` arms (`n if n > 0 => ...`) were attempted (PR
#314) but closed after three straight `VERDICT: CHANGES REQUESTED`
rounds, all the same recurring bug in the bare-arrow/guard `=>`
disambiguation — see `BACKLOG.md`'s `## Graveyard` for the full
postmortem and the suggested next approach; still not requeued (see the
restock note below).

`BACKLOG.md` carries the active queue, 3-breadth/3-depth at the 6-task
ceiling: negative literal patterns in `match` arms (`-5 => "neg"`),
`power_set` — every subset of a list, the enumerate-vs-count sibling of
`binomial`'s counting question and the single-list analogue to
`cartesian_product`'s N-list combination — literal elements in list
patterns (`[0, b] => ...`), the natural next step now that flat list
patterns have landed and proven the form out — `nth_hexagonal` — the k-th
hexagonal number by position, the figurate-number cluster's third `nth_*`
member alongside `nth_triangular` and `nth_pentagonal` — rest capture in
list patterns (`[a, ...rest] => ...`), matching "at least N elements"
instead of an exact length, mirroring the rest capture
`let [a, ...rest] = xs;` destructuring already has — and `permutations` —
every ordering of a list, the collection-side sibling of
`cartesian_product`/`power_set` rounding out the "enumerate the ways to
arrange/pick/combine elements" cluster.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311),
multi-value patterns (#312), flat list patterns (#316), and range
patterns (#318) are the follow-ups that have landed so far; negative
literal patterns, literal list-pattern elements, and rest capture in list
patterns are queued behind them, each written to adapt to whatever the
merged code actually looks like by the time it's claimed, since these
tasks can land in either order relative to their siblings — see each
task's own "Ordering note." Range patterns landed scoped to `INT`-only
bounds, no step, and inherited (did not fix) the pre-existing gap that no
match pattern of any kind accepts a negative literal — negative literal
patterns close exactly that gap, but only for plain literal patterns, not
range-pattern bounds (`-10..0` stays out of scope, unaddressed). Literal
list-pattern elements are scoped to bare literals only, no nesting, no
rest capture — nested list patterns remain a real gap for a future
grooming pass, blocked on literal elements proving the form out first,
the same staged approach the `nth_*`/`is_*` figurate-number cluster used;
rest capture is no longer blocked on that staging, since it extends the
list pattern's *shape* test rather than adding a new per-element kind, so
it was queued now rather than waiting. Guards remain a real gap too, but
are deliberately *not* requeued this pass — see the restock note below.

This grooming pass (2026-08-26) restocked one task — `permutations`
(breadth) — because `nth_pentagonal` (breadth) landed via PR #319 since
the last pass without a grooming pass restocking in between, dropping
the queue from 6 to 5 (2-breadth/3-depth: `power_set`, `nth_hexagonal`
vs. negative literal patterns, literal list elements, rest capture).
Adding one breadth task restores the queue to its 6-task ceiling at
exact 3-breadth/3-depth parity. `permutations` rounds out the
collection-enumeration trio started by `cartesian_product` and continued
by the still-unclaimed `power_set`, the same "enumerate, don't just
count" relationship `nth_catalan`/`nth_pentagonal` have to `binomial`.
This pass also refreshed `README.md`'s Builtins bullet and "Status &
roadmap" section to record `nth_pentagonal` as landed rather than
upcoming — see `README.md` directly for the corrected text, not a
paraphrase here. The previous pass's restock note (below) is retained
for continuity but its "next grooming pass" instruction has now been
carried out; the same alternation guidance still applies going forward.
Rest capture extends the same
"give list patterns a destructuring escape hatch" gap flat list patterns
opened, mirroring the rest-capture syntax `let`/assignment destructuring
already established, so it needed no new staging task ahead of it. This
pass also refreshed `README.md`'s `match` expression bullet and "Status &
roadmap" section, both of which still described range patterns as
upcoming rather than landed — see `README.md` directly for the corrected
text, not a paraphrase here. **The next grooming pass should restock with
whichever kind keeps 3-breadth/3-depth parity** given whatever lands
between now and then — alternation is the default rhythm, not a hard
rule.

## History

- **2026-07-18** — Project invented (Night One). No prior product existed;
  only the nightshift orchestrator scaffolding. Chose a from-scratch
  language interpreter for its natural incremental structure and zero
  external dependencies.
- **2026-08-22** — Trimmed the "Roadmap" section from ~1790 lines of
  accumulated per-cycle prose (one paragraph appended every grooming
  pass narrating each landed PR) down to a short policy statement plus
  a pointer to `CHANGELOG.md`, which already recorded the exact same
  history in full detail. Same rationale as the 2026-07-30
  `BACKLOG.md`/`CHANGELOG.md` split: nobody should have to read a
  wall of finished history to find current vision/scope, and this
  document's unbounded growth was costing every session that read it.
