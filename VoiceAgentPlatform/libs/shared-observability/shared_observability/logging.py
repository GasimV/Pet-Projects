from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(session_id)s %(turn_id)s")
    )
    root.handlers.clear()
    root.addHandler(handler)

