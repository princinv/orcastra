#!/usr/bin/env python3
"""
log_rotate.py
- Periodically runs logrotate inside swarm-orch container.
- Centralized, modular log management for multiple hosts/mounts.
- Logrotate configuration mounted externally at /etc/swarm-orchestration/logrotate.d/.
- Safe: tolerates missing log paths and missing configuration.
- Does not crash if mountpoints are absent.
"""

import asyncio
import logging
import subprocess
import os

# --- Configuration ---
LOGROTATE_CONF_DIR = "/etc/swarm-orchestration/logrotate.d"
LOGROTATE_INTERVAL_SECONDS = 6 * 3600  # every 6 hours

async def run():
    while True:
        logging.info("[logrotate] Checking for logrotate configurations...")

        if not os.path.isdir(LOGROTATE_CONF_DIR):
            logging.warning(f"[logrotate] Config directory {LOGROTATE_CONF_DIR} not found. Skipping run.")
            await asyncio.sleep(LOGROTATE_INTERVAL_SECONDS)
            continue

        configs = [os.path.join(LOGROTATE_CONF_DIR, f) for f in os.listdir(LOGROTATE_CONF_DIR) if f.endswith(".conf")]

        if not configs:
            logging.info("[logrotate] No logrotate config files found. Nothing to rotate.")
            await asyncio.sleep(LOGROTATE_INTERVAL_SECONDS)
            continue

        for config in configs:
            logging.info(f"[logrotate] Running logrotate with config {config}")
            try:
                subprocess.run(["logrotate", config], check=True)
                logging.info(f"[logrotate] Logrotate completed successfully for {config}.")
            except subprocess.CalledProcessError as e:
                logging.error(f"[logrotate] Logrotate failed for {config}: {e}")

        await asyncio.sleep(LOGROTATE_INTERVAL_SECONDS)
