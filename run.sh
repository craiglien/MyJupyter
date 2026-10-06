#!/bin/bash
source config.sh

# Source-commit provenance, computed here (on the host, where .git actually
# lives — it's never mounted into the container) and handed to entrypoint.sh
# via env vars. Only git's own relative-date formatting is used (%cr) so
# this stays portable across BSD date (macOS) and GNU date (Linux) hosts —
# no `date -d` math needed on the host side. See DECISIONS.md.
RUN_COMMIT=$(git rev-parse --short HEAD)
RUN_COMMIT_SUBJECT=$(git log -1 --format=%s)
RUN_COMMIT_RELTIME=$(git log -1 --format=%cr)

docker run -it --rm \
    -p "$HOST_PORT":"$HOST_PORT" \
    -e HOST_PORT=$HOST_PORT \
    -e LOCAL_UID="$USER_UID" \
    -e LOCAL_GID="$USER_GID" \
    -e RUN_COMMIT="$RUN_COMMIT" \
    -e RUN_COMMIT_SUBJECT="$RUN_COMMIT_SUBJECT" \
    -e RUN_COMMIT_RELTIME="$RUN_COMMIT_RELTIME" \
    -v "$HOST_NOTEBOOK_DIR":/app \
    -v "$HOST_DATA_DIR":/data \
    $IMAGE_NAME
