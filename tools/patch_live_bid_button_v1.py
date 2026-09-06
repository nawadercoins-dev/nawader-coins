from pathlib import Path
import re

auction_html = Path('public/live_auction.html')
auction_js = Path('public/live_auction.js')
studio_html = Path('public/live_studio.html')

# 1) Viewer: replace the long slider UI with one compact next-bid button.
s = auction_html.read_text(encoding='utf-8')
s = re.sub(
    r"\.bid-slider-card\{.*?\.quick-bids button\{.*?\}",
    ".next-bid-card{margin-top:12px;padding:12px;border:1px solid #e2c36f;border-radius:14px;background:#fff8e8;text-align:center}.next-bid-label{font-weight:900;color:#6d5a35;margin-bottom:8px}.next-bid-button{width:min(190px,100%);min-height:96px;border:0;border-radius:16px;background:#c78b2d;color:#fff;display:inline-flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;font-weight:1000;cursor:pointer;box-shadow:0 7px 18px #9c6d222f}.next-bid-button span{font-size:.92rem}.next-bid-button strong{font-size:1.55rem;line-height:1}.next-bid-button:disabled{opacity:.65;cursor:wait}.next-bid-note{font-size:.86rem;color:#6d5a35;margin-top:8px}",
    s,
    count=1,
    flags=re.S,
)
s = s.replace('.bid-row{grid-template-columns:1fr}.bid-row button{min-height:48px}.quick-bids{grid-template-columns:repeat(3,1fr)}', '.next-bid-button{width:min(210px,100%);min-height:104px}')
s = s.replace('/live_auction.js?v=5.4.6', '/live_auction.js?v=5.4.8')
auction_html.write_text(s, encoding='utf-8')

# 2) Viewer logic: next amount = current price + fixed step, one click submits exactly that amount.
s = auction_js.read_text(encoding='utf-8')
new_render = r'''function renderActive(){const s=active();if(!s)return;$('viewerTitle').textContent=(s.status==='live'?'🔴 ':'')+(s.title||'بث مباشر');const info=currentInfo(s),step=Math.max(1,Number(s.bidStep||1)),price=Number(s.currentPrice||0),minimum=price>0?price+step:step;$('stripPrice').textContent=price.toLocaleString('ar-SA')+' ر.س';$('stripStep').textContent=step.toLocaleString('ar-SA')+' ر.س';$('stripBidder').textContent=s.latestBidderName||'لا يوجد';renderChat(s);renderMarket(s);if(!info.title){$('bidPanel').innerHTML='<h3>بانتظار فتح القطعة التالية</h3><p class="muted">تستطيع متابعة البث والتعليقات حتى يفتح المذيع المزايدة.</p>';return}$('bidPanel').innerHTML=`${info.image?`<img class="lot-image" src="${esc(info.image)}" alt="صورة القطعة">`:''}<h3>${esc(info.title)}</h3><div class="live-price">${price.toLocaleString('ar-SA')} ر.س</div><p>قيمة الزيادة: <b>${step.toLocaleString('ar-SA')} ر.س</b></p><p>آخر مزايد: <b>${esc(s.latestBidderName||'لا يوجد بعد')}</b></p><div class="countdown" id="liveCountdown"></div><div class="next-bid-card"><div class="next-bid-label">المزايدة التالية</div><button id="nextBidButton" class="next-bid-button" type="button" onclick="submitBid(${minimum})"><span>🔨 زايد الآن</span><strong>${minimum.toLocaleString('ar-SA')} ر.س</strong></button><div class="next-bid-note">بالضغط ينتقل السعر مباشرة إلى ${minimum.toLocaleString('ar-SA')} ر.س. الزيادة ثابتة: ${step.toLocaleString('ar-SA')} ر.س.</div></div><div id="bidMsg" class="muted">المزايدة متاحة للحساب الموثق بالكامل. إذا لم تكن مسجلًا سيحوّلك النظام إلى حسابك ثم يعيدك لنفس الجلسة.</div><div class="activity"><b>آخر المزايدات</b>${(s.bids||[]).slice(-12).reverse().map(b=>`<div class="activity-item">🔨 ${esc(b.bidderName)} — ${Number(b.amount||0).toLocaleString('ar-SA')} ر.س</div>`).join('')||'<div class="activity-item">لا توجد مزايدات بعد</div>'}</div>`;updateCountdown()}
function updateCountdown'''
s, n = re.subn(r"function setBidAmount[\s\S]*?function updateCountdown", new_render, s, count=1)
if n != 1:
    raise SystemExit('Could not replace slider render block')

s, n = re.subn(
    r"async function submitBid\(\)\{.*?\}\nfunction renderMarket",
    "async function submitBid(amount){const bidAmount=Number(amount||0),msg=$('bidMsg'),btn=$('nextBidButton');try{if(!bidAmount)throw Error('قيمة المزايدة غير صالحة');if(btn){btn.disabled=true;btn.innerHTML='<span>جارٍ تسجيل المزايدة…</span><strong>'+bidAmount.toLocaleString('ar-SA')+' ر.س</strong>'}await j('/api/live-auctions/bid',{method:'POST',body:JSON.stringify({id:activeId,amount:bidAmount})});msg.textContent='✓ تم تسجيل مزايدتك بنجاح.';await load()}catch(e){if(e.status===401){location.href='/account?next='+encodeURIComponent('/live-auction?session='+activeId);return}msg.textContent=e.message||'تعذر تسجيل المزايدة'}finally{if(btn)btn.disabled=false}}\nfunction renderMarket",
    s,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit('Could not replace submitBid')

s = s.replace('window.watchSession=watchSession;window.submitBid=submitBid;window.setBidAmount=setBidAmount;window.bidPlus=bidPlus;', 'window.watchSession=watchSession;window.submitBid=submitBid;')
auction_js.write_text(s, encoding='utf-8')

# 3) Studio: preview the same compact button concept, not a slider.
s = studio_html.read_text(encoding='utf-8')
s = s.replace('.bid-preview input[type=range]{width:100%;accent-color:#c78b2d}', '.bid-preview-button{width:min(190px,100%);min-height:92px;margin:10px auto 0;border-radius:15px;background:#c78b2d;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;font-weight:1000}.bid-preview-button strong{font-size:1.45rem}')
s = s.replace('<div id="studioBidPreview" class="bid-preview" hidden><div class="bid-preview-head"><b>معاينة شريط المزايدة للمشاهدين</b><strong id="studioBidPreviewValue">—</strong></div><input id="studioBidPreviewRange" type="range" min="0" max="100" value="0" disabled><div class="bid-preview-note">هذه معاينة داخل الاستوديو فقط. المزايدة الفعلية تتم من واجهة المشاهدين.</div></div>', '<div id="studioBidPreview" class="bid-preview" hidden><div class="bid-preview-head"><b>معاينة زر المزايدة للمشاهدين</b></div><div id="studioBidPreviewButton" class="bid-preview-button"><span>🔨 زايد الآن</span><strong id="studioBidPreviewValue">—</strong></div><div class="bid-preview-note">الزر يعرض دائمًا السعر التالي فقط: السعر الحالي + قيمة الزيادة.</div></div>')
s = s.replace("const p=document.getElementById('studioBidPreview'),r=document.getElementById('studioBidPreviewRange'),v=document.getElementById('studioBidPreviewValue');if(!p||!r||!v)return;", "const p=document.getElementById('studioBidPreview'),v=document.getElementById('studioBidPreviewValue');if(!p||!v)return;")
s = s.replace("const step=Math.max(1,Number(s?.bidStep||1)),price=Number(s?.currentPrice||0),min=price>0?price+step:step,max=min+(step*20);p.hidden=false;r.min=min;r.max=max;r.step=step;r.value=min;v.textContent=min.toLocaleString('ar-SA')+' ر.س';", "const step=Math.max(1,Number(s?.bidStep||1)),price=Number(s?.currentPrice||0),min=price>0?price+step:step;p.hidden=false;v.textContent=min.toLocaleString('ar-SA')+' ر.س';")
s = s.replace('/live_studio.js?v=5.4.7', '/live_studio.js?v=5.4.8')
studio_html.write_text(s, encoding='utf-8')

# Hard checks.
viewer_html = auction_html.read_text(encoding='utf-8')
viewer_js = auction_js.read_text(encoding='utf-8')
studio = studio_html.read_text(encoding='utf-8')
assert 'liveBidSlider' not in viewer_js
assert 'type="range"' not in viewer_js
assert 'nextBidButton' in viewer_js
assert 'المزايدة التالية' in viewer_js
assert 'studioBidPreviewRange' not in studio
assert 'معاينة زر المزايدة' in studio
print('live bid button patch applied')
