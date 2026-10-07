"""Analysis for the study track: a second, additive notebook pair
(study.py/study_marimo.py) for richer visualizations and motif detection,
alongside — not replacing — game_marimo.py/collections_marimo.py. See
TASKS.md's "Study track" for the phase breakdown and DECISIONS.md for why
this is a separate track rather than folded into game.py.

Phase 1 (scaffolding) is reuse-only: no new analysis yet, just a thin entry
point so study_marimo.py has its own call site to extend in later phases
without touching game.py."""

import game

__ver__ = "0.1.0"
print(f"study ver {__ver__}")


def load_game(pgn_text, time_limit=0.3):
    """Sweep a PGN via game.sweep_game() — the study notebook's one entry
    point for ply records, so later phases (material imbalance, captures,
    motif detection) have a single place to extend. Pure passthrough for
    now; Phase 1 adds no new analysis."""
    return game.sweep_game(pgn_text, time_limit=time_limit)
