"""Database models and Pydantic schemas for the release controller."""

from __future__ import annotations

import datetime
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ReleaseStatus(str, Enum):
    REGISTERED = "registered"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    ACTIVE_BLUE = "active_blue"
    ACTIVE_GREEN = "active_green"
    ROLLED_BACK = "rolled_back"
    ARCHIVED = "archived"


class ReleaseDecision(str, Enum):
    STAY_ON_BLUE = "stay_on_blue"
    SWITCH_TO_GREEN = "switch_to_green"
    ROLLBACK_TO_BLUE = "rollback_to_blue"
    HOLD_FOR_REVIEW = "hold_for_review"


# ── SQLAlchemy ORM models ──


class ReleaseRecord(Base):
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    release_id = Column(String(64), unique=True, nullable=False, index=True)
    model_name = Column(String(256), nullable=False)
    version = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default=ReleaseStatus.REGISTERED.value)
    slot = Column(String(8), nullable=True)  # "blue" or "green"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    eval_metrics = Column(JSON, nullable=True)
    decision = Column(String(32), nullable=True)
    decision_rationale = Column(Text, nullable=True)
    mlflow_run_id = Column(String(64), nullable=True)


# ── Pydantic schemas ──


class RegisterReleaseRequest(BaseModel):
    model_name: str
    version: str
    slot: str = Field("green", pattern="^(blue|green)$")


class RegisterReleaseResponse(BaseModel):
    release_id: str
    status: str


class ReleaseInfo(BaseModel):
    release_id: str
    model_name: str
    version: str
    status: str
    slot: str | None
    created_at: str
    eval_metrics: dict | None = None
    decision: str | None = None
    decision_rationale: str | None = None


class DecisionRequest(BaseModel):
    blue_release_id: str
    green_release_id: str
    auto_apply: bool = False  # default: recommendation only


class DecisionResponse(BaseModel):
    decision: str
    rationale: str
    blue_release_id: str
    green_release_id: str
    metrics_summary: dict = Field(default_factory=dict)
    applied: bool = False
