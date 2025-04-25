#!/usr/bin/env python3
"""
rebalance.py
- Entrypoint script for triggering memory-aware service rebalancing logic.
- Delegates orchestration to the decision engine and metrics system.
- Can be run via supervisor, CLI, or docker exec interface.
"""

import asyncio
from lib.rebalance.rebalance_decision import run_rebalance_loop

async def run():
    """
    Start the memory-based rebalance loop asynchronously.
    """
    await run_rebalance_loop()

if __name__ == "__main__":
    asyncio.run(run())
