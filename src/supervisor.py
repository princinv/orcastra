#!/usr/bin/env python3
"""
supervisor.py
- Entrypoint for the swarm-orch container.
- Launches all orchestrator subsystems concurrently:
    • label_sync     — maintains anchor ↔ dependent placement
    • bootstrap_swarm — maintains Swarm cluster + node labels
    • rebalance       — memory-aware service rebalancing
"""
import time
import threading
import sys
import os

import logging

debug = os.getenv("DEBUG", "false").lower() == "true"
logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)


print("[supervisor] Sleeping 10s to ensure mounts are ready...")
time.sleep(10)

# --- Extend sys.path to support src layout ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "core")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "lib")))

print("[supervisor] sys.path:", sys.path)

# --- Load persistent retry state before orchestrator threads start ---
from lib.retries import load_retry_state
load_retry_state()

# --- Import all orchestrator modules ---
import bootstrap_swarm
import label_sync_runner as label_sync
import rebalance

# --- Thread Wrappers with Crash Logging ---
def run_label_sync():
    try:
        label_sync.run()
    except Exception as e:
        print(f"[supervisor] label_sync thread crashed: {e}")

def run_bootstrap():
    try:
        bootstrap_swarm.run()
    except Exception as e:
        print(f"[supervisor] bootstrap thread crashed: {e}")

def run_rebalance():
    try:
        rebalance.run()
    except Exception as e:
        print(f"[supervisor] rebalance thread crashed: {e}")

# --- Start Threads ---
threads = [
    threading.Thread(target=run_label_sync, name="label_sync"),
    threading.Thread(target=run_bootstrap, name="bootstrap_swarm"),
    threading.Thread(target=run_rebalance, name="rebalance"),
]

for t in threads:
    t.start()

for t in threads:
    t.join()
