from __future__ import annotations

import pathlib
import sys

from grpc_tools import protoc


ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "libs" / "proto"
OUT_DIR = PROTO_DIR / "generated"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    protos = sorted((PROTO_DIR / "voice_platform").glob("*.proto"))
    if not protos:
        print("No proto files found", file=sys.stderr)
        return 1

    args = [
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--pyi_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        *[str(proto) for proto in protos],
    ]
    return protoc.main(args)


if __name__ == "__main__":
    raise SystemExit(main())

