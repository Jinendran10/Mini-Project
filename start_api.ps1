# Quick Start Script for JIE Detection API
# Run this to start all services locally

Write-Host "=== JIE Detection API Quick Start ===" -ForegroundColor Cyan

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Creating from example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env - Please edit and set API_KEY!" -ForegroundColor Green
    exit 1
}

# Check if venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "⚠️  Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host "`nActivating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Cyan
pip install -q -r requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Check Redis
Write-Host "`nChecking Redis..." -ForegroundColor Cyan
try {
    $null = Test-Connection -ComputerName localhost -Port 6379 -ErrorAction Stop
    Write-Host "✓ Redis is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Redis not running. Starting with Docker..." -ForegroundColor Yellow
    docker run -d -p 6379:6379 --name jie-redis redis:latest
    Start-Sleep -Seconds 3
    Write-Host "✓ Redis started" -ForegroundColor Green
}

# Check checkpoints
Write-Host "`nChecking model checkpoints..." -ForegroundColor Cyan
if (-not (Test-Path "checkpoints/gpt2-medium")) {
    Write-Host "⚠️  Checkpoints not found!" -ForegroundColor Red
    Write-Host "Please run jie_training.ipynb in Colab to generate checkpoints" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Checkpoints found" -ForegroundColor Green

# Start Celery worker in background
Write-Host "`nStarting Celery worker..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {.\.venv\Scripts\Activate.ps1; celery -A src.api.tasks worker --loglevel=info --pool=solo}" -WindowStyle Normal
Write-Host "✓ Celery worker started in new window" -ForegroundColor Green

# Wait a bit for worker to start
Start-Sleep -Seconds 3

# Start API server
Write-Host "`nStarting API server..." -ForegroundColor Cyan
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`nPress Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
