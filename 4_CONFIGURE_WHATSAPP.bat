@echo off
title Aura ERP - WhatsApp settings
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
venv\Scripts\python.exe manage.py configure whatsapp
echo.
if "%~1"=="" pause
