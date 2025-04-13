"""
node_labels.py
- Determines which node a given service is running on.
- Also includes logic for labeling nodes that run anchor services.
"""

from core.docker_client import client
from lib.labels import apply_label
from lib.docker_helpers import get_service_node


def label_anchors(anchor_list, stack_name, dry_run=False, debug=False):
    """
    Applies a label like gitea_db=true to the node currently running that service.
    """
    for anchor in anchor_list:
        service_name = f"{stack_name}_{anchor}"
        node_id = get_service_node(service_name, debug=debug)
        if not node_id or node_id == "starting":
            if debug:
                print(f"[label_anchors] {service_name} is not ready.")
            continue
        apply_label(client, node_id, anchor, dry_run=dry_run)
        if debug:
            print(f"[label_anchors] Applied {anchor}=true to node {node_id}")
