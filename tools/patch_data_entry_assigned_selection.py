from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')

if 'id="selectAllAssignedRows"' not in s:
    marker='        <div class="assignment-toolbar pending-toolbar">\n'
    insert='''        <div class="assignment-toolbar assigned-toolbar">\n          <button id="selectAllAssignedRows" type="button" class="smallbtn">تحديد كل قيد الإدخال</button>\n          <button id="clearAssignedSelection" type="button" class="smallbtn">إلغاء التحديد</button>\n          <button id="openSelectedAssigned" type="button" class="btn ghost">✎ فتح أول المحدد</button>\n          <span id="assignedSelectionCount" class="muted">0 محدد</span>\n        </div>\n'''
    if marker not in s: raise SystemExit('pending toolbar marker missing')
    s=s.replace(marker,insert+marker,1)

if 'selectedAssignedRows=new Set()' not in s:
    old='let selectedDraftRows=new Set(),selectedPendingRows=new Set();'
    if old not in s: raise SystemExit('selection declaration missing')
    s=s.replace(old,'let selectedDraftRows=new Set(),selectedAssignedRows=new Set(),selectedPendingRows=new Set();',1)

if "const assigned=rows.filter(r=>r.status==='assigned');" not in s:
    old="  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));\n  const pending=rows.filter(r=>r.status==='pending');"
    if old not in s: raise SystemExit('sync filter block missing')
    s=s.replace(old,"  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));\n  const assigned=rows.filter(r=>r.status==='assigned');\n  const pending=rows.filter(r=>r.status==='pending');",1)
if 'selectedAssignedRows=new Set([...selectedAssignedRows]' not in s:
    old='  selectedDraftRows=new Set([...selectedDraftRows].filter(id=>drafts.some(r=>String(r.id)===String(id))));\n'
    if old not in s: raise SystemExit('draft selection sync missing')
    s=s.replace(old,old+'  selectedAssignedRows=new Set([...selectedAssignedRows].filter(id=>assigned.some(r=>String(r.id)===String(id))));\n',1)
if "$('assignedSelectionCount')" not in s:
    old="  if($('draftSelectionCount'))$('draftSelectionCount').textContent=`${selectedDraftRows.size} محدد`;\n"
    if old not in s: raise SystemExit('draft count sync missing')
    s=s.replace(old,old+"  if($('assignedSelectionCount'))$('assignedSelectionCount').textContent=`${selectedAssignedRows.size} محدد`;\n",1)
if "$('openSelectedAssigned')" not in s:
    old="  if($('assignSelectedDrafts'))$('assignSelectedDrafts').disabled=!selectedDraftRows.size;\n"
    if old not in s: raise SystemExit('draft button sync missing')
    s=s.replace(old,old+"  if($('openSelectedAssigned'))$('openSelectedAssigned').disabled=!selectedAssignedRows.size;\n",1)

if 'window.toggleAssignedRow=' not in s:
    old="window.toggleDraftRow=(id,checked)=>{checked?selectedDraftRows.add(String(id)):selectedDraftRows.delete(String(id));syncDraftSelection()};\n"
    if old not in s: raise SystemExit('draft toggle missing')
    s=s.replace(old,old+"window.toggleAssignedRow=(id,checked)=>{checked?selectedAssignedRows.add(String(id)):selectedAssignedRows.delete(String(id));syncDraftSelection()};\n",1)

if 'assignedSelectable=r.status' not in s:
    old1="    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';"
    new1="    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),assignedSelectable=r.status==='assigned',recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';"
    if old1 not in s: raise SystemExit('current render declaration missing')
    s=s.replace(old1,new1,1)
    old2="    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:r.status==='assigned'?`<span class=\"chip\">مهمة جاهزة للعمل</span>`:'';"
    new2="    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:assignedSelectable?`<input class=\"assigned-select\" type=\"checkbox\" aria-label=\"تحديد قيد الإدخال\" ${selectedAssignedRows.has(String(r.id))?'checked':''} onchange=\"toggleAssignedRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:'';"
    if old2 not in s: raise SystemExit('current selector expression missing')
    s=s.replace(old2,new2,1)

if "$('selectAllAssignedRows').onclick" not in s:
    marker="if($('clearDraftSelection')) $('clearDraftSelection').onclick=()=>{selectedDraftRows.clear();renderRows()};\n"
    handlers="if($('selectAllAssignedRows')) $('selectAllAssignedRows').onclick=()=>{selectedAssignedRows=new Set(rows.filter(r=>r.status==='assigned').map(r=>String(r.id)));renderRows()};\nif($('clearAssignedSelection')) $('clearAssignedSelection').onclick=()=>{selectedAssignedRows.clear();renderRows()};\nif($('openSelectedAssigned')) $('openSelectedAssigned').onclick=()=>{const id=[...selectedAssignedRows][0];if(id)editRow(id)};\n"
    if marker not in s: raise SystemExit('clear draft handler missing')
    s=s.replace(marker,marker+handlers,1)

if 'data-entry-assigned-selection-v1' not in s:
    css='''\n/* data-entry-assigned-selection-v1 */\n.assigned-toolbar{border-color:#816b33;background:#171f2a}.assigned-select{width:20px;height:20px;accent-color:#d6b15a}.row.assigned .assigned-select{flex:0 0 auto}\n'''
    s=s.replace('</style>',css+'\n</style>',1)

for required in ['id="selectAllAssignedRows"','selectedAssignedRows=new Set()','window.toggleAssignedRow=','assignedSelectable=r.status',"$('selectAllAssignedRows').onclick",'data-entry-assigned-selection-v1']:
    if required not in s: raise SystemExit('missing after patch: '+required)

p.write_text(s,encoding='utf-8')
print('patched assigned manual/select-all controls')
