"""Notes shown at the bottom of the landing page, read from one plain file.

The file is edited by hand (in an editor, or by asking Claude to edit it). Its
first line is a "last updated" header that this module keeps current: each time
the page renders, if the note text no longer matches the hash recorded in the
header, the header is rewritten with the file's own modification time. So the
stamp is the real edit time, even though nothing ran at the moment of the edit.
A header is added automatically the first time the file is rendered.

See DECISIONS.md for why the stamp lives in the file rather than in the OS mtime."""

import datetime
import hashlib
import html
import os
import re

__ver__ = "0.1.0"
print(f"notes ver {__ver__}")

HEADER_RE = re.compile(r"<!-- last updated: (.+?) \| hash: ([0-9a-f]{12}) -->\n?")
URL_RE = re.compile(r"https?://[^\s<]+")


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


def render_notes_html(path):
    """The notes section for the landing page: one paragraph per non-blank
    line, bare URLs turned into links, and the last-updated stamp. Escapes
    everything first, so a note can't inject markup. Returns an HTML string."""
    result = sync(path)
    if result is None:
        return '<section class="notes"><h2>Notes</h2><p class="stamp">No notes yet.</p></section>'
    stamp, body = result
    paragraphs = []
    for line in body.splitlines():
        if not line.strip():
            continue
        escaped = html.escape(line.strip())
        linked = URL_RE.sub(lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>', escaped)
        paragraphs.append(f"<p>{linked}</p>")
    return (
        '<section class="notes"><h2>Notes</h2>'
        + "".join(paragraphs)
        + f'<p class="stamp">Last updated {stamp}</p></section>'
    )
