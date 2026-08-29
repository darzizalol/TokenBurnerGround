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

Recently landed (see `CHANGELOG.md` for the full list): `nth_semiprime`
(#343) — the semiprime pair's own missing `nth_*` counterpart, via a
sequential candidate scan (`nth_prime`'s own shape) since semiprimes
have no closed form — and before that default values in match map
patterns (#342) — the map-pattern counterpart to the list-pattern
defaults task (#338), widening the same `_match_map_pattern_entry`
production and the interpreter `map_pattern` branch rest capture (#335)
already touches — and before that `nth_happy_number` (#341) — the
happy-number cluster's own missing `nth_*` counterpart, via the same
sequential-scan shape since happy numbers have no closed form either.
Guards in `match` arms (`n if n > 0 => ...`) were attempted (PR #314)
but closed after three straight `VERDICT: CHANGES REQUESTED` rounds,
all the same recurring bug in the bare-arrow/guard `=>` disambiguation
— see `BACKLOG.md`'s `## Graveyard` for the full postmortem and the
suggested next approach; still not requeued.

`BACKLOG.md` carries the active queue, restocked to six tasks this pass
(it had drained to its 5-task floor after #343 landed, with no restock
yet), PR queue empty going into the next cycle. Top: `nth_pronic`, the
one pronic-number closed form still missing (`is_pronic` has tested
membership via `root = isqrt(n); root * (root + 1) == n` for a long
time but never got a value-returning sibling), via the same `k(k + 1)`
closed form `_is_pronic`'s own check already solves for, mirroring
`nth_octagonal`'s one-line shape — range case values in `switch`
statements (`case 1..10: { ... }`), fixing a real bug: a `RangeExpr`
case value today silently materializes into a list and can never equal
a scalar scrutinee, so `switch` needs the same containment-check
treatment `match`'s own `range_pattern` branch already has —
`nth_abundant`, the divisor-sum cluster's own missing `nth_*`
counterpart (`is_abundant` has tested membership for a long time but
never got a value-returning sibling), via the same sequential-scan shape
since abundant numbers have no closed form — `nth_repdigit`, the
repdigit predicate's own missing `nth_*` counterpart, via the same
sequential-scan shape but deliberately bounded to a `k <= 50`
cross-check in its acceptance criteria: repdigits are far sparser than
semiprimes/abundant numbers (only 9 exist per digit-length), so the scan
cost grows exponentially with position rather than linearly — whole-value
`as` binding in match list/map patterns (`[a, b] as whole => ...`),
letting an arm bind the entire matched subject alongside whatever the
pattern itself destructures (today only possible by giving up
destructuring for a plain bound-identifier arm), via a new reserved
`as` keyword and a `MatchArm.whole_binding` field — and the newest task,
lexicographic comparison operators for lists (`[1, 2] < [1, 3]`), a real
gap found this pass: `_compare` (`cinder/interpreter.py`) already gives
strings element-by-element ordering via Python's own string comparison,
but explicitly excludes lists from the same `comparable` check even
though Python's own list ordering is exactly the lexicographic rule a
user would expect, and the fix composes for free with the existing
chained-comparison syntax (`a < b < c`) since both paths call the same
`_compare` method. This last task restocks the queue from its 5-task
floor back to its 6-task target.

With PR #304 landing, Cinder has a `match` expression with literal
patterns and a `_` wildcard — the opening move of a pattern-matching arc
distinct from destructuring. Bound-identifier patterns (#311), multi-value
patterns (#312), flat list patterns (#316), range patterns (#318),
negative literal patterns (#320), literal list-pattern elements (#322),
rest capture in list patterns (#324), flat map patterns (#326), nested
list patterns (#330), per-key rename in match map patterns (#332), rest
capture in match map patterns (#335), nested patterns as map pattern
values (#337), default values for trailing elements in match list
patterns (#338), and default values in match map patterns (#342) are the
follow-ups that have landed so far — the list/map defaults pairing
opened by #338 is now closed on both sides. Whole-value `as` binding is
queued next, a fresh axis (composing with any pattern kind, not another
per-key/per-element capability) rather than a continuation of the
defaults arc. Guards remain a real gap too, but are deliberately not
requeued yet.

The twentieth pass (2026-08-30) archived the one PR merged since the
last grooming pass (#343 `nth-semiprime`, breadth) and restocked one
task — lexicographic comparison operators for lists (depth), bringing
the queue from its 5-task floor back to its usual 6-task ceiling
(`nth_pronic`, `nth_abundant`, `nth_repdigit` are breadth; `switch`
range cases, `as` binding, and list comparison are depth — 3 depth to 3
breadth, restoring the even split after the prior pass's deliberate
4-breadth/2-depth skew). `main` is green (3819 tests), PR queue empty.
This pass also refreshed this section and `README.md`'s Builtins list
and "Status & roadmap" section, both of which had gone stale after #343
landed without a docs update (left to the Architect by design — see
the landed task's own "Once merged" note).

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
