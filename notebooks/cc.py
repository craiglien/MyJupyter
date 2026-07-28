import io

import chess
import chess.engine
import chess.svg
import chess.pgn
from IPython.display import SVG, HTML, display

__ver__ = .9
print(f"cc ver {__ver__}")

# Path to your Stockfish executable
stockfish_path = "/usr/bin/stockfish"

def get_color(color):
    if color.lower().startswith('b'):
        return chess.BLACK
    elif color.lower().startswith('w'):
        return chess.WHITE
    else:
        return 'invalid'


class CCBoard:
    board = None
    user = None

    def __init__(self, fen, user):
        self.board = chess.Board(fen)
        self.user = get_color(user)


def pgn(pgn, user):
    pgn_file = io.StringIO(pgn)
    gm = chess.pgn.read_game(pgn_file)
    print(gm)
    print(dir(gm))
    print(type(gm.board))
    bd = gm.board()
    print(bd)
    for m in gm.mainline_moves():
        print(m)
        bd.push(m)
        print(bd)
    print(bd)
    print(type(bd))
    print(dir(bd))
    return CCBoard(bd.fen(), user)



def make(fen, user):
    return CCBoard(fen, user)


def show(board):
        display(SVG(chess.svg.board(board=board.board, size=300, orientation=board.user)))


def move(board, mv):
    board.board.push_uci(mv)


def classify_move(board, move):
    """Move-type facts shared by describe_move_reason() and move_tag(), so
    both agree and neither recomputes is_capture/is_checkmate separately.
    `board` must be the position BEFORE `move` is played."""
    en_passant = board.is_en_passant(move)
    castle_side = None
    if board.is_castling(move):
        castle_side = "kingside" if board.is_kingside_castling(move) else "queenside"

    captured = None
    if not castle_side and not en_passant and board.is_capture(move):
        captured = board.piece_at(move.to_square)

    temp_board = board.copy()
    temp_board.push(move)

    return {
        "castle_side": castle_side,
        "en_passant": en_passant,
        "captured": captured,
        "promotion": move.promotion,
        "checkmate": temp_board.is_checkmate(),
        "check": board.gives_check(move),
    }


def describe_move_reason(class_info):
    """Describe why a move is suggested, from the facts classify_move() returns."""
    reasons = []

    if class_info["castle_side"]:
        reasons.append(f"Castles {class_info['castle_side']}, improving king safety.")
    elif class_info["en_passant"]:
        reasons.append("Captures a pawn en passant.")
    elif class_info["captured"]:
        piece_name = chess.piece_name(class_info["captured"].piece_type).capitalize()
        color_name = "White's" if class_info["captured"].color == chess.WHITE else "Black's"
        reasons.append(f"Captures {color_name} {piece_name}.")

    if class_info["promotion"]:
        reasons.append(f"Promotes to a {chess.piece_name(class_info['promotion']).capitalize()}.")

    if class_info["checkmate"]:
        reasons.append("Delivers checkmate.")
    elif class_info["check"]:
        reasons.append("Puts the opponent in check.")

    if not reasons:
        reasons.append("A quiet move — improves piece placement without immediate tactics.")

    return reasons


def move_tag(class_info):
    """Short one-phrase label for the summary table."""
    if class_info["checkmate"]:
        return "Checkmate"
    if class_info["castle_side"]:
        return f"Castle ({class_info['castle_side']})"
    if class_info["en_passant"]:
        return "En passant"
    if class_info["captured"]:
        return f"Captures {chess.piece_name(class_info['captured'].piece_type).capitalize()}"
    if class_info["promotion"]:
        return f"Promotes to {chess.piece_name(class_info['promotion']).capitalize()}"
    if class_info["check"]:
        return "Check"
    return "Quiet"


def describe_gap(best_score, this_score):
    """Compare `this_score` against the top candidate's score. Both are
    Score objects relative to the side to move. Returns (gap_text, note)."""
    if best_score.is_mate() and this_score.is_mate():
        diff = this_score.mate() - best_score.mate()
        if diff == 0:
            return "0.00", "Equally forcing, same mate distance."
        return f"{diff:+d} moves to mate", "Also involves forced mate, but the distance differs from the top move."

    if best_score.is_mate() and not this_score.is_mate():
        if best_score.mate() > 0:
            return "n/a", "Misses the forced mate the top move delivers."
        return "n/a", "The top move still loses by force; this one avoids an immediate forced mate but may still be much worse."

    if this_score.is_mate() and not best_score.is_mate():
        if this_score.mate() > 0:
            return "n/a", "This move forces mate — unexpectedly ranked below a non-mate move."
        return "n/a", "This move allows the opponent to force mate — much worse than the top move."

    gap = (best_score.score() - this_score.score()) / 100
    gap_text = f"-{gap:.2f}" if gap > 0 else "0.00"
    if gap <= 0.05:
        note = "Essentially tied with the top move."
    elif gap <= 0.3:
        note = "Slightly behind the top move."
    elif gap <= 1.0:
        note = "Clearly behind the top move."
    else:
        note = "Far behind the top move."
    return gap_text, note


def describe_score(score):
    """Human-readable evaluation, e.g. '+0.53' or 'Mate in 4'. `score` is
    relative to the side that just moved (positive = good for the mover)."""
    if score.is_mate():
        mate_in = abs(score.mate())
        return f"Mate in {mate_in}", "This move leads to a forced checkmate."

    pawns = score.score() / 100
    score_text = f"{pawns:+.2f}"
    if pawns > 2:
        eval_text = "A significant advantage."
    elif pawns > 0.5:
        eval_text = "A solid edge."
    elif pawns > 0:
        eval_text = "A slight edge."
    elif pawns > -0.5:
        eval_text = "Roughly balanced."
    else:
        eval_text = "This loses ground."
    return score_text, eval_text


def moves(board, show=True):
    """Show the top candidate moves for `board`, ranked and compared
    against each other, with an explanation for each. Returns the engine's
    raw multipv analysis so a specific candidate's continuation can be
    inspected further with explain_line()."""
    user = board.user
    root_board = board.board

    # Start the Stockfish engine
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:

        # Analyze the board for a certain amount of time (e.g., 2 seconds)
        info = engine.analyse(root_board, chess.engine.Limit(time=2.0), multipv=5)
        best_score = info[0]["score"].relative

        # Precompute per-candidate facts once, shared by the summary table
        # and the detailed blocks below.
        candidates = []
        for move_info in info:
            move = move_info["pv"][0]
            score = move_info["score"].relative
            san = root_board.san(move)
            class_info = classify_move(root_board, move)
            score_text, eval_text = describe_score(score)
            gap_text, gap_note = describe_gap(best_score, score)
            candidates.append({
                "move_info": move_info, "move": move, "score": score, "san": san,
                "class_info": class_info, "score_text": score_text, "eval_text": eval_text,
                "gap_text": gap_text, "gap_note": gap_note,
            })

        # Summary table: scan all candidates and their ranking at a glance.
        rows = "".join(
            f"<tr><td>{idx}</td><td>{c['san']}</td><td>{c['score_text']}</td>"
            f"<td>{c['gap_text']}</td><td>{move_tag(c['class_info'])}</td></tr>"
            for idx, c in enumerate(candidates, start=1)
        )
        table_html = f"""
        <table border="1" cellpadding="6" style="border-collapse: collapse; font-size: 15px;">
        <tr><th>Rank</th><th>Move</th><th>Score</th><th>Gap vs best</th><th>Type</th></tr>
        {rows}
        </table>"""
        display(HTML(table_html))

        print(f"\nTop {len(info)} Moves:")
        for idx, c in enumerate(candidates, start=1):
            move, pv = c["move"], c["move_info"]["pv"]

            temp_board = root_board.copy()
            temp_board.push(move)

            svg_move = chess.svg.board(temp_board, arrows=[(move.from_square, move.to_square)],
                                        size=300, orientation=user, lastmove=move)

            reasons = describe_move_reason(c["class_info"])
            rank_note = "This is the engine's top choice." if idx == 1 \
                else f"{c['gap_note']} (Gap vs best: {c['gap_text']})"

            reply_note = None
            if len(pv) >= 2:
                reply_note = f"Engine expects the reply {temp_board.san(pv[1])}."

            mv_out = f"{idx}. {c['san']} ({move.uci()}) &mdash; {c['score_text']}"
            detail_lines = [f"Eval: {c['eval_text']}", "<br>".join(reasons), rank_note]
            if reply_note:
                detail_lines.append(reply_note)
            detail_out = "<hr>".join(detail_lines)

            html_content = f"""
            <div style="display: flex; align-items: center;">
            <div>{svg_move}</div>
            <div style="margin-left: 20px; font-size: 16px;">{mv_out}<hr>{detail_out}</div>
            </div>"""

            display(HTML(html_content))

        return info


def explain_line(board, info, candidate=1, plies=4):
    """Step through candidate move number `candidate` (1-indexed, matching
    the numbering printed by moves()) ply by ply, using the continuation
    the engine already computed for it. `info` is the list returned by
    moves() — no extra engine calls are made."""
    user = board.user
    walk_board = board.board.copy()

    pv = info[candidate - 1]["pv"][:plies]

    for ply_num, mv in enumerate(pv, start=1):
        mover = "White" if walk_board.turn == chess.WHITE else "Black"
        san = walk_board.san(mv)
        walk_board.push(mv)

        svg_ply = chess.svg.board(walk_board, size=300, orientation=user, lastmove=mv)

        html_content = f"""
        <div style="display: flex; align-items: center;">
        <div>{svg_ply}</div>
        <div style="margin-left: 20px; font-size: 16px;">Ply {ply_num}: {mover} plays {san}</div>
        </div>"""

        display(HTML(html_content))

