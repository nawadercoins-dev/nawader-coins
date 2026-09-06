from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA_ENTRY = ROOT / 'public' / 'data_entry.html'
ADMIN_APP = ROOT / 'admin' / 'app.js'
SERVER = ROOT / 'server.py'

# --- 1) Data-entry UX -------------------------------------------------------
text = DATA_ENTRY.read_text(encoding='utf-8')
css_marker = '/* data-entry-ux-v1 */'
if css_marker not in text:
    css = r'''
/* data-entry-ux-v1 */
/* واجهة إدخال أبسط: الصور في الوسط، أحجام ثابتة، وتقليل التشتيت البصري. */
.vault-selected-card,.vault-pick,.batch-card,.row{overflow:hidden}
.vault-selected-card img,.vault-pick img,.thumbs img,.batch-card .thumbs img{
  object-fit:contain!important;object-position:center!important;background:#06111d
}
.vault-selected-card img{height:150px!important}
.vault-pick img{height:135px!important}
.thumbs{justify-content:center!important}
.form-grid>label,.form-grid>.wide{min-width:0}
.price-table input{text-align:center;font-weight:800}
.smart-price-help{margin-top:6px;color:#b9c4d1;font-size:.84rem;line-height:1.6}
.quick-entry-note{margin:10px 0 14px;padding:10px 12px;border:1px solid #425b73;border-radius:12px;background:#0d2034;color:#d9e2ea}
.quick-entry-note b{color:#f0d995}
/* في الصفحة الرئيسية نعرض المهم لمسؤول الإدخال فقط؛ الحالات الأخرى تبقى في السجلات. */
.stats .stat:nth-child(n+3){display:none}
.stats{grid-template-columns:repeat(2,minmax(0,1fr))!important}
@media(max-width:560px){
  .wrap{padding:10px}.panel{border-radius:14px}.top{justify-content:center;text-align:center}
  .links{width:100%;justify-content:center}.mode-switch{width:100%}.mode-switch .btn{flex:1}
  .vault-selected{grid-template-columns:repeat(2,minmax(0,1fr))}
  .vault-selected-card img{height:125px!important}
}
'''
    if '</style>' not in text:
        raise RuntimeError('data_entry.html: closing style tag not found')
    text = text.replace('</style>', css + '\n</style>', 1)

# Add a concise operating hint below the store banner.
hint_marker = 'data-entry-quick-note-v1'
if hint_marker not in text:
    anchor = '    <div class="mode-switch">'
    hint = '''    <div class="quick-entry-note" id="data-entry-quick-note-v1"><b>المسار السريع:</b> اختر صورة من خزينة الصور ← ينتقل سعر الشراء تلقائيًا ← يحسب النظام سعر البيع افتراضيًا بربح 100% ← عدّل السعر للأعلى أو للأسفل إن رغبت ← أرسل للاعتماد.</div>\n\n'''
    if anchor not in text:
        raise RuntimeError('data_entry.html: mode switch anchor not found')
    text = text.replace(anchor, hint + anchor, 1)

# Add editable profit percentage beside purchase/sale prices.
profit_marker = 'id="profitPercent"'
if profit_marker not in text:
    sale_row = '<tr><td><b>سعر البيع</b></td><td><input id="salePrice" type="number" min="0" step="0.01" placeholder="0.00"></td></tr>'
    replacement = sale_row + '''\n            <tr><td><b>نسبة الربح الافتراضية</b></td><td><input id="profitPercent" type="number" min="-100" step="1" value="100"><div class="smart-price-help">100% = سعر البيع ضعف سعر الشراء. يمكنك تغيير النسبة أو تعديل سعر البيع مباشرة.</div></td></tr>'''
    if sale_row not in text:
        raise RuntimeError('data_entry.html: sale price row not found')
    text = text.replace(sale_row, replacement, 1)

# Preserve purchasePrice metadata when images move from the vault into a collectible.
old_clone = "function cloneImages(items){return (items||[]).map(x=>({id:String(x.id||''),url:String(x.url||'')})).filter(x=>x.id||x.url)}"
new_clone = "function cloneImages(items){return (items||[]).map(x=>({id:String(x.id||''),url:String(x.url||''),purchasePrice:Number(x.purchasePrice||0)})).filter(x=>x.id||x.url)}"
if old_clone in text:
    text = text.replace(old_clone, new_clone, 1)
elif new_clone not in text:
    raise RuntimeError('data_entry.html: cloneImages function not found')

# Show the stored purchase price on selected vault images.
old_card = "<span class=\"vault-role\">${esc(imageRole(i))}</span><img src=\"${esc(x.url)}\" alt=\"\"><button type=\"button\" class=\"vault-remove\""
new_card = "<span class=\"vault-role\">${esc(imageRole(i))}</span><img src=\"${esc(x.url)}\" alt=\"\">${Number(x.purchasePrice||0)>0?`<div class=\"muted\" style=\"text-align:center;margin-top:5px\">شراء: ${Number(x.purchasePrice).toLocaleString('ar-SA')} ر.س</div>`:''}<button type=\"button\" class=\"vault-remove\""
if old_card in text:
    text = text.replace(old_card, new_card, 1)
elif 'شراء: ${Number(x.purchasePrice)' not in text:
    raise RuntimeError('data_entry.html: selected image card template not found')

# Smart price behaviour and automatic purchase-price import from the vault.
js_marker = '// data-entry-smart-pricing-v1'
if js_marker not in text:
    js = r'''
// data-entry-smart-pricing-v1
let salePriceManuallyEdited=false;
let lastVaultPurchaseApplied=null;
function calcSuggestedSale(force=false){
  const purchase=Number($('purchase')?.value||0), pct=Number($('profitPercent')?.value||100);
  if(!purchase || (!$('salePrice')))return;
  if(!force && salePriceManuallyEdited && Number($('salePrice').value||0)>0)return;
  const suggested=Math.max(0,purchase*(1+pct/100));
  $('salePrice').value=(Math.round(suggested*100)/100).toString();
}
function applyPurchaseFromVault(){
  const prices=(currentImages.items||[]).map(x=>Number(x.purchasePrice||0)).filter(x=>x>0);
  if(!prices.length)return;
  const first=prices[0];
  const purchaseEl=$('purchase');
  if(!purchaseEl)return;
  const current=Number(purchaseEl.value||0);
  if(!current || current===Number(lastVaultPurchaseApplied||0)){
    purchaseEl.value=String(first);
    lastVaultPurchaseApplied=first;
    salePriceManuallyEdited=false;
    calcSuggestedSale(true);
  }
}
$('purchase')?.addEventListener('input',()=>{salePriceManuallyEdited=false;calcSuggestedSale(true)});
$('profitPercent')?.addEventListener('input',()=>{salePriceManuallyEdited=false;calcSuggestedSale(true)});
$('salePrice')?.addEventListener('input',()=>{salePriceManuallyEdited=true});
const _renderSelectedImages=renderSelectedImages;
renderSelectedImages=function(){_renderSelectedImages();applyPurchaseFromVault()};
'''
    if '\ninit();\n</script>' not in text:
        raise RuntimeError('data_entry.html: init anchor not found')
    text = text.replace('\ninit();\n</script>', '\n' + js + '\ninit();\n</script>', 1)

DATA_ENTRY.write_text(text, encoding='utf-8')

# --- 2) Administration image-vault upload: one purchase price per image ------
app = ADMIN_APP.read_text(encoding='utf-8')
admin_marker = '// image-vault-purchase-price-v1'
if admin_marker not in app:
    needle = "      const f=await prepareVaultImageUpload(original);\n      const r=await fetch('/api/image-vault/upload',{method:'POST',credentials:'same-origin',headers:{'Content-Type':f.type||original.type||'image/jpeg','X-Original-Name':encodeURIComponent(original.name||'image')},body:f});"
    repl = "      const f=await prepareVaultImageUpload(original);\n      // image-vault-purchase-price-v1\n      const rawPurchase=window.prompt(`سعر شراء الصورة ${i+1} من ${files.length} — ${original.name||'الصورة'} (ر.س)`, '');\n      if(rawPurchase===null)throw new Error('تم إلغاء الرفع قبل حفظ سعر الشراء.');\n      const purchasePrice=Number(String(rawPurchase).replace(/,/g,'.').trim());\n      if(!Number.isFinite(purchasePrice)||purchasePrice<0)throw new Error('سعر الشراء غير صحيح. أدخل صفرًا أو رقمًا موجبًا.');\n      const r=await fetch('/api/image-vault/upload',{method:'POST',credentials:'same-origin',headers:{'Content-Type':f.type||original.type||'image/jpeg','X-Original-Name':encodeURIComponent(original.name||'image'),'X-Purchase-Price':String(purchasePrice)},body:f});"
    if needle not in app:
        raise RuntimeError('admin/app.js: vault upload request not found')
    app = app.replace(needle, repl, 1)
ADMIN_APP.write_text(app, encoding='utf-8')

# --- 3) Server: store purchasePrice on each image-vault record ----------------
server = SERVER.read_text(encoding='utf-8')
server_marker = '# image-vault-purchase-price-v1'
if server_marker not in server:
    start = server.find("        if p=='/api/image-vault/upload':")
    end = server.find("        try: d=self.body()", start)
    if start < 0 or end < 0:
        raise RuntimeError('server.py: image vault upload block not found')
    block = server[start:end]
    ctype_line = "                ctype=(self.headers.get('Content-Type') or '').lower(); ext='.jpg'"
    if ctype_line not in block:
        raise RuntimeError('server.py: vault content-type line not found')
    price_parse = "                # image-vault-purchase-price-v1\n                try: purchase_price=max(0,float(str(self.headers.get('X-Purchase-Price') or '0').strip() or 0))\n                except Exception: purchase_price=0.0\n"
    block = block.replace(ctype_line, price_parse + ctype_line, 1)
    # Add purchasePrice to the first newly-created available vault row.
    block2, count = re.subn(r"('status'\s*:\s*'available')", r"\1,'purchasePrice':purchase_price", block, count=1)
    if count != 1:
        raise RuntimeError('server.py: available vault row not found')
    server = server[:start] + block2 + server[end:]
SERVER.write_text(server, encoding='utf-8')

# --- 4) Upgrade report --------------------------------------------------------
report = ROOT / 'V5.6.4_DATA_ENTRY_VAULT_PRICING_UX_AR.md'
report.write_text('''# V5.6.4 — ترقية مسؤول إدخال البيانات وخزينة الصور\n\nتم تنفيذ الآتي:\n\n- خزينة الصور: لكل صورة سعر شراء مستقل حتى عند رفع عدة صور دفعة واحدة.\n- مسؤول إدخال البيانات: سعر الشراء ينتقل مع الصورة من الخزينة.\n- التسعير الذكي: افتراضي 100% ربح (مثال: شراء 50 → بيع 100)، مع إمكانية تعديل النسبة أو سعر البيع يدويًا للأعلى أو للأسفل.\n- تبسيط الواجهة: إبراز المسودات وبانتظار الاعتماد فقط، مع بقاء بقية الحالات في السجلات.\n- توسيط الصور وتوحيد طريقة عرضها داخل البطاقات على الجوال والكمبيوتر.\n- منع تكرار ملف الصورة: الصور تظل مرتبطة بسجل الخزينة وتنتقل للمقتنى بمرجعها.\n- لا يوجد نشر تلقائي من دور مسؤول إدخال البيانات؛ الإرسال يبقى للاعتماد.\n\n## التحقق\n\nيجب أن يجتاز الإصدار: `py_compile` للخادم، وفحص وجود علامات الترقية، و`git diff --check`.\n''', encoding='utf-8')

print('V5.6.4 data-entry/vault pricing UX patch applied successfully.')
