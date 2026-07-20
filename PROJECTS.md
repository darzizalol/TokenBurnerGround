# PROJECTS — the studio's product index

Every product this studio builds lives in its own directory under
`projects/<slug>/`, carrying its own `README.md`, `PROJECT.md` (vision &
spec, Architect-owned) and `BACKLOG.md` (prioritized tasks).

The night shift works **one project at a time** — the one named on the
`ACTIVE:` line below. Agents and scripts parse that line; keep its format.

ACTIVE: projects/cinder

| Project | Status | What it is |
|---------|--------|------------|
| [Cinder](projects/cinder/) | **active** | A scripting language with a tree-walking interpreter, in pure Python. Started night one (2026-07-18). |

Rules (Architect-owned file):

- Starting a new project requires the active one to be shipped-and-stable or
  declared dead — record the hand-off or obituary here **and** in the old
  project's `PROJECT.md` history before switching the `ACTIVE:` line.
- Retired projects keep their directory; they are history, not garbage.
