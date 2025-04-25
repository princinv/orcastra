#!/usr/bin/env python3
"""
static_labels.py
- Entrypoint script to sync static node labels defined in nodes.yml.
- Reads from /etc/swarm-orchestration/nodes.yml and applies labels to Docker Swarm nodes.
- Static labels are persistent attributes like zfs, ubuntu, proxmox — not dynamically managed.
"""
from core.config_loader import load_yaml
from core.docker_client import client
from lib.sync.static_label_utils import sync_static_node_labels

def run():
    config = load_yaml("/etc/swarm-orchestration/nodes.yml")
    nodes_config = config.get("nodes", {})
    sync_static_node_labels(client, nodes_config)
