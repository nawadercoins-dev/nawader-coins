from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')
marker='data-entry-image-quick-actions-v1'
if marker in s:
    print('already applied')
    raise SystemExit(0)

css=r'''

/* data-entry-image-quick-actions-v1 */
.vault-selected-card img,.vault-pick img{cursor:zoom-in!important}
.de-inspect-viewer{position:fixed;inset:0;z-index:5000;background:#000e;display:flex;flex-direction:column;padding:10px}
.de-inspect-viewer.hidden{display:none!important}
.de-inspect-tools{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;align-items:center;padding:8px;background:#0a1929;border:1px solid #40566d;border-radius:12px;position:relative;z-index:2}
.de-inspect-stage{flex:1;min-height:0;overflow:hidden;display:grid;place-items:center;touch-action:none}
.de-inspect-stage img{max-width:94%;max-height:94%;object-fit:contain;transform-origin:center;user-select:none;cursor:grab;transition:filter .12s ease}
.de-inspect-stage img:active{cursor:grabbing}
.de-inspect-caption{text-align:center;padding:6px;color:#f0d995;font-weight:800}
.quick-record-bar{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:2200;width:min(960px,calc(100vw - 20px));background:#0a1929f5;border:1px solid #b99647;border-radius:16px;padding:10px;box-shadow:0 14px 36px #0009;display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap}
.quick-record-bar.hidden{display:none!important}.quick-record-bar .smallbtn{font-weight:900;background:#0d2034}.quick-record-bar .primary{background:#b99647;color:#071321;border-color:#b99647}.quick-record-count{color:#f0d995;font-weight:900;margin-inline:4px}
.row.assigned,.row.pending,.row.draft,.row.needs_changes{position:relative}.row.assigned:focus-within,.row.pending:focus-within,.row.draft:focus-within,.row.needs_changes:focus-within{outline:2px solid #d6b15a55;outline-offset:2px}
@media(max-width:560px){.quick-record-bar{bottom:6px;border-radius:12px}.quick-record-bar .smallbtn{flex:1 1 44%;min-width:0}.de-inspect-tools .smallbtn{flex:1 1 28%}}
'''
s=s.replace('</style>',css+'\n</style>',1)

js=r'''

// data-entry-image-quick-actions-v1
let DEINSPECT={imgs:[],idx:0,scale:1,x:0,y:0,rot:0,contrast:1,brightness:1,drag:false,px:0,py:0};
function drawDEInspect(){
  const im=document.getElementById('deInspectImg'); if(!im)return;
  im.style.transform=`translate(${DEINSPECT.x}px,${DEINSPECT.y}px) scale(${DEINSPECT.scale}) rotate(${DEINSPECT.rot}deg)`;
  im.style.filter=`contrast(${DEINSPECT.contrast}) brightness(${DEINSPECT.brightness})`;
  const c=document.getElementById('deInspectCaption'); if(c)c.textContent=DEINSPECT.imgs.length?`${DEINSPECT.idx+1} / ${DEINSPECT.imgs.length} — معاينة فقط، الأصل محفوظ في خزينة الصور`:'';
}
function openDEInspect(imgs,start=0){
  DEINSPECT.imgs=(imgs||[]).filter(Boolean); if(!DEINSPECT.imgs.length)return;
  DEINSPECT.idx=Math.max(0,Math.min(Number(start)||0,DEINSPECT.imgs.length-1));
  DEINSPECT.scale=1;DEINSPECT.x=0;DEINSPECT.y=0;DEINSPECT.rot=0;DEINSPECT.contrast=1;DEINSPECT.brightness=1;
  let v=document.getElementById('deInspectViewer');
  if(!v){
    v=document.createElement('div');v.id='deInspectViewer';v.className='de-inspect-viewer';
    v.innerHTML=`<div class="de-inspect-tools"><button class="smallbtn" data-di="close">✕ إغلاق</button><button class="smallbtn" data-di="prev">‹ السابق</button><button class="smallbtn" data-di="zin">＋ تكبير</button><button class="smallbtn" data-di="zout">− تصغير</button><button class="smallbtn" data-di="left">↶ تدوير</button><button class="smallbtn" data-di="right">↷ تدوير</button><button class="smallbtn" data-di="contrast">◐ وضوح</button><button class="smallbtn" data-di="bright">☀ إضاءة</button><button class="smallbtn" data-di="reset">◎ إظهار كامل</button><button class="smallbtn" data-di="next">التالي ›</button></div><div class="de-inspect-stage"><img id="deInspectImg" alt="معاينة مكبرة"></div><div id="deInspectCaption" class="de-inspect-caption"></div>`;
    document.body.appendChild(v);
    v.querySelectorAll('[data-di]').forEach(b=>b.onclick=()=>{
      const a=b.dataset.di;if(a==='close'){v.classList.add('hidden');return}
      if(a==='prev')DEINSPECT.idx=(DEINSPECT.idx-1+DEINSPECT.imgs.length)%DEINSPECT.imgs.length;
      if(a==='next')DEINSPECT.idx=(DEINSPECT.idx+1)%DEINSPECT.imgs.length;
      if(a==='zin')DEINSPECT.scale=Math.min(7,DEINSPECT.scale+.25);
      if(a==='zout')DEINSPECT.scale=Math.max(.3,DEINSPECT.scale-.25);
      if(a==='left')DEINSPECT.rot-=90;if(a==='right')DEINSPECT.rot+=90;
      if(a==='contrast')DEINSPECT.contrast=DEINSPECT.contrast>=1.8?1:Math.min(1.8,DEINSPECT.contrast+.2);
      if(a==='bright')DEINSPECT.brightness=DEINSPECT.brightness>=1.5?1:Math.min(1.5,DEINSPECT.brightness+.15);
      if(a==='reset'){DEINSPECT.scale=1;DEINSPECT.x=0;DEINSPECT.y=0;DEINSPECT.rot=0;DEINSPECT.contrast=1;DEINSPECT.brightness=1}
      document.getElementById('deInspectImg').src=DEINSPECT.imgs[DEINSPECT.idx];drawDEInspect();
    });
    const st=v.querySelector('.de-inspect-stage');
    st.onpointerdown=e=>{DEINSPECT.drag=true;DEINSPECT.px=e.clientX;DEINSPECT.py=e.clientY;st.setPointerCapture?.(e.pointerId)};
    st.onpointermove=e=>{if(!DEINSPECT.drag)return;DEINSPECT.x+=e.clientX-DEINSPECT.px;DEINSPECT.y+=e.clientY-DEINSPECT.py;DEINSPECT.px=e.clientX;DEINSPECT.py=e.clientY;drawDEInspect()};
    st.onpointerup=st.onpointercancel=()=>DEINSPECT.drag=false;
    st.onwheel=e=>{e.preventDefault();DEINSPECT.scale=Math.max(.3,Math.min(7,DEINSPECT.scale+(e.deltaY<0?.2:-.2)));drawDEInspect()};
  }
  v.classList.remove('hidden');document.getElementById('deInspectImg').src=DEINSPECT.imgs[DEINSPECT.idx];drawDEInspect();
}
window.openDEInspect=openDEInspect;

document.addEventListener('click',e=>{
  const im=e.target.closest?.('.vault-selected-card img,.vault-pick img');if(!im)return;
  e.preventDefault();e.stopPropagation();
  const scope=im.closest('.vault-selected,.vault-picker-grid')||document;
  const imgs=[...scope.querySelectorAll('.vault-selected-card img,.vault-pick img')].map(x=>x.currentSrc||x.src).filter(Boolean);
  const idx=Math.max(0,imgs.indexOf(im.currentSrc||im.src));openDEInspect(imgs,idx);
},true);

function ensureQuickRecordBar(){
  let b=document.getElementById('quickRecordBar');if(b)return b;
  b=document.createElement('div');b.id='quickRecordBar';b.className='quick-record-bar hidden';
  b.innerHTML=`<span id="quickRecordCount" class="quick-record-count"></span><button type="button" class="smallbtn" id="quickPreviewSelected">🔎 معاينة أول المحدد</button><button type="button" class="smallbtn" id="quickEditSelected">✎ فتح/تعديل أول المحدد</button><button type="button" class="smallbtn primary" id="quickSubmitSelected">✓ إرسال المحدد للاعتماد</button><button type="button" class="smallbtn" id="quickWithdrawSelected">↩ استرجاع المرسل للتعديل</button>`;
  document.body.appendChild(b);
  document.getElementById('quickPreviewSelected').onclick=()=>{const id=[...selectedAssignedRows,...selectedPendingRows,...selectedDraftRows][0];if(id)previewRowImages(id,0)};
  document.getElementById('quickEditSelected').onclick=()=>{const id=[...selectedAssignedRows,...selectedDraftRows][0];if(id)editRow(id)};
  document.getElementById('quickSubmitSelected').onclick=()=>submitAssignedSelection();
  document.getElementById('quickWithdrawSelected').onclick=()=>withdrawPendingRows([...selectedPendingRows]);
  return b;
}
function syncQuickRecordBar(){
  const b=ensureQuickRecordBar(),a=selectedAssignedRows.size,p=selectedPendingRows.size,d=selectedDraftRows.size,total=a+p+d;
  b.classList.toggle('hidden',!total);document.getElementById('quickRecordCount').textContent=total?`${total} محدد`:'';
  document.getElementById('quickPreviewSelected').disabled=!total;
  document.getElementById('quickEditSelected').disabled=!(a||d);
  document.getElementById('quickSubmitSelected').disabled=!a;
  document.getElementById('quickWithdrawSelected').disabled=!p;
}
const __syncDraftSelectionQuickBase=syncDraftSelection;
syncDraftSelection=function(){__syncDraftSelectionQuickBase();syncQuickRecordBar()};
setTimeout(syncQuickRecordBar,0);
'''
anchor='async function loadRows(){'
if anchor not in s:
    raise SystemExit('loadRows anchor not found')
s=s.replace(anchor,js+'\n'+anchor,1)
p.write_text(s,encoding='utf-8')
print('patched data-entry image inspection + quick record actions')
