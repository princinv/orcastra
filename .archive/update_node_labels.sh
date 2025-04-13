#!/bin/bash

# Ensure DATABASE_LIST is set
DATABASE_LIST="${DATABASE_LIST:-}"
RELABEL_TIME=${RELABEL_TIME:-60}

LOG_TO_FILE="${LOG_TO_FILE:-false}"   # Default: false (logs to stdout)
LOG_FILE="/var/log/swarm-labels.log"

# Determine if we're using the proxy or direct socket
if [[ -S "/var/run/docker.sock" ]]; then
    DOCKER_CMD="docker"
else
    DOCKER_CMD="docker --host ${DOCKER_HOST}"
fi

# Function to log messages to both STDOUT and optionally a file
log() {
    local message="$1"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    full_message="[$timestamp] $message"

    # Always print to stdout
    echo "$full_message"

    # Only write to file if LOG_TO_FILE=true
    if [[ "$LOG_TO_FILE" == "true" ]]; then
        echo "$full_message" >> "$LOG_FILE"
    fi
}

set -e

while true; do
    log "🔍 Fetching running Swarm services..."

    # 🔥 Print current labels BEFORE making changes
    echo "🔍 Current Node Labels:"
    $DOCKER_CMD node inspect $($DOCKER_CMD node ls -q) --format '{{ .ID }}: {{ json .Spec.Labels }}'

    # Log the exact command that is running
    log "Executing: $DOCKER_CMD service ls --format '{{.Name}}'"
    ALL_SERVICES=$($DOCKER_CMD service ls --format '{{.Name}}')

    # Reset SERVICES array
    declare -A SERVICES

    # Convert DATABASE_LIST from "semaphore_db,gitea_db,komodo_db" → Searchable array
    IFS=',' read -r -a services_array <<< "$DATABASE_LIST"

    # Match service names dynamically with their stack prefixes
    for full_service_name in $ALL_SERVICES; do
        for short_name in "${services_array[@]}"; do
            if [[ "$full_service_name" == *"_"$short_name ]]; then
                SERVICES["$short_name"]="$full_service_name"
                log "✅ Found service: $full_service_name (Matches: $short_name)"
            fi
        done
    done

    log "🔄 Updating Swarm node labels for tracked services..."

    # Step 1: Remove old labels from all nodes
    for node in $($DOCKER_CMD node ls --format '{{.ID}}'); do
        for label in "${!SERVICES[@]}"; do
            log "Executing: $DOCKER_CMD node update --label-rm '$label' '$node'"
            if $DOCKER_CMD node update --label-rm "$label" "$node" 2>/dev/null; then
                log "🗑️ Removed label '$label' from node $node."
            fi
        done
    done

    # Step 2: Apply correct labels to nodes where services are running
    for label in "${!SERVICES[@]}"; do
        SERVICE_NAME="${SERVICES[$label]}"

        log "Executing: $DOCKER_CMD service inspect '$SERVICE_NAME'"
        if ! $DOCKER_CMD service inspect "$SERVICE_NAME" &>/dev/null; then
            log "❌ Service $SERVICE_NAME does not exist in Swarm. Skipping."
            continue
        fi

        log "Executing: $DOCKER_CMD service ps --filter 'desired-state=running' --format '{{.Node}}' '$SERVICE_NAME'"
        SERVICE_NODE=$($DOCKER_CMD service ps --filter "desired-state=running" --format '{{.Node}}' "$SERVICE_NAME" | head -n 1 || echo "")

        if [[ -z "$SERVICE_NODE" ]]; then
            log "❌ $SERVICE_NAME is not running. No label applied."
            continue
        fi

        log "Executing: $DOCKER_CMD node update --label-add '$label=true' '$SERVICE_NODE'"
        if $DOCKER_CMD node update --label-add "$label=true" "$SERVICE_NODE"; then
            log "✅ $SERVICE_NAME is running on node: $SERVICE_NODE. Applied label '$label=true'."
        else
            log "❌ Failed to apply label '$label' to node $SERVICE_NODE."
        fi

    done

        # OPTIONAL: Trigger service update --force for services that depend on labels
    for label in "${!SERVICES[@]}"; do
        MAIN_SERVICE="${STACK_NAME}_${label/_db/}"
        DB_SERVICE="${SERVICES[$label]}"

        MAIN_NODE=$($DOCKER_CMD service ps --filter "desired-state=running" --format '{{.Node}}' "$MAIN_SERVICE" | head -n 1 || echo "")
        DB_NODE=$($DOCKER_CMD service ps --filter "desired-state=running" --format '{{.Node}}' "$DB_SERVICE" | head -n 1 || echo "")

        if [[ -z "$MAIN_NODE" || -z "$DB_NODE" ]]; then
            log "❌ Unable to determine placement for $MAIN_SERVICE or $DB_SERVICE. Skipping update."
            continue
        fi

        if [[ "$MAIN_NODE" != "$DB_NODE" ]]; then
            log "🔁 $MAIN_SERVICE is not co-located with $DB_SERVICE. Forcing update."
            $DOCKER_CMD service update --force "$MAIN_SERVICE"
        else
            log "✅ $MAIN_SERVICE already on same node as $DB_SERVICE. No update needed."
        fi
    done

    log "✅ All labels updated successfully!"
    sleep $RELABEL_TIME
done
