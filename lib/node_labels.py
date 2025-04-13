"""
node_labels.py
- Encapsulates logic for discovering which node is running a service and labeling accordingly.
"""

import time

def get_service_node(service, wait_timeout=5):
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        tasks = service.tasks()
        for task in tasks:
            status = task.get("Status", {})
            if status.get("State") == "running":
                return task.get("NodeID")
        time.sleep(1)
    return None
