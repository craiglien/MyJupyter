import io
import os

import chess.pgn

__ver__ = "0.2.0"
print(f"game_collections ver {__ver__}")

COLLECTIONS_DIR = "/data/collections"
# Games you save from the game notebook (save_game()). Gitignored — personal
# games, never committed — but listed alongside COLLECTIONS_DIR's files.
GAMES_DIR = "/data/games"
SAVED_COLLECTION = "my_games"


def list_collections():
    """Names (filename stem) of every *.pgn file under COLLECTIONS_DIR and
    GAMES_DIR, sorted. Bind-mounted (./data on the host) — add or edit a file
    there and it shows up next time this is called, no rebuild or restart needed."""
    names = set()
    for directory in (COLLECTIONS_DIR, GAMES_DIR):
        if os.path.isdir(directory):
            names.update(
                os.path.splitext(f)[0]
                for f in os.listdir(directory)
                if f.endswith(".pgn")
            )
    return sorted(names)


def _collection_path(name):
    for directory in (COLLECTIONS_DIR, GAMES_DIR):
        path = os.path.join(directory, f"{name}.pgn")
        if os.path.exists(path):
            return path
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


def save_game(name, pgn_text):
    """Append the game in `pgn_text` to the saved-games collection, labeled
    `name` (stored as the game's Event header, so it shows in the picker).
    Returns the game's label. Raises ValueError if there's no name or no game
    in the text. Re-exported through chess.pgn, so the saved file always has
    clean headers and mainline moves, whatever was pasted in."""
    name = name.strip()
    if not name:
        raise ValueError("Give the game a name before saving.")
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None or not list(game.mainline_moves()):
        raise ValueError("No game with moves found in the PGN text.")
    game.headers["Event"] = name
    os.makedirs(GAMES_DIR, exist_ok=True)
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    with open(os.path.join(GAMES_DIR, f"{SAVED_COLLECTION}.pgn"), "a", encoding="utf-8") as f:
        f.write(game.accept(exporter) + "\n\n")
    return _game_label(game.headers)
