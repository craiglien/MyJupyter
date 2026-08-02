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

## Switch cc.py's __ver__ to semantic versioning, reset baseline to 0.0.0
Status: DECIDED

`__ver__` had been an informal float (`0.9`, then `1.0`) bumped on "notable changes" —
no real rule for what counted as notable, so the number carried no information about
whether a change was safe to pull into an existing notebook session. Switched `__ver__`
to a semver string and reset it to `0.0.0` as the new baseline: MAJOR for breaking
changes to a function's signature/behavior, MINOR for new backwards-compatible
functions/features, PATCH for bug fixes only. See `CLAUDE.md`.

## Strip notebook outputs on commit via nbstripout, instead of gitignoring Chess.ipynb
Status: DECIDED

`notebooks/Chess.ipynb` kept showing modified after every run, even with no real edits,
because Jupyter stores cell outputs (execution counts, printed text, rendered SVG boards)
inline in the `.ipynb` JSON. A `git diff` mixed real source edits together with pure
output noise, making the diff unreadable and the file effectively uncommittable without
manually separating the two.

Considered gitignoring the file outright, but that would also throw away real source
edits (which FEN/position is being tested, which functions are called) — not just the
noise. Instead installed `nbstripout` (via `uv tool install nbstripout`, since it's a
git-hook CLI, not a project runtime dependency) and registered it as a git clean filter
via `nbstripout --install --attributes .gitattributes`, so outputs are stripped
automatically whenever a notebook is staged. `.gitattributes` (committed, shareable)
declares which files use the filter; each clone still needs to run
`nbstripout --install` once locally to register the actual filter command, since git
filters can't be fully defined in a committed file.

## Name the whole-game analysis module gac.py, not gc.py
Status: DECIDED

The planned module name `gc.py` turned out to be unusable: `gc` is a module compiled
directly into the Python interpreter (`sys.builtin_module_names`), so `import gc` always
resolves to Python's own garbage collector regardless of `sys.path` order — confirmed by
testing (a script doing `sys.path.insert(0, "/app"); import gc` still got the builtin, not
`notebooks/gc.py`). Renamed to `gac.py` before writing any more code against the old name.

## Draw pieces on top of move arrows in cc.py's board rendering
Status: DECIDED

`_display_ranked_moves()`'s candidate boards draw an arrow from the move's origin to
destination square, but `chess.svg.board()` emits the arrow's SVG elements after (so
visually on top of) the piece elements. For a short move — mainly knight hops, since a
knight's destination is close to its origin relative to its visual footprint — the
arrowhead polygon lands almost entirely on top of the piece that just moved there, making
it look like it was never drawn. Found while testing `gac.py`'s critical-moment
drill-down against `1. e4 d5 2. Nc3 Nf6 3. Bd3`, where the engine's suggested alternative
at White's 3rd move was itself a knight move; the bug is in shared rendering code, not
specific to `gac.py`, and affects `cc.moves()` in `Chess.ipynb` equally, just less
noticeably since knight-move candidates come up less consistently there.

`chess.svg.board()` has no built-in option to reorder or shrink the arrow. Fixed with a
small post-processing helper, `_pieces_over_arrows()`, that moves the arrow `<line>`/
`<polygon>` elements (found via a regex on `class="arrow"`) to just before the first
piece `<use>` element in the returned SVG string — pieces render on top, the arrow still
shows as a trail leading into the square. Bumped `cc.py` to `0.0.1` (PATCH, bug fix only).

## Clean up cc.py before debugging the game-analysis notebook
Status: DECIDED

Audited `cc.py` for bugs before relying on it further from `gac.py`/`Game.ipynb`. Found
and fixed four issues, all PATCH-level (bug fixes / cleanup, no new features, no breaking
signature changes):

- `moves(board, show=True)`'s `show` parameter did nothing — `_display_ranked_moves()`
  always displayed regardless. Wired it through (`show=False` now genuinely suppresses
  the table/board/print output while still returning the raw `info`) rather than removing
  the parameter, to keep the signature backwards-compatible.
- Calling `_display_ranked_moves()` (via `moves()` or `explain_reply()`) on a position
  with no legal moves crashed with `KeyError` — confirmed empirically that
  `engine.analyse()` on a checkmate/stalemate position returns a result dict with no
  `'pv'` key at all. Added an `is_game_over()` guard that prints "Checkmate — no moves to
  analyze." (or Stalemate/Game over) and returns `info` instead of crashing. Not currently
  reachable through `gac.py`'s own call paths (critical-moment drill-down only ever
  analyzes the position *before* a flagged move), but a real landmine for direct callers.
- `get_color()` silently returned the string `'invalid'` for unrecognized input instead of
  raising — a typo'd color argument would quietly produce wrong board orientation later
  instead of failing where the mistake was made. Now raises `ValueError`.
- `pgn()` was full of leftover debug prints (`print(dir(gm))`, printing the board after
  every pushed move, `print(dir(bd))`) — removed; behavior unchanged.

Bumped `cc.py` to `0.0.2`. Verified via a script exercising all four fixes plus a
`gac.py` regression run (checked `gac.py` still imports and runs cleanly against the
updated `cc.py`).
