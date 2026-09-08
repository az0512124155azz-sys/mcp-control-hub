#!/usr/bin/env python3
from pathlib import Path
import shutil, zipfile

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'Missing expected marker in {label}: {old[:80]!r}')
    return text.replace(old, new, 1)


# ---------------- Browser MCP ----------------
browser_path = 'servers/browser-mcp/src/index.ts'
browser = read(browser_path)

browser = browser.replace('import { join } from "node:path";', 'import { dirname, join } from "node:path";')
browser = browser.replace('import { URL } from "node:url";', 'import { URL, fileURLToPath } from "node:url";')
if 'from "node:fs"' not in browser:
    browser = browser.replace('import { randomBytes } from "node:crypto";\n', 'import { randomBytes } from "node:crypto";\nimport { readFileSync } from "node:fs";\n')

# Fix the earlier Playwright readonly-array build error if an older copy was re-uploaded.
browser = browser.replace('    } as const;\n', '    };\n')

pairing_block_ts = '''const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
const PAIRING_FILE = join(MODULE_DIR, "..", ".pairing-code");

function requirePairingCode() {
  let expected = "";
  try {
    expected = readFileSync(PAIRING_FILE, "utf8").trim().toUpperCase();
  } catch {
    throw new Error(`Pairing code file is missing: ${PAIRING_FILE}. Run the MCP Control Hub installer again.`);
  }

  const supplied = (process.env.MCP_PAIRING_CODE || "").trim().toUpperCase();
  if (!supplied) {
    throw new Error("MCP_PAIRING_CODE is missing. Enter the pairing code shown by the installer when generating your MCP config.");
  }
  if (supplied !== expected) {
    throw new Error("MCP pairing code is invalid for this computer.");
  }
}

'''
if 'function requirePairingCode()' not in browser:
    browser = replace_once(browser, 'class BrowserRuntime {', pairing_block_ts + 'class BrowserRuntime {', browser_path)

if 'requirePairingCode();\nvoid serveStdio(buildServer);' not in browser:
    browser = replace_once(browser, 'void serveStdio(buildServer);', 'requirePairingCode();\nvoid serveStdio(buildServer);', browser_path)

write(browser_path, browser)
write('servers/browser-mcp/.env.example', 'MCP_PAIRING_CODE=YOUR_8_CHARACTER_CODE\n')


# ---------------- Computer MCP ----------------
computer_path = 'servers/computer-mcp/server.py'
computer = read(computer_path)
if 'from pathlib import Path' not in computer:
    computer = computer.replace('import platform\n', 'import platform\nfrom pathlib import Path\n')

pairing_block_py = '''\nPAIRING_FILE = Path(__file__).with_name(".pairing-code")


def _require_pairing_code() -> None:
    try:
        expected = PAIRING_FILE.read_text(encoding="utf-8").strip().upper()
    except OSError as exc:
        raise RuntimeError(f"Pairing code file is missing: {PAIRING_FILE}. Run the MCP Control Hub installer again.") from exc

    supplied = os.getenv("MCP_PAIRING_CODE", "").strip().upper()
    if not supplied:
        raise RuntimeError(
            "MCP_PAIRING_CODE is missing. Enter the pairing code shown by the installer when generating your MCP config."
        )
    if supplied != expected:
        raise RuntimeError("MCP pairing code is invalid for this computer.")


_require_pairing_code()
'''
if '_require_pairing_code()' not in computer:
    computer = replace_once(computer, 'mcp = MCPServer("Computer Control MCP")\n', 'mcp = MCPServer("Computer Control MCP")\n' + pairing_block_py, computer_path)

write(computer_path, computer)
write('servers/computer-mcp/.env.example', 'MCP_PAIRING_CODE=YOUR_8_CHARACTER_CODE\nMCP_COMPUTER_ALLOW_SCREENSHOTS=1\nMCP_COMPUTER_ALLOW_ACTIONS=1\n')


# ---------------- Windows installer ----------------
win_path = 'INSTALL-WINDOWS.ps1'
win = read(win_path)
if '$PairingFile =' not in win:
    win = replace_once(win, "$ComputerDir = Join-Path $InstallRoot 'servers\\computer-mcp'\n", "$ComputerDir = Join-Path $InstallRoot 'servers\\computer-mcp'\n$PairingFile = Join-Path $InstallRoot 'pairing-code.txt'\n", win_path)

pairing_ps = r'''
# Keep one stable pairing code for this computer. Reinstalling preserves it.
if (Test-Path $PairingFile) {
  $PairingCode = (Get-Content $PairingFile -Raw).Trim().ToUpperInvariant()
} else {
  $Alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'.ToCharArray()
  $Bytes = New-Object byte[] 8
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($Bytes)
  $Chars = for ($i = 0; $i -lt 8; $i++) { $Alphabet[$Bytes[$i] % $Alphabet.Length] }
  $PairingCode = -join $Chars
  Set-Content -Path $PairingFile -Value $PairingCode -Encoding ASCII
}
Set-Content -Path (Join-Path $BrowserDir '.pairing-code') -Value $PairingCode -Encoding ASCII
Set-Content -Path (Join-Path $ComputerDir '.pairing-code') -Value $PairingCode -Encoding ASCII

$ShowCodeBat = Join-Path $InstallRoot 'SHOW-PAIRING-CODE.bat'
$ShowCodeContents = "@echo off`r`necho.`r`necho MCP Control Hub pairing code:`r`necho.`r`ntype `"%LOCALAPPDATA%\\MCP-Control-Hub\\pairing-code.txt`"`r`necho.`r`npause`r`n"
Set-Content -Path $ShowCodeBat -Value $ShowCodeContents -Encoding ASCII
'''
if '# Keep one stable pairing code for this computer.' not in win:
    win = replace_once(win, "Copy-Item $ComputerSource $ComputerDir -Recurse -Force\n", "Copy-Item $ComputerSource $ComputerDir -Recurse -Force\n" + pairing_ps + "\n", win_path)

if 'YOUR PAIRING CODE' not in win:
    win = replace_once(win, "Write-Host 'Installation completed successfully.' -ForegroundColor Green\n", "Write-Host 'Installation completed successfully.' -ForegroundColor Green\nWrite-Host ''\nWrite-Host '=========================================' -ForegroundColor Yellow\nWrite-Host '          YOUR PAIRING CODE' -ForegroundColor Yellow\nWrite-Host ''\nWrite-Host (\"              {0}\" -f $PairingCode) -ForegroundColor Cyan\nWrite-Host ''\nWrite-Host '=========================================' -ForegroundColor Yellow\nWrite-Host 'Enter this code on the MCP Control Hub website before downloading your AI config.' -ForegroundColor Green\nWrite-Host (\"Show it again later: {0}\" -f $ShowCodeBat) -ForegroundColor Gray\n", win_path)
write(win_path, win)


# ---------------- macOS / Linux installers ----------------
def patch_shell(rel):
    text = read(rel)
    if 'PAIRING_FILE="$INSTALL_ROOT/pairing-code.txt"' not in text:
        text = replace_once(text, 'COMPUTER_DIR="$INSTALL_ROOT/servers/computer-mcp"\n', 'COMPUTER_DIR="$INSTALL_ROOT/servers/computer-mcp"\nPAIRING_FILE="$INSTALL_ROOT/pairing-code.txt"\n', rel)

    block = '''\n# Keep one stable pairing code for this computer. Reinstalling preserves it.\nif [[ -f "$PAIRING_FILE" ]]; then\n  PAIRING_CODE="$(tr -d '\\r\\n ' < "$PAIRING_FILE" | tr '[:lower:]' '[:upper:]')"\nelse\n  if command -v openssl >/dev/null 2>&1; then\n    PAIRING_CODE="$(openssl rand -hex 4 | tr '[:lower:]' '[:upper:]')"\n  else\n    PAIRING_CODE="$(python3 - <<'PY'\nimport secrets\nalphabet='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'\nprint(''.join(secrets.choice(alphabet) for _ in range(8)))\nPY\n)"\n  fi\n  printf '%s\\n' "$PAIRING_CODE" > "$PAIRING_FILE"\n  chmod 600 "$PAIRING_FILE"\nfi\nprintf '%s\\n' "$PAIRING_CODE" > "$BROWSER_DIR/.pairing-code"\nprintf '%s\\n' "$PAIRING_CODE" > "$COMPUTER_DIR/.pairing-code"\nchmod 600 "$BROWSER_DIR/.pairing-code" "$COMPUTER_DIR/.pairing-code"\ncat > "$INSTALL_ROOT/SHOW-PAIRING-CODE.sh" <<'SH'\n#!/usr/bin/env bash\ncat "$HOME/.mcp-control-hub/pairing-code.txt"\nSH\nchmod +x "$INSTALL_ROOT/SHOW-PAIRING-CODE.sh"\n'''
    if '# Keep one stable pairing code for this computer.' not in text:
        text = replace_once(text, 'cp -R "$COMPUTER_SOURCE" "$COMPUTER_DIR"\n', 'cp -R "$COMPUTER_SOURCE" "$COMPUTER_DIR"\n' + block + '\n', rel)

    if 'YOUR PAIRING CODE' not in text:
        text = replace_once(text, "printf '\\nInstallation completed successfully.\\n'\n", "printf '\\nInstallation completed successfully.\\n'\nprintf '\\n=========================================\\n'\nprintf '          YOUR PAIRING CODE\\n\\n'\nprintf '              %s\\n' \"$PAIRING_CODE\"\nprintf '\\n=========================================\\n'\nprintf 'Enter this code on the MCP Control Hub website before downloading your AI config.\\n'\nprintf 'Show it again later with: %s\\n' \"$INSTALL_ROOT/SHOW-PAIRING-CODE.sh\"\n", rel)
    write(rel, text)

patch_shell('INSTALL-MACOS.sh')
patch_shell('INSTALL-LINUX.sh')


# ---------------- Website ----------------
site_path = 'index.html'
site = read(site_path)

pairing_html = '''\n        <div class="info-box" id="pairing-box">\n          <strong>קוד החיבור של ה-MCP</strong>\n          <p>אחרי ההתקנה ה-MCP מציג קוד בן 8 תווים. הכנס אותו כאן ורק אז הורד את קובץ ההגדרה ל-AI.</p>\n          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px">\n            <input id="pairing-code" dir="ltr" maxlength="8" autocomplete="off" spellcheck="false" placeholder="לדוגמה: 7K4P9M2Q" style="min-width:220px;padding:12px 14px;border:1px solid #cfd6e4;border-radius:10px;font:700 16px ui-monospace,monospace;text-transform:uppercase" />\n            <span id="pairing-status" style="font-size:13px;color:#667085">נדרש לפני הורדת קובץ ההגדרה</span>\n          </div>\n        </div>\n'''
if 'id="pairing-code"' not in site:
    marker = '        <p class="guide-note" id="client-note"></p>\n'
    site = replace_once(site, marker, pairing_html + '\n' + marker, site_path)

if 'let pairingCode =' not in site:
    site = replace_once(site, '  let client = "claude";\n', '  let client = "claude";\n  let pairingCode = "";\n', site_path)

if 'const pairingCodeInput' not in site:
    site = replace_once(site, '  const changeOsButton = document.getElementById("change-os");\n', '  const changeOsButton = document.getElementById("change-os");\n  const pairingCodeInput = document.getElementById("pairing-code");\n  const pairingStatus = document.getElementById("pairing-status");\n', site_path)

# Add pairing env to both server entries.
site = site.replace('          args: ["/d", "/s", "/c", "node \\"%LOCALAPPDATA%\\\\MCP-Control-Hub\\\\servers\\\\browser-mcp\\\\dist\\\\index.js\\\""]\n        },', '          args: ["/d", "/s", "/c", "node \\"%LOCALAPPDATA%\\\\MCP-Control-Hub\\\\servers\\\\browser-mcp\\\\dist\\\\index.js\\\""],\n          env: { MCP_PAIRING_CODE: pairingCode }\n        },')
site = site.replace('          env: {\n            MCP_COMPUTER_ALLOW_SCREENSHOTS: "1",', '          env: {\n            MCP_PAIRING_CODE: pairingCode,\n            MCP_COMPUTER_ALLOW_SCREENSHOTS: "1",')
site = site.replace('          args: ["-lc", "node \\"$HOME/.mcp-control-hub/servers/browser-mcp/dist/index.js\\\""]\n        },', '          args: ["-lc", "node \\"$HOME/.mcp-control-hub/servers/browser-mcp/dist/index.js\\\""],\n          env: { MCP_PAIRING_CODE: pairingCode }\n        },')

if 'function validPairingCode()' not in site:
    helper = '''\n  function validPairingCode() {\n    return /^[A-Z2-9]{8}$/.test(pairingCode);\n  }\n\n  function syncPairingUi() {\n    pairingCode = String(pairingCodeInput.value || "").toUpperCase().replace(/[^A-Z2-9]/g, "").slice(0, 8);\n    pairingCodeInput.value = pairingCode;\n    const ok = validPairingCode();\n    pairingStatus.textContent = ok ? "הקוד מוכן — אפשר להוריד קובץ הגדרה" : "הכנס את הקוד בן 8 התווים שהמתקין הציג";\n    pairingStatus.style.color = ok ? "#17803d" : "#667085";\n    downloadConfigButton.disabled = !ok;\n    downloadConfigButton.style.opacity = ok ? "1" : ".55";\n    downloadConfigButton.style.cursor = ok ? "pointer" : "not-allowed";\n  }\n'''
    site = replace_once(site, '  function installLocation(currentOs) {', helper + '\n  function installLocation(currentOs) {', site_path)

if 'pairingCodeInput.addEventListener' not in site:
    site = replace_once(site, '  downloadConfigButton.addEventListener("click", downloadConfig);\n', '  pairingCodeInput.addEventListener("input", () => { syncPairingUi(); render(); });\n  downloadConfigButton.addEventListener("click", () => {\n    if (!validPairingCode()) {\n      pairingCodeInput.focus();\n      pairingStatus.textContent = "צריך להזין קודם את קוד החיבור שה-MCP הציג";\n      return;\n    }\n    downloadConfig();\n  });\n', site_path)

if 'syncPairingUi();\n  render();' not in site:
    site = site.replace('  render();\n})();', '  syncPairingUi();\n  render();\n})();')

write(site_path, site)
write('apps/web/index.html', site)


# ---------------- README ----------------
readme = read('README.md')
section = '''\n## Pairing code\n\nAfter installation, MCP Control Hub generates one stable 8-character pairing code for the computer. Enter that code on the website before downloading an AI configuration. The generated config passes it as `MCP_PAIRING_CODE`; both local MCP servers compare it with the locally stored code and refuse to start if it does not match.\n\n- Windows: `%LOCALAPPDATA%\\MCP-Control-Hub\\SHOW-PAIRING-CODE.bat`\n- macOS/Linux: `~/.mcp-control-hub/SHOW-PAIRING-CODE.sh`\n\n'''
if '## Pairing code' not in readme:
    readme += section
write('README.md', readme)


# ---------------- Distribution ZIPs ----------------
server_files = [
    'servers/browser-mcp/package.json',
    'servers/browser-mcp/tsconfig.json',
    'servers/browser-mcp/src/index.ts',
    'servers/browser-mcp/.env.example',
    'servers/computer-mcp/server.py',
    'servers/computer-mcp/requirements.txt',
    'servers/computer-mcp/pyproject.toml',
    'servers/computer-mcp/.env.example',
]

platforms = {
    'Windows': ['INSTALL-WINDOWS.bat', 'INSTALL-WINDOWS.ps1'],
    'macOS': ['INSTALL-MACOS.sh'],
    'Linux': ['INSTALL-LINUX.sh'],
    'Local': ['INSTALL-WINDOWS.bat', 'INSTALL-WINDOWS.ps1', 'INSTALL-MACOS.sh', 'INSTALL-LINUX.sh'],
}

(ROOT / 'downloads').mkdir(exist_ok=True)
for name, installers in platforms.items():
    out = ROOT / 'downloads' / f'MCP-Control-Hub-{name}.zip'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel in installers + server_files + ['README.md', 'SECURITY.md']:
            path = ROOT / rel
            if path.exists():
                zf.write(path, rel)
    shutil.copy2(out, ROOT / out.name)
    app_downloads = ROOT / 'apps' / 'web' / 'downloads'
    app_downloads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, app_downloads / out.name)

print('Pairing-code update applied successfully.')
