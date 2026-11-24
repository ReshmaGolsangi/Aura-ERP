@echo off
title Aura ERP - Test email
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
set /p TO=Send a test email to which address? 
venv\Scripts\python.exe manage.py send_test_email "%TO%"
echo.
pause
