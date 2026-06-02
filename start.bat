@echo off
echo ==========================================
echo       Starting Diaa Store Services
echo ==========================================

echo Starting Backend API...
start "Diaa Store Backend" cmd /k "cd backend && title Backend API && python -m uvicorn main:app --reload --port 8000"

echo Starting Telegram Bot...
start "Diaa Store Bot" cmd /k "cd bot && title Telegram Bot && python main.py"

echo Starting Admin Panel...
start "Diaa Store Admin" cmd /k "cd admin && title Admin Panel && npm run dev"

echo.
echo All services launched in separate windows!
echo Close this window at any time.
