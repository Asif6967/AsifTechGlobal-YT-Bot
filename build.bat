@echo off
chcp 65001 >nul
title AsifTechGlobal Launcher — Build
echo.
echo  ⚡ AsifTechGlobal Launcher — Build Script
echo  ==========================================
echo.

:: Check if g++ is available
where g++ >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] g++ not found in PATH.
    echo  Install WinLibs via:
    echo    winget install -e --id BrechtSanders.WinLibs.POSIX.MSVCRT
    echo.
    echo  After install, open a NEW terminal and run build.bat again.
    pause
    exit /b 1
)

echo  [INFO] Compiler found:
where g++
echo.
echo  [BUILD] Compiling launcher.cpp ...
echo.

g++ -std=c++17 -O2 ^
    -o launcher.exe launcher.cpp ^
    -lgdiplus -ldwmapi -lshell32 -lcomctl32 ^
    -mwindows ^
    -finput-charset=UTF-8 ^
    -Wall -Wno-unused-variable

if %errorlevel% neq 0 (
    echo.
    echo  [FAILED] Build failed. Check errors above.
    pause
    exit /b 1
)

echo.
echo  [SUCCESS] launcher.exe built!
echo.
echo  Run it:  .\launcher.exe
echo  Or double-click launcher.exe in File Explorer
echo.
pause
