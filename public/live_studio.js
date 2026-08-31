const $=id=>document.getElementById(id); const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let activeSession=null, room=null, isSeller=false, micOn=true, currentFacing='user', refreshTimer=null, countdownTimer=null;
const querySession=new URLSearchParams(location.search).get('session')||'';
async function json(url,opt={}){const r=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});let d={};try{d=await r.json()}catch{}if(!r.ok){let e=new Error(d.error||`HTTP ${r.status}`);e.status=r.status;throw e}return d}
async function adminOrSellerControl(action,extra={}){if(!activeSession)throw Error('اختر جلسة أولًا');const body=JSON.stringify({id:activeSession.id,action,...extra});try{return await json('/api/live-auctions/control',{method:'POST',body})}catch(e){if(e.status!==401&&e.status!==403)throw e;return await json('/api/live-auctions/seller-control',{method:'POST',body})}}
async function saveNewSession(){const body={title:$('newSessionTitle').value||'بث مباشر من الكاميرا',description:$('newSessionDescription').value||'',bidStep:Number($('newSessionStep').value||1),mode:'camera',itemIds:[]};try{return await json('/api/live-auctions/save',{method:'POST',body:JSON.stringify(body)})}catch(e){if(e.status!==401&&e.status!==403)throw e;return await json('/api/live-auctions/seller-save',{method:'POST',body:JSON.stringify(body)})}}
function setStatus(msg,kind=''){$('studioStatus').className='status '+kind;$('studioStatus').textContent=msg}
function selectSession(s){activeSession=s;history.replaceState(null,'','/live-studio?session='+encodeURIComponent(s.id));$('studioMain').hidden=false;$('sessionTitle').textContent='🔴 '+(s.title||'البث المباشر');$('lotStep').value=Number(s.bidStep||1);renderPrepared(s);renderMarketState(s);renderTicker(s);refreshSession()}
function sessionDate(s){const raw=s.startedAt||s.startAt||s.created||'';if(!raw)return 'بدون تاريخ';try{return new Date(raw).toLocaleDateString('ar-SA',{year:'numeric',month:'2-digit',day:'2-digit'})}catch{return String(raw).slice(0,10)}}
function renderSessions(rows){const active=(rows||[]).filter(x=>['scheduled','live'].includes(x.status));$('sessionList').innerHTML=active.map(s=>`<div class="session-row"><div><b>${esc(s.title||'جلسة بث')}</b><div>${s.status==='live'?'🔴 مباشر الآن':'🗓️ مجدولة'} — ${esc(sessionDate(s))} — ${s.mode==='prepared'?'مُحضّرة':'كاميرا حرة'}</div></div><button class="primary" data-sid="${esc(s.id)}">فتح الاستوديو</button></div>`).join('')||'<p>لا توجد جلسات نشطة. الجلسات المنتهية محفوظة في أرشيف الإدارة.</p>';document.querySelectorAll('[data-sid]').forEach(b=>b.onclick=()=>{const s=active.find(x=>String(x.id)===String(b.dataset.sid));if(s)selectSession(s)})}
async function boot(){let rows=[];
  // V5.3.1: when the same browser is logged in as both admin and participant,
  // prefer the admin session. V5.3.0 checked the participant session first and
  // stopped if that participant lacked liveBroadcast permission, leaving the
  // studio session list empty even when opened from the admin live-auction card.
  try{
    const a=await json('/api/live-auctions/admin');
    isSeller=false;
    rows=a.sessions||[];
    $('createSessionBox').hidden=false;
    setStatus('✓ استوديو الإدارة جاهز.','ok');
  }catch(adminErr){
    try{
      const mine=await json('/api/live-auctions/mine');
      isSeller=true;
      if(!mine.allowed){
        setStatus('حسابك مسجل، لكن صلاحية البث المباشر غير مفعلة. اطلب تفعيلها من الإدارة.','warn');
        renderSessions([]);
        return;
      }
      rows=mine.sessions||[];
      $('createSessionBox').hidden=false;
      setStatus('✓ حساب بائع موثق ومصرّح له بالبث المباشر.','ok');
    }catch(e){
      setStatus('سجل الدخول إلى الإدارة أو حساب بائع موثق لديه صلاحية البث.','warn');
      return;
    }
  }
  renderSessions(rows);
  if(querySession){
    const s=rows.find(x=>String(x.id)===String(querySession));
    if(s)selectSession(s);
    else setStatus('لم يتم العثور على جلسة البث المطلوبة ضمن الجلسات المتاحة لهذا الحساب.','warn');
  }
}
function attachLocalVideo(){if(!room)return;const box=$('localVideo');box.querySelectorAll('video,audio').forEach(x=>x.remove());for(const pub of room.localParticipant.trackPublications.values()){if(pub.track&&pub.track.kind==='video'){const el=pub.track.attach();el.autoplay=true;el.muted=true;el.playsInline=true;box.appendChild(el)}}}
async function startCamera(){if(!activeSession)return alert('اختر جلسة أولًا');if(!window.LivekitClient)return alert('تعذر تحميل مكتبة الفيديو الحي. تحقق من الاتصال بالإنترنت.');$('startCamera').disabled=true;$('mediaStatus').textContent='جارٍ طلب إذن الكاميرا والميكروفون…';try{await adminOrSellerControl('start');const t=await json('/api/live-media/token?sessionId='+encodeURIComponent(activeSession.id)+'&role=publisher');room=new LivekitClient.Room({adaptiveStream:true,dynacast:true});room.on(LivekitClient.RoomEvent.Disconnected,()=>{$('mediaStatus').textContent='انقطع اتصال الفيديو.'});await room.connect(t.url,t.token);currentFacing='user';await room.localParticipant.setCameraEnabled(true,{facingMode:{ideal:currentFacing}});await room.localParticipant.setMicrophoneEnabled(true);attachLocalVideo();$('mediaStatus').className='status ok';$('mediaStatus').textContent='🔴 الكاميرا والصوت يبثان الآن للمشاهدين. الفيديو غير مسجل.';$('switchCamera').disabled=false;$('toggleMic').disabled=false;$('endStream').disabled=false;activeSession.status='live';renderTicker(activeSession);startPolling()}catch(e){$('startCamera').disabled=false;$('mediaStatus').className='status warn';$('mediaStatus').textContent=e.message||'تعذر بدء الفيديو'}}
async function switchCamera(){if(!room)return;const next=currentFacing==='user'?'environment':'user';$('switchCamera').disabled=true;try{const src=LivekitClient.Track?.Source?.Camera;let pub=src&&room.localParticipant.getTrackPublication?room.localParticipant.getTrackPublication(src):null;if(!pub)pub=[...room.localParticipant.trackPublications.values()].find(p=>p.track&&p.track.kind==='video');if(pub?.track?.restartTrack){await pub.track.restartTrack({facingMode:{ideal:next}})}else{await room.localParticipant.setCameraEnabled(false);await room.localParticipant.setCameraEnabled(true,{facingMode:{ideal:next}})}currentFacing=next;attachLocalVideo();$('mediaStatus').className='status ok';$('mediaStatus').textContent=currentFacing==='environment'?'📷 الكاميرا الخلفية تعمل الآن.':'🤳 الكاميرا الأمامية تعمل الآن.'}catch(e){$('mediaStatus').className='status warn';$('mediaStatus').textContent='تعذر تبديل الكاميرا على هذا الجهاز: '+(e.message||'جرّب من الجوال')}finally{$('switchCamera').disabled=false}}
async function endStream(){if(!confirm('إنهاء البث المباشر؟ سيتم نقل الجلسة تلقائيًا إلى أرشيف الإدارة.'))return;try{await adminOrSellerControl('end')}catch{}if(room){await room.disconnect();room=null}$('startCamera').disabled=false;$('switchCamera').disabled=true;$('toggleMic').disabled=true;$('endStream').disabled=true;$('mediaStatus').className='status';$('mediaStatus').textContent='تم إنهاء البث ونقل الجلسة إلى الأرشيف.';stopPolling();await boot()}
async function toggleMic(){if(!room)return;micOn=!micOn;await room.localParticipant.setMicrophoneEnabled(micOn);$('toggleMic').textContent=micOn?'🎙 كتم الميكروفون':'🎙 تشغيل الميكروفون'}
async function openLot(){const title=$('lotTitle').value.trim();if(!title)return alert('اكتب اسم أو وصف القطعة المعروضة أمام الكاميرا');try{await adminOrSellerControl('open-free-lot',{title,country:$('lotCountry').value.trim(),notes:$('lotNotes').value.trim(),startPrice:Number($('lotStart').value||0),bidStep:Number($('lotStep').value||1),durationSec:Number($('lotDuration').value||60)});$('lotTitle').value='';$('lotNotes').value='';await refreshSession()}catch(e){alert(e.message)}}
async function closeLot(sold){if(sold&&!confirm('اعتماد البيع لآخر مزايد وإنشاء الطلب والفاتورة؟'))return;try{await adminOrSellerControl('close-item',{sold});await refreshSession()}catch(e){alert(e.message)}}
async function openPrepared(itemId){const price=prompt('سعر البداية','0');if(price===null)return;try{await adminOrSellerControl('open-item',{itemId,price:Number(price||0)});await refreshSession()}catch(e){alert(e.message)}}

function renderTicker(s){const box=$('studioTicker'),track=$('studioTickerTrack');if(!box||!track)return;const lot=s?.currentLot;const current=(s?.items||s?.itemsDetailed||[]).find(i=>String(i.id||i.itemId)===String(s?.currentItemId||''));const title=lot?.title||current?.title||'بانتظار فتح القطعة';const price=Number(s?.currentPrice||0).toLocaleString('ar-SA');const bidder=s?.latestBidderName||'لا توجد مزايدة';const state=s?.status==='live'?'مباشر الآن':'مجدول';track.innerHTML=`<span>🔴 ${esc(state)}</span><span>🔨 ${esc(title)}</span><span>💰 السعر ${price} ر.س</span><span>🏆 آخر مزايد: ${esc(bidder)}</span><span>➕ الزيادة ${Number(s?.bidStep||1).toLocaleString('ar-SA')} ر.س</span>`;box.hidden=false}
function renderMarketState(s){const on=!!s?.marketEnabled,chip=$('marketLiveState'),btn=$('toggleLiveMarket');if(!chip||!btn)return;chip.className='market-chip '+(on?'on':'');chip.textContent=on?'✓ السوق مفعل':'غير مفعل';btn.textContent=on?'إيقاف السوق في البث':'تفعيل السوق في البث'}
async function toggleLiveMarket(){if(!activeSession)return alert('اختر جلسة أولًا');try{const on=!activeSession.marketEnabled;const d=await adminOrSellerControl('market-toggle',{enabled:on});activeSession=d.session||{...activeSession,marketEnabled:on};renderMarketState(activeSession);renderTicker(activeSession)}catch(e){alert(e.message||'تعذر تغيير حالة السوق')}}

function renderPrepared(s){const box=$('preparedBox'),items=s.items||s.itemsDetailed||[];if(s.mode!=='prepared'&&!(s.itemIds||[]).length){box.hidden=true;return}box.hidden=false;$('preparedItems').innerHTML=(items||[]).map(i=>`<div class="session-row"><b>${esc(i.title||i.itemId||i.id)}</b><button class="ghost" onclick="openPrepared('${esc(i.id||i.itemId)}')">فتح للمزايدة</button></div>`).join('')||'<p>لا توجد مقتنيات محضّرة.</p>'}
function renderCurrent(s){const lot=s.currentLot;const open=!!(lot||s.currentItemId);$('sellLot').disabled=!open||!s.latestBidderName;$('closeLot').disabled=!open;if(!open){$('currentLotBox').innerHTML='لا توجد قطعة مفتوحة.';return}const title=lot?.title||((s.items||[]).find(i=>String(i.id)===String(s.currentItemId))?.title)||'مقتنى محضّر';$('currentLotBox').innerHTML=`<b>${esc(title)}</b><div class="price">${Number(s.currentPrice||0).toLocaleString('ar-SA')} ر.س</div><div>آخر مزايد: ${esc(s.latestBidderName||'لا يوجد بعد')}</div><div class="countdown" id="studioCountdown"></div>`;updateCountdown(s.lotEndsAt,'studioCountdown')}
function updateCountdown(end,id){const el=$(id);if(!el)return;if(!end){el.textContent='مفتوح حتى الإغلاق اليدوي';return}const ms=new Date(end).getTime()-Date.now();if(ms<=0){el.textContent='انتهى الوقت';return}const sec=Math.ceil(ms/1000);el.textContent=`متبقي ${Math.floor(sec/60)}:${String(sec%60).padStart(2,'0')}`}
async function refreshSession(){if(!activeSession)return;try{let rows=[];try{rows=(await json('/api/live-auctions/admin')).sessions||[]}catch{rows=(await json('/api/live-auctions/mine')).sessions||[]}const s=rows.find(x=>String(x.id)===String(activeSession.id));if(s){activeSession=s;renderCurrent(s);renderPrepared(s);renderMarketState(s);renderTicker(s)}}catch{}}
function startPolling(){stopPolling();refreshTimer=setInterval(refreshSession,1800);countdownTimer=setInterval(()=>{if(activeSession)updateCountdown(activeSession.lotEndsAt,'studioCountdown')},500)}function stopPolling(){clearInterval(refreshTimer);clearInterval(countdownTimer)}
$('switchCamera').onclick=switchCamera;$('toggleLiveMarket').onclick=toggleLiveMarket;$('createSessionBtn').onclick=async()=>{try{const d=await saveNewSession();selectSession(d.session);await boot()}catch(e){alert(e.message)}};$('startCamera').onclick=startCamera;$('toggleMic').onclick=toggleMic;$('endStream').onclick=endStream;$('openLot').onclick=openLot;$('sellLot').onclick=()=>closeLot(true);$('closeLot').onclick=()=>closeLot(false);window.openPrepared=openPrepared;window.addEventListener('beforeunload',()=>{try{room?.disconnect()}catch{}});boot();
