from pathlib import Path

studio = Path('public/live_studio.html')
auction = Path('public/live_auction.js')

s = studio.read_text(encoding='utf-8')
s = s.replace('معاينة زر المزايدة للمشاهدين', 'ادخل المزاد')
s = s.replace('<div id="studioBidPreviewButton" class="bid-preview-button"><span>🔨 زايد الآن</span><strong id="studioBidPreviewValue">—</strong></div>', '<button id="studioBidPreviewButton" class="bid-preview-button" type="button"><span>المزايدة</span><strong id="studioBidPreviewValue">—</strong></button>')
s = s.replace('.bid-preview-button{width:min(190px,100%);min-height:92px;margin:10px auto 0;border-radius:15px;background:#c78b2d;color:#fff;display:flex;', '.bid-preview-button{width:min(190px,100%);min-height:92px;margin:10px auto 0;border:0;border-radius:15px;background:#c78b2d;color:#fff;display:flex;cursor:pointer;')
s = s.replace("const box=document.getElementById('createSessionBox'),toggle=document.getElementById('mobileSessionToggle');", "const box=document.getElementById('createSessionBox'),toggle=document.getElementById('mobileSessionToggle'),bidEntry=document.getElementById('studioBidPreviewButton');")
s = s.replace("if(toggle&&box){toggle.addEventListener('click',()=>{box.hidden=false;box.classList.add('mobile-open');box.querySelectorAll('input,button,select,textarea').forEach(el=>el.disabled=false);box.scrollIntoView({behavior:'smooth',block:'center'});});}", "if(toggle&&box){toggle.addEventListener('click',()=>{box.hidden=false;box.classList.add('mobile-open');box.querySelectorAll('input,button,select,textarea').forEach(el=>el.disabled=false);box.scrollIntoView({behavior:'smooth',block:'center'});});}\n  if(bidEntry){bidEntry.disabled=false;bidEntry.addEventListener('click',()=>{const s=window.__liveStudioSession||null;const id=s?.id||new URLSearchParams(location.search).get('session')||'';if(!id){alert('اختر جلسة مزاد أولًا');return}window.open('/live-auction?session='+encodeURIComponent(id),'_blank','noopener');});}")
s = s.replace('هذه معاينة داخل الاستوديو فقط. المزايدة الفعلية تتم من واجهة المشاهدين.', 'اضغط زر المزايدة للدخول إلى واجهة المزاد للمشاهدين واختبار المزايدة الفعلية.')
s = s.replace('الزر يعرض دائمًا السعر التالي فقط: السعر الحالي + قيمة الزيادة.', 'السعر الظاهر هو المزايدة التالية: السعر الحالي + قيمة الزيادة.')
# bust studio cache
s = s.replace('/live_studio.js?v=5.4.8', '/live_studio.js?v=5.4.9')
studio.write_text(s, encoding='utf-8')

a = auction.read_text(encoding='utf-8')
a = a.replace('<span>🔨 زايد الآن</span><strong>${minimum.toLocaleString(\'ar-SA\')} ر.س</strong>', '<span>المزايدة</span><strong>${minimum.toLocaleString(\'ar-SA\')} ر.س</strong>')
a = a.replace("btn.innerHTML='<span>جارٍ تسجيل المزايدة…</span><strong>'+bidAmount.toLocaleString('ar-SA')+' ر.س</strong>'", "btn.innerHTML='<span>جارٍ تسجيل المزايدة…</span><strong>'+bidAmount.toLocaleString('ar-SA')+' ر.س</strong>'")
auction.write_text(a, encoding='utf-8')

html = Path('public/live_auction.html')
h = html.read_text(encoding='utf-8')
h = h.replace('/live_auction.js?v=5.4.6', '/live_auction.js?v=5.4.9')
html.write_text(h, encoding='utf-8')

print('patched live bid entry button')
