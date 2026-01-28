# Set Version
ARG UBUNTU_VERSION=24.04
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
RUN pip install pandas numpy matplotlib seaborn
RUN pip install django
RUN pip install prettytable
RUN pip install cryptography

RUN pip install "httpx<0.24"

RUN pip install --prefer-binary chess

COPY stockfish-ubuntu-x86-64 /usr/bin/stockfish

WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start Jupyter Notebook
CMD ["/entrypoint.sh"]
