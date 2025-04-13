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
