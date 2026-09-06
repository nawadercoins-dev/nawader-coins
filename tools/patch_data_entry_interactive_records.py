from pathlib import Path

p=Path('public/data_entry.html')
s=p.read_text(encoding='utf-8')

# Make thumbnails/buttons unmistakably interactive and give assigned work a visible action.
s=s.replace(".row .thumbs img{cursor:zoom-in}", ".row .thumbs img{cursor:zoom-in}.row.assigned,.row.pending,.row.draft,.row.needs_changes{cursor:default}.row .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.row .actions .smallbtn{min-width:110px}.row.assigned{border-color:#b99647;box-shadow:inset 0 0 0 1px #b9964744}.row.assigned h3{color:#f0d995}")

old="""    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';
    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:'';
"""
new="""    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),recallable=r.status==='pending',store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';
    const selector=assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:recallable?`<input class=\"pending-select\" type=\"checkbox\" aria-label=\"تحديد المرسل للاعتماد\" ${selectedPendingRows.has(String(r.id))?'checked':''} onchange=\"togglePendingRow('${esc(r.id)}',this.checked)\">`:r.status==='assigned'?`<span class=\"chip\">مهمة جاهزة للعمل</span>`:'';
"""
if old not in s:
    raise SystemExit('selector block not found')
s=s.replace(old,new)

old2="""    <div class=\"actions\">${imgs.length?`<button class=\"smallbtn\" onclick=\"previewRowImages('${esc(r.id)}',0)\">معاينة الصور</button>`:''}${editable?`<button class=\"smallbtn\" onclick=\"editRow('${esc(r.id)}')\">${r.status==='assigned'?'فتح وإكمال':'تعديل'}</button>`:''}${recallable?`<button class=\"smallbtn\" onclick=\"withdrawPendingRows(['${esc(r.id)}'])\">↩ استرجاع للتعديل</button>`:''}</div></article>`
"""
new2="""    <div class=\"actions\">${imgs.length?`<button type=\"button\" class=\"smallbtn\" onclick=\"previewRowImages('${esc(r.id)}',0)\">🔎 معاينة الصور</button>`:''}${editable?`<button type=\"button\" class=\"smallbtn\" onclick=\"editRow('${esc(r.id)}')\">${r.status==='assigned'?'✎ فتح وإكمال البيانات':'✎ تعديل البيانات'}</button>`:''}${recallable?`<button type=\"button\" class=\"smallbtn\" onclick=\"withdrawPendingRows(['${esc(r.id)}'])\">↩ استرجاع للتعديل</button>`:''}${['approved','rejected'].includes(r.status)?`<span class=\"muted\">سجل نهائي للعرض فقط</span>`:''}</div></article>`
"""
if old2 not in s:
    raise SystemExit('actions block not found')
s=s.replace(old2,new2)

# Make handler installation resilient if an old cached HTML fragment misses a control.
for id_ in ['selectAllDraftRows','clearDraftSelection','selectAllPendingRows','clearPendingSelection','withdrawSelectedPending']:
    s=s.replace(f"$('%s').onclick="%id_, f"if($('%s')) $('%s').onclick="%(id_,id_))

# Add a visible instruction before assigned rows.
needle="""  rows.sort((a,b)=>(a.status==='assigned'?0:1)-(b.status==='assigned'?0:1)||String(b.updated||b.created||'').localeCompare(String(a.updated||a.created||'')));
  renderRows()
"""
repl="""  rows.sort((a,b)=>(a.status==='assigned'?0:1)-(b.status==='assigned'?0:1)||String(b.updated||b.created||'').localeCompare(String(a.updated||a.created||'')));
  renderRows();
  if(assignedCount) setNotice(`لديك ${assignedCount} مقتنى قيد الإدخال. اضغط «فتح وإكمال البيانات» داخل البطاقة للعمل عليه، ويمكنك الضغط على الصورة أو «معاينة الصور».`,'good')
"""
if needle not in s:
    raise SystemExit('loadRows tail not found')
s=s.replace(needle,repl)

p.write_text(s,encoding='utf-8')
