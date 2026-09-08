@echo off
setlocal
cd /d "%~dp0"

echo.
echo MCP Control Hub - Windows installer
echo No paths to edit. This launcher uses its own folder automatically.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-WINDOWS.ps1"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo Installation finished successfully.
) else (
  echo Installation failed with exit code %EXITCODE%.
  echo Keep this window open and copy the error above if you need help.
)
echo.
pause
exit /b %EXITCODE%
