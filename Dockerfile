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

RUN pip install jupyter

# The "Restart Kernel and Run All Cells" confirmation dialog's "Do not ask
# me again" checkbox only sets an in-memory flag on the browser tab's
# session object — it's never persisted, so it reappears on every page
# reload. This settings override is the actual persistent switch for it;
# lives under a system-wide config path (not $HOME) since /home/crun is
# re-created fresh by entrypoint.sh on every container start.
RUN mkdir -p /usr/local/etc/jupyter/labconfig && \
    printf '%s\n' \
        '{' \
        '  "@jupyterlab/apputils-extension:sessionDialogs": {' \
        '    "skipKernelRestartDialog": true' \
        '  }' \
        '}' \
        > /usr/local/etc/jupyter/labconfig/overrides.json

RUN pip install pandas numpy matplotlib seaborn
RUN pip install django
RUN pip install prettytable
RUN pip install cryptography

RUN pip install "httpx<0.24"

RUN pip install --prefer-binary chess

RUN pip install marimo

COPY --from=stockfish-build /build/src/stockfish /usr/bin/stockfish

WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start Jupyter Notebook
CMD ["/entrypoint.sh"]
