@echo off
chcp 936 >nul
title Bilibili Video Downloader

echo ========================================
echo    Bilibili Video Downloader
echo ========================================
echo.
echo Starting server, please wait...
echo.

if not exist runtime\python.exe (
    echo [Error] runtime\python.exe not found
    echo Please make sure runtime folder exists
    pause
    exit /b 1
)

if not exist api.py (
    echo [Error] api.py not found
    pause
    exit /b 1
)

echo [Info] Starting server...
echo [Info] Please wait, first start may take a few seconds
echo.

runtime\python.exe api.py

echo.
echo Server stopped, press any key to exit...
pause >nul
