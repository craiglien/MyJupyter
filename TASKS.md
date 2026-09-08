# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
- Follow up on the "What's risky" candidate-list note just added to
  `render_candidate_html()`/`_describe_continuation()` (2026-08-24) — see `DECISIONS.md`.
  Only offline-verified so far (hand-built `FakeEngine` multipv result); not yet checked
  live in the running marimo notebook.

## Backburner
Marimo migration work is good enough for now — explicitly deprioritized in favor of the
"What's risky" feature above (2026-08-24). Revisit whenever that's done.

- Return to the game side (`game.py`/`game_marimo.py`/`Game.ipynb`) — not touched in the
  last 48h (as of 2026-08-19) while attention has been on `position.py`/`Position.ipynb`,
  which is now working well.
- Decide on a workflow fix for the `Game.ipynb` autosave-clobbering risk: a live browser
  tab's autosave can silently overwrite direct file edits to the same notebook, and vice
  versa. Happened once already this session. See `DECISIONS.md`. Note: `game_marimo.py`
  doesn't have this specific failure mode (no autosave/JSON layer), but `Game.ipynb`
  itself is still Jupyter and still exposed to it.
- Convert `Position.ipynb` to marimo too. `Game.ipynb`'s workflow got a marimo sibling
  (`game_marimo.py`, candidate-picker only) rather than a full replacement — Jupyter and
  marimo now run side by side in the container (see `DECISIONS.md`). Position-side
  conversion, retiring Jupyter entirely, and the `Game.ipynb` autosave-clobbering fix
  above are all still open.
- Port `show_sweep()`/`show_critical_moments()`'s eval-curve chart and auto-flagged
  critical moments to `game_marimo.py` — both are Jupyter/`display()`-side-effect-only
  today and were left out of the marimo notebook, which currently only covers looking at
  one position's candidates.

## Backlog
- Game Collections (scoped and ready, not yet built — 2026-08-26): user-curated named
  lists of games to page through (e.g. "Favorite Capablanca Endgames," "Ruy Lopez Opening
  Traps"). Design settled via MCQ discussion:
  - Data: `./data/collections/*.pgn`, one file per collection (filename → collection
    name), multiple games per file via standard multi-game PGN — bind-mounted, so adding
    or editing a collection needs no rebuild.
  - Code: new `collections.py` module listing available collection files and the games
    inside one, built on `position.parse_pgn()`/`chess.pgn`'s existing multi-game-read
    support — no duplicated PGN-parsing or analysis logic.
  - UI: a new sibling notebook (not a change to `game_marimo.py`) — collection picker,
    then Next/Prev buttons to step through games in the chosen collection (mirroring the
    existing ply-stepper's button pattern in `game_marimo.py`). Selecting a game
    auto-fills the new notebook's own `pgn_text`-equivalent, reusing the whole existing
    candidate-picker/risk-notes/try-your-own-move stack unchanged; if nothing's selected
    yet, it stays on whatever's currently loaded rather than resetting to empty.
- Don't-list "moves toward the center" selection heuristic: v1 (shipped) only scores
  captures and checks as "tempting"; a concrete rule for center-ward quiet moves (e.g.
  destination square in the central 4 or 16 squares) was left out. Add if it turns out
  to matter in practice.
- Flesh out `README.md` (currently a 16-byte stub) per the content rule in `CLAUDE.md`:
  what the project is, how it's structured, and copy-pasteable, up-to-date build/run/test
  commands.
- `notebooks/game.py` has no `explain_reply()`-chained narrative for critical moments —
  see IDEAS.md's Idea 3 (deferred).
- Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
  (see `IDEAS.md`) instead of an untracked snapshot.
- `notebooks/__marimo__/session/Chess.py.json` is a stale session artifact for a
  different, still-nonexistent `Chess.py` (predates the `Position.ipynb` rename) —
  unrelated to the new `game_marimo.py` file; still safe to ignore.
