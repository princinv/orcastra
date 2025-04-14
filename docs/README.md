# 🐳 swarm-orchestration

---

## ORCHA

---

A modular container designed for **orchestrating Docker Swarm service placement**, ensuring **co-location of dependent services**, **automated failover**, and **memory-aware rebalancing** based on real-world resource metrics (via `node_exporter`).

## 🌟 Purpose

Docker Swarm alone doesn’t guarantee that dependent services (e.g., an app and its database) will be scheduled on the same node. This container provides:

- 🔗 **Anchor-following** — ensures dependent services follow their "anchor" (usually a DB).
- ↻ **Auto-restarts** — force-updates services that fail to meet placement constraints.
- 📆 **Label-based orchestration** — updates node labels to reflect current anchor locations.
- 📉 **Resource-aware rebalancing** — migrates services to underutilized nodes using Prometheus metrics.
- ⬆️ **Event and Polling modes** — runs continuously or triggers on container events.
- ⚙️ **Command YAML interface** — easily trigger reconciliations, restarts, pauses, and more.

---

## 🧱 Directory Structure

```bash
swarm-orch/
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
├── commands/                      # CLI-triggerable swarm-orch commands
│   └── swarm-orch.command.yml
├── config/                        # Cluster-specific configuration files
│   ├── dependencies.yml       # Anchor → dependent mappings
│   ├── nodes.yml              # Node definitions, labels, and IPs
│   └── rebalance_config.yml   # Per-service and default rebalance logic
├── docs/                          # License, notes, and published README
│   ├── LICENSE
│   ├── notes.md
│   └── README.md
├── logs/                          # Runtime logs (container-mounted)
│   └── swarm-labels.log
├── scripts/                       # Optional CLI or trigger wrappers
│   └── trigger-bootstrap.sh   # Sends SIGHUP to supervisor process
├── src/                           # Entrypoints and all source code
│   ├── __init__.py
│   ├── bootstrap_swarm.py     # Swarm init/join/promotion & label sync
│   ├── label_sync.py          # Entrypoint wrapper for label_sync_runner
│   ├── rebalance.py           # Rebalancer control loop
│   ├── supervisor.py          # Launches all orchestration threads
│   ├── core/                  # Shared core modules (env/config/state)
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── config_loader.py
│   │   ├── constants.py
│   │   ├── docker_client.py
│   │   ├── retry_state.py
│   │   └── state.py
│   ├── lib/                   # Modular orchestration logic
│   │   ├── __init__.py
│   │   ├── bootstrap_labels.py
│   │   ├── bootstrap_tasks.py
│   │   ├── dependency_loader.py
│   │   ├── docker_helpers.py
│   │   ├── labels.py
│   │   ├── label_sync_runner.py
│   │   ├── metrics.py
│   │   ├── node_labels.py
│   │   ├── rebalance_decision.py
│   │   ├── retries.py
│   │   ├── service_utils.py
│   │   └── ssh_helpers.py
│   └── __pycache__/           # Compiled Python cache (excluded in production)
│       ├── bootstrap_swarm.cpython-312.pyc
│       ├── label_dependencies.cpython-312.pyc
│       ├── label_sync.cpython-312.pyc
│       ├── rebalance.cpython-312.pyc
│       ├── rebalance_services.cpython-312.pyc
│       └── supervisor.cpython-312.pyc
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

## ↻ Runtime Behavior

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

## 🧹 Example Deployment (Docker Compose)

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

## 🎀 Status

- ✅ Fully modularized
- ✅ Multi-threaded entrypoint
- ✅ Docker socket aware
- ✅ YAML-configurable orchestration
- ✅ GHCR-published image

---

## 🐙 Author

Maintained by [@princinv](https://github.com/princinv)  
PRs welcome!
