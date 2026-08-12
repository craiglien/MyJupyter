# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- Visually confirm `GameCursor` in the browser (`Game.ipynb`/`Game.debug.ipynb`) — the
  underlying mechanics (navigation, error handling, a real Stockfish `.explain()` call,
  and a checkmate-ending game) are already verified against Fool's Mate; see
  `DECISIONS.md`. This is just eyeballing that the notebook UI renders it correctly.
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
