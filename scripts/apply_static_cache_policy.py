from pathlib import Path

path = Path('server.py')
text = path.read_text(encoding='utf-8')

marker = """            is_upload = raw_path.startswith('/uploads/')
            is_static = raw_path.endswith(static_ext) and not is_upload
"""
patched_marker = """            is_upload = raw_path.startswith('/uploads/')
            is_static = raw_path.endswith(static_ext) and not is_upload
            is_admin_asset = raw_path.startswith('/admin/') or raw_path == '/app.js'
"""
if patched_marker not in text:
    if marker not in text:
        raise SystemExit('Expected cache classification block not found; refusing unsafe patch')
    text = text.replace(marker, patched_marker, 1)

old_upload = """            if successful and is_upload and not sensitive:
                self.send_header('Cache-Control','private, max-age=86400, stale-while-revalidate=604800')
"""
new_upload = """            if successful and is_upload and not sensitive:
                self.send_header('Cache-Control','private, max-age=86400, stale-while-revalidate=604800')
                self.send_header('Vary','Cookie')
"""
if new_upload not in text:
    if old_upload not in text:
        raise SystemExit('Expected protected upload cache branch not found; refusing unsafe patch')
    text = text.replace(old_upload, new_upload, 1)

old_admin = """            elif successful and is_static and is_admin_asset and not sensitive:
                self.send_header('Cache-Control','private, max-age=86400, stale-while-revalidate=604800')
"""
new_admin = """            elif successful and is_static and is_admin_asset and not sensitive:
                self.send_header('Cache-Control','private, max-age=86400, stale-while-revalidate=604800')
                self.send_header('Vary','Cookie')
"""
if new_admin not in text:
    if old_admin not in text:
        raise SystemExit('Expected protected admin cache branch not found; refusing unsafe patch')
    text = text.replace(old_admin, new_admin, 1)

old_static = """            elif successful and is_static and not sensitive:
                self.send_header('Cache-Control','public, max-age=86400, stale-while-revalidate=604800')
"""
if old_static not in text:
    raise SystemExit('Expected public static cache branch not found; refusing unsafe patch')

require_admin = """            self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma','no-cache'); self.send_header('Expires','0'); self.end_headers()
"""
if require_admin not in text:
    raise SystemExit('Admin redirect cache protection missing; refusing unsafe patch')

head_method = """    def do_HEAD(self):
        # Do not inherit SimpleHTTPRequestHandler.do_HEAD: it bypasses this app's
        # custom GET router and can reveal local file metadata outside routed paths.
        self.send_response(405)
        self.send_header('Allow','GET, POST')
        self.send_header('Content-Length','0')
        self.end_headers()
"""
if head_method not in text:
    get_marker = "    def do_GET(self):\n"
    if get_marker not in text:
        raise SystemExit('do_GET method not found; refusing unsafe HEAD patch')
    text = text.replace(get_marker, head_method + get_marker, 1)

start = text.find('    def send_file(self,path,content_type=None):')
if start < 0:
    raise SystemExit('send_file method not found')
end = text.find('\n    def ', start + 5)
if end < 0:
    end = len(text)
chunk = text[start:end]
if "self.send_header('Cache-Control','no-store')" in chunk:
    raise SystemExit('send_file still forces no-store; refusing inconsistent policy')
if "            self.end_headers()\n" not in chunk:
    raise SystemExit('send_file end_headers call is not intact; refusing unsafe patch')

path.write_text(text, encoding='utf-8')
print('Static cache policy is applied: protected private responses vary by Cookie; inherited HEAD file serving is blocked; public static assets remain public')
