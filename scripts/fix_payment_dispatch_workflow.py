from pathlib import Path

root=Path(__file__).resolve().parents[1]
server=root/'server.py'
admin_js=root/'admin'/'app.js'
account=root/'public'/'account.html'

# --- server ---
s=server.read_text(encoding='utf-8')
marker='# payment-dispatch-final-confirm-v1'
if marker not in s:
    # allow manual-claimed orders to move through preparing/ready_to_ship, but never ship before admin payment confirmation
    old="""                if status in ('preparing','ready_to_ship','shipped') and str(row.get('paymentStatus') or '')!='paid':
                    self.sendj({'error':'لا يمكن تجهيز أو شحن الطلب قبل تأكيد السداد'},409); return
"""
    new="""                # payment-dispatch-final-confirm-v1
                payment_now=str(row.get('paymentStatus') or 'unpaid')
                manual_claimed=str(row.get('manualPaymentStatus') or '')=='claimed'
                if status in ('preparing','ready_to_ship') and payment_now!='paid' and not manual_claimed:
                    self.sendj({'error':'لا يمكن تجهيز الطلب قبل السداد أو طلب مصادقة السداد اليدوي'},409); return
                if status=='shipped' and payment_now!='paid':
                    self.sendj({'error':'لا يمكن إخراج الطلب للشحن قبل مصادقة الإدارة على استلام المبلغ'},409); return
"""
    if old not in s:
        raise SystemExit('server payment gate anchor not found')
    s=s.replace(old,new,1)

    # insert manual confirmation branch in admin order status endpoint
    anchor="""                if row.get('archived') and status not in ('completed','returned'): self.sendj({'error':'الطلب المكتمل مؤرشف ولا يعاد للخلف إلا كمرتجع'},409); return
"""
    branch="""                if bool(d.get('manualPaymentConfirm')):
                    if str(row.get('manualPaymentStatus') or '')!='claimed':
                        self.sendj({'error':'لا يوجد طلب مصادقة سداد يدوي معلق لهذا الطلب'},409); return
                    if str(row.get('status') or '') not in ('preparing','ready_to_ship'):
                        self.sendj({'error':'مصادقة السداد اليدوي تكون في مرحلة التجهيز النهائية قبل خروج الشحنة'},409); return
                    if not bool(row.get('shippingFeeConfirmed')):
                        self.sendj({'error':'يجب اعتماد الشحن أولًا'},409); return
                    now=datetime.datetime.now().isoformat()
                    row['paymentStatus']='paid'; row['paidAt']=now; row['manualPaymentStatus']='approved'; row['manualPaymentApprovedAt']=now; row['updated']=now
                    row.setdefault('history',[]).append({'status':str(row.get('status') or ''),'at':now,'note':'صادقت الإدارة على استلام المبلغ قبل خروج الشحنة'})
                    if row.get('source')=='auction':
                        dues=load_auction_dues(); due=next((x for x in dues if str(x.get('id'))==str(row.get('sourceId'))),None)
                        if due:
                            due['status']='paid'; due['paidAt']=now; due['updated']=now; save_json(AUCTION_DUES,{'dues':dues})
                    save_json(ORDERS,{'orders':rows})
                    append_operation('مصادقة السداد قبل الشحن',{'orderId':oid,'orderNumber':row.get('orderNumber')},actor='الإدارة')
                    add_notification('participant',row.get('participantId'),'finance','✅ تمت مصادقة السداد',f'تم تأكيد استلام مبلغ الطلب {row.get("orderNumber") or oid}. الطلب جاهز للخروج للشحن.','', '/account')
                    self.sendj({'ok':True,'order':row}); return
"""
    if anchor not in s:
        raise SystemExit('server order status anchor not found')
    s=s.replace(anchor,branch+anchor,1)

server.write_text(s,encoding='utf-8')

# --- admin app ---
j=admin_js.read_text(encoding='utf-8')
if 'payment-dispatch-admin-v1' not in j:
    old="""    awaiting_payment: o.paymentStatus===\"proof_submitted\"||o.paymentProofStatus===\"pending\"?[]:[[\"paid\", o.manualPaymentStatus===\"claimed\"?\"✅ تم استلام المبلغ — مصادقة السداد\":\"تأكيد السداد يدويًا\"]],
    paid: [[\"preparing\", \"بدء التجهيز\"]],
    preparing: [[\"ready_to_ship\", \"جاهز للشحن\"]],
    ready_to_ship: [[\"shipped\", \"تم الشحن\"]],
"""
    new="""    awaiting_payment: o.paymentStatus===\"proof_submitted\"||o.paymentProofStatus===\"pending\"?[]:(o.manualPaymentStatus===\"claimed\"?[[\"preparing\",\"بدء التجهيز\"]]:[[\"paid\",\"تأكيد السداد يدويًا\"]]),
    paid: [[\"preparing\", \"بدء التجهيز\"]],
    preparing: [[\"ready_to_ship\", \"جاهز للشحن\"]],
    ready_to_ship: (o.manualPaymentStatus===\"claimed\"&&o.paymentStatus!==\"paid\")?[]:[[\"shipped\", \"تم الشحن\"]],
"""
    if old not in j:
        raise SystemExit('admin order button map anchor not found')
    j=j.replace(old,new,1)

    anchor="""window.resolvePaymentProof=resolvePaymentProof;
function orderNextButtons(o) {
"""
    helper="""window.resolvePaymentProof=resolvePaymentProof;
// payment-dispatch-admin-v1
async function confirmManualPaymentAtDispatch(id){
  if(!confirm('تأكيد أن المبلغ تم استلامه فعليًا وأن الطلب يمكن أن يخرج للشحن؟'))return;
  try{
    await api('/api/order/status',{method:'POST',body:JSON.stringify({id,status:'ready_to_ship',manualPaymentConfirm:true})});
    toast('✓ تمت مصادقة السداد. يمكن الآن اعتماد «تم الشحن».');
    await renderOrders(); await renderAdminNotifications();
  }catch(e){alert(e.message)}
}
window.confirmManualPaymentAtDispatch=confirmManualPaymentAtDispatch;
function orderNextButtons(o) {
"""
    if anchor not in j:
        raise SystemExit('admin helper anchor not found')
    j=j.replace(anchor,helper,1)

    old_return="""  return b+requests+`<button class=\"ghost\" onclick=\"orderStatus('${o.id}','stalled')\">متعثر</button><button class=\"ghost\" onclick=\"orderStatus('${o.id}','returned')\">مرتجع</button>`+release;
"""
    new_return="""  let manualFinal=(o.status==='ready_to_ship'&&o.manualPaymentStatus==='claimed'&&o.paymentStatus!=='paid')?`<button class=\"gold-action\" onclick=\"confirmManualPaymentAtDispatch('${o.id}')\">✅ تم استلام المبلغ — مصادقة السداد قبل الشحن</button><span class=\"muted\">لن يتفعّل «تم الشحن» قبل هذه المصادقة.</span>`:'';
  return b+manualFinal+requests+`<button class=\"ghost\" onclick=\"orderStatus('${o.id}','stalled')\">متعثر</button><button class=\"ghost\" onclick=\"orderStatus('${o.id}','returned')\">مرتجع</button>`+release;
"""
    if old_return not in j:
        raise SystemExit('admin order return anchor not found')
    j=j.replace(old_return,new_return,1)

    # Prominent operational payment controls inside Orders & Shipping, not only buried in Settings.
    tail="""
// payment-mode-quick-controls-v1
async function installOrdersPaymentQuickControls(){
  const list=$('ordersList'); if(!list)return;
  const host=list.closest('.panel')||list.parentElement; if(!host||$('ordersPaymentQuickControls'))return;
  const box=document.createElement('div'); box.id='ordersPaymentQuickControls'; box.className='panel';
  box.style.cssText='margin:0 0 16px;border:2px solid #c89b3c;background:#fffaf0';
  box.innerHTML=`<h3 style=\"margin-top:0\">💳 تشغيل طرق السداد</h3><p class=\"muted\">هذه المفاتيح تشغيلية وتبقى بيانات IBAN محفوظة حتى عند إيقافه.</p><div style=\"display:flex;gap:18px;flex-wrap:wrap;align-items:center\"><label><input type=\"checkbox\" id=\"ordersManualPayEnabled\"> السداد اليدوي / التواصل</label><label><input type=\"checkbox\" id=\"ordersBankPayEnabled\"> التحويل البنكي / IBAN</label></div><div style=\"display:grid;grid-template-columns:minmax(220px,1fr) auto;gap:8px;margin-top:10px\"><input id=\"ordersPaymentIban\" dir=\"ltr\" placeholder=\"SA00...\" style=\"padding:10px;border:1px solid #ccd5df;border-radius:9px\"><button id=\"saveOrdersPaymentModes\" type=\"button\">حفظ تشغيل السداد</button></div><div id=\"ordersPaymentModeStatus\" class=\"muted\" style=\"margin-top:7px\"></div>`;
  host.insertBefore(box,list);
  try{const r=await api('/api/settings/admin'),st=r.settings||{};$('ordersManualPayEnabled').checked=st.paymentManualModeEnabled!==false;$('ordersBankPayEnabled').checked=!!st.paymentBankModeEnabled;$('ordersPaymentIban').value=st.paymentIban||'';}catch(e){$('ordersPaymentModeStatus').textContent=e.message}
  $('saveOrdersPaymentModes').onclick=async()=>{try{await api('/api/settings',{method:'POST',body:JSON.stringify({paymentManualModeEnabled:!!$('ordersManualPayEnabled').checked,paymentBankModeEnabled:!!$('ordersBankPayEnabled').checked,paymentIban:String($('ordersPaymentIban').value||'').trim()})});$('ordersPaymentModeStatus').textContent='✓ تم حفظ طرق السداد. يمكن تشغيل أو إيقاف IBAN دون حذف بياناته.';}catch(e){$('ordersPaymentModeStatus').textContent=e.message}};
}
const __oldRenderOrders=renderOrders; renderOrders=async function(...args){await installOrdersPaymentQuickControls();return __oldRenderOrders.apply(this,args)};
setTimeout(()=>installOrdersPaymentQuickControls().catch(()=>{}),700);
"""
    j += tail

admin_js.write_text(j,encoding='utf-8')

# --- account dialog controls ---
a=account.read_text(encoding='utf-8')
if 'payment-dialog-functional-controls-v2' not in a:
    old="""$('closePaymentDialog').onclick=()=>{$('paymentDialog').close?.();$('paymentDialog').removeAttribute('open')};
"""
    new="""// payment-dialog-functional-controls-v2
function closePaymentDialogNow(){const d=$('paymentDialog');if(!d)return;try{d.close?.()}catch{}d.removeAttribute('open')}
$('closePaymentDialog').onclick=closePaymentDialogNow;
if($('paymentDialogX'))$('paymentDialogX').onclick=closePaymentDialogNow;
if($('paymentDialog'))$('paymentDialog').addEventListener('cancel',e=>{e.preventDefault();closePaymentDialogNow()});
if($('manualPaymentConfirm'))$('manualPaymentConfirm').onclick=async()=>{
  const btn=$('manualPaymentConfirm'),st=$('manualPaymentStatus');
  if(!activePaymentOrderIds.length||!currentInvoiceParticipantId){if(st)st.textContent='تعذر تحديد الطلب الحالي.';return}
  if(btn.disabled)return;
  if(!confirm('هل تم السداد فعليًا؟ سيتم إرسال الطلب للإدارة للمصادقة على استلام المبلغ.'))return;
  btn.disabled=true;
  try{
    const r=await fetch('/api/visitor/order/action',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({participantId:currentInvoiceParticipantId,orderId:activePaymentOrderIds[0],action:'manual_payment_claim'})});
    const d=await r.json().catch(()=>({})); if(!r.ok)throw Error(d.error||'تعذر إرسال طلب المصادقة');
    if(st)st.textContent='✅ تم الإرسال — بانتظار مصادقة الإدارة عند تجهيز الشحنة.';
    btn.textContent='⏳ بانتظار مصادقة الإدارة';
    await loadAccountOrders?.();
  }catch(e){btn.disabled=false;if(st)st.textContent=e.message}
};
"""
    if old not in a:
        raise SystemExit('account close button anchor not found')
    a=a.replace(old,new,1)

    # Always show IBAN section; enable/disable is operationally visible.
    old2="if(bank)bank.hidden=!pm.bankModeEnabled;if(form)form.hidden=!!pm.manualModeEnabled&&!pm.bankModeEnabled;return paymentSettingsCache"
    new2="if(bank){bank.hidden=false;bank.dataset.enabled=pm.bankModeEnabled?'1':'0';}if(form)form.hidden=!pm.bankModeEnabled;return paymentSettingsCache"
    if old2 in a:
        a=a.replace(old2,new2,1)

    # Add explicit status label in bank block after it is rendered.
    old3="""$('paymentBankInfo').innerHTML=`<b>بيانات التحويل البنكي</b>${p.bankName?`<div>البنك: <strong>${esc(p.bankName)}</strong></div>`:''}${p.accountName?`<div>اسم الحساب: <strong>${esc(p.accountName)}</strong></div>`:''}${p.iban?`<div>IBAN: <strong dir=\"ltr\">${esc(p.iban)}</strong> <button type=\"button\" onclick=\"navigator.clipboard?.writeText('${esc(p.iban)}')\">نسخ</button></div>`:''}${p.instructions?`<div class=\"payment-note\">${esc(p.instructions)}</div>`:''}${p.whatsapp?`<div>واتساب السداد: <strong dir=\"ltr\">${esc(p.whatsapp)}</strong></div>`:''}${!configured?'<div class=\"payment-rejected\">لم تضف الإدارة رقم IBAN بعد. تواصل مع الإدارة قبل التحويل.</div>':''}`;
"""
    new3="""$('paymentBankInfo').innerHTML=`<b>التحويل البنكي / IBAN</b>${p.bankModeEnabled?'<div class=\"payment-pending\">✅ مفعّل من الإدارة</div>':'<div class=\"payment-wait\">⏸ غير مفعّل حاليًا من الإدارة — بياناته محفوظة ويمكن تشغيله لاحقًا.</div>'}${p.bankName?`<div>البنك: <strong>${esc(p.bankName)}</strong></div>`:''}${p.accountName?`<div>اسم الحساب: <strong>${esc(p.accountName)}</strong></div>`:''}${p.iban?`<div>IBAN: <strong dir=\"ltr\">${esc(p.iban)}</strong> <button type=\"button\" onclick=\"navigator.clipboard?.writeText('${esc(p.iban)}')\">نسخ</button></div>`:''}${p.instructions?`<div class=\"payment-note\">${esc(p.instructions)}</div>`:''}${p.whatsapp?`<div>واتساب السداد: <strong dir=\"ltr\">${esc(p.whatsapp)}</strong></div>`:''}${p.bankModeEnabled&&!configured?'<div class=\"payment-rejected\">التحويل البنكي مفعّل لكن لم تضف الإدارة رقم IBAN بعد.</div>':''}`;
"""
    if old3 not in a:
        raise SystemExit('account bank html anchor not found')
    a=a.replace(old3,new3,1)

account.write_text(a,encoding='utf-8')
print('payment dispatch workflow fixed')
