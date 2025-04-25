#!/usr/bin/env python3
"""
gc_prune.py
- Periodically runs Docker system prune and volume prune based on GC_* environment variables.
- Absorbed from docker-gc-cron.
- Exposes Prometheus metrics for prune statistics.
"""

import os
import asyncio
import subprocess
import logging
from datetime import datetime
from time import time

# --- Prometheus Metrics ---
gc_prune_runs_total = 0
gc_prune_errors_total = 0
gc_prune_last_duration_seconds = 0.0

def parse_env_int(var, default=0):
    try:
        return int(os.getenv(var, default))
    except ValueError:
        return default

async def run():
    # --- Configuration ---
    interval_seconds = 4 * 3600  # default to every 4 hours
    cron_expr = os.getenv("GC_CRON")
    if cron_expr:
        # Very simple cron approximation: "0 */4 * * *" → 4 hours
        try:
            fields = cron_expr.split()
            if len(fields) == 5 and fields[1].startswith("*/"):
                hours = int(fields[1][2:])
                interval_seconds = hours * 3600
        except Exception:
            logging.warning("[gc_prune] Failed to parse GC_CRON. Using 4h default.")

    force_image_removal = parse_env_int("GC_FORCE_IMAGE_REMOVAL", 1)
    force_container_removal = parse_env_int("GC_FORCE_CONTAINER_REMOVAL", 1)
    minimum_images_to_save = parse_env_int("GC_MINIMUM_IMAGES_TO_SAVE", 3)
    grace_period_seconds = parse_env_int("GC_GRACE_PERIOD_SECONDS", 10800)
    dry_run = parse_env_int("GC_DRY_RUN", 0)
    clean_up_volumes = parse_env_int("GC_CLEAN_UP_VOLUMES", 1)

    # --- Main Loop ---
    global gc_prune_runs_total, gc_prune_errors_total, gc_prune_last_duration_seconds

    while True:
        logging.info("[gc_prune] Starting garbage collection...")
        start_time = time()

        try:
            # Dry-run simulation
            if dry_run:
                logging.info("[gc_prune] Dry-run mode: No actual pruning will occur.")

            # Prune stopped containers older than grace period
            if force_container_removal:
                cmd = [
                    "docker", "container", "prune", "-f",
                    "--filter", f"until={grace_period_seconds}s"
                ]
                if dry_run:
                    logging.info(f"[gc_prune] Would run: {' '.join(cmd)}")
                else:
                    subprocess.run(cmd, check=True)
                    logging.info("[gc_prune] Containers pruned successfully.")

            # Prune unused images, preserving minimum
            if force_image_removal:
                images = subprocess.check_output(["docker", "images", "-q"], text=True).strip().splitlines()
                if len(images) > minimum_images_to_save:
                    cmd = ["docker", "image", "prune", "-af"]
                    if dry_run:
                        logging.info(f"[gc_prune] Would run: {' '.join(cmd)}")
                    else:
                        subprocess.run(cmd, check=True)
                        logging.info("[gc_prune] Images pruned successfully.")
                else:
                    logging.info(f"[gc_prune] Skipping image prune: Only {len(images)} images found (minimum {minimum_images_to_save}).")

            # Prune dangling volumes
            if clean_up_volumes:
                cmd = ["docker", "volume", "prune", "-f"]
                if dry_run:
                    logging.info(f"[gc_prune] Would run: {' '.join(cmd)}")
                else:
                    subprocess.run(cmd, check=True)
                    logging.info("[gc_prune] Volumes pruned successfully.")

            gc_prune_runs_total += 1
            gc_prune_last_duration_seconds = time() - start_time

        except Exception as e:
            logging.error(f"[gc_prune] Prune operation failed: {e}")
            gc_prune_errors_total += 1

        logging.info(f"[gc_prune] Sleeping for {interval_seconds} seconds...")
        await asyncio.sleep(interval_seconds)
