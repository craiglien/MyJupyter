# TASKS.md

## Active
(none)

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
