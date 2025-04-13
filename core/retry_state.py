"""
In-memory retry tracking system with failure count and cooldown logic.
Used to manage staggered updates for stuck or relocating services.
"""
import time
from collections import defaultdict

retry_state = defaultdict(lambda: {"failures": 0, "last_attempt": 0})

def should_retry(service_name, intervals):
    now = time.time()
    state = retry_state[service_name]
    delay = intervals[min(state["failures"], len(intervals) - 1)]
    return now - state["last_attempt"] >= delay

def record_retry(service_name):
    retry_state[service_name]["failures"] += 1
    retry_state[service_name]["last_attempt"] = time.time()

def clear_retry(service_name):
    if service_name in retry_state:
        del retry_state[service_name]
