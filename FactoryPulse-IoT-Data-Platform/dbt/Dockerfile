FROM python:3.11-slim

RUN pip install --no-cache-dir dbt-core dbt-clickhouse

WORKDIR /usr/app/dbt

ENTRYPOINT ["dbt"]
CMD ["run"]
