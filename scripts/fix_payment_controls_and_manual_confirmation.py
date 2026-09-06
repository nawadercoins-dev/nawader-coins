from pathlib import Path

root=Path(__file__).resolve().parents[1]
server=root/'server.py'
admin_js=root/'admin'/'app.js'
account=root/'public'/'account.html'

s=server.read_text(encoding='utf-8')
# Persist manual/bank payment toggles and instructions.
needle="if 'paymentWhatsapp' in d: st['paymentWhatsapp']=''.join(ch for ch in str(d.get('paymentWhatsapp') or '') if ch.isdigit() or ch=='+')[:24]"
insert="""if 'paymentWhatsapp' in d: st['paymentWhatsapp']=''.join(ch for ch in str(d.get('paymentWhatsapp') or '') if ch.isdigit() or ch=='+')[:24]\n                if 'paymentManualModeEnabled' in d: st['paymentManualModeEnabled']=bool(d.get('paymentManualModeEnabled'))\n                if 'paymentBankModeEnabled' in d: st['paymentBankModeEnabled']=bool(d.get('paymentBankModeEnabled'))\n                if 'paymentManualInstructions' in d: st['paymentManualInstructions']=str(d.get('paymentManualInstructions') or '').strip()[:800]"""
if needle in s and "if 'paymentManualModeEnabled' in d" not in s:
    s=s.replace(needle,insert,1)

# Add manual payment declaration action before refund_request branch.
anchor="                if action=='refund_request':\n"
block="""                if action=='manual_payment_claim':\n                    stcfg=load_settings()\n                    if not bool(stcfg.get('paymentManualModeEnabled',True)):\n                        self.sendj({'error':'السداد اليدوي غير مفعّل حاليًا'},409); return\n                    if payment in ('paid','refunded','proof_submitted') or status not in ('new','awaiting_payment','stalled'):\n                        self.sendj({'error':'لا يمكن إرسال طلب مصادقة السداد في الحالة الحالية'},409); return\n                    if not bool(row.get('shippingFeeConfirmed')):\n                        self.sendj({'error':'يجب اعتماد الشحن قبل طلب مصادقة السداد'},409); return\n                    targets=[x for x in rows if str(x.get('participantId') or '')==pid and bool(x.get('shippingFeeConfirmed')) and str(x.get('paymentStatus') or 'unpaid') not in ('paid','refunded','proof_submitted') and str(x.get('status') or '') in ('new','awaiting_payment','stalled') and not x.get('archived') and not x.get('cancellationRequestedAt')]\n                    for x in targets:\n                        x['manualPaymentStatus']='claimed'; x['manualPaymentClaimedAt']=now; x['updated']=now\n                        x.setdefault('history',[]).append({'status':str(x.get('status') or ''),'at':now,'note':'أبلغ العميل بإتمام السداد اليدوي وينتظر مصادقة الإدارة'})\n                    save_json(ORDERS,{'orders':rows})\n                    add_notification('admin','','finance','💰 طلب مصادقة سداد يدوي',f'أبلغ العميل بإتمام السداد للدفعة المرتبطة بالطلب {number}. يرجى التحقق ثم الضغط على «تم استلام المبلغ».','', '/admin')\n                    append_operation('طلب مصادقة سداد يدوي',{'orderId':oid,'participantId':pid,'count':len(targets)},actor='العميل')\n                    self.sendj({'ok':True,'message':'تم إرسال طلب مصادقة السداد إلى الإدارة.','count':len(targets)}); return\n"""
if anchor in s and "action=='manual_payment_claim'" not in s:
    s=s.replace(anchor,block+anchor,1)
server.write_text(s,encoding='utf-8')

# Admin: clearer manual confirmation wording.
j=admin_js.read_text(encoding='utf-8')
j=j.replace('[["paid", "تأكيد السداد يدويًا"]]','[["paid", o.manualPaymentStatus==="claimed"?"✅ تم استلام المبلغ — مصادقة السداد":"تأكيد السداد يدويًا"]]')
# Add notice for claimed manual payment.
needle="let proofNotice='';\n"
if needle in j and 'manualPaymentStatus===\"claimed\"' not in j:
    j=j.replace(needle,"let proofNotice='';\n  if(o.manualPaymentStatus===\"claimed\"&&o.paymentStatus!==\"paid\")proofNotice=`<div class=\"notice\"><b>💰 العميل أبلغ بإتمام السداد اليدوي</b><div>بانتظار تحقق الإدارة ثم الضغط على «تم استلام المبلغ — مصادقة السداد».</div></div>`;\n",1)
admin_js.write_text(j,encoding='utf-8')

# Account: add X close button, manual confirmation button, and status language.
a=account.read_text(encoding='utf-8')
# CSS for close X
cssneedle='.payment-box{padding:20px;background:#fff;color:#14243b}'
cssrepl='.payment-box{padding:20px;background:#fff;color:#14243b;position:relative}.payment-dialog-x{position:absolute;top:10px;left:12px;width:40px;height:40px;border:0;border-radius:50%;background:#eef1f5;color:#14243b;font-size:25px;font-weight:900;cursor:pointer;display:grid;place-items:center;z-index:3}.payment-manual-confirm{margin-top:12px;border:0;border-radius:10px;padding:11px 15px;background:#17633c;color:#fff;font-weight:900;cursor:pointer}.payment-manual-confirm:disabled{opacity:.55;cursor:not-allowed}'
if cssneedle in a and 'payment-dialog-x' not in a:
    a=a.replace(cssneedle,cssrepl,1)
# Insert X and button in dialog.
old='<dialog id="paymentDialog" class="payment-dialog"><div class="payment-box"><h2>💳 سداد المستحقات</h2>'
new='<dialog id="paymentDialog" class="payment-dialog"><div class="payment-box"><button type="button" id="paymentDialogX" class="payment-dialog-x" aria-label="إغلاق">×</button><h2>💳 سداد المستحقات</h2>'
if old in a:
    a=a.replace(old,new,1)
old2='<div class="payment-bank" id="paymentManualInfo" hidden><b>تعليمات السداد</b><div id="paymentManualText">سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة.</div></div>'
new2='<div class="payment-bank" id="paymentManualInfo" hidden><b>تعليمات السداد</b><div id="paymentManualText">سيتم التواصل معك من الإدارة لإرسال تعليمات السداد المناسبة.</div><button type="button" id="manualPaymentConfirm" class="payment-manual-confirm">✅ تم السداد — إرسال للمصادقة</button><div id="manualPaymentStatus" class="payment-note" style="margin-top:8px"></div></div>'
if old2 in a:
    a=a.replace(old2,new2,1)
# Status text
old3="function paymentStatusText(x){if(x.paymentStatus==='paid')return '✅ تم السداد';"
new3="function paymentStatusText(x){if(x.paymentStatus==='paid')return '✅ تم السداد وتم استلام المبلغ';if(x.manualPaymentStatus==='claimed')return '⏳ بانتظار مصادقة السداد من الإدارة';"
if old3 in a:
    a=a.replace(old3,new3,1)
# eligible excludes claimed
old4="function eligiblePaymentOrder(x){return !!x&&x.shippingFeeConfirmed&&!['paid','refunded','proof_submitted'].includes(String(x.paymentStatus||''))"
new4="function eligiblePaymentOrder(x){return !!x&&x.shippingFeeConfirmed&&x.manualPaymentStatus!=='claimed'&&!['paid','refunded','proof_submitted'].includes(String(x.paymentStatus||''))"
if old4 in a:
    a=a.replace(old4,new4,1)
# Hook close x and manual claim after existing close button wiring if present.
script_anchor="$('closePaymentDialog')?.addEventListener('click',()=>$('paymentDialog')?.close());"
extra="""$('closePaymentDialog')?.addEventListener('click',()=>$('paymentDialog')?.close());\n$('paymentDialogX')?.addEventListener('click',()=>$('paymentDialog')?.close());\n$('paymentDialog')?.addEventListener('click',e=>{if(e.target===$('paymentDialog'))$('paymentDialog')?.close()});\n$('manualPaymentConfirm')?.addEventListener('click',async()=>{\n  const btn=$('manualPaymentConfirm'),msg=$('manualPaymentStatus');\n  if(!activePaymentOrderIds.length){if(msg)msg.textContent='لا توجد طلبات جاهزة للمصادقة.';return;}\n  if(!confirm('هل تؤكد أنك أتممت السداد وفق تعليمات الإدارة؟ سيتم إرسال الطلب للإدارة للمصادقة على استلام المبلغ.'))return;\n  try{btn.disabled=true;if(msg)msg.textContent='جارٍ إرسال طلب المصادقة…';\n    const oid=activePaymentOrderIds[0];\n    const r=await fetch('/api/visitor/order/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({participantId:currentInvoiceParticipantId,orderId:oid,action:'manual_payment_claim'})});\n    const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'تعذر إرسال طلب المصادقة');\n    if(msg)msg.textContent='✓ تم إرسال طلب مصادقة السداد إلى الإدارة.';\n    setTimeout(()=>{$('paymentDialog')?.close();paymentSettingsCache=null;loadOrders?.();},800);\n  }catch(e){if(msg)msg.textContent=e.message;}finally{btn.disabled=false;}\n});"""
if script_anchor in a and "manualPaymentConfirm')?.addEventListener" not in a:
    a=a.replace(script_anchor,extra,1)
account.write_text(a,encoding='utf-8')
print('payment controls/manual confirmation fix applied')
