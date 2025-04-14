# ---------- Stage 1: Build and Install Dependencies ----------
    FROM python:3.12-slim AS builder

    WORKDIR /build
    
    # Install build tools and Docker CLI (used by swarm-orch scripts)
    RUN apt-get update && \
        apt-get install -y --no-install-recommends \
            build-essential \
            iputils-ping \
            openssh-client \
            curl \
            gnupg \
            ca-certificates \
            lsb-release && \
        curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
        apt-get update && \
        apt-get install -y --no-install-recommends docker-ce-cli && \
        rm -rf /var/lib/apt/lists/*
    
    # Install Python dependencies into default /usr/local/ path
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # ---------- Stage 2: Final Runtime Image ----------
    FROM python:3.12-slim AS runtime
    
    WORKDIR /src
    
    # Ensure Python modules and local source code are available
    ENV PYTHONPATH="/src:/src/core:/src/lib"
    
    # Copy CLI tools needed at runtime
    COPY --from=builder /usr/bin/docker /usr/bin/docker
    COPY --from=builder /usr/bin/ssh /usr/bin/ssh
    COPY --from=builder /usr/bin/ping /usr/bin/ping
    
    # Copy runtime-installed Python dependencies
    COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
    COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
    COPY --from=builder /usr/local/bin /usr/local/bin
    
    # Create runtime directories
    RUN mkdir -p /etc/swarm-orchestration /var/lib/swarm-orchestration /var/log/swarm-orchestration
    
    # Copy orchestrator code and configs
    COPY src/ /src/
    COPY config/ /etc/swarm-orchestration/
    COPY scripts/ /usr/local/bin/
    
    # Entrypoint for Swarm-Orch service
    ENTRYPOINT ["python"]
    CMD ["/src/supervisor.py"]
    