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

## Study track (new, separate notebook pair — `study.py` / `study_marimo.py`)
Status 2026-10-07: Phases 1-5 DONE — the whole `more_chess_study.md` spec is implemented and
verified. Phase 6 (below) stays parked, not built — it's gated on an actual caching
bottleneck showing up in normal use, and none has. Next step is normal use and testing, not
more building; revisit Phase 6 only if sweeps actually get slow.

Started 2026-10-07, source spec is `more_chess_study.md` (a Gemini chat). A second,
additive notebook pair — mounted at `/study` once `study_marimo.py` exists, same as any
other `*_marimo.py` file — not a replacement for `game_marimo.py`/`collections_marimo.py`,
which keep working exactly as they do today, including the landing-page notes file. See
`DECISIONS.md` for the naming/reuse rationale.

Reuse-first throughout: no duplicate engine invocation, PGN parsing, or caching — build on
`position.py` (`open_engine()`, `classify_move()`, the Stockfish cache) and `game.py`
(`sweep_game()`, ply records) rather than re-implementing any of it in `study.py`.

1. **Scaffolding** — DONE 2026-10-07. `study.py` (`load_game()`, a thin passthrough to
   `game.sweep_game()`) and `study_marimo.py` (paste-a-PGN box, in-memory only — no disk
   persistence yet, unlike `game_marimo.py`'s `current_game.pgn` — plus a First/Prev/Next/
   Last stepper and board render). Mounted at `/study` automatically via `serve.py`.
   Verified in an isolated container: default game renders a board, the stepper works, and
   loading a shorter pasted game while deep into a longer one clamps the ply instead of
   raising `IndexError`.
2. **Colorblind dual-panel chart** — DONE 2026-10-07. `study.material_imbalance()` (pure
   `python-chess`, reads each ply's `fen_after`, no new engine calls) and
   `study.study_figure()` (blue/orange eval curve, never red/green, over a stacked
   material-imbalance bar chart, five colorblind-safe piece-type hues). Click-to-jump on
   either panel, same pattern as `game_marimo.py`'s eval chart, plus a dashed cursor line
   at the current ply. Verified: `material_imbalance()` matches a hand count for a Ruy
   Lopez bishop-for-knight exchange, and the browser shows all 5 piece-type bar traces and
   a working click-to-jump.
3. **Captures timeline strip** — DONE 2026-10-07. `study.captures_timeline()`: a third
   chart row with a Unicode glyph (outline = White, filled = Black) at the ply of every
   capture, including en passant. No new engine calls. Verified: matches a hand count for a
   Ruy Lopez exchange and a separate en-passant game, and both glyphs render on the actual
   chart in a browser.
4. **Pawn-structure detection** — DONE 2026-10-07. `study.pawn_structure()`: doubled,
   isolated, backward, passed pawns, and pawn-island count, per side. Pure `python-chess`,
   no engine calls. `study.pawn_structure_html()` renders badges with plain-English
   definitions on hover (`PAWN_STRUCTURE_GLOSSARY`). Documented as the standard simplified
   heuristics, not formal definitions. Verified against two hand-traced FEN positions
   covering all five facts for both colors — every field matched the hand trace exactly —
   plus a doubled-pawn badge confirmed rendering in a browser.
5. **Tactical & positional motif detection** — DONE 2026-10-07. Pins and skewers (absolute
   and relative, one shared ray-scan function interpreted two ways), forks, discovered
   attacks (the one move-dependent detector), fianchettoed bishops, open/semi-open files,
   outposts, king safety, and the Exchange imbalance — all in `study.py`, rendered as
   hover-glossary badges via `study.concepts_html()`. Pure `python-chess`/geometry, no engine
   calls, documented as heuristic rather than a tactics engine. Verified against 9 hand-built
   FEN positions (one per motif) — every one matched exactly — plus a real game position
   showing a fork, fianchetto, pin, semi-open file, and a discovered attack simultaneously in
   the browser.
6. **Caching strategy review** (stretch, optional) — compare `mo.persistent_cache` against
   the existing `engine_cache.json` approach; only worth doing if caching actually becomes
   a bottleneck for this notebook, not on spec alone.

## Endgame studies track
Decided 2026-10-12, see `DECISIONS.md`. Content lives in the `data/endgame_studies/`
submodule (its own repo, local-only, no remote — see its `README.md` for the per-study
folder convention); this track is only the feature half, built reuse-first on
`position.py`/`game.py` like the study track. No new `*_marimo.py` notebook shows up on the
landing page or in the nav bar until Phase 2 creates one — both already auto-discover via
glob, so nothing extra is needed there once it exists.

**Phase 1 — content. DONE 2026-10-12.** Created the `endgame_studies` repo (local-only,
`~/src/endgame_studies`) and added it as a submodule at `data/endgame_studies/`, with the
first entry (`kaminer_botvinnik_1925/`: FEN + PGN for both the +a4 and original positions,
each with the composer's main line and Stockfish's best defense, plus notes.md and the
source transcript). Verified: all lines legal and composer's lines checkmate via
python-chess (`chess.pgn.read_game()` round-trip), both inside and outside the container.

**Phase 2 — load & browse. DONE 2026-10-12.** New `endgame_studies.py` module +
`endgame_studies_marimo.py` notebook.
- Study and variant pickers, listing via glob (`data/endgame_studies/*/`, `position*.fen`).
- Renders `notes.md` and the starting position.
- Milestone verified: `/endgame_studies` picks `kaminer_botvinnik_1925`, either variant, shows
  the right notes; appears automatically on the landing page and in the nav bar.

**Phase 3 — solving flow. DONE 2026-10-12.** Move input ended up being mouse drag-and-drop
(not just SAN text entry as originally planned here) — see DECISIONS.md's board-widget entry
for why plain SAN-only turned out not to be enough on its own.
- `board_widget.py` (new, shared — see DECISIONS.md): a drag-and-drop board. A SAN text box
  stays alongside it as a fallback, per request — either input works.
- After each of your moves, Black auto-replies from the recorded composer's-line PGN.
- A deviation the recorded line doesn't cover is reported as "off the recorded line" and play
  continues freely for both sides from there, rather than guessing at a reply or locking the
  board.
- Milestone verified in an isolated container via Playwright, including a real mouse-drag
  simulation: played `1.g4+ Kh4 2.Bh6! Qxh6 3.Qh2+ Kg5 4.Qd2+ Nf4 5.Qd8#` move by move on both
  variants to "Solved!", with the expected capture count; an unrecorded-but-legal move is
  flagged off-script (free play still allowed); a truly illegal move is rejected with a
  message, not applied; Reset returns to ply 0.

**Phase 4 — reveal (not started).**
- A "Reveal" control showing the composer's main line and the engine's best defense side by
  side, with each line's existing per-move PGN comments rendered, not just a bare move list.
- Milestone: revealing `kaminer_botvinnik_1925` shows both lines with their comments
  (clearance/decoy/skewer/X-ray notes) for both variants.

**Phase 5 — live engine check (stretch, optional).** Only build if Phases 2-4 feel
incomplete without it — most of this study's value is in the recorded lines + notes, not a
general solver.
- When you deviate from a recorded line, let you ask "is this still winning?" via a direct
  `position.py` Stockfish call, reusing the existing engine-cache machinery, rather than a
  recorded reply.

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
