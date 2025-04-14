# ---------- Stage 1: Build and Install Dependencies ----------
    FROM python:3.12-slim AS builder

    WORKDIR /build
    
    # System dependencies for pip and docker CLI
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
        apt-get update && apt-get install -y docker-ce-cli && \
        rm -rf /var/lib/apt/lists/*
    
    # Install Python dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # ---------- Stage 2: Final Runtime Image ----------
    FROM python:3.12-slim AS runtime
    
    WORKDIR /src
    ENV PYTHONPATH="/src:/src/core:/src/lib"
    
    # Copy runtime-only dependencies from builder
    COPY --from=builder /usr/bin/docker /usr/bin/docker
    COPY --from=builder /usr/bin/ssh /usr/bin/ssh
    COPY --from=builder /usr/bin/ping /usr/bin/ping
    COPY --from=builder /usr/lib /usr/lib
    COPY --from=builder /lib /lib
    COPY --from=builder /etc/ssl /etc/ssl
    COPY --from=builder /etc/ssh /etc/ssh
    COPY --from=builder /etc/ca-certificates.conf /etc/ca-certificates.conf
    
    # Python environment
    COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
    COPY --from=builder /usr/local/bin /usr/local/bin
    COPY --from=builder /usr/local/include /usr/local/include
    COPY --from=builder /usr/local/lib /usr/local/lib
    
    # Create runtime directories
    RUN mkdir -p /etc/swarm-orchestration /var/lib/swarm-orchestration /var/log/swarm-orchestration
    
    # Copy source code and configs
    COPY src/ /src/
    COPY config/ /etc/swarm-orchestration/
    COPY scripts/ /usr/local/bin/
    
    # Entrypoint
    ENTRYPOINT ["python"]
    CMD ["/src/supervisor.py"]
    