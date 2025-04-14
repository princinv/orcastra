#!/usr/bin/env python3
"""
rebalance.py
- Entrypoint for monitoring and rebalancing Swarm services based on memory.
"""

import os
import time
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from core.config_loader import load_yaml
from core.docker_client import client
from core.retry_state import retry_state
from lib.service_utils import get_service_node
from lib.service_utils import force_update_service
from lib.metrics import get_node_exporter_memory, get_docker_reported_memory, get_container_memory_usage
from lib.rebalance_decision import should_rebalance

# --- Config Paths ---
CONFIG_PATH = "/etc/swarm-orchestration/rebalance_config.yml"
DEPENDENCIES_PATH = "/etc/swarm-orchestration/dependencies.yml"
STATE_PATH = "/var/lib/swarm-orchestration/rebalance_state.json"

IGNORED_STATES = {"pending", "preparing", "assigned", "starting", "ready"}  # Do not rebalance these


def load_state():
    if Path(STATE_PATH).exists():
        with open(STATE_PATH, 'r') as f:
            return json.load(f)
    return {}


def save_state(state):
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def run_rebalance_loop(dry_run=False, debug=False):
    config = load_yaml(CONFIG_PATH)
    dependencies = load_yaml(DEPENDENCIES_PATH) or {}
    state = load_state()
    interval = int(config.get("monitor_interval_seconds", 30))
    node_map = config.get("node_map", {})
    exporter_nodes = config.get("node_exporter_nodes", {})
    services = list(config.get("services", {}).keys())

    while True:
        free_mem = {}
        all_nodes = set()

        for service in services:
            node = get_service_node(client, service, debug=debug)
            if node and node not in IGNORED_STATES:
                all_nodes.add(node)

        for node in all_nodes:
            host = node_map.get(node)
            url = exporter_nodes.get(host, {}).get("exporter_url")
            if url:
                mem = get_node_exporter_memory(url)
                if mem is not None:
                    free_mem[node] = mem

        fallback = get_docker_reported_memory(all_nodes - set(free_mem))
        free_mem.update(fallback)

        container_mem = get_container_memory_usage()

        if debug:
            print(f"[DEBUG] Memory availability: {free_mem}")
            print("[DEBUG] Container memory usage:")
            for name, mem in container_mem.items():
                print(f"  - {name}: {mem} GB")

        moved = []

        for service in services:
            current_node = get_service_node(client, service, debug=debug)

            if current_node in IGNORED_STATES:
                print(f"[SKIP] {service} task is still initializing: {current_node}")
                continue

            if not current_node:
                print(f"[WARN] {service}: No running task with valid NodeID.")
                if debug:
                    print(f"[DEBUG] Inspecting task status for {service} via 'docker service ps'...")
                    try:
                        result = subprocess.run(
                            ["docker", "service", "ps", "--no-trunc", service],
                            capture_output=True, text=True, timeout=5
                        )
                        print(result.stdout.strip())
                    except Exception as e:
                        print(f"[DEBUG] Failed to inspect service {service}: {e}")
                continue

            trigger, target = should_rebalance(
                service, current_node, free_mem,
                config, state, container_mem,
                dependencies, debug
            )
            if trigger:
                print(f"[REBALANCE] {service}: {current_node} → {target}")
                if not dry_run:
                    success = force_update_service(client, service)
                    if not success:
                        print(f"[ERROR] Failed to update service {service}.")
                state[service] = {
                    "last_moved": datetime.utcnow().isoformat(),
                    "moved_to": target
                }
                moved.append(service)
            elif debug:
                print(f"[DEBUG] {service} remains on {current_node}")

        if debug:
            print("[DEBUG] Summary of this run:")
            if moved:
                print(f"  ✅ Services rebalanced: {', '.join(moved)}")
            else:
                print("  ⏸️ No services moved this cycle.")

        save_state(state)
        time.sleep(interval)


def run():
    parser = argparse.ArgumentParser(description="Swarm Rebalancer")
    parser.add_argument("--dry-run", action="store_true", help="Print intended actions without applying")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args, _ = parser.parse_known_args()

    dry_run = args.dry_run or os.getenv("DRY_RUN", "false").lower() == "true"
    debug = args.debug or os.getenv("DEBUG", "false").lower() == "true"

    run_rebalance_loop(dry_run=dry_run, debug=debug)


if __name__ == "__main__":
    run()

