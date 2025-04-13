"""
Shared functions to load and save persistent rebalance state on disk.
Stores `first_detected`, `last_moved`, and `moved_to` metadata.
"""
import json
from pathlib import Path
from core.config import REBALANCE_STATE_PATH

def load_state():
    if Path(REBALANCE_STATE_PATH).exists():
        with open(REBALANCE_STATE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    Path(REBALANCE_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(REBALANCE_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
