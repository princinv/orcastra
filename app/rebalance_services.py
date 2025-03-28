# rebalance_services.py

import time
import yaml
import json
import requests
import subprocess
import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

# --- Config Paths ---
CONFIG_PATH = "/etc/swarm-orchestration/rebalance_config.yml"
DEPENDENCIES_PATH = "/etc/swarm-orchestration/dependencies.yml"
STATE_PATH = "/var/lib/swarm-orchestration/rebalance_state.json"

# --- Load Config ---
def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def load_dependencies():
    if Path(DEPENDENCIES_PATH).exists():
        with open(DEPENDENCIES_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {}

# --- Load or Init State ---
def load_state():
    if Path(STATE_PATH).exists():
        with open(STATE_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2, default=str)

# --- Scrape memory from node_exporter ---
def get_node_exporter_memory(url):
    try:
        response = requests.get(url, timeout=2)
        lines = response.text.split('\n')
        mem_total = mem_free = 0
        for line in lines:
            if line.startswith("node_memory_MemTotal_bytes"):
                mem_total = float(line.split()[-1])
            elif line.startswith("node_memory_MemAvailable_bytes"):
                mem_free = float(line.split()[-1])
        if mem_total and mem_free:
            return round(mem_free / (1024**3), 2)
    except Exception as e:
        print(f"Failed to get metrics from node_exporter ({url}): {e}")
    return None

# --- Scrape memory from Docker node ---
def get_docker_reported_memory(node_names):
    memory_data = {}
    for node in node_names:
        try:
            result = subprocess.run(
                ["docker", "node", "inspect", node, "--format", "{{.Description.Resources.MemoryBytes}}"],
                capture_output=True, text=True, timeout=3
            )
            mem_bytes = int(result.stdout.strip())
            memory_data[node] = round(mem_bytes / (1024**3), 2)
        except Exception as e:
            print(f"Failed to get Docker memory for {node}: {e}")
    return memory_data

# --- Get running node for service ---
def get_service_node(service_name):
    try:
        result = subprocess.run(
            ["docker", "service", "ps", service_name, "--filter", "desired-state=running", "--format", "{{.Node}}"],
            capture_output=True, text=True, timeout=3
        )
        node_name = result.stdout.strip().split('\n')[0] if result.stdout.strip() else None
        return node_name
    except Exception as e:
        print(f"Failed to get node for service {service_name}: {e}")
        return None

# --- Collect container memory usage (for debug and filtering) ---
def get_container_memory_usage():
    usage = {}
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}:{{.MemUsage}}"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split('\n'):
            try:
                name, mem = line.split(":")
                mem_value = mem.split("/")[0].strip()
                if mem_value.lower().endswith("mb"):
                    value = float(mem_value[:-2]) / 1024
                elif mem_value.lower().endswith("gb"):
                    value = float(mem_value[:-2])
                else:
                    value = 0
                usage[name] = round(value, 2)
            except Exception:
                continue
    except Exception as e:
        print(f"Failed to collect container memory stats: {e}")
    return usage

# --- Rebalance Decision Engine ---
def should_rebalance(service, current_node, free_mem_by_node, config, state, container_mem, dependencies, debug=False):
    now = datetime.utcnow()
    cooldown_minutes = config['default'].get('cooldown_minutes', 15)
    sustained_minutes = config['default'].get('sustained_high_minutes', 10)
    mem_gap_gb = config['default'].get('memory_difference_gb', 2)

    service_cfg = config.get('services', {}).get(service, {})
    cooldown_minutes = service_cfg.get('cooldown_minutes', cooldown_minutes)
    sustained_minutes = service_cfg.get('sustained_high_minutes', sustained_minutes)
    mem_gap_gb = service_cfg.get('memory_difference_gb', mem_gap_gb)

    if debug:
        print(f"[DEBUG] Evaluating {service}: cooldown={cooldown_minutes} min, sustained={sustained_minutes} min, mem_gap={mem_gap_gb} GB")

    last_moved_str = state.get(service, {}).get('last_moved')
    if last_moved_str:
        last_moved = datetime.fromisoformat(last_moved_str)
        if now - last_moved < timedelta(minutes=cooldown_minutes):
            if debug:
                print(f"[DEBUG] {service} in cooldown period (last moved {last_moved})")
            return False, None

    current_mem = free_mem_by_node.get(current_node)
    if current_mem is None:
        if debug:
            print(f"[DEBUG] No memory info for current node {current_node}. Skipping {service}.")
        return False, None

    better_nodes = [node for node, mem in free_mem_by_node.items() if mem - current_mem >= mem_gap_gb]
    if debug:
        print(f"[DEBUG] Nodes with significantly more memory than {current_node}: {better_nodes}")

    if len(better_nodes) >= 2:
        total_mem = container_mem.get(service, 0)
        if service in dependencies:
            for dep in dependencies[service]:
                total_mem += container_mem.get(dep, 0)
        max_delta = max(free_mem_by_node.values()) - min(free_mem_by_node.values())
        if total_mem >= max_delta:
            if debug:
                print(f"[DEBUG] {service} group memory ({round(total_mem,2)} GB) exceeds max delta ({round(max_delta,2)} GB). Skipping.")
            return False, None

        first_seen = state.get(service, {}).get('first_detected')
        if not first_seen:
            state[service] = {'first_detected': now.isoformat()}
            if debug:
                print(f"[DEBUG] First detection of imbalance for {service} at {now}")
            return False, None

        first_detected = datetime.fromisoformat(first_seen)
        if now - first_detected >= timedelta(minutes=sustained_minutes):
            best_node = sorted(better_nodes, key=lambda n: free_mem_by_node[n], reverse=True)[0]
            if debug:
                print(f"[REBALANCE] {service} has sustained imbalance. Best candidate: {best_node}")
            return True, best_node
        else:
            if debug:
                remaining = timedelta(minutes=sustained_minutes) - (now - first_detected)
                print(f"[DEBUG] {service} has not reached sustained threshold. Remaining: {remaining}")
    else:
        if debug:
            print(f"[DEBUG] {service} does not have enough better node candidates.")
        state.pop(service, None)

    return False, None

# --- Perform Docker Rebalance ---
def rebalance_service(service, dry_run=False, debug=False):
    cmd = ["docker", "service", "update", "--force", service]
    if dry_run or debug:
        print(f"[DEBUG] Would run: {' '.join(cmd)}")
    if not dry_run:
        subprocess.run(cmd)

# --- Main Loop ---
def main():
    parser = argparse.ArgumentParser(description="Swarm Service Rebalancer")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    config = load_config()
    dependencies = load_dependencies()
    state = load_state()
    monitor_interval = int(config.get('monitor_interval_seconds', 30))
    exporter_nodes = config.get('node_exporter_nodes', {})
    node_map = config.get('node_map', {})
    services = list(config.get('services', {}).keys())

    debug = args.debug or os.getenv("DEBUG", "false").lower() == "true"
    dry_run = args.dry_run or os.getenv("DRY_RUN", "false").lower() == "true"

    while True:
        free_mem = {}
        all_nodes = set()

        for service in services:
            node = get_service_node(service)
            if node:
                all_nodes.add(node)

        for node in all_nodes:
            exporter_host = node_map.get(node)
            exporter_config = exporter_nodes.get(exporter_host)
            if exporter_host and exporter_config:
                mem = get_node_exporter_memory(exporter_config['exporter_url'])
                if mem is not None:
                    free_mem[node] = mem

        missing_nodes = all_nodes - set(free_mem.keys())
        fallback_mem = get_docker_reported_memory(missing_nodes)
        free_mem.update(fallback_mem)

        container_mem = get_container_memory_usage()

        if debug:
            print(f"[DEBUG] Memory availability: {free_mem}")
            print("[DEBUG] Container memory usage:")
            for name, mem in container_mem.items():
                print(f"  - {name}: {mem} GB")

        moved_services = []

        for service in services:
            current_node = get_service_node(service)
            if not current_node:
                if debug:
                    print(f"[DEBUG] {service} has no running task. Skipping.")
                continue

            trigger, target_node = should_rebalance(service, current_node, free_mem, config, state, container_mem, dependencies, debug=debug)
            if trigger:
                print(f"[REBALANCE] {service}: {current_node} → {target_node}")
                rebalance_service(service, dry_run=dry_run, debug=debug)
                state[service] = {
                    'last_moved': datetime.utcnow().isoformat(),
                    'moved_to': target_node
                }
                moved_services.append(service)
            else:
                if debug:
                    print(f"[DEBUG] {service} remains on {current_node}")

        if debug:
            print("[DEBUG] Summary of this run:")
            if moved_services:
                print(f"  ✅ Services rebalanced: {', '.join(moved_services)}")
            else:
                print("  ⏸️ No services moved this cycle.")

        save_state(state)
        time.sleep(monitor_interval)

if __name__ == "__main__":
    main()