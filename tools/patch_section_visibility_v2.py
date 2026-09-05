from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'server.py'
ADMIN_HTML = ROOT / 'admin' / 'index.html'
ADMIN_JS = ROOT / 'admin' / 'app.js'
VISITOR_JS = ROOT / 'public' / 'visitor.js'
SECTION_JS = ROOT / 'public' / 'section_visibility.js'
COINS_HOME = ROOT / 'public' / 'public_home.html'
COLLECTIBLES_HOME = ROOT / 'public' / 'collectibles_home.html'
DAR_HOME = ROOT / 'public' / 'dar_home.html'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


def replace_all_required(text, old, new, label, min_count=1):
    count = text.count(old)
    if count < min_count:
        raise RuntimeError(f'{label}: expected at least {min_count} match(es), found {count}')
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# Server — extend the EXISTING visitorSections mechanism only.
# This deliberately does not touch orders, inventory, payment, auth, or auction logic.
# ---------------------------------------------------------------------------
server = SERVER.read_text(encoding='utf-8')

old_defaults = "'fantasia':True},'fullPublicEnableV493':False}"
new_defaults = "'fantasia':True,'promotions':True,'announcements':True,'liveAuction':True,'collectiblesStore':True},'fullPublicEnableV493':False}"
if old_defaults in server:
    server = replace_once(server, old_defaults, new_defaults, 'visitor section defaults')
elif "'collectiblesStore':True" not in server:
    raise RuntimeError('visitor section defaults: current source did not match expected safe marker')

old_normalized = "        'fantasia': bool(vis.get('fantasia',True)),\n    }"
new_normalized = "        'fantasia': bool(vis.get('fantasia',True)),\n        'promotions': bool(vis.get('promotions',True)),\n        'announcements': bool(vis.get('announcements',True)),\n        'liveAuction': bool(vis.get('liveAuction',True)),\n        'collectiblesStore': bool(vis.get('collectiblesStore',True)),\n    }"
if old_normalized in server:
    server = replace_once(server, old_normalized, new_normalized, 'visitor section normalization')
elif "'collectiblesStore': bool(vis.get('collectiblesStore',True))" not in server:
    raise RuntimeError('visitor section normalization: safe marker missing')

old_migration = "            'fantasia':True,\n        }"
new_migration = "            'fantasia':True,\n            'promotions':True,\n            'announcements':True,\n            'liveAuction':True,\n            'collectiblesStore':True,\n        }"
if old_migration in server:
    server = replace_once(server, old_migration, new_migration, 'visitor section one-time migration')
elif "            'collectiblesStore':True," not in server:
    raise RuntimeError('visitor section migration: safe marker missing')

old_effective = "        'fantasia':vs.get('fantasia',True) is not False,\n    }"
new_effective = "        'fantasia':vs.get('fantasia',True) is not False,\n        'promotions':vs.get('promotions',True) is not False,\n        'announcements':vs.get('announcements',True) is not False,\n        'liveAuction':vs.get('liveAuction',True) is not False,\n        'collectiblesStore':vs.get('collectiblesStore',True) is not False,\n    }"
if old_effective in server:
    server = replace_once(server, old_effective, new_effective, 'effective visitor sections')
elif "'collectiblesStore':vs.get('collectiblesStore',True) is not False" not in server:
    raise RuntimeError('effective visitor sections: safe marker missing')

old_whitelist = "for key in ('market','auction','specialNumbers','transitionalIssues','fantasia'):"
new_whitelist = "for key in ('market','auction','specialNumbers','transitionalIssues','fantasia','promotions','announcements','liveAuction','collectiblesStore'):"
if old_whitelist in server:
    server = replace_once(server, old_whitelist, new_whitelist, 'visitor section save whitelist')
elif new_whitelist not in server:
    raise RuntimeError('visitor section save whitelist: safe marker missing')

if "'/section_visibility.js'" not in server:
    server = replace_once(server, "'/visitor.js','/visitor.css'", "'/visitor.js','/section_visibility.js','/visitor.css'", 'public section visibility asset')

old_market_api = """        if p=='/api/public/market':
            with LOCK:
                store=requested_store(self.path)
                items=[public_market_item(i) for i in load() if i.get('forMarket') and i.get('marketApproved') and item_is_public(i) and (not store or item_store_type(i)==store)]
                self.sendj({'items':items,'store':store}); return
"""
new_market_api = """        if p=='/api/public/market':
            sections=effective_visitor_sections()
            store=requested_store(self.path)
            if not sections['market'] or (store=='collectibles' and not sections['collectiblesStore']):
                self.sendj({'items':[],'store':store,'hidden':True}); return
            with LOCK:
                items=[public_market_item(i) for i in load() if i.get('forMarket') and i.get('marketApproved') and item_is_public(i) and (not store or item_store_type(i)==store)]
                self.sendj({'items':items,'store':store}); return
"""
if old_market_api in server:
    server = replace_once(server, old_market_api, new_market_api, 'market public API visibility guard')
elif "if not sections['market'] or (store=='collectibles' and not sections['collectiblesStore'])" not in server:
    raise RuntimeError('market public API guard: safe marker missing')

old_auction_store = "                store=requested_store(self.path)\n                for i in source_items:"
new_auction_store = "                store=requested_store(self.path)\n                if store=='collectibles' and not effective_visitor_sections()['collectiblesStore']:\n                    self.sendj({'items':[],'store':store,'hidden':True}); return\n                for i in source_items:"
if old_auction_store in server:
    server = replace_once(server, old_auction_store, new_auction_store, 'collectibles auction API guard')
elif "store=='collectibles' and not effective_visitor_sections()['collectiblesStore']" not in server:
    raise RuntimeError('collectibles auction API guard: safe marker missing')

old_fantasia_api = """        if p=='/api/public/fantasia':
            if not effective_visitor_sections()['fantasia']:
                self.sendj({'items':[],'hidden':True,'launchMode':True}); return
"""
new_fantasia_api = """        if p=='/api/public/fantasia':
            sections=effective_visitor_sections()
            if not sections['fantasia'] or not sections['collectiblesStore']:
                self.sendj({'items':[],'hidden':True,'launchMode':True}); return
"""
if old_fantasia_api in server:
    server = replace_once(server, old_fantasia_api, new_fantasia_api, 'fantasia public API visibility guard')
elif "if not sections['fantasia'] or not sections['collectiblesStore']" not in server:
    raise RuntimeError('fantasia public API guard: safe marker missing')

old_collectibles_route = """        if p in ('/collectibles','/collectibles/','/collectibles_home.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'collectibles_home.html'),'text/html; charset=utf-8'); return
"""
new_collectibles_route = """        if p in ('/collectibles','/collectibles/','/collectibles_home.html'):
            if not effective_visitor_sections()['collectiblesStore']:
                self.send_response(302); self.send_header('Location','/dar'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'collectibles_home.html'),'text/html; charset=utf-8'); return
"""
if old_collectibles_route in server:
    server = replace_once(server, old_collectibles_route, new_collectibles_route, 'collectibles store route guard')
elif "if not effective_visitor_sections()['collectiblesStore']" not in server:
    raise RuntimeError('collectibles store route guard: safe marker missing')

old_announcements_route = """        if p in ('/announcements','/announcements/','/announcements.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'announcements.html'),'text/html; charset=utf-8'); return
"""
new_announcements_route = """        if p in ('/announcements','/announcements/','/announcements.html'):
            if not effective_visitor_sections()['announcements']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'announcements.html'),'text/html; charset=utf-8'); return
"""
if old_announcements_route in server:
    server = replace_once(server, old_announcements_route, new_announcements_route, 'announcements route guard')
elif "effective_visitor_sections()['announcements']" not in server:
    raise RuntimeError('announcements route guard: safe marker missing')

old_live_route = """        if p in ('/live-auction','/live-auction/','/live_auction.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'live_auction.html'),'text/html; charset=utf-8'); return
"""
new_live_route = """        if p in ('/live-auction','/live-auction/','/live_auction.html'):
            if not effective_visitor_sections()['liveAuction']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'live_auction.html'),'text/html; charset=utf-8'); return
"""
if old_live_route in server:
    server = replace_once(server, old_live_route, new_live_route, 'live auction route guard')
elif "effective_visitor_sections()['liveAuction']" not in server:
    raise RuntimeError('live auction route guard: safe marker missing')

old_fantasia_route = """        if p in ('/fantasia','/fantasia/','/fantasia.html'):
            if not effective_visitor_sections()['fantasia']:
                self.sendj({'error':'قسم فانتازيا غير متاح حاليًا'},404); return
            self.send_file(os.path.join(PUBLIC_DIR,'fantasia.html'),'text/html; charset=utf-8'); return
"""
new_fantasia_route = """        if p in ('/fantasia','/fantasia/','/fantasia.html'):
            sections=effective_visitor_sections()
            if not sections['fantasia'] or not sections['collectiblesStore']:
                self.sendj({'error':'قسم فانتازيا غير متاح حاليًا'},404); return
            self.send_file(os.path.join(PUBLIC_DIR,'fantasia.html'),'text/html; charset=utf-8'); return
"""
if old_fantasia_route in server:
    server = replace_once(server, old_fantasia_route, new_fantasia_route, 'fantasia route guard')
elif "if not sections['fantasia'] or not sections['collectiblesStore']" not in server:
    raise RuntimeError('fantasia route guard: safe marker missing')

old_auction_route = """        if p in ('/auction','/auction/','/public_auction.html','/public-auction'):
            if not effective_visitor_sections()['auction']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_auction.html'),'text/html; charset=utf-8'); return
"""
new_auction_route = """        if p in ('/auction','/auction/','/public_auction.html','/public-auction'):
            sections=effective_visitor_sections(); store=requested_store(self.path)
            if not sections['auction'] or (store=='collectibles' and not sections['collectiblesStore']):
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_auction.html'),'text/html; charset=utf-8'); return
"""
if old_auction_route in server:
    server = replace_once(server, old_auction_route, new_auction_route, 'auction route visibility guard')
elif "if not sections['auction'] or (store=='collectibles' and not sections['collectiblesStore'])" not in server:
    raise RuntimeError('auction route visibility guard: safe marker missing')

old_market_route = """        if p in ('/market','/market/','/public_market.html','/public-market'):
            if not effective_visitor_sections()['market']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_market.html'),'text/html; charset=utf-8'); return
"""
new_market_route = """        if p in ('/market','/market/','/public_market.html','/public-market'):
            sections=effective_visitor_sections(); store=requested_store(self.path)
            if not sections['market'] or (store=='collectibles' and not sections['collectiblesStore']):
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_market.html'),'text/html; charset=utf-8'); return
"""
if old_market_route in server:
    server = replace_once(server, old_market_route, new_market_route, 'market route visibility guard')
elif "if not sections['market'] or (store=='collectibles' and not sections['collectiblesStore'])" not in server:
    raise RuntimeError('market route visibility guard: safe marker missing')

SERVER.write_text(server, encoding='utf-8')


# ---------------------------------------------------------------------------
# Administration — extend the existing settings panel; explicit Save remains.
# ---------------------------------------------------------------------------
admin_html = ADMIN_HTML.read_text(encoding='utf-8')
anchor = '<label class="check"><input id="visitorSectionFantasia" type="checkbox" /> إظهار قسم فانتازيا</label>'
extra = anchor + '\n              <label class="check"><input id="visitorSectionPromotions" type="checkbox" /> إظهار العروض المميزة</label>\n              <label class="check"><input id="visitorSectionAnnouncements" type="checkbox" /> إظهار الأخبار والإعلانات</label>\n              <label class="check"><input id="visitorSectionLiveAuction" type="checkbox" /> إظهار المزاد المباشر</label>\n              <label class="check"><input id="visitorSectionCollectiblesStore" type="checkbox" /> إظهار متجر نوادر المقتنيات</label>'
if 'id="visitorSectionCollectiblesStore"' not in admin_html:
    admin_html = replace_once(admin_html, anchor, extra, 'admin section visibility controls')
ADMIN_HTML.write_text(admin_html, encoding='utf-8')

admin_js = ADMIN_JS.read_text(encoding='utf-8')
load_anchor = '    if ($("visitorSectionFantasia")) $("visitorSectionFantasia").checked = vs.fantasia !== false;'
load_extra = load_anchor + '\n    if ($("visitorSectionPromotions")) $("visitorSectionPromotions").checked = vs.promotions !== false;\n    if ($("visitorSectionAnnouncements")) $("visitorSectionAnnouncements").checked = vs.announcements !== false;\n    if ($("visitorSectionLiveAuction")) $("visitorSectionLiveAuction").checked = vs.liveAuction !== false;\n    if ($("visitorSectionCollectiblesStore")) $("visitorSectionCollectiblesStore").checked = vs.collectiblesStore !== false;'
if '$("visitorSectionCollectiblesStore").checked = vs.collectiblesStore !== false' not in admin_js:
    admin_js = replace_all_required(admin_js, load_anchor, load_extra, 'load extended visitor sections')

save_anchor = '            fantasia: $("visitorSectionFantasia") ? !!$("visitorSectionFantasia").checked : true,'
save_extra = save_anchor + '\n            promotions: $("visitorSectionPromotions") ? !!$("visitorSectionPromotions").checked : true,\n            announcements: $("visitorSectionAnnouncements") ? !!$("visitorSectionAnnouncements").checked : true,\n            liveAuction: $("visitorSectionLiveAuction") ? !!$("visitorSectionLiveAuction").checked : true,\n            collectiblesStore: $("visitorSectionCollectiblesStore") ? !!$("visitorSectionCollectiblesStore").checked : true,'
if 'collectiblesStore: $("visitorSectionCollectiblesStore")' not in admin_js:
    admin_js = replace_all_required(admin_js, save_anchor, save_extra, 'save extended visitor sections')

saved_anchor = '      if ($("visitorSectionFantasia")) $("visitorSectionFantasia").checked = savedVs.fantasia !== false;'
saved_extra = saved_anchor + '\n      if ($("visitorSectionPromotions")) $("visitorSectionPromotions").checked = savedVs.promotions !== false;\n      if ($("visitorSectionAnnouncements")) $("visitorSectionAnnouncements").checked = savedVs.announcements !== false;\n      if ($("visitorSectionLiveAuction")) $("visitorSectionLiveAuction").checked = savedVs.liveAuction !== false;\n      if ($("visitorSectionCollectiblesStore")) $("visitorSectionCollectiblesStore").checked = savedVs.collectiblesStore !== false;'
if '$("visitorSectionCollectiblesStore").checked = savedVs.collectiblesStore !== false' not in admin_js:
    admin_js = replace_all_required(admin_js, saved_anchor, saved_extra, 'restore saved extended visitor sections')
ADMIN_JS.write_text(admin_js, encoding='utf-8')


# ---------------------------------------------------------------------------
# Shared visitor visibility script — isolated, reversible DOM hiding only.
# ---------------------------------------------------------------------------
section_script = r"""// Visitor section visibility v2 — presentation only; server routes also enforce the same settings.
(()=>{
'use strict';
const PATH_KEYS={
  '/announcements':'announcements','/announcements.html':'announcements',
  '/live-auction':'liveAuction','/live_auction.html':'liveAuction',
  '/special-numbers':'specialNumbers','/special_numbers.html':'specialNumbers',
  '/transitional-issues':'transitionalIssues','/transitional_issues.html':'transitionalIssues',
  '/fantasia':'fantasia',
  '/collectibles':'collectiblesStore','/collectibles_home.html':'collectiblesStore'
};
const cleanPath=p=>{p=String(p||'/').replace(/\/+$/,'');return p||'/'};
function controlledHidden(el,hide){
  if(!el)return;
  if(hide){
    if(!el.hidden){el.hidden=true;el.dataset.sectionVisibilityHidden='1'}
  }else if(el.dataset.sectionVisibilityHidden==='1'){
    el.hidden=false;delete el.dataset.sectionVisibilityHidden;
  }
}
function enabled(vs,key){return !key || (vs||{})[key]!==false}
function linkVisible(a,vs){
  let u;try{u=new URL(a.getAttribute('href')||'',location.origin)}catch{return true}
  const p=cleanPath(u.pathname),store=String(u.searchParams.get('store')||'').toLowerCase();
  if((p==='/market'||p==='/public_market.html'||p==='/public-market') && !enabled(vs,'market'))return false;
  if((p==='/auction'||p==='/public_auction.html'||p==='/public-auction'||p==='/daily-auction') && !enabled(vs,'auction'))return false;
  if((p==='/market'||p==='/auction') && store==='collectibles' && !enabled(vs,'collectiblesStore'))return false;
  const key=PATH_KEYS[p];
  if(key && !enabled(vs,key))return false;
  if(p==='/fantasia' && !enabled(vs,'collectiblesStore'))return false;
  return true;
}
function apply(vs){
  vs=vs||{};
  document.querySelectorAll('[data-section]').forEach(el=>{
    const key=el.getAttribute('data-section');
    controlledHidden(el,!enabled(vs,key));
  });
  document.querySelectorAll('a[href]').forEach(a=>controlledHidden(a,!linkVisible(a,vs)));
  window.dispatchEvent(new CustomEvent('nawader-section-visibility',{detail:{visitorSections:vs}}));
}
async function refresh(){
  try{
    const r=await fetch('/api/settings/public',{cache:'no-store'});
    if(!r.ok)return;
    const d=await r.json();apply(d.visitorSections||{});
  }catch(_){ }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();
window.NawaderSectionVisibility={refresh,apply};
window.refreshVisitorSections=refresh;
})();
"""
SECTION_JS.write_text(section_script, encoding='utf-8')

visitor = VISITOR_JS.read_text(encoding='utf-8')
marker = '/* V4.3.3 — Central visitor section visibility */'
loader = marker + r"""
(function(){
  if(document.querySelector('script[data-section-visibility]'))return;
  const s=document.createElement('script');s.src='/section_visibility.js?v=2';s.defer=true;s.dataset.sectionVisibility='1';document.head.appendChild(s);
})();
"""
if marker in visitor and "src='/section_visibility.js?v=2'" not in visitor:
    before, after = visitor.split(marker, 1)
    if 'window.refreshVisitorSections=refresh;' not in after:
        raise RuntimeError('visitor visibility legacy block was not in the expected tail section')
    visitor = before.rstrip() + '\n\n' + loader
elif "src='/section_visibility.js?v=2'" not in visitor:
    raise RuntimeError('visitor visibility marker missing')
VISITOR_JS.write_text(visitor, encoding='utf-8')


# ---------------------------------------------------------------------------
# Page markers — no content deletion, only attach visibility keys.
# ---------------------------------------------------------------------------
coins = COINS_HOME.read_text(encoding='utf-8')
old = '<section class="home-row promo-row" id="promotions" aria-label="العروض والصفقات المميزة">'
new = '<section class="home-row promo-row" id="promotions" data-section="promotions" aria-label="العروض والصفقات المميزة">'
if old in coins: coins = replace_once(coins, old, new, 'coins promotions marker')
elif new not in coins: raise RuntimeError('coins promotions marker missing')
COINS_HOME.write_text(coins, encoding='utf-8')

collectibles = COLLECTIBLES_HOME.read_text(encoding='utf-8')
repls = [
    ('<section class="categories">','<section class="categories" data-section="market">','collectibles categories market marker'),
    ('<section class="row"><div class="row-head"><h2>🛍 أحدث عروض نوادر المقتنيات</h2>','<section class="row" data-section="market"><div class="row-head"><h2>🛍 أحدث عروض نوادر المقتنيات</h2>','collectibles market row marker'),
    ('<section class="row"><div class="row-head"><h2>⚖ مزادات نوادر المقتنيات</h2>','<section class="row" data-section="auction"><div class="row-head"><h2>⚖ مزادات نوادر المقتنيات</h2>','collectibles auction row marker'),
    ('<section class="row"><div class="row-head"><h2>🎭 الفنتازيا</h2>','<section class="row" data-section="fantasia"><div class="row-head"><h2>🎭 الفنتازيا</h2>','collectibles fantasia row marker'),
]
for old,new,label in repls:
    if old in collectibles: collectibles=replace_once(collectibles,old,new,label)
    elif new not in collectibles: raise RuntimeError(label+': marker missing')
COLLECTIBLES_HOME.write_text(collectibles, encoding='utf-8')

dar = DAR_HOME.read_text(encoding='utf-8')
old = '<article class="store collectibles">'
new = '<article class="store collectibles" data-section="collectiblesStore">'
if old in dar: dar=replace_once(dar,old,new,'Dar collectibles card marker')
elif new not in dar: raise RuntimeError('Dar collectibles card marker missing')
if '/section_visibility.js?v=2' not in dar:
    dar=replace_once(dar,'</main>\n</body>','</main>\n<script src="/section_visibility.js?v=2" defer></script>\n</body>','Dar visibility script')
DAR_HOME.write_text(dar, encoding='utf-8')

print('Section visibility v2 patch applied safely.')
