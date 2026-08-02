# IDEAS.md

Scratch notes — promote into `TASKS.md` or `DECISIONS.md` once they firm up.

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

## Whole-game analysis notebook (new module `gc.py`)
`cc.py` explains a single position at a time (from a FEN). The next step is a second
notebook, alongside `Chess.ipynb`, that has a sense of a whole *game* and can narrate its
strategy — built on a new `gc.py` module, reusing `cc.py`'s existing helpers
(`classify_move`, `_analyze`, `moves`, `explain_reply`) rather than duplicating them.

- Input: a full PGN, pasted as-is into a single notebook cell as a triple-quoted string
  (`pgn_text = """..."""`), parsed the same way `cc.py`'s existing `pgn()` function already
  does (`chess.pgn.read_game(io.StringIO(pgn_text))`). No reformatting required — copy the
  PGN, paste it, run the cell.
- Core mechanism: an eval curve — walk every ply of the parsed game with a cheap engine
  pass (low time, multipv=1) to get the evaluation after each move.
- Move-quality classification: compare each move's eval to the best available at that
  position (centipawn loss), label Best/Good/Inaccuracy/Mistake/Blunder.
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
