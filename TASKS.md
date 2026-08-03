# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- Try `gac.at_move(records, move_number, side)` against a real full game with a specific
  remembered tactical moment (motivating example: "I thought I had the opponent's queen
  trapped a couple of moves earlier, but missed an escape square") — this workflow is
  built and unit-tested but not yet exercised against a real game end to end.
- Decide on a workflow fix for the `Game.ipynb` autosave-clobbering risk: a live browser
  tab's autosave can silently overwrite direct file edits to the same notebook, and vice
  versa. Happened once already this session. See `DECISIONS.md`.

## Backlog
- `notebooks/gac.py` has no `explain_reply()`-chained narrative for critical moments —
  see IDEAS.md's Idea 3 (deferred).
- Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
  (see `IDEAS.md`) instead of an untracked snapshot.
