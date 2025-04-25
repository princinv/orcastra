"""
state.py
- Loads and saves persistent rebalance state to disk for long-term tracking.
- Stores metadata such as:
    - first_detected: When imbalance was first detected
    - last_moved: Timestamp of last service movement
    - moved_to: Target node ID or hostname

Used by rebalance orchestrator to apply cooldowns and avoid flapping.
"""

import json
from pathlib import Path
from core.config import REBALANCE_STATE_PATH

def load_state():
    """
    Load rebalance state from disk (JSON file).
    
    Returns:
        dict: Parsed state dictionary, or {} if no file exists.
    """
    if Path(REBALANCE_STATE_PATH).exists():
        with open(REBALANCE_STATE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    """
    Save rebalance state to disk as formatted JSON.
    
    Args:
        state (dict): The current rebalance state to persist.
    """
    Path(REBALANCE_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(REBALANCE_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
