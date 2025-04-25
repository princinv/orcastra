"""
docker_client.py
- Provides a shared, preconfigured Docker SDK client instance for all modules.
- Exposes Docker version info and handles initialization errors gracefully.
"""

import docker
from docker import from_env

try:
    client = from_env()
    DOCKER_SDK_VERSION = tuple(map(int, docker.__version__.split(".")))
except Exception:
    client = None
    DOCKER_SDK_VERSION = (0, 0, 0)  # fallback if docker SDK is not usable
