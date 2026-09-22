import os

import chess.pgn

__ver__ = "0.1.0"
print(f"game_collections ver {__ver__}")

COLLECTIONS_DIR = "/data/collections"


def list_collections():
    """Names (filename stem) of every *.pgn file under COLLECTIONS_DIR, sorted.
    Bind-mounted (./data/collections on the host) — add or edit a file there
    and it shows up next time this is called, no rebuild or restart needed."""
    if not os.path.isdir(COLLECTIONS_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(COLLECTIONS_DIR)
        if f.endswith(".pgn")
    )


def _collection_path(name):
    return os.path.join(COLLECTIONS_DIR, f"{name}.pgn")


def _game_label(headers):
    label = f"{headers.get('White', '?')} vs {headers.get('Black', '?')}"
    extra = [
        v for v in (headers.get("Event"), headers.get("Date"))
        if v and v not in ("?", "????.??.??")
    ]
    if extra:
        label = f"{label} ({', '.join(extra)})"
    return label


def list_games(collection_name):
    """Every game in a collection file, in file order. Returns a list of
    dicts: {label, pgn_text}. `pgn_text` is a freshly re-exported PGN string
    (headers + mainline moves) for just that one game — the same "paste a
    full PGN" shape game.sweep_game() already expects everywhere else, not
    a raw slice of the original file. Relies on chess.pgn.read_game()'s own
    support for repeated reads from one stream to walk a multi-game file;
    no PGN-parsing logic duplicated here."""
    games = []
    with open(_collection_path(collection_name), encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
            games.append({
                "label": _game_label(game.headers),
                "pgn_text": game.accept(exporter),
            })
    return games
