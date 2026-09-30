# Starts the NWIS backend (FastAPI, :8008) and frontend (Vite, :5173) in two windows.
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File .\start-nwis.ps1
# First run only:              add -Install to install Python and npm dependencies.
param([switch]$Install)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Install) {
    Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
    python -m pip install -r "$root\backend\requirements.txt"
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location "$root\frontend"; npm install; Pop-Location
}

# Demo data is generated deterministically; rebuild it if the source PDFs are missing.
if (-not (Test-Path "$root\backend\app\data\source_documents")) {
    Write-Host "Generating demo augmentation and source documents..." -ForegroundColor Cyan
    Push-Location "$root\backend\app\data\synthetic"
    python augment_demo.py
    python generate_source_documents.py
    Pop-Location
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python run.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "NWIS is starting:" -ForegroundColor Green
Write-Host "  App       http://localhost:5173"
Write-Host "  API docs  http://127.0.0.1:8008/docs"
