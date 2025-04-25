"""
config_loader.py
- Loads and previews YAML configuration files used by orchestration modules.
- Supports dependencies.yml, nodes.yml, and rebalance_config.yml.
"""

import os
import yaml
import logging

def load_yaml(path):
    """Safely load a YAML file and return a parsed dict. Returns {} on failure."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.error(f"[load_yaml] Failed to load {path}: {e}")
        return {}

def preview_yaml(path, name=None):
    """
    Print a human-readable preview of the YAML file contents for debugging.
    Typically used during startup to verify config presence and structure.
    """
    if not os.path.exists(path):
        logging.warning(f"[config] File not found: {path}")
        return

    try:
        with open(path, "r") as f:
            contents = f.read()
            logging.info(f"\n📄 Loaded {name or path}:\n" + "\n".join(f"│ {line}" for line in contents.strip().splitlines()))
    except Exception as e:
        logging.error(f"[config] Could not preview {path}: {e}")
