#!/usr/bin/env python3
"""
rebalance_decision.py
- Encapsulates the decision logic for memory-aware Docker Swarm service rebalancing.
"""

from datetime import datetime, timedelta
import asyncio
from loguru import logger
from time import time

from core.constants import DEFAULT_REBALANCE_BUFFER_GB

rebalance_attempts_total = 0
rebalance_success_total = 0
rebalance_failures_total = 0
rebalance_last_duration_seconds = 0.0

# --- Decision Logic ---

def should_rebalance(service, current_node, free_mem_by_node, config, state, container_mem, dependencies, preferred_node=None, debug=False):
    now = datetime.utcnow()
    cooldown = config['default'].get('cooldown_minutes', 15)
    sustained = config['default'].get('sustained_high_minutes', 10)
    threshold = config['default'].get('memory_difference_gb', 2)

    if current_node not in free_mem_by_node:
        return False, None

    total_mem = container_mem.get(service, 0)
    for dep in dependencies.get(service, []):
        total_mem += container_mem.get(dep, 0)

    rebalance_buffer = config['default'].get('rebalance_buffer_gb', DEFAULT_REBALANCE_BUFFER_GB)

    if preferred_node and preferred_node != current_node:
        preferred_mem = free_mem_by_node.get(preferred_node)
        if preferred_mem is not None:
            source_mem = free_mem_by_node[current_node]
            predicted_source_mem = source_mem + total_mem
            predicted_target_mem = preferred_mem - total_mem

            if (predicted_target_mem - predicted_source_mem) >= rebalance_buffer:
                logger.info(f"[rebalance] {service} should move to preferred node {preferred_node} (currently on {current_node})")
                return True, preferred_node

    better_nodes = [n for n, mem in free_mem_by_node.items() if mem - free_mem_by_node[current_node] >= threshold]
    if not better_nodes:
        state.pop(service, None)
        return False, None

    max_delta = max(free_mem_by_node.values()) - min(free_mem_by_node.values())
    if total_mem >= max_delta:
        return False, None

    if service not in state:
        state[service] = {'first_detected': now.isoformat()}
        return False, None

    first_seen = datetime.fromisoformat(state[service]['first_detected'])
    if now - first_seen >= timedelta(minutes=sustained):
        best = max(better_nodes, key=lambda n: free_mem_by_node[n])

        source_mem = free_mem_by_node[current_node]
        target_mem = free_mem_by_node[best]

        predicted_source_mem = source_mem + total_mem
        predicted_target_mem = target_mem - total_mem

        if (predicted_target_mem - predicted_source_mem) >= rebalance_buffer:
            return True, best
        else:
            logger.info(f"[rebalance] Skipping move for {service}: improvement less than {rebalance_buffer} GB after accounting for dependents.")
            return False, None

    return False, None

# --- Async Rebalance Loop ---

async def run_rebalance_loop():
    from core.config import REBALANCE_CONFIG_PATH
    from core.config_loader import load_yaml
    from core.state import load_state, save_state
    from lib.metrics.metrics_helpers import get_node_exporter_memory, get_container_memory_usage
    from core.docker_client import client

    global rebalance_attempts_total, rebalance_success_total, rebalance_failures_total, rebalance_last_duration_seconds

    config = load_yaml(REBALANCE_CONFIG_PATH)
    state = load_state()

    loop_interval = config['default'].get('check_interval_seconds', 60)
    exporters = config.get('node_exporters', {})

    while True:
        logger.info("[rebalance] Checking memory stats for rebalancing decisions...")
        start_time = time()

        free_mem_by_node = {}
        for node, url in exporters.items():
            mem = get_node_exporter_memory(url)
            if mem is not None:
                free_mem_by_node[node] = mem

        if not free_mem_by_node:
            logger.warning("[rebalance] No memory data available. Skipping.")
            await asyncio.sleep(loop_interval)
            continue

        container_mem = get_container_memory_usage()
        dependencies = load_yaml(config['default'].get('dependencies_file', '/etc/swarm-orchestration/dependencies.yml'))

        for service in container_mem.keys():
            try:
                svc_obj = client.services.get(service)
                labels = svc_obj.attrs['Spec'].get('Labels', {})

                if labels.get("orchestration.rebalance", "true").lower() != "true":
                    logger.debug(f"[rebalance] Skipping {service} due to orchestration.rebalance=false")
                    continue

                preferred_node = labels.get("orchestration.preferred.node")

                current_node = None
                tasks = svc_obj.tasks()
                for task in tasks:
                    if task.get('Status', {}).get('State') == 'running':
                        current_node = task.get('NodeID')
                        break

                if not current_node:
                    continue

                if preferred_node and current_node != preferred_node:
                    logger.debug(f"[rebalance] {service} prefers node {preferred_node}. Currently on {current_node}.")

                rebalance_attempts_total += 1

                should_move, target_node = should_rebalance(
                    service, current_node, free_mem_by_node, config, state, container_mem, dependencies, preferred_node=preferred_node
                )

                if should_move and target_node:
                    logger.warning(f"[rebalance] Triggering rebalance of {service} to {target_node}")
                    svc_obj.update(force_update=True)
                    rebalance_success_total += 1
                    state[service]['last_moved'] = datetime.utcnow().isoformat()
                    state[service]['moved_to'] = target_node

            except Exception as e:
                logger.error(f"[rebalance] Failed to evaluate rebalance for {service}: {e}")
                rebalance_failures_total += 1

        rebalance_last_duration_seconds = time() - start_time
        save_state(state)
        await asyncio.sleep(loop_interval)
