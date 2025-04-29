#!/usr/bin/env python3
"""
label_sync.py
- Entrypoint script for Docker Swarm label orchestration.
- Triggers anchor label application and dependent service updates.
- Can be called by main supervisor or manually via CLI (e.g., entrypoint.py).
"""

import asyncio
from core.config_loader import load_yaml, preview_yaml
from lib.sync import label_manager

SWARM_FILE = "/etc/swarm-orchestration/swarm.yml"

# Preview loaded config for clarity at startup
preview_yaml(SWARM_FILE, name="swarm.yml")

async def run():
    """
    Run the label manager orchestration loop asynchronously.
    """
    config = load_yaml(SWARM_FILE)
    dependencies = config.get("dependencies", {})
    await label_manager.run(dependencies)

if __name__ == "__main__":
    asyncio.run(run())
