#!/usr/bin/env python3
"""
main.py
- Main asynchronous entrypoint for the swarm-orch container.
- Launches:
    - Label sync loop: ensures dependent services follow anchors
    - Bootstrap loop: keeps Swarm initialized and labels applied
    - Rebalance loop: memory-aware service redistribution
"""

import asyncio
from runner import label_sync, rebalance, bootstrap
from core.config import DEBUG
import logging

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from fastapi import FastAPI
from threading import Thread
import uvicorn

api = FastAPI()

@api.get("/healthz")
async def health():
    return {"status": "ok"}

@api.post("/sync")
async def sync_now():
    from lib.sync import label_manager
    await label_manager.main_loop()  # runs 1 pass only
    return {"status": "triggered"}

def start_api():
    uvicorn.run(api, host="0.0.0.0", port=8080)

# Start FastAPI in background thread before main loop
Thread(target=start_api, daemon=True).start()

async def main():
    try:
        await asyncio.gather(
            label_sync.run(),
            bootstrap.run(),
            rebalance.run()
        )
    except asyncio.CancelledError:
        print("📴 Shutting down orchestrators cleanly...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 KeyboardInterrupt received. Exiting.")
