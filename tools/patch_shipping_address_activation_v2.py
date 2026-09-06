from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
app=ROOT/'admin'/'app.js'
server=ROOT/'server.py'
styles=ROOT/'admin'/'styles.css'

# --- admin UI: when address is missing, route directly into an inline address editor instead of showing a dead-end alert.
s=app.read_text(encoding='utf-8')
if '// admin-order-address-editor-v2' not in s:
    marker='function orderNextButtons(o) {'
    if marker not in s:
        raise RuntimeError('orderNextButtons marker not found')
    helper=r'''
// admin-order-address-editor-v2
function orderAddressComplete(o){
  const a=o&&o.shippingAddress&&typeof o.shippingAddress==='object'?o.shippingAddress:{};
  return !!(String(a.country||'').trim()&&String(a.city||'').trim()&&String(a.addressLine||'').trim());
}
function orderAddressEditorHtml(o){
  const a=o&&o.shippingAddress&&typeof o.shippingAddress==='object'?o.shippingAddress:{};
  const id=String(o.id||'');
  return `<section class="order-address-editor" id="order-address-editor-${esc(id)}" hidden>
    <h4>📍 إدخال / تصحيح عنوان التسليم</h4>
    <p class="muted">أكمل العنوان هنا مباشرة ثم احفظه. بعد الحفظ يمكنك اعتماد «جاهز للشحن» بدون الرجوع لصفحة أخرى.</p>
    <div class="order-address-grid">
      <input id="addr-recipient-${esc(id)}" value="${esc(a.recipientName||o.customerName||'')}" placeholder="اسم المستلم">
      <input id="addr-phone-${esc(id)}" value="${esc(a.recipientPhone||o.customerPhone||'')}" placeholder="جوال المستلم">
      <input id="addr-country-${esc(id)}" value="${esc(a.country||'')}" placeholder="الدولة *">
      <input id="addr-city-${esc(id)}" value="${esc(a.city||'')}" placeholder="المدينة *">
      <input id="addr-district-${esc(id)}" value="${esc(a.district||'')}" placeholder="الحي">
      <input id="addr-postal-${esc(id)}" value="${esc(a.postalCode||'')}" placeholder="الرمز البريدي">
      <input class="wide" id="addr-line-${esc(id)}" value="${esc(a.addressLine||'')}" placeholder="العنوان بالتفصيل: الشارع، المبنى، الوحدة *">
      <textarea class="wide" id="addr-notes-${esc(id)}" placeholder="ملاحظات التسليم">${esc(a.notes||'')}</textarea>
    </div>
    <div class="actions"><button onclick="saveOrderAddress('${esc(id)}')">✅ حفظ وتفعيل العنوان</button><button class="ghost" onclick="closeOrderAddressEditor('${esc(id)}')">إغلاق</button></div>
  </section>`;
}
window.openOrderAddressEditor=(id)=>{
  const box=document.getElementById(`order-address-editor-${id}`); if(!box)return;
  box.hidden=false; box.classList.add('attention'); box.scrollIntoView({behavior:'smooth',block:'center'});
  setTimeout(()=>{
    const ids=[`addr-country-${id}`,`addr-city-${id}`,`addr-line-${id}`];
    const first=ids.map(x=>document.getElementById(x)).find(el=>el&&!String(el.value||'').trim());
    (first||document.getElementById(`addr-recipient-${id}`))?.focus?.();
  },250);
};
window.closeOrderAddressEditor=(id)=>{const box=document.getElementById(`order-address-editor-${id}`);if(box){box.hidden=true;box.classList.remove('attention')}};
window.saveOrderAddress=async(id)=>{
  const get=(k)=>String(document.getElementById(`${k}-${id}`)?.value||'').trim();
  const shippingAddress={recipientName:get('addr-recipient'),recipientPhone:get('addr-phone'),country:get('addr-country'),city:get('addr-city'),district:get('addr-district'),postalCode:get('addr-postal'),addressLine:get('addr-line'),notes:get('addr-notes')};
  const missing=[]; if(!shippingAddress.country)missing.push('الدولة'); if(!shippingAddress.city)missing.push('المدينة'); if(!shippingAddress.addressLine)missing.push('العنوان بالتفصيل');
  if(missing.length){adminMoveNotice('أكمل الحقول المطلوبة: '+missing.join('، '));openOrderAddressEditor(id);return;}
  try{
    await api('/api/order/shipping',{method:'POST',body:JSON.stringify({id,shippingAddress})});
    adminMoveNotice('✅ تم حفظ عنوان التسليم وتفعيله للطلب.');
    await renderOrders();
  }catch(e){alert(e.message||'تعذر حفظ عنوان التسليم')}
};
'''
    s=s.replace(marker,helper+'\n'+marker,1)

    old="""  let b = (map[o.status] || []).map((x) => `<button onclick=\"orderStatus('${o.id}','${x[0]}')\">${x[1]}</button>`).join(\"\");"""
    new="""  let b = (map[o.status] || []).map((x) => (x[0]==='ready_to_ship'&&!orderAddressComplete(o))?`<button onclick=\"openOrderAddressEditor('${o.id}')\">${x[1]}</button>`:`<button onclick=\"orderStatus('${o.id}','${x[0]}')\">${x[1]}</button>`).join(\"\");"""
    if old not in s:
        raise RuntimeError('order button mapping not found')
    s=s.replace(old,new,1)

    card_old="""</div>${itemHtml}<div class=\"order-shipping-fields\">"""
    card_new="""</div>${itemHtml}${orderAddressEditorHtml(o)}<div class=\"order-shipping-fields\">"""
    if card_old not in s:
        raise RuntimeError('order card insertion point not found')
    s=s.replace(card_old,card_new,1)

    app.write_text(s,encoding='utf-8')

# --- server: allow admin shipping endpoint to save the address on the order and sync the customer profile for future orders.
s=server.read_text(encoding='utf-8')
if '# admin-order-address-save-v2' not in s:
    needle="""                row['shippingCompany']=str(d.get('shippingCompany') or '').strip(); row['trackingNumber']=str(d.get('trackingNumber') or '').strip()\n"""
    insert="""                row['shippingCompany']=str(d.get('shippingCompany') or '').strip(); row['trackingNumber']=str(d.get('trackingNumber') or '').strip()\n                # admin-order-address-save-v2\n                if isinstance(d.get('shippingAddress'),dict):\n                    incoming=d.get('shippingAddress') or {}\n                    shipping_address={\n                        'recipientName':str(incoming.get('recipientName') or '').strip(),\n                        'recipientPhone':str(incoming.get('recipientPhone') or '').strip(),\n                        'country':str(incoming.get('country') or '').strip(),\n                        'city':str(incoming.get('city') or '').strip(),\n                        'district':str(incoming.get('district') or '').strip(),\n                        'postalCode':str(incoming.get('postalCode') or '').strip(),\n                        'addressLine':str(incoming.get('addressLine') or '').strip(),\n                        'notes':str(incoming.get('notes') or '').strip(),\n                    }\n                    if not shipping_address['country'] or not shipping_address['city'] or not shipping_address['addressLine']:\n                        self.sendj({'error':'عنوان التسليم غير مكتمل: الدولة والمدينة والعنوان بالتفصيل مطلوبة','code':'shipping_address_incomplete'},400); return\n                    row['shippingAddress']=shipping_address\n                    row['shippingAddressUpdatedByAdminAt']=datetime.datetime.now().isoformat()\n                    pid=str(row.get('participantId') or '')\n                    if pid:\n                        people=load_people(); person=next((x for x in people if str(x.get('id') or '')==pid),None)\n                        if person is not None:\n                            person['shippingAddress']=dict(shipping_address)\n                            person['updated']=datetime.datetime.now().isoformat()\n                            save_json(PEOPLE,{'participants':people})\n"""
    if needle not in s:
        raise RuntimeError('shipping endpoint marker not found')
    s=s.replace(needle,insert,1)
    server.write_text(s,encoding='utf-8')

# --- styles for the inline editor.
c=styles.read_text(encoding='utf-8')
if 'admin-order-address-editor-v2' not in c:
    c += r'''

/* admin-order-address-editor-v2 */
.order-address-editor{margin:14px 0;padding:14px;border:2px solid #d8b45b;border-radius:14px;background:#fff9e8;box-shadow:0 8px 24px #0000000d}.order-address-editor[hidden]{display:none!important}.order-address-editor.attention{box-shadow:0 0 0 4px #d8b45b35,0 12px 28px #00000012}.order-address-editor h4{margin:0 0 6px;color:#0b2a52}.order-address-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.order-address-grid .wide{grid-column:1/-1}.order-address-grid input,.order-address-grid textarea{width:100%;margin:0;padding:10px;border:1px solid #cfd8e3;border-radius:9px;background:white}.order-address-grid textarea{min-height:70px;resize:vertical}.order-address-editor .actions{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}@media(max-width:760px){.order-address-grid{grid-template-columns:1fr}.order-address-grid .wide{grid-column:1}}
'''
    styles.write_text(c,encoding='utf-8')

print('patched shipping address activation v2')
