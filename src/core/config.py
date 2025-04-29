"""
config.py
- Defines global configuration values derived from environment variables.
- Used by all runners and logic modules for shared behavior control.
"""

import os

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("swarm-orch")

# --- Runtime Behavior Flags ---
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"

# --- Stack & Logging ---
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"  # Correct for Loguru string levels

# Optional: configure loguru early if it's available
if "loguru" in globals():
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )

# --- Config Paths ---
SWARM_FILE = os.getenv("SWARM_FILE", "/etc/swarm-orchestration/swarm.yml")
REBALANCE_CONFIG_PATH = os.getenv("REBALANCE_CONFIG", "/etc/swarm-orchestration/rebalance_config.yml")
REBALANCE_STATE_PATH = "/var/lib/swarm-orchestration/rebalance_state.json"
