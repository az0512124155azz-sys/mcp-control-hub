$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host 'MCP Control Hub - Windows installer' -ForegroundColor Cyan
Write-Host 'This installer detects its own folder automatically. You do not need to edit any path.' -ForegroundColor Gray
Write-Host ''

$SourceRoot = $PSScriptRoot
$InstallRoot = Join-Path $env:LOCALAPPDATA 'MCP-Control-Hub'
$BrowserSource = Join-Path $SourceRoot 'servers\browser-mcp'
$ComputerSource = Join-Path $SourceRoot 'servers\computer-mcp'
$BrowserDir = Join-Path $InstallRoot 'servers\browser-mcp'
$ComputerDir = Join-Path $InstallRoot 'servers\computer-mcp'

if (-not (Test-Path $BrowserSource)) { throw "Missing folder: $BrowserSource" }
if (-not (Test-Path $ComputerSource)) { throw "Missing folder: $ComputerSource" }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 20+ is required. Install Node.js, reopen PowerShell, and run this installer again.' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'npm was not found. Reinstall Node.js and run this installer again.' }

$PythonExe = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
  $PythonExe = 'python'
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
  $PythonExe = 'py'
} else {
  throw 'Python 3 is required. Install Python 3, enable Add Python to PATH, reopen PowerShell, and run this installer again.'
}

Write-Host "Installing to: $InstallRoot" -ForegroundColor Yellow
New-Item -ItemType Directory -Path (Join-Path $InstallRoot 'servers') -Force | Out-Null

if (Test-Path $BrowserDir) { Remove-Item $BrowserDir -Recurse -Force }
if (Test-Path $ComputerDir) { Remove-Item $ComputerDir -Recurse -Force }
Copy-Item $BrowserSource $BrowserDir -Recurse -Force
Copy-Item $ComputerSource $ComputerDir -Recurse -Force

Write-Host ''
Write-Host '[1/2] Installing Browser MCP...' -ForegroundColor Cyan
Push-Location $BrowserDir
try {
  npm install
  if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Browser MCP build failed.' }
  npx playwright install chromium
  if ($LASTEXITCODE -ne 0) { throw 'Playwright Chromium installation failed.' }
} finally {
  Pop-Location
}

Write-Host ''
Write-Host '[2/2] Installing Computer MCP...' -ForegroundColor Cyan
Push-Location $ComputerDir
try {
  if ($PythonExe -eq 'py') {
    & py -3 -m venv .venv
  } else {
    & python -m venv .venv
  }
  if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
  $VenvPython = Join-Path $ComputerDir '.venv\Scripts\python.exe'
  & $VenvPython -m pip install --upgrade pip
  if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
  & $VenvPython -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw 'Computer MCP dependency installation failed.' }
} finally {
  Pop-Location
}

Write-Host ''
Write-Host 'Installation completed successfully.' -ForegroundColor Green
Write-Host "Permanent install folder: $InstallRoot" -ForegroundColor Gray
Write-Host 'You can now download an MCP config from the website. It uses the permanent install folder automatically.' -ForegroundColor Green
Write-Host ''
