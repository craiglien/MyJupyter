IMAGE_NAME="jupyter-notebook"
HOST_NOTEBOOK_DIR=~+/notebooks
HOST_DATA_DIR=~+/data

# HOST_PORT is the one stable, externally-published port. With 2+ notebooks
# it hosts a generated landing page (see entrypoint.sh); with exactly one
# (today: just game_marimo.py) that one notebook runs directly on it instead.
# Jupyter is retired; each *_marimo.py notebook found under ./notebooks gets
# its own port assigned at container start, sequentially from
# MARIMO_PORT_START up to MARIMO_PORT_END — the range just needs to be big
# enough to cover however many *_marimo.py files exist, with room to grow
# (see TASKS.md's Backlog items 2-3 for planned future notebooks).
HOST_PORT=12345
MARIMO_PORT_START=12346
MARIMO_PORT_END=12350

USER_UID=$(id -u)
USER_GID=$(id -g)
