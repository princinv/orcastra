docker push ghcr.io/princinv/orcastra:v0.3.0

The push refers to repository [ghcr.io/princinv/orcastra]
19f971e2d8cd: Layer already exists 
6ee5ceb34fd8: Layer already exists 
8cf169dff6b2: Layer already exists 
5a47714961b6: Layer already exists 
00a9c11f9c0f: Layer already exists 
b22b26e46bff: Layer already exists 
57eaabbf7ad6: Layer already exists 
6b63e624a7d4: Retrying in 7 seconds 
8f55e30a1501: Layer already exists 
84a86f614ade: Layer already exists 
9aeba49f9ae6: Layer already exists 
d50d320ea099: Layer already exists 
6c4c763d22d0: Layer already exists 


🐙 ORASTRA: Swarm Orchestration Container
<img src="https://raw.githubusercontent.com/princinv/swarm-orch/main/docs/banner.png" alt="Orchestration Banner" width="100%" />
🛠️ What is ORASTRA?
A modular container designed for advanced Docker Swarm orchestration — ensuring service co-location, dynamic failover recovery, memory-aware rebalancing, continuous Swarm label reconciliation, and mod download management.

ORASTRA empowers Docker Swarm to behave like a true orchestrator — node-aware, dependency-respecting, self-healing, and dynamic.

✨ Core Features

Feature	Description
🔗 Anchor-following	Services automatically follow their "anchor" service (e.g., an app follows its database) via dynamic node labeling.
🔁 Auto-restarts	If placement constraints fail, services are auto-restarted with forced updates and cooldowns.
🏷️ Node Label Management	Nodes are labeled in real time to reflect service placement, and static labels are synchronized.
📊 Memory-aware Rebalancing	Services are moved between nodes based on real memory availability via Prometheus node_exporter.
⏱️ Event and Polling Modes	Supports both event-based and interval-based monitoring of Docker services.
⚙️ Command YAML Interface	Define actions like bootstrap, sync, restart, pause via easy YAML commands (swarm-orch.command.yml).
🛠️ Swarm Bootstrap & Self-Healing	Automatically initializes Swarm, promotes nodes, and re-joins dropped nodes.
🧹 Autoheal, GC, Logrotate	Optional side-utilities keep your Swarm clean and responsive.
🎮 Mod Manager	Periodically downloads mods based on a config file (modcache system) and updates them automatically.
📁 Directory Overview
bash
Copy
Edit
src/
├── cli/                  # Entrypoints and CLI runners
│   └── entrypoint.py
├── commands/              # Dynamic command triggers
│   └── swarm-orch.command.yml
├── core/                  # Global configuration and state handling
│   ├── config_loader.py
│   ├── config.py
│   ├── constants.py
│   ├── docker_client.py
│   ├── retry_state.py
│   └── state.py
├── lib/                   # Modular logic layers
│   ├── bootstrap/         # Swarm join, promote, label tasks
│   ├── common/            # Docker CLI helpers, task inspection
│   ├── sync/              # Labeling logic
│   ├── metrics/           # Memory scraping helpers
│   └── rebalance/         # Rebalance decisions
├── runner/                # Main orchestrators (label sync, rebalance, bootstrap, modmanager, etc.)
├── utils/                 # Healthcheck and small utilities
├── config/                # Mounted runtime YAMLs (dependencies, nodes, rebalance config)
└── logs/                  # Service activity logs
🚀 Main Orchestrators

Runner	Purpose
bootstrap_swarm.py	Initializes Swarm, promotes nodes, applies static labels.
label_sync_runner.py	Applies anchor labels and ensures dependents are colocated (dynamic runtime).
rebalance.py	Moves services to better nodes if memory pressure exists.
static_labels.py	Re-syncs static node labels from nodes.yml.
autoheal.py	Watches unhealthy tasks and triggers safe updates.
log_rotate.py	Runs periodic log rotation inside the container.
deploy_node_exporter.py	(Optional) Remotely deploys node_exporter containers via SSH.
gc_prune.py	Performs optional GC/prune cleanups if configured.
mod_manager.py	Downloads and refreshes mods automatically into modcache/, triggered on interval or manually.
🧹 Example Compose Deployment
yaml
Copy
Edit
services:
  orastra:
    image: ghcr.io/princinv/orastra:latest
    environment:
      - STACK_NAME=swarm-dev
      - DEBUG=true
      - EVENT_MODE=false
      - POLLING_MODE=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/etc/swarm-orchestration:ro
⚙️ Environment Variables

Variable	Default	Purpose
STACK_NAME	swarm-dev	Prefix for services and labels
DEPENDENCIES_FILE	/etc/swarm-orchestration/dependencies.yml	Dependency mappings
REBALANCE_CONFIG	/etc/swarm-orchestration/rebalance_config.yml	Rebalancing rules
NODES_FILE	/etc/swarm-orchestration/nodes.yml	Static node labels
DEBUG	false	Enable debug output
DRY_RUN	false	Simulate actions without applying
RUN_ONCE	false	Only perform a single cycle
EVENT_MODE	false	Watch Docker events instead of polling
POLLING_MODE	true	Perform periodic checks
MOD_MANAGER_CONFIG	/etc/mods/config.json	JSON file specifying mods to download
MOD_MANAGER_DEST	/mnt/mods	Destination modcache folder
MOD_MANAGER_REFRESH_INTERVAL_MINUTES	6	Refresh interval for mod downloads
🌟 Project Status
✅ Fully modularized (multi-runner architecture)

✅ Node and anchor label synchronization

✅ Resource-based dynamic rebalancing

✅ Docker socket event and interval-driven

✅ Mod Manager support for dynamic mod downloading

✅ GHCR-published image (soon under correct ORASTRA tag)

🐳 Maintainer
Maintained by @princinv
Pull requests, suggestions, and improvements are welcome.

✅ ORASTRA: Production-ready Docker Swarm intelligence + mod orchestration
Would you also like me to cleanly fix the folder structure drawing at the end to show /runner/mod_manager.py properly under it?
(I can reformat that too if you want it even more perfect.)

→ Do you want a corrected folder tree, too? 🎯
(Just yes/no, and I'll get it in one step clean.)






You said:
sorry it is called Orcastra. and the banner is in the assets folder as orcastra_banner. And i do not loke emojis. 



ChatGPT said:
Crystal clear now — here's your corrected final version, no nonsense:

Orcastra: Swarm Orchestration Container
<img src="https://raw.githubusercontent.com/princinv/swarm-orch/main/assets/orcastra_banner.png" alt="Orcastra Banner" width="100%" />
What is Orcastra?
Orcastra is a modular container designed for advanced Docker Swarm orchestration — ensuring co-location of dependent services, dynamic failover recovery, real-world memory-aware rebalancing, continuous Swarm label reconciliation, and periodic mod download management.

It extends Docker Swarm into a fully autonomous, dependency-aware, resource-driven orchestrator.

Core Features

Feature	Description
Anchor-following	Ensures dependent services follow their "anchor" (e.g., an app colocates with its database).
Auto-restarts	Automatically restarts services that violate placement constraints, with retry cooldowns.
Node label management	Dynamically labels nodes based on anchor presence and maintains static labels from configuration.
Memory-aware rebalancing	Continuously evaluates node memory and relocates services if better nodes are available.
Event and polling modes	Supports event-driven updates (planned) and periodic polling-based reconciliation (active).
Command YAML interface	Allows manual triggering of syncs, restarts, or reboots through a simple YAML file.
Swarm bootstrap and healing	Auto-joins missing nodes, promotes managers, corrects labels on recovery.
Mod Manager integration	Periodically downloads and refreshes mod files into a designated modcache directory.
Autoheal, GC, log rotation	Optional utilities to maintain container and log hygiene.
Directory Overview
bash
Copy
Edit
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
Main Runners

Script	Purpose
bootstrap.py	Ensures Swarm is initialized, nodes are promoted, labels are synced.
label_sync.py	Maintains anchor-based placement and updates dependent services.
rebalance.py	Moves services between nodes based on memory pressure.
static_labels.py	Syncs persistent labels defined in nodes.yml.
mod_manager.py	Periodically downloads mod files into a modcache destination.
autoheal.py	Monitors and restarts unhealthy containers.
log_rotate.py	Performs container-internal log rotations.
deploy_node_exporter.py	(Optional) Deploys Node Exporters to remote nodes via SSH.
gc_prune.py	Periodic system prune to remove unused Docker artifacts.
Example Compose Deployment
yaml
Copy
Edit
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
Environment Variables

Variable	Default	Purpose
STACK_NAME	swarm-dev	Prefix for services and labels
DEPENDENCIES_FILE	/etc/swarm-orchestration/dependencies.yml	Dependency mappings
REBALANCE_CONFIG	/etc/swarm-orchestration/rebalance_config.yml	Rebalancing rules
NODES_FILE	/etc/swarm-orchestration/nodes.yml	Static node labels
DEBUG	false	Enable debug output
DRY_RUN	false	Simulate actions without applying changes
RUN_ONCE	false	Perform a single full orchestration cycle
EVENT_MODE	false	Event-driven service monitoring (future)
POLLING_MODE	true	Interval-driven service monitoring
MOD_MANAGER_CONFIG	/etc/mods/config.json	Mod download configuration file
MOD_MANAGER_DEST	/mnt/mods	Modcache destination directory
MOD_MANAGER_REFRESH_INTERVAL_MINUTES	6	Mod download refresh interval
Project Status
Fully modular architecture

Continuous placement enforcement

Live memory-driven rebalancing

Static and dynamic label synchronization

Mod Manager integration for external assets

GitHub Container Registry published

Maintainer
Maintained by @princinv.
Contributions and issue reports are welcome.

Orcastra: Production-ready intelligent orchestration for Docker Swarm clusters.
Would you like me to also:

(optional) Update the Compose sample so MOD_MANAGER_CONFIG and MOD_MANAGER_DEST are mounted properly too?

(optional) Rewrite a super-compact version for the "About" box (GitHub sidebar)?
(Takes less than 30 seconds if you want.)

