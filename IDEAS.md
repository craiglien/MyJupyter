# IDEAS.md

Scratch notes — promote into `TASKS.md` or `DECISIONS.md` once they firm up.

## General pattern: config / build / run / entrypoint (not chess-specific)
This project's `config.sh` / `build.sh` / `run.sh` / `entrypoint.sh` follow a reusable
pattern worth remembering independent of this repo:

- **Config file** (sourced by the other scripts, never run standalone): the small set of
  values build-time and run-time both need to agree on — image name/tag, host↔container
  path mappings, ports, host UID/GID. Centralizing these keeps the scripts from drifting
  out of sync.
- **Build script** (run occasionally, whenever the image definition changes): produces the
  image. If it needs to extract an artifact that's environment-dependent (e.g.
  architecture-specific) and shouldn't be permanently baked into the final image, build a
  second throwaway image targeting just that stage, spin up a disposable container from
  it, `cp` the artifact out to the host, then delete the container — guarantees the
  artifact matches the *build environment's* real characteristics instead of an assumption
  baked in at image-definition time.
- **Run script** (run every session): starts a new container with `--rm` (disposable, no
  accumulation of stopped containers), publishes whatever ports the container exposes,
  bind-mounts any directory that needs to survive past the container's life or be edited
  directly from the host, and passes in env vars (commonly host UID/GID) for the
  entrypoint to consume.
- **Entrypoint script** (the image's `CMD`, baked in at build time — unlike bind-mounted
  content, edits need a rebuild, not just a restart, to take effect): reconciles the
  container's internal user with the host UID/GID so bind-mounted writes come out
  host-owned, launches the actual long-running process(es) (backgrounded if there's more
  than one), and traps signals so `docker stop`/Ctrl-C shuts every backgrounded child down
  cleanly and the container exits if any one of them dies unexpectedly.

The asymmetry worth remembering: bind-mounted paths reflect host edits immediately;
anything `COPY`'d into the image at build time requires a rebuild to pick up a change,
even though a plain container restart looks like it should be enough.

- Pin `stockfish/src` to a specific tagged Stockfish release (currently an untracked
  snapshot — worth recording which version/commit it came from for reproducibility).
- The current `ARCH=x86-64` / `ARCH=armv8` build selection is a conservative baseline
  (no AVX2/BMI2/dotprod). Could offer an opt-in optimized build (e.g. via a Docker
  build-arg) if engine analysis speed becomes a bottleneck.
- `notebooks/__marimo__/session/Chess.py.json` exists but there's no `Chess.py` — marimo
  was apparently pointed at `Chess.ipynb` at some point. Worth deciding whether marimo is
  an intentional alternate notebook interface for this project or just a one-off.

## Deeper explanations for the reply move and beyond
Three options considered for explaining *why* the engine expects a given reply (and
possibly the move after that), in increasing cost. 1 and 2 promoted to `TASKS.md` /
`DECISIONS.md` for implementation; 3 stays here as a future on-demand extension.

- Idea 1 (free): run the existing `classify_move()` machinery on the opponent's reply
  (and the following move) instead of showing a bare SAN string — reuses data already in
  `pv`, no extra engine calls.
- Idea 2 (opt-in, new engine calls): a new function that recurses the `moves()`
  ranking-table-plus-narrative approach one ply deeper — analyze the position after a
  chosen candidate move with a fresh multipv call, so the opponent's reply is explained
  by ranking it against their own alternatives, the same way we already explain our own
  top move against ours.
- Idea 3 (not being built now): chain Idea 2 again one more ply down (our best follow-up
  after their reply), for a small explained game-tree. Cost compounds fast — each hop is
  another multipv call — so this should stay an on-demand, one-line-at-a-time call rather
  than anything automatic, if it's ever built.

## v2: hybrid Stockfish + LLM narrative
Not scheduled. The current explanation text (`describe_move_reason()`, `describe_gap()`,
`describe_score()` in `position.py`) is template-formatted strings built directly from
Stockfish facts (`classify_move()` dicts, `Score`/`PovScore` objects, PVs). A future
version wants to pair Stockfish with an LLM API to generate richer, more natural
narrative — e.g. explaining a whole sequence of actual moves in prose, not just one
position's ranked candidates. For that swap to be additive rather than a rewrite, keep
the fact-computation functions (`classify_move`, the raw engine `info`/PVs, eval numbers)
separate from the narrative-formatting functions, so an LLM step can consume the same
facts and produce prose without touching engine-interaction code.

## Whole-game analysis notebook (new module `gac.py`)
`cc.py` explains a single position at a time (from a FEN). The next step is a second
notebook, alongside `Chess.ipynb`, that has a sense of a whole *game* and can narrate its
strategy — built on a new `gac.py` module, reusing `cc.py`'s existing helpers
(`classify_move`, `_analyze`, `moves`, `explain_reply`) rather than duplicating them. (Named
`gac.py`, not `gc.py` — `gc` is a compiled-in Python builtin module and can never be
imported under that name; see `DECISIONS.md`.)

- Input: a full PGN, pasted as-is into a single notebook cell as a triple-quoted string
  (`pgn_text = """..."""`), parsed the same way `cc.py`'s existing `pgn()` function already
  does (`chess.pgn.read_game(io.StringIO(pgn_text))`). No reformatting required — copy the
  PGN, paste it, run the cell.
- Core mechanism: an eval curve — walk every ply of the parsed game with a cheap engine
  pass (low time, multipv=1) to get the evaluation after each move.
- Move-quality classification: compare each move's eval to the best available at that
  position (centipawn loss), label Best/Good/Inaccuracy/Blunder — reusing the exact
  tier boundaries `cc.py`'s `describe_gap()` already uses for "gap vs best."
- Critical-moment detection: flag the plies with the largest eval swings — these, and only
  these, get a deeper multipv drill-down via `cc.py`'s existing `moves()`/`explain_reply()`,
  keeping engine time bounded instead of running deep analysis on every move.
- Phase detection: opening/middlegame/endgame via move count + material heuristics, so the
  narrative can shift register (e.g. "still in known theory" vs. "the position has
  simplified into an endgame").
- Stockfish result cache: an on-disk cache (JSON, under `./data`, gitignored as a derived
  artifact) keyed by `(FEN, multipv, time_limit, stockfish_version)` — the version comes
  from the engine's UCI `id` handshake (`engine.id["name"]`), so a rebuilt/upgraded
  Stockfish naturally gets a different key instead of silently reusing stale evals. Each
  entry also records a timestamp for visibility/debugging, but does NOT auto-expire —
  entries stay valid until manually cleared or until the version in the key changes. This
  matters most for the exact workflow of restarting the kernel and re-running all cells,
  which would otherwise redo the entire eval sweep from scratch every time. Optional
  future extension: TTL-based auto-expiry (e.g. entries older than N days get recomputed
  even if the key still matches) — not needed for the first version, but the recorded
  timestamp is what would make it possible to add later without a cache format change.

## `game_marimo.py` candidate-picker UX ideas

- "Don't" list (name TBD) — promoted to `TASKS.md`, design in progress there. (Original
  framing here was wrong: the top-5 `multipv` candidate list can't supply these moves,
  since multipv only ever returns strong moves — a real trap won't appear in it. Settled
  on scoring a targeted set of tempting-looking moves instead, via `root_moves=`.)
- Preview a candidate move "in play" — a way to see the board with a given candidate move
  actually made on it, without committing to it as the selected/analyzed line. Scope: the
  candidate-move picker in `game_marimo.py` specifically (where `render_candidate_html`
  already renders a board-with-move view for the selected radio choice) — this would let
  you spot-check other candidates' resulting positions without changing the selection.
  Two mechanisms considered, both still on the table (2026-09-09):
  - Hover (preferred): since `render_candidate_html()` builds each candidate's board+
    arrow purely from data `rank_candidates()` already computed, all candidates' boards
    could be pre-rendered up front — no extra Stockfish calls — then shown via plain CSS
    `:hover` next to the option being pointed at. Likely no server round-trip needed at
    all, unlike marimo's usual click-driven reactive-state model.
  - Right-click/context menu — noted as a fallback in case hover doesn't work well on
    touch/trackpad interactions.
- Quick-append move box above `pgn_text` (2026-09-22): a small text input placed right
  above the `pgn_text` cell in `game_marimo.py` — type a SAN move, it appends to the end
  of the PGN move string and nothing else. Deliberately just one cell, no engine call of
  its own — unlike "Try your own move" below the board, which scores the move immediately.
  Downstream cells (`sweep_game`, the board, candidates) still re-run automatically since
  they already depend on `pgn_text` — that's normal marimo reactivity, not something this
  widget needs to trigger itself. Still unscoped: whether the appended move needs a
  legality check first (parsing against the *current last position* in `records`, the same
  way the try-your-own-move panel does) or just gets appended blind and lets `sweep_game`
  surface a parse error if it's illegal; and the move-number/color prefix formatting
  (`"5."` vs `"5..."`) needed to keep the resulting string valid PGN.

## marimo's single-shared-kernel-per-notebook behavior (discovered 2026-09-22)
While live-verifying "What's risky" with a throwaway Playwright script, found that
`marimo edit` binds one running kernel to the notebook file — every new browser connection
(a second tab, a fresh Playwright session, whatever) attaches to that *same* kernel and
inherits whatever state (current ply, board flip, etc.) was last left there. A second
connection opens read-only ("You are currently connected as a reader") until it explicitly
clicks "Take over," which then makes it the sole editor and demotes any other viewer to
read-only. This is presumably intentional upstream behavior (marimo's collaborative-editing
safety model), not a bug in anything we built — but it means today, opening this notebook
in two tabs (e.g. one on a laptop, one on a phone, or two people at once) does NOT give two
independent views; they fight over the one editable session.

Not scoped or decided whether this is worth fixing, and if so how — options that come to
mind: switch to `marimo run` (app/view mode) for a genuinely read-only second viewer instead
of the reader/"Take over" editor model; accept it as-is and just document the constraint (in
`CLAUDE.md` or a future `README.md`); or, if multiple simultaneous independent sessions ever
actually matter, look into whether marimo supports one-kernel-per-connection at all. Worth
revisiting if the Game Collections or Opening-prep notebooks (see `TASKS.md` Backlog) end up
wanting multiple people/tabs poking at the same notebook concurrently.
