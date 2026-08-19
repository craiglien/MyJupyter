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

- "Don't" list (name TBD) — alongside the ranked good-move candidates, surface a short
  list of tempting-looking but bad moves, so the picker warns you away from traps as well
  as pointing you toward good moves. Basis: reuse the existing `move_tag`/quality
  classification already computed for the candidate ranking (Best/Good/Inaccuracy/
  Mistake/Blunder) rather than building new trap-detection analysis — filter for the
  low-quality end of the same ranked list instead of a separate eval-swing check. Shown
  as a preamble/caption above the candidate radio buttons in the picker cell.
- Preview a candidate move "in play" — a way to see the board with a given candidate move
  actually made on it, without committing to it as the selected/analyzed line. Considered
  mechanism: right-click (or similar context menu) on an entry in the candidate radio
  list to trigger the board preview. Scope: the candidate-move picker in
  `game_marimo.py` specifically (where `render_candidate_html` already renders a
  board-with-move view for the selected radio choice) — this would let you spot-check
  other candidates' resulting positions without changing the selection.
