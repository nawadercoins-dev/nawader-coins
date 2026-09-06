from pathlib import Path

APP=Path('admin/app.js')
app=APP.read_text(encoding='utf-8')
marker='// dues-layout-cleanup-v3'
if marker in app:
    print('already patched')
    raise SystemExit(0)

needle="function unifiedDueStyles(){\n  if(document.getElementById('unifiedDuesStyle')) return;"
if needle not in app:
    raise SystemExit('unified dues marker not found')

insert=r'''
// dues-layout-cleanup-v3
function closeDuesImageViewer(){
  try{
    document.querySelectorAll('.image-viewer,.viewer-tools,[id*="lightbox" i],[class*="lightbox" i],[id*="imageViewer" i],[class*="image-viewer" i]').forEach(el=>{
      if(el.closest && el.closest('#dues')) return;
      if(el.tagName==='DIALOG' && el.open){try{el.close()}catch(_){}}
      el.classList?.remove('open','active','show','visible');
      el.removeAttribute?.('open');
      if(el.classList?.contains('image-viewer')||el.classList?.contains('viewer-tools')||String(el.id||'').toLowerCase().includes('lightbox')) el.style.display='none';
    });
  }catch(_){ }
}
'''
app=app.replace(needle,insert+'\n'+needle,1)

# Ensure the unwanted large image viewer is closed whenever the dues center renders.
old="async function renderDues(){\n  if(!$('duesList'))return; unifiedDueStyles();"
new="async function renderDues(){\n  if(!$('duesList'))return; unifiedDueStyles(); closeDuesImageViewer();"
if old not in app:
    raise SystemExit('renderDues marker not found')
app=app.replace(old,new,1)

# Replace the injected dues CSS with a cleaner, wider and more consistent layout.
old_css=".dues-board{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.dues-lane{border:1px solid #dacb9b;border-radius:16px;background:#fffaf0;padding:12px;min-height:160px}.dues-lane h3{margin:0 0 10px;color:#0b2a52;display:flex;justify-content:space-between;gap:8px}.dues-lane h3 span{background:#0b2a52;color:#fff;border-radius:999px;padding:2px 8px;font-size:.8rem}.due-row{margin:9px 0}.source-chip{display:inline-block;border-radius:999px;padding:4px 8px;font-weight:900;background:#e9eef7;color:#0b2a52}.source-chip.auction{background:#fff0cd;color:#805300}.source-chip.market{background:#ddf1e5;color:#17633c}.source-chip.other{background:#e9e2f8;color:#5f3b8c}.due-route-note{margin-top:6px;font-size:.82rem;color:#64748b}.dues-empty{padding:18px;text-align:center;color:#7a8491}.due-actions button{margin:3px}.dues-help{padding:10px 12px;border-radius:12px;background:#eef6ff;border:1px solid #c7dbee;color:#174f84;line-height:1.8;margin:10px 0 14px}@media(max-width:950px){.dues-board{grid-template-columns:1fr}}"
new_css=".dues-board{display:grid;grid-template-columns:repeat(3,minmax(280px,1fr));gap:16px;align-items:start}.dues-lane{border:1px solid #dacb9b;border-radius:18px;background:#fffaf0;padding:14px;min-height:180px;box-shadow:0 5px 16px rgba(11,42,82,.06)}.dues-lane h3{margin:0 0 12px;color:#0b2a52;display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:1.05rem}.dues-lane h3 span{display:inline-flex;align-items:center;justify-content:center;min-width:28px;height:28px;background:#0b2a52;color:#fff;border-radius:999px;padding:0 8px;font-size:.8rem}.due-row{margin:10px 0;padding:13px;border:1px solid #e0d3ad;border-radius:14px;background:#fff;box-shadow:0 3px 10px rgba(11,42,82,.04)}.due-row b{display:block;margin:7px 0 4px;line-height:1.55;color:#14243b}.due-row p{margin:4px 0;line-height:1.55;color:#526173}.source-chip{display:inline-flex;align-items:center;min-height:28px;border-radius:999px;padding:4px 9px;font-weight:900;background:#e9eef7;color:#0b2a52;font-size:.78rem}.source-chip.auction{background:#fff0cd;color:#805300}.source-chip.market{background:#ddf1e5;color:#17633c}.source-chip.other{background:#e9e2f8;color:#5f3b8c}.due-route-note{margin-top:7px;font-size:.82rem;color:#64748b}.dues-empty{padding:22px;text-align:center;color:#7a8491}.due-actions{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-top:11px}.due-actions button{margin:0!important;min-height:42px;padding:8px 7px;border-radius:10px;line-height:1.35;white-space:normal;font-size:.84rem}.dues-help{padding:11px 13px;border-radius:12px;background:#eef6ff;border:1px solid #c7dbee;color:#174f84;line-height:1.8;margin:10px 0 14px}.dues-source-tabs{align-items:center}.dues-source-tabs button{min-height:38px}@media(max-width:1050px){.dues-board{grid-template-columns:repeat(2,minmax(280px,1fr))}}@media(max-width:720px){.dues-board{grid-template-columns:1fr}.due-actions{grid-template-columns:1fr 1fr}.due-actions button:first-child{grid-column:1/-1}}body:has(#dues.view.active) .image-viewer,body:has(#dues.view.active) .viewer-tools{display:none!important}"
if old_css not in app:
    raise SystemExit('dues css marker not found')
app=app.replace(old_css,new_css,1)

APP.write_text(app,encoding='utf-8')
print('patched dues layout cleanup v3')
