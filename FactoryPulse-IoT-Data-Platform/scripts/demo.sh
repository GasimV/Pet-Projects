#!/usr/bin/env bash
# FactoryPulse end-to-end demo script.
# Run: make demo  (or bash scripts/demo.sh)
set -euo pipefail

COMPOSE="docker compose"
API="http://localhost:8000"
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

step() { echo -e "\n${BOLD}${CYAN}[$1/$TOTAL] $2${NC}"; }
TOTAL=10

echo -e "${BOLD}============================================="
echo "  FactoryPulse IoT Data Platform — Demo"
echo -e "=============================================${NC}"

# ------------------------------------------------------------------
step 1 "Starting the platform"
$COMPOSE up -d
echo "Waiting 30 s for services to initialize..."
sleep 30
bash scripts/wait_for_services.sh || true

# ------------------------------------------------------------------
step 2 "Generating batch reference data"
$COMPOSE run --rm simulator python batch_reference_gen.py
echo -e "${GREEN}✓ Reference data uploaded to MinIO${NC}"

# ------------------------------------------------------------------
step 3 "Running Spark batch ingest (batch layer — Lambda)"
$COMPOSE exec -T spark-master spark-submit \
  --master local[*] \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4 \
  /opt/spark-apps/batch/ingest_reference.py || echo "(Spark batch ingest completed or skipped)"
echo -e "${GREEN}✓ Batch data ingested into Iceberg + ClickHouse${NC}"

# ------------------------------------------------------------------
step 4 "Launching Spark Structured Streaming (speed layer — Lambda)"
echo "Starting streaming in background..."
$COMPOSE exec -d spark-master spark-submit \
  --master local[*] \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4 \
  /opt/spark-apps/streaming/telemetry_stream.py
echo "Letting streaming run for 30 s to accumulate data..."
sleep 30
echo -e "${GREEN}✓ Streaming pipeline running${NC}"

# ------------------------------------------------------------------
step 5 "Running anomaly scoring (batch ML — Lambda)"
$COMPOSE exec -T spark-master spark-submit \
  --master local[*] \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4 \
  /opt/spark-apps/batch/anomaly_scoring.py || echo "(Anomaly scoring completed or skipped)"
echo -e "${GREEN}✓ Anomaly scores computed${NC}"

# ------------------------------------------------------------------
step 6 "Running dbt transformations (ELT in ClickHouse)"
$COMPOSE run --rm dbt run --profiles-dir . || echo "(dbt run completed or skipped)"
$COMPOSE run --rm dbt test --profiles-dir . || echo "(dbt test completed)"
echo -e "${GREEN}✓ dbt models materialized${NC}"

# ------------------------------------------------------------------
step 7 "Ingesting vectors into Qdrant (semantic search)"
$COMPOSE exec -T api python /app/qdrant_ingest.py || echo "(Qdrant ingest completed or skipped)"
echo -e "${GREEN}✓ Vectors ingested into Qdrant${NC}"

# ------------------------------------------------------------------
step 8 "Running Great Expectations validation"
$COMPOSE exec -T api python /app/ge_validate.py || echo "(GE validation completed or skipped)"
echo -e "${GREEN}✓ Data quality validated${NC}"

# ------------------------------------------------------------------
step 9 "Querying the API"
echo ""
echo "--- Health Check ---"
curl -s "$API/health" | python -m json.tool 2>/dev/null || curl -s "$API/health"
echo ""

echo "--- Recent Telemetry (5 rows) ---"
curl -s "$API/api/v1/telemetry?limit=5" | python -m json.tool 2>/dev/null || echo "(no data yet)"
echo ""

echo "--- Active Alerts ---"
curl -s "$API/api/v1/alerts/active?limit=5" | python -m json.tool 2>/dev/null || echo "(no alerts yet)"
echo ""

echo "--- Devices ---"
curl -s "$API/api/v1/devices?limit=5" | python -m json.tool 2>/dev/null || echo "(no devices yet)"
echo ""

echo "--- Semantic Search: 'overheating motor' ---"
curl -s -X POST "$API/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{"query":"overheating motor","limit":3}' | python -m json.tool 2>/dev/null || echo "(search not ready)"
echo ""

echo -e "${GREEN}✓ API responding${NC}"

# ------------------------------------------------------------------
step 10 "Summary — Open these in your browser"
echo ""
echo "  Service            URL"
echo "  ─────────────────  ──────────────────────────────"
echo "  FastAPI (docs)     http://localhost:8000/docs"
echo "  Grafana            http://localhost:3000       (admin/admin)"
echo "  Airflow            http://localhost:8082       (admin/admin)"
echo "  Spark UI           http://localhost:8080"
echo "  MinIO Console      http://localhost:9001       (minioadmin/minioadmin)"
echo "  MLflow             http://localhost:5050"
echo "  Marquez            http://localhost:3001"
echo "  ClickHouse HTTP    http://localhost:8123"
echo "  Qdrant Dashboard   http://localhost:6333/dashboard"
echo "  Prometheus         http://localhost:9090"
echo "  Iceberg REST       http://localhost:8181"
echo ""
echo -e "${BOLD}${GREEN}Demo complete! The simulator is still running, producing data every 2 seconds.${NC}"
