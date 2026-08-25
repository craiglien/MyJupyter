import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full")


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
    # the same top-5 multipv list the good candidates use. Always shows
    # something, even when there's nothing to warn about (common early
    # in the game, when there just aren't many captures/checks on offer
    # yet) — otherwise an empty section reads as broken, not "checked,
    # nothing found."
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
    # No bare display here — this cell's output is composed into the
    # side-by-side layout below instead, alongside the try-your-own-move
    # column, so it needs to stay silent on its own.
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
    # References board (not just for the label) so this cell — and the
    # text/button instances it creates — reruns on every ply change,
    # resetting whatever was typed. A SAN move only means something for
    # the exact position it was typed against. No bare display — composed
    # into the side-by-side layout below.
    mover_label = "White" if board.board.turn else "Black"
    move_text = mo.ui.text(label=f"Try a move for {mover_label} (SAN, e.g. Nxe5)",
                            placeholder="Nxe5")
    analyze_button = mo.ui.run_button(label="Analyze")
    return analyze_button, move_text


@app.cell
def _(analyze_button, board, candidates, mo, move_text, position):
    # if/else instead of mo.stop() — this cell's result now feeds the
    # combining layout below rather than displaying itself, so `result`
    # must always be bound and returned, including on the no-click and
    # empty-input paths (mo.stop()'s early exit would skip the return
    # entirely, leaving `result` undefined for that cell's downstream
    # consumer). Still only reaches score_move()'s engine call on an
    # actual click — analyze_button.value is only True on the run
    # immediately following one.
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
    # Side by side, per explicit request: candidate picker on the left,
    # try-your-own-move on the right — so the result renders right next
    # to the button that produced it, not scrolled away below.
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
