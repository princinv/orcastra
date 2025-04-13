"""
metrics_scraper.py
- Contains functions to scrape Node Exporter metrics or Docker stats output for memory info.
"""

import requests

def get_node_exporter_memory(url):
    try:
        response = requests.get(url, timeout=2)
        lines = response.text.split('\n')
        mem_total = mem_free = 0
        for line in lines:
            if line.startswith("node_memory_MemTotal_bytes"):
                mem_total = float(line.split()[-1])
            elif line.startswith("node_memory_MemAvailable_bytes"):
                mem_free = float(line.split()[-1])
        if mem_total and mem_free:
            return round(mem_free / (1024**3), 2)
    except Exception as e:
        print(f"Failed to scrape metrics: {e}")
    return None
