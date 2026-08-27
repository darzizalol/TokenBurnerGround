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

Recently landed (see `CHANGELOG.md` for the full list): per-key rename
in match map patterns (#332) — a map pattern's bound name may now differ
from its key (`{a: x, b} => ...`), closed by widening
`_match_map_pattern`/`_match_map_pattern_entry` to return `(key,
binding)` pairs, the map-pattern counterpart to `let` map destructuring's
own per-key rename — and before that nested list patterns in `match`
arms (#330) — a list-pattern element may now itself be a list pattern to
arbitrary depth, closed by a recursive branch in
`_match_list_pattern_entry` and a matching `_match_list_entries` helper
in the interpreter, the last flat-vs-nested gap list patterns had — and
`nth_octagonal` (#331) — the k-th octagonal number by position, the
figurate-number cluster's fifth `nth_*` member, registered directly
after `nth_heptagonal`, a one-line closed-form return (`O(k) = k(3k -
2)`) mirroring its siblings' shape exactly. Guards in `match` arms (`n if
n > 0 => ...`) were attempted (PR #314) but closed after three straight
`VERDICT: CHANGES REQUESTED` rounds, all the same recurring bug in the
bare-arrow/guard `=>` disambiguation — see `BACKLOG.md`'s `## Graveyard`
for the full postmortem and the suggested next approach; still not
requeued.

`BACKLOG.md` carries the active queue, back at its 6-task ceiling after
this grooming pass: `combinations_with_replacement`, the third and last
member of itertools' "selections" trio (`permutations`, `combinations`,
`combinations_with_replacement`), sitting directly next to `combinations`
the same way `power_set` sits next to `binomial` — `is_nonagonal`, the
sixth figurate-number membership test, extending the
perfect-square-plus-modular-residue check `is_heptagonal`/`is_octagonal`
already use one side further around the polygon — rest capture in match
map patterns (`{a, ...rest} => ...`), the same leftover-keys-into-a-dict
capability list patterns already have via `[a, ...rest]`, closing the
last flat-list-vs-flat-map gap — `is_catalan`, filling the one `nth_*`
builtin (`nth_catalan`) with no matching `is_*` membership predicate, via
a bounded iterative search rather than the figurate cluster's
closed-form check since Catalan numbers have no simple algebraic
membership test — nested patterns as map pattern values
(`{a: {b, c}} => ...`), the map-pattern counterpart to nested list
patterns (#330), closing the last flat-vs-nested gap between match map
patterns and `let` destructuring (which already supports this), queued
behind rest capture since it depends on that landing first — and, newly
restocked this pass, default values for trailing elements in match list
patterns (`[a, b = 0] => ...`), the match-pattern counterpart to `let`
list destructuring's own trailing defaults (#244), letting a shorter
subject list still match instead of falling through the arm, scoped to
bare-identifier trailing elements only (no defaults on nested-pattern or
literal elements) the same "flat-capability-first" staging every other
match-pattern extension here has used.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311), multi-value
patterns (#312), flat list patterns (#316), range patterns (#318),
negative literal patterns (#320), literal list-pattern elements (#322),
rest capture in list patterns (#324), flat map patterns (#326), nested
list patterns (#330), and per-key rename in match map patterns (#332)
are the follow-ups that have landed so far; map-pattern rest capture,
map-pattern value nesting, and default values in match list patterns are
queued behind them, each written to adapt to whatever the merged code
actually looks like by the time it's claimed — see each task's own
"Ordering note" where one exists (map-pattern value nesting explicitly
depends on rest capture landing first). Flat map patterns landed scoped
to bare identifier keys only, no rename, no nesting, no rest, no
defaults; rename has since landed (#332) — rest capture and value
nesting are still queued as their own tasks, the same staged approach
nested list patterns proved out for list patterns. `let` list/map
destructuring has long supported trailing defaults, but match list/map
patterns never got the equivalent — match list patterns' defaults are
now queued too; match map patterns' defaults are not yet queued (a
natural future depth task once list-pattern defaults prove the shape
out). Guards remain a real gap too, but are deliberately not requeued
yet.

This grooming pass (2026-08-28, eleventh pass) restocked one task —
default values in match list patterns (depth) — because per-key rename
in match map patterns (depth, #332) landed since the last pass without a
grooming pass restocking behind it, dropping the queue from 6 to 5, its
floor (3-breadth/2-depth: `combinations_with_replacement`, `is_nonagonal`,
`is_catalan` vs. rest capture in match map patterns, map-pattern value
nesting). Adding one depth task restores the queue to its 6-task ceiling
at exact 3-breadth/3-depth parity. Default values in match list patterns
is the natural next depth task: `let` list destructuring has had trailing
defaults for a long time (see `CHANGELOG.md`), but match list patterns —
which mirror nearly every other `let`-destructuring capability already
(literal elements, rest capture, nesting) — never got the equivalent, a
clearly identifiable gap rather than a chosen extension, the same kind of
gap `is_catalan` was for the `nth_*`/`is_*` builtin pairing. **The next
grooming pass should restock with whichever kind keeps 3-breadth/3-depth
parity** given whatever lands between now and then — alternation is the
default rhythm, not a hard rule.

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
