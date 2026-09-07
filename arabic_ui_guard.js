/* R9.8 SAFE UI GUARD.
   Loads only administration presentation/UX helpers. Business data, permissions,
   feature toggles, order states and stored values are not reset by this guard. */
(() => {
  "use strict";
  try {
    if (!String(location.pathname || "").startsWith("/admin")) return;

    if (!document.getElementById("admin-ui-stability-r9-8")) {
      const link = document.createElement("link");
      link.id = "admin-ui-stability-r9-8";
      link.rel = "stylesheet";
      link.href = "/admin/admin-ui-stability-r9.8.css?v=5.6.2-r9.8";
      link.dataset.safeUiOnly = "true";
      document.head.appendChild(link);
    }

    if (!document.getElementById("admin-runtime-r9-8")) {
      const script = document.createElement("script");
      script.id = "admin-runtime-r9-8";
      script.src = "/admin/admin-r9.8-runtime.js?v=5.6.2-r9.8";
      script.defer = true;
      script.dataset.safeUxOnly = "true";
      document.head.appendChild(script);
    }
  } catch (_) {
    /* The guard must never block the administration page. */
  }
})();
