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

