# swarm-orchestrationThe following structure modularizes the original update_node_labels.py into discrete components under a package called swarm_orch.

🔧 Structure Overview
graphql
Copy code
swarm_orch/
├── __init__.py
├── config.py               # All ENV + constants
├── docker_client.py        # Docker client and SDK version detection
├── labels.py               # Node label management (add/remove)
├── services.py             # Service state inspection (get_service_node, retry logic)
├── update.py               # Main reconciliation loop
├── watcher.py              # Event-based listener for anchor restarts
├── commands.py             # YAML command file processing
└── run.py                  # Entrypoint logic (threading, signal handling)
📄 File Descriptions
swarm_orch/config.py
Centralized configuration loaded from environment variables:

Paths to files (DEPENDENCIES_FILE, etc.)

Polling and debounce timings

Retry intervals

Logging level, dry run mode, etc.

swarm_orch/docker_client.py
Initializes the Docker SDK client (docker.from_env()) and detects the Docker SDK version for compatibility.

swarm_orch/labels.py
Handles all Docker Swarm node label operations:

add_label_to_node()

remove_label_from_all_nodes()

swarm_orch/services.py
Handles Docker service logic:

get_service_node() — inspects task states and determines where (if at all) the service is running.

Retry tracking: should_retry(), record_retry(), clear_retry()

force_update_service() — performs safe rolling updates

swarm_orch/update.py
Main loop for:

Labeling anchor nodes

Restarting dependents when anchors move

Making placement-based decisions about co-location

Evaluates retry cooldowns, logs retry state

swarm_orch/watcher.py
Listens to Docker events:

Reacts to anchor container restarts

Debounces to avoid excessive triggering

Triggers main_loop() after event

swarm_orch/commands.py
Parses and runs commands from a YAML file (swarm-orch.command.yml):

pause_dependents

resume_dependents

update_dependents

remove_all_labels, etc.

swarm_orch/run.py
Entry point:

Signal handler (SIGHUP, SIGUSR1)

Runs event mode and polling mode as background threads

Imports and runs main_loop() from update.py