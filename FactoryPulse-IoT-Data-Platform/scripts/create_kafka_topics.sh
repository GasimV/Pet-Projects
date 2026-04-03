#!/usr/bin/env bash
# Create Kafka topics for FactoryPulse.
set -euo pipefail

BROKER="${KAFKA_BROKER:-kafka:9092}"

topics=(
  "factory.telemetry.raw:3"
  "factory.alerts:1"
  "factory.incidents:1"
)

for entry in "${topics[@]}"; do
  topic="${entry%%:*}"
  partitions="${entry##*:}"
  echo "Creating topic: $topic (partitions=$partitions)"
  kafka-topics.sh --bootstrap-server "$BROKER" \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions "$partitions" \
    --replication-factor 1
done

echo "Done. Topics:"
kafka-topics.sh --bootstrap-server "$BROKER" --list
