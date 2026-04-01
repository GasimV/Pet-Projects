FROM python:3.11-slim

WORKDIR /app

COPY services/agent-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/agent-service/app/ /app/app/

ENV PYTHONPATH=/app
EXPOSE 50051

CMD ["python", "-m", "app.server"]
