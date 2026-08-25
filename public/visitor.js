// V4.9.0 — persistent participant session-aware visitor state and market-first launch.
(()=>{
const K='nawaderVisitor',C='nawaderCart';
const reactionKey=(kind)=>{let v=read(K,null);return (kind==='favorite'?'nawaderFavorites:':'nawaderLikes:')+(v?.id||'guest')};
const reactionList=(kind)=>read(reactionKey(kind),[]);
const reactionHas=(kind,id)=>reactionList(kind).some(x=>String(typeof x==='object'?x.id:x)===String(id));
const reactionToggle=(kind,item)=>{let a=reactionList(kind),id=String(item.id),on=reactionHas(kind,id);a=on?a.filter(x=>String(typeof x==='object'?x.id:x)!==id):[{id,title:item.title||'',image:item.image||'',url:item.url||location.pathname+'#'+encodeURIComponent(id),kind:item.kind||''},...a];write(reactionKey(kind),a);window.dispatchEvent(new CustomEvent('nawader-reaction-change',{detail:{kind,id,on:!on}}));toast(kind==='favorite'?(!on?'أضيف للمفضلة':'أزيل من المفضلة'):(!on?'تم تسجيل الإعجاب':'أزيل الإعجاب'));return !on};
const read=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))||d}catch{return d}};
const write=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
window.NawaderVisitor={
 get:()=>read(K,null), set:v=>{write(K,v);refresh()}, logout:()=>{localStorage.removeItem(K);fetch('/account-logout',{cache:'no-store'}).catch(()=>{});refresh();toast('تم تسجيل الخروج')},
 cart:()=>read(C,[]), add:item=>{let a=read(C,[]),x=a.find(z=>z.id===item.id);if(x)x.quantity=Math.min(Number(item.max||99),Number(x.quantity||1)+Number(item.quantity||1));else a.push(item);write(C,a);refresh();toast('تمت الإضافة إلى السلة')},
 remove:id=>{write(C,read(C,[]).filter(x=>x.id!==id));refresh();window.dispatchEvent(new Event('nawader-cart-change'))},
 clear:()=>{write(C,[]);refresh();window.dispatchEvent(new Event('nawader-cart-change'))},
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
document.addEventListener('click',e=>{if(e.target.closest('[data-back]'))history.back();if(e.target.closest('[data-logout]'))window.NawaderVisitor.logout();});
document.addEventListener('DOMContentLoaded',()=>{installVisitorNavigation();centerVisitorNavigation();refresh()});
if(document.body){installVisitorNavigation();centerVisitorNavigation()}
refresh();
})();

// V4.0.20: فصل واجهة العميل عن الإدارة بالكامل؛ لا تُحقن روابط الإدارة في الصفحات العامة.


/* V4.3.3 — Central visitor section visibility */
(function(){
  const sectionLinks={
    market:['/market','/public_market.html','/public-market'],
    auction:['/auction','/public_auction.html','/public-auction','/daily-auction'],
    specialNumbers:['/special-numbers','/special_numbers.html'],
    transitionalIssues:['/transitional-issues','/transitional_issues.html']
  };
  function pathOnly(href){
    try{return new URL(href,location.origin).pathname.replace(/\/+$/,'')||'/'}catch(e){return ''}
  }
  function setLinkVisibility(key,visible){
    const paths=(sectionLinks[key]||[]).map(x=>x.replace(/\/+$/,''));
    document.querySelectorAll('a[href]').forEach(a=>{
      const p=pathOnly(a.getAttribute('href'));
      if(paths.includes(p)) a.hidden=!visible;
    });
  }
  function apply(vs){
    vs=vs||{};
    const market=vs.market!==false, auction=vs.auction!==false,
      special=vs.specialNumbers!==false, transitional=vs.transitionalIssues!==false;
    setLinkVisibility('market',market);
    setLinkVisibility('auction',auction);
    setLinkVisibility('specialNumbers',special);
    setLinkVisibility('transitionalIssues',transitional);

    // Home-page image showcases follow the same switches.
    const auctionStrip=document.getElementById('auctionImageStrip');
    if(auctionStrip){
      const box=auctionStrip.closest('.showcase');
      if(box) box.hidden=!auction;
    }
    const marketStrip=document.getElementById('marketImageStrip');
    if(marketStrip){
      const box=marketStrip.closest('.showcase');
      if(box) box.hidden=!market;
    }
  }
  async function refresh(){
    try{
      const r=await fetch('/api/settings/public',{cache:'no-store'});
      if(!r.ok) return;
      const d=await r.json();
      apply(d.visitorSections||{});
    }catch(e){}
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',refresh,{once:true});
  else refresh();
  window.refreshVisitorSections=refresh;
})();
