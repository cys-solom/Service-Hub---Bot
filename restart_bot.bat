@echo off
title Restart Bot Only
color 0E

echo Restarting Bot only (keeping Backend alive)...

:: Find and kill bot process specifically
for /f "tokens=5" %%a in ('netstat -aon 2^>nul') do (echo %%a) >nul

:: Kill python processes that are running main.py (bot) 
:: We identify it by looking for the bot window title
taskkill /FI "WINDOWTITLE eq DiaaStore-Bot" /F >nul 2>&1
timeout /t 1 /nobreak >nul

:: Start Bot again
start "DiaaStore-Bot" cmd /k "cd /d %~dp0bot && python main.py"
echo Bot restarted!
timeout /t 2 /nobreak >nul
