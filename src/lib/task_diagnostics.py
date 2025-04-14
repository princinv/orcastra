"""
task_diagnostics.py
- Utility to inspect and log task-level state for any Docker Swarm service.
- Used during retries and troubleshooting in label_sync and bootstrap.
"""

import subprocess
import logging
import shutil

def log_task_status(service_name, context="unknown"):
    docker_path = shutil.which("docker") or "/usr/bin/docker"
     """
    Logs the full output of `docker service ps` for the given service name.
    Used for diagnosing services marked as not running.
    """
    try:
        result = subprocess.run(
            [docker_path, "service", "ps", "--no-trunc", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        logging.debug(f"[task_diagnostics] Task status for {service_name} ({context}):\n{result.stdout.strip()}")
    except Exception as e:
        logging.debug(f"[task_diagnostics] Could not inspect {service_name} ({context}): {e}")"""
task_diagnostics.py
- Utility to inspect and log task-level state for any Docker Swarm service.
- Used during retries and troubleshooting in label_sync and bootstrap.
"""

import subprocess
import logging
import shutil

def log_task_status(service_name, context="unknown"):
    docker_path = shutil.which("docker") or "/usr/bin/docker"
     """
    Logs the full output of `docker service ps` for the given service name.
    Used for diagnosing services marked as not running.
    """
    try:
        result = subprocess.run(
            [docker_path, "service", "ps", "--no-trunc", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        logging.debug(f"[task_diagnostics] Task status for {service_name} ({context}):\n{result.stdout.strip()}")
    except Exception as e:
        logging.debug(f"[task_diagnostics] Could not inspect {service_name} ({context}): {e}")"""
task_diagnostics.py
- Utility to inspect and log task-level state for any Docker Swarm service.
- Used during retries and troubleshooting in label_sync and bootstrap.
"""

import subprocess
import logging
import shutil

def log_task_status(service_name, context="unknown"):
    docker_path = shutil.which("docker") or "/usr/bin/docker"
     """
    Logs the full output of `docker service ps` for the given service name.
    Used for diagnosing services marked as not running.
    """
    try:
        result = subprocess.run(
            [docker_path, "service", "ps", "--no-trunc", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        logging.debug(f"[task_diagnostics] Task status for {service_name} ({context}):\n{result.stdout.strip()}")
    except Exception as e:
        logging.debug(f"[task_diagnostics] Could not inspect {service_name} ({context}): {e}")