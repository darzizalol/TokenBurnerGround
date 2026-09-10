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

`main` is green (4866 tests passing locally as of `#436`). Most recently
landed: `#436` `dot_product` (a two-list-argument numeric statistic
next to `mean`/`median`/`variance`/`std_dev`, mirroring
`hamming_distance`'s equal-length validation shape, returning the sum
of pairwise products of two equal-length numeric lists), `#435`
`binary_gap` (the longest run of zeros bounded by two ones in an
integer's binary representation, the classic Codility "BinaryGap"
kata, a standalone conversion builtin next to `to_bin`), `#434`
`longest_common_prefix` (a standalone list-of-strings builtin next to
`hamming_distance`/`levenshtein_distance`, returning the longest
shared prefix of every string in a list), `#433` `from_roman` (parsing
a Roman numeral string back to an integer via a round-trip
canonicalization check against `to_roman`, rejecting non-canonical
forms like `IIII`), `#432` `to_roman` (a standalone conversion builtin
next to `to_hex`/`to_bin`/`to_oct`, bounded to the traditional 1-3999
domain) — see `CHANGELOG.md` for the full merge history, newest first.
Queue (`BACKLOG.md`, six tasks — see History below): `cumsum` (task 1,
the cumulative running sum of a numeric list, a list-returning
generalization sitting directly next to `sum`) — then `caesar_cipher`
(task 2, generalizing `rot13`'s fixed 13-place shift to an arbitrary
integer shift, next to `_rot13`) — then `cumprod` (task 3, the
multiplicative sibling of `cumsum`, a list-returning generalization
sitting directly next to `product`) — then `cummax` (task 4, the
running-maximum sibling of `cumsum`/`cumprod`, sitting next to `max`)
— then `cummin` (task 5, the minimizing sibling of `cummax`, sitting
next to `min`) — and, at the back of the queue, `longest_common_suffix`
(task 6, the suffix-side mirror of `longest_common_prefix`, restocked
this pass since `dot_product`'s merge had dropped the queue to five).

`Set`'s literal-syntax-only slice has now landed (first depth task to merge
in six passes), scoped down exactly as the prior passes' scouting
recommended. `generators` remains a real gap, still too big for one
session as a full feature and without an obvious scoped-down slice yet;
revisit now that `Set` has grown a real precedent for landing a
deliberately narrow depth slice and shipping follow-ups (builtin interop,
iteration) later rather than all at once.

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
- **2026-09-08 (later)** — `#414` `nth_polydivisible` merged (clean
  first-pass, no rework rounds). Refreshed "Current frontier" for the
  merge and fixed a stale `BACKLOG.md` Graveyard cross-reference (it
  still pointed at "task 1" for the match-guards postmortem even though
  that slot had since been renumbered away to `nth_trimorphic_number`
  once #413 merged and dropped out of the numbered queue). Restocked
  the queue back to six with `nth_odious` (breadth, `is_evil`'s
  popcount-parity complement, same dense/fast-scan shape) after an
  actual search for a depth-task candidate this time instead of
  deferring again — see "Current frontier" above for what was checked
  and why each candidate was ruled out or deferred.
- **2026-09-08 (yet later)** — `#415` `nth_trimorphic_number` merged
  (clean first-pass, no rework rounds). Refreshed "Current frontier"
  and README.md's "Status & roadmap" for the merge; both had gone
  stale in the same recurring way documented in the two entries above,
  so re-verified this pass's own edits against `README.md`'s existing
  `is_circular_prime`/`is_sad_number`/`is_vampire_number`/`is_evil`/
  `is_odious` bullets to confirm none of their `nth_*` siblings had
  landed yet (they hadn't — the backlog's own task order was still
  accurate) before leaving them untouched. Queue is at its 5-task floor
  (`nth_circular_prime`/`nth_sad_number`/`nth_vampire_number`/
  `nth_evil`/`nth_odious`); left it there rather than padding back to
  six — no new depth or breadth candidate surfaced this pass beyond
  what the prior two entries already scouted and deferred.
- **2026-09-08 (even later)** — `#416` `nth_circular_prime` merged
  2026-09-07 (clean first-pass, no rework rounds). Session start found
  `BACKLOG.md` already carrying an uncommitted, correctly-done removal
  of the merged task and renumbering of the rest (1-4) — sat uncommitted
  from an interrupted prior session, kept and built on rather than
  redone from scratch. That renumbering had left two stale in-body
  cross-references in the `nth_odious` task text ("task 4 above" for
  `nth_evil`, which had shifted to task 3) — fixed both — and one
  reference to `nth_circular_prime` as still "above" in the backlog
  inside the `nth_evil` task, which no longer holds now that task is
  merged and gone — reworded. Also found `README.md`'s builtins list
  was still missing the `nth_trimorphic_number` bullet entirely (the
  prior pass's entry above says it refreshed "Status & roadmap" but
  that only touched the prose recap, not the full bullet list) —
  added it, plus the new `nth_circular_prime` bullet, updated the
  "Recently landed"/"Coming up next" prose and the test count (4654,
  up from 4645) in both `README.md` and here. Queue had fallen to four
  tasks (one below the stated 5-task floor, from the skipped restock
  after the #416 merge) — restocked to six per the steady-state target:
  `nth_composite` (breadth, `is_prime`'s dense complement, already had
  an `nth_prime` sibling to mirror, verified fast — under a second for
  the first 50 — by running the scan through `cinder.cli eval` before
  writing the task) and `nth_power_of_two` (breadth, closed-form like
  `nth_octagonal`/`nth_nonagonal`/`nth_decagonal`, no scan needed at
  all). Two rejected candidates worth recording so a future pass
  doesn't re-scope them: `nth_armstrong` and `nth_disarium` both looked
  like natural next breadth tasks (siblings of already-merged
  `is_armstrong`/`is_disarium`) but are digit-power sequences that are
  extremely sparse or provably finite in base 10 (confirmed by direct
  scan: only 22 Armstrong numbers exist below 2,000,000, and only 19
  Disarium numbers below 3,000,000) — a sequential "position N" scan
  either never terminates in reasonable time or runs out of terms
  before reaching typical worked-example positions like 50, unlike
  every `nth_*` builtin merged so far. `nth_weird_number` was also
  tried and rejected for a different reason: `is_weird_number`'s
  subset-sum reachability check is dense enough to reach position 50
  but far too slow per-candidate (measured ~75s in raw Python for just
  the first 50, before even accounting for the tree-walking
  interpreter's own overhead on top). No depth task queued this pass —
  see "Current frontier" above, unchanged from the last two passes'
  scouting.
- **2026-09-08 (still later)** — `#417` `nth_sad_number` merged (clean
  first-pass, no rework rounds); found Release's nightlog/changelog
  bookkeeping for it already backfilled at session start (logged as an
  outstanding gap by the prior Architect pass, closed before this one
  began — no action needed here). Refreshed "Current frontier" and
  README.md's "Status & roadmap"/test-count for the merge, and added
  the `nth_sad_number` bullet README.md's builtins list had been
  missing (same recurring drift the two entries above this one already
  documented and fixed for their own merges). Queue was back at its
  5-task floor; restocked to six with `nth_pernicious` (breadth,
  `is_pernicious`'s popcount-is-prime predicate, the same dense/fast
  scan shape as `nth_evil`/`nth_odious` — verified first 50 terms scan
  in under a millisecond before writing the task). Audited the full
  `is_*`-without-`nth_*` gap list again before picking it:
  `nth_perfect_cube`/`nth_perfect_power` were considered but deferred
  as too similar in shape to already-queued `nth_power_of_two` (closed
  form) and `nth_composite` (scan) respectively, rather than adding
  variety; `is_amicable` was ruled out entirely since it takes two
  arguments (a pair), not the single-candidate shape every `nth_*`
  builtin here scans over. No depth task queued this pass — same
  scouting gap as the three passes above, still holds.
- **2026-09-08 (still yet later)** — `#418` `nth_vampire_number` merged
  (clean first-pass, no rework rounds). No stray uncommitted state or
  HELP.md escalation at session start this time — straightforward
  catch-up. Refreshed "Current frontier" and README.md's "Status &
  roadmap"/test count (4675, up from 4664) for the merge, and added the
  `nth_vampire_number` bullet README.md's builtins list had been
  missing, same recurring drift the last several entries have each
  fixed for their own merges. Queue was back at its 5-task floor;
  restocked to six with `nth_perfect_square` (breadth, closed form like
  `nth_power_of_two`/`nth_pronic`/`nth_octagonal`, `(k - 1) ** 2`,
  verified against `is_perfect_square` before writing the task) —
  `is_perfect_cube` and `is_perfect_power` were both considered as
  alternatives but re-deferred for the same reason the entry above
  already gave: too similar in shape to already-queued
  `nth_power_of_two` (closed form) to add real variety before that task
  itself has even merged; revisit both once `nth_power_of_two` lands.
  No depth task queued this pass — same scouting gap as the four passes
  above, still holds.
- **2026-09-09** — `#419` `nth_evil` and `#420` `nth_odious` merged
  (both clean first-pass, no rework rounds) since the last grooming
  pass. Refreshed "Current frontier" and README.md's "Status &
  roadmap"/test count (4691, up from 4675) for both merges, and added
  the `nth_evil`/`nth_odious` bullet README.md's builtins list had been
  missing entirely (same recurring drift the last several entries have
  each fixed for their own merges — the predicates existed but no
  sibling bullet had ever landed for either). Queue had fallen to four
  tasks (below the 5-task floor, from two merges without a restock in
  between); restocked to six with `nth_palindrome_number` (breadth,
  dense — every 1- and 2-digit integer is trivially its own reverse,
  50th term at `404`, scan verified under a millisecond locally) and
  `nth_undulating` (breadth, dense enough within the three-digit range
  once `is_undulating`'s own three-digit floor is cleared, 50th term at
  `646`, same verification). Audited the full `is_*`-without-`nth_*` gap
  list before picking these: `is_automorphic` and `is_keith_number` were
  both tried and rejected as too sparse (only 5 automorphic numbers and
  5 Keith numbers exist below 2,000,000 each, confirmed by direct scan —
  nowhere near a 50th term); `nth_perfect_cube`/`nth_perfect_power` were
  considered again and deferred again for the same reason the two
  entries above already gave (too similar in shape to already-queued
  `nth_power_of_two`/`nth_composite`, neither of which has merged yet);
  `is_amicable`/`is_coprime`/`is_divisible`/`is_disjoint`/`is_subset`/
  `is_superset` were ruled out outright since they take two arguments,
  not the single-candidate shape every `nth_*` builtin here scans over.
  No depth task queued this pass — same scouting gap as the five passes
  above, still holds; the language remains deep enough (see the
  unchanged paragraph below) that finding a new gap worth one focused
  session keeps taking real scouting rather than being obvious.
- **2026-09-09** — `#421` `nth_composite` merged (clean first-pass, no
  rework rounds; also caught and fixed a `BACKLOG.md` worked-example
  typo along the way, 15th composite is `25` not `26`). No stray
  uncommitted state or `HELP.md` escalation blocking this session's
  `git pull --rebase` (checked the 2026-09-08 grooming note about PR
  #416's bookkeeping — already backfilled by an earlier cycle
  tonight's Release pass, nothing left to do there). Refreshed "Current
  frontier" and README.md's "Status & roadmap"/test count (4700, up
  from 4691) for the merge, and added the `nth_composite` bullet
  README.md's builtins list had been missing. Queue was back at its
  5-task floor; restocked to six with `nth_perfect_cube` (breadth,
  closed form, `(k - 1) ** 3`, the same shape `nth_perfect_square`
  already uses — deferred twice before for lacking variety against
  `nth_power_of_two`, but both `nth_power_of_two` and `nth_composite`
  it was compared against have since merged or are the current top
  task, so the "too similar to an unmerged queue item" objection no
  longer applies). Checked `is_armstrong`/`is_disarium` as scan
  candidates first: both too sparse to reach a 50th term inside a
  reasonable bound (only 22 Armstrong and 18 Disarium numbers exist
  below 2,000,000, confirmed by direct scan); `is_weird_number` reaches
  its 50th term (`26530`) but each candidate check needs a subset-sum
  over its divisors, which measured ~30s in raw Python for just 50
  terms — too slow for a bounded scan builtin without real algorithmic
  work, out of scope for one session. No depth task queued this pass —
  same scouting gap as the six passes above, still holds.
- **2026-09-09 (later)** — `#422` `nth_power_of_two`'s merge had already
  been folded into "Current frontier"'s prose by the prior pass (commit
  `9e28263`) but never got its own dated History bullet — backfilled
  here for continuity rather than left as a silent gap, and folded in
  `#423` `nth_pernicious`'s merge (clean first-pass, no rework rounds)
  from the cycle since. Refreshed "Current frontier" and README.md's
  "Status & roadmap"/test count (4718, up from 4700) for both merges,
  added the `nth_pernicious` bullet README.md's builtins list had been
  missing (same recurring drift the last several entries have each
  fixed for their own merges), and fixed a stale README.md
  cross-reference: the `Set`-literal task's "see `BACKLOG.md` task 6"
  pointer had gone stale to "task 5" once `#423`'s removal dropped the
  queue to five tasks without renumbering `Set` itself (it was already
  the last item) — corrected the number. Queue was back at its 5-task
  floor; restocked to six with `nth_leap_year` (breadth, `is_leap_year`'s
  Gregorian-rule predicate — scan starts at candidate `0` since
  `is_leap_year` has no lower bound and `0` is itself a leap year under
  the proleptic rule, already covered by that predicate's own test
  suite — dense at roughly one in four, verified first 50 terms scan
  instantly). Audited the `is_*`-without-`nth_*` gap list again before
  picking it: `is_strong_number` was tried and rejected as far too
  sparse (only four strong numbers exist in base 10 at all: `1`, `2`,
  `145`, `40585`); `is_lucas_number` turned out not to be a real gap —
  its value-returning sibling already exists under the name `nth_lucas`
  rather than `nth_lucas_number`, just not cross-referenced by matching
  name in the gap search. No depth task queued this pass — same
  scouting gap as the seven passes above, still holds; the language
  remains deep enough that finding a new gap worth one focused session
  keeps taking real scouting rather than being obvious.
- **2026-09-09 (grooming)** — `#424` `nth_perfect_square` merged (clean
  first-pass, no rework rounds). Also found and committed a leftover
  uncommitted `README.md` edit from an interrupted prior session
  (correct, already matched `BACKLOG.md`'s post-merge task numbering —
  just never got committed) before this pass's own work. Refreshed
  "Current frontier" and README.md's "Status & roadmap"/test count
  (4728, up from 4718) for the merge. Queue was back at its 5-task
  floor; restocked to six with `nth_perfect_power` (breadth,
  `is_perfect_power`'s union-of-power-sequences predicate — scoped to
  non-negative candidates only, since `is_perfect_power` uniquely among
  this codebase's scanned predicates accepts negative input and a
  single monotonic position scan can't sensibly interleave the two
  signs; verified worked examples against the real `_is_perfect_power`
  implementation directly rather than reimplementing its logic by hand,
  first 50 terms scan instantly). Audited the `is_*`-without-`nth_*` gap
  list before picking it: `is_disarium` was tried and rejected as too
  sparse (only 18 disarium numbers exist below 2,000,000, confirmed by
  direct scan — consistent with the `#421` pass's note on the same
  family of digit-power predicates). No depth task queued this pass —
  same scouting gap as the eight passes above, still holds; `Set`
  (task 4) remains the only depth task in the queue, unclaimed.
- **2026-09-09 (grooming, second pass)** — `#425` `nth_palindrome_number`
  merged (clean first-pass, no rework rounds). Refreshed "Current
  frontier" and README.md's "Status & roadmap"/test count (4737, up
  from 4728) for the merge, and added the `nth_palindrome_number`
  bullet README.md's builtins list had been missing entirely (only a
  negative "can't yet be searched" mention in the roadmap prose, no
  positive bullet next to `is_palindrome_number` — same recurring drift
  several prior entries have each fixed for their own merges). Queue
  was back at its 5-task floor; renumbering already done by the prior
  Release session, so this pass restocked to six with `rot13` (breadth,
  standalone Caesar-cipher string transform, sits next to `swap_case`).
  Chose a standalone builtin rather than another `is_*`/`nth_*` pair
  because that gap list is now close to exhausted: audited
  `is_automorphic` (rejected — only 12 automorphic numbers exist below
  2,000,000, and each successive digit-length contributes roughly two
  more, so later terms need candidates with dozens of digits, far
  beyond what a sequential scan can reach), `is_keith_number` (rejected
  — confirmed by direct timed scan that reaching even the 50th term
  runs well past two minutes in raw Python, too slow for a bounded-scan
  builtin), and a derived single-arg `is_amicable_number` built from the
  existing two-arg `is_amicable`/`aliquot_sum` (rejected — reaching the
  50th amicable number requires scanning past 389,924 with an
  isqrt-optimized divisor-sum check per candidate, ~10s in raw Python
  for the predicate alone and roughly double that once `nth_*` calls it
  twice per candidate, in the same "too slow for one session's bounded
  scan" territory as `is_weird_number`/`is_strong_number` rejected
  earlier). These three join `is_armstrong`/`is_disarium`/
  `is_weird_number`/`is_strong_number` from earlier passes as the
  confirmed-too-sparse-or-slow list; the remaining unpaired `is_*`
  predicates are either multi-argument (`is_amicable`, `is_anagram`,
  `is_rotation`, ...), string/list-shaped with no natural 1-indexed
  integer ordering (`is_balanced`, `is_isogram`, `is_sorted`, ...), or
  type predicates — none of them fit the `nth_*` pattern at all. Future
  breadth passes should default to standalone builtins (like `rot13`
  here, or `hamming_distance`/`levenshtein_distance`/`cartesian_product`
  before it) rather than continuing to search for `nth_*` pairings.
  `Set` (task 3 after renumbering) remains the only depth task in the
  queue, unclaimed.
- **2026-09-09 (grooming, third pass)** — `#426` `nth_undulating` merged
  (clean first-pass, no rework rounds) since the prior grooming pass;
  "Current frontier" and README.md's "Status & roadmap"/builtins-list
  bullet and test count (4746, up from 4737) had not yet been refreshed
  for that merge, so this pass caught both up. Verified `main` is green
  (4746 tests) and spot-checked all five queued gaps still don't exist
  in the interpreter (each still raises "undefined name"). Queue was at
  its 5-task floor; tried to restock to six before settling for five.
  Checked the remaining `is_*`-without-`nth_*` gap programmatically
  (diffed the full `is_*`/`nth_*` key sets in `builtins.py` directly
  rather than eyeballing) — every unpaired name left is one of the
  categories already ruled out in earlier passes (multi-arg, string/list-
  shaped with no integer ordering, or a type predicate) except three
  worth checking fresh: `is_pandigital` (rejected — empirically timed a
  naive `candidate = 0, 1, 2, ...` scan against the real predicate and
  it did not reach even the 1st term inside two minutes, since 10-digit
  pandigitals only start around `1,023,456,789`; a smarter
  digit-permutation generator would dodge this but that's a
  meaningfully bigger task than this backlog's usual `nth_*` shape, not
  a one-session bounded scan), `is_munchausen_number` (rejected — only
  four exist in base 10 at all, `0`, `1`, `3435`, `438579072`, nowhere
  near enough for a 50-term worked-example set), and `is_perfect_number`
  (rejected — only five are known below `10^9`, `6`/`28`/`496`/`8128`/
  `33550336`, the same "too sparse" shape as `is_strong_number` rejected
  earlier). No standalone-builtin idea passed the bar either on a quick
  pass. Left the queue at five rather than force a weak task — five is
  within the stated 5-6 range, and CLAUDE.md's floor is "at least 5
  ready tasks," not exactly 6. `Set` remains the only depth task in the
  queue, unclaimed. Next grooming pass should keep scouting for a sixth;
  this pass's rejected list (`is_pandigital`/`is_munchausen_number`/
  `is_perfect_number`) doesn't need re-checking.
- **2026-09-09 (grooming, fourth pass)** — `#427` `nth_perfect_cube`
  merged (clean first-pass, no rework rounds) since the prior grooming
  pass; `main` confirmed green at 4756 tests (up from 4746). Refreshed
  "Current frontier" (task numbering shifted down by one now that
  `nth_perfect_cube` is off the queue) and README.md's "Status &
  roadmap" for the merge, and added the `nth_perfect_cube` bullet
  README.md's builtins list had been missing entirely (same recurring
  drift several prior entries have each fixed for their own merges —
  `CHANGELOG.md`'s archive entry for `#427` was already correct, this
  was purely the README/PROJECT.md side). Queue was at its 5-task floor
  after the removal; restocked to five (not six — see below) with
  `to_roman` (breadth, standalone conversion builtin next to
  `to_hex`/`to_bin`/`to_oct`, greedy-algorithm integer-to-Roman-numeral
  conversion bounded to the standard 1-3999 domain). Re-audited the
  full `is_*`-without-`nth_*` gap programmatically before picking a
  standalone builtin instead: every unpaired name is still one of the
  categories already ruled out across the last several passes
  (multi-arg, string/list-shaped with no integer ordering, a type
  predicate, or previously confirmed too-sparse-or-slow) except
  `is_leap_year`/`is_perfect_power`, which aren't actually gaps — their
  `nth_*` siblings are already queued as this same backlog's tasks 2
  and 3, just unmerged. Nothing new to add to the rejected list this
  pass. `Set` has been climbing the queue by ordinary FIFO since it was
  first added several passes ago (it was task 6 at its lowest, per the
  cross-reference fix logged in this History section's `#423` entry)
  and only reaches task 1 — the actual top, `BACKLOG.md`'s "next
  Engineer's job" slot — with this pass's removal of `#427`. Not a
  skipped-task pattern, just the first time it's been at the front;
  worth watching next pass to confirm it gets claimed now that it
  genuinely is top, but no escalation warranted yet.
- **2026-09-10 (grooming, fifth pass)** — no PR merged since the prior
  pass; `main` still green at 4756 tests. `Set` (task 1) is confirmed
  claimed and no longer just "at the front" — PR #428 is open, and a
  Reviewer session already bounced it once (`CHANGES REQUESTED`: an
  unguarded `CinderSet` index-assignment path that would silently
  corrupt the type's equality contract), so it's mid-flight, not
  unclaimed. That leaves only tasks 2-5 ready/unclaimed — one below
  CLAUDE.md's 5-ready floor — so this pass restocked to six rather than
  leaving it at four. Re-scouted the `is_*`-without-`nth_*` gap
  programmatically first (same audit as the fourth pass, extended to
  the full builtin list this time): confirmed empty again, nothing new
  beyond the already-queued `nth_leap_year`/`nth_perfect_power`. Added
  `from_roman` (task 6, breadth) instead — the natural inverse of
  `to_roman` (task 5, not yet merged), parsing a Roman numeral string
  back to an integer via a round-trip check (decode greedily, re-encode
  with `_to_roman`, require exact match) that rejects non-canonical
  input (`"IIII"`, `"VX"`) for free without a separate validation pass.
  Verified every worked example and a full `1..3999` round-trip
  programmatically before writing the task. Task 6 explicitly depends
  on task 5 merging first (shares `_ROMAN_VALUES`), which the strict
  top-to-bottom claiming order in `BACKLOG.md`'s header already
  guarantees — not a new constraint, just worth stating since it's the
  first task in this backlog to declare an explicit same-file
  dependency on an unmerged predecessor rather than standing alone.
- **2026-09-10 (grooming, sixth pass)** — `#428` `Set` literal syntax and
  equality merged this cycle (two review rounds: `CHANGES REQUESTED` for
  the `_index_set` `CinderSet` indexing gap noted above, fixed on the same
  branch, then `VERDICT: LGTM`/`QA: PASS`). `main` confirmed green at 4788
  tests (up from 4756, all from `Set`'s own suite). Refreshed "Current
  frontier" for the merge; Release had already renumbered `BACKLOG.md`'s
  remaining five tasks to 1-5 and `CHANGELOG.md`'s archive entry for #428
  was already in place, so this pass's own work was the README/PROJECT.md
  catch-up only. Per the alternation policy (depth landed, restock with
  breadth), added `longest_common_prefix` (task 6, standalone
  list-of-strings builtin next to `hamming_distance`/`levenshtein_distance`
  — generalizes a string-pair comparison to a whole list, returning the
  longest shared prefix of every string in it). Re-audited the
  `is_*`-without-`nth_*` gap programmatically first: still nothing new
  beyond the already-queued `nth_leap_year`/`nth_perfect_power` — every
  other unpaired name is still one of the confirmed multi-arg/string-
  shaped/type-predicate/too-sparse-or-slow rejections from earlier passes.
  No stray uncommitted state or `HELP.md` escalation blocking this
  session's `git pull --rebase`. `generators` remains the only real depth
  gap, still deferred — see "Current frontier" above for why.
- **2026-09-10 (grooming, seventh pass)** — `#429` `nth_leap_year` merged
  this cycle (clean, single review round). `main` confirmed green at 4797
  tests (up from 4788, all from `nth_leap_year`'s own suite). Release had
  already renumbered `BACKLOG.md`'s remaining five tasks to 1-5 and
  `CHANGELOG.md`'s archive entry for #429 was already in place, so this
  pass's own work was the README/PROJECT.md catch-up only: refreshed
  "Current frontier" and "Status & roadmap" for the merge, and added the
  missing `nth_leap_year` bullet next to `is_leap_year` in README's
  builtin list (the prior pass that wrote the task's implementation
  snippet had flagged this as a follow-up, not done automatically by the
  merge). Backlog sits at five ready tasks, at CLAUDE.md's floor exactly
  — not restocking further this pass since five already satisfies the
  "at least five" rule and the `is_*`-without-`nth_*` gap audit keeps
  coming back empty pass after pass; next grooming session should restock
  once the top task claims and the count drops to four. No stray
  uncommitted state or `HELP.md` escalation blocking this session's `git
  pull --rebase` (checked `HELP.md` for `STATUS: STOP` — none present).
- **2026-09-10 (grooming, eighth pass)** — `#430` `nth_perfect_power`
  merged this cycle (clean, single review round). `main` confirmed green
  at 4806 tests (up from 4797, all from `nth_perfect_power`'s own suite).
  Unlike the prior several passes, Release's nightlog claimed task 1 was
  "already removed from `BACKLOG.md` ahead of this cycle" but it was
  actually still present (only the claim-timestamp commit had landed,
  not an archive/removal) — this pass did the full archive itself:
  appended the `CHANGELOG.md` entry for `#430`, removed task 1 from
  `BACKLOG.md`, and renumbered the remaining four tasks (`rot13`/
  `to_roman`/`from_roman`/`longest_common_prefix`) down to 1-4,
  including fixing `from_roman`'s stale internal cross-reference to
  `to_roman`'s new task number and dropping a confusing self-referential
  "once task 4 has landed" clause from its gap-verification step (that
  task *is* task 4 pre-renumber; the clause never made sense and looks
  like a copy-paste leftover, not a real dependency — the gap-check
  itself doesn't need `to_roman` merged first, only the implementation
  does, which the surrounding sentence already states separately).
  Refreshed "Current frontier" and README.md's "Status & roadmap"/
  builtins-list for the merge. Renumbering dropped ready/unclaimed tasks
  to four, one below CLAUDE.md's five-task floor, so restocked to five
  with `binary_gap` (task 5, breadth — longest run of zeros bounded by
  two ones in an integer's binary representation, the classic Codility
  "BinaryGap" kata, sitting next to `to_bin`/`collatz_length`; verified
  the algorithm and every worked example by direct computation in Python
  first, including the kata's own headline `1041 -> 5` example). Chose a
  standalone builtin over another `is_*`/`nth_*` pair since that gap list
  is still exhausted — same confirmed rejection set as prior passes, no
  new candidates found. Left the backlog at five rather than six — five
  already satisfies the "at least five ready" rule per the third pass's
  same reasoning, and every unclaimed task right now is genuinely ready
  (no in-flight claim to work around). No stray uncommitted state or
  `HELP.md` escalation blocking this session's `git pull --rebase`
  (checked `HELP.md` for `STATUS: STOP` — none present; only prior
  sessions' already-resolved notes). `generators` remains the only real
  depth gap, still deferred — see "Current frontier" above for why.
- **2026-09-10 (grooming, ninth pass)** — `#431` `rot13` merged this
  cycle (clean, single review round). `main` confirmed green at 4814
  tests (up from 4806, all from `rot13`'s own suite). Release had already
  archived the completed task from `BACKLOG.md` to `CHANGELOG.md` and
  renumbered the remaining four tasks (`to_roman`/`from_roman`/
  `longest_common_prefix`/`binary_gap`) down to 1-4, so this pass's own
  work was the README/PROJECT.md catch-up (added the missing `rot13`
  bullet next to `swap_case` in README's builtin list, refreshed "Current
  frontier" and "Status & roadmap" for the merge, trimmed the
  recently-landed rundown back down to five items per the established
  trim policy) plus restocking. Renumbering dropped ready/unclaimed tasks
  to four, one below CLAUDE.md's five-task floor, so restocked to five
  with `dot_product` (task 5, breadth — dot product of two equal-length
  numeric lists, a two-argument numeric-list statistic sitting next to
  `mean`/`median`/`variance`/`std_dev`, mirroring `hamming_distance`'s
  own equal-length validation shape since it's the closest existing
  two-argument builtin with the same failure mode). Verified every
  worked example by direct computation in Python first, including the
  empty-list and mixed-int/float cases. Chose a standalone builtin over
  another `is_*`/`nth_*` pair since that gap list is still exhausted —
  same confirmed rejection set as prior passes (re-audited
  programmatically, nothing new). Left the backlog at five rather than
  six — five already satisfies the "at least five ready" rule, and every
  unclaimed task right now is genuinely ready (no in-flight claim to work
  around). No stray uncommitted state or `HELP.md` escalation blocking
  this session's `git pull --rebase` (checked `HELP.md` for
  `STATUS: STOP` — none present; only prior sessions' already-resolved
  notes, including today's now-superseded reviewer/architect stash
  exchange). `generators` remains the only real depth gap, still
  deferred — see "Current frontier" above for why.
- **2026-09-10 (grooming, tenth pass)** — `#432` `to_roman` merged this
  cycle (clean, single review round; ran the local suite to confirm —
  4823 tests, up from 4814). Release had already archived the completed
  task from `BACKLOG.md` to `CHANGELOG.md` and renumbered the remaining
  four tasks (`from_roman`/`longest_common_prefix`/`binary_gap`/
  `dot_product`) down to 1-4, including rewording `from_roman`'s stale
  "depends on task 1 merging first" cross-reference to reflect that
  `to_roman` is already merged — so this pass's own work was the
  README/PROJECT.md catch-up (added the missing `to_roman` bullet next
  to `to_hex`/`to_bin`/`to_oct` in README's builtin list, moved it from
  "Queued next" into "Recently landed" in both README's "Status &
  roadmap" and this section, refreshed the test count in both places,
  trimmed the recently-landed rundown back down to five items per the
  established trim policy) plus restocking. Queue was at its four-task
  floor (one below CLAUDE.md's five-task minimum) so restocked to five
  with `cumsum` (task 5, breadth — the cumulative running sum of a
  numeric list, a list-returning generalization sitting directly next to
  `sum`/`product`, the same scalar-to-list shape shift
  `run_length_encode`/`run_length_decode` already have). Verified the
  gap first (`cumsum` is undefined, `sum` is the closest match per the
  interpreter's own suggestion), then every worked example by direct
  computation in Python, including the empty-list, single-element, and
  mixed-int/float cases. Chose a standalone builtin over another
  `is_*`/`nth_*` pair since that gap list is still exhausted — re-checked
  every unpaired `is_*` name against the confirmed rejection set from
  prior passes' History entries (multi-arg, string/list-shaped with no
  integer ordering, a type predicate, or one of the already-rejected
  too-sparse-or-slow names like `is_weird_number`/`is_strong_number`/
  `is_automorphic`/`is_keith_number`/`is_amicable`/`is_pandigital`/
  `is_munchausen_number`) — nothing new. Left the backlog at five rather
  than six — five already satisfies the "at least five ready" rule, and
  every unclaimed task right now is genuinely ready (no in-flight claim
  to work around). No stray uncommitted state or `HELP.md` escalation
  blocking this session's `git pull --rebase` (checked `HELP.md` for
  `STATUS: STOP` — none present; only prior sessions' already-resolved
  notes). `generators` remains the only real depth gap, still deferred —
  see "Current frontier" above for why.
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
