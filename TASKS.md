# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- Return to the game side (`game.py`/`game_marimo.py`/`Game.ipynb`) — not touched in the
  last 48h (as of 2026-08-19) while attention has been on `position.py`/`Position.ipynb`,
  which is now working well.
- "Don't" list for the candidate picker (promoted from `IDEAS.md`, design in progress):
  a dedicated area shown *before* the top-5 good candidates, listing tempting-looking-but-
  bad moves, each explained in the same depth the good candidates already get — not just a
  one-line reason. Correction to the original idea: the top-5 `multipv` list can't supply
  these moves, since multipv only ever returns strong moves — a real trap (a capture that
  hangs a piece, a natural push that drops material) won't appear in it. Mechanism decided:
  score only "tempting-looking" moves, not every legal move.
  - Selection heuristic (which moves count as "tempting"): captures and checks not
    already in the top-5 PV are the clear cases. "Moves toward the center" still needs a
    concrete rule (e.g. destination square in the central 4 or 16 squares?) — open.
  - Scoring mechanism: `chess.engine.SimpleEngine.analyse()` supports a `root_moves=`
    argument to restrict the search to a specific move list — call it with just the
    tempting-move subset (`multipv=len(subset)`) instead of a full-board multipv sweep.
    `position.py`'s `_analyze()` doesn't expose `root_moves` yet; would need extending
    (or a sibling function) to accept it.
  - Explanation depth: each don't-list entry's "why" must include the 2-3-ply punishing
    sequence, not just a static eval number — e.g. "looks tempting because it captures the
    pawn, but after ...Qd4! forking the knight and rook, White wins material." Stockfish's
    own `pv` for a `root_moves`-restricted move already contains this continuation, so this
    reuses `_describe_continuation()` verbatim (the same function `render_candidate_html()`
    already calls for the selected good candidate) — no new continuation logic needed.
  - Quality label plumbing: `_gap_tier()` already computes a Best/Good/Inaccuracy/Blunder
    label, but `describe_gap()` currently discards it (`note, _ = _gap_tier(gap)`) — the
    don't-list will need that label surfaced, not just the prose note.
  - Display: its own area above the candidate radio buttons in `game_marimo.py`, per the
    original idea — separate from, not mixed into, the good-candidates list.
- Decide on a workflow fix for the `Game.ipynb` autosave-clobbering risk: a live browser
  tab's autosave can silently overwrite direct file edits to the same notebook, and vice
  versa. Happened once already this session. See `DECISIONS.md`. Note: `game_marimo.py`
  doesn't have this specific failure mode (no autosave/JSON layer), but `Game.ipynb`
  itself is still Jupyter and still exposed to it.

## Backlog
- Flesh out `README.md` (currently a 16-byte stub) per the content rule in `CLAUDE.md`:
  what the project is, how it's structured, and copy-pasteable, up-to-date build/run/test
  commands.
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
