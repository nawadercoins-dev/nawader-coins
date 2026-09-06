from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')

marker='''        <div class="assignment-toolbar pending-toolbar">\n'''
insert='''        <div class="assignment-toolbar assigned-toolbar">\n          <button id="selectAllAssignedRows" type="button" class="smallbtn">تحديد كل قيد الإدخال</button>\n          <button id="clearAssignedSelection" type="button" class="smallbtn">إلغاء التحديد</button>\n          <button id="openSelectedAssigned" type="button" class="btn ghost">✎ فتح أول المحدد</button>\n          <span id="assignedSelectionCount" class="muted">0 محدد</span>\n        </div>\n'''
if 'id="selectAllAssignedRows"' not in s:
    if marker not in s: raise SystemExit('pending toolbar marker missing')
    s=s.replace(marker,insert+marker,1)

old="let selectedDraftRows=new Set(),selectedPendingRows=new Set();"
new="let selectedDraftRows=new Set(),selectedAssignedRows=new Set(),selectedPendingRows=new Set();"
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('selection declaration missing')

old='''  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));\n  const pending=rows.filter(r=>r.status==='pending');\n  selectedDraftRows=new Set([...selectedDraftRows].filter(id=>drafts.some(r=>String(r.id)===String(id))));\n  selectedPendingRows=new Set([...selectedPendingRows].filter(id=>pending.some(r=>String(r.id)===String(id))));\n  if($('draftSelectionCount'))$('draftSelectionCount').textContent=`${selectedDraftRows.size} محدد`;\n  if($('pendingSelectionCount'))$('pendingSelectionCount').textContent=`${selectedPendingRows.size} محدد`;\n  if($('assignSelectedDrafts'))$('assignSelectedDrafts').disabled=!selectedDraftRows.size;\n  if($('withdrawSelectedPending'))$('withdrawSelectedPending').disabled=!selectedPendingRows.size\n'''
new='''  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));\n  const assigned=rows.filter(r=>r.status==='assigned');\n  const pending=rows.filter(r=>r.status==='pending');\n  selectedDraftRows=new Set([...selectedDraftRows].filter(id=>drafts.some(r=>String(r.id)===String(id))));\n  selectedAssignedRows=new Set([...selectedAssignedRows].filter(id=>assigned.some(r=>String(r.id)===String(id))));\n  selectedPendingRows=new Set([...selectedPendingRows].filter(id=>pending.some(r=>String(r.id)===String(id))));\n  if($('draftSelectionCount'))$('draftSelectionCount').textContent=`${selectedDraftRows.size} محدد`;\n  if($('assignedSelectionCount'))$('assignedSelectionCount').textContent=`${selectedAssignedRows.size} محدد`;\n  if($('pendingSelectionCount'))$('pendingSelectionCount').textContent=`${selectedPendingRows.size} محدد`;\n  if($('assignSelectedDrafts'))$('assignSelectedDrafts').disabled=!selectedDraftRows.size;\n  if($('openSelectedAssigned'))$('openSelectedAssigned').disabled=!selectedAssignedRows.size;\n  if($('withdrawSelectedPending'))$('withdrawSelectedPending').disabled=!selectedPendingRows.size\n'''
if old in s:
    s=s.replace(old,new,1)
elif "const assigned=rows.filter(r=>r.status==='assigned');" not in s:
    raise SystemExit('sync selection block missing')

old="window.toggleDraftRow=(id,checked)=>{checked?selectedDraftRows.add(String(id)):selectedDraftRows.delete(String(id));syncDraftSelection()};\nwindow.togglePendingRow=(id,checked)=>{checked?selectedPendingRows.add(String(id)):selectedPendingRows.delete(String(id));syncDraftSelection()};"
new="window.toggleDraftRow=(id,checked)=>{checked?selectedDraftRows.add(String(id)):selectedDraftRows.delete(String(id));syncDraftSelection()};\nwindow.toggleAssignedRow=(id,checked)=>{checked?selectedAssignedRows.add(String(id)):selectedAssignedRows.delete(String(id));syncDraftSelection()};\nwindow.togglePendingRow=(id,checked)=>{checked?selectedPendingRows.add(String(id)):selectedPendingRows.delete(String(id));syncDraftSelection()};"
if old in s:
    s=s.replace(old,new,1)
elif 'window.toggleAssignedRow=' not in s:
    raise SystemExit('toggle selection block missing')

old="const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';\n    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:'';"
new="const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),assignedSelectable=r.status==='assigned',recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';\n    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:assignedSelectable?`<input class=\"assigned-select\" type=\"checkbox\" aria-label=\"تحديد قيد الإدخال\" ${selectedAssignedRows.has(String(r.id))?'checked':''} onchange=\"toggleAssignedRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:'';"
if old in s:
    s=s.replace(old,new,1)
elif 'assignedSelectable=r.status' not in s:
    raise SystemExit('render selector block missing')

old="$('selectAllDraftRows').onclick=()=>{selectedDraftRows=new Set(rows.filter(r=>['draft','needs_changes'].includes(r.status)).map(r=>String(r.id)));renderRows()};\n$('clearDraftSelection').onclick=()=>{selectedDraftRows.clear();renderRows()};\n$('selectAllPendingRows').onclick=()=>{selectedPendingRows=new Set(rows.filter(r=>r.status==='pending').map(r=>String(r.id)));renderRows()};"
new="$('selectAllDraftRows').onclick=()=>{selectedDraftRows=new Set(rows.filter(r=>['draft','needs_changes'].includes(r.status)).map(r=>String(r.id)));renderRows()};\n$('clearDraftSelection').onclick=()=>{selectedDraftRows.clear();renderRows()};\n$('selectAllAssignedRows').onclick=()=>{selectedAssignedRows=new Set(rows.filter(r=>r.status==='assigned').map(r=>String(r.id)));renderRows()};\n$('clearAssignedSelection').onclick=()=>{selectedAssignedRows.clear();renderRows()};\n$('openSelectedAssigned').onclick=()=>{const id=[...selectedAssignedRows][0];if(id)editRow(id)};\n$('selectAllPendingRows').onclick=()=>{selectedPendingRows=new Set(rows.filter(r=>r.status==='pending').map(r=>String(r.id)));renderRows()};"
if old in s:
    s=s.replace(old,new,1)
elif "$('selectAllAssignedRows').onclick" not in s:
    raise SystemExit('toolbar handlers block missing')

css='''\n/* data-entry-assigned-selection-v1 */\n.assigned-toolbar{border-color:#816b33;background:#171f2a}.assigned-select{width:20px;height:20px;accent-color:#d6b15a}.row.assigned .assigned-select{flex:0 0 auto}\n'''
if 'data-entry-assigned-selection-v1' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

p.write_text(s,encoding='utf-8')
print('patched assigned manual/select-all controls')
