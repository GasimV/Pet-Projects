$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Safe-Command {
  param([scriptblock]$Action)
  try { & $Action } catch { $null }
}

$video = Safe-Command { Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion }
$cpu = Safe-Command { Get-CimInstance Win32_Processor | Select-Object -First 1 NumberOfCores, NumberOfLogicalProcessors }
$mem = Safe-Command { Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory }
$wsl = Safe-Command { wsl -l -v | Out-String }
$docker = Safe-Command { docker version --format '{{json .}}' }
$nvidiaCsv = Safe-Command { nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader,nounits }
$wslNvidia = Safe-Command { wsl -e sh -lc "nvidia-smi >/dev/null 2>&1 && echo yes || echo no" }

$gpus = @()
if ($nvidiaCsv) {
  foreach ($line in ($nvidiaCsv -split "`n")) {
    if (-not [string]::IsNullOrWhiteSpace($line)) {
      $parts = $line.Split(",").ForEach({ $_.Trim() })
      $gpus += @{
        name = $parts[0]
        memory_mib = [int]$parts[1]
        driver_version = $parts[2]
        compute_cap = $parts[3]
      }
    }
  }
} elseif ($video) {
  foreach ($gpu in $video) {
    $gpus += @{
      name = $gpu.Name
      memory_mib = [int]([math]::Round($gpu.AdapterRAM / 1MB))
      driver_version = $gpu.DriverVersion
      compute_cap = $null
    }
  }
}

$payload = @{
  cpu_cores = [int]($cpu.NumberOfCores)
  logical_processors = [int]($cpu.NumberOfLogicalProcessors)
  memory_gib = [math]::Round(([double]$mem.TotalPhysicalMemory / 1GB), 1)
  wsl_present = [bool]($wsl -or ($wslNvidia -match "yes"))
  docker_desktop_wsl2 = [bool]($docker -match "microsoft-standard-WSL2")
  gpu_visible_in_wsl = [bool]($wslNvidia -match "yes")
  gpus = $gpus
}

$jsonPath = Join-Path $env:TEMP "voice_platform_hardware.json"
$pyPath = Join-Path $env:TEMP "voice_platform_render_hw.py"
$payload | ConvertTo-Json -Depth 4 | Set-Content -Path $jsonPath -Encoding UTF8

@"
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[2])
sys.path.insert(0, str(root / "libs" / "shared-config"))

from shared_config.runtime_profile import env_file_text, parse_snapshot, report_markdown, select_runtime_plan

snapshot = parse_snapshot(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8-sig")))
plan = select_runtime_plan(snapshot)
(root / ".env.generated").write_text(env_file_text(plan, snapshot), encoding="utf-8")
(root / "docs" / "hardware-report.md").write_text(report_markdown(plan, snapshot), encoding="utf-8")
print(report_markdown(plan, snapshot))
"@ | Set-Content -Path $pyPath -Encoding UTF8

python $pyPath $jsonPath $root

Remove-Item $jsonPath, $pyPath -Force
