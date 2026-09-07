/* R9.8 runtime UX layer.
   Purpose: layout, navigation separation and shipping-entry UX only.
   It does not mutate stored permissions, feature toggles, inventory data, prices or order states. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const SHIPPING = ["سمسا","أرامكس","SPL البريد السعودي","ناقل","DHL","FedEx","UPS","J&T","iMile","أخرى"];

  function activateView(id, clickedBtn) {
    document.querySelectorAll("main .view").forEach(v => v.classList.toggle("active", v.id === id));
    document.querySelectorAll("nav button[data-v]").forEach(b => b.classList.toggle("active", b === clickedBtn));
  }

  function installLiveSalesSection() {
    const nav = document.querySelector("nav");
    const liveBtn = nav?.querySelector('button[data-v="live-auctions"]');
    const listBtn = nav?.querySelector('button[data-v="list"]');
    if (listBtn) listBtn.textContent = "السجل العام";

    let salesBtn = nav?.querySelector('button[data-v="live-sales"]');
    if (!salesBtn && liveBtn) {
      salesBtn = document.createElement("button");
      salesBtn.type = "button";
      salesBtn.dataset.v = "live-sales";
      salesBtn.textContent = "مبيعات البث المباشر";
      liveBtn.insertAdjacentElement("afterend", salesBtn);
    }

    let section = $("live-sales");
    if (!section) {
      section = document.createElement("section");
      section.id = "live-sales";
      section.className = "view";
      section.innerHTML = `
        <div class="panel">
          <div class="auction-title-row">
            <div>
              <h2>🧺 مبيعات البث المباشر</h2>
              <p class="muted">قسم تشغيلي مستقل لنتائج البث. السجل العام للتوثيق فقط؛ أما السداد والتجهيز والشحن فتتم من هنا ومن الطلبات والشحن.</p>
            </div>
            <div class="actions">
              <button type="button" id="r98OpenOrders" class="gold-action">📦 فتح الطلبات والشحن</button>
              <button type="button" id="r98RefreshLiveSales" class="ghost">↻ تحديث</button>
            </div>
          </div>
          <div class="panel" style="margin:12px 0;background:#fffaf0">
            <b>المسار المعتمد:</b> إرساء المزاد ← بانتظار السداد ← تم السداد ← التجهيز ← الشحن ← الإكمال. لا تستخدم صفحة السجل العام لتنفيذ هذه الإجراءات.
          </div>
          <div id="r98LiveResultsHost"></div>
        </div>`;
      const orders = $("orders");
      if (orders) orders.insertAdjacentElement("beforebegin", section);
      else document.querySelector("main")?.appendChild(section);
    }

    const basket = $("liveResultsBasket");
    const host = $("r98LiveResultsHost");
    if (basket && host && basket.parentElement !== host) {
      basket.querySelector("h3") && (basket.querySelector("h3").textContent = "نتائج ومبيعات البث المباشر");
      const p = basket.querySelector("p.muted");
      if (p) p.textContent = "تظهر هنا نتائج الفوز المعلقة حتى اكتمال السداد والشحن ثم إقفال البطاقة.";
      host.appendChild(basket);
    }

    salesBtn?.addEventListener("click", async (e) => {
      e.preventDefault();
      activateView("live-sales", salesBtn);
      try { if (typeof window.renderLiveAuctions === "function") await window.renderLiveAuctions(); } catch (_) {}
      enhanceLiveResultActions();
    });
    $("r98RefreshLiveSales")?.addEventListener("click", async () => {
      try { if (typeof window.renderLiveAuctions === "function") await window.renderLiveAuctions(); } catch (_) {}
      enhanceLiveResultActions();
    });
    $("r98OpenOrders")?.addEventListener("click", () => {
      const b = document.querySelector('nav button[data-v="orders"]');
      b?.click();
    });
  }

  function wrapGeneralRecords() {
    try {
      if (typeof window.renderList !== "function" || window.renderList.__r98Wrapped) return;
      const original = window.renderList;
      const wrapped = function(rows) {
        const safe = Array.isArray(rows)
          ? rows.filter(i => String(i?.sourceChannel || "") !== "live_camera")
          : rows;
        return original.call(this, safe);
      };
      wrapped.__r98Wrapped = true;
      window.renderList = wrapped;
    } catch (_) {}
  }

  function shippingSelectFromInput(input) {
    if (!input || input.tagName !== "INPUT" || input.dataset.r98Converted === "1") return;
    const current = String(input.value || "").trim();
    const select = document.createElement("select");
    select.id = input.id;
    select.className = input.className;
    select.dataset.r98ShippingCompany = "1";
    const values = ["", ...SHIPPING];
    if (current && !values.includes(current)) values.splice(values.length - 1, 0, current);
    values.forEach(v => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v || "اختر شركة الشحن";
      if (v === current) o.selected = true;
      select.appendChild(o);
    });
    input.dataset.r98Converted = "1";
    input.replaceWith(select);
  }

  function enhanceShippingFields(root = document) {
    root.querySelectorAll?.('input[id^="shipco-"]').forEach(shippingSelectFromInput);
    root.querySelectorAll?.('input[id^="track-"]').forEach(el => {
      if (!el.placeholder || el.placeholder === "رقم التتبع") el.placeholder = "رقم التتبع / مرجع الشحنة";
    });
  }

  function enhanceLiveResultActions() {
    document.querySelectorAll("#liveResultsList .live-winner-admin-card").forEach(card => {
      const actions = card.querySelector(".actions");
      if (!actions || actions.querySelector(".r98-orders-btn")) return;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "gold-action r98-orders-btn";
      b.textContent = "📦 متابعة السداد والشحن";
      b.addEventListener("click", () => document.querySelector('nav button[data-v="orders"]')?.click());
      actions.insertBefore(b, actions.firstChild);
      const close = [...actions.querySelectorAll("button")].find(x => /اعتماد وإقفال بطاقة الفوز/.test(x.textContent || ""));
      if (close) close.textContent = "إقفال بطاقة الفوز بعد اكتمال المعالجة";
    });
  }

  function installObservers() {
    const orders = $("ordersList");
    if (orders) new MutationObserver(() => enhanceShippingFields(orders)).observe(orders, {childList:true,subtree:true});
    const live = $("r98LiveResultsHost") || $("liveResultsBasket");
    if (live) new MutationObserver(() => enhanceLiveResultActions()).observe(live, {childList:true,subtree:true});
  }

  function boot() {
    if (!String(location.pathname || "").startsWith("/admin")) return;
    installLiveSalesSection();
    wrapGeneralRecords();
    enhanceShippingFields(document);
    enhanceLiveResultActions();
    installObservers();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, {once:true});
  else boot();
})();
