#!/bin/bash

# --- Provenance banner ---
# Three points in time that can silently drift apart over a long-lived,
# bind-mounted-source setup like this one: when the source was last
# committed, when the image was built from it, and when this container
# actually started. Printed first, before anything else, so it's the first
# thing visible in `bash run.sh`'s terminal output. See DECISIONS.md.
_fmt_age() {
  # Seconds elapsed -> a short human string ("5m ago", "3h ago", "2d ago").
  local secs=$1
  if [ "$secs" -lt 60 ]; then
    echo "${secs}s ago"
  elif [ "$secs" -lt 3600 ]; then
    echo "$((secs / 60))m ago"
  elif [ "$secs" -lt 86400 ]; then
    echo "$((secs / 3600))h ago"
  else
    echo "$((secs / 86400))d ago"
  fi
}

if [ -f /build_info.txt ]; then
  mapfile -t _build_info < /build_info.txt
  BUILD_COMMIT=${_build_info[0]}
  BUILD_COMMIT_SUBJECT=${_build_info[1]}
  BUILD_EPOCH=${_build_info[2]}
fi
BUILD_EPOCH=${BUILD_EPOCH:-0}
BUILD_AGE=$(_fmt_age "$(( $(date +%s) - BUILD_EPOCH ))")

echo "=================================================================="
echo "Source commit (as of 'bash run.sh'): ${RUN_COMMIT:-unknown} — ${RUN_COMMIT_SUBJECT:-unknown} (${RUN_COMMIT_RELTIME:-unknown})"
echo "Image built from commit:             ${BUILD_COMMIT:-unknown} — ${BUILD_COMMIT_SUBJECT:-unknown} (${BUILD_AGE})"
echo "Container starting:                  now"
if [ -n "$RUN_COMMIT" ] && [ "${BUILD_COMMIT:-unknown}" != "unknown" ] && [ "$RUN_COMMIT" != "$BUILD_COMMIT" ]; then
  echo ""
  echo "⚠  Image was built from a DIFFERENT commit than what's checked out now."
  echo "   Run 'bash build.sh' to pick up the latest source."
else
  echo "✓  Image matches the current source commit."
fi
echo "=================================================================="

U=crun
G=${U}

USER_ID=${LOCAL_UID:-1000}
GROUP_ID=${LOCAL_GID:-1000}

existing_group=$(getent group $GROUP_ID | cut -d: -f1)
if [ -n "$existing_group" ]; then
  groupmod -n ${G} $existing_group
else
  groupadd -g $GROUP_ID ${G}
fi


existing_user=$(getent passwd $USER_ID | cut -d: -f1)
if [ -n "$existing_user" ]; then
  usermod -l ${U} $existing_user
  usermod -d /home/${U} -m ${U}
else
  # Create the user if it doesn't already exist
  useradd -m -u $USER_ID -g ${G} -s /bin/bash ${U}
fi

chown ${U}:${G} /app

PIDS=()
HOST_PORT_VAL=${HOST_PORT:-12345}

# One server for everything, on the one published port: serve.py mounts every
# *_marimo.py notebook under /<name> and the landing page at /. Served by
# uvicorn with --reload, so a .py edit restarts the server (notebook kernels
# reset, which is the trade-off DECISIONS.md records) — no per-notebook ports.
shopt -s nullglob
NOTEBOOKS=(/app/*_marimo.py)
shopt -u nullglob

# endgame_studies is pinned last rather than left in alphabetical order —
# it's an additional/bonus feature, not part of the core notebook set.
# nav.py's in-page nav bar follows the same convention.
ENDGAME_NB=""
OTHER_NOTEBOOKS=()
for nb in "${NOTEBOOKS[@]}"; do
  if [ "$(basename "$nb" _marimo.py)" = "endgame_studies" ]; then
    ENDGAME_NB="$nb"
  else
    OTHER_NOTEBOOKS+=("$nb")
  fi
done
NOTEBOOKS=("${OTHER_NOTEBOOKS[@]}")
if [ -n "$ENDGAME_NB" ]; then
  NOTEBOOKS+=("$ENDGAME_NB")
fi

if [ "${#NOTEBOOKS[@]}" -eq 0 ]; then
  echo "entrypoint: no *_marimo.py notebooks found under /app" >&2
  exit 1
fi

# Landing page, regenerated on every container start and written to /srv/landing
# rather than /app — /app is bind-mounted to the host, and a generated file there
# would show up as untracked in `git status`. Same provenance as the terminal
# banner above, shown on the page so the commit is visible without a terminal.
LANDING_DIR=/srv/landing
mkdir -p "$LANDING_DIR"

html_escape() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<< "$1"; }
PROV_HTML="<p class=\"prov\">Source commit <code>${RUN_COMMIT:-unknown}</code> — $(html_escape "${RUN_COMMIT_SUBJECT:-unknown}") (${RUN_COMMIT_RELTIME:-unknown})<br>
Image built from <code>${BUILD_COMMIT:-unknown}</code> — $(html_escape "${BUILD_COMMIT_SUBJECT:-unknown}") (${BUILD_AGE})</p>"

LINKS_HTML=""
for nb in "${NOTEBOOKS[@]}"; do
  slug=$(basename "$nb" _marimo.py)
  LINKS_HTML="${LINKS_HTML}
    <li class=\"nb\"><a class=\"nb-link\" href=\"${slug}/\">${slug}</a></li>"
done

cat > "${LANDING_DIR}/index.html" <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>myjupyter-pychess notebooks</title>
<style>
  body { font-family: sans-serif; max-width: 40em; margin: 3em auto; }
  ul { list-style: none; padding: 0; }
  li.nb { padding: 0.5em 0; border-bottom: 1px solid #ddd; }
  a.nb-link { font-size: 1.1em; text-decoration: none; }
  .prov { font-size: 0.85em; color: #888; margin: 0 0 1.5em; }
  section.notes { margin-top: 2.5em; border-top: 1px solid #ddd; padding-top: 0.5em; }
  section.notes p { margin: 0.5em 0; line-height: 1.4; }
  section.notes h3 { margin: 1.2em 0 0.4em; }
  section.notes h4 { margin: 0.8em 0 0.3em; }
  .note-entry { margin: 0.6em 0; }
  .note-title { font-weight: bold; margin: 0; }
  .note-link { font-size: 0.85em; margin: 0.15em 0; }
  .note-link a { color: inherit; }
  .note-date { font-size: 0.8em; color: #888; margin: 0 0 0.3em; }
  .stamp { font-size: 0.85em; color: #888; }
</style>
</head>
<body>
<h1>Notebooks</h1>
${PROV_HTML}
<ul>
${LINKS_HTML}
</ul>
<!--NOTES-->
</body>
</html>
HTML

chown -R ${U}:${G} "$LANDING_DIR"

gosu ${U} uvicorn serve:app --app-dir /app --host 0.0.0.0 --port "$HOST_PORT_VAL" --reload --reload-dir /app &
PIDS+=($!)

trap 'kill -TERM "${PIDS[@]}" 2>/dev/null' TERM INT
wait -n "${PIDS[@]}"
