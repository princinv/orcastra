"""
retries.py
- Central logic to record retry failures and determine if a retry is allowed.
- Includes disk persistence and retry attempt logging.
"""

import os
import time
import json
import logging
from collections import defaultdict
from pathlib import Path

# --- Retry Config ---
RETRY_STATE_PATH = os.getenv("RETRY_STATE_PATH", "/var/lib/swarm-orchestration/retry_state.json")
retry_state = defaultdict(lambda: {"failures": 0, "last_attempt": 0})

# --- Load from Disk (if exists) ---
def load_retry_state():
    if Path(RETRY_STATE_PATH).exists():
        try:
            with open(RETRY_STATE_PATH, "r") as f:
                data = json.load(f)
                for service, state in data.items():
                    retry_state[service] = state
            logging.info(f"[retries] Loaded retry state from {RETRY_STATE_PATH}")
        except Exception as e:
            logging.warning(f"[retries] Failed to load retry state: {e}")

# --- Save to Disk ---
def save_retry_state():
    try:
        Path(RETRY_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(RETRY_STATE_PATH, "w") as f:
            json.dump(retry_state, f, indent=2)
    except Exception as e:
        logging.warning(f"[retries] Failed to save retry state: {e}")

def should_retry(service_name, retry_intervals):
    now = time.time()
    state = retry_state[service_name]
    failures = state["failures"]
    last = state["last_attempt"]
    interval = retry_intervals[min(failures, len(retry_intervals) - 1)]
    return now - last >= interval

def record_retry(service_name):
    retry_state[service_name]["failures"] += 1
    retry_state[service_name]["last_attempt"] = time.time()
    logging.warning(f"[retries] Retry recorded for {service_name}: {retry_state[service_name]}")
    save_retry_state()

def clear_retry(service_name):
    if service_name in retry_state:
        logging.info(f"[retries] Cleared retry state for {service_name}")
        del retry_state[service_name]
        save_retry_state()
