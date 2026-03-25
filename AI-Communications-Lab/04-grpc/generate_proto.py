"""Generate Python gRPC stubs from .proto files."""

import subprocess
import sys
from pathlib import Path

PROTO_DIR = Path(__file__).parent / "protos"
OUT_DIR = Path(__file__).parent / "generated"
OUT_DIR.mkdir(exist_ok=True)

# Create __init__.py so the generated dir is importable
(OUT_DIR / "__init__.py").touch()

subprocess.run(
    [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        f"--pyi_out={OUT_DIR}",
        str(PROTO_DIR / "ai_services.proto"),
    ],
    check=True,
)
print(f"[codegen] Stubs written to {OUT_DIR}")
