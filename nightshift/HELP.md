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

## 2026-07-24T19:50Z — Engineer

What's wrong: same session, second task. Implemented BACKLOG.md task 2
(string interpolation), tests green (794 passing, up from 769), pushed to
`origin/feat/20260724-string-interp`. `gh pr create` failed with the same
GraphQL 500 (support ID `E7EE:37FC5F:528E75:577BFE:6A63C1FE`); a REST
retry (`gh api repos/.../pulls`, `--verbose`) showed the identical bare
`HTTP/2.0 500 Internal Server Error`, `Content-Length: 0` seen on
`flat-map` earlier this session.

What I tried: one GraphQL attempt + one REST attempt (not repeating past
that — already past the retry budget for this known issue).

What I did instead: this is new evidence worth flagging even though I
already paged via `notify.sh` once this session for the identical error —
this failure is on a **completely different branch** (`string-interp`,
never touched by the `flat-map` work), which rules out anything specific
to that one branch/commit and confirms the block is repo/account-wide on
PR creation itself. Given `X-Accepted-Github-Permissions:
pull_requests=write` shows up in the response headers on every attempt,
if the human is investigating: worth double-checking the fine-grained
PAT's repository permissions include "Pull requests: write" — a
permissions gap can sometimes surface as a 500 instead of a clean 403 on
GitHub's API. Not re-paging via `notify.sh` (same root cause already
flagged). Annotated BACKLOG.md task 2 the same way task 1 was annotated:
code complete in `.worktrees/string-interp` on
`feat/20260724-string-interp`, next session should just retry `gh pr
create` once this is unblocked, not re-implement. Both of the two
top backlog tasks are now in this same state — nothing else left to pick
up productively this session, so stopping here rather than starting a
third task that would likely hit the identical wall.

---

## 2026-07-28 22:40:11 — orchestrator
Claude CLI authentication failed during the engineer session (see logs/20260728-223905-engineer.log).
Human: run 'claude' in a terminal and re-login. No agent can fix this.

---

## 2026-08-03T19:47Z — Release

What's wrong: PR #163 (`feat/20260803-symmetric-difference`) has both
`VERDICT: LGTM` and `QA: PASS` since its sole commit — merge-eligible —
but `gh pr merge 163 --squash --delete-branch` failed 3x in a row with
three different transient-looking errors: a GraphQL 500 ("Something went
wrong while executing your query"), a 502 Bad Gateway from nginx, then
twice more `Merge already in progress` (once via `gh api -X PUT
.../merge`, once via `gh pr merge` again) even though `gh pr view 163`
consistently shows `state: OPEN`, `mergedAt: null`, `mergeStateStatus:
CLEAN`, `mergeable: MERGEABLE` — i.e. GitHub's REST/GraphQL merge
endpoints are erroring or wedged but the PR itself is untouched, not
actually mid-merge.

What I tried: `gh pr merge` (x2, GraphQL), `gh api -X PUT .../merge`
(REST), then polled `mergedAt` for ~20s waiting for an async completion
that never landed. This is the same flavor of GitHub-API-500 flakiness
logged on 2026-07-24 for `gh pr create` (see above), just hitting the
merge endpoint instead of PR creation this time — looks account/repo-wide
on the mutation side of the API rather than specific to this PR.

What I did instead: stopping at 3 failed attempts per the token-discipline
rule rather than continuing to retry. Left PR #163 open, untouched,
worktree already cleaned up (`.worktrees/symmetric-difference` removed
pre-merge per protocol, so nothing to re-clean). Not moving its BACKLOG.md
task since it isn't actually done yet. Next Release session should just
retry `gh pr merge 163 --squash --delete-branch` once — no re-review, no
re-QA needed, both verdicts still stand since nothing has been pushed to
the branch since they were posted. Not paging via `notify.sh` since this
is the same class of transient GitHub outage already flagged to the human
on 2026-07-24 (mutation-side 5xx errors), not a new credential/account/config
issue requiring human hands.

---

## 2026-08-03T19:52Z — Release (correction)

Correction to the entry immediately above: after logging that as
"blocked," a `git pull --rebase` turned up `558fa4a "engineer: add
symmetric_difference builtin (#163)"` already sitting on `main` — one of
the three failed-looking `gh pr merge`/`gh api` attempts had actually
written the squash commit to `main` before erroring; GitHub just never
flipped PR #163's own state to merged or deleted its branch (`gh pr view`
kept showing `state: OPEN`, `merged: false` even with the commit live on
`main`). Confirmed content is correct and complete (single-parent commit,
matching diff, matching squash-merge commit message format). Reconciled
by hand: closed PR #163 with an explanatory comment, deleted the leftover
`feat/20260803-symmetric-difference` branch, and added its CHANGELOG.md
entry / renumbered BACKLOG.md (task 1 removed, 2-5 to 1-4) since the work
is in fact shipped. Lesson for future Release sessions: after a `gh pr
merge` failure, don't just trust `gh pr view`'s `merged`/`state` fields —
`git pull --rebase origin main` and check whether the commit landed
anyway before logging it as blocked, since GitHub's merge endpoint can
apparently fail *after* writing to the base branch.

---

## 2026-08-13T14:39:40Z — QA

What's wrong: SSH auth to `git@github.com` started failing mid-session with
`Permission denied (publickey)`. The session's very first step (`git pull
--rebase origin main`) succeeded cleanly. Minutes later, trying to fetch
PR #236's branch for QA (`git fetch origin` / `git worktree add --detach
.worktrees/qa-pr236 origin/feat/20260813-hamming-distance`) failed with
`Permission denied (publickey)`. `ssh-add -l` reports "Could not open a
connection to your authentication agent" — no `SSH_AUTH_SOCK`/agent
available in this session. `git config core.sshCommand` is unset (no
custom key override), so this is the default `ssh` using whatever agent
identity was available — which evidently went away between the start-of-session
pull and this fetch.

What I tried: `git fetch origin` (fail), `ssh-add -l` (no agent), `git
fetch origin` again (fail, same error), `git pull --rebase origin main`
again (fail, same error) — 3 identical failures, stopped per the
3x-repeat token-discipline rule rather than continuing to retry.

What I did instead: paged the human via `notify.sh` since this smells
like an expired/unloaded SSH key or a dropped `ssh-agent` — something
only human hands can fix (re-add the key to the agent, or check if the
deploy key/PAT-backed SSH key expired). PR #236 (`hamming_distance`
builtin) has `VERDICT: LGTM` and is otherwise ready for QA but could not
be tested — no worktree could be created to check it out. No other open
PRs to check this session. Nothing else for the QA role to do while git
push/fetch is down, so ending this session here rather than sitting and
retrying. Next QA session should retry `git fetch origin` first thing —
if it succeeds, resume QA on PR #236 (worktree was never created, so
nothing to clean up).

**Addendum, same session, ~1 min later:** this was committed locally
(couldn't push — same publickey error). Then, out of curiosity before
ending the session, tried `git push origin main` once more: this time it
got *past* SSH auth cleanly and instead hit `remote: Internal Server
Error` / `! [remote rejected] main -> main (Internal Server Error)`
(Request ID `5350cce3d1161fa6d7127ffee077f3b8`). Immediately retried `git
fetch origin` right after and got the *original* `Permission denied
(publickey)` again. So this isn't a clean single-cause failure — auth
itself is flaking (sometimes passes, sometimes doesn't) layered with a
GitHub-side mutation-endpoint 500, which matches the flavor of
transient GitHub-API flakiness already logged multiple times in this
file (2026-07-24 through 2026-08-03 entries, `gh pr create`/`gh pr
merge` 500s). Given the inconsistency, this may resolve on its own; not
retrying further this session (well past the 3x budget now). This
commit (`b64dc53`, this HELP.md entry) is sitting local-only on `main`
in the repo root until a push succeeds — next session should `git push
origin main` early if `git log origin/main..HEAD` shows it's still
unpushed.

---

## 2026-08-13T14:43:55Z — Release

What's wrong: same SSH auth outage QA logged above (`Permission denied
(publickey)` on `git@github.com`). This session's `git pull --rebase
origin main` at start succeeded, but PR #236 had no `QA: PASS` yet (only
`VERDICT: LGTM`), so no merge was due regardless. While writing this
NIGHTLOG entry, tried to push it plus the two QA commits
(`b64dc53`, `5fd0442`) still sitting local-only on `main`: `git push
origin main` failed 3x in a row with `Permission denied (publickey)`, and
a `git fetch origin` in between also failed the same way — so this isn't
resolved yet, still flaking as of this timestamp.

What I tried: `git push origin main` x3, `git fetch origin` x1, `ssh-add
-l` (no agent, same as QA's finding) — stopped at the 3x-repeat budget.

What I did instead: not re-paging via `notify.sh` since QA already fired
it for this exact issue ~4 minutes ago and it's still unresolved on the
human's end. Left `main` with 3 unpushed local commits
(`b64dc53`, `5fd0442`, and this cycle's NIGHTLOG entry) — nothing
destructive, just queued. PR #236 stays open, unmerged, waiting on QA
(which itself is blocked on the same outage). Next session with working
git access: `git push origin main` first before anything else.

**Addendum, same session, ~1 min later:** retried `git push origin main`
once more out of curiosity before ending the session — this time it went
through cleanly (`b0ee034..aa6f953`). Confirms QA's read that this is
flaky/intermittent rather than a hard credential failure. All commits
are now on `origin/main`; nothing left unpushed. Not closing this thread
out entirely since the underlying flakiness is still unexplained and may
recur — leaving it open for the human to investigate at their
convenience, not urgent anymore.

## 2026-08-14 22:00:29 — orchestrator
Claude CLI authentication failed during the architect session (see logs/20260814-220016-architect.log).
Human: run 'claude' in a terminal and re-login. No agent can fix this.

## 2026-08-17T18:09:50Z — Reviewer

What's wrong: reviewed PR #265 (trailing commas, feat/20260817-trailing-commas)
in full — read the diff, checked the four parser sites against BACKLOG.md
task 1's scoping, checked out the branch in a detached worktree
(`.worktrees/rev-pr265`, already cleaned up), and ran the full suite (2992
tests, all pass). Verdict was LGTM. But `gh pr comment 265 --body ...`
failed 3x in a row with the same error: `non-200 OK status code: 503
Service Unavailable body: "No server is currently available to service
your request..."`. This matches the flavor of transient GitHub-API
mutation-endpoint flakiness already logged repeatedly in this file
(2026-07-24 through 2026-08-13 entries).

What I tried: `gh pr comment 265 --body "..."` x3, identical body each
time, ~immediate consecutive retries.

What I did instead: stopped at the 3x-repeat budget per CLAUDE.md's token
discipline rule. No other open PRs this session, so nothing else to
review. Not paging via notify.sh — this is API flakiness with clear
precedent, not something requiring human action, and prior entries note
it tends to self-resolve. Leaving PR #265 without a posted verdict;
next Reviewer (or this session's continuation) should retry
`gh pr comment 265` — the review content is fully written and can be
regenerated from `gh pr diff 265` + BACKLOG.md task 1 if needed, but
ideally just retry the post since the analysis is already done and sound
(VERDICT: LGTM, see reasoning above).
