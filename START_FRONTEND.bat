@echo off
title Aura ERP - React screens (keep this window open)
cd /d "%~dp0frontend"
if not exist "node_modules" ( echo Run 1_SETUP.bat first. & pause & exit /b 1 )
call npm run dev
pause
