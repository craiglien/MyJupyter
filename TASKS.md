# TASKS.md

## Active
- Implement Idea 1: explain the opponent's expected reply (and the follow-up move) using
  `classify_move()`, instead of showing a bare SAN string. See `IDEAS.md` / `DECISIONS.md`.
- Implement Idea 2: new opt-in function that recurses the `moves()` ranking-table-plus-
  narrative approach one ply deeper, to explain *why* the engine expects that particular
  reply rather than the opponent's alternatives. See `IDEAS.md` / `DECISIONS.md`.

## Up next
(none — waiting on feature requests)

## Backlog
- Decide fate of tracked editor backup files (`build.sh~`, `config.sh~`, `Dockerfile~`,
  `Dockerfile.orig~`, `entrypoint.sh~`, `run.sh~`) — currently committed to git; likely
  safe to remove and gitignore `*~`.
- Confirm whether `data/athlete_events.csv` and `data/noc_regions.csv` (Olympic-athletes
  dataset) are actually used by anything in this project, or are leftover from an
  unrelated notebook and can be dropped.
- `notebooks/Chess.ipynb` has an uncommitted diff that is just notebook execution state
  (cell outputs/counts) — decide whether to reset it, or strip outputs before commit so
  this stops recurring.
- Decide whether `stockfish/src` should track a specific pinned Stockfish release/commit
  (see `IDEAS.md`) instead of an untracked snapshot.
