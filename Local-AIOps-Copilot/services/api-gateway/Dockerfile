FROM python:3.11-slim

WORKDIR /app

COPY services/api-gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/api-gateway/app/ /app/app/

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
