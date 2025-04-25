#!/usr/bin/env python3
"""
healthcheck.py
- Basic healthcheck script for Docker HEALTHCHECK.
- Returns exit code 0 if the service is healthy, 1 if not.
- Currently checks for existence of the swarm-orchestration log file.
"""

import sys
from pathlib import Path

def main():
    # Basic file existence check
    log_file = Path("/var/log/swarm-orchestration/swarm-labels.log")

    if log_file.exists():
        sys.exit(0)  # Healthy
    else:
        print("❌ Healthcheck failed: Log file missing or container not initialized")
        sys.exit(1)  # Unhealthy

if __name__ == "__main__":
    main()
