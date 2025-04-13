FROM python:3.12-slim

# Set working directory
WORKDIR /app

# --- Environment Variables ---
# Ensure Python can locate all modular packages
ENV PYTHONPATH="/app:/app/core:/app/lib"

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
COPY app/ /app/
COPY core/ /app/core/
COPY lib/ /app/lib/
COPY config/ /etc/swarm-orchestration/

# --- Default entrypoint ---
CMD ["sh", "-c", "exec python /app/supervisor.py"]
