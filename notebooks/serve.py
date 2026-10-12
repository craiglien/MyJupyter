"""One ASGI app for the whole container: every *_marimo.py notebook mounted at
/<name> (game_marimo.py -> /game), and the generated landing page at /.

Run by entrypoint.sh via uvicorn, on the single published port. Replaces the
earlier one-marimo-process-per-notebook-plus-landing-page setup, which needed a
port per notebook; see DECISIONS.md for why this is one server now."""

import glob
from pathlib import Path

import marimo
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import notes

NOTEBOOK_DIR = "/app"
# Vendored JS/CSS for board_widget.py's drag-and-drop board (see
# notebooks/vendor/chessground/VENDORED.md) — mounted at the site root, not
# under any one notebook's /<slug> prefix, so the same absolute URL
# (/vendor/chessground/...) resolves correctly no matter which notebook's
# page references it.
VENDOR_DIR = f"{NOTEBOOK_DIR}/vendor"
# Written by entrypoint.sh at container start (see there for why /srv, not /app).
LANDING_PAGE = "/srv/landing/index.html"
# Your notes, shown on the landing page. Lives in ./data (gitignored), so it's
# read per request: edits appear on the next page load, no restart needed.
NOTES_PATH = "/data/notes.md"


def build_app():
    builder = marimo.create_asgi_app(quiet=True, include_code=True)
    for path in sorted(glob.glob(f"{NOTEBOOK_DIR}/*_marimo.py")):
        slug = Path(path).stem.removesuffix("_marimo")
        builder = builder.with_app(path=f"/{slug}", root=path)

    async def landing(request):
        with open(LANDING_PAGE, encoding="utf-8") as f:
            page = f.read()
        return HTMLResponse(page.replace("<!--NOTES-->", notes.render_notes_html(NOTES_PATH)))

    return Starlette(routes=[
        Route("/", landing),
        Mount("/vendor", app=StaticFiles(directory=VENDOR_DIR)),
        Mount("/", app=builder.build()),
    ])


app = build_app()
