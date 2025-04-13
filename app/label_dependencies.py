# update_node_labels.py

# Standard libraries
import os
import time
import yaml
import logging
from collections import defaultdict

# Docker SDK imports
import docker
from docker import from_env
from docker.errors import APIError

# Configurable environment variables
DEPENDENCIES_FILE = os.getenv("DEPENDENCIES_FILE", "/etc/swarm/dependencies.yaml")
RELABEL_TIME = int(os.getenv("RELABEL_TIME", "60"))
STACK_NAME = os.getenv("STACK_NAME", "swarm-dev")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
EVENT_MODE = os.getenv("EVENT_MODE", "false").lower() == "true"
POLLING_MODE = os.getenv("POLLING_MODE", "true").lower() == "true"
RESTART_DEPENDENTS = os.getenv("RESTART_DEPENDENTS", "false").lower() == "true"
DEBOUNCE_TIME = int(os.getenv("DEBOUNCE_TIME", "5"))
DEFAULT_RETRY_INTERVALS = [2, 10, 60, 300, 900]  # seconds
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
LOG_FILE = "/var/log/swarm-labels.log"

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE) if LOG_TO_FILE else logging.StreamHandler()
    ]
)

# Initialize Docker client and detect SDK version
client = from_env()
try:
    DOCKER_SDK_VERSION = tuple(map(int, docker.__version__.split(".")))
    logging.info(f"🐳 Docker SDK version: {docker.__version__}")
except Exception as e:
    DOCKER_SDK_VERSION = (0, 0, 0)
    logging.warning(f"⚠️ Failed to detect Docker SDK version: {e}")
retry_state = defaultdict(lambda: {"failures": 0, "last_attempt": 0})

# Load dependency map from a YAML file
def load_dependencies():
    try:
        with open(DEPENDENCIES_FILE, 'r') as f:
            data = yaml.safe_load(f) or {}
            logging.info(f"📄 Loaded dependencies: {data}")
            return data
    except Exception as e:
        logging.error(f"❌ Failed to load dependencies file: {e}")
        return {}

# Get all running service names
def get_running_services():
    try:
        services = [service.name for service in client.services.list()]
        logging.info(f"📦 Running services: {services}")
        return services
    except APIError as e:
        logging.error(f"Failed to list services: {e}")
        return []

# Get node ID where a service is running
def get_service_node(service_name, wait_timeout=5):
    try:
        service = client.services.get(service_name)
        deadline = time.time() + wait_timeout

        while time.time() < deadline:
            tasks = service.tasks(filters={"desired-state": "running"})

            for task in tasks:
                status = task.get("Status", {})
                state = status.get("State")
                node_id = task.get("NodeID")

                if state == "running" and node_id:
                    logging.info(f"📍 {service_name} is running on node {node_id}")
                    return node_id

                if state == "starting" and node_id:
                    logging.info(f"⏳ {service_name} is starting on node {node_id}, will retry later")

            # Wait and retry
            time.sleep(1)

        # Log full task states if nothing valid was found
        for task in tasks:
            logging.debug(
                f"🧪 Task for {service_name}: ID={task.get('ID')} | "
                f"State={task.get('Status', {}).get('State')} | "
                f"NodeID={task.get('NodeID')}"
            )
        logging.warning(f"❌ No running task with valid NodeID found for {service_name}")
    except APIError as e:
        logging.warning(f"⚠️ Could not inspect service: {service_name} — {e}")
    except Exception as e:
        logging.error(f"🔥 Unexpected error checking node for {service_name}: {e}")
    return None

# Remove a label from all nodes
def remove_label_from_all_nodes(label):
    for node in client.nodes.list():
        node.reload()
        spec = node.attrs['Spec']
        labels = spec.get('Labels', {})
        if label in labels:
            labels.pop(label)
            if DRY_RUN:
                logging.info(f"[DRY RUN] Would remove label '{label}' from node {node.id}")
            else:
                try:
                    node.update({
                        'Role': spec['Role'],
                        'Availability': spec['Availability'],
                        'Labels': labels
                    })
                    logging.info(f"🗑️ Removed label '{label}' from node {node.id}")
                except APIError as e:
                    logging.error(f"❌ Failed to remove label '{label}' from node {node.id}: {e}")

# Apply a label to a node
def add_label_to_node(label, node_id):
    try:
        # Refetch node to avoid stale "update out of sequence" errors
        node = client.nodes.get(node_id)
        node.reload()
        spec = node.attrs["Spec"]
        labels = spec.get("Labels", {})
        labels[label] = "true"
        if DRY_RUN:
            logging.info(f"[DRY RUN] Would apply label '{label}=true' to node {node_id}")
        else:
            node.update({
                'Role': spec['Role'],
                'Availability': spec['Availability'],
                'Labels': labels
            })
            logging.info(f"✅ Applied label '{label}=true' to node {node_id}")
    except APIError as e:
        logging.error(f"❌ Failed to apply label '{label}' to node {node_id}: {e}")
    except Exception as e:
        logging.error(f"🔥 Unexpected error labeling node {node_id}: {e}")

# Determine if retry should proceed based on interval progression
def should_retry(service_name, retry_intervals):
    now = time.time()
    state = retry_state[service_name]
    failures = state["failures"]
    last = state["last_attempt"]
    interval = retry_intervals[min(failures, len(retry_intervals) - 1)]
    return now - last >= interval

# Update retry tracking
def record_retry(service_name):
    retry_state[service_name]["failures"] += 1
    retry_state[service_name]["last_attempt"] = time.time()

# Reset retry state on success
def clear_retry(service_name):
    if service_name in retry_state:
        del retry_state[service_name]

# Force a rolling update on a service
def force_update_service(service_name):
    try:
        if DRY_RUN:
            logging.info(f"[DRY RUN] Would force update service: {service_name}")
            return True

        service = client.services.get(service_name)
        spec = service.attrs['Spec']
        logging.debug(f"🔧 Service spec keys: {list(spec.keys())}")

        try:
            if DOCKER_SDK_VERSION >= (7, 0, 0):
                service.update(
                    task_template=spec["TaskTemplate"],
                    name=spec["Name"],
                    labels=spec.get("Labels", {}),
                    mode=spec.get("Mode"),
                    update_config=spec.get("UpdateConfig"),
                    rollback_config=spec.get("RollbackConfig"),
                    endpoint_spec=spec.get("EndpointSpec")
                )
            else:
                raise TypeError("Fallback to force_update")
        except TypeError as te:
            logging.warning(f"⚠️ Primary update method failed, falling back: {te}")
            service.update(force_update=True)

        logging.info(f"🔁 Forced update of service: {service_name}")
        clear_retry(service_name)
        return True
    except Exception as e:
        logging.error(f"❌ Failed to update service '{service_name}': {e}")
        record_retry(service_name)
        return False

# Reconciliation logic

def is_paused():
    return os.path.exists("/tmp/swarm-orch.paused")

def run_update_for_anchor(anchor_label):
    logging.info(f"🔁 Manually updating dependents for anchor: {anchor_label}")
    dependencies = load_dependencies()
    dependents = dependencies.get(anchor_label, {}).get("services") if isinstance(dependencies.get(anchor_label), dict) else dependencies.get(anchor_label)
    db_service = f"{STACK_NAME}_{anchor_label}"
    db_node = get_service_node(db_service)
    if not db_node:
        logging.warning(f"❌ Could not find anchor node for {db_service}. Skipping.")
        return

    for dep in dependents:
        full_dep_service = f"{STACK_NAME}_{dep}"
        try:
            logging.info(f"🔄 Forcing update of {full_dep_service} dependent on {anchor_label}")
            force_update_service(full_dep_service)
        except Exception as e:
            logging.error(f"🔥 Failed to update dependent service {full_dep_service}: {e}")

def main_loop():
    if is_paused():
        logging.info("⏸️ Skipping main_loop — dependent updates are paused.")
        return
    def should_restart(anchor_label):
        value = dependencies.get(anchor_label)
        if isinstance(value, dict):
            return value.get("restart_dependents", RESTART_DEPENDENTS)
        return RESTART_DEPENDENTS

    def retry_intervals_for(anchor_label):
        value = dependencies.get(anchor_label)
        if isinstance(value, dict):
            return value.get("retry_intervals", DEFAULT_RETRY_INTERVALS)
        return DEFAULT_RETRY_INTERVALS

    logging.info("🚀 Starting dependency reconciliation run...")
    global dependencies
    dependencies = load_dependencies()
    services = get_running_services()

    for anchor_label in dependencies:
        remove_label_from_all_nodes(anchor_label)

    for anchor_label in dependencies:
        full_db_service = f"{STACK_NAME}_{anchor_label}"
        node_id = get_service_node(full_db_service)
        if not node_id:
            logging.warning(f"❌ {full_db_service} is not running. Skipping.")
            continue
        add_label_to_node(anchor_label, node_id)

    for anchor_label, config in dependencies.items():
        dependents = config.get("services") if isinstance(config, dict) else config
        db_service = f"{STACK_NAME}_{anchor_label}"
        db_node = get_service_node(db_service)
        if not db_node:
            logging.warning(f"❌ Could not find anchor node for {db_service}. Skipping.")
            continue

        all_failed = True
        for dep in dependents:
            full_dep_service = f"{STACK_NAME}_{dep}"
            try:
                dep_node = get_service_node(full_dep_service)
                retry_schedule = retry_intervals_for(anchor_label)

                if not dep_node:
                    if should_retry(full_dep_service, retry_schedule):
                        logging.warning(f"❌ {full_dep_service} is not running. Retrying update.")
                        if force_update_service(full_dep_service):
                            all_failed = False
                    else:
                        logging.info(f"⏳ Skipping retry for {full_dep_service} (waiting cooldown)")
                    continue

                if db_node != dep_node:
                    if should_retry(full_dep_service, retry_schedule):
                        logging.info(f"🔁 {full_dep_service} not co-located. Retrying update.")
                        if force_update_service(full_dep_service):
                            all_failed = False
                    else:
                        logging.info(f"⏳ Skipping retry for {full_dep_service} (waiting cooldown)")
                else:
                    logging.info(f"✅ {full_dep_service} already co-located.")
                    if should_restart(anchor_label):
                        if should_retry(full_dep_service, retry_schedule):
                            logging.info(f"🔄 RESTART_DEPENDENTS=true, restarting {full_dep_service}.")
                            force_update_service(full_dep_service)
                        else:
                            logging.info(f"⏳ Skipping restart for {full_dep_service} (waiting cooldown)")
                    all_failed = False
            except Exception as e:
                logging.error(f"🔥 Unexpected error handling {full_dep_service}: {e}")

        if all_failed:
            logging.warning(f"⚠️ All dependent updates for anchor '{anchor_label}' failed. Removing label to prevent misplacement.")
            remove_label_from_all_nodes(anchor_label)

        # Log retry status
        for dep in dependents:
            if dep in retry_state:
                state = retry_state[dep]
                logging.info(f"🔁 Retry pending for {dep}: {state['failures']} failures, last at {time.ctime(state['last_attempt'])}")

# Event-driven listener for anchor restarts with per-service debounce + skipped event logging
def listen_for_anchor_restarts(anchor_services):
    logging.info("🔍 Watching for anchor service restarts...")
    last_triggered = {}

    for event in client.events(decode=True):
        try:
            if event.get("Type") == "container" and event.get("Action") in ["start", "die"]:
                attrs = event.get("Actor", {}).get("Attributes", {})
                service = attrs.get("com.docker.swarm.service.name", "")

                if service in anchor_services:
                    now = time.time()
                    last = last_triggered.get(service, 0)
                    if now - last >= DEBOUNCE_TIME:
                        logging.info(f"🚨 Triggered by {service}, running reconciliation")
                        time.sleep(3)  # 🕒 Let Swarm assign the anchor task to a node
                        main_loop()
                        last_triggered[service] = now
                    else:
                        logging.info(f"⏸️ Debounced {service} (triggered {now - last:.2f}s ago, waiting {DEBOUNCE_TIME}s)")
        except Exception as e:
            logging.error(f"⚠️ Error in event listener: {e}")

# Process commands from YAML file
COMMAND_FILE = os.getenv("COMMAND_FILE", "/tmp/swarm-orch.command.yml")

def run_update_for_all_anchors():
    deps = load_dependencies()
    for anchor_label in deps:
        run_update_for_anchor(anchor_label)

COMMAND_MAP = {
    "relabel_all": main_loop,
    "remove_all_labels": lambda: [remove_label_from_all_nodes(label) for label in load_dependencies().keys()],
    "pause_dependents": lambda: open("/tmp/swarm-orchestration.paused", "w").write("true"),
    "resume_dependents": lambda: os.remove("/tmp/swarm-orchestration.paused") if os.path.exists("/tmp/swarm-orchestration.paused") else None,
    "relabel_anchor": lambda anchor: main_loop(),
    "update_dependents": lambda anchor=None: run_update_for_anchor(anchor) if anchor else run_update_for_all_anchors(),
    "noop": lambda: logging.info("ℹ️ Received noop command")
}

def process_command_file():
    try:
        if not os.path.exists(COMMAND_FILE):
            logging.warning(f"⚠️ Command file not found: {COMMAND_FILE}")
            return
        with open(COMMAND_FILE, "r") as f:
            commands = yaml.safe_load(f) or []
        if not isinstance(commands, list):
            logging.error("❌ Command file must contain a YAML list")
            return
        for entry in commands:
            if isinstance(entry, str):
                cmd, arg = (entry.split(":", 1) + [None])[:2]
                handler = COMMAND_MAP.get(cmd)
                if handler:
                    logging.info(f"🎯 Executing command: {entry}")
                    if arg:
                        handler(arg)
                    else:
                        handler()
                else:
                    logging.warning(f"⚠️ Unknown command: {cmd}")
    except Exception as e:
        logging.error(f"❌ Failed to process command file: {e}")
import signal
import threading

def handle_sighup(signum, frame):
    logging.info("📣 Received SIGHUP: running main_loop() now")
    main_loop()

signal.signal(signal.SIGHUP, handle_sighup)
signal.signal(signal.SIGUSR1, lambda s, f: threading.Thread(target=process_command_file).start())


if __name__ == "__main__":
    if RUN_ONCE:
        main_loop()
    elif EVENT_MODE:
        main_loop()  # Ensure at least one pass runs at startup
        anchors = [f"{STACK_NAME}_{s}" for s in load_dependencies().keys()]
        listen_for_anchor_restarts(anchors)
    elif POLLING_MODE:
        while True:
            main_loop()
            time.sleep(RELABEL_TIME)
