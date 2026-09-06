from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'server.py'
PAGE=ROOT/'public'/'data_entry.html'

# ---------- server ----------
s=SERVER.read_text(encoding='utf-8')

old="""            rows=[x for x in load_collectible_submissions() if x.get('submissionSource')=='data_entry' and str(x.get('dataEntryParticipantId') or '')==pid]
"""
new="""            rows=[x for x in load_collectible_submissions() if x.get('submissionSource')=='data_entry' and (str(x.get('dataEntryParticipantId') or '')==pid or str(x.get('status') or '')=='assigned')]
"""
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise RuntimeError('GET data-entry row filter not found')

old="""                mode=str(d.get('mode') or 'draft').strip().lower()
                if mode not in ('draft','submit'): mode='draft'
"""
new="""                mode=str(d.get('mode') or 'draft').strip().lower()
                if mode not in ('draft','submit','assign'): mode='draft'
"""
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise RuntimeError('data-entry mode block not found')

old="""                    row=next((x for x in rows if str(x.get('id'))==sid and x.get('submissionSource')=='data_entry' and str(x.get('dataEntryParticipantId') or '')==pid),None)
                    if not row:
                        self.sendj({'error':'سجل الإدخال غير موجود'},404); return
                    if row.get('status') not in ('draft','needs_changes'):
                        self.sendj({'error':'هذا السجل أُرسل بالفعل ولا يمكن تعديله قبل قرار الإدارة'},409); return
"""
new="""                    row=next((x for x in rows if str(x.get('id'))==sid and x.get('submissionSource')=='data_entry' and (str(x.get('dataEntryParticipantId') or '')==pid or str(x.get('status') or '')=='assigned')),None)
                    if not row:
                        self.sendj({'error':'سجل الإدخال غير موجود'},404); return
                    if mode=='assign':
                        if row.get('status') not in ('draft','needs_changes'):
                            self.sendj({'error':'يمكن إرسال المسودات أو المعاد للتعديل فقط لمسؤول إدخال البيانات'},409); return
                        now=datetime.datetime.now().isoformat()
                        row['status']='assigned'; row['assignedAt']=now; row['assignedByParticipantId']=pid; row['updated']=now
                        save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                        append_operation('إرسال مسودة لمسؤول إدخال البيانات',{'submissionId':sid,'senderId':pid},actor='مالك/مسؤول الإدخال')
                        self.sendj({'ok':True,'submission':row}); return
                    if row.get('status') not in ('draft','needs_changes','assigned'):
                        self.sendj({'error':'هذا السجل أُرسل بالفعل ولا يمكن تعديله قبل قرار الإدارة'},409); return
                    if row.get('status')=='assigned' and str(row.get('dataEntryParticipantId') or '')!=pid:
                        row['dataEntryParticipantId']=pid
                        row['dataEntryName']=person.get('alias') or person.get('name') or 'مسؤول إدخال البيانات'
                        row['pickedUpAt']=datetime.datetime.now().isoformat()
"""
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise RuntimeError('data-entry ownership/status block not found')

SERVER.write_text(s,encoding='utf-8')

# ---------- page ----------
p=PAGE.read_text(encoding='utf-8')

old="""function statusLabel(s){return({draft:'مسودة',pending:'بانتظار الاعتماد',needs_changes:'معاد للتعديل',approved:'معتمد للمستودع',rejected:'مرفوض'})[s]||s||'—'}
"""
new="""function statusLabel(s){return({draft:'مسودة',assigned:'قيد الإدخال',pending:'بانتظار الاعتماد',needs_changes:'معاد للتعديل',approved:'معتمد للمستودع',rejected:'مرفوض'})[s]||s||'—'}
"""
if old in p:
    p=p.replace(old,new,1)
elif new not in p:
    raise RuntimeError('statusLabel not found')

css_marker='/* assignment-queue-v1 */'
if css_marker not in p:
    css="""
/* assignment-queue-v1 */
.assignment-toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px;margin:8px 0 12px;border:1px solid #3b5067;border-radius:12px;background:#0d2034}
.assignment-toolbar .muted{margin-inline-start:auto}.row-select{width:20px;height:20px;accent-color:#d6b15a}.row.assigned{border-color:#846f37;box-shadow:inset 0 0 0 1px #846f3733}
@media(max-width:560px){.assignment-toolbar .btn{flex:1}.assignment-toolbar .muted{width:100%;margin:0;text-align:center}}
"""
    p=p.replace('</style>',css+'\n</style>',1)

old="""      <aside class=\"panel\">\n        <h2>سجلاتي</h2>\n        <p class=\"muted\">السجلات المحفوظة من المتجرين تظهر هنا. في الإدخال الجماعي تظهر القائمة المؤقتة أعلى الصفحة حتى تحفظها أو ترسلها.</p>\n        <div id=\"rows\" class=\"rows\"></div>\n      </aside>
"""
new="""      <aside class=\"panel\">\n        <h2>سجلاتي</h2>\n        <p class=\"muted\">حدد مسودة واحدة أو عدة مسودات ثم أرسلها دفعة واحدة لمسؤول إدخال البيانات. تتحول حالتها إلى «قيد الإدخال» حتى يكمل البيانات ويرسلها للاعتماد.</p>\n        <div class=\"assignment-toolbar\">\n          <button id=\"selectAllDraftRows\" type=\"button\" class=\"smallbtn\">تحديد كل المسودات</button>\n          <button id=\"clearDraftSelection\" type=\"button\" class=\"smallbtn\">إلغاء التحديد</button>\n          <button id=\"assignSelectedDrafts\" type=\"button\" class=\"btn\">إرسال المحدد لمسؤول إدخال البيانات</button>\n          <span id=\"draftSelectionCount\" class=\"muted\">0 محدد</span>\n        </div>\n        <div id=\"rows\" class=\"rows\"></div>\n      </aside>
"""
if old in p:
    p=p.replace(old,new,1)
elif 'id="assignSelectedDrafts"' not in p:
    raise RuntimeError('records aside block not found')

old="""function renderRows(){
  $('rows').innerHTML=rows.map(r=>{
    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes'].includes(r.status),store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';
    return`<article class=\"row ${esc(r.status||'')}\"><div style=\"display:flex;justify-content:space-between;gap:8px;align-items:center\"><h3>${esc(r.country||'—')} — ${esc(r.denomination||'—')}</h3><span class=\"chip\">${esc(statusLabel(r.status))}</span></div>
"""
new="""let selectedDraftRows=new Set();
function syncDraftSelection(){
  const drafts=rows.filter(r=>['draft','needs_changes'].includes(r.status));
  selectedDraftRows=new Set([...selectedDraftRows].filter(id=>drafts.some(r=>String(r.id)===String(id))));
  if($('draftSelectionCount'))$('draftSelectionCount').textContent=`${selectedDraftRows.size} محدد`;
  if($('assignSelectedDrafts'))$('assignSelectedDrafts').disabled=!selectedDraftRows.size
}
window.toggleDraftRow=(id,checked)=>{checked?selectedDraftRows.add(String(id)):selectedDraftRows.delete(String(id));syncDraftSelection()};
function renderRows(){
  $('rows').innerHTML=rows.map(r=>{
    const imgs=[r.frontImage,r.backImage,...(r.additionalImages||[])].filter(Boolean),editable=['draft','needs_changes','assigned'].includes(r.status),assignable=['draft','needs_changes'].includes(r.status),store=r.storeType==='collectibles'?'collectibles':'coins',category=store==='collectibles'?(CATEGORY_LABELS[r.collectibleCategory]||'أخرى'):'';
    return`<article class=\"row ${esc(r.status||'')}\"><div style=\"display:flex;justify-content:space-between;gap:8px;align-items:center\"><div style=\"display:flex;gap:8px;align-items:center\">${assignable?`<input class=\"row-select\" type=\"checkbox\" aria-label=\"تحديد المسودة\" ${selectedDraftRows.has(String(r.id))?'checked':''} onchange=\"toggleDraftRow('${esc(r.id)}',this.checked)\">`:''}<h3>${esc(r.country||'—')} — ${esc(r.denomination||'—')}</h3></div><span class=\"chip\">${esc(statusLabel(r.status))}</span></div>
"""
if old in p:
    p=p.replace(old,new,1)
elif 'let selectedDraftRows=new Set();' not in p:
    raise RuntimeError('renderRows header not found')

old="""  }).join('')||'<p class=\"muted\">لا توجد سجلات بعد. ابدأ بإضافة أول مقتنى.</p>'
}
async function loadRows(){
"""
new="""  }).join('')||'<p class=\"muted\">لا توجد سجلات بعد. ابدأ بإضافة أول مقتنى.</p>';
  syncDraftSelection()
}
$('selectAllDraftRows').onclick=()=>{selectedDraftRows=new Set(rows.filter(r=>['draft','needs_changes'].includes(r.status)).map(r=>String(r.id)));renderRows()};
$('clearDraftSelection').onclick=()=>{selectedDraftRows.clear();renderRows()};
$('assignSelectedDrafts').onclick=async()=>{
  const ids=[...selectedDraftRows];if(!ids.length)return;
  if(!confirm(`إرسال ${ids.length} مسودة لمسؤول إدخال البيانات؟`))return;
  $('assignSelectedDrafts').disabled=true;let ok=0,failed=0;
  for(const id of ids){try{await api('/api/data-entry/submissions',{method:'POST',body:JSON.stringify({id,mode:'assign'})});ok++}catch(e){failed++}}
  selectedDraftRows.clear();await loadRows();setNotice(failed?`تم إرسال ${ok} وتعذر ${failed}.`:`تم إرسال ${ok} مسودة لمسؤول إدخال البيانات وأصبحت «قيد الإدخال».`,failed?'warn':'good')
};
async function loadRows(){
"""
if old in p:
    p=p.replace(old,new,1)
elif "$('assignSelectedDrafts').onclick" not in p:
    raise RuntimeError('renderRows footer not found')

# Assigned records can be opened by the operator.
old="""  const r=rows.find(x=>x.id===id);if(!r||!['draft','needs_changes'].includes(r.status))return;
"""
new="""  const r=rows.find(x=>x.id===id);if(!r||!['draft','needs_changes','assigned'].includes(r.status))return;
"""
if old in p:
    p=p.replace(old,new,1)
elif new not in p:
    raise RuntimeError('editRow status check not found')

PAGE.write_text(p,encoding='utf-8')
print('Data-entry assignment queue patch applied.')
