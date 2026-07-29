# DECISIONS.md

## Build Stockfish from source instead of shipping a pre-built binary
Status: DECIDED

The repo previously shipped `stockfish-ubuntu-x86-64`, a pre-built Linux x86-64 ELF binary,
copied directly into the Docker image. On arm64 hosts (e.g. Apple Silicon) this fails with
"exec format error" once the container is built natively for arm64, since the Dockerfile
had no platform pin.

Fix: vendor the Stockfish source tree (`stockfish/src`) and compile it in a
`stockfish-build` Docker stage, selecting `ARCH=x86-64` or `ARCH=armv8` from `uname -m`
inside that stage (the vendored tree is missing `scripts/get_native_properties.sh`, so
`ARCH=native` can't self-detect — this is a deliberate, conservative baseline choice, not
the most-optimized build). This guarantees `/usr/bin/stockfish` always matches the
container's actual build architecture, regardless of host.

## Extract the compiled Stockfish binary as a host artifact
Status: DECIDED

`build.sh` additionally builds the `stockfish-build` target alone and `docker cp`s the
resulting binary out to `./stockfish-bin` on the host. Useful for inspection/reuse outside
the container. This file is arch-specific to whatever host built it, so it's gitignored,
never committed.

## Vendor `stockfish/src` directly in the repo (not a submodule, not fetched at build time)
Status: DECIDED

Chosen over a git submodule or an in-Dockerfile `git clone`/`wget` because it's small
(~1.2MB source-only), and avoids a network dependency during `docker build`. Tradeoff:
the vendored snapshot isn't obviously pinned to a tagged release — see `TASKS.md`.

## Project control-file framework: plain four-file bootstrap, not CONTEXT.md/GUARDRAIL.loc.md
Status: DECIDED

A stray `CLAUDE.md` pointer file (referencing `CONTEXT.md`, `GUARDRAIL.loc.md`,
`DESIGN.loc.md`, a `/boot` skill, and an MCQ-driven discipline) briefly appeared in the
repo root. Confirmed with the user it wasn't intentional for this project; they deleted
it. This project uses the plain four-file bootstrap from `~/.claude/CLAUDE.md`
(`CLAUDE.md`/`TASKS.md`/`DECISIONS.md`/`IDEAS.md`) instead.

## Deepen reply-move explanations with Idea 1 + Idea 2; defer Idea 3
Status: DECIDED

`moves()`'s "Engine expects the reply X" line was too shallow — no explanation of what
that reply does or why the engine expects it over the opponent's other options. Three
options were considered (see `IDEAS.md`), ordered by cost:

1. Classify the reply (and the move after it) using the existing `classify_move()`
   machinery, reusing data already in the principal variation — free, no extra engine
   calls, but only describes move type (capture/check/quiet), not comparative reasoning.
2. A new opt-in function that recurses the `moves()` ranking-table-plus-narrative
   approach one ply deeper — a fresh multipv call on the position after a chosen
   candidate move, ranking the opponent's replies against each other the same way we
   rank our own candidates. This is the real "why," at the cost of an extra engine call
   per invocation.
3. Chain idea 2 again for our follow-up move after their reply — a small explained
   game-tree. Cost compounds per hop (another multipv call each time).

Decision: build 1 (as a default upgrade to `moves()`) and 2 (as a new on-demand
function, not automatic for all 5 candidates, to keep engine time bounded). Idea 3 stays
in `IDEAS.md` as a future on-demand extension, not built now.
