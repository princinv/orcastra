"""
docker_helpers.py
- Helper to run docker inspect commands or interact with CLI when SDK is insufficient.
"""

import subprocess

def get_docker_node_memory(node_name):
    try:
        result = subprocess.run(
            ["docker", "node", "inspect", node_name, "--format", "{{.Description.Resources.MemoryBytes}}"],
            capture_output=True, text=True, timeout=3
        )
        return int(result.stdout.strip())
    except Exception as e:
        print(f"Error inspecting node memory for {node_name}: {e}")
        return None

from core.docker_client import client
import time

def get_service_node(service_name, wait_timeout=5, debug=False):
    try:
        service = client.services.get(service_name)
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            tasks = service.tasks()
            for task in tasks:
                status = task.get("Status", {})
                state = status.get("State")
                if debug:
                    print(f"[get_service_node] {service_name} task in state: {state}")
                if state == "running":
                    return task.get("NodeID")
                if state in ["failed", "shutdown", "rejected"]:
                    return None
            time.sleep(1)
    except Exception as e:
        if debug:
            print(f"[get_service_node] Error for {service_name}: {e}")
    return None
