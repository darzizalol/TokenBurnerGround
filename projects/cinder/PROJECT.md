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

Recently landed (see `CHANGELOG.md` for the full list): flat list
patterns in `match` arms (#316) — `[a, b] => a + b` tests a list
subject's shape and destructures it in one step, falling through (not
raising) on a non-list subject or a length mismatch — and before that
`nth_catalan` (#315) — the k-th Catalan number by position, a thin
composition of `binomial` (`C(k) = binomial(2k, k) / (k + 1)`) — and
before that `nth_triangular` (#313) — the "which position" question for
triangular numbers, answered by an exact closed form (`n(n+1)/2`) rather
than an iterated recurrence, the value-returning sibling of
`is_triangular`'s membership test — and before that multi-value literal
patterns in `match` arms (#312) and bound-identifier patterns (#311).
Guards in `match` arms (`n if n > 0 => ...`) were attempted (PR #314) but
closed after three straight `VERDICT: CHANGES REQUESTED` rounds, all the
same recurring bug in the bare-arrow/guard `=>` disambiguation — see
`BACKLOG.md`'s `## Graveyard` for the full postmortem and the suggested
next approach; still not requeued (see the restock note below). Both
`README.md` and this section were out of date relative to `main` at the
start of this grooming pass — #315 and #316 had merged but were still
listed as "coming up next" in prose written before they landed, and
`BACKLOG.md`'s range-patterns task still described `MatchArm` as if
`list_pattern` (added by #316) didn't exist yet, which would have
regressed flat list patterns had it been implemented as originally
written. Both are fixed as of this pass.

`BACKLOG.md` carries the active queue, 3-breadth/3-depth at the 6-task
ceiling: `cartesian_product` — every ordered combination of one element
from each of N lists, the collection-side analogue to `binomial`/
`nth_catalan`'s combinatorics-side counting — range patterns in `match`
arms (`1..10 => "small"`), `nth_pentagonal` — the k-th pentagonal number
by position, the same closed-form pattern as `nth_triangular` applied to
the next figurate-number cluster member — negative literal patterns in
`match` arms (`-5 => "neg"`), `power_set` — every subset of a list, the
enumerate-vs-count sibling of `binomial`'s counting question and the
single-list analogue to `cartesian_product`'s N-list combination — and
literal elements in list patterns (`[0, b] => ...`), the natural next
step now that flat list patterns have landed and proven the form out.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311),
multi-value patterns (#312), and flat list patterns (#316) are the
follow-ups that have landed so far; range patterns, negative literal
patterns, and literal list-pattern elements are queued behind them, each
written to adapt to whatever the merged code actually looks like by the
time it's claimed, since these tasks can land in either order relative
to their siblings — see each task's own "Ordering note." Range patterns
are scoped to `INT`-only bounds, no step, and inherit (do not fix) the
pre-existing gap that no match pattern of any kind accepts a negative
literal yet — negative literal patterns close exactly that gap, but only
for plain literal patterns, not range-pattern bounds (`-10..0` stays out
of scope for range patterns specifically). Literal list-pattern elements
are scoped to bare literals only, no nesting, no rest capture — nested
list patterns and rest capture both remain real gaps for a future
grooming pass, blocked on this task proving the literal-element form out
first, the same staged approach the `nth_*`/`is_*` figurate-number
cluster used. Guards remain a real gap too, but are deliberately *not*
requeued this pass — see the restock note below.

This grooming pass restocked two tasks — `power_set` (breadth) and
literal elements in list patterns (depth) — because two tasks landed
since the last grooming pass (`nth_catalan`, breadth, and flat list
patterns, depth) without a grooming pass restocking in between, dropping
the queue from 6 to 4 (2-breadth/2-depth: `cartesian_product`,
`nth_pentagonal` vs. range patterns, negative literal patterns). Adding
one of each kind restores the queue to its 6-task ceiling at exact
3-breadth/3-depth parity, continuing the established alternation.
Deliberately **not** re-queuing guards itself this pass: its postmortem
(`BACKLOG.md`'s `## Graveyard`) identifies a real fix but a structurally
different one from what was tried three times (lookahead at the `=>`
site instead of a suppression-depth counter threaded through every
bracket-opening production) — re-queuing it cold, written the same way
the failed attempt was, risks a fourth failed round for no better odds.
**Guards should be requeued in a future grooming pass**, but only once
someone has actually sketched the lookahead-based redesign the
postmortem suggests — until then it stays in the graveyard, not silently
forgotten. **The next grooming pass should restock with whichever kind
keeps 3-breadth/3-depth parity** given whatever lands between now and
then — alternation is the default rhythm, not a hard rule.

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
