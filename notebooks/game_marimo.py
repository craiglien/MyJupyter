import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import os

    import marimo as mo

    import game
    import position

    # Same RUN_COMMIT* env vars entrypoint.sh's startup banner already
    # prints to the terminal (see run.sh/DECISIONS.md). Rendered as real
    # cell output (mo.md), not print() — marimo run (see DECISIONS.md's
    # Phase 3 entry) doesn't display stdout/print() output at all, only
    # actual cell output. position.py/game.py's own "X ver Y" prints stay
    # invisible under marimo run for the same reason — accepted tradeoff,
    # not worth touching those shared modules just for this.
    _commit = os.environ.get("RUN_COMMIT", "unknown")
    _subject = os.environ.get("RUN_COMMIT_SUBJECT", "unknown")
    _reltime = os.environ.get("RUN_COMMIT_RELTIME", "unknown")
    mo.md(f"*commit `{_commit}` — {_subject} ({_reltime})*")
    return game, mo, os, position


@app.cell
def _():
    # The current game lives in a file under ./data (gitignored, bind-mounted,
    # survives container restarts) instead of a hardcoded string here —
    # switching games via the box below, or hand-editing the file directly in
    # a real text editor, no longer dirties git. See DECISIONS.md. DEFAULT_PGN
    # is only ever used to seed the file the very first time it doesn't exist
    # yet (e.g. a fresh clone) — it must stay a real, parseable game, since an
    # empty/blank fallback would crash game.sweep_game() on a fresh setup.
    CURRENT_GAME_PATH = "/data/current_game.pgn"
    DEFAULT_PGN = """
    1. e4 e5 2. Nc3 Nf6 3. Nf3 Bb4 4. a3 Bxc3 5. bxc3 d5 6. exd5 Nxd5 7. Nxe5 Qe7 8.
    Qe2 O-O *
    """
    return CURRENT_GAME_PATH, DEFAULT_PGN


@app.cell
def _(CURRENT_GAME_PATH, DEFAULT_PGN, mo, os):
    def _read_disk_pgn():
        if os.path.exists(CURRENT_GAME_PATH):
            with open(CURRENT_GAME_PATH) as _f:
                return _f.read()
        with open(CURRENT_GAME_PATH, "w") as _f:
            _f.write(DEFAULT_PGN)
        return DEFAULT_PGN

    # mo.state(), not a plain variable — both buttons below need to update
    # the same value from their own on_click callbacks, and have that
    # update reliably seen by every other cell (including after a
    # hand-edit-and-reload, not just after typing in the box).
    get_pgn_text, set_pgn_text = mo.state(_read_disk_pgn(), allow_self_loops=True)
    return get_pgn_text, set_pgn_text


@app.cell
def _(mo):
    # Confirmation text shown after Load/Reload — clicking either button
    # otherwise gives no visible feedback at all; you'd have to notice the
    # board/move caption further down the page changed.
    get_load_status, set_load_status = mo.state("", allow_self_loops=True)
    return get_load_status, set_load_status


@app.cell
def _(CURRENT_GAME_PATH, get_load_status, get_pgn_text, mo, set_load_status, set_pgn_text):
    pgn_editor = mo.ui.text_area(
        value=get_pgn_text(), label="Current game (PGN)", full_width=True
    )

    def _load(_):
        text = pgn_editor.value
        with open(CURRENT_GAME_PATH, "w") as f:
            f.write(text)
        set_pgn_text(lambda v: text)
        set_load_status(lambda v: "✓ Game loaded and saved.")

    def _reload_from_disk(_):
        with open(CURRENT_GAME_PATH) as f:
            text = f.read()
        set_pgn_text(lambda v: text)
        set_load_status(lambda v: "✓ Reloaded from disk.")

    load_button = mo.ui.button(label="Load game", on_click=_load)
    reload_button = mo.ui.button(label="↻ Reload from disk", on_click=_reload_from_disk)

    status = get_load_status()

    mo.vstack([
        mo.md("### Current game"),
        pgn_editor,
        mo.hstack([load_button, reload_button], justify="start"),
        mo.md(f"*{status}*") if status else mo.md(""),
    ])
    return


@app.cell
def _(get_pgn_text):
    pgn_text = get_pgn_text()
    return (pgn_text,)


@app.cell
def _(game, mo, pgn_text):
    # sweep_game() calls Stockfish once per ply — a long game (dozens of
    # moves) can take a noticeable few seconds, with nothing else on the
    # page to indicate anything's happening in the meantime.
    with mo.status.spinner(
        title="Analyzing game…",
        subtitle="Running Stockfish on every ply — longer games take longer",
    ):
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
def _(mo):
    # Board orientation (True = viewing from Black's side), toggled by the
    # flip-board button next to the ply-stepper. Kept separate from
    # get_ply/set_ply above so flipping the board doesn't touch or reset
    # your place in the game.
    get_flipped, set_flipped = mo.state(False, allow_self_loops=True)
    return get_flipped, set_flipped


@app.cell
def _(get_flipped, get_ply, mo, records, set_flipped, set_ply):
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
    ply = get_ply()
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
def _(board, candidates, mo, position):
    # Thumbnails for every candidate, hover-enlarged with CSS. Pure display —
    # hovering never changes the selected candidate below.
    candidate_previews = mo.Html(
        position.render_candidate_previews_html(board.board, candidates, board.user)
    )
    return (candidate_previews,)


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
def _(analyze_button, candidate_previews, candidate_radio, detail_html, mo, move_text, result):
    # Side by side, per explicit request: candidate picker on the left,
    # try-your-own-move on the right — so the result renders right next
    # to the button that produced it, not scrolled away below.
    mo.hstack(
        [
            mo.vstack([candidate_previews, candidate_radio, detail_html]),
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
