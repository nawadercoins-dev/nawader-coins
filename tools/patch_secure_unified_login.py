from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = ROOT / 'public' / 'account.html'
SERVER = ROOT / 'server.py'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


# --- Public account page: only identity methods are public. ---
account = ACCOUNT.read_text(encoding='utf-8')

old_help = '<section class="panel auth-panel" id="loginBox"><h2>الدخول الموحد — دار المقتنيات</h2><p class="auth-help"><b>الدخول السريع:</b> استخدم Facebook أو Google للدخول المباشر بعد ربط الجوال مرة واحدة، أو استخدم واتساب مباشرة. العميل والبائع ومسؤول إدخال البيانات يستخدمون الحساب نفسه، والصلاحيات تحددها الإدارة داخل النظام.</p>'
new_help = '<section class="panel auth-panel" id="loginBox"><h2>الدخول الموحد — دار المقتنيات</h2><p class="auth-help"><b>دخول واحد وآمن:</b> استخدم Facebook أو Google أو واتساب لإثبات هويتك. بعد نجاح التحقق يحدد الخادم صلاحية الحساب ويوجهك تلقائيًا إلى صفحتك المناسبة؛ لا يمكن اختيار صلاحية إدارية من هذه الصفحة.</p>'
if old_help in account:
    account = replace_once(account, old_help, new_help, 'secure login help')
elif new_help not in account:
    raise RuntimeError('secure login help: expected current or patched text')

old_methods = '<div class="login-methods"><a class="login-method facebook-login" id="facebookLogin" href="/auth/facebook"><span class="f">f</span><span>الدخول عبر Facebook</span></a><a class="login-method google-login" id="googleLogin" href="/auth/google"><span class="g">G</span><span>الدخول عبر Google</span></a><button class="login-method wa-login" id="showWaLogin" type="button">💬 الدخول عبر واتساب</button><a class="login-method role-login" href="/data-entry">⌨ مسؤول إدخال البيانات</a><a class="login-method admin-login" href="/admin">🔐 الإدارة</a></div>'
new_methods = '<div class="login-methods"><a class="login-method facebook-login" id="facebookLogin" href="/auth/facebook"><span class="f">f</span><span>الدخول عبر Facebook</span></a><a class="login-method google-login" id="googleLogin" href="/auth/google"><span class="g">G</span><span>الدخول عبر Google</span></a><button class="login-method wa-login" id="showWaLogin" type="button">💬 الدخول عبر واتساب</button></div>'
if old_methods in account:
    account = replace_once(account, old_methods, new_methods, 'remove privileged public role buttons')
elif new_methods not in account:
    raise RuntimeError('role buttons: expected current or patched methods')

old_boot = "loadGoogleLoginState();loadFacebookLoginState();\nsync();window.addEventListener('storage',sync);"
new_boot = """async function routeAuthenticatedRole(){
  try{
    const r=await fetch('/api/auth/route',{cache:'no-store'}),d=await r.json();
    if(r.ok&&d.authenticated&&d.redirect&&d.redirect!='/account'){
      location.replace(d.redirect);return true;
    }
  }catch(e){}
  return false;
}
routeAuthenticatedRole().then(routed=>{if(!routed){loadGoogleLoginState();loadFacebookLoginState();sync();window.addEventListener('storage',sync)}});"""
if old_boot in account:
    account = replace_once(account, old_boot, new_boot, 'automatic server-side role routing bootstrap')
elif 'async function routeAuthenticatedRole()' not in account:
    raise RuntimeError('role routing bootstrap: expected current or patched script')

ACCOUNT.write_text(account, encoding='utf-8')


# --- Server: authoritative role routing + admin brute-force throttling. ---
server = SERVER.read_text(encoding='utf-8')

old_globals = "ADMIN_SESSIONS={}\nPARTICIPANT_SESSIONS={}\nSESSION_TTL_SECONDS=12*60*60"
new_globals = "ADMIN_SESSIONS={}\nPARTICIPANT_SESSIONS={}\nADMIN_LOGIN_ATTEMPTS={}\nADMIN_LOGIN_WINDOW_SECONDS=15*60\nADMIN_LOGIN_MAX_ATTEMPTS=5\nSESSION_TTL_SECONDS=12*60*60"
if old_globals in server:
    server = replace_once(server, old_globals, new_globals, 'admin login throttle globals')
elif 'ADMIN_LOGIN_ATTEMPTS={}' not in server:
    raise RuntimeError('admin throttle globals: expected current or patched globals')

get_marker = "    def do_GET(self):\n        p=urlparse(self.path).path\n"
route_block = """    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/auth/route':
            # Authoritative post-login routing. Public UI never grants or selects roles.
            if self.is_admin():
                self.sendj({'ok':True,'authenticated':True,'role':'admin','redirect':'/admin'}); return
            person=self.participant_person()
            if not person:
                self.sendj({'ok':True,'authenticated':False,'role':'visitor','redirect':'/account'}); return
            pid=str(person.get('id') or '')
            perms=participant_permissions(pid)
            if perms.get('dataEntry'):
                role,redirect='data_entry','/data-entry'
            elif perms.get('sellerMarket') or perms.get('sellerEndedAuctions') or perms.get('liveBroadcast'):
                role,redirect='seller','/seller'
            else:
                role,redirect='customer','/account'
            self.sendj({'ok':True,'authenticated':True,'role':role,'redirect':redirect}); return
"""
if "if p=='/api/auth/route':" not in server:
    server = replace_once(server, get_marker, route_block, 'authoritative auth route endpoint')

old_admin_verify = """            if not verify_admin_password(username,password):
                time.sleep(0.35); self.login_page('اسم المستخدم أو كلمة المرور غير صحيحة.'); return
            token=secrets.token_urlsafe(32); ADMIN_SESSIONS[token]={'created':time.time(),'last':time.time()}
"""
new_admin_verify = """            client_key=(self.headers.get('X-Forwarded-For') or '').split(',')[0].strip() or str(self.client_address[0] if self.client_address else 'unknown')
            now=time.time(); tries=[t for t in ADMIN_LOGIN_ATTEMPTS.get(client_key,[]) if now-t<ADMIN_LOGIN_WINDOW_SECONDS]
            if len(tries)>=ADMIN_LOGIN_MAX_ATTEMPTS:
                self.login_page('تم إيقاف محاولات دخول الإدارة مؤقتًا بسبب تكرار المحاولات. حاول بعد 15 دقيقة.'); return
            if not verify_admin_password(username,password):
                tries.append(now); ADMIN_LOGIN_ATTEMPTS[client_key]=tries
                time.sleep(0.5); self.login_page('اسم المستخدم أو كلمة المرور غير صحيحة.'); return
            ADMIN_LOGIN_ATTEMPTS.pop(client_key,None)
            token=secrets.token_urlsafe(32); ADMIN_SESSIONS[token]={'created':time.time(),'last':time.time()}
"""
if old_admin_verify in server:
    server = replace_once(server, old_admin_verify, new_admin_verify, 'admin login brute-force throttle')
elif 'ADMIN_LOGIN_MAX_ATTEMPTS' not in server or 'client_key=' not in server:
    raise RuntimeError('admin login throttle: expected current or patched login block')

SERVER.write_text(server, encoding='utf-8')
print('Secure unified login patch applied.')
