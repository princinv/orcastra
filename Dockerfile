FROM python:3.12-slim

# --- Set working directory ---
WORKDIR /src

# --- Environment Variables ---
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/src:/src/lib:/src/runner:/src/core"
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV DEBIAN_FRONTEND=noninteractive

# --- Install OS dependencies in smaller layers (safe, minimal) ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    openssh-client \
    logrotate \
    docker.io \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Preconfigure pip and Python ---
RUN python -m pip install --upgrade pip setuptools wheel

# --- Install Python dependencies ---
COPY src/requirements.txt /tmp/requirements.txt

# Hardened pip install: auto retry if network glitches
RUN bash -c 'for i in {1..3}; do pip install --no-cache-dir --verbose -r /tmp/requirements.txt && break || sleep 5; done'

# --- Create runtime directories ---
RUN mkdir -p \
    /etc/swarm-orchestration \
    /var/lib/swarm-orchestration \
    /var/log/swarm-orchestration \
    /modcache

# --- Copy project structure (split for layers) ---
COPY src/main.py /src/main.py
COPY src/core/ /src/core/
COPY src/cli/ /src/cli/
COPY src/commands/ /src/commands/
COPY src/lib/ /src/lib/
COPY src/runner/ /src/runner/
COPY src/utils/ /src/utils/
COPY config/ /etc/swarm-orchestration/
COPY scripts/ /usr/local/bin/
COPY src/utils/healthcheck.py /usr/local/bin/check_health.py

# --- Configure container healthcheck ---
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/usr/local/bin/check_health.py"]

# --- Optional: switch to non-root user ---
# RUN useradd -m swarmuser && chown -R swarmuser /src
# USER swarmuser

# --- Default container entrypoint ---
CMD ["python", "/src/main.py"]
