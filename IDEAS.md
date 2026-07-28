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
