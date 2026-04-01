# Start all services in GPU mode (Windows PowerShell — for second machine)
param(
    [string]$Profile = "vllm",
    [switch]$Build,
    [switch]$Detach
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Local-AIOps-Copilot in GPU mode..." -ForegroundColor Cyan
Write-Host "Profile: $Profile" -ForegroundColor Yellow

$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
Push-Location $projectRoot

try {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        (Get-Content ".env") -replace 'LLM_BACKEND=mock', 'LLM_BACKEND=vllm' `
                             -replace 'ENVIRONMENT=dev', 'ENVIRONMENT=gpu' |
            Set-Content ".env"
        Write-Host "Created .env configured for GPU mode" -ForegroundColor Yellow
    }

    $args = @("-f", "docker-compose.gpu.yml", "--profile", $Profile, "up")
    if ($Build) { $args += "--build" }
    if ($Detach) { $args += "-d" }

    docker compose @args
} finally {
    Pop-Location
}
