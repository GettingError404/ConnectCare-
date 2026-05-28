```bat
@echo off
TITLE AI Voice Agent Project Starter

echo ==========================================
echo Starting Full AI Voice Agent Project
echo ==========================================

:: -----------------------------
:: START BACKEND
:: -----------------------------
echo.
echo [1/3] Starting Backend...
start cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: -----------------------------
:: START AGENT
:: -----------------------------
echo.
echo [2/3] Starting AI Agent...
start cmd /k "cd agent && venv\Scripts\activate && python main.py"

:: -----------------------------
:: START FRONTEND
:: -----------------------------
echo.
echo [3/3] Starting Frontend...
start cmd /k "cd frontend && npm run dev"

 echo.
 echo ==========================================
 echo All Services Started Successfully
 echo ==========================================

pause
```