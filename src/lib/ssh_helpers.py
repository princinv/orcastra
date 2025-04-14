"""
ssh_helpers.py
- Utility functions for checking node availability and running remote commands over SSH.
- Used by bootstrap_swarm.py to control other Swarm nodes from the leader.
TODO: consider switching to python-native ssh library
"""

import subprocess

def is_online(ip):
    """
    Returns True if the target IP responds to a single ping.
    Used to skip unreachable nodes during bootstrap.
    """
    return subprocess.call(
        ["ping", "-c", "1", "-W", "1", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

def ssh(host, command, debug=False):
    """
    Runs a shell command on a remote host via SSH.
    Used to run docker join/promote/info commands on remote nodes.
    """
    if debug:
        print(f"[ssh_helpers] SSH {host}: {command}")
    return subprocess.run(
        ["ssh", host, command],
        capture_output=True,
        text=True
    )
