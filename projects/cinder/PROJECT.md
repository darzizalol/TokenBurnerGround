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

Recently landed (see `CHANGELOG.md` for the full list): nested patterns
as map pattern values (#337) — the map-pattern counterpart to nested
list patterns (#330), closing the last flat-vs-nested gap between match
map patterns and `let` destructuring (which already supports this) —
and before that rest capture in match map patterns (#335) — the same
leftover-keys-into-a-dict capability list patterns already have via
`[a, ...rest]` (`{a, ...rest} => ...`), closing the last
flat-list-vs-flat-map gap — and `is_catalan` (#336) — the one `nth_*`
builtin (`nth_catalan`) that had no matching `is_*` membership
predicate, via a bounded iterative search rather than the figurate
cluster's closed-form check since Catalan numbers have no simple
algebraic membership test — and before that `is_nonagonal` (#334) — the
sixth and final figurate-number membership test, completing the
triangular..nonagonal `is_*` cluster via the same
perfect-square-plus-modular-residue check its siblings use. Guards in
`match` arms (`n if n > 0 => ...`) were attempted (PR #314) but closed
after three straight `VERDICT: CHANGES REQUESTED` rounds, all the same
recurring bug in the bare-arrow/guard `=>` disambiguation — see
`BACKLOG.md`'s `## Graveyard` for the full postmortem and the suggested
next approach; still not requeued.

`BACKLOG.md` carries the active queue, six tasks deep, PR queue empty
going into the next cycle. Top: default values for trailing elements in
match list patterns (`[a, b = 0] => ...`), the match-pattern counterpart
to `let` list destructuring's own trailing defaults (#244), letting a
shorter subject list still match instead of falling through the arm,
scoped to bare-identifier trailing elements only (no defaults on
nested-pattern or literal elements) the same "flat-capability-first"
staging every other match-pattern extension here has used. Behind it:
`is_twin_prime`, filling a gap in the prime-relationship cluster
(`is_semiprime`/`is_sphenic`/`is_emirp`/`is_circular_prime` already test
other adjacency/structure relationships on primes, but none test the
classic twin-prime pairing — a prime with another prime exactly 2 away),
via the same local-nested-trial-division shape `is_circular_prime`
already uses rather than a shared module-level primality helper,
matching this cluster's existing convention of each predicate
reimplementing trial division inline — `nth_nonagonal`, the gap
`is_nonagonal` (#334) left behind it: every other figurate shape with a
`nth_*` closed-form has a matching `is_*` predicate and vice versa, but
nonagonal was left with only the membership test, via the same
`k(7k - 5)/2` closed form `_is_nonagonal`'s own perfect-square check
already solves for, mirroring `nth_octagonal`'s one-line shape exactly —
`nth_happy_number`, the happy-number cluster's own missing `nth_*`
counterpart, via a sequential candidate scan (`nth_prime`'s own shape)
rather than a closed form since happy numbers have none — default
values in match map patterns (`{a, b = 0} => ...`), the map-pattern
counterpart to the list-pattern defaults task, queued behind it since it
widens the same production and interpreter branch — and `nth_semiprime`,
the newest task, the semiprime pair's own missing `nth_*` counterpart
(`is_semiprime` has tested membership for a long time but never got a
value-returning sibling), via the same sequential-scan shape as
`nth_prime`/`nth_happy_number` since semiprimes have no closed form.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311), multi-value
patterns (#312), flat list patterns (#316), range patterns (#318),
negative literal patterns (#320), literal list-pattern elements (#322),
rest capture in list patterns (#324), flat map patterns (#326), nested
list patterns (#330), per-key rename in match map patterns (#332), rest
capture in match map patterns (#335), and nested patterns as map pattern
values (#337) are the follow-ups that have landed so far; default values
in match list/map patterns are queued behind them, each written to adapt
to whatever the merged code actually looks like by the time it's claimed
— see each task's own "Ordering note" where one exists. `let` list/map
destructuring has long supported trailing defaults, but match list/map
patterns never got the equivalent — both are now queued (list patterns'
defaults first, proving the shape out before map patterns' own). Guards
remain a real gap too, but are deliberately not requeued yet.

The sixteenth pass (2026-08-29) archived the two PRs merged since the
last grooming pass (#335 rest capture in match map patterns, #337 nested
patterns as map pattern values — both from this same shift) and restocked
one task — `nth_semiprime` (breadth) — bringing the queue back to its
usual 6-task ceiling at 3-breadth/3-depth parity (`is_twin_prime`,
`nth_nonagonal`, `nth_happy_number`, `nth_semiprime` are breadth;
list-pattern defaults and map-pattern defaults are depth). `main` is
green (3761 tests, 28 subtests), PR queue empty. This pass also refreshed
this section and `README.md`'s "Status & roadmap", which had gone stale
after #337 landed without a docs update (left to the Architect by design
— see each landed task's own "Once merged" note). **The next grooming
pass should let the queue drain before restocking further**, picking
whichever kind keeps breadth/depth parity — alternation is the default
rhythm, not a hard rule.

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
