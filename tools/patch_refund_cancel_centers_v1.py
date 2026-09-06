from pathlib import Path

p=Path('admin/app.js')
s=p.read_text(encoding='utf-8')
marker='// refund-cancel-centers-v1'
if marker in s:
    print('already patched')
    raise SystemExit(0)

s += r'''

// refund-cancel-centers-v1
(function(){
  const esc2=(v)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function reqKind(o){
    if(String(o.refundStatus||'')==='requested' || o.refundRequestedAt) return 'refund';
    if(String(o.cancellationStatus||'')==='requested' || o.cancellationRequestedAt) return 'cancel';
    return '';
  }
  function isCancelled(o){return String(o.status||'')==='cancelled' && String(o.paymentStatus||'')!=='refunded'}
  function isRefunded(o){return String(o.paymentStatus||'')==='refunded' || String(o.refundStatus||'')==='completed'}
  function orderTitle(o){return ((o.items||[]).map(x=>x.title).filter(Boolean).join(' + ')) || o.itemTitle || o.orderNumber || 'طلب'}
  function qty(o){return (o.items||[]).reduce((n,x)=>n+Math.max(1,Number(x.quantity||1)),0)||1}
  function ensureStyles(){
    if(document.getElementById('refundCancelCenterStyles'))return;
    const st=document.createElement('style');st.id='refundCancelCenterStyles';st.textContent=`
    .rc-center{margin:18px 0;padding:16px;border:1px solid #d9c790;border-radius:18px;background:#fffdf7}.rc-center h3{margin:0 0 12px;color:#0b2a52}.rc-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px}.rc-metric{padding:12px;border-radius:14px;background:#0b2a52;color:#fff;text-align:center}.rc-metric b{display:block;font-size:1.45rem;margin-top:4px}.rc-list{display:grid;gap:10px}.rc-row{border:1px solid #e2d7b8;border-radius:14px;padding:12px;background:#fff;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center}.rc-row h4{margin:0 0 6px;color:#14243b}.rc-row p{margin:3px 0;color:#5f6c7b}.rc-badge{display:inline-flex;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:900;background:#fff0cd;color:#805300}.rc-badge.refund{background:#e7f7ef;color:#17633c}.rc-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-start}.rc-actions button{min-height:38px;border-radius:9px;padding:7px 11px}.rc-actions .approve{background:#17845f;color:white}.rc-actions .reject{background:#a92e52;color:white}.rc-empty{padding:16px;text-align:center;color:#728094}.rc-history{display:grid;grid-template-columns:1fr 1fr;gap:12px}.rc-history-box{border:1px solid #e2d7b8;border-radius:14px;padding:12px;background:#fff}.rc-history-box h4{margin:0 0 10px;color:#0b2a52}.rc-history-item{padding:9px 0;border-bottom:1px solid #eee7d5}.rc-history-item:last-child{border-bottom:0}@media(max-width:900px){.rc-metrics{grid-template-columns:1fr 1fr}.rc-row{grid-template-columns:1fr}.rc-history{grid-template-columns:1fr}}`;
    document.head.appendChild(st);
  }
  async function resolveRequest(id,action){
    const labels={approve_cancel:'اعتماد إلغاء الطلب وإعادة الكمية؟',complete_refund:'اعتماد الاسترداد وإعادة الكمية وتسجيل المبلغ كمسترد؟',reject:'رفض الطلب المعلق؟'};
    if(!confirm(labels[action]||'تنفيذ الإجراء؟'))return;
    let note='';
    if(action==='reject') note=prompt('سبب الرفض (اختياري):','')||'';
    try{
      await api('/api/order/request/resolve',{method:'POST',body:JSON.stringify({id,action,note})});
      if(typeof window.toast==='function') window.toast('تم تنفيذ الإجراء وتحديث الطلب.');
      if(typeof renderFinance==='function') await renderFinance();
      if(typeof renderWarehouse==='function' && document.querySelector('#warehouseView.view.active')) await renderWarehouse();
      if(typeof renderOrders==='function' && document.querySelector('#orders.view.active')) await renderOrders();
      if(typeof renderAdminNotifications==='function') await renderAdminNotifications();
    }catch(e){alert(e.message||'تعذر تنفيذ الإجراء')}
  }
  window.resolveRefundCancelRequest=resolveRequest;

  async function fetchOrdersSafe(){
    try{return (await api('/api/orders')).orders||[]}catch(_){return []}
  }
  function metricsHtml(orders){
    const pendingCancel=orders.filter(o=>String(o.cancellationStatus||'')==='requested').length;
    const pendingRefund=orders.filter(o=>String(o.refundStatus||'')==='requested').length;
    const cancelled=orders.filter(isCancelled).length;
    const refunded=orders.filter(isRefunded).length;
    return `<div class="rc-metrics"><div class="rc-metric">إلغاء بانتظار الاعتماد<b>${pendingCancel}</b></div><div class="rc-metric">استرداد بانتظار الاعتماد<b>${pendingRefund}</b></div><div class="rc-metric">الملغي<b>${cancelled}</b></div><div class="rc-metric">المسترد<b>${refunded}</b></div></div>`;
  }
  function pendingHtml(orders){
    const pending=orders.filter(o=>String(o.cancellationStatus||'')==='requested'||String(o.refundStatus||'')==='requested');
    if(!pending.length)return '<div class="rc-empty">لا توجد طلبات إلغاء أو استرداد بانتظار الاعتماد.</div>';
    return `<div class="rc-list">${pending.map(o=>{
      const k=String(o.refundStatus||'')==='requested'?'refund':'cancel';
      const approve=k==='refund'?'complete_refund':'approve_cancel';
      const label=k==='refund'?'استرداد':'إلغاء';
      return `<article class="rc-row"><div><span class="rc-badge ${k}">${label}</span><h4>${esc2(orderTitle(o))}</h4><p>الطلب: ${esc2(o.orderNumber||o.id||'')} • الكمية: ${qty(o)}</p><p>العميل: ${esc2(o.customerName||o.participantName||'')} ${esc2(o.customerPhone||o.participantPhone||'')}</p><p>المبلغ: ${typeof money==='function'?money(Number(o.total||o.buyerTotal||0)):Number(o.total||o.buyerTotal||0).toFixed(2)+' ر.س'}</p></div><div class="rc-actions"><button class="approve" onclick="resolveRefundCancelRequest('${esc2(o.id)}','${approve}')">${k==='refund'?'✅ اعتماد الاسترداد':'✅ اعتماد الإلغاء'}</button><button class="reject" onclick="resolveRefundCancelRequest('${esc2(o.id)}','reject')">رفض</button></div></article>`
    }).join('')}</div>`;
  }
  function historyHtml(orders){
    const cancelled=orders.filter(isCancelled).slice().sort((a,b)=>String(b.updated||b.created||'').localeCompare(String(a.updated||a.created||''))).slice(0,20);
    const refunded=orders.filter(isRefunded).slice().sort((a,b)=>String(b.refundedAt||b.updated||'').localeCompare(String(a.refundedAt||a.updated||''))).slice(0,20);
    const block=(title,rows,kind)=>`<div class="rc-history-box"><h4>${title} (${rows.length})</h4>${rows.map(o=>`<div class="rc-history-item"><b>${esc2(orderTitle(o))}</b><div>${esc2(o.orderNumber||o.id||'')} • ${qty(o)} قطعة/وحدة</div><small>${kind==='refund'?'تم رد المبلغ وإعادة الكمية':'تم إلغاء الطلب وإعادة الكمية'}</small></div>`).join('')||'<div class="rc-empty">لا توجد سجلات.</div>'}</div>`;
    return `<div class="rc-history">${block('المسترد',refunded,'refund')}${block('الملغي',cancelled,'cancel')}</div>`;
  }
  function mount(viewId,hostClass,title,orders,includePending){
    const view=document.getElementById(viewId); if(!view)return;
    const panel=view.querySelector('.panel')||view;
    let box=panel.querySelector('.'+hostClass);
    if(!box){box=document.createElement('section');box.className='rc-center '+hostClass;panel.appendChild(box)}
    box.innerHTML=`<h3>${title}</h3>${metricsHtml(orders)}${includePending?'<h3 style="font-size:1rem">طلبات تحتاج اعتماد الإدارة</h3>'+pendingHtml(orders):''}<h3 style="font-size:1rem;margin-top:16px">سجل الملغي والمسترد</h3>${historyHtml(orders)}`;
  }

  const oldFinance=window.renderFinance||renderFinance;
  window.renderFinance=renderFinance=async function(){
    await oldFinance.apply(this,arguments); ensureStyles(); const orders=await fetchOrdersSafe(); mount('finance','finance-refund-cancel-center','الإلغاء والاسترداد',orders,true);
  };
  const oldWarehouse=window.renderWarehouse||renderWarehouse;
  window.renderWarehouse=renderWarehouse=async function(){
    await oldWarehouse.apply(this,arguments); ensureStyles(); const orders=await fetchOrdersSafe(); mount('warehouseView','warehouse-refund-cancel-center','حركة الملغي والمسترد في المستودع',orders,false);
  };
})();
'''

p.write_text(s,encoding='utf-8')
print('patched refund/cancel centers v1')
