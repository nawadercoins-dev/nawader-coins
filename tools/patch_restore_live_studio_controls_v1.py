from pathlib import Path

p = Path('public/live_studio.html')
s = p.read_text(encoding='utf-8')
marker = '<!-- restore-live-studio-controls-v1 -->'
if marker in s:
    print('already patched')
    raise SystemExit(0)

css_anchor = ".market-chip.on{background:#eaf8ef;color:#176035}"
css_add = css_anchor + ".auction-ticker{overflow:hidden;border-radius:12px;background:#0b3260;color:#fff;margin:10px 0;white-space:nowrap}.auction-ticker-track{display:inline-flex;gap:38px;min-width:100%;padding:9px 0;font-weight:900;animation:studioTickerMove 18s linear infinite}.auction-ticker-track span{padding-inline:14px}@keyframes studioTickerMove{from{transform:translateX(20%)}to{transform:translateX(-100%)}}"
if css_anchor not in s:
    raise SystemExit('CSS anchor not found')
s = s.replace(css_anchor, css_add, 1)

html_anchor = '<div class="video-box" id="localVideo"><span class="live-chip">LIVE</span><div style="color:#fff">الكاميرا لم تبدأ بعد</div></div><div class="controlbar">'
html_add = '<div class="video-box" id="localVideo"><span class="live-chip">LIVE</span><div style="color:#fff">الكاميرا لم تبدأ بعد</div></div><div class="auction-ticker" id="studioTicker" hidden><div class="auction-ticker-track" id="studioTickerTrack"></div></div><div class="controlbar">'
if html_anchor not in s:
    raise SystemExit('video/controlbar anchor not found')
s = s.replace(html_anchor, html_add, 1)

# Cache-bust the JS so restored controls are not masked by an older browser copy.
s = s.replace('/live_studio.js?v=5.4.5', '/live_studio.js?v=5.4.6')

# Add a compact feature contract note for maintainers; no UI impact.
s = s.replace('</main><script src=', marker + '</main><script src=', 1)

required = [
    'id="startCamera"', 'id="switchCamera"', 'id="toggleMic"', 'id="endStream"',
    'id="openLot"', 'id="sellLot"', 'id="closeLot"', 'id="studioChatForm"',
    'id="toggleLiveMarket"', 'id="studioTicker"', 'id="studioTickerTrack"'
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('missing restored live controls: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('restored live studio control surface and ticker')
