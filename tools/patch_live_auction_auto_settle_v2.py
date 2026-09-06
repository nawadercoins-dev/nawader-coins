from pathlib import Path

server=Path('server.py')
text=server.read_text(encoding='utf-8')

marker="# live-auction-auto-settle-session-lock-v2"
if marker not in text:
    anchor="def live_lot_expired(row):\n    rem=live_timer_remaining(row)\n    return rem is not None and rem<=0 and bool(row.get('currentItemId') or row.get('currentLot'))\n"
    insert=anchor+"\n"+marker+"\ndef live_participant_unpaid_ended_session(participant_id,current_session_id='',sessions=None):\n    pid=str(participant_id or '')\n    current=str(current_session_id or '')\n    if not pid: return None\n    sessions=sessions if isinstance(sessions,list) else load_live_auctions()\n    ended={str(s.get('id') or '') for s in sessions if str(s.get('status') or '') in ('ended','cancelled')}\n    if not ended: return None\n    for o in load_orders():\n        if str(o.get('participantId') or '')!=pid: continue\n        if str(o.get('source') or '')!='live_auction': continue\n        sid=str(o.get('sourceId') or '')\n        if not sid or sid==current or sid not in ended: continue\n        if str(o.get('paymentStatus') or 'unpaid') in ('paid','refunded'): continue\n        if str(o.get('status') or '') in ('cancelled','refunded','completed') and str(o.get('paymentStatus') or '') in ('paid','refunded'): continue\n        return o\n    return None\n\ndef notify_live_session_payment_due(row):\n    sid=str(row.get('id') or '')\n    if not sid: return 0\n    orders=[o for o in load_orders() if str(o.get('source') or '')=='live_auction' and str(o.get('sourceId') or '')==sid and str(o.get('paymentStatus') or 'unpaid') not in ('paid','refunded')]\n    by_pid={}\n    for o in orders:\n        pid=str(o.get('participantId') or '')\n        if not pid: continue\n        by_pid.setdefault(pid,[]).append(o)\n    count=0\n    for pid,rows in by_pid.items():\n        total=sum(float(o.get('total') or 0) for o in rows)\n        add_notification('participant',pid,'orders','💳 انتهى البث — مستحقات المزاد المباشر',f'انتهت جلسة البث ولديك {len(rows)} عملية فوز بإجمالي {total:g} ر.س. يلزم سداد المستحقات قبل المشاركة في بث مباشر جديد.','', '/account')\n        count+=1\n    return count\n"
    if anchor not in text: raise SystemExit('anchor helper not found')
    text=text.replace(anchor,insert,1)

old="""            pending_result=row.get('lastResult') if isinstance(row.get('lastResult'),dict) else None
            result_waiting=bool(pending_result and pending_result.get('sold') and not pending_result.get('clearedAt'))
            if action=='clear-result':
                if not pending_result: self.sendj({'error':'لا توجد نتيجة مزاد معلقة'},409); return
                pending_result['clearedAt']=datetime.datetime.now().isoformat(); pending_result['clearedBy']='admin'; row['lastResult']=pending_result
                row['updated']=datetime.datetime.now().isoformat(); save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('إقفال بطاقة فائز المزاد المباشر',{'sessionId':sid,'orderId':pending_result.get('orderId')}); self.sendj({'ok':True,'session':with_live_timer(row)}); return
            if action in ('open-item','open-free-lot') and result_waiting:
                self.sendj({'error':'أقفل بطاقة الفائز السابقة من سلة المزادات المباشرة قبل بدء مزايدة جديدة'},409); return
            if action in ('end','cancel') and result_waiting:
                self.sendj({'error':'لا يمكن إنهاء الجلسة قبل إقفال بطاقة الفائز من سلة المزادات المباشرة'},409); return
"""
new="""            pending_result=row.get('lastResult') if isinstance(row.get('lastResult'),dict) else None
            if action=='clear-result':
                if not pending_result: self.sendj({'error':'لا توجد نتيجة مزاد معلقة'},409); return
                pending_result['clearedAt']=datetime.datetime.now().isoformat(); pending_result['clearedBy']='admin'; row['lastResult']=pending_result
                row['updated']=datetime.datetime.now().isoformat(); save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('إخفاء بطاقة نتيجة المزاد المباشر',{'sessionId':sid,'orderId':pending_result.get('orderId')}); self.sendj({'ok':True,'session':with_live_timer(row)}); return
"""
if old in text:
    text=text.replace(old,new,1)

needle="""            if not row or row.get('status')!='live' or not (row.get('currentItemId') or row.get('currentLot')): self.sendj({'error':'لا يوجد مقتنى مفتوح للمزايدة الآن'},409); return
"""
replace=needle+"""            blocked_order=live_participant_unpaid_ended_session(person.get('id'),sid,sessions)
            if blocked_order:
                self.sendj({'error':'لديك مستحقات من بث مباشر سابق انتهى. يجب سدادها قبل المشاركة في بث مباشر جديد.','code':'previous_live_session_unpaid','orderId':blocked_order.get('id'),'actionUrl':'/account'},409); return
"""
if 'previous_live_session_unpaid' not in text:
    if needle not in text: raise SystemExit('bid guard anchor missing')
    text=text.replace(needle,replace,1)

oldend="""                if action in ('end','cancel'): row['endedAt']=datetime.datetime.now().isoformat(); row['archivedAt']=row['endedAt']
"""
newend="""                if action in ('end','cancel'):
                    row['endedAt']=datetime.datetime.now().isoformat(); row['archivedAt']=row['endedAt']
                    notify_live_session_payment_due(row)
"""
if oldend in text:
    text=text.replace(oldend,newend,1)

server.write_text(text,encoding='utf-8')

js=Path('public/live_auction.js')
j=js.read_text(encoding='utf-8')
oldfun="function launchGoldConfetti(key){if(!key||window.__lastGoldConfetti===key)return;window.__lastGoldConfetti=key;const wrap=document.createElement('div');wrap.className='gold-confetti';for(let i=0;i<55;i++){const p=document.createElement('i');p.style.left=(Math.random()*100)+'vw';p.style.animationDelay=(Math.random()*1.2)+'s';p.style.animationDuration=(2.4+Math.random()*2)+'s';wrap.appendChild(p)}document.body.appendChild(wrap);setTimeout(()=>wrap.remove(),5200)}"
newfun="function launchGoldConfetti(key){if(!key||window.__lastGoldConfetti===key)return;window.__lastGoldConfetti=key;const wrap=document.createElement('div');wrap.className='gold-confetti';for(let i=0;i<70;i++){const p=document.createElement('i');p.style.left=(Math.random()*100)+'vw';p.style.animationDelay=(Math.random()*.9)+'s';p.style.animationDuration=(2.3+Math.random()*1.8)+'s';wrap.appendChild(p)}const balloons=document.createElement('div');balloons.className='winner-balloons';for(let i=0;i<12;i++){const b=document.createElement('b');b.textContent=['🎈','🎈','🎊','🏆'][i%4];b.style.left=(4+Math.random()*92)+'vw';b.style.animationDelay=(Math.random()*.8)+'s';balloons.appendChild(b)}document.body.appendChild(wrap);document.body.appendChild(balloons);setTimeout(()=>{wrap.remove();balloons.remove()},5600)}"
if oldfun in j: j=j.replace(oldfun,newfun,1)
oldstart="function renderActive(){const s=active();if(!s)return;$('viewerTitle').textContent="
newstart="function renderActive(){const s=active();if(!s)return;winnerResultHtml(s);$('viewerTitle').textContent="
if oldstart in j: j=j.replace(oldstart,newstart,1)
js.write_text(j,encoding='utf-8')

html=Path('public/live_auction.html')
h=html.read_text(encoding='utf-8')
css=".winner-balloons{position:fixed;inset:0;z-index:100000;pointer-events:none;overflow:hidden}.winner-balloons b{position:absolute;bottom:-70px;font-size:34px;animation:balloonRise 4.8s ease-out forwards;filter:drop-shadow(0 4px 8px #0003)}@keyframes balloonRise{0%{transform:translateY(0) scale(.8);opacity:0}12%{opacity:1}100%{transform:translateY(-115vh) translateX(20px) scale(1.1);opacity:.95}}"
if '.winner-balloons{' not in h:
    h=h.replace('</style>',css+'</style>',1)
html.write_text(h,encoding='utf-8')

admin=Path('admin/app.js')
a=admin.read_text(encoding='utf-8')
olda="async function liveCloseItem(id,sold){if(sold&&!confirm('اعتماد البيع لآخر مزايد وإنشاء طلب تلقائي؟'))return;await liveControl(id,'close-item',{sold});}"
newa="async function liveCloseItem(id,sold){const s=(window.__liveSessions||[]).find(x=>String(x.id)===String(id));const autoSold=!!(s&&s.latestBidderId);await liveControl(id,'close-item',{sold:autoSold});}"
if olda in a: a=a.replace(olda,newa,1)
a=a.replace("بيع وإغلاق القطعة","إنهاء القطعة الآن",1)
admin.write_text(a,encoding='utf-8')

print('patched live auction auto settlement v2')
