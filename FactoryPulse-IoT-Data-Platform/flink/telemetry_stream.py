"""
FactoryPulse — Flink Telemetry Streaming Job (Kappa Architecture)
=================================================================

KAPPA ARCHITECTURE APPROACH
----------------------------
Traditional Lambda architecture maintains two parallel pipelines:
  - A *batch layer* that reprocesses the full history periodically (Spark batch)
  - A *speed layer* that handles real-time events (Spark Structured Streaming)

This Flink job implements the **Kappa architecture** alternative: a single
streaming pipeline handles *all* processing.  Historical reprocessing is
achieved by simply replaying the Kafka topic from an earlier offset rather
than running a separate batch job.  Benefits:

  1. Single codebase — no drift between batch and streaming logic.
  2. Lower operational complexity — one framework to monitor and tune.
  3. Flink's event-time semantics and exactly-once guarantees make the
     stream pipeline as correct as a batch recomputation.

Pipeline overview
-----------------
  Kafka (factory.telemetry.raw)
      |
      v
  [Flink] Parse JSON telemetry
      |
      +---> Raw events  --> JSON files on MinIO  (s3a://factory-curated/flink-output/)
      |                     partitioned by dt=YYYY-MM-DD
      |
      +---> 1-min tumbling window aggregates --> JSON on MinIO
                                (s3a://factory-curated/flink-aggregates/)
                                partitioned by dt=YYYY-MM-DD

Environment variables (set via docker-compose.flink.yml):
  KAFKA_BROKER          — bootstrap servers  (default: kafka:9092)
  KAFKA_TOPIC_TELEMETRY — source topic       (default: factory.telemetry.raw)
  MINIO_ENDPOINT        — S3 endpoint        (default: http://minio:9000)
  AWS_ACCESS_KEY_ID     — MinIO access key   (default: minioadmin)
  AWS_SECRET_ACCESS_KEY — MinIO secret key   (default: minioadmin)
"""

import os
import logging

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings

# ---------------------------------------------------------------------------
#  Configuration from environment
# ---------------------------------------------------------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_TELEMETRY", "factory.telemetry.raw")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

RAW_OUTPUT_PATH = "s3a://factory-curated/flink-output/"
AGGREGATES_OUTPUT_PATH = "s3a://factory-curated/flink-aggregates/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telemetry_stream")


def configure_environment():
    """
    Create and configure the Flink streaming + table environment.

    Key settings:
      - Checkpointing every 60 s for exactly-once fault tolerance
      - S3A filesystem configuration pointing at MinIO
      - Parallelism kept low for a dev / single-node setup
    """
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)

    # -- Checkpointing (required for exactly-once sinks) ---------------------
    env.enable_checkpointing(60_000)  # every 60 seconds

    # -- Table environment ----------------------------------------------------
    settings = EnvironmentSettings.in_streaming_mode()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    # -- S3A / MinIO configuration via Flink SQL hints is not available,
    #    so we set Hadoop-style config through the Flink configuration.
    config = t_env.get_config()
    config.set("fs.s3a.endpoint", MINIO_ENDPOINT)
    config.set("fs.s3a.access.key", AWS_ACCESS_KEY)
    config.set("fs.s3a.secret.key", AWS_SECRET_KEY)
    config.set("fs.s3a.path.style.access", "true")
    config.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    # Disable SSL for local MinIO
    config.set("fs.s3a.connection.ssl.enabled", "false")

    # -- Ensure connector JARs on the classpath are discovered ----------------
    # The JARs were already placed in /opt/flink/lib/ by the Dockerfile,
    # so they are on the classpath automatically.

    return env, t_env


# ===========================================================================
#  1. Kafka Source Table — raw telemetry events
# ===========================================================================
def create_kafka_source(t_env: StreamTableEnvironment):
    """
    Define a Flink SQL table backed by the Kafka topic.

    The JSON payload produced by the IoT simulators has the schema:
      event_id, device_id, device_type, location, timestamp,
      temperature, vibration, pressure, humidity, power_usage, rpm, error_code
    """
    t_env.execute_sql(f"""
        CREATE TABLE kafka_telemetry (
            event_id        STRING,
            device_id       STRING,
            device_type     STRING,
            location        STRING,
            `timestamp`     STRING,
            temperature     DOUBLE,
            vibration       DOUBLE,
            pressure        DOUBLE,
            humidity        DOUBLE,
            power_usage     DOUBLE,
            rpm             DOUBLE,
            error_code      STRING,
            -- Derive an event-time attribute from the JSON timestamp field.
            -- This enables event-time windows even when events arrive late.
            event_time AS TO_TIMESTAMP(`timestamp`),
            WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
        ) WITH (
            'connector'                  = 'kafka',
            'topic'                      = '{KAFKA_TOPIC}',
            'properties.bootstrap.servers' = '{KAFKA_BROKER}',
            'properties.group.id'        = 'flink-telemetry-consumer',
            'scan.startup.mode'          = 'earliest-offset',
            'format'                     = 'json',
            'json.fail-on-missing-field' = 'false',
            'json.ignore-parse-errors'   = 'true'
        )
    """)
    logger.info("Kafka source table 'kafka_telemetry' created on topic %s", KAFKA_TOPIC)


# ===========================================================================
#  2. Filesystem Sink — raw events as partitioned JSON files
# ===========================================================================
def create_raw_sink(t_env: StreamTableEnvironment):
    """
    Write every raw telemetry event as a JSON file to MinIO, partitioned
    by date (dt=YYYY-MM-DD).  This serves as the curated raw zone in the
    Kappa pipeline — equivalent to the batch ingest in Lambda.
    """
    t_env.execute_sql(f"""
        CREATE TABLE raw_sink (
            event_id        STRING,
            device_id       STRING,
            device_type     STRING,
            location        STRING,
            `timestamp`     STRING,
            temperature     DOUBLE,
            vibration       DOUBLE,
            pressure        DOUBLE,
            humidity        DOUBLE,
            power_usage     DOUBLE,
            rpm             DOUBLE,
            error_code      STRING,
            dt              STRING
        ) PARTITIONED BY (dt) WITH (
            'connector'                = 'filesystem',
            'path'                     = '{RAW_OUTPUT_PATH}',
            'format'                   = 'json',
            'sink.partition-commit.trigger'        = 'process-time',
            'sink.partition-commit.delay'           = '1 min',
            'sink.partition-commit.policy.kind'     = 'success-file',
            'sink.rolling-policy.file-size'         = '128MB',
            'sink.rolling-policy.rollover-interval' = '5 min',
            'sink.rolling-policy.check-interval'    = '1 min'
        )
    """)
    logger.info("Raw filesystem sink created at %s", RAW_OUTPUT_PATH)


# ===========================================================================
#  3. Filesystem Sink — 1-minute windowed aggregates
# ===========================================================================
def create_aggregates_sink(t_env: StreamTableEnvironment):
    """
    Destination for tumbling-window aggregations.
    Schema: window boundaries, device_id, and computed metrics.
    """
    t_env.execute_sql(f"""
        CREATE TABLE aggregates_sink (
            window_start    TIMESTAMP(3),
            window_end      TIMESTAMP(3),
            device_id       STRING,
            event_count     BIGINT,
            avg_temperature DOUBLE,
            max_vibration   DOUBLE,
            avg_pressure    DOUBLE,
            avg_humidity    DOUBLE,
            avg_power_usage DOUBLE,
            avg_rpm         DOUBLE,
            dt              STRING
        ) PARTITIONED BY (dt) WITH (
            'connector'                = 'filesystem',
            'path'                     = '{AGGREGATES_OUTPUT_PATH}',
            'format'                   = 'json',
            'sink.partition-commit.trigger'        = 'process-time',
            'sink.partition-commit.delay'           = '1 min',
            'sink.partition-commit.policy.kind'     = 'success-file',
            'sink.rolling-policy.file-size'         = '128MB',
            'sink.rolling-policy.rollover-interval' = '5 min',
            'sink.rolling-policy.check-interval'    = '1 min'
        )
    """)
    logger.info("Aggregates filesystem sink created at %s", AGGREGATES_OUTPUT_PATH)


# ===========================================================================
#  4. Pipeline wiring — INSERT INTO statements
# ===========================================================================
def start_raw_pipeline(t_env: StreamTableEnvironment):
    """
    Continuously stream parsed Kafka events into the raw JSON sink,
    adding a partition column `dt` derived from the event timestamp.
    """
    stmt_set = t_env.create_statement_set()
    stmt_set.add_insert_sql("""
        INSERT INTO raw_sink
        SELECT
            event_id,
            device_id,
            device_type,
            location,
            `timestamp`,
            temperature,
            vibration,
            pressure,
            humidity,
            power_usage,
            rpm,
            error_code,
            DATE_FORMAT(event_time, 'yyyy-MM-dd') AS dt
        FROM kafka_telemetry
    """)
    logger.info("Raw pipeline INSERT statement registered")
    return stmt_set


def add_aggregation_pipeline(t_env: StreamTableEnvironment, stmt_set):
    """
    Tumbling window (1 minute) aggregation per device_id.

    Computes:
      - avg(temperature)
      - max(vibration)      — spikes are more interesting than averages
      - avg(pressure)
      - avg(humidity)
      - avg(power_usage)
      - avg(rpm)

    In the Kappa architecture this replaces what would otherwise be a
    periodic Spark batch job computing the same statistics.  Because
    Flink processes events in event-time with watermarks, the results
    are deterministic and reproducible even when replaying historical
    data from Kafka.
    """
    stmt_set.add_insert_sql("""
        INSERT INTO aggregates_sink
        SELECT
            window_start,
            window_end,
            device_id,
            COUNT(*)             AS event_count,
            AVG(temperature)     AS avg_temperature,
            MAX(vibration)       AS max_vibration,
            AVG(pressure)        AS avg_pressure,
            AVG(humidity)        AS avg_humidity,
            AVG(power_usage)     AS avg_power_usage,
            AVG(rpm)             AS avg_rpm,
            DATE_FORMAT(window_start, 'yyyy-MM-dd') AS dt
        FROM TABLE(
            TUMBLE(TABLE kafka_telemetry, DESCRIPTOR(event_time), INTERVAL '1' MINUTE)
        )
        GROUP BY
            window_start,
            window_end,
            device_id
    """)
    logger.info("Aggregation pipeline (1-min tumbling window) INSERT statement registered")
    return stmt_set


# ===========================================================================
#  Main
# ===========================================================================
def main():
    logger.info("=== FactoryPulse Flink Telemetry Stream (Kappa Architecture) ===")
    logger.info("Kafka broker : %s", KAFKA_BROKER)
    logger.info("Kafka topic  : %s", KAFKA_TOPIC)
    logger.info("MinIO endpoint: %s", MINIO_ENDPOINT)
    logger.info("Raw output   : %s", RAW_OUTPUT_PATH)
    logger.info("Agg output   : %s", AGGREGATES_OUTPUT_PATH)

    # -- Build environment ----------------------------------------------------
    _env, t_env = configure_environment()

    # -- Register tables ------------------------------------------------------
    create_kafka_source(t_env)
    create_raw_sink(t_env)
    create_aggregates_sink(t_env)

    # -- Wire pipelines -------------------------------------------------------
    # StatementSet lets Flink optimise multiple INSERT statements into a
    # single execution graph, reading from Kafka only once.
    stmt_set = start_raw_pipeline(t_env)
    stmt_set = add_aggregation_pipeline(t_env, stmt_set)

    # -- Execute (blocks until the job is cancelled) --------------------------
    logger.info("Submitting Flink job graph ...")
    stmt_set.execute()
    logger.info("Job finished.")


if __name__ == "__main__":
    main()
