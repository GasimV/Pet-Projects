#!/usr/bin/env bash
# Simple helper script to run two GPU workers in parallel
# for the NVIDIA MPS hands-on lab.

set -e

# Go to the directory where this script is located
cd "$(dirname "$0")"

echo "Starting first worker..."
python gpu_worker.py &

echo "Starting second worker..."
python gpu_worker.py &

echo "Both workers started. Waiting for them to finish..."
wait
echo "Both workers finished."
