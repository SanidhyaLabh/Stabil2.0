#!/usr/bin/env bash
# STABIL - 1-Click Launcher for Linux & macOS

set -e
cd "$(dirname "$0")"

echo "========================================================"
echo "         STABIL - Surgical Precision Tracking"
echo "========================================================"

# Check for virtual environment
if [ -d "venv/bin" ]; then
    echo "[*] Activating virtual environment..."
    source venv/bin/activate
fi

python3 run.py "$@"
