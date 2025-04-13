"""
Holds global environment configuration values, derived from os.environ.
These are shared across scripts to maintain consistency.
"""
import os
import logging

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

DEPENDENCIES_FILE = os.getenv("DEPENDENCIES_FILE", "/etc/swarm-orchestration/dependencies.yml")
REBALANCE_CONFIG_PATH = os.getenv("REBALANCE_CONFIG", "/config/rebalance_config.yml")
REBALANCE_STATE_PATH = "/var/lib/swarm-orchestration/rebalance_state.json"
