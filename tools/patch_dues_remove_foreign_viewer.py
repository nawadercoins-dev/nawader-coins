from pathlib import Path
p=Path('admin/app.js')
s=p.read_text(encoding='utf-8')
marker='// dues-foreign-viewer-cleanup-v4'
if marker not in s:
    s += r'''

// dues-foreign-viewer-cleanup-v4
(function(){
  const cues=['السابق','تكبير','تصغير','تدوير','توسيط','إظهار كامل','100%','ملء الشاشة','التالي'];
  function duesActive(){return !!document.querySelector('#dues.view.active, #dues.active');}
  function score(el){
    const txt=(el.innerText||'').replace(/\s+/g,' ');
    return cues.reduce((n,c)=>n+(txt.includes(c)?1:0),0);
  }
  function hideForeignViewer(){
    if(!duesActive()) return;
    const candidates=[...document.querySelectorAll('section,div,dialog,aside')];
    for(const el of candidates){
      if(el.closest('#dues')) continue;
      if(score(el)<5) continue;
      const r=el.getBoundingClientRect();
      if(r.height<180 || r.width<420) continue;
      el.dataset.hiddenOnDues='1';
      el.style.setProperty('display','none','important');
    }
    document.querySelectorAll('.image-viewer,.viewer-tools').forEach(el=>{
      if(!el.closest('#dues')) el.style.setProperty('display','none','important');
    });
  }
  function restoreOutsideDues(){
    if(duesActive()) return;
    document.querySelectorAll('[data-hidden-on-dues="1"]').forEach(el=>{el.style.removeProperty('display');delete el.dataset.hiddenOnDues;});
    document.querySelectorAll('.image-viewer,.viewer-tools').forEach(el=>el.style.removeProperty('display'));
  }
  const sync=()=>{if(duesActive()) hideForeignViewer(); else restoreOutsideDues();};
  document.addEventListener('click',()=>setTimeout(sync,0),true);
  new MutationObserver(()=>setTimeout(sync,0)).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',sync); else sync();
})();
'''
    p.write_text(s,encoding='utf-8')
print('patched dues foreign viewer cleanup v4')
