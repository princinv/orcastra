#!/usr/bin/env python3
"""
bootstrap.py
- Ensures Docker Swarm is initialized and that all nodes have the correct labels.
- Can be run via main supervisor or manually via CLI.
- Executes node promotion, label syncing, static label syncing, and initial join flow.
"""

import os
import signal
import asyncio
from loguru import logger

from core.config_loader import load_yaml, preview_yaml
from lib.bootstrap.bootstrap_tasks import check_swarm, get_join_token, join_node, get_node_map
from lib.bootstrap.bootstrap_labels import sync_labels
from lib.common.ssh_helpers import is_online, ssh
from runner import static_labels  # Static label sync module

# --- Runtime Environment Variables ---
SWARM_FILE = os.getenv("SWARM_FILE", "/etc/swarm-orchestration/swarm.yml")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
should_run = True

# --- Startup Preview ---
preview_yaml(SWARM_FILE, name="swarm.yml")

def bootstrap_swarm():
    logger.info("[bootstrap] Starting bootstrap sequence...")
    config = load_yaml(SWARM_FILE)
    leader = config.get("leader")
    advertise = config.get("advertise_addr")
    nodes = config.get("nodes", {})
    prune = config.get("options", {}).get("prune_unknown_labels", False)

    if not is_online(advertise):
        logger.warning(f"[bootstrap] Leader {leader} offline at {advertise}, skipping.")
        return False

    if check_swarm(advertise, DEBUG):
        logger.info("[bootstrap] Swarm was not active — initialized.")
    else:
        logger.info("[bootstrap] Swarm already active on leader.")

    token = get_join_token(advertise, DEBUG)
    if not token:
        logger.error("[bootstrap] Failed to retrieve join token.")
        return False

    for name, meta in nodes.items():
        ip = meta["ip"]
        if name == leader:
            logger.debug(f"[bootstrap] Skipping leader {name}")
            continue
        if not is_online(ip):
            logger.warning(f"[bootstrap] Node {name} at {ip} is offline, skipping.")
            continue
        if ssh(ip, "docker info | grep 'Swarm: active'", DEBUG).returncode != 0:
            join_node(ip, token, advertise, DEBUG)
            logger.info(f"[bootstrap] Node {name} joined to Swarm.")
        else:
            logger.debug(f"[bootstrap] Node {name} already in Swarm.")

    node_map = get_node_map(advertise, DEBUG)
    for name in nodes:
        if name in node_map:
            logger.info(f"[bootstrap] Promoting node {name} to manager.")
            ssh(advertise, f"docker node promote {node_map[name]}", DEBUG)
        else:
            logger.warning(f"[bootstrap] Skipping promotion — {name} not found in node_map.")

    logger.info("[bootstrap] Applying bootstrap-time dynamic labels...")
    sync_labels(advertise, nodes, node_map, prune=prune, dry_run=DRY_RUN, debug=DEBUG)

    logger.info("[bootstrap] Running static label sync via SDK...")
    try:
        static_labels.run()
        logger.info("[bootstrap] Static label sync completed successfully.")
    except Exception as e:
        logger.exception(f"[bootstrap] Static label sync failed: {e}")

    return True

def sighup_handler(signum, frame):
    logger.info("📣 SIGHUP received — re-running bootstrap...")
    bootstrap_swarm()

async def run():
    signal.signal(signal.SIGHUP, sighup_handler)
    if RUN_ONCE:
        logger.info("[bootstrap] RUN_ONCE=true — running bootstrap once.")
        bootstrap_swarm()
    else:
        logger.info(f"[bootstrap] Starting loop every {LOOP_INTERVAL} seconds...")
        while should_run:
            bootstrap_swarm()
            await asyncio.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    asyncio.run(run())
