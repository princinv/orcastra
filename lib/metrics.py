# lib/metrics.py
import subprocess
import requests

def get_node_exporter_memory(url):
    try:
        response = requests.get(url, timeout=2)
        lines = response.text.split('\n')
        mem_total = mem_free = 0
        for line in lines:
            if line.startswith("node_memory_MemTotal_bytes"):
                mem_total = float(line.split()[-1])
            elif line.startswith("node_memory_MemAvailable_bytes"):
                mem_free = float(line.split()[-1])
        if mem_total and mem_free:
            return round(mem_free / (1024**3), 2)
    except Exception as e:
        print(f"Failed to scrape metrics: {e}")
    return None

def get_docker_reported_memory(node_names):
    memory_data = {}
    for node in node_names:
        try:
            result = subprocess.run(
                ["docker", "node", "inspect", node, "--format", "{{.Description.Resources.MemoryBytes}}"],
                capture_output=True, text=True, timeout=3
            )
            mem_bytes = int(result.stdout.strip())
            memory_data[node] = round(mem_bytes / (1024**3), 2)
        except Exception as e:
            print(f"Failed to get Docker memory for {node}: {e}")
    return memory_data

def get_container_memory_usage():
    usage = {}
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}:{{.MemUsage}}"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split('\n'):
            try:
                name, mem = line.split(":")
                mem_value = mem.split("/")[0].strip()
                if mem_value.lower().endswith("mb"):
                    value = float(mem_value[:-2]) / 1024
                elif mem_value.lower().endswith("gb"):
                    value = float(mem_value[:-2])
                else:
                    value = 0
                usage[name] = round(value, 2)
            except Exception:
                continue
    except Exception as e:
        print(f"Failed to collect container memory stats: {e}")
    return usage
