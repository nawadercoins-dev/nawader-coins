from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
html_path=ROOT/'admin'/'index.html'
js_path=ROOT/'admin'/'app.js'
html=html_path.read_text(encoding='utf-8')
js=js_path.read_text(encoding='utf-8')

# 1) Directly load final admin stylesheet so browser cache/guard indirection cannot hide it.
needle='<link rel="stylesheet" href="/admin/styles.css?v=5.6.2-r4-lightbox3" />'
extra='\n    <link rel="stylesheet" href="/admin/admin-ui-stability-r9.8.css?v=5.6.2-r9.8" />'
if 'admin-ui-stability-r9.8.css' not in html:
    assert needle in html, 'main admin stylesheet link not found'
    html=html.replace(needle,needle+extra,1)

# 2) Keep the general record area documentary only; live-camera operational sales get their own area.
html=html.replace('><button data-v="live-auctions">البث المباشر 🔴</button><button data-v="list">السجل</button',
                  '><button data-v="live-auctions">البث المباشر 🔴</button><button data-v="live-sales">مبيعات البث المباشر</button><button data-v="list">السجل العام</button',1)

old_basket='<div id="liveResultsBasket" class="panel" style="margin-top:14px"><h3>🧺 سلة المزادات المباشرة</h3><p class="muted">نتائج الفوز تبقى هنا وفي واجهة المشاهدين حتى تعتمد الإدارة إقفالها.</p><div id="liveResultsList" class="participants-list"></div></div>'
if old_basket in html:
    html=html.replace(old_basket,'',1)

live_sales='''      <section id="live-sales" class="view">\n        <div class="panel">\n          <div class="auction-title-row">\n            <div><h2>🧺 مبيعات البث المباشر</h2><p class="muted">مسار تشغيلي مستقل لنتائج البث: فوز، سداد، تجهيز وشحن. السجل العام يبقى للتوثيق فقط.</p></div>\n            <div class="actions"><button type="button" class="ghost dashboard-go" data-go="orders">📦 فتح الطلبات والشحن</button><button type="button" id="refreshLiveSales" class="ghost">↻ تحديث</button></div>\n          </div>\n          <div class="panel" style="margin:12px 0;background:#fffaf0"><b>المسار المعتمد:</b> بعد الإرساء ينشأ الطلب تلقائيًا. بعد اعتماد السداد ينتقل إلى التجهيز، ويمكن إرساله مباشرة إلى الشحن من دورة الطلب دون بقائه في السجل العام.</div>\n          <div id="liveResultsList" class="live-sales-list"></div>\n        </div>\n      </section>\n'''
if 'id="live-sales"' not in html:
    marker='      <section id="orders" class="view">'
    assert marker in html, 'orders section marker not found'
    html=html.replace(marker,live_sales+marker,1)

# 3) Hide camera-created live inventory records from the general records page only.
old='function renderList(a) {\n  a=filterAdminItems(a);'
new='function renderList(a) {\n  a=filterAdminItems(a).filter((i) => String(i?.sourceChannel || "") !== "live_camera");'
if old in js:
    js=js.replace(old,new,1)
elif new not in js:
    raise AssertionError('renderList signature not found')

# 4) Reuse live-auction renderer for the separate live-sales page and refresh button.
old_listener='document.querySelectorAll(\'[data-v="live-auctions"],.dashboard-go[data-go="live-auctions"]\').forEach(b=>b.addEventListener(\'click\',renderLiveAuctions));'
new_listener='document.querySelectorAll(\'[data-v="live-auctions"],[data-v="live-sales"],.dashboard-go[data-go="live-auctions"],.dashboard-go[data-go="live-sales"]\').forEach(b=>b.addEventListener(\'click\',renderLiveAuctions));\n$("refreshLiveSales")?.addEventListener("click",renderLiveAuctions);'
if old_listener in js:
    js=js.replace(old_listener,new_listener,1)
elif new_listener not in js:
    raise AssertionError('live renderer listener not found')

# 5) Make live result card operational: explicit order/shipping path, while keeping safe close action.
old_actions='<div class="actions"><button class="gold-action" onclick="liveControl(\'${s.id}\',\'clear-result\')">اعتماد وإقفال بطاقة الفوز</button><a class="public-link" href="/live-auction?session=${encodeURIComponent(s.id)}" target="_blank">معاينة ما يراه الزائر</a></div>'
new_actions='<div class="actions"><button class="gold-action dashboard-go" data-go="orders">📦 متابعة السداد والشحن</button><button class="ghost" onclick="liveControl(\'${s.id}\',\'clear-result\')">إقفال بطاقة الفوز بعد اكتمال المعالجة</button><a class="public-link" href="/live-auction?session=${encodeURIComponent(s.id)}" target="_blank">معاينة ما يراه الزائر</a></div>'
if old_actions in js:
    js=js.replace(old_actions,new_actions,1)

# 6) Shipping company list: fixed names + Other, preserving existing stored value.
old_fields='<div class="order-shipping-fields"><input id="shipfee-${o.id}" type="number" min="0" step="0.01" value="${Number(o.shippingFee || 0)}" placeholder="مبلغ الشحن (0 = مجاني)" ${o.paymentStatus === "paid" ? "disabled" : ""}><input id="shipco-${o.id}" value="${esc(o.shippingCompany || "")}" placeholder="شركة الشحن"><input id="track-${o.id}" value="${esc(o.trackingNumber || "")}" placeholder="رقم التتبع"></div>'
new_fields='<div class="order-shipping-fields"><input id="shipfee-${o.id}" type="number" min="0" step="0.01" value="${Number(o.shippingFee || 0)}" placeholder="مبلغ الشحن (0 = مجاني)" ${o.paymentStatus === "paid" ? "disabled" : ""}><select id="shipco-${o.id}">${shippingCompanyOptions(o.shippingCompany || "")}</select><input id="track-${o.id}" value="${esc(o.trackingNumber || "")}" placeholder="رقم التتبع / مرجع الشحنة"></div>'
if old_fields in js:
    js=js.replace(old_fields,new_fields,1)
elif 'shippingCompanyOptions(o.shippingCompany' not in js:
    raise AssertionError('order shipping fields not found')

helper='''\nconst SHIPPING_COMPANIES=["سمسا","أرامكس","SPL البريد السعودي","ناقل","DHL","FedEx","UPS","J&T","iMile","أخرى"];\nfunction shippingCompanyOptions(current=""){\n  const c=String(current||"").trim();\n  const known=SHIPPING_COMPANIES.includes(c);\n  const rows=["",...SHIPPING_COMPANIES];\n  if(c&&!known) rows.splice(rows.length-1,0,c);\n  return rows.map(x=>`<option value="${esc(x)}" ${x===c?"selected":""}>${x||"اختر شركة الشحن"}</option>`).join("");\n}\n'''
if 'const SHIPPING_COMPANIES=' not in js:
    anchor='function paymentOrderLabel(o) {'
    pos=js.find(anchor)
    if pos<0:
        # robust fallback before order card renderer
        anchor='function orderCard(o) {'
        pos=js.find(anchor)
    assert pos>=0, 'shipping helper anchor not found'
    js=js[:pos]+helper+js[pos:]

# 7) Better source labels, including live auction.
js=js.replace('${o.source === "auction" ? "مزاد" : "السوق العام"}', '${o.source === "live_auction" ? "بث مباشر" : (o.source === "auction" ? "مزاد" : "السوق العام")}', 1)

html_path.write_text(html,encoding='utf-8')
js_path.write_text(js,encoding='utf-8')
print('R9.8 patch applied safely')
