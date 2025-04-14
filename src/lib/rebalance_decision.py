"""
rebalance_decision.py
- Decision logic to determine if a service should be rebalanced.
"""

from datetime import datetime, timedelta

def should_rebalance(service, current_node, free_mem_by_node, config, state, container_mem, dependencies, debug=False):
    now = datetime.utcnow()

    # Load default and per-service config
    default_cfg = config.get('default', {})
    service_cfg = config.get('services', {}).get(service, {})
    cooldown_minutes = service_cfg.get('cooldown_minutes', default_cfg.get('cooldown_minutes', 15))
    sustained_minutes = service_cfg.get('sustained_high_minutes', default_cfg.get('sustained_high_minutes', 10))
    mem_gap_gb = service_cfg.get('memory_difference_gb', default_cfg.get('memory_difference_gb', 2))

    if debug:
        print(f"[DEBUG] Evaluating {service}: cooldown={cooldown_minutes} min, sustained={sustained_minutes} min, mem_gap={mem_gap_gb} GB")

    last_moved_str = state.get(service, {}).get('last_moved')
    if last_moved_str:
        last_moved = datetime.fromisoformat(last_moved_str)
        if now - last_moved < timedelta(minutes=cooldown_minutes):
            if debug:
                print(f"[DEBUG] {service} in cooldown period (last moved {last_moved})")
            return False, None

    current_mem = free_mem_by_node.get(current_node)
    if current_mem is None:
        if debug:
            print(f"[DEBUG] No memory info for current node {current_node}. Skipping {service}.")
        return False, None

    better_nodes = [node for node, mem in free_mem_by_node.items() if mem - current_mem >= mem_gap_gb]
    if debug:
        print(f"[DEBUG] Nodes with significantly more memory than {current_node}: {better_nodes}")

    if len(better_nodes) >= 2:
        # Calculate total memory used by service group (service + deps)
        total_mem = container_mem.get(service, 0)
        if service in dependencies:
            for dep in dependencies[service]:
                total_mem += container_mem.get(dep, 0)

        max_delta = max(free_mem_by_node.values()) - min(free_mem_by_node.values())
        if total_mem >= max_delta:
            if debug:
                print(f"[DEBUG] {service} group memory ({round(total_mem, 2)} GB) exceeds max delta ({round(max_delta, 2)} GB). Skipping.")
            return False, None

        # Check sustained imbalance detection
        first_seen = state.get(service, {}).get('first_detected')
        if not first_seen:
            state[service] = {'first_detected': now.isoformat()}
            if debug:
                print(f"[DEBUG] First detection of imbalance for {service} at {now}")
            return False, None

        first_detected = datetime.fromisoformat(first_seen)
        if now - first_detected >= timedelta(minutes=sustained_minutes):
            best_node = sorted(better_nodes, key=lambda n: free_mem_by_node[n], reverse=True)[0]
            if debug:
                print(f"[REBALANCE] {service} has sustained imbalance. Best candidate: {best_node}")
            return True, best_node
        else:
            remaining = timedelta(minutes=sustained_minutes) - (now - first_detected)
            if debug:
                print(f"[DEBUG] {service} has not reached sustained threshold. Remaining: {remaining}")
    else:
        if debug:
            print(f"[DEBUG] {service} does not have enough better node candidates.")
        state.pop(service, None)

    return False, None
