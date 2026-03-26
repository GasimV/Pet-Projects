from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
for rel in (
    ROOT / "libs" / "shared-config",
    ROOT / "libs" / "shared-events",
    ROOT / "libs" / "shared-observability",
    ROOT / "libs" / "proto" / "generated",
    ROOT / "apps" / "session-orchestrator",
    ROOT / "apps" / "rag-service",
):
    rel_str = str(rel)
    if rel_str not in sys.path:
        sys.path.insert(0, rel_str)

