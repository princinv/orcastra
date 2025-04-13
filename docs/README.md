# 🐳 swarm-orchestration

---

## ORCHA

---

A modular container designed for **orchestrating Docker Swarm service placement**, ensuring **co-location of dependent services**, **automated failover**, and **memory-aware rebalancing** based on real-world resource metrics (via `node_exporter`).

## 🎯 Purpose

Docker Swarm alone doesn’t guarantee that dependent services (e.g., an app and its database) will be scheduled on the same node. This container provides:

- 🔗 **Anchor-following** — ensures dependent services follow their "anchor" (usually a DB).
- 🔁 **Auto-restarts** — force-updates services that fail to meet placement constraints.
- 📦 **Label-based orchestration** — updates node labels to reflect current anchor locations.
- 📉 **Resource-aware rebalancing** — migrates services to underutilized nodes using Prometheus metrics.
- ⬆️ **Event and Polling modes** — runs continuously or triggers on container events.
- ⚙️ **Command YAML interface** — easily trigger reconciliations, restarts, pauses, and more.

---

## 🧱 Directory Structure

```bash
swarm-orch/
├── Dockerfile
├── requirements.txt
├── src/                        # Main entrypoint + orchestrator threads
│   ├── bootstrap_swarm.py     # Joins/labels all swarm nodes, ensures correct Swarm state
│   ├── label_sync.py          # Anchor-dependency logic, placement decisions, and retries
│   ├── rebalance.py           # Memory-aware service rebalancer (uses node_exporter)
│   └── supervisor.py          # Launches all modules in parallel
├── core/                      # Global helpers and state
│   ├── config.py              # ENV loader and default constants
│   ├── config_loader.py       # Shared YAML config loading
│   ├── constants.py           # Shared string constants (future use)
│   ├── docker_client.py       # Docker SDK setup
│   ├── retry_state.py         # Retry tracking for placement enforcement
│   └── state.py               # JSON state persistence (used by rebalance)
├── lib/                       # Modular logic
│   ├── bootstrap_labels.py    # Adds/removes swarm labels based on config
│   ├── bootstrap_tasks.py     # Swarm join/promotion/leader logic
│   ├── dependency_loader.py   # Parses dependencies.yml (anchor → dependents)
│   ├── docker_helpers.py      # Subprocess calls for service/node info
│   ├── labels.py              # High-level label actions used by orchestrators
│   ├── metrics_scraper.py     # Pulls metrics from node_exporter
│   ├── node_labels.py         # Determines where services should run
│   ├── rebalance_decision.py  # Logic to determine rebalance eligibility
│   ├── retries.py             # Retry helper used across modules
│   ├── service_update.py      # Performs rolling updates using Docker API
│   └── ssh_helpers.py         # Runs SSH commands (used in bootstrap)
├── config/                    # Runtime configuration
│   ├── dependencies.yml       # Anchor ↔ dependent mappings
│   ├── nodes.yml              # Node metadata (hostnames, IPs, labels)
│   └── rebalance_config.yml   # Per-service and global rebalance settings
└── logs/
    └── swarm-labels.log
```

---

## ⚙️ Features & Modes

### Anchor/Dependent Sync (`label_sync.py`)

- Marks the node running the anchor with a label like `gitea_db=true`.
- Forces a rolling update on dependents if not co-located or failed to start.
- Skips restarts if within retry cooldown.

### Bootstrap Swarm (`bootstrap_swarm.py`)

- Ensures all nodes have joined the Swarm and are promoted as managers.
- Syncs node labels based on `nodes.yml`.
- Uses `ssh` and `ping` to remotely control Swarm from the leader.

### Rebalance Services (`rebalance.py`)

- Uses `node_exporter` to determine free memory on each node.
- Moves services if a significantly better node is underutilized.
- Includes global and per-service cooldowns, thresholds, and dependencies.

---

## 🔁 Runtime Behavior

### Entry Point: `supervisor.py`

This script runs all three components concurrently using Python `threading`:

```python
import threading
from src import bootstrap_swarm, label_sync, rebalance

# Launch all three orchestrators
for fn in [bootstrap_swarm.run, label_sync.run, rebalance.run]:
    threading.Thread(target=fn).start()
```

---

## 🧚‍♂️ Example Deployment (Docker Compose)

```yaml
services:
  swarm-orch:
    image: ghcr.io/princinv/swarm-orch:0.1.1
    environment:
      - STACK_NAME=swarm-dev
      - DEBUG=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/etc/swarm-orchestration:ro
```

---

## 🚀 Supported ENV Vars

| Variable            | Default                                        | Description                             |
|---------------------|------------------------------------------------|-----------------------------------------|
| `STACK_NAME`        | `swarm-dev`                                    | Compose/Swarm stack prefix              |
| `DEPENDENCIES_FILE` | `/etc/swarm-orchestration/dependencies.yml`   | Dependency mapping                      |
| `REBALANCE_CONFIG`  | `/etc/swarm-orchestration/rebalance_config.yml` | Rebalance settings                    |
| `NODES_FILE`        | `/etc/swarm-orchestration/nodes.yml`          | Node bootstrap info                     |
| `DRY_RUN`           | `false`                                        | Simulate actions                        |
| `RUN_ONCE`          | `false`                                        | Only run one cycle                      |
| `EVENT_MODE`        | `false`                                        | Enable Docker socket watch             |
| `POLLING_MODE`      | `true`                                         | Re-evaluate every interval              |
| `RELABEL_TIME`      | `60`                                           | Polling loop interval (in seconds)      |
| `DEBUG`             | `false`                                        | Enable debug output                     |

---

## 🌟 Status

- ✅ Fully modularized
- ✅ Multi-threaded entrypoint
- ✅ Docker socket aware
- ✅ YAML-configurable orchestration
- ✅ GHCR-published image

---

## 🐙 Author

Maintained by [@princinv](https://github.com/princinv)  
PRs welcome!
