from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'server.py'
PAGE=ROOT/'public'/'data_entry.html'
ADMIN=ROOT/'admin'/'app.js'

# ---------------- server ----------------
s=SERVER.read_text(encoding='utf-8')

old="""                if mode=='assign':
                        if row.get('status') not in ('draft','needs_changes'):
                            self.sendj({'error':'يمكن إرسال المسودات أو المعاد للتعديل فقط لمسؤول إدخال البيانات'},409); return
                        now=datetime.datetime.now().isoformat()
                        row['status']='assigned'; row['assignedAt']=now; row['assignedByParticipantId']=pid; row['updated']=now
                        save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                        append_operation('إرسال مسودة لمسؤول إدخال البيانات',{'submissionId':sid,'senderId':pid},actor='مالك/مسؤول الإدخال')
                        self.sendj({'ok':True,'submission':row}); return
"""
new="""                if mode=='assign':
                        if row.get('status') not in ('draft','needs_changes'):
                            self.sendj({'error':'يمكن إرسال المسودات أو المعاد للتعديل فقط لمسؤول إدخال البيانات'},409); return
                        now=datetime.datetime.now().isoformat()
                        row['status']='assigned'; row['assignedAt']=now; row['assignedByParticipantId']=pid; row['updated']=now
                        save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                        # إشعار كل حساب مفعّل له دور مسؤول إدخال البيانات بوجود مهمة جديدة.
                        try:
                            for target_id,perms in load_user_permissions().items():
                                if isinstance(perms,dict) and perms.get('dataEntry'):
                                    add_notification('participant',str(target_id),'data-entry','📥 مهمة إدخال بيانات جديدة','تم إرسال مقتنى إلى قائمة قيد الإدخال. افتح صفحة مسؤول إدخال البيانات لإكماله.',sid,'/data-entry')
                        except Exception:
                            pass
                        append_operation('إرسال مسودة لمسؤول إدخال البيانات',{'submissionId':sid,'senderId':pid},actor='مالك/مسؤول الإدخال')
                        self.sendj({'ok':True,'submission':row}); return
"""
if old in s:
    s=s.replace(old,new,1)
elif "📥 مهمة إدخال بيانات جديدة" not in s:
    raise RuntimeError('assign notification block not found')

old="""                row.update(payload); row['updated']=now; row['status']='pending' if mode=='submit' else 'draft'
"""
new="""                was_assigned=bool(row and str(row.get('status') or '')=='assigned')
                row.update(payload); row['updated']=now; row['status']='pending' if mode=='submit' else ('assigned' if was_assigned else 'draft')
"""
if old in s:
    s=s.replace(old,new,1)
elif "('assigned' if was_assigned else 'draft')" not in s:
    raise RuntimeError('assigned status preservation block not found')

SERVER.write_text(s,encoding='utf-8')

# ---------------- data-entry page ----------------
p=PAGE.read_text(encoding='utf-8')

marker='<div id="assignmentInboxNotice" class="notice hidden"></div>'
if marker not in p:
    anchor='<div id="notice" class="notice">هذا الدور لا ينشر ولا يحذف نهائيًا. كل مقتنى ترسله ينتقل إلى «بانتظار الاعتماد» لدى الإدارة.</div>'
    if anchor not in p: raise RuntimeError('main notice anchor not found')
    p=p.replace(anchor,anchor+'\n    '+marker,1)

old="""    <div class=\"actions\">${editable?`<button class=\"smallbtn\" onclick=\"editRow('${esc(r.id)}')\">تعديل</button>`:''}</div></article>`
"""
new="""    <div class=\"actions\">${editable?`<button class=\"smallbtn\" onclick=\"editRow('${esc(r.id)}')\">${r.status==='assigned'?'فتح وإكمال':'تعديل'}</button>`:''}</div></article>`
"""
if old in p:
    p=p.replace(old,new,1)
elif "r.status==='assigned'?'فتح وإكمال':'تعديل'" not in p:
    raise RuntimeError('row action label not found')

old="""async function loadRows(){
  const r=await api('/api/data-entry/submissions');operator=r.operator;rows=r.submissions||[];const c=r.counts||{};
  $('cDraft').textContent=c.draft||0;$('cPending').textContent=c.pending||0;$('cNeeds').textContent=c.needsChanges||0;$('cApproved').textContent=c.approved||0;$('cRejected').textContent=c.rejected||0;renderRows()
}
"""
new="""async function loadRows(){
  const r=await api('/api/data-entry/submissions');operator=r.operator;rows=r.submissions||[];const c=r.counts||{};
  $('cDraft').textContent=c.draft||0;$('cPending').textContent=c.pending||0;$('cNeeds').textContent=c.needsChanges||0;$('cApproved').textContent=c.approved||0;$('cRejected').textContent=c.rejected||0;
  const assignedCount=rows.filter(x=>x.status==='assigned').length, inbox=$('assignmentInboxNotice');
  if(inbox){inbox.classList.toggle('hidden',!assignedCount);inbox.className='notice'+(assignedCount?' warn':' hidden');inbox.innerHTML=assignedCount?`📥 لديك <b>${assignedCount}</b> ${assignedCount===1?'مقتنى':'مقتنيات'} قيد الإدخال. افتحها من «سجلاتي» واضغط «فتح وإكمال»، ثم أرسلها للاعتماد.`:''}
  rows.sort((a,b)=>(a.status==='assigned'?0:1)-(b.status==='assigned'?0:1)||String(b.updated||b.created||'').localeCompare(String(a.updated||a.created||'')));
  renderRows()
}
"""
if old in p:
    p=p.replace(old,new,1)
elif 'assignedCount=rows.filter' not in p:
    raise RuntimeError('loadRows block not found')

PAGE.write_text(p,encoding='utf-8')

# ---------------- admin approval page ----------------
a=ADMIN.read_text(encoding='utf-8')
old="""    const submissions=(subRes.submissions||[]).filter(x=>x.submissionSource==='data_entry');
    const pending=submissions.filter(x=>x.status==='pending');
    const needs=submissions.filter(x=>x.status==='needs_changes');
    const total=submissions.length;
"""
new="""    const submissions=(subRes.submissions||[]).filter(x=>x.submissionSource==='data_entry');
    const assigned=submissions.filter(x=>x.status==='assigned');
    const pending=submissions.filter(x=>x.status==='pending');
    const needs=submissions.filter(x=>x.status==='needs_changes');
    const total=submissions.length;
"""
if old in a:
    a=a.replace(old,new,1)
elif 'const assigned=submissions.filter' not in a:
    raise RuntimeError('admin submission counters block not found')

old="""    const list=$('dataEntryApprovalsList');
    if(list){
      const ordered=submissions.slice().sort((a,b)=>String(b.updated||b.created||'').localeCompare(String(a.updated||a.created||'')));
"""
new="""    const list=$('dataEntryApprovalsList');
    if(list){
      let queueNotice=$('dataEntryQueueNotice');
      if(!queueNotice){queueNotice=document.createElement('div');queueNotice.id='dataEntryQueueNotice';queueNotice.className='admin-info-box';list.parentNode.insertBefore(queueNotice,list)}
      queueNotice.innerHTML=assigned.length?`📥 <b>${assigned.length}</b> ${assigned.length===1?'مقتنى قيد الإدخال لدى مسؤول البيانات':'مقتنيات قيد الإدخال لدى مسؤول البيانات'} — هذه العناصر ليست جاهزة للاعتماد بعد. <a href=\"/data-entry\" target=\"_blank\">فتح صفحة مسؤول إدخال البيانات</a>`:'لا توجد مقتنيات قيد الإدخال حاليًا.';
      const ordered=submissions.filter(x=>x.status!=='assigned'&&x.status!=='draft').slice().sort((a,b)=>String(b.updated||b.created||'').localeCompare(String(a.updated||a.created||'')));
"""
if old in a:
    a=a.replace(old,new,1)
elif "x.status!=='assigned'&&x.status!=='draft'" not in a:
    raise RuntimeError('admin approval list filter block not found')

ADMIN.write_text(a,encoding='utf-8')
print('Data-entry flow fix applied.')
