from pathlib import Path

APP=Path('admin/app.js')
s=APP.read_text(encoding='utf-8')
marker='// dues-action-containment-v5'
if marker in s:
    print('already patched')
    raise SystemExit(0)

s += r'''

// dues-action-containment-v5
(function(){
  function install(){
    if(document.getElementById('duesActionContainmentV5')) return;
    const st=document.createElement('style');
    st.id='duesActionContainmentV5';
    st.textContent=`
      #dues .dues-board{overflow:visible!important}
      #dues .dues-lane{min-width:0!important;overflow:hidden!important}
      #dues .due-row{display:block!important;position:relative!important;width:100%!important;max-width:100%!important;min-width:0!important;overflow:hidden!important;float:none!important;transform:none!important;box-sizing:border-box!important}
      #dues .due-row>div:first-child{display:block!important;width:100%!important;max-width:100%!important;min-width:0!important;overflow-wrap:anywhere!important}
      #dues .due-actions{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;width:100%!important;max-width:100%!important;min-width:0!important;margin:12px 0 0!important;padding:0!important;position:static!important;inset:auto!important;float:none!important;transform:none!important;box-sizing:border-box!important;overflow:hidden!important}
      #dues .due-actions button{display:flex!important;align-items:center!important;justify-content:center!important;width:100%!important;max-width:100%!important;min-width:0!important;min-height:44px!important;margin:0!important;padding:8px 6px!important;white-space:normal!important;overflow-wrap:anywhere!important;line-height:1.25!important;font-size:.80rem!important;box-sizing:border-box!important;position:static!important;float:none!important;transform:none!important}
      #dues .due-actions button:first-child{grid-column:1/-1!important}
      #dues .source-chip{max-width:100%!important;white-space:normal!important;text-align:center!important}
      @media(max-width:760px){#dues .due-actions{grid-template-columns:1fr!important}#dues .due-actions button:first-child{grid-column:auto!important}}
    `;
    document.head.appendChild(st);
  }
  function normalize(){
    install();
    const active=document.querySelector('#dues.view.active,#dues.active');
    if(!active) return;
    active.querySelectorAll('.due-actions').forEach(a=>{
      a.style.removeProperty('left');a.style.removeProperty('right');a.style.removeProperty('top');a.style.removeProperty('bottom');a.style.removeProperty('transform');
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',normalize);else normalize();
  document.addEventListener('click',()=>setTimeout(normalize,0),true);
  new MutationObserver(()=>setTimeout(normalize,0)).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
})();
'''
APP.write_text(s,encoding='utf-8')
print('patched dues action containment v5')
