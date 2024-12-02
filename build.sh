#!/bin/bash
source config.sh

docker build --progress=plain -t $IMAGE_NAME .
