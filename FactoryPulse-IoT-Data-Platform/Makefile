# FactoryPulse IoT Data Platform — Makefile
# ------------------------------------------
# Works with: GNU Make, mingw32-make, or via make.bat on Windows.
#
# On Windows without `make`, use:
#   mingw32-make up
#   -- or --
#   make.bat up

COMPOSE       = docker compose
COMPOSE_FLINK = docker compose -f docker-compose.yml -f docker-compose.flink.yml
ENV_FILE      = .env
SHELL         = sh

.PHONY: help env up stop down restart logs ps \
        up-flink down-flink \
        topics minio-buckets \
        spark-streaming spark-batch spark-anomaly \
        flink-streaming \
        dbt-run dbt-test \
        feast-apply feast-materialize \
        qdrant-ingest \
        ge-validate \
        api-test demo \
        clean prune

help: ## Show this help
	@echo "FactoryPulse — available targets:"
	@echo ""
	@echo "  up                 Start core stack (Kafka + Spark streaming)"
	@echo "  stop               Stop running services without removing containers"
	@echo "  down               Stop all services"
	@echo "  restart            Restart everything"
	@echo "  logs               Tail logs (SVC=<name> to filter)"
	@echo "  ps                 Show running services"
	@echo "  up-flink           Start stack with Flink overlay"
	@echo "  down-flink         Stop Flink overlay"
	@echo "  topics             Create Kafka topics"
	@echo "  minio-buckets      Create MinIO buckets"
	@echo "  spark-streaming    Launch Spark Structured Streaming"
	@echo "  spark-batch        Run Spark batch ingest"
	@echo "  spark-anomaly      Run anomaly scoring"
	@echo "  flink-streaming    Submit Flink streaming job"
	@echo "  dbt-run            Run dbt models"
	@echo "  dbt-test           Run dbt tests"
	@echo "  feast-apply        Apply Feast feature definitions"
	@echo "  feast-materialize  Materialize features to Redis"
	@echo "  qdrant-ingest      Ingest vectors into Qdrant"
	@echo "  ge-validate        Run data quality validation"
	@echo "  api-test           Run API tests"
	@echo "  demo               Run full demo script"
	@echo "  clean              Stop + remove volumes"
	@echo "  prune              Full cleanup including images"

# ---------- Environment ----------
env: ## Create .env from .env.example
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env created from .env.example"; else echo ".env already exists"; fi

# ---------- Core Stack ----------
up: env ## Start core stack (Kafka + Spark streaming)
	$(COMPOSE) --env-file $(ENV_FILE) up -d
	@echo "Waiting for services to initialize..."
	@sleep 8
	-$(MAKE) topics
	-$(MAKE) minio-buckets
	@echo ""
	@echo "FactoryPulse is running.  http://localhost:3000 (Grafana)"

stop: ## Stop running services without removing containers
	$(COMPOSE) --env-file $(ENV_FILE) stop
	$(COMPOSE_FLINK) --env-file $(ENV_FILE) stop || exit 0

down: ## Stop all services
	$(COMPOSE) --env-file $(ENV_FILE) down
	$(COMPOSE_FLINK) --env-file $(ENV_FILE) down || exit 0

restart: down up ## Restart everything

logs: ## Tail logs (pass SVC=<name> to filter)
ifdef SVC
	$(COMPOSE) logs -f $(SVC)
else
	$(COMPOSE) logs -f --tail=100
endif

ps: ## Show running services
	$(COMPOSE) ps

# ---------- Flink Overlay ----------
up-flink: env ## Start stack with Flink instead of Spark Streaming
	$(COMPOSE_FLINK) --env-file $(ENV_FILE) up -d
	@sleep 8
	-$(MAKE) topics
	-$(MAKE) minio-buckets

down-flink: ## Stop Flink overlay
	$(COMPOSE_FLINK) --env-file $(ENV_FILE) down

# ---------- Bootstrap ----------
topics: ## Create Kafka topics
	$(COMPOSE) exec -T kafka kafka-topics --bootstrap-server kafka:9092 \
	  --create --if-not-exists --topic factory.telemetry.raw   --partitions 3 --replication-factor 1
	$(COMPOSE) exec -T kafka kafka-topics --bootstrap-server kafka:9092 \
	  --create --if-not-exists --topic factory.alerts           --partitions 1 --replication-factor 1
	$(COMPOSE) exec -T kafka kafka-topics --bootstrap-server kafka:9092 \
	  --create --if-not-exists --topic factory.incidents         --partitions 1 --replication-factor 1
	@echo "Kafka topics created"

minio-buckets: ## Create MinIO buckets
	-$(COMPOSE) exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin
	$(COMPOSE) exec -T minio mc mb --ignore-existing local/factory-raw
	$(COMPOSE) exec -T minio mc mb --ignore-existing local/factory-curated
	$(COMPOSE) exec -T minio mc mb --ignore-existing local/mlflow-artifacts
	@echo "MinIO buckets created"

# ---------- Spark ----------
spark-streaming: ## Launch Spark Structured Streaming job
	$(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
	  --master local[*] \
	  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.iceberg:iceberg-aws-bundle:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4 \
	  /opt/spark-apps/streaming/telemetry_stream.py

spark-batch: ## Run Spark batch ingest (reference data)
	$(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
	  --master local[*] \
	  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.iceberg:iceberg-aws-bundle:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4 \
	  /opt/spark-apps/batch/ingest_reference.py

spark-anomaly: ## Run Spark batch anomaly scoring
	$(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
	  --master local[*] \
	  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.iceberg:iceberg-aws-bundle:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4 \
	  /opt/spark-apps/batch/anomaly_scoring.py

# ---------- Flink ----------
flink-streaming: ## Submit Flink streaming job
	$(COMPOSE) exec -T flink-jobmanager flink run -py /opt/flink-apps/telemetry_stream.py

# ---------- dbt ----------
dbt-run: ## Run dbt models
	$(COMPOSE) run --rm dbt run

dbt-test: ## Run dbt tests
	$(COMPOSE) run --rm dbt test

# ---------- Feast ----------
feast-apply: ## Apply Feast feature definitions
	$(COMPOSE) run --rm feast feast apply

feast-materialize: ## Materialize features to Redis
	$(COMPOSE) run --rm feast feast materialize-incremental $$(date -u +"%Y-%m-%dT%H:%M:%S")

# ---------- Qdrant ----------
qdrant-ingest: ## Ingest incident texts into Qdrant
	$(COMPOSE) run --rm api python /app/qdrant_ingest.py

# ---------- Great Expectations ----------
ge-validate: ## Run Great Expectations validation
	$(COMPOSE) run --rm api python /app/ge_validate.py

# ---------- Tests ----------
api-test: ## Run API tests
	$(COMPOSE) run --rm api pytest /app/tests/ -v

# ---------- Demo ----------
demo: ## Run full demo script
	bash scripts/demo.sh

# ---------- Cleanup ----------
clean: down ## Stop containers and remove volumes
	$(COMPOSE) --env-file $(ENV_FILE) down -v

prune: clean ## Full cleanup including images
	docker system prune -f
