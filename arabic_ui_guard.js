/* R9.8 SAFE UI GUARD — non-destructive UX fallbacks.
   The administration page loads R9.8 directly. This file never resets business data,
   permissions, feature toggles, inventory values, prices or order states. */
(() => {
  "use strict";
  try {
    if (!String(location.pathname || "").startsWith("/admin")) return;

    if (!document.querySelector('link[href*="admin-ui-stability-r9.8.css"]')) {
      const link = document.createElement("link");
      link.id = "admin-ui-stability-r9-8";
      link.rel = "stylesheet";
      link.href = "/admin/admin-ui-stability-r9.8.css?v=5.6.2-r9.8";
      link.dataset.safeUiOnly = "true";
      document.head.appendChild(link);
    }

    /* Dynamic live-sale buttons use data-go=orders after render; route them safely. */
    document.addEventListener("click", (e) => {
      const go = e.target.closest?.('[data-go="orders"]');
      if (!go) return;
      const nav = document.querySelector('nav button[data-v="orders"]');
      if (!nav || go === nav) return;
      e.preventDefault();
      nav.click();
    });

    /* "Other" shipping company keeps the list clean while allowing any carrier. */
    document.addEventListener("change", (e) => {
      const sel = e.target.closest?.('select[id^="shipco-"]');
      if (!sel || sel.value !== "أخرى") return;
      const custom = String(prompt("اكتب اسم شركة الشحن:", "") || "").trim();
      if (!custom) { sel.value = ""; return; }
      let opt = [...sel.options].find(o => o.value === custom);
      if (!opt) {
        opt = document.createElement("option");
        opt.value = custom;
        opt.textContent = custom;
        sel.insertBefore(opt, [...sel.options].find(o => o.value === "أخرى") || null);
      }
      sel.value = custom;
    });
  } catch (_) {
    /* The guard must never block the administration page. */
  }
})();
