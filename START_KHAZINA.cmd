@echo off
setlocal
cd /d "%~dp0"
title Nawader Coins V4.0.24
where python >nul 2>nul
if %errorlevel%==0 goto runpython
where py >nul 2>nul
if %errorlevel%==0 goto runpy

echo Python was not found on this computer.
echo Install Python, then run this file again.
pause
exit /b 1

:runpython
python server.py
if not %errorlevel%==0 echo Error code: %errorlevel% > START_ERROR.txt
pause
exit /b

:runpy
py server.py
if not %errorlevel%==0 echo Error code: %errorlevel% > START_ERROR.txt
pause
exit /b
