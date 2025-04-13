import yaml
from lib.ssh_helpers import ssh

def sync_labels(advertise, nodes, node_map, prune=False, dry_run=False, debug=False):
    for name, meta in nodes.items():
        if name not in node_map:
            continue
        labels = set(meta.get("labels", []))
        current = ssh(advertise, f"docker node inspect {name} --format '{{{{json .Spec.Labels}}}}'", debug=debug).stdout.strip()
        try:
            current_labels = yaml.safe_load(current) or {}
        except:
            current_labels = {}

        for label in labels:
            if current_labels.get(label) != "true":
                if not dry_run:
                    ssh(advertise, f"docker node update --label-add {label}=true {name}", debug=debug)
                print(f"[labels] Added {label}=true to {name}")

        if prune:
            for label in current_labels:
                if label not in labels and label != name:
                    if not dry_run:
                        ssh(advertise, f"docker node update --label-rm {label} {name}", debug=debug)
                    print(f"[labels] Removed label {label} from {name}")
