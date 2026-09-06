from pathlib import Path

p=Path('server.py')
text=p.read_text(encoding='utf-8')
mark='flat-shipping-35-v1'
if mark in text:
    print('already patched')
    raise SystemExit(0)

helper='''\n# flat-shipping-35-v1\nFLAT_SHIPPING_FEE=35.0\n\ndef apply_flat_shipping_for_participant(orders, participant_id):\n    """Apply one fixed 35 SAR shipping charge across all active unpaid orders for the participant.\n    The charge is attached to one order only; sibling orders in the same unpaid batch carry 0 shipping\n    so the customer is never charged 35 per item/order.\n    """\n    pid=str(participant_id or '')\n    active=[o for o in orders if str(o.get('participantId') or '')==pid and str(o.get('paymentStatus') or 'unpaid') not in ('paid','refunded','proof_submitted') and str(o.get('status') or '') in ('new','awaiting_payment','stalled') and not o.get('archived') and not o.get('cancellationRequestedAt')]\n    if not active:\n        return 0\n    active.sort(key=lambda o: str(o.get('created') or ''))\n    primary=active[0]\n    for o in active:\n        fee=FLAT_SHIPPING_FEE if o is primary else 0.0\n        o['shippingFee']=fee\n        o['shippingFeeConfirmed']=True\n        o['shippingFeePolicy']='flat_per_active_batch'\n        o['shippingBatchPrimary']=bool(o is primary)\n        o['total']=round(float(o.get('subtotal') or 0)+float(o.get('buyerFee') or 0)+fee,2)\n        o['updated']=datetime.datetime.now().isoformat()\n    return len(active)\n'''
anchor='def load_live_auctions(): return load_json(LIVE_AUCTIONS,{\'sessions\':[]}).get(\'sessions\',[])\n'
if anchor not in text:
    raise SystemExit('anchor not found')
text=text.replace(anchor,anchor+helper,1)

old="""                    try: fee=max(0,float(d.get('shippingFee') or 0))\n                    except Exception: self.sendj({'error':'مبلغ الشحن غير صالح'},400); return\n                    row['shippingFee']=fee; row['shippingFeeConfirmed']=True\n                    row['total']=float(row.get('subtotal') or 0)+float(row.get('buyerFee') or 0)+fee\n                row['updated']=datetime.datetime.now().isoformat(); save_json(ORDERS,{'orders':rows}); self.sendj({'ok':True,'order':row}); return"""
new="""                    # سياسة الشحن المعتمدة: 35 ريال مرة واحدة فقط لكل دفعة طلبات نشطة لنفس العميل.\n                    # حتى لو اشترى عدة منتجات، لا تتكرر رسوم الشحن على كل طلب.\n                    apply_flat_shipping_for_participant(rows,row.get('participantId'))\n                row['updated']=datetime.datetime.now().isoformat(); save_json(ORDERS,{'orders':rows}); self.sendj({'ok':True,'order':row,'flatShippingFee':FLAT_SHIPPING_FEE}); return"""
if old not in text:
    raise SystemExit('shipping update block not found')
text=text.replace(old,new,1)

# When customer account loads, reconcile legacy unpaid orders so existing orders also follow the policy.
old2="""            ensure_auction_outcomes(); reconcile_direct_market_buy_orders(pid); phone=str(person.get('phone') or '').replace(' ',''); labels="""
new2="""            ensure_auction_outcomes(); reconcile_direct_market_buy_orders(pid);\n            _orders=load_orders();\n            if apply_flat_shipping_for_participant(_orders,pid): save_json(ORDERS,{'orders':_orders})\n            phone=str(person.get('phone') or '').replace(' ',''); labels="""
if old2 not in text:
    raise SystemExit('visitor orders anchor not found')
text=text.replace(old2,new2,1)

p.write_text(text,encoding='utf-8')
print('patched server.py')
