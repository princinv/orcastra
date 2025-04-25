"""
service_helpers.py
- Contains logic for:
    - Determining which node a service is running on
    - Forcibly triggering rolling updates via SDK or CLI fallback
- Handles retry tracking when updates fail.
"""

import logging
import time
import subprocess
from docker.errors import APIError
from core.retry_state import retry_state

def get_service_node(client, service_name, wait_timeout=5):
    """
    Identify which node is currently running a given Swarm service.

    Args:
        client: Docker SDK client
        service_name (str): Full service name (e.g. swarm-dev_gitea)
        wait_timeout (int): Time in seconds to wait for a valid task

    Returns:
        str or None: Node ID where the service is running
    """
    try:
        service = client.services.get(service_name)
        deadline = time.time() + wait_timeout

        while time.time() < deadline:
            tasks = service.tasks()
            for task in tasks:
                status = task.get("Status", {})
                state = status.get("State")
                node_id = task.get("NodeID")

                if state == "running" and node_id:
                    logging.info(f"📍 {service_name} is running on node {node_id}")
                    return node_id
                if state == "starting" and node_id:
                    logging.info(f"⏳ {service_name} is starting on node {node_id}, will retry later")

            time.sleep(1)

        for task in tasks:
            logging.debug(
                f"🧪 Task for {service_name}: ID={task.get('ID')} | "
                f"State={task.get('Status', {}).get('State')} | "
                f"NodeID={task.get('NodeID')}"
            )
        logging.warning(f"❌ No running task with valid NodeID found for {service_name}")

    except APIError as e:
        logging.warning(f"⚠️ Could not inspect service: {service_name} — {e}")
    except Exception as e:
        logging.error(f"🔥 Unexpected error checking node for {service_name}: {e}")
    return None

def force_update_service(client, service_name):
    """
    Force a rolling update of a Swarm service via Docker SDK or CLI.
    Handles retry tracking and CLI fallback.

    Args:
        client: Docker SDK client
        service_name (str): The name of the service to update

    Returns:
        bool: True on success, False on failure
    """
    try:
        service = client.services.get(service_name)

        try:
            service.update(
                labels=service.attrs['Spec'].get('Labels', {}),
                force_update=True
            )
            logging.info(f"🔁 Forced update of service: {service_name} (SDK)")
        except Exception as te:
            logging.warning(f"⚠️ SDK update failed for {service_name}: {te}, falling back to CLI")
            subprocess.run(["docker", "service", "update", "--force", service_name], check=True)
            logging.info(f"🔁 Forced update of service: {service_name} (CLI)")

        retry_state.pop(service_name, None)
        return True

    except Exception as e:
        logging.error(f"❌ Failed to update service '{service_name}': {e}")
        retry_state[service_name]["failures"] += 1
        retry_state[service_name]["last_attempt"] = time.time()
        return False
