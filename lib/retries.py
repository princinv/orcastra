"""
retries.py
- Central logic to record retry failures and determine if a retry is allowed.
"""

import time
from collections import defaultdict

retry_state = defaultdict(lambda: {"failures": 0, "last_attempt": 0})

def should_retry(service_name, retry_intervals):
    now = time.time()
    state = retry_state[service_name]
    failures = state["failures"]
    last = state["last_attempt"]
    interval = retry_intervals[min(failures, len(retry_intervals) - 1)]
    return now - last >= interval

def record_retry(service_name):
    retry_state[service_name]["failures"] += 1
    retry_state[service_name]["last_attempt"] = time.time()

def clear_retry(service_name):
    if service_name in retry_state:
        del retry_state[service_name]
