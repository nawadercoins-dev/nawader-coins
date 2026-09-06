from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'server.py'
APP=ROOT/'admin'/'app.js'
CSS=ROOT/'admin'/'styles.css'

# ---- server: admin edit pending data-entry submission ----
s=SERVER.read_text(encoding='utf-8')
marker="""            if p=='/api/data-entry/review':
"""
block="""            if p=='/api/data-entry/admin-edit':
                if not self.is_admin():
                    self.sendj({'error':'يلزم تسجيل دخول الإدارة'},401); return
                sid=str(d.get('id') or '').strip()
                if not sid:
                    self.sendj({'error':'معرّف السجل مطلوب'},400); return
                rows=load_collectible_submissions(); row=next((x for x in rows if str(x.get('id'))==sid and x.get('submissionSource')=='data_entry'),None)
                if not row:
                    self.sendj({'error':'السجل غير موجود'},404); return
                if row.get('status')!='pending':
                    self.sendj({'error':'يمكن تعديل السجل من الإدارة فقط وهو بانتظار الاعتماد'},409); return
                text_fields=('country','denomination','year','issueEdition','type','condition','serial','notes')
                limits={'country':120,'denomination':180,'year':80,'issueEdition':140,'type':120,'condition':120,'serial':160,'notes':3000}
                for k in text_fields:
                    if k in d: row[k]=str(d.get(k) or '').strip()[:limits[k]]
                if not str(row.get('country') or '').strip() or not str(row.get('denomination') or '').strip():
                    self.sendj({'error':'الدولة/المنشأ واسم المقتنى/الفئة مطلوبان'},400); return
                for k in ('purchase','shipping','other','salePrice'):
                    if k in d:
                        try: row[k]=max(0,float(d.get(k) or 0))
                        except Exception: row[k]=0
                row['expectedPrice']=row.get('salePrice') or row.get('expectedPrice') or 0
                if 'inventoryUnitCount' in d:
                    try: row['inventoryUnitCount']=max(1,int(float(d.get('inventoryUnitCount') or 1)))
                    except Exception: row['inventoryUnitCount']=1
                if 'piecesPerUnit' in d:
                    try: row['piecesPerUnit']=max(1,int(float(d.get('piecesPerUnit') or 1)))
                    except Exception: row['piecesPerUnit']=1
                row['quantity']=max(1,int(row.get('inventoryUnitCount') or 1))*max(1,int(row.get('piecesPerUnit') or 1))
                now=datetime.datetime.now().isoformat(); row['updated']=now; row['adminEditedAt']=now
                hist=row.get('reviewHistory') if isinstance(row.get('reviewHistory'),list) else []
                hist.append({'action':'admin_edit','note':'تعديل مباشر قبل الاعتماد','at':now,'by':'الإدارة'}); row['reviewHistory']=hist[-50:]
                save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                append_operation('تعديل سجل مسؤول إدخال البيانات قبل الاعتماد',{'submissionId':sid},actor='الإدارة')
                self.sendj({'ok':True,'submission':row}); return

"""
if "if p=='/api/data-entry/admin-edit':" not in s:
    if marker not in s: raise RuntimeError('review endpoint marker not found')
    s=s.replace(marker,block+marker,1)
SERVER.write_text(s,encoding='utf-8')

# ---- app: buttons + inline admin edit dialog ----
p=APP.read_text(encoding='utf-8')
old="""${editable?`<div class=\"actions\"><button class=\"approve\" onclick=\"reviewDataEntry('${esc(r.id)}','approve')\">✓ اعتماد وإرسال للمستودع</button><button class=\"changes\" onclick=\"reviewDataEntry('${esc(r.id)}','needs_changes')\">↩ إعادة للتعديل</button><button class=\"reject\" onclick=\"reviewDataEntry('${esc(r.id)}','reject')\">رفض</button></div>`:''}
"""
new="""${editable?`<div class=\"actions data-entry-review-actions\"><button class=\"changes\" onclick=\"editPendingDataEntry('${esc(r.id)}')\">✎ تعديل البيانات</button><button class=\"approve\" onclick=\"reviewDataEntry('${esc(r.id)}','approve')\">✓ اعتماد وإرسال للمستودع</button><button class=\"changes\" onclick=\"reviewDataEntry('${esc(r.id)}','needs_changes')\">↩ إرجاع لمسؤول إدخال البيانات</button><button class=\"reject\" onclick=\"reviewDataEntry('${esc(r.id)}','reject')\">رفض</button></div>`:''}
"""
if old in p:
    p=p.replace(old,new,1)
elif 'editPendingDataEntry' not in p:
    raise RuntimeError('approval action block not found')

anchor="""window.reviewDataEntry=async(id,action)=>{
"""
func="""window.editPendingDataEntry=async(id)=>{
  try{
    const res=await api('/api/collectible-submissions/admin');
    const r=(res.submissions||[]).find(x=>String(x.id)===String(id));
    if(!r)throw new Error('السجل غير موجود');
    if(r.status!=='pending')throw new Error('السجل لم يعد بانتظار الاعتماد');
    let d=document.getElementById('adminDataEntryEditDialog');
    if(!d){
      d=document.createElement('dialog');d.id='adminDataEntryEditDialog';d.className='admin-data-entry-edit-dialog';
      d.innerHTML=`<form method=\"dialog\" id=\"adminDataEntryEditForm\"><button type=\"button\" class=\"admin-edit-close\" aria-label=\"إغلاق\">×</button><h2>تعديل المقتنى قبل الاعتماد</h2><p class=\"muted\">التعديل هنا يحفظ السجل بانتظار الاعتماد ولا يرسله للمستودع حتى تضغط اعتماد.</p><div class=\"admin-edit-grid\"><label>الدولة / المنشأ<input name=\"country\" required></label><label>الفئة / اسم المقتنى<input name=\"denomination\" required></label><label>السنة<input name=\"year\"></label><label>الإصدار<input name=\"issueEdition\"></label><label>النوع<input name=\"type\"></label><label>الحالة<input name=\"condition\"></label><label>الرقم التسلسلي<input name=\"serial\"></label><label>عدد الوحدات<input name=\"inventoryUnitCount\" type=\"number\" min=\"1\"></label><label>عدد القطع في الوحدة<input name=\"piecesPerUnit\" type=\"number\" min=\"1\"></label><label>سعر الشراء<input name=\"purchase\" type=\"number\" min=\"0\" step=\"0.01\"></label><label>الشحن<input name=\"shipping\" type=\"number\" min=\"0\" step=\"0.01\"></label><label>تكاليف أخرى<input name=\"other\" type=\"number\" min=\"0\" step=\"0.01\"></label><label>سعر البيع<input name=\"salePrice\" type=\"number\" min=\"0\" step=\"0.01\"></label><label class=\"wide\">ملاحظات<textarea name=\"notes\"></textarea></label></div><div class=\"actions\"><button type=\"button\" class=\"approve\" id=\"adminDataEntrySaveEdit\">حفظ التعديل</button><button type=\"button\" class=\"ghost\" id=\"adminDataEntryCancelEdit\">إلغاء</button></div></form>`;
      document.body.appendChild(d);
      d.querySelector('.admin-edit-close').onclick=()=>d.close();
      d.querySelector('#adminDataEntryCancelEdit').onclick=()=>d.close();
      d.addEventListener('click',e=>{if(e.target===d)d.close()});
    }
    const f=d.querySelector('form');
    const set=(n,v)=>{if(f.elements[n])f.elements[n].value=v??''};
    ['country','denomination','year','issueEdition','type','condition','serial','notes','purchase','shipping','other','salePrice','inventoryUnitCount','piecesPerUnit'].forEach(k=>set(k,r[k]));
    d.dataset.recordId=String(id);d.showModal();
    d.querySelector('#adminDataEntrySaveEdit').onclick=async()=>{
      const body={id:d.dataset.recordId};
      ['country','denomination','year','issueEdition','type','condition','serial','notes'].forEach(k=>body[k]=String(f.elements[k]?.value||'').trim());
      ['purchase','shipping','other','salePrice','inventoryUnitCount','piecesPerUnit'].forEach(k=>body[k]=Number(f.elements[k]?.value||0));
      const btn=d.querySelector('#adminDataEntrySaveEdit'),txt=btn.textContent;btn.disabled=true;btn.textContent='جارٍ الحفظ…';
      try{await api('/api/data-entry/admin-edit',{method:'POST',body:JSON.stringify(body)});d.close();await renderCollectibleApprovals();toast('تم تعديل البيانات وبقي المقتنى بانتظار الاعتماد.')}catch(e){alert(e.message)}finally{btn.disabled=false;btn.textContent=txt}
    };
  }catch(e){alert(e.message)}
};

"""
if 'window.editPendingDataEntry=async' not in p:
    if anchor not in p: raise RuntimeError('review function anchor not found')
    p=p.replace(anchor,func+anchor,1)

# Improve lightbox close behavior even if toolbar overlaps it.
close_anchor="""if ($("coinLightboxClose"))
  $("coinLightboxClose").onclick = () => $("coinLightbox").close();
"""
close_new="""if ($("coinLightboxClose"))
  $("coinLightboxClose").onclick = (e) => { e.preventDefault(); e.stopPropagation(); $("coinLightbox").close(); };
if ($("coinLightbox")) $("coinLightbox").addEventListener('click',e=>{ if(e.target===$("coinLightbox")) $("coinLightbox").close(); });
"""
if close_anchor in p:p=p.replace(close_anchor,close_new,1)
APP.write_text(p,encoding='utf-8')

# ---- styles ----
c=CSS.read_text(encoding='utf-8')
marker_css='/* admin-approval-edit-close-v1 */'
if marker_css not in c:
    c += """

/* admin-approval-edit-close-v1 */
.coin-lightbox .lightbox-close{z-index:50!important;top:10px!important;right:10px!important;left:auto!important;width:44px!important;height:44px!important;min-width:44px!important;padding:0!important;border-radius:50%!important;background:#8d2431!important;color:#fff!important;font-size:30px!important;line-height:1!important;display:grid!important;place-items:center!important;box-shadow:0 4px 16px #0008!important}
.data-entry-review-actions{display:flex!important;gap:8px!important;flex-wrap:wrap!important;margin-top:12px!important}.data-entry-review-actions button{min-height:42px!important}
.admin-data-entry-edit-dialog{width:min(860px,94vw);max-height:90vh;overflow:auto;border:0;border-radius:18px;padding:18px;background:#f8faf9;color:#17302a}.admin-data-entry-edit-dialog::backdrop{background:#000b}.admin-data-entry-edit-dialog form{position:relative}.admin-data-entry-edit-dialog .admin-edit-close{position:absolute;left:0;top:0;width:42px;height:42px;border-radius:50%;padding:0;background:#8d2431;color:#fff;font-size:28px}.admin-edit-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:14px}.admin-edit-grid label{display:flex;flex-direction:column;gap:5px}.admin-edit-grid .wide{grid-column:1/-1}.admin-edit-grid textarea{min-height:100px}@media(max-width:680px){.admin-edit-grid{grid-template-columns:1fr}.admin-edit-grid .wide{grid-column:1}.data-entry-review-actions button{flex:1 1 45%}}
"""
CSS.write_text(c,encoding='utf-8')
print('admin approval edit/return + lightbox close patch applied')
