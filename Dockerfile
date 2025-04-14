FROM python:3.12-slim

# Set working directory
WORKDIR /src

# --- Environment Variables ---
# Ensure Python can locate all modular packages
ENV PYTHONPATH="/src:/src/core:/src/lib"

# --- Install OS dependencies ---
RUN apt-get update && \
    apt-get install -y iputils-ping openssh-client && \
    rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Create runtime dirs ---
RUN mkdir -p /etc/swarm-orchestration /var/lib/swarm-orchestration /var/log/swarm-orchestration

# --- Copy project structure ---
COPY src/ /src/
COPY config/ /etc/swarm-orchestration/
COPY scripts/ /usr/local/bin/

# --- Default entrypoint ---
    ENTRYPOINT ["python"]
    CMD ["/src/supervisor.py"]
    