#!/usr/bin/env bash
set -euo pipefail

printf '\nMCP Control Hub - macOS installer\n'
printf 'This installer detects its own folder automatically. You do not need to edit any path.\n\n'

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$HOME/.mcp-control-hub"
BROWSER_SOURCE="$SOURCE_ROOT/servers/browser-mcp"
COMPUTER_SOURCE="$SOURCE_ROOT/servers/computer-mcp"
BROWSER_DIR="$INSTALL_ROOT/servers/browser-mcp"
COMPUTER_DIR="$INSTALL_ROOT/servers/computer-mcp"

[[ -d "$BROWSER_SOURCE" ]] || { echo "Missing folder: $BROWSER_SOURCE"; exit 1; }
[[ -d "$COMPUTER_SOURCE" ]] || { echo "Missing folder: $COMPUTER_SOURCE"; exit 1; }
command -v node >/dev/null 2>&1 || { echo 'Node.js 20+ is required.'; exit 1; }
command -v npm >/dev/null 2>&1 || { echo 'npm is required.'; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo 'Python 3 is required.'; exit 1; }

printf 'Installing to: %s\n' "$INSTALL_ROOT"
mkdir -p "$INSTALL_ROOT/servers"
rm -rf "$BROWSER_DIR" "$COMPUTER_DIR"
cp -R "$BROWSER_SOURCE" "$BROWSER_DIR"
cp -R "$COMPUTER_SOURCE" "$COMPUTER_DIR"

printf '\n[1/2] Installing Browser MCP...\n'
cd "$BROWSER_DIR"
npm install
npm run build
npx playwright install chromium

printf '\n[2/2] Installing Computer MCP...\n'
cd "$COMPUTER_DIR"
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

printf '\nInstallation completed successfully.\n'
printf 'Permanent install folder: %s\n' "$INSTALL_ROOT"
printf 'You can now download an MCP config from the website. It uses the permanent install folder automatically.\n\n'
