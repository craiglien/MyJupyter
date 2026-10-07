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
always get right, same spirit as game.py's _game_phase() heuristic."""

import chess

import game

__ver__ = "0.4.0"
print(f"study ver {__ver__}")

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
