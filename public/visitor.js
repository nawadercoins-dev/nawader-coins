// V5.6.2-R8 — robust participant state, unified cart events, and section navigation.
(()=>{
const K='nawaderVisitor',C='nawaderCart';
const reactionKey=(kind)=>{let v=read(K,null);return (kind==='favorite'?'nawaderFavorites:':'nawaderLikes:')+(v?.id||'guest')};
const reactionList=(kind)=>read(reactionKey(kind),[]);
const reactionHas=(kind,id)=>reactionList(kind).some(x=>String(typeof x==='object'?x.id:x)===String(id));
const reactionToggle=(kind,item)=>{let a=reactionList(kind),id=String(item.id),on=reactionHas(kind,id);a=on?a.filter(x=>String(typeof x==='object'?x.id:x)!==id):[{id,title:item.title||'',image:item.image||'',url:item.url||location.pathname+'#'+encodeURIComponent(id),kind:item.kind||''},...a];write(reactionKey(kind),a);window.dispatchEvent(new CustomEvent('nawader-reaction-change',{detail:{kind,id,on:!on}}));toast(kind==='favorite'?(!on?'أضيف للمفضلة':'أزيل من المفضلة'):(!on?'تم تسجيل الإعجاب':'أزيل الإعجاب'));return !on};
const MEM={};
const read=(k,d)=>{try{const raw=localStorage.getItem(k);if(raw==null)return Object.prototype.hasOwnProperty.call(MEM,k)?MEM[k]:d;const v=JSON.parse(raw);MEM[k]=v;return v??d}catch{return Object.prototype.hasOwnProperty.call(MEM,k)?MEM[k]:d}};
const write=(k,v)=>{MEM[k]=v;try{localStorage.setItem(k,JSON.stringify(v));return true}catch{return false}};
const cartChanged=()=>window.dispatchEvent(new CustomEvent('nawader-cart-change',{detail:{items:read(C,[])}}));
window.NawaderVisitor={
 get:()=>read(K,null), set:v=>{write(K,v);refresh()}, logout:()=>{try{localStorage.removeItem(K)}catch{};delete MEM[K];fetch('/account-logout',{cache:'no-store'}).catch(()=>{});refresh();toast('تم تسجيل الخروج')},
 cart:()=>read(C,[]), add:item=>{let a=read(C,[]),id=String(item?.id??'');if(!id)return false;let x=a.find(z=>String(z.id)===id);const max=Math.max(1,Number(item.max||x?.max||99));if(x){x.quantity=Math.min(max,Number(x.quantity||1)+Math.max(1,Number(item.quantity||1)));x.max=max;if(item.unitPrice!=null)x.unitPrice=Number(item.unitPrice||0);if(item.title)x.title=item.title;if(item.unitLabel)x.unitLabel=item.unitLabel;if(item.storeType)x.storeType=item.storeType}else a.push({...item,id,quantity:Math.max(1,Number(item.quantity||1)),max});write(C,a);refresh();cartChanged();toast('تمت الإضافة إلى السلة');return true},
 setQuantity:(id,qty)=>{let a=read(C,[]),x=a.find(z=>String(z.id)===String(id));if(!x)return false;x.quantity=Math.max(1,Math.min(Math.max(1,Number(x.max||99)),Number(qty||1)));write(C,a);refresh();cartChanged();return true},
 remove:id=>{write(C,read(C,[]).filter(x=>String(x.id)!==String(id)));refresh();cartChanged()},
 clear:()=>{write(C,[]);refresh();cartChanged()},
 cartCount:()=>read(C,[]).reduce((n,x)=>n+Number(x.quantity||1),0),
 openCart:()=>window.dispatchEvent(new Event('nawader-cart-open')),
 favorites:()=>reactionList('favorite'), likes:()=>reactionList('like'),
 isFavorite:id=>reactionHas('favorite',id), isLiked:id=>reactionHas('like',id),
 toggleFavorite:item=>reactionToggle('favorite',item), toggleLike:item=>reactionToggle('like',item)
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
function centerVisitorNavigation(){
 const viewport=window.visualViewport;
 const center=viewport
  ? viewport.offsetLeft+(viewport.width/2)
  : window.innerWidth/2;
 document.documentElement.style.setProperty('--visitor-floating-center',`${Math.round(center)}px`);
}
window.addEventListener('resize',centerVisitorNavigation,{passive:true});
window.addEventListener('orientationchange',centerVisitorNavigation,{passive:true});
if(window.visualViewport){
 window.visualViewport.addEventListener('resize',centerVisitorNavigation,{passive:true});
 window.visualViewport.addEventListener('scroll',centerVisitorNavigation,{passive:true});
}
function refresh(){let v=read(K,null),n=read(C,[]).reduce((s,x)=>s+Number(x.quantity||1),0);document.querySelectorAll('[data-cart-count]').forEach(e=>e.textContent=n);document.querySelectorAll('[data-account-name]').forEach(e=>e.textContent=v?.name?`مرحباً ${v.name}`:'زائر');document.querySelectorAll('[data-logout]').forEach(e=>e.hidden=!v);document.querySelectorAll('[data-notification-count]').forEach(e=>e.textContent='0');if(v?.id)fetch('/api/participant/status?id='+encodeURIComponent(v.id),{cache:'no-store'}).then(async r=>{let d=await r.json().catch(()=>({}));if(r.status===401||r.status===403){write(K,{...v,sessionExpired:true});return}if(d.participant)write(K,{...v,...d.participant})}).catch(()=>{});if(v?.verified)fetch('/api/notifications?participantId='+encodeURIComponent(v.id),{cache:'no-store'}).then(r=>r.json()).then(d=>document.querySelectorAll('[data-notification-count]').forEach(e=>e.textContent=Number(d.unread||0))).catch(()=>{})}
document.addEventListener('click',e=>{if(e.target.closest('[data-back]'))history.back();if(e.target.closest('[data-logout]'))window.NawaderVisitor.logout();if(e.target.closest('[data-cart-open]')){e.preventDefault();window.NawaderVisitor.openCart()}});
document.addEventListener('DOMContentLoaded',()=>{installVisitorNavigation();centerVisitorNavigation();refresh()});
if(document.body){installVisitorNavigation();centerVisitorNavigation()}
refresh();
})();

// V4.0.20: فصل واجهة العميل عن الإدارة بالكامل؛ لا تُحقن روابط الإدارة في الصفحات العامة.

/* V4.3.3 — Central visitor section visibility */
(function(){
  if(document.querySelector('script[data-section-visibility]'))return;
  const s=document.createElement('script');s.src='/section_visibility.js?v=2';s.defer=true;s.dataset.sectionVisibility='1';document.head.appendChild(s);
})();
