import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from redis import Redis
from redis.exceptions import RedisError


APP_NAME = os.getenv("APP_NAME", "k8s-lab-backend")
REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
COUNTER_KEY = os.getenv("COUNTER_KEY", "visits")
LOG_PATH = Path(os.getenv("APP_LOG_PATH", "/var/log/app/app.log"))
POD_NAME = os.getenv("POD_NAME", "unknown-pod")
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "unknown-namespace")


def configure_logging() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


logger = configure_logging()
app = FastAPI(title="k8s multinode lab backend", version="1.0.0")


def get_redis_client() -> Redis:
    return Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


@app.get("/health")
def health() -> dict:
    response = {
        "status": "ok",
        "app": APP_NAME,
        "pod": POD_NAME,
        "namespace": POD_NAMESPACE,
        "redis": "reachable",
    }

    try:
        get_redis_client().ping()
        return response
    except RedisError as exc:
        logger.warning("Health check failed because Redis is unavailable: %s", exc)
        response["status"] = "degraded"
        response["redis"] = "unreachable"
        raise HTTPException(status_code=503, detail=response) from exc


@app.get("/visits")
def visits() -> dict:
    try:
        client = get_redis_client()
        visits_count = client.incr(COUNTER_KEY)
    except RedisError as exc:
        logger.exception("Failed to increment the visit counter")
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Redis is unavailable",
                "redis_host": REDIS_HOST,
            },
        ) from exc

    logger.info("Visit recorded on %s. Counter is now %s.", POD_NAME, visits_count)
    return {
        "message": "Visit counter incremented successfully",
        "visits": visits_count,
        "served_by": POD_NAME,
        "redis_host": REDIS_HOST,
    }
