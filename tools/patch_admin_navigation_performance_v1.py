from pathlib import Path

PATH = Path('admin/app.js')
text = PATH.read_text(encoding='utf-8')
original = text

old_all = '''async function all() {
  return ((await api("/api/items")).items || []).filter(i => !['archived','removed'].includes(i.moderationStatus||'') && !i.ownerArchived);
}
async function archivedItems(){ return (await api('/api/archive/items')).items || []; }
async function put(x) {
  return api("/api/item", {
    method: "POST",
    body: JSON.stringify({ item: x }),
  });
}
async function del(id) {
  return api("/api/item/" + encodeURIComponent(id), { method: "DELETE" });
}
'''
new_all = '''const ADMIN_ITEMS_CACHE_TTL_MS = 12000;
let adminItemsCache = { rows: null, at: 0, pending: null };
function invalidateAdminItemsCache() {
  adminItemsCache.rows = null;
  adminItemsCache.at = 0;
}
async function all(force = false) {
  const now = Date.now();
  if (!force && Array.isArray(adminItemsCache.rows) && now - adminItemsCache.at < ADMIN_ITEMS_CACHE_TTL_MS)
    return adminItemsCache.rows.slice();
  if (!force && adminItemsCache.pending)
    return (await adminItemsCache.pending).slice();
  const pending = api("/api/items")
    .then(r => ((r.items || []).filter(i => !['archived','removed'].includes(i.moderationStatus||'') && !i.ownerArchived)))
    .then(rows => {
      adminItemsCache.rows = rows;
      adminItemsCache.at = Date.now();
      return rows;
    });
  adminItemsCache.pending = pending;
  try {
    return (await pending).slice();
  } finally {
    if (adminItemsCache.pending === pending) adminItemsCache.pending = null;
  }
}
async function archivedItems(){ return (await api('/api/archive/items')).items || []; }
async function put(x) {
  const result = await api("/api/item", {
    method: "POST",
    body: JSON.stringify({ item: x }),
  });
  invalidateAdminItemsCache();
  return result;
}
async function del(id) {
  const result = await api("/api/item/" + encodeURIComponent(id), { method: "DELETE" });
  invalidateAdminItemsCache();
  return result;
}
'''
if old_all not in text:
    raise SystemExit('Expected all()/put()/del() block not found; aborting without changes.')
text = text.replace(old_all, new_all, 1)

old_refresh = '    let allRows = await all();\n'
new_refresh = '    let allRows = await all(force);\n'
if old_refresh not in text:
    raise SystemExit('Expected refresh all() call not found; aborting without changes.')
text = text.replace(old_refresh, new_refresh, 1)

# Navigation should reuse a very recent item snapshot. Explicit refresh buttons and writes still force a fresh read.
nav_patterns = [
    ('        await refresh(true);\n      if (b.dataset.v === "participants")',
     '        await refresh(false);\n      if (b.dataset.v === "participants")'),
    ('      await refresh(true);\n    if (vw === "participants")',
     '      await refresh(false);\n    if (vw === "participants")'),
    ("  lastDataToken=''; await refresh(true);\n  const id=document.querySelector('.view.active')?.id||'';",
     "  lastDataToken=''; await refresh(false);\n  const id=document.querySelector('.view.active')?.id||'';"),
]
for old, new in nav_patterns:
    if old not in text:
        raise SystemExit('Expected navigation pattern not found; aborting without changes: ' + old[:80])
    text = text.replace(old, new, 1)

if text == original:
    raise SystemExit('No changes produced.')
PATH.write_text(text, encoding='utf-8')
print('ADMIN_NAV_PERFORMANCE_PATCH_OK')
print('cache_ttl_ms=', ADMIN_ITEMS_CACHE_TTL_MS if 'ADMIN_ITEMS_CACHE_TTL_MS' in globals() else 12000)
