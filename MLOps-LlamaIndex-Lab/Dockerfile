# =============================================================================
# MLOps-LlamaIndex-Lab — Application Dockerfile
# =============================================================================
# Multi-stage build: install dependencies first (cached), then copy app code.
# =============================================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by pypdf / python-docx
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# ── Dependencies stage ──────────────────────────────────────────────────────

COPY requirements-docker.txt .
RUN pip install -r requirements-docker.txt

# ── Application stage ───────────────────────────────────────────────────────

COPY app/ app/
COPY data/sample_docs/ data/sample_docs/

# Create the uploads directory inside the container
RUN mkdir -p data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
