'''
retry_state.py
- In-memory retry tracking system for service orchestration.
- Centralized logic for retry cooldowns, exponential backoff, and reset conditions.
'''

import time
from collections import defaultdict

# Tracks {service_name: {failures: int, last_attempt: float_timestamp}}
retry_state = defaultdict(lambda: {"failures": 0, "last_attempt": 0})

def should_retry(service_name, retry_intervals):
    """
    Determine whether enough time has passed to retry a failed service update.

    Args:
        service_name (str): The name of the service.
        retry_intervals (list[int]): Cooldown values in seconds per failure count.

    Returns:
        bool: True if retry is permitted, False otherwise.
    """
    now = time.time()
    state = retry_state[service_name]
    failures = state["failures"]
    last = state["last_attempt"]
    delay = retry_intervals[min(failures, len(retry_intervals) - 1)]
    return now - last >= delay

def record_retry(service_name):
    """
    Increment failure count and record the retry timestamp for a service.
    """
    retry_state[service_name]["failures"] += 1
    retry_state[service_name]["last_attempt"] = time.time()

def clear_retry(service_name):
    """
    Reset the retry state for a service (e.g. after successful co-location).
    """
    if service_name in retry_state:
        del retry_state[service_name]
