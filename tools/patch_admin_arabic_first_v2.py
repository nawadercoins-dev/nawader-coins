from pathlib import Path
p=Path('admin/app.js')
s=p.read_text(encoding='utf-8')
marker='// admin-arabic-first-v2'
if marker in s:
    print('already patched')
    raise SystemExit(0)
old="    'Blackstick':'بلاستيك'"
new="    'Blackstick':'بلاك ستيك'"
if old in s:
    s=s.replace(old,new,1)
else:
    print('Blackstick mapping not found; continuing')
s += r'''

// admin-arabic-first-v2
// أسماء العلامات والأسماء الخاصة لا تُترجم ترجمة معنوية خاطئة.
// إذا ظهر الاسم الإنجليزي Blackstick في واجهة الإدارة، نعرضه كتابةً عربية فقط.
(function(){
  function fixProperNames(root=document){
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    nodes.forEach(n=>{
      const p=n.parentElement;if(!p||['SCRIPT','STYLE','CODE','PRE'].includes(p.tagName))return;
      const raw=String(n.nodeValue||'');
      if(raw.trim()==='Blackstick'||raw.trim()==='بلاستيك') n.nodeValue=raw.replace(raw.trim(),'بلاك ستيك');
    });
  }
  const run=()=>fixProperNames(document);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
  const mo=new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===Node.ELEMENT_NODE)fixProperNames(n);else if(n.nodeType===Node.TEXT_NODE&&['Blackstick','بلاستيك'].includes(String(n.nodeValue||'').trim()))n.nodeValue='بلاك ستيك';})));
  if(document.body)mo.observe(document.body,{childList:true,subtree:true});
})();
'''
p.write_text(s,encoding='utf-8')
print('patched admin Arabic-first UI v2')
