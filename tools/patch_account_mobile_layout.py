from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = ROOT / 'public' / 'account.html'
text = ACCOUNT.read_text(encoding='utf-8')

marker = '/* mobile-login-layout-v1 */'
if marker not in text:
    css = r'''
/* mobile-login-layout-v1 */
@media (max-width:700px){
  html,body{width:100%;max-width:100%;overflow-x:hidden}
  body{font-size:15px}
  .hero{padding:14px 10px 12px}
  .top{width:100%;max-width:100%;display:block}
  .brand{text-align:center;margin-bottom:10px}
  .brand h1{font-size:1.7rem;line-height:1.3}
  .visitor-nav{display:flex;gap:6px;overflow-x:auto;white-space:nowrap;padding:2px 0 4px;max-width:100%;scrollbar-width:none}
  .visitor-nav::-webkit-scrollbar{display:none}
  .visitor-nav>a,.visitor-nav>button,.visitor-nav>details{flex:0 0 auto}
  .wrap{width:100%;max-width:100%;margin:0;padding:12px 10px 86px}
  .panel{width:100%;max-width:100%;margin:0 0 12px;padding:16px 12px;border-radius:16px;overflow:hidden}
  .auth-panel{width:100%;max-width:520px;margin:0 auto 12px}
  .auth-panel h2{margin:0 0 10px;text-align:center;font-size:1.35rem;line-height:1.45;color:#0b3260}
  .auth-help{margin:0 0 14px;text-align:center;line-height:1.8;font-size:.92rem;color:#455468}
  .login-methods{display:grid!important;grid-template-columns:1fr!important;gap:10px!important;margin:12px 0!important;width:100%;max-width:100%}
  .login-method{width:100%;max-width:100%;min-width:0;min-height:50px;padding:13px 10px;font-size:1rem;border-radius:12px}
  .auth-sep{margin:14px 0 10px}
  .auth-form,.auth-form[style]{display:grid!important;grid-template-columns:1fr!important;gap:10px!important;width:100%;max-width:100%}
  .auth-field,.auth-action{width:100%;max-width:100%;min-width:0;grid-column:1!important}
  .auth-field label{font-size:.9rem;text-align:right}
  .auth-form input,.auth-form select,.auth-form button{display:block;width:100%;max-width:100%;min-width:0;font-size:16px}
  .google-pending,#waVerifyBox{width:100%;max-width:100%;overflow-wrap:anywhere}
  .google-pending p,#waVerifyBox p{line-height:1.7}
  #msg{line-height:1.7;text-align:center;overflow-wrap:anywhere}
  .panel *{min-width:0}
}
@media (max-width:390px){
  .wrap{padding-left:8px;padding-right:8px}
  .panel{padding:14px 10px}
  .auth-panel h2{font-size:1.22rem}
  .auth-help{font-size:.88rem}
  .login-method{font-size:.95rem}
}
'''
    if '</style>' not in text:
        raise RuntimeError('style closing tag not found')
    text = text.replace('</style>', css + '\n</style>', 1)

old_block = '<div class="auth-sep"><span>التحقق برقم الجوال</span></div><div id="phoneLoginFields">'
new_block = '<div class="auth-sep" id="phoneLoginSep" hidden><span>التحقق برقم الجوال</span></div><div id="phoneLoginFields" hidden>'
if old_block in text:
    text = text.replace(old_block, new_block, 1)
elif 'id="phoneLoginSep"' not in text or 'id="phoneLoginFields" hidden' not in text:
    raise RuntimeError('phone login block not found')

old_click = "if($('showWaLogin'))$('showWaLogin').onclick=()=>{$('phoneLoginFields').scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>$('phone')?.focus(),250)};"
new_click = "if($('showWaLogin'))$('showWaLogin').onclick=()=>{$('phoneLoginSep').hidden=false;$('phoneLoginFields').hidden=false;$('phoneLoginFields').scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>$('phone')?.focus(),250)};"
if old_click in text:
    text = text.replace(old_click, new_click, 1)
elif new_click not in text:
    raise RuntimeError('WhatsApp login click handler not found')

g_old = "googleLinkMode=true;$('googlePending').hidden=false;$('googlePendingName').textContent=d.pending.name||'حساب Google';$('googlePendingEmail').textContent=d.pending.email||'';"
g_new = "googleLinkMode=true;$('googlePending').hidden=false;$('phoneLoginSep').hidden=false;$('phoneLoginFields').hidden=false;$('googlePendingName').textContent=d.pending.name||'حساب Google';$('googlePendingEmail').textContent=d.pending.email||'';"
if g_old in text:
    text = text.replace(g_old, g_new, 1)
elif g_new not in text:
    raise RuntimeError('Google pending block not found')

f_old = "facebookLinkMode=true;$('facebookPending').hidden=false;$('facebookPendingName').textContent=d.pending.name||'حساب Facebook';$('facebookPendingEmail').textContent=d.pending.email||'';"
f_new = "facebookLinkMode=true;$('facebookPending').hidden=false;$('phoneLoginSep').hidden=false;$('phoneLoginFields').hidden=false;$('facebookPendingName').textContent=d.pending.name||'حساب Facebook';$('facebookPendingEmail').textContent=d.pending.email||'';"
if f_old in text:
    text = text.replace(f_old, f_new, 1)
elif f_new not in text:
    raise RuntimeError('Facebook pending block not found')

ACCOUNT.write_text(text, encoding='utf-8')
print('Account mobile layout patch applied.')
