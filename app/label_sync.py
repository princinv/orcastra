#!/usr/bin/env python3
"""
Entrypoint script for running the label dependency resolver.

Delegates logic to the `lib.labels` and `lib.node_labels` modules.
"""

from lib.labels import run_label_dependency_manager

if __name__ == "__main__":
    run_label_dependency_manager()
