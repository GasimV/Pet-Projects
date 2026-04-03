# FactoryPulse — Flink Processing Layer (Kappa Architecture)
# ===========================================================
# Replaces Spark Structured Streaming as the speed layer.
# In a Kappa architecture every data path goes through the stream
# processor — there is no separate batch layer. Flink handles both
# real-time enrichment/aggregation AND late-arriving / reprocessed
# data in a single unified pipeline.
#
# Base: official Flink 1.18 on Java 11
# Extras: Python 3 + PyFlink, Kafka connector, Iceberg connector,
#         S3 (hadoop-aws) JARs for MinIO access.

FROM flink:1.18-java11

# -----------------------------------------------------------
#  Install Python 3 and pip (required for PyFlink)
# -----------------------------------------------------------
USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        build-essential \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------
#  Install PyFlink and Python dependencies
# -----------------------------------------------------------
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# -----------------------------------------------------------
#  Download connector JARs into /opt/flink/lib/
#  These are automatically loaded by every Flink job.
#
#  1. flink-sql-connector-kafka  — Kafka source/sink via Table API
#  2. flink-sql-connector-filesystem — filesystem/S3 sink
#  3. iceberg-flink-runtime      — Iceberg table format support
#  4. hadoop-aws + aws-java-sdk  — S3A filesystem for MinIO
#  5. flink-s3-fs-hadoop         — Flink S3 filesystem plugin
# -----------------------------------------------------------
ENV FLINK_VERSION=1.18.1
ENV ICEBERG_VERSION=1.5.2
ENV HADOOP_AWS_VERSION=3.3.4
ENV AWS_SDK_VERSION=1.12.367

RUN cd /opt/flink/lib && \
    # Kafka SQL connector (fat jar — includes kafka-clients)
    curl -fSL "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${FLINK_VERSION}/flink-sql-connector-kafka-${FLINK_VERSION}.jar" \
         -o flink-sql-connector-kafka-${FLINK_VERSION}.jar && \
    # Iceberg Flink runtime (fat jar)
    curl -fSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-1.18/${ICEBERG_VERSION}/iceberg-flink-runtime-1.18-${ICEBERG_VERSION}.jar" \
         -o iceberg-flink-runtime-1.18-${ICEBERG_VERSION}.jar && \
    # Hadoop AWS — S3A filesystem implementation
    curl -fSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
         -o hadoop-aws-${HADOOP_AWS_VERSION}.jar && \
    # AWS SDK bundle (required by hadoop-aws)
    curl -fSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" \
         -o aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar

# -----------------------------------------------------------
#  Install the Flink S3 plugin so checkpoints/savepoints can
#  be written to MinIO as well.
# -----------------------------------------------------------
RUN mkdir -p /opt/flink/plugins/s3-fs-hadoop && \
    cp /opt/flink/opt/flink-s3-fs-hadoop-*.jar /opt/flink/plugins/s3-fs-hadoop/ 2>/dev/null || \
    curl -fSL "https://repo1.maven.org/maven2/org/apache/flink/flink-s3-fs-hadoop/${FLINK_VERSION}/flink-s3-fs-hadoop-${FLINK_VERSION}.jar" \
         -o /opt/flink/plugins/s3-fs-hadoop/flink-s3-fs-hadoop-${FLINK_VERSION}.jar

# -----------------------------------------------------------
#  Tell Flink where Python is
# -----------------------------------------------------------
ENV PYFLINK_PYTHON=/usr/bin/python3

# -----------------------------------------------------------
#  Copy application code
# -----------------------------------------------------------
COPY . /opt/flink-apps

WORKDIR /opt/flink

# The base image already ships a docker-entrypoint.sh that reads
# FLINK_PROPERTIES and starts the appropriate daemon (jobmanager
# or taskmanager) based on the CMD passed at runtime.
