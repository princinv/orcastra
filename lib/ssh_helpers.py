import subprocess

def is_online(ip):
    return subprocess.call(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def ssh(host, command, debug=False):
    if debug:
        print(f"[ssh_helpers] SSH {host}: {command}")
    return subprocess.run(["ssh", host, command], capture_output=True, text=True)
