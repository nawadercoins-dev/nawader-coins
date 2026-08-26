// V4.6.7 — seller identity is rendered in every auction card.
const $=x=>document.getElementById(x),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])),money=x=>Number(x||0).toLocaleString('ar-SA')+' ر.س';
async function api(path,opt={}){let r=await fetch(path,{...opt,headers:{'Content-Type':'application/json',...(opt.headers||{})},cache:'no-store'});let j={};try{j=await r.json()}catch{}if(!r.ok)throw new Error(j.error||'تعذر الاتصال');return j}
function clock(end){if(!end)return'بدون وقت انتهاء';let d=new Date(end).getTime()-Date.now();if(d<=0)return'انتهى المزاد';let days=Math.floor(d/86400000);d%=86400000;let h=Math.floor(d/3600000);d%=3600000;let m=Math.floor(d/60000),s=Math.floor((d%60000)/1000);return`${days} يوم، ${h} ساعة، ${m} دقيقة، ${s} ثانية`}
let pid='',auctionSessionValid=false,platformSettings={buyerFeePercent:2.5,auctionEntryFee:10,entryFeeEnabled:false,negotiationHours:48};async function loadSettings(){try{platformSettings=await api('/api/settings/public');let x=$('feePolicy');if(x)x.textContent=`عمولة المشتري عند نجاح البيع ${Number(platformSettings.buyerFeePercent||0)}% لصالح المنصة${platformSettings.entryFeeEnabled?`، ورسم دخول المزاد ${money(platformSettings.auctionEntryFee||0)}`:''}.`;}catch(e){}}
function showParticipantStatus(p){if(!p)return;let box=$('participantStatusBox');if(box)box.hidden=false;let s=p.approvalStatus||(p.approved?'final':'preliminary'),ok=s==='final',labels={preliminary:'اعتماد مبدئي',final:'اعتماد نهائي',suspended:'الاعتماد معلّق',stopped:'الحساب موقوف',cancelled:'الحساب ملغى',new:'طلب جديد'};if($('participantStatusTitle'))$('participantStatusTitle').textContent=(ok?'✅ ':'⏳ ')+(labels[s]||'قيد المراجعة');if($('participantCode'))$('participantCode').textContent='رمز المشاركة: '+p.id;$('joinStatus').textContent=ok?'✅ جلسة الدخول فعالة ويمكنك المزايدة الآن':'يمكنك التصفح، وتحتاج اعتماد الإدارة النهائي قبل المزايدة.'}
async function checkParticipantStatus(){
  try{
    let r=await fetch('/api/participant/me',{cache:'no-store'});
    let d=await r.json().catch(()=>({}));
    if(!r.ok){
      pid='';auctionSessionValid=false;
      let box=$('participantStatusBox');if(box)box.hidden=false;
      if($('participantStatusTitle'))$('participantStatusTitle').textContent='🔐 تسجيل الدخول للمزايدة';
      if($('participantCode'))$('participantCode').textContent='';
      if($('joinStatus'))$('joinStatus').textContent='المزاد نشط. يلزم تسجيل الدخول فقط عند المزايدة.';
      return false;
    }
    let p=d.participant||{};
    pid=String(p.id||'');auctionSessionValid=!!pid;
    if(pid)localStorage.setItem('khazinaParticipantId',pid);
    if(window.NawaderVisitor&&p.id)NawaderVisitor.set({...p,verified:true});
    showParticipantStatus(p);
    return true;
  }catch(e){
    if($('joinStatus'))$('joinStatus').textContent='تعذر التحقق من جلسة الدخول مؤقتًا؛ المزاد ما زال نشطًا.';
    return auctionSessionValid;
  }
}
$('register').onclick=async()=>{try{let r=await api('/api/participant/register',{method:'POST',body:JSON.stringify({name:$('pname').value.trim(),phone:$('pphone').value.trim()})});if(!r.verified)throw new Error('لم يكتمل التفعيل الآلي؛ أعد المحاولة');pid=r.participant.id;auctionSessionValid=true;localStorage.setItem('khazinaParticipantId',pid);showParticipantStatus(r.participant);$('joinStatus').textContent=r.message||'تم منحك اعتمادًا مبدئيًا وتنتظر مراجعة الإدارة.'}catch(e){$('joinStatus').textContent='⚠️ '+e.message}}
let auctionImageGroups={};function photo(src,id,groupId,index){if(!src)return'';let v='pv-'+id+'-'+Math.random().toString(36).slice(2,7);return `<div><div class="public-photo-tools" data-target="${v}"><button data-act="open" title="فتح الصورة بحجم كبير">⛶</button><button data-act="zin" title="تكبير">＋</button><button data-act="zout" title="تصغير">－</button><button data-act="rl" title="تدوير يسار">↺</button><button data-act="rr" title="تدوير يمين">↻</button><button data-act="reset" title="إعادة الضبط">إعادة</button></div><div class="public-photo" id="${v}"><img src="${esc(src)}" data-auction-group="${esc(groupId)}" data-auction-index="${index}" class="auction-expandable-image" title="اضغط لفتح الصورة بحجم كبير" style="cursor:zoom-in"></div></div>`}

function sellerIdentity(i){
  const name=esc(i.sellerName||'صاحب المقتنى'), flag=esc(i.sellerFlag||'🌐');
  const avatar=i.sellerAvatar?`<img src="${esc(i.sellerAvatar)}" alt="">`:`<span>${name.slice(0,1)}</span>`;
  const countryTitle=esc(i.sellerCountry||'دولة الشحن غير محددة');
  return `<div class="seller-identity" title="دولة صاحب الحساب والشحن: ${countryTitle}">
    <div class="seller-avatar">${avatar}</div>
    <div class="seller-name">${name}${i.sellerVerified?' <b class="seller-check">✓</b>':''}</div>
    <div class="seller-flag" aria-label="${countryTitle}" title="${countryTitle}">${flag}</div>
  </div>`;
}

function card(i){
  let current=Number(i.auctionCurrentPrice||0);
  let opening=Number(i.auctionOpeningPrice||i.auctionStartPrice||0),step=Number(i.auctionBidStep||1); if(step<=0)step=1;
  let bids=Number(i.bidCount||0),ended=!!i.auctionEnded,sold=!!i.auctionSold;
  let suggested=bids>0?current+step:opening;
  let reserveClass=i.reserveState==='met'?'reserve-met':i.reserveState==='below'?'reserve-below':'reserve-none';
  let slideLabel=bids>0?`اسحب للمزايدة بـ ${money(suggested)} (+${money(step)}) ←`:`اسحب لفتح المزايدة بـ ${money(suggested)} ←`;
  let statusChip=ended?(sold?`<span class="winner-chip">🏆 تم البيع</span>`:`<span class="ended-chip">انتهى</span>`):`<span class="live-chip">● مزاد نشط</span>`;
  let transitionChip=i.transitionalIssueEnabled?`<span class="transitional-public-badge">⇄ إصدار انتقالي</span>`:'';
  let meta={id:i.id,title:`${i.country} — ${i.denomination}`,image:i.frontImg||'',url:'/auction#'+encodeURIComponent(i.id),kind:'auction'},fav=NawaderVisitor.isFavorite(i.id),liked=NawaderVisitor.isLiked(i.id);
  let gradeState = i.isGraded ? `${esc(i.gradingCompany||'مقيمة')} ${esc(i.gradeValue||'')}` : (String(i.condition||'').toUpperCase().includes('UNC') ? 'UNC / أنسر' : esc(i.condition||'غير مقيمة'));
  let result=ended?(sold?`<div class="auction-result sold">🏆 تم البيع بنجاح — تم اعتماد الفائز بالمزاد</div>`:`<div class="auction-result unsold">لم يتم البيع / لم يتحقق شرط البيع</div>`):'';
  let bidControls=ended?'':`
      <div class="bid-compact-row">
        <div class="bid-mini"><div class="mini-label">المزايدة التالية</div><div class="mini-value" id="next-${i.id}">${money(suggested)}</div></div>
        <div class="bid-mini"><div class="mini-label">مبلغ مزايدتك</div><input type="number" min="0.01" step="0.01" value="${suggested||''}" id="amt-${i.id}" oninput="updateSwipeAmount('${i.id}')"></div>
      </div>
      <div class="swipe-bid" id="swipe-${i.id}"><span class="swipe-text">${slideLabel}</span><span class="swipe-handle">◀</span></div><p class="muted" id="msg-${i.id}"></p>`;
  auctionImageGroups[i.id]=[i.frontImg,i.backImg,i.gradingCertImage,...(i.additionalImages||[])].filter(Boolean);

  return `<article class="auction-public-card two-column-auction-card" id="${i.id}" data-current="${current}" data-opening="${opening}" data-step="${step}" data-bids="${bids}">
    ${sellerIdentity(i)}
    <div class="auction-top-grid">
      <div class="auction-image-column">
        ${(i.frontImg||i.backImg)?`<div class="auction-cover" data-cover-id="${esc(i.id)}">
          <button class="cover-arrow cover-prev" type="button" onclick="event.stopPropagation();shiftAuctionCover('${i.id}',-1)" aria-label="الصورة السابقة">‹</button>
          <img id="cover-${i.id}" src="${esc(i.frontImg||i.backImg)}" data-cover-index="0" onclick="openAuctionLightbox('${i.id}',Number(this.dataset.coverIndex||0))" alt="${esc(i.country)} — ${esc(i.denomination)}">
          <button class="cover-arrow cover-next" type="button" onclick="event.stopPropagation();shiftAuctionCover('${i.id}',1)" aria-label="الصورة التالية">›</button>
          <span class="cover-count" id="cover-count-${i.id}">1/${auctionImageGroups[i.id].length}</span>
        </div>`:'<div class="auction-cover no-photo">لا توجد صورة</div>'}
        <div class="image-social-actions">
          <button class="${liked?'on':''}" onclick='toggleAuctionReaction(${JSON.stringify(meta)},"like",this)'>👍 <span>${liked?'معجب':'إعجاب'}</span></button>
          <button class="${fav?'on':''}" onclick='toggleAuctionReaction(${JSON.stringify(meta)},"favorite",this)'>❤️ <span>${fav?'في المفضلة':'مفضلة'}</span></button>
          <button onclick="shareAuctionItem('${i.id}')">↗ <span>مشاركة</span></button>
        </div>
        <div class="image-column-countdown">
          <span>الوقت المتبقي</span>
          <strong class="auction-clock" data-end="${esc(i.auctionEnd||'')}">${ended?'انتهى المزاد':esc(clock(i.auctionEnd))}</strong>
        </div>
      </div>

      <div class="auction-info-column">
        <div class="info-status-row">${statusChip}${transitionChip}</div>
        <div class="auction-title-marquee" title="${esc(i.country)} — ${esc(i.denomination)}">
          <div class="auction-title-track">${esc(i.country)} — ${esc(i.denomination)}</div>
        </div>
        <div class="info-meta">${esc(i.year||'')}${i.year&&gradeState?' · ':''}${gradeState}</div>
        <div class="info-price ${reserveClass}">
          <span>السعر الحالي</span>
          <strong>${money(current)}</strong>
        </div>
        <div class="info-mini-grid">
          <div><span>الفئة</span><b>${esc(i.denomination||'—')}</b></div>
          <div><span>المزايدات</span><b>${bids}</b></div>
          <div><span>الزيادة</span><b>${money(step)}</b></div>
          <div><span>سعر الفتح</span><b>${money(opening)}</b></div>
        </div>
      </div>
    </div>

    <div class="auction-lower">
      <div class="clean-activity">
        <div class="activity-head"><b>مؤشر المزاد</b><span>${i.reserveState==='met'?'✅ جاهز للبيع':i.reserveState==='below'?'يتقدم':'بانتظار المزايدات'}</span></div>
        <div class="auction-activity"><span class="activity-marker" style="left:${i.reserveState==='met'?88:Math.min(70,18+(bids*9))}%"></span></div>
      </div>

      ${result}
      ${i.auctionAdditionalTerms?`<div class="auction-extra-terms"><b>الشروط الإضافية</b><p>${esc(i.auctionAdditionalTerms)}</p></div>`:''}
      ${i.notes?`<p class="auction-notes">${esc(i.notes)}</p>`:''}
      <div class="clean-bid-area">${bidControls}</div>

    </div>
  </article>`
}
window.shiftAuctionCover=(id,dir)=>{
  const g=auctionImageGroups[id]||[], img=document.getElementById('cover-'+id), count=document.getElementById('cover-count-'+id);
  if(!img||!g.length)return;
  let n=(Number(img.dataset.coverIndex||0)+dir+g.length)%g.length;
  img.dataset.coverIndex=String(n); img.src=g[n]; if(count)count.textContent=`${n+1}/${g.length}`;
};
window.shareAuctionItem=async(id)=>{
  const i=(auctionAllItems||[]).find(x=>String(x.id)===String(id));
  if(!i)return;
  const url=location.origin+location.pathname+'#'+encodeURIComponent(id);
  const title=`مزاد ${i.country||''} ${i.denomination||''}`.trim();
  const text=`شاهد هذا المزاد في نوادر العملات: ${title}`;
  try{
    if(navigator.share){ await navigator.share({title,text,url}); return; }
  }catch(e){ if(e && e.name==='AbortError') return; }
  const action=prompt('اختر طريقة المشاركة:\n1 = واتساب\n2 = نسخ الرابط','1');
  if(action==='1') window.open('https://wa.me/?text='+encodeURIComponent(text+' '+url),'_blank','noopener');
  else if(action==='2'){
    try{ await navigator.clipboard.writeText(url); alert('تم نسخ رابط المزاد'); }
    catch(e){ prompt('انسخ الرابط:',url); }
  }
};
window.updateSwipeAmount=id=>{let input=$('amt-'+id),el=$('swipe-'+id),next=$('next-'+id);if(!input||!el)return;let amount=Number(input.value||0),card=document.getElementById(id),bids=Number(card?.dataset.bids||0);if(next)next.textContent=money(amount);let t=el.querySelector('.swipe-text');if(t)t.textContent=(bids?`اسحب للمزايدة بـ ${money(amount)} ←`:`اسحب لفتح المزايدة بـ ${money(amount)} ←`);resetSwipe(id)};
function initPublicViewers(){document.querySelectorAll('.public-photo').forEach(box=>{if(box.dataset.ready)return;box.dataset.ready='1';let img=box.querySelector('img'),st={scale:1,rot:0,x:0,y:0,drag:false,sx:0,sy:0};let draw=()=>img.style.transform=`translate(${st.x}px,${st.y}px) scale(${st.scale}) rotate(${st.rot}deg)`;let openLarge=()=>window.openAuctionLightbox?.(img.dataset.auctionGroup,Number(img.dataset.auctionIndex||0));let tools=document.querySelector(`.public-photo-tools[data-target="${box.id}"]`);tools?.querySelectorAll('button').forEach(b=>b.onclick=e=>{e.preventDefault();e.stopPropagation();let a=b.dataset.act;if(a==='open'){openLarge();return}if(a==='zin'){openLarge();return}if(a==='zout')st.scale=Math.max(.25,st.scale-.25);if(a==='rl')st.rot-=90;if(a==='rr')st.rot+=90;if(a==='reset')Object.assign(st,{scale:1,rot:0,x:0,y:0});draw()});box.ondblclick=e=>{e.preventDefault();openLarge()};box.onpointerdown=e=>{st.drag=true;st.sx=e.clientX-st.x;st.sy=e.clientY-st.y;box.setPointerCapture(e.pointerId)};box.onpointermove=e=>{if(!st.drag)return;st.x=e.clientX-st.sx;st.y=e.clientY-st.sy;draw()};box.onpointerup=box.onpointercancel=()=>{st.drag=false}})}
let auctionRenderToken='',initialAuctionLoad=true,hashHandled=false,auctionAllItems=[],auctionEndingOnly=false;
function auctionMatches(i){let q=($('auctionSearch')?.value||'').trim().toLowerCase();if(q&&!JSON.stringify([i.country,i.denomination,i.year,i.condition,i.notes]).toLowerCase().includes(q))return false;if(auctionEndingOnly){let t=new Date(i.auctionEnd||0).getTime()-Date.now();return !i.auctionEnded&&t>0&&t<=6*3600000}return true}

function initAuctionTitleMarquees(){
  document.querySelectorAll('.auction-title-marquee').forEach(box=>{
    const track=box.querySelector('.auction-title-track');
    if(!track)return;
    box.classList.remove('is-overflowing');
    track.style.removeProperty('--marquee-distance');
    requestAnimationFrame(()=>{
      const overflow=Math.max(0,track.scrollWidth-box.clientWidth);
      if(overflow>8){
        track.style.setProperty('--marquee-distance',`-${overflow+18}px`);
        box.classList.add('is-overflowing');
      }
    });
  });
}

function renderAuctionDiscovery(){let a=auctionAllItems.filter(auctionMatches);$('publicAuctions').innerHTML=a.map(card).join('')||'<div class="panel"><h2>لا توجد مزادات مطابقة.</h2></div>';initPublicViewers();initSwipes();initAuctionTitleMarquees();let soon=auctionAllItems.filter(i=>{let t=new Date(i.auctionEnd||0).getTime()-Date.now();return !i.auctionEnded&&t>0&&t<=6*3600000}).sort((x,y)=>new Date(x.auctionEnd)-new Date(y.auctionEnd));let strip=$('endingSoonStrip');if(strip){strip.hidden=!soon.length;strip.innerHTML=soon.slice(0,6).map(i=>`<button onclick="document.getElementById('${i.id}')?.scrollIntoView({behavior:'smooth',block:'center'})"><b>${esc(i.country)} — ${esc(i.denomination)}</b><small>${esc(clock(i.auctionEnd))}</small></button>`).join('')}}
function auctionToken(a){return a.map(i=>[i.id,i.auctionRound,i.auctionCurrentPrice,i.auctionEnd,i.auctionApproved,i.negotiationEnabled,i.negotiationPercent,i.reserveState,i.auctionEnded,i.auctionSold,i.updated].join(':')).join('|')}async function load(){try{let r=await api('/api/public/auctions'),a=r.items||[],token=auctionToken(a);auctionAllItems=a;if(initialAuctionLoad||token!==auctionRenderToken){let y=window.scrollY;auctionRenderToken=token;renderAuctionDiscovery();if(!hashHandled&&location.hash){hashHandled=true;requestAnimationFrame(()=>{let el=document.querySelector(location.hash);if(el)el.scrollIntoView({block:'start'})})}else if(!initialAuctionLoad){requestAnimationFrame(()=>window.scrollTo({top:y,left:0,behavior:'auto'}))}}initialAuctionLoad=false}catch(e){console.warn('تعذر تحديث المزادات مؤقتًا',e);if(initialAuctionLoad){$('publicAuctions').innerHTML='<div class="panel">تعذر الاتصال بالمزاد مؤقتًا. سيتم إعادة المحاولة تلقائيًا.</div>'}}}
window.toggleAuctionReaction=(meta,kind,btn)=>{let on=kind==='like'?NawaderVisitor.toggleLike(meta):NawaderVisitor.toggleFavorite(meta);btn.classList.toggle('on',on);btn.querySelector('span').textContent=kind==='like'?(on?'معجب':'إعجاب'):(on?'في المفضلة':'مفضلة')};
window.resetSwipe=id=>{let el=$('swipe-'+id);if(!el)return;let h=el.querySelector('.swipe-handle');h.style.transform='translateX(0)';el.classList.remove('ready','disabled')};
function initSwipes(){document.querySelectorAll('.swipe-bid').forEach(el=>{if(el.dataset.ready)return;el.dataset.ready='1';let id=el.id.slice(6),h=el.querySelector('.swipe-handle'),drag=false,startX=0,dx=0;let reset=()=>{dx=0;h.style.transform='translateX(0)';el.classList.remove('ready')};h.onpointerdown=e=>{if(el.classList.contains('disabled'))return;drag=true;startX=e.clientX;h.setPointerCapture(e.pointerId)};h.onpointermove=e=>{if(!drag)return;let max=Math.max(0,el.clientWidth-h.offsetWidth-8);dx=Math.max(-max,Math.min(0,e.clientX-startX));h.style.transform=`translateX(${dx}px)`;if(Math.abs(dx)>=max*.58)el.classList.add('ready');else el.classList.remove('ready')};h.onpointerup=h.onpointercancel=async()=>{if(!drag)return;drag=false;let max=Math.max(0,el.clientWidth-h.offsetWidth-8);if(Math.abs(dx)>=max*.58){el.classList.add('disabled');await bid(id)}else reset()}})}
window.bid=async id=>{let msg=$('msg-'+id),sw=$('swipe-'+id);let ok=auctionSessionValid||await checkParticipantStatus();if(!ok||!pid){msg.textContent='🔐 يلزم تسجيل الدخول للمزايدة. المزاد نفسه ما زال نشطًا.';resetSwipe(id);setTimeout(()=>{location.href='/account?next='+encodeURIComponent('/auction#'+id)},700);return}try{let amount=Number($('amt-'+id).value||0);if(amount<=0)throw new Error('اكتب مبلغ المزايدة أولًا');let r=await api('/api/bid',{method:'POST',body:JSON.stringify({itemId:id,participantId:pid,amount})});msg.textContent='✅ تم قبول مزايدتك: '+money(r.current);await load()}catch(e){let text=String(e.message||'');if(text.includes('جلسة الحساب')||text.includes('تسجيل الدخول')){auctionSessionValid=false;pid='';msg.textContent='🔐 تحتاج تحديث تسجيل الدخول للمزايدة فقط؛ المزاد ما زال نشطًا.';setTimeout(()=>{location.href='/account?next='+encodeURIComponent('/auction#'+id)},700)}else msg.textContent='⚠️ '+text;resetSwipe(id)}};

// V4.0.20: أزيل التفاوض من واجهة المزاد العامة.
function paintAuctionClocks(){document.querySelectorAll('.auction-clock').forEach(x=>{x.textContent=clock(x.dataset.end);let d=new Date(x.dataset.end).getTime()-Date.now();x.classList.remove('clock-hour','clock-ten','clock-minute');if(d>0&&d<=60000)x.classList.add('clock-minute');else if(d>0&&d<=600000)x.classList.add('clock-ten');else if(d>0&&d<=3600000)x.classList.add('clock-hour')})}setInterval(paintAuctionClocks,1000);paintAuctionClocks();setInterval(load,8000);setInterval(checkParticipantStatus,3000);loadSettings().then(load);checkParticipantStatus();

// V4.0.9 unified professional full-screen lightbox (same interaction model as market)
let ALB={group:'',idx:0,scale:1,rot:0,x:0,y:0,p:new Map(),dist:0};
function albImage(){return document.getElementById('auctionLightboxImg')}
function albDialog(){return document.getElementById('auctionLightbox')}
function albDraw(animate=false){let im=albImage();if(!im)return;im.style.transition=animate?'transform .22s ease':'none';im.style.transform=`translate(${ALB.x}px,${ALB.y}px) scale(${ALB.scale}) rotate(${ALB.rot}deg)`;if(animate)setTimeout(()=>{if(im)im.style.transition='none'},240)}
function albCenter(animate=true){ALB.x=0;ALB.y=0;albDraw(animate)}
function albReset(){Object.assign(ALB,{scale:1,rot:0,x:0,y:0});albDraw(true)}
function albLoadCurrent(){let a=auctionImageGroups[ALB.group]||[],im=albImage(),count=document.getElementById('auctionLightboxCount');if(!a.length||!im)return;ALB.idx=Math.max(0,Math.min(ALB.idx,a.length-1));im.src=a[ALB.idx];im.alt=`صورة ${ALB.idx+1} من ${a.length} للمقتنى في المزاد`;if(count)count.textContent=(ALB.idx+1)+' / '+a.length;albReset()}
window.openAuctionLightbox=(g,idx=0)=>{let a=auctionImageGroups[g]||[];if(!a.length)return;ALB.group=g;ALB.idx=Math.min(Math.max(0,idx),a.length-1);ALB.p.clear();ALB.dist=0;albLoadCurrent();let dlg=albDialog();if(dlg&&typeof dlg.showModal==='function'&&!dlg.open)dlg.showModal()};
// V4.0.10.1 robust delegated image opening (works after every auction re-render)
document.addEventListener('click',e=>{let im=e.target.closest?.('.auction-expandable-image');if(!im)return;e.preventDefault();e.stopPropagation();window.openAuctionLightbox(im.dataset.auctionGroup,Number(im.dataset.auctionIndex||0))});
function albMove(d){let a=auctionImageGroups[ALB.group]||[];if(!a.length)return;ALB.idx=(ALB.idx+d+a.length)%a.length;ALB.p.clear();ALB.dist=0;albLoadCurrent()}
document.getElementById('auctionLightboxClose')?.addEventListener('click',()=>albDialog()?.close());
document.querySelectorAll('[data-alb]').forEach(b=>b.addEventListener('click',async()=>{let a=b.dataset.alb;if(a==='prev'){albMove(-1);return}if(a==='next'){albMove(1);return}if(a==='zin')ALB.scale=Math.min(8,ALB.scale+.35);if(a==='zout')ALB.scale=Math.max(.25,ALB.scale-.35);if(a==='rl')ALB.rot-=90;if(a==='rr')ALB.rot+=90;if(a==='center'){albCenter();return}if(a==='reset'){albReset();return}if(a==='full'){let dlg=albDialog();try{if(document.fullscreenElement)await document.exitFullscreen();else if(dlg?.requestFullscreen)await dlg.requestFullscreen();else dlg?.classList.toggle('force-fullscreen')}catch(_){dlg?.classList.toggle('force-fullscreen')}return}albDraw()}));
let ast=document.getElementById('auctionLightboxStage');
if(ast){
  ast.addEventListener('pointerdown',e=>{ALB.p.set(e.pointerId,{x:e.clientX,y:e.clientY});ast.setPointerCapture(e.pointerId)});
  ast.addEventListener('pointermove',e=>{if(!ALB.p.has(e.pointerId))return;let old=ALB.p.get(e.pointerId);ALB.p.set(e.pointerId,{x:e.clientX,y:e.clientY});let v=[...ALB.p.values()];if(v.length===1){ALB.x+=e.clientX-old.x;ALB.y+=e.clientY-old.y}else if(v.length===2){let d=Math.hypot(v[0].x-v[1].x,v[0].y-v[1].y);if(ALB.dist)ALB.scale=Math.max(.35,Math.min(6,ALB.scale*d/ALB.dist));ALB.dist=d}albDraw()});
  function albPointerDone(e){ALB.p.delete(e.pointerId);if(ALB.p.size<2)ALB.dist=0}
  ast.addEventListener('pointerup',albPointerDone);ast.addEventListener('pointercancel',albPointerDone);
  ast.addEventListener('dblclick',()=>{ALB.scale=ALB.scale>1?1:2.25;albCenter(true)});
  ast.addEventListener('wheel',e=>{e.preventDefault();ALB.scale=Math.max(.25,Math.min(8,ALB.scale+(e.deltaY<0?.25:-.25)));albDraw()},{passive:false});
}
albDialog()?.addEventListener('click',e=>{if(e.target===albDialog())albDialog().close()});
document.addEventListener('keydown',e=>{let dlg=albDialog();if(!dlg?.open)return;if(e.key==='ArrowLeft')albMove(1);if(e.key==='ArrowRight')albMove(-1);if(e.key==='0')albReset();});

$('auctionSearch')?.addEventListener('input',renderAuctionDiscovery);$('endingSoonBtn')?.addEventListener('click',()=>{auctionEndingOnly=true;renderAuctionDiscovery()});$('allAuctionsBtn')?.addEventListener('click',()=>{auctionEndingOnly=false;if($('auctionSearch'))$('auctionSearch').value='';renderAuctionDiscovery()});
