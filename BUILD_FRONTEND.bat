@echo off
title Aura ERP - Build React for production
cd /d "%~dp0frontend"
call npm run build
echo.
echo Finished. The production files are in the frontend\dist folder.
pause
