@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Khazinat V1.5.1
where python >nul 2>nul
if %errorlevel%==0 (python server.py & pause & exit /b)
where py >nul 2>nul
if %errorlevel%==0 (py server.py & pause & exit /b)
echo Python was not found.
pause
