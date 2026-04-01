FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

COPY services/release-controller/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/release-controller/app/ /app/app/

ENV PYTHONPATH=/app
EXPOSE 50055

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "50055"]
