#!/usr/bin/env python3
"""
bootstrap.py
- Ensures Docker Swarm is initialized and that all nodes have the correct labels.
- Can be run via main supervisor or manually via CLI.
- Executes node promotion, label syncing, and initial join flow.
"""

import os
import signal
import asyncio
from core.config_loader import load_yaml, preview_yaml
from lib.bootstrap.bootstrap_tasks import check_swarm, get_join_token, join_node, get_node_map
from lib.bootstrap.bootstrap_labels import sync_labels
from lib.common.ssh_helpers import is_online, ssh

# --- Runtime Environment Variables ---
COMMAND_FILE = os.getenv("COMMAND_FILE", "/tmp/swarm-orchestration.command.yml")
NODES_FILE = os.getenv("NODES_FILE", "/etc/swarm-orchestration/nodes.yml")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
should_run = True

# --- Startup Preview ---
preview_yaml(NODES_FILE, name="nodes.yml")

def bootstrap_swarm():
    """
    Main bootstrap routine:
    - Checks if Swarm is active
    - Joins any unjoined nodes
    - Promotes them to managers
    - Ensures labels are up to date
    """
    config = load_yaml(NODES_FILE)
    leader = config.get("leader")
    advertise = config.get("advertise_addr")
    nodes = config.get("nodes", {})
    prune = config.get("options", {}).get("prune_unknown_labels", False)

    if not is_online(advertise):
        print(f"[bootstrap] Leader {leader} offline at {advertise}, skipping.")
        return False

    if check_swarm(advertise, DEBUG):
        print("[bootstrap] Swarm initialized.")
    else:
        print("[bootstrap] Swarm already active.")

    token = get_join_token(advertise, DEBUG)
    if not token:
        print("[bootstrap] Failed to retrieve join token.")
        return False

    for name, meta in nodes.items():
        ip = meta["ip"]
        if name == leader or not is_online(ip):
            continue
        if ssh(ip, "docker info | grep 'Swarm: active'", DEBUG).returncode != 0:
            join_node(ip, token, advertise, DEBUG)
            print(f"[bootstrap] {name} joined.")

    node_map = get_node_map(advertise, DEBUG)
    for name in nodes:
        if name in node_map:
            ssh(advertise, f"docker node promote {node_map[name]}", DEBUG)

    sync_labels(advertise, nodes, node_map, prune=prune, dry_run=DRY_RUN, debug=DEBUG)
    return True

def sighup_handler(signum, frame):
    print("📣 SIGHUP received — re-running bootstrap...")
    bootstrap_swarm()

async def run():
    signal.signal(signal.SIGHUP, sighup_handler)
    if RUN_ONCE:
        bootstrap_swarm()
    else:
        while should_run:
            bootstrap_swarm()
            await asyncio.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    asyncio.run(run())
