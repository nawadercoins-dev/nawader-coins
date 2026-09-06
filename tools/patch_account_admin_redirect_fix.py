from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'public'/'account.html'
s=P.read_text(encoding='utf-8')
mark='account-admin-redirect-fix-v1'
if mark not in s:
    old="""async function routeAuthenticatedRole(){
  try{
    const r=await fetch('/api/auth/route',{cache:'no-store'}),d=await r.json();
    if(r.ok&&d.authenticated&&d.role==='admin'&&d.redirect&&d.redirect!='/account'){
      location.replace(d.redirect);return true;
    }
  }catch(e){}
  return false;
}
routeAuthenticatedRole().then(routed=>{if(!routed){loadGoogleLoginState();loadFacebookLoginState();sync();window.addEventListener('storage',sync)}});"""
    new="""// account-admin-redirect-fix-v1
// /account is a customer-facing page. Never force an authenticated admin session
// away from it; admins must be able to test the buyer checkout/order flow explicitly.
async function routeAuthenticatedRole(){ return false; }
loadGoogleLoginState();
loadFacebookLoginState();
sync();
window.addEventListener('storage',sync);"""
    if old not in s:
        raise RuntimeError('account role redirect block not found')
    s=s.replace(old,new,1)
    P.write_text(s,encoding='utf-8')
print('Account admin redirect fix applied.')
