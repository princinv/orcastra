"""
Loads YAML configuration files (dependencies, nodes, rebalance_config).
Used across bootstrap, rebalance, and label orchestration.
"""
import yaml

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}
