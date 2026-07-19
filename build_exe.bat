@echo off
chcp 65001 >nul
title AsifTechGlobal — EXE Builder
color 0A

echo.
echo  ██████╗  ██╗   ██╗██╗██╗     ██████╗
echo  ██╔══██╗ ██║   ██║██║██║     ██╔══██╗
echo  ██████╔╝ ██║   ██║██║██║     ██║  ██║
echo  ██╔══██╗ ██║   ██║██║██║     ██║  ██║
echo  ██████╔╝ ╚██████╔╝██║███████╗██████╔╝
echo  ╚═════╝   ╚═════╝ ╚═╝╚══════╝╚═════╝
echo.
echo  AsifTechGlobal — Software Builder
echo  ====================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found!
    echo  Download from: https://python.org
    pause & exit /b 1
)

:: Install/update required packages
echo  [1/4] Installing dependencies...
python -m pip install flask flask-login authlib selenium webdriver-manager pyinstaller --quiet
if %errorlevel% neq 0 (
    echo  [ERROR] pip install failed!
    pause & exit /b 1
)
echo        Done!

:: Clean old build
echo  [2/4] Cleaning old build...
if exist dist\AsifTechGlobal.exe del /q dist\AsifTechGlobal.exe
if exist build rmdir /s /q build
echo        Done!

:: Build EXE
echo  [3/4] Building AsifTechGlobal.exe ...
echo        (This takes 2-5 minutes, please wait...)
echo.
python -m PyInstaller AsifTechGlobal.spec --noconfirm --clean
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Build failed! See errors above.
    pause & exit /b 1
)

:: Verify
if not exist dist\AsifTechGlobal.exe (
    echo  [ERROR] EXE not created!
    pause & exit /b 1
)

echo.
echo  [4/4] Done!
echo.
echo  ==========================================
echo   SUCCESS!
echo   File: dist\AsifTechGlobal.exe
echo.

:: Get file size
for %%A in (dist\AsifTechGlobal.exe) do echo   Size: %%~zA bytes

echo.
echo   SHARE KARNE KA TARIKA:
echo   ----------------------
echo   dist\AsifTechGlobal.exe ko kisi ko bhi bhejo
echo   Double-click karein → Software chalu!
echo   Chrome install hona chahiye (bot ke liye)
echo   ==========================================
echo.

set /p OPEN="Open dist folder now? (y/n): "
if /i "%OPEN%"=="y" explorer dist

pause
