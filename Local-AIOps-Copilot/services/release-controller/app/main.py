"""Release Controller — manages blue-green release lifecycle."""

from __future__ import annotations

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import httpx
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from shared.config import get_settings
from shared.logging import setup_logging, get_logger
from shared.metrics import setup_metrics
from app.models import (
    Base,
    DecisionRequest,
    DecisionResponse,
    RegisterReleaseRequest,
    RegisterReleaseResponse,
    ReleaseInfo,
    ReleaseRecord,
    ReleaseStatus,
)
from app.decision_engine import make_decision

settings = get_settings()
setup_logging(settings.log_level, settings.log_format, "release-controller")
logger = get_logger(__name__)
metrics = setup_metrics("release-controller")

# Database setup
try:
    engine = create_engine(settings.postgres_url)
    SessionLocal = sessionmaker(bind=engine)
except Exception as e:
    logger.warning("postgres_unavailable", error=str(e), msg="Using SQLite fallback")
    engine = create_engine("sqlite:///release_controller.db")
    SessionLocal = sessionmaker(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("release_controller_started")
    yield
    logger.info("release_controller_stopped")


app = FastAPI(title="Release Controller", version="0.1.0", lifespan=lifespan)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/v1/releases", response_model=RegisterReleaseResponse)
async def register_release(request: RegisterReleaseRequest):
    """Register a new release candidate."""
    release_id = f"rel-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        record = ReleaseRecord(
            release_id=release_id,
            model_name=request.model_name,
            version=request.version,
            status=ReleaseStatus.REGISTERED.value,
            slot=request.slot,
        )
        db.add(record)
        db.commit()

    logger.info("release_registered", release_id=release_id, model=request.model_name)
    return RegisterReleaseResponse(release_id=release_id, status=ReleaseStatus.REGISTERED.value)


@app.get("/api/v1/releases", response_model=list[ReleaseInfo])
async def list_releases():
    """List all releases."""
    with SessionLocal() as db:
        records = db.query(ReleaseRecord).order_by(ReleaseRecord.created_at.desc()).all()
        return [
            ReleaseInfo(
                release_id=r.release_id,
                model_name=r.model_name,
                version=r.version,
                status=r.status,
                slot=r.slot,
                created_at=r.created_at.isoformat() if r.created_at else "",
                eval_metrics=r.eval_metrics,
                decision=r.decision,
                decision_rationale=r.decision_rationale,
            )
            for r in records
        ]


@app.get("/api/v1/releases/{release_id}", response_model=ReleaseInfo)
async def get_release(release_id: str):
    """Get a specific release."""
    with SessionLocal() as db:
        r = db.query(ReleaseRecord).filter(ReleaseRecord.release_id == release_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Release not found")
        return ReleaseInfo(
            release_id=r.release_id,
            model_name=r.model_name,
            version=r.version,
            status=r.status,
            slot=r.slot,
            created_at=r.created_at.isoformat() if r.created_at else "",
            eval_metrics=r.eval_metrics,
            decision=r.decision,
            decision_rationale=r.decision_rationale,
        )


@app.post("/api/v1/releases/decide", response_model=DecisionResponse)
async def decide_release(request: DecisionRequest):
    """Run the blue-green decision engine."""
    with SessionLocal() as db:
        blue = db.query(ReleaseRecord).filter(ReleaseRecord.release_id == request.blue_release_id).first()
        green = db.query(ReleaseRecord).filter(ReleaseRecord.release_id == request.green_release_id).first()

        if not blue or not green:
            raise HTTPException(status_code=404, detail="Release(s) not found")

        blue_metrics = blue.eval_metrics or {
            "error_rate": 0.03, "quality_score": 0.80, "latency_p99_ms": 400.0
        }
        green_metrics = green.eval_metrics or {
            "error_rate": 0.02, "quality_score": 0.85, "latency_p99_ms": 350.0
        }

        decision, rationale = make_decision(blue_metrics, green_metrics)

        # Update records
        blue.decision = decision
        blue.decision_rationale = rationale
        green.decision = decision
        green.decision_rationale = rationale

        applied = False
        if request.auto_apply and decision == "switch_to_green":
            blue.status = ReleaseStatus.ARCHIVED.value
            green.status = ReleaseStatus.ACTIVE_GREEN.value
            applied = True
            logger.info("release_switched", decision=decision, green=request.green_release_id)
        elif request.auto_apply and decision == "rollback_to_blue":
            green.status = ReleaseStatus.ROLLED_BACK.value
            blue.status = ReleaseStatus.ACTIVE_BLUE.value
            applied = True
            logger.info("release_rolled_back", decision=decision, blue=request.blue_release_id)

        db.commit()

    metrics.request_count.labels("POST", "/api/v1/releases/decide", "200").inc()
    return DecisionResponse(
        decision=decision,
        rationale=rationale,
        blue_release_id=request.blue_release_id,
        green_release_id=request.green_release_id,
        metrics_summary={"blue": blue_metrics, "green": green_metrics},
        applied=applied,
    )


@app.get("/health")
async def health():
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(select(ReleaseRecord).limit(1))
            db_ok = True
    except Exception:
        pass
    return {"status": "healthy" if db_ok else "degraded", "database": db_ok}
