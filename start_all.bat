@echo off
title Diaa Store Launcher

echo [1/3] Killing all old Python processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM python3.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Starting Backend (port 8000)...
start "BACKEND" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul

echo [3/3] Starting Bot...
start "BOT" cmd /k "cd /d %~dp0bot && python main.py"

echo.
echo ==============================
echo  All services started cleanly
echo  Backend : http://localhost:8000
echo  Admin   : http://localhost:5173
echo ==============================
pause
