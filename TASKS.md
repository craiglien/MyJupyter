# TASKS.md

## Active
(none — paused; chess is a hobby project, picking back up whenever)

## Up next
(none — the "What's risky" candidate-list note is now live-verified, see `DECISIONS.md`)

## Backburner
- Convert `Position.ipynb` to marimo (2026-09-18: raised in priority, not just "still
  open" — Jupyter itself is now retired, per `DECISIONS.md`, so there is currently NO
  interactive way to use `Position.ipynb`'s functionality at all until either this
  conversion happens or Jupyter is manually re-enabled in `entrypoint.sh`. The file
  itself is untouched, per standing convention — only the server that could open it is
  gone.) The `Game.ipynb` autosave-clobbering risk noted here previously is moot for the
  same reason — no live Jupyter session left to autosave anything.
  Everything else that was on this list — returning to the game side, and porting the
  eval-curve chart and critical moments to `game_marimo.py` — is done; see `DECISIONS.md`.

## Backlog
1. Opening-prep notebook with Gemini chat (idea stage, not scoped — 2026-09-09): a new
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
2. Tutorial notebook (idea stage, not scoped — 2026-09-11): a new sibling notebook +
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
3. `notebooks/game.py` has no `explain_reply()`-chained narrative for critical moments —
   see IDEAS.md's Idea 3 (deferred).
4. Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
   (see `IDEAS.md`) instead of an untracked snapshot.
5. Game database as a git submodule (idea only, 2026-10-05): keep the game collections in
   their own git repository, attached to this project as a submodule. No such repository
   exists yet, and this repo has no `.gitmodules` or submodule entry. Open questions: where
   it would mount (likely `data/collections/`, which `game_collections.py` already reads,
   replacing the tracked `fischer.pgn`); how a fresh clone would fetch it (`git submodule
   update --init`, and whether `run.sh` or the setup notes need to say so); and how it
   fits the `data/collections/` git-tracking convention in `CLAUDE.md`.
