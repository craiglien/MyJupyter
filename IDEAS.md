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
- Preview a candidate move "in play" — RESOLVED 2026-10-04 via `render_candidate_previews_html()`
  (`position.py` 0.11.0, see `DECISIONS.md`): a row of thumbnails, one per candidate,
  pre-rendered from data `rank_candidates()` already computed, enlarged on hover with plain
  CSS — no extra Stockfish calls, no server round-trip. The hover mechanism from the two
  considered here.
- Quick-append move box above `pgn_text` — RESOLVED 2026-10-06 via `game.append_move()`
  (`game.py` 0.9.0, see `DECISIONS.md`): checks the SAN against the final position first
  (illegal moves are refused, never appended), and the move number/color prefix is written
  by chess.pgn's own exporter rather than typed by hand.

## marimo's single-shared-kernel-per-notebook behavior — RESOLVED by Phase 3
Discovered 2026-09-22 under `marimo edit`: one running kernel per notebook file, every new
browser connection (a second tab, a fresh Playwright session) attaching to that *same*
kernel and inheriting whatever state was last left there — a second connection opened
read-only until it clicked "Take over," fighting over the one editable session.

Resolved as a side effect of switching to `marimo run` (2026-09-24, see `DECISIONS.md`'s
Phase 3 entry) — empirically confirmed 2026-09-28: two simultaneous connections to the same
`marimo run` notebook show no "Take over"/"Reconnected" banner at all, both fully
interactive independently. Not deeply verified beyond that (e.g. whether stepping through
plies in one tab affects another's view), but the specific annoyance this entry was about —
fighting over one editable session — is gone.

## `marimo edit` doesn't auto-run a freshly started kernel — RESOLVED by Phase 3
Discovered 2026-09-22: a brand-new `marimo edit` kernel showed every cell as bare,
unexecuted source code until the floating "run all" control was clicked — meaning every
notebook sat blank after each container restart until someone opened it and clicked that.

Resolved by switching to `marimo run` (2026-09-24, see `DECISIONS.md`'s Phase 3 entry),
which auto-executes on load since it's meant to serve a finished app rather than an editing
session — confirmed during Phase 3's own verification.

## Traefik (or similar) reverse proxy, to get back down to one published socket — RESOLVED without a proxy
Resolved 2026-10-06 (see `DECISIONS.md`): a single uvicorn server running `notebooks/serve.py`
mounts every notebook under its own path (`/game`, `/collections`) and serves the landing page at
`/`, so only one port is published. marimo's own ASGI support made the proxy unnecessary. The rest
of the original reasoning below is kept for reference.

Not urgent — just an idea for cleaning up sockets, not a problem actually being hit today.

Right now `run.sh` publishes `$HOST_PORT` plus the entire `$MARIMO_PORT_START`-
`$MARIMO_PORT_END` range (see `config.sh`), because Docker port-publishing has to be fixed
at `docker run` time even though which notebook claims which port inside that range is
decided dynamically at container start (see the "Jupyter retired" decision in
`DECISIONS.md`). That's several published sockets for what's conceptually one service. A
reverse proxy (Traefik came up by name, but any WebSocket-capable one would do) sitting
inside the container could instead terminate everything on the one stable `$HOST_PORT` and
route to each notebook's internal port by path or hostname — collapsing the published range
back down to a single socket, with the landing page's links pointing at proxied paths
instead of raw ports.

Why this hasn't been done already: when reusing one port came up before (2026-09-22, see
the "single-notebook/no-landing-page refinement" in `DECISIONS.md`), a full reverse proxy
was explicitly the road not taken in favor of the simpler single-notebook direct-port
shortcut — marimo is a reactive server (WebSocket-based), so proxying it isn't just HTTP
path rewriting, it needs WebSocket proxying done correctly too. Worth a proper look if the
published port range ever actually becomes a nuisance (e.g. once several of the Backlog's
planned notebooks exist at once), but not worth the added moving part today.
