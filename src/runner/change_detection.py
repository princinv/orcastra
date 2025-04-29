#!/usr/bin/env python3
"""
change_detection.py
- Watches key config files (nodes.yml, dependencies.yml, rebalance_config.yml)
- Triggers appropriate handlers when changes are detected.
- Includes debouncing to avoid rapid repeated triggers.
"""

import time
from loguru import logger
from pathlib import Path
from threading import Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from runner.static_labels import run as sync_static_labels
from lib.sync.label_manager import main_loop as sync_dynamic_labels
from core.config import SWARM_FILE, REBALANCE_CONFIG_PATH
from core.constants import DEBOUNCE_TIME

CONFIG_DIR = Path("/etc/swarm-orchestration")

WATCHED_FILES = {
    CONFIG_DIR / "swarm.yml": lambda: (sync_static_labels(), sync_dynamic_labels()),
    Path(REBALANCE_CONFIG_PATH): lambda: logger.info("[watcher] Rebalance config changed (hook not implemented)")
}

debounce_tracker = {}
debounce_lock = Lock()

class ConfigChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        path = Path(event.src_path)
        if path not in WATCHED_FILES:
            return

        now = time.time()
        with debounce_lock:
            last_trigger = debounce_tracker.get(path, 0)
            if now - last_trigger < DEBOUNCE_TIME:
                logger.debug(f"[watcher] Debounced {path.name} (last trigger {now - last_trigger:.2f}s ago)")
                return
            debounce_tracker[path] = now

        logger.info(f"[watcher] Detected change in {path.name}, triggering handler.")
        try:
            WATCHED_FILES[path]()
        except Exception as e:
            logger.error(f"[watcher] Failed to handle {path.name}: {e}")

def run():
    observer = Observer()
    handler = ConfigChangeHandler()
    observer.schedule(handler, str(CONFIG_DIR), recursive=False)
    observer.start()
    logger.info("[watcher] Watching YAML files for changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
