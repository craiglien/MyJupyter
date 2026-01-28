import io

import chess
import chess.engine
import chess.svg
import chess.pgn
from IPython.display import SVG, HTML

__ver__ = .8
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


def describe_move_reason(board, move, info):
    """Describe why a move is suggested."""
    reasons = []

    # Extract evaluation
    eval_info = info.get("score")
#    if eval_info:
#        if eval_info.is_mate():
#            reasons.append(f"Mate in {abs(eval_info.mate())} moves.")
#        else:
#            score_cp = eval_info.white().score(mate_score=10000)  # White's perspective
#            reasons.append(f"Evaluation score: {score_cp / 100:.2f} pawns advantage.")
    
    # Look for tactical or strategic reasons
    if board.is_capture(move):
        reasons.append("This move captures an opponent's piece.")
    if board.is_check():
        reasons.append("This move places the opponent in check.")
    if board.is_checkmate():
        reasons.append("This move delivers checkmate.")
    
    # Positional aspects
    if board.piece_at(move.to_square):
        reasons.append(f"It places a {board.piece_at(move.to_square).symbol().upper()} in a strong position.")
    
    # Fallback for unclear moves
    if not reasons:
        reasons.append("Improves the position or prepares a follow-up.")

    return reasons


def moves(board, show=True):
    user = board.user
    board = board.board

    # Start the Stockfish engine
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:

        # Analyze the board for a certain amount of time (e.g., 2 seconds)
        info = engine.analyse(board, chess.engine.Limit(time=2.0), multipv=5)

        print(f"\nTop {len(info)} Moves with Side Information:")
        for idx, move_info in enumerate(info, start=1):
            move = move_info["pv"][0]
            score = move_info["score"].relative
            move_uci = move.uci()
    
            # Determine the side of the board
            from_square = move.from_square
            to_square = move.to_square
    
            from_file = chess.square_file(from_square)
            to_file = chess.square_file(to_square)
    
            # Classify based on files: 0-3 are queenside, 4-7 are kingside
            def classify_side(file):
                if file <= 3:
                    return "Queenside"
                else:
                    return "Kingside"
    
            from_side = classify_side(from_file)
            to_side = classify_side(to_file)
            ex_text = []
            mv_text = []
    
            temp_board = board.copy()
            temp_board.push(move)
            st_sq = move.from_square
            en_sq = move.to_square

            svg_move = chess.svg.board(temp_board, arrows=[(st_sq, en_sq)], size=300,
                                       orientation=user)
            #display(SVG(svg_move))
    
            # Print the move with its score and side information
            mv_text.append(f"{idx}. Move: {move_uci}, Score: {score}")
#            ex_text.append(f"   Reason: {side_explanation}")
            # Explanation
            ex_text.append(f"Move starts on the {from_side} and ends on the {to_side}.")

    
            # Explain why the move was chosen
            if score.is_mate():
                explanation = "This move leads to a checkmate in the foreseeable future."
            elif score.score() > 200:
                explanation = "This move provides a significant advantage to the player."
            elif score.score() > 50:
                explanation = "This move is a good positional improvement or material gain."
            elif score.score() > 0:
                explanation = "This move slightly improves the position."
            else:
                explanation = "This move is neutral or maintains the balance of the game."
    
            ex_text.append(f"   Positional Reason: {explanation}")
            ex_out = "<br>".join(ex_text)

            ex_text2 = describe_move_reason(temp_board, move, move_info)

            ex_out2 = "<br>".join(ex_text2)
            mv_out = "<br>".join(mv_text)

            html_content = f"""
            <div style="display: flex; align-items: center;">
            <div>{svg_move}</div>
            <div style="margin-left: 20px; font-size: 16px;">{mv_out}<hr>{ex_out}<hr>{ex_out2}</div>
            </div>"""

            display(HTML(html_content))

