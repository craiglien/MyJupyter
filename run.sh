#!/bin/bash
source config.sh

docker run -it --rm \
    -p "$HOST_PORT":"$HOST_PORT" \
    -p "$MARIMO_PORT_START"-"$MARIMO_PORT_END":"$MARIMO_PORT_START"-"$MARIMO_PORT_END" \
    -e LANDING_PORT=$HOST_PORT \
    -e MARIMO_PORT_START=$MARIMO_PORT_START \
    -e MARIMO_PORT_END=$MARIMO_PORT_END \
    -e LOCAL_UID="$USER_UID" \
    -e LOCAL_GID="$USER_GID" \
    -v "$HOST_NOTEBOOK_DIR":/app \
    -v "$HOST_DATA_DIR":/data \
    $IMAGE_NAME
