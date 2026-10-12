"""A drag-and-drop chess board, for any notebook that wants mouse-driven move
input instead of pasting PGN or typing SAN. Shared infrastructure — wire it
into a notebook only when that notebook actually needs it; the existing
PGN/SAN-based notebooks (game_marimo.py, study_marimo.py, collections_marimo.py)
don't, and are untouched by this module existing.

Built as a marimo mo.ui.anywidget wrapping lichess's chessground JS library
(no dependencies, drag-and-drop built in). chessground's files are vendored
under notebooks/vendor/chessground/ (see VENDORED.md there) and served
locally by serve.py at /vendor/chessground/ — not fetched from a CDN, since
this project needs to work with no network access at all. chessground is
GPL-3.0; irrelevant for this private, unpublished project, but worth knowing
if that ever changes (see CLAUDE.md's README-on-publish note).

python-chess computes legal destinations and is the only move-legality
authority; the widget just reports (from_square, to_square) drags and
re-renders whatever FEN/destinations it's given — it has no chess rules of
its own.
"""

import os

import anywidget
import chess
import traitlets

__ver__ = "0.1.0"
print(f"board_widget ver {__ver__}")

_VENDOR = "/vendor/chessground"
_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "chessground")


def _read_vendored(filename):
    with open(os.path.join(_VENDOR_DIR, filename)) as f:
        return f.read()

_ESM = f"""
import {{ Chessground }} from "{_VENDOR}/chessground.mjs";

function toDests(destsObj) {{
  const m = new Map();
  for (const [from, tos] of Object.entries(destsObj)) {{
    m.set(from, tos);
  }}
  return m;
}}

function render({{ model, el }}) {{
  el.style.width = "400px";
  el.style.height = "400px";

  const cg = Chessground(el, {{
    fen: model.get("fen"),
    orientation: model.get("orientation"),
    movable: {{
      free: false,
      color: model.get("turn_color"),
      dests: toDests(model.get("dests")),
      events: {{
        after: (orig, dest) => {{
          model.set("last_move", orig + dest);
          model.save_changes();
        }},
      }},
    }},
  }});

  model.on("change:fen", () => cg.set({{ fen: model.get("fen") }}));
  model.on("change:dests", () =>
    cg.set({{ movable: {{ dests: toDests(model.get("dests")) }} }})
  );
  model.on("change:turn_color", () =>
    cg.set({{ movable: {{ color: model.get("turn_color") }} }})
  );
  model.on("change:orientation", () =>
    cg.set({{ orientation: model.get("orientation") }})
  );
}}

export default {{ render }};
"""

# Inlined, not @import-ed: anywidget applies _css via a Constructable
# Stylesheet (CSSStyleSheet.replace()), and @import rules are rejected
# there (see https://github.com/WICG/construct-stylesheets/issues/119) —
# confirmed as a real, silent styling failure before switching to this.
_CSS = "\n".join(
    _read_vendored(name)
    for name in ("chessground.base.css", "chessground.brown.css", "chessground.cburnett.css")
)


class BoardWidget(anywidget.AnyWidget):
    """A chessground board. Set `fen`/`dests`/`turn_color` to drive what's
    shown and draggable; read `last_move` (a 4-character UCI string like
    "e2e4") for what the user actually dragged. last_move is sticky — it
    isn't cleared after being read, so a caller must track which value it
    already acted on (e.g. comparing against a remembered "applied" value)
    rather than reacting to every read of it."""

    _esm = _ESM
    _css = _CSS

    fen = traitlets.Unicode("start").tag(sync=True)
    orientation = traitlets.Unicode("white").tag(sync=True)
    turn_color = traitlets.Unicode("white").tag(sync=True)
    dests = traitlets.Dict({}).tag(sync=True)
    last_move = traitlets.Unicode("").tag(sync=True)


def legal_dests(board):
    """board.legal_moves, reshaped into the {from_square: [to_square, ...]}
    shape chessground's `movable.dests` wants, for restricting/highlighting
    draggable destinations. Squares as chessground expects them: lowercase
    algebraic ("e2"), not python-chess's 0-63 integers."""
    dests = {}
    for move in board.legal_moves:
        frm = chess.square_name(move.from_square)
        to = chess.square_name(move.to_square)
        dests.setdefault(frm, []).append(to)
    return dests


def color_name(color):
    """chess.WHITE/chess.BLACK -> the "white"/"black" strings chessground's
    orientation/turn_color want."""
    return "white" if color == chess.WHITE else "black"
