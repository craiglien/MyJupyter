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
def _(mo):
    # Which ply to look at. mo.state() + buttons, so Next/Prev step through
    # the game reactively — see the marimo tutorial's counter example for
    # this exact getter/setter/button pattern.
    get_ply, set_ply = mo.state(0)
    return get_ply, set_ply


@app.cell
def _(mo, records, set_ply):
    prev_button = mo.ui.button(
        label="◀ Prev", on_click=lambda _: set_ply(lambda v: max(v - 1, 0))
    )
    next_button = mo.ui.button(
        label="Next ▶", on_click=lambda _: set_ply(lambda v: min(v + 1, len(records) - 1))
    )
    mo.hstack([prev_button, next_button], justify="start")
    return next_button, prev_button


@app.cell
def _(chess, get_ply, mo, position, records):
    r = records[get_ply()]
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
