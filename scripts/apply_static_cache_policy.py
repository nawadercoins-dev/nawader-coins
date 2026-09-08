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

patched_end_v1 = """    def end_headers(self):
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

patched_end_v2 = """    def end_headers(self):
        # Performance: keep sensitive/dynamic and error responses uncached while
        # allowing successful uploaded images and static assets to be reused.
        buffered = b''.join(getattr(self, '_headers_buffer', [])).lower()
        has_cache_control = b'\\ncache-control:' in buffered or b'\\rcache-control:' in buffered
        if not has_cache_control:
            raw_path = urlparse(self.path).path.lower()
            static_ext = ('.css','.js','.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.woff','.woff2')
            sensitive = raw_path.startswith(('/api/','/admin-login','/logout','/oauth/','/auth/'))
            first_line = buffered.splitlines()[0] if buffered else b''
            successful = b' 200 ' in first_line
            cacheable = successful and (raw_path.startswith('/uploads/') or raw_path.endswith(static_ext)) and not sensitive
            if cacheable:
                self.send_header('Cache-Control','public, max-age=86400, stale-while-revalidate=604800')
            else:
                self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
                self.send_header('Pragma','no-cache')
                self.send_header('Expires','0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
"""

new_end = """    def end_headers(self):
        # Performance: keep sensitive/dynamic and error responses uncached.
        # Successful protected uploads are browser-cacheable but never public/shared.
        buffered = b''.join(getattr(self, '_headers_buffer', [])).lower()
        has_cache_control = b'\\ncache-control:' in buffered or b'\\rcache-control:' in buffered
        if not has_cache_control:
            raw_path = urlparse(self.path).path.lower()
            static_ext = ('.css','.js','.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.woff','.woff2')
            sensitive = raw_path.startswith(('/api/','/admin-login','/logout','/oauth/','/auth/'))
            first_line = buffered.splitlines()[0] if buffered else b''
            successful = b' 200 ' in first_line
            is_upload = raw_path.startswith('/uploads/')
            is_static = raw_path.endswith(static_ext) and not is_upload
            if successful and is_upload and not sensitive:
                self.send_header('Cache-Control','private, max-age=86400, stale-while-revalidate=604800')
            elif successful and is_static and not sensitive:
                self.send_header('Cache-Control','public, max-age=86400, stale-while-revalidate=604800')
            else:
                self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
                self.send_header('Pragma','no-cache')
                self.send_header('Expires','0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
"""

if old_end in text:
    text = text.replace(old_end, new_end, 1)
elif patched_end_v1 in text:
    text = text.replace(patched_end_v1, new_end, 1)
elif patched_end_v2 in text:
    text = text.replace(patched_end_v2, new_end, 1)
elif new_end not in text:
    raise SystemExit('Expected original or known patched end_headers block not found; refusing unsafe patch')

old_require_admin = """    def require_admin(self,api=False):
        if self.is_admin(): return True
        if api: self.sendj({'error':'هذه الصفحة أو العملية خاصة بالإدارة. سجل الدخول أولًا.'},401)
        else:
            self.send_response(302); self.send_header('Location','/admin-login'); self.end_headers()
        return False
"""

new_require_admin = """    def require_admin(self,api=False):
        if self.is_admin(): return True
        if api: self.sendj({'error':'هذه الصفحة أو العملية خاصة بالإدارة. سجل الدخول أولًا.'},401)
        else:
            self.send_response(302); self.send_header('Location','/admin-login')
            self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma','no-cache'); self.send_header('Expires','0'); self.end_headers()
        return False
"""

if old_require_admin in text:
    text = text.replace(old_require_admin, new_require_admin, 1)
elif new_require_admin not in text:
    raise SystemExit('Expected original or patched require_admin block not found; refusing unsafe patch')

start = text.find('    def send_file(self,path,content_type=None):')
if start < 0:
    raise SystemExit('send_file method not found')
end = text.find('\n    def ', start + 5)
if end < 0:
    end = len(text)
chunk = text[start:end]
old_line = "            self.send_header('Cache-Control','no-store')\n"
if old_line in chunk:
    chunk = chunk.replace(old_line, '', 1)
    text = text[:start] + chunk + text[end:]
elif "            self.end_headers()\n" not in chunk:
    raise SystemExit('send_file cache header is absent but end_headers call is not intact; refusing unsafe patch')

path.write_text(text, encoding='utf-8')
print('Static cache policy is applied and safe to rerun')
