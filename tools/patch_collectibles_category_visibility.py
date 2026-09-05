from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_HTML = ROOT / 'admin' / 'index.html'
ADMIN_JS = ROOT / 'admin' / 'app.js'
SERVER = ROOT / 'server.py'
VISIBILITY = ROOT / 'public' / 'section_visibility.js'
COLLECTIBLES = ROOT / 'public' / 'collectibles_home.html'
MARKET_JS = ROOT / 'public' / 'public_market.js'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


# 1) Admin UI: add only the missing collectibles category switches.
html = ADMIN_HTML.read_text(encoding='utf-8')
anchor = '              <label class="check"><input id="visitorSectionCollectiblesStore" type="checkbox" /> إظهار متجر نوادر المقتنيات</label>\n'
block = anchor + '''              <div style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid #d8c07e"><b>أقسام نوادر المقتنيات</b><div class="muted" style="margin-top:4px">فنتازيا يتحكم بها خيار «إظهار قسم فنتازيا» أعلاه.</div></div>\n              <label class="check"><input id="visitorCollectiblesAntiques" type="checkbox" /> إظهار التحف</label>\n              <label class="check"><input id="visitorCollectiblesPrayerBeads" type="checkbox" /> إظهار السبح</label>\n              <label class="check"><input id="visitorCollectiblesVehiclesModels" type="checkbox" /> إظهار السيارات والمجسمات</label>\n              <label class="check"><input id="visitorCollectiblesAviationMarine" type="checkbox" /> إظهار الطائرات والسفن والقطارات</label>\n              <label class="check"><input id="visitorCollectiblesJewelryStones" type="checkbox" /> إظهار الخواتم والأحجار الكريمة</label>\n              <label class="check"><input id="visitorCollectiblesGames" type="checkbox" /> إظهار الألعاب والمقتنيات</label>\n              <label class="check"><input id="visitorCollectiblesOther" type="checkbox" /> إظهار قسم أخرى</label>\n'''
if 'id="visitorCollectiblesAntiques"' not in html:
    html = replace_once(html, anchor, block, 'admin collectibles category switches')
ADMIN_HTML.write_text(html, encoding='utf-8')


# 2) Admin JS: load/save/confirm the new switches.
js = ADMIN_JS.read_text(encoding='utf-8')
load_anchor = '    if ($("visitorSectionCollectiblesStore")) $("visitorSectionCollectiblesStore").checked = vs.collectiblesStore !== false;\n'
load_block = load_anchor + '''    if ($("visitorCollectiblesAntiques")) $("visitorCollectiblesAntiques").checked = vs.collectiblesAntiques !== false;\n    if ($("visitorCollectiblesPrayerBeads")) $("visitorCollectiblesPrayerBeads").checked = vs.collectiblesPrayerBeads !== false;\n    if ($("visitorCollectiblesVehiclesModels")) $("visitorCollectiblesVehiclesModels").checked = vs.collectiblesVehiclesModels !== false;\n    if ($("visitorCollectiblesAviationMarine")) $("visitorCollectiblesAviationMarine").checked = vs.collectiblesAviationMarine !== false;\n    if ($("visitorCollectiblesJewelryStones")) $("visitorCollectiblesJewelryStones").checked = vs.collectiblesJewelryStones !== false;\n    if ($("visitorCollectiblesGames")) $("visitorCollectiblesGames").checked = vs.collectiblesGames !== false;\n    if ($("visitorCollectiblesOther")) $("visitorCollectiblesOther").checked = vs.collectiblesOther !== false;\n'''
if 'vs.collectiblesAntiques' not in js:
    js = replace_once(js, load_anchor, load_block, 'admin load collectibles switches')

save_anchor = '            collectiblesStore: $("visitorSectionCollectiblesStore") ? !!$("visitorSectionCollectiblesStore").checked : true,\n'
save_block = save_anchor + '''            collectiblesAntiques: $("visitorCollectiblesAntiques") ? !!$("visitorCollectiblesAntiques").checked : true,\n            collectiblesPrayerBeads: $("visitorCollectiblesPrayerBeads") ? !!$("visitorCollectiblesPrayerBeads").checked : true,\n            collectiblesVehiclesModels: $("visitorCollectiblesVehiclesModels") ? !!$("visitorCollectiblesVehiclesModels").checked : true,\n            collectiblesAviationMarine: $("visitorCollectiblesAviationMarine") ? !!$("visitorCollectiblesAviationMarine").checked : true,\n            collectiblesJewelryStones: $("visitorCollectiblesJewelryStones") ? !!$("visitorCollectiblesJewelryStones").checked : true,\n            collectiblesGames: $("visitorCollectiblesGames") ? !!$("visitorCollectiblesGames").checked : true,\n            collectiblesOther: $("visitorCollectiblesOther") ? !!$("visitorCollectiblesOther").checked : true,\n'''
if 'collectiblesAntiques: $("visitorCollectiblesAntiques")' not in js:
    js = replace_once(js, save_anchor, save_block, 'admin save collectibles switches')

confirm_anchor = '      if ($("visitorSectionCollectiblesStore")) $("visitorSectionCollectiblesStore").checked = savedVs.collectiblesStore !== false;\n'
confirm_block = confirm_anchor + '''      if ($("visitorCollectiblesAntiques")) $("visitorCollectiblesAntiques").checked = savedVs.collectiblesAntiques !== false;\n      if ($("visitorCollectiblesPrayerBeads")) $("visitorCollectiblesPrayerBeads").checked = savedVs.collectiblesPrayerBeads !== false;\n      if ($("visitorCollectiblesVehiclesModels")) $("visitorCollectiblesVehiclesModels").checked = savedVs.collectiblesVehiclesModels !== false;\n      if ($("visitorCollectiblesAviationMarine")) $("visitorCollectiblesAviationMarine").checked = savedVs.collectiblesAviationMarine !== false;\n      if ($("visitorCollectiblesJewelryStones")) $("visitorCollectiblesJewelryStones").checked = savedVs.collectiblesJewelryStones !== false;\n      if ($("visitorCollectiblesGames")) $("visitorCollectiblesGames").checked = savedVs.collectiblesGames !== false;\n      if ($("visitorCollectiblesOther")) $("visitorCollectiblesOther").checked = savedVs.collectiblesOther !== false;\n'''
if 'savedVs.collectiblesAntiques' not in js:
    js = replace_once(js, confirm_anchor, confirm_block, 'admin confirm collectibles switches')
ADMIN_JS.write_text(js, encoding='utf-8')


# 3) Server settings: whitelist/persist only these visibility booleans. No auction/order/data logic touched.
server = SERVER.read_text(encoding='utf-8')
default_old = "'fantasia':True,'promotions':True,'announcements':True,'liveAuction':True,'collectiblesStore':True},'fullPublicEnableV493':False}"
default_new = "'fantasia':True,'promotions':True,'announcements':True,'liveAuction':True,'collectiblesStore':True,'collectiblesAntiques':True,'collectiblesPrayerBeads':True,'collectiblesVehiclesModels':True,'collectiblesAviationMarine':True,'collectiblesJewelryStones':True,'collectiblesGames':True,'collectiblesOther':True},'fullPublicEnableV493':False}"
if "'collectiblesAntiques':True" not in server:
    server = replace_once(server, default_old, default_new, 'server defaults')

norm_anchor = "        'collectiblesStore': bool(vis.get('collectiblesStore',True)),\n"
norm_block = norm_anchor + """        'collectiblesAntiques': bool(vis.get('collectiblesAntiques',True)),\n        'collectiblesPrayerBeads': bool(vis.get('collectiblesPrayerBeads',True)),\n        'collectiblesVehiclesModels': bool(vis.get('collectiblesVehiclesModels',True)),\n        'collectiblesAviationMarine': bool(vis.get('collectiblesAviationMarine',True)),\n        'collectiblesJewelryStones': bool(vis.get('collectiblesJewelryStones',True)),\n        'collectiblesGames': bool(vis.get('collectiblesGames',True)),\n        'collectiblesOther': bool(vis.get('collectiblesOther',True)),\n"""
if "'collectiblesAntiques': bool(vis.get('collectiblesAntiques'" not in server:
    server = replace_once(server, norm_anchor, norm_block, 'server normalize visibility')

migration_anchor = "            'collectiblesStore':True,\n"
migration_block = migration_anchor + """            'collectiblesAntiques':True,\n            'collectiblesPrayerBeads':True,\n            'collectiblesVehiclesModels':True,\n            'collectiblesAviationMarine':True,\n            'collectiblesJewelryStones':True,\n            'collectiblesGames':True,\n            'collectiblesOther':True,\n"""
if "            'collectiblesAntiques':True," not in server:
    server = replace_once(server, migration_anchor, migration_block, 'server migration defaults')

effective_anchor = "        'collectiblesStore':vs.get('collectiblesStore',True) is not False,\n"
effective_block = effective_anchor + """        'collectiblesAntiques':vs.get('collectiblesAntiques',True) is not False,\n        'collectiblesPrayerBeads':vs.get('collectiblesPrayerBeads',True) is not False,\n        'collectiblesVehiclesModels':vs.get('collectiblesVehiclesModels',True) is not False,\n        'collectiblesAviationMarine':vs.get('collectiblesAviationMarine',True) is not False,\n        'collectiblesJewelryStones':vs.get('collectiblesJewelryStones',True) is not False,\n        'collectiblesGames':vs.get('collectiblesGames',True) is not False,\n        'collectiblesOther':vs.get('collectiblesOther',True) is not False,\n"""
if "'collectiblesAntiques':vs.get('collectiblesAntiques'" not in server:
    server = replace_once(server, effective_anchor, effective_block, 'server effective visibility')

keys_old = "for key in ('market','auction','specialNumbers','transitionalIssues','fantasia','promotions','announcements','liveAuction','collectiblesStore'):"
keys_new = "for key in ('market','auction','specialNumbers','transitionalIssues','fantasia','promotions','announcements','liveAuction','collectiblesStore','collectiblesAntiques','collectiblesPrayerBeads','collectiblesVehiclesModels','collectiblesAviationMarine','collectiblesJewelryStones','collectiblesGames','collectiblesOther'):"
if 'collectiblesPrayerBeads' not in server.split('for key in (',1)[-1]:
    server = replace_once(server, keys_old, keys_new, 'server settings whitelist')
SERVER.write_text(server, encoding='utf-8')


# 4) Shared visitor visibility: category links obey the same saved switches.
vis = VISIBILITY.read_text(encoding='utf-8')
map_anchor = "const PATH_KEYS={\n"
map_prefix = """const COLLECTIBLE_CATEGORY_KEYS={\n  'fantasia':'fantasia',\n  'antiques':'collectiblesAntiques',\n  'prayer-beads':'collectiblesPrayerBeads',\n  'vehicles-models':'collectiblesVehiclesModels',\n  'aviation-marine':'collectiblesAviationMarine',\n  'jewelry-stones':'collectiblesJewelryStones',\n  'games':'collectiblesGames',\n  'other':'collectiblesOther'\n};\nconst PATH_KEYS={\n"""
if 'COLLECTIBLE_CATEGORY_KEYS' not in vis:
    vis = replace_once(vis, map_anchor, map_prefix, 'visitor category key map')
old_parse = "  const p=cleanPath(u.pathname),store=String(u.searchParams.get('store')||'').toLowerCase();\n"
new_parse = "  const p=cleanPath(u.pathname),store=String(u.searchParams.get('store')||'').toLowerCase(),category=String(u.searchParams.get('category')||'').toLowerCase();\n"
if 'category=String(u.searchParams.get' not in vis:
    vis = replace_once(vis, old_parse, new_parse, 'visitor category query parsing')
store_anchor = "  if((p==='/market'||p==='/auction') && store==='collectibles' && !enabled(vs,'collectiblesStore'))return false;\n"
store_block = store_anchor + "  if((p==='/market'||p==='/public_market.html'||p==='/public-market') && store==='collectibles' && category && category!=='all'){const catKey=COLLECTIBLE_CATEGORY_KEYS[category];if(catKey&&!enabled(vs,catKey))return false;}\n"
if 'const catKey=COLLECTIBLE_CATEGORY_KEYS[category]' not in vis:
    vis = replace_once(vis, store_anchor, store_block, 'visitor category link visibility')
VISIBILITY.write_text(vis, encoding='utf-8')


# 5) Collectibles home: each visible category is independently controllable.
collectibles = COLLECTIBLES.read_text(encoding='utf-8')
old_categories = '<section class="categories" data-section="market"><a class="cat" href="/market?store=collectibles&category=fantasia">🎭<b>فنتازيا</b></a><a class="cat" href="/market?store=collectibles&category=antiques">🏺<b>تحف</b></a><a class="cat" href="/market?store=collectibles&category=prayer-beads">📿<b>سبح</b></a><a class="cat" href="/market?store=collectibles&category=vehicles-models">🚗<b>سيارات ومجسمات</b></a><a class="cat" href="/market?store=collectibles&category=aviation-marine">✈️<b>طائرات وسفن وقطارات</b></a><a class="cat" href="/market?store=collectibles&category=jewelry-stones">💍<b>خواتم وأحجار</b></a><a class="cat" href="/market?store=collectibles&category=games">🧸<b>ألعاب ومقتنيات</b></a><a class="cat" href="/market?store=collectibles&category=other">🧰<b>أخرى</b></a></section>'
new_categories = '<section class="categories" data-section="market"><a class="cat" data-section="fantasia" href="/market?store=collectibles&category=fantasia">🎭<b>فنتازيا</b></a><a class="cat" data-section="collectiblesAntiques" href="/market?store=collectibles&category=antiques">🏺<b>تحف</b></a><a class="cat" data-section="collectiblesPrayerBeads" href="/market?store=collectibles&category=prayer-beads">📿<b>سبح</b></a><a class="cat" data-section="collectiblesVehiclesModels" href="/market?store=collectibles&category=vehicles-models">🚗<b>سيارات ومجسمات</b></a><a class="cat" data-section="collectiblesAviationMarine" href="/market?store=collectibles&category=aviation-marine">✈️<b>طائرات وسفن وقطارات</b></a><a class="cat" data-section="collectiblesJewelryStones" href="/market?store=collectibles&category=jewelry-stones">💍<b>خواتم وأحجار</b></a><a class="cat" data-section="collectiblesGames" href="/market?store=collectibles&category=games">🧸<b>ألعاب ومقتنيات</b></a><a class="cat" data-section="collectiblesOther" href="/market?store=collectibles&category=other">🧰<b>أخرى</b></a></section>'
if 'data-section="collectiblesAntiques"' not in collectibles:
    collectibles = replace_once(collectibles, old_categories, new_categories, 'collectibles home category attributes')
COLLECTIBLES.write_text(collectibles, encoding='utf-8')


# 6) Collectibles market tabs/items: hidden categories disappear from the market UI too.
market = MARKET_JS.read_text(encoding='utf-8')
category_anchor = "const $=id=>document.getElementById(id);const QUERY=new URLSearchParams(location.search);let ITEMS=[],SETTINGS={},CURRENT=null,HASH_DONE=false,CATEGORY=(QUERY.get('category')||'all').trim()||'all';\n"
category_block = category_anchor + """const COLLECTIBLE_SECTION_KEYS={fantasia:'fantasia',antiques:'collectiblesAntiques','prayer-beads':'collectiblesPrayerBeads','vehicles-models':'collectiblesVehiclesModels','aviation-marine':'collectiblesAviationMarine','jewelry-stones':'collectiblesJewelryStones',games:'collectiblesGames',other:'collectiblesOther'};\nfunction collectibleCategoryVisible(key){if(STORE!=='collectibles'||key==='all')return true;const vs=(SETTINGS&&SETTINGS.visitorSections)||{};const sectionKey=COLLECTIBLE_SECTION_KEYS[key];return !sectionKey||vs[sectionKey]!==false}\nfunction applyCollectibleCategoryVisibility(){if(STORE!=='collectibles')return;document.querySelectorAll('#marketCategoryTabs [data-category]').forEach(b=>{const key=b.dataset.category||'all';b.hidden=!collectibleCategoryVisible(key)});if(CATEGORY!=='all'&&!collectibleCategoryVisible(CATEGORY)){CATEGORY='all';syncCategoryTab()}}\n"""
if 'COLLECTIBLE_SECTION_KEYS' not in market:
    market = replace_once(market, category_anchor, category_block, 'market collectibles visibility helpers')
render_old = "function render(){let q=$('search').value.trim().toLowerCase(),t=$('type').value,g=STORE==='coins'?($('grader')?.value||''):'',gv=STORE==='coins'?($('grade')?.value||''):'';let a=ITEMS.filter(i=>{let cat=itemCategoryKey(i);if(CATEGORY!=='all'&&cat!==CATEGORY)return false;"
render_new = "function render(){let q=$('search').value.trim().toLowerCase(),t=$('type').value,g=STORE==='coins'?($('grader')?.value||''):'',gv=STORE==='coins'?($('grade')?.value||''):'';let a=ITEMS.filter(i=>{let cat=itemCategoryKey(i);if(STORE==='collectibles'&&!collectibleCategoryVisible(cat))return false;if(CATEGORY!=='all'&&cat!==CATEGORY)return false;"
if "!collectibleCategoryVisible(cat)" not in market:
    market = replace_once(market, render_old, render_new, 'market item category filtering')
load_old = "async function load(){try{let [m,s]=await Promise.all([get('/api/public/market'+STORE_Q),get('/api/settings/public')]);ITEMS=m.items||[];SETTINGS=s||{};populateGradingFilters();render();"
load_new = "async function load(){try{let [m,s]=await Promise.all([get('/api/public/market'+STORE_Q),get('/api/settings/public')]);ITEMS=m.items||[];SETTINGS=s||{};applyCollectibleCategoryVisibility();populateGradingFilters();render();"
if 'SETTINGS=s||{};applyCollectibleCategoryVisibility();' not in market:
    market = replace_once(market, load_old, load_new, 'market apply category switches')
MARKET_JS.write_text(market, encoding='utf-8')

print('Collectibles category visibility patch applied safely.')
