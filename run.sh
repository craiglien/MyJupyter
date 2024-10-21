#!/bin/bash
source config.sh

docker run -it --rm -p "$HOST_PORT":"$HOST_PORT" \
    -e JUPYTER_PORT=$HOST_PORT \
    -e LOCAL_UID="$USER_UID" \
    -e LOCAL_GID="$USER_GID" \
    -v "$HOST_NOTEBOOK_DIR":/app \
    -v "$HOST_DATA_DIR":/data \
    $IMAGE_NAME
