FROM python:3.11-slim

WORKDIR /app

COPY services/frontend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/frontend/app/ /app/app/

ENV PYTHONPATH=/app
EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
