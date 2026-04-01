# Start all services in CPU-only dev mode (Windows PowerShell)
param(
    [switch]$Build,
    [switch]$Detach
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Local-AIOps-Copilot in DEV mode (CPU-only)..." -ForegroundColor Cyan

$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
Push-Location $projectRoot

try {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example" -ForegroundColor Yellow
    }

    $args = @("-f", "docker-compose.dev.yml", "up")
    if ($Build) { $args += "--build" }
    if ($Detach) { $args += "-d" }

    docker compose @args
} finally {
    Pop-Location
}
