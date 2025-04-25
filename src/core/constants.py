"""
constants.py
- Project-wide constants shared across logic and runner scripts.
- Includes retry intervals, debounce timers, and other tuned values.
"""

# --- Retry Timing Defaults ---
DEFAULT_RETRY_INTERVALS = [2, 10, 60, 300, 900]  # in seconds

# --- Polling Debounce ---
DEBOUNCE_TIME = 5  # seconds between rechecks (used in metric polling)
