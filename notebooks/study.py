"""Analysis for the study track: a second, additive notebook pair
(study.py/study_marimo.py) for richer visualizations and motif detection,
alongside — not replacing — game_marimo.py/collections_marimo.py. See
TASKS.md's "Study track" for the phase breakdown and DECISIONS.md for why
this is a separate track rather than folded into game.py.

Phase 1 (scaffolding) is reuse-only: no new analysis yet, just a thin entry
point so study_marimo.py has its own call site to extend in later phases
without touching game.py. Phase 2 adds the colorblind dual-panel chart
(eval curve + material imbalance) — see material_imbalance()/study_figure()
below.

Colorblind palette (never red/green, per the study track's spec): blue for
White's advantage, orange/amber for Black's, both chosen to match
Okabe-Ito-style colorblind-safe hues. The five piece-type colors in the
material panel are picked from the same constraint — distinguishable
without relying on red vs. green. Phase 3 adds the captures timeline strip
— see captures_timeline() below. Phase 4 adds pawn-structure detection —
see pawn_structure()/PAWN_STRUCTURE_GLOSSARY below. These are the standard
simplified heuristics most study tools use, not formal engine-verified
definitions — real pawn structures have edge cases a one-line rule won't
always get right, same spirit as game.py's _game_phase() heuristic.

Phase 5 adds tactical/positional motif detection — pins, skewers, forks,
discovered attacks, fianchettoed bishops, open/semi-open files, outposts,
king safety, and the Exchange imbalance. Same disclaimer as Phase 4,
doubled: these are geometry/heuristic checks, not a tactics engine — they
find the textbook pattern, not every tactic in a position."""

import chess

import game

__ver__ = "0.5.0"
print(f"study ver {__ver__}")

KING_VALUE = 1000  # for value comparisons in pins/skewers — always "most valuable"

WHITE_ADV_COLOR = "#1f77b4"  # blue — also game.py's existing eval-line color
BLACK_ADV_COLOR = "#d95f02"  # orange/amber
NEUTRAL_COLOR = "#888888"

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
PIECE_LABELS = {
    chess.PAWN: "Pawns", chess.KNIGHT: "Knights", chess.BISHOP: "Bishops",
    chess.ROOK: "Rooks", chess.QUEEN: "Queens",
}
PIECE_COLORS = {
    chess.PAWN: "#0072B2", chess.KNIGHT: "#56B4E9", chess.BISHOP: "#E69F00",
    chess.ROOK: "#F0E442", chess.QUEEN: "#000000",
}
# Outline glyphs for White's pieces, filled glyphs for Black's — the
# standard Unicode convention, so a captured piece's color reads from the
# glyph itself without needing color as the only cue.
PIECE_GLYPHS = {
    (chess.WHITE, chess.PAWN): "♙", (chess.WHITE, chess.KNIGHT): "♘", (chess.WHITE, chess.BISHOP): "♗",
    (chess.WHITE, chess.ROOK): "♖", (chess.WHITE, chess.QUEEN): "♕",
    (chess.BLACK, chess.PAWN): "♟", (chess.BLACK, chess.KNIGHT): "♞", (chess.BLACK, chess.BISHOP): "♝",
    (chess.BLACK, chess.ROOK): "♜", (chess.BLACK, chess.QUEEN): "♛",
}

PAWN_STRUCTURE_GLOSSARY = {
    "Doubled pawns": "Two or more of your pawns stuck on the same file — they "
                     "can't defend each other, and the front one is often a "
                     "fixed target with no pawn able to trade it off.",
    "Isolated pawns": "A pawn with no friendly pawn on either neighboring file, "
                      "so no other pawn can ever come to its defense.",
    "Backward pawns": "A pawn that's fallen behind its neighbors and can't "
                      "safely advance, because an enemy pawn controls the "
                      "square right in front of it.",
    "Passed pawns": "A pawn with no enemy pawn in front of it on its own file "
                    "or either neighboring file — nothing but pieces can stop "
                    "it from reaching the end.",
    "Pawn islands": "A group of pawns on files with no gaps between them. "
                    "Fewer, bigger islands are usually healthier than several "
                    "small, scattered ones.",
}

CONCEPT_GLOSSARY = {
    "Pin": "A piece that can't — or really shouldn't — move, because moving it "
           "would expose a more valuable piece, or the king, to capture along "
           "the same line.",
    "Skewer": "Like a pin in reverse: a valuable piece is attacked first, and "
              "whatever sits behind it on the same line is exposed once it moves.",
    "Fork": "One piece attacking two or more enemy pieces at once, so at least "
            "one of them can't be saved.",
    "Discovered attack": "Moving one piece out of the way reveals an attack "
                         "from a piece that was behind it the whole time.",
    "Fianchetto": "A bishop developed to b2, g2, b7, or g7, aiming down the "
                  "long diagonal from behind its own pawn chain.",
    "Open file": "A file with no pawns at all — rooks and queens control it freely.",
    "Semi-open file": "A file with no pawn of this side, but the opponent "
                      "still has one there — good for a rook, since only enemy "
                      "pieces, not pawns, block it.",
    "Outpost": "A square where a piece — usually a knight — can never be "
               "kicked away by an enemy pawn, defended by one of your own pawns.",
    "Castled": "The king has moved to safety behind its pawn shield, out of the center.",
    "Open king": "The king is still in the center, uncastled, with open lines "
                 "nearby — more exposed to attack.",
    "The Exchange": "One side has an extra rook where the other has an extra "
                    "minor piece instead — a rook is worth a bit more, so being "
                    "\"up the Exchange\" is a real, if modest, advantage.",
}

_DIAG_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
_STRAIGHT_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
_FIANCHETTO_SQUARES = {chess.WHITE: (chess.B2, chess.G2), chess.BLACK: (chess.B7, chess.G7)}


def _slider_dirs(piece_type):
    if piece_type == chess.BISHOP:
        return _DIAG_DIRS
    if piece_type == chess.ROOK:
        return _STRAIGHT_DIRS
    if piece_type == chess.QUEEN:
        return _DIAG_DIRS + _STRAIGHT_DIRS
    return []


def _value_of(board, square):
    piece_type = board.piece_type_at(square)
    return KING_VALUE if piece_type == chess.KING else PIECE_VALUES.get(piece_type, 0)


def _ray_scan(board, color):
    """For every one of `color`'s sliding pieces, walk each of its rays and
    record the first two occupied squares found along it (of either color),
    as (attacker_sq, first_sq, second_sq) triples. Pure geometry — doesn't
    judge whose piece is whose; find_pins()/find_skewers() interpret the
    same scan two different ways."""
    results = []
    for piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        for attacker_sq in board.pieces(piece_type, color):
            af, ar = chess.square_file(attacker_sq), chess.square_rank(attacker_sq)
            for df, dr in _slider_dirs(piece_type):
                f, r = af + df, ar + dr
                seen = []
                while 0 <= f <= 7 and 0 <= r <= 7 and len(seen) < 2:
                    sq = chess.square(f, r)
                    if board.piece_at(sq) is not None:
                        seen.append(sq)
                    f, r = f + df, r + dr
                if len(seen) == 2:
                    results.append((attacker_sq, seen[0], seen[1]))
    return results


def find_pins(board, color):
    """Pieces of `color` pinned along a line to a more valuable piece of the
    same color — including the king (an absolute pin) — by an enemy sliding
    piece. Returns a list of {"pinned", "to", "by", "absolute"} dicts."""
    pins = []
    for attacker_sq, first, second in _ray_scan(board, not color):
        fp, sp = board.piece_at(first), board.piece_at(second)
        if fp.color == color and sp.color == color and _value_of(board, second) > _value_of(board, first):
            pins.append({"pinned": first, "to": second, "by": attacker_sq, "absolute": sp.piece_type == chess.KING})
    return pins


def find_skewers(board, color):
    """Enemy pieces skewered by one of `color`'s sliding pieces: a piece at
    least as valuable as the one behind it is attacked first, so moving it
    (or just getting captured, for the king) exposes the weaker piece
    behind. Returns a list of {"front", "behind", "by"} dicts."""
    skewers = []
    for attacker_sq, first, second in _ray_scan(board, color):
        fp, sp = board.piece_at(first), board.piece_at(second)
        if fp.color != color and sp.color != color and _value_of(board, first) >= _value_of(board, second):
            skewers.append({"front": first, "behind": second, "by": attacker_sq})
    return skewers


def find_forks(board, color):
    """Pieces of `color` (other than the king) simultaneously attacking two
    or more enemy pieces. Returns a list of {"by", "targets"} dicts."""
    forks = []
    for sq, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        targets = [t for t in board.attacks(sq) if board.piece_at(t) and board.piece_at(t).color != color]
        if len(targets) >= 2:
            forks.append({"by": sq, "targets": targets})
    return forks


def discovered_attacks(records):
    """Moves, among every ply already swept, that revealed a new attack
    from a piece other than the one that moved — a discovered attack. No
    new engine calls: for each ply, compares a same-square slider's attacked
    squares before vs. after the move; a newly-attacked enemy piece or king
    that wasn't attacked before means the moved piece had been blocking that
    line. Returns a list of {"x", "mover", "label"} dicts, in ply order."""
    events = []
    for r in records:
        board_before = chess.Board(r["fen_before"])
        move = r["move"]
        mover_color = board_before.turn
        board_after = chess.Board(r["fen_after"])
        for piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            for slider_sq in board_after.pieces(piece_type, mover_color):
                if slider_sq == move.to_square:
                    continue  # the piece that just moved, not a "discovered" attacker
                if board_before.piece_type_at(slider_sq) != piece_type or board_before.color_at(slider_sq) != mover_color:
                    continue  # wasn't this piece before the move (e.g. just promoted here)
                before = {
                    sq for sq in board_before.attacks(slider_sq)
                    if board_before.piece_at(sq) and board_before.piece_at(sq).color != mover_color
                }
                after = {
                    sq for sq in board_after.attacks(slider_sq)
                    if board_after.piece_at(sq) and board_after.piece_at(sq).color != mover_color
                }
                for target in after - before:
                    target_piece = board_after.piece_at(target)
                    events.append({
                        "x": r["ply"], "mover": r["mover"],
                        "label": f"{r['mover']}'s {chess.piece_name(piece_type)} on "
                                 f"{chess.square_name(slider_sq)} now attacks "
                                 f"{'the' if target_piece.piece_type == chess.KING else 'a'} "
                                 f"{chess.piece_name(target_piece.piece_type)} on "
                                 f"{chess.square_name(target)}, discovered by {r['san']}",
                    })
    return events


def find_fianchettos(board, color):
    """Bishops of `color` on the fianchetto squares (b2/g2 for White,
    b7/g7 for Black). Returns a list of squares."""
    return [sq for sq in _FIANCHETTO_SQUARES[color] if board.piece_at(sq) == chess.Piece(chess.BISHOP, color)]


def open_files(board):
    """Files with no pawns of either color, and files semi-open for each
    color (no pawn of that color, but the opponent still has one there).
    Returns {"open", "semi_open_white", "semi_open_black"}, each a list of
    file letters."""
    has_pawn = {f: {chess.WHITE: False, chess.BLACK: False} for f in range(8)}
    for color in (chess.WHITE, chess.BLACK):
        for sq in board.pieces(chess.PAWN, color):
            has_pawn[chess.square_file(sq)][color] = True
    open_f, semi_white, semi_black = [], [], []
    for f, info in has_pawn.items():
        letter = chess.FILE_NAMES[f]
        if not info[chess.WHITE] and not info[chess.BLACK]:
            open_f.append(letter)
        elif not info[chess.WHITE] and info[chess.BLACK]:
            semi_white.append(letter)  # open FOR White -- White has no pawn here
        elif info[chess.WHITE] and not info[chess.BLACK]:
            semi_black.append(letter)  # open FOR Black
    return {"open": open_f, "semi_open_white": semi_white, "semi_open_black": semi_black}


def find_outposts(board, color):
    """Squares in enemy territory (ranks 4-6 for White, 3-5 for Black)
    defended by a friendly pawn, where no enemy pawn on an adjacent file
    could ever advance far enough to challenge it. Reported whether the
    square is empty (a potential outpost) or already holds a friendly piece
    (an outpost in use). Returns a list of squares."""
    outposts = []
    enemy_pawns = board.pieces(chess.PAWN, not color)
    friendly_pawns = board.pieces(chess.PAWN, color)
    ranks = range(3, 6) if color == chess.WHITE else range(2, 5)
    for rank in ranks:
        for file in range(8):
            sq = chess.square(file, rank)
            occupant = board.piece_at(sq)
            if occupant is not None and occupant.color != color:
                continue
            defended = any(
                chess.square_file(p) in (file - 1, file + 1)
                and chess.square_rank(p) == (rank - 1 if color == chess.WHITE else rank + 1)
                for p in friendly_pawns
            )
            if not defended:
                continue
            challengeable = any(
                chess.square_file(p) in (file - 1, file + 1)
                and (chess.square_rank(p) > rank if color == chess.WHITE else chess.square_rank(p) < rank)
                for p in enemy_pawns
            )
            if not challengeable:
                outposts.append(sq)
    return outposts


def king_safety(board, color):
    """A few cheap, well-known king-safety signals for `color`: whether it
    has castled, which side, and how many of its three shield pawns (in
    front of and beside the king) are still on their starting squares. Not
    a full king-safety evaluation — just concrete, explainable facts."""
    king_sq = board.king(color)
    home_rank = 0 if color == chess.WHITE else 7
    castled_kingside = king_sq == chess.square(6, home_rank)
    castled_queenside = king_sq == chess.square(2, home_rank)
    king_file = chess.square_file(king_sq)
    shield_files = [f for f in (king_file - 1, king_file, king_file + 1) if 0 <= f <= 7]
    shield_rank = 1 if color == chess.WHITE else 6
    intact_shield = sum(
        1 for f in shield_files
        if board.piece_at(chess.square(f, shield_rank)) == chess.Piece(chess.PAWN, color)
    )
    return {
        "castled": "Kingside" if castled_kingside else "Queenside" if castled_queenside else None,
        "shield_pawns_intact": intact_shield,
        "shield_pawns_total": len(shield_files),
        "open_king": not (castled_kingside or castled_queenside) and king_file in (3, 4),
    }


def exchange_imbalance(board):
    """Whether one side is up the Exchange — an extra rook where the other
    side has an extra minor piece instead. Returns None if material doesn't
    show this pattern, else {"up": "White"|"Black"}."""
    def counts(color):
        rooks = len(board.pieces(chess.ROOK, color))
        minors = len(board.pieces(chess.KNIGHT, color)) + len(board.pieces(chess.BISHOP, color))
        return rooks, minors

    wr, wm = counts(chess.WHITE)
    br, bm = counts(chess.BLACK)
    if wr - br == 1 and bm - wm == 1:
        return {"up": "White"}
    if br - wr == 1 and wm - bm == 1:
        return {"up": "Black"}
    return None


def concepts_html(board, discovered=None):
    """Badges for the tactical/positional concepts detected in `board`:
    pins, skewers, forks, fianchettoed bishops, open/semi-open files,
    outposts, castling/king safety, and the Exchange imbalance, each with
    its plain-English definition from CONCEPT_GLOSSARY on hover.
    `discovered` is an optional list of this-ply events from
    discovered_attacks() — that one needs the move, not just the static
    board, so study_marimo.py filters it to the current ply itself. Returns
    an HTML string."""
    chips = []

    def _chip(name, text):
        chips.append(f'<span class="badge" title="{CONCEPT_GLOSSARY[name]}">{text}</span>')

    for color in (chess.WHITE, chess.BLACK):
        label = "White" if color == chess.WHITE else "Black"
        for p in find_pins(board, color):
            kind = "Absolute pin" if p["absolute"] else "Pin"
            _chip("Pin", f'{kind}: {label}\'s {chess.piece_name(board.piece_type_at(p["pinned"]))} '
                         f'on {chess.square_name(p["pinned"])}')
        for s in find_skewers(board, color):
            _chip("Skewer", f'{label} skewers the {chess.piece_name(board.piece_type_at(s["front"]))} '
                            f'on {chess.square_name(s["front"])}')
        for f in find_forks(board, color):
            targets_txt = ", ".join(chess.square_name(t) for t in f["targets"])
            _chip("Fork", f'{label}\'s {chess.piece_name(board.piece_type_at(f["by"]))} on '
                          f'{chess.square_name(f["by"])} forks {targets_txt}')
        for sq in find_fianchettos(board, color):
            _chip("Fianchetto", f'{label} fianchetto on {chess.square_name(sq)}')

    files = open_files(board)
    for f in files["open"]:
        _chip("Open file", f'Open {f}-file')
    for f in files["semi_open_white"]:
        _chip("Semi-open file", f'{f}-file semi-open for White')
    for f in files["semi_open_black"]:
        _chip("Semi-open file", f'{f}-file semi-open for Black')

    for color in (chess.WHITE, chess.BLACK):
        label = "White" if color == chess.WHITE else "Black"
        for sq in find_outposts(board, color):
            occupant = board.piece_at(sq)
            state = f"occupied by a {chess.piece_name(occupant.piece_type)}" if occupant else "open"
            _chip("Outpost", f'{label} outpost on {chess.square_name(sq)} ({state})')

    for color in (chess.WHITE, chess.BLACK):
        label = "White" if color == chess.WHITE else "Black"
        ks = king_safety(board, color)
        if ks["castled"]:
            _chip("Castled", f'{label} castled {ks["castled"]} '
                              f'({ks["shield_pawns_intact"]}/{ks["shield_pawns_total"]} shield pawns)')
        elif ks["open_king"]:
            _chip("Open king", f"{label}'s king is still uncastled in the center")

    exch = exchange_imbalance(board)
    if exch:
        _chip("The Exchange", f'{exch["up"]} is up the Exchange')

    for e in (discovered or []):
        _chip("Discovered attack", e["label"])

    body = "".join(chips) if chips else "<i>Nothing notable detected right now.</i>"
    return f'<div class="pawn-badges">{_BADGE_STYLE}{body}</div>'


def load_game(pgn_text, time_limit=0.3):
    """Sweep a PGN via game.sweep_game() — the study notebook's one entry
    point for ply records, so later phases (material imbalance, captures,
    motif detection) have a single place to extend. Pure passthrough for
    now; Phase 1 adds no new analysis."""
    return game.sweep_game(pgn_text, time_limit=time_limit)


def material_imbalance(records):
    """Net material difference (White minus Black) per piece type, in
    pawns-equivalent units, for every ply already swept. No new engine
    calls — each ply's board comes straight from the fen_after sweep_game()
    already recorded. Returns a list of dicts, one per record, keyed by
    piece label ("Pawns", "Knights", …); positive means White has more of
    that piece type, negative means Black does."""
    rows = []
    for r in records:
        board = chess.Board(r["fen_after"])
        rows.append({
            PIECE_LABELS[pt]: (len(board.pieces(pt, chess.WHITE)) - len(board.pieces(pt, chess.BLACK))) * value
            for pt, value in PIECE_VALUES.items()
        })
    return rows


def captures_timeline(records):
    """Capture events for every ply already swept, in ply order: which ply
    (matching study_figure()'s 1-based x), which side made the capture, and
    the Unicode glyph + plain-English label for the piece that was lost. No
    new engine calls — reconstructs each ply's board from fen_before and
    the move already recorded. Handles en passant, where the captured pawn
    isn't on the move's to-square."""
    events = []
    for r in records:
        board = chess.Board(r["fen_before"])
        move = r["move"]
        if not board.is_capture(move):
            continue
        captured_color = not board.turn  # the side NOT about to move owns the captured piece
        captured_type = chess.PAWN if board.is_en_passant(move) else board.piece_at(move.to_square).piece_type
        captured_side = "White" if captured_color else "Black"
        events.append({
            "x": r["ply"],
            "mover": r["mover"],
            "captured_color": captured_side,
            "glyph": PIECE_GLYPHS[(captured_color, captured_type)],
            "label": f"{r['mover']} captures — {captured_side} loses a {chess.piece_name(captured_type)}",
        })
    return events


def study_figure(records, material_rows, captures=None, current_ply=None):
    """Three-panel colorblind-safe chart for mo.ui.plotly: eval curve on
    top (blue shading above zero = White ahead, orange below = Black ahead
    — never red/green), stacked material imbalance by piece type in the
    middle, and a captures timeline strip at the bottom, all sharing the
    ply axis. current_ply (0-based, matching the notebook's stepper) draws
    a dashed vertical cursor across all three panels when given."""
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    captures = captures or []
    xs = list(range(1, len(records) + 1))
    ys = [max(-10, min(10, r["white_eval"])) for r in records]
    ys_pos = [max(v, 0) for v in ys]
    ys_neg = [min(v, 0) for v in ys]
    custom = [
        [f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'} {r['san']}",
         r["white_eval_display"], r["quality"]]
        for r in records
    ]

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, row_heights=[0.55, 0.3, 0.15], vertical_spacing=0.08,
        subplot_titles=("Evaluation over the game", "Material imbalance by piece type", "Captures"),
    )

    fig.add_trace(go.Scatter(
        x=xs, y=ys_pos, mode="none", fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.18)", hoverinfo="skip", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=xs, y=ys_neg, mode="none", fill="tozeroy",
        fillcolor="rgba(217, 95, 2, 0.18)", hoverinfo="skip", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers", marker=dict(size=5), line=dict(color=WHITE_ADV_COLOR),
        customdata=custom, showlegend=False,
        hovertemplate="%{customdata[0]} · %{customdata[1]} · %{customdata[2]}<extra></extra>",
    ), row=1, col=1)
    fig.add_hline(y=0, line_color=NEUTRAL_COLOR, line_width=1, row=1, col=1)

    for pt, label in PIECE_LABELS.items():
        fig.add_trace(go.Bar(
            x=xs, y=[row[label] for row in material_rows], name=label,
            marker_color=PIECE_COLORS[pt],
        ), row=2, col=1)
    fig.add_hline(y=0, line_color=NEUTRAL_COLOR, line_width=1, row=2, col=1)
    fig.update_layout(barmode="relative")

    fig.add_trace(go.Scatter(
        x=[e["x"] for e in captures], y=[0] * len(captures), mode="text",
        text=[e["glyph"] for e in captures], textfont=dict(size=18),
        hovertext=[e["label"] for e in captures], hoverinfo="text", showlegend=False,
    ), row=3, col=1)
    fig.update_yaxes(visible=False, range=[-1, 1], row=3, col=1)

    if current_ply is not None:
        fig.add_vline(
            x=current_ply + 1, line_color=NEUTRAL_COLOR, line_width=1, line_dash="dash",
            row="all", col=1,
        )

    fig.update_layout(
        height=600, margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Ply (1 = White's first move)", row=3, col=1)
    fig.update_yaxes(title_text="Advantage (pawns)", row=1, col=1)
    fig.update_yaxes(title_text="Material (pawns-eq.)", row=2, col=1)
    return fig


def pawn_structure(board, color):
    """Heuristic pawn-structure facts for `color` on `board`: doubled,
    isolated, backward, and passed pawns (each a list of squares), plus the
    number of pawn islands. See the module docstring — these are the
    standard simplified heuristics, not formal definitions.

    - Doubled: 2+ of this color's pawns share a file.
    - Isolated: no friendly pawn on either neighboring file, at any rank.
    - Passed: no enemy pawn on this file or either neighboring file that's
      still ahead of it (so nothing but a piece can ever stop it).
    - Backward: not passed, no friendly pawn on a neighboring file that's
      level with or behind it (so it has no potential defender), and the
      square right in front of it is attacked by an enemy pawn (so
      advancing loses it).
    - Pawn islands: the number of contiguous runs of occupied files."""
    pawns = board.pieces(chess.PAWN, color)
    enemy_pawns = board.pieces(chess.PAWN, not color)
    files_with_pawns = {}
    for sq in pawns:
        files_with_pawns.setdefault(chess.square_file(sq), []).append(sq)

    doubled = [sq for squares in files_with_pawns.values() if len(squares) > 1 for sq in squares]

    isolated = [
        sq for f, squares in files_with_pawns.items()
        if (f - 1) not in files_with_pawns and (f + 1) not in files_with_pawns
        for sq in squares
    ]

    passed = []
    for sq in pawns:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        blocked = any(
            chess.square_file(esq) in (f - 1, f, f + 1)
            and (chess.square_rank(esq) > r if color == chess.WHITE else chess.square_rank(esq) < r)
            for esq in enemy_pawns
        )
        if not blocked:
            passed.append(sq)

    backward = []
    for sq in pawns:
        if sq in passed:
            continue
        f, r = chess.square_file(sq), chess.square_rank(sq)
        has_potential_defender = any(
            chess.square_file(other) in (f - 1, f + 1)
            and (chess.square_rank(other) <= r if color == chess.WHITE else chess.square_rank(other) >= r)
            for other in pawns if other != sq
        )
        if has_potential_defender:
            continue
        stop_square = sq + 8 if color == chess.WHITE else sq - 8
        if not (0 <= stop_square <= 63):
            continue
        if any(board.piece_type_at(a) == chess.PAWN for a in board.attackers(not color, stop_square)):
            backward.append(sq)

    occupied_files = sorted(files_with_pawns.keys())
    islands = sum(1 for i, f in enumerate(occupied_files) if i == 0 or f != occupied_files[i - 1] + 1)

    return {"doubled": doubled, "isolated": isolated, "backward": backward, "passed": passed, "islands": islands}


_STRUCTURE_BADGE_KEYS = (
    ("doubled", "Doubled pawns"), ("isolated", "Isolated pawns"),
    ("backward", "Backward pawns"), ("passed", "Passed pawns"),
)

_BADGE_STYLE = """<style>
  .pawn-badges .badge { display:inline-block; margin:2px 4px 2px 0; padding:3px 8px;
    border-radius:12px; background:#eee; font-size:13px; cursor:help; }
  .pawn-badges .side { margin-bottom:6px; }
</style>"""


def pawn_structure_html(board):
    """Badges for both sides' pawn structure at `board` (a chess.Board),
    each with its plain-English definition from PAWN_STRUCTURE_GLOSSARY on
    hover. The one entry point study_marimo.py calls — see pawn_structure()
    for the underlying facts. Returns an HTML string."""

    def _side(label, color):
        structure = pawn_structure(board, color)
        chips = [
            f'<span class="badge" title="{PAWN_STRUCTURE_GLOSSARY[name]}">'
            f'{name} ({", ".join(chess.square_name(sq) for sq in structure[key])})</span>'
            for key, name in _STRUCTURE_BADGE_KEYS if structure[key]
        ]
        islands = structure["islands"]
        chips.append(
            f'<span class="badge" title="{PAWN_STRUCTURE_GLOSSARY["Pawn islands"]}">'
            f'{islands} pawn island{"s" if islands != 1 else ""}</span>'
        )
        return f'<div class="side"><b>{label}</b><br>{"".join(chips)}</div>'

    return f'<div class="pawn-badges">{_BADGE_STYLE}{_side("White", chess.WHITE)}{_side("Black", chess.BLACK)}</div>'
