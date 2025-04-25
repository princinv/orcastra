"""
metrics_scraper.py
- Lightweight wrapper to scrape memory metrics from node_exporter endpoints.
- Used in simple integrations or direct CLI-style testing.
"""

import requests
import logging

def get_node_exporter_memory(url):
    """
    Return available memory in GB from a Prometheus-style node_exporter endpoint.

    Args:
        url (str): Full URL to the metrics endpoint (e.g. http://host:9100/metrics)

    Returns:
        float or None: Available memory in GB, or None on failure.
    """
    try:
        response = requests.get(url, timeout=2)
        lines = response.text.splitlines()
        mem_total = mem_free = 0
        for line in lines:
            if line.startswith("node_memory_MemTotal_bytes"):
                mem_total = float(line.split()[-1])
            elif line.startswith("node_memory_MemAvailable_bytes"):
                mem_free = float(line.split()[-1])
        if mem_total > 0 and mem_free > 0:
            return round(mem_free / (1024**3), 2)
    except Exception as e:
        logging.warning(f"[metrics_scraper] Failed to scrape metrics from {url}: {e}")
    return None
