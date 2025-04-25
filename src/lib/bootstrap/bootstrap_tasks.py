"""
bootstrap_tasks.py
- Wraps Swarm init/join logic and remote commands used during cluster bootstrapping.
- Uses SSH to communicate with nodes and the leader directly.
"""

import yaml
from lib.common.ssh_helpers import ssh, is_online

def check_swarm(advertise, debug=False):
    """
    Check if Swarm is initialized on the leader node.
    If not, initializes it using the provided advertise address.

    Returns:
        bool: True if Swarm was initialized, False if already active.
    """
    if ssh(advertise, "docker info | grep 'Swarm: active'", debug=debug).returncode != 0:
        ssh(advertise, f"docker swarm init --advertise-addr {advertise}", debug=debug)
        return True
    return False

def get_join_token(advertise, debug=False):
    """
    Fetch the current manager join token from the leader node.

    Returns:
        str: The join token as a string.
    """
    return ssh(advertise, "docker swarm join-token -q manager", debug=debug).stdout.strip()

def join_node(ip, token, advertise, debug=False):
    """
    Instruct a node to join the Swarm using the given token and advertise address.
    """
    ssh(ip, f"docker swarm join --token {token} {advertise}:2377", debug=debug)

def get_node_map(advertise, debug=False):
    """
    Returns a dictionary mapping hostname -> Swarm Node ID.

    Returns:
        dict[str, str]: Hostname-to-ID map of nodes visible to the Swarm leader.
    """
    output = ssh(advertise, "docker node ls --format '{{.Hostname}} {{.ID}}'", debug=debug).stdout.strip()
    return {
        line.split()[0]: line.split()[1]
        for line in output.splitlines() if line.strip()
    }
