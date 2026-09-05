from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1) Account page: a normal participant (including a data-entry-enabled user)
# must stay on /account when the user explicitly opens "حسابي".
# Protected destinations still pass ?next=... and continue to work after login.
account = ROOT / 'public' / 'account.html'
s = account.read_text(encoding='utf-8')
old = "if(r.ok&&d.authenticated&&d.redirect&&d.redirect!='/account'){"
new = "if(r.ok&&d.authenticated&&d.role==='admin'&&d.redirect&&d.redirect!='/account'){"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('account routing anchor not found')
account.write_text(s, encoding='utf-8')

# 2) Mobile toast: keep cart/status messages visibly above the fixed visitor nav.
css = ROOT / 'public' / 'visitor.css'
s = css.read_text(encoding='utf-8')
marker = '/* V5.6.2-R8.1 — mobile toast above fixed visitor navigation */'
if marker not in s:
    s += '''\n\n/* V5.6.2-R8.1 — mobile toast above fixed visitor navigation */\n.has-visitor-floating-nav .visitor-toast{\n  z-index:100060!important;\n  bottom:calc(78px + env(safe-area-inset-bottom,0px))!important;\n  max-width:calc(100vw - 24px)!important;\n  width:max-content!important;\n  text-align:center!important;\n  white-space:normal!important;\n  line-height:1.55!important;\n  pointer-events:none!important;\n}\n@media(max-width:480px){\n  .has-visitor-floating-nav .visitor-toast{\n    bottom:calc(72px + env(safe-area-inset-bottom,0px))!important;\n    max-width:calc(100vw - 18px)!important;\n    font-size:14px!important;\n  }\n}\n'''
css.write_text(s, encoding='utf-8')

# 3) Market images: make the actual public product image a crawlable <a href=/item/...>.
# This gives Google and users a real HTML link to the public item page instead of
# relying only on JS/share URLs or sitemap discovery.
market = ROOT / 'public' / 'public_market.js'
s = market.read_text(encoding='utf-8')
old = '''          <img id="market-cover-${i.id}" src="${esc(images[0])}" data-market-index="0" loading="lazy" alt="${esc(title)}">'''
new = '''          <a class="public-item-image-link" href="/item/${encodeURIComponent(i.id)}" aria-label="فتح تفاصيل ${esc(title)}"><img id="market-cover-${i.id}" src="${esc(images[0])}" data-market-index="0" loading="lazy" alt="${esc(title)}"></a>'''
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('market image anchor not found')
market.write_text(s, encoding='utf-8')

# Matching layout rule for the new image anchor.
css = ROOT / 'public' / 'visitor.css'
s = css.read_text(encoding='utf-8')
marker2 = '/* V5.6.2-R8.1 — crawlable public item image link */'
if marker2 not in s:
    s += '''\n\n/* V5.6.2-R8.1 — crawlable public item image link */\n.market-photo .public-item-image-link{\n  display:block!important;\n  width:100%!important;\n  height:100%!important;\n  min-width:0!important;\n}\n.market-photo .public-item-image-link img{cursor:pointer!important}\n'''
css.write_text(s, encoding='utf-8')

print('account/cart/google-entry patch applied')
