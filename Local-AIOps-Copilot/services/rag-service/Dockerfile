FROM python:3.11-slim

WORKDIR /app

COPY services/rag-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/rag-service/app/ /app/app/

ENV PYTHONPATH=/app
EXPOSE 50052

CMD ["python", "-m", "app.main"]
