# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- Build a `GameCursor` in `game.py` — a stateful forward/backward stepper over a game's
  actual played moves (`.next()`/`.prev()`/`.goto(move_number, side)`), plus an on-demand
  `.explain()` that shows the engine's ranked alternatives at the cursor's position
  against what was actually played. `at_move()` already has the position-lookup logic;
  this generalizes it into something you can step through move-by-move instead of only
  jumping to one named move at a time. See `DECISIONS.md` for the full design. Motivating
  example, not yet run: "I thought I had the opponent's queen trapped a couple of moves
  earlier, but missed an escape square" — build this, then run it against that real game
  as the first end-to-end test.
- Decide on a workflow fix for the `Game.ipynb` autosave-clobbering risk: a live browser
  tab's autosave can silently overwrite direct file edits to the same notebook, and vice
  versa. Happened once already this session. See `DECISIONS.md`.

## Backlog
- `notebooks/game.py` has no `explain_reply()`-chained narrative for critical moments —
  see IDEAS.md's Idea 3 (deferred).
- Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
  (see `IDEAS.md`) instead of an untracked snapshot.
- Convert `Position.ipynb`/`Game.ipynb` from Jupyter to marimo (https://marimo.io/) once
  the `GameCursor` navigator above is built: marimo's reactive re-execution model fits
  forward/backward step-through much better than Jupyter's manual re-run, and as a bonus
  its plain-`.py`-file notebooks have no autosave/JSON layer, which would also eliminate
  the `Game.ipynb` autosave-clobbering risk logged above. There's already a stale,
  unrelated marimo artifact at `notebooks/__marimo__/session/Chess.py.json` (no matching
  `Chess.py`, predates the `Position.ipynb` rename) — left alone for now; resolving it is
  naturally part of doing this conversion for real, not a separate cleanup.
