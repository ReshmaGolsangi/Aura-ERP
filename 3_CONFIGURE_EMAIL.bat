@echo off
title Aura ERP - Email (SMTP) settings
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
venv\Scripts\python.exe manage.py configure email
echo.
echo Now run 5_TEST_EMAIL.bat to check that email works.
if "%~1"=="" pause
