#!/bin/bash
source config.sh

# Build-time provenance, baked into the image as /build_info.txt so
# entrypoint.sh can compare it against the *current* source commit at
# container-start time (see run.sh) and flag drift. BUILD_EPOCH (not a
# human string) is what's actually baked in — computing "how long ago" is
# left to entrypoint.sh, which always runs inside the Ubuntu container and
# can rely on GNU date; `date +%s` alone is portable enough for this host
# side. See DECISIONS.md.
BUILD_COMMIT=$(git rev-parse --short HEAD)
BUILD_COMMIT_SUBJECT=$(git log -1 --format=%s)
BUILD_EPOCH=$(date -u +%s)

# docker build --progress=plain -t $IMAGE_NAME .
DOCKER_BUILDKIT=0 docker build \
    --build-arg BUILD_COMMIT="$BUILD_COMMIT" \
    --build-arg BUILD_COMMIT_SUBJECT="$BUILD_COMMIT_SUBJECT" \
    --build-arg BUILD_EPOCH="$BUILD_EPOCH" \
    -t $IMAGE_NAME .

# Pull the Stockfish binary built inside the container (native to the build
# host's architecture) back out as a standalone artifact.
DOCKER_BUILDKIT=0 docker build --target stockfish-build -t "${IMAGE_NAME}-stockfish-build" .
CID=$(docker create "${IMAGE_NAME}-stockfish-build")
docker cp "$CID":/build/src/stockfish ./stockfish-bin
docker rm "$CID" > /dev/null

