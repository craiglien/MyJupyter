# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- **Debug (divide and conquer, one issue at a time): "why does it think it's Black's
  move?"** Reported while running chess.com's 2026-08-09 Daily Puzzle through
  `game.analyze_game()` in `Game.ipynb`. Symptom not yet pinned down to an exact line of
  output — session ran out of time before the exact text could be pasted.
  - PGN used (pasted into the gitignored `Game.debug.ipynb`, not saved anywhere durable —
    preserved here so it can be reproduced):
    ```
    [White "Josten, Gerhard"]
    [Black "Study + Pawn on c4"]
    [Result "*"]
    [FEN "5K1B/4p3/P7/8/2P2P2/1k2P1n1/7P/7r w - - 0 1"]
    [Link "https://www.chess.com/daily/2026-08-09"]

    1. a7 Rxh2 2. Bb2 Kxb2 3. Kg8 Nf5 4. a8=Q *
    ```
  - Ruled out already: `game.sweep_game()`'s per-ply mover attribution on this exact PGN
    is correct (White plays first, matching the FEN's `w` to move; alternates correctly
    through all 7 plies). The critical-moment labels from `analyze_game()`
    (`1...Rxh2`, `2.Bb2`, `3...Nf5`) are also correct standard PGN notation, not a mislabel.
  - Suspected but unconfirmed: `position.pgn(pgn_text, 'w')` (the legacy single-position
    path in `Position.ipynb`) plays the PGN to its *end* and returns that ending position
    — after `4. a8=Q`, it's genuinely Black to move. If that's what was looked at while
    expecting "the puzzle position" (the FEN header, before any moves), that's a real
    position — but not what someone solving a puzzle wants to see. Not yet confirmed this
    is actually what was looked at.
  - Next single step: get the exact pasted output/quote showing "Black's move" (or a
    screenshot), then trace it to one specific function call before touching any code.
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
