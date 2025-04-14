#!/usr/bin/env python3
"""
rebalance.py
- Entrypoint for monitoring and rebalancing Swarm services based on memory.
"""
import os
import time
import json
from datetime import datetime
from pathlib import Path
from core.config_loader import load_yaml
from lib.service_utils import get_service_node, force_update_service
from lib.metrics import get_node_exporter_memory, get_docker_reported_memory, get_container_memory_usage

CONFIG_PATH = "/etc/swarm-orchestration/rebalance_config.yml"
DEPENDENCIES_PATH = "/etc/swarm-orchestration/dependencies.yml"
STATE_PATH = "/var/lib/swarm-orchestration/rebalance_state.json"

def run_rebalance_loop():
    config = load_yaml(CONFIG_PATH)
    dependencies = load_yaml(DEPENDENCIES_PATH) or {}
    state = load_state()
    interval = int(config.get("monitor_interval_seconds", 30))
    node_map = config.get("node_map", {})
    exporter_nodes = config.get("node_exporter_nodes", {})
    services = list(config.get("services", {}).keys())

    debug = os.getenv("DEBUG", "false").lower() == "true"
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    while True:
        free_mem = {}
        all_nodes = set()
        for service in services:
            node = get_service_node(service)
            if node:
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
        moved = []

        for service in services:
            current_node = get_service_node(service)
            if not current_node:
                continue
            trigger, target = should_rebalance(service, current_node, free_mem, config, state, container_mem, dependencies, debug)
            if trigger:
                print(f"[REBALANCE] {service}: {current_node} → {target}")
                if not dry_run:
                    force_update_service(None, service)  # You can add the client if needed
                state[service] = {
                    "last_moved": datetime.utcnow().isoformat(),
                    "moved_to": target
                }
                moved.append(service)
            elif debug:
                print(f"[DEBUG] {service} remains on {current_node}")

        if debug:
            print(f"[DEBUG] Rebalance summary — moved: {moved or 'none'}")

        save_state(state)
        time.sleep(interval)

def load_state():
    if Path(STATE_PATH).exists():
        with open(STATE_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)

def run():
    run_rebalance_loop()
