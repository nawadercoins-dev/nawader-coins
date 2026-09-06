from pathlib import Path

APP=Path('admin/app.js')
SERVER=Path('server.py')

app=APP.read_text(encoding='utf-8')
marker='// unified-dues-routing-v2'
if marker not in app:
    app += r'''

// unified-dues-routing-v2
let unifiedDuesSourceFilter='all';
function unifiedDueSourceKey(x){
  if(x._kind==='auction') return 'auction';
  const s=String(x.source||x.orderSource||'').toLowerCase();
  if(s==='market') return 'market';
  return 'other';
}
function unifiedDueSourceLabel(k){return k==='auction'?'⚖ المزادات':k==='market'?'🛒 السوق العام':'📦 مشتريات أخرى'}
function unifiedDueBucket(x){
  const claimed=String(x.manualPaymentStatus||'')==='claimed'||String(x.paymentProofStatus||'')==='pending'||String(x.paymentStatus||'')==='proof_submitted';
  if(claimed) return 'review';
  const over=x._kind==='auction'&&x.status==='unpaid'&&x.paymentDeadline&&new Date(x.paymentDeadline).getTime()<=Date.now();
  return over?'overdue':'unpaid';
}
function unifiedDueStyles(){
  if(document.getElementById('unifiedDuesStyle')) return;
  const s=document.createElement('style');s.id='unifiedDuesStyle';s.textContent=`
  .dues-source-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.dues-source-tabs button{border:1px solid #d0b46c;background:#fff;color:#0b2a52;border-radius:999px;padding:9px 14px;font-weight:900;cursor:pointer}.dues-source-tabs button.active{background:#0b2a52;color:#fff;border-color:#0b2a52}.dues-board{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.dues-lane{border:1px solid #dacb9b;border-radius:16px;background:#fffaf0;padding:12px;min-height:160px}.dues-lane h3{margin:0 0 10px;color:#0b2a52;display:flex;justify-content:space-between;gap:8px}.dues-lane h3 span{background:#0b2a52;color:#fff;border-radius:999px;padding:2px 8px;font-size:.8rem}.due-row{margin:9px 0}.source-chip{display:inline-block;border-radius:999px;padding:4px 8px;font-weight:900;background:#e9eef7;color:#0b2a52}.source-chip.auction{background:#fff0cd;color:#805300}.source-chip.market{background:#ddf1e5;color:#17633c}.source-chip.other{background:#e9e2f8;color:#5f3b8c}.due-route-note{margin-top:6px;font-size:.82rem;color:#64748b}.dues-empty{padding:18px;text-align:center;color:#7a8491}.due-actions button{margin:3px}.dues-help{padding:10px 12px;border-radius:12px;background:#eef6ff;border:1px solid #c7dbee;color:#174f84;line-height:1.8;margin:10px 0 14px}@media(max-width:950px){.dues-board{grid-template-columns:1fr}}
  `;document.head.appendChild(s);
}
async function renderDues(){
  if(!$('duesList'))return; unifiedDueStyles();
  try{
    const [dueRes,orderRes]=await Promise.all([api('/api/dues'),api('/api/orders')]);
    const auctionRows=(dueRes.dues||[]).map(x=>({...x,_kind:'auction',_sourceLabel:'مزاد'}));
    const orderRows=(orderRes.orders||[]).filter(o=>!o.archived&&!['paid','refunded'].includes(String(o.paymentStatus||''))&&!['cancelled','returned','completed','shipped','received'].includes(String(o.status||''))).map(o=>({...o,_kind:'order',_sourceLabel:String(o.source||'')==='market'?'السوق العام':'مشتريات',amount:Number(o.buyerTotal??o.total??0),itemTitle:o.itemTitle||((o.items||[])[0]||{}).title||o.orderNumber||'طلب',participantName:o.customerName||o.participantName||'',participantPhone:o.customerPhone||o.participantPhone||'',status:String(o.paymentStatus||'unpaid')==='paid'?'paid':'unpaid'}));
    let rows=[...auctionRows.filter(x=>!['paid','cancelled'].includes(String(x.status||''))),...orderRows];
    rows=rows.filter(x=>adminStoreMatchesOrder? (x._kind==='auction'||adminStoreMatchesOrder(x,null,adminStoreFilter)) : true);
    const counts={all:rows.length,auction:rows.filter(x=>unifiedDueSourceKey(x)==='auction').length,market:rows.filter(x=>unifiedDueSourceKey(x)==='market').length,other:rows.filter(x=>unifiedDueSourceKey(x)==='other').length};
    const host=$('duesList');
    const panel=host.closest('.panel')||host.parentElement;
    let tabs=panel.querySelector('.dues-source-tabs');
    if(!tabs){tabs=document.createElement('div');tabs.className='dues-source-tabs';host.before(tabs)}
    tabs.innerHTML=[['all','الكل'],['auction','المزادات'],['market','السوق العام'],['other','مشتريات أخرى']].map(([k,l])=>`<button type="button" data-dues-source="${k}" class="${unifiedDuesSourceFilter===k?'active':''}">${l} (${counts[k]||0})</button>`).join('');
    tabs.querySelectorAll('[data-dues-source]').forEach(b=>b.onclick=()=>{unifiedDuesSourceFilter=b.dataset.duesSource;renderDues()});
    let help=panel.querySelector('.dues-help');if(!help){help=document.createElement('div');help.className='dues-help';tabs.after(help)}
    help.textContent='المستحقات النشطة فقط تظهر هنا. اعتماد السداد ينقل الطلب تلقائيًا إلى التجهيز والشحن، إلغاء المستحق يخرجه من المركز، وإرجاعه لغير مسدد ينقله إلى باب «غير مسدد».';
    if(unifiedDuesSourceFilter!=='all') rows=rows.filter(x=>unifiedDueSourceKey(x)===unifiedDuesSourceFilter);
    const buckets={review:[],unpaid:[],overdue:[]};rows.forEach(x=>buckets[unifiedDueBucket(x)].push(x));
    const renderCard=x=>{
      const sk=unifiedDueSourceKey(x), source=`<span class="source-chip ${sk}">${unifiedDueSourceLabel(sk)}</span>`;
      const claimed=String(x.manualPaymentStatus||'')==='claimed';let actions='';
      if(x._kind==='auction') actions=`<button class="due-paid" data-due="${esc(x.id)}" data-status="paid">اعتماد السداد</button><button class="due-cancel" data-due="${esc(x.id)}" data-status="cancelled">إلغاء المستحق</button><button class="due-unpaid" data-due="${esc(x.id)}" data-status="unpaid">↩ إرجاع لغير مسدد</button>`;
      else actions=`<button class="due-paid" data-order-due="${esc(x.id)}" data-order-action="paid">${claimed?'✅ تم استلام المبلغ — مصادقة':'اعتماد السداد'}</button><button class="due-cancel" data-order-due="${esc(x.id)}" data-order-action="cancelled">إلغاء المستحق</button><button class="due-unpaid" data-order-due="${esc(x.id)}" data-order-action="unpaid">↩ إرجاع لغير مسدد</button>`;
      return `<article class="due-row"><div>${source} <b>${esc(x.itemTitle||'مقتنى')}</b><p>${esc(x.participantName||'مشارك')} — ${esc(x.participantPhone||'')}</p><small>المبلغ: ${money(x.amount||0)}${x.paymentDeadline?` • التاريخ: ${fmtDate(x.paymentDeadline)}`:''}</small><div class="due-route-note">${unifiedDueBucket(x)==='review'?'ينتظر مصادقة الإدارة':unifiedDueBucket(x)==='overdue'?'متأخر ويحتاج إجراء':'جاهز للسداد / غير مسدد'}</div></div><div class="actions due-actions">${actions}</div></article>`;
    };
    const lane=(k,title)=>`<section class="dues-lane"><h3>${title}<span>${buckets[k].length}</span></h3>${buckets[k].map(renderCard).join('')||'<div class="dues-empty">لا توجد عناصر في هذا الباب.</div>'}</section>`;
    host.innerHTML=`<div class="dues-board">${lane('review','بانتظار المصادقة')}${lane('unpaid','غير مسدد')}${lane('overdue','متأخر')}</div>`;
    document.querySelectorAll('[data-due][data-status]').forEach(b=>b.onclick=async()=>{const label=b.dataset.status==='paid'?'اعتماد السداد ونقل الطلب إلى الشحن؟':b.dataset.status==='cancelled'?'إلغاء المستحق وإخراجه من المركز؟':'إرجاعه إلى غير مسدد؟';if(!confirm(label))return;try{await api('/api/dues/status',{method:'POST',body:JSON.stringify({id:b.dataset.due,status:b.dataset.status})});await renderDues();await renderAdminNotifications()}catch(e){alert(e.message)}});
    document.querySelectorAll('[data-order-due][data-order-action]').forEach(b=>b.onclick=async()=>{const a=b.dataset.orderAction,label=a==='paid'?'اعتماد استلام المبلغ ونقل الطلب إلى التجهيز والشحن؟':a==='cancelled'?'إلغاء المستحق/الطلب وإخراجه من المركز؟':'إرجاع الطلب إلى غير مسدد؟';if(!confirm(label))return;try{await api('/api/order/payment-admin',{method:'POST',body:JSON.stringify({id:b.dataset.orderDue,action:a})});await renderDues();if(typeof renderOrders==='function')await renderOrders();await renderAdminNotifications()}catch(e){alert(e.message)}});
  }catch(e){$('duesList').innerHTML=`<p class="muted">${esc(e.message||'تعذر تحميل المستحقات')}</p>`}
}
'''
    APP.write_text(app,encoding='utf-8')

server=SERVER.read_text(encoding='utf-8')
old="""update_order_status(row,'paid','تم اعتماد استلام المبلغ من مركز المستحقات والسداد')\n                    row['manualPaymentStatus']='approved'; row['manualPaymentApprovedAt']=now"""
new="""update_order_status(row,'paid','تم اعتماد استلام المبلغ من مركز المستحقات والسداد')\n                    update_order_status(row,'preparing','انتقل تلقائيًا إلى التجهيز والشحن بعد اعتماد السداد')\n                    row['manualPaymentStatus']='approved'; row['manualPaymentApprovedAt']=now"""
if old in server:
    server=server.replace(old,new,1)
SERVER.write_text(server,encoding='utf-8')
print('patched unified dues routing v2')
