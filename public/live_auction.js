const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let sessions=[],activeId='',room=null,poll=null,tick=null,marketItems=[];const querySession=new URLSearchParams(location.search).get('session')||'';
async function j(url,opt={}){const r=await fetch(url,{cache:'no-store',credentials:'same-origin',headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});let d={};try{d=await r.json()}catch{}if(!r.ok){let e=new Error(d.error||`HTTP ${r.status}`);e.status=r.status;throw e}return d}
function renderList(){const rows=sessions.filter(s=>['scheduled','live'].includes(s.status));$('liveList').innerHTML=rows.map(s=>`<article class="live-session-card"><h3>${s.status==='live'?'🔴 مباشر الآن':'🗓️ مجدول'} — ${esc(s.title||'بث مباشر')}</h3><p>${esc(s.description||'')}</p><p>${esc(s.broadcasterName||'نوادر العملات')}</p><p>${esc(s.startAt||'')}</p><button class="watch-btn" onclick="watchSession('${esc(s.id)}')">${s.status==='live'?'▶ مشاهدة البث':'فتح الجلسة'}</button></article>`).join('')||'<p>لا توجد جلسات بث مباشر مجدولة حاليًا.</p>'}
async function load(){try{const d=await j('/api/public/live-auctions');sessions=d.sessions||[];renderList();if(activeId)renderActive();else if(querySession&&sessions.some(s=>String(s.id)===String(querySession)))watchSession(querySession)}catch{$('liveList').innerHTML='<p>تعذر تحميل جلسات البث المباشر.</p>'}}
async function loadMarket(){try{marketItems=(await j('/api/public/market')).items||[]}catch{marketItems=[]}}
function active(){return sessions.find(s=>String(s.id)===String(activeId))}
async function watchSession(id){activeId=id;history.replaceState(null,'','/live-auction?session='+encodeURIComponent(id));const s=active();if(!s)return;$('viewerPanel').hidden=false;$('viewerTitle').textContent=(s.status==='live'?'🔴 ':'')+(s.title||'بث مباشر');$('viewerPanel').scrollIntoView({behavior:'smooth'});await connectVideo();renderActive();clearInterval(poll);poll=setInterval(load,1800);clearInterval(tick);tick=setInterval(renderCountdown,500)}
async function connectVideo(){
  if(room){await room.disconnect();room=null}
  const stage=$('videoStage');
  stage.innerHTML='<span class="viewer-wait" style="color:white">جارٍ الاتصال بالبث…</span>';
  $('videoMsg').textContent='';
  try{
    if(!window.LivekitClient)throw Error('تعذر تحميل مكتبة الفيديو');
    const t=await j('/api/live-media/token?sessionId='+encodeURIComponent(activeId)+'&role=viewer');
    room=new LivekitClient.Room({adaptiveStream:true});
    const attachTrack=(track)=>{
      if(!track||!(track.kind==='video'||track.kind==='audio'))return;
      const el=track.attach();el.autoplay=true;el.playsInline=true;
      if(track.kind==='video'){
        stage.querySelectorAll('video,.viewer-wait').forEach(x=>x.remove());
        stage.appendChild(el);
      }else{
        el.dataset.liveAudio='1';
        document.querySelectorAll('audio[data-live-audio="1"]').forEach(x=>{if(x!==el)x.remove()});
        document.body.appendChild(el);
        el.play?.().catch(()=>{});
      }
    };
    room.on(LivekitClient.RoomEvent.TrackSubscribed,(track)=>attachTrack(track))
      .on(LivekitClient.RoomEvent.TrackUnsubscribed,(track)=>track.detach())
      .on(LivekitClient.RoomEvent.ParticipantConnected,()=>{$('videoMsg').textContent='متصل بالبث المباشر.'})
      .on(LivekitClient.RoomEvent.Disconnected,()=>{$('videoMsg').textContent='انقطع اتصال الفيديو. يمكنك إعادة فتح الجلسة.'});
    await room.connect(t.url,t.token);
    // Important: a publisher may already be live before the viewer joins. In that
    // case TrackSubscribed can fire during room.connect(). Never overwrite the
    // attached <video> after connect, and also sweep existing publications once.
    for(const participant of room.remoteParticipants.values()){
      for(const pub of participant.trackPublications.values()){
        if(pub.track)attachTrack(pub.track);
      }
    }
    if(!stage.querySelector('video')){
      stage.innerHTML='<span class="viewer-wait" style="color:white">تم الاتصال. بانتظار كاميرا المذيع…</span>';
    }
    $('videoMsg').textContent='الفيديو مباشر وغير مسجل.';
  }catch(e){
    stage.innerHTML='<span style="color:white">الفيديو غير متاح حاليًا</span>';
    $('videoMsg').textContent=e.message||'تعذر الاتصال بالفيديو';
  }
}
function renderTicker(s,title){const box=$('viewerTicker'),track=$('viewerTickerTrack');if(!box||!track)return;const price=Number(s.currentPrice||0).toLocaleString('ar-SA');track.innerHTML=`<span>🔴 ${s.status==='live'?'مباشر الآن':'مجدول'}</span><span>🔨 ${esc(title||'بانتظار القطعة التالية')}</span><span>💰 السعر ${price} ر.س</span><span>🏆 آخر مزايد: ${esc(s.latestBidderName||'لا توجد مزايدة')}</span><span>➕ الزيادة ${Number(s.bidStep||1).toLocaleString('ar-SA')} ر.س</span>`;box.hidden=false}
function renderLiveMarket(s){const box=$('liveMarket'),row=$('liveMarketRow');if(!box||!row)return;if(!s.marketEnabled){box.hidden=true;return}box.hidden=false;const picks=marketItems.slice(0,12);row.innerHTML=picks.map(i=>{const title=i.title||[i.country,i.denomination].filter(Boolean).join(' — ')||'مقتنى';const price=Number(i.marketSalePrice||i.marketUnitPrice||i.price||0).toLocaleString('ar-SA');return `<article class="live-market-item">${i.frontImg?`<img src="${esc(i.frontImg)}" alt="">`:''}<b>${esc(title)}</b><div>${price} ر.س</div><a href="/market" target="_blank">عرض في السوق</a></article>`}).join('')||'<p>لا توجد عروض سوق نشطة الآن.</p>'}
function renderActive(){const s=active();if(!s)return;$('viewerTitle').textContent=(s.status==='live'?'🔴 ':'')+(s.title||'بث مباشر');const lot=s.currentLot,current=(s.items||[]).find(i=>String(i.id)===String(s.currentItemId||''));const title=lot?.title||current?.title||'';renderTicker(s,title);renderLiveMarket(s);if(!title){$('bidPanel').innerHTML='<h3>بانتظار فتح القطعة التالية للمزايدة…</h3><p class="muted">استمر في مشاهدة الكاميرا.</p>';return}const step=Number(s.bidStep||1),currentPrice=Number(s.currentPrice||0),minimum=currentPrice>0?currentPrice+step:step;$('bidPanel').innerHTML=`<h3>${esc(title)}</h3><div class="live-price">${currentPrice.toLocaleString('ar-SA')} ر.س</div><p>قيمة الزيادة: ${step.toLocaleString('ar-SA')} ر.س</p><p>آخر مزايد: ${esc(s.latestBidderName||'لا يوجد بعد')}</p><div class="live-count" id="liveCountdown"></div><div class="live-actions"><input id="liveBidAmount" type="number" min="${minimum}" step="${step}" value="${minimum}"><button onclick="submitBid()">زايد الآن</button></div><p id="bidMsg" class="muted">المزايدة تتطلب حسابًا موثقًا بالكامل.</p>`;renderCountdown()}
function renderCountdown(){const s=active(),el=$('liveCountdown');if(!s||!el)return;if(!s.lotEndsAt){el.textContent='المزاد مفتوح حتى يغلقه المذيع';return}const ms=new Date(s.lotEndsAt).getTime()-Date.now();if(ms<=0){el.textContent='انتهى وقت القطعة';return}const sec=Math.ceil(ms/1000);el.textContent=`متبقي ${Math.floor(sec/60)}:${String(sec%60).padStart(2,'0')}`}
async function submitBid(){const amount=Number($('liveBidAmount')?.value||0),msg=$('bidMsg');try{const d=await j('/api/live-auctions/bid',{method:'POST',body:JSON.stringify({id:activeId,amount})});msg.textContent='✓ تم تسجيل مزايدتك.';await load()}catch(e){if(e.status===401){location.href='/account?next='+encodeURIComponent('/live-auction?session='+activeId);return}msg.textContent=e.message||'تعذر تسجيل المزايدة'}}
async function closeViewer(){activeId='';clearInterval(poll);clearInterval(tick);if(room){await room.disconnect();room=null}$('viewerPanel').hidden=true}window.watchSession=watchSession;window.submitBid=submitBid;$('closeViewer').onclick=closeViewer;Promise.all([loadMarket(),load()]);setInterval(()=>{if(!activeId)load()},7000);
