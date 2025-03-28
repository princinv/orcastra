FROM python:3.12-slim

WORKDIR /app

# --- Install dependencies ---
RUN apt-get update && \
    apt-get install -y iputils-ping openssh-client && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir docker pyyaml requests

# --- Create needed dirs ---
RUN mkdir -p /etc/swarm-orchestration /var/lib/swarm-orchestration /var/log/swarm-orchestration

# --- Copy project structure ---
COPY app/ /app/
COPY utils/ /app/utils/
COPY config/ /etc/swarm-orchestration/
COPY commands/ /app/commands/


# --- Default CMD (override with docker-compose or ENV) ---
CMD ["python", "/app/label_dependencies.py"]
