#!/usr/bin/env python3
"""
entrypoint.py
- Manual entrypoint for triggering orchestrator tasks via `docker exec`.
- Usage:
    docker exec <container> python /src/runner/entrypoint.py [label_sync|rebalance]

- Extensible command router to support additional runners.
"""

import sys
import signal
from runner import label_sync, rebalance  # Extendable

def usage():
    print("Usage: python entrypoint.py <command>")
    print("Available commands:")
    print("  label_sync   Run the label dependency sync loop")
    print("  rebalance    Run the service rebalance loop")
    sys.exit(1)

def handle_exit(signum, frame):
    print("📴 Received shutdown signal. Exiting...")
    sys.exit(0)

# Register clean shutdown signals
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    if len(sys.argv) != 2:
        usage()

    command = sys.argv[1]

    if command == "label_sync":
        label_sync.run()
    elif command == "rebalance":
        rebalance.run()
    # Future additions:
    # elif command == "bootstrap":
    #     from lib.bootstrap import bootstrap_runner
    #     bootstrap_runner.run()
    else:
        print(f"❌ Unknown command: {command}")
        usage()

if __name__ == "__main__":
    main()
