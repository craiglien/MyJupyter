"""One ASGI app for the whole container: every *_marimo.py notebook mounted at
/<name> (game_marimo.py -> /game), and the generated landing page at /.

Run by entrypoint.sh via uvicorn, on the single published port. Replaces the
earlier one-marimo-process-per-notebook-plus-landing-page setup, which needed a
port per notebook; see DECISIONS.md for why this is one server now."""

import glob
from pathlib import Path

import marimo
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route

NOTEBOOK_DIR = "/app"
# Written by entrypoint.sh at container start (see there for why /srv, not /app).
LANDING_PAGE = "/srv/landing/index.html"


def build_app():
    builder = marimo.create_asgi_app(quiet=True, include_code=True)
    for path in sorted(glob.glob(f"{NOTEBOOK_DIR}/*_marimo.py")):
        slug = Path(path).stem.removesuffix("_marimo")
        builder = builder.with_app(path=f"/{slug}", root=path)

    async def landing(request):
        return FileResponse(LANDING_PAGE)

    return Starlette(routes=[
        Route("/", landing),
        Mount("/", app=builder.build()),
    ])


app = build_app()
