"""
docker_helpers.py
- Provides low-level helpers for interacting with Docker via subprocess when the SDK is insufficient.
- Used for Swarm node inspection tasks such as memory availability.
"""

import subprocess
import logging
import time
from core.docker_client import client


def get_docker_node_memory(node_name):
    """
    Return the available memory in bytes for the given Swarm node by name.
    
    Args:
        node_name (str): The Docker node's hostname or ID.

    Returns:
        int or None: The memory in bytes, or None if the lookup fails.
    """
    try:
        result = subprocess.run(
            ["docker", "node", "inspect", node_name, "--format", "{{.Description.Resources.MemoryBytes}}"],
            capture_output=True, text=True, timeout=3
        )
        memory = result.stdout.strip()
        if memory.isdigit():
            return int(memory)
        logging.warning(f"[docker_helpers] Unexpected memory output for {node_name}: {memory}")
    except Exception as e:
        logging.error(f"[docker_helpers] Error inspecting node memory for {node_name}: {e}")
    return None

def get_task_state(service_name, wait_timeout=5, debug=False):
    deadline = time.time() + wait_timeout

    while time.time() < deadline:
        try:
            service = client.services.get(service_name)
            tasks = service.tasks()

            if not tasks:
                return None, None

            most_recent = sorted(tasks, key=lambda t: t.get("Status", {}).get("Timestamp", ""))[-1]
            status = most_recent.get("Status", {})
            state = status.get("State")
            desired = most_recent.get("DesiredState")
            node_id = most_recent.get("NodeID")
            message = status.get("Err", "") or status.get("Message", "")

            if debug:
                logging.debug(
                    f"[get_task_state] {service_name} — State: {state}, Desired: {desired}, NodeID: {node_id}, Message: {message}"
                )

            return state, node_id

        except Exception as e:
            logging.debug(f"[get_task_state] Exception retrieving {service_name}: {e}")

        time.sleep(1)

    return None, None
