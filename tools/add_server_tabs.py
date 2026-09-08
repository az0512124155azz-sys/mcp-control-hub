from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'Missing marker in {label}: {old[:100]!r}')
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# 1) Website: remove the previous tabs and inject TWO independent templates.
# ---------------------------------------------------------------------------
site_path = 'index.html'
s = read(site_path)

# Remove the old injected tab UI if it was already applied.
s = re.sub(r'\n?<style id="mcp-server-tabs-style">.*?</style>\n?', '\n', s, flags=re.S)
s = re.sub(r'\n?<script id="mcp-server-tabs-script">.*?</script>\n?', '\n', s, flags=re.S)
# Make reruns idempotent.
s = re.sub(r'\n?<style id="mcp-server-templates-style">.*?</style>\n?', '\n', s, flags=re.S)
s = re.sub(r'\n?<script id="mcp-server-templates-script">.*?</script>\n?', '\n', s, flags=re.S)

css = r'''
<style id="mcp-server-templates-style">
.mcp-template-section{margin:22px 0 18px}.mcp-template-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:14px;margin-bottom:12px}.mcp-template-heading h3{margin:0;font-size:22px;letter-spacing:-.02em}.mcp-template-heading p{margin:4px 0 0;color:#68707d;font-size:13px;line-height:1.6}.mcp-template-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.mcp-template-card{border:1px solid #dde2e9;border-radius:18px;background:#fbfcfe;overflow:hidden}.mcp-template-card.browser{box-shadow:inset 0 4px 0 #2458e6}.mcp-template-card.computer{box-shadow:inset 0 4px 0 #7557e8}.mcp-template-head{padding:18px 18px 14px;border-bottom:1px solid #e4e8ee;background:white}.mcp-template-head .badge{display:inline-flex;padding:5px 8px;border-radius:999px;background:#eef3ff;color:#2458e6;font-size:11px;font-weight:800}.mcp-template-card.computer .badge{background:#f2efff;color:#6b4ee2}.mcp-template-head h4{margin:9px 0 4px;font-size:19px}.mcp-template-head p{margin:0;color:#6d7682;font-size:12px;line-height:1.55}.mcp-template-body{padding:16px;display:grid;gap:12px}.mcp-field{display:grid;gap:6px}.mcp-field-label{font-size:11px;font-weight:800;color:#58616d}.mcp-value{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:42px;border:1px solid #dfe3e8;border-radius:10px;background:white;padding:8px 10px;direction:ltr;text-align:left}.mcp-value code{font-size:12px;overflow:auto;white-space:nowrap;flex:1}.mcp-copy{border:1px solid #d8dde5;background:#f7f8fa;border-radius:7px;padding:5px 8px;font-size:11px;cursor:pointer;white-space:nowrap}.mcp-args{display:grid;gap:6px}.mcp-arg{display:flex;align-items:center;gap:8px;direction:ltr}.mcp-arg-number{width:22px;height:22px;border-radius:6px;background:#eef1f5;display:grid;place-items:center;font-size:10px;color:#66707c;flex:0 0 auto}.mcp-arg code{flex:1;min-width:0;border:1px solid #e0e4ea;border-radius:8px;background:white;padding:8px 10px;font-size:11px;overflow:auto;white-space:nowrap}.mcp-empty{color:#88919d;font-size:12px;border:1px dashed #d5dbe3;border-radius:9px;padding:9px 10px;background:white}.mcp-simple-note{margin-top:4px;border-radius:10px;padding:10px 11px;background:#edf8f2;color:#286247;font-size:12px;line-height:1.55}.mcp-template-card.computer .mcp-simple-note{background:#f3f0ff;color:#5a4794}@media(max-width:820px){.mcp-template-grid{grid-template-columns:1fr}.mcp-template-heading{display:block}}
</style>
'''

js = r'''
<script id="mcp-server-templates-script">
(()=>{
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const osName=()=>{
    const active=document.querySelector('[data-os].active');
    if(active&&active.dataset.os)return active.dataset.os;
    const u=(navigator.userAgent||'').toLowerCase();
    if(u.includes('mac'))return 'mac';
    if(u.includes('linux'))return 'linux';
    return 'windows';
  };
  const dataFor=(kind)=>{
    const os=osName();
    if(os==='windows'){
      return kind==='browser' ? {
        name:'MCP Control Hub - Chrome', command:'cmd.exe',
        args:['/d','/s','/c','"%LOCALAPPDATA%\\MCP-Control-Hub\\START-BROWSER-MCP.cmd"'],
        note:'תבנית זו נותנת ל-AI רק את כלי Chrome / Browser MCP.'
      } : {
        name:'MCP Control Hub - Screen Control', command:'cmd.exe',
        args:['/d','/s','/c','"%LOCALAPPDATA%\\MCP-Control-Hub\\START-COMPUTER-MCP.cmd"'],
        note:'תבנית זו נותנת ל-AI שליטה במסך, עכבר ומקלדת בלבד.'
      };
    }
    const root='$HOME/.mcp-control-hub';
    return kind==='browser' ? {
      name:'MCP Control Hub - Chrome', command:'sh', args:['-lc',`"${root}/START-BROWSER-MCP.sh"`], note:'תבנית זו נותנת ל-AI רק את כלי Chrome / Browser MCP.'
    } : {
      name:'MCP Control Hub - Screen Control', command:'sh', args:['-lc',`"${root}/START-COMPUTER-MCP.sh"`], note:'תבנית זו נותנת ל-AI שליטה במסך, עכבר ומקלדת בלבד.'
    };
  };
  const copy=async(value,button)=>{try{await navigator.clipboard.writeText(value);const old=button.textContent;button.textContent='הועתק';setTimeout(()=>button.textContent=old,900);}catch{}};
  const field=(label,value)=>`<div class="mcp-field"><div class="mcp-field-label">${esc(label)}</div><div class="mcp-value"><code>${esc(value)}</code><button type="button" class="mcp-copy" data-copy="${esc(value)}">העתק</button></div></div>`;
  const argsHtml=(args)=>`<div class="mcp-field"><div class="mcp-field-label">Arguments — לחץ Add argument והכנס כל שורה בנפרד</div><div class="mcp-args">${args.map((a,i)=>`<div class="mcp-arg"><span class="mcp-arg-number">${i+1}</span><code>${esc(a)}</code><button type="button" class="mcp-copy" data-copy="${esc(a)}">העתק</button></div>`).join('')}</div></div>`;
  const card=(kind)=>{
    const d=dataFor(kind), browser=kind==='browser';
    return `<article class="mcp-template-card ${kind}"><div class="mcp-template-head"><span class="badge">תבנית ${browser?'1':'2'}</span><h4>${browser?'Chrome MCP':'שליטה במסך'}</h4><p>${esc(d.note)}</p></div><div class="mcp-template-body">${field('Name',d.name)}${field('Type','STDIO')}${field('Command to launch',d.command)}${argsHtml(d.args)}<div class="mcp-field"><div class="mcp-field-label">Environment variables</div><div class="mcp-empty">להשאיר ריק — ה-launcher קורא את קוד החיבור מהמחשב אוטומטית.</div></div><div class="mcp-field"><div class="mcp-field-label">Environment variable passthrough</div><div class="mcp-empty">להשאיר ריק</div></div><div class="mcp-field"><div class="mcp-field-label">Working directory</div><div class="mcp-empty">להשאיר ריק</div></div><div class="mcp-simple-note">אין צורך להקליד כאן את Pairing Code. המתקין שומר אותו מקומית וה-launcher המתאים טוען אותו לבד.</div></div></article>`;
  const render=()=>{
    const host=document.getElementById('mcp-two-templates'); if(!host)return;
    host.innerHTML=`<div class="mcp-template-heading"><div><h3>שתי תבניות נפרדות — אחת לכל MCP</h3><p>לא טאבים. כל תבנית עומדת בפני עצמה ומתחברת כ-Custom MCP נפרד.</p></div></div><div class="mcp-template-grid">${card('browser')}${card('computer')}</div>`;
  };
  const mount=()=>{
    const clientTabs=document.querySelector('.client-tabs');
    if(!clientTabs)return;
    let host=document.getElementById('mcp-two-templates');
    if(!host){host=document.createElement('section');host.id='mcp-two-templates';host.className='mcp-template-section';clientTabs.parentNode.insertBefore(host,clientTabs);}
    render();
    document.addEventListener('click',e=>{
      const b=e.target.closest('.mcp-copy'); if(b){copy(b.dataset.copy||'',b);return;}
      if(e.target.closest('[data-os]'))setTimeout(render,0);
    });
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
</script>
'''

s = s.replace('</head>', css + '\n</head>')
s = s.replace('</body>', js + '\n</body>')
write(site_path, s)
if (ROOT / 'apps/web/index.html').exists():
    write('apps/web/index.html', s)


# ---------------------------------------------------------------------------
# 2) Installers: create one launcher per MCP so the templates stay simple.
# ---------------------------------------------------------------------------
win_path = 'INSTALL-WINDOWS.ps1'
win = read(win_path)
launcher_marker = "Write-Host ''\nWrite-Host 'Installation completed successfully.' -ForegroundColor Green\n"
launcher_block = r'''
# Create simple launchers for Custom MCP screens. They load the local pairing
# code automatically, so users do not need to type environment variables.
$BrowserLauncher = Join-Path $InstallRoot 'START-BROWSER-MCP.cmd'
$BrowserLauncherContent = @"
@echo off
setlocal
set /p MCP_PAIRING_CODE=<"%~dp0pairing-code.txt"
node "%~dp0servers\browser-mcp\dist\index.js"
"@
[System.IO.File]::WriteAllText($BrowserLauncher, $BrowserLauncherContent, [System.Text.Encoding]::ASCII)

$ComputerLauncher = Join-Path $InstallRoot 'START-COMPUTER-MCP.cmd'
$ComputerLauncherContent = @"
@echo off
setlocal
set /p MCP_PAIRING_CODE=<"%~dp0pairing-code.txt"
set MCP_COMPUTER_ALLOW_SCREENSHOTS=1
set MCP_COMPUTER_ALLOW_ACTIONS=1
set MCP_COMPUTER_ACTION_PAUSE=0.05
"%~dp0servers\computer-mcp\.venv\Scripts\python.exe" "%~dp0servers\computer-mcp\server.py"
"@
[System.IO.File]::WriteAllText($ComputerLauncher, $ComputerLauncherContent, [System.Text.Encoding]::ASCII)

'''
if "START-BROWSER-MCP.cmd" not in win:
    win = replace_once(win, launcher_marker, launcher_block + launcher_marker, win_path)
write(win_path, win)


def patch_shell(rel):
    text = read(rel)
    marker = "printf '\\nInstallation completed successfully.\\n'\n"
    block = r'''# Create simple launchers for Custom MCP screens.
cat > "$INSTALL_ROOT/START-BROWSER-MCP.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
export MCP_PAIRING_CODE="$(tr -d '\r\n ' < "$HOME/.mcp-control-hub/pairing-code.txt")"
exec node "$HOME/.mcp-control-hub/servers/browser-mcp/dist/index.js"
SH
chmod +x "$INSTALL_ROOT/START-BROWSER-MCP.sh"

cat > "$INSTALL_ROOT/START-COMPUTER-MCP.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
export MCP_PAIRING_CODE="$(tr -d '\r\n ' < "$HOME/.mcp-control-hub/pairing-code.txt")"
export MCP_COMPUTER_ALLOW_SCREENSHOTS=1
export MCP_COMPUTER_ALLOW_ACTIONS=1
export MCP_COMPUTER_ACTION_PAUSE=0.05
exec "$HOME/.mcp-control-hub/servers/computer-mcp/.venv/bin/python" "$HOME/.mcp-control-hub/servers/computer-mcp/server.py"
SH
chmod +x "$INSTALL_ROOT/START-COMPUTER-MCP.sh"

'''
    if 'START-BROWSER-MCP.sh' not in text:
        text = replace_once(text, marker, block + marker, rel)
    write(rel, text)


patch_shell('INSTALL-MACOS.sh')
patch_shell('INSTALL-LINUX.sh')


# ---------------------------------------------------------------------------
# 3) Rebuild downloadable bundles so the website downloads the new installers.
# ---------------------------------------------------------------------------
EXCLUDE_PARTS = {'node_modules', 'dist', '.venv', '__pycache__', '.git'}


def add_servers(zf):
    base = ROOT / 'servers'
    for path in sorted(base.rglob('*')):
        if path.is_dir():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        zf.write(path, rel.as_posix())


def make_zip(name, installers, start_text):
    temp = ROOT / name
    with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in installers:
            zf.write(ROOT / rel, rel)
        add_servers(zf)
        zf.writestr('START-HERE.txt', start_text)
    targets = [ROOT / 'downloads' / name, ROOT / name]
    web_downloads = ROOT / 'apps/web/downloads'
    if web_downloads.exists():
        targets.append(web_downloads / name)
    data = temp.read_bytes()
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


make_zip(
    'MCP-Control-Hub-Windows.zip',
    ['INSTALL-WINDOWS.bat', 'INSTALL-WINDOWS.ps1'],
    'Windows: extract this ZIP and double-click INSTALL-WINDOWS.bat.\nAfter installation, the website shows TWO separate Custom MCP templates: Chrome and Screen Control.\n',
)
make_zip(
    'MCP-Control-Hub-macOS.zip',
    ['INSTALL-MACOS.sh'],
    'macOS: extract the ZIP, run chmod +x ./INSTALL-MACOS.sh, then ./INSTALL-MACOS.sh.\nThe website shows TWO separate Custom MCP templates.\n',
)
make_zip(
    'MCP-Control-Hub-Linux.zip',
    ['INSTALL-LINUX.sh'],
    'Linux: extract the ZIP, run chmod +x ./INSTALL-LINUX.sh, then ./INSTALL-LINUX.sh.\nThe website shows TWO separate Custom MCP templates.\n',
)
make_zip(
    'MCP-Control-Hub-Local.zip',
    ['INSTALL-WINDOWS.bat', 'INSTALL-WINDOWS.ps1', 'INSTALL-MACOS.sh', 'INSTALL-LINUX.sh'],
    'Choose the installer for your operating system. The install creates two independent MCP launchers: one for Chrome and one for screen control.\n',
)

print('Updated website with two independent MCP templates and rebuilt installer bundles.')
