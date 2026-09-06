from pathlib import Path

p=Path('admin/app.js')
s=p.read_text(encoding='utf-8')
marker='// shipping-final-send-v1'
if marker not in s:
    s += r'''

// shipping-final-send-v1
// In the preparing stage, the shipping company + tracking entry is the final operational step.
// The existing ready_to_ship transition is performed internally, then the order is immediately marked shipped.
(function installFinalShippingSendFlow(){
  const originalOrderStatus = window.orderStatus;
  if (typeof originalOrderStatus !== 'function') return;

  function syncSendButtons(root=document){
    try {
      root.querySelectorAll('button[onclick*="ready_to_ship"]').forEach(btn=>{
        btn.textContent='📦 إرسال الطلب';
        btn.title='يحفظ شركة الشحن ورقم التتبع ثم يسجل الطلب تم الشحن مباشرة';
      });
    } catch(_) {}
  }

  window.shipOrderNow = async function(id){
    const company = String(document.getElementById('shipco-'+id)?.value || '').trim();
    const tracking = String(document.getElementById('track-'+id)?.value || '').trim();
    if(!company){
      window.toast?.('حدد شركة الشحن أولًا، ثم اضغط إرسال الطلب.');
      const el=document.getElementById('shipco-'+id); el?.focus(); el?.scrollIntoView?.({behavior:'smooth',block:'center'});
      return;
    }
    if(!tracking){
      window.toast?.('أدخل رقم التتبع أو مرجع الشحنة، ثم اضغط إرسال الطلب.');
      const el=document.getElementById('track-'+id); el?.focus(); el?.scrollIntoView?.({behavior:'smooth',block:'center'});
      return;
    }
    try{
      // Save the final shipping identity first. Do not change a paid order's shipping fee here.
      await api('/api/order/shipping',{
        method:'POST',
        body:JSON.stringify({id,shippingCompany:company,trackingNumber:tracking})
      });
      // Preserve the server lifecycle, but make it one user action with one final confirmation.
      await api('/api/order/update',{method:'POST',body:JSON.stringify({id,status:'ready_to_ship',note:'تم اعتماد بيانات شركة الشحن تلقائيًا عند الإرسال'})});
      await api('/api/order/update',{method:'POST',body:JSON.stringify({id,status:'shipped',note:'تم إرسال الطلب وتسجيل بيانات الشحن'})});
      window.toast?.('✅ تم إرسال الطلب وتسجيل شركة الشحن ورقم التتبع بنجاح.',4200);
      await renderOrders();
      syncSendButtons();
    }catch(e){
      window.toast?.(e?.message || 'تعذر إرسال الطلب. راجع بيانات الشحن.',5000);
    }
  };

  window.orderStatus = async function(id,status){
    if(status==='ready_to_ship') return window.shipOrderNow(id);
    return originalOrderStatus(id,status);
  };

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>syncSendButtons());
  else syncSendButtons();
  try{new MutationObserver(()=>syncSendButtons()).observe(document.body,{childList:true,subtree:true});}catch(_){}
})();
'''
    p.write_text(s,encoding='utf-8')
print('patched shipping final send flow')
