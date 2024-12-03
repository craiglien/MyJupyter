#!/bin/bash
source config.sh

DOCKER_BUILDKIT=0 docker build -t $IMAGE_NAME .
