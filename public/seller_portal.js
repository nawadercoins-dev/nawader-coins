(()=>{
'use strict';
const $=id=>document.getElementById(id), esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const money=value=>Number(value||0).toLocaleString('ar-SA',{maximumFractionDigits:2})+' ر.س';
const date=value=>{try{return new Intl.DateTimeFormat('ar-SA',{dateStyle:'medium'}).format(new Date(value))}catch{return ''}};
let state={data:null,orderFilter:'all',shipmentFilter:'all',inventoryFilter:'all',storeFilter:(()=>{try{return ['coins','collectibles','all'].includes(localStorage.getItem('sellerStoreFilter'))?localStorage.getItem('sellerStoreFilter'):'coins'}catch{return 'coins'}})(),query:'',shippingOrder:null};
const statusClass=status=>esc(status||'');
function empty(message){return `<div class="empty-inline">${esc(message)}</div>`}
const storeLabel=s=>s==='collectibles'?'نوادر المقتنيات':s==='coins'?'نوادر العملات':'كل دار المقتنيات';
const storeMatch=x=>state.storeFilter==='all'||String(x?.storeType||'coins')===state.storeFilter;
const visibleOrders=()=> (state.data?.orders||[]).filter(storeMatch);
const visibleInventory=()=> (state.data?.inventory||[]).filter(storeMatch);
const storeBadge=s=>`<span class="seller-store-badge ${s==='collectibles'?'collectibles':'coins'}">${s==='collectibles'?'🏺 مقتنيات':'🪙 عملات'}</span>`;
function orderMatches(order,filter){
 if(filter==='all')return true;
 if(filter==='work')return ['paid','preparing','ready_to_ship','shipped','received'].includes(order.status);
 if(filter==='completed')return ['completed','received'].includes(order.status);
 return order.status===filter;
}
function shipmentOrders(){return visibleOrders().filter(x=>['preparing','ready_to_ship','shipped','received','completed'].includes(x.status))}
function orderCard(order,shipment=false){
 const line=(order.items||[])[0]||{}, canManage=!!state.data?.permissions?.ordersManage;
 let action='';
 if(canManage&&order.status==='paid') action=`<button data-status-order="${esc(order.id)}" data-next-status="preparing">بدء التجهيز</button>`;
 if(canManage&&order.status==='preparing') action=`<button data-shipping-order="${esc(order.id)}">تجهيز الشحنة</button>`;
 if(canManage&&order.status==='ready_to_ship') action=`<button data-shipping-order="${esc(order.id)}">اعتماد تم الشحن</button>`;
 const shipInfo=shipment?`<div class="order-actions">${order.shippingCompany?`<span class="secondary">شركة الشحن: ${esc(order.shippingCompany)}</span>`:''}${order.trackingNumber?`<span class="secondary">التتبع: ${esc(order.trackingNumber)}</span>`:''}</div>`:'';
 return `<article class="order-card" data-order-id="${esc(order.id)}"><div class="order-top"><div><h3>${storeBadge(order.storeType)} ${esc(order.customerName||'مشتري')}</h3><div class="order-number">${esc(order.orderNumber||order.id)}</div><div class="order-date">${date(order.created)}</div></div><span class="status-chip ${statusClass(order.status)}">${esc(order.statusLabel||order.status)}</span></div><div class="order-body">${line.image?`<img class="order-img" src="${esc(line.image)}" alt="">`:'<div class="order-img"></div>'}<div><b>${esc(line.title||'مقتنى')}</b><small>الكمية: ${Number(line.quantity||1).toLocaleString('ar-SA')}</small></div><div class="order-money">${money(order.subtotal)}</div></div>${shipInfo}${action?`<div class="order-actions">${action}</div>`:''}</article>`;
}
function renderOrders(){
 const list=visibleOrders().filter(x=>orderMatches(x,state.orderFilter)).filter(x=>!state.query||`${x.orderNumber} ${(x.items||[]).map(y=>y.title).join(' ')}`.toLowerCase().includes(state.query));
 $('ordersList').innerHTML=list.map(x=>orderCard(x)).join('')||empty('لا توجد طلبات مطابقة.');
}
function renderShipments(){
 const list=shipmentOrders().filter(x=>state.shipmentFilter==='all'||(state.shipmentFilter==='completed'?['received','completed'].includes(x.status):x.status===state.shipmentFilter));
 $('shipmentsList').innerHTML=list.map(x=>orderCard(x,true)).join('')||empty('لا توجد شحنات في هذه الحالة.'); $('shipmentsTotal').textContent=shipmentOrders().length.toLocaleString('ar-SA');
}
function renderInventory(){
 const list=visibleInventory().filter(x=>state.inventoryFilter==='all'||(state.inventoryFilter==='market'?x.forMarket:(state.inventoryFilter==='auction'?x.forAuction:(!x.forMarket&&!x.forAuction))));
 $('inventoryList').innerHTML=list.map(x=>`<article class="inventory-card">${x.image?`<img src="${esc(x.image)}" alt="${esc(x.title)}" loading="lazy">`:'<div class="inventory-placeholder">🪙</div>'}<div class="inventory-info"><h3>${storeBadge(x.storeType)} ${esc(x.title)}</h3><div class="badge-row">${x.forMarket?`<span class="mini-badge ${x.marketApproved?'on':''}">${x.marketApproved?'في السوق':'السوق غير نشط'}</span>`:''}${x.forAuction?`<span class="mini-badge ${x.auctionApproved?'on':''}">${x.auctionApproved?'مزاد نشط':'المزاد غير نشط'}</span>`:''}${!x.forMarket&&!x.forAuction?'<span class="mini-badge">غير معروض</span>':''}</div><p>المتاح: ${Number(x.availableQuantity||0).toLocaleString('ar-SA')}${x.marketPrice?` · ${money(x.marketPrice)}`:''}</p></div></article>`).join('')||empty('لا توجد مقتنيات في هذا القسم.');
}
function renderFinance(){
 const paid=visibleOrders().filter(x=>x.paymentStatus==='paid'&&!['cancelled','returned'].includes(x.status));
 $('paidOrdersCount').textContent=paid.length.toLocaleString('ar-SA'); $('financeList').innerHTML=paid.map(x=>`<article class="order-card"><div class="order-top"><div><h3>${esc(x.orderNumber)}</h3><div class="order-date">${date(x.created)}</div></div><span class="status-chip paid">مسدد</span></div><div class="order-body"><div class="order-img"></div><div><b>${esc(((x.items||[])[0]||{}).title||'مقتنى')}</b><small>عمولة البائع: ${money(x.sellerFee)}</small></div><div class="order-money">صافي ${money(x.sellerNet)}</div></div></article>`).join('')||empty('لا توجد مستحقات مسددة حتى الآن.');
}
function fill(data){
 state.data=data; const seller=data.seller||{};
 $('sellerName').textContent=seller.name||'بائع'; $('sellerCountry').textContent=[seller.flag,seller.country,seller.verified?'✓ موثق':''].filter(Boolean).join('  ');
 const avatar=$('sellerAvatar'); if(seller.avatarUrl){avatar.style.backgroundImage=`url("${String(seller.avatarUrl).replace(/["\\]/g,'')}")`;avatar.textContent=''}else avatar.textContent=(seller.name||'ن').trim().charAt(0);
 document.querySelectorAll('[data-seller-store]').forEach(b=>b.classList.toggle('active',b.dataset.sellerStore===state.storeFilter));
 const inventory=visibleInventory(), orders=visibleOrders(), paid=orders.filter(x=>x.paymentStatus==='paid'&&!['cancelled','returned'].includes(x.status)), open=orders.filter(x=>['new','awaiting_payment','paid','preparing','ready_to_ship','shipped','received','stalled'].includes(x.status));
 const paidGross=paid.reduce((sum,x)=>sum+Number(x.subtotal||0),0), sellerNet=paid.reduce((sum,x)=>sum+Number(x.sellerNet||0),0), pending=orders.filter(x=>x.paymentStatus!=='paid'&&!['cancelled','returned','completed'].includes(x.status)).length, ready=orders.filter(x=>x.status==='ready_to_ship').length, shipped=orders.filter(x=>x.status==='shipped').length;
 [['paidGross',money(paidGross)],['sellerNet',money(sellerNet)],['financeNet',money(sellerNet)],['openOrders',open.length.toLocaleString('ar-SA')],['readyToShip',ready.toLocaleString('ar-SA')],['inventoryCount',inventory.length.toLocaleString('ar-SA')],['marketActive',inventory.filter(x=>x.forMarket&&x.marketApproved).length.toLocaleString('ar-SA')],['auctionActive',inventory.filter(x=>x.forAuction&&x.auctionApproved).length.toLocaleString('ar-SA')],['ordersTotal',orders.length.toLocaleString('ar-SA')]].forEach(([id,value])=>$(id).textContent=value);
 $('pendingPayments').textContent=`${pending.toLocaleString('ar-SA')} بانتظار السداد`; $('shippedCount').textContent=`${shipped.toLocaleString('ar-SA')} تم شحنها`;
 $('recentOrders').innerHTML=orders.slice(0,3).map(x=>orderCard(x)).join('')||empty('لا توجد طلبات في '+storeLabel(state.storeFilter)+'.');
 const requests=(data.requests||[]).filter(storeMatch), offers=requests.filter(x=>x.action==='offer'&&!['completed','cancelled','rejected'].includes(String(x.status||'pending'))).length;
 const alerts=[]; if(pending)alerts.push(`${pending} طلب بانتظار اعتماد السداد`); if(ready)alerts.push(`${ready} طلب جاهز للشحن`); if(offers)alerts.push(`${offers} عرض تفاوض يحتاج متابعة`); if(!alerts.length)alerts.push('لا توجد إجراءات عاجلة الآن'); $('operationAlerts').innerHTML=alerts.map((x,i)=>`<div class="alert ${!i&&!pending&&!ready&&!offers?'good':''}">${esc(x)}</div>`).join('');
 $('ordersBadge').textContent=open.length;$('ordersBadge').hidden=!open.length;$('shippingBadge').textContent=ready;$('shippingBadge').hidden=!ready;
 $('liveStudioLink').hidden=!data.permissions?.liveBroadcast; renderOrders();renderShipments();renderInventory();renderFinance();
}
function showView(name){document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.dataset.view===name));document.querySelectorAll('.seller-bottom [data-go]').forEach(x=>x.classList.toggle('active',x.dataset.go===name));scrollTo({top:0,behavior:'smooth'});history.replaceState(null,'','#'+name)}
async function load(){
 const visitor=NawaderVisitor.get(); if(!visitor?.verified){$('loginGate').hidden=false;return}
 $('sellerApp').hidden=false;$('sellerNav').hidden=false;
 try{const response=await fetch('/api/seller/dashboard?participantId='+encodeURIComponent(visitor.id),{cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(data.error||'تعذر تحميل مركز البائع');fill(data)}catch(error){$('sellerApp').innerHTML=empty(error.message)}
}
async function updateStatus(order,status,shipping={}){
 const button=$('saveShipping');if(button)button.disabled=true;
 try{const response=await fetch('/api/seller/order/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:order.id,status,...shipping})});const data=await response.json();if(!response.ok)throw Error(data.error||'تعذر تحديث الطلب');if($('shippingDialog').open)$('shippingDialog').close();window.nawaderToast?.('تم تحديث الطلب بنجاح');await load()}catch(error){alert(error.message)}finally{if(button)button.disabled=false}
}
document.addEventListener('click',event=>{
 const store=event.target.closest('[data-seller-store]');if(store){state.storeFilter=store.dataset.sellerStore;try{localStorage.setItem('sellerStoreFilter',state.storeFilter)}catch{};fill(state.data||{});return}
 const go=event.target.closest('[data-go]');if(go){showView(go.dataset.go);return}
 if(event.target.closest('[data-refresh]')){load();return}
 const status=event.target.closest('[data-status-order]');if(status){const order=(state.data?.orders||[]).find(x=>String(x.id)===status.dataset.statusOrder);if(order)updateStatus(order,status.dataset.nextStatus);return}
 const shipping=event.target.closest('[data-shipping-order]');if(shipping){const order=(state.data?.orders||[]).find(x=>String(x.id)===shipping.dataset.shippingOrder);if(!order)return;state.shippingOrder=order;$('shippingOrderName').textContent=`${order.orderNumber} — ${order.statusLabel}`;$('shippingCompany').value=order.shippingCompany||'';$('trackingNumber').value=order.trackingNumber||'';$('trackingNumber').required=order.status==='ready_to_ship';$('shippingDialog').showModal()}
});
function bindFilters(id,key,render){$(id).addEventListener('click',event=>{const button=event.target.closest('[data-filter]');if(!button)return;$(id).querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===button));state[key]=button.dataset.filter;render()})}
bindFilters('orderFilters','orderFilter',renderOrders);bindFilters('shipmentFilters','shipmentFilter',renderShipments);bindFilters('inventoryFilters','inventoryFilter',renderInventory);
$('orderSearch').addEventListener('input',event=>{state.query=event.target.value.trim().toLowerCase();renderOrders()});
$('saveShipping').addEventListener('click',()=>{const order=state.shippingOrder;if(!order)return;const next=order.status==='preparing'?'ready_to_ship':'shipped';updateStatus(order,next,{shippingCompany:$('shippingCompany').value.trim(),trackingNumber:$('trackingNumber').value.trim()})});
const initial=location.hash.slice(1);showView(['home','orders','shipments','finance','inventory','more'].includes(initial)?initial:'home');load();
})();
