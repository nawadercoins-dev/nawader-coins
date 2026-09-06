from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
admin_html=root/'admin'/'index.html'
admin_js=root/'admin'/'app.js'
server=root/'server.py'

# --- Admin HTML: rename the dues center and clarify its unified purpose ---
h=admin_html.read_text(encoding='utf-8')
h=h.replace('مستحقات المزادات','المستحقات والسداد')
h=h.replace('تُجمع المشاركات تلقائيًا من مزايدة جديدة إذا بقي مستحق فوز سابق غير مسدد بعد 24 ساعة من نهاية المزاد.',
            'مركز موحد لكل مستحقات العملاء: المزادات والسوق العام والمشتريات. طرق السداد واحدة وتُدار من مكان واحد، ثم تنتقل الطلبات إلى التجهيز والشحن.')
admin_html.write_text(h,encoding='utf-8')

# --- Admin JS: replace renderDues with a unified auction + orders center ---
j=admin_js.read_text(encoding='utf-8')
start=j.find('async function renderDues() {')
end=j.find('if ($("refreshDues")) $("refreshDues").onclick = renderDues;', start)
if start<0 or end<0:
    raise SystemExit('renderDues block not found')
end += len('if ($("refreshDues")) $("refreshDues").onclick = renderDues;')
new_block=r'''async function renderDues() {
  if (!$("duesList")) return;
  try {
    const [dueRes, orderRes] = await Promise.all([api("/api/dues"), api("/api/orders")]);
    const auctionRows = (dueRes.dues || []).map(x => ({...x, _kind:"auction", _sourceLabel:"مزاد"}));
    const allOrders = orderRes.orders || [];
    const orderRows = allOrders
      .filter(o => !o.archived && String(o.source||"") !== "auction")
      .filter(o => !["completed","returned"].includes(String(o.status||"")))
      .map(o => ({
        ...o,
        _kind:"order",
        _sourceLabel: String(o.source||"")==="market" ? "السوق العام" : "مشتريات",
        amount:Number(o.total||o.buyerTotal||0),
        participantName:o.customerName||o.participantName||"عميل",
        participantPhone:o.customerPhone||o.participantPhone||"",
        itemTitle:(o.items||[]).map(i=>i.title).filter(Boolean).join(" + ") || o.itemTitle || o.orderNumber || "طلب",
        paymentDeadline:o.paymentDeadline||o.created||o.updated||"",
        status: String(o.paymentStatus||"unpaid")==="paid" ? "paid" : (String(o.paymentStatus||"")==="refunded" || String(o.status||"")==="cancelled" ? "cancelled" : "unpaid")
      }));
    let rows=[...auctionRows,...orderRows];
    if(adminStoreFilter!=="all"){
      const dueItems=await all(), dueMap=new Map(dueItems.map(i=>[String(i.id||''),i]));
      rows=rows.filter(x=>{
        if(x._kind==="auction") return itemStoreKey(dueMap.get(String(x.itemId||''))||{})===adminStoreFilter;
        return adminOrderStoreKey(x,new Map(dueItems.map(i=>[String(i.id||''),i])))===adminStoreFilter;
      });
    }
    const now=Date.now();
    const unpaid=rows.filter(x=>x.status==="unpaid"), paid=rows.filter(x=>x.status==="paid");
    const overdue=unpaid.filter(x=>x._kind==="auction" && x.paymentDeadline && new Date(x.paymentDeadline).getTime()<=now);
    $("duesUnpaidCount").textContent=unpaid.length;
    $("duesOverdueCount").textContent=overdue.length;
    $("duesPaidCount").textContent=paid.length;
    $("duesList").innerHTML=rows.map(x=>{
      const isOver=x._kind==="auction"&&x.status==="unpaid"&&x.paymentDeadline&&new Date(x.paymentDeadline).getTime()<=now;
      const source=`<span class="source-chip">${esc(x._sourceLabel)}</span>`;
      const state=isOver?"متأخر +24 ساعة":dueStatusLabel(x);
      let actions="";
      if(x._kind==="auction"){
        actions=`<button class="due-paid ${x.status==="paid"?"is-current":""}" data-due="${esc(x.id)}" data-status="paid" ${x.status==="paid"?"disabled":""}>${x.status==="paid"?"✓ تم السداد":"اعتماد السداد"}</button><button class="due-cancel" data-due="${esc(x.id)}" data-status="cancelled" ${x.status==="cancelled"?"disabled":""}>إلغاء المستحق</button><button class="due-unpaid" data-due="${esc(x.id)}" data-status="unpaid" ${x.status==="unpaid"?"disabled":""}>↩ إرجاع لغير مسدد</button>`;
      }else{
        const claimed=String(x.manualPaymentStatus||"")==="claimed";
        actions=`<button class="due-paid ${x.status==="paid"?"is-current":""}" data-order-due="${esc(x.id)}" data-order-action="paid" ${x.status==="paid"?"disabled":""}>${claimed?"✅ تم استلام المبلغ — مصادقة":"اعتماد السداد"}</button><button class="due-cancel" data-order-due="${esc(x.id)}" data-order-action="cancelled" ${x.status==="cancelled"?"disabled":""}>إلغاء المستحق</button><button class="due-unpaid" data-order-due="${esc(x.id)}" data-order-action="unpaid" ${x.status==="unpaid"&&!claimed?"disabled":""}>↩ إرجاع لغير مسدد</button>`;
      }
      return `<article class="due-row ${isOver?"overdue":""}"><div>${source} <b>${esc(x.itemTitle||"مقتنى")}</b><p>${esc(x.participantName||"مشارك")} — ${esc(x.participantPhone||"")}</p><small>المبلغ: ${money(x.amount||0)}${x.paymentDeadline?` • التاريخ: ${fmtDate(x.paymentDeadline)}`:""}</small></div><span class="due-status ${x.status}">${state}</span><div class="actions due-actions">${actions}</div></article>`;
    }).join("") || '<p class="muted">لا توجد مستحقات مسجلة حاليًا.</p>';

    document.querySelectorAll("[data-due][data-status]").forEach(b=>b.onclick=async()=>{
      try{await api("/api/dues/status",{method:"POST",body:JSON.stringify({id:b.dataset.due,status:b.dataset.status})});await renderDues();await renderAdminNotifications()}catch(e){alert(e.message)}
    });
    document.querySelectorAll("[data-order-due][data-order-action]").forEach(b=>b.onclick=async()=>{
      const id=b.dataset.orderDue, action=b.dataset.orderAction;
      const label=action==="paid"?"اعتماد استلام المبلغ لهذا الطلب؟":action==="unpaid"?"إرجاع الطلب إلى غير مسدد؟":"إلغاء المستحق/الطلب؟";
      if(!confirm(label))return;
      try{
        await api('/api/order/payment-admin',{method:'POST',body:JSON.stringify({id,action})});
        await renderDues(); await renderOrders(); await renderAdminNotifications();
      }catch(e){alert(e.message)}
    });
  } catch (e) {
    $("duesList").textContent = "تعذر تحميل مركز المستحقات: " + e.message;
  }
}
if ($("refreshDues")) $("refreshDues").onclick = renderDues;'''
j=j[:start]+new_block+j[end:]
admin_js.write_text(j,encoding='utf-8')

# --- Server: add one admin endpoint for market/general order payment state ---
s=server.read_text(encoding='utf-8')
if "'/api/order/payment-admin'" not in s:
    # add to admin API permission set when present
    s=s.replace("'/api/operations','/api/orders'", "'/api/operations','/api/orders','/api/order/payment-admin'")

marker="            if p=='/api/order/request/resolve':"
if "if p=='/api/order/payment-admin':" not in s:
    if marker not in s: raise SystemExit('server insertion marker not found')
    endpoint="""            if p=='/api/order/payment-admin':
                oid=str(d.get('id') or ''); action=str(d.get('action') or ''); rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==oid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                now=datetime.datetime.now().isoformat(); number=row.get('orderNumber') or oid
                if action=='paid':
                    if not bool(row.get('shippingFeeConfirmed')): self.sendj({'error':'اعتمد الشحن أولًا قبل اعتماد السداد'},409); return
                    update_order_status(row,'paid','تم اعتماد استلام المبلغ من مركز المستحقات والسداد')
                    row['manualPaymentStatus']='approved'; row['manualPaymentApprovedAt']=now
                    add_notification('participant',row.get('participantId'),'finance','✅ تم اعتماد السداد',f'تم اعتماد استلام مبلغ الطلب {number}.','', '/account')
                elif action=='unpaid':
                    if str(row.get('status') or '') in ('shipped','received','completed'): self.sendj({'error':'لا يمكن إرجاع طلب مشحون أو مكتمل إلى غير مسدد'},409); return
                    row['paymentStatus']='unpaid'; row['paymentProofStatus']=''; row['manualPaymentStatus']=''; row['paidAt']=''; row['status']='awaiting_payment'; row['updated']=now
                    row.setdefault('history',[]).append({'status':'awaiting_payment','at':now,'note':'أعيد إلى غير مسدد من مركز المستحقات'})
                elif action=='cancelled':
                    if str(row.get('paymentStatus') or '')=='paid': self.sendj({'error':'الطلب مسدد؛ نفّذ الاسترداد بدل الإلغاء المباشر'},409); return
                    update_order_status(row,'cancelled','أُلغي من مركز المستحقات والسداد')
                else: self.sendj({'error':'إجراء السداد غير صالح'},400); return
                save_json(ORDERS,{'orders':rows}); append_operation('تحديث مستحق طلب',{'orderId':oid,'orderNumber':number,'action':action}); self.sendj({'ok':True,'order':row}); return
"""
    s=s.replace(marker,endpoint+marker,1)
server.write_text(s,encoding='utf-8')
print('unified dues center applied')
