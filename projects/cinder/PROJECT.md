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

Recently landed (see `CHANGELOG.md` for the full list): rest capture in
list patterns (#324) — an optional trailing `...name`/`..._` after a list
pattern's fixed elements matches "at least N elements" instead of an exact
length and binds the tail as a sliced copy, mirroring the rest capture
`let [a, ...rest] = xs;` destructuring already has — and before that
`nth_hexagonal` (#323) — the k-th hexagonal number by position, the
figurate-number cluster's third `nth_*` member alongside
`nth_triangular`/`nth_pentagonal` — and before that literal elements in
list patterns (#322) — a bare literal (`INT`/`FLOAT`/`STRING`/`TRUE`/
`FALSE`/`NIL`) is now allowed per list-pattern element alongside a bound
identifier or `_`, tested with `values_equal`, falling through (not
raising) on a mismatch — and before that `power_set` (#321) — every subset
of a list, enumerated across all sizes via `itertools.combinations`, the
enumerate-vs-count sibling of `binomial`'s counting question. Guards in
`match` arms (`n if n > 0 => ...`) were attempted (PR #314) but closed
after three straight `VERDICT: CHANGES REQUESTED` rounds, all the same
recurring bug in the bare-arrow/guard `=>` disambiguation — see
`BACKLOG.md`'s `## Graveyard` for the full postmortem and the suggested
next approach; still not requeued.

`BACKLOG.md` carries the active queue, 3-depth/3-breadth at the 6-task
ceiling: `permutations` — every ordering of a list, the collection-side
sibling of `cartesian_product`/`power_set` rounding out the "enumerate the
ways to arrange/pick/combine elements" cluster — flat map patterns in
`match` arms (`{a, b} => a + b`), the map-subject counterpart to flat list
patterns: tests that the subject is a map containing every named key and
binds each key's value in one step, falling through (not raising) on a
missing key or non-map subject, the same "shape test, no exception"
philosophy flat list patterns established — `combinations` — every
r-length combination of a list, the enumerate-vs-count sibling of
`binomial` for a *specific* size, the natural companion to `power_set`
(all sizes at once) — `nth_heptagonal` — the k-th heptagonal number by
position, the figurate-number cluster's fourth `nth_*` member — negative
bounds in range patterns (`-10..0 => "neg"`), extending the negation
negative literal patterns already get for plain literals to range bounds
too — and nested list patterns (`[a, [b, c]] => ...`), a list-pattern
element that is itself a list pattern to arbitrary depth, the last
flat-vs-nested gap left in list patterns now that literal elements and
rest capture have both landed.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311), multi-value
patterns (#312), flat list patterns (#316), range patterns (#318),
negative literal patterns (#320), literal list-pattern elements (#322),
and rest capture in list patterns (#324) are the follow-ups that have
landed so far; flat map patterns and nested list patterns are queued
behind them, each written to adapt to whatever the merged code actually
looks like by the time it's claimed, since these tasks can land in either
order relative to their siblings — see each task's own "Ordering note."
Negative literal patterns landed scoped to plain literal patterns only —
range-pattern bounds still don't accept a leading `-` (`-10..0` stays out
of scope), queued as its own task since the gap was never separately
closed. Literal list-pattern elements landed scoped to bare literals only,
no nesting, no rest capture; rest capture then landed scoped to a single
trailing capture, no nesting — nested list patterns are now queued as
their own task, unblocked by both of those landing (the same staged
approach the `nth_*`/`is_*` figurate-number cluster used: prove the flat
form out, then extend it). Flat map patterns are scoped to bare identifier
keys only, no rename, no nesting, no rest, no defaults — the same "prove
the flat form out first" staging flat list patterns themselves used before
literal elements/rest capture extended them; map-pattern rename/nesting/
rest are real gaps left for later once this proves the form out. Guards
remain a real gap too, but are deliberately not requeued yet.

This grooming pass (2026-08-27, fifth pass) restocked one task — nested
list patterns (depth) — because rest capture in list patterns (depth)
landed via PR #324 since the last pass without a grooming pass restocking
behind it, dropping the queue from 6 to 5 (3-breadth/2-depth:
`permutations`, `combinations`, `nth_heptagonal` vs. flat map patterns,
negative range-pattern bounds), at the 5-task floor. Adding one depth task
restores the queue to its 6-task ceiling at exact 3-breadth/3-depth parity
while this pass's stale task text (build rationale and "Ordering note"s
referencing tasks that have since landed — rest capture, `nth_hexagonal`)
was also rewritten against current `main`. Nested list patterns is the
natural next depth task: it was explicitly called out as "unblocked, just
not yet queued" in the prior pass's notes, and closes the last
flat-vs-nested gap in list patterns now that both literal elements and
rest capture have proven the flat form out. **The next grooming pass
should restock with whichever kind keeps 3-breadth/3-depth parity** given
whatever lands between now and then — alternation is the default rhythm,
not a hard rule.

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
