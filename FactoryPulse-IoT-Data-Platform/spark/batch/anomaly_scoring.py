"""
FactoryPulse  --  Spark Batch: Anomaly Scoring
===============================================
BATCH LAYER (Lambda architecture)

Reads recent telemetry from the Iceberg table ``factory_db.raw_telemetry``,
applies rule-based anomaly scoring, classifies severity, then writes the
results to ``factory_db.anomaly_scores`` (Iceberg) and pushes WARNING /
CRITICAL alerts to ClickHouse ``factory_pulse.raw_alerts``.

MLflow is used to track each scoring run (parameters, counts, metrics).

Environment variables
---------------------
AWS_ACCESS_KEY_ID       MinIO / S3 access key
AWS_SECRET_ACCESS_KEY   MinIO / S3 secret key
CLICKHOUSE_USER         ClickHouse user  (default: default)
CLICKHOUSE_PASSWORD     ClickHouse password (default: clickhouse)
MLFLOW_TRACKING_URI     MLflow server     (default: http://mlflow:5000)
"""

import os
import uuid
import logging

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

import mlflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("anomaly_scoring")

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

MINIO_ENDPOINT = "http://minio:9000"
ICEBERG_REST_URI = "http://iceberg-rest:8181"

CLICKHOUSE_JDBC_URL = "jdbc:clickhouse://clickhouse:8123/factory_pulse"
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse")

CLICKHOUSE_JDBC_PROPERTIES = {
    "driver": "com.clickhouse.jdbc.ClickHouseDriver",
    "user": CLICKHOUSE_USER,
    "password": CLICKHOUSE_PASSWORD,
}

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

# ---------------------------------------------------------------------------
#  Scoring thresholds
# ---------------------------------------------------------------------------
TEMP_THRESHOLD = 95.0       # score += 30
VIBRATION_THRESHOLD = 3.0   # score += 25
PRESSURE_HIGH = 250.0       # score += 20
PRESSURE_LOW = 50.0         # score += 20
POWER_THRESHOLD = 90.0      # score += 15
# error_code is not null      score += 10


# ---------------------------------------------------------------------------
#  Spark session
# ---------------------------------------------------------------------------
def _build_spark_session() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("FactoryPulse-AnomalyScoring")
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


# ---------------------------------------------------------------------------
#  Iceberg table helpers
# ---------------------------------------------------------------------------
def _ensure_anomaly_table(spark: SparkSession) -> None:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS factory_db.factory_db")

    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS factory_db.factory_db.anomaly_scores (
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
            anomaly_score   INT,
            severity        STRING,
            scored_at       TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (severity)
        """
    )
    log.info("Iceberg table factory_db.factory_db.anomaly_scores is ready.")


# ---------------------------------------------------------------------------
#  Scoring logic
# ---------------------------------------------------------------------------
def compute_anomaly_scores(telemetry_df: DataFrame) -> DataFrame:
    """Apply rule-based anomaly scoring and severity classification."""

    scored = (
        telemetry_df
        # -- individual scores ------------------------------------------------
        .withColumn(
            "score_temp",
            F.when(F.col("temperature") > TEMP_THRESHOLD, 30).otherwise(0),
        )
        .withColumn(
            "score_vibration",
            F.when(F.col("vibration") > VIBRATION_THRESHOLD, 25).otherwise(0),
        )
        .withColumn(
            "score_pressure",
            F.when(
                (F.col("pressure") > PRESSURE_HIGH) | (F.col("pressure") < PRESSURE_LOW),
                20,
            ).otherwise(0),
        )
        .withColumn(
            "score_power",
            F.when(F.col("power_usage") > POWER_THRESHOLD, 15).otherwise(0),
        )
        .withColumn(
            "score_error",
            F.when(F.col("error_code").isNotNull(), 10).otherwise(0),
        )
        # -- aggregate score --------------------------------------------------
        .withColumn(
            "anomaly_score",
            F.col("score_temp")
            + F.col("score_vibration")
            + F.col("score_pressure")
            + F.col("score_power")
            + F.col("score_error"),
        )
        # -- severity classification ------------------------------------------
        .withColumn(
            "severity",
            F.when(F.col("anomaly_score") >= 50, "CRITICAL")
            .when(F.col("anomaly_score") >= 30, "WARNING")
            .otherwise("NORMAL"),
        )
        .withColumn("scored_at", F.current_timestamp())
        # -- drop intermediate columns ----------------------------------------
        .drop("score_temp", "score_vibration", "score_pressure", "score_power", "score_error")
    )

    return scored


# ---------------------------------------------------------------------------
#  Write helpers
# ---------------------------------------------------------------------------
def _write_scores_to_iceberg(scores_df: DataFrame) -> None:
    scores_projected = scores_df.select(
        "event_id",
        "device_id",
        "device_type",
        "location",
        "timestamp",
        "temperature",
        "vibration",
        "pressure",
        "humidity",
        "power_usage",
        "rpm",
        "error_code",
        "anomaly_score",
        "severity",
        "scored_at",
    )
    scores_projected.writeTo("factory_db.factory_db.anomaly_scores").overwritePartitions()
    log.info("Wrote anomaly scores to Iceberg.")


def _write_alerts_to_clickhouse(scores_df: DataFrame) -> None:
    """Push WARNING and CRITICAL rows to ClickHouse raw_alerts table."""
    generate_uuid = F.udf(lambda: str(uuid.uuid4()), StringType())

    alerts = (
        scores_df
        .filter(F.col("severity").isin("WARNING", "CRITICAL"))
        .withColumn("alert_id", generate_uuid())
        .withColumn("alert_type", F.lit("ANOMALY_SCORE"))
        .withColumn(
            "message",
            F.concat(
                F.lit("Anomaly detected on device "),
                F.col("device_id"),
                F.lit(" (score="),
                F.col("anomaly_score").cast("string"),
                F.lit(", severity="),
                F.col("severity"),
                F.lit(")"),
            ),
        )
        .withColumn("metric_name", F.lit("anomaly_score"))
        .withColumn("metric_value", F.col("anomaly_score").cast("double"))
        .withColumn("threshold", F.lit(30.0))
        .withColumn("resolved", F.lit(0).cast("int"))
        .withColumn("ingested_at", F.current_timestamp())
        .select(
            "alert_id",
            "device_id",
            "alert_type",
            "severity",
            "message",
            "metric_name",
            "metric_value",
            "threshold",
            "timestamp",
            "resolved",
            "ingested_at",
        )
    )

    alert_count = alerts.count()
    if alert_count == 0:
        log.info("No alerts to write to ClickHouse.")
        return

    (
        alerts.write
        .format("jdbc")
        .option("url", CLICKHOUSE_JDBC_URL)
        .option("dbtable", "factory_pulse.raw_alerts")
        .options(**CLICKHOUSE_JDBC_PROPERTIES)
        .mode("append")
        .save()
    )
    log.info("Wrote %d alerts to ClickHouse raw_alerts.", alert_count)


# ---------------------------------------------------------------------------
#  MLflow logging
# ---------------------------------------------------------------------------
def _log_to_mlflow(total_records: int, scores_df: DataFrame) -> None:
    """Log a scoring run to MLflow."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("factoryPulse-anomaly-scoring")

    severity_counts = (
        scores_df
        .groupBy("severity")
        .count()
        .collect()
    )
    count_map = {row["severity"]: row["count"] for row in severity_counts}

    with mlflow.start_run(run_name="anomaly-scoring-batch"):
        # -- parameters -------------------------------------------------------
        mlflow.log_param("temp_threshold", TEMP_THRESHOLD)
        mlflow.log_param("vibration_threshold", VIBRATION_THRESHOLD)
        mlflow.log_param("pressure_high", PRESSURE_HIGH)
        mlflow.log_param("pressure_low", PRESSURE_LOW)
        mlflow.log_param("power_threshold", POWER_THRESHOLD)
        mlflow.log_param("scoring_method", "rule_based")

        # -- metrics ----------------------------------------------------------
        mlflow.log_metric("total_records", total_records)
        mlflow.log_metric("critical_count", count_map.get("CRITICAL", 0))
        mlflow.log_metric("warning_count", count_map.get("WARNING", 0))
        mlflow.log_metric("normal_count", count_map.get("NORMAL", 0))

        anomaly_rate = (
            (count_map.get("CRITICAL", 0) + count_map.get("WARNING", 0))
            / max(total_records, 1)
        )
        mlflow.log_metric("anomaly_rate", round(anomaly_rate, 4))

    log.info(
        "MLflow run logged -- total=%d, CRITICAL=%d, WARNING=%d, NORMAL=%d, anomaly_rate=%.4f",
        total_records,
        count_map.get("CRITICAL", 0),
        count_map.get("WARNING", 0),
        count_map.get("NORMAL", 0),
        anomaly_rate,
    )


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("Starting FactoryPulse anomaly scoring batch job.")

    spark = _build_spark_session()
    _ensure_anomaly_table(spark)

    # -----------------------------------------------------------------
    #  Read recent telemetry from Iceberg
    # -----------------------------------------------------------------
    telemetry_df = spark.table("factory_db.factory_db.raw_telemetry")

    total_records = telemetry_df.count()
    log.info("Read %d telemetry records from Iceberg.", total_records)

    if total_records == 0:
        log.warning("No telemetry data available -- nothing to score.")
        spark.stop()
        return

    # -----------------------------------------------------------------
    #  Score
    # -----------------------------------------------------------------
    scores_df = compute_anomaly_scores(telemetry_df)
    scores_df.cache()

    # -----------------------------------------------------------------
    #  Write results
    # -----------------------------------------------------------------
    _write_scores_to_iceberg(scores_df)
    _write_alerts_to_clickhouse(scores_df)

    # -----------------------------------------------------------------
    #  Log to MLflow
    # -----------------------------------------------------------------
    _log_to_mlflow(total_records, scores_df)

    scores_df.unpersist()
    spark.stop()
    log.info("Anomaly scoring batch job complete.")


if __name__ == "__main__":
    main()
