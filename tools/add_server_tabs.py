from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

css = r'''
<style id="mcp-server-tabs-style">
.server-mode-tabs{display:flex;gap:8px;margin:18px 0 8px;padding:5px;background:#f1f3f6;border-radius:12px;width:max-content;max-width:100%}.server-mode-tabs button{border:0;background:transparent;color:#66707c;padding:10px 16px;border-radius:9px;font-weight:750;cursor:pointer}.server-mode-tabs button.active{background:#fff;color:#2458e6;box-shadow:0 2px 10px rgba(29,35,46,.08)}.server-mode-note{margin:8px 0 14px;color:#68707d;font-size:13px}
</style>
'''
js = r'''
<script id="mcp-server-tabs-script">
(()=>{
  let mode='browser';
  const labels={browser:'Chrome / Browser MCP',computer:'שליטה במסך / Computer MCP'};
  function mount(){
    const clientTabs=document.querySelector('.client-tabs');
    if(!clientTabs||document.getElementById('server-mode-tabs'))return;
    const wrap=document.createElement('div');
    wrap.id='server-mode-tabs'; wrap.className='server-mode-tabs';
    wrap.innerHTML='<button type="button" data-mode="browser" class="active">Chrome</button><button type="button" data-mode="computer">שליטה במסך</button>';
    const note=document.createElement('div'); note.id='server-mode-note'; note.className='server-mode-note';
    clientTabs.parentNode.insertBefore(wrap,clientTabs);
    clientTabs.parentNode.insertBefore(note,clientTabs);
    wrap.addEventListener('click',e=>{const b=e.target.closest('button[data-mode]');if(!b)return;mode=b.dataset.mode;wrap.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));renderMode();});
    renderMode();
  }
  function renderMode(){
    const note=document.getElementById('server-mode-note'); if(note) note.textContent=mode==='browser'?'חיבור נפרד לשליטה ב-Chrome. ה-AI יקבל רק את כלי הדפדפן.':'חיבור נפרד לשליטה במסך, עכבר ומקלדת. ה-AI יקבל רק את כלי המחשב.';
    window.MCP_CONTROL_HUB_SERVER_MODE=mode;
    document.dispatchEvent(new CustomEvent('mcp-server-mode-change',{detail:{mode}}));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
</script>
'''
if 'mcp-server-tabs-style' not in s:
    s = s.replace('</head>', css+'\n</head>')
if 'mcp-server-tabs-script' not in s:
    s = s.replace('</body>', js+'\n</body>')
p.write_text(s,encoding='utf-8',newline='\n')
# keep compatibility copy if it exists
q=Path('apps/web/index.html')
if q.exists(): q.write_text(s,encoding='utf-8',newline='\n')
