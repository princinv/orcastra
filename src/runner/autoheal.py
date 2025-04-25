#!/usr/bin/env python3
"""
autoheal.py
- Monitors Swarm tasks for unhealthy containers.
- Force-updates services when tasks become unhealthy to trigger rescheduling.
- No enable/disable toggle; always active as part of swarm-orch.
- Adheres to swarm-orch project structure and best practices.
- Exposes basic metrics for Prometheus.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from core.docker_client import client

# --- Autoheal Metrics ---
autoheal_attempts_total = 0
autoheal_success_total = 0
autoheal_failures_total = 0

# --- Configuration Defaults ---
AUTOHEAL_CHECK_INTERVAL = int(os.getenv("AUTOHEAL_CHECK_INTERVAL", 30))  # seconds
AUTOHEAL_GRACE_PERIOD = int(os.getenv("AUTOHEAL_GRACE_PERIOD", 60))      # seconds unhealthy before action

async def run():
    global autoheal_attempts_total, autoheal_success_total, autoheal_failures_total

    while True:
        logging.info("[autoheal] Scanning services for unhealthy containers...")

        try:
            services = client.services.list()
            now = datetime.utcnow()

            for service in services:
                service_name = service.attrs.get("Spec", {}).get("Name", "unknown")

                try:
                    tasks = service.tasks(filters={"desired-state": "running"})

                    for task in tasks:
                        status = task.get("Status", {})
                        state = status.get("State", "")
                        container_status = status.get("ContainerStatus", {})
                        health = container_status.get("Health", {})
                        health_status = health.get("Status", "")
                        started_at = status.get("Timestamp")

                        if health_status.lower() == "unhealthy":
                            # Respect grace period
                            task_started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                            unhealthy_duration = (now - task_started).total_seconds()

                            if unhealthy_duration >= AUTOHEAL_GRACE_PERIOD:
                                autoheal_attempts_total += 1
                                logging.warning(f"[autoheal] {service_name} has unhealthy container. Attempting recovery...")
                                try:
                                    service.update(force_update=True)
                                    autoheal_success_total += 1
                                    logging.info(f"[autoheal] Successfully triggered update for {service_name}.")
                                except Exception as e:
                                    autoheal_failures_total += 1
                                    logging.error(f"[autoheal] Failed to heal {service_name}: {e}")

                except Exception as inner_e:
                    logging.error(f"[autoheal] Failed to inspect service {service_name}: {inner_e}")

        except Exception as outer_e:
            logging.error(f"[autoheal] Top-level autoheal scan failed: {outer_e}")

        await asyncio.sleep(AUTOHEAL_CHECK_INTERVAL)
