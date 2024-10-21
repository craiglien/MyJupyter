#!/bin/bash
source config.sh

docker build -t $IMAGE_NAME .
