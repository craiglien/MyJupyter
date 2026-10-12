# Set Version
ARG UBUNTU_VERSION=24.04

# Build Stockfish from source for whatever architecture this stage runs on,
# instead of shipping a pre-built x86-64 binary that fails with "exec format
# error" on arm64 hosts (e.g. Apple Silicon).
FROM ubuntu:${UBUNTU_VERSION} AS stockfish-build

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl && \
    rm -rf /var/lib/apt/lists/*

COPY stockfish/src /build/src
WORKDIR /build/src
# The vendored source tree doesn't include scripts/get_native_properties.sh,
# so ARCH=native can't self-detect; pick a safe baseline per CPU family
# instead (matches what the official generic x86-64/arm64 releases use).
RUN case "$(uname -m)" in \
        x86_64) ARCH=x86-64 ;; \
        aarch64|arm64) ARCH=armv8 ;; \
        *) echo "Unsupported build architecture: $(uname -m)" >&2; exit 1 ;; \
    esac && \
    make -j"$(nproc)" build ARCH="$ARCH"

# Start with the latest Ubuntu base image
FROM ubuntu:${UBUNTU_VERSION}

ARG PYTHON_VERSION=3.10
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and the desired Python version
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        software-properties-common \
        ca-certificates \
        gosu \
        wget \
        unzip

# Dead Snakes
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update

RUN apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip && \
      rm -rf /var/lib/apt/lists/*

# Ensure the desired Python version is the default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

# Verify the Python version
RUN python3 --version && python --version

# Jupyter itself is retired (see DECISIONS.md/CLAUDE.md) — only IPython's
# display() machinery is still needed, for position.py/game.py's Jupyter-
# style display(HTML(...))/display(SVG(...)) calls (used when show=True,
# still relevant for the not-yet-converted Position.ipynb/Game.ipynb).
# The full `jupyter` metapackage (notebook/lab server, all its JS assets)
# is unnecessary weight for that alone.
RUN pip install ipython

# Only matplotlib is actually imported anywhere (game.py's show_sweep()) —
# pandas/numpy/seaborn were never used by any module.
RUN pip install matplotlib

# Interactive eval chart (game.py's eval_curve_plotly()): marimo's mo.ui.plotly
# needs plotly, and clicking a point there jumps the stepper to that ply.
RUN pip install plotly

RUN pip install "httpx<0.24"

RUN pip install --prefer-binary chess

RUN pip install marimo

# The drag-and-drop board widget (notebooks/board_widget.py, used by
# endgame_studies_marimo.py) is a marimo mo.ui.anywidget wrapping lichess's
# chessground JS library — anywidget is the Python/JS state-sync layer
# marimo expects for that. chessground's own files are vendored under
# notebooks/vendor/chessground/ (see VENDORED.md there), not fetched from a
# CDN at build or run time — this project stays usable with no network
# access at all, which matters since it travels.
RUN pip install anywidget

COPY --from=stockfish-build /build/src/stockfish /usr/bin/stockfish

# Build-time provenance (see build.sh/DECISIONS.md) — baked in as a plain
# file, not just build-args, since ARGs don't survive past the build into
# a running container. entrypoint.sh reads this to compare against the
# *current* source commit (passed in fresh by run.sh at container start)
# and flag if the image is stale relative to the checked-out source.
ARG BUILD_COMMIT=unknown
ARG BUILD_COMMIT_SUBJECT=unknown
ARG BUILD_EPOCH=0
RUN printf '%s\n' "$BUILD_COMMIT" "$BUILD_COMMIT_SUBJECT" "$BUILD_EPOCH" > /build_info.txt

WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Launch entrypoint.sh's marimo notebook(s) + landing page
CMD ["/entrypoint.sh"]
