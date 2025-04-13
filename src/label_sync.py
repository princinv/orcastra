#!/usr/bin/env python3
"""
Entrypoint script for running the label dependency resolver.

Delegates logic to the label_sync_runner module which coordinates anchor labeling
and dependent restarts.
"""

from lib.label_sync_runner import run

if __name__ == "__main__":
    run()
