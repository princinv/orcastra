import yaml
from lib.ssh_helpers import ssh, is_online

def check_swarm(advertise, debug=False):
    if ssh(advertise, "docker info | grep 'Swarm: active'", debug=debug).returncode != 0:
        ssh(advertise, f"docker swarm init --advertise-addr {advertise}", debug=debug)
        return True
    return False

def get_join_token(advertise, debug=False):
    return ssh(advertise, "docker swarm join-token -q manager", debug=debug).stdout.strip()

def join_node(ip, token, advertise, debug=False):
    ssh(ip, f"docker swarm join --token {token} {advertise}:2377", debug=debug)

def get_node_map(advertise, debug=False):
    output = ssh(advertise, "docker node ls --format '{{.Hostname}} {{.ID}}'", debug=debug).stdout.strip()
    return {line.split()[0]: line.split()[1] for line in output.splitlines()}
