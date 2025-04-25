#!/usr/bin/env python3
"""
label_sync.py
- Entrypoint script for Docker Swarm label orchestration.
- Triggers anchor label application and dependent service updates.
- Can be called by main supervisor or manually via CLI (e.g., entrypoint.py).
"""

import asyncio
from core.config import DEPENDENCIES_FILE
from core.config_loader import preview_yaml
from lib.sync import label_manager

# Preview loaded config for clarity at startup
preview_yaml(DEPENDENCIES_FILE, name="dependencies.yml")

async def run():
    """
    Run the label manager orchestration loop asynchronously.
    """
    await label_manager.run()

if __name__ == "__main__":
    asyncio.run(run())
