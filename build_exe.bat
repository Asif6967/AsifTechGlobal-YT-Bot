@echo off
setlocal
chcp 65001 >nul
title AsifTechGlobal - EXE Builder
color 0A
cd /d "%~dp0"

echo.
echo  AsifTechGlobal - Portable EXE Builder
echo  =====================================
echo.

python --version >nul 2>&1
if errorlevel 1 goto :no_python

echo [1/4] Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :install_failed

echo [2/4] Removing previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/4] Building AsifTechGlobal.exe...
REM Builds from app.py directly. The old script referenced an absent .spec file.
python -m PyInstaller --noconfirm --clean --onefile --name AsifTechGlobal ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "config.example.json;." ^
  --add-data "oauth_config.example.json;." ^
  --hidden-import web_panel ^
  --hidden-import bot ^
  --hidden-import bot_runner ^
  --hidden-import bot_mobile ^
  --hidden-import youtube_bot ^
  --collect-all selenium ^
  --collect-all webdriver_manager ^
  --collect-all authlib ^
  app.py
if errorlevel 1 goto :build_failed

echo [4/4] Verifying output...
if not exist dist\AsifTechGlobal.exe goto :build_failed

echo.
echo [SUCCESS] dist\AsifTechGlobal.exe is ready.
echo Chrome must be installed on PCs using Desktop mode.
pause
goto :eof

:no_python
echo [ERROR] Python 3.10 or newer was not found in PATH.
pause
goto :eof

:install_failed
echo [ERROR] Package installation failed.
pause
goto :eof

:build_failed
echo [ERROR] EXE build failed. Copy the error above when requesting support.
pause
goto :eof
