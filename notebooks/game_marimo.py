import marimo

__generated_with = "0.23.16"
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
    1. e4 e5 2. Nc3 Nf6 3. Nf3 Bb4 4. a3 Bxc3 5. bxc3 d5 6. exd5 Nxd5 7. Nxe5 Qe7 8.
    Qe2 O-O *
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
    # this exact getter/setter/button pattern. allow_self_loops=True so the
    # button cell below (which calls set_ply) still re-runs on its own
    # clicks — needed to keep the First/Last disabled state current, since
    # marimo otherwise excludes a state setter's own caller cell from the
    # rerun it triggers.
    get_ply, set_ply = mo.state(0, allow_self_loops=True)
    return get_ply, set_ply


@app.cell
def _(get_ply, mo, records, set_ply):
    # A static caption here, not a live ply count — the live "ply X of N"
    # indicator lives in the board cell below instead, which is simpler
    # since it only reads get_ply() and never calls set_ply.
    #
    # Named button_ply, not ply — the board cell below also does
    # `ply = get_ply()`, and marimo treats the same top-level name assigned
    # in two cells as a namespace conflict (both cells get marked "CELL NOT
    # RUN"), the same class of collision noted in DECISIONS.md for the
    # candidate-table cell's loop variable.
    button_ply = get_ply()
    first_button = mo.ui.button(
        label="⏮ First", on_click=lambda _: set_ply(lambda v: 0), disabled=button_ply == 0
    )
    prev_button = mo.ui.button(
        label="◀ Prev", on_click=lambda _: set_ply(lambda v: max(v - 1, 0))
    )
    next_button = mo.ui.button(
        label="Next ▶", on_click=lambda _: set_ply(lambda v: min(v + 1, len(records) - 1))
    )
    last_button = mo.ui.button(
        label="Last ⏭",
        on_click=lambda _: set_ply(lambda v: len(records) - 1),
        disabled=button_ply == len(records) - 1,
    )
    mo.vstack([
        mo.md("### Step through the game"),
        mo.hstack([first_button, prev_button, next_button, last_button], justify="start"),
    ])
    return


@app.cell(hide_code=True)
def _(chess, get_ply, mo, position, records):
    ply = get_ply()
    r = records[ply]
    board = position.make(r["fen_after"], "w")

    move_label = f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'}"
    board_svg = chess.svg.board(board=board.board, size=300, orientation=board.user)

    mo.vstack([
        mo.md(f"**Move {ply + 1} of {len(records)}: {move_label}{r['san']}** — "
              f"{r['quality']} ({r['white_eval_display']})"),
        mo.Html(board_svg),
    ])
    return (board,)


@app.cell
def _(board, mo, position):
    info = position.moves(board, show=False)
    # No legal moves at this ply (game-ending checkmate/stalemate move, e.g.
    # the last ply of a decisive game) — nothing to rank or show a picker
    # for. mo.stop() shows this message in place of the cell's output and
    # skips the candidate-picker/detail cells below rather than erroring.
    mo.stop(not info, mo.md("*Game over — no candidate moves at this position.*"))
    candidates = position.rank_candidates(board.board, info)
    dont_candidates = position.rank_dont_list(board.board, info)
    return candidates, dont_candidates


@app.cell
def _(board, dont_candidates, mo, position):
    # Tempting-looking-but-bad moves, shown above the good candidates —
    # see rank_dont_list()'s own docstring for why these can't come from
    # the same top-5 multipv list the good candidates use. Empty output
    # (via mo.stop) when there's nothing tempting-and-bad to warn about.
    mo.stop(not dont_candidates, mo.md(""))
    dont_blocks = "<hr>".join(
        position.render_dont_html(board.board, dont_candidates, idx, board.user)
        for idx in range(1, len(dont_candidates) + 1)
    )
    mo.vstack([
        mo.md("### Tempting, but don't"),
        mo.Html(dont_blocks),
    ])
    return


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
