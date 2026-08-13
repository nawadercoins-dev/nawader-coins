(()=>{
const K='nawaderVisitor',C='nawaderCart';
const read=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))||d}catch{return d}};
const write=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
window.NawaderVisitor={
 get:()=>read(K,null), set:v=>{write(K,v);refresh()}, logout:()=>{localStorage.removeItem(K);refresh();toast('تم تسجيل الخروج')},
 cart:()=>read(C,[]), add:item=>{let a=read(C,[]),x=a.find(z=>z.id===item.id);if(x)x.quantity=Math.min(Number(item.max||99),Number(x.quantity||1)+Number(item.quantity||1));else a.push(item);write(C,a);refresh();toast('تمت الإضافة إلى السلة')},
 remove:id=>{write(C,read(C,[]).filter(x=>x.id!==id));refresh();window.dispatchEvent(new Event('nawader-cart-change'))},
 clear:()=>{write(C,[]);refresh();window.dispatchEvent(new Event('nawader-cart-change'))}
};
function toast(s){let e=document.createElement('div');e.className='visitor-toast';e.textContent=s;document.body.appendChild(e);setTimeout(()=>e.remove(),1800)} window.nawaderToast=toast;
function installVisitorNavigation(){
 if(document.querySelector('.visitor-floating-nav'))return;
 const nav=document.createElement('nav');
 nav.className='visitor-floating-nav';
 nav.setAttribute('aria-label','التنقل السريع');
 nav.innerHTML='<button type="button" data-visitor-back aria-label="الصفحة السابقة">↩<span>السابق</span></button><a href="/home" aria-label="الصفحة الرئيسية">⌂<span>الرئيسية</span></a><button type="button" data-visitor-forward aria-label="الصفحة التالية">↪<span>التالي</span></button>';
 document.body.appendChild(nav);
 document.body.classList.add('has-visitor-floating-nav');
 nav.querySelector('[data-visitor-back]').addEventListener('click',()=>{if(history.length>1)history.back();else location.href='/home'});
 nav.querySelector('[data-visitor-forward]').addEventListener('click',()=>history.forward());
}
function refresh(){let v=read(K,null),n=read(C,[]).reduce((s,x)=>s+Number(x.quantity||1),0);document.querySelectorAll('[data-cart-count]').forEach(e=>e.textContent=n);document.querySelectorAll('[data-account-name]').forEach(e=>e.textContent=v?.name?`مرحباً ${v.name}`:'زائر');document.querySelectorAll('[data-logout]').forEach(e=>e.hidden=!v);document.querySelectorAll('[data-notification-count]').forEach(e=>e.textContent='0');if(v?.verified)fetch('/api/notifications?participantId='+encodeURIComponent(v.id),{cache:'no-store'}).then(r=>r.json()).then(d=>document.querySelectorAll('[data-notification-count]').forEach(e=>e.textContent=Number(d.unread||0))).catch(()=>{})}
document.addEventListener('click',e=>{if(e.target.closest('[data-back]'))history.back();if(e.target.closest('[data-logout]'))window.NawaderVisitor.logout();});
document.addEventListener('DOMContentLoaded',()=>{installVisitorNavigation();refresh()});
if(document.body)installVisitorNavigation();
refresh();
})();

// V4.0.20: فصل واجهة العميل عن الإدارة بالكامل؛ لا تُحقن روابط الإدارة في الصفحات العامة.
