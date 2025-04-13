"""
labels.py
- Provides reusable logic to apply and remove labels on Swarm nodes using the Docker SDK.
"""

def apply_label(client, node_id, key, value="true", dry_run=False):
    node = client.nodes.get(node_id)
    node.reload()
    spec = node.attrs["Spec"]
    labels = spec.get("Labels", {})
    labels[key] = value
    if not dry_run:
        node.update({
            'Role': spec['Role'],
            'Availability': spec['Availability'],
            'Labels': labels
        })

def remove_label(client, node, label_key, dry_run=False):
    node.reload()
    spec = node.attrs["Spec"]
    labels = spec.get("Labels", {})
    if label_key in labels:
        labels.pop(label_key)
        if not dry_run:
            node.update({
                'Role': spec['Role'],
                'Availability': spec['Availability'],
                'Labels': labels
            })
