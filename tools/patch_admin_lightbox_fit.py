from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STYLE=ROOT/'admin'/'styles.css'
INDEX=ROOT/'admin'/'index.html'
APP=ROOT/'admin'/'app.js'

# ---- styles: make the lightbox a true viewport with a flexible stage ----
s=STYLE.read_text(encoding='utf-8')
marker='/* admin-lightbox-fit-v1 */'
if marker not in s:
    s += r'''

/* admin-lightbox-fit-v1 */
.coin-lightbox{
  width:min(1280px,98vw)!important;
  height:94vh!important;
  max-height:94vh!important;
  padding:0!important;
  overflow:hidden!important;
  display:flex!important;
  flex-direction:column!important;
}
.coin-lightbox[open]{display:flex!important}
.lightbox-toolbar{
  flex:0 0 auto;
  position:relative;
  z-index:3;
  overflow-x:auto;
  overflow-y:hidden;
  flex-wrap:nowrap!important;
  scrollbar-width:thin;
}
.lightbox-stage{
  flex:1 1 auto!important;
  min-height:0!important;
  height:auto!important;
  width:100%!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  overflow:hidden!important;
  position:relative!important;
  touch-action:none!important;
  cursor:grab;
}
.lightbox-stage:active{cursor:grabbing}
.lightbox-stage img,
#coinLightboxImg{
  width:auto!important;
  height:auto!important;
  max-width:94%!important;
  max-height:94%!important;
  object-fit:contain!important;
  object-position:center!important;
  margin:auto!important;
  transform-origin:center center!important;
  user-select:none!important;
  -webkit-user-drag:none!important;
  pointer-events:none!important;
}
.lightbox-caption{flex:0 0 auto;min-height:32px}
@media(max-width:700px){
  .coin-lightbox{width:100vw!important;height:100dvh!important;max-height:100dvh!important;border-radius:0!important}
  .lightbox-toolbar{padding-inline:44px 8px!important}
  .lightbox-toolbar button{white-space:nowrap!important;flex:0 0 auto!important}
  .lightbox-stage img,#coinLightboxImg{max-width:98%!important;max-height:98%!important}
}
'''
    STYLE.write_text(s,encoding='utf-8')

# ---- index: add explicit fit-to-screen control if missing ----
p=INDEX.read_text(encoding='utf-8')
if 'data-lb="fit"' not in p:
    target='''><button type="button" data-lb="center">◎ توسيط</button\n        ><button type="button" data-lb="reset">100%</button'''
    repl='''><button type="button" data-lb="center">◎ توسيط</button\n        ><button type="button" data-lb="fit">⊙ إظهار كامل</button\n        ><button type="button" data-lb="reset">100%</button'''
    if target not in p:
        raise RuntimeError('lightbox toolbar target not found')
    p=p.replace(target,repl,1)
    # bust caches for admin assets
    p=p.replace('/admin/styles.css?v=5.6.2-r4','/admin/styles.css?v=5.6.2-r4-lightbox1',1)
    p=p.replace('/admin/app.js?v=5.6.2-r9.5a','/admin/app.js?v=5.6.2-r9.5a-lightbox1',1)
    INDEX.write_text(p,encoding='utf-8')

# ---- app: explicit fit command + image-load redraw ----
a=APP.read_text(encoding='utf-8')
fit_marker='// admin-lightbox-fit-v1'
if fit_marker not in a:
    old='''      if (a === "center") {\n        LB.x = LB.y = 0;\n      }\n      if (a === "reset") {'''
    new='''      if (a === "center") {\n        LB.x = LB.y = 0;\n      }\n      // admin-lightbox-fit-v1: the CSS base size is already contain-fit; reset transform to show the whole image.\n      if (a === "fit") {\n        LB.scale = 1;\n        LB.rot = 0;\n        LB.x = LB.y = 0;\n      }\n      if (a === "reset") {'''
    if old not in a:
        raise RuntimeError('lightbox command block not found')
    a=a.replace(old,new,1)

    old2='''  $("coinLightboxImg").src = LB.imgs[LB.idx];\n  $("coinLightboxCaption").textContent ='''
    new2='''  const lbImg=$("coinLightboxImg");\n  lbImg.onload=()=>{ LB.scale=1; LB.rot=0; LB.x=LB.y=0; lbDraw(); };\n  lbImg.src = LB.imgs[LB.idx];\n  $("coinLightboxCaption").textContent ='''
    if old2 not in a:
        raise RuntimeError('lightbox open image assignment not found')
    a=a.replace(old2,new2,1)
    APP.write_text(a,encoding='utf-8')

print('Admin lightbox fit patch applied.')
