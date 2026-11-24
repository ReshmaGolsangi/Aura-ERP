@echo off
title Aura ERP - Excel import template
set "HERE=%~dp0"
cd /d "%HERE%backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
venv\Scripts\python.exe manage.py excel_template
start "" explorer "%HERE%exports"
echo.
echo Fill the sheets (Customers, Products, Distributors, Distributor Products), then run EXCEL_IMPORT.bat
pause
