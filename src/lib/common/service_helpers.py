"""
service_helpers.py
- Contains logic for:
    - Determining which node a service is running on
    - Forcibly triggering rolling updates via SDK or CLI fallback
- Handles retry tracking when updates fail.
"""

import subprocess
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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
                    logger.info(f"📍 {service_name} is running on node {node_id}")
                    return node_id
                if state == "starting" and node_id:
                    logger.info(f"⏳ {service_name} is starting on node {node_id}, will retry later")

            time.sleep(1)

        for task in tasks:
            logger.debug(
                f"🧪 Task for {service_name}: ID={task.get('ID')} | "
                f"State={task.get('Status', {}).get('State')} | "
                f"NodeID={task.get('NodeID')}"
            )
        logger.warning(f"❌ No running task with valid NodeID found for {service_name}")

    except APIError as e:
        logger.warning(f"⚠️ Could not inspect service: {service_name} — {e}")
    except Exception as e:
        logger.error(f"🔥 Unexpected error checking node for {service_name}: {e}")
    return None


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(APIError)
)
def force_update_service(client, service_name):
    """
    Force-update a Docker service using SDK or fallback to CLI.

    Args:
        client: Docker SDK client
        service_name (str): Full service name (e.g. swarm-dev_gitea)

    Returns:
        bool: True if update succeeded, False otherwise
    """
    try:
        service = client.services.get(service_name)

        try:
            service.update(
                labels=service.attrs['Spec'].get('Labels', {}),
                force_update=True
            )
            logger.info(f"🔁 Forced update of service: {service_name} (SDK)")
        except Exception as sdk_error:
            logger.warning(f"⚠️ SDK update failed for {service_name}: {sdk_error}, falling back to CLI")
            subprocess.run(["docker", "service", "update", "--force", service_name], check=True)
            logger.info(f"🔁 Forced update of service: {service_name} (CLI fallback)")

        retry_state.pop(service_name, None)
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update service '{service_name}': {e}")
        retry_state.setdefault(service_name, {"failures": 0, "last_attempt": time.time()})
        retry_state[service_name]["failures"] += 1
        retry_state[service_name]["last_attempt"] = time.time()
        return False
