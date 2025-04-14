from core.config_loader import load_yaml
from lib.bootstrap_tasks import check_swarm, get_join_token, join_node, get_node_map
from lib.bootstrap_labels import sync_labels
from lib.ssh_helpers import is_online, ssh
import os, signal, threading, time, yaml

# ENV
COMMAND_FILE = os.getenv("COMMAND_FILE", "/tmp/swarm-orchestration.command.yml")
NODES_FILE = os.getenv("NODES_FILE", "/etc/swarm/nodes.yml")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
should_run = True

def bootstrap_swarm():
    config = load_yaml(NODES_FILE)
    leader = config.get("leader")
    advertise = config.get("advertise_addr")
    nodes = config.get("nodes", {})
    prune = config.get("options", {}).get("prune_unknown_labels", False)

    if not is_online(advertise):
        print(f"[bootstrap] Leader {leader} offline at {advertise}, skipping.")
        return

    if check_swarm(advertise, DEBUG):
        print("[bootstrap] Swarm initialized.")
    else:
        print("[bootstrap] Swarm already active.")

    token = get_join_token(advertise, DEBUG)
    if not token:
        print("[bootstrap] Failed to retrieve join token.")
        return

    for name, meta in nodes.items():
        ip = meta["ip"]
        if name == leader or not is_online(ip):
            continue
        if ssh(ip, "docker info | grep 'Swarm: active'", DEBUG).returncode != 0:
            join_node(ip, token, advertise, DEBUG)
            print(f"[bootstrap] {name} joined.")

    node_map = get_node_map(advertise, DEBUG)
    for name in nodes:
        if name in node_map:
            ssh(advertise, f"docker node promote {node_map[name]}", DEBUG)

    sync_labels(advertise, nodes, node_map, prune=prune, dry_run=DRY_RUN, debug=DEBUG)

def sighup_handler(signum, frame):
    print("📣 SIGHUP: Re-running bootstrap now...")
    bootstrap_swarm()

def run():
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, sighup_handler)

    if RUN_ONCE:
        bootstrap_swarm()
    else:
        while should_run:
            bootstrap_swarm()
            time.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    run()
