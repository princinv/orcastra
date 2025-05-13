#!/usr/bin/env python3
"""
deploy_node_exporter.py
- Deploys the Prometheus Node Exporter across all Swarm nodes using a configuration file.
- Reads from /etc/swarm-orchestration/node_exporter_deploy.yml.
- Uses local Docker socket to determine if service exists and update or create accordingly.
- Avoids SSH and survives Swarm leader changes automatically.
"""

import os
import shlex
import subprocess
from loguru import logger

from core.config_loader import load_yaml
from tenacity import retry, stop_after_attempt, wait_fixed

CONFIG_PATH = "/etc/swarm-orchestration/deploy_node_exporter.yml"  # <-- FIXED

def build_service_command(cfg):
    cmd = ["docker", "service", "create"]

    # --- Service Name ---
    cmd += ["--name", cfg.get("name", "node_exporter")]

    # --- Mode ---
    if cfg.get("deploy", {}).get("mode", "global") == "global":
        cmd += ["--mode", "global"]

    # --- Endpoint Mode ---
    endpoint_mode = cfg.get("deploy", {}).get("endpoint_mode")
    if endpoint_mode:
        cmd += ["--endpoint-mode", endpoint_mode]

    # --- Placement Constraints ---
    for constraint in cfg.get("deploy", {}).get("placement", {}).get("constraints", []):
        cmd += ["--constraint", constraint]

    # --- Restart Policy ---
    restart = cfg.get("deploy", {}).get("restart_policy", {})
    if restart:
        cmd += ["--restart-condition", restart.get("condition", "on-failure")]
        cmd += ["--restart-delay", restart.get("delay", "5s")]
        cmd += ["--restart-max-attempts", str(restart.get("max_attempts", 2))]
        cmd += ["--restart-window", restart.get("window", "60s")]

    # --- Stop Signal & Grace ---
    if "stop_grace_period" in cfg:
        cmd += ["--stop-grace-period", cfg["stop_grace_period"]]
    if "stop_signal" in cfg:
        cmd += ["--stop-signal", cfg["stop_signal"]]

    # --- Logging ---
    logging_opts = cfg.get("logging", {})
    if logging_opts:
        cmd += ["--log-driver", logging_opts.get("driver", "json-file")]
        for k, v in logging_opts.get("options", {}).items():
            cmd += ["--log-opt", f"{k}={v}"]

    # --- Networks ---
    for net in cfg.get("networks", []):
        cmd += ["--network", net]

    # --- Ports ---
    for port in cfg.get("ports", []):
        port_def = f"{port['published']}:{port['target']}/{port.get('protocol', 'tcp')}"
        cmd += ["--publish", port_def]

    # --- Labels ---
    for key, value in cfg.get("deploy", {}).get("labels", {}).items():
        cmd += ["--label", f"{key}={value}"]
    for key, value in cfg.get("labels", {}).items():
        cmd += ["--label", f"{key}={value}"]

    # --- Mounts ---
    for m in cfg.get("mounts", []):
        opt = f"type=bind,src={m['source']},dst={m['target']}"
        if m.get("read_only"):
            opt += ",readonly"
        cmd += ["--mount", opt]

    # --- Environment Vars ---
    if cfg.get("timezone", {}).get("env_tz"):
        tz = os.environ.get("TZ", "UTC")
        cmd += ["--env", f"TZ={tz}"]

    # --- Healthcheck ---
    hc = cfg.get("healthcheck", {})
    if hc:
        test_cmd = hc.get('test')
        if isinstance(test_cmd, list) and len(test_cmd) >= 2:
            if test_cmd[0] == "CMD-SHELL":
                cmd += ["--health-cmd", test_cmd[1]]
            else:
                cmd += ["--health-cmd", test_cmd[1]]
        elif isinstance(test_cmd, str):
            cmd += ["--health-cmd", test_cmd]
        else:
            logger.warning("[deploy] Skipping healthcheck: invalid test command structure.")

        cmd += ["--health-interval", hc.get("interval", "30s")]
        cmd += ["--health-timeout", hc.get("timeout", "30s")]
        cmd += ["--health-retries", str(hc.get("retries", 3))]
        cmd += ["--health-start-period", hc.get("start_period", "60s")]

    # --- Image and Args ---
    cmd.append(cfg.get("image", "prom/node-exporter:latest"))
    cmd.extend(cfg.get("args", []))

    return cmd

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def deploy():
    cfg = load_yaml(CONFIG_PATH)
    if not cfg:
        logger.error("[node_exporter] Configuration missing or invalid.")
        return

    inspect_cmd = ["docker", "service", "inspect", "node_exporter"]
    result = subprocess.run(inspect_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode == 0:
        logger.info("[node_exporter] Service exists, forcing update...")
        try:
            subprocess.run(["docker", "service", "update", "--force", "node_exporter"], check=True)
            logger.info("[node_exporter] Service update successful.")
        except subprocess.CalledProcessError as e:
            logger.error(f"[node_exporter] Update failed: {e}")
    else:
        logger.info("[node_exporter] Service not found. Creating...")
        cmd = build_service_command(cfg)
        try:
            subprocess.run(cmd, check=True)
            logger.info("[node_exporter] Service created successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"[node_exporter] Service creation failed: {e}")


if __name__ == "__main__":
    deploy()
