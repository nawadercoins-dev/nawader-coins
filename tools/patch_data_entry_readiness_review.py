from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')

# 1) Add a clear readiness board for assigned records.
needle='''        <div class="workflow-label">2) قيد الإدخال — تعديل ثم إرسال للاعتماد</div>\n        <div class="assignment-toolbar assigned-toolbar">'''
board='''        <div class="workflow-label">2) قيد الإدخال — تدقيق واستكمال ثم إرسال للاعتماد</div>\n        <div class="readiness-board" id="assignedReadinessBoard">\n          <button type="button" class="readiness-box ready" id="showReadyAssigned">✅ جاهزة للاعتماد <b id="readyAssignedCount">0</b></button>\n          <button type="button" class="readiness-box manual" id="showManualAssigned">🛠 تحتاج تدخل يدوي <b id="manualAssignedCount">0</b></button>\n          <button type="button" class="smallbtn" id="showAllAssigned">عرض الكل</button>\n        </div>\n        <div class="assignment-toolbar assigned-toolbar">'''
if 'id="assignedReadinessBoard"' not in s:
    if needle not in s: raise SystemExit('assigned workflow label not found')
    s=s.replace(needle,board,1)

# 2) Extend viewer state and transform with non-destructive rotation/enhancement.
s=s.replace("let DEVIEW={imgs:[],idx:0,scale:1,x:0,y:0,drag:false,px:0,py:0};",
            "let DEVIEW={imgs:[],idx:0,scale:1,x:0,y:0,rot:0,enhance:false,drag:false,px:0,py:0};")
s=s.replace("function drawDEViewer(){const im=document.getElementById('deViewerImg');if(im)im.style.transform=`translate(${DEVIEW.x}px,${DEVIEW.y}px) scale(${DEVIEW.scale})`;const c=document.getElementById('deViewerCaption');if(c)c.textContent=DEVIEW.imgs.length?`${DEVIEW.idx+1} / ${DEVIEW.imgs.length}`:''}",
            "function drawDEViewer(){const im=document.getElementById('deViewerImg');if(im){im.style.transform=`translate(${DEVIEW.x}px,${DEVIEW.y}px) scale(${DEVIEW.scale}) rotate(${DEVIEW.rot}deg)`;im.style.filter=DEVIEW.enhance?'contrast(1.35) brightness(1.08) saturate(.92)':'none'}const c=document.getElementById('deViewerCaption');if(c)c.textContent=DEVIEW.imgs.length?`${DEVIEW.idx+1} / ${DEVIEW.imgs.length}`:''}")
s=s.replace("DEVIEW.idx=Math.max(0,Math.min(idx,DEVIEW.imgs.length-1));DEVIEW.scale=1;DEVIEW.x=DEVIEW.y=0;",
            "DEVIEW.idx=Math.max(0,Math.min(idx,DEVIEW.imgs.length-1));DEVIEW.scale=1;DEVIEW.x=DEVIEW.y=0;DEVIEW.rot=0;DEVIEW.enhance=false;")
old_tools='''<button class="smallbtn" data-dv="close">✕ إغلاق</button><button class="smallbtn" data-dv="prev">‹ السابق</button><button class="smallbtn" data-dv="zin">＋ تكبير</button><button class="smallbtn" data-dv="zout">− تصغير</button><button class="smallbtn" data-dv="reset">إظهار كامل</button><button class="smallbtn" data-dv="next">التالي ›</button>'''
new_tools='''<button class="smallbtn" data-dv="close">✕ إغلاق</button><button class="smallbtn" data-dv="prev">‹ السابق</button><button class="smallbtn" data-dv="zin">＋ تكبير</button><button class="smallbtn" data-dv="zout">− تصغير</button><button class="smallbtn" data-dv="rleft">↺ تدوير</button><button class="smallbtn" data-dv="rright">↻ تدوير</button><button class="smallbtn" data-dv="enhance">◐ تحسين القراءة</button><button class="smallbtn" data-dv="reset">إظهار كامل</button><button class="smallbtn" data-dv="next">التالي ›</button>'''
if old_tools in s: s=s.replace(old_tools,new_tools,1)
old_logic="if(a==='zin')DEVIEW.scale=Math.min(6,DEVIEW.scale+.25);if(a==='zout')DEVIEW.scale=Math.max(.35,DEVIEW.scale-.25);if(a==='reset'){DEVIEW.scale=1;DEVIEW.x=DEVIEW.y=0}"
new_logic="if(a==='zin')DEVIEW.scale=Math.min(6,DEVIEW.scale+.25);if(a==='zout')DEVIEW.scale=Math.max(.35,DEVIEW.scale-.25);if(a==='rleft')DEVIEW.rot=(DEVIEW.rot-90)%360;if(a==='rright')DEVIEW.rot=(DEVIEW.rot+90)%360;if(a==='enhance')DEVIEW.enhance=!DEVIEW.enhance;if(a==='reset'){DEVIEW.scale=1;DEVIEW.x=DEVIEW.y=0;DEVIEW.rot=0;DEVIEW.enhance=false}"
if old_logic in s: s=s.replace(old_logic,new_logic,1)

# 3) Add readiness filtering state/helpers immediately before renderRows.
marker='''function renderRows(){\n'''
helper='''let assignedReadinessFilter='all';\nfunction assignedReadiness(r){\n  const missing=missingFor(rowAsData(r));\n  return {missing,ready:missing.length===0};\n}\nfunction syncAssignedReadiness(){\n  const assigned=rows.filter(r=>r.status==='assigned');\n  const ready=assigned.filter(r=>assignedReadiness(r).ready);\n  const manual=assigned.filter(r=>!assignedReadiness(r).ready);\n  if($('readyAssignedCount'))$('readyAssignedCount').textContent=ready.length;\n  if($('manualAssignedCount'))$('manualAssignedCount').textContent=manual.length;\n  if($('showReadyAssigned'))$('showReadyAssigned').classList.toggle('active',assignedReadinessFilter==='ready');\n  if($('showManualAssigned'))$('showManualAssigned').classList.toggle('active',assignedReadinessFilter==='manual');\n  if($('showAllAssigned'))$('showAllAssigned').classList.toggle('active',assignedReadinessFilter==='all');\n}\n\nfunction renderRows(){\n'''
if 'function assignedReadiness(r)' not in s:
    if marker not in s: raise SystemExit('renderRows marker missing')
    s=s.replace(marker,helper,1)

# 4) Filter only assigned records when a readiness box is chosen.
s=s.replace("  $('rows').innerHTML=rows.map(r=>{",
            "  const visibleRows=rows.filter(r=>r.status!=='assigned'||assignedReadinessFilter==='all'||(assignedReadinessFilter==='ready'?assignedReadiness(r).ready:!assignedReadiness(r).ready));\n  $('rows').innerHTML=visibleRows.map(r=>{",1)

# 5) Compute missing fields/readiness per card.
old_const="const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),assignedSelectable=r.status==='assigned',recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';"
new_const="const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),assignedSelectable=r.status==='assigned',recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'',readiness=r.status==='assigned'?assignedReadiness(r):{missing:[],ready:false};"
if old_const in s: s=s.replace(old_const,new_const,1)
elif 'readiness=r.status' not in s: raise SystemExit('render row const marker missing')

# 6) Add visible readiness/missing-data notice under metadata.
meta='''    <div class="meta"><span class="chip store-chip">${esc(STORE_LABELS[store])}</span>${category?`<span>التصنيف: ${esc(category)}</span>`:''}<span>${esc(r.year||'')}</span><span>الكمية: ${Number(r.quantity||r.inventoryUnitCount||1)}</span><span>شراء: ${Number(r.purchase||0).toLocaleString('ar-SA')}</span><span>بيع: ${Number(r.salePrice||r.expectedPrice||0).toLocaleString('ar-SA')}</span></div>\n'''
notice=meta+'''    ${r.status==='assigned'?(readiness.ready?`<div class="readiness-note ready">✅ جاهز للاعتماد — راجع الصورة والبيانات ثم أرسله.</div>`:`<div class="readiness-note manual"><b>🛠 يحتاج استكمال يدوي قبل الاعتماد:</b> ${readiness.missing.map(esc).join('، ')} <button type="button" class="smallbtn" onclick="editRow('${esc(r.id)}')">فتح وإكمال الآن</button></div>`):''}\n'''
if 'يحتاج استكمال يدوي قبل الاعتماد' not in s:
    if meta not in s: raise SystemExit('meta block marker missing')
    s=s.replace(meta,notice,1)

# 7) Make failed bulk submit actionable: show exact missing fields and switch to manual queue.
old_incomplete="""  if(incomplete.length){\n    setNotice(`يوجد ${incomplete.length} مقتنى ناقص. افتح «تعديل المحدد» وأكمل: ${[...new Set(incomplete.flatMap(x=>x.missing))].join('، ')}.`,'error');\n    return;\n  }\n  if(!confirm(`إرسال ${selected.length} مقتنى محدد للإدارة للاعتماد؟`))return;\n"""
new_incomplete="""  if(incomplete.length){\n    assignedReadinessFilter='manual';renderRows();\n    const fields=[...new Set(incomplete.flatMap(x=>x.missing))].join('، ');\n    setNotice(`⚠️ تعذر إرسال ${incomplete.length} مقتنى لأنها غير جاهزة. البيانات الناقصة: ${fields}. تم فتح خانة «تحتاج تدخل يدوي» لإكمالها الآن.`,'error');\n    document.querySelector('.row.assigned .readiness-note.manual')?.scrollIntoView({behavior:'smooth',block:'center'});\n    return;\n  }\n  if(!confirm(`تم فحص الحقول الأساسية لـ ${selected.length} مقتنى. هل راجعت الصورة والسنة/الرقم/الفئة ودققت البيانات قبل إرسالها للإدارة؟`))return;\n"""
if old_incomplete in s: s=s.replace(old_incomplete,new_incomplete,1)
elif 'تم فتح خانة «تحتاج تدخل يدوي»' not in s: raise SystemExit('bulk incomplete marker missing')

# 8) Keep board counts synced after every render and add filter handlers.
s=s.replace("  syncDraftSelection()\n}","  syncDraftSelection();syncAssignedReadiness()\n}",1)
handler_marker="if($('selectAllAssignedRows')) $('selectAllAssignedRows').onclick=()=>{selectedAssignedRows=new Set(rows.filter(r=>r.status==='assigned').map(r=>String(r.id)));renderRows()};\n"
handlers="""if($('showReadyAssigned')) $('showReadyAssigned').onclick=()=>{assignedReadinessFilter='ready';renderRows()};\nif($('showManualAssigned')) $('showManualAssigned').onclick=()=>{assignedReadinessFilter='manual';renderRows()};\nif($('showAllAssigned')) $('showAllAssigned').onclick=()=>{assignedReadinessFilter='all';renderRows()};\n"""
if "assignedReadinessFilter='ready'" not in s:
    if handler_marker not in s: raise SystemExit('assigned selector handler marker missing')
    s=s.replace(handler_marker,handlers+handler_marker,1)

# 9) Make 'select all assigned' respect the chosen readiness box.
s=s.replace("if($('selectAllAssignedRows')) $('selectAllAssignedRows').onclick=()=>{selectedAssignedRows=new Set(rows.filter(r=>r.status==='assigned').map(r=>String(r.id)));renderRows()};",
            "if($('selectAllAssignedRows')) $('selectAllAssignedRows').onclick=()=>{selectedAssignedRows=new Set(rows.filter(r=>r.status==='assigned'&&(assignedReadinessFilter==='all'||(assignedReadinessFilter==='ready'?assignedReadiness(r).ready:!assignedReadiness(r).ready))).map(r=>String(r.id)));renderRows()};",1)

# 10) Styling for the two readiness boxes and review prompts.
if 'data-entry-readiness-review-v1' not in s:
    css='''\n/* data-entry-readiness-review-v1 */\n.readiness-board{display:grid;grid-template-columns:1fr 1fr auto;gap:10px;margin:10px 0 12px}.readiness-box{border:1px solid #ffffff22;border-radius:14px;padding:12px 14px;font-weight:900;background:#0b1732;color:#fff;cursor:pointer}.readiness-box.ready{border-color:#42d39288;background:#0b2b25}.readiness-box.manual{border-color:#e0ac5788;background:#392914}.readiness-box.active{outline:2px solid #f0d995;box-shadow:0 0 0 3px #f0d99522}.readiness-box b{display:inline-grid;place-items:center;min-width:28px;height:28px;border-radius:999px;background:#ffffff18;margin-inline-start:8px}.readiness-note{margin:8px 0;padding:10px 12px;border-radius:12px;font-weight:750}.readiness-note.ready{background:#12392d;border:1px solid #42d39266}.readiness-note.manual{background:#3a2914;border:1px solid #e0ac5766}.readiness-note.manual .smallbtn{margin-inline-start:8px}.de-viewer-tools{max-height:30vh;overflow:auto}.de-viewer-stage img{transform-origin:center center;will-change:transform,filter}\n@media(max-width:700px){.readiness-board{grid-template-columns:1fr 1fr}.readiness-board>#showAllAssigned{grid-column:1/-1}.readiness-box{font-size:.9rem;padding:10px 8px}}\n'''
    s=s.replace('</style>',css+'\n</style>',1)

# Validation markers.
required=['assignedReadinessBoard','function assignedReadiness(r)','يحتاج استكمال يدوي قبل الاعتماد','readyAssignedCount','manualAssignedCount','data-dv="rleft"','data-dv="enhance"','data-entry-readiness-review-v1']
for x in required:
    if x not in s: raise SystemExit('missing after patch: '+x)

p.write_text(s,encoding='utf-8')
print('patched data-entry readiness review and image tools')
