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
- Stop `git status` from showing a modified file just from normal use (idea stage,
  discussed 2026-09-09, not yet written down until now): `pgn_text` — "which game am I
  looking at" — lives inside the git-tracked `game_marimo.py`, so every time you switch
  games it shows up as a code diff needing a commit, even though it's working state, not
  a code change. Two-phase plan, Phase 1 a strict subset of Phase 2 so doing it first
  doesn't box in the second:
  - Phase 1 (small, self-contained): move the "current game" value out of
    `game_marimo.py` into a file under `./data` (bind-mounted, gitignored like
    `engine_cache.json`/`debug.log`, survives container restarts). The notebook reads it
    at startup instead of a hardcoded triple-quoted string; a text box lets you overwrite
    it. Switching games becomes a data-file edit, nothing to commit, state still there
    next time.
  - Phase 2: this is exactly the plumbing the Game Collections item below needs anyway —
    "selecting a game auto-fills pgn_text" is the same mechanism, just fed from a chosen
    collection instead of a single text box.
- Opening-prep notebook with Gemini chat (idea stage, not scoped — 2026-09-09): a new
  `opening_marimo.py`, separate from `game_marimo.py`, focused on opening exploration.
  Direction settled via MCQ discussion:
  - Keeps the existing Stockfish candidate-picker for verified move quality, plus a
    Gemini chat panel alongside it purely for narrative ("type in a few moves, ask what
    the options are for the next 3-4 moves, which famous games/players played this
    style"). Engine facts and LLM narrative stay visually separate, same reasoning as the
    v2 hybrid-narrative idea below.
  - Famous-game references get grounded against a local PGN collection (not just trusted
    from Gemini's training) — depends on the Game Collections item below existing first,
    or at least a "famous games" collection file, so answers are checked against real
    PGN data instead of the model inventing specifics.
  - Gemini API key stored under a new `.auth/` directory at the repo root (gitignored,
    added 2026-09-09), read by `config.sh`/`run.sh` and passed into the container as an
    env var — same untracked-on-host delivery pattern already used for `LOCAL_UID`/
    `LOCAL_GID`, just sourced from a dedicated gitignored file instead of the shell env.
  - Still unscoped: which Gemini model/SDK, how the chat UI embeds in marimo, exact
    matching logic from "a few moves" to "which famous games opened this way," and
    whether this needs container network egress (not needed by anything today).
  - Noted 2026-09-09: pair this with the already-shipped "What's risky" candidate-list
    flagging (`render_candidate_html()`/`_describe_continuation()`, see `DECISIONS.md`)
    once this chat exists — Stockfish stays the objective source of *what's* risky, the
    AI adds plain-language *why*/story on top, rather than trusting the AI's own risk
    judgment standalone. "What's risky" was called out as genuinely good education worth
    building on, not just a UI tweak.
- Tutorial notebook (idea stage, not scoped — 2026-09-11): a new sibling notebook +
  module, focused on walking through one whole game as a guided lesson. Direction settled
  via MCQ discussion:
  - Game input: paste a PGN directly, same convention as `game_marimo.py` — no picker/AI
    game-selection for this idea (unlike the Opening-prep notebook above).
  - Focus model: you mark one ply/move as "the point in time I'm interested in"; the rest
    of the game gets light step-through treatment, but the moves immediately before and
    after that focal point get a real breakdown — not uniform depth across every move.
  - Breakdown content: engine facts (reusing existing candidate/eval/quality/"What's
    risky" machinery) paired with AI narrative once the Gemini chat exists — same
    objective-facts-plus-AI-narrative split already decided for the Opening-prep notebook
    and the What's-risky link above, not an either/or.
  - Still unscoped: exact mechanism for marking the focal ply, how many plies before/after
    count as "before and after," and whether a first cut can ship with engine-only
    breakdown before the Gemini plumbing exists.
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
