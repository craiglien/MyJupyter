# CLAUDE.md (project)

Cross-project rules (Python/uv conventions, git conventions, bootstrap methodology) live in
the user-level `~/.claude/CLAUDE.md`, not here. This file is project-specific only.

## What this is
A Jupyter Notebook environment, Dockerized, for experimenting with chess via `python-chess`
and a locally-built Stockfish engine.

## What runs it
- `./build.sh` — builds the `jupyter-notebook` Docker image (see `config.sh` for the name),
  then separately builds the `stockfish-build` stage and `docker cp`s the compiled Stockfish
  binary out to `./stockfish-bin` on the host (gitignored artifact).
- `run.sh` (invoke as `bash run.sh` — no exec bit, by design) — runs the image, mounting
  `./notebooks` → `/app` and `./data` → `/data`, publishing the one stable port `$HOST_PORT`
  (default `12345`, see `config.sh`) plus a range `$MARIMO_PORT_START`-`$MARIMO_PORT_END`
  (default `12346`-`12350`) for individual notebook processes.
- `entrypoint.sh` — inside the container, maps the host UID/GID onto a `crun` user via
  `gosu`, then launches one `marimo edit` process per `*_marimo.py` file found under `/app`.
  With exactly one notebook, it runs directly on `$HOST_PORT`. With two or more (the
  current state, since `collections_marimo.py` was added — see `DECISIONS.md`), each gets
  its own port from the range above, and a generated landing page at
  `/srv/landing/index.html` linking to all of them is served on `$HOST_PORT` via
  `python3 -m http.server`. Jupyter is retired (not launched) — see `DECISIONS.md`/
  `TASKS.md`.

## Stack
- Base image: `ubuntu:24.04`.
- Python 3.10 via the `deadsnakes` PPA (pinned as the `python`/`python3` alternative).
- Pip packages: `jupyter`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `django`,
  `prettytable`, `cryptography`, `httpx<0.24`, `chess`.
- Stockfish 17: compiled from the vendored source at `stockfish/src` in a multi-stage
  Docker build (`stockfish-build` stage), with `ARCH` picked from `uname -m` inside that
  stage (`x86-64` or `armv8`) so the binary always matches the container's actual
  architecture — not the host's. See `DECISIONS.md`.

## Where data lives
- `./data` (mounted to `/data` in the container):
  - `data/engine_cache.json` is an on-disk Stockfish result cache (gitignored, disposable —
    see `notebooks/position.py`).
  - `data/collections/*.pgn` are user-curated game collections (one file per collection,
    multiple games per file via standard multi-game PGN) — tracked in git, not gitignored;
    add/edit files here directly, no rebuild needed. See `notebooks/game_collections.py`.
- `./notebooks` (mounted to `/app`) — the notebook files and their Python modules, layered:
  - `notebooks/position.py` — single-position/FEN analysis primitives: build a position
    from a FEN or PGN, get ranked candidate moves and explanations from Stockfish
    (`stockfish_path = "/usr/bin/stockfish"`), and drill into a specific reply/line. Also
    owns the Stockfish invocation (`open_engine()`) and on-disk result cache used by both
    layers. Driven interactively by `notebooks/Position.ipynb`.
  - `notebooks/game.py` — whole-game/PGN orchestration built entirely on `position.py`'s
    API (no duplicate engine-invocation or PGN-parsing logic): sweep every ply of a PGN
    for an eval curve and move-quality classification, flag critical moments, and jump to
    any named move. Driven interactively by `notebooks/Game.ipynb`.
  - `notebooks/game_collections.py` — lists collection files under `data/collections/` and
    the games inside one (each re-exported as a standalone `pgn_text` string via
    `chess.pgn`, ready for `game.sweep_game()` unchanged). Named `game_collections.py`, not
    `collections.py` — `collections` is a Python stdlib module name and would shadow it,
    the same class of naming collision `DECISIONS.md` documents for `gac.py`/`gc.py`.
    Driven interactively by `notebooks/collections_marimo.py`.
  - All three modules are versioned via their own `__ver__` constant (a semver string,
    printed on import) — bump MAJOR for breaking changes to a function's signature/
    behavior, MINOR for new backwards-compatible functions/features, PATCH for bug fixes
    only. Git log / `DECISIONS.md` cover the *why*; there's no separate changelog file.

## Hard constraints
- Never commit a pre-built, architecture-specific Stockfish binary directly (that's the bug
  this project already hit once — see `DECISIONS.md`). `stockfish/src` (source) is tracked;
  `stockfish-bin` (compiled artifact) is gitignored.
- `notebooks/__marimo__/` is a marimo runtime/session-state dir — gitignored, do not commit.
- `git add` explicit file paths only, never a directory (`git add -A`/`git add .`) — avoids
  accidentally staging unrelated in-progress edits (e.g. the user's own live notebook edits).
- Never install software via pipe-to-shell (`curl|bash`, `wget -O- | sh`, etc.); prefer
  verified release artifacts and explicit installation steps, matching how Stockfish is
  already built from vendored source rather than downloaded and piped.
- `README.md` must document what the project is, how it's structured, and how it's run,
  built, and tested — any command the user is meant to run themselves belongs there,
  copy-pasteable and kept up to date. Currently a stub; see `TASKS.md`.
