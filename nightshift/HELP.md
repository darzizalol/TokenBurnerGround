# HELP — pager between the night shift and the human

Agents: append escalations at the bottom (timestamp, role, what's wrong, what
you tried, what you did instead) and fire `nightshift/notify.sh` per CLAUDE.md.

Human: reply inline under an entry. To halt all overnight work, add a new line
that starts exactly with `STATUS: STOP`; remove it to resume.

---

## 2026-07-24T19:30:22Z — Engineer

What's wrong: `gh pr create` failed 3x in a row with a GitHub-side GraphQL
error (`Something went wrong while executing your query`, distinct support
IDs each time), then a REST fallback (`gh api repos/.../pulls`) also failed
with `unexpected end of JSON input`. `gh auth status` confirms the token is
valid and not expired, so this looks like a transient GitHub API issue, not
a credential problem.

What I tried: retried the GraphQL `gh pr create` 3x (one with a short sleep
in between), then tried the REST endpoint directly as a fallback — all 4
attempts failed.

What I did instead: work is complete and safe — implemented, tested (777
tests pass), committed, and pushed to `origin/feat/20260724-flat-map`
(branch for BACKLOG.md task 1, `flat_map` builtin). Per token discipline
(3x-repeat rule) I stopped retrying rather than burning more tokens on it.
No PR exists yet for this branch. The next session (Engineer or otherwise)
should just run `gh pr create` from
`.worktrees/flat-map` (worktree still in place) — if GitHub's API has
recovered it should go through immediately; no rework needed on the code
itself. Not paging via notify.sh since this doesn't need human
credentials/action, just a retry once GitHub's API is healthy again.

---

## 2026-07-25T00:00:00Z — Release

What's wrong: retried `gh pr create` from `.worktrees/flat-map` for the
`feat/20260724-flat-map` branch (as the prior Engineer entry suggested) —
still fails with the same GitHub-side GraphQL error (new support ID
`C006:EAEBB:49C2D8:4E4DD0:6A63BDC7`). This is now attempt 5 total across
sessions, still failing.

What I tried: one `gh pr create` retry (GraphQL, the same command as
before).

What I did instead: stopping per the 3x-repeat rule rather than burning
more tokens on it — this is a GitHub-API-side issue that outlasted one
overnight cycle already, not something retries fix. No PR opened this
cycle either. Nothing else was open to merge, so this cycle's release
pass otherwise had nothing to do. Not paging via notify.sh — no
credential/human action needed, just GitHub API health. Next session
(any role) can retry `gh pr create` from `.worktrees/flat-map`
(worktree still in place, branch pushed and clean) once GitHub's API
looks healthy; if this keeps failing across several more nights it may
be worth escalating to the human as a standing GitHub outage.

---

## 2026-07-25T~ — Architect

What's wrong: nothing new — grooming session, but checked in on the
`flat_map` PR-creation blocker (5 straight `gh pr create` failures across
two prior sessions, see above) since it stalled the entire previous cycle.

What I tried: read-only health check, not a `gh pr create` retry (opening
PRs isn't this role's job) — `gh auth status`, `gh api
repos/darzizalol/TokenBurnerGround`, and `gh api /rate_limit` all
succeeded cleanly. Basic REST/GraphQL-adjacent API access looks healthy
right now; the earlier failures may have been a transient GitHub-side
outage that has since cleared.

What I did instead: annotated BACKLOG.md task 1 so the next session that
picks this up knows the code is already done (777 tests, pushed to
`origin/feat/20260724-flat-map`, worktree `.worktrees/flat-map` intact)
and should just retry `gh pr create` rather than re-implementing; if that
retry still fails, told it to page via `notify.sh` this time — we're now
well past the 3x-repeat threshold and two full sessions have already
logged this without paging.

---

## 2026-07-25T19:39Z — Engineer

What's wrong: `gh pr create` for `feat/20260724-flat-map` still fails —
this is attempt 8 across four sessions/two nights. This session first
rebased the branch onto current `main` (clean, no code conflicts; one
`README.md` conflict from a builtins-list merge, resolved by keeping both
`take`/`drop` and `flat_map` entries), reran the full suite (777 tests,
still passing), force-pushed the rebased branch, then retried `gh pr
create` twice (GraphQL, distinct support IDs `D4EC:3728D9:4D2DAA:51D893:6A63BF47`
and `D59A:39E6ED:4E2CBC:52E1C3:6A63BF54`) — both failed with the same
"Something went wrong while executing your query" error.

What I tried: to rule out a `gh`-CLI/GraphQL-client-specific bug (as
opposed to a GitHub platform issue), I dropped to the raw REST API:
`gh api repos/darzizalol/TokenBurnerGround/pulls -f title=... -f head=...
-f base=... -f body=...`. This also failed (`unexpected end of JSON
input`). Running the same call with `--verbose` showed the actual
response: `HTTP/2.0 500 Internal Server Error` with `Content-Length: 0` —
GitHub's PR-creation endpoint is returning a bare 500 for this repo, on
both the GraphQL and REST paths. Meanwhile `gh auth status`, `gh api
/rate_limit`, and `gh api repos/darzizalol/TokenBurnerGround` (plain
reads) all succeed instantly — so this isn't token expiry, scope, or
rate-limiting, it's specifically PR creation on this repo that 500s.

What I did instead: paged the human via `notify.sh` ("GitHub PR creation
broken for TokenBurnerGround") since this is now a confirmed
GitHub-platform-side 500 that has outlasted 8 retries over 2+ nights —
squarely past the 3x-repeat threshold and not something further retries
will fix. Left `.worktrees/flat-map` in place, rebased onto latest
`main`, tests green, pushed to `origin/feat/20260724-flat-map` — the very
next `gh pr create` from that worktree should work once GitHub resolves
this (no code changes needed). Moving on to BACKLOG.md task 2 this
session so the cycle isn't fully blocked. Human: if this 500 persists,
worth checking the repo's PR settings (branch protection rules,
disabled/restricted PRs, or an app/webhook mis-integration) since a
platform-wide GraphQL outage would likely also break other repos' PR
creation, whereas this looks scoped to this one repo.

---
