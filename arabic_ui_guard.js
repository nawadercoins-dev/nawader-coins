/* R9.8 SAFE UI GUARD — stylesheet fallback only.
   The administration page loads R9.8 directly. This guard only ensures the style exists
   without touching business data, permissions, feature toggles, routes or order states. */
(() => {
  "use strict";
  try {
    if (!String(location.pathname || "").startsWith("/admin")) return;
    if (document.querySelector('link[href*="admin-ui-stability-r9.8.css"]')) return;
    const link = document.createElement("link");
    link.id = "admin-ui-stability-r9-8";
    link.rel = "stylesheet";
    link.href = "/admin/admin-ui-stability-r9.8.css?v=5.6.2-r9.8";
    link.dataset.safeUiOnly = "true";
    document.head.appendChild(link);
  } catch (_) {
    /* The guard must never block the administration page. */
  }
})();
