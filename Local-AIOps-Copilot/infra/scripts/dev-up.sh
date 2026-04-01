#!/bin/bash
# Start all services in CPU-only dev mode
set -e

echo "Starting Local-AIOps-Copilot in DEV mode (CPU-only)..."
echo "Backend: ${LLM_BACKEND:-mock}"

cd "$(dirname "$0")/../.."

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

docker compose -f docker-compose.dev.yml up --build "$@"
