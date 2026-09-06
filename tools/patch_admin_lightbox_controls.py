from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'admin'/'app.js'
STYLE=ROOT/'admin'/'styles.css'
INDEX=ROOT/'admin'/'index.html'

mark='// admin-lightbox-controls-v2'
a=APP.read_text(encoding='utf-8')
if mark not in a:
    inject=r'''

// admin-lightbox-controls-v2
(function installAdminLightboxControls(){
  const dlg=()=>document.getElementById('coinLightbox');
  const img=()=>document.getElementById('coinLightboxImg');
  function safeClose(){
    const d=dlg(); if(!d)return;
    try{ if(document.fullscreenElement) document.exitFullscreen?.().catch?.(()=>{}); }catch(_){ }
    try{ if(typeof d.close==='function' && d.open) d.close(); else d.removeAttribute('open'); }catch(_){ try{d.removeAttribute('open')}catch(__){} }
    document.documentElement.classList.remove('lightbox-open');
    document.body?.classList.remove('lightbox-open');
  }
  function act(a){
    if(!dlg())return;
    if(a==='close'){safeClose();return}
    if(a==='prev'){lbMove(-1);return}
    if(a==='next'){lbMove(1);return}
    if(a==='zin') LB.scale=Math.min(6,Number(LB.scale||1)+.25);
    else if(a==='zout') LB.scale=Math.max(.35,Number(LB.scale||1)-.25);
    else if(a==='rl') LB.rot=Number(LB.rot||0)-90;
    else if(a==='rr') LB.rot=Number(LB.rot||0)+90;
    else if(a==='center'){LB.x=0;LB.y=0}
    else if(a==='fit'){LB.scale=1;LB.rot=0;LB.x=0;LB.y=0}
    else if(a==='reset'){LB.scale=1;LB.rot=0;LB.x=0;LB.y=0}
    else if(a==='full'){
      const d=dlg();
      try{ if(!document.fullscreenElement) d?.requestFullscreen?.().catch?.(()=>{}); else document.exitFullscreen?.().catch?.(()=>{}); }catch(_){ }
    }
    try{lbDraw()}catch(_){ }
  }
  document.addEventListener('click',function(e){
    const close=e.target.closest?.('#coinLightboxClose');
    if(close){e.preventDefault();e.stopPropagation();safeClose();return}
    const b=e.target.closest?.('#coinLightbox [data-lb]');
    if(b){e.preventDefault();e.stopPropagation();act(b.dataset.lb);return}
    const d=dlg(); if(d && e.target===d){e.preventDefault();safeClose()}
  },true);
  document.addEventListener('keydown',function(e){
    const d=dlg(); if(!d?.open)return;
    if(e.key==='Escape'){e.preventDefault();safeClose()}
    else if(e.key==='ArrowLeft')act('prev');
    else if(e.key==='ArrowRight')act('next');
    else if(e.key==='+'||e.key==='=')act('zin');
    else if(e.key==='-')act('zout');
  },true);
  document.addEventListener('fullscreenchange',()=>{ try{lbDraw()}catch(_){ } });
  window.__closeAdminLightbox=safeClose;
})();
'''
    a += inject
    APP.write_text(a,encoding='utf-8')

s=STYLE.read_text(encoding='utf-8')
cssmark='/* admin-lightbox-controls-v2 */'
if cssmark not in s:
    s += r'''

/* admin-lightbox-controls-v2 */
.coin-lightbox{position:relative!important}
.lightbox-close{
  position:absolute!important;top:10px!important;right:10px!important;left:auto!important;
  z-index:50!important;width:46px!important;height:46px!important;min-width:46px!important;
  display:grid!important;place-items:center!important;padding:0!important;border-radius:999px!important;
  background:#8f2530!important;color:#fff!important;border:2px solid #fff8!important;
  font-size:30px!important;line-height:1!important;cursor:pointer!important;pointer-events:auto!important;
  box-shadow:0 4px 18px #0008!important
}
.lightbox-toolbar{padding-right:64px!important;pointer-events:auto!important;z-index:20!important}
.lightbox-toolbar button{pointer-events:auto!important;cursor:pointer!important;min-height:42px!important}
.coin-lightbox::backdrop{background:#000c}
html.lightbox-open,body.lightbox-open{overflow:hidden!important}
@media(max-width:700px){
 .lightbox-close{position:fixed!important;top:8px!important;right:8px!important}
 .lightbox-toolbar{padding-right:62px!important}
}
'''
    STYLE.write_text(s,encoding='utf-8')

p=INDEX.read_text(encoding='utf-8')
# Cache bust both admin assets so the fixed controls reach the browser immediately.
p=p.replace('/admin/styles.css?v=5.6.2-r4-lightbox1','/admin/styles.css?v=5.6.2-r4-lightbox2')
p=p.replace('/admin/app.js?v=5.6.2-r9.5a-lightbox1','/admin/app.js?v=5.6.2-r9.5a-lightbox2')
INDEX.write_text(p,encoding='utf-8')

print('Admin lightbox controls v2 applied.')
