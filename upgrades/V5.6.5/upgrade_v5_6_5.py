#!/usr/bin/env python3
from pathlib import Path
import argparse, datetime, py_compile, shutil, subprocess, sys

V="V5.6.5"
class Stop(RuntimeError): pass

def one(s,a,b,n):
    c=s.count(a)
    if c!=1: raise Stop(f"{n}: anchor count={c}")
    return s.replace(a,b,1)

def patch_server(s):
    a="""def market_listing_physical(item):
    if not (item.get('forMarket') and item.get('marketApproved')): return 0
    listed=max(0,inventory_int(item.get('marketQuantity'),0))
    sold_units=max(0,inventory_int(item.get('marketSoldQuantity'),0))
    return max(0,listed-sold_units)*market_physical_per_unit(item)

"""
    b=a+"""def market_available_units(item,orders=None):
    if not (item.get('forMarket') and item.get('marketApproved')): return 0
    per_unit=max(1,market_physical_per_unit(item))
    listed=max(0,inventory_int(item.get('marketQuantity'),0))
    sold_units=max(0,inventory_int(item.get('marketSoldQuantity'),0))
    _,_,by_source=item_order_quantities(item.get('id'),orders,item)
    reserved=max(0,inventory_int(by_source.get('market',0),0))
    return max(0,listed-sold_units-((reserved+per_unit-1)//per_unit))

"""
    s=one(s,a,b,"helper")
    a="""    _,_,reserved=item_order_quantities(i.get('id'),item=i)
    per_unit=market_physical_per_unit(i)
    reserved_units=(reserved.get('market',0)+per_unit-1)//per_unit
    sold_units=int(i.get('marketSoldQuantity') or 0)
    out['availableQuantity']=max(0,int(i.get('marketQuantity') or i.get('quantity') or 1)-sold_units-reserved_units)
    out['availabilityStatus']='available' if out['availableQuantity']>0 else ('reserved' if reserved_units>0 else 'sold')
"""
    b="""    _,_,by_source=item_order_quantities(i.get('id'),item=i)
    per_unit=max(1,market_physical_per_unit(i))
    reserved=max(0,inventory_int(by_source.get('market',0),0))
    reserved_units=(reserved+per_unit-1)//per_unit
    out['availableQuantity']=market_available_units(i)
    out['availabilityStatus']='available' if out['availableQuantity']>0 else ('reserved' if reserved_units>0 else 'sold')
"""
    s=one(s,a,b,"public availability")
    a="""                for i in load():
                    x=dict(i); x['storeType']=item_store_type(i); rows.append(x)
                self.sendj({'items':rows}); return
"""
    b="""                for i in load():
                    x=dict(i); x['storeType']=item_store_type(i)
                    x['marketAvailableQuantity']=market_available_units(i); rows.append(x)
                self.sendj({'items':rows}); return
"""
    s=one(s,a,b,"admin items availability")
    a="""                old_item=next((i for i in items if str(i.get('id'))==iid),None) if iid else None
                x['storeType']=normalize_store_type(x.get('storeType'),old_item or x)
"""
    b="""                old_item=next((i for i in items if str(i.get('id'))==iid),None) if iid else None
                if old_item and x.get('forMarket') and x.pop('_marketQuantityIsAvailable',False):
                    desired=max(0,inventory_int(x.get('marketQuantity'),0))
                    per_unit=max(1,market_physical_per_unit(x or old_item))
                    _,_,src=item_order_quantities(iid,item=old_item)
                    reserved=max(0,inventory_int(src.get('market',0),0))
                    x['marketQuantity']=max(0,inventory_int(old_item.get('marketSoldQuantity'),0))+((reserved+per_unit-1)//per_unit)+desired
                else: x.pop('_marketQuantityIsAvailable',None)
                x['storeType']=normalize_store_type(x.get('storeType'),old_item or x)
"""
    s=one(s,a,b,"edit quantity normalization")
    a="qty=max(1,int(d.get('quantity') or 1)); avail=max(0,int(item.get('marketQuantity') or item.get('quantity') or 1)-int(item.get('marketSoldQuantity') or 0))"
    if a not in s: raise Stop("purchase availability anchor missing")
    s=s.replace(a,"qty=max(1,int(d.get('quantity') or 1)); avail=market_available_units(item)")
    a="""                _,_,reserved=item_order_quantities(item.get('id'),item=item); per_unit=market_physical_per_unit(item)
                reserved_units=(reserved.get('market',0)+per_unit-1)//per_unit
                avail=max(0,int(item.get('marketQuantity') or item.get('quantity') or 1)-int(item.get('marketSoldQuantity') or 0)-reserved_units)
"""
    if a not in s: raise Stop("reserved availability anchor missing")
    s=s.replace(a,"""                avail=market_available_units(item)
""")
    a="""                item['marketSalePrice']=price; item['availableQuantity']=min(qty,max_qty)
                item['marketNegotiationEnabled']=bool(d.get('marketNegotiationEnabled',item.get('marketNegotiationEnabled',False)))
"""
    b="""                desired=min(qty,max_qty)
                _,_,src=item_order_quantities(iid,item=item); per_unit=max(1,market_physical_per_unit(item))
                reserved=max(0,inventory_int(src.get('market',0),0))
                item['marketSalePrice']=price
                item['marketQuantity']=max(0,inventory_int(item.get('marketSoldQuantity'),0))+((reserved+per_unit-1)//per_unit)+desired
                item['availableQuantity']=desired
                item['marketNegotiationEnabled']=bool(d.get('marketNegotiationEnabled',item.get('marketNegotiationEnabled',False)))
"""
    s=one(s,a,b,"seller market quantity")
    a="""            if p=='/api/shipping-policy':
"""
    b="""            if p=='/api/market/relist':
                if not self.require_admin(api=True): return
                iid=str(d.get('itemId') or '').strip(); desired=max(0,inventory_int(d.get('availableQuantity'),0))
                if not iid or desired<=0: self.sendj({'error':'حدد المقتنى والكمية المراد إتاحتها'},400); return
                with LOCK:
                    items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                    if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                    if item.get('forAuction') and item.get('auctionApproved'): self.sendj({'error':'لا يمكن إعادة كمية السوق أثناء وجود مزاد نشط'},409); return
                    total=inventory_total(item); sold=inventory_int(item.get('soldQuantity'),0); damaged=inventory_int(item.get('damagedQuantity'),0)
                    reserved,returned,src=item_order_quantities(iid,item=item); per_unit=max(1,market_physical_per_unit(item))
                    max_units=max(0,total-sold-damaged-returned-reserved)//per_unit
                    if max_units<=0: self.sendj({'error':'لا توجد كمية حرة يمكن إعادتها للسوق'},409); return
                    desired=min(desired,max_units); market_reserved=max(0,inventory_int(src.get('market',0),0)); sold_units=max(0,inventory_int(item.get('marketSoldQuantity'),0))
                    before=dict(item); item['marketQuantity']=sold_units+((market_reserved+per_unit-1)//per_unit)+desired
                    item['availableQuantity']=desired; item['forMarket']=True; item['marketApproved']=True; item['adminLocation']='market'; item['updated']=int(time.time()*1000); save(items)
                    saved=next((x for x in load() if str(x.get('id'))==iid),None); actual=market_available_units(saved or item)
                    if actual!=desired:
                        rows=load(); idx=next((n for n,x in enumerate(rows) if str(x.get('id'))==iid),None)
                        if idx is not None: rows[idx]=before; save(rows)
                        self.sendj({'error':f'فشل التحقق من الكمية بعد الحفظ: {actual}'},500); return
                    append_operation('إعادة كمية السوق',{'itemId':iid,'availableQuantity':actual})
                    self.sendj({'ok':True,'itemId':iid,'availableQuantity':actual,'maxAvailable':max_units}); return
            if p=='/api/shipping-policy':
"""
    return one(s,a,b,"relist endpoint")

def patch_admin(s):
    a="""  Object.keys(i).forEach((k) => {
    if ($(k) && ![\"front\", \"back\", \"year\", \"country\"].includes(k)) $(k).value = i[k] ?? \"\";
  });
"""
    b=a+"""  if ($(\"marketQuantity\") && i.marketAvailableQuantity != null)
    $(\"marketQuantity\").value = Number(i.marketAvailableQuantity || 0);
"""
    s=one(s,a,b,"edit form availability")
    a="""      marketQuantity: wantsMarket ? n(\"marketQuantity\") || 1 : 0,
      marketSoldQuantity: old?.marketSoldQuantity || 0,
"""
    b="""      marketQuantity: wantsMarket ? n(\"marketQuantity\") || 1 : 0,
      _marketQuantityIsAvailable: !!(old && wantsMarket),
      marketSoldQuantity: old?.marketSoldQuantity || 0,
"""
    s=one(s,a,b,"payload marker")
    a="""  let qty = Number(i.marketQuantity || i.quantity || 1),
    sold = Number(i.marketSoldQuantity || 0),
    left = Math.max(0, qty - sold),
"""
    b="""  let qty = Number(i.marketQuantity || i.quantity || 1),
    sold = Number(i.marketSoldQuantity || 0),
    left = Number(i.marketAvailableQuantity ?? Math.max(0, qty - sold)),
"""
    s=one(s,a,b,"market card availability")
    a="async function renderMarketAdmin(items) {\n"
    b="""window.relistMarketQuantity = async (id) => {
  try {
    const rows=await all(), item=rows.find(x=>String(x.id)===String(id)); if(!item)throw Error(\"المقتنى غير موجود\");
    const current=Number(item.marketAvailableQuantity??0), raw=prompt(`الكمية المتاحة حاليًا: ${current}\\nأدخل الكمية التي تريد إتاحتها الآن:`,String(Math.max(1,current||1)));
    if(raw===null)return; const desired=Math.max(1,Math.floor(Number(raw))); if(!Number.isFinite(desired))throw Error(\"أدخل كمية صحيحة\");
    const r=await api(\"/api/market/relist\",{method:\"POST\",body:JSON.stringify({itemId:id,availableQuantity:desired})});
    lastDataToken=\"\"; await refresh(true); await renderMarketAdmin(); toast(`تمت إعادة الكمية للسوق: ${Number(r.availableQuantity||desired)}`);
  } catch(e) { alert(e.message||\"تعذر إعادة الكمية للسوق\"); }
};
async function renderMarketAdmin(items) {
"""
    s=one(s,a,b,"relist action")
    a="""<button onclick=\"editItem('${i.id}')\">تعديل</button>${archiveButton(i.id)}${adminMoveButtons(i,\"market\")}"""
    b="""<button onclick=\"editItem('${i.id}')\">تعديل</button><button class=\"ghost\" onclick=\"relistMarketQuantity('${i.id}')\">↻ إعادة الكمية</button>${archiveButton(i.id)}${adminMoveButtons(i,\"market\")}"""
    return one(s,a,b,"relist button")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--check",action="store_true"); p.add_argument("--target"); a=p.parse_args()
    root=Path(a.target).resolve() if a.target else Path(__file__).resolve().parents[2]
    sp=root/"server.py"; ap=root/"admin/app.js"
    if not sp.is_file() or not ap.is_file(): raise Stop("server.py/admin/app.js not found")
    os=sp.read_text(encoding="utf-8"); oa=ap.read_text(encoding="utf-8")
    ns=patch_server(os); na=patch_admin(oa)
    if a.check: print(V+": anchors OK; no files changed"); return
    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); b=root/f"backup_manual_{V.replace('.','_')}_{stamp}"; (b/"admin").mkdir(parents=True)
    shutil.copy2(sp,b/"server.py"); shutil.copy2(ap,b/"admin/app.js")
    try:
        sp.write_text(ns,encoding="utf-8"); ap.write_text(na,encoding="utf-8"); py_compile.compile(str(sp),doraise=True)
        if shutil.which("node"): subprocess.run(["node","--check",str(ap)],check=True)
    except Exception:
        shutil.copy2(b/"server.py",sp); shutil.copy2(b/"admin/app.js",ap); raise
    print(V+" installed"); print("backup:",b); print("changed: server.py, admin/app.js"); print("live broadcast/auction untouched")

if __name__=="__main__":
    try: main()
    except Stop as e: print("UPGRADE STOPPED:",e,file=sys.stderr); raise SystemExit(2)
