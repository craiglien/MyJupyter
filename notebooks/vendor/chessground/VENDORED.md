# Vendored: chessground 9.2.1

Fetched 2026-10-12 from jsdelivr's mirror of the published npm package (not built from
source, not a CDN reference — these 4 files are committed here so `board_widget.py`'s
drag-and-drop board works with zero network access, at both build time and runtime; see
`DECISIONS.md`).

License: GPL-3.0 (lichess-org/chessground). Irrelevant for this private, unpublished
project; see `CLAUDE.md`'s README-on-publish note if that ever changes.

Files, and how they were fetched (re-run with a newer version number to update):

```
curl -fsSL "https://cdn.jsdelivr.net/npm/chessground@9.2.1/+esm" -o chessground.mjs
curl -fsSL "https://cdn.jsdelivr.net/npm/chessground@9.2.1/assets/chessground.base.css" -o chessground.base.css
curl -fsSL "https://cdn.jsdelivr.net/npm/chessground@9.2.1/assets/chessground.brown.css" -o chessground.brown.css
curl -fsSL "https://cdn.jsdelivr.net/npm/chessground@9.2.1/assets/chessground.cburnett.css" -o chessground.cburnett.css
```

All piece and board-square artwork is embedded in the CSS as base64 data URIs (chessground's
own doing, not something added here) — no separate image files, no further assets to vendor.
`chessground.mjs` has zero `import` statements (chessground has no runtime dependencies) —
confirmed before committing, so this one file is truly self-contained.
