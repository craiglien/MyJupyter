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

LANDING_PORT_VAL=${LANDING_PORT:-12345}
MARIMO_PORT_START_VAL=${MARIMO_PORT_START:-12346}
MARIMO_PORT_END_VAL=${MARIMO_PORT_END:-12350}

# Jupyter is retired (see TASKS.md's Backlog) — every *_marimo.py file under
# /app gets its own marimo process instead. An arbitrary number of
# long-running servers now share the container (not a fixed two), so PIDs
# go in an array; trap/wait below generalize accordingly.
PIDS=()

shopt -s nullglob
NOTEBOOKS=(/app/*_marimo.py)
shopt -u nullglob

if [ "${#NOTEBOOKS[@]}" -eq 1 ]; then
  # Only one notebook exists — put it directly on the one stable,
  # externally-published port instead of standing up a landing page with
  # nothing else to link to. The moment a second *_marimo.py file shows up
  # (Collections/Opening-prep/Tutorial, per TASKS.md), this falls through
  # to the landing-page branch below with no further changes needed here.
  # marimo run, not marimo edit — see DECISIONS.md's Phase 3 entry. Notebook
  # authoring happens by editing the .py file directly (Claude Code, or by
  # hand), never through marimo's own in-browser code editor; --watch picks
  # up any such file edit and reloads automatically, no restart needed.
  # --include-code keeps the source visible in the browser, matching the
  # previous edit-mode experience (marimo run hides it by default).
  gosu ${U} marimo run "${NOTEBOOKS[0]}" --headless --no-token --watch --include-code --host 0.0.0.0 --port "$LANDING_PORT_VAL" &
  PIDS+=($!)

elif [ "${#NOTEBOOKS[@]}" -gt 1 ]; then
  # Multiple notebooks: each gets its own port from the range, sequentially,
  # and a landing page on LANDING_PORT links to all of them. Regenerated
  # fresh on every container start rather than hand-maintained, and written
  # to /srv/landing — deliberately NOT under /app (bind-mounted to the
  # host) — so this generated file never shows up as an untracked/dirty
  # file in `git status` on the host, which is the exact problem TASKS.md's
  # "Stop git status..." item is about.
  LANDING_DIR=/srv/landing
  mkdir -p "$LANDING_DIR"

  LINKS_HTML=""
  port=$MARIMO_PORT_START_VAL

  for nb in "${NOTEBOOKS[@]}"; do
    name=$(basename "$nb" .py)
    if [ "$port" -gt "$MARIMO_PORT_END_VAL" ]; then
      echo "entrypoint: no free port left in ${MARIMO_PORT_START_VAL}-${MARIMO_PORT_END_VAL} for ${name}, skipping" >&2
      continue
    fi

    # marimo run, not marimo edit — see the single-notebook branch above and
    # DECISIONS.md's Phase 3 entry for why.
    gosu ${U} marimo run "$nb" --headless --no-token --watch --include-code --host 0.0.0.0 --port "$port" &
    PIDS+=($!)

    LINKS_HTML="${LINKS_HTML}
    <li class=\"nb\">
      <a href=\"#\" class=\"nb-link\" data-port=\"${port}\">${name}</a>
      <span class=\"status\" id=\"status-${port}\">checking…</span>
    </li>"

    port=$((port + 1))
  done

  # Status per notebook is checked client-side (a fetch() probe against
  # each port, run in the browser on page load) rather than baked in here
  # at container-start — that's the difference between "genuinely live"
  # and "what was running when the container booted."
  cat > "${LANDING_DIR}/index.html" <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>myjupyter-pychess notebooks</title>
<style>
  body { font-family: sans-serif; max-width: 40em; margin: 3em auto; }
  ul { list-style: none; padding: 0; }
  li.nb { display: flex; justify-content: space-between; padding: 0.5em 0; border-bottom: 1px solid #ddd; }
  a.nb-link { font-size: 1.1em; text-decoration: none; }
  .status { font-size: 0.9em; color: #888; }
  .status.up { color: #2a7; }
  .status.down { color: #c33; }
</style>
</head>
<body>
<h1>Notebooks</h1>
<ul>
${LINKS_HTML}
</ul>
<script>
  document.querySelectorAll(".nb-link").forEach(function (a) {
    var port = a.dataset.port;
    a.href = "http://" + window.location.hostname + ":" + port + "/";
  });

  function checkStatus(el) {
    var port = el.id.replace("status-", "");
    var url = "http://" + window.location.hostname + ":" + port + "/";
    fetch(url, { mode: "no-cors", cache: "no-store" })
      .then(function () { el.textContent = "● up"; el.className = "status up"; })
      .catch(function () { el.textContent = "● down"; el.className = "status down"; });
  }

  document.querySelectorAll(".status").forEach(checkStatus);
</script>
</body>
</html>
HTML

  chown -R ${U}:${G} "$LANDING_DIR"

  gosu ${U} python3 -m http.server "$LANDING_PORT_VAL" --directory "$LANDING_DIR" --bind 0.0.0.0 &
  PIDS+=($!)

else
  echo "entrypoint: no *_marimo.py notebooks found under /app" >&2
fi

trap 'kill -TERM "${PIDS[@]}" 2>/dev/null' TERM INT
wait -n "${PIDS[@]}"
