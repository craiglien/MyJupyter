import io
import json
import os
import re
import time

import chess
import chess.engine
import chess.svg
import chess.pgn
from IPython.display import SVG, HTML, display

__ver__ = "0.1.0"
print(f"position ver {__ver__}")

# Path to your Stockfish executable
stockfish_path = "/usr/bin/stockfish"

# On-disk cache of Stockfish results, keyed by (engine version, multipv,
# time_limit, FEN) so a rebuilt/upgraded engine or a different time budget
# never silently reuses a stale result. Shared by _analyze()'s multipv
# drill-down (moves()/explain_reply(), and game.py's at_move() through
# those) and game.py's cheap multipv=1 eval sweep via _evaluate_cached() —
# multipv is part of the key so the two kinds of entry never collide, they
# just share the same cache file and load/save helpers. Entries record a
# timestamp for visibility/debugging but don't auto-expire; they stay valid
# until manually cleared or until the version in the key changes.
_CACHE_PATH = "/data/engine_cache.json"


def _load_cache():
    if os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH) as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    with open(_CACHE_PATH, "w") as f:
        json.dump(cache, f)


def _engine_version(engine):
    return engine.id.get("name", "unknown")


def _evaluate_cached(engine, board, cache, time_limit, version):
    """White-POV eval (centipawns, mate capped to +/-100000) for `board`,
    from the on-disk cache if present, else a fresh engine.analyse() call
    that also populates the cache. Used by game.py's per-ply eval sweep,
    which is always multipv=1 by construction (a cheap pass over every
    ply); deeper multipv drill-down for critical moments goes through
    _analyze() instead, which caches separately (see _CACHE_PATH)."""
    fen = board.fen()
    key = f"{version}|1|{time_limit}|{fen}"
    if key in cache:
        return cache[key]["white_cp"]

    info = engine.analyse(board, chess.engine.Limit(time=time_limit))
    white_cp = info["score"].white().score(mate_score=100000)
    cache[key] = {"white_cp": white_cp, "timestamp": time.time()}
    return white_cp


def _serialize_info(info):
    """JSON-serializable form of engine.analyse()'s multipv result list —
    just enough to reconstruct what _display_ranked_moves() reads back out
    (each entry's PV and its score relative to the side to move)."""
    return [
        {
            "pv": [m.uci() for m in entry["pv"]],
            "cp": entry["score"].relative.score(),
            "mate": entry["score"].relative.mate(),
        }
        for entry in info
    ]


def _deserialize_info(data, turn):
    """Inverse of _serialize_info(); `turn` is the side to move in the
    position the analysis was run from (PovScore needs it to know whose
    perspective the stored relative score is from)."""
    info = []
    for entry in data:
        rel = chess.engine.Mate(entry["mate"]) if entry["mate"] is not None else chess.engine.Cp(entry["cp"])
        info.append({
            "pv": [chess.Move.from_uci(u) for u in entry["pv"]],
            "score": chess.engine.PovScore(rel, turn),
        })
    return info


# Tier boundaries (in pawns) for "how far behind the best move is this
# one." Shared between describe_gap()'s human-readable note below and
# game.py's move-quality label, so the two can't silently drift out of
# sync the way they used to when each hand-maintained its own copy.
GAP_TIERS = (
    (0.05, "Essentially tied with the top move.", "Best"),
    (0.3, "Slightly behind the top move.", "Good"),
    (1.0, "Clearly behind the top move.", "Inaccuracy"),
)
GAP_TIER_FALLBACK = ("Far behind the top move.", "Blunder")


def _gap_tier(gap_pawns):
    """(note, quality_label) for a centipawn-loss gap expressed in pawns."""
    for threshold, note, label in GAP_TIERS:
        if gap_pawns <= threshold:
            return note, label
    return GAP_TIER_FALLBACK


def get_color(color):
    if color.lower().startswith('b'):
        return chess.BLACK
    elif color.lower().startswith('w'):
        return chess.WHITE
    else:
        raise ValueError(f"Unrecognized color {color!r}; expected something starting with 'w' or 'b'")


class CCBoard:
    board = None
    user = None

    def __init__(self, fen, user):
        self.board = chess.Board(fen)
        self.user = get_color(user)


def parse_pgn(pgn_text):
    """Parse a full PGN string (headers and all) into a chess.pgn.Game.
    Shared by pgn() below and game.py's sweep_game()."""
    return chess.pgn.read_game(io.StringIO(pgn_text))


def pgn(pgn, user):
    gm = parse_pgn(pgn)
    bd = gm.board()
    for m in gm.mainline_moves():
        bd.push(m)
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
    note, _ = _gap_tier(gap)
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


def _pieces_over_arrows(svg):
    """chess.svg.board() draws arrows after (visually on top of) the pieces,
    which for short moves — mainly knight hops — puts the arrowhead right
    over the piece that just landed there, making it look erased. Move the
    arrow elements to just before the first piece <use> element instead, so
    pieces always render on top of the arrow trail leading into their square."""
    arrow_pattern = re.compile(r'<(?:line|polygon)[^>]*class="arrow"[^>]*/>')
    arrows = arrow_pattern.findall(svg)
    if not arrows:
        return svg
    svg = arrow_pattern.sub('', svg)
    first_use = svg.index('<use ')
    return svg[:first_use] + "".join(arrows) + svg[first_use:]


def open_engine():
    """Start a Stockfish process via UCI. Use as `with open_engine() as
    engine:`. One place to change if engine startup options are ever
    needed; shared by _analyze() (opens/closes per call) and game.py's
    sweep_game() (opens once, holds it for the whole sweep) even though
    the two use different lifecycles."""
    return chess.engine.SimpleEngine.popen_uci(stockfish_path)


def _analyze(root_board, multipv=5, time_limit=2.0):
    """Run one multipv analysis pass, cached on disk (see _CACHE_PATH) so
    re-running a notebook cell against a position just analyzed doesn't
    re-hit Stockfish for the full time_limit. Shared by moves() and
    explain_reply() so both go through the same engine-invocation and
    caching path."""
    fen = root_board.fen()
    cache = _load_cache()
    with open_engine() as engine:
        version = _engine_version(engine)
        key = f"{version}|{multipv}|{time_limit}|{fen}"
        if key in cache:
            return _deserialize_info(cache[key]["info"], root_board.turn)
        info = engine.analyse(root_board, chess.engine.Limit(time=time_limit), multipv=multipv)
    cache[key] = {"info": _serialize_info(info), "timestamp": time.time()}
    _save_cache(cache)
    return info


def _describe_continuation(board_after_move, pv_rest, max_extra_plies=2):
    """Describe up to `max_extra_plies` further plies of a principal
    variation (the reply, and possibly the move after that), each with a
    short reason via classify_move()/describe_move_reason(). Reuses data
    already in the PV — no extra engine calls."""
    lines = []
    walk_board = board_after_move.copy()
    for i, mv in enumerate(pv_rest[:max_extra_plies]):
        mover = "White" if walk_board.turn == chess.WHITE else "Black"
        san = walk_board.san(mv)
        reason = " ".join(describe_move_reason(classify_move(walk_board, mv)))
        if i == 0:
            lines.append(f"Engine expects {mover}'s reply {san} — {reason}")
        else:
            lines.append(f"Then {mover} likely continues with {san} — {reason}")
        walk_board.push(mv)
    return lines


def _display_ranked_moves(root_board, info, user, header, show=True):
    """Summary table + per-candidate detail blocks with comparative
    ranking, for whichever position `info` was analyzed from. Shared by
    moves() (the position on the board) and explain_reply() (the position
    after a candidate move, one ply deeper)."""
    if root_board.is_game_over():
        if root_board.is_checkmate():
            reason = "Checkmate"
        elif root_board.is_stalemate():
            reason = "Stalemate"
        else:
            reason = "Game over"
        print(f"\n{reason} — no moves to analyze.")
        return info

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
    if show:
        display(HTML(table_html))
        print(f"\n{header}")

    for idx, c in enumerate(candidates, start=1):
        move, pv = c["move"], c["move_info"]["pv"]

        temp_board = root_board.copy()
        temp_board.push(move)

        svg_move = _pieces_over_arrows(chess.svg.board(
            temp_board, arrows=[(move.from_square, move.to_square)],
            size=300, orientation=user, lastmove=move))

        reasons = describe_move_reason(c["class_info"])
        rank_note = "This is the engine's top choice." if idx == 1 \
            else f"{c['gap_note']} (Gap vs best: {c['gap_text']})"

        continuation_lines = _describe_continuation(temp_board, pv[1:], max_extra_plies=2)

        mv_out = f"{idx}. {c['san']} ({move.uci()}) &mdash; {c['score_text']}"
        detail_lines = [f"Eval: {c['eval_text']}", "<br>".join(reasons), rank_note] + continuation_lines
        detail_out = "<hr>".join(detail_lines)

        html_content = f"""
        <div style="display: flex; align-items: center;">
        <div>{svg_move}</div>
        <div style="margin-left: 20px; font-size: 16px;">{mv_out}<hr>{detail_out}</div>
        </div>"""

        if show:
            display(HTML(html_content))

    return info


def moves(board, show=True):
    """Show the top candidate moves for `board`, ranked and compared
    against each other, with an explanation for each. Returns the engine's
    raw multipv analysis so a specific candidate's continuation can be
    inspected further with explain_line() or explain_reply()."""
    user = board.user
    root_board = board.board

    info = _analyze(root_board, multipv=5, time_limit=2.0)
    return _display_ranked_moves(root_board, info, user, header=f"Top {len(info)} Moves:", show=show)


def explain_reply(board, info, candidate=1, multipv=3, time_limit=1.0):
    """Explain WHY the engine expects a given reply, by analyzing the
    position after candidate move `candidate` (1-indexed, matching the
    numbering from moves()) and ranking the opponent's own options against
    each other — the same way moves() ranks ours. This makes a fresh
    engine call, one ply deeper than `info`. Returns that analysis, so
    calling explain_reply() again on it (with a board built from the
    resulting position) goes another ply deeper."""
    user = board.user
    root_board = board.board

    move = info[candidate - 1]["pv"][0]
    reply_board = root_board.copy()
    reply_board.push(move)

    mover_label = "White" if reply_board.turn == chess.WHITE else "Black"
    print(f"\nAfter {root_board.san(move)}, it's {mover_label}'s move:")

    reply_info = _analyze(reply_board, multipv=multipv, time_limit=time_limit)
    return _display_ranked_moves(reply_board, reply_info, user,
                                  header=f"Top {len(reply_info)} Replies for {mover_label}:")


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
