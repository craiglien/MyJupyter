# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- Decide on a workflow fix for the `Game.ipynb` autosave-clobbering risk: a live browser
  tab's autosave can silently overwrite direct file edits to the same notebook, and vice
  versa. Happened once already this session. See `DECISIONS.md`. Note: `game_marimo.py`
  doesn't have this specific failure mode (no autosave/JSON layer), but `Game.ipynb`
  itself is still Jupyter and still exposed to it.

## Backlog
- `notebooks/game.py` has no `explain_reply()`-chained narrative for critical moments —
  see IDEAS.md's Idea 3 (deferred).
- Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
  (see `IDEAS.md`) instead of an untracked snapshot.
- Convert `Position.ipynb` to marimo too. `Game.ipynb`'s workflow got a marimo sibling
  (`game_marimo.py`, candidate-picker only) rather than a full replacement — Jupyter and
  marimo now run side by side in the container (see `DECISIONS.md`). Position-side
  conversion, retiring Jupyter entirely, and the `Game.ipynb` autosave-clobbering fix
  above are all still open.
- Port `show_sweep()`/`show_critical_moments()`'s eval-curve chart and auto-flagged
  critical moments to `game_marimo.py` — both are Jupyter/`display()`-side-effect-only
  today and were left out of the marimo notebook, which currently only covers looking at
  one position's candidates.
- `notebooks/__marimo__/session/Chess.py.json` is a stale session artifact for a
  different, still-nonexistent `Chess.py` (predates the `Position.ipynb` rename) —
  unrelated to the new `game_marimo.py` file; still safe to ignore.
