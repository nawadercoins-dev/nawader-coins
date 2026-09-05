from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'server.py'
MARKET_JS = ROOT / 'public' / 'public_market.js'
AUCTION_JS = ROOT / 'public' / 'public_auction.js'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


server = SERVER.read_text(encoding='utf-8')

# Safe imports only.
old_import = 'from urllib.parse import urlparse, parse_qs, quote, urlencode\n'
new_import = 'from urllib.parse import urlparse, parse_qs, quote, urlencode, unquote\n'
if 'urlencode, unquote' not in server:
    server = replace_once(server, old_import, new_import, 'urllib unquote import')
if 'import html as html_lib\n' not in server:
    server = replace_once(server, 'import urllib.request, urllib.error\n', 'import urllib.request, urllib.error\nimport html as html_lib\n', 'html escape import')

helper_anchor = 'ADMIN_GET_API={\n'
helper_block = r'''# Public searchable item pages. Read-only: no inventory/order/auction state is changed here.
PUBLIC_ITEM_TEMPLATE=os.path.join(PUBLIC_DIR,'item_landing.html')
PUBLIC_CANONICAL_ORIGIN='https://nawadercoins.com'
PUBLIC_COLLECTIBLE_VISIBILITY={
    'fantasia':'fantasia','antiques':'collectiblesAntiques','prayer-beads':'collectiblesPrayerBeads',
    'vehicles-models':'collectiblesVehiclesModels','aviation-marine':'collectiblesAviationMarine',
    'jewelry-stones':'collectiblesJewelryStones','games':'collectiblesGames','other':'collectiblesOther'
}

def _public_item_category(i):
    if item_store_type(i)!='collectibles': return ''
    cc=str(i.get('collectibleCategory') or '').strip().lower()
    if cc: return cc
    mc=str(i.get('marketCategory') or '').strip().lower()
    if mc=='fantasia' or i.get('fantasiaEnabled'): return 'fantasia'
    if mc=='games': return 'games'
    if mc=='diecast': return 'vehicles-models'
    if mc=='collectibles': return 'other'
    return 'other'

def _public_item_modes(i):
    if not i or not item_is_public(i): return {'visible':False,'market':False,'auction':False}
    sections=effective_visitor_sections(); store=item_store_type(i)
    if store=='collectibles':
        if not sections.get('collectiblesStore',True): return {'visible':False,'market':False,'auction':False}
        cat=_public_item_category(i); key=PUBLIC_COLLECTIBLE_VISIBILITY.get(cat)
        if key and not sections.get(key,True): return {'visible':False,'market':False,'auction':False}
    market=bool(i.get('forMarket') and i.get('marketApproved') and sections.get('market',True))
    auction=bool(i.get('forAuction') and i.get('auctionApproved') and sections.get('auction',True))
    special=bool(store=='coins' and i.get('specialNumberEnabled') and sections.get('specialNumbers',True))
    transitional=bool(store=='coins' and i.get('transitionalIssueEnabled') and sections.get('transitionalIssues',True))
    fantasia=bool(store=='collectibles' and i.get('fantasiaEnabled') and sections.get('fantasia',True))
    return {'visible':bool(market or auction or special or transitional or fantasia),'market':market,'auction':auction}

def _public_item_title(i):
    title=str(i.get('marketTitle') or '').strip()
    if title: return title[:180]
    if item_store_type(i)=='collectibles':
        bits=[i.get('collectibleBrand'),i.get('collectibleModel'),i.get('collectibleCategory')]
    else:
        bits=[i.get('country'),i.get('denomination'),i.get('year')]
    title=' — '.join(str(x).strip() for x in bits if str(x or '').strip())
    return title[:180] or 'مقتنى نادر'

def _public_item_description(i,title):
    bits=[]
    for val in (i.get('country'),i.get('denomination'),i.get('year'),i.get('issueEdition') or i.get('issueEditionOther'),i.get('condition')):
        s=str(val or '').strip()
        if s and s not in bits: bits.append(s)
    if i.get('isGraded'):
        grade=' '.join(x for x in (str(i.get('gradingCompany') or '').strip(),str(i.get('gradeValue') or '').strip()) if x)
        if grade: bits.append('تقييم '+grade)
    note=re.sub(r'\s+',' ',str(i.get('notes') or '')).strip()
    text=' · '.join(bits)
    if note: text=(text+' — '+note).strip(' —')
    if not text: text=title+' ضمن دار المقتنيات.'
    return text[:320]

def _public_abs_url(url):
    u=str(url or '').strip()
    if not u: return ''
    if u.startswith('http://') or u.startswith('https://'): return u
    if u.startswith('//'): return 'https:'+u
    if not u.startswith('/'): u='/'+u
    return PUBLIC_CANONICAL_ORIGIN+u

def _public_item_images(i):
    out=[]
    for u in [i.get('frontImg'),i.get('backImg'),i.get('gradingCertImage'),*(i.get('additionalImages') or [])]:
        s=str(u or '').strip()
        if s and s not in out and not s.lower().startswith('data:'): out.append(s)
    return out[:8]

def _public_item_details(i,modes):
    rows=[]
    def add(label,value):
        v=str(value or '').strip()
        if v: rows.append((label,v))
    add('الدولة',i.get('country')); add('الفئة',i.get('denomination')); add('السنة',i.get('year')); add('الحالة',i.get('condition'))
    if item_store_type(i)=='collectibles':
        add('النوع',i.get('collectibleCategory')); add('العلامة',i.get('collectibleBrand')); add('الموديل',i.get('collectibleModel')); add('الخامة',i.get('collectibleMaterial'))
    if i.get('isGraded'):
        add('التقييم',' '.join(x for x in (str(i.get('gradingCompany') or '').strip(),str(i.get('gradeValue') or '').strip()) if x))
    if modes.get('market'):
        try:
            mv=public_market_item(i); price=float(mv.get('marketSalePrice') or mv.get('marketUnitPrice') or 0); available=int(mv.get('availableQuantity') or 0)
        except Exception:
            price=float(i.get('marketSalePrice') or i.get('marketUnitPrice') or 0); available=0
        if price>0: add('سعر العرض',f'{price:,.2f} ر.س')
        if available>0: add('المتاح',available)
    if modes.get('auction'):
        opening=float(i.get('auctionOpeningPrice') or i.get('auctionStartPrice') or 0)
        current=float(i.get('auctionCurrentPrice') or 0)
        if opening>0: add('سعر افتتاح المزاد',f'{opening:,.2f} ر.س')
        if current>0: add('السعر الحالي',f'{current:,.2f} ر.س')
        add('انتهاء المزاد',i.get('auctionEnd'))
    return rows

def _public_item_page(i):
    modes=_public_item_modes(i)
    if not modes.get('visible'): return None
    iid=str(i.get('id') or '').strip()
    if not iid: return None
    store=item_store_type(i); store_label='نوادر المقتنيات' if store=='collectibles' else 'نوادر العملات'; store_home='/collectibles' if store=='collectibles' else '/coins'
    title=_public_item_title(i); description=_public_item_description(i,title); canonical=PUBLIC_CANONICAL_ORIGIN+'/item/'+quote(iid,safe='')
    images=_public_item_images(i); primary=_public_abs_url(images[0]) if images else PUBLIC_CANONICAL_ORIGIN+'/assets/dar-al-muqtanyat-logo.webp'
    esc=lambda x: html_lib.escape(str(x or ''),quote=True)
    gallery=''.join(f'<img src="{esc(u)}" alt="{esc(title)}" loading="lazy">' for u in images) or '<div class="noimg">لا توجد صورة عامة لهذا المقتنى حاليًا.</div>'
    badges=[store_label]
    if i.get('specialNumberEnabled'): badges.append('رقم مميز / نادر')
    if i.get('transitionalIssueEnabled'): badges.append('إصدار انتقالي')
    if i.get('fantasiaEnabled'): badges.append('فنتازيا')
    badges_html=''.join(f'<span class="badge">{esc(x)}</span>' for x in badges)
    details_html=''.join(f'<div class="detail"><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k,v in _public_item_details(i,modes))
    note=re.sub(r'\s+',' ',str(i.get('notes') or '')).strip(); notes_html=f'<div class="notes">{esc(note)}</div>' if note else ''
    market_target='/market?store='+store+'#'+quote(iid,safe='') if modes.get('market') else ''
    auction_target='/auction?store='+store+'#'+quote(iid,safe='') if modes.get('auction') else ''
    actions=[]
    if modes.get('market'): actions.append('<button class="primary" type="button" data-public-action="market">🛒 شراء / طلب شراء</button>')
    if modes.get('auction'): actions.append('<button class="auction" type="button" data-public-action="auction">⚖ فتح المزاد / المزايدة</button>')
    if not actions: actions.append('<a class="primary" href="'+store_home+'">مشاهدة القسم</a>')
    schema={'@context':'https://schema.org','@type':'Product','name':title,'description':description,'url':canonical,'image':[_public_abs_url(x) for x in images] or [primary],'category':store_label}
    if modes.get('market'):
        try: price=float(i.get('marketSalePrice') or i.get('marketUnitPrice') or 0)
        except Exception: price=0
        if price>0: schema['offers']={'@type':'Offer','priceCurrency':'SAR','price':str(price),'url':canonical,'availability':'https://schema.org/InStock'}
    template=open(PUBLIC_ITEM_TEMPLATE,'r',encoding='utf-8').read()
    values={
        '{{TITLE}}':esc(title+' | '+store_label), '{{HEADING}}':esc(title), '{{DESCRIPTION}}':esc(description), '{{CANONICAL}}':esc(canonical), '{{IMAGE}}':esc(primary),
        '{{STORE_LABEL}}':esc(store_label), '{{STORE_HOME}}':esc(store_home), '{{GALLERY}}':gallery, '{{BADGES}}':badges_html, '{{DETAILS}}':details_html, '{{NOTES}}':notes_html,
        '{{ACTIONS}}':''.join(actions), '{{SCHEMA_JSON}}':json.dumps(schema,ensure_ascii=False).replace('<','\\u003c'),
        '{{MARKET_TARGET_JSON}}':json.dumps(market_target or None,ensure_ascii=False), '{{AUCTION_TARGET_JSON}}':json.dumps(auction_target or None,ensure_ascii=False),
        '{{SELF_PATH_JSON}}':json.dumps('/item/'+quote(iid,safe=''),ensure_ascii=False)
    }
    for token,value in values.items(): template=template.replace(token,value)
    return template.encode('utf-8')

def _public_sitemap_xml():
    entries=[]
    for i in load():
        modes=_public_item_modes(i)
        iid=str(i.get('id') or '').strip()
        if not iid or not modes.get('visible'): continue
        loc=PUBLIC_CANONICAL_ORIGIN+'/item/'+quote(iid,safe='')
        image_tags=''.join('<image:image><image:loc>'+html_lib.escape(_public_abs_url(u),quote=True)+'</image:loc><image:title>'+html_lib.escape(_public_item_title(i),quote=True)+'</image:title></image:image>' for u in _public_item_images(i)[:4])
        lastmod=''
        upd=i.get('updated')
        try:
            if isinstance(upd,(int,float)) and upd>0: lastmod='<lastmod>'+datetime.datetime.fromtimestamp(float(upd)/1000,datetime.timezone.utc).date().isoformat()+'</lastmod>'
            elif isinstance(upd,str) and re.match(r'^\\d{4}-\\d{2}-\\d{2}',upd): lastmod='<lastmod>'+html_lib.escape(upd[:10])+'</lastmod>'
        except Exception: lastmod=''
        entries.append('<url><loc>'+html_lib.escape(loc,quote=True)+'</loc>'+lastmod+image_tags+'</url>')
    xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'+''.join(entries)+'</urlset>'
    return xml.encode('utf-8')

def _send_public_bytes(handler,body,content_type,status=200,cache='public, max-age=120'):
    handler.send_response(status); handler.send_header('Content-Type',content_type); handler.send_header('Content-Length',str(len(body))); handler.send_header('Cache-Control',cache)
    handler.send_header('X-Content-Type-Options','nosniff'); handler.send_header('Referrer-Policy','same-origin'); handler.end_headers(); handler.wfile.write(body)

'''
if 'PUBLIC_ITEM_TEMPLATE=' not in server:
    server = replace_once(server, helper_anchor, helper_block + helper_anchor, 'public item helpers')

route_anchor = '    def do_GET(self):\n        p=urlparse(self.path).path\n'
route_block = '''    def do_GET(self):\n        p=urlparse(self.path).path\n        if p=='/robots.txt':\n            body=("User-agent: *\\nAllow: /\\nDisallow: /admin\\nDisallow: /api/\\nSitemap: https://nawadercoins.com/sitemap.xml\\n").encode('utf-8')\n            _send_public_bytes(self,body,'text/plain; charset=utf-8',cache='public, max-age=3600'); return\n        if p=='/sitemap.xml':\n            _send_public_bytes(self,_public_sitemap_xml(),'application/xml; charset=utf-8',cache='public, max-age=300'); return\n        if p.startswith('/item/'):\n            iid=unquote(p[len('/item/'):].strip('/'))\n            item=next((x for x in load() if str(x.get('id') or '')==iid),None)\n            body=_public_item_page(item) if item else None\n            if not body:\n                body=b'<!doctype html><html><head><meta name="robots" content="noindex"><meta charset="utf-8"></head><body>Not found</body></html>'\n                _send_public_bytes(self,body,'text/html; charset=utf-8',404,cache='no-store'); return\n            _send_public_bytes(self,body,'text/html; charset=utf-8'); return\n'''
if "if p=='/sitemap.xml':" not in server:
    server = replace_once(server, route_anchor, route_block, 'public SEO routes')

SERVER.write_text(server, encoding='utf-8')

# Share links now point to the stable public item URL instead of a JS fragment URL.
market = MARKET_JS.read_text(encoding='utf-8')
market = market.replace("url:'/market'+STORE_Q+'#'+encodeURIComponent(i.id)", "url:'/item/'+encodeURIComponent(i.id)")
market = market.replace("const url=location.origin+location.pathname+STORE_Q+'#'+encodeURIComponent(id);", "const url=location.origin+'/item/'+encodeURIComponent(id);")
MARKET_JS.write_text(market, encoding='utf-8')

auction = AUCTION_JS.read_text(encoding='utf-8')
auction = auction.replace("url:'/auction'+STORE_Q+'#'+encodeURIComponent(i.id)", "url:'/item/'+encodeURIComponent(i.id)")
auction = auction.replace("const url=location.origin+location.pathname+'#'+encodeURIComponent(id);", "const url=location.origin+'/item/'+encodeURIComponent(id);")
AUCTION_JS.write_text(auction, encoding='utf-8')
