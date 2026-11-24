@echo off
setlocal
title Aura ERP - First time setup
set "HERE=%~dp0"
cd /d "%HERE%"
echo ================================================
echo   Aura ERP - First time setup
echo   Safe to run again after receiving a new version
echo ================================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :nopython
where npm >nul 2>nul
if errorlevel 1 goto :nonode

echo [1/6] Creating Python virtual environment...
if not exist "backend\venv\Scripts\python.exe" %PY% -m venv "backend\venv"
if errorlevel 1 goto :fail

echo [2/6] Installing Python packages. This can take a few minutes...
"backend\venv\Scripts\python.exe" -m pip install --upgrade pip
"backend\venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :fail

echo [3/6] Creating private settings file...
cd /d "%HERE%backend"
venv\Scripts\python.exe manage.py init_env
if errorlevel 1 goto :fail

echo [4/6] Creating / updating the database...
venv\Scripts\python.exe manage.py makemigrations erp
venv\Scripts\python.exe manage.py migrate
if errorlevel 1 goto :fail

echo.
choice /c YN /m "Create the ADMIN login now"
if errorlevel 2 goto :skipadmin
venv\Scripts\python.exe manage.py createsuperuser
:skipadmin

echo [5/6] Installing React packages. This can take a few minutes...
cd /d "%HERE%frontend"
call npm install
if errorlevel 1 goto :fail

cd /d "%HERE%"
echo.
choice /c YN /m "Enter company details for the PDFs now"
if errorlevel 2 goto :skipco
call "%HERE%2_CONFIGURE_COMPANY.bat" nopause
:skipco

echo.
echo [6/6] DONE.
echo Next: double-click START_APP.bat, then open http://localhost:5173
echo.
pause
exit /b 0

:nopython
echo.
echo Python is not installed. Download Python 3.11 or newer from https://www.python.org/downloads/
echo During install, tick "Add python.exe to PATH". Then run this file again.
pause
exit /b 1

:nonode
echo.
echo Node.js is not installed. Download the LTS version from https://nodejs.org
echo Install it, then CLOSE this window and run this file again.
pause
exit /b 1

:fail
echo.
echo *** Setup stopped because of an error. Read the message above. ***
pause
exit /b 1
