"""
rebalance_decision.py
- Encapsulates decision logic for when a service should be rebalanced to another node.
- Provides an async rebalance loop for continuous monitoring.
"""

from datetime import datetime, timedelta
import asyncio
import logging

# --- Decision Logic ---

def should_rebalance(service, current_node, free_mem_by_node, config, state, container_mem, dependencies, debug=False):
    """
    Evaluate whether a service should be rebalanced to a new node based on memory metrics.

    Args:
        service (str): The Swarm service name.
        current_node (str): Node where the service is currently running.
        free_mem_by_node (dict): Memory available per node (in GB).
        config (dict): Rebalance policy (cooldown, sustained time, thresholds).
        state (dict): Service state from disk (first_detected, etc.).
        container_mem (dict): Memory usage (in GB) per container.
        dependencies (dict): Services to co-locate with (same-node constraints).
        debug (bool): If True, enables verbose decision output (currently unused).

    Returns:
        tuple: (bool, str or None) - Should rebalance, and which node to target if applicable.
    """
    now = datetime.utcnow()
    cooldown = config['default'].get('cooldown_minutes', 15)
    sustained = config['default'].get('sustained_high_minutes', 10)
    threshold = config['default'].get('memory_difference_gb', 2)

    current_mem = free_mem_by_node.get(current_node)
    if current_mem is None:
        return False, None

    better_nodes = [n for n, mem in free_mem_by_node.items() if mem - current_mem >= threshold]
    if len(better_nodes) < 2:
        state.pop(service, None)
        return False, None

    total_mem = container_mem.get(service, 0)
    for dep in dependencies.get(service, []):
        total_mem += container_mem.get(dep, 0)

    max_delta = max(free_mem_by_node.values()) - min(free_mem_by_node.values())
    if total_mem >= max_delta:
        return False, None

    if service not in state:
        state[service] = {'first_detected': now.isoformat()}
        return False, None

    first_seen = datetime.fromisoformat(state[service]['first_detected'])
    if now - first_seen >= timedelta(minutes=sustained):
        best = max(better_nodes, key=lambda n: free_mem_by_node[n])
        return True, best

    return False, None

# --- Async Rebalance Loop ---

async def run_rebalance_loop():
    """
    Main async loop for running rebalance decisions.
    Periodically checks memory usage and triggers service moves.
    """
    from core.config import REBALANCE_CONFIG_PATH
    from core.config_loader import load_yaml
    from core.state import load_state, save_state
    from lib.metrics.metrics_helpers import get_node_exporter_memory, get_docker_reported_memory, get_container_memory_usage
    from core.docker_client import client

    config = load_yaml(REBALANCE_CONFIG_PATH)
    state = load_state()

    loop_interval = config['default'].get('check_interval_seconds', 60)
    exporters = config.get('node_exporters', {})

    while True:
        logging.info("[rebalance] Checking memory stats for rebalancing decisions...")

        free_mem_by_node = {}
        for node, url in exporters.items():
            mem = get_node_exporter_memory(url)
            if mem is not None:
                free_mem_by_node[node] = mem

        if not free_mem_by_node:
            logging.warning("[rebalance] No memory data available. Skipping.")
            await asyncio.sleep(loop_interval)
            continue

        container_mem = get_container_memory_usage()
        dependencies = load_yaml(config['default'].get('dependencies_file', '/etc/swarm-orchestration/dependencies.yml'))

        for service in container_mem.keys():
            try:
                current_node = None
                tasks = client.services.get(service).tasks()
                for task in tasks:
                    if task.get('Status', {}).get('State') == 'running':
                        current_node = task.get('NodeID')
                        break

                if not current_node:
                    continue

                should_move, target_node = should_rebalance(
                    service, current_node, free_mem_by_node, config, state, container_mem, dependencies
                )

                if should_move and target_node:
                    logging.warning(f"[rebalance] Triggering rebalance of {service} to {target_node}")
                    client.services.get(service).update(force_update=True)
                    state[service]['last_moved'] = datetime.utcnow().isoformat()
                    state[service]['moved_to'] = target_node

            except Exception as e:
                logging.error(f"[rebalance] Failed to evaluate rebalance for {service}: {e}")

        save_state(state)
        await asyncio.sleep(loop_interval)
