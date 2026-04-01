#!/bin/bash
# Run tests
set -e

cd "$(dirname "$0")/../.."

echo "Installing test dependencies..."
pip install -r tests/requirements.txt -q

echo "Running unit tests..."
python -m pytest tests/unit/ -v --tb=short

echo ""
echo "To run smoke tests (requires running services):"
echo "  python -m pytest tests/smoke/ -v -m smoke"
