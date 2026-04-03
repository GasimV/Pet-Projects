# FactoryPulse — Spark Processing Layer
# ======================================
# Runs as Spark master (default) or worker depending on SPARK_MODE.
# Contains both streaming (speed layer) and batch jobs.

FROM bitnami/spark:3.5.1

USER root

# -----------------------------------------------------------
#  Install additional Python dependencies
# -----------------------------------------------------------
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# -----------------------------------------------------------
#  Copy application code
# -----------------------------------------------------------
COPY . /opt/spark-apps

# -----------------------------------------------------------
#  Spark mode (master | worker) — overridable at runtime
# -----------------------------------------------------------
ENV SPARK_MODE=${SPARK_MODE:-master}

# -----------------------------------------------------------
#  Default entrypoint: start the Spark master
# -----------------------------------------------------------
# The bitnami image already has an entrypoint script that reads
# SPARK_MODE and launches the correct daemon. We simply ensure
# the default mode is "master".
ENTRYPOINT ["/opt/bitnami/scripts/spark/entrypoint.sh"]
CMD ["/opt/bitnami/scripts/spark/run.sh"]
