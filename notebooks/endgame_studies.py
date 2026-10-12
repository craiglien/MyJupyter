"""Loader and solving-flow logic for the endgame_studies submodule content
(data/endgame_studies/), feeding endgame_studies_marimo.py. Pure file I/O
plus python-chess — no engine calls (see TASKS.md's Phase 5 for why that
stays optional), no duplicate PGN-parsing logic.

One folder per study (data/endgame_studies/<slug>/), one or more position
variants per study (position<_variant>.fen / solution<_variant>.pgn pairs) —
see that submodule's own README.md for the full folder convention."""

import glob
import os

import chess
import chess.pgn

__ver__ = "0.1.0"
print(f"endgame_studies ver {__ver__}")

STUDIES_DIR = "/data/endgame_studies"


def list_studies():
    """Every study folder's slug, alphabetically."""
    return sorted(
        os.path.basename(p.rstrip("/"))
        for p in glob.glob(f"{STUDIES_DIR}/*/")
    )


def list_variants(slug):
    """Every variant for a study, derived from its position*.fen files.
    "" (no suffix, just position.fen) is a valid variant name, meaning "the
    only one"."""
    variants = []
    for path in sorted(glob.glob(f"{os.path.join(STUDIES_DIR, slug)}/position*.fen")):
        name = os.path.basename(path)[len("position"):-len(".fen")]
        variants.append(name[1:] if name.startswith("_") else name)
    return variants


def _suffix(variant):
    return f"_{variant}" if variant else ""


def load_variant(slug, variant):
    """The study's FEN, its solution PGN's games (composer's main line
    first, by the folder convention), and its notes.md/source.txt text
    (None if that file doesn't exist for this study)."""
    folder = os.path.join(STUDIES_DIR, slug)
    suffix = _suffix(variant)

    with open(f"{folder}/position{suffix}.fen") as f:
        fen = f.read().strip()

    games = []
    with open(f"{folder}/solution{suffix}.pgn") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            games.append(game)

    return {
        "fen": fen,
        "games": games,
        "notes": _read_optional(f"{folder}/notes.md"),
        "source": _read_optional(f"{folder}/source.txt"),
    }


def _read_optional(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()


def board_at(fen, moves_so_far):
    """The position reached by replaying moves_so_far (a sequence of UCI
    strings) from fen."""
    board = chess.Board(fen)
    for uci in moves_so_far:
        board.push_uci(uci)
    return board


def on_script(moves_so_far, composer_moves):
    """Whether every move played so far matches composer_moves (a list of
    chess.Move, from a Game's mainline_moves()) at the same ply."""
    for i, uci in enumerate(moves_so_far):
        if i >= len(composer_moves) or uci != composer_moves[i].uci():
            return False
    return True


def solved(moves_so_far, composer_moves):
    return bool(composer_moves) and on_script(moves_so_far, composer_moves) and (
        len(moves_so_far) >= len(composer_moves)
    )


def apply_move(moves_so_far, composer_moves, move):
    """Push `move` (a chess.Move already confirmed legal by the caller) onto
    moves_so_far, then — only while still on_script — auto-append
    composer_moves' next move too (the recorded reply). Going off the
    recorded line doesn't raise; the caller just sees no auto-reply
    appended, same as any other move. Returns the new moves-so-far tuple of
    UCI strings."""
    new_moves = moves_so_far + (move.uci(),)
    ply = len(moves_so_far)
    if on_script(moves_so_far, composer_moves) and ply < len(composer_moves) and move.uci() == composer_moves[ply].uci():
        reply_ply = ply + 1
        if reply_ply < len(composer_moves):
            new_moves = new_moves + (composer_moves[reply_ply].uci(),)
    return new_moves
