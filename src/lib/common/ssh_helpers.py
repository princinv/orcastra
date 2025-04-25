"""
ssh_helpers.py
- Provides basic SSH and ping connectivity utilities for remote command execution.
- Used during bootstrap and label synchronization to manage Swarm nodes remotely.
"""

import subprocess
import logging

def is_online(ip):
    """
    Check if a given IP is reachable via ping.

    Args:
        ip (str): Target IP address or hostname.

    Returns:
        bool: True if ping returns successfully, False otherwise.
    """
    return subprocess.call(
        ["ping", "-c", "1", "-W", "1", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

def ssh(host, command, debug=False):
    """
    Execute a command on a remote host over SSH.

    Args:
        host (str): Hostname or IP of the remote machine.
        command (str): The shell command to run.
        debug (bool): If True, logs the command before execution.

    Returns:
        CompletedProcess: Subprocess result with stdout, stderr, returncode.
    """
    if debug:
        logging.debug(f"[ssh_helpers] SSH {host}: {command}")
    return subprocess.run(
        ["ssh", host, command],
        capture_output=True,
        text=True,
        timeout=10  # prevent indefinite hangs
    )
