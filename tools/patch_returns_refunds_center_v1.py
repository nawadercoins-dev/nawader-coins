from pathlib import Path

APP=Path('admin/app.js')
SERVER=Path('server.py')
app=APP.read_text(encoding='utf-8')
server=SERVER.read_text(encoding='utf-8')

# --- server: restore cancelled/refunded items to their origin section (visibility only; inventory reversal already handled by order flow) ---
marker='# returns-refunds-origin-restore-v1'
if marker not in server:
    insert=r'''

# returns-refunds-origin-restore-v1
def restore_order_visibility_to_origin(order):
    """Restore item display routing after an approved cancellation/refund without changing quantities.
    Inventory quantities are already reversed by the existing order-status flow.
    """
    try:
        items=load(); changed=False
        by_id={str(i.get('id') or ''):i for i in items}
        source=str(order.get('source') or '').strip().lower()
        fallback={'market':'market','auction':'auction','special':'special','rare':'special','offers':'special','collectibles':'warehouse','antiques':'warehouse'}.get(source,'warehouse')
        for line in (order.get('items') or []):
            iid=str(line.get('itemId') or line.get('id') or '')
            item=by_id.get(iid)
            if not item: continue
            origin=str(line.get('originLocation') or line.get('adminLocation') or order.get('originLocation') or fallback).strip().lower()
            if origin not in ('warehouse','market','auction','special','outside'):
                origin=fallback
            item['adminLocation']=origin
            item['forMarket']=origin=='market'; item['marketApproved']=origin=='market'
            item['forAuction']=origin=='auction'; item['auctionApproved']=origin=='auction'
            item['specialNumberEnabled']=origin=='special'
            item['outsideDisplay']=origin=='outside'
            item['sold']=False
            item['updated']=int(datetime.datetime.now().timestamp()*1000)
            changed=True
        if changed: save(items)
    except Exception as e:
        print('restore_order_visibility_to_origin warning:',e)
'''
    needle='def update_order_status(order,status,note=\'\'):'
    if needle not in server:
        raise SystemExit('update_order_status marker not found')
    server=server.replace(needle,insert+'\n'+needle,1)

# Hook approved cancellation and completed refund to route item back to origin.
old="update_order_status(row,'cancelled',note or 'اعتمدت الإدارة طلب الإلغاء؛ أعيدت الكمية إلى المتاح'); row['cancellationStatus']='approved'; row['cancellationResolvedAt']=now"
new="update_order_status(row,'cancelled',note or 'اعتمدت الإدارة طلب الإلغاء؛ أعيدت الكمية إلى المتاح'); restore_order_visibility_to_origin(row); row['cancellationStatus']='approved'; row['cancellationResolvedAt']=now"
if old in server:
    server=server.replace(old,new,1)
old2="update_order_status(row,'cancelled',note or 'اعتمدت الإدارة الاسترداد قبل الشحن؛ أعيدت الكمية إلى المتاح'); row['paymentStatus']='refunded'; row['refundStatus']='completed'; row['refundedAt']=now; row['refundedAmount']=float(row.get('total') or 0)"
new2="update_order_status(row,'cancelled',note or 'اعتمدت الإدارة الاسترداد قبل الشحن؛ أعيدت الكمية إلى المتاح'); restore_order_visibility_to_origin(row); row['paymentStatus']='refunded'; row['refundStatus']='completed'; row['refundedAt']=now; row['refundedAmount']=float(row.get('total') or 0)"
if old2 in server:
    server=server.replace(old2,new2,1)

# --- admin UI: dedicated cancellation/refund approval center inside Orders ---
ui_marker='// returns-refunds-center-v1'
if ui_marker not in app:
    app += r'''

// returns-refunds-center-v1
(function(){
  const moneySafe=v=>{try{return money(Number(v||0))}catch(_){return Number(v||0).toFixed(2)+' ر.س'}};
  const srcLabel=o=>{
    const s=String(o.source||'').toLowerCase();
    return s==='auction'?'⚖ المزاد':s==='market'?'🛒 السوق العام':s==='special'?'⭐ المميزة والنادرة':s==='antiques'?'🏺 التحف':'📦 المشتريات';
  };
  async function resolveRequest(id,action){
    const labels={approve_cancel:'اعتماد الإلغاء وإرجاع المقتنى إلى مكانه السابق؟',complete_refund:'اعتماد الاسترداد وإرجاع المقتنى إلى مكانه السابق؟',reject:'رفض الطلب؟'};
    if(!confirm(labels[action]||'تنفيذ الإجراء؟'))return;
    const note=prompt('ملاحظة الإدارة (اختياري):','')||'';
    await api('/api/order/request/resolve',{method:'POST',body:JSON.stringify({id,action,note})});
    if(typeof renderOrders==='function') await renderOrders();
    if(typeof renderAdminNotifications==='function') await renderAdminNotifications();
  }
  async function renderReturnsRefundsCenter(){
    const view=document.getElementById('orders'); if(!view)return;
    let host=document.getElementById('returnsRefundsCenter');
    if(!host){
      host=document.createElement('section');host.id='returnsRefundsCenter';host.className='panel';
      const first=view.querySelector('.panel'); if(first) first.before(host); else view.prepend(host);
    }
    try{
      const res=await api('/api/orders'); const rows=res.orders||[];
      const pendingCancel=rows.filter(o=>o.cancellationStatus==='requested'||(o.cancellationRequestedAt&&!['approved','rejected'].includes(String(o.cancellationStatus||''))));
      const pendingRefund=rows.filter(o=>o.refundStatus==='requested');
      const cancelled=rows.filter(o=>String(o.status||'')==='cancelled'&&String(o.paymentStatus||'')!=='refunded');
      const refunded=rows.filter(o=>String(o.paymentStatus||'')==='refunded'||o.refundStatus==='completed');
      const cancelledValue=cancelled.reduce((s,o)=>s+Number(o.total||o.buyerTotal||0),0);
      const refundedValue=refunded.reduce((s,o)=>s+Number(o.refundedAmount||o.total||o.buyerTotal||0),0);
      const card=(o,type)=>`<article class="rr-card"><div><span class="rr-source">${srcLabel(o)}</span><b>${esc(o.orderNumber||o.id||'طلب')}</b><p>${esc(o.customerName||o.participantName||'عميل')} — ${esc(o.customerPhone||o.participantPhone||'')}</p><small>القيمة: ${moneySafe(o.total||o.buyerTotal||0)}</small></div><div class="rr-actions">${type==='cancel'?`<button class="rr-approve" data-rr-id="${esc(o.id)}" data-rr-action="approve_cancel">✅ اعتماد الإلغاء وإرجاع المقتنى</button>`:`<button class="rr-approve" data-rr-id="${esc(o.id)}" data-rr-action="complete_refund">✅ اعتماد الاسترداد وإرجاع المقتنى</button>`}<button class="rr-reject" data-rr-id="${esc(o.id)}" data-rr-action="reject">رفض</button></div></article>`;
      host.innerHTML=`<style>
      #returnsRefundsCenter{border-top:4px solid #0b2a52}.rr-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.rr-summary{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;margin:12px 0}.rr-summary article{background:#f7f9fc;border:1px solid #dbe3ef;border-radius:12px;padding:11px}.rr-summary b{display:block;font-size:1.25rem;color:#0b2a52}.rr-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.rr-col{border:1px solid #e4d5ad;border-radius:14px;padding:12px;background:#fffaf0}.rr-card{background:#fff;border:1px solid #e3e6eb;border-radius:12px;padding:12px;margin:9px 0;display:grid;gap:10px}.rr-source{display:inline-block;background:#eef3fb;color:#0b2a52;border-radius:999px;padding:4px 8px;font-weight:800;font-size:.8rem}.rr-card b{display:block;margin:6px 0}.rr-card p{margin:3px 0;color:#5f6b7a}.rr-actions{display:grid;grid-template-columns:2fr 1fr;gap:7px}.rr-actions button{min-height:40px;border-radius:9px;border:0;color:#fff;font-weight:800}.rr-approve{background:#198754}.rr-reject{background:#9c2e2e}@media(max-width:850px){.rr-grid{grid-template-columns:1fr}.rr-summary{grid-template-columns:1fr 1fr}}
      </style><div class="rr-head"><div><h2>↩️ الإلغاء والاسترداد</h2><p class="muted">كل طلب يحتاج اعتماد الإدارة قبل إعادة المقتنى. بعد الاعتماد يعود المقتنى إلى القسم الذي كان معروضًا فيه قبل البيع.</p></div></div><div class="rr-summary"><article><span>بانتظار اعتماد الإلغاء</span><b>${pendingCancel.length}</b></article><article><span>بانتظار اعتماد الاسترداد</span><b>${pendingRefund.length}</b></article><article><span>إجمالي الملغي</span><b>${cancelled.length}</b><small>${moneySafe(cancelledValue)}</small></article><article><span>إجمالي المسترد</span><b>${refunded.length}</b><small>${moneySafe(refundedValue)}</small></article></div><div class="rr-grid"><section class="rr-col"><h3>طلبات الإلغاء (${pendingCancel.length})</h3>${pendingCancel.map(o=>card(o,'cancel')).join('')||'<p class="muted">لا توجد طلبات إلغاء معلقة.</p>'}</section><section class="rr-col"><h3>طلبات الاسترداد (${pendingRefund.length})</h3>${pendingRefund.map(o=>card(o,'refund')).join('')||'<p class="muted">لا توجد طلبات استرداد معلقة.</p>'}</section></div>`;
      host.querySelectorAll('[data-rr-action]').forEach(b=>b.onclick=()=>resolveRequest(b.dataset.rrId,b.dataset.rrAction).catch(e=>alert(e.message)));
    }catch(e){host.innerHTML=`<h2>↩️ الإلغاء والاسترداد</h2><p class="muted">${esc(e.message||'تعذر تحميل الطلبات')}</p>`}
  }
  if(typeof renderOrders==='function'){
    const base=renderOrders;
    renderOrders=async function(){const r=await base.apply(this,arguments);await renderReturnsRefundsCenter();return r;};
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{if(document.querySelector('#orders.view.active,#orders.active'))renderReturnsRefundsCenter()});
})();
'''

APP.write_text(app,encoding='utf-8')
SERVER.write_text(server,encoding='utf-8')
print('patched returns/refunds center v1')
