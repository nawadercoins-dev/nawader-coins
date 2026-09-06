(()=>{
'use strict';
const EXACT={
  'Dashboard':'لوحة التحكم','Home':'الرئيسية','Settings':'الإعدادات','Orders':'الطلبات','Finance':'المالية',
  'Market':'السوق العام','Auction':'المزاد','Auctions':'المزادات','Warehouse':'المستودع','Archive':'الأرشيف',
  'Notifications':'الإشعارات','Approvals':'الاعتمادات','Permissions':'الصلاحيات','Participants':'المشاركون',
  'Pending':'بانتظار الاعتماد','Approved':'معتمد','Rejected':'مرفوض','Paid':'مسدد','Unpaid':'غير مسدد',
  'Cancelled':'ملغي','Refunded':'مسترد','Ready to ship':'جاهز للشحن','Shipped':'تم الشحن','Delivered':'تم الاستلام',
  'Live':'مباشر','Scheduled':'مجدول','Ended':'منتهي','Close':'إغلاق','Save':'حفظ','Edit':'تعديل','Delete':'حذف',
  'Back':'رجوع','Next':'التالي','Previous':'السابق','Search':'بحث','All':'الكل','Open':'فتح'
};
const attrs=['title','placeholder','aria-label'];
function translateExact(s){const t=String(s??'').trim();return EXACT[t]||null}
function normalizeElement(el){
  if(!el||el.nodeType!==1)return;
  for(const a of attrs){if(el.hasAttribute?.(a)){const v=translateExact(el.getAttribute(a));if(v)el.setAttribute(a,v)}}
  for(const n of el.childNodes||[]){if(n.nodeType===3){const raw=n.nodeValue||'',v=translateExact(raw);if(v)n.nodeValue=raw.replace(raw.trim(),v)}}
}
function sweep(root=document){
  document.documentElement.lang='ar';document.documentElement.dir='rtl';
  if(document.body)document.body.dir='rtl';
  if(root.nodeType===1)normalizeElement(root);
  root.querySelectorAll?.('*').forEach(normalizeElement);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>sweep());else sweep();
new MutationObserver(ms=>{for(const m of ms){for(const n of m.addedNodes||[]){if(n.nodeType===1)sweep(n);else if(n.nodeType===3){const v=translateExact(n.nodeValue);if(v)n.nodeValue=v}}}}).observe(document.documentElement,{subtree:true,childList:true});
})();
