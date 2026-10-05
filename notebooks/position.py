import io
import json
import logging
import logging.handlers
import os
import re
import time

import chess
import chess.engine
import chess.svg
import chess.pgn
from IPython.display import SVG, HTML, display

__ver__ = "0.12.0"
print(f"position ver {__ver__}")

# Path to your Stockfish executable
stockfish_path = "/usr/bin/stockfish"

# Debug log for engine calls, cache hits/misses, and anything else worth
# tracing back after the fact (e.g. "what did the engine actually see when
# I tried that move"). Rotated so a long-running container doesn't grow it
# unbounded; written under /data so it survives container restarts like
# engine_cache.json does, but — unlike the cache — kept even across a cache
# clear, since its whole point is a history of what happened. `log` (this
# module) and game.py's own logger are both children of the "chess" logger,
# which is the one that actually owns the handler — see the guard below,
# needed because Python caches imported modules but marimo/Jupyter can
# still re-run this module-level code (kernel restart, cache-cleared
# reimport), and a second handler would double every line.
_LOG_PATH = "/data/debug.log"
log = logging.getLogger("chess.position")
_log_root = logging.getLogger("chess")
if not _log_root.handlers:
    _log_root.setLevel(logging.DEBUG)
    _handler = logging.handlers.RotatingFileHandler(_LOG_PATH, maxBytes=2_000_000, backupCount=3)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _log_root.addHandler(_handler)
    _log_root.propagate = False

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
        log.debug("eval cache HIT fen=%s time_limit=%s", fen, time_limit)
        return cache[key]["white_cp"]

    log.debug("eval cache MISS fen=%s time_limit=%s — calling engine", fen, time_limit)
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


def gap_quality(best_score, this_score):
    """Best/Good/Inaccuracy/Blunder label for how `this_score` compares to
    `best_score` — the label _gap_tier() computes but describe_gap() below
    discards (it only keeps the prose note). Mirrors describe_gap()'s own
    mate-handling so the two always agree. Used by rank_dont_list() to
    filter tempting moves down to the ones actually worth warning about."""
    if best_score.is_mate() and this_score.is_mate():
        return "Best" if this_score.mate() == best_score.mate() else "Inaccuracy"
    if best_score.is_mate() and not this_score.is_mate():
        return "Blunder"
    if this_score.is_mate() and not best_score.is_mate():
        return "Best" if this_score.mate() > 0 else "Blunder"
    gap = (best_score.score() - this_score.score()) / 100
    _, label = _gap_tier(gap)
    return label


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


def pgn(pgn, user, plies=None):
    """Play a full PGN (headers and all) and return the resulting position.
    By default (plies=None) plays every move in the mainline and returns the
    FINAL position — not the position in a `[FEN]` header before any moves
    are played. For a puzzle-style PGN where you want the starting position
    instead, pass plies=0 (or make(fen, user) directly, if you already have
    just the FEN)."""
    gm = parse_pgn(pgn)
    bd = gm.board()
    moves = list(gm.mainline_moves())
    if plies is not None:
        moves = moves[:plies]
    for m in moves:
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

    mover = board.turn
    opponent = not mover
    piece = board.piece_at(move.from_square)
    back_rank = 0 if mover == chess.WHITE else 7

    return {
        "castle_side": castle_side,
        "en_passant": en_passant,
        "captured": captured,
        "promotion": move.promotion,
        "checkmate": temp_board.is_checkmate(),
        "check": board.gives_check(move),
        # Positional facts, all read from the position AFTER the move. Raw
        # (square, Piece) pairs and booleans only — describe_move_reason()
        # turns them into sentences, keeping facts separate from wording.
        "hangs_after": _undefended_pieces(temp_board, mover),
        "threatens_after": [
            (sq, piece_there)
            for sq, piece_there in _undefended_pieces(temp_board, opponent)
            if sq in temp_board.attacks(move.to_square)
        ],
        "central": move.to_square in CENTER_SQUARES,
        "develops": piece is not None and piece.piece_type in (chess.KNIGHT, chess.BISHOP)
                    and chess.square_rank(move.from_square) == back_rank,
        "mover_color": mover,
        "moved_piece": piece,
    }


CENTER_SQUARES = {chess.D4, chess.E4, chess.D5, chess.E5}


def _undefended_pieces(board, color):
    """(square, Piece) pairs for `color`'s non-king pieces that the opponent
    attacks and nothing of `color` defends. Static: no exchange counting,
    so a piece defended only by a more valuable one still shows as defended."""
    out = []
    for sq, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        if board.is_attacked_by(not color, sq) and not board.is_attacked_by(color, sq):
            out.append((sq, piece))
    return out


def _piece_phrase(square, piece):
    """e.g. "White's Knight on f3" — shared wording for the positional sentences."""
    color_name = "White's" if piece.color == chess.WHITE else "Black's"
    return f"{color_name} {chess.piece_name(piece.piece_type).capitalize()} on {chess.square_name(square)}"


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

    for sq, piece in class_info["hangs_after"][:2]:
        reasons.append(f"Leaves {_piece_phrase(sq, piece)} undefended.")
    for sq, piece in class_info["threatens_after"][:2]:
        reasons.append(f"Attacks the undefended {_piece_phrase(sq, piece)}.")

    if class_info["develops"]:
        name = chess.piece_name(class_info["moved_piece"].piece_type)
        reasons.append(f"Develops the {name} off its back rank.")
    if class_info["central"]:
        reasons.append("Puts a piece on a central square.")

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


def render_board_svg(board_after_move, move, user, size=300):
    """Board SVG with `move`'s from/to squares highlighted (`lastmove=`)
    and an arrow drawn over them, piece-over-arrow fixed up via
    _pieces_over_arrows(). Shared by render_candidate_html(),
    render_dont_html(), and game_marimo.py's step-through board, so a
    played move looks the same everywhere it's shown."""
    return _pieces_over_arrows(chess.svg.board(
        board_after_move, arrows=[(move.from_square, move.to_square)],
        size=size, orientation=user, lastmove=move))


def open_engine():
    """Start a Stockfish process via UCI. Use as `with open_engine() as
    engine:`. One place to change if engine startup options are ever
    needed; shared by _analyze() (opens/closes per call) and game.py's
    sweep_game() (opens once, holds it for the whole sweep) even though
    the two use different lifecycles."""
    log.debug("starting Stockfish engine process: %s", stockfish_path)
    return chess.engine.SimpleEngine.popen_uci(stockfish_path)


def _analyze(root_board, multipv=5, time_limit=2.0, root_moves=None):
    """Run one multipv analysis pass, cached on disk (see _CACHE_PATH) so
    re-running a notebook cell against a position just analyzed doesn't
    re-hit Stockfish for the full time_limit. Shared by moves() and
    explain_reply() so both go through the same engine-invocation and
    caching path.

    `root_moves`, if given, restricts the search to that list of
    chess.Move (UCI's "searchmoves") instead of a full-board sweep — used
    by rank_dont_list() to score specific tempting-looking moves that a
    full-board multipv sweep wouldn't surface (multipv only ever returns
    strong moves). `multipv` is capped to len(root_moves) in that case,
    and the cache key includes the move list so a root_moves-restricted
    result never collides with a full-board one for the same position.

    Returns [] without touching the engine if root_board has no legal
    moves (checkmate/stalemate) — Stockfish's own no-legal-moves fallback
    reports a bare score with no "pv", which _serialize_info() can't
    round-trip (KeyError: 'pv'). There's nothing to analyze in a finished
    position anyway; callers already handle an empty/game-over result
    (see _display_ranked_moves())."""
    if root_board.is_game_over():
        log.debug("_analyze: game over at fen=%s, skipping engine call", root_board.fen())
        return []

    fen = root_board.fen()
    cache = _load_cache()
    with open_engine() as engine:
        version = _engine_version(engine)
        if root_moves is not None:
            multipv = min(multipv, len(root_moves))
            moves_key = ",".join(sorted(mv.uci() for mv in root_moves))
            key = f"{version}|{multipv}|{time_limit}|{fen}|root:{moves_key}"
        else:
            key = f"{version}|{multipv}|{time_limit}|{fen}"
        if key in cache:
            log.debug("analyze cache HIT fen=%s multipv=%s time_limit=%s", fen, multipv, time_limit)
            return _deserialize_info(cache[key]["info"], root_board.turn)
        log.debug("analyze cache MISS fen=%s multipv=%s time_limit=%s root_moves=%s — calling engine",
                   fen, multipv, time_limit, root_moves is not None)
        info = engine.analyse(root_board, chess.engine.Limit(time=time_limit), multipv=multipv,
                               root_moves=root_moves)
    cache[key] = {"info": _serialize_info(info), "timestamp": time.time()}
    _save_cache(cache)
    return info


def _describe_continuation(board_after_move, pv_rest, max_extra_plies=2, risky=False):
    """Describe up to `max_extra_plies` further plies of a principal
    variation (the reply, and possibly the move after that), each with a
    short reason via classify_move()/describe_move_reason(). Reuses data
    already in the PV — no extra engine calls.

    `risky=True` reframes the first line as the actual downside of the
    move being described — "What's risky: opens the door to ..." instead
    of the neutral "Engine expects ..." — for an Inaccuracy/Blunder-tier
    candidate in render_candidate_html(), where the reply isn't just
    "expected", it's *why the candidate is graded worse than the top
    move*. Later plies keep the neutral "Then ... continues" phrasing
    either way — they're follow-through, not the risk itself."""
    lines = []
    walk_board = board_after_move.copy()
    for i, mv in enumerate(pv_rest[:max_extra_plies]):
        mover = "White" if walk_board.turn == chess.WHITE else "Black"
        san = walk_board.san(mv)
        reason = " ".join(describe_move_reason(classify_move(walk_board, mv)))
        if i == 0:
            if risky:
                lines.append(f"What's risky: opens the door to {mover}'s {san} — {reason}")
            else:
                lines.append(f"Engine expects {mover}'s reply {san} — {reason}")
        else:
            lines.append(f"Then {mover} likely continues with {san} — {reason}")
        walk_board.push(mv)
    return lines


def rank_candidates(root_board, info, best_score=None):
    """Per-candidate facts (move, score, san, class_info, score_text,
    eval_text, gap_text, gap_note) for each entry in `info`, ranked in the
    order the engine returned them (best first). Pure — no display, no
    engine call. Shared by _display_ranked_moves() (Jupyter) and any other
    caller that wants the same ranking without Jupyter's display() side
    effects, e.g. a marimo notebook building its own candidate-picker UI.

    `best_score` defaults to info[0]'s own score (the best of `info`
    itself). rank_dont_list() passes the real best-of-position score
    explicitly instead, so tempting moves are graded against the actual
    best move rather than the best of the tempting subset.

    Includes a `quality` label (Best/Good/Inaccuracy/Blunder, from
    gap_quality()) on every candidate — render_candidate_html() uses it
    to decide whether a candidate's expected reply gets framed as an
    explicit risk rather than a neutral forecast."""
    if best_score is None:
        best_score = info[0]["score"].relative

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
            "quality": gap_quality(best_score, score),
        })
    return candidates


def score_move(root_board, move, best_score=None, time_limit=2.0):
    """Score one specific move via a root_moves-restricted _analyze() call
    (see its docstring) and return it in the same per-candidate shape as
    rank_candidates()/rank_dont_list(), plus a `quality` label. For
    checking an arbitrary move that isn't already in the top-5 or the
    don't-list — e.g. a "try your own move" input. `best_score` defaults
    to this move's own score (nothing to grade it against); pass the
    position's actual best score (e.g. candidates[0]["score"]) to grade
    it against the real best move instead. Returns None if `move` turns
    out to have no legal response to analyze from (shouldn't happen for
    a legal move in a non-game-over position, but mirrors _analyze()'s
    own empty-result contract rather than assuming)."""
    log.debug("score_move: fen=%s move=%s time_limit=%s", root_board.fen(), move.uci(), time_limit)
    info = _analyze(root_board, multipv=1, time_limit=time_limit, root_moves=[move])
    if not info:
        log.debug("score_move: no analysis returned for move=%s", move.uci())
        return None
    candidate = rank_candidates(root_board, info, best_score=best_score)[0]
    reference = best_score if best_score is not None else candidate["score"]
    candidate["quality"] = gap_quality(reference, candidate["score"])
    return candidate


def _tempting_but_unranked_moves(root_board, top_moves):
    """Legal moves a human eye is drawn to — captures, checks, and moves
    landing on a central square (CENTER_SQUARES) — that aren't already among
    `top_moves` (the engine's own top picks). Real traps live here:
    multipv's own top-N search only ever returns strong moves, so it can't
    surface them. Candidate pool for the "don't" list; scored separately via
    a root_moves-restricted _analyze() call."""
    return [
        mv for mv in root_board.legal_moves
        if mv not in top_moves and (
            root_board.is_capture(mv)
            or root_board.gives_check(mv)
            or mv.to_square in CENTER_SQUARES
        )
    ]


def rank_dont_list(root_board, good_info, max_dont=3, time_limit=2.0):
    """Tempting-looking moves that are actually bad: captures/checks not
    among the engine's own top picks (`good_info`, from _analyze()),
    scored via a root_moves-restricted _analyze() call and filtered down
    to the Inaccuracy/Blunder tier, worst first, capped to `max_dont`.
    Same per-candidate shape as rank_candidates() plus a `quality` label.
    Returns [] if there's nothing tempting-and-bad worth warning about —
    either no such moves exist, or none of them are actually bad enough."""
    if not good_info:
        return []

    top_moves = {entry["pv"][0] for entry in good_info}
    tempting = _tempting_but_unranked_moves(root_board, top_moves)
    log.debug("rank_dont_list: %d tempting move(s) to score at fen=%s", len(tempting), root_board.fen())
    if not tempting:
        return []

    tempting_info = _analyze(root_board, multipv=len(tempting), time_limit=time_limit,
                              root_moves=tempting)
    if not tempting_info:
        return []

    best_score = good_info[0]["score"].relative
    candidates = rank_candidates(root_board, tempting_info, best_score=best_score)
    for c in candidates:
        c["quality"] = gap_quality(best_score, c["score"])

    bad = [c for c in candidates if c["quality"] in ("Inaccuracy", "Blunder")]
    bad.sort(key=lambda c: c["score"].score() if not c["score"].is_mate()
              else (10**6 if c["score"].mate() > 0 else -10**6))
    return bad[:max_dont]


def render_dont_html(root_board, dont_candidates, idx, user):
    """The board-diagram-plus-text detail block for don't-list entry `idx`
    (1-indexed into rank_dont_list()'s output) — same shape as
    render_candidate_html() below, but framed as a warning: what makes
    the move tempting, then the punishing continuation that makes it
    actually bad, reusing _describe_continuation() on the same pv data."""
    c = dont_candidates[idx - 1]
    move, pv = c["move"], c["move_info"]["pv"]

    temp_board = root_board.copy()
    temp_board.push(move)

    svg_move = render_board_svg(temp_board, move, user)

    tempting_reasons = describe_move_reason(c["class_info"])
    warning = f"Looks tempting — {' '.join(tempting_reasons)}"
    verdict = f"{c['quality']}: {c['gap_note']} (Gap vs best: {c['gap_text']})"

    continuation_lines = _describe_continuation(temp_board, pv[1:], max_extra_plies=2)

    mv_out = f"{idx}. {c['san']} ({move.uci()}) &mdash; {c['score_text']}"
    detail_lines = [warning, f"Eval: {c['eval_text']}", verdict] + continuation_lines
    detail_out = "<hr>".join(detail_lines)

    return f"""
    <div style="display: flex; align-items: center;">
    <div>{svg_move}</div>
    <div style="margin-left: 20px; font-size: 16px; color: #a33;">{mv_out}<hr>{detail_out}</div>
    </div>"""


def render_candidate_html(root_board, candidates, idx, user):
    """The full board-diagram-plus-text detail block for candidate `idx`
    (1-indexed into rank_candidates()'s output) — board SVG with the move
    arrow, why-this-move reasons, a rank note, and the engine's expected
    continuation. Returns the HTML string; no display() call, so it works
    the same whether the caller wraps it for Jupyter (display(HTML(...)))
    or marimo (mo.Html(...))."""
    c = candidates[idx - 1]
    move, pv = c["move"], c["move_info"]["pv"]

    temp_board = root_board.copy()
    temp_board.push(move)

    svg_move = render_board_svg(temp_board, move, user)

    reasons = describe_move_reason(c["class_info"])
    # Gap-based, not idx == 1: idx is only "the top choice" when `candidates`
    # is a real ranked list (rank_candidates()'s own output, where entry 1
    # always has gap_text "0.00" by construction). score_move() also reuses
    # this renderer for a single arbitrary move wrapped in a one-item list
    # at idx=1, where that assumption doesn't hold — checking the actual gap
    # keeps the note honest either way.
    rank_note = "This is the engine's top choice." if c["gap_text"] == "0.00" \
        else f"{c['gap_note']} (Gap vs best: {c['gap_text']})"

    # Only Inaccuracy/Blunder tier gets the "What's risky" framing — a
    # Good move just a touch behind the top choice isn't actually wrong,
    # so its expected reply stays a neutral forecast rather than a warning.
    is_risky = c["quality"] in ("Inaccuracy", "Blunder")
    continuation_lines = _describe_continuation(temp_board, pv[1:], max_extra_plies=2, risky=is_risky)

    mv_out = f"{idx}. {c['san']} ({move.uci()}) &mdash; {c['score_text']}"
    detail_lines = [f"Eval: {c['eval_text']}", "<br>".join(reasons), rank_note] + continuation_lines
    detail_out = "<hr>".join(detail_lines)

    return f"""
    <div style="display: flex; align-items: center;">
    <div>{svg_move}</div>
    <div style="margin-left: 20px; font-size: 16px;">{mv_out}<hr>{detail_out}</div>
    </div>"""


def render_candidate_previews_html(root_board, candidates, user):
    """A row of small board thumbnails, one per candidate, each showing the
    position after that candidate's move. Hovering a thumbnail enlarges it
    in place via plain CSS :hover — no engine call, no server round-trip,
    and no change to whichever candidate is selected below. Built from the
    same render_board_svg() the detail view uses, so a preview matches the
    full diagram exactly."""
    cards = []
    for idx, c in enumerate(candidates, start=1):
        temp_board = root_board.copy()
        temp_board.push(c["move"])
        svg = render_board_svg(temp_board, c["move"], user, size=300)
        cards.append(
            f'<div class="cand-preview"><div class="cand-thumb">{svg}</div>'
            f'<div class="cand-label">{idx}. {c["san"]}</div></div>'
        )
    return f"""
    <style>
    .cand-previews {{ display: flex; flex-wrap: wrap; gap: 12px; }}
    .cand-preview {{ width: 120px; }}
    .cand-thumb {{ position: relative; width: 120px; height: 120px; }}
    .cand-thumb svg {{ width: 120px; height: 120px; }}
    .cand-preview:hover .cand-thumb svg {{
        position: absolute; z-index: 10; width: 300px; height: 300px;
        background: white; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    }}
    .cand-label {{ font-size: 13px; text-align: center; }}
    </style>
    <div class="cand-previews">{"".join(cards)}</div>"""


def _display_ranked_moves(root_board, info, user, header, show=True, full_detail=1):
    """Summary table (every candidate) + full board-diagram detail blocks
    (only the top `full_detail` candidates, default 1) for whichever
    position `info` was analyzed from. Keeps the default view scannable —
    all `len(info)` detail blocks stacking up, especially across repeated
    GameCursor.explain() calls, is what actually made this hard to read.
    Drill into any other candidate with explain_reply()/explain_line().
    Shared by moves() (the position on the board) and explain_reply() (the
    position after a candidate move, one ply deeper)."""
    if root_board.is_game_over():
        if root_board.is_checkmate():
            reason = "Checkmate"
        elif root_board.is_stalemate():
            reason = "Stalemate"
        else:
            reason = "Game over"
        print(f"\n{reason} — no moves to analyze.")
        return info

    candidates = rank_candidates(root_board, info)

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

    for idx in range(1, min(full_detail, len(candidates)) + 1):
        if show:
            display(HTML(render_candidate_html(root_board, candidates, idx, user)))

    return info


def moves(board, show=True, full_detail=1):
    """Show the top candidate moves for `board`, ranked and compared
    against each other, with an explanation for each. Only the top
    `full_detail` candidates (default 1) get a full board-diagram detail
    block, to keep the default view scannable; the summary table still
    covers every candidate, and any of them can be drilled into further
    with explain_line() or explain_reply(). Returns the engine's raw
    multipv analysis."""
    user = board.user
    root_board = board.board

    info = _analyze(root_board, multipv=5, time_limit=2.0)
    return _display_ranked_moves(root_board, info, user, header=f"Top {len(info)} Moves:",
                                  show=show, full_detail=full_detail)


def explain_reply(board, info, candidate=1, multipv=3, time_limit=1.0, full_detail=1):
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
                                  header=f"Top {len(reply_info)} Replies for {mover_label}:",
                                  full_detail=full_detail)


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
