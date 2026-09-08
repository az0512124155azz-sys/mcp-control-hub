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
$PairingFile = Join-Path $InstallRoot 'pairing-code.txt'

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

if (-not (Test-Path $PairingFile)) {
  $Alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  $Bytes = New-Object byte[] 8
  $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try {
    $Rng.GetBytes($Bytes)
  } finally {
    $Rng.Dispose()
  }
  $PairingCode = -join ($Bytes | ForEach-Object { $Alphabet[$_ % $Alphabet.Length] })
  [System.IO.File]::WriteAllText($PairingFile, $PairingCode, [System.Text.Encoding]::ASCII)
} else {
  $PairingCode = (Get-Content $PairingFile -Raw).Trim().ToUpperInvariant()
}

# Restrict the pairing-code file to the current Windows account when possible.
try {
  $CurrentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $Acl = New-Object System.Security.AccessControl.FileSecurity
  $Acl.SetAccessRuleProtection($true, $false)
  $Rule = New-Object System.Security.AccessControl.FileSystemAccessRule($CurrentIdentity, 'FullControl', 'Allow')
  $Acl.AddAccessRule($Rule)
  Set-Acl -Path $PairingFile -AclObject $Acl
} catch {
  Write-Host 'Could not tighten the pairing-code ACL automatically; continuing.' -ForegroundColor DarkYellow
}

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

$ShowCodeBat = Join-Path $InstallRoot 'SHOW-PAIRING-CODE.bat'
$ShowCodeContent = @"
@echo off
echo.
echo MCP Control Hub pairing code:
type "%~dp0pairing-code.txt"
echo.
echo.
pause
"@
[System.IO.File]::WriteAllText($ShowCodeBat, $ShowCodeContent, [System.Text.Encoding]::ASCII)

Write-Host ''
Write-Host 'Installation completed successfully.' -ForegroundColor Green
Write-Host "Permanent install folder: $InstallRoot" -ForegroundColor Gray
Write-Host ''
Write-Host '=========================================' -ForegroundColor Cyan
Write-Host '          YOUR PAIRING CODE' -ForegroundColor Cyan
Write-Host ''
Write-Host "              $PairingCode" -ForegroundColor Yellow
Write-Host ''
Write-Host '=========================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Enter this code on the MCP Control Hub website before downloading your MCP config.' -ForegroundColor Green
Write-Host "You can show it again later by opening: $ShowCodeBat" -ForegroundColor Gray
Write-Host ''
