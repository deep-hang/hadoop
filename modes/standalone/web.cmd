@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web.ps1" %*
set "m5_exit=%errorlevel%"
if "%~1"=="" pause
exit /b %m5_exit%
