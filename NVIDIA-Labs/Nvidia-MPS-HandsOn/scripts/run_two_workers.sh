#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Starting first worker..."
python gpu_worker.py &

echo "Starting second worker..."
python gpu_worker.py &

wait
echo "Both workers finished."