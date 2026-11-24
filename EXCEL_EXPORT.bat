@echo off
title Aura ERP - Export to Excel
set "HERE=%~dp0"
cd /d "%HERE%backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
venv\Scripts\python.exe manage.py export_excel --out "%HERE%exports"
if errorlevel 1 ( pause & exit /b 1 )
start "" explorer "%HERE%exports"
echo.
pause
