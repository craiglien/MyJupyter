#!/bin/bash
source config.sh

# docker build --progress=plain -t $IMAGE_NAME .
DOCKER_BUILDKIT=0 docker build -t $IMAGE_NAME .

# Pull the Stockfish binary built inside the container (native to the build
# host's architecture) back out as a standalone artifact.
DOCKER_BUILDKIT=0 docker build --target stockfish-build -t "${IMAGE_NAME}-stockfish-build" .
CID=$(docker create "${IMAGE_NAME}-stockfish-build")
docker cp "$CID":/build/src/stockfish ./stockfish-bin
docker rm "$CID" > /dev/null

