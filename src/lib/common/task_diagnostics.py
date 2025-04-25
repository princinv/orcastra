"""
task_diagnostics.py
- Utility to inspect and log task-level state for any Docker Swarm service.
- Used during retries and troubleshooting in label_sync, rebalance, and bootstrap logic.
"""

import subprocess
import logging
import shutil

def log_task_status(service_name: str, context: str = "unknown"):
    """
    Logs the output of `docker service ps --no-trunc` for a given service.
    Used to diagnose why services may not be running or are stuck in certain states.

    Args:
        service_name (str): The full name of the service (e.g. "swarm-dev_gitea").
        context (str): Caller context (e.g. "anchor-label", "rebalance-check").
    """
    docker_path = shutil.which("docker") or "/usr/bin/docker"

    try:
        result = subprocess.run(
            [docker_path, "service", "ps", "--no-trunc", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout.strip()
        if output:
            logging.debug(f"[task_diagnostics] Task status for {service_name} ({context}):\n{output}")
        else:
            logging.debug(f"[task_diagnostics] No task output returned for {service_name} ({context})")
    except Exception as e:
        logging.debug(f"[task_diagnostics] Could not inspect {service_name} ({context}): {e}")
