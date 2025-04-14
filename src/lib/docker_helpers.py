"""
docker_helpers.py
- Helper to run docker inspect commands or interact with CLI when SDK is insufficient.
"""

import subprocess
import time
from core.docker_client import client

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

def get_service_node(service_name, wait_timeout=5, debug=False):
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        try:
            service = client.services.get(service_name)
            tasks = service.tasks()
            for task in tasks:
                status = task.get("Status", {})
                state = status.get("State")
                desired = task.get("DesiredState")
                if debug:
                    print(f"[get_service_node] {service_name} task state: {state}, desired: {desired}")
                if state in ["running", "starting", "assigned", "ready"] and desired == "running":
                    return task.get("NodeID")
        except Exception as e:
            if debug:
                print(f"[get_service_node] Error: {e}")
        time.sleep(1)
    return None

