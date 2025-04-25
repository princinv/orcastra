#!/usr/bin/env python3
"""
main.py
- Main asynchronous entrypoint for the swarm-orch container.
- Launches:
    - Label sync loop: ensures dependent services follow anchors
    - Bootstrap loop: keeps Swarm initialized and labels applied
    - Rebalance loop: memory-aware service redistribution
    - Garbage Collection loop with Prometheus metrics
    - Autoheal loop for unhealthy containers
    - Node Exporter deployment at startup
"""

import asyncio
import logging
from threading import Thread

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

from core.config import DEBUG
from runner import label_sync, rebalance, bootstrap
from runner.static_labels import run as run_static_label_sync
from runner.change_detection import run as start_file_watcher
from runner.deploy_node_exporter import deploy as deploy_node_exporter
from runner import gc_prune
from runner import rebalance_decision
from runner import autoheal

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# --- FastAPI Server ---
api = FastAPI()

@api.get("/healthz")
async def health():
    return {"status": "ok"}

@api.post("/sync")
async def sync_now():
    from lib.sync import label_manager
    await label_manager.main_loop()  # runs 1 pass only
    return {"status": "triggered"}

@api.get("/metrics")
async def metrics():
    return PlainTextResponse(
        f"""# HELP gc_prune_runs_total Total successful GC prune runs
# TYPE gc_prune_runs_total counter
gc_prune_runs_total {gc_prune.gc_prune_runs_total}
# HELP gc_prune_errors_total Total GC prune errors
# TYPE gc_prune_errors_total counter
gc_prune_errors_total {gc_prune.gc_prune_errors_total}
# HELP gc_prune_last_duration_seconds Last GC prune operation duration in seconds
# TYPE gc_prune_last_duration_seconds gauge
gc_prune_last_duration_seconds {gc_prune.gc_prune_last_duration_seconds}
# HELP rebalance_attempts_total Total rebalance evaluation attempts
# TYPE rebalance_attempts_total counter
rebalance_attempts_total {rebalance_decision.rebalance_attempts_total}
# HELP rebalance_success_total Successful service rebalances
# TYPE rebalance_success_total counter
rebalance_success_total {rebalance_decision.rebalance_success_total}
# HELP rebalance_failures_total Failed service rebalances
# TYPE rebalance_failures_total counter
rebalance_failures_total {rebalance_decision.rebalance_failures_total}
# HELP rebalance_last_duration_seconds Last rebalance loop duration in seconds
# TYPE rebalance_last_duration_seconds gauge
rebalance_last_duration_seconds {rebalance_decision.rebalance_last_duration_seconds}
# HELP autoheal_attempts_total Total autoheal attempts on unhealthy containers
# TYPE autoheal_attempts_total counter
autoheal_attempts_total {autoheal.autoheal_attempts_total}
# HELP autoheal_success_total Successful autoheal operations
# TYPE autoheal_success_total counter
autoheal_success_total {autoheal.autoheal_success_total}
# HELP autoheal_failures_total Failed autoheal operations
# TYPE autoheal_failures_total counter
autoheal_failures_total {autoheal.autoheal_failures_total}
""",
        media_type="text/plain"
    )

def start_api():
    uvicorn.run(api, host="0.0.0.0", port=8080)

# --- Start background threads ---
Thread(target=start_api, daemon=True).start()
Thread(target=start_file_watcher, daemon=True).start()

# --- Main Async Orchestration ---
async def main():
    try:
        await asyncio.gather(
            label_sync.run(),
            bootstrap.run(),
            rebalance.run(),
            gc_prune.run(),
            autoheal.run(),
        )
    except asyncio.CancelledError:
        print("📴 Shutting down orchestrators cleanly...")

if __name__ == "__main__":
    try:
        # Static labels one-time run at startup
        run_static_label_sync()
        # Node Exporter one-time deploy at startup
        deploy_node_exporter()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 KeyboardInterrupt received. Exiting.")
