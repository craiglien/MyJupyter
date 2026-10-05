import logging
import re

import chess
import matplotlib.pyplot as plt
from IPython.display import HTML, display

import position

__ver__ = "0.7.0"
print(f"game ver {__ver__}")

log = logging.getLogger("chess.game")


def _game_phase(board):
    """Rough opening/middlegame/endgame heuristic from move count and
    remaining non-pawn material — advisory narrative flavor, not exact."""
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    majors_minors = sum(
        len(board.pieces(pt, color))
        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
        for color in (chess.WHITE, chess.BLACK)
    )
    if board.fullmove_number <= 10 and queens == 2:
        return "Opening"
    if majors_minors <= 6:
        return "Endgame"
    return "Middlegame"


def _is_mate_range(white_cp):
    """True once a cp value is deep enough into the mate_score=100000
    cap that it can only have come from an actual forced mate, not a
    large-but-real material/positional eval."""
    return abs(white_cp) >= 90000


def _format_eval(white_cp):
    """Human-readable eval: '+1.35' normally, 'M3'/'-M2' once the score
    is a forced mate (mate_score capping otherwise turns this into a
    meaningless four-figure pawn count)."""
    if _is_mate_range(white_cp):
        mate_in = 100000 - abs(white_cp)
        return f"{'M' if white_cp > 0 else '-M'}{mate_in}"
    return f"{white_cp / 100:+.2f}"


def _format_loss(loss_cp):
    """Human-readable per-move loss: pawns normally, 'Mate' once the
    swing only makes sense as crossing into/out of forced-mate territory."""
    if loss_cp >= 2000:
        return "Mate"
    return f"{loss_cp / 100:.2f}"


def _classify_quality(loss_pawns):
    """Move-quality label from centipawn loss, via position.py's shared
    _gap_tier() — the exact tier boundaries describe_gap() uses for 'gap
    vs best' (tied/slightly behind/clearly behind/far behind), so both
    layers agree on what counts as a small vs large evaluation swing."""
    _, label = position._gap_tier(loss_pawns)
    return label


def sweep_game(pgn_text, time_limit=0.3):
    """Walk every ply of a PGN with a cheap engine pass (cached on disk),
    building an eval curve and per-move quality classification. Returns a
    list of per-move records; see show_sweep() to display them and
    critical_moments()/show_critical_moments() to drill into the biggest
    swings."""
    game = position.parse_pgn(pgn_text)
    board = game.board()
    log.debug("sweep_game: starting, time_limit=%s", time_limit)

    cache = position._load_cache()
    records = []

    with position.open_engine() as engine:
        version = position._engine_version(engine)
        prev_white_cp = position._evaluate_cached(engine, board, cache, time_limit, version)

        for ply, move in enumerate(game.mainline_moves(), start=1):
            mover = "White" if board.turn == chess.WHITE else "Black"
            san = board.san(move)
            phase = _game_phase(board)
            fen_before = board.fen()

            board.push(move)
            white_cp = position._evaluate_cached(engine, board, cache, time_limit, version)

            if mover == "White":
                loss_cp = max(0, prev_white_cp - white_cp)
            else:
                loss_cp = max(0, white_cp - prev_white_cp)
            loss_pawns = loss_cp / 100

            records.append({
                "ply": ply,
                "move_number": (ply + 1) // 2,
                "mover": mover,
                "move": move,
                "san": san,
                "white_eval": white_cp / 100,
                "white_eval_display": _format_eval(white_cp),
                "loss": loss_pawns,
                "loss_display": _format_loss(loss_cp),
                "quality": _classify_quality(loss_pawns),
                "phase": phase,
                "fen_before": fen_before,
                "fen_after": board.fen(),
            })

            prev_white_cp = white_cp

    position._save_cache(cache)
    log.debug("sweep_game: done, swept %d ply", len(records))
    return records


def show_sweep(records):
    """Move-by-move quality table plus an eval-over-time chart for a
    sweep_game() result."""
    rows = "".join(
        f"<tr><td>{r['move_number']}{'.' if r['mover'] == 'White' else '...'}</td>"
        f"<td>{r['mover']}</td><td>{r['san']}</td>"
        f"<td>{r['white_eval_display']}</td><td>{r['loss_display']}</td>"
        f"<td>{r['quality']}</td><td>{r['phase']}</td></tr>"
        for r in records
    )
    table_html = f"""
    <table border="1" cellpadding="6" style="border-collapse: collapse; font-size: 15px;">
    <tr><th>Move</th><th>Side</th><th>SAN</th><th>Eval (White)</th><th>Loss</th><th>Quality</th><th>Phase</th></tr>
    {rows}
    </table>"""
    display(HTML(table_html))
    eval_curve_figure(records)
    plt.show()


def eval_curve_figure(records):
    """The eval-over-time chart for a sweep_game() result, as a matplotlib
    Figure. Doesn't show it — a marimo cell can return the figure directly
    to display it, and show_sweep() calls plt.show() on it for Jupyter."""
    # Clip mate-range evals for the chart's y-axis, or one forced-mate ply
    # would flatten every earlier, real eval to an indistinguishable line
    # near zero.
    xs = [r["ply"] for r in records]
    ys = [max(-10, min(10, r["white_eval"])) for r in records]
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(xs, ys)
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xlabel("Ply")
    ax.set_ylabel("Eval (pawns, White POV)")
    ax.set_title("Evaluation over the game")
    return fig


def critical_moments(records, top_n=3):
    """The top_n plies with the largest centipawn loss."""
    return sorted(records, key=lambda r: r["loss"], reverse=True)[:top_n]


def ply_for_move(records, text):
    """Index into `records` for a typed move reference, or None if the text
    isn't a move reference or the game has no such move. Accepts "23w",
    "23b", "23." (White), "23..." (Black), "23 black", and bare "23"
    (White). Pure — no display, no engine call."""
    m = re.fullmatch(r"\s*(\d+)\s*(\.{1,3}|[wb][a-z]*)?\s*", text, re.IGNORECASE)
    if not m:
        return None
    number = int(m.group(1))
    marker = (m.group(2) or "").lower()
    mover = "Black" if marker == "..." or marker.startswith("b") else "White"
    for i, r in enumerate(records):
        if r["move_number"] == number and r["mover"] == mover:
            return i
    return None


def critical_moments_html(records, top_n=3):
    """The top_n biggest swings as a short HTML list (move, SAN, quality,
    loss), for display next to the eval chart. Pure — no display() call."""
    items = "".join(
        f"<li><b>{r['move_number']}{'.' if r['mover'] == 'White' else '...'} {r['san']}</b> — "
        f"{r['quality']}, lost {r['loss_display']}</li>"
        for r in critical_moments(records, top_n=top_n)
    )
    return f"<p><b>Biggest swings</b></p><ul>{items}</ul>"


def _explore_record(r, user):
    """Show what was actually played at r's position, then — clearly
    labeled as an alternative, not a replay of the game — the engine's own
    ranked candidates there (via position.moves()). Returns
    {"record", "board", "info"} so exploration can continue further with
    position.explain_reply()/position.explain_line(). Shared by
    show_critical_moments() (auto-flagged moments) and at_move() (a move
    you name directly)."""
    move_label = f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'}"
    print(f"\n=== {move_label}{r['san']} — {r['quality']}, lost {r['loss_display']} ===")
    print(f"You played {move_label}{r['san']}. Below is NOT a replay of your game — "
          f"it's the engine's own ranked alternatives at this position instead:")
    board = position.make(r["fen_before"], user)
    info = position.moves(board)
    return {"record": r, "board": board, "info": info}


def show_critical_moments(records, top_n=3, user="w"):
    """Deep-dive the biggest swings in the game: for each, show what was
    actually played, then the engine's own ranked candidates at the
    position BEFORE that move. Returns a list of {"record", "board", "info"}
    dicts, one per critical moment shown — see _explore_record()."""
    return [_explore_record(r, user) for r in critical_moments(records, top_n=top_n)]


def _mover_from_side(side):
    """'White'/'Black' from a user-typed side string, e.g. at_move()'s
    "black" or GameCursor.goto()'s "w" — shared so both agree on what
    counts as valid input."""
    if side.lower().startswith("w"):
        return "White"
    elif side.lower().startswith("b"):
        return "Black"
    else:
        raise ValueError(f"Unrecognized side {side!r}; expected something starting with 'w' or 'b'")


def _find_move(records, move_number, side):
    """Index into `records` of the (move_number, side) ply, or raise if
    there's no such move in this game. Shared by at_move() and
    GameCursor.goto()."""
    mover = _mover_from_side(side)
    matches = [i for i, r in enumerate(records) if r["move_number"] == move_number and r["mover"] == mover]
    if not matches:
        raise ValueError(f"No move {move_number} for {mover} in this game")
    return matches[0]


def at_move(records, move_number, side, user="w"):
    """Jump directly to the position before a specific move you name —
    not necessarily one flagged as a critical moment — and show the
    engine's ranked options there. E.g. at_move(records, 15, "black") to
    discuss what Black could have done on move 15. Returns
    {"record", "board", "info"}, same shape as show_critical_moments(), so
    you can keep exploring further with position.explain_reply()/
    position.explain_line()."""
    return _explore_record(records[_find_move(records, move_number, side)], user)


class GameCursor:
    """Stateful forward/backward stepper over a game's actual played moves,
    built from sweep_game()'s records. .next()/.prev()/.goto() are cheap —
    they just move the cursor and display the board, no engine call. Only
    .explain() hits the engine, via the same _explore_record() path as
    at_move(): the engine's ranked alternatives at the position BEFORE the
    cursor's move, compared against what was actually played."""

    def __init__(self, records, user="w"):
        if not records:
            raise ValueError("Can't build a GameCursor from an empty game")
        self.records = records
        self.user = user
        self.index = 0

    @property
    def record(self):
        return self.records[self.index]

    def _show(self):
        r = self.record
        move_label = f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'}"
        print(f"{move_label}{r['san']} — {r['quality']} ({r['white_eval_display']})")
        board = position.make(r["fen_after"], self.user)
        position.show(board)
        return board

    def next(self):
        if self.index >= len(self.records) - 1:
            raise IndexError("Already at the last move")
        self.index += 1
        return self._show()

    def prev(self):
        if self.index <= 0:
            raise IndexError("Already at the first move")
        self.index -= 1
        return self._show()

    def goto(self, move_number, side):
        self.index = _find_move(self.records, move_number, side)
        return self._show()

    def explain(self):
        return _explore_record(self.record, self.user)


def analyze_game(pgn_text, time_limit=0.3, top_n_critical=3, user="w", show_critical=True):
    """Entry point: sweep the whole game, display the table + chart, and
    drill into the biggest swings. Returns (records, critical) — critical
    is [] if show_critical=False; see show_critical_moments() for how to
    keep exploring any of its entries further."""
    records = sweep_game(pgn_text, time_limit=time_limit)
    show_sweep(records)
    critical = show_critical_moments(records, top_n=top_n_critical, user=user) if show_critical else []
    return records, critical
