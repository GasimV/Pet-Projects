#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp)"

cpu_cores="$(nproc)"
memory_gib="$(awk '/MemTotal/ { printf "%.1f", $2 / 1024 / 1024 }' /proc/meminfo)"
wsl_present=false
docker_wsl2=false
gpu_visible_in_wsl=false

if grep -qi microsoft /proc/version 2>/dev/null; then
  wsl_present=true
fi

if docker version --format '{{json .Server}}' 2>/dev/null | grep -qi WSL2; then
  docker_wsl2=true
fi

gpus="[]"
if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_visible_in_wsl=true
  gpus="$(python - <<'PY'
import csv
import json
import subprocess

result = subprocess.check_output(
    ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap", "--format=csv,noheader,nounits"],
    text=True,
)
rows = []
for row in csv.reader(result.splitlines()):
    rows.append(
        {
            "name": row[0].strip(),
            "memory_mib": int(row[1].strip()),
            "driver_version": row[2].strip(),
            "compute_cap": row[3].strip(),
        }
    )
print(json.dumps(rows))
PY
)"
fi

cat >"$TMP" <<JSON
{
  "cpu_cores": $cpu_cores,
  "logical_processors": $cpu_cores,
  "memory_gib": $memory_gib,
  "wsl_present": $wsl_present,
  "docker_desktop_wsl2": $docker_wsl2,
  "gpu_visible_in_wsl": $gpu_visible_in_wsl,
  "gpus": $gpus
}
JSON

python - <<'PY' "$TMP" "$ROOT"
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[2])
sys.path.insert(0, str(root / "libs" / "shared-config"))

from shared_config.runtime_profile import env_file_text, parse_snapshot, report_markdown, select_runtime_plan

snapshot = parse_snapshot(json.loads(pathlib.Path(sys.argv[1]).read_text()))
plan = select_runtime_plan(snapshot)
(root / ".env.generated").write_text(env_file_text(plan, snapshot), encoding="utf-8")
(root / "docs" / "hardware-report.md").write_text(report_markdown(plan, snapshot), encoding="utf-8")
print(report_markdown(plan, snapshot))
PY

rm -f "$TMP"

