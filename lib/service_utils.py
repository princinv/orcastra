# lib/service_utils.py

import logging
from docker.errors import APIError
from core.retry_state import retry_state
import time

# Get node ID where a service is running
def get_service_node(client, service_name, wait_timeout=5):
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

# Force a rolling update on a service
def force_update_service(client, service_name):
    try:
        service = client.services.get(service_name)
        spec = service.attrs['Spec']
        logging.debug(f"🔧 Service spec keys: {list(spec.keys())}")

        try:
            service.update(
                task_template=spec["TaskTemplate"],
                name=spec["Name"],
                labels=spec.get("Labels", {}),
                mode=spec.get("Mode"),
                update_config=spec.get("UpdateConfig"),
                rollback_config=spec.get("RollbackConfig"),
                endpoint_spec=spec.get("EndpointSpec")
            )
        except TypeError as te:
            logging.warning(f"⚠️ Primary update method failed, falling back: {te}")
            service.update(force_update=True)

        logging.info(f"🔁 Forced update of service: {service_name}")
        if service_name in retry_state:
            del retry_state[service_name]
        return True
    except Exception as e:
        logging.error(f"❌ Failed to update service '{service_name}': {e}")
        retry_state[service_name]["failures"] += 1
        retry_state[service_name]["last_attempt"] = time.time()
        return False
