"""
label_utils.py
- Encapsulates logic for:
    - Resolving which node a Docker Swarm service is running on
    - Applying and removing node labels through the Docker CLI

Used by label_sync, bootstrap, and rebalance logic for task placement control.
"""

import logging
import time
import subprocess
import docker
from core.docker_client import client
from lib.common.task_diagnostics import log_task_status


def debug_anchor(anchor_service):
    print(f"Debugging anchor service: {anchor_service}")
    try:
        service = client.services.get(anchor_service)
        tasks = service.tasks()
        print(f"Found {len(tasks)} task(s) for {anchor_service}")
        for task in tasks:
            print(f"Task ID: {task['ID']}, State: {task['Status']['State']}, NodeID: {task.get('NodeID')}")
    except Exception as e:
        print(f"Exception while debugging {anchor_service}: {e}")


def apply_label(node_id, key, value="true", dry_run=False):
    try:
        cmd = ["docker", "node", "update", "--label-add", f"{key}={value}", node_id]
        if dry_run:
            logging.info(f"[apply_label] (Dry Run) Would run: {' '.join(cmd)}")
            return
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"[apply_label] Applied label '{key}={value}' to node {node_id}")
    except subprocess.CalledProcessError as e:
        logging.error(f"[apply_label] Failed: {e.stderr.strip()}")
    except Exception as e:
        logging.error(f"[apply_label] Unexpected error: {e}")


def remove_label(node_id, label_key, dry_run=False):
    try:
        cmd = ["docker", "node", "update", "--label-rm", label_key, node_id]
        if dry_run:
            logging.info(f"[remove_label] (Dry Run) Would run: {' '.join(cmd)}")
            return
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"[remove_label] Removed label '{label_key}' from node {node_id}")
    except subprocess.CalledProcessError as e:
        logging.error(f"[remove_label] Failed: {e.stderr.strip()}")
    except Exception as e:
        logging.error(f"[remove_label] Unexpected error: {e}")


def label_anchors(anchor_list, stack_name, dry_run=False, debug=False):
    """
    Applies labels to nodes running anchor services.
    Labels are ONLY cleared or updated when anchors move or go down.
    """
    logging.info("[label_anchors] Updating anchor labels without aggressive clearing.")
    current_anchor_nodes = {}

    for anchor in anchor_list:
        service_name = f"{stack_name}_{anchor}"
        node_id = get_anchor_node_for_labeling(service_name, debug=debug)

        if node_id and node_id != "starting":
            current_anchor_nodes[anchor] = node_id
            logging.info(f"[label_anchors] {anchor} is running on node {node_id}.")
        else:
            logging.warning(f"[label_anchors] {anchor} is down or starting (node_id={node_id}).")

    for node in client.nodes.list():
        node_id = node.id
        labels = node.attrs["Spec"].get("Labels", {})
        hostname = node.attrs["Description"]["Hostname"]

        for anchor in anchor_list:
            anchor_current_node = current_anchor_nodes.get(anchor)

            if labels.get(anchor) and anchor_current_node != node_id:
                reason = "down" if not anchor_current_node else f"moved to {anchor_current_node}"
                logging.info(f"[label_anchors] Removing {anchor}=true from {hostname} ({reason}).")
                if not dry_run:
                    remove_label(node_id, anchor)

            if anchor_current_node == node_id and not labels.get(anchor):
                logging.info(f"[label_anchors] Adding {anchor}=true to {hostname}.")
                if not dry_run:
                    apply_label(node_id, anchor)

    logging.info("[label_anchors] Anchor labels updated correctly.")


def get_anchor_node_for_labeling(service_name, debug=False):
    try:
        service = client.services.get(service_name)
        tasks = service.tasks()
        for task in tasks:
            state = task["Status"]["State"]
            node_id = task.get("NodeID")
            if debug:
                logging.debug(f"[labeling] Task {task['ID']} - State: {state}, NodeID: {node_id}")
            if state == "running" and node_id:
                return node_id
    except docker.errors.NotFound:
        logging.warning(f"[labeling] Anchor service {service_name} not found.")
    except Exception as e:
        logging.error(f"[labeling] Unexpected error for {service_name}: {e}")
    return None


def get_anchor_state_for_failover(service_name, debug=False):
    try:
        service = client.services.get(service_name)
        tasks = service.tasks()
        if not tasks:
            return ("no_tasks", None)

        recent = sorted(tasks, key=lambda t: t["Status"]["Timestamp"], reverse=True)[0]
        state = recent["Status"]["State"]
        node_id = recent.get("NodeID")

        if debug:
            logging.debug(f"[failover] Task {recent['ID']} - State: {state}, NodeID: {node_id}")
        return (state, node_id)
    except docker.errors.NotFound:
        logging.error(f"[failover] Service {service_name} not found.")
        return ("not_found", None)
    except Exception as e:
        logging.error(f"[failover] Error resolving failover state for {service_name}: {e}")
        return ("error", None)
