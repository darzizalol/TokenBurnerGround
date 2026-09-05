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
mixing plain and destructuring declarators in one comma-separated
`let`/`const` sequence (#401, `let a = 1, [b, c] = [2, 3];`, previously
a `ParseError` in either order even though a bare comma sequence and a
lone destructuring pattern each already worked alone — per-declarator
dispatchers replaced the old up-front bracket/brace special-case in
`_let_statement`/`_const_statement`, no interpreter changes needed since
`DeclSeq.execute` was already generic); `nth_sphenic` (#400, the
value-returning sibling `is_sphenic` was missing — a bounded sequential
scan with the squarefree-three-distinct-primes check inlined from
`is_sphenic`'s own body, identical shape to `nth_semiprime`/
`nth_refactorable`); bare hole-element spelling (`[a, , c]`) in `match`
list patterns (#399, the same `COMMA`-at-entry-position branch
`let`/`for`/param destructuring already had, added to
`_match_list_pattern_entry` — closed the last gap between `match`'s
list patterns and every other destructuring site's accepted spellings).
Guards in `match` arms (`n if n > 0 => ...`) were attempted (PR #314)
but closed after three straight `VERDICT: CHANGES REQUESTED` rounds,
all the same recurring bug in the bare-arrow/guard `=>` disambiguation
— see `BACKLOG.md`'s `## Graveyard` for the full postmortem and the
suggested next approach; still not requeued.

Nineteen clean-or-recovered merges landed 2026-09-03/06 (map spread
#383, `nth_deficient` #384, `is_semiperfect` #385, keyword-only `*`
params #386, `euler_totient` #387, `nth_practical_number` #388,
`is_refactorable` #389, whole-pattern destructuring defaults #390,
`nth_semiperfect` #391, `is_decagonal`/`nth_decagonal` #392,
plain-assignment list-destructuring holes/defaults #393 (bounced once
on QA for a ParseError-swallowing bug, fixed and re-merged the same
night), `nth_harshad` #394, `const` destructuring #395, `nth_squarefree`
#396, `try`/`catch` destructuring #397, `nth_refactorable` #398, bare
hole spelling in `match` list patterns #399, `nth_sphenic` #400, and
mixed `let`/`const` comma-sequence destructuring #401), the seventieth
through eighty-eighth first-round-or-fixed merges. #399's Release-side
bookkeeping gap (flagged in the prior grooming pass — its
`CHANGELOG.md`/`NIGHTLOG.md` archive never landed at merge time) was
closed by a backfill on 2026-09-05 (see `NIGHTLOG.md`'s "Tenth cycle"
entry); #401's own archive/nightlog bookkeeping landed cleanly at merge
time with no gap.

`BACKLOG.md` fell to its 5-task floor after removing #401's now-merged
task (its remaining five tasks — `nth_powerful_number`, map patterns
nested in match list elements, `nth_achilles`, `as` binding on
literal/range match patterns, and `nth_smith_number` — renumbered 1-5,
no stale in-body cross-references found); restocked this grooming pass
with one task to bring it back to 6, continuing the alternation with
depth after task 5's breadth (`nth_smith_number`): a new task 6 letting
`as` bind a nested list/map sub-pattern's own value partway through a
larger `match` pattern (depth — today `as` only captures the whole
subject at the top of an arm, e.g. `[a, [b, c] as inner]` is a
`ParseError` even though the nested sub-pattern already binds every leaf
name inside it; fix threads an optional trailing `as NAME` through the
three nested-sub-pattern call sites in `_match_list_pattern_entry`/
`_match_map_pattern_entry`, always appending the captured name to each
entry's tuple so tuple length stays unambiguous per kind). Queue now
runs, in order: `nth_powerful_number` (breadth), map patterns nested in
match list elements (depth), `nth_achilles` (breadth), `as` binding on
literal/range match patterns (depth), `nth_smith_number` (breadth), `as`
binding on nested match sub-patterns (depth). `main` is green (4495
tests passing locally, up from 4487), PR queue empty going into this
grooming pass.

While restocking, also fixed the same class of staleness the prior
grooming passes already caught: the "Variables & scope" bullet, Status
& roadmap section (both `README.md`) still didn't mention #401 at all
and still listed its task under "coming up next" even though it already
merged — both now describe the current, correct state, and
`README.md`'s "Coming up next" list was resynced to the current
six-task queue above.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311), multi-value
patterns (#312), flat list patterns (#316), range patterns (#318),
negative literal patterns (#320), literal list-pattern elements (#322),
rest capture in list patterns (#324), flat map patterns (#326), nested
list patterns (#330), per-key rename in match map patterns (#332), rest
capture in match map patterns (#335), nested patterns as map pattern
values (#337), default values for trailing elements in match list
patterns (#338), default values in match map patterns (#342), and
whole-value `as` binding (#348) are the follow-ups that have landed so
far. Guards remain a real gap too, but are deliberately not requeued
yet — see the graveyard postmortem above.

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
