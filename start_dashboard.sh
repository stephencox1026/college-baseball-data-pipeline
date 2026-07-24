#!/bin/bash
# Start the Node.js/TypeScript scouting API + dashboard

cd "$(dirname "$0")"

pkill -f "python3 dashboard.py" 2>/dev/null
pkill -f "tsx watch src/index.ts" 2>/dev/null
pkill -f "node dist/index.js" 2>/dev/null
sleep 1

cd api
if [ ! -d node_modules ]; then
  echo "Installing API dependencies..."
  npm install
fi

echo "Starting College Baseball API (Node.js / TypeScript) on http://localhost:8080 ..."
npm run dev
