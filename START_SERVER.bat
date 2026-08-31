@echo off
setlocal
chcp 65001 >nul
title AsifTechGlobal - YT Bot Panel
cd /d "%~dp0"

echo.
echo  ==========================================
echo   AsifTechGlobal - YT Bot Panel
echo  ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 goto :no_python

echo [1/2] Installing or checking dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed

echo.
echo [2/2] Starting panel...
python app.py
echo.
echo Panel stopped. Copy any error shown above when requesting support.
pause
goto :eof

:no_python
echo [ERROR] Python 3.10 or newer was not found in PATH.
echo Install Python from https://www.python.org/downloads/ and select "Add Python to PATH".
pause
goto :eof

:install_failed
echo.
echo [ERROR] Dependencies could not be installed. Check your internet connection and the error above.
pause
goto :eof
