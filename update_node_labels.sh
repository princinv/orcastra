#!/bin/bash

# Define services and their respective labels
STACK_NAME="swarm-dev" 

declare -A SERVICES
SERVICES=(
    ["semaphore_db"]="${STACK_NAME}_semaphore_db"
    ["gitea_db"]="${STACK_NAME}_gitea_db"
    ["komodo_db"]="${STACK_NAME}_komodo_db"
)

# 🔥 Print current labels BEFORE making changes
echo "🔍 Current Node Labels:"
docker node inspect $(docker node ls -q) --format '{{ .ID }}: {{ json .Spec.Labels }}'


echo "🔄 Updating Swarm node labels for tracked services..."

# Step 1: Remove old labels from all nodes
docker node ls --format '{{.ID}}' | while read -r node; do
    for label in "${!SERVICES[@]}"; do
        docker node update --label-rm "$label" "$node" 2>/dev/null
    done
done

# Step 2: Apply correct labels to nodes where services are running
for label in "${!SERVICES[@]}"; do
    SERVICE_NAME="${SERVICES[$label]}"
    SERVICE_NODE=$(docker service ps "$SERVICE_NAME" --format '{{.Node}}' | head -n 1)

    if [ -z "$SERVICE_NODE" ]; then
        echo "❌ $SERVICE_NAME is not running. No label applied."
        continue
    fi

    echo "✅ $SERVICE_NAME is running on node: $SERVICE_NODE. Applying label '$label=true'."
    docker node update --label-add "$label=true" "$SERVICE_NODE"
done

echo "✅ All labels updated successfully!"
sleep 60  # Wait before next update
exec "$0"  # Loop infinitely
