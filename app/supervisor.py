# app/supervisor.py
# Entry point for the container that launches all core scripts in parallel.
# This script spawns threads for:
#   - label_dependencies (handles anchor/dependent label management)
#   - bootstrap_swarm (ensures nodes are correctly labeled and joined)
#   - rebalance_services (performs memory-aware service rebalancing)

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
