from pathlib import Path

p=Path('admin/app.js')
s=p.read_text(encoding='utf-8')
marker='// admin-arabic-first-v1'
if marker in s:
    print('already patched')
    raise SystemExit(0)

s += r'''

// admin-arabic-first-v1
(function(){
  const MAP={
    'Dashboard':'لوحة التحكم',
    'Home':'الرئيسية',
    'Settings':'الإعدادات',
    'Orders':'الطلبات',
    'Order':'طلب',
    'Finance':'المالية',
    'Market':'السوق العام',
    'Auction':'المزاد',
    'Auctions':'المزادات',
    'Warehouse':'المستودع',
    'Approvals':'الاعتمادات',
    'Approval':'الاعتماد',
    'Live':'البث المباشر',
    'Archive':'الأرشيف',
    'Notifications':'الإشعارات',
    'Reports':'التقارير',
    'Search':'بحث',
    'Save':'حفظ',
    'Edit':'تعديل',
    'Delete':'حذف',
    'Cancel':'إلغاء',
    'Close':'إغلاق',
    'Open':'فتح',
    'View':'عرض',
    'Details':'التفاصيل',
    'Status':'الحالة',
    'Pending':'بانتظار الاعتماد',
    'Approved':'معتمد',
    'Rejected':'مرفوض',
    'Paid':'مسدد',
    'Unpaid':'غير مسدد',
    'Ready to ship':'جاهز للشحن',
    'Shipped':'تم الشحن',
    'Delivered':'تم الاستلام',
    'Completed':'مكتمل',
    'Cancelled':'ملغي',
    'Refunded':'مسترد',
    'Customer':'العميل',
    'Seller':'البائع',
    'Buyer':'المشتري',
    'Amount':'المبلغ',
    'Quantity':'الكمية',
    'Shipping':'الشحن',
    'Tracking':'التتبع',
    'Profile':'الحساب',
    'Logout':'خروج الإدارة',
    'Blackstick':'بلاستيك'
  };
  const ATTRS=['title','aria-label','placeholder'];
  function tr(v){const x=String(v||'').trim();return MAP[x]||v}
  function translateNode(root=document){
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const nodes=[]; while(walker.nextNode())nodes.push(walker.currentNode);
    nodes.forEach(n=>{
      const parent=n.parentElement;if(!parent||['SCRIPT','STYLE','CODE','PRE'].includes(parent.tagName))return;
      const raw=n.nodeValue||'', trimmed=raw.trim(); if(!trimmed||!MAP[trimmed])return;
      n.nodeValue=raw.replace(trimmed,MAP[trimmed]);
    });
    const els=root.querySelectorAll?root.querySelectorAll('*'):[];
    els.forEach(el=>ATTRS.forEach(a=>{if(el.hasAttribute(a)){const v=el.getAttribute(a);const nv=tr(v);if(nv!==v)el.setAttribute(a,nv)}}));
    document.documentElement.lang='ar';document.documentElement.dir='rtl';
    document.body&&document.body.setAttribute('dir','rtl');
  }
  const boot=()=>{
    translateNode(document);
    const mo=new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{
      if(n.nodeType===Node.ELEMENT_NODE)translateNode(n);
      else if(n.nodeType===Node.TEXT_NODE&&MAP[String(n.nodeValue||'').trim()])n.nodeValue=tr(n.nodeValue);
    })));
    mo.observe(document.body,{childList:true,subtree:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
'''

p.write_text(s,encoding='utf-8')
print('patched admin Arabic-first UI v1')
