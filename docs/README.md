# Orcastra: Swarm Orchestration Container

<img src="https://raw.githubusercontent.com/princinv/orcastra/main/assets/orcastra_banner.png" alt="Orcastra Banner" width="100%" />

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
src/
├── cli/                  # CLI entrypoints
│   └── entrypoint.py
├── commands/              # Dynamic command file triggers
│   └── swarm-orch.command.yml
├── core/                  # Global configuration and persistent state
│   ├── config_loader.py
│   ├── config.py
│   ├── constants.py
│   ├── docker_client.py
│   ├── retry_state.py
│   └── state.py
├── lib/                   # Logical modules
│   ├── bootstrap/
│   ├── common/
│   ├── metrics/
│   ├── rebalance/
│   └── sync/
├── runner/                # Lightweight orchestrators
│   ├── autoheal.py
│   ├── bootstrap.py
│   ├── change_detection.py
│   ├── deploy_node_exporter.py
│   ├── gc_prune.py
│   ├── label_sync.py
│   ├── log_rotate.py
│   ├── mod_manager.py
│   ├── rebalance.py
│   └── static_labels.py
├── config/                # Mounted YAML configurations
├── utils/                 # Healthchecks and simple utilities
└── logs/                  # Internal container logs
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

| Variable                          | Default                                        | Purpose |
|:----------------------------------|:------------------------------------------------|:--------|
| STACK_NAME                        | `swarm-dev`                                    | Prefix for services and labels |
| DEPENDENCIES_FILE                 | `/etc/swarm-orchestration/dependencies.yml`    | Dependency mappings |
| REBALANCE_CONFIG                  | `/etc/swarm-orchestration/rebalance_config.yml`| Rebalancing rules |
| NODES_FILE                        | `/etc/swarm-orchestration/nodes.yml`           | Static node labels |
| DEBUG                             | `false`                                        | Enable debug output |
| DRY_RUN                           | `false`                                        | Simulate actions without applying changes |
| RUN_ONCE                          | `false`                                        | Perform a single full orchestration cycle |
| EVENT_MODE                        | `false`                                        | Event-driven service monitoring (future) |
| POLLING_MODE                      | `true`                                         | Interval-driven service monitoring |
| MOD_MANAGER_CONFIG                | `/etc/mods/config.json`                        | Mod download configuration file |
| MOD_MANAGER_DEST                  | `/mnt/mods`                                    | Modcache destination directory |
| MOD_MANAGER_REFRESH_INTERVAL_MINUTES | `6`                                          | Mod download refresh interval |

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

