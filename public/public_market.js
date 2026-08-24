document.documentElement.dataset.marketVersion='4.5.1';console.info('Nawader Market V4.5.1 loaded');
const $=id=>document.getElementById(id);let ITEMS=[],SETTINGS={},CURRENT=null,HASH_DONE=false;
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const money=x=>Number(x||0).toLocaleString('ar-SA',{maximumFractionDigits:2})+' ر.س';
function typeLabel(t){return t==='bundle'?'حزمة / بندل':t==='set'?'طقم':'قطعة واحدة'}
function priceUnit(i){return i.marketPriceUnit||(i.marketOfferType==='set'?'set':i.marketOfferType==='bundle'?'bundle':'piece')}
function priceUnitLabel(i){let p=priceUnit(i);return p==='set'?'الطقم':p==='bundle'?'الحزمة / البندل':p==='sheet'?'الورقة':'القطعة'}
function qtyUnitLabel(i,n=1){if(i.marketOfferType==='set')return n===1?'طقم':'أطقم';if(i.marketOfferType==='bundle')return n===1?'حزمة':'حزم';return priceUnit(i)==='sheet'?(n===1?'ورقة':'أوراق'):(n===1?'قطعة':'قطع')}
function setSizeLabel(v){return v==='mini'?'ميني / صغير':v==='medium'?'متوسط':v==='large'?'كبير':v==='full'?'كامل':v==='other'?'أخرى':''}
function setModeLabel(v){return v==='single-denoms'?'عملة واحدة / فئات متعددة':v==='single-issues'?'عملة واحدة / إصدارات أو سنوات متعددة':v==='multiple'?'أكثر من عملة أو دولة':v==='single'?'عملة واحدة / فئات متعددة':''}
function displayPrice(i){if(i.marketPriceUnit)return Number(i.marketSalePrice||0);if(i.marketOfferType==='set'&&Number(i.marketUnitPrice||0)>0)return Number(i.marketUnitPrice);return Number(i.marketSalePrice||i.marketUnitPrice||0)}
function briefDescription(i){
 const note=String(i.notes||'').replace(/\s+/g,' ').trim();
 if(note)return note;
 const edition=String(i.issueEdition||i.issueEditionOther||'').trim();
 return [edition?`الإصدار ${edition}`:'',i.year?`سنة ${i.year}`:'',i.condition?`حالة ${i.condition}`:''].filter(Boolean).join(' • ')||'مقتنى معروض للبيع';
}
async function get(url){let r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('تعذر تحميل السوق');return r.json()}
function totalFor(i,qty=1){return displayPrice(i)*Math.max(1,Number(qty||1))}
function reactionButtons(i){
  let meta={id:i.id,title:i.marketTitle||`${i.country} — ${i.denomination}`,image:i.frontImg||'',url:'/market#'+encodeURIComponent(i.id),kind:'market'},
      fav=NawaderVisitor.isFavorite(i.id),liked=NawaderVisitor.isLiked(i.id);
  return `<div class="market-social-actions">
    <button class="reaction-btn ${liked?'on':''}" onclick='toggleMarketReaction(${JSON.stringify(meta)},"like",this)'>👍 <span>${liked?'معجب':'إعجاب'}</span></button>
    <button class="reaction-btn ${fav?'on':''}" onclick='toggleMarketReaction(${JSON.stringify(meta)},"favorite",this)'>❤️ <span>${fav?'في المفضلة':'مفضلة'}</span></button>
    <button class="reaction-btn" onclick="shareMarketItem('${i.id}')">↗ <span>مشاركة</span></button>
  </div>`
}
window.toggleMarketReaction=(meta,kind,btn)=>{let on=kind==='like'?NawaderVisitor.toggleLike(meta):NawaderVisitor.toggleFavorite(meta);btn.classList.toggle('on',on);btn.querySelector('span').textContent=kind==='like'?(on?'معجب':'إعجاب'):(on?'في المفضلة':'مفضلة')};

window.shareMarketItem=async(id)=>{
  const i=ITEMS.find(x=>String(x.id)===String(id));
  if(!i)return;
  const url=location.origin+location.pathname+'#'+encodeURIComponent(id);
  const title=i.marketTitle||`${i.country||''} — ${i.denomination||''}`;
  const text=`شاهد هذا المعروض في سوق نوادر العملات: ${title}`;
  try{
    if(navigator.share){await navigator.share({title,text,url});return}
  }catch(e){if(e&&e.name==='AbortError')return}
  const action=prompt('اختر طريقة المشاركة:\\n1 = واتساب\\n2 = نسخ الرابط','1');
  if(action==='1')window.open('https://wa.me/?text='+encodeURIComponent(text+' '+url),'_blank','noopener');
  else if(action==='2'){
    try{await navigator.clipboard.writeText(url);alert('تم نسخ رابط المعروض')}
    catch(e){prompt('انسخ الرابط:',url)}
  }
};

let MARKET_IMAGE_GROUPS={};
window.shiftMarketImage=(id,dir)=>{
  const g=MARKET_IMAGE_GROUPS[id]||[],img=document.getElementById('market-cover-'+id),count=document.getElementById('market-cover-count-'+id);
  if(!img||!g.length)return;
  let n=(Number(img.dataset.marketIndex||0)+dir+g.length)%g.length;
  img.dataset.marketIndex=String(n);img.src=g[n];if(count)count.textContent=`${n+1}/${g.length}`;
};

function initMarketTitleMarquees(){
  document.querySelectorAll('.market-title-marquee,.market-line-scroll').forEach(box=>{
    const track=box.querySelector('.market-scroll-track');
    if(!track)return;
    box.classList.remove('is-overflowing');
    track.style.removeProperty('--market-marquee-distance');
    requestAnimationFrame(()=>{
      const overflow=Math.max(0,track.scrollWidth-box.clientWidth);
      if(overflow>8){
        track.style.setProperty('--market-marquee-distance',`-${overflow+16}px`);
        box.classList.add('is-overflowing');
      }
    });
  });
}
function card(i){
  let price=displayPrice(i),
      grade=i.isGraded?`${esc(i.gradingCompany||'مُقيَّم')} ${esc(i.gradeValue||'')}`:'',
      available=Number(i.availableQuantity||0),
      pieces=Number(i.marketSetPieces||0),
      size=setSizeLabel(i.marketSetSize),
      mode=setModeLabel(i.marketSetCurrencyMode),
      brief=briefDescription(i),
      title=i.marketTitle||`${i.country} — ${i.denomination}`,
      images=[i.frontImg,i.backImg,i.gradingCertImage,...(i.additionalImages||[])].filter(Boolean);
  MARKET_IMAGE_GROUPS[i.id]=images;
  return `<article class="card market-compact-card" id="${esc(i.id)}">
    <div class="market-card-top">
      <div class="market-image-column">
        <div class="photo market-photo">
          ${images.length?`<button class="market-photo-arrow market-photo-prev" type="button" onclick="event.stopPropagation();shiftMarketImage('${i.id}',-1)">‹</button>
          <img id="market-cover-${i.id}" src="${esc(images[0])}" data-market-index="0" loading="lazy" alt="${esc(title)}">
          <button class="market-photo-arrow market-photo-next" type="button" onclick="event.stopPropagation();shiftMarketImage('${i.id}',1)">›</button>
          <span class="market-photo-count" id="market-cover-count-${i.id}">1/${images.length}</span>`:'<span class="no-market-photo">لا توجد صورة</span>'}
        </div>
        ${reactionButtons(i)}
      </div>

      <div class="market-info-column">
        <div class="market-badge-row">
          <span class="badge">${typeLabel(i.marketOfferType)}</span>
          ${i.isGraded?`<span class="badge graded">${grade}</span>`:''}
          ${i.transitionalIssueEnabled?`<span class="badge transitional-public-badge">⇄ انتقالي</span>`:''}
        </div>

        <div class="market-title-marquee" title="${esc(title)}">
          <div class="market-scroll-track">${esc(title)}</div>
        </div>

        <div class="market-line-scroll" title="${esc(brief)}">
          <div class="market-scroll-track market-brief-track">${esc(brief)}</div>
        </div>

        <div class="market-price-box">
          <span>سعر ${priceUnitLabel(i)}</span>
          <strong>${money(price)}</strong>
        </div>

        <div class="market-mini-grid">
          <div><span>المتاح</span><b>${available} ${qtyUnitLabel(i,available)}</b></div>
          <div><span>الحالة</span><b>${esc(i.condition||'—')}</b></div>
          ${pieces?`<div><span>محتوى ${i.marketOfferType==='set'?'الطقم':'الحزمة'}</span><b>${pieces} قطعة</b></div>`:''}
          ${size?`<div><span>الحجم</span><b>${esc(size)}</b></div>`:''}
        </div>
      </div>
    </div>

    ${(mode||i.notes)?`<div class="market-secondary-line market-line-scroll"><div class="market-scroll-track">${mode?`التكوين: ${esc(mode)}`:''}${mode&&i.notes?' • ':''}${i.notes?esc(String(i.notes).replace(/\\s+/g,' ').trim()):''}</div></div>`:''}

    <div class="actions market-card-actions">
      <button class="buy" onclick="addToCart('${i.id}')">🛒 أضف للسلة</button>
      ${i.marketNegotiationEnabled?`<button class="offer" onclick="openRequest('${i.id}','offer')">تفاوض</button>`:''}
    </div>
  </article>`
}

function equalizeMarketCardRows(){
  const cards=[...document.querySelectorAll('#items .market-compact-card')];
  cards.forEach(c=>c.style.height='auto');
  if(!cards.length)return;

  const rows=[];
  cards.forEach(card=>{
    const top=Math.round(card.offsetTop);
    let row=rows.find(r=>Math.abs(r.top-top)<=3);
    if(!row){row={top,cards:[]};rows.push(row)}
    row.cards.push(card);
  });

  rows.forEach(row=>{
    const max=Math.max(...row.cards.map(c=>Math.ceil(c.getBoundingClientRect().height)));
    row.cards.forEach(c=>c.style.height=max+'px');
  });
}

let marketEqualizeTimer=null;
function scheduleMarketEqualize(){
  clearTimeout(marketEqualizeTimer);
  marketEqualizeTimer=setTimeout(equalizeMarketCardRows,80);
}

function render(){let q=$('search').value.trim().toLowerCase(),t=$('type').value;let a=ITEMS.filter(i=>(!t||i.marketOfferType===t)&&(!q||JSON.stringify(i).toLowerCase().includes(q)));$('items').innerHTML=a.map(card).join('')||'<div class="empty">لا توجد عروض مطابقة حاليًا.</div>';initMarketTitleMarquees();scheduleMarketEqualize()}
function setQty(v){if(!CURRENT)return;let max=Math.max(1,Number(CURRENT.availableQuantity||1)),n=Math.max(1,Math.min(max,Number(v||1)));$('requestQty').value=n;$('qtyNow').textContent=n;updateSummary()}
window.qtyStep=d=>setQty(Number($('requestQty').value||1)+d);
window.openRequest=(id,action)=>{let i=ITEMS.find(x=>x.id===id);if(!i)return;CURRENT=i;$('itemId').value=id;$('action').value=action;$('dlgTitle').textContent=action==='offer'?'تقديم عرض تفاوض':'السلة / طلب شراء';$('offerWrap').hidden=action!=='offer';$('requestQty').value=1;$('requestQty').max=Math.max(1,Number(i.availableQuantity||1));$('qtyUnit').textContent=qtyUnitLabel(i,2);$('qtyNow').textContent='1';$('offerAmount').value='';$('msg').textContent='';$('requestReceipt').hidden=true;$('requestReceipt').innerHTML='';updateSummary();if(typeof $('requestDlg').showModal==='function')$('requestDlg').showModal();else $('requestDlg').setAttribute('open','open')};
function updateSummary(){if(!CURRENT)return;let q=Math.max(1,Number($('requestQty').value||1)),base=totalFor(CURRENT,q),fee=base*Number(SETTINGS.buyerFeePercent||0)/100,total=base+fee;$('requestSummary').innerHTML=`<div class="cart-title">${esc(CURRENT.marketTitle||`${CURRENT.country} — ${CURRENT.denomination}`)}</div><div>الكمية: <b>${q} ${qtyUnitLabel(CURRENT,q)}</b></div><div>سعر ${priceUnitLabel(CURRENT)}: <b>${money(displayPrice(CURRENT))}</b></div><div>قيمة المشتريات: <b>${money(base)}</b></div><div>رسوم المنصة: ${money(fee)} (${Number(SETTINGS.buyerFeePercent||0)}%)</div><div class="cart-total">الإجمالي: ${money(total)}</div>${CURRENT.marketNegotiationEnabled?`<div>التفاوض المسموح حتى ${Number(CURRENT.marketNegotiationPercent||0)}%</div>`:''}`;if($('action').value==='offer'){let min=base*(1-Number(CURRENT.marketNegotiationPercent||0)/100);$('offerAmount').min=min.toFixed(2);$('offerAmount').placeholder='الحد الأدنى '+money(min)}}
$('requestQty').oninput=()=>setQty($('requestQty').value);function closeRequestDlg(){let d=$('requestDlg');if(typeof d.close==='function')d.close();else d.removeAttribute('open')};$('closeDlg').onclick=closeRequestDlg;if($('closeDlgTop'))$('closeDlgTop').onclick=closeRequestDlg;
$('sendRequest').onclick=async()=>{let btn=$('sendRequest'),msg=$('msg');try{btn.disabled=true;msg.textContent='جارٍ إرسال الطلب...';msg.className='';let body={itemId:$('itemId').value,action:$('action').value,name:$('buyerName').value.trim(),phone:$('buyerPhone').value.trim(),quantity:Number($('requestQty').value||1),offeredAmount:Number($('offerAmount').value||0)};let r=await fetch('/api/market/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'}),d=await r.json();if(!r.ok)throw new Error(d.error||'تعذر إرسال الطلب');let rr=d.request||{};$('requestReceipt').hidden=false;$('requestReceipt').innerHTML=`<b>تم تسجيل الطلب بنجاح</b><br>السلعة: ${esc(rr.itemTitle||CURRENT?.marketTitle||'')}<br>المشتري: ${esc(rr.name||body.name)} — ${esc(rr.phone||body.phone)}<br>الكمية: ${Number(rr.quantity||body.quantity)} ${qtyUnitLabel(CURRENT,Number(rr.quantity||body.quantity))}<br>${body.action==='offer'?'عرض التفاوض':'قيمة الشراء'}: ${money(body.action==='offer'?(rr.offeredAmount||body.offeredAmount):(rr.listedAmount||totalFor(CURRENT,body.quantity)))}`;msg.textContent='✅ وصل الطلب إلى الإدارة.';msg.className='ok';setTimeout(()=>load(),300)}catch(e){msg.textContent='⚠️ '+e.message;msg.className='err'}finally{btn.disabled=false}};
async function load(){try{let [m,s]=await Promise.all([get('/api/public/market'),get('/api/settings/public')]);ITEMS=m.items||[];SETTINGS=s||{};render();let hash=decodeURIComponent(location.hash.slice(1));if(hash&&!HASH_DONE){HASH_DONE=true;setTimeout(()=>document.getElementById(hash)?.scrollIntoView({behavior:'smooth',block:'center'}),100)}}catch(e){$('items').innerHTML='<div class="empty">تعذر تحميل السوق. تحقق من تشغيل البرنامج ثم حاول مرة أخرى.</div>'}}
$('search').oninput=render;$('type').onchange=render;load();setInterval(load,12000);


// V3.0: عارض صورة كامل مع تكبير/تدوير/سحب وتوسيط تلقائي
const imageDlg=document.getElementById('imageDlg');
const fullImage=document.getElementById('fullImage');
const imageStage=document.getElementById('imageStage');
const imageToolbar=document.getElementById('imageToolbar');
const IV={scale:1,rot:0,x:0,y:0,drag:false,sx:0,sy:0};
function drawMarketImage(animate=false){if(!fullImage)return;fullImage.style.transition=animate?'transform .22s ease':'none';fullImage.style.transform=`translate(${IV.x}px,${IV.y}px) scale(${IV.scale}) rotate(${IV.rot}deg)`;if(animate)setTimeout(()=>{if(fullImage)fullImage.style.transition='none'},240)}
function centerMarketImage(animate=true){IV.x=0;IV.y=0;drawMarketImage(animate)}
function resetMarketImage(){Object.assign(IV,{scale:1,rot:0,x:0,y:0});drawMarketImage(true)}
document.addEventListener('click',(e)=>{const img=e.target.closest?.('.photo img');if(img&&imageDlg&&fullImage){fullImage.src=img.src;fullImage.alt=img.alt||'صورة المقتنى';Object.assign(IV,{scale:1,rot:0,x:0,y:0,drag:false});drawMarketImage();imageDlg.showModal()}});
imageToolbar?.addEventListener('click',(e)=>{const a=e.target.closest?.('button')?.dataset.imgact;if(!a)return;if(a==='zin')IV.scale=Math.min(5,IV.scale+.25);if(a==='zout')IV.scale=Math.max(.35,IV.scale-.25);if(a==='rl')IV.rot-=90;if(a==='rr')IV.rot+=90;if(a==='center'){centerMarketImage();return}if(a==='reset'){resetMarketImage();return}centerMarketImage(false);drawMarketImage()});
imageStage?.addEventListener('pointerdown',(e)=>{IV.drag=true;IV.sx=e.clientX-IV.x;IV.sy=e.clientY-IV.y;imageStage.setPointerCapture(e.pointerId)});
imageStage?.addEventListener('pointermove',(e)=>{if(!IV.drag)return;IV.x=e.clientX-IV.sx;IV.y=e.clientY-IV.sy;drawMarketImage()});
function finishMarketDrag(){if(!IV.drag)return;IV.drag=false;setTimeout(()=>centerMarketImage(true),140)}
imageStage?.addEventListener('pointerup',finishMarketDrag);imageStage?.addEventListener('pointercancel',finishMarketDrag);
document.getElementById('closeImageDlg')?.addEventListener('click',()=>imageDlg?.close());imageDlg?.addEventListener('click',(e)=>{if(e.target===imageDlg)imageDlg.close()});


window.addToCart=id=>{let i=ITEMS.find(x=>x.id===id);if(!i)return;NawaderVisitor.add({id:i.id,title:i.marketTitle||`${i.country} — ${i.denomination}`,quantity:1,max:Number(i.availableQuantity||1),unitPrice:displayPrice(i),unitLabel:qtyUnitLabel(i,1)});};
function ensureCartPanel(){if(document.getElementById('visitorCartPanel'))return;let p=document.createElement('div');p.id='visitorCartPanel';p.className='visitor-cart-panel';p.hidden=true;p.innerHTML='<div class="visitor-cart-box"><h2>🛒 سلة مشترياتي</h2><div id="visitorCartRows"></div><div id="visitorCartTotal"></div><div class="visitor-cart-actions"><button id="visitorCheckout">إتمام الطلب</button><button id="visitorClear" class="secondary">تفريغ السلة</button><button id="visitorClose" class="secondary">إغلاق</button></div><p id="visitorCartMsg"></p></div>';document.body.appendChild(p);document.getElementById('visitorClose').onclick=()=>p.hidden=true;document.getElementById('visitorClear').onclick=()=>NawaderVisitor.clear();document.getElementById('visitorCheckout').onclick=checkoutCart;window.addEventListener('nawader-cart-change',renderCart)}
function renderCart(){ensureCartPanel();let a=NawaderVisitor.cart(),rows=document.getElementById('visitorCartRows'),total=a.reduce((s,x)=>s+Number(x.unitPrice||0)*Number(x.quantity||1),0);rows.innerHTML=a.map(x=>`<div class="visitor-cart-row"><div><b>${esc(x.title)}</b><div>${Number(x.quantity||1)} × ${money(x.unitPrice)}</div></div><button onclick="NawaderVisitor.remove('${esc(x.id)}')">حذف</button></div>`).join('')||'<p>السلة فارغة.</p>';document.getElementById('visitorCartTotal').innerHTML=a.length?`<h3>قيمة المشتريات: ${money(total)}</h3><small>تضاف رسوم المنصة عند تسجيل الطلب.</small>`:''}
async function checkoutCart(){let v=NawaderVisitor.get(),a=NawaderVisitor.cart(),msg=document.getElementById('visitorCartMsg');if(!v?.verified){location.href='/account?next=/market';return}if(!a.length){msg.textContent='السلة فارغة.';return}try{msg.textContent='جارٍ تسجيل الطلبات...';for(const x of a){let r=await fetch('/api/market/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({itemId:x.id,action:'buy',name:v.name,phone:v.phone,quantity:Number(x.quantity||1),participantId:v.id}),cache:'no-store'}),d=await r.json();if(!r.ok)throw Error(d.error||'تعذر تسجيل أحد الطلبات')}NawaderVisitor.clear();msg.textContent='✅ تم إرسال مشترياتك إلى الإدارة. يمكنك متابعتها من «حسابي».';setTimeout(load,300)}catch(e){msg.textContent='⚠️ '+e.message}}
document.addEventListener('DOMContentLoaded',()=>{ensureCartPanel();document.getElementById('cartOpen')?.addEventListener('click',()=>{renderCart();document.getElementById('visitorCartPanel').hidden=false});let v=NawaderVisitor.get();if(v){if($('buyerName'))$('buyerName').value=v.name||'';if($('buyerPhone'))$('buyerPhone').value=v.phone||''}});


document.addEventListener('load',e=>{
  if(e.target && e.target.matches && e.target.matches('#items .market-photo img')) scheduleMarketEqualize();
},true);
window.addEventListener('resize',scheduleMarketEqualize);
