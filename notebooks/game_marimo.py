import marimo

__generated_with = "0.19.6"
app = marimo.App()


@app.cell
def _():
    import chess
    import chess.svg
    import marimo as mo

    import game
    import position

    return chess, game, mo, position


@app.cell
def _():
    # Edit and re-run to try a different game — same "paste a full PGN,
    # headers and all" convention as Position.ipynb/Game.ipynb.
    pgn_text = """
[Event "Fool's Mate"]
[White "Amateur"]
[Black "Amateur"]
[Result "0-1"]

1. f3 e5 2. g4 Qh4# 0-1
"""
    return (pgn_text,)


@app.cell
def _(game, pgn_text):
    records = game.sweep_game(pgn_text)
    return (records,)


@app.cell
def _():
    # Which ply to look at. Plain variable, not a widget, for this pass —
    # stepping through the game with buttons is a separate future task.
    ply_index = 0
    return (ply_index,)


@app.cell
def _(chess, mo, ply_index, position, records):
    r = records[ply_index]
    board = position.make(r["fen_after"], "w")

    move_label = f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'}"
    board_svg = chess.svg.board(board=board.board, size=300, orientation=board.user)

    mo.vstack([
        mo.md(f"**{move_label}{r['san']}** — {r['quality']} ({r['white_eval_display']})"),
        mo.Html(board_svg),
    ])
    return (board,)


@app.cell
def _(board, position):
    info = position.moves(board, show=False)
    candidates = position.rank_candidates(board.board, info)
    return (candidates,)


@app.cell
def _(candidates, mo, position):
    options = {
        f"{rank}. {c['san']} — {c['score_text']} (gap {c['gap_text']}, {position.move_tag(c['class_info'])})": rank
        for rank, c in enumerate(candidates, start=1)
    }
    candidate_radio = mo.ui.radio(
        options=options, value=next(iter(options)), label="Candidate moves"
    )
    candidate_radio
    return (candidate_radio,)


@app.cell
def _(board, candidate_radio, candidates, mo, position):
    idx = candidate_radio.value
    mo.Html(position.render_candidate_html(board.board, candidates, idx, board.user))
    return


if __name__ == "__main__":
    app.run()
