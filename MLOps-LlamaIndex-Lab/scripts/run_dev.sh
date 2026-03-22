#!/usr/bin/env bash
# =============================================================================
# Quick-start: run the app in development mode (requires venv + Qdrant).
# =============================================================================
set -euo pipefail

echo "Starting MLOps-LlamaIndex-Lab in dev mode…"
echo "Make sure Qdrant is running on localhost:6333"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
