#!/usr/bin/env python3
"""
Entrypoint script for running the service rebalancer.

Delegates all logic to `lib.rebalance_decision`, `lib.metrics_scraper`, and `core.state`.
"""

from lib.rebalance_decision import run_rebalance_loop

if __name__ == "__main__":
    run_rebalance_loop()
