"""
docker_helpers.py
- Helper to run docker inspect commands or interact with CLI when SDK is insufficient.
"""

import subprocess
import time
import logging
from core.docker_client import client

# --- Task State Groups ---
IGNORED_STATES = {"new", "allocated", "pending"}
WAITING_STATES = {"assigned", "accepted", "preparing", "ready", "starting"}
SUCCESS_STATES = {"running", "complete"}
FAILURE_STATES = {"failed", "rejected", "remove", "orphaned"}
TERMINAL_STATES = SUCCESS_STATES | FAILURE_STATES | {"shutdown"}

def get_docker_node_memory(node_name):
    """
    Returns the memory in bytes for the specified Docker Swarm node by name.
    Falls back to logging debug message and returning None if inspection fails.
    """
    try:
        result = subprocess.run(
            ["docker", "node", "inspect", node_name, "--format", "{{.Description.Resources.MemoryBytes}}"],
            capture_output=True, text=True, timeout=3
        )
        memory = result.stdout.strip()
        if memory.isdigit():
            return int(memory)
        logging.debug(f"[docker_helpers] Unexpected memory output for {node_name}: {memory}")
    except Exception as e:
        logging.debug(f"[docker_helpers] Error inspecting node memory for {node_name}: {e}")
    return None

def get_service_node(service_name, wait_timeout=5, debug=False):
    """
    Returns the NodeID for a running task of the given service.

    If no task is running:
    - Returns "starting" if at least one task is accepted or initializing.
    - Returns None if all tasks are pending or failed due to unmet constraints.

    Args:
        service_name (str): Full Swarm service name.
        wait_timeout (int): Seconds to keep checking for a running task.
        debug (bool): Whether to emit extra debug logs.
    """
    deadline = time.time() + wait_timeout

    while time.time() < deadline:
        try:
            service = client.services.get(service_name)
            tasks = service.tasks()

            for task in tasks:
                status = task.get("Status", {})
                state = status.get("State")
                desired = task.get("DesiredState")
                node_id = task.get("NodeID")
                message = status.get("Err", "")

                if debug:
                    logging.debug(
                        f"[get_service_node] {service_name} — "
                        f"State: {state}, Desired: {desired}, NodeID: {node_id}, Message: {message}"
                    )

                if state == "running" and desired == "running" and node_id:
                    return node_id

            for task in tasks:
                state = task.get("Status", {}).get("State")
                if state in ("preparing", "assigned", "accepted", "ready", "starting"):
                    return "starting"

            if debug:
                logging.debug(f"[get_service_node] {service_name} has no runnable task — likely due to unmet constraints")

        except Exception as e:
            logging.debug(f"[get_service_node] Exception retrieving {service_name}: {e}")

        time.sleep(1)

    return None

def get_service_node(service, debug=False):
    tasks = service.tasks()

    node_id = None
    fallback_state = None

    for task in tasks:
        status = task.get("Status", {})
        state = status.get("State")
        node = task.get("NodeID")

        if debug:
            logging.debug(f"[get_service_node] {service.name} — State: {state}, Desired: {task.get('DesiredState')}, NodeID: {node}, Message: {status.get('Message')}")

        if state == "running":
            return node  # ✅ Running wins immediately
        elif state in WAITING_STATES and fallback_state is None:
            fallback_state = "starting"
        elif state in FAILURE_STATES and not node_id:
            fallback_state = None  # Only use if no valid tasks

    return fallback_state or None
