"""
dependency_loader.py
- Loads dependency YAML definitions used to define anchor -> dependent service mappings.
"""

import yaml

def load_dependencies(path="/etc/swarm-orchestration/dependencies.yml"):
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Failed to load dependencies: {e}")
        return {}
