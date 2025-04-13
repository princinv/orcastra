import os
import time
import yaml
import subprocess
import signal
import threading

COMMAND_FILE = os.getenv("COMMAND_FILE", "/tmp/swarm-orchestration.command.yml")
NODES_FILE = os.getenv("NODES_FILE", "/etc/swarm/nodes.yml")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

should_run = True

def log(msg):
    print(f"[bootstrap_swarm] {msg}")

def is_online(ip):
    return subprocess.call(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def ssh(host, command):
    if DEBUG:
        log(f"SSH {host}: {command}")
    return subprocess.run(["ssh", host, command], capture_output=True, text=True)

def load_nodes():
    with open(NODES_FILE, 'r') as f:
        return yaml.safe_load(f)

def bootstrap_swarm():
    config = load_nodes()
    leader = config.get("leader")
    advertise = config.get("advertise_addr")
    nodes = config.get("nodes", {})
    prune = config.get("options", {}).get("prune_unknown_labels", False)

    if not is_online(advertise):
        log(f"Leader {leader} offline at {advertise}, skipping.")
        return

    log("Checking Swarm status...")
    if ssh(advertise, "docker info | grep 'Swarm: active'").returncode != 0:
        ssh(advertise, f"docker swarm init --advertise-addr {advertise}")
        log("Swarm initialized.")
    else:
        log("Swarm already active.")

    token = ssh(advertise, "docker swarm join-token -q manager").stdout.strip()
    if not token:
        log("Could not get join token.")
        return

    for name, meta in nodes.items():
        ip = meta["ip"]
        if name == leader or not is_online(ip):
            continue
        if ssh(ip, "docker info | grep 'Swarm: active'").returncode != 0:
            ssh(ip, f"docker swarm join --token {token} {advertise}:2377")
            log(f"{name} joined.")
        else:
            log(f"{name} already in Swarm.")

    # Promote all
    result = ssh(advertise, "docker node ls --format '{{.Hostname}} {{.ID}}'")
    node_map = {line.split()[0]: line.split()[1] for line in result.stdout.splitlines()}
    for name in nodes:
        if name in node_map:
            ssh(advertise, f"docker node promote {node_map[name]}")

    # Label sync
    for name, meta in nodes.items():
        if name not in node_map:
            continue
        labels = set(meta.get("labels", []))
        current = ssh(advertise, f"docker node inspect {name} --format '{{{{json .Spec.Labels}}}}'").stdout.strip()
        try:
            current_labels = yaml.safe_load(current) or {}
        except:
            current_labels = {}

        # Add/update needed labels
        for label in labels:
            if current_labels.get(label) != "true":
                if not DRY_RUN:
                    ssh(advertise, f"docker node update --label-add {label}=true {name}")
                log(f"Added {label}=true to {name}")

        # Remove extra labels if prune enabled
        if prune:
            for label in current_labels:
                if label not in labels and label != name:
                    if not DRY_RUN:
                        ssh(advertise, f"docker node update --label-rm {label} {name}")
                    log(f"Removed label {label} from {name}")

    log("Bootstrap complete.")

def watch_command_file():
    global should_run
    while should_run:
        try:
            if os.path.exists(COMMAND_FILE):
                with open(COMMAND_FILE, 'r') as f:
                    commands = yaml.safe_load(f) or []
                new_commands = []
                for entry in commands:
                    cmd, arg = (entry.split(":", 1) + [None])[:2] if isinstance(entry, str) else (None, None)
                    if cmd == "bootstrap_swarm":
                        bootstrap_swarm()
                    else:
                        new_commands.append(entry)  # Keep unknowns
                with open(COMMAND_FILE, 'w') as f:
                    yaml.safe_dump(new_commands, f)
        except Exception as e:
            log(f"Error watching command file: {e}")
        time.sleep(5)

def sighup_handler(signum, frame):
    log("Received SIGHUP: running bootstrap now")
    bootstrap_swarm()

def main():
    signal.signal(signal.SIGHUP, sighup_handler)
    if RUN_ONCE:
        bootstrap_swarm()
    elif os.getenv("WATCH_COMMAND_FILE", "false").lower() == "true":
        watch_command_file()
    else:
        while should_run:
            bootstrap_swarm()
            time.sleep(LOOP_INTERVAL)

def run():
    main()

if __name__ == "__main__":
    run()

