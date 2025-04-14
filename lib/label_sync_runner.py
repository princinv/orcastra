#!/usr/bin/env python3
"""
Main orchestration logic for managing anchor ↔ dependent service placement in Docker Swarm.
Triggered by the label_sync entrypoint.
"""

import os
import time
import signal
import threading
import logging
from core.config_loader import load_yaml
from core.docker_client import client
from core.retry_state import retry_state
from lib.node_labels import label_anchors
from lib.retries import should_retry, record_retry, clear_retry
from lib.service_utils import get_service_node, force_update_service

# ENV
DEPENDENCIES_FILE = os.getenv("DEPENDENCIES_FILE", "/etc/swarm-orchestration/dependencies.yml")
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
RELABEL_TIME = int(os.getenv("RELABEL_TIME", "60"))
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
RESTART_DEPENDENTS = os.getenv("RESTART_DEPENDENTS", "false").lower() == "true"
DEFAULT_RETRY_INTERVALS = [2, 10, 60, 300, 900]

should_run = True

def retry_intervals_for(anchor_label, dependencies):
    value = dependencies.get(anchor_label)
    if isinstance(value, dict):
        return value.get("retry_intervals", DEFAULT_RETRY_INTERVALS)
    return DEFAULT_RETRY_INTERVALS

def should_restart(anchor_label, dependencies):
    value = dependencies.get(anchor_label)
    if isinstance(value, dict):
        return value.get("restart_dependents", RESTART_DEPENDENTS)
    return RESTART_DEPENDENTS

def update_dependents(client, dependencies):
    logging.info("[label_sync] Updating dependents for colocated anchors")

    for anchor_label, config in dependencies.items():
        dependents = config.get("services") if isinstance(config, dict) else config
        db_service = f"{STACK_NAME}_{anchor_label}"
        db_node = get_service_node(client, db_service)
        if not db_node:
            logging.warning(f"[label_sync] Anchor {db_service} is not running. Skipping.")
            continue

        for dep in dependents:
            full_dep_service = f"{STACK_NAME}_{dep}"
            retry_schedule = retry_intervals_for(anchor_label, dependencies)
            try:
                dep_node = get_service_node(client, full_dep_service)

                if not dep_node:
                    if should_retry(full_dep_service, retry_schedule):
                        logging.warning(f"❌ {full_dep_service} not running. Retrying.")
                        force_update_service(client, full_dep_service)
                    else:
                        logging.info(f"⏳ Cooldown: Skipping retry for {full_dep_service}")
                    continue

                if db_node != dep_node:
                    if should_retry(full_dep_service, retry_schedule):
                        logging.info(f"🔁 {full_dep_service} not co-located with {anchor_label}. Retrying.")
                        force_update_service(client, full_dep_service)
                    else:
                        logging.info(f"⏳ Cooldown: Skipping retry for {full_dep_service}")
                else:
                    logging.info(f"✅ {full_dep_service} already co-located with {anchor_label}")
                    if should_restart(anchor_label, dependencies):
                        logging.debug(f"[label_sync] Restart not required for {full_dep_service}")
                    clear_retry(full_dep_service)

            except Exception as e:
                logging.error(f"🔥 Error handling {full_dep_service}: {e}")
                record_retry(full_dep_service)

def main_loop():
    dependencies = load_yaml(DEPENDENCIES_FILE)
    if not dependencies:
        logging.warning("[label_sync] No dependencies found.")
        return

    logging.info("[label_sync] Running label sync main loop")
    label_anchors(client, dependencies)
    update_dependents(client, dependencies)

def event_listener():
    # Optional future implementation of Docker event-based logic
    pass

def signal_handler(signum, frame):
    logging.info("[label_sync] SIGHUP received — forcing label sync now")
    main_loop()

def run():
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, signal_handler)

    if POLLING_MODE:
        while should_run:
            main_loop()
            time.sleep(RELABEL_TIME)
    elif EVENT_MODE:
        event_listener()
