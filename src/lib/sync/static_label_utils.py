#!/usr/bin/env python3
"""
static_label_utils.py
- Syncs static node labels based on nodes.yml definition.
- These are persistent, non-anchor labels (e.g., zfs, ubuntu, proxmox).
- Labels are applied using the Docker SDK and only removed if explicitly absent from config.
"""
from loguru import logger

from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def sync_static_node_labels(client, nodes_config, dry_run=False):

    managed_labels_set = set()  # track all labels we manage system-wide
    for node_labels in nodes_config.values():
        managed_labels_set.update(node_labels.get("labels", []))

    available_nodes = {n.attrs["Description"]["Hostname"]: n for n in client.nodes.list()}
    found, missing = [], []

    for hostname, meta in nodes_config.items():
        desired_labels = {label: "true" for label in meta.get("labels", [])}
        node = available_nodes.get(hostname)

        if not node:
            missing.append(hostname)
            continue

        found.append(hostname)
        current = node.attrs["Spec"].get("Labels", {}).copy()

        # 1. Add/update desired labels
        updated_labels = current.copy()
        updated_labels.update(desired_labels)

        # 2. Remove obsolete managed labels that aren't in desired set for this node
        for key in managed_labels_set:
            if key not in desired_labels and key in updated_labels:
                del updated_labels[key]

        if current != updated_labels:
            if dry_run:
                logger.info(f"[static_label] (Dry Run) Would update {hostname} → {updated_labels}")
                continue  # <-- inside loop, now valid

        if current != updated_labels:
            if dry_run:
                logger.info(f"[static_label] (Dry Run) Would update {hostname} → {updated_labels}")
                continue

            try:
                version = node.attrs["Version"]["Index"]
                client.api.update_node(node.id, version=version, labels=updated_labels)
                logger.info(f"[static_label] Synced labels on {hostname}: {updated_labels}")
            except Exception as e:
                logger.error(f"[static_label] Failed to update {hostname}: {e}")

    logger.info(f"[static_label] Labeled nodes: {found}")
    if missing:
        logger.info(f"[static_label] Nodes not found in Swarm (may be offline, ignored): {missing}")
