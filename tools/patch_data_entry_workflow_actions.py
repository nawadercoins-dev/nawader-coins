from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')

# 1) Clarify the three workflow bands and add the missing assigned -> approval action.
s=s.replace('''        <div class="assignment-toolbar">\n          <button id="selectAllDraftRows" type="button" class="smallbtn">تحديد كل المسودات</button>''','''        <div class="workflow-label">1) المسودات — إرسال لمسؤول إدخال البيانات</div>\n        <div class="assignment-toolbar">\n          <button id="selectAllDraftRows" type="button" class="smallbtn">تحديد كل المسودات</button>''',1)

s=s.replace('''        <div class="assignment-toolbar assigned-toolbar">\n          <button id="selectAllAssignedRows" type="button" class="smallbtn">تحديد كل قيد الإدخال</button>\n          <button id="clearAssignedSelection" type="button" class="smallbtn">إلغاء التحديد</button>\n          <button id="openSelectedAssigned" type="button" class="btn ghost">✎ فتح أول المحدد</button>\n          <span id="assignedSelectionCount" class="muted">0 محدد</span>\n        </div>''','''        <div class="workflow-label">2) قيد الإدخال — تعديل ثم إرسال للاعتماد</div>\n        <div class="assignment-toolbar assigned-toolbar">\n          <button id="selectAllAssignedRows" type="button" class="smallbtn">تحديد كل قيد الإدخال</button>\n          <button id="clearAssignedSelection" type="button" class="smallbtn">إلغاء التحديد</button>\n          <button id="openSelectedAssigned" type="button" class="btn ghost">✎ فتح وتعديل المحدد</button>\n          <button id="submitSelectedAssigned" type="button" class="btn">✓ إرسال المحدد للاعتماد</button>\n          <span id="assignedSelectionCount" class="muted">0 محدد</span>\n        </div>''',1)

s=s.replace('''        <div class="assignment-toolbar pending-toolbar">\n          <button id="selectAllPendingRows" type="button" class="smallbtn">تحديد كل المرسلة للاعتماد</button>''','''        <div class="workflow-label">3) بانتظار الاعتماد — يمكن استرجاعه قبل قرار الإدارة</div>\n        <div class="assignment-toolbar pending-toolbar">\n          <button id="selectAllPendingRows" type="button" class="smallbtn">تحديد كل المرسلة للاعتماد</button>''',1)

# 2) Enable/disable the new action with selection state.
needle="  if($('openSelectedAssigned'))$('openSelectedAssigned').disabled=!selectedAssignedRows.size;\n"
if needle in s and "submitSelectedAssigned" not in s[s.find(needle):s.find(needle)+220]:
    s=s.replace(needle,needle+"  if($('submitSelectedAssigned'))$('submitSelectedAssigned').disabled=!selectedAssignedRows.size;\n",1)

# 3) Convert an existing server row to the same data shape used by bulk submit.
marker="window.togglePendingRow=(id,checked)=>{checked?selectedPendingRows.add(String(id)):selectedPendingRows.delete(String(id));syncDraftSelection()};\n"
helper='''\nfunction rowAsData(r){\n  const urls=[r.frontImage,r.backImage,...(Array.isArray(r.additionalImages)?r.additionalImages:[])].filter(Boolean).slice(0,8);\n  const ids=Array.isArray(r.vaultImageIds)?r.vaultImageIds:[];\n  return {\n    id:r.id||'',storeType:r.storeType||'coins',collectibleCategory:r.collectibleCategory||'other',country:r.country||'',denomination:r.denomination||'',\n    year:r.year||'',issueEdition:r.issueEdition||'',type:r.type||'',condition:r.condition||'',serial:r.serial||'',collectionClass:r.collectionClass||'single',\n    inventoryUnitType:r.inventoryUnitType||'piece',inventoryUnitCount:Number(r.inventoryUnitCount||r.quantity||1),piecesPerUnit:Number(r.piecesPerUnit||1),\n    images:urls.map((url,i)=>({id:ids[i]||'',url})),purchase:Number(r.purchase||0),salePrice:Number(r.salePrice||r.expectedPrice||0),\n    shipping:Number(r.shipping||0),other:Number(r.other||0),warehouse:r.warehouse||'المستودع الرئيسي',cabinet:r.cabinet||'',shelf:r.shelf||'',\n    box:r.box||'',album:r.album||'',pocket:r.pocket||'',notes:r.notes||''\n  };\n}\n\nasync function submitAssignedSelection(){\n  const ids=[...selectedAssignedRows];\n  if(!ids.length){setNotice('حدد مقتنى واحدًا أو أكثر من «قيد الإدخال» أولًا.','error');return}\n  const selected=ids.map(id=>rows.find(r=>String(r.id)===String(id))).filter(Boolean);\n  const incomplete=selected.map(r=>({r,missing:missingFor(rowAsData(r))})).filter(x=>x.missing.length);\n  if(incomplete.length){\n    setNotice(`يوجد ${incomplete.length} مقتنى ناقص. افتح «تعديل المحدد» وأكمل: ${[...new Set(incomplete.flatMap(x=>x.missing))].join('، ')}.`,'error');\n    return;\n  }\n  if(!confirm(`إرسال ${selected.length} مقتنى محدد للإدارة للاعتماد؟`))return;\n  const btn=$('submitSelectedAssigned'); if(btn)btn.disabled=true;\n  let ok=0,failed=0,firstError='';\n  for(const r of selected){\n    try{await api('/api/data-entry/submissions',{method:'POST',body:JSON.stringify(dataToPayload(rowAsData(r),'submit'))});ok++}\n    catch(e){failed++;if(!firstError)firstError=e.message||'تعذر الإرسال'}\n  }\n  selectedAssignedRows.clear();\n  await loadRows();\n  if(btn)btn.disabled=false;\n  setNotice(failed?`تم إرسال ${ok} للاعتماد وتعذر ${failed}${firstError?' — '+firstError:''}.`:`✓ تم إرسال ${ok} مقتنى محدد للاعتماد بنجاح.`,failed?'warn':'good');\n}\n'''
if 'function rowAsData(r)' not in s:
    if marker not in s: raise SystemExit('togglePendingRow marker missing')
    s=s.replace(marker,marker+helper,1)

# 4) Hook toolbar controls defensively.
marker="if($('clearPendingSelection')) $('clearPendingSelection').onclick=()=>{selectedPendingRows.clear();renderRows()};\n"
handlers="""if($('openSelectedAssigned')) $('openSelectedAssigned').onclick=()=>{\n  const id=[...selectedAssignedRows][0];\n  if(!id){setNotice('حدد مقتنى من «قيد الإدخال» أولًا.','error');return}\n  editRow(id);\n};\nif($('submitSelectedAssigned')) $('submitSelectedAssigned').onclick=submitAssignedSelection;\n"""
if "$('submitSelectedAssigned').onclick=submitAssignedSelection" not in s:
    if marker not in s: raise SystemExit('pending clear handler missing')
    s=s.replace(marker,marker+handlers,1)

# 5) Make edit permission explicit per assigned card, and send one directly if desired.
old="${editable?`<button type=\"button\" class=\"smallbtn\" onclick=\"editRow('${esc(r.id)}')\">${r.status==='assigned'?'✎ فتح وإكمال البيانات':'✎ تعديل البيانات'}</button>`:''}${recallable?"
new="${editable?`<button type=\"button\" class=\"smallbtn\" onclick=\"editRow('${esc(r.id)}')\">${r.status==='assigned'?'✎ فتح وتعديل البيانات':'✎ تعديل البيانات'}</button>`:''}${r.status==='assigned'?`<button type=\"button\" class=\"smallbtn\" onclick=\"selectedAssignedRows=new Set(['${esc(r.id)}']);syncDraftSelection();submitAssignedSelection()\">✓ إرسال للاعتماد</button>`:''}${recallable?"
if old in s:
    s=s.replace(old,new,1)
elif "✓ إرسال للاعتماد</button>" not in s:
    raise SystemExit('row action marker missing')

# 6) UX: labels and prominent workflow buttons.
if 'data-entry-workflow-actions-v1' not in s:
    css='''\n/* data-entry-workflow-actions-v1 */\n.workflow-label{margin:10px 2px 5px;color:#f0d995;font-weight:900;font-size:.9rem}.assigned-toolbar{box-shadow:inset 0 0 0 1px #d6b15a33}.assigned-toolbar .btn{min-width:170px}.row.assigned .actions{display:flex!important;gap:8px;flex-wrap:wrap}.row.assigned .actions .smallbtn{font-weight:800}\n@media(max-width:560px){.assigned-toolbar .btn,.assigned-toolbar .smallbtn{flex:1 1 46%}.workflow-label{text-align:center}}\n'''
    s=s.replace('</style>',css+'\n</style>',1)

for required in ['id="submitSelectedAssigned"','function rowAsData(r)','function submitAssignedSelection()','data-entry-workflow-actions-v1','✓ إرسال المحدد للاعتماد']:
    if required not in s: raise SystemExit('missing after patch: '+required)

p.write_text(s,encoding='utf-8')
print('patched data-entry workflow actions')
