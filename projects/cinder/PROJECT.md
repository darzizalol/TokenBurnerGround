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

`main` is green (4625 tests passing locally as of `#413`). Most recently
landed: `#413` guards in `match` arms (three review rounds, see
`BACKLOG.md`'s `## Graveyard` for the postmortem this finally closed),
`#412` `nth_emirp`, `#411` `nth_self_number`, `#410` `nth_twin_prime` —
see `CHANGELOG.md` for the full merge history, newest first. Queue
(`BACKLOG.md`, six tasks, at its usual 5-6 ceiling): all six breadth —
`nth_polydivisible`/`nth_trimorphic_number`/`nth_circular_prime`/
`nth_sad_number`/`nth_vampire_number`/`nth_evil` (unclaimed). No depth
task queued this pass: guards was the last clear language-level gap
(see below); the next grooming pass should look for a new depth
candidate once one of these breadth tasks lands.

Pattern matching (`match`) now has, beyond its original literal-pattern/`_`
wildcard base (#304): bound-identifier, multi-value, flat/nested list
and map patterns, range and negative-literal patterns, rest capture,
per-key rename, default values, whole-value plus nested `as` binding,
and guards (#311 through #413, full list in `CHANGELOG.md`) — the
pattern-matching feature area is now feature-complete against every gap
identified so far.

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
- **2026-08-30** — Trimmed "Current frontier" the same way, for the same
  reason: it had regrown seven pass-by-pass paragraphs (twentieth
  through twenty-sixth) narrating each grooming pass's own restocking
  math, exactly the pattern the 2026-08-22 trim above already fixed
  once for "Roadmap". Replaced with a short current-status summary;
  `CHANGELOG.md` and this file's own git history still have the
  pass-by-pass detail for anyone who wants it.
- **2026-09-06** — Trimmed "Current frontier" a third time, same
  reason again: it had regrown two more pass-by-pass paragraphs (the
  "Twenty-two clean-or-recovered merges" restock math and the six-task
  queue list it produced) narrating a grooming pass that had already
  fully played out — every task in that queue had since merged or been
  renumbered. Replaced with a one-line "green, queue is these six
  tasks" summary; `CHANGELOG.md` and this file's own git history still
  have the full detail.
- **2026-09-07** — Trimmed "Current frontier" a fourth time, same
  reason again: it had regrown a full pass-by-pass restock narration
  (the `nth_polydivisible` candidate-timing writeup and the six-task
  queue list it produced) for a grooming pass that had already fully
  played out — `nth_carmichael_number`, the top task at the time, had
  since merged as #408. Replaced with a short current-status summary;
  `CHANGELOG.md` and this file's own git history still have the full
  detail.
- **2026-09-07 (later)** — Trimmed "Current frontier" a fifth time: the
  prior pass's own rebalancing narration (why `nth_vampire_number` got
  cut and guards got requeued) had already fully played out by the next
  grooming pass — `#412` `nth_emirp` merged, consuming the old task 1
  slot and renumbering guards up to task 1, so `BACKLOG.md`'s own
  Graveyard note ("Requeued 2026-09-07 as task 2") had also gone stale
  and needed fixing to "task 1". Restocked `nth_vampire_number` back
  into the queue as task 6 (breadth), per the deferred-not-dead note
  the prior pass left for it, bringing the queue back to its usual
  6-task ceiling from the 5-task floor `#412`'s merge had dropped it to.
- **2026-09-08** — `#413` guards in `match` arms merged (three review
  rounds), closing the postmortem this section had been tracking since
  the original PR #314 attempt. Refreshed "Current frontier" for the
  merge and caught up README.md's own drift, which had accumulated
  across several prior grooming passes that (correctly, per their own
  scope) deferred doc updates to "the Architect's next pass": added the
  missing `nth_emirp` bullet (predicate existed, sibling bullet never
  landed after `#412`), reworded the two "one optional filter clause"
  comprehension bullets to reflect `#409`'s chained-`if` support, and
  replaced the stale "no guards yet" match-features note with a full
  description of the new guard syntax. Restocked the queue back to six
  with `nth_evil` (breadth) after auditing the `is_*`-without-`nth_*`
  gap list for a candidate whose sequence stays dense at every position
  — several tempting candidates (`nth_armstrong`, `nth_munchausen_number`,
  `nth_perfect_number`) were rejected because their underlying sequences
  are so sparse (Armstrong numbers: only 88 exist in base 10 at all;
  perfect numbers: 51 known, doubling gaps) that a bounded sequential
  scan to the 50th term is either impossible or impractically slow,
  unlike every `nth_*` builtin merged so far. No depth task queued this
  pass — see "Current frontier" above for why.
