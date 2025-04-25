#!/usr/bin/env python3
"""
logrotate_runner.py
- Periodically runs logrotate inside swarm-orch container.
- Centralized log rotation for mounted host logs.
"""

import asyncio
import logging
import subprocess

LOGROTATE_CONF_PATH = "/etc/logrotate.d/swarm-logs"
LOGROTATE_INTERVAL_SECONDS = 6 * 3600  # every 6 hours

async def run():
    while True:
        logging.info("[logrotate] Running logrotate...")
        try:
            subprocess.run(["logrotate", LOGROTATE_CONF_PATH], check=True)
            logging.info("[logrotate] Logrotate completed successfully.")
        except Exception as e:
            logging.error(f"[logrotate] Logrotate failed: {e}")
        await asyncio.sleep(LOGROTATE_INTERVAL_SECONDS)
