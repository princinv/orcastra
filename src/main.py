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
    - Mod Manager loop for automatic mod downloads
"""
import asyncio
import os
import sys
from threading import Thread

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

from core.config import DEBUG
from core.docker_client import is_leader_node
from runner import label_sync, rebalance, bootstrap
from lib.sync import label_manager
from lib.rebalance import rebalance_decision
from runner.static_labels import run as run_static_label_sync
from runner.change_detection import run as start_file_watcher
from runner.deploy_node_exporter import deploy as deploy_node_exporter
from runner import gc_prune
from runner import autoheal
from runner import log_rotate
from lib.mods import mod_manager  # <-- NEW

from loguru import logger  # <-- NEW

# OPTIONAL: Only if you have a Sentry DSN
import sentry_sdk
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        send_default_pii=True  # optional: includes user info if available
    )

# --- Logging Setup ---
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG" if DEBUG else "INFO",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# --- FastAPI Server ---
api = FastAPI()

@api.get("/healthz")
async def health():
    return {"status": "ok"}

@api.post("/sync")
async def sync_now():
    await label_manager.main_loop()
    return {"status": "triggered"}

@api.post("/refresh_mods")
async def manual_mod_refresh():
    Thread(target=mod_manager.refresh_mods).start()
    return {"status": "mod_refresh_triggered"}

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
# HELP swarm_orch_leader 1 if this instance is Swarm leader, 0 if follower
# TYPE swarm_orch_leader gauge
# HELP anchor_updates_total Total anchor services label updates
# TYPE anchor_updates_total counter
anchor_updates_total {label_manager.anchor_updates_total}
# HELP dependent_updates_total Total dependent services updated
# TYPE dependent_updates_total counter
dependent_updates_total {label_manager.dependent_updates_total}
# HELP anchor_sync_errors_total Total errors during anchor-dependent sync
# TYPE anchor_sync_errors_total counter
anchor_sync_errors_total {label_manager.anchor_sync_errors_total}
# HELP anchor_sync_last_duration_seconds Duration of last sync in seconds
# TYPE anchor_sync_last_duration_seconds gauge
anchor_sync_last_duration_seconds {label_manager.anchor_sync_last_duration_seconds}
swarm_orch_leader {1 if is_leader_node() else 0}
# Mod Manager Metrics
# HELP mod_downloads_total Total successful mod downloads
# TYPE mod_downloads_total counter
mod_downloads_total {mod_manager.mod_downloads_total}
# HELP mod_download_errors_total Total failed mod downloads
# TYPE mod_download_errors_total counter
mod_download_errors_total {mod_manager.mod_download_errors_total}
# HELP mod_refresh_last_duration_seconds Duration of last mod refresh cycle
# TYPE mod_refresh_last_duration_seconds gauge
mod_refresh_last_duration_seconds {mod_manager.mod_refresh_last_duration_seconds}
""",
        media_type="text/plain"
    )

def start_api():
    uvicorn.run(api, host="0.0.0.0", port=6060)

# --- Start background threads ---
Thread(target=start_api, daemon=True).start()
Thread(target=start_file_watcher, daemon=True).start()
Thread(target=mod_manager.scheduled_mod_refresh, daemon=True).start()  # <-- NEW background loop

# --- Main Async Orchestration ---
async def main():
    try:
        tasks = []

        if is_leader_node():
            logger.info("[swarm-orch] Leadership status: LEADER — running global orchestration tasks.")
            tasks += [
                label_sync.run(),
                bootstrap.run(),
                rebalance.run(),
            ]
        else:
            logger.info("[swarm-orch] Leadership status: FOLLOWER — skipping global orchestration tasks.")

        # Always-run safe tasks
        tasks += [
            gc_prune.run(),
            autoheal.run(),
            log_rotate.run(),
        ]

        await asyncio.gather(*tasks)
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
