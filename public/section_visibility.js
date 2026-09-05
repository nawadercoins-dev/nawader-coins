// Visitor section visibility v2 — presentation only; server routes also enforce the same settings.
(()=>{
'use strict';
const PATH_KEYS={
  '/announcements':'announcements','/announcements.html':'announcements',
  '/live-auction':'liveAuction','/live_auction.html':'liveAuction',
  '/special-numbers':'specialNumbers','/special_numbers.html':'specialNumbers',
  '/transitional-issues':'transitionalIssues','/transitional_issues.html':'transitionalIssues',
  '/fantasia':'fantasia',
  '/collectibles':'collectiblesStore','/collectibles_home.html':'collectiblesStore'
};
const cleanPath=p=>{p=String(p||'/').replace(/\/+$/,'');return p||'/'};
function controlledHidden(el,hide){
  if(!el)return;
  if(hide){
    if(!el.hidden){el.hidden=true;el.dataset.sectionVisibilityHidden='1'}
  }else if(el.dataset.sectionVisibilityHidden==='1'){
    el.hidden=false;delete el.dataset.sectionVisibilityHidden;
  }
}
function enabled(vs,key){return !key || (vs||{})[key]!==false}
function linkVisible(a,vs){
  let u;try{u=new URL(a.getAttribute('href')||'',location.origin)}catch{return true}
  const p=cleanPath(u.pathname),store=String(u.searchParams.get('store')||'').toLowerCase();
  if((p==='/market'||p==='/public_market.html'||p==='/public-market') && !enabled(vs,'market'))return false;
  if((p==='/auction'||p==='/public_auction.html'||p==='/public-auction'||p==='/daily-auction') && !enabled(vs,'auction'))return false;
  if((p==='/market'||p==='/auction') && store==='collectibles' && !enabled(vs,'collectiblesStore'))return false;
  const key=PATH_KEYS[p];
  if(key && !enabled(vs,key))return false;
  if(p==='/fantasia' && !enabled(vs,'collectiblesStore'))return false;
  return true;
}
function apply(vs){
  vs=vs||{};
  document.querySelectorAll('[data-section]').forEach(el=>{
    const key=el.getAttribute('data-section');
    controlledHidden(el,!enabled(vs,key));
  });
  document.querySelectorAll('a[href]').forEach(a=>controlledHidden(a,!linkVisible(a,vs)));
  window.dispatchEvent(new CustomEvent('nawader-section-visibility',{detail:{visitorSections:vs}}));
}
async function refresh(){
  try{
    const r=await fetch('/api/settings/public',{cache:'no-store'});
    if(!r.ok)return;
    const d=await r.json();apply(d.visitorSections||{});
  }catch(_){ }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refresh,{once:true});else refresh();
window.NawaderSectionVisibility={refresh,apply};
window.refreshVisitorSections=refresh;
})();
