"""
FactoryPulse  --  Spark Structured Streaming: Telemetry Ingest
==============================================================
SPEED LAYER (Lambda architecture)

Reads raw telemetry events from the Kafka topic ``factory.telemetry.raw``,
parses the JSON payload, and continuously appends rows to the Iceberg table
``factory_db.raw_telemetry``.

Environment variables
---------------------
KAFKA_BROKER            Kafka bootstrap servers  (default: kafka:9092)
AWS_ACCESS_KEY_ID       MinIO / S3 access key
AWS_SECRET_ACCESS_KEY   MinIO / S3 secret key
"""

import os
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    TimestampType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("telemetry_stream")

# ---------------------------------------------------------------------------
#  Configuration from environment
# ---------------------------------------------------------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = "factory.telemetry.raw"

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

MINIO_ENDPOINT = "http://minio:9000"
ICEBERG_REST_URI = "http://iceberg-rest:8181"

CHECKPOINT_LOCATION = "s3a://factory-curated/checkpoints/telemetry_stream"

# ---------------------------------------------------------------------------
#  Telemetry JSON schema
# ---------------------------------------------------------------------------
TELEMETRY_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), True),
        StructField("device_id", StringType(), True),
        StructField("device_type", StringType(), True),
        StructField("location", StringType(), True),
        StructField("timestamp", StringType(), True),  # parsed later
        StructField("temperature", DoubleType(), True),
        StructField("vibration", DoubleType(), True),
        StructField("pressure", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("power_usage", DoubleType(), True),
        StructField("rpm", DoubleType(), True),
        StructField("error_code", StringType(), True),
    ]
)


def _build_spark_session() -> SparkSession:
    """Create a SparkSession configured for Iceberg + S3 (MinIO) + Kafka."""
    builder = (
        SparkSession.builder
        .appName("FactoryPulse-TelemetryStream")
        # ---- Iceberg catalog ------------------------------------------------
        .config("spark.sql.catalog.factory_db", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.factory_db.type", "rest")
        .config("spark.sql.catalog.factory_db.uri", ICEBERG_REST_URI)
        .config(
            "spark.sql.catalog.factory_db.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO",
        )
        .config("spark.sql.catalog.factory_db.s3.endpoint", MINIO_ENDPOINT)
        .config("spark.sql.catalog.factory_db.s3.path-style-access", "true")
        # ---- S3A / Hadoop ----------------------------------------------------
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config(
            "spark.hadoop.fs.s3a.impl",
            "org.apache.hadoop.fs.s3a.S3AFileSystem",
        )
        # ---- Iceberg extensions ----------------------------------------------
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.catalog.factory_db.warehouse", "s3a://factory-curated/iceberg")
    )
    return builder.getOrCreate()


def _ensure_namespace_and_table(spark: SparkSession) -> None:
    """Create the Iceberg namespace and raw_telemetry table if they do not exist."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS factory_db.factory_db")

    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS factory_db.factory_db.raw_telemetry (
            event_id        STRING,
            device_id       STRING,
            device_type     STRING,
            location        STRING,
            timestamp       TIMESTAMP,
            temperature     DOUBLE,
            vibration       DOUBLE,
            pressure        DOUBLE,
            humidity        DOUBLE,
            power_usage     DOUBLE,
            rpm             DOUBLE,
            error_code      STRING,
            ingested_at     TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(timestamp))
        """
    )
    log.info("Iceberg namespace and table factory_db.factory_db.raw_telemetry are ready.")


def main() -> None:
    log.info("Starting FactoryPulse telemetry streaming job (speed layer).")

    spark = _build_spark_session()
    _ensure_namespace_and_table(spark)

    # -----------------------------------------------------------------
    #  Read from Kafka
    # -----------------------------------------------------------------
    raw_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKER)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # -----------------------------------------------------------------
    #  Parse JSON and project columns
    # -----------------------------------------------------------------
    parsed = (
        raw_stream
        .selectExpr("CAST(value AS STRING) AS json_str")
        .select(F.from_json(F.col("json_str"), TELEMETRY_SCHEMA).alias("data"))
        .select("data.*")
        .withColumn("timestamp", F.to_timestamp(F.col("timestamp")))
        .withColumn("ingested_at", F.current_timestamp())
    )

    # -----------------------------------------------------------------
    #  Write to Iceberg (append micro-batches)
    # -----------------------------------------------------------------
    query = (
        parsed.writeStream
        .format("iceberg")
        .outputMode("append")
        .option("path", "factory_db.factory_db.raw_telemetry")
        .option("checkpointLocation", CHECKPOINT_LOCATION)
        .trigger(processingTime="10 seconds")
        .start()
    )

    log.info("Streaming query started. Waiting for termination...")
    query.awaitTermination()


if __name__ == "__main__":
    main()
