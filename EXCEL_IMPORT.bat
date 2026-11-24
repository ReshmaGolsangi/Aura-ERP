@echo off
title Aura ERP - Import from Excel
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
echo What do you want to import?
echo   1 = Customers
echo   2 = Products
echo   3 = Distributors
echo   4 = Distributor Products   (import Distributors and Products first)
choice /c 1234 /m "Choose"
set "KIND=customers"
if errorlevel 4 (set "KIND=distributor_products") else if errorlevel 3 (set "KIND=distributors") else if errorlevel 2 (set "KIND=products")
echo.
set "FILE=%~1"
if not defined FILE set /p FILE=Drag your Excel file into this window, then press Enter: 
set "FILE=%FILE:"=%"
echo.
echo Existing records are UPDATED, new ones are ADDED. Nothing is deleted.
venv\Scripts\python.exe manage.py import_excel %KIND% "%FILE%"
echo.
pause
