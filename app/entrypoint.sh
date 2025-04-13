#!/bin/sh

echo "Starting bootstrap_swarm.py in background..."
python /app/bootstrap_swarm.py &

echo "Starting label_dependencies.py in foreground..."
python python /app/label_dependencies.py

echo "🔁 Starting rebalance_services.py in foreground..."
exec python /app/rebalance_services.py