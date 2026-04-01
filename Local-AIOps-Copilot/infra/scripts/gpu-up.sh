#!/bin/bash
# Start all services in GPU mode (for second machine)
set -e

echo "Starting Local-AIOps-Copilot in GPU mode..."
echo "Backend: ${LLM_BACKEND:-vllm}"

cd "$(dirname "$0")/../.."

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    sed -i 's/LLM_BACKEND=mock/LLM_BACKEND=vllm/' .env
    sed -i 's/ENVIRONMENT=dev/ENVIRONMENT=gpu/' .env
    echo "Created .env configured for GPU mode"
fi

# Start with specific profile
PROFILE=${1:-vllm}
echo "Using profile: $PROFILE"

docker compose -f docker-compose.gpu.yml --profile "$PROFILE" up --build "${@:2}"
