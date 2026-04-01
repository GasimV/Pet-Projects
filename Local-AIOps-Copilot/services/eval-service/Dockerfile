FROM python:3.11-slim

WORKDIR /app

COPY services/eval-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/eval-service/app/ /app/app/

ENV PYTHONPATH=/app
EXPOSE 50054

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "50054"]
