/* R9.7 SAFE UI GUARD — presentation only.
   Never mutates business data, permissions, checkbox values, task state, routes, or API calls. */
(() => {
  "use strict";
  try {
    if (!String(location.pathname || "").startsWith("/admin")) return;
    if (document.getElementById("admin-ui-stability-r9-7")) return;

    const link = document.createElement("link");
    link.id = "admin-ui-stability-r9-7";
    link.rel = "stylesheet";
    link.href = "/admin/admin-ui-stability-r9.7.css?v=5.6.2-r9.7";
    link.dataset.safeUiOnly = "true";
    document.head.appendChild(link);
  } catch (_) {
    /* UI guard must never block the administration page. */
  }
})();
