"""
label_utils.py
- Encapsulates logic for:
    - Resolving which node a Docker Swarm service is running on
    - Applying and removing node labels through the Docker SDK

Used by label_sync, bootstrap, and rebalance logic for task placement control.
"""

import time
import logging
from core.docker_client import client

# --- Service Task Node Resolution ---

def get_service_node(service_name: str, wait_timeout: int = 5, debug: bool = False) -> str | None:
    """
    Resolve which Swarm node a service task is currently running on.

    Args:
        service_name (str): Full Swarm service name (e.g. swarm-dev_gitea_db).
        wait_timeout (int): How many seconds to retry before giving up.
        debug (bool): If True, logs task state on each check.

    Returns:
        str or None: Node ID the service is running on, or None if unresolved.
    """
    try:
        service = client.services.get(service_name)
        deadline = time.time() + wait_timeout

        while time.time() < deadline:
            tasks = service.tasks()
            for task in tasks:
                status = task.get("Status", {})
                node_id = task.get("NodeID")
                state = status.get("State")

                if debug:
                    logging.debug(f"[get_service_node] Task {task.get('ID')} for {service_name} - State: {state}, NodeID: {node_id}")

                if state == "running" and node_id:
                    return node_id

            time.sleep(1)

        logging.warning(f"[get_service_node] No running task found for {service_name}")
    except Exception as e:
        logging.error(f"[get_service_node] Failed to resolve node for {service_name}: {e}")
    return None

# --- Node Label Management ---

def apply_label(client, node_id: str, key: str, value: str = "true", dry_run: bool = False):
    """
    Apply a label to a Swarm node via Docker SDK.

    Args:
        client: Docker client instance.
        node_id (str): Target node ID.
        key (str): Label key.
        value (str): Label value (default: "true").
        dry_run (bool): If True, do not actually update.
    """
    node = client.nodes.get(node_id)
    node.reload()
    spec = node.attrs["Spec"]
    labels = spec.get("Labels", {})
    labels[key] = value

    if not dry_run:
        node.update({
            'Role': spec['Role'],
            'Availability': spec['Availability'],
            'Labels': labels
        })

def remove_label(client, node, label_key: str, dry_run: bool = False):
    """
    Remove a label from a Swarm node via Docker SDK.

    Args:
        client: Docker client instance.
        node: Docker node object (preloaded).
        label_key (str): Label to remove.
        dry_run (bool): If True, skip actual removal.
    """
    node.reload()
    spec = node.attrs["Spec"]
    labels = spec.get("Labels", {})

    if label_key in labels:
        labels.pop(label_key)
        if not dry_run:
            node.update({
                'Role': spec['Role'],
                'Availability': spec['Availability'],
                'Labels': labels
            })
