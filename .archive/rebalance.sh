#!/bin/bash

# Ensure environment variables are set
REBALANCE_LIST="${REBALANCE_LIST:-}"
REBALANCE_TIME="${REBALANCE_TIME:-300}"   # Default to 5 minutes
LOG_TO_FILE="${LOG_TO_FILE:-false}"       # Default: false (logs to stdout)
LOG_FILE="/var/log/swarm-rebalance.log"

sleep 30

# Function to log messages to both STDOUT and optionally a file
log() {
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    full_message="[$timestamp] $1"

    # Always print to stdout
    echo "$full_message"

    # Only write to file if LOG_TO_FILE=true
    if [[ "$LOG_TO_FILE" == "true" ]]; then
        echo "$full_message" >> "$LOG_FILE"
    fi
}

set -e  # Exit script on any error

log "🔄 Starting periodic Swarm rebalancing process..."

while true; do
    log "🔍 Fetching running Swarm services..."

    # Fetch all Swarm services
    ALL_SERVICES=$(docker service ls --format '{{.Name}}')

    # Ensure REBALANCE_LIST is set
    if [[ -z "$REBALANCE_LIST" ]]; then
        log "❌ No services defined for rebalancing! Sleeping for ${REBALANCE_TIME}s..."
        sleep "$REBALANCE_TIME"
        continue
    fi

    # Convert REBALANCE_LIST (comma-separated) to an array
    IFS=',' read -r -a services_array <<< "$REBALANCE_LIST"

    declare -A MATCHED_SERVICES

    # Match short service names to full names
    for full_service_name in $ALL_SERVICES; do
        for short_name in "${services_array[@]}"; do
            if [[ "$full_service_name" == *"_"$short_name ]]; then
                MATCHED_SERVICES["$short_name"]="$full_service_name"
                log "✅ Matched: $full_service_name (Short name: $short_name)"
            fi
        done
    done

    if [[ ${#MATCHED_SERVICES[@]} -eq 0 ]]; then
        log "❌ No matching services found in Swarm. Sleeping for ${REBALANCE_TIME}s..."
        sleep "$REBALANCE_TIME"
        continue
    fi

    # Get available memory & CPU for all nodes
    declare -A NODE_MEM NODE_CPU_UTIL

    for node in $(docker node ls --format '{{.Hostname}}'); do
        TOTAL_MEM=$(docker node inspect --format '{{.Description.Resources.MemoryBytes}}' "$node")
        TOTAL_CPU=$(docker node inspect --format '{{.Description.Resources.NanoCPUs}}' "$node")

        # Get current memory usage
        USED_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" | awk '{print $1}' | paste -sd+ | bc || echo "0")
        AVAILABLE_MEM=$((TOTAL_MEM - USED_MEM))

        # Get CPU usage from stats (percentage)
        CPU_USAGE=$(docker stats --no-stream --format "{{.CPUPerc}}" | awk -F'%' '{print $1}' | paste -sd+ | bc || echo "0")

        NODE_MEM["$node"]=$AVAILABLE_MEM
        NODE_CPU_UTIL["$node"]=$CPU_USAGE

        log "📊 Node: $node | Available Mem: ${AVAILABLE_MEM} | CPU Utilization: ${CPU_USAGE}%"
    done

    for short_name in "${!MATCHED_SERVICES[@]}"; do
        SERVICE_NAME="${MATCHED_SERVICES[$short_name]}"

        log "🔍 Checking service status for: $SERVICE_NAME"

        # Get the service state
        SERVICE_STATE=$(docker service ps --format '{{.CurrentState}}' "$SERVICE_NAME" | head -n 1)
        SERVICE_ERROR=$(docker service ps --format '{{.Error}}' "$SERVICE_NAME" | grep -v '^$' | head -n 1)

        if [[ -z "$SERVICE_STATE" ]]; then
            log "❌ Service $SERVICE_NAME does not exist or has no tasks. Skipping."
            continue
        fi

        if [[ "$SERVICE_STATE" == *"Complete"* || "$SERVICE_STATE" == *"Shutdown"* ]]; then
            log "⚠️ Service $SERVICE_NAME is marked as '$SERVICE_STATE'. Skipping."
            continue
        fi

        if [[ -n "$SERVICE_ERROR" ]]; then
            log "⚠️ Skipping $SERVICE_NAME due to recent failure: $SERVICE_ERROR"
            continue
        fi

        CURRENT_NODE=$(docker service ps --format '{{.Node}}' "$SERVICE_NAME" | head -n 1)

        # Determine best node based on deploy priority:
        # 1. Highest available memory
        # 2. If memory is equal, lowest CPU utilization

        BEST_NODE=$CURRENT_NODE
        MAX_MEM=${NODE_MEM[$CURRENT_NODE]}
        LOWEST_CPU=${NODE_CPU_UTIL[$CURRENT_NODE]}

        for node in "${!NODE_MEM[@]}"; do
            if [[ "${NODE_MEM[$node]}" -gt "$MAX_MEM" ]]; then
                BEST_NODE=$node
                MAX_MEM=${NODE_MEM[$node]}
                LOWEST_CPU=${NODE_CPU_UTIL[$node]}
            elif [[ "${NODE_MEM[$node]}" -eq "$MAX_MEM" ]] && [[ "${NODE_CPU_UTIL[$node]}" -lt "$LOWEST_CPU" ]]; then
                BEST_NODE=$node
                LOWEST_CPU=${NODE_CPU_UTIL[$node]}
            fi
        done

        if [[ "$BEST_NODE" == "$CURRENT_NODE" ]]; then
            log "⚖️ Service $SERVICE_NAME is already optimally placed on $CURRENT_NODE. No update needed."
            continue
        fi

        log "⚖️ Moving $SERVICE_NAME from $CURRENT_NODE → $BEST_NODE"
        docker service update --label-add dummy=$(date +%s) "$SERVICE_NAME"
        log "✅ Rebalance request sent for $SERVICE_NAME"
    done

    log "✅ Swarm rebalancing cycle complete. Sleeping for ${REBALANCE_TIME}s..."
    sleep "$REBALANCE_TIME"
done
