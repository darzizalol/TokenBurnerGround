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

This section stayed a rolling per-pass narration (twentieth through
twenty-sixth passes) for long enough to repeat the exact growth pattern
the old "Roadmap" section hit before its 2026-08-22 trim — see the
History entry below for that precedent. Trimmed the same way here on
2026-08-30 (twenty-seventh pass): the full pass-by-pass story is not
lost, it is exactly what `CHANGELOG.md` (merge order) and this file's
own git history already preserve; this section only needs to state
where things stand right now.

Recently landed (see `CHANGELOG.md` for the full list, newest first):
`as` binding on a nested list/map sub-pattern inside `match` (#407, `[a,
[b, c] as inner]` — extended the same tuple-shape/`env.define` machinery
`_match_list_pattern_entry`/`_match_map_pattern_entry` already use for
whole-pattern `as` down into individual list/map pattern elements, no
new AST node needed); whole-value `as` binding extended to literal and
range `match` patterns (#405, `match (5) { 1..10 as whole => whole, _ =>
nil }` — reused `_match_whole_binding` unchanged, the fix was purely
adding the same optional-`as`-parse call already used on list/map
patterns to the literal/range arm branches too); `nth_smith_number`
(#406, the value-returning sibling `is_smith_number` was missing — a
bounded sequential scan with the digit-sum-equals-own-prime-factor-
digit-sum check inlined from `is_smith_number`'s own body, identical
shape to `nth_refactorable`/`nth_sphenic`). Guards in `match` arms (`n
if n > 0 => ...`) were attempted (PR #314) but closed after three
straight `VERDICT: CHANGES REQUESTED` rounds, all the same recurring bug
in the bare-arrow/guard `=>` disambiguation — see `BACKLOG.md`'s
`## Graveyard` for the full postmortem and the suggested next approach;
still not requeued.

`BACKLOG.md` dropped to its 5-task floor after Release archived #407's
now-merged task and renumbered the rest down to 1-5 (see
`NIGHTLOG.md`'s "Fifth cycle" entry, 2026-09-06). This pass restocked it
back to six with a new breadth task, `nth_polydivisible` (the
value-returning sibling `is_polydivisible` was missing, same gap
`nth_smith_number`/`nth_carmichael_number`/`nth_twin_prime`/
`nth_self_number`/`nth_emirp` already close). Before settling on it,
this pass timed several other `is_*`-without-`nth_*` candidates through
the interpreter and rejected the slow ones: `is_automorphic` hung
outright scanning up from `1` (automorphic numbers grow by roughly a
decimal digit each term — `9376`, `90625`, `890625`, ... — so a
by-`1` scan for even the 15th term never finishes), `is_disarium` and
`is_keith_number` both timed out at 30s reaching their 50th term. Kept
as viable but not chosen this pass: `is_trimorphic_number` (50th term
`218751`, ~1.5s) and `is_vampire_number` (50th term `163944`, ~3.2s) —
either is a fine pick for a future breadth task if `nth_polydivisible`
turns out to need bouncing. `is_polydivisible` itself reaches its 50th
term (`88`) in well under a second since single-digit numbers are all
trivially polydivisible and the density stays high, so it was the one
to add — it shares `nth_self_number`'s own position-1-maps-to-
candidate-0 quirk since `0` (a single "digit") is trivially
polydivisible too. This pass also repeated a quick depth-gap probe
(bitwise operators, `try`/`catch`/`finally`, ternary chaining, keyword
call arguments, `do`/`while` loops — all already implemented and
working) and found nothing new, so alternation stays breadth-heavy for
now: breadth/depth/breadth/depth/breadth/breadth/breadth. Next grooming
pass should either find a genuine depth gap the studio hasn't already
closed, or keep leaning breadth given how thin the remaining depth gaps
have become.

`main` is green (4558 tests passing locally as of #407), PR queue empty
going into this grooming pass. `BACKLOG.md` is at its 6-task floor:
`nth_carmichael_number`, chained `if` filter clauses in comprehensions,
`nth_twin_prime`, `nth_self_number`, `nth_emirp`, `nth_polydivisible`.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311), multi-value
patterns (#312), flat list patterns (#316), range patterns (#318),
negative literal patterns (#320), literal list-pattern elements (#322),
rest capture in list patterns (#324), flat map patterns (#326), nested
list patterns (#330), per-key rename in match map patterns (#332), rest
capture in match map patterns (#335), nested patterns as map pattern
values (#337), default values for trailing elements in match list
patterns (#338), default values in match map patterns (#342),
whole-value `as` binding (#348), `as` binding extended to literal/range
patterns (#405), and `as` binding on a nested list/map sub-pattern
(#407) are the follow-ups that have landed so far. Guards remain a real
gap too, but are deliberately not requeued yet — see the graveyard
postmortem above.

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
