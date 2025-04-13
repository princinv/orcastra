"""
rebalance_decision.py
- Decision logic to determine if a service should be rebalanced.
"""

from datetime import datetime, timedelta

def should_rebalance(service, current_node, free_mem_by_node, config, state, container_mem, dependencies, debug=False):
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
