"""
node_labels.py
- Determines which node a given service is running on.
- Applies Swarm node labels based on where anchor services are deployed.
- Ensures exclusivity and retry logic for delayed tasks.
"""

import time
import logging
from core.docker_client import client
from lib.labels import apply_label, remove_label
from lib.service_utils import get_service_node
from lib.task_diagnostics import log_task_status

def label_anchors(anchor_list, stack_name, dry_run=False, debug=False):
    """
    Applies a label like gitea_db=true to the node currently running that service.
    Ensures exclusivity by removing the label from all other nodes.
    Retries up to 5 times over 15 seconds. Logs all failures, success, and skips.
    """

    logging.info("[label_anchors] Clearing old anchor labels")
    for node in client.nodes.list():
        nid = node.id
        hostname = node.attrs["Description"]["Hostname"]
        labels = node.attrs["Spec"].get("Labels", {})
        for anchor in anchor_list:
            if anchor in labels:
                logging.info(f"[label_anchors] Removing stale label {anchor}=true from {hostname}")
                if not dry_run:
                    try:
                        remove_label(client, nid, anchor)
                    except Exception as e:
                        logging.error(f"[label_anchors] ❌ Failed to remove label {anchor} from {hostname}: {e}")

    for anchor in anchor_list:
        service_name = f"{stack_name}_{anchor}"
        node_id = None

        for attempt in range(5):
            node_id = get_service_node(client, service_name, debug=debug)
            if node_id and node_id != "starting":
                break
            logging.debug(f"[label_anchors] Attempt {attempt + 1}/5 — {service_name} not ready (node_id={node_id}). Retrying...")
            log_task_status(service_name, context="anchor-label")
            time.sleep(3)

        if not node_id or node_id == "starting":
            logging.warning(f"[label_anchors] ❌ Failed to label: No valid running task for {service_name} (anchor: {anchor})")
            continue

        logging.info(f"[label_anchors] Labeling node {node_id} with {anchor}=true for service {service_name}")

        for node in client.nodes.list():
            nid = node.id
            hostname = node.attrs["Description"]["Hostname"]
            labels = node.attrs["Spec"].get("Labels", {})
            if labels.get(anchor) and nid != node_id:
                logging.info(f"[label_anchors] Removing {anchor}=true from {hostname}")
                if not dry_run:
                    try:
                        remove_label(client, nid, anchor)
                    except Exception as e:
                        logging.error(f"[label_anchors] ❌ Failed to remove label from {hostname}: {e}")

        try:
            logging.info(f"[label_anchors] Applying {anchor}=true to node {node_id}")
            if not dry_run:
                apply_label(client, node_id, anchor)
            logging.info(f"[label_anchors] ✅ Applied label {anchor}=true to node {node_id}")
        except Exception as e:
            logging.error(f"[label_anchors] ❌ Failed to apply label {anchor}=true to node {node_id}: {e}")
