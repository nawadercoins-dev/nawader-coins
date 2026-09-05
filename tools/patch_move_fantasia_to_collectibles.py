from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_HTML = ROOT / 'admin' / 'index.html'

html = ADMIN_HTML.read_text(encoding='utf-8')
fantasia = '              <label class="check"><input id="visitorSectionFantasia" type="checkbox" /> إظهار قسم فانتازيا</label>\n'
old_header = '              <div style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid #d8c07e"><b>أقسام نوادر المقتنيات</b><div class="muted" style="margin-top:4px">فنتازيا يتحكم بها خيار «إظهار قسم فنتازيا» أعلاه.</div></div>\n'
new_header = '              <div style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid #d8c07e"><b>أقسام نوادر المقتنيات</b></div>\n' + fantasia

# Move the existing Fantasia switch from the general/coins-facing group into
# the collectibles category group. Keep the same input id so save/load/server
# behavior is unchanged; this is a presentation-only correction.
if old_header in html:
    if html.count(fantasia) != 1:
        raise RuntimeError(f'expected exactly one Fantasia switch, found {html.count(fantasia)}')
    html = html.replace(fantasia, '', 1)
    html = html.replace(old_header, new_header, 1)
elif new_header in html:
    pass
else:
    raise RuntimeError('collectibles visibility header not found; refusing to touch unrelated markup')

if html.count('id="visitorSectionFantasia"') != 1:
    raise RuntimeError('Fantasia switch must exist exactly once')
if html.index('<b>أقسام نوادر المقتنيات</b>') > html.index('id="visitorSectionFantasia"'):
    raise RuntimeError('Fantasia switch was not moved under collectibles heading')

ADMIN_HTML.write_text(html, encoding='utf-8')
