"""
metrics_helpers.py
- Collects memory-related metrics from:
    - node_exporter
    - Docker Swarm nodes
    - Running containers

Used for memory-aware service scheduling and rebalancing decisions.
"""

import subprocess
import requests
import logging

def get_node_exporter_memory(url):
    """
    Query Prometheus-style node_exporter endpoint for MemAvailable bytes.
    
    Args:
        url (str): Full URL to the node_exporter endpoint.

    Returns:
        float or None: Available memory in GB, or None on failure.
    """
    try:
        response = requests.get(url, timeout=2)
        lines = response.text.splitlines()
        mem_total = mem_free = 0
        for line in lines:
            if line.startswith("node_memory_MemTotal_bytes"):
                mem_total = float(line.split()[-1])
            elif line.startswith("node_memory_MemAvailable_bytes"):
                mem_free = float(line.split()[-1])
        if mem_total > 0 and mem_free > 0:
            gb = round(mem_free / (1024**3), 2)
            return max(gb, 0)
    except Exception as e:
        logging.warning(f"[metrics] Failed to get node_exporter metrics from {url}: {e}")
    return None

def get_docker_reported_memory(node_names):
    """
    Use Docker CLI to collect Swarm-level memory capacity per node.

    Args:
        node_names (list[str]): List of Swarm node hostnames.

    Returns:
        dict[str, float]: Mapping of node -> available memory in GB.
    """
    memory_data = {}
    for node in node_names:
        try:
            result = subprocess.run(
                ["docker", "node", "inspect", node, "--format", "{{.Description.Resources.MemoryBytes}}"],
                capture_output=True, text=True, timeout=3
            )
            mem_bytes = int(result.stdout.strip())
            gb = round(mem_bytes / (1024**3), 2)
            memory_data[node] = max(gb, 0)
        except Exception as e:
            logging.warning(f"[metrics] Failed to get Docker memory for {node}: {e}")
    return memory_data

def get_container_memory_usage():
    """
    Use `docker stats` to collect active container memory usage.

    Returns:
        dict[str, float]: Mapping of container name -> used memory in GB.
    """
    usage = {}
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}:{{.MemUsage}}"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().splitlines():
            try:
                name, mem = line.split(":")
                mem_value = mem.split("/")[0].strip().lower()
                if mem_value.endswith("mb"):
                    value = float(mem_value[:-2]) / 1024
                elif mem_value.endswith("gb"):
                    value = float(mem_value[:-2])
                else:
                    value = 0
                usage[name] = max(round(value, 2), 0)
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"[metrics] Failed to collect container memory stats: {e}")
    return usage
