from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STYLE=ROOT/'admin'/'styles.css'
APP=ROOT/'admin'/'app.js'
INDEX=ROOT/'admin'/'index.html'

css=STYLE.read_text(encoding='utf-8')
marker='/* admin-persistent-lightbox-remove-v1 */'
if marker not in css:
    css += r'''

/* admin-persistent-lightbox-remove-v1 */
/* The collectible viewer must never occupy page space unless it is intentionally opened. */
#coinLightbox:not([open]),
.coin-lightbox:not([open]){
  display:none!important;
  visibility:hidden!important;
  width:0!important;
  height:0!important;
  min-height:0!important;
  max-height:0!important;
  margin:0!important;
  padding:0!important;
  overflow:hidden!important;
}
#coinLightbox[open],.coin-lightbox[open]{
  visibility:visible!important;
}
'''
    STYLE.write_text(css,encoding='utf-8')

app=APP.read_text(encoding='utf-8')
jsmarker='// admin-persistent-lightbox-remove-v1'
if jsmarker not in app:
    app += r'''

// admin-persistent-lightbox-remove-v1
(function(){
  function closePersistentAdminViewer(){
    const d=document.getElementById('coinLightbox');
    if(!d)return;
    try{ if(d.open && typeof d.close==='function') d.close(); else d.removeAttribute('open'); }catch(_){ try{d.removeAttribute('open')}catch(__){} }
    document.documentElement.classList.remove('lightbox-open');
    document.body?.classList.remove('lightbox-open');
  }
  // Close any stale viewer on first admin load and every navigation between admin sections.
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',closePersistentAdminViewer,{once:true});
  else closePersistentAdminViewer();
  document.addEventListener('click',(e)=>{
    if(e.target.closest?.('nav [data-v], .dashboard-go, [data-go]')) setTimeout(closePersistentAdminViewer,0);
  },true);
  window.__closePersistentAdminViewer=closePersistentAdminViewer;
})();
'''
    APP.write_text(app,encoding='utf-8')

idx=INDEX.read_text(encoding='utf-8')
idx=idx.replace('/admin/styles.css?v=5.6.2-r4-lightbox2','/admin/styles.css?v=5.6.2-r4-lightbox3')
idx=idx.replace('/admin/app.js?v=5.6.2-r9.5a-lightbox2','/admin/app.js?v=5.6.2-r9.5a-lightbox3')
INDEX.write_text(idx,encoding='utf-8')

print('patched persistent admin lightbox visibility')
