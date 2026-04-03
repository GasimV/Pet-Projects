# FactoryPulse — Airflow Orchestration Layer
# ============================================
# Extends the official Apache Airflow image with providers and
# libraries needed by the FactoryPulse DAGs.

FROM apache/airflow:2.8.3-python3.11

USER airflow

# -----------------------------------------------------------
#  Install extra Python dependencies
# -----------------------------------------------------------
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# -----------------------------------------------------------
#  Copy DAGs and plugins into the image (also mounted at runtime)
# -----------------------------------------------------------
COPY dags/ /opt/airflow/dags/
COPY plugins/ /opt/airflow/plugins/
