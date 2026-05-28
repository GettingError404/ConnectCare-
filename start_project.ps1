Write-Host "=========================================="
Write-Host "Starting Full AI Voice Agent Project"
Write-Host "=========================================="

# Root Path
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# -----------------------------
# START DATABASE
# -----------------------------
Write-Host "[1/4] Starting Database Containers..."
Start-Process powershell -ArgumentList "cd '$root'; docker compose up -d"

Start-Sleep -Seconds 5

# -----------------------------
# START BACKEND
# -----------------------------
Write-Host "[2/4] Starting Backend..."
Start-Process powershell -ArgumentList "cd '$root/backend'; .\venv\Scripts\Activate.ps1; uvicorn main:app --reload"

# -----------------------------
# START AGENT
# -----------------------------
Write-Host "[3/4] Starting AI Agent..."
Start-Process powershell -ArgumentList "cd '$root/agent'; .\venv\Scripts\Activate.ps1; python main.py"

# -----------------------------
# START FRONTEND
# -----------------------------
Write-Host "[4/4] Starting Frontend..."
Start-Process powershell -ArgumentList "cd '$root/frontend'; npm run dev"

Write-Host "=========================================="
Write-Host "All Services Started Successfully"
Write-Host "=========================================="