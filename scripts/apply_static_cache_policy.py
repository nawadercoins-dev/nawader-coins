from pathlib import Path

path = Path('server.py')
text = path.read_text(encoding='utf-8')

old_end = """    def end_headers(self):
        self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma','no-cache')
        self.send_header('Expires','0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
"""

new_end = """    def end_headers(self):
        # Performance: keep sensitive/dynamic responses uncached while allowing
        # uploaded images and static assets to be reused by the browser.
        buffered = b''.join(getattr(self, '_headers_buffer', [])).lower()
        has_cache_control = b'\\ncache-control:' in buffered or b'\\rcache-control:' in buffered
        if not has_cache_control:
            raw_path = urlparse(self.path).path.lower()
            static_ext = ('.css','.js','.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.woff','.woff2')
            sensitive = raw_path.startswith(('/api/','/admin-login','/logout','/oauth/','/auth/'))
            cacheable = (raw_path.startswith('/uploads/') or raw_path.endswith(static_ext)) and not sensitive
            if cacheable:
                self.send_header('Cache-Control','public, max-age=86400, stale-while-revalidate=604800')
            else:
                self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
                self.send_header('Pragma','no-cache')
                self.send_header('Expires','0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
"""

if old_end not in text:
    raise SystemExit('Expected end_headers block not found; refusing unsafe patch')
text = text.replace(old_end, new_end, 1)

start = text.find('    def send_file(self,path,content_type=None):')
if start < 0:
    raise SystemExit('send_file method not found')
end = text.find('\n    def ', start + 5)
if end < 0:
    end = len(text)
chunk = text[start:end]
old_line = "            self.send_header('Cache-Control','no-store')\n"
if old_line not in chunk:
    raise SystemExit('Expected send_file no-store header not found; refusing unsafe patch')
chunk = chunk.replace(old_line, '', 1)
text = text[:start] + chunk + text[end:]

path.write_text(text, encoding='utf-8')
print('Applied static cache policy safely')