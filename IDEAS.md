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
