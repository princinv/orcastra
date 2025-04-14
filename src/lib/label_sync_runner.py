#!/usr/bin/env python3
"""
label_sync_runner.py
- Main orchestration logic for managing anchor ↔ dependent service placement in Docker Swarm.
- Triggered by the label_sync entrypoint.
"""

import os
import time
import signal
import threading
import logging
from datetime import datetime

from core.config_loader import load_yaml
from core.docker_client import client
from core.retry_state import retry_state
from lib.node_labels import label_anchors
from lib.retries import should_retry, record_retry, clear_retry
from lib.docker_helpers import get_service_node
from lib.service_utils import force_update_service
from lib.task_diagnostics import log_task_status

# --- Environment Variables / Defaults ---
DEPENDENCIES_FILE = os.getenv("DEPENDENCIES_FILE", "/etc/swarm-orchestration/dependencies.yml")
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
RELABEL_TIME = int(os.getenv("RELABEL_TIME", "60"))
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
RESTART_DEPENDENTS = os.getenv("RESTART_DEPENDENTS", "false").lower() == "true"
DEFAULT_RETRY_INTERVALS = [2, 10, 60, 300, 900]
MAX_MISMATCH_DURATION = int(os.getenv("MAX_MISMATCH_DURATION", "600"))  # seconds

should_run = True
mismatch_timestamps = {}  # Track how long a service has been mismatched

# --- Config-Driven Overrides ---
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

# --- Dependent Coordination Logic ---
def update_dependents(client, dependencies):
    logging.info("[label_sync] Updating dependents for colocated anchors")
    service_node_map = {}

    for anchor_label, config in dependencies.items():
        dependents = config.get("services") if isinstance(config, dict) else config
        db_service = f"{STACK_NAME}_{anchor_label}"

        # Cache anchor node
        db_node = service_node_map.get(db_service)
        if db_node is None:
            db_node = get_service_node(db_service, debug=True)
            service_node_map[db_service] = db_node

        if not db_node or db_node == "starting":
            logging.info(f"[label_sync] Anchor {db_service} is still initializing or not running. Skipping.")
            log_task_status(db_service, context="anchor")
            continue

        for dep in dependents:
            full_dep_service = f"{STACK_NAME}_{dep}"
            retry_schedule = retry_intervals_for(anchor_label, dependencies)

            # Cache dependent node
            dep_node = service_node_map.get(full_dep_service)
            if dep_node is None:
                dep_node = get_service_node(full_dep_service, debug=True)
                service_node_map[full_dep_service] = dep_node

            now = datetime.utcnow()

            try:
                if not dep_node or dep_node == "starting":
                    logging.info(f"⏳ {full_dep_service} is still initializing or pending scheduling. Skipping update.")
                    continue

                if db_node != dep_node:
                    first_mismatch = mismatch_timestamps.get(full_dep_service, now)
                    mismatch_timestamps[full_dep_service] = first_mismatch

                    mismatch_duration = (now - first_mismatch).total_seconds()
                    logging.info(f"🔁 {full_dep_service} is on {dep_node}, expected {db_node}. Mismatch for {int(mismatch_duration)}s")

                    if mismatch_duration >= MAX_MISMATCH_DURATION:
                        logging.warning(f"⛔ {full_dep_service} has exceeded max mismatch duration. Skipping update.")
                        continue

                    if should_retry(full_dep_service, retry_schedule):
                        logging.info(f"[label_sync] Forcing update of {full_dep_service} after mismatch")
                        force_update_service(client, full_dep_service)
                    else:
                        logging.info(f"⏳ Cooldown: Skipping retry for {full_dep_service}")
                    continue

                logging.info(f"✅ {full_dep_service} already co-located with {anchor_label}")
                clear_retry(full_dep_service)
                mismatch_timestamps.pop(full_dep_service, None)

            except Exception as e:
                logging.error(f"🔥 Error handling {full_dep_service}: {e}")
                record_retry(full_dep_service)

# --- Main Loop: Label Anchors + Update Dependents ---
def main_loop():
    dependencies = load_yaml(DEPENDENCIES_FILE)
    if not dependencies:
        logging.warning("[label_sync] No dependencies found.")
        return

    logging.info("[label_sync] Running label sync main loop")
    label_anchors(list(dependencies.keys()), STACK_NAME, debug=True)
    update_dependents(client, dependencies)

# --- Placeholder for Event-Driven Mode ---
def event_listener():
    logging.info("[label_sync] Event listener mode not yet implemented.")
    pass

# --- Signal Support (e.g. docker kill -s HUP) ---
def signal_handler(signum, frame):
    logging.info("[label_sync] SIGHUP received — forcing label sync now")
    main_loop()

# --- Entrypoint ---
def run():
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, signal_handler)

    if POLLING_MODE:
        while should_run:
            main_loop()
            time.sleep(RELABEL_TIME)
    elif EVENT_MODE:
        event_listener()

