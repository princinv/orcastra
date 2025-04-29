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

from core.docker_client import client
from core.retry_state import retry_state, should_retry, record_retry, clear_retry
from lib.common.service_helpers import force_update_service
from lib.sync.label_utils import label_anchors
from lib.common.docker_helpers import get_task_state
from lib.common.task_diagnostics import log_task_status
from lib.sync.label_utils import get_anchor_state_for_failover

# --- Metrics ---
anchor_updates_total = 0
dependent_updates_total = 0
dependent_force_update_failures_total = 0
anchor_sync_errors_total = 0
anchor_sync_last_duration_seconds = 0.0

# --- Task State Groups ---
IGNORED_STATES = {"new", "allocated", "pending"}
WAITING_STATES = {"assigned", "accepted", "preparing", "ready", "starting"}
SUCCESS_STATES = {"running", "complete"}
FAILURE_STATES = {"failed", "rejected", "remove", "orphaned"}
TERMINAL_STATES = SUCCESS_STATES | FAILURE_STATES | {"shutdown"}

# --- Config via Environment Variables ---
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
RELABEL_TIME = int(os.getenv("RELABEL_TIME", "60"))
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
RESTART_DEPENDENTS = os.getenv("RESTART_DEPENDENTS", "false").lower() == "true"
DEFAULT_RETRY_INTERVALS = [2, 10, 60, 300, 900]
MAX_MISMATCH_DURATION = int(os.getenv("MAX_MISMATCH_DURATION", "600"))

should_run = True
mismatch_timestamps = {}
missing_anchors = {}

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
    global dependent_updates_total
    logging.info("[label_sync] Updating dependents strictly based on anchor status and configured cooldowns.")

    for anchor_label, config in dependencies.items():
        dependents = config.get("services") if isinstance(config, dict) else config
        anchor_service = f"{STACK_NAME}_{anchor_label}"
        retry_intervals = retry_intervals_for(anchor_label, dependencies)

        anchor_state, anchor_node = get_anchor_state_for_failover(anchor_service, debug=True)

        if anchor_state in WAITING_STATES:
            logging.info(f"[label_sync] Anchor {anchor_service} initializing (state={anchor_state}). Waiting, no restarts yet.")
            continue

        if anchor_state in FAILURE_STATES or anchor_node is None:
            logging.warning(f"[label_sync] Anchor {anchor_service} failed (state={anchor_state}). Considering restart per cooldown.")

            if should_retry(anchor_service, retry_intervals):
                logging.warning(f"[label_sync] Restarting anchor {anchor_service} per cooldown settings.")
                record_retry(anchor_service)
                force_update_service(client, anchor_service)
            else:
                logging.info(f"[label_sync] Anchor {anchor_service} in cooldown. Skipping anchor restart.")

            restart_dependents = config.get('restart_dependents', False)
            if restart_dependents:
                for dep in dependents:
                    dep_service = f"{STACK_NAME}_{dep}"
                    if should_retry(dep_service, retry_intervals):
                        logging.warning(f"[label_sync] Restarting dependent {dep_service} due to anchor failure per cooldown.")
                        record_retry(dep_service)
                        force_update_service(client, dep_service)
                        dependent_updates_total += 1
                    else:
                        logging.debug(f"[label_sync] Dependent {dep_service} cooldown active, skipping restart.")
            continue

        if anchor_state == "running":
            for dep in dependents:
                dep_service = f"{STACK_NAME}_{dep}"
                task_state, dep_node = get_task_state(dep_service, debug=True)

                if not dep_node:
                    logging.warning(f"[label_sync] {dep_service} has no valid NodeID, skipping temporarily.")
                    continue

                if task_state in IGNORED_STATES | WAITING_STATES:
                    logging.debug(f"[label_sync] {dep_service} is initializing (state={task_state}), skipping.")
                    continue

                if dep_node == anchor_node:
                    logging.debug(f"[label_sync] ✅ {dep_service} correctly colocated with anchor {anchor_label}.")
                    clear_retry(dep_service)
                    mismatch_timestamps.pop(dep_service, None)
                    continue

                now = datetime.utcnow()
                first_mismatch = mismatch_timestamps.get(dep_service, now)
                mismatch_timestamps[dep_service] = first_mismatch
                mismatch_duration = (now - first_mismatch).total_seconds()

                logging.info(f"[label_sync] {dep_service} mismatch detected for {int(mismatch_duration)}s (should follow {anchor_node}).")

                if mismatch_duration >= MAX_MISMATCH_DURATION:
                    logging.warning(f"[label_sync] {dep_service} mismatch duration exceeded. Skipping further updates for now.")
                    continue

                if should_retry(dep_service, retry_intervals):
                    logging.info(f"[label_sync] Restarting {dep_service} due to mismatch per cooldown.")
                    record_retry(dep_service)
                    force_update_service(client, dep_service)
                    dependent_updates_total += 1
                else:
                    logging.debug(f"[label_sync] {dep_service} cooldown active, skipping restart.")

    logging.info("[label_sync] Dependent services updated respecting anchor-specific cooldown rules.")

# --- Entrypoint Loop ---
def main_loop(dependencies):
    global anchor_updates_total, anchor_sync_errors_total, anchor_sync_last_duration_seconds

    start_time = time.time()
    try:
        if not dependencies:
            logging.warning("[label_sync] No dependencies found.")
            return

        logging.info("[label_sync] Running label sync main loop")
        label_anchors(list(dependencies.keys()), STACK_NAME, debug=True)
        anchor_updates_total += 1
        update_dependents(client, dependencies)

    except Exception as e:
        logging.error(f"[label_sync] Unexpected error during label sync: {e}")
        anchor_sync_errors_total += 1

    finally:
        anchor_sync_last_duration_seconds = time.time() - start_time

# --- Signal Support for SIGHUP Rerun ---
def signal_handler(signum, frame):
    logging.info("[label_sync] SIGHUP received — forcing label sync now")

# --- Entrypoint Dispatcher ---
def run(dependencies):
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, lambda s, f: main_loop(dependencies))

    if POLLING_MODE:
        while should_run:
            main_loop(dependencies)
            time.sleep(RELABEL_TIME)
    elif EVENT_MODE:
        logging.info("[label_sync] Event-driven mode is not implemented yet.")
