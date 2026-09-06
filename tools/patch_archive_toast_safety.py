from pathlib import Path

ROOT = Path('.')
MARK = 'archive-toast-safety-v1'
changed = []

JS_HELPER = """// archive-toast-safety-v1\nfunction __safeToast(message, timeout){\n  try {\n    if (typeof window !== 'undefined' && typeof window.toast === 'function') return window.toast(message, timeout);\n  } catch (_) {}\n  try { alert(String(message ?? '')); } catch (_) {}\n}\n"""
HTML_HELPER = """<script>\n// archive-toast-safety-v1\nfunction __safeToast(message, timeout){\n  try {\n    if (typeof window !== 'undefined' && typeof window.toast === 'function') return window.toast(message, timeout);\n  } catch (_) {}\n  try { alert(String(message ?? '')); } catch (_) {}\n}\n</script>\n"""

for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in {'.js', '.html'}:
        continue
    if any(part in {'.git','node_modules','tools'} for part in p.parts):
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    if 'window.toast(' not in text:
        continue
    new = text.replace('window.toast(', '__safeToast(')
    if MARK not in new:
        if p.suffix.lower() == '.js':
            new = JS_HELPER + '\n' + new
        else:
            if '</head>' in new:
                new = new.replace('</head>', HTML_HELPER + '</head>', 1)
            else:
                new = HTML_HELPER + new
    if new != text:
        p.write_text(new, encoding='utf-8')
        changed.append(str(p))

if not changed:
    print('No unsafe window.toast calls found; nothing to patch.')
else:
    print('Patched files:')
    for x in changed:
        print(' -', x)
