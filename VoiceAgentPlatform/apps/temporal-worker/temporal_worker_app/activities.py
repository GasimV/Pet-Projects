from __future__ import annotations

import json
from pathlib import Path

from temporalio import activity


ARTIFACT_ROOT = Path("docs/artifacts")


@activity.defn
async def archive_session_activity(payload: dict) -> str:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    target = ARTIFACT_ROOT / f"{payload['session_id']}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(target)


@activity.defn
async def summarize_session_activity(payload: dict) -> dict:
    transcript = payload.get("transcript", "")
    response = payload.get("assistant_response", "")
    return {
        "session_id": payload["session_id"],
        "summary": f"User said: {transcript[:120]}; assistant replied: {response[:120]}",
    }


@activity.defn
async def retry_tool_activity(payload: dict) -> dict:
    return {"status": "queued", "tool": payload["tool_name"], "arguments": payload.get("arguments_json", "{}")}

