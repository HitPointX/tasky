#!/bin/bash
# Launch Tasky from anywhere — handles venv activation automatically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".venv/bin/python3" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -q psutil
fi

exec .venv/bin/python3 main.py "$@"
