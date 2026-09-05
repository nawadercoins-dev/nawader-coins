from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ACCOUNT=ROOT/'public'/'account.html'

def replace_once(text,old,new,label):
    count=text.count(old)
    if count!=1: raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old,new,1)

account=ACCOUNT.read_text(encoding="utf-8")
# Account page — extend the existing Google + WhatsApp entry with Facebook and role links.
UI_MARKER = 'id="facebookLogin"'
if UI_MARKER not in account:
    account = replace_once(
        account,
        '.login-methods{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}',
        '.login-methods{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}',
        'login grid columns',
    )
    account = replace_once(
        account,
        '.google-login{background:#fff;color:#1f1f1f;border:1px solid #cfd5dc}.google-login .g{font:900 21px Arial;color:#4285f4}.wa-login{background:#1f8f4d;color:#fff;border:1px solid #16713d}',
        '.google-login{background:#fff;color:#1f1f1f;border:1px solid #cfd5dc}.google-login .g{font:900 21px Arial;color:#4285f4}.facebook-login{background:#1877f2;color:#fff;border:1px solid #0f66d5}.facebook-login .f{font:900 22px Arial}.wa-login{background:#1f8f4d;color:#fff;border:1px solid #16713d}.role-login{background:#071b35;color:#fff;border:1px solid #071b35}.admin-login{background:#8a642b;color:#fff;border:1px solid #73511f}',
        'facebook login styles',
    )
    account = replace_once(
        account,
        '<section class="panel auth-panel" id="loginBox"><h2>تسجيل / دخول العميل أو البائع</h2><p class="auth-help"><b>الدخول السريع:</b> استخدم Google للدخول المباشر بعد ربط الجوال مرة واحدة، أو استخدم واتساب مباشرة.</p>',
        '<section class="panel auth-panel" id="loginBox"><h2>الدخول الموحد — دار المقتنيات</h2><p class="auth-help"><b>الدخول السريع:</b> استخدم Facebook أو Google للدخول المباشر بعد ربط الجوال مرة واحدة، أو استخدم واتساب مباشرة. العميل والبائع ومسؤول إدخال البيانات يستخدمون الحساب نفسه، والصلاحيات تحددها الإدارة داخل النظام.</p>',
        'unified login heading',
    )
    old_methods = '<div class="login-methods"><a class="login-method google-login" id="googleLogin" href="/auth/google"><span class="g">G</span><span>الدخول عبر Google</span></a><button class="login-method wa-login" id="showWaLogin" type="button">💬 الدخول عبر واتساب</button></div>'
    new_methods = '<div class="login-methods"><a class="login-method facebook-login" id="facebookLogin" href="/auth/facebook"><span class="f">f</span><span>الدخول عبر Facebook</span></a><a class="login-method google-login" id="googleLogin" href="/auth/google"><span class="g">G</span><span>الدخول عبر Google</span></a><button class="login-method wa-login" id="showWaLogin" type="button">💬 الدخول عبر واتساب</button><a class="login-method role-login" href="/data-entry">⌨ مسؤول إدخال البيانات</a><a class="login-method admin-login" href="/admin">🔐 الإدارة</a></div>'
    account = replace_once(account, old_methods, new_methods, 'facebook and role login methods')
    account = replace_once(
        account,
        '<div id="googlePending" class="google-pending" hidden><b>تم التحقق من حساب Google</b><div id="googlePendingName"></div><div id="googlePendingEmail"></div><p>أدخل رقم الجوال مرة واحدة فقط لربطه بالحساب والتحقق عبر واتساب.</p></div>',
        '<div id="googlePending" class="google-pending" hidden><b>تم التحقق من حساب Google</b><div id="googlePendingName"></div><div id="googlePendingEmail"></div><p>أدخل رقم الجوال مرة واحدة فقط لربطه بالحساب والتحقق عبر واتساب.</p></div><div id="facebookPending" class="google-pending" hidden><b>تم التحقق من حساب Facebook</b><div id="facebookPendingName"></div><div id="facebookPendingEmail"></div><p>أدخل رقم الجوال مرة واحدة فقط لربطه بالحساب والتحقق عبر واتساب.</p></div>',
        'facebook pending panel',
    )
    account = replace_once(
        account,
        '<p>بعد التحقق يتم تسجيل الدخول وربط Google تلقائيًا إذا بدأت منه.</p>',
        '<p>بعد التحقق يتم تسجيل الدخول وربط Facebook أو Google تلقائيًا إذا بدأت منه.</p>',
        'whatsapp social help',
    )

    old_js = """let googleLinkMode=false;
async function loadGoogleLoginState(){
  try{
    const q=new URLSearchParams(location.search),flag=q.get('google');
    let r=await fetch('/api/google/status',{cache:'no-store'}),d=await r.json();
    if($('googleLogin')){
      $('googleLogin').style.opacity=d.configured?'1':'.55';
      $('googleLogin').title=d.configured?'الدخول عبر Google':'يلزم إعداد مفاتيح Google في الخادم';
    }
    if(d.pending){
      googleLinkMode=true;$('googlePending').hidden=false;$('googlePendingName').textContent=d.pending.name||'حساب Google';$('googlePendingEmail').textContent=d.pending.email||'';
      if(d.pending.name)$('name').value=d.pending.name;$('register').textContent='ربط الجوال بـ Google والتحقق عبر واتساب';
    }else if(flag==='not-configured'){$('msg').textContent='⚠️ يلزم إعداد GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET و GOOGLE_REDIRECT_URI على الخادم أولًا.'}
    else if(flag==='cancelled'){$('msg').textContent='تم إلغاء الدخول عبر Google.'}
    else if(flag==='error'){$('msg').textContent='⚠️ تعذر إكمال الدخول عبر Google. أعد المحاولة.'}
  }catch(e){}
}
if($('showWaLogin'))$('showWaLogin').onclick=()=>{$('phoneLoginFields').scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>$('phone')?.focus(),250)};
if($('googleLogin'))$('googleLogin').onclick=e=>{if($('googleLogin').style.opacity==='.55'){e.preventDefault();$('msg').textContent='⚠️ Google غير مهيأ على الخادم بعد.'}};
$('register').onclick=async()=>{try{clearWaPending();$('waVerifyBox').hidden=true;let phone=$('phone').value.trim();if(!phone){$('msg').textContent='⚠️ رقم الجوال مطلوب';return}let r=await fetch(googleLinkMode?'/api/google/link/start':'/api/participant/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('name').value.trim(),phone,country:$('regCountry')?.value||'',googleLink:googleLinkMode})}),d=await r.json();if(!r.ok)throw Error(d.error||'تعذر إنشاء طلب التوثيق');if(!d.requestToken)throw Error('تعذر إنشاء مفتاح تحقق جديد. حدّث الصفحة وأعد المحاولة.');let pending={requestId:d.requestId,requestToken:d.requestToken,requestCode:d.requestCode,whatsappUrl:d.whatsappUrl,phone};saveWaPending(pending);showWaPending(pending);startWaPolling();$('msg').textContent=googleLinkMode?'✅ تم إنشاء طلب ربط Google بالجوال. افتح واتساب وأرسل الرسالة الجاهزة من نفس الرقم.':'✅ تم إنشاء طلب التوثيق. افتح واتساب وأرسل الرسالة الجاهزة من نفس الرقم.'}catch(e){$('msg').textContent='⚠️ '+e.message}};
$('waCheck').onclick=checkWaApproval;let restoredWa=getWaPending();if(restoredWa){showWaPending(restoredWa);startWaPolling();checkWaApproval()}
loadGoogleLoginState();
sync();window.addEventListener('storage',sync);"""
    new_js = """let googleLinkMode=false,facebookLinkMode=false;
function socialNext(){let n=new URLSearchParams(location.search).get('next')||'/account';return n.startsWith('/')&&!n.startsWith('//')?n:'/account'}
async function loadGoogleLoginState(){
  try{
    const q=new URLSearchParams(location.search),flag=q.get('google');
    if($('googleLogin'))$('googleLogin').href='/auth/google?next='+encodeURIComponent(socialNext());
    let r=await fetch('/api/google/status',{cache:'no-store'}),d=await r.json();
    if($('googleLogin')){
      $('googleLogin').style.opacity=d.configured?'1':'.55';
      $('googleLogin').title=d.configured?'الدخول عبر Google':'يلزم إعداد مفاتيح Google في الخادم';
    }
    if(d.pending){
      googleLinkMode=true;$('googlePending').hidden=false;$('googlePendingName').textContent=d.pending.name||'حساب Google';$('googlePendingEmail').textContent=d.pending.email||'';
      if(d.pending.name)$('name').value=d.pending.name;$('register').textContent='ربط الجوال بـ Google والتحقق عبر واتساب';
    }else if(flag==='not-configured'){$('msg').textContent='⚠️ يلزم إعداد مفاتيح Google على الخادم أولًا.'}
    else if(flag==='cancelled'){$('msg').textContent='تم إلغاء الدخول عبر Google.'}
    else if(flag==='error'){$('msg').textContent='⚠️ تعذر إكمال الدخول عبر Google. أعد المحاولة.'}
  }catch(e){}
}
async function loadFacebookLoginState(){
  try{
    const q=new URLSearchParams(location.search),flag=q.get('facebook');
    if($('facebookLogin'))$('facebookLogin').href='/auth/facebook?next='+encodeURIComponent(socialNext());
    let r=await fetch('/api/facebook/status',{cache:'no-store'}),d=await r.json();
    if($('facebookLogin')){
      $('facebookLogin').style.opacity=d.configured?'1':'.55';
      $('facebookLogin').title=d.configured?'الدخول عبر Facebook':'يلزم إعداد مفاتيح Facebook في الخادم';
    }
    if(d.pending){
      facebookLinkMode=true;$('facebookPending').hidden=false;$('facebookPendingName').textContent=d.pending.name||'حساب Facebook';$('facebookPendingEmail').textContent=d.pending.email||'';
      if(d.pending.name)$('name').value=d.pending.name;$('register').textContent='ربط الجوال بـ Facebook والتحقق عبر واتساب';
    }else if(flag==='not-configured'){$('msg').textContent='⚠️ يلزم إعداد مفاتيح Facebook على الخادم أولًا.'}
    else if(flag==='cancelled'){$('msg').textContent='تم إلغاء الدخول عبر Facebook.'}
    else if(flag==='blocked'){$('msg').textContent='⚠️ هذا الحساب موقوف أو غير متاح للدخول.'}
    else if(flag==='error'){$('msg').textContent='⚠️ تعذر إكمال الدخول عبر Facebook. أعد المحاولة.'}
  }catch(e){}
}
if($('showWaLogin'))$('showWaLogin').onclick=()=>{$('phoneLoginFields').scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>$('phone')?.focus(),250)};
if($('googleLogin'))$('googleLogin').onclick=e=>{if($('googleLogin').style.opacity==='.55'){e.preventDefault();$('msg').textContent='⚠️ Google غير مهيأ على الخادم بعد.'}};
if($('facebookLogin'))$('facebookLogin').onclick=e=>{if($('facebookLogin').style.opacity==='.55'){e.preventDefault();$('msg').textContent='⚠️ Facebook غير مهيأ على الخادم بعد.'}};
$('register').onclick=async()=>{try{clearWaPending();$('waVerifyBox').hidden=true;let phone=$('phone').value.trim();if(!phone){$('msg').textContent='⚠️ رقم الجوال مطلوب';return}let endpoint=facebookLinkMode?'/api/facebook/link/start':googleLinkMode?'/api/google/link/start':'/api/participant/register';let r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('name').value.trim(),phone,country:$('regCountry')?.value||'',googleLink:googleLinkMode,facebookLink:facebookLinkMode})}),d=await r.json();if(!r.ok)throw Error(d.error||'تعذر إنشاء طلب التوثيق');if(!d.requestToken)throw Error('تعذر إنشاء مفتاح تحقق جديد. حدّث الصفحة وأعد المحاولة.');let pending={requestId:d.requestId,requestToken:d.requestToken,requestCode:d.requestCode,whatsappUrl:d.whatsappUrl,phone};saveWaPending(pending);showWaPending(pending);startWaPolling();$('msg').textContent=facebookLinkMode?'✅ تم إنشاء طلب ربط Facebook بالجوال. افتح واتساب وأرسل الرسالة الجاهزة من نفس الرقم.':googleLinkMode?'✅ تم إنشاء طلب ربط Google بالجوال. افتح واتساب وأرسل الرسالة الجاهزة من نفس الرقم.':'✅ تم إنشاء طلب التوثيق. افتح واتساب وأرسل الرسالة الجاهزة من نفس الرقم.'}catch(e){$('msg').textContent='⚠️ '+e.message}};
$('waCheck').onclick=checkWaApproval;let restoredWa=getWaPending();if(restoredWa){showWaPending(restoredWa);startWaPolling();checkWaApproval()}
loadGoogleLoginState();loadFacebookLoginState();
sync();window.addEventListener('storage',sync);"""
    account = replace_once(account, old_js, new_js, 'unified social login javascript')

ACCOUNT.write_text(account, encoding='utf-8')
print('Facebook account patch applied successfully.')
