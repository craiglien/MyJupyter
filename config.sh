IMAGE_NAME="jupyter-notebook"
HOST_NOTEBOOK_DIR=~+/notebooks
HOST_DATA_DIR=~+/data

# HOST_PORT is the one port the container publishes. serve.py (run by
# entrypoint.sh via uvicorn) serves the landing page on it at /, and every
# *_marimo.py notebook under ./notebooks at /<name>.
HOST_PORT=12345

USER_UID=$(id -u)
USER_GID=$(id -g)
