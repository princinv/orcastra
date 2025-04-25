"""
bootstrap_labels.py
- Reconciles Docker Swarm node labels with the expected values defined in nodes.yml.
- Executes label updates remotely over SSH via the Swarm leader.
- Optionally prunes stale labels.

Used by bootstrap_runner.py to apply label consistency on Swarm startup or rebalance.
"""

import yaml
from lib.common.ssh_helpers import ssh

def sync_labels(advertise, nodes, node_map, prune=False, dry_run=False, debug=False):
    """
    Ensure each Swarm node has its expected labels.

    Args:
        advertise (str): IP or hostname of the Swarm leader (to SSH into).
        nodes (dict): Parsed config of all nodes and their labels.
        node_map (dict): Map of node names to their Docker Swarm ID.
        prune (bool): If True, remove labels that shouldn't be there.
        dry_run (bool): If True, only print actions without executing them.
        debug (bool): If True, pass --debug output to ssh wrapper.
    """
    for name, meta in nodes.items():
        if name not in node_map:
            continue

        labels = set(meta.get("labels", []))
        cmd = f"docker node inspect {name} --format '{{{{json .Spec.Labels}}}}'"
        current = ssh(advertise, cmd, debug=debug).stdout.strip()

        try:
            current_labels = yaml.safe_load(current) or {}
        except Exception:
            current_labels = {}

        # Add missing labels
        for label in labels:
            if current_labels.get(label) != "true":
                if not dry_run:
                    ssh(advertise, f"docker node update --label-add {label}=true {name}", debug=debug)
                print(f"[labels] Added {label}=true to {name}")

        # Optionally remove extra labels
        if prune:
            for label in current_labels:
                if label not in labels and label != name:
                    if not dry_run:
                        ssh(advertise, f"docker node update --label-rm {label} {name}", debug=debug)
                    print(f"[labels] Removed label {label} from {name}")
