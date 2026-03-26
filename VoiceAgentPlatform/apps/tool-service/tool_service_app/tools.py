from __future__ import annotations

import pathlib
import sys
import platform
from pathlib import Path
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[3]
shared_config_path = str(ROOT / "libs" / "shared-config")
if shared_config_path not in sys.path:
    sys.path.insert(0, shared_config_path)

from shared_config.settings import get_settings


def get_system_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "project": settings.project_name,
        "environment": settings.environment,
        "runtime_profile": settings.runtime_profile,
        "platform": platform.platform(),
        "gpu_enabled": settings.runtime_profile != "local-cpu",
        "providers": {
            "llm": "ollama" if settings.enable_ollama else "vllm",
            "tts": settings.tts_provider,
        },
    }


def get_domain_mode(domain: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    return {"domain": domain or settings.default_domain_pack}


def search_manuals(query: str, domain: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    root = Path(settings.knowledge_dir)
    search_root = root / domain if domain else root
    matches: list[dict[str, str]] = []
    for path in search_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if query.lower() in text.lower():
            excerpt = next((line for line in text.splitlines() if query.lower() in line.lower()), "")[:240]
            matches.append({"source": str(path.relative_to(root)), "excerpt": excerpt})
    return {"query": query, "matches": matches[:5]}


def list_capabilities() -> dict[str, Any]:
    return {
        "capabilities": [
            "get_system_status",
            "get_domain_mode",
            "search_manuals",
            "list_capabilities",
        ]
    }


TOOL_REGISTRY = {
    "get_system_status": lambda **_: get_system_status(),
    "get_domain_mode": lambda domain=None, **_: get_domain_mode(domain=domain),
    "search_manuals": lambda query="", domain=None, **_: search_manuals(query=query, domain=domain),
    "list_capabilities": lambda **_: list_capabilities(),
}
