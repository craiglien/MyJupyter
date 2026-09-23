import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full")


@app.cell
def _():
    import os

    import marimo as mo

    import game
    import game_collections
    import position

    # Same RUN_COMMIT* env vars entrypoint.sh's startup banner already
    # prints to the terminal (see run.sh/DECISIONS.md) — printed here too,
    # right alongside position/game/game_collections's own version prints,
    # rather than as a separate rendered cell further down the page.
    _commit = os.environ.get("RUN_COMMIT", "unknown")
    _subject = os.environ.get("RUN_COMMIT_SUBJECT", "unknown")
    _reltime = os.environ.get("RUN_COMMIT_RELTIME", "unknown")
    print(f"commit {_commit} — {_subject} ({_reltime})")

    return game, game_collections, mo, position


@app.cell
def _(mo):
    # Which game, within the chosen collection. Mirrors get_ply/set_ply's
    # getter/setter/button pattern below, one level up — this steps through
    # games in a collection, not plies within one game.
    get_game_idx, set_game_idx = mo.state(0, allow_self_loops=True)
    return get_game_idx, set_game_idx


@app.cell
def _(game_collections, mo):
    collection_names = game_collections.list_collections()
    collection_picker = mo.ui.dropdown(
        options=collection_names,
        value=collection_names[0] if collection_names else None,
        label="Collection",
    )
    return collection_names, collection_picker


@app.cell
def _(collection_picker, game_collections):
    collection_games = game_collections.list_games(collection_picker.value) if collection_picker.value else []
    return (collection_games,)


@app.cell
def _(collection_games, get_game_idx, mo, set_game_idx):
    # Clamped, not reset — switching to a shorter collection/game can leave
    # a stale index from a longer one pointing past the end. Same "clamp on
    # read rather than force a reset" choice made for button_ply below.
    button_game_idx = min(get_game_idx(), len(collection_games) - 1) if collection_games else 0
    game_first_button = mo.ui.button(
        label="⏮ First game",
        on_click=lambda _: set_game_idx(lambda v: 0),
        disabled=not collection_games or button_game_idx == 0,
    )
    game_prev_button = mo.ui.button(
        label="◀ Prev game",
        on_click=lambda _: set_game_idx(lambda v: max(v - 1, 0)),
        disabled=not collection_games,
    )
    game_next_button = mo.ui.button(
        label="Next game ▶",
        on_click=lambda _: set_game_idx(lambda v: min(v + 1, len(collection_games) - 1)),
        disabled=not collection_games,
    )
    game_last_button = mo.ui.button(
        label="Last game ⏭",
        on_click=lambda _: set_game_idx(lambda v: len(collection_games) - 1),
        disabled=not collection_games or button_game_idx == len(collection_games) - 1,
    )
    return button_game_idx, game_first_button, game_last_button, game_next_button, game_prev_button


@app.cell
def _(button_game_idx, collection_games):
    # No collection selected yet (or an empty one) — stay on a small default
    # demo game instead of resetting to nothing, same "don't go blank"
    # convention as game_marimo.py's own always-present pgn_text.
    if collection_games:
        pgn_text = collection_games[button_game_idx]["pgn_text"]
        current_game_label = collection_games[button_game_idx]["label"]
    else:
        pgn_text = """
        1. e4 e5 2. Nc3 Nc6 3. Bc4 Nf6 4. Nf3 Bb4 *
        """
        current_game_label = "(no collection selected — default demo game)"
    return current_game_label, pgn_text


@app.cell
def _(
    collection_picker,
    current_game_label,
    game_first_button,
    game_last_button,
    game_next_button,
    game_prev_button,
    mo,
):
    mo.vstack([
        mo.md("### Choose a collection & game"),
        collection_picker,
        mo.hstack([game_first_button, game_prev_button, game_next_button, game_last_button], justify="start"),
        mo.md(f"**{current_game_label}**"),
    ])
    return


@app.cell
def _(game, pgn_text):
    records = game.sweep_game(pgn_text)
    return (records,)


@app.cell
def _(mo):
    # Which ply to look at within the current game — see game_marimo.py for
    # the full rationale on this getter/setter/button pattern.
    get_ply, set_ply = mo.state(0, allow_self_loops=True)
    return get_ply, set_ply


@app.cell
def _(mo):
    # Board orientation (True = viewing from Black's side).
    get_flipped, set_flipped = mo.state(False, allow_self_loops=True)
    return get_flipped, set_flipped


@app.cell
def _(get_flipped, get_ply, mo, records, set_flipped, set_ply):
    # Clamped, not reset — switching games can leave a stale ply from a
    # longer game pointing past the end of a shorter one.
    button_ply = min(get_ply(), len(records) - 1)
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
    flip_button = mo.ui.button(
        label=f"⇄ Flip board (viewing as {'Black' if get_flipped() else 'White'})",
        on_click=lambda _: set_flipped(lambda v: not v),
    )
    mo.vstack([
        mo.md("### Step through the game"),
        mo.hstack([first_button, prev_button, next_button, last_button, flip_button], justify="start"),
    ])
    return


@app.cell(hide_code=True)
def _(get_flipped, get_ply, mo, position, records):
    ply = min(get_ply(), len(records) - 1)
    r = records[ply]
    board = position.make(r["fen_after"], "b" if get_flipped() else "w")

    move_label = f"{r['move_number']}{'.' if r['mover'] == 'White' else '...'}"
    board_svg = position.render_board_svg(board.board, r["move"], board.user)

    mo.vstack([
        mo.md(f"**Move {ply + 1} of {len(records)}: {move_label}{r['san']}** — "
              f"{r['quality']} ({r['white_eval_display']})"),
        mo.Html(board_svg),
    ])
    return (board,)


@app.cell
def _(board, mo, position):
    info = position.moves(board, show=False)
    mo.stop(not info, mo.md("*Game over — no candidate moves at this position.*"))
    candidates = position.rank_candidates(board.board, info)
    dont_candidates = position.rank_dont_list(board.board, info)
    return candidates, dont_candidates


@app.cell
def _(board, dont_candidates, mo, position):
    if dont_candidates:
        dont_blocks = "<hr>".join(
            position.render_dont_html(board.board, dont_candidates, idx, board.user)
            for idx in range(1, len(dont_candidates) + 1)
        )
        dont_body = mo.Html(dont_blocks)
    else:
        dont_body = mo.md("*Nothing tempting-and-bad stands out here.*")
    mo.vstack([
        mo.md("### Tempting, but don't"),
        dont_body,
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
    return (candidate_radio,)


@app.cell
def _(board, candidate_radio, candidates, mo, position):
    idx = candidate_radio.value
    detail_html = mo.Html(position.render_candidate_html(board.board, candidates, idx, board.user))
    return (detail_html,)


@app.cell
def _(board, mo):
    mover_label = "White" if board.board.turn else "Black"
    move_text = mo.ui.text(label=f"Try a move for {mover_label} (SAN, e.g. Nxe5)",
                            placeholder="Nxe5")
    analyze_button = mo.ui.run_button(label="Analyze")
    return analyze_button, move_text


@app.cell
def _(analyze_button, board, candidates, mo, move_text, position):
    if not analyze_button.value:
        result = mo.md("")
    else:
        text = move_text.value.strip()
        if not text:
            result = mo.md("*Type a move first.*")
        else:
            try:
                move = board.board.parse_san(text)
            except ValueError as e:
                position.log.debug(
                    "try-your-own-move: illegal SAN %r at fen=%s (%s)", text, board.board.fen(), e
                )
                result = mo.md(f"*Not a legal move here — {e}*")
            else:
                existing = next(
                    (i for i, c in enumerate(candidates, start=1) if c["move"] == move), None
                )
                if existing is not None:
                    result = mo.md(
                        f"*That's already candidate {existing} above "
                        f"({candidates[existing - 1]['san']}).*"
                    )
                else:
                    custom = position.score_move(board.board, move, best_score=candidates[0]["score"])
                    result = mo.Html(position.render_candidate_html(board.board, [custom], 1, board.user))
    return (result,)


@app.cell
def _(analyze_button, candidate_radio, detail_html, mo, move_text, result):
    mo.hstack(
        [
            mo.vstack([candidate_radio, detail_html]),
            mo.vstack([
                mo.md("### Try your own move"),
                mo.hstack([move_text, analyze_button], justify="start"),
                result,
            ]),
        ],
        justify="start",
        align="start",
        gap=2,
    )
    return


if __name__ == "__main__":
    app.run()
