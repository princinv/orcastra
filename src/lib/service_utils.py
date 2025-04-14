# lib/service_utils.py

import subprocess
import logging
import time
from core.retry_state import retry_state

def force_update_service(client, service_name):
    """
    Forces a rolling update of a service using either the Docker SDK or CLI.
    Tracks retry state for orchestrator cooldown logic.
    """
    try:
        service = client.services.get(service_name)

        try:
            # Safe update using force flag; avoid task_template or name re-specification
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
