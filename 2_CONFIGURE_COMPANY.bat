@echo off
title Aura ERP - Company details
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
echo Company details are printed on every quotation, proforma, receipt and purchase order.
echo.
venv\Scripts\python.exe manage.py configure company
echo.
if "%~1"=="" pause
