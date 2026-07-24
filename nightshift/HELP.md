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
