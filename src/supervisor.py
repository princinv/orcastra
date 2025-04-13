# src/supervisor.py

"""
Entry point for the swarm-orch container.
Launches:
- label_sync: ensures dependent services follow anchors
- bootstrap_swarm: keeps Swarm initialized and nodes labeled
- rebalance: memory-aware service distribution
"""

import threading
import bootstrap_swarm
import label_sync
import rebalance


def run_label_sync():
    label_sync.run()

def run_bootstrap():
    bootstrap_swarm.run()

def run_rebalance():
    rebalance.run()

threads = [
    threading.Thread(target=run_label_sync),
    threading.Thread(target=run_bootstrap),
    threading.Thread(target=run_rebalance),
]

for t in threads:
    t.start()

for t in threads:
    t.join()
