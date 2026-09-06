from pathlib import Path


def rep(path, old, new, label):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'missing pattern: {label}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

# 1) Server: keep winning result visible until admin clears it, block new lot/end, enrich order/result notifications.
rep('server.py',
"""            if action=='delete':
                sessions=[x for x in sessions if str(x.get('id'))!=sid]; save_json(LIVE_AUCTIONS,{'sessions':sessions}); self.sendj({'ok':True}); return
            if action in ('start','end','cancel'):
""",
"""            if action=='delete':
                sessions=[x for x in sessions if str(x.get('id'))!=sid]; save_json(LIVE_AUCTIONS,{'sessions':sessions}); self.sendj({'ok':True}); return
            pending_result=row.get('lastResult') if isinstance(row.get('lastResult'),dict) else None
            result_waiting=bool(pending_result and pending_result.get('sold') and not pending_result.get('clearedAt'))
            if action=='clear-result':
                if not pending_result: self.sendj({'error':'لا توجد نتيجة مزاد معلقة'},409); return
                pending_result['clearedAt']=datetime.datetime.now().isoformat(); pending_result['clearedBy']='admin'; row['lastResult']=pending_result
                row['updated']=datetime.datetime.now().isoformat(); save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('إقفال بطاقة فائز المزاد المباشر',{'sessionId':sid,'orderId':pending_result.get('orderId')}); self.sendj({'ok':True,'session':with_live_timer(row)}); return
            if action in ('open-item','open-free-lot') and result_waiting:
                self.sendj({'error':'أقفل بطاقة الفائز السابقة من سلة المزادات المباشرة قبل بدء مزايدة جديدة'},409); return
            if action in ('end','cancel') and result_waiting:
                self.sendj({'error':'لا يمكن إنهاء الجلسة قبل إقفال بطاقة الفائز من سلة المزادات المباشرة'},409); return
            if action in ('start','end','cancel'):
""",'admin live result guard')

rep('server.py',
"""            orders=load_orders(); orders.append(order); save_json(ORDERS,{'orders':orders}); hist['orderId']=order['id']
            # ثبّت نتيجة المزاد على سجل المقتنى حتى يظهر البيع في الإدارة والسلة ولا تضيع النتيجة بعد إعادة التشغيل.
""",
"""            orders=load_orders(); orders.append(order); apply_flat_shipping_for_participant(orders,winner_id); save_json(ORDERS,{'orders':orders}); hist['orderId']=order['id']
            order=next((o for o in orders if str(o.get('id'))==str(order.get('id'))),order)
            hist.update({'itemTitle':item_title(item),'itemImage':item.get('frontImg') or item.get('backImg') or '', 'winnerName':person.get('name') or row.get('latestBidderName') or 'الفائز', 'orderNumber':order.get('orderNumber') or order.get('id'), 'shippingFee':float(order.get('shippingFee') or 0), 'total':float(order.get('total') or 0), 'ownerName':item.get('ownerName') or item.get('sellerName') or item.get('owner') or 'دار المقتنيات'})
            # ثبّت نتيجة المزاد على سجل المقتنى حتى يظهر البيع في الإدارة والسلة ولا تضيع النتيجة بعد إعادة التشغيل.
""",'enrich live result')

rep('server.py',
"""            add_notification('participant',winner_id,'orders','🏆 فوز في المزاد المباشر',f\"تم إنشاء طلب بقيمة {float(row.get('currentPrice') or 0):g} ر.س للمقتنى {item_title(item)}.\",closed_item,'/account')
            add_notification('admin','','auction','🏆 تم إرساء مزاد مباشر',f\"فاز {person.get('name') or 'مشارك'} بالمقتنى {item_title(item)} بقيمة {float(row.get('currentPrice') or 0):g} ر.س وتم إنشاء طلب المبيعات تلقائيًا.\",closed_item,'/admin')
""",
"""            ship=float(order.get('shippingFee') or 0); total=float(order.get('total') or 0); win=float(row.get('currentPrice') or 0)
            add_notification('participant',winner_id,'orders','🎉 مبروك الفوز بالمزاد المباشر',f\"فزت بالمقتنى {item_title(item)} بسعر {win:g} ر.س. الشحن {ship:g} ر.س، وإجمالي الطلب {total:g} ر.س. تم إنشاء الطلب {order.get('orderNumber') or order.get('id')}.\",closed_item,'/account')
            seller_id=str(item.get('ownerParticipantId') or item.get('sellerParticipantId') or item.get('participantId') or '')
            if seller_id and seller_id!=winner_id:
                add_notification('participant',seller_id,'auction','🏆 تم بيع مقتناك في المزاد المباشر',f\"تم إرساء {item_title(item)} على {person.get('name') or 'الفائز'} بسعر {win:g} ر.س.\",closed_item,'/account')
            add_notification('admin','','auction','🏆 تم إرساء مزاد مباشر',f\"فاز {person.get('name') or 'مشارك'} بالمقتنى {item_title(item)} بقيمة {win:g} ر.س. الشحن {ship:g} ر.س، والإجمالي {total:g} ر.س. الطلب {order.get('orderNumber') or order.get('id')} بانتظار المتابعة.\",closed_item,'/admin')
""",'live winner notifications')

# 2) Admin: add live-auction basket and clear button.
rep('admin/index.html',
"""<div id=\"liveSessions\" class=\"participants-list\"></div></div></section>""",
"""<div id=\"liveResultsBasket\" class=\"panel\" style=\"margin-top:14px\"><h3>🧺 سلة المزادات المباشرة</h3><p class=\"muted\">نتائج الفوز تبقى هنا وفي واجهة المشاهدين حتى تعتمد الإدارة إقفالها.</p><div id=\"liveResultsList\" class=\"participants-list\"></div></div><div id=\"liveSessions\" class=\"participants-list\"></div></div></section>""",'admin live basket html')

rep('admin/app.js',
""" const [lr,allItems,media]=await Promise.all([api('/api/live-auctions/admin'),all(),api('/api/live-media/status').catch(()=>({configured:false}))]);
""",
""" const [lr,allItems,media,or]=await Promise.all([api('/api/live-auctions/admin'),all(),api('/api/live-media/status').catch(()=>({configured:false})),api('/api/orders').catch(()=>({orders:[]}))]);
""",'load live orders')

rep('admin/app.js',
""" const sessions=lr.sessions||[], active=sessions.filter(s=>['scheduled','live'].includes(s.status)), archived=sessions.filter(s=>!['scheduled','live'].includes(s.status)).sort((a,b)=>String(b.endedAt||b.updated||'').localeCompare(String(a.endedAt||a.updated||'')));
""",
""" const sessions=lr.sessions||[], active=sessions.filter(s=>['scheduled','live'].includes(s.status)), archived=sessions.filter(s=>!['scheduled','live'].includes(s.status)).sort((a,b)=>String(b.endedAt||b.updated||'').localeCompare(String(a.endedAt||a.updated||'')));
 const orders=or.orders||[], orderMap=new Map(orders.map(o=>[String(o.id||''),o]));
 const pendingResults=sessions.map(s=>({s,r:s.lastResult})).filter(x=>x.r&&x.r.sold&&!x.r.clearedAt);
 const rb=$('liveResultsList'); if(rb) rb.innerHTML=pendingResults.map(({s,r})=>{const it=items.find(i=>String(i.id)===String(r.itemId||''))||{},o=orderMap.get(String(r.orderId||''))||{};const img=r.itemImage||it.frontImg||it.backImg||'';const ship=Number(o.shippingFee??r.shippingFee??0),total=Number(o.total??r.total??r.price??0);return `<article class=\"participant-card live-winner-admin-card\">${img?`<img src=\"${esc(img)}\" alt=\"\" style=\"width:110px;height:90px;object-fit:contain;border-radius:10px;background:#fff\">`:''}<h3>🏆 ${esc(r.itemTitle||item_title(it)||'مقتنى مزاد مباشر')}</h3><p><b>الفائز:</b> ${esc(r.winnerName||r.bidderName||'—')} <small>${esc(r.participantId||'')}</small></p><p><b>سعر الفوز:</b> ${Number(r.price||0).toLocaleString('ar-SA')} ر.س — <b>الشحن:</b> ${ship.toLocaleString('ar-SA')} ر.س — <b>الإجمالي:</b> ${total.toLocaleString('ar-SA')} ر.س</p><p><b>صاحب القطعة:</b> ${esc(r.ownerName||it.ownerName||it.sellerName||'دار المقتنيات')} — <b>الطلب:</b> ${esc(o.orderNumber||r.orderNumber||r.orderId||'—')}</p><div class=\"actions\"><button class=\"gold-action\" onclick=\"liveControl('${s.id}','clear-result')\">اعتماد وإقفال بطاقة الفوز</button><a class=\"public-link\" href=\"/live-auction?session=${encodeURIComponent(s.id)}\" target=\"_blank\">معاينة ما يراه الزائر</a></div></article>`}).join('')||'<p class=\"muted\">لا توجد نتائج فوز معلقة حاليًا.</p>';
""",'render live basket')

# 3) Public viewer: persistent winner card + gold confetti until admin closes it.
rep('public/live_auction.js',
"""function renderActive(){const s=active();if(!s)return;$('viewerTitle').textContent=(s.status==='live'?'🔴 ':'')+(s.title||'بث مباشر');const info=currentInfo(s),step=Math.max(1,Number(s.bidStep||1)),price=Number(s.currentPrice||0),minimum=price>0?price+step:step;$('stripPrice').textContent=price.toLocaleString('ar-SA')+' ر.س';$('stripStep').textContent=step.toLocaleString('ar-SA')+' ر.س';$('stripBidder').textContent=s.latestBidderName||'لا يوجد';renderChat(s);renderMarket(s);if(!info.title){$('bidPanel').innerHTML='<h3>بانتظار فتح القطعة التالية</h3><p class=\"muted\">تستطيع متابعة البث والتعليقات حتى يفتح المذيع المزايدة.</p>';return}""",
"""function launchGoldConfetti(key){if(!key||window.__lastGoldConfetti===key)return;window.__lastGoldConfetti=key;const wrap=document.createElement('div');wrap.className='gold-confetti';for(let i=0;i<55;i++){const p=document.createElement('i');p.style.left=(Math.random()*100)+'vw';p.style.animationDelay=(Math.random()*1.2)+'s';p.style.animationDuration=(2.4+Math.random()*2)+'s';wrap.appendChild(p)}document.body.appendChild(wrap);setTimeout(()=>wrap.remove(),5200)}
function winnerResultHtml(s){const r=s?.lastResult;if(!r||!r.sold||r.clearedAt)return'';launchGoldConfetti(String(r.closedAt||r.orderId||r.itemId));const ship=Number(r.shippingFee||0),total=Number(r.total||r.price||0);return `<div class=\"winner-card\">${r.itemImage?`<img src=\"${esc(r.itemImage)}\" alt=\"صورة المقتنى الفائز\">`:''}<div><div class=\"winner-crown\">🏆 تم الفوز بالمزاد</div><h3>${esc(r.itemTitle||'مقتنى المزاد المباشر')}</h3><p>الفائز: <b>${esc(r.winnerName||r.bidderName||'الفائز')}</b></p><p>سعر الفوز: <b>${Number(r.price||0).toLocaleString('ar-SA')} ر.س</b></p><p>الشحن: <b>${ship.toLocaleString('ar-SA')} ر.س</b> — الإجمالي: <b>${total.toLocaleString('ar-SA')} ر.س</b></p><p>صاحب القطعة: <b>${esc(r.ownerName||'دار المقتنيات')}</b></p><small>تبقى هذه النتيجة معروضة حتى تعتمد الإدارة إقفالها ثم تبدأ المزايدة التالية.</small></div></div>`}
function renderActive(){const s=active();if(!s)return;$('viewerTitle').textContent=(s.status==='live'?'🔴 ':'')+(s.title||'بث مباشر');const info=currentInfo(s),step=Math.max(1,Number(s.bidStep||1)),price=Number(s.currentPrice||0),minimum=price>0?price+step:step;$('stripPrice').textContent=price.toLocaleString('ar-SA')+' ر.س';$('stripStep').textContent=step.toLocaleString('ar-SA')+' ر.س';$('stripBidder').textContent=s.latestBidderName||'لا يوجد';renderChat(s);renderMarket(s);if(!info.title){const win=winnerResultHtml(s);$('bidPanel').innerHTML=win||'<h3>بانتظار فتح القطعة التالية</h3><p class=\"muted\">تستطيع متابعة البث والتعليقات حتى يفتح المذيع المزايدة.</p>';return}""",'public winner card')

rep('public/live_auction.html',
""".close{border:0;background:#edf1f6;border-radius:9px;padding:8px 12px;font-weight:900}""",
""".winner-card{display:grid;grid-template-columns:120px 1fr;gap:12px;align-items:center;border:2px solid #d5a531;background:linear-gradient(145deg,#fffaf0,#fff1c7);border-radius:16px;padding:14px}.winner-card img{width:120px;height:105px;object-fit:contain;background:#fff;border-radius:12px}.winner-crown{font-weight:1000;color:#8c5b08;font-size:1.15rem}.winner-card h3{margin:.35rem 0;color:#0b3260}.winner-card p{margin:.3rem 0}.gold-confetti{position:fixed;inset:0;z-index:99999;pointer-events:none;overflow:hidden}.gold-confetti i{position:absolute;top:-20px;width:10px;height:16px;background:#d7a52f;transform:rotate(15deg);animation:goldFall 3.2s linear forwards}.gold-confetti i:nth-child(3n){background:#f1cf69;width:7px;height:12px}.gold-confetti i:nth-child(4n){background:#b88627}@keyframes goldFall{to{transform:translateY(110vh) rotate(720deg);opacity:.9}}.close{border:0;background:#edf1f6;border-radius:9px;padding:8px 12px;font-weight:900}""",'winner css')

print('live auction winner flow v1 applied')
