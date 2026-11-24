@echo off
title Aura ERP - Backup
set "HERE=%~dp0"
if not exist "%HERE%backend\db.sqlite3" ( echo No database file found. If you use PostgreSQL, back it up with pg_dump. & pause & exit /b 1 )
if not exist "%HERE%backups" mkdir "%HERE%backups"
for /f %%i in ('powershell -nologo -command "Get-Date -Format yyyyMMdd_HHmm"') do set "TS=%%i"
copy "%HERE%backend\db.sqlite3" "%HERE%backups\db_%TS%.sqlite3" >nul
echo Backup saved: backups\db_%TS%.sqlite3
echo Tip: copy the backups folder to a pen drive or cloud drive regularly.
pause
