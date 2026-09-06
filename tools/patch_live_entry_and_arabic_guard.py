from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# 1) Shared exact-token Arabic UI guard. It never translates substrings or proper names.
guard=ROOT/'public'/'arabic_ui_guard.js'
guard.write_text(r'''(()=>{
'use strict';
const EXACT={
  'Dashboard':'لوحة التحكم','Home':'الرئيسية','Settings':'الإعدادات','Orders':'الطلبات','Finance':'المالية',
  'Market':'السوق العام','Auction':'المزاد','Auctions':'المزادات','Warehouse':'المستودع','Archive':'الأرشيف',
  'Notifications':'الإشعارات','Approvals':'الاعتمادات','Permissions':'الصلاحيات','Participants':'المشاركون',
  'Pending':'بانتظار الاعتماد','Approved':'معتمد','Rejected':'مرفوض','Paid':'مسدد','Unpaid':'غير مسدد',
  'Cancelled':'ملغي','Refunded':'مسترد','Ready to ship':'جاهز للشحن','Shipped':'تم الشحن','Delivered':'تم الاستلام',
  'Live':'مباشر','Scheduled':'مجدول','Ended':'منتهي','Close':'إغلاق','Save':'حفظ','Edit':'تعديل','Delete':'حذف',
  'Back':'رجوع','Next':'التالي','Previous':'السابق','Search':'بحث','All':'الكل','Open':'فتح'
};
const attrs=['title','placeholder','aria-label'];
function translateExact(s){const t=String(s??'').trim();return EXACT[t]||null}
function normalizeElement(el){
  if(!el||el.nodeType!==1)return;
  for(const a of attrs){if(el.hasAttribute?.(a)){const v=translateExact(el.getAttribute(a));if(v)el.setAttribute(a,v)}}
  for(const n of el.childNodes||[]){if(n.nodeType===3){const raw=n.nodeValue||'',v=translateExact(raw);if(v)n.nodeValue=raw.replace(raw.trim(),v)}}
}
function sweep(root=document){
  document.documentElement.lang='ar';document.documentElement.dir='rtl';
  if(document.body)document.body.dir='rtl';
  if(root.nodeType===1)normalizeElement(root);
  root.querySelectorAll?.('*').forEach(normalizeElement);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>sweep());else sweep();
new MutationObserver(ms=>{for(const m of ms){for(const n of m.addedNodes||[]){if(n.nodeType===1)sweep(n);else if(n.nodeType===3){const v=translateExact(n.nodeValue);if(v)n.nodeValue=v}}}}).observe(document.documentElement,{subtree:true,childList:true});
})();
''',encoding='utf-8')

# 2) Inject the guard into every admin HTML page. Static Arabic remains the source of truth.
for p in (ROOT/'admin').glob('*.html'):
    s=p.read_text(encoding='utf-8')
    tag='<script src="/arabic_ui_guard.js?v=1" defer></script>'
    if tag not in s:
        s=s.replace('</head>',tag+'\n</head>',1)
        p.write_text(s,encoding='utf-8')

# 3) Public live-entry widget: always visible, pulses only while a session is live.
LIVE_CSS=r'''
.live-entry{display:inline-flex;align-items:center;gap:8px;color:#fff!important;text-decoration:none!important;border:1px solid #ffffff38!important;border-radius:999px!important;padding:9px 13px!important;background:#ffffff0c!important;font-weight:900!important;position:relative}
.live-entry .live-dot{width:10px;height:10px;border-radius:50%;background:#8b93a1;box-shadow:0 0 0 0 transparent;flex:0 0 auto}
.live-entry.live-active{background:linear-gradient(135deg,#8c1525,#d6293d)!important;border-color:#ff6d7e!important;box-shadow:0 0 0 1px #ff829055,0 0 24px #d6293d66}
.live-entry.live-active .live-dot{background:#ff263f;animation:livePulse 1.05s infinite}
@keyframes livePulse{0%{box-shadow:0 0 0 0 #ff263f99}70%{box-shadow:0 0 0 10px #ff263f00}100%{box-shadow:0 0 0 0 #ff263f00}}
'''
LIVE_SCRIPT=r'''
<script>
(()=>{const el=document.getElementById('globalLiveEntry');if(!el)return;const text=el.querySelector('.live-text');async function refresh(){try{const r=await fetch('/api/public/live-auctions',{cache:'no-store'});const d=await r.json();const live=(d.sessions||[]).find(s=>String(s.status)==='live');if(live){el.classList.add('live-active');el.href='/live-auction?session='+encodeURIComponent(live.id);if(text)text.textContent='بث مباشر الآن';el.setAttribute('aria-label','البث المباشر يعمل الآن — اضغط للدخول')}else{el.classList.remove('live-active');el.href='/live-auction';if(text)text.textContent='بث مباشر';el.setAttribute('aria-label','الدخول إلى صفحة البث المباشر')}}catch(_){el.classList.remove('live-active');el.href='/live-auction';if(text)text.textContent='بث مباشر'}}refresh();setInterval(refresh,5000)})();
</script>
'''
ANCHOR='<a id="globalLiveEntry" class="live-entry" href="/live-auction"><span class="live-dot" aria-hidden="true"></span><span class="live-text">بث مباشر</span></a>'

def patch_home(path, nav_marker):
    p=ROOT/path
    s=p.read_text(encoding='utf-8')
    if '.live-entry{' not in s:
        s=s.replace('</style>',LIVE_CSS+'\n</style>',1)
    if 'id="globalLiveEntry"' not in s:
        s=s.replace(nav_marker,nav_marker+'\n'+ANCHOR,1)
    if "'/api/public/live-auctions'" not in s and 'globalLiveEntry' in s:
        s=s.replace('</body>',LIVE_SCRIPT+'\n</body>',1)
    p.write_text(s,encoding='utf-8')

patch_home(Path('public/dar_home.html'),'<a href="/account">حسابي</a>')
patch_home(Path('public/public_home.html'),'<a href="/account">حسابي</a>')
patch_home(Path('public/collectibles_home.html'),'<a href="/account?store=collectibles">حسابي</a>')

# 4) CI-readable marker for the Arabic-first contract.
contract=ROOT/'ARABIC_UI_POLICY.md'
contract.write_text('''# سياسة الواجهة العربية\n\n- اللغة العربية هي المصدر الأساسي لكل نصوص الواجهة.\n- يمنع استخدام مترجم شامل يستبدل أجزاء الكلمات أو الأسماء التجارية.\n- يسمح فقط بتحويل الرموز والحالات الإنجليزية المعروفة بتحويل مطابق كامل Exact Match.\n- جميع صفحات الإدارة يجب أن تحمل `lang="ar"` و`dir="rtl"` و`meta charset="utf-8"`.\n- الأسماء الفنية مثل IBAN وLiveKit وأرقام الطلبات لا تُترجم.\n''',encoding='utf-8')
print('patched public live entry + Arabic UI guard')
