@echo off
set "HERE=%~dp0"
echo Starting Aura ERP. Two black windows will open - keep both open while you work.
start "Aura ERP - Backend" "%HERE%START_BACKEND.bat"
start "Aura ERP - Frontend" "%HERE%START_FRONTEND.bat"
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
