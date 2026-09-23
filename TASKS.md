# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
(none — the "What's risky" candidate-list note is now live-verified, see `DECISIONS.md`)

## Backburner
Marimo migration work is good enough for now — was explicitly deprioritized in favor of the
"What's risky" feature (2026-08-24), which is now done and live-verified (2026-09-22, see
`DECISIONS.md`). Revisiting is open again, whenever picked back up.

- Return to the game side (`game.py`/`game_marimo.py`/`Game.ipynb`) — not touched in the
  last 48h (as of 2026-08-19) while attention has been on `position.py`/`Position.ipynb`,
  which is now working well.
- Convert `Position.ipynb` to marimo (2026-09-18: raised in priority, not just "still
  open" — Jupyter itself is now retired, per `DECISIONS.md`, so there is currently NO
  interactive way to use `Position.ipynb`'s functionality at all until either this
  conversion happens or Jupyter is manually re-enabled in `entrypoint.sh`. The file
  itself is untouched, per standing convention — only the server that could open it is
  gone.) The `Game.ipynb` autosave-clobbering risk noted here previously is moot for the
  same reason — no live Jupyter session left to autosave anything.
- Port `show_sweep()`/`show_critical_moments()`'s eval-curve chart and auto-flagged
  critical moments to `game_marimo.py` — both are Jupyter/`display()`-side-effect-only
  today and were left out of the marimo notebook, which currently only covers looking at
  one position's candidates.

## Backlog
1. Stop `git status` from showing a modified file just from normal use (idea stage,
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
   - Phase 2: this is exactly the plumbing Game Collections already needed (now shipped,
     see `DECISIONS.md`) — "selecting a game auto-fills pgn_text" is the same mechanism,
     just fed from a chosen collection instead of a single text box.
   - Phase 3, idea stage (2026-09-23, researched via Gemini — also motivated by a separate
     annoyance: `marimo edit` rewrites the notebook's own `__generated_with` header on disk
     just from browser interaction, another source of incidental diffs beyond `pgn_text`):
     serve notebooks via `marimo run` instead of `marimo edit`. Read-only app mode — no code
     editing from the frontend at all, so the `.py` file is never written to, period; `git
     status` stays clean by construction rather than by moving one variable out. `mo.ui.*`
     widgets (buttons, text boxes, dropdowns) still work fine in this mode, only cell-source
     editing is disabled. A second strategy Gemini offered alongside this one was explicitly
     rejected: copy the tracked notebook into a gitignored working directory (e.g. a
     `.something/` dir) and run/edit that copy instead, so all the runtime disk-writes land
     on the untracked copy while the tracked original stays pristine. Rejected as extra
     mechanics for the same outcome `marimo run` gets for free — it needs a copy-in step
     before each session, a manual sync-back step whenever a real code edit (not just
     `pgn_text`/game selection) needs to actually reach git, and now two on-disk copies of
     every notebook that can silently drift, with no automatic way to tell which one is
     "real" at a glance. Same shape as the manual revert-then-restore dance already used all
     session for `pgn_text` edits, just formalized into a parallel directory structure and
     an ongoing sync burden, instead of removing the write entirely.
     - Depends on Phase 1/2 above landing first: today, changing which game you're looking
       at means editing `pgn_text`'s source directly — the entire reason `marimo edit` mode
       is used at all right now. Once that's UI-widget-driven (Phase 1's text box, or
       Phase 2's collection picker) instead of a hardcoded string, switching to `marimo run`
       stops losing any real functionality.
     - Not scoped: whether this is an entrypoint.sh flag change, a per-notebook choice, or
       needs both modes available (edit for actually authoring new notebook cells, run for
       day-to-day play).
2. Opening-prep notebook with Gemini chat (idea stage, not scoped — 2026-09-09): a new
   `opening_marimo.py`, separate from `game_marimo.py`, focused on opening exploration.
   Direction settled via MCQ discussion:
   - Keeps the existing Stockfish candidate-picker for verified move quality, plus a
     Gemini chat panel alongside it purely for narrative ("type in a few moves, ask what
     the options are for the next 3-4 moves, which famous games/players played this
     style"). Engine facts and LLM narrative stay visually separate, same reasoning as the
     v2 hybrid-narrative idea below.
   - Famous-game references get grounded against a local PGN collection (not just trusted
     from Gemini's training) — Game Collections (see `DECISIONS.md`) now exists for this;
     needs at least a "famous games" collection file added under `./data/collections/`, so
     answers are checked against real PGN data instead of the model inventing specifics.
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
3. Tutorial notebook (idea stage, not scoped — 2026-09-11): a new sibling notebook +
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
4. Don't-list "moves toward the center" selection heuristic: v1 (shipped) only scores
   captures and checks as "tempting"; a concrete rule for center-ward quiet moves (e.g.
   destination square in the central 4 or 16 squares) was left out. Add if it turns out
   to matter in practice.
5. `notebooks/game.py` has no `explain_reply()`-chained narrative for critical moments —
   see IDEAS.md's Idea 3 (deferred).
6. Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
   (see `IDEAS.md`) instead of an untracked snapshot.
