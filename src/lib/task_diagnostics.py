"""
task_diagnostics.py
- Utility to inspect and log task-level state for any Docker Swarm service.
- Used during retries and troubleshooting in label_sync and bootstrap.
"""

import subprocess
import logging

def log_task_status(service_name, context="diagnostic"):
    """
    Logs the full output of `docker service ps` for the given service name.
    Used for diagnosing services marked as not running.
    """
    try:
        result = subprocess.run(
            ["docker", "service", "ps", "--no-trunc", service_name],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip()
        if output:
            logging.debug(f"[{context}] Task status for {service_name}:\n{output}")
        else:
            logging.debug(f"[{context}] No task output for {service_name}")
    except Exception as e:
        logging.debug(f"[{context}] Could not inspect {service_name}: {e}")
