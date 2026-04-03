"""
FactoryPulse  --  Spark Batch: Ingest Reference & Historical Data
=================================================================
BATCH LAYER (Lambda architecture)

1. Reads device reference CSV from ``s3a://factory-raw/reference/devices.csv``
   and writes it to Iceberg ``factory_db.dim_devices`` **and** ClickHouse
   ``factory_pulse.raw_devices``.

2. Reads historical telemetry Parquet from ``s3a://factory-raw/historical/``
   and appends it to Iceberg ``factory_db.raw_telemetry`` **and** ClickHouse
   ``factory_pulse.raw_telemetry``.

Environment variables
---------------------
AWS_ACCESS_KEY_ID       MinIO / S3 access key
AWS_SECRET_ACCESS_KEY   MinIO / S3 secret key
CLICKHOUSE_USER         ClickHouse user  (default: default)
CLICKHOUSE_PASSWORD     ClickHouse password (default: clickhouse)
"""

import os
import logging

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest_reference")

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

MINIO_ENDPOINT = "http://minio:9000"
ICEBERG_REST_URI = "http://iceberg-rest:8181"

DEVICES_CSV_PATH = "s3a://factory-raw/reference/devices.csv"
HISTORICAL_PARQUET_PATH = "s3a://factory-raw/historical/"

CLICKHOUSE_JDBC_URL = "jdbc:clickhouse://clickhouse:8123/factory_pulse"
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse")

CLICKHOUSE_JDBC_PROPERTIES = {
    "driver": "com.clickhouse.jdbc.ClickHouseDriver",
    "user": CLICKHOUSE_USER,
    "password": CLICKHOUSE_PASSWORD,
}


# ---------------------------------------------------------------------------
#  Spark session
# ---------------------------------------------------------------------------
def _build_spark_session() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("FactoryPulse-IngestReference")
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
#  Iceberg namespace / table helpers
# ---------------------------------------------------------------------------
def _ensure_iceberg_tables(spark: SparkSession) -> None:
    """Create the Iceberg namespace and both target tables if they do not exist."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS factory_db.factory_db")

    # -- dim_devices ----------------------------------------------------------
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS factory_db.factory_db.dim_devices (
            device_id                   STRING,
            device_type                 STRING,
            manufacturer                STRING,
            model                       STRING,
            install_date                DATE,
            location                    STRING,
            zone                        STRING,
            maintenance_interval_days   INT,
            last_maintenance_date       DATE,
            status                      STRING,
            updated_at                  TIMESTAMP
        )
        USING iceberg
        """
    )

    # -- raw_telemetry --------------------------------------------------------
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
    log.info("Iceberg tables dim_devices and raw_telemetry are ready.")


# ---------------------------------------------------------------------------
#  Write helpers
# ---------------------------------------------------------------------------
def _write_to_clickhouse(df: DataFrame, table: str) -> None:
    """Append a DataFrame into a ClickHouse table via JDBC."""
    (
        df.write
        .format("jdbc")
        .option("url", CLICKHOUSE_JDBC_URL)
        .option("dbtable", table)
        .options(**CLICKHOUSE_JDBC_PROPERTIES)
        .mode("append")
        .save()
    )
    log.info("Wrote %d rows to ClickHouse %s.", df.count(), table)


# ---------------------------------------------------------------------------
#  Ingest device reference data
# ---------------------------------------------------------------------------
def ingest_devices(spark: SparkSession) -> None:
    log.info("Reading device reference CSV from %s", DEVICES_CSV_PATH)

    devices_df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(DEVICES_CSV_PATH)
        .withColumn("updated_at", F.current_timestamp())
    )

    record_count = devices_df.count()
    log.info("Loaded %d device records.", record_count)

    if record_count == 0:
        log.warning("No device records found -- skipping.")
        return

    # -- Iceberg (overwrite dimension each run) -------------------------------
    devices_df.writeTo("factory_db.factory_db.dim_devices").overwritePartitions()
    log.info("Wrote dim_devices to Iceberg.")

    # -- ClickHouse -----------------------------------------------------------
    _write_to_clickhouse(devices_df, "factory_pulse.raw_devices")


# ---------------------------------------------------------------------------
#  Ingest historical telemetry
# ---------------------------------------------------------------------------
def ingest_historical_telemetry(spark: SparkSession) -> None:
    log.info("Reading historical telemetry Parquet from %s", HISTORICAL_PARQUET_PATH)

    try:
        telemetry_df = (
            spark.read.parquet(HISTORICAL_PARQUET_PATH)
            .withColumn("ingested_at", F.current_timestamp())
        )
    except Exception as exc:
        log.warning("Could not read historical Parquet: %s. Skipping.", exc)
        return

    record_count = telemetry_df.count()
    log.info("Loaded %d historical telemetry records.", record_count)

    if record_count == 0:
        log.warning("No historical telemetry found -- skipping.")
        return

    # Select the columns that match the Iceberg table schema
    telemetry_projected = telemetry_df.select(
        "event_id",
        "device_id",
        "device_type",
        "location",
        F.col("timestamp").cast("timestamp").alias("timestamp"),
        "temperature",
        "vibration",
        "pressure",
        "humidity",
        "power_usage",
        "rpm",
        "error_code",
        "ingested_at",
    )

    # -- Iceberg (append) -----------------------------------------------------
    telemetry_projected.writeTo("factory_db.factory_db.raw_telemetry").append()
    log.info("Appended historical telemetry to Iceberg raw_telemetry.")

    # -- ClickHouse -----------------------------------------------------------
    _write_to_clickhouse(telemetry_projected, "factory_pulse.raw_telemetry")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("Starting FactoryPulse batch ingest (batch layer).")

    spark = _build_spark_session()
    _ensure_iceberg_tables(spark)

    ingest_devices(spark)
    ingest_historical_telemetry(spark)

    spark.stop()
    log.info("Batch ingest complete.")


if __name__ == "__main__":
    main()
