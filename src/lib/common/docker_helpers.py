"""
docker_helpers.py
- Provides low-level helpers for interacting with Docker via subprocess when the SDK is insufficient.
- Used for Swarm node inspection tasks such as memory availability.
"""

import subprocess
import logging

def get_docker_node_memory(node_name):
    """
    Return the available memory in bytes for the given Swarm node by name.
    
    Args:
        node_name (str): The Docker node's hostname or ID.

    Returns:
        int or None: The memory in bytes, or None if the lookup fails.
    """
    try:
        result = subprocess.run(
            ["docker", "node", "inspect", node_name, "--format", "{{.Description.Resources.MemoryBytes}}"],
            capture_output=True, text=True, timeout=3
        )
        memory = result.stdout.strip()
        if memory.isdigit():
            return int(memory)
        logging.warning(f"[docker_helpers] Unexpected memory output for {node_name}: {memory}")
    except Exception as e:
        logging.error(f"[docker_helpers] Error inspecting node memory for {node_name}: {e}")
    return None
