# FactoryPulse — Spark Processing Layer
# ======================================
# Runs as Spark master. Contains both streaming (speed layer) and batch jobs.

FROM apache/spark:3.5.1

USER root

# -----------------------------------------------------------
#  Install additional Python dependencies
# -----------------------------------------------------------
RUN pip3 install --upgrade pip
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# -----------------------------------------------------------
#  Copy application code
# -----------------------------------------------------------
COPY . /opt/spark-apps

# -----------------------------------------------------------
#  Expose Spark master ports
# -----------------------------------------------------------
EXPOSE 8080 7077 4040

# -----------------------------------------------------------
#  Start Spark master
# -----------------------------------------------------------
ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH
ENV SPARK_MASTER_HOST=0.0.0.0
ENV SPARK_MASTER_PORT=7077
ENV SPARK_MASTER_WEBUI_PORT=8080
ENV SPARK_NO_DAEMONIZE=true

CMD ["/opt/spark/sbin/start-master.sh"]
