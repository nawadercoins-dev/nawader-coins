from pathlib import Path
import re

server=Path('server.py')
app=Path('admin/app.js')
s=server.read_text(encoding='utf-8')
a=app.read_text(encoding='utf-8')

# 1) Make the flat shipping fee configurable from platform settings.
s=s.replace("defaults={'buyerFeePercent':2.5,", "defaults={'flatShippingFee':35.0,'buyerFeePercent':2.5,", 1)

old="""# flat-shipping-35-v1\nFLAT_SHIPPING_FEE=35.0\n\ndef apply_flat_shipping_for_participant(orders, participant_id):\n    \"\"\"Apply one fixed 35 SAR shipping charge across all active unpaid orders for the participant.\n    The charge is attached to one order only; sibling orders in the same unpaid batch carry 0 shipping\n    so the customer is never charged 35 per item/order.\n    \"\"\"\n    pid=str(participant_id or '')\n"""
new="""# flat-shipping-configurable-v2\ndef flat_shipping_fee():\n    try:\n        return max(0.0, round(float(load_settings().get('flatShippingFee',35.0)),2))\n    except Exception:\n        return 35.0\n\ndef apply_flat_shipping_for_participant(orders, participant_id):\n    \"\"\"Apply one configurable flat shipping charge across all active unpaid orders for a participant.\n    The configured amount is attached to one order only; sibling orders in the same unpaid batch carry 0 shipping.\n    \"\"\"\n    pid=str(participant_id or '')\n"""
if old not in s:
    raise SystemExit('flat shipping marker not found')
s=s.replace(old,new,1)
s=s.replace("fee=FLAT_SHIPPING_FEE if o is primary else 0.0", "fee=flat_shipping_fee() if o is primary else 0.0", 1)

# 2) Admin endpoint to change the amount and immediately recalculate active unpaid customer batches.
marker="""            if p=='/api/merge':\n"""
branch="""            if p=='/api/shipping-policy':\n                if not self.require_admin(api=True): return\n                try: fee=max(0.0,round(float(d.get('flatShippingFee')),2))\n                except Exception: self.sendj({'error':'مبلغ الشحن غير صالح'},400); return\n                if fee>10000: self.sendj({'error':'مبلغ الشحن غير منطقي'},400); return\n                st=load_settings(); st['flatShippingFee']=fee; save_json(SETTINGS,st)\n                rows=load_orders(); pids=sorted({str(o.get('participantId') or '') for o in rows if str(o.get('participantId') or '')})\n                affected=0\n                for pid in pids:\n                    affected+=apply_flat_shipping_for_participant(rows,pid)\n                if rows: save_json(ORDERS,{'orders':rows})\n                append_operation('تعديل سياسة الشحن الثابت',{'flatShippingFee':fee,'affectedOrders':affected},actor='الإدارة')\n                self.sendj({'ok':True,'flatShippingFee':fee,'affectedOrders':affected}); return\n"""
if marker not in s:
    raise SystemExit('POST insertion marker not found')
s=s.replace(marker,branch+marker,1)

# 3) Include the current amount in the public settings payload for customer UI wording if needed.
needle="""'whatsappVerificationNumber':st.get('whatsappVerificationNumber','966551892409'),'payment':{"""
if needle in s:
    s=s.replace(needle, "'whatsappVerificationNumber':st.get('whatsappVerificationNumber','966551892409'),'flatShippingFee':flat_shipping_fee(),'payment':{",1)

server.write_text(s,encoding='utf-8')

# 4) Inject a compact admin control into Orders & Shipping without changing the main HTML structure.
js=r'''

// configurable-flat-shipping-v2
(function(){
  async function installFlatShippingControl(){
    const view=document.getElementById('orders');
    if(!view||document.getElementById('flatShippingPolicyBox')) return;
    const panel=view.querySelector('.panel')||view;
    const box=document.createElement('div');
    box.id='flatShippingPolicyBox';
    box.style.cssText='margin:12px 0;padding:12px;border:1px solid rgba(212,164,71,.55);border-radius:14px;background:rgba(7,27,53,.45);display:flex;gap:10px;align-items:end;flex-wrap:wrap';
    box.innerHTML='<label style="display:grid;gap:6px;min-width:220px"><b>رسوم الشحن الثابتة للعميل</b><span style="font-size:.82rem;opacity:.8">تُحسب مرة واحدة على جميع طلباته النشطة غير المسددة، مهما كان عدد القطع.</span><input id="flatShippingFeeInput" type="number" min="0" step="1" inputmode="decimal" style="padding:10px;border-radius:9px"></label><button id="saveFlatShippingFee" class="gold-action" type="button">حفظ وتطبيق على الطلبات النشطة</button><span id="flatShippingFeeStatus"></span>';
    const anchor=panel.querySelector('.auction-title-row');
    if(anchor) anchor.insertAdjacentElement('afterend',box); else panel.prepend(box);
    try{
      const d=await api('/api/settings/admin');
      const fee=Number(d?.settings?.flatShippingFee ?? 35);
      document.getElementById('flatShippingFeeInput').value=Number.isFinite(fee)?fee:35;
    }catch(e){ document.getElementById('flatShippingFeeStatus').textContent='تعذر قراءة قيمة الشحن'; }
    document.getElementById('saveFlatShippingFee').onclick=async()=>{
      const input=document.getElementById('flatShippingFeeInput');
      const status=document.getElementById('flatShippingFeeStatus');
      const fee=Number(input.value);
      if(!Number.isFinite(fee)||fee<0){ status.textContent='⚠️ أدخل مبلغًا صحيحًا'; return; }
      status.textContent='جارٍ الحفظ والتطبيق...';
      try{
        const r=await api('/api/shipping-policy',{method:'POST',body:JSON.stringify({flatShippingFee:fee})});
        status.textContent=`✅ تم اعتماد ${Number(r.flatShippingFee).toLocaleString('ar-SA')} ر.س وتحديث ${Number(r.affectedOrders||0).toLocaleString('ar-SA')} طلب نشط`;
        if(typeof renderOrders==='function') await renderOrders();
      }catch(e){ status.textContent='⚠️ '+e.message; }
    };
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',installFlatShippingControl); else installFlatShippingControl();
})();
'''
if '// configurable-flat-shipping-v2' not in a:
    a += js
app.write_text(a,encoding='utf-8')

# basic validations
compile(s,'server.py','exec')
assert 'flatShippingFee' in s and '/api/shipping-policy' in s
assert 'flatShippingPolicyBox' in a and 'saveFlatShippingFee' in a
print('configurable shipping patch applied')
