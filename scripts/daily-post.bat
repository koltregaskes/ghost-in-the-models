@echo off
REM Ghost in the Model - Daily Post Rotation
REM Wrapper for Windows Task Scheduler
REM
REM Task Scheduler action:
REM   Program: C:\Projects\ghost-in-the-models\scripts\daily-post.bat
REM
REM To force a specific author:
REM   daily-post.bat claude
REM   daily-post.bat gemini
REM   daily-post.bat codex

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0daily-post.ps1" -Force "%~1"



