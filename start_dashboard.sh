#!/bin/bash
# Script to start the dashboard server

cd "$(dirname "$0")"

# Kill any existing dashboard processes
pkill -f "python3 dashboard.py" 2>/dev/null
sleep 1

# Start the dashboard
echo "Starting College Baseball Dashboard..."
python3 dashboard.py

