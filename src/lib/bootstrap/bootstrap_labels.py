"""
bootstrap_labels.py
- Reconciles Docker Swarm node labels with the expected values defined in nodes.yml.
- Executes label updates remotely over SSH via the Swarm leader.
- Optionally prunes stale labels.

Used by bootstrap_runner.py to apply label consistency on Swarm startup or rebalance.
"""

import yaml
from loguru import logger
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
    logger.info("[labels] Starting bootstrap-time label reconciliation...")

    for name, meta in nodes.items():
        if name not in node_map:
            logger.warning(f"[labels] Skipping {name}: not found in node_map.")
            continue

        labels = set(meta.get("labels", []))
        logger.debug(f"[labels] Desired labels for {name}: {sorted(labels)}")

        cmd = f"docker node inspect {name} --format '{{{{json .Spec.Labels}}}}'"
        result = ssh(advertise, cmd, debug=debug)
        current = result.stdout.strip()

        try:
            current_labels = yaml.safe_load(current) or {}
        except Exception as e:
            logger.error(f"[labels] Failed to parse labels for {name}: {e}")
            current_labels = {}

        logger.debug(f"[labels] Current labels on {name}: {current_labels}")

        # Add missing or incorrect labels
        for label in labels:
            if current_labels.get(label) != "true":
                if dry_run:
                    logger.info(f"[labels] (Dry Run) Would add {label}=true to {name}")
                else:
                    ssh(advertise, f"docker node update --label-add {label}=true {name}", debug=debug)
                    logger.info(f"[labels] Added {label}=true to {name}")

        # Optionally remove extra labels
        if prune:
            for label in current_labels:
                if label not in labels and label != name:
                    if dry_run:
                        logger.info(f"[labels] (Dry Run) Would remove label {label} from {name}")
                    else:
                        ssh(advertise, f"docker node update --label-rm {label} {name}", debug=debug)
                        logger.info(f"[labels] Removed label {label} from {name}")

    logger.info("[labels] Label reconciliation complete.")
