from pathlib import Path

p = Path('admin/app.js')
s = p.read_text(encoding='utf-8')

old_record = '<div><span>حالة الحفظ</span><b>${esc(i.condition || "—")}</b></div><div class="quantity-stack">'
new_record = '<div><span>حالة الحفظ</span><b>${esc(i.condition || "—")}</b></div><div class="record-price-stack"><span>الأسعار</span><b><em>سعر الشراء</em><strong>${Number(i.purchase || 0) > 0 ? money(i.purchase) : "—"}</strong></b><b><em>سعر البيع المتوقع</em><strong>${Number(i.expectedPrice || 0) > 0 ? money(i.expectedPrice) : "—"}</strong></b></div><div class="quantity-stack">'
if old_record not in s:
    raise SystemExit('record card anchor not found')
s = s.replace(old_record, new_record, 1)

old_warehouse = '<div class="warehouse-item-quantities"><span>التصنيف <b>${classification}</b></span><span>الإجمالي <b>${x.total}</b></span>'
new_warehouse = '<div class="warehouse-item-prices"><span>سعر الشراء <b>${Number(x._source?.purchase || 0) > 0 ? money(x._source.purchase) : "—"}</b></span><span>سعر البيع المتوقع <b>${Number(x._source?.expectedPrice || 0) > 0 ? money(x._source.expectedPrice) : "—"}</b></span></div><div class="warehouse-item-quantities"><span>التصنيف <b>${classification}</b></span><span>الإجمالي <b>${x.total}</b></span>'
if old_warehouse not in s:
    raise SystemExit('warehouse card anchor not found')
s = s.replace(old_warehouse, new_warehouse, 1)

p.write_text(s, encoding='utf-8')
print('V5.6.6 admin price ordering applied')
