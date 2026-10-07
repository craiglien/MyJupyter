import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    import position
    import study
    return mo, position, study


@app.cell
def _():
    # Phase 1 scaffolding only — in-memory, no disk persistence yet (unlike
    # game_marimo.py's current_game.pgn). A real game, not blank, so the
    # sweep below has something to analyze before you paste your own.
    DEFAULT_PGN = """
    1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be2 e5 7. Nb3 Be7
    8. O-O O-O *
    """
    return (DEFAULT_PGN,)


@app.cell
def _(DEFAULT_PGN, mo):
    # Same get/set-state-plus-button pattern as game_marimo.py's PGN box:
    # the text area edits freely, and only "Load game" commits it, so the
    # sweep below doesn't re-run Stockfish on every keystroke.
    get_pgn_text, set_pgn_text = mo.state(DEFAULT_PGN, allow_self_loops=True)
    return get_pgn_text, set_pgn_text


@app.cell
def _(get_pgn_text, mo, set_pgn_text):
    pgn_editor = mo.ui.text_area(
        value=get_pgn_text(), label="Game (PGN)", full_width=True
    )

    def _load(_):
        set_pgn_text(lambda v: pgn_editor.value)

    load_button = mo.ui.button(label="Load game", on_click=_load)

    mo.vstack([
        mo.md("### Study: paste a game"),
        pgn_editor,
        load_button,
    ])
    return


@app.cell
def _(get_pgn_text):
    pgn_text = get_pgn_text()
    return (pgn_text,)


@app.cell
def _(mo, pgn_text, study):
    # study.load_game() is a thin passthrough to game.sweep_game() for now —
    # see study.py. Later phases (material imbalance, captures, motif
    # detection) extend this same call site.
    with mo.status.spinner(
        title="Analyzing game…",
        subtitle="Running Stockfish on every ply — longer games take longer",
    ):
        records = study.load_game(pgn_text)
    return (records,)


@app.cell
def _(records, study):
    # Pure python-chess, no new engine calls — see study.material_imbalance()
    # and study.captures_timeline().
    material_rows = study.material_imbalance(records)
    captures = study.captures_timeline(records)
    return captures, material_rows


@app.cell
def _(mo):
    # Same mo.state()-plus-button stepper pattern as game_marimo.py.
    get_ply, set_ply = mo.state(0, allow_self_loops=True)
    return get_ply, set_ply


@app.cell
def _(captures, get_ply, material_rows, mo, records, set_ply, study):
    # Clicking a point on any of the three panels jumps the stepper there,
    # same pattern as game_marimo.py's eval chart. The current ply is drawn
    # back in as a dashed cursor line, so this cell depends on get_ply() too.
    def _jump(points):
        if points:
            idx = int(points[0]["x"]) - 1
            set_ply(lambda v: idx)

    current_ply = min(get_ply(), len(records) - 1)
    study_chart = mo.ui.plotly(
        study.study_figure(records, material_rows, captures=captures, current_ply=current_ply),
        on_change=_jump,
    )
    return (study_chart,)


@app.cell
def _(mo, study_chart):
    mo.vstack([
        mo.md("### Evaluation + material"),
        study_chart,
    ])
    return


@app.cell
def _(get_ply, mo, records, set_ply):
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
def _(get_ply, mo, position, records):
    # Clamped, not just get_ply() directly: loading a shorter game while
    # deep into a longer one would otherwise leave the ply past the end of
    # the new records and crash this cell.
    ply = min(get_ply(), len(records) - 1)
    r = records[ply]
    board = position.make(r["fen_after"], "w")

    move_label = f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'}"
    board_svg = position.render_board_svg(board.board, r["move"], board.user)

    mo.vstack([
        mo.md(f"**Move {ply + 1} of {len(records)}: {move_label}{r['san']}** — "
              f"{r['quality']} ({r['white_eval_display']})"),
        mo.Html(board_svg),
    ])
    return (board,)


@app.cell
def _(board, mo, study):
    # Pure python-chess, no new engine calls — see study.pawn_structure().
    mo.vstack([
        mo.md("### Pawn structure"),
        mo.Html(study.pawn_structure_html(board.board)),
    ])
    return


if __name__ == "__main__":
    app.run()
