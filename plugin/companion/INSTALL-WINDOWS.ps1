$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host 'MCP Control Hub Companion - Windows installer' -ForegroundColor Cyan
Write-Host 'This installs the local companion used by the ChatGPT plugin.'
Write-Host ''

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = Join-Path $env:LOCALAPPDATA 'MCP-Control-Hub-Plugin'
$Venv = Join-Path $InstallRoot '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python 3 is required. Install Python first, then run this installer again.'
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item -Force (Join-Path $SourceDir 'companion.py') (Join-Path $InstallRoot 'companion.py')
Copy-Item -Force (Join-Path $SourceDir 'requirements.txt') (Join-Path $InstallRoot 'requirements.txt')

python -m venv $Venv
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $InstallRoot 'requirements.txt')
& $Python -m playwright install chromium

$Launcher = @'
@echo off
setlocal
if "%MCP_CONTROL_HUB_PLUGIN_WS%"=="" set "MCP_CONTROL_HUB_PLUGIN_WS=ws://127.0.0.1:8787/companion"
"%~dp0.venv\Scripts\python.exe" "%~dp0companion.py"
pause
'@
[System.IO.File]::WriteAllText((Join-Path $InstallRoot 'START-COMPANION.cmd'), $Launcher, [System.Text.Encoding]::ASCII)

Write-Host ''
Write-Host 'Installed successfully.' -ForegroundColor Green
Write-Host "Folder: $InstallRoot"
Write-Host 'Start it with:'
Write-Host (Join-Path $InstallRoot 'START-COMPANION.cmd') -ForegroundColor Yellow
Write-Host ''
Write-Host 'IMPORTANT: before public/remote use, set MCP_CONTROL_HUB_PLUGIN_WS to your deployed wss://.../companion URL.' -ForegroundColor Yellow
