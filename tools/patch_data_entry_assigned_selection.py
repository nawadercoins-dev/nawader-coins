from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')

# 1) Add toolbar for records currently assigned / in data entry.
if 'id="selectAllAssignedRows"' not in s:
    marker='        <div class="assignment-toolbar pending-toolbar">\n'
    insert='''        <div class="assignment-toolbar assigned-toolbar">\n          <button id="selectAllAssignedRows" type="button" class="smallbtn">تحديد كل قيد الإدخال</button>\n          <button id="clearAssignedSelection" type="button" class="smallbtn">إلغاء التحديد</button>\n          <button id="openSelectedAssigned" type="button" class="btn ghost">✎ فتح أول المحدد</button>\n          <span id="assignedSelectionCount" class="muted">0 محدد</span>\n        </div>\n'''
    if marker not in s:
        raise SystemExit('pending toolbar marker missing')
    s=s.replace(marker,insert+marker,1)

# 2) Add assigned selection set.
if 'selectedAssignedRows=new Set()' not in s:
    s=s.replace('let selectedDraftRows=new Set(),selectedPendingRows=new Set();',
                'let selectedDraftRows=new Set(),selectedAssignedRows=new Set(),selectedPendingRows=new Set();',1)

# 3) Sync selected assigned ids and toolbar state.
if "const assigned=rows.filter(r=>r.status==='assigned');" not in s:
    s=s.replace("  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));\n  const pending=rows.filter(r=>r.status==='pending');",
                "  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));\n  const assigned=rows.filter(r=>r.status==='assigned');\n  const pending=rows.filter(r=>r.status==='pending');",1)
if 'selectedAssignedRows=new Set([...selectedAssignedRows]' not in s:
    s=s.replace('  selectedDraftRows=new Set([...selectedDraftRows].filter(id=>drafts.some(r=>String(r.id)===String(id))));\n',
                '  selectedDraftRows=new Set([...selectedDraftRows].filter(id=>drafts.some(r=>String(r.id)===String(id))));\n  selectedAssignedRows=new Set([...selectedAssignedRows].filter(id=>assigned.some(r=>String(r.id)===String(id))));\n',1)
if "$('assignedSelectionCount')" not in s:
    s=s.replace("  if($('draftSelectionCount'))$('draftSelectionCount').textContent=`${selectedDraftRows.size} محدد`;\n",
                "  if($('draftSelectionCount'))$('draftSelectionCount').textContent=`${selectedDraftRows.size} محدد`;\n  if($('assignedSelectionCount'))$('assignedSelectionCount').textContent=`${selectedAssignedRows.size} محدد`;\n",1)
if "$('openSelectedAssigned')" not in s:
    s=s.replace("  if($('assignSelectedDrafts'))$('assignSelectedDrafts').disabled=!selectedDraftRows.size;\n",
                "  if($('assignSelectedDrafts'))$('assignSelectedDrafts').disabled=!selectedDraftRows.size;\n  if($('openSelectedAssigned'))$('openSelectedAssigned').disabled=!selectedAssignedRows.size;\n",1)

# 4) Manual checkbox handler.
if 'window.toggleAssignedRow=' not in s:
    s=s.replace("window.toggleDraftRow=(id,checked)=>{checked?selectedDraftRows.add(String(id)):selectedDraftRows.delete(String(id));syncDraftSelection()};\n",
                "window.toggleDraftRow=(id,checked)=>{checked?selectedDraftRows.add(String(id)):selectedDraftRows.delete(String(id));syncDraftSelection()};\nwindow.toggleAssignedRow=(id,checked)=>{checked?selectedAssignedRows.add(String(id)):selectedAssignedRows.delete(String(id));syncDraftSelection()};\n",1)

# 5) Add manual checkbox to assigned rows. Use exact current single-line selector construction.
needle="""    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';\n    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:'';"""
replacement="""    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),assignedSelectable=r.status==='assigned',recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';\n    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:assignedSelectable?`<input class=\"assigned-select\" type=\"checkbox\" aria-label=\"تحديد قيد الإدخال\" ${selectedAssignedRows.has(String(r.id))?'checked':''} onchange=\"toggleAssignedRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:'';"""
if 'assignedSelectable=r.status' not in s:
    if needle not in s:
        raise SystemExit('current render selector block missing')
    s=s.replace(needle,replacement,1)

# 6) Toolbar handlers: select all, clear, open first selected.
if "$('selectAllAssignedRows').onclick" not in s:
    marker="$('clearDraftSelection').onclick=()=>{selectedDraftRows.clear();renderRows()};\n"
    handlers="""$('clearDraftSelection').onclick=()=>{selectedDraftRows.clear();renderRows()};\n$('selectAllAssignedRows').onclick=()=>{selectedAssignedRows=new Set(rows.filter(r=>r.status==='assigned').map(r=>String(r.id)));renderRows()};\n$('clearAssignedSelection').onclick=()=>{selectedAssignedRows.clear();renderRows()};\n$('openSelectedAssigned').onclick=()=>{const id=[...selectedAssignedRows][0];if(id)editRow(id)};\n"""
    if marker not in s:
        raise SystemExit('clear draft handler missing')
    s=s.replace(marker,handlers,1)

# 7) Visual style.
if 'data-entry-assigned-selection-v1' not in s:
    css='''\n/* data-entry-assigned-selection-v1 */\n.assigned-toolbar{border-color:#816b33;background:#171f2a}.assigned-select{width:20px;height:20px;accent-color:#d6b15a}.row.assigned .assigned-select{flex:0 0 auto}\n'''
    s=s.replace('</style>',css+'\n</style>',1)

# Sanity checks.
for required in ['id="selectAllAssignedRows"','selectedAssignedRows=new Set()','window.toggleAssignedRow=','assignedSelectable=r.status',"$('selectAllAssignedRows').onclick",'data-entry-assigned-selection-v1']:
    if required not in s:
        raise SystemExit('missing after patch: '+required)

p.write_text(s,encoding='utf-8')
print('patched assigned manual/select-all controls')
