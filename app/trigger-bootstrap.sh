#!/bin/sh

COMMAND_FILE="/tmp/swarm-orchestration.command.yml"

# Ensure file exists
touch "$COMMAND_FILE"

# Append if not already present
if ! grep -q "bootstrap_swarm" "$COMMAND_FILE"; then
  echo "- bootstrap_swarm" >> "$COMMAND_FILE"
  echo "bootstrap_swarm command added"
else
  echo "bootstrap_swarm already queued"
fi
