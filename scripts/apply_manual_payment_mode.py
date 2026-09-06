from pathlib import Path

root=Path(__file__).resolve().parents[1]
server=root/'server.py'
admin_html=root/'admin'/'index.html'
admin_js=root/'admin'/'app.js'
account=root/'public'/'account.html'

s=server.read_text(encoding='utf-8')
# settings defaults
old="'paymentInstructions':'حوّل المبلغ النهائي بعد اعتماد الشحن، ثم ارفع صورة إشعار التحويل من صفحة المستحقات.','paymentWhatsapp':'','visitorSections':"
new="'paymentInstructions':'حوّل المبلغ النهائي بعد اعتماد الشحن، ثم ارفع صورة إشعار التحويل من صفحة المستحقات.','paymentWhatsapp':'','paymentManualModeEnabled':True,'paymentBankModeEnabled':False,'paymentManualInstructions':'سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة لهذا الطلب.','visitorSections':"
if old in s and 'paymentManualModeEnabled' not in s:
    s=s.replace(old,new,1)
# public settings payload
old="'payment':{'method':'bank_transfer','bankName':st.get('paymentBankName',''),'accountName':st.get('paymentAccountName',''),'iban':st.get('paymentIban',''),'instructions':st.get('paymentInstructions',''),'whatsapp':st.get('paymentWhatsapp','')}}"
new="'payment':{'method':'manual' if st.get('paymentManualModeEnabled',True) else 'bank_transfer','manualModeEnabled':bool(st.get('paymentManualModeEnabled',True)),'bankModeEnabled':bool(st.get('paymentBankModeEnabled',False)),'manualInstructions':st.get('paymentManualInstructions','سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة لهذا الطلب.'),'bankName':st.get('paymentBankName',''),'accountName':st.get('paymentAccountName',''),'iban':st.get('paymentIban',''),'instructions':st.get('paymentInstructions',''),'whatsapp':st.get('paymentWhatsapp','')}}"
if old in s:
    s=s.replace(old,new,1)
server.write_text(s,encoding='utf-8')

h=admin_html.read_text(encoding='utf-8')
anchor='<label>اسم البنك<input id="paymentBankName"'
if anchor in h and 'paymentManualModeEnabled' not in h:
    insert='''<div class="panel" style="margin:12px 0"><h3>طريقة السداد الحالية</h3><label style="display:flex;gap:8px;align-items:center;margin:8px 0"><input id="paymentManualModeEnabled" type="checkbox"> تفعيل السداد اليدوي المؤقت</label><label style="display:flex;gap:8px;align-items:center;margin:8px 0"><input id="paymentBankModeEnabled" type="checkbox"> تفعيل السداد عبر الحساب البنكي / IBAN</label><label>تعليمات السداد اليدوي<textarea id="paymentManualInstructions" rows="3" placeholder="مثال: سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة."></textarea></label><p class="muted">يمكن تفعيل اليدوي الآن، ثم إلغاؤه وتفعيل الحساب البنكي لاحقًا عند اعتماد المنصة والحساب التجاري.</p></div>'''
    h=h.replace(anchor,insert+anchor,1)
admin_html.write_text(h,encoding='utf-8')

j=admin_js.read_text(encoding='utf-8')
needle='if ($("paymentBankName")) $("paymentBankName").value = st.paymentBankName || "";'
if needle in j and 'paymentManualModeEnabled' not in j:
    j=j.replace(needle,'if ($("paymentManualModeEnabled")) $("paymentManualModeEnabled").checked = st.paymentManualModeEnabled !== false;\n    if ($("paymentBankModeEnabled")) $("paymentBankModeEnabled").checked = !!st.paymentBankModeEnabled;\n    if ($("paymentManualInstructions")) $("paymentManualInstructions").value = st.paymentManualInstructions || "سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة لهذا الطلب.";\n    '+needle,1)
needle2='paymentBankName: $("paymentBankName") ? $("paymentBankName").value.trim() : "",'
if needle2 in j and 'paymentManualModeEnabled:' not in j:
    j=j.replace(needle2,'paymentManualModeEnabled: $("paymentManualModeEnabled") ? !!$("paymentManualModeEnabled").checked : true,\n          paymentBankModeEnabled: $("paymentBankModeEnabled") ? !!$("paymentBankModeEnabled").checked : false,\n          paymentManualInstructions: $("paymentManualInstructions") ? $("paymentManualInstructions").value.trim() : "",\n          '+needle2,1)
admin_js.write_text(j,encoding='utf-8')

a=account.read_text(encoding='utf-8')
# Switch payment dialog behavior without deleting future bank UI
old="<div class=\"payment-bank\" id=\"paymentBankInfo\"><b>بيانات التحويل البنكي</b><div>بانتظار تحميل بيانات السداد...</div></div>"
new="<div class=\"payment-bank\" id=\"paymentManualInfo\" hidden><b>تعليمات السداد</b><div id=\"paymentManualText\">سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة.</div></div><div class=\"payment-bank\" id=\"paymentBankInfo\"><b>بيانات التحويل البنكي</b><div>بانتظار تحميل بيانات السداد...</div></div>"
if old in a and 'paymentManualInfo' not in a:
    a=a.replace(old,new,1)
# Hook getPaymentSettings to toggle modes
needle="paymentSettingsCache=d.payment||{};return paymentSettingsCache"
if needle in a and 'paymentManualInfo' in a:
    repl="paymentSettingsCache=d.payment||{};const pm=paymentSettingsCache;const manual=document.getElementById('paymentManualInfo'),bank=document.getElementById('paymentBankInfo'),form=document.getElementById('paymentForm');if(manual){manual.hidden=!pm.manualModeEnabled;const t=document.getElementById('paymentManualText');if(t)t.textContent=pm.manualInstructions||'سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة لهذا الطلب.';}if(bank)bank.hidden=!pm.bankModeEnabled;if(form)form.hidden=!!pm.manualModeEnabled&&!pm.bankModeEnabled;return paymentSettingsCache"
    a=a.replace(needle,repl,1)
# next step language in manual mode will be resolved when opening payment; keep button available but make dialog non-bank
account.write_text(a,encoding='utf-8')

print('manual payment mode patch applied')