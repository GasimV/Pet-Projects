from __future__ import annotations

import pathlib
import sys


def repo_root(current_file: str) -> pathlib.Path:
    return pathlib.Path(current_file).resolve().parents[3]


def configure_imports(current_file: str) -> pathlib.Path:
    root = repo_root(current_file)
    extra_paths = [
        root / "libs" / "shared-config",
        root / "libs" / "shared-events",
        root / "libs" / "shared-observability",
        root / "libs" / "proto" / "generated",
    ]
    for path in extra_paths:
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
    return root

