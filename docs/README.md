# Orcastra: Swarm Orchestration Container

<img src="https://raw.githubusercontent.com/princinv/assets/main/orcastra_banner.png" alt="Orcastra Banner" width="100%" />

---

## What is Orcastra?

Orcastra is a modular container designed for advanced Docker Swarm orchestration — ensuring co-location of dependent services, dynamic failover recovery, real-world memory-aware rebalancing, continuous Swarm label reconciliation, and periodic mod download management.

It extends Docker Swarm into a fully autonomous, dependency-aware, resource-driven orchestrator.

---

## Core Features

| Feature | Description |
|:--------|:------------|
| Anchor-following | Ensures dependent services follow their "anchor" (e.g., an app colocates with its database). |
| Auto-restarts | Automatically restarts services that violate placement constraints, with retry cooldowns. |
| Node label management | Dynamically labels nodes based on anchor presence and maintains static labels from configuration. |
| Memory-aware rebalancing | Continuously evaluates node memory and relocates services if better nodes are available. |
| Event and polling modes | Supports event-driven updates (planned) and periodic polling-based reconciliation (active). |
| Command YAML interface | Allows manual triggering of syncs, restarts, or reboots through a simple YAML file. |
| Swarm bootstrap and healing | Auto-joins missing nodes, promotes managers, corrects labels on recovery. |
| Mod Manager integration | Periodically downloads and refreshes mod files into a designated `modcache` directory. |
| Autoheal, GC, log rotation | Optional utilities to maintain container and log hygiene. |

---

## Directory Overview

```bash
.
├── assets
├── config
│   ├── dependencies.yml
│   ├── logrotate.d
│   │   └── default.conf
│   ├── node_exporter_deploy.yml
│   ├── nodes.yml
│   └── rebalance_config.yml
├── Dockerfile
├── docs
│   ├── LICENSE
│   ├── notes.md
│   └── README.md
├── scripts
│   └── trigger-bootstrap.sh
└── src
    ├── cli
    │   └── entrypoint.py
    ├── commands
    │   └── swarm-orch.command.yml
    ├── core
    │   ├── config_loader.py
    │   ├── config.py
    │   ├── constants.py
    │   ├── docker_client.py
    │   ├── retry_state.py
    │   └── state.py
    ├── lib
    │   ├── bootstrap
    │   │   ├── bootstrap_labels.py
    │   │   └── bootstrap_tasks.py
    │   ├── common
    │   │   ├── docker_helpers.py
    │   │   ├── service_helpers.py
    │   │   ├── ssh_helpers.py
    │   │   └── task_diagnostics.py
    │   ├── metrics
    │   │   ├── metrics_helpers.py
    │   │   └── metrics_scraper.py
    │   ├── mods
    │   │   └── mod_manager.py
    │   ├── rebalance
    │   │   └── rebalance_decision.py
    │   └── sync
    │       ├── label_manager.py
    │       └── label_utils.py
    ├── main.py
    ├── requirements.txt
    ├── runner
    │   ├── autoheal.py
    │   ├── bootstrap.py
    │   ├── change_detection.py
    │   ├── deploy_node_exporter.py
    │   ├── gc_prune.py
    │   ├── label_sync.py
    │   ├── log_rotate.py
    │   ├── rebalance.py
    │   └── static_labels.py
    └── utils
        └── healthcheck.py
```

---

## Main Runners

| Script | Purpose |
|:-------|:--------|
| bootstrap.py | Ensures Swarm is initialized, nodes are promoted, labels are synced. |
| label_sync.py | Maintains anchor-based placement and updates dependent services. |
| rebalance.py | Moves services between nodes based on memory pressure. |
| static_labels.py | Syncs persistent labels defined in `nodes.yml`. |
| mod_manager.py | Periodically downloads mod files into a modcache destination. |
| autoheal.py | Monitors and restarts unhealthy containers. |
| log_rotate.py | Performs container-internal log rotations. |
| deploy_node_exporter.py | (Optional) Deploys Node Exporters to remote nodes via SSH. |
| gc_prune.py | Periodic system prune to remove unused Docker artifacts. |

---

## Example Compose Deployment

```yaml
services:
  orcastra:
    image: ghcr.io/princinv/orcastra:latest
    environment:
      - STACK_NAME=swarm-dev
      - DEBUG=true
      - EVENT_MODE=false
      - POLLING_MODE=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/etc/swarm-orchestration:ro
```

---

## Environment Variables

## Environment Variables

| Variable                            | Default                                         | Purpose |
|:------------------------------------|:------------------------------------------------|:--------|
| TZ                                  | (none)                                          | Container timezone |
| STACK_NAME                          | `swarm-dev`                                     | Prefix for services and labels |
| BOOTSTRAP_MODE                      | `watch`                                         | Bootstrap behavior: loop, once, or watch |
| LOOP_INTERVAL                       | `300`                                           | Bootstrap mode loop interval (seconds) |
| PRUNE_UNKNOWN_LABELS                | `false`                                         | Whether to remove unexpected labels during bootstrap |
| RELABEL_TIME                        | `60`                                            | Label sync polling interval (seconds) |
| EVENT_MODE                          | `true`                                          | Enable Docker event-based monitoring |
| POLLING_MODE                        | `true`                                          | Enable interval-based monitoring |
| RESTART_DEPENDENTS                  | `true`                                          | Restart dependents when anchor fails |
| REBALANCE_MONITOR_INTERVAL_SECONDS  | `30`                                            | Interval to check memory metrics (seconds) |
| REBALANCE_GLOBAL_COOLDOWN_MINUTES   | `10`                                            | Global cooldown before rebalancing again (minutes) |
| REBALANCE_GLOBAL_MEM_THRESHOLD_PERCENT | `85`                                        | Trigger rebalance when node memory % exceeds this threshold |
| GC_CRON                             | `0 */4 * * *`                                   | Cron expression for GC runs (default every 4 hours) |
| GC_FORCE_IMAGE_REMOVAL              | `1`                                             | Force remove images when cleaning up |
| GC_MINIMUM_IMAGES_TO_SAVE           | `3`                                             | Number of images to retain before GC |
| GC_FORCE_CONTAINER_REMOVAL          | `1`                                             | Force remove exited containers |
| GC_GRACE_PERIOD_SECONDS             | `10800`                                         | Time before cleaning exited containers (seconds) |
| GC_DRY_RUN                          | `0`                                             | Run GC without making changes |
| GC_CLEAN_UP_VOLUMES                 | `1`                                             | Whether to remove orphaned volumes during GC |
| MOD_MANAGER_DEST                    | `/modcache`                                     | Modcache destination folder |
| MOD_MANAGER_REFRESH_INTERVAL_MINUTES | `720`                                          | Interval to refresh mod downloads (minutes) |
| COMMAND_FILE                        | `/mnt/commands/swarm-orchestration.command.yml` | Path to dynamic command file |
| NODES_FILE                          | `/etc/swarm-orchestration/nodes.yml`            | Static node metadata for bootstrap and labeling |
| DEPENDENCIES_FILE                   | `/etc/swarm-orchestration/dependencies.yml`     | Anchor/dependent mappings |
| LOG_TO_FILE                         | `false`                                         | Enable logging to file inside container |
| DRY_RUN                             | `false`                                         | Simulate all actions without actually applying changes |
| RUN_ONCE                            | `false`                                         | Only run one cycle instead of continuous operation |
| DEBUG                               | `true`                                          | Enable verbose debug logging |

---

## Project Status

- Fully modular architecture
- Continuous placement enforcement
- Live memory-driven rebalancing
- Static and dynamic label synchronization
- Mod Manager integration for external assets
- GitHub Container Registry published

---

## Maintainer

Maintained by [@princinv](https://github.com/princinv).
Contributions and issue reports are welcome.

---

# Orcastra: Production-ready intelligent orchestration for Docker Swarm clusters.

