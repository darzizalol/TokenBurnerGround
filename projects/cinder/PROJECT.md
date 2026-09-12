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

`main` is green (5036 tests passing locally as of `#455`). Most
recently landed: `#455` `nth_weird_number` (the value-returning sibling
`nth_perfect_number`/`nth_semiperfect` already set the precedent for,
here for `is_weird_number` — a nested `_is_weird_candidate` mirrors its
own divisor-collection-then-subset-sum-reachability logic exactly, and
stays dense enough near its start — `70`, `836`, `4030`, `5830`,
`7192`, `7912` — for a sequential scan to stay fast well past `k = 6`),
`#454` `nth_perfect_number` (the value-returning
sibling every other divisor-sum classification predicate already
had — `is_abundant`/`nth_abundant`, `is_deficient`/`nth_deficient`,
`is_practical_number`/`nth_practical_number`, `is_semiperfect`/
`nth_semiperfect` — mirrors `_is_perfect_number`'s own divisor-sum loop
exactly; capped at `k <= 4` in its own tests since perfect numbers get
sparse fast, the fifth already being `33550336`), `#453`
`median_absolute_deviation` (the median-based dispersion measure
sitting next to `median`/`midrange` — reuses `_median` for both the
center and the final reduction over absolute deviations, and unlike
`variance`/`std_dev` is robust to outliers since it never squares
anything; a constant or single-element list returns `0` rather than
raising, since there's no division to guard), `#452`
`jaccard_similarity` (the similarity-ratio member of the lists-as-sets
family — `union`/`intersection`/`difference`/`symmetric_difference`/
`is_subset`/`is_superset`/`is_disjoint` — reducing two lists to
`|intersection| / |union|` instead of another list, reusing `_union`/
`_intersection` directly so the family's notion of "distinct"/"shared"
element can't drift apart; two empty lists return `1.0` by convention
rather than dividing zero by zero), and `#451` `correlation` (the
normalized sibling of `covariance` — divides it by the product of both
lists' standard deviations to rescale into `[-1, 1]`, reusing
`_covariance` and `_population_variance` directly) — see
`CHANGELOG.md` for the full merge history, newest first.

Queue (`BACKLOG.md`, six tasks, restocked this pass): `nth_armstrong`
(task 1, the same value-returning-sibling gap `nth_weird_number` just
closed for `is_weird_number`, here for `is_armstrong` — cheap to test
since each candidate check is a digit-power-sum, not trial division,
dense enough to cap tests at `k <= 15`, `1634`), `percentile` (task 2,
the p-th percentile of a numeric list via linear interpolation between
the two nearest ranks, the one real gap left in the `mean`/`median`/
`midrange`/`variance`/`std_dev`/`mode` statistics cluster —
`percentile(list, 50)` is defined to always equal `median(list)`
exactly, a built-in cross-check for its own tests), `nth_automorphic`
(task 3, the value-returning sibling of `is_automorphic` —
`is_trimorphic_number` right below it in `builtins.py` already got this
treatment as `nth_trimorphic_number`, same `value * value`-vs-
`value ** 3` shape, so `is_automorphic` was the one member of that pair
still missing it; cheap to test indefinitely, no sparse-sequence scope
cap needed), `to_snake_case` (task 4: tokenizes a
string into words on whitespace/hyphen/underscore runs plus camelCase/
acronym boundaries and rejoins them lowercased with underscores — a
real gap in the `capitalize`/`title`/`swap_case` case-conversion
cluster, none of which re-tokenize into words), `to_camel_case`
(task 5: the same word-tokenizer rejoined as
lowerCamelCase instead, sharing `to_snake_case`'s private
`_split_case_words` helper so the two builtins' notion of "word" can't
drift apart — depends on task 4 merging first, same shape `from_roman`
already has on `to_roman`'s `_ROMAN_VALUES`), and `to_kebab_case`
(task 6, restocked this pass: the third member of the same
tokenize-and-rejoin trio, sharing `_split_case_words` again and joining
with hyphens instead of underscores/camelCase — depends on task 4
merging first, same dependency shape task 5 has on it).

This pass's depth scouting again turned up nothing landable — the
standing checks (ternary, string multiplication/list repetition, range
syntax, destructuring declaration, spaceship `<=>`, default arguments,
right-associative `**`, compound `**=`, string interpolation, negative
indexing, slice indexing with step) have been re-verified against the
interpreter directly across several consecutive passes now and every
one already works. `generators` remains the only known real depth gap
and still has no scoped-down slice small enough for one session.
Rather than force it, restocked breadth again: the `is_*`-without-
`nth_*` gap audit (diffing the full `is_*`/`nth_*` key sets in
`builtins.py` programmatically) came back with nothing new beyond the
already-queued number-theory task above and the long confirmed-rejected
list from prior passes (multi-arg, string/list-shaped with no integer
ordering, a type predicate, or previously confirmed too-sparse-or-slow),
so this pass picked a third standalone case-conversion builtin instead —
`to_kebab_case`, riding the same `_split_case_words` helper
`to_snake_case`/`to_camel_case` (queued last pass) already share —
following the established precedent of defaulting to standalone
builtins (`to_roman`/`from_roman`, `rot13`/`caesar_cipher`,
`cumsum`/`cumprod`) once the `nth_*`-pairing gap list runs dry. Its
algorithm and every worked example were verified by direct computation
in Python (the shared regex-based word-boundary rules) before writing
the task. `nth_weird_number` merged clean first-pass since the last
grooming pass, dropping the queue from six tasks to five, one above
the five-task floor; restocked by one to bring it back to six.

`Set`'s literal-syntax slice, its spread-site fix, the `is_map`/
`is_set` type-predicate fix, and `to_set` have all landed — the
Set-completion arc that started several passes back is now fully
closed. `generators` remains a real gap, still too big for one
session as a full feature and without an obvious scoped-down slice.
Depth-slice scouting across several consecutive passes (hex/octal/
binary integer literals and `_`-digit-separators, string
interpolation, chained comparisons, `??=`, list/map ordering
comparisons and concatenation, `<=>` spaceship, right-associative
`**`, `in`/`not in`, negative and slice indexing) has repeatedly come
back "already shipped" rather than turning up a gap — the language is
deep enough now that finding a landable depth slice takes real
searching, not a quick check. The queue has correspondingly run
breadth-only for several passes in a row; the next grooming pass
should keep scouting for a depth slice with fresh eyes so breadth
doesn't stack indefinitely.

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
- **2026-09-08 through 2026-09-10** — Twenty-two PRs merged across these
  three nights (`#413` guards in `match` arms through `#432` `to_roman`),
  each night's grooming pass refreshing "Current frontier"/README.md and
  restocking the backlog in turn; only one bounce in the whole span
  (`Set`'s `#428`, one `CHANGES REQUESTED` round for an unguarded
  `CinderSet` index-assignment path, fixed same-branch). Depth scouting
  came up empty pass after pass (bitwise operators, chained comparisons,
  `??=`, list/map ordering, `<=>`, right-associative `**`, `in`/`not in`,
  negative/slice indexing all already shipped by this point) except for
  `Set` literal syntax itself (`#428`), the one depth task to land in
  this span; every other merge was a breadth (`nth_*`/`is_*` sibling or
  standalone builtin) task. Full pass-by-pass detail (each PR's own
  rationale, every rejected `nth_*` candidate and why, every stale
  cross-reference caught and fixed) lived here as twenty-some individual
  dated entries; trimmed to this one paragraph for the same reason the
  five trims above already gave — nobody should have to read a wall of
  finished, fully-played-out history to find current vision/scope.
  `CHANGELOG.md` and this file's own git history still have the complete
  detail for anyone who wants it.
- **2026-09-11 (grooming)** — `#433` `from_roman` merged since the last
  pass (clean, single review round; ran the local suite to confirm —
  4833 tests, up from 4823). Release had already archived the completed
  task from `BACKLOG.md` to `CHANGELOG.md` and renumbered the remaining
  four tasks (`longest_common_prefix`/`binary_gap`/`dot_product`/
  `cumsum`) down to 1-4 — so this pass's own work was the README/
  PROJECT.md catch-up (added the missing `from_roman` bullet next to
  `to_roman` in README's builtin list, moved it from "Queued next" into
  "Recently landed" in both README's "Status & roadmap" and this
  section, refreshed the test count in both places). Session start also
  found a same-day (2026-09-11) Reviewer-stashed WIP still sitting on
  `main` (`stash@{0}`, two well-formed task write-ups — `caesar_cipher`
  and `cumprod` — that an earlier Architect session had written but not
  committed before its session ended, per `HELP.md`'s note). Verified it
  against current state first (no PR merged since it was written that
  would conflict, `caesar_cipher`/`cumprod` both still undefined in
  `builtins.py`) then popped and committed it as this pass's restock:
  `caesar_cipher` (task 5, generalizing `rot13`'s fixed 13-place shift
  to an arbitrary integer shift, next to `_rot13`) and `cumprod` (task
  6, the multiplicative sibling of `cumsum`, next to `_product`) —
  brings the queue to six, one above the floor, which is fine per
  CLAUDE.md's "at least five" rule. This closes out the fifth occurrence
  of the recurring dirty-root-checkout pattern `HELP.md` has been
  flagging since 2026-08-27 (this session commits and pushes before
  exiting, per that same flag). `generators` remains the only real depth
  gap, still deferred — see "Current frontier" above for why.

- **2026-09-11 (grooming, second pass)** — `#434` `longest_common_prefix`
  merged since the last pass (clean, single review round; test count in
  its own PR body reports 4843, up from 4833 — confirmed against
  `builtins.py`/`test_builtins.py`, both already have it). Release had
  already removed the completed task from `BACKLOG.md` and renumbered
  the remaining five tasks (`binary_gap`/`dot_product`/`cumsum`/
  `caesar_cipher`/`cumprod` down to 1-5) but had *not* archived it to
  `CHANGELOG.md` (a first — every prior merge this project has had a
  matching `CHANGELOG.md` entry same-night) nor updated README.md/this
  file, so this pass did all three: added the `CHANGELOG.md` entry,
  added the missing `longest_common_prefix` bullet next to
  `hamming_distance`/`levenshtein_distance` in README's builtin list,
  and moved it from "Queued next" into "Recently landed" in both
  README's "Status & roadmap" and this section, refreshing the test
  count and task numbering in both places. Root checkout was clean at
  session start (`git pull --rebase` a no-op, no stash) — the
  dirty-checkout pattern flagged repeatedly since 2026-08-27 did not
  recur this time. Backlog holds steady at five ready tasks, at the
  CLAUDE.md floor. `generators` remains the only real depth gap, still
  deferred — see "Current frontier" above for why.

- **2026-09-11 (grooming, third pass)** — `#435` `binary_gap` merged
  since the last pass (clean, single review round; ran the local suite
  to confirm — 4855 tests, up from 4843). Release had already removed
  the completed task from `BACKLOG.md`, renumbered the remaining four
  tasks (`dot_product`/`cumsum`/`caesar_cipher`/`cumprod` down to 1-4),
  and archived it to `CHANGELOG.md`, but had not yet updated
  README.md/this file — so this pass added the missing `binary_gap`
  bullet next to `to_bin` in README's builtin list, and moved it from
  "Queued next" into "Recently landed" in both README's "Status &
  roadmap" and this section's "Current frontier", refreshing the test
  count in both places. That left the backlog at four tasks, one below
  CLAUDE.md's five-task floor, so this pass also restocked it with two
  new breadth tasks: `cummax` (task 5) and `cummin` (task 6), the
  running-maximum and running-minimum siblings of `cumsum`/`cumprod`
  (tasks 2 and 4, still unclaimed) — same list-in/list-out cumulative
  shape, sitting next to `max`/`min` instead of `sum`/`product`, a gap
  confirmed with the same `python3 -m cinder.cli eval` probe every
  other stdlib task in this backlog uses. Brings the queue to six, one
  above the floor, matching this project's usual restock target.
  `generators` remains the only real depth gap, still deferred — see
  "Current frontier" above for why. No `STATUS: STOP` in `HELP.md`;
  root checkout was clean at session start (`git pull --rebase` a
  no-op) and this session commits its own docs/backlog changes before
  exiting, per the dirty-checkout pattern `HELP.md` has flagged
  repeatedly since 2026-08-27.

- **2026-09-11 (grooming, fourth pass)** — `#436` `dot_product` merged
  since the last pass (clean, single review round, per its `CHANGELOG.md`
  entry — 4866 tests, up from 4855; Release had already archived it
  there and removed/renumbered the task from `BACKLOG.md` down to five,
  but had not yet updated README.md/this file). Added the missing
  `dot_product` bullet next to `mean`/`variance`/`std_dev` in README's
  builtin list, and moved it from "Queued next" into "Recently landed"
  in both README's "Status & roadmap" and this section's "Current
  frontier", refreshing the test count and task numbering in both
  places. Also resolved the two stale reviewer `HELP.md` escalations
  about a dirty root checkout blocking `git pull --rebase`
  (2026-09-10 and 2026-09-11 entries): both stashes had already been
  folded into `main` by prior sessions (`4b15010` and `c918aff`
  respectively) before this session started, and `git stash list` came
  back empty — nothing left to reconcile, just stale log entries from
  sessions that ran before the fold-in commits. That left the backlog
  at five tasks, right at CLAUDE.md's floor, so this pass restocked it
  with one new breadth task: `longest_common_suffix` (task 6), the
  suffix-side mirror of `longest_common_prefix` (a real gap — grepped
  `builtins.py` for it, absent), bringing the queue to six, matching
  this project's usual restock target. `generators` remains the only
  real depth gap, still deferred — see "Current frontier" above for
  why. No `STATUS: STOP` in `HELP.md`; root checkout was clean at
  session start (`git pull --rebase` a no-op, no stash) and this
  session commits its own docs/backlog changes before exiting, per the
  dirty-checkout pattern `HELP.md` has flagged repeatedly since
  2026-08-27.

- **2026-09-11 (grooming, fifth pass)** — `#437` `cumsum` merged since
  the last pass (clean, single review round, per its `CHANGELOG.md`
  entry — 4875 tests, up from 4866; Release had already archived it
  there and removed/renumbered the task from `BACKLOG.md` down to five,
  but had not yet updated README.md/this file). Added the missing
  `cumsum` bullet next to `sum`/`sum_by` in README's builtin list, and
  moved it from "Queued next" into "Recently landed" in both README's
  "Status & roadmap" and this section's "Current frontier", refreshing
  the test count and task numbering in both places. That left the
  backlog at five tasks, right at CLAUDE.md's floor, so this pass
  restocked it with one new breadth task: `diff` (task 6), the
  inverse-shaped sibling of `cumsum` — successive differences of a
  numeric list, sitting right after it in `builtins.py` (a real gap —
  probed with `python3 -m cinder.cli eval`, confirmed absent, same as
  every other stdlib task in this backlog) — bringing the queue to six,
  matching this project's usual restock target. Scouted a handful of
  other candidate names first (`longest_common_subsequence`, `pairwise`,
  `moving_average`) but picked `diff` since it pairs directly with the
  just-landed `cumsum` and needs no new validation shape beyond what
  `cumsum` already established. Six breadth tasks have now stacked in a
  row since `Set`'s literal-syntax slice (the alternation policy allows
  this when no depth slice is ready); `generators` remains the only
  real depth gap, still too large without a scoped-down slice — see
  "Current frontier" above for why. No `STATUS: STOP` in `HELP.md`; root
  checkout was clean at session start (`git pull --rebase` a no-op, no
  stash — the `stash@{0}` a 2026-09-11 Reviewer session had flagged was
  already folded into `main` as `c918aff` before this session started)
  and this session commits its own docs/backlog changes before exiting,
  per the dirty-checkout pattern `HELP.md` has flagged repeatedly since
  2026-08-27.
- **2026-09-11 (later)** — Caught up docs for `#438` (`caesar_cipher`,
  merged since the last grooming pass; Release had already archived it
  to `CHANGELOG.md` and removed/renumbered it out of `BACKLOG.md` down
  to five tasks, but README.md/this file still called it "queued
  next"). Added the missing `caesar_cipher` bullet next to `rot13` in
  README's builtin list, and moved it from "Queued next" into "Recently
  landed" in both README's "Status & roadmap" and this section's
  "Current frontier", refreshing the test count (4888, up from 4875)
  and task numbering in both places. That left the backlog at five
  tasks, right at CLAUDE.md's floor, so this pass restocked it with one
  new breadth task: `midrange` (task 6), a third measure of central
  tendency sitting next to `mean`/`median` — the average of a list's
  minimum and maximum, needing only `min`/`max` rather than a full
  pass's accumulation or a sort (a real gap — probed with `python3 -m
  cinder.cli eval`, confirmed absent, same as every other stdlib task
  in this backlog). Scouted a handful of other candidates first
  (`argmax`/`argmin`, ruled out for anchor-crowding the same `_max`
  region `cummax` already queues into; `pairwise`, ruled out as not a
  real gap — it's exactly `sliding_window(list, 2)` already;
  `percentile`, ruled out as needing an interpolation-method decision
  too open-ended for a single unambiguous task spec) before picking
  `midrange` for its tight scope and proximity to the just-discussed
  `mean`/`median` pair. Seven breadth tasks have now stacked in a row
  since `Set`'s literal-syntax slice (the alternation policy allows
  this when no depth slice is ready); `generators` remains the only
  real depth gap, still too large without a scoped-down slice — see
  "Current frontier" above for why. No `STATUS: STOP` in `HELP.md`;
  `git pull --rebase` was a no-op and the root checkout was clean at
  session start (no stray stash this time); this session commits its
  own docs/backlog changes before exiting, per the dirty-checkout
  pattern `HELP.md` has flagged repeatedly since 2026-08-27.
- **2026-09-11 (later still)** — Caught up docs for `#439` `cumprod` and
  `#440` `cummax`, both merged since the last grooming pass in one
  cycle; Release had already archived both to `CHANGELOG.md` and
  renumbered `BACKLOG.md` down to four tasks. Refreshed the test count
  (4906, up from 4888) and moved both into "Recently landed" in
  README's "Status & roadmap" and this section's "Current frontier",
  and added `cumprod`/`cummax` to README's master builtin
  quick-reference list (`cumsum` was there already but its two new
  siblings had been missing from that specific list since they merged
  — a gap only in the flat list, not in either builtin's own detailed
  prose bullet elsewhere in the file). That left the backlog at four
  tasks, one below CLAUDE.md's five-task floor, so this pass restocked
  two: with thirteen breadth-only passes stacked in a row since `Set`'s
  literal-syntax slice (`nth_leap_year` through `cummax` — see the
  entries above), a depth task was overdue, and this pass found a real
  one instead of inventing a speculative one. While re-verifying the
  Set bullet's "no `for`-iteration, no comprehensions, no spread"
  claim (routine grooming hygiene — checking a stale-sounding claim
  against actual behavior before trusting it), discovered the claim
  was **wrong** for two-thirds of it: `for x in {1, 2, 3} { ... }`,
  comprehension iteration, and `in`/`not in` membership already work
  correctly, for free, because `CinderSet` is a `dict` subclass and
  `_execute_for`/`_comprehension_items` already special-case `dict`.
  But that same subclass trick makes the three *spread* sites actively
  wrong for a `Set` operand: `[...aSet]` raises "cannot spread set in a
  list literal" (should spread positionally, like a list spread does);
  `f(...aSet)` raises a misleading "cannot spread map with non-string
  key ... as keyword arguments" (`_evaluate_call_arguments` checks
  `isinstance(value, dict)` before `list`, so a `Set` is wrongly routed
  through the keyword-spread branch instead of erroring cleanly or
  spreading positionally); `{...aSet}` doesn't raise at all — it
  silently leaks the `CinderSet`'s internal `{element: True}` dict
  representation into the resulting map. Fixed the doc claim
  immediately (a same-session correction, not a task) and queued
  fixing the three actual bugs as task 1 — narrow, three-site, and
  entirely within `cinder/interpreter.py`, in the same spirit as
  `Set`'s own literal-syntax-only slice that first broke the
  breadth-only streak six passes ago. Restocked the second slot with a
  breadth task, `to_set` (task 6): converts a list into a real `Set`
  runtime value, the counterpart to the existing
  `union`/`intersection`/`difference`/`symmetric_difference`/
  `is_subset`/`is_superset`/`is_disjoint` cluster (all of which already
  implement set-style semantics on plain lists but never construct an
  actual `Set`), and notable for being able to produce an *empty* Set
  (`to_set([])`), which no Set literal can spell since `{}` is
  grammatically claimed by the empty map literal. No `STATUS: STOP` in
  `HELP.md`; `git pull --rebase` was a no-op and the root checkout was
  clean at session start (no stray stash); this session commits its own
  docs/backlog changes before exiting, per the dirty-checkout pattern
  `HELP.md` has flagged repeatedly since 2026-08-27.
- **2026-09-11 (later still)** — Caught up docs for `#441` (the `Set`
  spread depth task, task 1 from the entry above): Release had already
  merged it, archived it to `CHANGELOG.md`, and renumbered `BACKLOG.md`
  down to five tasks (`cummin` through `to_set`, 1–5), so this pass was
  pure doc catch-up, no backlog surgery needed — the backlog already
  sat at CLAUDE.md's five-task floor. Refreshed the test count (4911,
  up from 4906) and moved `Set` spread into "Recently landed" in
  README's "Status & roadmap" and this section's "Current frontier".
  Fixed the two doc claims that PR #441 made stale: README's Set
  bullet (search `does not yet behave correctly at any of the three
  spread sites`) still said spread was a known bug across all three
  sites — updated it to describe the actual landed behavior (positional
  spread in list literals/calls, clean rejection in map literals,
  since a Set has no key/value pairs to merge). Also checked
  `nightshift/HELP.md`'s 2026-09-11 Reviewer entry about a stashed
  Architect `cinder/BACKLOG.md` WIP for `caesar_cipher`/`cumprod`: that
  WIP was already resolved and committed by an earlier session
  (`4b15010`, see the entry above), and the stash itself is gone from
  `git stash list` — nothing left to fold in, just a stale pointer in
  `HELP.md` for whoever next has reason to prune that file. No
  `STATUS: STOP` in `HELP.md`; `git pull --rebase origin main` was a
  no-op and the root checkout was clean at session start. This session
  commits its own docs changes before exiting, per the dirty-checkout
  pattern `HELP.md` has flagged repeatedly since 2026-08-27.
- **2026-09-11 (grooming, sixth pass)** — Caught up docs for `#442`
  (`cummin`, merged since the last pass): refreshed the test count
  (4920, up from 4911), added `cummin` to README's builtins
  quick-reference list and moved it into "Recently landed" in both
  README's "Status & roadmap" and this section's "Current frontier".
  While scoping what breadth task to restock with, noticed `BACKLOG.md`
  had dropped to four tasks (below CLAUDE.md's five-task floor) since
  `cummin` was already removed — while investigating the `to_set` task
  for a plausible next slice, found a real bug rather than just a gap:
  `is_map` (`cinder/builtins.py`, `def _is_map`) is a bare
  `isinstance(value, dict)` check, and `CinderSet` (`cinder/
  interpreter.py`, `class CinderSet(dict)`) is a `dict` subclass, so
  `is_map({1, 2, 3})` wrongly returns `true` for a `Set` literal —
  confirmed live via `python3 -m cinder.cli eval 'print(is_map({1, 2,
  3}));'`. `type_name` already special-cases `CinderSet` before its
  `dict` fallback (search `def type_name`), `is_map` never got the
  matching fix, and there's no `is_set` predicate at all to cover the
  gap the other way. Added this as the new top `BACKLOG.md` task (fix
  `is_map` + add `is_set`, one session, same file region) ahead of the
  four existing breadth tasks (`longest_common_suffix`/`diff`/
  `midrange`/`to_set`, renumbered 2–5), bringing the backlog back to
  five. This is a correctness fix for an existing builtin, not new
  scope, so it jumps the queue rather than going to the back — same
  reasoning CLAUDE.md gives for a broken `main`, applied to a narrower
  bug in one builtin rather than the whole test suite. No `STATUS:
  STOP` in `HELP.md`; `git pull --rebase origin main` was a no-op, the
  root checkout was clean at session start (no stray stash — the one
  `HELP.md`'s 2026-09-11 Reviewer entry flagged was already resolved
  by an earlier session, see the 2026-09-11 grooming-pass entries
  above). This session commits its own docs/backlog changes before
  exiting, per the dirty-checkout pattern `HELP.md` has flagged
  repeatedly since 2026-08-27.
- **2026-09-12 (grooming, seventh pass)** — Nothing merged since the
  last pass: task 1 (`is_map`/`is_set`) is still out for review as PR
  #443, carrying `VERDICT: LGTM` but no `QA: PASS` yet, so it hadn't
  cleared the merge bar by this pass. With task 1 in flight (not
  available for a new Engineer to claim), the backlog's five *other*
  tasks left only four genuinely ready — below the five-task floor in
  spirit even though the file listed five rows. Restocked `rms` (task
  6): the quadratic mean (root mean square), the fourth classical
  Pythagorean mean completing the `mean`/`geometric_mean`/
  `harmonic_mean` trio already in `cinder/builtins.py`, placed directly
  after `_harmonic_mean` and modeled on its validate-then-reduce shape
  plus the QM-AM inequality cross-check `test_harmonic_mean_am_gm_hm_
  inequality` already establishes for the other three means — unlike
  `geometric_mean`/`harmonic_mean`, squaring removes the positivity
  restriction, so `rms` accepts negative elements. Brings the queue
  back to its usual six-task ceiling. No `STATUS: STOP` in `HELP.md`;
  `git pull --rebase origin main` was a no-op, the root checkout was
  clean at session start. This session commits its own docs/backlog
  changes before exiting, per the dirty-checkout pattern `HELP.md` has
  flagged repeatedly since 2026-08-27.
- **2026-09-12 (grooming, eighth pass)** — `#443` `is_map`/`is_set` and
  `#444` `longest_common_suffix` both merged since the last pass (per
  `nightshift/NIGHTLOG.md`'s second cycle entry today), confirmed
  clean on `main`: full suite is 4936 tests, up from 4920. Refreshed
  "Current frontier" for both merges and caught up `README.md`'s own
  drift (its Set-literal bullet, type-predicate list, and "Status &
  roadmap" section were all still describing #443 as out for review).
  Queue had dropped to its 4-task floor (`diff`, `midrange`, `to_set`,
  `rms`) after the two merges without an intervening restock; added
  `zscore` (task 5) — a numeric-list *transform* (standardize to zero
  mean/unit variance) rather than another scalar reduction, reusing
  `_population_variance` the same way `variance`/`std_dev` already do,
  placed directly after `_std_dev`. Considered `nth_keith_number` and
  an `nth_perfect_number`/`nth_automorphic` revisit as depth-adjacent
  breadth candidates but both are the same too-sparse sequences prior
  passes already ruled out (documented in this file's own history
  above) — no new information to reverse that call, so left both
  out and stayed on breadth work again this pass rather than force a
  depth task that isn't scoped yet. No `STATUS: STOP` in `HELP.md`;
  `git pull --rebase origin main` was a no-op, root checkout clean at
  session start and kept clean by committing this pass's docs/backlog
  changes directly, per the dirty-checkout fix the 2026-09-10 pass
  above put in place.
- **2026-09-12 (grooming, ninth pass)** — `#445` `diff` merged since
  the last pass (clean, single review round, per `nightshift/
  NIGHTLOG.md`'s third cycle entry today; ran the local suite to
  confirm — 4946 tests, up from 4936). `CHANGELOG.md` already had the
  archive entry and `BACKLOG.md` was already renumbered down to four
  tasks (`midrange`/`to_set`/`rms`/`zscore`, 1-4), but README.md/this
  file still called `diff` "queued next" and README's builtins
  quick-reference list was missing its bullet entirely (the flat list
  at the top of the Builtins section, not `diff`'s own detailed prose
  elsewhere — same narrow gap prior passes have repeatedly caught for
  other builtins). Fixed both, refreshed the test count in both
  places, and moved `diff` into "Recently landed" in README's "Status
  & roadmap" and this section's "Current frontier". Queue was at its
  four-task floor (one below CLAUDE.md's five-task minimum), so
  restocked with `covariance` (task 5, breadth) — the two-list
  generalization of `variance`, combining `dot_product`'s equal-length
  two-list validation with `variance`'s non-empty-list requirement
  (population covariance divides by `n`, which `dot_product` never
  does), placed directly after `_dot_product`. Verified the gap first
  (`covariance` undefined, `variance` the closest suggested match),
  then every worked example by direct computation in Python, including
  the self-covariance-equals-variance cross-check
  (`covariance([1,2,3],[1,2,3]) == variance([1,2,3])`) in the same
  spirit as the QM-AM inequality check `rms`'s own task already uses.
  Considered `weighted_mean` as an alternative but deferred it — no
  precedent in this codebase for how a weights argument should be
  validated (equal-length check with which list required to be
  positive?), the same kind of open design question that got
  `percentile` rejected two passes ago; `covariance` needed no new
  validation shape beyond what `dot_product`/`variance` already
  established, same reasoning `diff`'s own task gave for reusing
  `cumsum`'s shape. No depth task queued this pass — `generators`
  remains the only real depth gap, still too large without a
  scoped-down slice, same standing note as every pass since `Set`
  spread landed. No `STATUS: STOP` in `HELP.md`; `git pull --rebase
  origin main` was a no-op, root checkout clean at session start (no
  stray stash — `git stash list` empty), and this session commits its
  own docs/backlog changes before exiting, per the dirty-checkout fix
  the 2026-09-10 pass put in place (holding for the fourth pass in a
  row now).
- **2026-09-12 (Architect grooming, catching up on `#446`/`#447`)** —
  `git pull --rebase origin main` was a no-op, root checkout clean at
  session start (no `STATUS: STOP` in `HELP.md`, no stray stash).
  `main` green (4963 tests, up from 4955). Two merges since the last
  grooming pass had gone undocumented: `#446` `midrange` and `#447`
  `to_set`, both already reflected in `BACKLOG.md`/`CHANGELOG.md` by
  Engineer/Release but not yet in this file's "Current frontier" or
  README's "Status & roadmap" — refreshed both, and added `to_set` to
  README's builtins quick-reference and its Set-literal feature bullet
  (it had been merged without a docs follow-up task, since `to_set`'s
  own task write-up left that to "the Architect's next grooming pass"
  same as every other stdlib task does). Queue had dropped to four
  tasks (`rms`/`zscore`/`covariance`/`correlation`) after `to_set`
  shipped, one below the five-task floor, and the last two passes'
  "Current frontier" note had explicitly asked this pass to prioritize
  finding a scoped-down depth slice before adding more breadth. Spent
  real effort on that: checked hex/octal/binary integer literals and
  `_` digit separators, string interpolation, chained comparisons,
  `??=`, and list/map ordering comparisons/concatenation against the
  actual lexer/parser/README — all already implemented, none a gap.
  `generators` remains the only known real depth gap and still has no
  scoped-down slice. Rather than force a weak depth task or leave the
  queue short, restocked with one breadth task, `jaccard_similarity`
  (task 5) — the missing "reduce to a single number" member of the
  `union`/`intersection`/`difference`/`symmetric_difference`/
  `is_subset`/`is_superset`/`is_disjoint` lists-as-sets family, built
  by calling `_union`/`_intersection` directly so it can't drift from
  their notion of "distinct"/"shared" element. Verified every worked
  example (including the `jaccard_similarity([], [])` is `1.0`
  by-convention edge case) by running `_union`/`_intersection`
  directly in Python before writing the task. This keeps the breadth
  run at five rather than growing it to six; the next grooming pass
  should keep scouting for a depth slice with fresh eyes.
- **2026-09-12 (Architect grooming, catching up on `#449`)** —
  `git pull --rebase origin main` was a no-op, root checkout clean at
  session start (no `STATUS: STOP` in `HELP.md`, no stray stash, no
  open PRs). `main` green (4981 tests, up from 4963). One merge since
  the last grooming pass had gone undocumented: `#449` `zscore`,
  already reflected in `BACKLOG.md`/`CHANGELOG.md` by Engineer/Release
  but not yet in this file's "Current frontier" or README's "Status &
  roadmap" — refreshed both, and added `zscore` to README's builtins
  quick-reference list. Queue had dropped to four tasks
  (`covariance`/`correlation`/`jaccard_similarity`/
  `median_absolute_deviation`), one below the five-task floor and two
  below the usual six. Scouted for a depth slice again with fresh eyes
  per the last two passes' standing ask: re-checked the operator table
  and `match`/`switch`/loop features actually implemented against
  README line-by-line for gaps (spaceship `<=>`, list/map ordering
  comparisons, every `?.`/`??`/pipe/rest/keyword-argument corner) —
  still nothing; `generators` remains the only known real depth gap and
  still has no scoped-down slice small enough for one session.  Rather
  than force it, restocked with two more breadth tasks to bring the
  queue back to six: `nth_perfect_number` (task 5) and
  `nth_weird_number` (task 6), both closing the same kind of gap
  `jaccard_similarity` closed last pass — a value-returning `nth_X`
  sibling missing for an existing `is_X` classification predicate,
  following the exact precedent of `is_abundant`/`nth_abundant`,
  `is_deficient`/`nth_deficient`, `is_practical_number`/
  `nth_practical_number`, and `is_semiperfect`/`nth_semiperfect`.
  Deliberately did *not* revive `percentile` (rejected twice already
  for an open interpolation-method design question) or `weighted_mean`
  (rejected once for an open weight-validation question) a third time
  without a genuinely new angle on either open question. Checked
  `nth_perfect_number` for a performance trap before queuing it — perfect
  numbers are extremely sparse (the 5th is `33550336`) unlike every
  other `nth_X` predicate in this family, so its task write-up caps
  tests at `k <= 4` and explicitly tells the Engineer not to test
  `k = 5`, the same way `_nth_abundant`'s own O(sqrt(n))-per-candidate
  scan would need the domain restricted if abundant numbers were ever
  this sparse. `nth_weird_number` has no such trap (`70`, `836`,
  `4030`, `5830`, `7192`, `7912` all comfortably reachable). Both
  worked-example sequences confirmed by running each candidate function
  directly in Python before writing the tasks, and both gaps confirmed
  absent via `python3 -m cinder.cli eval` before that. Two breadth
  tasks in a row (following `jaccard_similarity`/
  `median_absolute_deviation` last pass) is more than the "occasional"
  stacking the alternation policy anticipates, but a real depth gap
  still hasn't turned up in four scouting passes now — the next
  grooming pass should treat finding one as the priority over restocking
  further breadth.
- **2026-09-12 (Architect grooming, catching up on `#450`)** —
  `git pull --rebase origin main` was a no-op, root checkout clean at
  session start (no `STATUS: STOP` in `HELP.md`, no stray stash, no
  open PRs — `gh pr list --state all` showed `#450` merged). `main`
  green (4992 tests, up from 4981). One merge since the last grooming
  pass had gone undocumented: `#450` `covariance`, already reflected
  in `CHANGELOG.md` by Engineer/Release but not yet in this file's
  "Current frontier" or README's "Status & roadmap"/builtins
  quick-reference list — refreshed all three. Also caught a stale
  cross-reference left behind by the merge: `BACKLOG.md` task 1
  (`correlation`) still said "once task 1 lands `_covariance`..." as
  if covariance were still pending, even though the engineer who
  claimed the old task 1 had already renumbered the remaining tasks
  down to five (`correlation` through `nth_weird_number`, 1-5) without
  updating that one leftover sentence — fixed it to state plainly that
  `_covariance` has landed and sits where the task already assumes.
  Queue had dropped to five tasks, exactly this project's documented
  5-task floor (see "Each grooming pass alternates" above), so per
  that same policy renumbered (no-op, already 1-5) and added one new
  task to bring it back to six. Scouted for a depth slice with fresh
  eyes per the last several passes' standing ask: confirmed bitwise
  `&`/`|`/`^`/`<<`/`>>` and their compound-assignment forms are already
  implemented (checked `cinder/tokens.py` directly rather than trusting
  README's prose) — still nothing new; `generators` remains the only
  known real depth gap and still has no scoped-down slice small enough
  for one session. Rather than force it, restocked with a third
  `nth_X`-sibling breadth task in a row: `nth_armstrong` (task 6),
  following the exact precedent `nth_perfect_number`/`nth_weird_number`
  set last pass — a value-returning sibling missing for an existing
  `is_X` classification predicate (`is_armstrong`, digit-power-sum
  numbers like `153 = 1^3+5^3+3^3`). Checked it for the same kind of
  sparsity trap `nth_perfect_number` had to guard against: unlike
  perfect numbers, each Armstrong candidate check is an O(digit-count)
  digit-power-sum rather than O(sqrt(n)) trial division, and the
  sequence stays dense enough (`0`-`9`, then `153`, `370`, `371`,
  `407`, `1634`, ...) to cap tests at a comfortable `k <= 15` rather
  than `nth_perfect_number`'s tight `k <= 4`. Confirmed the worked-example
  sequence by running the candidate-check function directly in Python
  before writing the task, and confirmed the gap absent via
  `python3 -m cinder.cli eval` first. Three breadth tasks in a row now
  (following `jaccard_similarity` two passes back, then
  `nth_perfect_number`/`nth_weird_number` last pass) is further past
  the alternation policy's "occasional" stacking than any prior run —
  flagged explicitly in "Current frontier" above that the next grooming
  pass should prioritize finding an actual depth slice over reaching
  for a fourth.
- **2026-09-12** — `#451` `correlation` merged clean first-pass (5004
  tests, up from 4992). Refreshed "Current frontier" and README.md's
  "Status & roadmap"/builtins list for the merge, renumbered the
  backlog's five remaining tasks back to 1-5, and fixed a stale
  self-reference in `BACKLOG.md`'s `jaccard_similarity` writeup that
  cited "`_correlation` in task 1 above" — left over from when
  `correlation` itself was queued as task 1; now that it's shipped and
  no longer a backlog entry, the aside just names `_correlation`
  directly. Depth scouting again came back empty (same standing note);
  no merge forced a restock this pass, so the queue stays at its
  5-task floor rather than being padded to six.
- **2026-09-12 (later)** — `#452` `jaccard_similarity` merged clean
  first-pass (5014 tests, up from 5004). Refreshed "Current frontier"
  and README.md's "Status & roadmap"/builtins quick-reference list for
  the merge, and renumbered the backlog's four remaining tasks to 1-4.
  Depth scouting again came back empty (same standing note, now four
  breadth tasks in a row), so restocked with `percentile` (task 5) — a
  genuine gap in the `mean`/`median`/`midrange`/`variance`/`std_dev`/
  `mode` statistics cluster rather than another `nth_X`/`is_X` sibling,
  chosen partly to break the run of divisor-sum/digit-property breadth
  tasks. Confirmed `main` green (5014 passing) and the working tree
  clean before exiting, per the recurring dirty-checkout pattern
  Reviewer sessions have flagged four times since 2026-08-27 (see
  `nightshift/HELP.md`) — this session commits its own docs work
  directly rather than leaving it for the next session to notice and
  stash.
- **2026-09-13 (grooming)** — `#453` `median_absolute_deviation` and
  `#454` `nth_perfect_number` both merged clean first-pass since the
  last grooming pass (5029 tests, up from 5014). Refreshed "Current
  frontier" and README.md's "Status & roadmap"/builtins quick-reference
  list for both merges (added the `median_absolute_deviation` and
  `nth_perfect_number` bullets README's list was missing). Two merges
  without an intervening restock had dropped `BACKLOG.md` to four tasks
  (`nth_weird_number`/`nth_armstrong`/`percentile`/`nth_automorphic`),
  one below the five-task floor — renumbered them to 1-4 and fixed the
  stale in-body cross-references each one had accumulated (`"task 2
  above"`-style references to `nth_perfect_number`, now shipped and no
  longer a numbered backlog entry; `nth_armstrong`'s aside on
  `nth_weird_number` also needed updating since that's task 1, not yet
  merged). Depth scouting came back empty again — re-ran the standing
  checks directly against the interpreter rather than trusting prior
  notes (ternary, string/list repetition, range syntax, destructuring,
  `<=>`, default arguments, `**=`, string interpolation, negative/slice
  indexing all confirmed still working); `generators` remains the only
  real gap. Restocked breadth by two instead of the usual one: audited
  the `is_*`-without-`nth_*` gap programmatically (still nothing new
  beyond the three already-queued number-theory tasks and the long
  confirmed-rejected list), so picked two standalone builtins instead —
  `to_snake_case` (task 5) and `to_camel_case` (task 6, sharing
  `to_snake_case`'s private `_split_case_words` helper, same
  same-file-dependency shape `from_roman` has on `to_roman`) — verifying
  both algorithms and every worked example by direct computation in
  Python first. Also trimmed this section's `2026-09-08` through
  `2026-09-10` span (twenty-two individual dated entries) down to one
  paragraph, same rationale as the five earlier trims recorded above:
  `main` was green and `HELP.md` had no `STATUS: STOP` and no stray
  uncommitted state at session start, `git pull --rebase origin main`
  a no-op.
