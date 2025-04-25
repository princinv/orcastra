FROM python:3.12-slim

# --- Set working directory ---
WORKDIR /src

# --- Environment Variables ---
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/src:/src/lib:/src/runner:/src/core"

# --- Install OS dependencies ---
    RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        docker.io \
        iputils-ping \
        openssh-client && \
    rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
COPY src/requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

# --- Create runtime directories ---
RUN mkdir -p /etc/swarm-orchestration /var/lib/swarm-orchestration /var/log/swarm-orchestration

# --- Copy project structure ---
COPY src/ /src/
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
