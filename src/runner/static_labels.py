#!/usr/bin/env python3
"""
static_labels.py
- Entrypoint script to sync static node labels defined in swarm.yml.
- Reads from /etc/swarm-orchestration/swarm.yml and applies labels to Docker Swarm nodes.
- Static labels are persistent attributes like zfs, ubuntu, proxmox — not dynamically managed.
"""

import logging
from core.config_loader import load_yaml
from core.docker_client import client
from core.config import DRY_RUN
from lib.sync.static_label_utils import sync_static_node_labels

SWARM_FILE = "/etc/swarm-orchestration/swarm.yml"

# --- Setup basic logging ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def run():
    logging.info("[static_labels] Starting static label synchronization...")
    config = load_yaml(SWARM_FILE)
    if not config:
        logging.error(f"[static_labels] Failed to load config from {SWARM_FILE}")
        return

    nodes_config = config.get("nodes", {})
    if not nodes_config:
        logging.warning("[static_labels] No nodes defined in config. Exiting.")
        return

    logging.debug(f"[static_labels] Nodes defined in config: {list(nodes_config.keys())}")

    # List all nodes seen by Docker
    try:
        swarm_nodes = client.nodes.list()
        detected_hostnames = [n.attrs["Description"]["Hostname"] for n in swarm_nodes]
        logging.debug(f"[static_labels] Swarm reports nodes: {detected_hostnames}")
    except Exception as e:
        logging.error(f"[static_labels] Failed to fetch Swarm nodes: {e}")
        return

    sync_static_node_labels(client, nodes_config, dry_run=DRY_RUN)

if __name__ == "__main__":
    run()
