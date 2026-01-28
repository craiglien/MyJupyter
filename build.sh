#!/bin/bash
source config.sh

# docker build --progress=plain -t $IMAGE_NAME .
DOCKER_BUILDKIT=0 docker build -t $IMAGE_NAME .

# Get stockfish.

#wget https://github.com/official-stockfish/Stockfish/releases/download/sf_17/stockfish-ubuntu-x86-64.tar

