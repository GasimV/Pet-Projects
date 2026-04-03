#!/usr/bin/env bash
# Wait for FactoryPulse services to become healthy.
set -euo pipefail

MAX_WAIT=120  # seconds

wait_for() {
  local name="$1" url="$2" elapsed=0
  printf "  Waiting for %-20s" "$name..."
  while ! curl -sf "$url" > /dev/null 2>&1; do
    sleep 2
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
      echo " TIMEOUT"
      return 1
    fi
  done
  echo " OK (${elapsed}s)"
}

echo "=== Waiting for FactoryPulse services ==="
wait_for "Kafka"        "http://localhost:29092" || true  # Kafka doesn't have HTTP, skip
wait_for "MinIO"        "http://localhost:9000/minio/health/live"
wait_for "ClickHouse"   "http://localhost:8123/ping"
wait_for "FastAPI"      "http://localhost:8000/health"
wait_for "Grafana"      "http://localhost:3000/api/health"
wait_for "Prometheus"   "http://localhost:9090/-/healthy"
wait_for "Qdrant"       "http://localhost:6333/readyz"
wait_for "MLflow"       "http://localhost:5050/"
wait_for "Airflow"      "http://localhost:8082/health"
wait_for "Marquez"      "http://localhost:5001/api/v1/namespaces"
wait_for "Iceberg REST" "http://localhost:8181/v1/config"
echo ""
echo "=== All services ready ==="
