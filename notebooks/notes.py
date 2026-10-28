"""Notes shown at the bottom of the landing page, read from one plain file.

The file is edited by hand (in an editor, or by asking Claude to edit it). Its
first line is a "last updated" header that this module keeps current: each time
the page renders, if the note text no longer matches the hash recorded in the
header, the header is rewritten with the file's own modification time. So the
stamp is the real edit time, even though nothing ran at the moment of the edit.
A header is added automatically the first time the file is rendered.

Body structure: "## <section>" and "### <subsection>" heading lines, then
entries underneath as three consecutive non-blank lines each (title, link,
date added). Blank lines are skipped, so they're optional but useful for
readability between entries.

See DECISIONS.md for why the stamp lives in the file rather than in the OS
mtime, and for why entries are structured this way."""

import datetime
import hashlib
import html
import os
import re

__ver__ = "1.0.0"
print(f"notes ver {__ver__}")

HEADER_RE = re.compile(r"<!-- last updated: (.+?) \| hash: ([0-9a-f]{12}) -->\n?")


def _hash(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def sync(path):
    """Return (stamp, body) for the notes file at `path`, rewriting its header
    first if the body changed since the header was last written. Returns None
    if there's no file yet."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = HEADER_RE.match(text)
    body = text[m.end():] if m else text
    if m and m.group(2) == _hash(body):
        return m.group(1), body

    edited = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    stamp = edited.strftime("%Y-%m-%d %H:%M")
    header = f"<!-- last updated: {stamp} | hash: {_hash(body)} -->\n"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(header + body)
    os.replace(tmp, path)
    return stamp, body


def _parse_items(body):
    """Body -> a list of ("h3", text) / ("h4", text) / ("entry", title, link,
    date) / ("incomplete", lines) items, in order. "## "/"### " lines are
    section/subsection headings; every other run of three consecutive
    non-blank lines is one entry (title, link, date added). A trailing run of
    1-2 lines (a hand-editing mistake, e.g. a forgotten date) comes back as
    "incomplete" instead of being silently dropped."""
    items = []
    buf = []

    def flush():
        if not buf:
            return
        if len(buf) == 3:
            items.append(("entry", buf[0], buf[1], buf[2]))
        else:
            items.append(("incomplete", list(buf)))
        buf.clear()

    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("### "):
            flush()
            items.append(("h4", line[len("### "):]))
        elif line.startswith("## "):
            flush()
            items.append(("h3", line[len("## "):]))
        else:
            buf.append(line)
            if len(buf) == 3:
                flush()
    flush()
    return items


def render_entry_html(title, link, date):
    """One note entry's HTML: a bold title, the link underneath in a smaller
    font (`.note-link`, styled in the landing page's <style> block), then the
    date it was added. Escapes everything first, so a note can't inject
    markup. The one place this formatting is defined — reused by every entry
    `render_notes_html()` renders, so new entries stay visually consistent as
    more get added."""
    return (
        '<div class="note-entry">'
        f'<p class="note-title">{html.escape(title)}</p>'
        f'<p class="note-link"><a href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(link)}</a></p>'
        f'<p class="note-date">Added {html.escape(date)}</p>'
        '</div>'
    )


def render_notes_html(path):
    """The notes section for the landing page: "## "/"### " section/subsection
    headings and three-line (title, link, date added) entries underneath
    them, rendered via render_entry_html(), plus the last-updated stamp.
    Returns an HTML string."""
    result = sync(path)
    if result is None:
        return '<section class="notes"><h2>Notes</h2><p class="stamp">No notes yet.</p></section>'
    stamp, body = result

    parts = []
    for item in _parse_items(body):
        kind = item[0]
        if kind == "h3":
            parts.append(f"<h3>{html.escape(item[1])}</h3>")
        elif kind == "h4":
            parts.append(f"<h4>{html.escape(item[1])}</h4>")
        elif kind == "entry":
            _, title, link, date = item
            parts.append(render_entry_html(title, link, date))
        else:  # "incomplete"
            lines = ", ".join(html.escape(l) for l in item[1])
            parts.append(
                '<p class="note-incomplete">⚠️ Incomplete note entry '
                f"(expected title/link/date): {lines}</p>"
            )

    return (
        '<section class="notes"><h2>Notes</h2>'
        + "".join(parts)
        + f'<p class="stamp">Last updated {stamp}</p></section>'
    )
