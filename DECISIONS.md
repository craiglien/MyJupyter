# DECISIONS.md

## Don't-list pool includes quiet moves to the four central squares (position 0.12.0)
Status: DECIDED

Implemented 2026-10-05. The don't-list's candidate pool used to be captures and checks
only, so a quiet move that walks into a pawn capture (e.g. Qd4 met by ...cxd4) could never
be flagged. The pool now also includes quiet moves whose destination is d4, e4, d5, or e5
(the standard four central squares). Anything in the pool is still scored by the engine
and only shown if it grades Inaccuracy or worse, so the wider pool only surfaces central
moves that are actually bad.

Rejected: the 16-square center (c3-f6) would flag too many ordinary developing moves as
"tempting."

Accepted cost: the pool is larger, so the don't-list's engine pass takes a little longer.

Verification: in the image, against the real engine, a position where Qd4 loses the queen
to ...cxd4 now flags Qd4 as a Blunder; before this change it could not appear at all.

## Candidate-move explanations: deterministic templates over board facts, LLM-ready seam
Status: DECIDED

Implemented 2026-10-04 in `position.py` 0.10.0. Chose template-generated English over an
LLM for v1: it runs offline, needs no API key or container egress, produces the same text
every time, and every claim can be checked against the board. The LLM option stays open as
a later layer.

Design: `classify_move()` returns raw facts only (undefended pieces left after the move,
undefended enemy pieces the moved piece attacks, central-square and back-rank development
flags). `describe_move_reason()` turns them into sentences, and the generic "quiet move"
line is now only the fallback when there's nothing concrete to say. Keeping facts and
wording separate is what lets a future LLM step consume the same facts without touching
engine or board code (the seam described in `IDEAS.md`'s v2 entry).

Limitations accepted for v1: "undefended" is static (no exchange counting), so a piece
defended only by a more valuable piece still reads as defended. Output is capped at two
hanging and two attacked pieces per move to keep the panel readable.

Verification: offline checks in an isolated container (see `position.py` commit message for
the cases); candidate panel rendered in the real notebook with no tracebacks.

## Notebooks served via marimo run, not marimo edit (Phase 3 of the git-dirty-state fix)
Status: DECIDED

Implemented 2026-09-24, right after Phase 1. Decided to switch fully to `marimo run` rather
than keep `marimo edit` available as a fallback: all actual notebook authoring happens by
editing the `.py` file directly (Claude Code, or by hand), never through marimo's own
in-browser code editor, so edit mode's authoring capability wasn't actually being used.
`entrypoint.sh` now launches both notebooks with `marimo run ... --watch --include-code`
instead of `marimo edit`: `--watch` hot-reloads on a file change with no container restart
needed (this is what marimo edit's own reactivity was already implicitly relied on for
the operator's browser interactions; now it also covers Claude-Code-made source edits),
and `--include-code` keeps the source visible, matching the previous experience (`marimo
run` hides it by default otherwise).

Bonus, not the original goal: `marimo run` auto-executes the notebook on load — fixes the
"must manually click run-all" annoyance already noted in `IDEAS.md`, which was specific to
`marimo edit`'s fresh-kernel behavior.

Real regression discovered during verification: `marimo run` doesn't display stdout/
`print()` output at all, only actual cell output. This silently made the commit-metadata
line (and `position.py`/`game.py`/`game_collections.py`'s own "X ver Y" import-time
prints) invisible, undoing the "put the metadata right there" work from earlier the same
day. Fixed the commit-metadata line by switching it from `print()` to `mo.md()` in both
notebooks' imports cell, so it renders as real cell output again. Left the shared modules'
own version prints invisible under `marimo run` — an accepted tradeoff (an
import-succeeded confirmation, not something actively being checked) rather than touching
`position.py`/`game.py`/`game_collections.py` just for this.

Verified against a rebuilt image, in an isolated container: both notebooks show "Running
X.py ⚡" (not "Edit X.py 📝"); the full analysis pipeline renders with no manual run-all
click; `--watch` picked up a subsequent edit to the notebook files live, no restart
needed; Phase 1's Load/Reload-from-disk buttons still write and re-analyze correctly
under the new mode; and the commit-metadata line renders correctly in both notebooks
after the `print()` → `mo.md()` fix.

## game_marimo.py's pgn_text moved to a disk file (Phase 1 of the git-dirty-state fix)
Status: DECIDED

Implemented 2026-09-24. Design settled via MCQ discussion:
- Load trigger is an explicit "Load game" button (text area + button), not live-reactive
  on every keystroke — matches the existing "Try your own move" pattern already in this
  notebook, and avoids triggering a slow Stockfish sweep mid-paste.
- Hand-editing `data/current_game.pgn` directly (in a real text editor) is explicitly
  supported, via a separate "↻ Reload from disk" button — not just the in-notebook text
  box.
- The file stays single-game only, even though hand-editing raised the idea of letting it
  hold several games. A multi-game picker here would rebuild Game Collections' job inside
  `game_marimo.py`, directly against the "many small notebooks" decision above — rejected
  for that reason. If more games in one editable place is ever wanted, that belongs in a
  `data/collections/*.pgn` file instead.

Implementation: `mo.state()` holds the current PGN text, seeded on first run by reading
`data/current_game.pgn` (falling back to a small `DEFAULT_PGN` and writing it out if the
file doesn't exist yet — e.g. a fresh clone). "Load game" writes the text box's content to
the file and updates the state; "Reload from disk" re-reads the file into the same state,
picking up external edits. Both paths converge on the one `mo.state`, so every other cell
(the board, candidates, "What's risky") reacts the same way regardless of which button was
used.

Verified against a real container: initial load pre-fills the text box from the seeded
file; editing + "Load game" writes the file and re-runs analysis correctly; hand-editing
the file directly + "Reload from disk" updates both the text box and analysis to match.
Milestone check: after switching games through the new UI, `git status` reports "nothing
to commit, working tree clean" — `game_marimo.py` itself is never touched by normal use
anymore.

Follow-up fix (2026-09-25): two problems surfaced from actual use. First, `DEFAULT_PGN` had
been hand-edited down to an empty string at some point, which would crash
`game.sweep_game()` on any fresh setup missing `data/current_game.pgn` — restored to a real
fallback game. Second, clicking "Load game" or "Reload from disk" gave no visible feedback
at all (only an indirect clue: the board/move caption further down the page happening to
change) — added a small confirmation message after each. Verified in an isolated container:
both buttons now show their confirmation text, and deleting `data/current_game.pgn` plus a
genuine fresh boot (container restart with the marimo session cache cleared too — a plain
restart alone isn't enough, since marimo persists session state across it) confirms
`DEFAULT_PGN` correctly re-seeds the file instead of crashing.

## Notebook architecture: many small single-purpose notebooks, not one merged one
Status: DECIDED

Settled 2026-09-23, prompted by an open question left in `TASKS.md`'s Phase 2 (Game
Collections shipped as its own notebook, `collections_marimo.py`, rather than as a change
to `game_marimo.py` — was that split intentional, or should they merge?). Decided
explicitly: Unix philosophy, small is beautiful — many small single-purpose notebooks
instead of one large multi-purpose one.

Concretely: `game_marimo.py` stays "paste one ad-hoc PGN and study it"; `collections_marimo.py`
stays "browse curated named collections of games." Neither absorbs the other's mechanism.
This resolves Phase 1's scope too — its "move `pgn_text` to a data file + text box" work
belongs in `game_marimo.py` on its own terms, not superseded by Game Collections' existence.

This is meant as a standing principle for future notebooks too (Opening-prep, Tutorial, per
`TASKS.md`'s Backlog), not just this one case — default to a new sibling notebook for a new
distinct purpose, rather than growing an existing notebook to cover it, even when there's
mechanism to share (share the underlying module — `position.py`/`game.py`/
`game_collections.py` — not the notebook UI).

## README.md removed for now; add back before ever going public
Status: DECIDED

Removed 2026-09-23 (by the operator directly) — it was a 16-byte stub nobody was reading,
for a private, single-user hobby repo with no external audience. A stub wasn't earning its
place, and the "flesh it out" backlog item (`TASKS.md`) was just sitting there indefinitely
with no real urgency behind it.

The one condition that changes this: if this repo is ever published publicly (e.g., pushed
to GitHub as a public repo), a real `README.md` must be added back FIRST — what the project
is, how it's structured, how to build/run/test it, copy-pasteable commands a stranger could
actually follow. Recorded as a hard constraint in `CLAUDE.md` so it isn't forgotten at
exactly the moment it'd matter most.

## Startup provenance banner: source commit vs. image build vs. container start
Status: DECIDED

Requested (2026-09-23) after a `bash build.sh && bash run.sh` cycle, prompted by wanting a
way to visually confirm — every time the container starts — that what's running actually
matches the source being discussed, given this repo is expected to be used for 10-15
years: "we know we're running the most recent build and everything's consistent." Three
points in time can silently drift apart in this bind-mounted-source setup: when the source
was last committed, when the image was actually built from it, and when a given container
started (which could be hours/days after either of the above, if the container's been left
running).

Implementation, split across the three scripts that already exist for this purpose:
- `build.sh` computes the current commit (short hash + subject) and a build epoch timestamp
  on the host, and passes them as `--build-arg`s.
- The `Dockerfile`'s final stage bakes those into `/build_info.txt` inside the image — a
  plain file, since build ARGs themselves don't survive into a running container.
- `run.sh` computes the commit fresh again (short hash + subject + `git`'s own `%cr`
  relative-date string, e.g. "12 minutes ago") at the moment you actually run the
  container, and passes those as env vars — deliberately re-computed here rather than
  reused from build time, since source can change between a build and a later run.
- `entrypoint.sh` prints a banner, first thing, comparing the run-time commit (env vars)
  against the build-time commit (`/build_info.txt`): a ✓ line if they match, or a ⚠ with
  an explicit "run `bash build.sh`" nudge if they don't.

Portability: only `git log --format=%cr` supplies human-relative time on the host side
(`build.sh`/`run.sh`), since those run on whatever OS the developer is using (BSD date on
macOS, GNU date on Linux) — no `date -d` math there. `entrypoint.sh` always runs inside the
Ubuntu container, so its own age computation (`$(date +%s)` minus the baked-in epoch) has
no portability concern.

Verified against a rebuilt image, in isolated foreground containers (separate from the live
session): confirmed the ✓ path with the real current commit on both sides, and separately
forced a ⚠ mismatch by passing a fake `RUN_COMMIT` env var, confirming the warning path
and its wording both fire correctly. Caught and fixed a real bug during this verification —
`IFS=$'\n' read -r A B C < file` does not split a 3-line file into three variables (`read`
only ever consumes one line); replaced with `mapfile -t`.

## Game Collections implemented; landing page now active (2 notebooks)
Status: DECIDED

Built per the design already scoped in `TASKS.md`'s Backlog (2026-08-26): user-curated
named lists of games to page through. Two new files:

- `notebooks/game_collections.py` — `list_collections()` (names of `*.pgn` files under
  `/data/collections`) and `list_games(name)` (every game in one file, via repeated
  `chess.pgn.read_game()` calls on the same stream — no custom PGN-parsing logic). Each
  game is re-exported through `chess.pgn.StringExporter` into a standalone `pgn_text`
  string (headers + mainline moves), the same shape `game.sweep_game()` already expects
  everywhere else — not a raw slice of the original file, so downstream code needed zero
  changes. Named `game_collections.py`, not `collections.py` — caught during
  implementation that `collections` is a Python stdlib module name and would have shadowed
  it for anything imported afterward in the same process, the same class of collision
  already documented below for `gac.py`/`gc.py`.
- `notebooks/collections_marimo.py` — a new sibling notebook, not a change to
  `game_marimo.py`. A collection dropdown plus First/Prev/Next/Last "which game" buttons
  (mirroring `game_marimo.py`'s ply-stepper pattern) feed `pgn_text`; everything downstream
  (board, candidate picker, "What's risky"/"Tempting, but don't" sections, try-your-own-
  move) is `game_marimo.py`'s existing cell logic duplicated as-is — marimo notebooks can't
  import cells from another notebook file, so this is copy-not-share, same as the original
  Backlog note anticipated ("reusing the whole existing stack unchanged"). Both the
  collection index and the ply index are *clamped on read* (`min(get_x(), len(...) - 1)`)
  rather than reset when the underlying list changes size — switching to a shorter
  collection or game no longer risks an out-of-range crash, and this matches the "stay on
  whatever's currently loaded" instinct from the original design note instead of silently
  jumping back to the start.

`data/collections/*.pgn` is tracked in git (not gitignored, unlike `engine_cache.json`) —
this is curated content, not a disposable derived artifact. Added `data/collections/`
(with a `.gitkeep`, matching the sibling `data/`/`notebooks/` directories) but no bundled
demo collection; a throwaway 2-game test fixture used during development was deleted
before committing, per an explicit choice to keep the directory empty until real
collections are added.

Verified against the real running container: restarted it after adding the two new files
(bind-mounted, no rebuild needed) and confirmed via `docker exec ps aux` that
`entrypoint.sh`'s existing `NOTEBOOKS -gt 1` branch activated correctly —
`collections_marimo.py` and `game_marimo.py` each got their own port (12346/12347) and the
landing page came back up on 12345, exactly as designed when Jupyter was retired (see
below) but never yet exercised with a real second notebook. Used a throwaway Playwright
script (see the live-verification note on the "What's risky" entry below for why
Playwright, not the Chrome extension) against the real Stockfish backend: picked a 2-game
test collection, confirmed the first game auto-loaded and fully analyzed (board, candidate
ranking, risk notes all rendered correctly), then confirmed "Next game" correctly switched
to the second game and re-ran the whole analysis pipeline for it (`Move 1 of 8: 1.e4 —
Best (+0.25)` vs. the first game's `Move 1 of 4: 1.f3 — Inaccuracy (-0.73)`).

Also discovered during this verification: a freshly started `marimo edit` kernel does NOT
auto-run its cells — every cell shows just source code with an individual ▶ run button
until something (a human, or a script) triggers the notebook-wide "run all" control.
`game_marimo.py` never showed this because its kernel had already been run interactively
before this session touched it. This means after every container restart, EVERY notebook
sits blank until manually run once — worth keeping in mind, and noted alongside the
related single-shared-kernel discovery in `IDEAS.md`.

## Jupyter retired; one stable port (12345) now hosts a generated landing page
Status: DECIDED

Requested: stop `git status` from ever needing to change alongside picking a port to use,
and get a single stable URL to point a browser at, instead of memorizing which port
serves which notebook. Implemented per TASKS.md Backlog items 2-3 (design settled via MCQ
discussion 2026-09-18):

- `entrypoint.sh` no longer launches `jupyter notebook` at all. The Dockerfile's `jupyter`
  pip install and `notebooks/Position.ipynb`/`Game.ipynb` themselves are untouched —
  reversible with a one-line entrypoint change, no rebuild needed to bring Jupyter back.
- `config.sh` drops the old single `MARIMO_PORT` in favor of a range
  (`MARIMO_PORT_START=12346`, `MARIMO_PORT_END=12350`) — `run.sh` publishes the whole
  range (`docker run -p 12346-12350:12346-12350`) since Docker's port mappings must be
  fixed before the container starts, even though which notebooks actually claim which
  port within that range is decided dynamically, inside the container, at each start.
- `entrypoint.sh` globs `/app/*_marimo.py`, launches one `marimo edit` process per file
  found (today: just `game_marimo.py`), assigning ports sequentially from
  `MARIMO_PORT_START`; extra notebooks beyond `MARIMO_PORT_END` are skipped with a
  stderr warning rather than crashing. New notebooks (Collections/Opening-prep/Tutorial,
  per TASKS.md) need zero `config.sh` changes to get a port.
- Refined same-day (2026-09-18, after the first pass put `game_marimo.py` on `12346` and
  the landing page alone on `12345`): with only one `*_marimo.py` file, standing up a
  landing page with nothing else to link to just adds a second port to remember for no
  benefit. `entrypoint.sh` now branches on the notebook count — exactly one notebook goes
  directly on `LANDING_PORT` (`12345`) with no landing page at all; two or more fall
  through to the landing-page behavior below, unchanged. The moment a second notebook
  (Collections/Opening-prep/Tutorial, per TASKS.md) shows up, the landing page reappears
  automatically — no further code changes needed then.
- Landing-page branch (two or more notebooks): a page generated fresh into
  `/srv/landing/index.html` on every container start (a build step, not a hand-maintained
  file) — deliberately NOT under `/app` (bind-mounted to the host), so the generated file
  never shows up in `git status` on the host. Served by a plain `gosu`'d `python3 -m
  http.server` on `LANDING_PORT` — zero new dependencies.
- Each notebook's "live" status on the page is a client-side JS `fetch(url, {mode:
  "no-cors"})` probe run in the browser on page load/refresh, not baked in at
  container-start — genuinely current, not just "what was running when the container
  booted."
- Both the array-based PID/trap/wait generalization (was hardcoded to exactly two
  processes; now handles however many `*_marimo.py` files exist, plus the landing-page
  server when there's more than one) and the whole flow were verified against a real
  rebuilt image and a running container (not just read through), across both branches:
  the original two-port pass confirmed no `jupyter` process exists, `12345` served the
  generated landing page linking to `game_marimo` on `12346`, `12346` itself responded,
  both server processes ran as the unprivileged `crun` user, and `docker stop` cleanly
  tore the container down (the brief "Dead" status observed was mid-teardown, not a hang
  — the `--rm` container fully self-removed immediately after). The same-day refinement
  was re-verified the same way: with the single `game_marimo.py` notebook, `12345` now
  serves marimo directly (confirmed via `curl` and the container's own startup log), and
  `ps aux` inside the container shows only the one marimo process — no landing page, no
  `http.server`, no `jupyter`.

## Candidate-list detail now flags "What's risky" for Inaccuracy/Blunder-tier moves
Status: DECIDED

Requested: the per-candidate detail block on the right of the board (rendered by
`render_candidate_html()` in `position.py`, shown by `game_marimo.py`'s candidate picker)
listed the engine's expected reply as a neutral forecast ("Engine expects Black's reply
Nxe5 — ...") even for candidates well behind the top move, without saying *why* that
reply is a problem. Extended `_describe_continuation()` with a `risky=` flag that reframes
just the first continuation line as "What's risky: opens the door to ... — {reason}"
instead — reusing the same PV/classify_move() data already computed, no new engine calls.
`render_candidate_html()` passes `risky=True` only when the candidate's `quality` (now
added to every `rank_candidates()` entry, via the existing `gap_quality()`) is
Inaccuracy or Blunder; Best/Good-tier candidates (including the top move itself) keep the
neutral phrasing, since a move that's merely a touch behind isn't actually wrong. Later PV
plies keep the neutral "Then ... continues" wording regardless — they're follow-through,
not the risk itself. Styling stays the same as the rest of the candidate list (no red/warn
color, unlike the separate "Tempting, but don't" section) since these are still legitimate
top-5 engine moves, not traps.

`position.py` bumped `0.7.0` → `0.8.0` (MINOR — new `quality` field and `risky=` param are
additive, no existing signature/behavior changes). Verified offline with a `FakeEngine`-
style hand-built multipv result (Stockfish itself won't run natively on the host): a Best
move and a Blunder-tier move both with replies confirmed the top move keeps "Engine
expects" while the Blunder-tier one gets "What's risky"; a second check with a synthetic
Good-tier candidate confirmed it stays neutral too.

Live-verified 2026-09-22 against the actual running container (`game_marimo.py` on port
12345, real Stockfish) via a throwaway Playwright script (`uv run`, using the `playwright`
package already present in the global `uv` environment — Chrome's own extension-based
automation wasn't connected this session). Stepped through the default demo game
(`1. e4 e5 2. Nc3 Nc6 3. Bc4 Nf6 4. Nf3 Bb4 5. Nd5 d6`), captured every ply's candidate-list
gap values, and selected the worst one found (ply 10, rank-5 candidate `h3`, gap -0.70 —
Inaccuracy tier). The detail panel read exactly as designed: "Clearly behind the top move.
(Gap vs best: -0.70)" followed by "What's risky: opens the door to Black's Nxd5 — Captures
White's Knight." Confirms the offline `FakeEngine` result generalizes to a real Stockfish
multipv result rendered through the live marimo UI, not just the hand-built test data.

## Debug logging added to position.py/game.py, writing to /data/debug.log
Status: DECIDED

Requested so unexpected behavior noticed while using `game_marimo.py` (the PGN
game-discusser) can be pointed back to a concrete log line instead of relying on memory.
Added a `logging` setup in `position.py`: a `"chess"` root logger holding one
`RotatingFileHandler` (`/data/debug.log`, 2MB/3 backups, gitignored like
`engine_cache.json`), guarded with `if not _log_root.handlers` so a kernel restart or
marimo reimport of the module doesn't double-attach handlers and double every line.
`position.py` logs as `"chess.position"`, `game.py` as `"chess.game"` — both children of
`"chess"`, so they share its one handler without each needing its own setup. Debug lines
cover the actual points worth tracing back: engine cache hit/miss in `_analyze()` and
`_evaluate_cached()`, engine process start in `open_engine()`, `score_move()`'s
try-your-own-move calls, `rank_dont_list()`'s tempting-move count, `sweep_game()`'s
start/end, and — in `game_marimo.py`'s try-your-own-move cell — illegal SAN input, since
that's a thing a user can actually trigger and want to mention later.

Verified offline (Stockfish itself won't run natively on the host — `./stockfish-bin` is
Linux-arch-specific, built for the container — so a `FakeEngine` stand-in matching
`chess.engine`'s real return shapes, dict for default multipv/list for explicit multipv,
was used instead): ran `position.moves()` twice (cache MISS then HIT), `score_move()`, a
deliberately illegal SAN, and `game.sweep_game()` against a short PGN, then read back
`/data/debug.log` and confirmed every expected line was there in order. `position.py`
bumped `0.6.0` → `0.7.0`, `game.py` `0.3.0` → `0.4.0` (both MINOR — new logging
infrastructure, no existing signature/behavior changes).

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
