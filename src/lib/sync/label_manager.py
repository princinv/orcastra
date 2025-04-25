#!/usr/bin/env python3
"""
label_manager.py
- Main orchestration logic for label synchronization and dependent service updates in Docker Swarm.
- Anchors (e.g. databases) are located and labeled, and dependents are updated to co-locate.
- Can be triggered manually or run continuously via main supervisor.
"""

import os
import time
import signal
import threading
import logging
from datetime import datetime

from core.config_loader import load_yaml
from core.docker_client import client
from core.retry_state import retry_state, should_retry, record_retry, clear_retry
from lib.common.service_helpers import force_update_service
from lib.sync.label_utils import label_anchors
from lib.common.docker_helpers import get_task_state
from lib.common.task_diagnostics import log_task_status

# --- Task State Groups ---
IGNORED_STATES = {"new", "allocated", "pending"}
WAITING_STATES = {"assigned", "accepted", "preparing", "ready", "starting"}
SUCCESS_STATES = {"running", "complete"}
FAILURE_STATES = {"failed", "rejected", "remove", "orphaned"}
TERMINAL_STATES = SUCCESS_STATES | FAILURE_STATES | {"shutdown"}

# --- Config via Environment Variables ---
DEPENDENCIES_FILE = os.getenv("DEPENDENCIES_FILE", "/etc/swarm-orchestration/dependencies.yml")
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
RELABEL_TIME = int(os.getenv("RELABEL_TIME", "60"))
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
RESTART_DEPENDENTS = os.getenv("RESTART_DEPENDENTS", "false").lower() == "true"
DEFAULT_RETRY_INTERVALS = [2, 10, 60, 300, 900]
MAX_MISMATCH_DURATION = int(os.getenv("MAX_MISMATCH_DURATION", "600"))

should_run = True
mismatch_timestamps = {}

# --- Retry & Restart Configuration ---
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

# --- Core Orchestration Logic ---
def update_dependents(client, dependencies):
    logging.info("[label_sync] Updating dependents for colocated anchors")
    service_node_map = {}

    for anchor_label, config in dependencies.items():
        dependents = config.get("services") if isinstance(config, dict) else config
        db_service = f"{STACK_NAME}_{anchor_label}"

        # Resolve and cache anchor node location
        db_node = service_node_map.get(db_service)
        if db_node is None:
            _, db_node = get_task_state(db_service, debug=True)
            service_node_map[db_service] = db_node

        if not db_node:
            logging.warning(f"[label_sync] Anchor {db_service} is not running. Skipping.")
            log_task_status(db_service, context="anchor")
            continue

        for dep in dependents:
            full_dep_service = f"{STACK_NAME}_{dep}"
            retry_schedule = retry_intervals_for(anchor_label, dependencies)
            now = datetime.utcnow()

            task_state, dep_node = get_task_state(full_dep_service, debug=True)

            if task_state in IGNORED_STATES | WAITING_STATES:
                logging.info(f"⏳ {full_dep_service} is still initializing (state={task_state}). Skipping update.")
                continue

            if task_state in FAILURE_STATES:
                if should_retry(full_dep_service, retry_schedule):
                    logging.warning(f"❌ {full_dep_service} failed (state={task_state}). Retrying.")
                    force_update_service(client, full_dep_service)
                else:
                    logging.info(f"⏳ Cooldown: Skipping retry for {full_dep_service}")
                continue

            if not dep_node:
                logging.warning(f"[label_sync] {full_dep_service} has no resolved NodeID. Skipping.")
                continue

            if db_node != dep_node:
                first_mismatch = mismatch_timestamps.get(full_dep_service, now)
                mismatch_timestamps[full_dep_service] = first_mismatch
                mismatch_duration = (now - first_mismatch).total_seconds()
                logging.info(f"🔁 {full_dep_service} is not co-located with {anchor_label}. Mismatch for {int(mismatch_duration)}s")

                if mismatch_duration >= MAX_MISMATCH_DURATION:
                    logging.warning(f"⛔ {full_dep_service} has exceeded max mismatch duration. Skipping update.")
                    continue

                if should_retry(full_dep_service, retry_schedule):
                    logging.info(f"[label_sync] Forcing update of {full_dep_service} after mismatch")
                    force_update_service(client, full_dep_service)
                else:
                    logging.info(f"⏳ Cooldown: Skipping retry for {full_dep_service}")
            else:
                logging.info(f"✅ {full_dep_service} already co-located with {anchor_label}")
                clear_retry(full_dep_service)
                mismatch_timestamps.pop(full_dep_service, None)

# --- Entrypoint Loop ---
def main_loop():
    dependencies = load_yaml(DEPENDENCIES_FILE)
    if not dependencies:
        logging.warning("[label_sync] No dependencies found.")
        return

    logging.info("[label_sync] Running label sync main loop")
    label_anchors(list(dependencies.keys()), STACK_NAME, debug=True)
    update_dependents(client, dependencies)

# --- Signal Support for SIGHUP Rerun ---
def signal_handler(signum, frame):
    logging.info("[label_sync] SIGHUP received — forcing label sync now")
    main_loop()

# --- Entrypoint Dispatcher ---
def run():
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, signal_handler)

    if POLLING_MODE:
        while should_run:
            main_loop()
            time.sleep(RELABEL_TIME)
    elif EVENT_MODE:
        logging.info("[label_sync] Event-driven mode is not implemented yet.")
