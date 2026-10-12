import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    import board_widget
    import chess
    import endgame_studies
    import nav

    mo.Html(nav.nav_bar_html("endgame_studies"))
    return board_widget, chess, endgame_studies, mo, nav


@app.cell
def _(mo):
    # moves_so_far: UCI strings played from the variant's starting FEN.
    # key: (study_slug, variant) last seen, to detect when to reset moves.
    # applied: the last widget.last_move value already acted on, so a drag
    # already processed doesn't get re-applied on an unrelated rerun.
    # error: an illegal-move message to show, if any.
    get_moves, set_moves = mo.state((), allow_self_loops=True)
    get_key, set_key = mo.state(None, allow_self_loops=True)
    get_applied, set_applied = mo.state("", allow_self_loops=True)
    get_error, set_error = mo.state("", allow_self_loops=True)
    return (
        get_applied,
        get_error,
        get_key,
        get_moves,
        set_applied,
        set_error,
        set_key,
        set_moves,
    )


@app.cell
def _(endgame_studies, mo):
    study_picker = mo.ui.dropdown(
        options=endgame_studies.list_studies(), label="Study"
    )
    study_picker
    return (study_picker,)


@app.cell
def _(endgame_studies, mo, study_picker):
    _variants = endgame_studies.list_variants(study_picker.value) if study_picker.value else []
    variant_picker = mo.ui.dropdown(
        options={(v or "(default)"): v for v in _variants},
        value=(_variants[0] or "(default)") if _variants else None,
        label="Variant",
    )
    variant_picker
    return (variant_picker,)


@app.cell
def _(get_key, set_applied, set_error, set_key, set_moves, study_picker, variant_picker):
    # New study/variant -> start that position over: clear the played moves,
    # the drag-dedupe tracker, and any stale error message.
    slug = study_picker.value
    variant = variant_picker.value
    key = (slug, variant)
    if slug and key != get_key():
        set_key(lambda _v: key)
        set_moves(lambda _v: ())
        set_applied(lambda _v: "")
        set_error(lambda _v: "")
    return key, slug, variant


@app.cell
def _(endgame_studies, mo, slug, variant):
    study_data = endgame_studies.load_variant(slug, variant) if slug else None
    composer_moves = list(study_data["games"][0].mainline_moves()) if study_data else []
    mo.vstack([
        mo.md("### Endgame study"),
        mo.md(study_data["notes"]) if study_data and study_data["notes"] else mo.md("_no notes_"),
    ])
    return composer_moves, study_data


@app.cell
def _(chess, composer_moves, endgame_studies, get_moves, study_data):
    board = chess.Board(study_data["fen"]) if study_data else None
    for _uci in (get_moves() if study_data else ()):
        board.push_uci(_uci)
    on_script = endgame_studies.on_script(get_moves(), composer_moves) if study_data else True
    solved = endgame_studies.solved(get_moves(), composer_moves) if study_data else False
    return board, on_script, solved


@app.cell
def _(mo, set_applied, set_error, set_moves, study_data):
    def _reset(_):
        set_moves(lambda _v: ())
        set_applied(lambda _v: "")
        set_error(lambda _v: "")

    reset_button = mo.ui.button(label="↺ Reset this study", on_click=_reset)
    reset_button if study_data else None
    return (reset_button,)


@app.cell
def _(board, board_widget, mo, study_data):
    widget = (
        mo.ui.anywidget(board_widget.BoardWidget(
            fen=board.fen(),
            orientation="white",
            turn_color=board_widget.color_name(board.turn),
            dests=board_widget.legal_dests(board),
        ))
        if study_data
        else None
    )
    widget
    return (widget,)


@app.cell
def _(
    board,
    composer_moves,
    endgame_studies,
    get_applied,
    set_applied,
    set_error,
    set_moves,
    study_data,
    widget,
):
    # The drag side of move input. widget.last_move is sticky (see
    # board_widget.py), so only act on it the first time it differs from
    # the last one we already applied.
    if study_data and widget.last_move and widget.last_move != get_applied():
        _uci = widget.last_move
        try:
            _mv = board.parse_uci(_uci)
        except ValueError:
            _mv = None
        if _mv is None or _mv not in board.legal_moves:
            set_error(lambda _v: f"Illegal move dragged: {_uci}")
        else:
            set_moves(lambda v: endgame_studies.apply_move(v, composer_moves, _mv))
            set_error(lambda _v: "")
        set_applied(lambda _v: _uci)
    return


@app.cell
def _(board, composer_moves, endgame_studies, mo, set_error, set_moves, study_data):
    def _play(_):
        san = san_box.value.strip()
        if not san:
            return
        try:
            mv = board.parse_san(san)
        except ValueError:
            set_error(lambda _v: f"Not a legal move: {san!r}")
            return
        set_moves(lambda v: endgame_studies.apply_move(v, composer_moves, mv))
        set_error(lambda _v: "")

    san_box = mo.ui.text(label="Or type a move (SAN)", placeholder="e.g. Qh2+")
    play_button = mo.ui.button(label="Play", on_click=_play)
    mo.hstack([san_box, play_button], justify="start") if study_data else None
    return play_button, san_box


@app.cell
def _(board, get_moves, mo, on_script, solved, study_data):
    if not study_data:
        status = mo.md("_Pick a study above to begin._")
    elif solved:
        status = mo.md(f"**Solved!** You played the composer's full line ({len(get_moves())} plies).")
    elif not on_script:
        status = mo.md(
            f"_Off the recorded line after {len(get_moves())} plies — no more "
            "auto-replies for Black. Keep playing if you like, or Reset to try again._"
        )
    else:
        status = mo.md(f"To move: **{'White' if board.turn else 'Black'}** ({len(get_moves())} plies played)")
    status
    return (status,)


@app.cell
def _(get_error, mo):
    mo.md(f"⚠️ {get_error()}") if get_error() else None
    return


if __name__ == "__main__":
    app.run()
