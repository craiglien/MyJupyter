# DECISIONS.md

## "Don't" list implemented in position.py/game_marimo.py; confirmed working in the browser
Status: DECIDED

Built the design from `TASKS.md`: `position.py` gained `gap_quality()` (surfaces the
Best/Good/Inaccuracy/Blunder label `_gap_tier()` computed but `describe_gap()` discarded),
a `root_moves=` param on `_analyze()` (UCI searchmoves — the cache key includes the move
list so it can't collide with a full-board result for the same position), an optional
`best_score=` override on `rank_candidates()`, and three new functions:
`_tempting_but_unranked_moves()` (captures/checks not already in the top-5 PV — "moves
toward the center" stayed out of scope, see `TASKS.md` backlog), `rank_dont_list()`
(scores that pool via `root_moves`, filters to Inaccuracy/Blunder, worst-first, capped at
3), and `render_dont_html()` (reuses `_describe_continuation()` for the punishing
sequence — the same function `render_candidate_html()` already uses for the selected good
candidate). `position.py` bumped `0.4.1` → `0.5.0` (new backwards-compatible functions/
params). `game_marimo.py` got one new cell: a "Tempting, but don't" area above the
candidate radio list, empty (via `mo.stop()`) when there's nothing to warn about.

Verified offline first (a monkeypatched smoke test against the pure selection/filtering/
rendering logic, no engine involved), then live against the real engine by stepping
through the game currently loaded in `game_marimo.py`, ply by ply, via Playwright/CDP
(the Claude-in-Chrome extension still isn't connecting this session; same go-chrome-remote
CDP workaround as the earlier game-over-crash verification). Confirmed: empty output on
quiet positions with nothing tempting-and-bad; correct population on positions with real
traps, e.g. 3.Nf3 candidates flag ...Nxe4?? as a Blunder (gap −2.71 pawns) with the
continuation "Engine expects White's reply ... "; later in the same game, 5...Nxe4 at a
different position graded only Inaccuracy (gap far smaller), confirming the tier boundary
actually discriminates rather than dumping everything into one bucket; a knight fork
attempt (Nxf7) was correctly flagged as a Blunder with its refutation (...Qxf7) rendered.
No errors in the notebook's own error counter across the full step-through. One process
note: each ply's don't-list needs a second, separate Stockfish call (`open_engine()` is
per-call, not held open) on top of the good-candidates call, so it's slower to settle
than the existing candidate picker — a fast poll loop while scripting the verification
caught this as apparent "false negatives" before the second call had finished; not a bug,
just something to allow for if scripting against the live notebook again.

## Reconcile the orphaned GUARDRAIL.loc.md into the four-file framework
Status: DECIDED

Supersedes/refines the "Project control-file framework: plain four-file bootstrap, not
CONTEXT.md/GUARDRAIL.loc.md" entry below: that decision's outcome stands — this project
still uses the plain four-file bootstrap, no `CONTEXT.md`, no Context-Code-Trace Loop —
but a stray, untracked `GUARDRAIL.loc.md` (a `gr`-tool-generated, globally-gitignored
`*.loc.md` policy artifact) was still sitting in the repo root. Confirmed the file
structure decision itself doesn't change; only worked through whether any of its
*content* was still worth keeping before deleting the file.

Adopted (folded into `CLAUDE.md`'s hard constraints): explicit-path-only `git add` (no
directory adds), no pipe-to-shell installs, and a README.md content requirement (see
`TASKS.md` backlog for the follow-up).

Declined:
- The STRICT/FREEFLOW mode contract, behavior contract, "Sync" keyword, and P0–P4
  violation taxonomy — this session's ambient assistant behavior (ask on ambiguity,
  confirm risky actions) already covers the same ground without a separate formal
  contract to maintain.
- The `LLM_TODO*.md`/`IMPLEMENTATION_PLAN*.md` scratch-file naming convention — replaced
  by a lighter existing convention instead: any `*.scratch.md` file is a raw, unstructured,
  never-committed pre-`IDEAS.md` landing space (already globally gitignored via
  `~/.config/git/gitignore_global`, so it needs no per-repo setup); content gets promoted
  into `IDEAS.md` by hand once it's actually worth tracking. Cross-project by nature, so
  not written into this project's own `CLAUDE.md`.
- The Document→Test→Fix→Verify production-error-prevention workflow and pytest/atomic-
  unit-testing rules — discarded entirely; its worked examples (Django migrations,
  Wagtail admin) don't match this project's stack, indicating generic template
  boilerplate rather than content actually curated for this repo.

`GUARDRAIL.loc.md` itself retired (untracked/gitignored, removed directly from the
filesystem, not via commit — see the file's own rules: it's an external policy artifact
managed by the `gr` tool, never meant to be committed to a consumer repo).

## marimo's floating run-all control can't be repositioned — noted, not fixed
Status: DECIDED

Raised after using `game_marimo.py` for real: marimo's "run all stale cells" button sits
fixed in the bottom-right corner of the screen, with no editor setting to move it
somewhere more prominent (e.g. near the top, closer to where JupyterLab's own run
controls live in its toolbar). Confirmed via marimo's own docs — no configuration option
exists for this; it's a fixed part of the app shell, not a per-notebook or per-user
preference.

No fix implemented (none available). Workaround: `Cmd/Ctrl+Shift+R` runs all stale cells
from anywhere, `Cmd/Ctrl+Enter` runs just the focused cell (via a play button at that
cell's own top-right, not the floating one), and `Cmd/Ctrl+K` opens a command palette.
Worth remembering this is a plausible common complaint for anyone arriving at marimo
from JupyterLab's more visible, top-anchored toolbar — the control layout genuinely
moved, not just the run button.

## Fix _analyze() crash on game-over positions; confirmed working in the browser
Status: DECIDED

Root cause: `_analyze()` (the multipv drill-down behind `moves()`/`rank_candidates()`)
always called Stockfish, and Stockfish's own no-legal-moves response (for a
checkmate/stalemate position) has no `"pv"` key — an assumption `_serialize_info()`
baked in. This is a different code path than the one already checked safe in the
"GameCursor end-to-end verification" decision above: that entry covered `sweep_game()`'s
cheap per-ply eval (multipv=1), which Stockfish's fallback happens to handle fine.
`_analyze()`'s multipv=5+ drill-down hit the same no-legal-moves case but didn't survive
it — `KeyError: 'pv'`. Jupyter's `GameCursor` never triggered this (it only ever explains
positions *before* a move, which always has a legal move to make); `game_marimo.py`'s
board cell uses the position *after* a move (`fen_after`), which for a game's last ply
can be checkmate — found by clicking Next through Fool's Mate (`1. f3 e5 2. g4 Qh4#`) to
the final move.

Fixed at the root: `_analyze()` now returns `[]` immediately if
`root_board.is_game_over()`, without calling the engine at all. `game_marimo.py`'s
analysis cell calls `mo.stop(not info, mo.md("*Game over — no candidate moves at this
position.*"))` before building the candidate picker, so navigating to a game-ending ply
shows that message instead of the picker/detail cells crashing downstream. Verified both
via `docker exec` against the real engine and the real Fool's Mate PGN, and via a real
marimo kernel export (`marimo export html` with the initial ply forced to the last one,
confirming the `mo.stop` message renders and the two downstream cells show "wasn't run
because an ancestor was stopped"). Confirmed a second time by the user directly in the
browser, after restarting the marimo kernel (needed since the long-running kernel process
had the old `position.py` cached in memory).

Correcting an assumption from earlier in this same session: `game_marimo.py` does *not*
get live-reloaded either. `entrypoint.sh` launches `marimo edit --headless` without
`--watch`, so an external edit to the notebook file itself sits inert in the running
kernel until a restart — same as any imported module. Confirmed directly this round: a
fix landed on disk (see below) and the browser kept showing the pre-fix error until the
container was restarted; a plain browser reload alone did nothing.

Also polished the step-through UI while in there: a "### Step through the game" heading
above the Next/Prev buttons (previously unlabeled, reported as feeling "in the middle of
nowhere" with no context); a live "Move X of N" indicator in the board cell (reads
`get_ply()` each render — kept there rather than the button cell, mainly for separation
of concerns, not necessity); and First/Last buttons alongside Prev/Next
(`set_ply(lambda v: 0)` / `set_ply(lambda v: len(records) - 1)`), so jumping straight to
the start or end of a longer game doesn't mean clicking Next/Prev through every ply in
between, each greyed out via `disabled=` once the game is already at that end.

Getting the greyed-out state right needed `mo.state(0, allow_self_loops=True)`: by
default, marimo excludes the cell that calls a state setter from the rerun that setter
triggers, even if that same cell also reads the getter — the button cell calls
`set_ply()` from its own `on_click` handlers, so without `allow_self_loops=True` its
`disabled=` values would freeze at whatever they were on the very first render. With it,
clicking any button re-runs the button cell too, recomputing `disabled=ply == 0` /
`disabled=ply == len(records) - 1` against the new ply before redrawing.

Shipping that greyed-out logic broke the notebook outright — a real bug, caught live in
the browser via Playwright driving the actual running container (Chrome's own extension
wasn't reachable this session; connected over CDP to a separate remote-debugging Chrome
instance instead, `playwright.chromium.connect_over_cdp`). The button cell's `ply =
get_ply()` collided with the board cell's own `ply = get_ply()` — marimo's static
analysis treats the same top-level name assigned in two cells as a namespace conflict and
refuses to run either ("CELL NOT RUN", "This cell redefines variables from other cells"),
which cascaded into `NameError: name 'board' is not defined` downstream. The exact same
class of collision already recorded above (the candidate-table cell's `idx`/`rank`
rename) — renamed the button cell's copy to `button_ply` to fix it. Confirmed after a
container restart: First greys out at ply 0, ungreys after Next/Last; Last greys out at
the final ply, ungreys after Prev/First; the candidate radio picker still updates the
board detail on click.

`position.py` bumped `0.4.0` → `0.4.1` (PATCH — bug fix only, no signature/behavior
change for any existing caller besides no longer crashing on a game-over position).

## Add Next/Prev buttons to game_marimo.py, ahead of schedule
Status: DECIDED

Discovered through actual use, not planned: `ply_index` was a fixed variable (always
`0`), so `game_marimo.py` only ever showed the position after White's first move and
Black's candidate replies there — it never advanced to show the rest of a game. This
had been deliberately deferred as a backlog item ("button-based ply stepping"), but the
user hit the gap immediately while testing, so pulled it forward rather than leaving
them with only the "manually edit `ply_index` and re-run" workaround.

Implemented with `mo.state()` + two `mo.ui.button`s, the exact getter/setter/button
pattern marimo's own documentation uses for counters — `get_ply, set_ply = mo.state(0)`
in one cell; a second cell's Next/Prev buttons call `set_ply(lambda v: ...)` clamped to
`[0, len(records) - 1]`; the board-rendering cell reads `get_ply()` and re-runs whenever
`set_ply` fires elsewhere, per marimo's documented reactive-state semantics. Considered
`mo.ui.slider` instead (simpler, no state cycle, and marimo's own docs suggest
preferring plain reactive widgets over `mo.state()` where possible) but the user asked
for buttons specifically, matching `GameCursor`'s `.next()`/`.prev()` mental model
they're already used to from Jupyter.

Verified the clamping logic against the real engine (Fool's Mate, 4 plies): simulated 5
Next clicks correctly advances ply 0→1→2→3 then clamps at 3 (the final `Qh4#`); 5 Prev
clicks correctly returns to 0 and clamps there. Notebook re-validated as
`status: valid` (no static errors) after the change.

## Swap game_marimo.py's candidate picker from mo.ui.table to mo.ui.radio
Status: DECIDED

Reported after actually clicking around in the browser: `mo.ui.table(selection="single")`
rendered as checkboxes, not radio buttons, and clicking one appeared to do nothing —
the row stayed effectively unselected. Root cause not fully chased down (no browser
automation available this session to inspect the live DOM/network traffic directly),
but traced the visible "not selected" text to react-aria's own `deselectedItem`
accessibility announcement string (`"${item} not selected."`), bundled in marimo's
frontend — i.e. some part of the table's selection-column interaction wasn't behaving
as a normal committed selection.

Rather than debug marimo's table-selection internals further, switched to `mo.ui.radio`
— it's what was actually asked for ("radio boxes"), and its `.value` binding is a much
simpler value round-trip (selected label's mapped value) than a table's list-of-selected-
row-dicts. `game_marimo.py`'s candidate-table cell now builds
`options = {"1. e5 — +0.76 (...)": 1, ...}` (label to rank) and
`mo.ui.radio(options=options, value=next(iter(options)))`; the detail cell reads
`candidate_radio.value` directly as the rank index — no more unpacking a selected-rows
list.

Verified against the real engine in the running container: simulated a frontend
selection change via the widget's own `_update()` method (the same path a real
websocket message from the browser drives), confirmed `.value` updates correctly and
`render_candidate_html()` renders the newly-selected candidate. Real click-in-browser
confirmation is still the user's to do — see `TASKS.md`.

## Add a marimo candidate-picker notebook for game.py, scoped to Game side only
Status: DECIDED

After trimming the move-options display to the top candidate by default, the remaining
complaint was that looking at a *different* candidate still required manually calling
`explain_reply(board, info, candidate=N)` — an interaction-model gap, not a display one.
Confirmed with the user this was specifically about not being able to click through
candidates, not about game-position stepping (rebuilding `GameCursor` as buttons was
explicitly declined for this pass) and not about converting `Position.ipynb` too
(explicitly deferred). Marimo's reactive `mo.ui.table` (with `selection="single"`) is
the natural fix: a clickable table where selecting a row reactively re-renders that
candidate's detail, no re-running cells or typing indices.

Scope decided: a new `notebooks/game_marimo.py`, not a full Jupyter replacement. Marimo
runs *alongside* Jupyter in the same container on a second port
(`MARIMO_PORT = HOST_PORT + 1`, i.e. 12346 by default — see `config.sh`), not replacing
it; `entrypoint.sh` now backgrounds both `jupyter notebook` and `marimo edit` under
`gosu`, with a `trap` forwarding `TERM`/`INT` to both PIDs so `docker stop`/Ctrl-C still
shuts the container down cleanly.

`notebooks/position.py`'s `_display_ranked_moves()` was split into two new public,
display-side-effect-free functions so both Jupyter and marimo can reuse the same
analysis/rendering logic without duplicating it: `rank_candidates(root_board, info)`
(the existing per-candidate fact-building, lifted out unchanged) and
`render_candidate_html(root_board, candidates, idx, user)` (the existing per-candidate
board-diagram-plus-text HTML building, lifted out unchanged — returns the HTML string
instead of calling `display()`, so Jupyter wraps it in `display(HTML(...))` and marimo
wraps the identical string in `mo.Html(...)`). `_display_ranked_moves()` itself calls
both internally; its own behavior for existing Jupyter callers (`Position.ipynb`,
`Game.ipynb`, `Game.debug.ipynb`) is unchanged — verified via the same real-engine
Fool's Mate check used earlier this session (`GameCursor.explain()` still renders 1
table + 1 detail block, unchanged). `position.py` bumped `0.3.0` → `0.4.0` (MINOR — new
public functions only).

`game_marimo.py` deliberately doesn't use `GameCursor` — it reads `records` (from
`game.sweep_game()`, already side-effect-free) directly via a plain `ply_index`
variable, since `GameCursor`'s `.next()`/`.prev()` machinery is built around Jupyter's
cell-by-cell re-run model and wasn't part of this pass's scope. It also doesn't port
`show_sweep()`'s eval chart or `show_critical_moments()`'s auto-flagged moments — both
are Jupyter/`display()`-only today; `game_marimo.py` only covers "look at one position's
ranked candidates," not the full `analyze_game()` experience.

Verified against the real engine (rebuilt image, `docker exec` — not just import checks):
`rank_candidates()`/`render_candidate_html()` return correct data/HTML for Fool's Mate's
opening position (5 ranked candidates, e.g. `e5 +0.76`/`d5 +0.51`/...), and simulating a
non-default row selection (rank 3) correctly renders that candidate's own detail via the
same code path the marimo notebook's detail cell uses. Also confirmed both `jupyter
notebook` and `marimo edit` start together in the rebuilt image without one blocking the
other, on a temporary alternate port pair so the user's already-running container (from
browser-testing the earlier display fix) wasn't disturbed.

One implementation snag worth recording: marimo's static analysis treats a name bound
inside a list-comprehension in one cell and reassigned in another cell as an ambiguous
multiple-definition ("this notebook has errors") even though Python's own comprehension
scoping wouldn't actually leak it — `game_marimo.py`'s candidate-table cell had to rename
its loop variable (`idx` → `rank`) to avoid colliding with the detail cell's `idx`.
Marimo also isn't version-pinned in the Dockerfile (matches the project's existing
convention for every other pip package except `httpx<0.24`); the image built with
marimo `0.23.16`, not the `0.19.6` used to draft this design — re-verify `mo.ui.table`'s
API and `marimo edit`'s CLI flags if either changes behavior on a future rebuild.

## Build Stockfish from source instead of shipping a pre-built binary
Status: DECIDED

The repo previously shipped `stockfish-ubuntu-x86-64`, a pre-built Linux x86-64 ELF binary,
copied directly into the Docker image. On arm64 hosts (e.g. Apple Silicon) this fails with
"exec format error" once the container is built natively for arm64, since the Dockerfile
had no platform pin.

Fix: vendor the Stockfish source tree (`stockfish/src`) and compile it in a
`stockfish-build` Docker stage, selecting `ARCH=x86-64` or `ARCH=armv8` from `uname -m`
inside that stage (the vendored tree is missing `scripts/get_native_properties.sh`, so
`ARCH=native` can't self-detect — this is a deliberate, conservative baseline choice, not
the most-optimized build). This guarantees `/usr/bin/stockfish` always matches the
container's actual build architecture, regardless of host.

## Extract the compiled Stockfish binary as a host artifact
Status: DECIDED

`build.sh` additionally builds the `stockfish-build` target alone and `docker cp`s the
resulting binary out to `./stockfish-bin` on the host. Useful for inspection/reuse outside
the container. This file is arch-specific to whatever host built it, so it's gitignored,
never committed.

## Vendor `stockfish/src` directly in the repo (not a submodule, not fetched at build time)
Status: DECIDED

Chosen over a git submodule or an in-Dockerfile `git clone`/`wget` because it's small
(~1.2MB source-only), and avoids a network dependency during `docker build`. Tradeoff:
the vendored snapshot isn't obviously pinned to a tagged release — see `TASKS.md`.

## Root-caused the "why does it think it's Black's move?" bug: `position.pgn()` always returns the end-of-PGN position
Status: DECIDED

Confirmed via code reading (`notebooks/position.py`'s old `pgn()`) plus a direct repro
against the exact 2026-08-09 Daily Puzzle PGN logged in `TASKS.md`: `position.pgn()`
unconditionally plays every move in the mainline and returns the resulting *final*
position — never the `[FEN]` header's starting position. For that puzzle, the mainline
ends with `4. a8=Q`, after which it's genuinely Black to move; anyone using
`position.pgn(pgn_text, 'w')` expecting "the puzzle's starting position" (matching the
FEN header's `w` to move) instead silently got the game's end state. Not a
move-attribution bug — `sweep_game()`/`analyze_game()` were already confirmed correct on
this exact PGN.

Fix: added an optional `plies` parameter to `pgn()` (default `None` preserves the
existing "play everything" behavior). `pgn(pgn_text, user, plies=0)` returns the starting
position instead, respecting the FEN header. Verified against the reported puzzle PGN:
default behavior still lands on Black to move; `plies=0` correctly returns White to move,
FEN-for-FEN matching the header. `position.py` bumped to `0.2.0` (new backwards-compatible
parameter, no behavior change for existing callers).

## GameCursor design: cheap navigation, engine calls only on demand
Status: DECIDED

Built `GameCursor` in `game.py` as a thin stateful wrapper over `sweep_game()`'s
`records` list, reusing `at_move()`'s existing position-lookup logic (extracted into
shared `_mover_from_side()`/`_find_move()` helpers so `at_move()` and
`GameCursor.goto()` can't drift apart) rather than inventing a parallel lookup path.

Key design choice: `.next()`/`.prev()`/`.goto()` only move the cursor's index and
re-render the board (`position.make()` + `position.show()`, both cheap/no engine call);
only `.explain()` hits Stockfish, via the same `_explore_record()` path `at_move()`/
`show_critical_moments()` already use. This keeps casual stepping through a game fast
and free, and makes the one expensive operation explicit and opt-in per move, rather
than re-analyzing on every `.next()`.

Verified `.next()`/`.prev()`/`.goto()` (including out-of-range/nonexistent-move error
handling) against synthetic records built from a real opening PGN, without needing
Stockfish. `.explain()` reuses `_explore_record()` unchanged, so it inherits that
function's existing behavior rather than needing separate verification — but running it
end to end against a real game (the motivating "missed an escape square" example) still
needs a real engine pass; see `TASKS.md`.

`game.py` bumped to `0.3.0` (new `GameCursor` class + `_mover_from_side()`/`_find_move()`
helpers, `at_move()`'s public signature/behavior unchanged).

## GameCursor end-to-end verification: Fool's Mate, not the original remembered game
Status: DECIDED

The original motivating example (a remembered game where a queen-trapping idea missed an
escape square) couldn't be found in game history. Substituted the shortest possible real
game — Fool's Mate (`1. f3 e5 2. g4 Qh4#`) — as the end-to-end test case instead, since
what actually needed verifying was the plumbing (`GameCursor` + a real Stockfish call),
not that specific tactical moment.

Ran it directly against the real engine (via the existing `jupyter-notebook` Docker
image, calling `position.py`/`game.py` outside the notebook UI to isolate engine
behavior) rather than assuming it would work. This incidentally exercised a genuine edge
case `sweep_game()` had never hit before: evaluating the position after a
checkmate-ending move, which has zero legal moves for the engine to search. It worked
without error — Stockfish's own no-legal-moves fallback (reports a mate/draw score
immediately rather than erroring) covers it, so no code change was needed.
`GameCursor.next()` and `.explain()` both produced correct results against the real
engine. Visual/browser confirmation of the notebook UI itself is still worth doing, but
the previously-open question (does this work against a real engine at all?) is answered.

## Trim move-options display to the top candidate by default, not all 5
Status: DECIDED

Reported as "hard to read" after visually testing `GameCursor` in the browser. Root
cause was a display problem in `position.py`'s `_display_ranked_moves()`, not a
Jupyter-vs-marimo one — it always rendered a full board-diagram-plus-text detail block
for every one of `multipv` (default 5) candidates, on top of the summary table. Calling
`GameCursor.explain()` repeatedly while stepping through a game stacked these up fast.

Fix: added a `full_detail` parameter (default `1`) to `moves()`/`explain_reply()`/
`_display_ranked_moves()` that caps how many top-ranked candidates get a full detail
block; the summary table still lists every candidate. Other candidates remain reachable
via the existing `explain_reply()`/`explain_line()` drill-down, unchanged. Verified
against the real engine (Fool's Mate via `GameCursor.explain()`): summary table still
shows all 5 candidates, only 1 detail block renders instead of 5.

`position.py` bumped to `0.3.0` (new backwards-compatible parameter; existing callers
still work, but default rendered output is intentionally less verbose than before).

## Project control-file framework: plain four-file bootstrap, not CONTEXT.md/GUARDRAIL.loc.md
Status: DECIDED

A stray `CLAUDE.md` pointer file (referencing `CONTEXT.md`, `GUARDRAIL.loc.md`,
`DESIGN.loc.md`, a `/boot` skill, and an MCQ-driven discipline) briefly appeared in the
repo root. Confirmed with the user it wasn't intentional for this project; they deleted
it. This project uses the plain four-file bootstrap from `~/.claude/CLAUDE.md`
(`CLAUDE.md`/`TASKS.md`/`DECISIONS.md`/`IDEAS.md`) instead.

## Deepen reply-move explanations with Idea 1 + Idea 2; defer Idea 3
Status: DECIDED

`moves()`'s "Engine expects the reply X" line was too shallow — no explanation of what
that reply does or why the engine expects it over the opponent's other options. Three
options were considered (see `IDEAS.md`), ordered by cost:

1. Classify the reply (and the move after it) using the existing `classify_move()`
   machinery, reusing data already in the principal variation — free, no extra engine
   calls, but only describes move type (capture/check/quiet), not comparative reasoning.
2. A new opt-in function that recurses the `moves()` ranking-table-plus-narrative
   approach one ply deeper — a fresh multipv call on the position after a chosen
   candidate move, ranking the opponent's replies against each other the same way we
   rank our own candidates. This is the real "why," at the cost of an extra engine call
   per invocation.
3. Chain idea 2 again for our follow-up move after their reply — a small explained
   game-tree. Cost compounds per hop (another multipv call each time).

Decision: build 1 (as a default upgrade to `moves()`) and 2 (as a new on-demand
function, not automatic for all 5 candidates, to keep engine time bounded). Idea 3 stays
in `IDEAS.md` as a future on-demand extension, not built now.

## Switch cc.py's __ver__ to semantic versioning, reset baseline to 0.0.0
Status: DECIDED

`__ver__` had been an informal float (`0.9`, then `1.0`) bumped on "notable changes" —
no real rule for what counted as notable, so the number carried no information about
whether a change was safe to pull into an existing notebook session. Switched `__ver__`
to a semver string and reset it to `0.0.0` as the new baseline: MAJOR for breaking
changes to a function's signature/behavior, MINOR for new backwards-compatible
functions/features, PATCH for bug fixes only. See `CLAUDE.md`.

## Strip notebook outputs on commit via nbstripout, instead of gitignoring Chess.ipynb
Status: DECIDED

`notebooks/Chess.ipynb` kept showing modified after every run, even with no real edits,
because Jupyter stores cell outputs (execution counts, printed text, rendered SVG boards)
inline in the `.ipynb` JSON. A `git diff` mixed real source edits together with pure
output noise, making the diff unreadable and the file effectively uncommittable without
manually separating the two.

Considered gitignoring the file outright, but that would also throw away real source
edits (which FEN/position is being tested, which functions are called) — not just the
noise. Instead installed `nbstripout` (via `uv tool install nbstripout`, since it's a
git-hook CLI, not a project runtime dependency) and registered it as a git clean filter
via `nbstripout --install --attributes .gitattributes`, so outputs are stripped
automatically whenever a notebook is staged. `.gitattributes` (committed, shareable)
declares which files use the filter; each clone still needs to run
`nbstripout --install` once locally to register the actual filter command, since git
filters can't be fully defined in a committed file.

## Name the whole-game analysis module gac.py, not gc.py
Status: DECIDED

The planned module name `gc.py` turned out to be unusable: `gc` is a module compiled
directly into the Python interpreter (`sys.builtin_module_names`), so `import gc` always
resolves to Python's own garbage collector regardless of `sys.path` order — confirmed by
testing (a script doing `sys.path.insert(0, "/app"); import gc` still got the builtin, not
`notebooks/gc.py`). Renamed to `gac.py` before writing any more code against the old name.

## Draw pieces on top of move arrows in cc.py's board rendering
Status: DECIDED

`_display_ranked_moves()`'s candidate boards draw an arrow from the move's origin to
destination square, but `chess.svg.board()` emits the arrow's SVG elements after (so
visually on top of) the piece elements. For a short move — mainly knight hops, since a
knight's destination is close to its origin relative to its visual footprint — the
arrowhead polygon lands almost entirely on top of the piece that just moved there, making
it look like it was never drawn. Found while testing `gac.py`'s critical-moment
drill-down against `1. e4 d5 2. Nc3 Nf6 3. Bd3`, where the engine's suggested alternative
at White's 3rd move was itself a knight move; the bug is in shared rendering code, not
specific to `gac.py`, and affects `cc.moves()` in `Chess.ipynb` equally, just less
noticeably since knight-move candidates come up less consistently there.

`chess.svg.board()` has no built-in option to reorder or shrink the arrow. Fixed with a
small post-processing helper, `_pieces_over_arrows()`, that moves the arrow `<line>`/
`<polygon>` elements (found via a regex on `class="arrow"`) to just before the first
piece `<use>` element in the returned SVG string — pieces render on top, the arrow still
shows as a trail leading into the square. Bumped `cc.py` to `0.0.1` (PATCH, bug fix only).

## Clean up cc.py before debugging the game-analysis notebook
Status: DECIDED

Audited `cc.py` for bugs before relying on it further from `gac.py`/`Game.ipynb`. Found
and fixed four issues, all PATCH-level (bug fixes / cleanup, no new features, no breaking
signature changes):

- `moves(board, show=True)`'s `show` parameter did nothing — `_display_ranked_moves()`
  always displayed regardless. Wired it through (`show=False` now genuinely suppresses
  the table/board/print output while still returning the raw `info`) rather than removing
  the parameter, to keep the signature backwards-compatible.
- Calling `_display_ranked_moves()` (via `moves()` or `explain_reply()`) on a position
  with no legal moves crashed with `KeyError` — confirmed empirically that
  `engine.analyse()` on a checkmate/stalemate position returns a result dict with no
  `'pv'` key at all. Added an `is_game_over()` guard that prints "Checkmate — no moves to
  analyze." (or Stalemate/Game over) and returns `info` instead of crashing. Not currently
  reachable through `gac.py`'s own call paths (critical-moment drill-down only ever
  analyzes the position *before* a flagged move), but a real landmine for direct callers.
- `get_color()` silently returned the string `'invalid'` for unrecognized input instead of
  raising — a typo'd color argument would quietly produce wrong board orientation later
  instead of failing where the mistake was made. Now raises `ValueError`.
- `pgn()` was full of leftover debug prints (`print(dir(gm))`, printing the board after
  every pushed move, `print(dir(bd))`) — removed; behavior unchanged.

Bumped `cc.py` to `0.0.2`. Verified via a script exercising all four fixes plus a
`gac.py` regression run (checked `gac.py` still imports and runs cleanly against the
updated `cc.py`).

## Label critical-moment boards as alternatives, not a replay of the game
Status: DECIDED

Reported as a bug: testing `gac.py` against `1. e4 d5 2. Nc3 Nf6 3. Bd3`, a critical-moment
board showed "1. exd5 (e4d5) — +0.70" — read as the notebook getting the game wrong (e4 and
d5 were both actually played as separate, non-capturing pawn moves). Traced it: this is not
a computation bug. `show_critical_moments()`'s board is the engine's own top candidate at
the position *before* the flagged move — genuinely `exd5` there — not a rendering of what
was actually played. Confirmed by walking the exact PGN through `sweep_game()` and
`cc.moves()` directly: every candidate returned was a legal, correctly-ranked move at that
position.

The real problem is presentation: nothing distinguished "what you played" from "what the
engine suggests instead," so a correct alternative reads as a wrong replay. Fixed by
rewriting `show_critical_moments()`'s print output to state the actually-played move
explicitly and label the candidate list "NOT a replay of your game" before showing it,
rather than changing the underlying analysis.

## Let critical moments be explored further, instead of a dead end
Status: DECIDED

Once `show_critical_moments()` showed the engine's suggested alternative at a critical
moment, that was it — there was no way to keep going down that alternate line. `cc.py`
already has exactly the tool for this (`explain_reply(board, info, candidate)`, which goes
one ply deeper along a candidate), but `gac.py` discarded the `board`/`info` it used for
each critical moment instead of handing them back.

Changed `show_critical_moments()` to return a list of `{"record", "board", "info"}` dicts
— one per critical moment shown — so any of them can be passed straight into
`cc.explain_reply()` or `cc.explain_line()` to keep exploring. `analyze_game()`'s return
changed from `records` alone to `(records, critical)` to expose this. Verified by chaining
`cc.explain_reply(critical[0]["board"], critical[0]["info"], candidate=1)` after
`analyze_game()` and confirming it correctly analyzed one ply deeper. Updated
`Game.ipynb`'s third cell for the new return shape and added a commented-out example cell
showing the chained-exploration call. Bumped `gac.py` to `0.1.0` (MINOR — new capability;
not yet committed anywhere, so no prior callers to break).

## Add at_move() to jump to any move, not just auto-flagged critical moments
Status: DECIDED

The actual use case turned out narrower than "auto-detect the worst moments": a specific
real game, a specific remembered moment ("I thought I had the queen trapped a couple of
moves earlier"), wanting to ask the engine about that exact point — which may not be one
of `show_critical_moments()`'s top-N eval-swing picks at all. `sweep_game()` already
records `fen_before` for every ply, not just flagged ones, so the data was already there;
it just had no direct entry point.

Added `at_move(records, move_number, side, user="w")` — looks up the matching record by
move number + side, then runs the same explore-and-display logic `show_critical_moments()`
uses (factored out into a shared `_explore_record()` helper to avoid duplicating it),
returning `{"record", "board", "info"}` so exploration can continue via
`cc.explain_reply()`/`cc.explain_line()` exactly like a critical moment can. Verified
end-to-end including bad move number and bad side raising `ValueError`, and chaining into
`cc.explain_reply()`. Bumped `gac.py` to `0.2.0`.

Separately: discovered while re-editing `Game.ipynb` that a previous edit (the
`records, critical` unpacking + example cell from the prior decision) had been silently
reverted — the file's disk mtime showed it was overwritten *after* that edit, matching
Jupyter's autosave writing the live browser tab's stale in-memory copy back over it. The
open browser tab was never reloaded after that file edit, so it had no way to know about
it. This is a standing risk whenever a notebook is both open live in a browser and edited
directly on disk: the browser's autosave can clobber out-of-band file edits at any time,
silently. No fix implemented yet — flagging it in case it needs a workflow change (e.g.
always reload the tab immediately after a file-level edit, before any further interaction
in the browser).

## Rename cc.py/gac.py/Chess.ipynb to position.py/game.py/Position.ipynb
Status: DECIDED

After ~20 months of incremental growth, the module names no longer said what the two
layers actually do: `cc.py` (single-position/FEN analysis) and `gac.py` (whole-game/PGN
orchestration built on it) don't read as a layered architecture, they read as two
unrelated abbreviations. Ahead of using this tooling for real game analysis (a specific
game where a queen-trap opportunity was believed missed) and likely repeated future
analyses beyond that one, renamed for clarity: `cc.py` → `position.py`, `gac.py` →
`game.py`, `Chess.ipynb` → `Position.ipynb` (`Game.ipynb` already matched `gac.py`/
`game.py` and didn't need to change). Done via `git mv` to preserve history. All internal
references updated (`import cc`/`import gac` → `import position`/`import game`, and every
qualified call site in both modules and both notebooks). Treated as a structural rename,
not a functional change — no version bump for the rename itself; see the next entry for
the version bumps that came from the accompanying cleanup.

## Deduplicate cc.py/gac.py overlap now that gac.py is built on cc.py's stabilized API
Status: DECIDED

Auditing the two layers ahead of real game analysis turned up four places `gac.py`
duplicated logic that already existed in (or belonged in) `cc.py`, addressed as part of
the same pass as the rename above:

1. **PGN parsing.** `cc.pgn()` and `gac.sweep_game()` each independently did
   `chess.pgn.read_game(io.StringIO(pgn_text))`. Added `position.parse_pgn()` as the one
   place that happens; both callers use it now.
2. **Engine invocation.** `cc._analyze()` and `gac.sweep_game()` each called
   `chess.engine.SimpleEngine.popen_uci(stockfish_path)` directly (with different
   lifecycles — `_analyze()` opens/closes per call, `sweep_game()` holds one engine open
   for the whole sweep, both lifecycles kept as-is). Added `position.open_engine()` as
   the one place that starts the process, so there's a single spot to add engine options
   later if needed.
3. **Eval caching, and closing a caching gap.** Moved `_load_cache()`/`_save_cache()`/
   `_engine_version()`/`_evaluate_cached()` from `gac.py` into `position.py` as shared
   utilities (`gac.py`'s per-ply sweep eval — always multipv=1 — uses them exactly as
   before). Separately, `position._analyze()` (the multipv=5+ drill-down behind
   `moves()`/`explain_reply()`, and transitively `game.py`'s `at_move()`/
   `show_critical_moments()`) previously had **no caching at all** — re-running a
   notebook cell against a position just analyzed always re-ran the full `time_limit`
   search. Extended caching to `_analyze()` too, in the same cache file
   (`/data/engine_cache.json`, renamed from `/data/gc_cache.json` since it's no longer
   gac-specific — gitignored and disposable, no migration needed), with `multipv` baked
   into each entry's key so the cheap multipv=1 sweep pass and the expensive multipv=5+
   drill-down never collide; they still answer different questions, they just now share
   the caching mechanism. Caching a full multipv result required serializing/
   deserializing each PV (list of UCI moves) and relative score (cp or mate) —
   `_serialize_info()`/`_deserialize_info()` in `position.py`. A cache hit still opens
   the engine briefly (fast UCI handshake, needed to confirm the version key still
   matches) but skips the full timed search.
4. **Move-quality tier thresholds.** `cc.describe_gap()`'s 0.05/0.3/1.0-pawn cutoffs were
   hand-duplicated as `gac._classify_quality()`'s Best/Good/Inaccuracy/Blunder labels,
   kept in sync only by comment. Extracted both the numeric thresholds and the label into
   one shared table, `position.GAP_TIERS` (read via `position._gap_tier()`), so
   `describe_gap()`'s note text and `game._classify_quality()`'s label are always
   derived from the same source.

Versioned per this project's existing semver convention: `position.py` 0.0.2 → 0.1.0
(MINOR — new public functions `parse_pgn`, `open_engine`, `GAP_TIERS`, plus `_analyze()`
gaining caching, all additive with no existing signature/behavior changes). `game.py`
0.2.0 → 0.2.1 (PATCH — internals now call `position.py`'s shared helpers instead of local
duplicates; `sweep_game`/`show_sweep`/`critical_moments`/`at_move`/`analyze_game` keep
identical signatures and observable behavior).

Deferred to `TASKS.md`: a `GameCursor` navigator for stepping forward/backward through a
game's actual played moves (not built in this pass) — see `TASKS.md` "Up next" for the
design. Also noted in `IDEAS.md`: a future v2 direction pairs Stockfish with an LLM API
for narrative generation, so this cleanup deliberately kept engine-fact computation
(`classify_move`, raw `info`/PVs, eval numbers) separate from narrative-formatting
functions.
