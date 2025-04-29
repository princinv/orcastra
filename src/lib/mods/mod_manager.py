#!/usr/bin/env python3
"""
mod_manager.py
- Periodically inspects running containers for mod labels and downloads mods into /modcache.
- Matches LinuxServer docker-modmanager automatic behavior.
- Exposes Prometheus metrics.
"""

import os
import logging
import requests
import time
from datetime import datetime
from core.docker_client import client

# --- Config ---
DEST_DIR = os.getenv("MOD_MANAGER_DEST", "/modcache")
REFRESH_INTERVAL_MINUTES = int(os.getenv("MOD_MANAGER_REFRESH_INTERVAL_MINUTES", "6"))
DOWNLOAD_RETRIES = 3
TIMEOUT_SECONDS = 30

# --- Metrics ---
mod_downloads_total = 0
mod_download_errors_total = 0
mod_refresh_last_duration_seconds = 0.0

# --- Core Functions ---

def discover_mods_from_containers():
    mods = []

    for container in client.containers.list():
        labels = container.labels or {}
        for key, value in labels.items():
            if key.startswith("com.linuxserver.mod.") and value:
                mods.append(value.strip())

    return mods

def download_file(url, dest_folder, retries=DOWNLOAD_RETRIES):
    global mod_downloads_total, mod_download_errors_total

    os.makedirs(dest_folder, exist_ok=True)
    filename = url.split("/")[-1]
    dest_path = os.path.join(dest_folder, filename)

    for attempt in range(retries):
        try:
            logging.info(f"[mod_manager] Downloading {url} → {dest_path}")
            response = requests.get(url, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(response.content)
            logging.info(f"[mod_manager] ✅ Successfully downloaded {filename}")
            mod_downloads_total += 1
            return
        except Exception as e:
            logging.warning(f"[mod_manager] ⚠️ Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(5)

    logging.error(f"[mod_manager] ❌ Failed to download {url} after {retries} attempts.")
    mod_download_errors_total += 1

def refresh_mods():
    global mod_refresh_last_duration_seconds

    start_time = datetime.utcnow()

    mods = discover_mods_from_containers()
    if not mods:
        logging.info("[mod_manager] No mod labels found.")
        mod_refresh_last_duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        return

    logging.info(f"[mod_manager] Found {len(mods)} mod(s) to download.")

    for mod_url in mods:
        download_file(mod_url, DEST_DIR)

    mod_refresh_last_duration_seconds = (datetime.utcnow() - start_time).total_seconds()

def scheduled_mod_refresh():
    while True:
        try:
            logging.info("[mod_manager] Running scheduled mod refresh...")
            refresh_mods()
        except Exception as e:
            logging.error(f"[mod_manager] Unexpected error during mod refresh: {e}")
        logging.info(f"[mod_manager] Sleeping {REFRESH_INTERVAL_MINUTES} minutes...")
        time.sleep(REFRESH_INTERVAL_MINUTES * 60)
