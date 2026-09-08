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
PAIRING_FILE="$INSTALL_ROOT/pairing-code.txt"

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

# Keep one stable pairing code for this computer. Reinstalling preserves it.
if [[ -f "$PAIRING_FILE" ]]; then
  PAIRING_CODE="$(tr -d '\r\n ' < "$PAIRING_FILE" | tr '[:lower:]' '[:upper:]')"
else
  if command -v openssl >/dev/null 2>&1; then
    PAIRING_CODE="$(openssl rand -hex 4 | tr '[:lower:]' '[:upper:]')"
  else
    PAIRING_CODE="$(python3 - <<'PY'
import secrets
alphabet='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
print(''.join(secrets.choice(alphabet) for _ in range(8)))
PY
)"
  fi
  printf '%s\n' "$PAIRING_CODE" > "$PAIRING_FILE"
  chmod 600 "$PAIRING_FILE"
fi
printf '%s\n' "$PAIRING_CODE" > "$BROWSER_DIR/.pairing-code"
printf '%s\n' "$PAIRING_CODE" > "$COMPUTER_DIR/.pairing-code"
chmod 600 "$BROWSER_DIR/.pairing-code" "$COMPUTER_DIR/.pairing-code"
cat > "$INSTALL_ROOT/SHOW-PAIRING-CODE.sh" <<'SH'
#!/usr/bin/env bash
cat "$HOME/.mcp-control-hub/pairing-code.txt"
SH
chmod +x "$INSTALL_ROOT/SHOW-PAIRING-CODE.sh"


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
printf '\n=========================================\n'
printf '          YOUR PAIRING CODE\n\n'
printf '              %s\n' "$PAIRING_CODE"
printf '\n=========================================\n'
printf 'Enter this code on the MCP Control Hub website before downloading your AI config.\n'
printf 'Show it again later with: %s\n' "$INSTALL_ROOT/SHOW-PAIRING-CODE.sh"
printf 'Permanent install folder: %s\n' "$INSTALL_ROOT"
printf 'You can now download an MCP config from the website. It uses the permanent install folder automatically.\n\n'
