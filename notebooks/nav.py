"""Shared top-of-page navigation bar for every *_marimo.py notebook.

Auto-discovers sibling notebooks with the same glob serve.py already uses
to mount them, so a new notebook (e.g. a future opening-prep one) shows up
in the bar automatically — no nav-bar edit needed when one's added or
removed. Each notebook calls nav_bar_html() with its own slug as the one
hardcoded string, so it can show itself as plain text instead of a link."""

import glob
import os

__ver__ = "0.1.0"
print(f"nav ver {__ver__}")

NOTEBOOK_DIR = os.path.dirname(os.path.abspath(__file__))

_STYLE = """<style>
  .nav-bar { display:flex; gap:16px; align-items:center; padding:8px 0 14px;
    margin-bottom:12px; border-bottom:1px solid #ddd; font-size:14px; }
  .nav-bar a { text-decoration:none; }
  .nav-bar .current { font-weight:bold; }
</style>"""


# Pinned last rather than sorted alphabetically with everything else —
# it's an additional/bonus feature, not part of the core notebook set.
# entrypoint.sh's landing-page link list follows the same convention.
_PINNED_LAST = ("endgame_studies",)


def nav_bar_html(current):
    """A top nav bar: a Home link back to the landing page, then every
    sibling *_marimo.py notebook, alphabetically except for _PINNED_LAST
    entries which always go last. `current` (the calling notebook's own
    slug, e.g. "game") is shown as plain bold text instead of a link to
    itself. Returns an HTML string."""
    slugs = sorted(
        os.path.basename(p)[: -len("_marimo.py")]
        for p in glob.glob(f"{NOTEBOOK_DIR}/*_marimo.py")
    )
    for slug in _PINNED_LAST:
        if slug in slugs:
            slugs.remove(slug)
            slugs.append(slug)
    items = ['<a href="/">← Home</a>']
    for slug in slugs:
        if slug == current:
            items.append(f'<span class="current">{slug}</span>')
        else:
            items.append(f'<a href="/{slug}/">{slug}</a>')
    return f'<div class="nav-bar">{_STYLE}{"".join(items)}</div>'
