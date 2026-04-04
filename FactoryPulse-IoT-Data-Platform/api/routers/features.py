"""Features router — online feature retrieval from Feast + Redis."""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from models import FeatureResponse

router = APIRouter(prefix="/api/v1/features", tags=["features"])

# Lazy-loaded Feast store
_store = None


def _get_feast_store():
    """Lazy-load the Feast FeatureStore."""
    global _store
    if _store is None:
        from feast import FeatureStore

        repo_path = os.environ.get("FEAST_REPO_PATH", "/app/feast")
        _store = FeatureStore(repo_path=repo_path)
    return _store


@router.get("/{device_id}", response_model=FeatureResponse)
async def get_device_features(device_id: str):
    """Get online features from Feast for a specific device.

    Returns the latest materialised features from Redis, including
    device_hourly_stats and device_health_features.
    """
    try:
        store = _get_feast_store()

        feature_refs = [
            "device_hourly_stats:avg_temperature",
            "device_hourly_stats:max_temperature",
            "device_hourly_stats:avg_vibration",
            "device_hourly_stats:max_vibration",
            "device_hourly_stats:avg_pressure",
            "device_hourly_stats:avg_power_usage",
            "device_hourly_stats:reading_count",
            "device_health_features:health_score",
            "device_health_features:days_since_maintenance",
            "device_health_features:alert_count_24h",
            "device_health_features:anomaly_score",
        ]

        entity_rows = [{"device_id": device_id}]
        features = store.get_online_features(
            features=feature_refs,
            entity_rows=entity_rows,
        ).to_dict()

        # Flatten the result — Feast returns lists
        flat = {}
        feature_names = []
        for key, values in features.items():
            if key == "device_id":
                continue
            flat[key] = values[0] if values else None
            feature_names.append(key)

        return FeatureResponse(
            device_id=device_id,
            features=flat,
            feature_names=feature_names,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Feature retrieval failed: {exc}",
        )
