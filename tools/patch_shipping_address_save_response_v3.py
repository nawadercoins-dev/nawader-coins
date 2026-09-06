from pathlib import Path
p=Path('server.py')
s=p.read_text(encoding='utf-8')
marker='# shipping-address-save-response-v3'
if marker in s:
    print('already patched')
    raise SystemExit(0)
old="row['updated']=datetime.datetime.now().isoformat(); save_json(ORDERS,{'orders':rows}); self.sendj({'ok':True,'order':row,'flatShippingFee':FLAT_SHIPPING_FEE}); return"
new="""# shipping-address-save-response-v3\n                row['updated']=datetime.datetime.now().isoformat(); save_json(ORDERS,{'orders':rows}); self.sendj({'ok':True,'order':row,'flatShippingFee':flat_shipping_fee()}); return"""
if old not in s:
    raise RuntimeError('shipping response marker not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched shipping address save response v3')
