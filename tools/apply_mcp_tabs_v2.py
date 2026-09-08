from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def patch(rel):
    p = ROOT / rel
    if not p.exists():
        return
    s = p.read_text(encoding='utf-8')

    # Remove the previously injected independent-template UI and any older tab UI.
    s = re.sub(r'\n?<style id="mcp-server-templates-style">.*?</style>\n?', '\n', s, flags=re.S)
    s = re.sub(r'\n?<script id="mcp-server-templates-script">.*?</script>\n?', '\n', s, flags=re.S)
    s = re.sub(r'\n?<style id="mcp-server-tabs-style">.*?</style>\n?', '\n', s, flags=re.S)
    s = re.sub(r'\n?<script id="mcp-server-tabs-script">.*?</script>\n?', '\n', s, flags=re.S)

    css = r'''
<style id="mcp-server-tabs-style">
.mcp-kind-wrap{margin:22px 0 18px}.mcp-kind-tabs{display:flex;gap:26px;border-bottom:1px solid #e6e8ec;margin-bottom:18px;overflow-x:auto}.mcp-kind-tab{border:0;background:transparent;color:#5f6874;padding:13px 8px 12px;margin-bottom:-1px;border-bottom:3px solid transparent;font-weight:800;font-size:15px;cursor:pointer;white-space:nowrap}.mcp-kind-tab.active{color:#2458e6;border-bottom-color:#2458e6}.mcp-kind-panel{display:none}.mcp-kind-panel.active{display:block}.mcp-kind-title{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin:0 0 14px}.mcp-kind-title h3{margin:0 0 5px;font-size:22px;letter-spacing:-.02em}.mcp-kind-title p{margin:0;color:#68707d;font-size:13px;line-height:1.6}.mcp-setup-card{border:1px solid #dfe3e8;border-radius:18px;background:#fbfcfe;overflow:hidden}.mcp-setup-card.browser{box-shadow:inset 0 4px 0 #2458e6}.mcp-setup-card.computer{box-shadow:inset 0 4px 0 #7557e8}.mcp-setup-body{padding:18px;display:grid;gap:12px}.mcp-field{display:grid;gap:6px}.mcp-field-label{font-size:11px;font-weight:800;color:#58616d}.mcp-value{display:flex;align-items:center;gap:10px;min-height:42px;border:1px solid #dfe3e8;border-radius:10px;background:#fff;padding:8px 10px;direction:ltr;text-align:left}.mcp-value code{font-size:12px;overflow:auto;white-space:nowrap;flex:1}.mcp-copy{border:1px solid #d8dde5;background:#f7f8fa;border-radius:7px;padding:5px 8px;font-size:11px;cursor:pointer;white-space:nowrap}.mcp-args{display:grid;gap:6px}.mcp-arg{display:flex;align-items:center;gap:8px;direction:ltr}.mcp-arg-number{width:22px;height:22px;border-radius:6px;background:#eef1f5;display:grid;place-items:center;font-size:10px;color:#66707c;flex:0 0 auto}.mcp-arg code{flex:1;min-width:0;border:1px solid #e0e4ea;border-radius:8px;background:#fff;padding:8px 10px;font-size:11px;overflow:auto;white-space:nowrap}.mcp-empty{color:#88919d;font-size:12px;border:1px dashed #d5dbe3;border-radius:9px;padding:9px 10px;background:#fff}.mcp-simple-note{border-radius:10px;padding:10px 11px;background:#edf8f2;color:#286247;font-size:12px;line-height:1.55}.mcp-setup-card.computer .mcp-simple-note{background:#f3f0ff;color:#5a4794}@media(max-width:760px){.mcp-kind-tabs{gap:14px}.mcp-kind-title{display:block}}
</style>
'''

    js = r'''
<script id="mcp-server-tabs-script">
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
        note:'החיבור הזה נותן ל-AI רק את כלי Chrome / Browser MCP.'
      } : {
        name:'MCP Control Hub - Screen Control', command:'cmd.exe',
        args:['/d','/s','/c','"%LOCALAPPDATA%\\MCP-Control-Hub\\START-COMPUTER-MCP.cmd"'],
        note:'החיבור הזה נותן ל-AI שליטה במסך, עכבר ומקלדת.'
      };
    }
    const root='$HOME/.mcp-control-hub';
    return kind==='browser' ? {
      name:'MCP Control Hub - Chrome', command:'sh', args:['-lc',`"${root}/START-BROWSER-MCP.sh"`], note:'החיבור הזה נותן ל-AI רק את כלי Chrome / Browser MCP.'
    } : {
      name:'MCP Control Hub - Screen Control', command:'sh', args:['-lc',`"${root}/START-COMPUTER-MCP.sh"`], note:'החיבור הזה נותן ל-AI שליטה במסך, עכבר ומקלדת.'
    };
  };
  const copy=async(value,button)=>{try{await navigator.clipboard.writeText(value);const old=button.textContent;button.textContent='הועתק';setTimeout(()=>button.textContent=old,900);}catch{}};
  const field=(label,value)=>`<div class="mcp-field"><div class="mcp-field-label">${esc(label)}</div><div class="mcp-value"><code>${esc(value)}</code><button type="button" class="mcp-copy" data-copy="${esc(value)}">העתק</button></div></div>`;
  const argsHtml=(args)=>`<div class="mcp-field"><div class="mcp-field-label">Arguments — לחץ Add argument והכנס כל שורה בנפרד</div><div class="mcp-args">${args.map((a,i)=>`<div class="mcp-arg"><span class="mcp-arg-number">${i+1}</span><code>${esc(a)}</code><button type="button" class="mcp-copy" data-copy="${esc(a)}">העתק</button></div>`).join('')}</div></div>`;
  const card=(kind)=>{
    const d=dataFor(kind), browser=kind==='browser';
    return `<div class="mcp-kind-title"><div><h3>${browser?'Chrome MCP':'שליטה במסך'}</h3><p>${esc(d.note)}</p></div></div><article class="mcp-setup-card ${kind}"><div class="mcp-setup-body">${field('Name',d.name)}${field('Type','STDIO')}${field('Command to launch',d.command)}${argsHtml(d.args)}<div class="mcp-field"><div class="mcp-field-label">Environment variables</div><div class="mcp-empty">להשאיר ריק — ה-launcher קורא את קוד החיבור אוטומטית.</div></div><div class="mcp-field"><div class="mcp-field-label">Environment variable passthrough</div><div class="mcp-empty">להשאיר ריק</div></div><div class="mcp-field"><div class="mcp-field-label">Working directory</div><div class="mcp-empty">להשאיר ריק</div></div><div class="mcp-simple-note">כל טאב הוא MCP נפרד. אם אתה רוצה את שניהם ב-AI, הוסף שני Custom MCPs — אחד מכל טאב.</div></div></article>`;
  };
  const renderPanels=()=>{
    const b=document.getElementById('mcp-browser-panel');
    const c=document.getElementById('mcp-computer-panel');
    if(b)b.innerHTML=card('browser');
    if(c)c.innerHTML=card('computer');
  };
  const mount=()=>{
    const clientTabs=document.querySelector('.client-tabs');
    if(!clientTabs)return;
    let host=document.getElementById('mcp-kind-wrap');
    if(!host){
      host=document.createElement('section');
      host.id='mcp-kind-wrap'; host.className='mcp-kind-wrap';
      host.innerHTML=`<div class="mcp-kind-tabs" role="tablist"><button type="button" class="mcp-kind-tab active" data-kind="browser">Chrome MCP</button><button type="button" class="mcp-kind-tab" data-kind="computer">שליטה במסך</button></div><div id="mcp-browser-panel" class="mcp-kind-panel active"></div><div id="mcp-computer-panel" class="mcp-kind-panel"></div>`;
      clientTabs.parentNode.insertBefore(host,clientTabs);
    }
    renderPanels();
    host.addEventListener('click',e=>{
      const tab=e.target.closest('.mcp-kind-tab');
      if(tab){
        host.querySelectorAll('.mcp-kind-tab').forEach(x=>x.classList.toggle('active',x===tab));
        host.querySelectorAll('.mcp-kind-panel').forEach(x=>x.classList.remove('active'));
        const panel=document.getElementById(tab.dataset.kind==='browser'?'mcp-browser-panel':'mcp-computer-panel');
        if(panel)panel.classList.add('active');
        return;
      }
      const b=e.target.closest('.mcp-copy'); if(b)copy(b.dataset.copy||'',b);
    });
    document.addEventListener('click',e=>{if(e.target.closest('[data-os]'))setTimeout(renderPanels,0);});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
</script>
'''

    s = s.replace('</head>', css + '\n</head>')
    s = s.replace('</body>', js + '\n</body>')
    p.write_text(s, encoding='utf-8', newline='\n')


patch('index.html')
patch('apps/web/index.html')
