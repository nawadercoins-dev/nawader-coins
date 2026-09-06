from pathlib import Path
p=Path(__file__).resolve().parents[1]/'public'/'account.html'
s=p.read_text(encoding='utf-8')

# Keep the IBAN capability visible even when disabled, so it is clear the feature exists and can be enabled later.
old="if(bank)bank.hidden=!pm.bankModeEnabled;if(form)form.hidden=!!pm.manualModeEnabled&&!pm.bankModeEnabled;return paymentSettingsCache"
new="if(bank){bank.hidden=false;bank.dataset.bankEnabled=pm.bankModeEnabled?'1':'0';if(!pm.bankModeEnabled)bank.innerHTML='<b>التحويل البنكي / IBAN</b><div class=\"payment-note\">غير مفعّل حاليًا من الإدارة. يمكن تفعيله لاحقًا من إعدادات السداد دون حذف بياناته.</div>';}if(form)form.hidden=!pm.bankModeEnabled;return paymentSettingsCache"
if old in s:
    s=s.replace(old,new,1)

# openPayment must not overwrite the disabled-bank notice.
old2="$('paymentBankInfo').innerHTML=`<b>بيانات التحويل البنكي</b>${p.bankName?`<div>البنك: <strong>${esc(p.bankName)}</strong></div>`:''}${p.accountName?`<div>اسم الحساب: <strong>${esc(p.accountName)}</strong></div>`:''}${p.iban?`<div>IBAN: <strong dir=\"ltr\">${esc(p.iban)}</strong> <button type=\"button\" onclick=\"navigator.clipboard?.writeText('${esc(p.iban)}')\">نسخ</button></div>`:''}${p.instructions?`<div class=\"payment-note\">${esc(p.instructions)}</div>`:''}${p.whatsapp?`<div>واتساب السداد: <strong dir=\"ltr\">${esc(p.whatsapp)}</strong></div>`:''}${!configured?'<div class=\"payment-rejected\">لم تضف الإدارة رقم IBAN بعد. تواصل مع الإدارة قبل التحويل.</div>':''}`;"
new2="if(p.bankModeEnabled){$('paymentBankInfo').innerHTML=`<b>بيانات التحويل البنكي</b>${p.bankName?`<div>البنك: <strong>${esc(p.bankName)}</strong></div>`:''}${p.accountName?`<div>اسم الحساب: <strong>${esc(p.accountName)}</strong></div>`:''}${p.iban?`<div>IBAN: <strong dir=\"ltr\">${esc(p.iban)}</strong> <button type=\"button\" onclick=\"navigator.clipboard?.writeText('${esc(p.iban)}')\">نسخ</button></div>`:''}${p.instructions?`<div class=\"payment-note\">${esc(p.instructions)}</div>`:''}${p.whatsapp?`<div>واتساب السداد: <strong dir=\"ltr\">${esc(p.whatsapp)}</strong></div>`:''}${!configured?'<div class=\"payment-rejected\">الحساب البنكي مفعّل لكن رقم IBAN لم يُدخل بعد.</div>':''}`;}"
if old2 in s:
    s=s.replace(old2,new2,1)

# Bank proof submit is enabled only when bank mode is on and IBAN exists.
s=s.replace("$('submitPaymentProof').disabled=!configured;","$('submitPaymentProof').disabled=!(p.bankModeEnabled&&configured);",1)

# Add robust close + manual-payment claim handlers after the existing lower close button handler.
anchor="$('closePaymentDialog').onclick=()=>{$('paymentDialog').close?.();$('paymentDialog').removeAttribute('open')};"
handler=r'''$('closePaymentDialog').onclick=()=>{$('paymentDialog').close?.();$('paymentDialog').removeAttribute('open')};
function closePaymentModal(){const d=$('paymentDialog');if(!d)return;try{d.close?.()}catch(e){}d.removeAttribute('open')}
if($('paymentDialogX'))$('paymentDialogX').onclick=(e)=>{e.preventDefault();e.stopPropagation();closePaymentModal()};
$('paymentDialog')?.addEventListener('click',(e)=>{if(e.target===$('paymentDialog'))closePaymentModal()});
document.addEventListener('keydown',(e)=>{if(e.key==='Escape'&&$('paymentDialog')?.open)closePaymentModal()});
if($('manualPaymentConfirm'))$('manualPaymentConfirm').onclick=async(e)=>{
  e.preventDefault();
  const btn=$('manualPaymentConfirm'),st=$('manualPaymentStatus');
  if(!activePaymentOrderIds.length||!currentInvoiceParticipantId){if(st)st.textContent='تعذر تحديد الطلب. أغلق النافذة وافتح «سداد الآن» من جديد.';return}
  if(!confirm('هل تؤكد أنك أتممت السداد وترغب بإرسال الطلب للإدارة لمصادقة استلام المبلغ؟'))return;
  btn.disabled=true;if(st)st.textContent='جارٍ إرسال طلب المصادقة...';
  try{
    const r=await fetch('/api/visitor/order/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({participantId:currentInvoiceParticipantId,orderId:activePaymentOrderIds[0],action:'manual_payment_claim'})});
    const d=await r.json().catch(()=>({}));if(!r.ok||d.ok===false)throw Error(d.error||'تعذر إرسال طلب المصادقة');
    if(st)st.textContent='✅ تم الإرسال — بانتظار مصادقة السداد من الإدارة';
    btn.textContent='⏳ بانتظار مصادقة الإدارة';btn.disabled=true;
    paymentSettingsCache=null;
    if(typeof loadOrders==='function')await loadOrders();
    setTimeout(closePaymentModal,900);
  }catch(err){btn.disabled=false;if(st)st.textContent='⚠️ '+err.message}
};'''
if anchor in s and "function closePaymentModal()" not in s:
    s=s.replace(anchor,handler,1)

p.write_text(s,encoding='utf-8')
print('payment dialog control fixes applied')
