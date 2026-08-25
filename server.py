# V4.6.6 — platform-owner seller country: admin ownerCountry field, default Saudi Arabia, public flag fallback.
# V4.6.5 — seller flag repair: normalize country and sync duplicate participant identities by phone.
# V4.6.4 — approved collectible lifecycle, owner records/actions, destination routing, clean activity feed.
# V4.6.3 — public seller identity uses flag icon on cards; country retained in API for shipping/filtering.
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, os, threading, shutil, datetime, atexit, re, secrets, mimetypes, socket, webbrowser, time, io, hashlib, hmac, zipfile, tempfile, subprocess, glob

ROOT=os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR=os.path.join(ROOT,'admin')
PUBLIC_DIR=os.path.join(ROOT,'public')
SHARED_DIR=os.path.join(ROOT,'shared')
# في Render اربط قرصًا دائمًا بالمسار /var/data. محليًا يبقى الحفظ بجانب البرنامج.
DATA_ROOT=os.path.abspath(os.environ.get('DATA_DIR') or ROOT)
os.makedirs(DATA_ROOT,exist_ok=True)
DATA=os.path.join(DATA_ROOT,'khazina_shared_data.json')
PEOPLE=os.path.join(DATA_ROOT,'auction_participants.json')
BIDS=os.path.join(DATA_ROOT,'auction_bids.json')
NEGOTIATIONS=os.path.join(DATA_ROOT,'auction_negotiations.json')
MARKET_REQUESTS=os.path.join(DATA_ROOT,'market_requests.json')
SUBSCRIPTIONS=os.path.join(DATA_ROOT,'subscription_ledger.json')
SAVE_AUDIT=os.path.join(DATA_ROOT,'save_audit.json')
SETTINGS=os.path.join(DATA_ROOT,'platform_settings.json')
NOTIFICATIONS=os.path.join(DATA_ROOT,'notifications.json')
AUCTION_DUES=os.path.join(DATA_ROOT,'auction_dues.json')
USER_PERMISSIONS=os.path.join(DATA_ROOT,'user_permissions.json')
OPERATIONS_LOG=os.path.join(DATA_ROOT,'operations_log.json')
ORDERS=os.path.join(DATA_ROOT,'orders_shipping.json')
COLLECTIBLE_SUBMISSIONS=os.path.join(DATA_ROOT,'collectible_submissions.json')
AUTH_FILE=os.path.join(DATA_ROOT,'admin_auth.json')
ADMIN_CREDENTIALS=os.path.join(DATA_ROOT,'بيانات_دخول_الإدارة.txt')
ADMIN_SESSIONS={}
SESSION_TTL_SECONDS=12*60*60
LOCK=threading.Lock()
BACKUP_DIR=os.path.join(DATA_ROOT,'backups')
UPLOAD_DIR=os.path.join(DATA_ROOT,'uploads')
os.makedirs(BACKUP_DIR,exist_ok=True)
os.makedirs(UPLOAD_DIR,exist_ok=True)

# تهيئة القرص في أول تشغيل فقط من الملفات المرفقة مع المشروع، دون استبدال أي بيانات دائمة.
if DATA_ROOT != ROOT:
    for _dst in (DATA,PEOPLE,BIDS,NEGOTIATIONS,MARKET_REQUESTS,SUBSCRIPTIONS,SAVE_AUDIT,SETTINGS,NOTIFICATIONS,AUCTION_DUES,USER_PERMISSIONS,OPERATIONS_LOG,ORDERS,COLLECTIBLE_SUBMISSIONS,AUTH_FILE):
        _src=os.path.join(ROOT,os.path.basename(_dst))
        if not os.path.exists(_dst) and os.path.isfile(_src):
            shutil.copy2(_src,_dst)
    _seed_uploads=os.path.join(ROOT,'uploads')
    if os.path.isdir(_seed_uploads) and not os.listdir(UPLOAD_DIR):
        for _name in os.listdir(_seed_uploads):
            _src=os.path.join(_seed_uploads,_name); _dst=os.path.join(UPLOAD_DIR,_name)
            if os.path.isfile(_src): shutil.copy2(_src,_dst)

def backup_data(reason='auto'):
    if not os.path.exists(DATA): return None
    try:
        os.makedirs(BACKUP_DIR,exist_ok=True)
        stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        dst=os.path.join(BACKUP_DIR,f'khazina_{reason}_{stamp}.json')
        shutil.copy2(DATA,dst)
        files=sorted((os.path.join(BACKUP_DIR,x) for x in os.listdir(BACKUP_DIR) if x.endswith('.json')), key=os.path.getmtime, reverse=True)
        for old in files[30:]:
            try: os.remove(old)
            except OSError: pass
        return dst
    except Exception as e:
        print('Backup warning:',e); return None

def load_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path,'r',encoding='utf-8') as f: return json.load(f)
    except Exception: return default

def save_json(path,obj):
    tmp=path+'.tmp'
    with open(tmp,'w',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def load(): return load_json(DATA,{'items':[]}).get('items',[])
def load_people(): return load_json(PEOPLE,{'participants':[]}).get('participants',[])
def load_bids(): return load_json(BIDS,{'bids':[]}).get('bids',[])
def load_negotiations(): return load_json(NEGOTIATIONS,{'negotiations':[]}).get('negotiations',[])
def load_market_requests(): return load_json(MARKET_REQUESTS,{'requests':[]}).get('requests',[])
def load_subscriptions(): return load_json(SUBSCRIPTIONS,{'subscriptions':[]}).get('subscriptions',[])
def load_notifications(): return load_json(NOTIFICATIONS,{'notifications':[]}).get('notifications',[])
def load_auction_dues(): return load_json(AUCTION_DUES,{'dues':[]}).get('dues',[])
def load_user_permissions(): return load_json(USER_PERMISSIONS,{'users':{}}).get('users',{})
def load_operations_log(): return load_json(OPERATIONS_LOG,{'events':[]}).get('events',[])
def load_orders(): return load_json(ORDERS,{'orders':[]}).get('orders',[])
def load_collectible_submissions(): return load_json(COLLECTIBLE_SUBMISSIONS,{'submissions':[]}).get('submissions',[])
def load_save_audit(): return load_json(SAVE_AUDIT,{'events':[]}).get('events',[])
def append_save_audit(event):
    rows=load_save_audit(); rows.append(event); rows=rows[-500:]; save_json(SAVE_AUDIT,{'events':rows})
def append_operation(action, details=None, actor='الإدارة'):
    rows=load_operations_log(); rows.append({'id':'op-'+secrets.token_hex(6),'action':str(action),'details':details or {},'actor':actor,'created':datetime.datetime.now().isoformat()}); rows=rows[-2000:]; save_json(OPERATIONS_LOG,{'events':rows})

def add_notification(recipient_type, recipient_id, category, title, message, item_id='', action_url=''):
    rows=load_notifications()
    row={'id':'nt-'+secrets.token_hex(6),'recipientType':recipient_type,'recipientId':str(recipient_id or ''),'category':category,'title':title,'message':message,'itemId':str(item_id or ''),'actionUrl':action_url,'read':False,'created':datetime.datetime.now().isoformat()}
    rows.append(row); rows=rows[-4000:]; save_json(NOTIFICATIONS,{'notifications':rows}); return row

APPROVAL_STATUSES=('new','preliminary','final','suspended','stopped','cancelled')
APPROVAL_LABELS={'new':'طلب جديد','preliminary':'اعتماد مبدئي','final':'اعتماد نهائي','suspended':'معلّق','stopped':'موقوف','cancelled':'ملغى'}

def participant_approval_status(person):
    status=str((person or {}).get('approvalStatus') or '').strip().lower()
    if status in APPROVAL_STATUSES: return status
    if (person or {}).get('archived'): return 'cancelled'
    if (person or {}).get('blocked'): return 'stopped'
    if (person or {}).get('approved') and (person or {}).get('verified'): return 'final'
    if (person or {}).get('verified'): return 'preliminary'
    return 'new'

def apply_approval_status(person,status):
    status=status if status in APPROVAL_STATUSES else 'new'; person['approvalStatus']=status
    person['verified']=status!='new'; person['approved']=status=='final'; person['blocked']=status in ('stopped','cancelled'); person['archived']=status=='cancelled'
    if status!='cancelled': person['archivedAt']=''; person['archiveReason']=''
    return person

def participant_can_access(person): return participant_approval_status(person) in ('preliminary','final','suspended','stopped')
def participant_can_transact(person): return participant_approval_status(person)=='final'
def participant_public(person):
    safe={k:v for k,v in (person or {}).items() if k not in ('otp','otpExpires','otpAttempts')}; status=participant_approval_status(person)
    safe['approvalStatus']=status; safe['approvalLabel']=APPROVAL_LABELS[status]; return safe

SELLER_COUNTRY_FLAGS={
    'السعودية':'🇸🇦','المملكة العربية السعودية':'🇸🇦',
    'الكويت':'🇰🇼','البحرين':'🇧🇭','قطر':'🇶🇦',
    'عمان':'🇴🇲','عُمان':'🇴🇲','سلطنة عمان':'🇴🇲',
    'الامارات':'🇦🇪','الإمارات':'🇦🇪','الإمارات العربية المتحدة':'🇦🇪',
    'مصر':'🇪🇬','الأردن':'🇯🇴','الاردن':'🇯🇴','لبنان':'🇱🇧','العراق':'🇮🇶',
    'اليمن':'🇾🇪','سوريا':'🇸🇾','ألمانيا':'🇩🇪','المانيا':'🇩🇪',
    'بريطانيا':'🇬🇧','المملكة المتحدة':'🇬🇧',
    'الولايات المتحدة':'🇺🇸','الولايات المتحدة الأمريكية':'🇺🇸'
}

def _norm_phone(value):
    digits=''.join(ch for ch in str(value or '') if ch.isdigit())
    # توحيد السعودية 05xxxxxxxx و 9665xxxxxxxx
    if digits.startswith('966') and len(digits)>=12:
        digits='0'+digits[3:]
    return digits

def _norm_country(value):
    c=str(value or '').strip()
    c=c.replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ى','ي').replace('ة','ه').replace('ُ','')
    aliases={
        'السعوديه':'السعودية','المملكه العربيه السعوديه':'المملكة العربية السعودية',
        'عمان':'عمان','سلطنه عمان':'سلطنة عمان',
        'الامارات':'الإمارات','الامارات العربيه المتحده':'الإمارات العربية المتحدة',
        'الاردن':'الأردن','المانيا':'ألمانيا',
        'الولايات المتحده':'الولايات المتحدة','الولايات المتحده الامريكيه':'الولايات المتحدة الأمريكية'
    }
    return aliases.get(c,c)

def public_seller_identity(item):
    """هوية عامة لصاحب المعروض، مع إصلاح تلقائي للحسابات المكررة القديمة."""
    pid=str((item or {}).get('ownerParticipantId') or '').strip()
    people=load_people()
    person=next((x for x in people if str(x.get('id') or '')==pid),None) if pid else None

    # بعض المقتنيات القديمة مرتبطة بسجل مكرر لا يحتوي دولة/اسم ظاهر.
    # ابحث عن سجل آخر لنفس الجوال واستعمل أحدث بيانات الهوية المتاحة.
    owner_phone=str((item or {}).get('ownerPhone') or (person or {}).get('phone') or '')
    phone_key=_norm_phone(owner_phone)
    siblings=[x for x in people if phone_key and _norm_phone(x.get('phone'))==phone_key]
    if siblings:
        richest=max(
            siblings,
            key=lambda x: (
                bool(str(x.get('country') or '').strip()),
                bool(str(x.get('alias') or x.get('displayName') or '').strip()),
                str(x.get('profileUpdatedAt') or x.get('lastSeen') or x.get('created') or '')
            )
        )
        if not person:
            person=richest
        else:
            # لا نستبدل هوية الحساب الأساسية، فقط نعوض الحقول الناقصة.
            person=dict(person)
            for k in ('country','alias','displayName','avatarUrl'):
                if not str(person.get(k) or '').strip() and str(richest.get(k) or '').strip():
                    person[k]=richest.get(k)

    display=str((person or {}).get('alias') or (person or {}).get('displayName') or (person or {}).get('name') or (item or {}).get('ownerName') or 'صاحب المقتنى').strip()
    country=_norm_country((person or {}).get('country') or (item or {}).get('ownerCountry') or ('المملكة العربية السعودية' if not pid else ''))
    flag=SELLER_COUNTRY_FLAGS.get(country)
    if not flag:
        # محاولة ثانية بالقيمة الأصلية قبل التطبيع.
        flag=SELLER_COUNTRY_FLAGS.get(str((person or {}).get('country') or (item or {}).get('ownerCountry') or ('المملكة العربية السعودية' if not pid else '')).strip(),'🌐')

    return {
        'sellerId':pid or str((person or {}).get('id') or ''),
        'sellerName':display,
        'sellerCountry':country,
        'sellerFlag':flag,
        'sellerAvatar':str((person or {}).get('avatarUrl') or '').strip(),
        'sellerVerified':bool((person or {}).get('verified') or (person or {}).get('approved')),
    }

def participant_permissions(pid):
    defaults={'sellerEndedAuctions':False,'sellerMarket':False,'marketSupervision':False,'auctionSupervision':False,'ordersView':False,'ordersManage':False}
    x=load_user_permissions().get(str(pid),{})
    defaults.update(x if isinstance(x,dict) else {})
    return defaults

def item_title(i):
    return str(i.get('marketTitle') or ((i.get('country') or '')+' — '+(i.get('denomination') or ''))).strip(' —') or 'مقتنى'


ORDER_FLOW=['new','awaiting_payment','paid','preparing','ready_to_ship','shipped','received','completed']
ORDER_EXCEPTION={'stalled','cancelled','returned'}
OPEN_ORDER_STATUSES={'new','awaiting_payment','paid','preparing','ready_to_ship','shipped','received','stalled'}

def inventory_int(value, default=0):
    try: return max(0,int(float(value)))
    except Exception: return max(0,int(default))

def submission_inventory_values(source):
    """Normalize submission classification and physical quantity."""
    collection_class=str(source.get('collectionClass') or 'single').strip().lower()
    if collection_class not in ('single','set'): collection_class='single'
    unit_type=str(source.get('inventoryUnitType') or ('set' if collection_class=='set' else 'piece')).strip().lower()
    if unit_type not in ('piece','coin','set','bundle','strap','lot'): unit_type='piece'
    if collection_class=='set': unit_type='set'
    unit_count=max(1,inventory_int(source.get('inventoryUnitCount'),1))
    default_pieces=100 if unit_type=='strap' else (2 if unit_type=='set' else 1)
    pieces_per_unit=max(1,inventory_int(source.get('piecesPerUnit'),default_pieces))
    if unit_type=='strap' and source.get('piecesPerUnit') in (None,''): pieces_per_unit=100
    is_graded=bool(source.get('isGraded'))
    classification='set' if collection_class=='set' else ('graded' if is_graded else 'ungraded')
    return {'collectionClass':collection_class,'inventoryClassification':classification,
            'isSet':collection_class=='set','isGraded':is_graded,
            'inventoryUnitType':unit_type,'inventoryUnitCount':unit_count,
            'piecesPerUnit':pieces_per_unit,
            'setPieces':pieces_per_unit if collection_class=='set' else 0,
            'quantity':unit_count*pieces_per_unit}

def inventory_unit_count(item):
    if item.get('inventoryUnitCount') not in (None,''): return max(1,inventory_int(item.get('inventoryUnitCount'),1))
    return max(1,inventory_int(item.get('quantity'),1))

def inventory_pieces_per_unit(item):
    return max(1,inventory_int(item.get('piecesPerUnit'),1))

def inventory_total(item):
    # السجلات الجديدة تحفظ quantity كعدد الأوراق/القطع الفعلي. السجلات القديمة
    # تبقى متوافقة وتُعامل كل وحدة فيها كقطعة واحدة حتى يعدلها المسؤول.
    return max(1,inventory_int(item.get('quantity'),inventory_unit_count(item)*inventory_pieces_per_unit(item)))

def inventory_schema_version(item):
    # السجلات القديمة كانت تحفظ marketQuantity كعدد القطع الفعلي حتى لو كان
    # نوع العرض "طقم". الإصدارات الجديدة تحفظ marketQuantity كعدد الوحدات
    # وتستخدم marketSetPieces/piecesPerUnit لتحويلها إلى كمية فعلية.
    # إبقاء النسخة 1 للسجلات القديمة يمنع إعادة تفسيرها عند مجرد التعديل.
    try: return max(1,int(item.get('inventorySchemaVersion') or 1))
    except Exception: return 1

def market_physical_per_unit(item):
    # توافق رجعي: لا نضرب كمية السوق القديمة في حجم الطقم مرة ثانية.
    if inventory_schema_version(item) < 2: return 1
    offer=str(item.get('marketOfferType') or 'single')
    if offer=='set': return max(1,inventory_int(item.get('marketSetPieces'),inventory_pieces_per_unit(item)))
    if offer=='bundle': return inventory_pieces_per_unit(item)
    return 1

def market_listing_physical(item):
    if not (item.get('forMarket') and item.get('marketApproved')): return 0
    listed=max(0,inventory_int(item.get('marketQuantity'),0))
    sold_units=max(0,inventory_int(item.get('marketSoldQuantity'),0))
    return max(0,listed-sold_units)*market_physical_per_unit(item)

def auction_is_active(item):
    if not (item.get('forAuction') and item.get('auctionApproved')): return False
    raw=str(item.get('auctionEnd') or '').strip()
    if not raw: return False
    try: return datetime.datetime.fromisoformat(raw)>datetime.datetime.now()
    except Exception: return False

def auction_listing_physical(item):
    return max(1,inventory_int(item.get('auctionQuantity'),1)) if auction_is_active(item) else 0

def order_line_physical(line,item=None):
    if line.get('physicalQuantity') not in (None,''): return inventory_int(line.get('physicalQuantity'),0)
    units=inventory_int(line.get('quantity'),1)
    return units*(market_physical_per_unit(item or {}) if item else 1)

def item_order_quantities(item_id,orders=None,item=None):
    reserved=returned=0; by_source={'market':0,'auction':0}
    for order in orders if orders is not None else load_orders():
        status=str(order.get('status') or '')
        for line in order.get('items') or []:
            if str(line.get('itemId'))!=str(item_id): continue
            physical=order_line_physical(line,item)
            if status in OPEN_ORDER_STATUSES:
                reserved+=physical; by_source[str(order.get('source') or 'market')]=by_source.get(str(order.get('source') or 'market'),0)+physical
            elif status=='returned': returned+=physical
    return reserved,returned,by_source

def inventory_snapshot(item,orders=None):
    total=inventory_total(item)
    sold=min(total,inventory_int(item.get('soldQuantity'),0))
    damaged=min(max(0,total-sold),inventory_int(item.get('damagedQuantity'),0))
    reserved,returned,by_source=item_order_quantities(item.get('id'),orders,item)
    returned=min(max(0,total-sold-damaged),returned)
    reserved=min(max(0,total-sold-damaged-returned),reserved)
    market=max(0,market_listing_physical(item)-by_source.get('market',0))
    auction=max(0,auction_listing_physical(item)-by_source.get('auction',0))
    capacity=max(0,total-sold-damaged-returned-reserved)
    market=min(capacity,market); capacity-=market
    auction=min(capacity,auction); capacity-=auction
    warehouse=capacity
    current=max(0,total-sold-damaged)
    special=current if item.get('specialNumberEnabled') else 0
    return {'itemId':str(item.get('id') or ''),'total':total,'current':current,'warehouse':warehouse,'market':market,'auction':auction,'reserved':reserved,'sold':sold,'returned':returned,'damaged':damaged,'special':special,'unitType':str(item.get('inventoryUnitType') or 'piece'),'unitCount':inventory_unit_count(item),'piecesPerUnit':inventory_pieces_per_unit(item)}

def inventory_summary():
    items=load(); orders=load_orders(); rows=[]
    totals={k:0 for k in ('total','current','warehouse','market','auction','reserved','sold','returned','damaged','special')}
    for item in items:
        snap=inventory_snapshot(item,orders); rows.append({**snap,'country':item.get('country',''),'denomination':item.get('denomination',''),'year':item.get('year',''),'frontImg':item.get('frontImg',''),'backImg':item.get('backImg',''),'location':storage_location(item),'specialNumberEnabled':bool(item.get('specialNumberEnabled')),'inventoryClassification':item.get('inventoryClassification') or ('set' if item.get('isSet') else ('graded' if item.get('isGraded') else 'ungraded')),'sourceSubmissionId':item.get('sourceSubmissionId','')})
        for key in totals: totals[key]+=inventory_int(snap.get(key),0)
    return {'totals':totals,'items':rows,'generatedAt':datetime.datetime.now().isoformat()}

def repair_approved_submission_inventory():
    """Repair approved customer submissions while preserving existing item data."""
    items=load(); rows=load_collectible_submissions(); repaired=created=0; skipped=[]; changed=False
    for row in rows:
        if row.get('status')!='approved': continue
        sid=str(row.get('id') or '')
        item=next((x for x in items if str(x.get('id'))==str(row.get('itemId') or '')),None)
        if not item: item=next((x for x in items if str(x.get('sourceSubmissionId') or '')==sid),None)
        inv=submission_inventory_values(row)
        if not item:
            serial=str(row.get('serial') or '').strip(); norm=re.sub(r'\s+','',serial).upper(); duplicate=False
            if norm:
                for other in items:
                    values=other.get('serials') or [other.get('serial')]
                    if not isinstance(values,list): values=[values]
                    if norm in {re.sub(r'\s+','',str(v or '')).upper() for v in values if str(v or '').strip()}: duplicate=True; break
            if duplicate:
                skipped.append({'submissionId':sid,'reason':'duplicate_serial'}); continue
            now=datetime.datetime.now().isoformat(); item_id='k-'+secrets.token_hex(8)
            item={'id':item_id,'country':row.get('country',''),'denomination':row.get('denomination',''),'issueEdition':row.get('issueEdition',''),'year':row.get('year',''),'type':row.get('type') or 'عملة ورقية','condition':row.get('condition','UNC'),'soldQuantity':0,'damagedQuantity':0,'serial':serial,'serials':[serial] if serial else [],'frontImg':row.get('frontImage',''),'backImg':row.get('backImage',''),'notes':row.get('notes',''),'ownerName':row.get('participantName',''),'ownerPhone':row.get('participantPhone',''),'ownerParticipantId':row.get('participantId',''),'sourceSubmissionId':sid,'storageStatus':'warehouse','warehouse':'المستودع الرئيسي','forMarket':str(row.get('desiredDestination') or 'vault')=='market','marketApproved':False,'forAuction':str(row.get('desiredDestination') or 'vault')=='auction','auctionApproved':False,'created':now,'updated':int(time.time()*1000),**inv}
            items.append(item); created+=1; changed=True
        else:
            before=json.dumps(item,ensure_ascii=False,sort_keys=True)
            for key,value in (('country',row.get('country','')),('denomination',row.get('denomination','')),('issueEdition',row.get('issueEdition','')),('year',row.get('year','')),('type',row.get('type') or 'عملة ورقية'),('condition',row.get('condition','UNC')),('frontImg',row.get('frontImage','')),('backImg',row.get('backImage',''))):
                if item.get(key) in (None,'') and value not in (None,''): item[key]=value
            for key,value in inv.items():
                if item.get(key) in (None,''): item[key]=value
            item['inventoryClassification']=item.get('inventoryClassification') or inv['inventoryClassification']
            item['collectionClass']='set' if item['inventoryClassification']=='set' else 'single'; item['isSet']=item['inventoryClassification']=='set'
            item['warehouse']=item.get('warehouse') or 'المستودع الرئيسي'; item['storageStatus']='warehouse'; item['sourceSubmissionId']=sid
            if json.dumps(item,ensure_ascii=False,sort_keys=True)!=before: repaired+=1; changed=True
        row['itemId']=item['id']; row['warehouseVerified']=True; row['warehouseVerifiedAt']=datetime.datetime.now().isoformat(); changed=True
    if changed:
        save(items); save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
        append_operation('فحص وإصلاح تحويلات المقتنيات إلى المستودع',{'repaired':repaired,'created':created,'skipped':skipped})
    return {'ok':True,'repaired':repaired,'created':created,'skipped':skipped,'inventory':inventory_summary()}

def storage_location(item):
    return {'warehouse':item.get('warehouse',''),'cabinet':item.get('cabinet',''),'shelf':item.get('shelf',''),'box':item.get('box',''),'album':item.get('album',''),'pocket':item.get('pocket','')}

def order_from_auction(due,item,person):
    physical=max(1,inventory_int(item.get('auctionQuantity'),1))
    return {'id':'ord-'+secrets.token_hex(6),'orderNumber':'NW-'+datetime.datetime.now().strftime('%y%m%d')+'-'+secrets.token_hex(3).upper(),'source':'auction','sourceId':due.get('id'),'auctionRound':due.get('auctionRound'),'participantId':due.get('participantId'),'customerName':person.get('name',''),'customerPhone':person.get('phone',''),'status':'awaiting_payment','paymentStatus':'unpaid','created':datetime.datetime.now().isoformat(),'updated':datetime.datetime.now().isoformat(),'subtotal':float(due.get('amount') or 0),'buyerFee':0,'total':float(due.get('amount') or 0),'items':[{'itemId':item.get('id'),'title':item_title(item),'quantity':1,'physicalQuantity':physical,'unitPrice':float(due.get('amount') or 0),'total':float(due.get('amount') or 0),'images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'storage':storage_location(item)}],'shippingCompany':'','trackingNumber':'','history':[{'status':'awaiting_payment','at':datetime.datetime.now().isoformat(),'note':'تم إنشاء الطلب تلقائيًا من فوز المزاد'}],'archived':False}

def create_order_for_due(due):
    orders=load_orders(); existing=next((o for o in orders if o.get('source')=='auction' and str(o.get('sourceId'))==str(due.get('id'))),None)
    if existing: return existing
    item=next((i for i in load() if str(i.get('id'))==str(due.get('itemId'))),{})
    person=next((x for x in load_people() if str(x.get('id'))==str(due.get('participantId'))),{})
    row=order_from_auction(due,item,person); orders.append(row); save_json(ORDERS,{'orders':orders}); due['orderId']=row['id']; return row

def create_order_for_market(req):
    orders=load_orders(); existing=next((o for o in orders if o.get('source')=='market' and str(o.get('sourceId'))==str(req.get('id'))),None)
    if existing: return existing
    item=next((i for i in load() if str(i.get('id'))==str(req.get('itemId'))),{})
    subtotal=float(req.get('offeredAmount') or req.get('listedAmount') or 0); fee=float(req.get('buyerFeeAmount') or 0)
    units=max(1,inventory_int(req.get('quantity'),1)); physical=units*market_physical_per_unit(item)
    row={'id':'ord-'+secrets.token_hex(6),'orderNumber':'NW-'+datetime.datetime.now().strftime('%y%m%d')+'-'+secrets.token_hex(3).upper(),'source':'market','sourceId':req.get('id'),'participantId':str(req.get('participantId') or ''),'customerName':req.get('name',''),'customerPhone':req.get('phone',''),'status':'awaiting_payment','paymentStatus':'unpaid','created':datetime.datetime.now().isoformat(),'updated':datetime.datetime.now().isoformat(),'subtotal':subtotal,'buyerFee':fee,'total':float(req.get('buyerTotal') or subtotal+fee),'items':[{'itemId':item.get('id'),'title':req.get('itemTitle') or item_title(item),'quantity':units,'physicalQuantity':physical,'unitPrice':float(req.get('unitPrice') or 0),'total':subtotal,'images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'storage':storage_location(item),'selectedSerials':list(req.get('selectedSerials') or [])}],'shippingCompany':'','trackingNumber':'','history':[{'status':'awaiting_payment','at':datetime.datetime.now().isoformat(),'note':'تم إنشاء الطلب من السوق العام'}],'archived':False}
    orders.append(row); save_json(ORDERS,{'orders':orders}); req['orderId']=row['id']; return row

def finalize_order_inventory(order,reverse=False):
    items=load(); changed=False
    for line in order.get('items') or []:
        item=next((x for x in items if str(x.get('id'))==str(line.get('itemId'))),None)
        if not item: continue
        physical=order_line_physical(line,item)
        current=inventory_int(item.get('soldQuantity'),0)
        item['soldQuantity']=max(0,current-physical) if reverse else min(inventory_total(item),current+physical)
        if order.get('source')=='market':
            units=inventory_int(line.get('quantity'),1); market_sold=inventory_int(item.get('marketSoldQuantity'),0)
            item['marketSoldQuantity']=max(0,market_sold-units) if reverse else min(inventory_int(item.get('marketQuantity'),market_sold+units),market_sold+units)
        if reverse:
            # المرتجع يبقى في منطقة فحص مستقلة ولا يعود للبيع تلقائيًا.
            item['marketApproved']=False; item['auctionApproved']=False
        item['updated']=int(datetime.datetime.now().timestamp()*1000); changed=True
    if changed: save(items)

def update_order_status(order,status,note=''):
    if status not in ORDER_FLOW and status not in ORDER_EXCEPTION: raise ValueError('حالة الطلب غير صالحة')
    previous=str(order.get('status') or ''); now=datetime.datetime.now().isoformat(); order['status']=status; order['updated']=now
    order.setdefault('history',[]).append({'status':status,'at':now,'note':note})
    if status=='paid': order['paymentStatus']='paid'; order['paidAt']=now
    if status=='shipped': order['shippedAt']=now
    if status=='received': order['receivedAt']=now
    if status=='completed':
        if not order.get('inventoryFinalized'): finalize_order_inventory(order,False); order['inventoryFinalized']=True; order['inventoryFinalizedAt']=now
        order['completedAt']=now; order['archived']=True; order['archivedAt']=now
    if status=='returned' and order.get('inventoryFinalized') and not order.get('inventoryReversed'):
        finalize_order_inventory(order,True); order['inventoryReversed']=True; order['inventoryReversedAt']=now; order['archived']=False

def ensure_dues_tracking_start():
    st=load_settings(); raw=str(st.get('duesTrackingStartedAt') or '').strip()
    if raw:
        try: return datetime.datetime.fromisoformat(raw)
        except Exception: pass
    now=datetime.datetime.now(); st['duesTrackingStartedAt']=now.isoformat(); save_json(SETTINGS,st); return now

def auction_local_now():
    # auctionEnd is stored as local Saudi wall-clock time (datetime-local).
    # Render runs in UTC, so comparing with datetime.now() directly delays settlement by 3 hours.
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).replace(tzinfo=None)

def ensure_auction_outcomes():
    """Create winner dues/notifications once for ended successful auction rounds. Safe to call repeatedly."""
    now=auction_local_now(); tracking_start=ensure_dues_tracking_start(); items=load(); bids=load_bids(); dues=load_auction_dues(); due_keys={(str(x.get('itemId')),int(x.get('auctionRound') or 1)) for x in dues}
    changed=False
    for item in items:
        if not (item.get('forAuction') and item.get('auctionApproved')): continue
        endraw=str(item.get('auctionEnd') or '').strip()
        if not endraw: continue
        try: enddt=datetime.datetime.fromisoformat(endraw)
        except Exception: continue
        if enddt>now: continue
        rnd=int(item.get('auctionRound') or 1); key=(str(item.get('id')),rnd)
        # قد يكون المستحق قد أُنشئ في طلب سابق بينما لم تُثبت نتيجة الجولة على
        # المقتنى (مثلاً بعد تحديث/إعادة تشغيل بين عمليتي الحفظ). وجود مستحق
        # غير ملغى لهذه الجولة دليل نهائي على أن المزاد أُرسي بالفعل؛ لذلك
        # نعيد مزامنة نتيجة المقتنى والطلب بدل ترك البطاقة تظهر "بلغ حد البيع
        # دون إرساء". هذه العملية idempotent ولا تنشئ بيعًا أو إشعارًا مكررًا.
        existing_due=next((x for x in dues if str(x.get('itemId'))==str(item.get('id')) and int(x.get('auctionRound') or 1)==rnd),None)
        if existing_due:
            if str(existing_due.get('status') or '')=='cancelled' or str(item.get('auctionOutcome') or '')=='exception':
                continue
            old_due_order_id=str(existing_due.get('orderId') or '')
            order=create_order_for_due(existing_due)
            due_changed=old_due_order_id!=str(existing_due.get('orderId') or order.get('id') or '')
            expected_amount=float(existing_due.get('amount') or 0)
            expected_pid=str(existing_due.get('participantId') or '')
            if (str(item.get('auctionOutcome') or '')!='sold' or
                str(item.get('auctionWinnerParticipantId') or '')!=expected_pid or
                abs(float(item.get('auctionWinningAmount') or 0)-expected_amount)>1e-9 or
                str(item.get('auctionOrderId') or '')!=str(order.get('id') or '')):
                item['auctionOutcome']='sold'
                item['auctionWinnerParticipantId']=expected_pid
                item['auctionWinningAmount']=expected_amount
                item['auctionOrderId']=order.get('id')
                item['auctionOutcomeAt']=item.get('auctionOutcomeAt') or now.isoformat()
                item['updated']=int(now.timestamp()*1000)
                changed=True
            if due_changed:
                save_json(AUCTION_DUES,{'dues':dues})
            continue
        rb=[b for b in bids if str(b.get('itemId'))==str(item.get('id')) and int(b.get('auctionRound') or 1)==rnd]
        if not rb: continue
        top=max(rb,key=lambda b: float(b.get('amount') or 0)); amount=float(top.get('amount') or 0); target=auction_target(item)
        if target>0 and amount+1e-9<target: continue
        migrated=enddt<tracking_start
        deadline=(now+datetime.timedelta(hours=24)) if migrated else (enddt+datetime.timedelta(hours=24))
        due={'id':'due-'+secrets.token_hex(6),'itemId':str(item.get('id')),'itemTitle':item_title(item),'auctionRound':rnd,'participantId':str(top.get('participantId') or ''),'amount':amount,'status':'unpaid','auctionEndedAt':enddt.isoformat(),'paymentDeadline':deadline.isoformat(),'created':now.isoformat(),'reconciled':bool(migrated)}
        dues.append(due); due_keys.add(key); changed=True
        order=create_order_for_due(due)
        item['auctionOutcome']='sold'; item['auctionWinnerParticipantId']=due['participantId']; item['auctionWinningAmount']=amount; item['auctionOrderId']=order.get('id'); item['auctionOutcomeAt']=now.isoformat(); item['updated']=int(now.timestamp()*1000)
        add_notification('participant',due['participantId'],'auction','🎉 مبارك، لقد فزت بالمزاد!',f"تم إرساء مزاد {due['itemTitle']} عليك بقيمة {amount:g} ر.س. يرجى إكمال السداد خلال 24 ساعة.",due['itemId'],'/account')
        add_notification('participant',due['participantId'],'order','📦 تم إنشاء طلب الفوز',f"تم إنشاء الطلب {order.get('orderNumber')} وبدأت مرحلة بانتظار السداد.",due['itemId'],'/account')
        add_notification('admin','','auction','فائز جديد بالمزاد',f"انتهى مزاد {due['itemTitle']} بفوز مشارك بقيمة {amount:g} ر.س.",due['itemId'],'/admin')
    if changed:
        save_json(AUCTION_DUES,{'dues':dues})
        save(items)
    return dues

def overdue_due_for(pid):
    now=datetime.datetime.now(); dues=ensure_auction_outcomes()
    for x in dues:
        if str(x.get('participantId'))!=str(pid) or x.get('status')!='unpaid': continue
        try:
            if datetime.datetime.fromisoformat(str(x.get('paymentDeadline')))<=now: return x
        except Exception: pass
    return None

def load_settings():
    defaults={'buyerFeePercent':2.5,'charityProfitPercent':5.0,'auctionEntryFee':10.0,'entryFeeEnabled':False,'negotiationPercents':[5,10,15,20],'negotiationHours':48,'adminEmail':'','platformName':'نوادر العملات','duesTrackingStartedAt':'','visitorSections':{'market':True,'auction':True,'specialNumbers':True,'transitionalIssues':True}}
    x=load_json(SETTINGS,defaults.copy())
    defaults.update(x if isinstance(x,dict) else {})
    vis=defaults.get('visitorSections')
    if not isinstance(vis,dict): vis={}
    defaults['visitorSections']={
        'market': bool(vis.get('market',True)),
        'auction': bool(vis.get('auction',True)),
        'specialNumbers': bool(vis.get('specialNumbers',True)),
        'transitionalIssues': bool(vis.get('transitionalIssues',True)),
    }
    return defaults

BACKUP_FILES=[
    ('khazina_shared_data.json',DATA),('auction_participants.json',PEOPLE),
    ('auction_bids.json',BIDS),('auction_negotiations.json',NEGOTIATIONS),
    ('market_requests.json',MARKET_REQUESTS),('subscription_ledger.json',SUBSCRIPTIONS),('save_audit.json',SAVE_AUDIT),('platform_settings.json',SETTINGS),
    ('notifications.json',NOTIFICATIONS),('auction_dues.json',AUCTION_DUES),('user_permissions.json',USER_PERMISSIONS),('operations_log.json',OPERATIONS_LOG),('orders_shipping.json',ORDERS),('collectible_submissions.json',COLLECTIBLE_SUBMISSIONS)
]

def create_full_backup_bytes():
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_DEFLATED) as z:
        manifest={'format':'khazina-full-backup','version':2,'created':datetime.datetime.now().isoformat(),'includes':['data','participants','bids','negotiations','market_requests','orders_shipping','collectible_submissions','subscriptions','settings','uploads']}
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for arc,path in BACKUP_FILES:
            if os.path.exists(path): z.write(path,'data/'+arc)
        if os.path.isdir(UPLOAD_DIR):
            for name in os.listdir(UPLOAD_DIR):
                src=os.path.join(UPLOAD_DIR,name)
                if os.path.isfile(src): z.write(src,'uploads/'+name)
    return mem.getvalue()

def restore_full_backup_bytes(raw):
    if not raw or len(raw)>2*1024*1024*1024: raise ValueError('حجم ملف النسخة الاحتياطية غير صالح')
    os.makedirs(BACKUP_DIR,exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(os.path.join(BACKUP_DIR,f'before_restore_{stamp}.khzbackup'),'wb') as f: f.write(create_full_backup_bytes())
    with zipfile.ZipFile(io.BytesIO(raw),'r') as z:
        names=set(z.namelist())
        if 'manifest.json' not in names: raise ValueError('الملف ليس نسخة خزينة كاملة')
        manifest=json.loads(z.read('manifest.json').decode('utf-8'))
        if manifest.get('format')!='khazina-full-backup': raise ValueError('صيغة النسخة الاحتياطية غير معروفة')
        for arc,path in BACKUP_FILES:
            member='data/'+arc
            if member in names: save_json(path,json.loads(z.read(member).decode('utf-8')))
        # أنشئ مجلد الاستعادة المؤقت داخل قرص البيانات نفسه حتى يكون النقل
        # إلى uploads ذريًا ولا يفشل بين نظام ملفات Render المؤقت والقرص الدائم.
        tmpdir=tempfile.mkdtemp(prefix='khazina_restore_',dir=DATA_ROOT)
        try:
            new_upload=os.path.join(tmpdir,'uploads'); os.makedirs(new_upload,exist_ok=True)
            for member in names:
                if not member.startswith('uploads/') or member.endswith('/'): continue
                rel=member[len('uploads/'):]
                if not rel or '/' in rel or '\\' in rel or rel in ('.','..'): continue
                with open(os.path.join(new_upload,rel),'wb') as f: f.write(z.read(member))
            old_upload=UPLOAD_DIR+'_old_restore'
            if os.path.exists(old_upload): shutil.rmtree(old_upload,ignore_errors=True)
            if os.path.exists(UPLOAD_DIR): os.replace(UPLOAD_DIR,old_upload)
            os.replace(new_upload,UPLOAD_DIR)
            shutil.rmtree(old_upload,ignore_errors=True)
        finally: shutil.rmtree(tmpdir,ignore_errors=True)
    return {'ok':True,'items':len(load()),'images':len([x for x in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR,x))])}

def save(items):
    backup_data('before_save')
    save_json(DATA,{'version':3,'items':items})
    backup_data('after_save')

def sig(i):
    serial=str(i.get('serial','')).strip()
    if serial: return 'S|'+serial+'|'+str(i.get('country',''))+'|'+str(i.get('denomination',''))+'|'+str(i.get('year',''))
    keys=['country','denomination','year','type','condition','quantity','warehouse','cabinet','shelf','box','album','pocket','purchase','shipping','other','expectedPrice','notes']
    return 'E|'+'|'.join(str(i.get(k,'')) for k in keys)

def auction_target(i):
    # Compatibility: older versions used auctionStartPrice as the reserve/target.
    # The achieved target is one riyal above that old value, matching the approved auction rule.
    if i.get('auctionTargetPrice') not in (None,''): return float(i.get('auctionTargetPrice') or 0)
    old=float(i.get('auctionStartPrice') or 0)
    return old+1 if old>0 else 0

def public_item(i):
    # The reserve amount remains confidential. Public UI receives only a coarse state
    # (below/met/none) so the current-price card can change color without exposing the target.
    round_no=int(i.get('auctionRound') or 1)
    bids=[b for b in load_bids() if b.get('itemId')==i.get('id') and int(b.get('auctionRound') or 1)==round_no]
    top=max([float(b.get('amount') or 0) for b in bids]+[0.0])
    target=auction_target(i)
    reserve_state='none' if target<=0 else ('met' if top>=target else 'below')
    ended=False
    end=str(i.get('auctionEnd') or '').strip()
    if end:
        try: ended=datetime.datetime.fromisoformat(end) <= auction_local_now()
        except Exception: ended=False
    sold=bool(ended and bids and (target<=0 or top>=target))
    public_keys=['id','country','denomination','year','type','condition','quantity','serials','frontImg','backImg','auctionEnd','auctionOpeningPrice','auctionBidStep','auctionAdditionalTerms','notes','negotiationEnabled','negotiationPercent','auctionRound','issueEdition','issueEditionOther','isGraded','gradingCompany','gradeValue','gradePercent','gradingCertNumber','specialNumberEnabled','specialNumberType','specialNumberTypes','specialNumberReason','updated']
    return {k:i.get(k) for k in public_keys} | public_seller_identity(i) | {'auctionCurrentPrice':top,'bidCount':len(bids),'reserveState':reserve_state,'auctionEnded':ended,'auctionSold':sold}



def public_market_item(i):
    # السوق العام لا يرسل سعر الشراء أو الموقع الداخلي أو أي بيانات مالية/إدارية سرية.
    keys=['id','country','denomination','year','type','condition','quantity','frontImg','backImg','notes',
          'issueEdition','issueEditionOther','isGraded','gradingCompany','gradeValue','gradePercent','gradingCertNumber','gradingVerificationStatus','gradingNotes',
          'marketOfferType','marketSalePrice','marketUnitPrice','marketQuantity','marketSetPieces','marketSetSize','marketSetCurrencyMode','marketPriceUnit',
          'marketPartialAllowed','marketNegotiationEnabled','marketNegotiationPercent','marketTitle','updated','specialNumberEnabled']
    out={k:i.get(k) for k in keys}
    out.update(public_seller_identity(i))
    _,_,reserved=item_order_quantities(i.get('id'),item=i)
    per_unit=market_physical_per_unit(i)
    reserved_units=(reserved.get('market',0)+per_unit-1)//per_unit
    out['availableQuantity']=max(0,int(i.get('marketQuantity') or i.get('quantity') or 1)-int(i.get('marketSoldQuantity') or 0)-reserved_units)
    return out

def special_serial_pool(item):
    raw=item.get("serials") or []
    if not isinstance(raw,list): raw=[raw]
    vals=[]
    for x in raw:
        x=str(x or "").strip()
        if x and x not in vals: vals.append(x)
    one=str(item.get("serial") or "").strip()
    if one and one not in vals: vals.append(one)
    return vals

def special_reserved_serials(item_id):
    now=datetime.datetime.now(); out=set()
    for r in load_market_requests():
        if str(r.get("itemId"))!=str(item_id) or r.get("status") not in ("pending","accepted"): continue
        if r.get("status")=="pending":
            try:
                if datetime.datetime.fromisoformat(str(r.get("reservedUntil") or "")) <= now: continue
            except Exception: continue
        for x in r.get("selectedSerials") or []:
            x=str(x).strip()
            if x: out.add(x)
    return out

def special_available_serials(item):
    sold={str(x).strip() for x in (item.get("marketSoldSerials") or []) if str(x).strip()}
    reserved=special_reserved_serials(item.get("id"))
    return [x for x in special_serial_pool(item) if x not in sold and x not in reserved]

def special_sale_price(item):
    try: return float(item.get("marketSalePrice") or item.get("marketUnitPrice") or 0)
    except Exception: return 0.0

def public_special_item(item):
    serials=special_serial_pool(item); available=special_available_serials(item)
    sold={str(x).strip() for x in (item.get("marketSoldSerials") or []) if str(x).strip()}; reserved=special_reserved_serials(item.get("id"))
    qty=max(0,int(item.get("marketQuantity") or item.get("quantity") or max(1,len(serials)))-int(item.get("marketSoldQuantity") or 0))
    if serials: qty=len(available)
    price=special_sale_price(item); sale=bool(item.get("forMarket") and item.get("marketApproved") and price>0 and qty>0)
    if serials and not available and reserved and len(sold)<len(serials): status="reserved"
    elif qty<=0: status="sold"
    else: status="available" if sale else "display"
    keys=("id","country","denomination","year","condition","serial","serials","frontImg","backImg","specialNumberType","specialNumberTypes","specialNumberReason","marketSalePrice","marketUnitPrice","marketNegotiationEnabled","marketNegotiationPercent","marketOfferType","marketTitle","quantity")
    out={k:item.get(k) for k in keys}; out.update({"availableSerials":available,"availableQuantity":qty,"unitPrice":price,"saleEnabled":sale,"soldOut":status=="sold","availabilityStatus":status}); return out

def public_portal_url(host):
    # V2.0: QR ثابت لا يعتمد على التاريخ أو رمز مؤقت.
    return f'http://{host}/auction'

def public_market_url(host):
    return f'http://{host}/market'


def _ocr_normalize(text):
    """Normalize Arabic/Latin OCR output without destroying serial-number evidence."""
    text=str(text or '')
    trans=str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹','01234567890123456789')
    text=text.translate(trans)
    text=text.replace('\u200f',' ').replace('\u200e',' ').replace('\u0640',' ')
    # Arabic normalization helps OCR variants match our dictionaries.
    text=re.sub('[إأآٱ]','ا',text)
    text=text.replace('ى','ي').replace('ة','ه')
    text=re.sub(r'\s+',' ',text)
    return text.strip()


def _confidence_bucket(score):
    return 'high' if score>=0.82 else ('medium' if score>=0.55 else 'low')


def parse_ocr_text(text):
    """Turn raw OCR text into conservative currency-field suggestions with confidence.

    High-confidence fields may be filled automatically by the UI. Medium confidence is
    displayed as a suggestion requiring user confirmation. Low confidence is never used.
    """
    raw=str(text or '')
    norm=_ocr_normalize(raw)
    out={}; fields={}; candidates={}

    def add(field,value,score,reason=''):
        value=str(value or '').strip()
        if not value: return
        score=max(0.0,min(0.99,float(score)))
        cur=fields.get(field)
        if not cur or score>float(cur.get('confidence',0)):
            fields[field]={'value':value,'confidence':round(score,2),'level':_confidence_bucket(score),'reason':reason}
        candidates.setdefault(field,[]).append({'value':value,'confidence':round(score,2),'reason':reason})

    # Country detection: exact normalized aliases first, then conservative fuzzy windows.
    country_aliases={
        'المملكة العربية السعودية':['المملكه العربيه السعوديه','السعوديه','المملكه السعوديه'],
        'الإمارات العربية المتحدة':['الامارات العربيه المتحده','دوله الامارات العربيه المتحده','الامارات المتحده','الامارات'],
        'سوريا':['الجمهوريه العربيه السوريه','سوريا','مصرف سوريه المركزي'],
        'الكويت':['دوله الكويت','الكويت','بنك الكويت المركزي'],
        'قطر':['دوله قطر','قطر','مصرف قطر المركزي'],
        'البحرين':['مملكه البحرين','البحرين','مصرف البحرين المركزي'],
        'عُمان':['سلطنه عمان','عمان','البنك المركزي العماني'],
        'اليمن':['الجمهوريه اليمنيه','اليمن','البنك المركزي اليمني'],
        'العراق':['جمهوريه العراق','العراق','البنك المركزي العراقي'],
        'الأردن':['المملكه الاردنيه الهاشميه','الاردن','البنك المركزي الاردني'],
        'مصر':['جمهوريه مصر العربيه','مصر','البنك المركزي المصري'],
        'لبنان':['الجمهوريه اللبنانيه','لبنان','مصرف لبنان'],
    }
    for canonical,aliases in country_aliases.items():
        best=0; matched=''
        for a in aliases:
            matched_here = bool(re.search(r'(?<![\w\u0600-\u06FF])'+re.escape(a)+r'(?![\w\u0600-\u06FF])',norm)) if len(a)<=6 else (a in norm)
            if matched_here:
                # Longer institutional/country phrases are more trustworthy than short names.
                score=.96 if len(a)>=15 else (.91 if len(a)>=8 else .84)
                if score>best: best=score; matched=a
        if best: add('country',canonical,best,'تطابق اسم الدولة/الجهة المصدرة: '+matched)

    # Year: prefer 4-digit calendar years. Avoid treating long serials as years.
    for m in re.finditer(r'(?<!\d)(1[89]\d{2}|20\d{2}|14\d{2})(?!\d)',norm):
        year=m.group(1); score=.9
        if int(year)>2100 or int(year)<1300: score=.45
        add('year',year,score,'سنة مكونة من أربعة أرقام')

    # Denominations: digits + currency word, including common Arabic number words.
    currency_units=r'(?:ريال|ريالات|ريالا|ليره|ليرات|دينار|دنانير|درهم|دراهم|جنيه|جنيهات|فلس)'
    for m in re.finditer(r'(?<!\d)(\d{1,6})\s*('+currency_units[3:-1]+r')(?![\w])',norm):
        add('denomination',m.group(1)+' '+m.group(2),.94,'قيمة رقمية متبوعة باسم العملة')
    word_numbers={
        'واحد':1,'واحده':1,'احد':1,'اثنان':2,'اثنين':2,'اثنتان':2,'ثلاثه':3,'ثلاث':3,'خمسه':5,'خمس':5,
        'عشره':10,'عشر':10,'عشرون':20,'عشرين':20,'خمسه وعشرون':25,'خمس وعشرون':25,
        'خمسون':50,'خمسين':50,'مائه':100,'مئه':100,'مائتان':200,'مئتان':200,
        'خمسمائه':500,'خمسمئه':500,'الف':1000,'الفان':2000,'خمسه الاف':5000,'خمس الاف':5000,'عشره الاف':10000,
    }
    for phrase,num in sorted(word_numbers.items(),key=lambda x:len(x[0]),reverse=True):
        mm=re.search(r'\b'+re.escape(phrase)+r'\s+('+currency_units[3:-1]+r')\b',norm)
        if mm:
            add('denomination',f'{num} {mm.group(1)}',.87,'قيمة مكتوبة بالكلمات')

    # Serial numbers. Score conservatively; reject likely years/denominations and uniform noise.
    serial_re=r'(?<![A-Za-z0-9])([A-Za-z]{0,3}\s*[-/]?\s*\d{5,12})(?![A-Za-z0-9])'
    for m in re.finditer(serial_re,norm):
        token=re.sub(r'\s+','',m.group(1)).strip('-/')
        digits=''.join(ch for ch in token if ch.isdigit())
        if len(digits)<5: continue
        if len(digits)==4 and 1300<=int(digits)<=2100: continue
        score=.67
        if len(digits)>=6: score+=.08
        if re.search('[A-Za-z]',token): score+=.07
        if len(set(digits))>=4: score+=.04
        if digits in ('00000','000000','111111','123456'): score-=.15
        add('serial',token,min(score,.9),'نمط رقم تسلسلي محتمل')

    # Keep legacy high-confidence data for backward compatibility.
    for k,v in fields.items():
        if float(v.get('confidence',0))>=.82:
            out[k]=v['value']
    return {'data':out,'fields':fields,'candidates':candidates,'normalizedText':norm[:5000],'rawText':raw[:5000]}

def _tesseract_candidates():
    """Return candidate tesseract executable paths without assuming one installation method."""
    candidates=[]
    settings=load_json(SETTINGS,{})
    configured=str(settings.get('ocrTesseractPath') or '').strip()
    env_cmd=str(os.environ.get('TESSERACT_CMD') or '').strip()
    if configured: candidates.append(configured)
    if env_cmd: candidates.append(env_cmd)

    # PATH is the most reliable source when Tesseract was installed previously.
    which=shutil.which('tesseract')
    if which: candidates.append(which)

    if os.name=='nt':
        # Registry paths used by common Windows installers.
        try:
            import winreg
            registry_locations=[
                (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\\Tesseract-OCR'),
                (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\\WOW6432Node\\Tesseract-OCR'),
                (winreg.HKEY_CURRENT_USER, r'SOFTWARE\\Tesseract-OCR'),
            ]
            for hive,key_name in registry_locations:
                try:
                    with winreg.OpenKey(hive,key_name) as key:
                        install_dir,_=winreg.QueryValueEx(key,'Path')
                        if install_dir:
                            candidates.append(os.path.join(str(install_dir),'tesseract.exe'))
                except OSError:
                    pass
        except Exception:
            pass

        roots=[
            os.environ.get('ProgramFiles',''),
            os.environ.get('ProgramFiles(x86)',''),
            os.environ.get('LOCALAPPDATA',''),
            os.environ.get('APPDATA',''),
            os.environ.get('USERPROFILE',''),
            r'C:\\Tesseract-OCR',
        ]
        patterns=[]
        for root in roots:
            if not root: continue
            patterns += [
                os.path.join(root,'Tesseract-OCR','tesseract.exe'),
                os.path.join(root,'Programs','Tesseract-OCR','tesseract.exe'),
                os.path.join(root,'tesseract','tesseract.exe'),
            ]
        patterns += [
            r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
            r'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe',
        ]
        for pat in patterns:
            candidates.extend(glob.glob(pat))

    # Preserve order while removing duplicates.
    out=[]; seen=set()
    for c in candidates:
        c=os.path.expandvars(os.path.expanduser(str(c).strip().strip('"')))
        key=os.path.normcase(os.path.abspath(c)) if c else ''
        if c and key not in seen:
            seen.add(key); out.append(c)
    return out


def resolve_tesseract():
    """Locate a working Tesseract executable and remember it for later runs."""
    diagnostics=[]
    for exe in _tesseract_candidates():
        if not os.path.isfile(exe):
            diagnostics.append(f'غير موجود: {exe}')
            continue
        try:
            r=subprocess.run([exe,'--version'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10,encoding='utf-8',errors='ignore')
            if r.returncode==0:
                try:
                    cfg=load_json(SETTINGS,{})
                    if cfg.get('ocrTesseractPath')!=exe:
                        cfg['ocrTesseractPath']=exe
                        save_json(SETTINGS,cfg)
                except Exception:
                    pass
                first=(r.stdout or '').splitlines()[0] if (r.stdout or '').splitlines() else 'Tesseract'
                return exe,first,diagnostics
            diagnostics.append(f'لم يعمل ({r.returncode}): {exe}')
        except Exception as e:
            diagnostics.append(f'{exe}: {e}')
    return '', '', diagnostics


def _tesseract_languages(exe):
    try:
        r=subprocess.run([exe,'--list-langs'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15,encoding='utf-8',errors='ignore')
        langs=[]
        for line in (r.stdout or '').splitlines():
            x=line.strip()
            if x and not x.lower().startswith('list of available languages'):
                langs.append(x)
        return set(langs)
    except Exception:
        return set()


def _run_tesseract(exe, image_path, lang, psm):
    cmd=[exe,image_path,'stdout','--psm',str(psm)]
    if lang:
        cmd += ['-l',lang]
    r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=45,encoding='utf-8',errors='ignore')
    if r.returncode!=0:
        raise RuntimeError((r.stderr or r.stdout or f'Tesseract exit {r.returncode}').strip())
    return r.stdout or ''


def analyze_image(url):
    # OCR is intentionally independent from database saving. A read failure must never block saving an item or image.
    # The public URL is /uploads/..., but on Render the real file can be
    # /var/data/uploads/... outside ROOT. Resolve it against UPLOAD_DIR.
    parsed_path=urlparse(str(url or '')).path
    prefix='/uploads/'
    if not parsed_path.startswith(prefix):
        return False,{},'الصورة غير موجودة على الخادم.'
    rel=parsed_path[len(prefix):]
    path=os.path.abspath(os.path.join(UPLOAD_DIR,rel))
    upload_root=os.path.abspath(UPLOAD_DIR)
    try:
        inside_uploads=os.path.commonpath([path,upload_root])==upload_root
    except ValueError:
        inside_uploads=False
    if not inside_uploads or not os.path.isfile(path):
        return False,{},'الصورة غير موجودة على الخادم.'

    exe,version,diag=resolve_tesseract()
    if not exe:
        hint='؛ '.join(diag[-2:]) if diag else 'لم يتم العثور على tesseract.exe في PATH أو Registry أو المسارات المعروفة.'
        return False,{},'لم يتم العثور على محرك Tesseract الذي سبق تثبيته على هذا الجهاز. '+hint+' رفع الصور وحفظ المقتنى يعملان بشكل مستقل.'

    langs=_tesseract_languages(exe)
    has_ara='ara' in langs
    has_eng='eng' in langs
    lang='ara+eng' if has_ara and has_eng else ('ara' if has_ara else ('eng' if has_eng else ''))
    language_note=''
    if not has_ara:
        language_note=' تنبيه: حزمة اللغة العربية ara غير ظاهرة في هذا التثبيت.'

    work=[]
    texts=[]
    errors=[]
    try:
        # Pillow improves currency OCR, but Tesseract can still run directly if Pillow is unavailable.
        try:
            from PIL import Image, ImageOps, ImageEnhance
            im=Image.open(path)
            im=ImageOps.exif_transpose(im).convert('L')
            im=ImageOps.autocontrast(im)
            im=ImageEnhance.Sharpness(im).enhance(1.8)
            for angle in (0,90,180,270):
                rim=im if angle==0 else im.rotate(angle,expand=True)
                fd,tmp=tempfile.mkstemp(prefix='nawader_ocr_',suffix='.png')
                os.close(fd)
                rim.save(tmp,format='PNG')
                work.append(tmp)
        except Exception as e:
            errors.append('تعذر تحسين الصورة بـ Pillow: '+str(e))
            work=[path]

        for img_path in work:
            for psm in (6,11):
                try:
                    texts.append(_run_tesseract(exe,img_path,lang,psm))
                except Exception as e:
                    errors.append(str(e))
                    # If combined Arabic+English fails for a traineddata reason, try the available default once.
                    if lang:
                        try: texts.append(_run_tesseract(exe,img_path,'',psm))
                        except Exception as e2: errors.append(str(e2))

        text=' '.join(t for t in texts if t).strip()
        parsed=parse_ocr_text(text)
        data=parsed.get('data',{})
        fields=parsed.get('fields',{})
        medium=[k for k,v in fields.items() if v.get('level')=='medium']
        if data or medium:
            note=f'تم تشغيل {version} وتحليل النص. البيانات عالية الثقة تُملأ تلقائيًا، والمتوسطة تظهر كاقتراح للمراجعة.'+language_note
            return True,{'values':data,'fields':fields,'rawText':parsed.get('rawText','')[:2500]},note
        if text:
            return False,{'values':{},'fields':fields,'rawText':parsed.get('rawText','')[:2500]},f'تم تشغيل {version} وقراءة نص من الصورة، لكن لم أجد بيانات موثوقة أو محتملة لملء الحقول.'+language_note
        detail=(' آخر خطأ: '+errors[-1][:220]) if errors else ''
        return False,{},f'تم العثور على {version} لكنه لم يُرجع نصًا من هذه الصورة.'+language_note+detail
    except subprocess.TimeoutExpired:
        return False,{},'تم العثور على Tesseract لكن تحليل الصورة تجاوز المهلة. جرّب صورة أصغر أو أوضح؛ الحفظ لا يتأثر.'
    except Exception as e:
        return False,{},'تم العثور على Tesseract لكن حدث خطأ أثناء التحليل: '+str(e)[:300]+'؛ الحفظ لا يتأثر.'
    finally:
        for tmp in work:
            if tmp!=path:
                try: os.remove(tmp)
                except OSError: pass


def _pbkdf2(password, salt_hex, iterations=260000):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), iterations).hex()

def _configured_admin_password():
    # Render/production can override this with ADMIN_PASSWORD.
    # The approved recovery default is 12345678 so local and Render logins stay in sync.
    return str(os.environ.get('ADMIN_PASSWORD') or '12345678')

def ensure_admin_auth():
    password=_configured_admin_password()
    cfg=load_json(AUTH_FILE,{})
    iterations=260000
    valid=False
    if isinstance(cfg,dict) and cfg.get('salt') and cfg.get('hash'):
        try:
            got=_pbkdf2(password,cfg['salt'],int(cfg.get('iterations') or iterations))
            valid=secrets.compare_digest(got,str(cfg.get('hash') or '')) and str(cfg.get('username') or 'admin')=='admin'
        except Exception:
            valid=False
    if valid:
        return cfg, None
    salt=secrets.token_hex(16)
    cfg={'version':2,'username':'admin','salt':salt,'iterations':iterations,'hash':_pbkdf2(password,salt,iterations),'created':datetime.datetime.now().isoformat(),'source':'ADMIN_PASSWORD/default-recovery'}
    save_json(AUTH_FILE,cfg)
    try:
        with open(ADMIN_CREDENTIALS,'w',encoding='utf-8') as f:
            f.write('دخول إدارة نوادر العملات\n')
            f.write('اسم المستخدم: admin\n')
            f.write('كلمة المرور: '+password+'\n\n')
            f.write('يمكن تغييرها لاحقًا عبر متغير ADMIN_PASSWORD في Render.\n')
            f.write('احتفظ بهذا الملف في جهاز الإدارة ولا تشاركه مع العملاء.\n')
    except Exception: pass
    return cfg, password

def verify_admin_password(username,password):
    cfg,_=ensure_admin_auth()
    if not secrets.compare_digest(str(username or ''),str(cfg.get('username') or 'admin')): return False
    got=_pbkdf2(str(password or ''),cfg['salt'],int(cfg.get('iterations') or 260000))
    return secrets.compare_digest(got,str(cfg.get('hash') or ''))

def clean_sessions():
    now=time.time()
    for token,meta in list(ADMIN_SESSIONS.items()):
        if now-float(meta.get('last',0))>SESSION_TTL_SECONDS: ADMIN_SESSIONS.pop(token,None)

def is_public_upload_url(url):
    if not url: return False
    path=urlparse(str(url)).path
    if not path.startswith('/uploads/'): return False
    for i in load():
        if not ((i.get('forAuction') and i.get('auctionApproved')) or (i.get('forMarket') and i.get('marketApproved'))): continue
        if urlparse(str(i.get('frontImg') or '')).path==path or urlparse(str(i.get('backImg') or '')).path==path: return True
    # صور طلبات المقتنيات تُحفظ بأسماء عشوائية على القرص الدائم، وتحتاجها
    # صفحة صاحب الطلب للمعاينة والتعديل قبل اعتماد الإدارة.
    for row in load_collectible_submissions():
        if urlparse(str(row.get('frontImage') or '')).path==path or urlparse(str(row.get('backImage') or '')).path==path: return True
    return False

ADMIN_GET_API={
    '/api/negotiations','/api/backup/full','/api/items','/api/participants','/api/participants/summary',
    '/api/bids','/api/market/requests','/api/subscriptions','/api/daily-qr','/api/market-qr',
    '/api/market-qr-info','/api/daily-qr-info','/api/settings/admin','/api/ocr/status','/api/notifications/admin','/api/permissions','/api/dues','/api/operations','/api/orders','/api/collectible-submissions/admin','/api/inventory/summary'
}
PUBLIC_POST_API={'/api/special/request','/api/market/request','/api/negotiate','/api/participant/register','/api/participant/verify','/api/participant/profile','/api/bid','/api/visitor/receive','/api/notifications/read','/api/collectible-submissions','/api/collectible-submissions/delete','/api/visitor/upload','/api/owner/item/update','/api/owner/item/delete','/api/owner/market/update','/api/owner/auction/update','/api/owner/auction/cancel'}
PUBLIC_STATIC={'/styles.css','/public_home.html','/public_market.html','/public_market.js','/public_auction.html','/public_auction.js','/special_numbers.html','/announcements.html','/account.html','/visitor.js','/visitor.css','/manifest.webmanifest','/sw.js','/notifications.html','/seller_portal.html','/invoice.html'}

class H(SimpleHTTPRequestHandler):
    def cookie_value(self,name):
        raw=self.headers.get('Cookie') or ''
        for part in raw.split(';'):
            if '=' in part:
                k,v=part.strip().split('=',1)
                if k==name: return v
        return ''
    def is_admin(self):
        clean_sessions(); token=self.cookie_value('KhazinaAdmin')
        meta=ADMIN_SESSIONS.get(token)
        if not meta: return False
        meta['last']=time.time(); return True
    def require_admin(self,api=False):
        if self.is_admin(): return True
        if api: self.sendj({'error':'هذه الصفحة أو العملية خاصة بالإدارة. سجل الدخول أولًا.'},401)
        else:
            self.send_response(302); self.send_header('Location','/admin-login'); self.end_headers()
        return False
    def same_origin_ok(self):
        origin=self.headers.get('Origin')
        if not origin: return True
        host=self.headers.get('Host') or ''
        return origin in ('http://'+host,'https://'+host)
    def login_page(self,error=''):
        err=('<div class="err">'+error+'</div>') if error else ''
        html='''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>دخول الإدارة | نوادر العملات</title><style>body{margin:0;background:#0b1224;font-family:Tahoma,Arial,sans-serif;color:#0d1b3b;min-height:100vh;display:grid;place-items:center}.box{width:min(430px,90vw);background:white;border-radius:22px;padding:28px;box-shadow:0 20px 60px #0008;border-top:5px solid #c79245}h1{margin:0 0 8px;color:#102659}p{color:#5c6470}label{display:block;font-weight:700;margin:16px 0 6px}input{box-sizing:border-box;width:100%;padding:13px;border:1px solid #ccd3df;border-radius:12px;font-size:17px}button{width:100%;margin-top:20px;padding:13px;border:0;border-radius:12px;background:#102659;color:white;font-weight:800;font-size:17px;cursor:pointer}.err{background:#fff0f0;color:#9d1b2d;padding:10px;border-radius:10px;margin:12px 0}.public{display:block;text-align:center;margin-top:16px;color:#8a642b;text-decoration:none}</style></head><body><form class="box" method="post" action="/admin-login"><h1>🔐 دخول الإدارة</h1><p>الخزينة والسجل والمالية وإدارة السوق والمزاد محمية ولا تظهر للزوار.</p>'''+err+'''<label>اسم المستخدم</label><input name="username" value="admin" autocomplete="username" required><label>كلمة المرور</label><input name="password" type="password" autocomplete="current-password" required><button type="submit">دخول الإدارة</button><a class="public" href="/">العودة إلى واجهة نوادر العملات</a></form></body></html>'''
        data=html.encode('utf-8'); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def end_headers(self):
        self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma','no-cache')
        self.send_header('Expires','0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy',"frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        super().end_headers()
    def log_message(self, fmt, *args):
        if self.path.startswith('/api/'): print(fmt%args)
    def sendj(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8'); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(b)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def send_file(self,path,content_type=None):
        try:
            with open(path,'rb') as f: data=f.read()
            self.send_response(200)
            self.send_header('Content-Type',content_type or mimetypes.guess_type(path)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.end_headers(); self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404,'File not found')
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/admin-login':
            if self.is_admin():
                self.send_response(302); self.send_header('Location','/admin'); self.end_headers(); return
            self.login_page(); return
        if p=='/admin-logout':
            token=self.cookie_value('KhazinaAdmin'); ADMIN_SESSIONS.pop(token,None)
            self.send_response(302); self.send_header('Set-Cookie','KhazinaAdmin=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict'); self.send_header('Location','/'); self.end_headers(); return
        # The root URL is the permanent public homepage. Keep /home as a
        # compatibility alias so old bookmarks and printed links never 404.
        if p in ('/','/home','/home/','/public_home.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'public_home.html'),'text/html; charset=utf-8'); return
        if p in ('/admin','/admin/','/index.html'):
            if not self.require_admin(): return
            self.send_file(os.path.join(ADMIN_DIR,'index.html'),'text/html; charset=utf-8'); return
        if p in ('/admin/app.js','/admin/styles.css'):
            if not self.require_admin(): return
            name=os.path.basename(p)
            ctype='application/javascript; charset=utf-8' if name.endswith('.js') else 'text/css; charset=utf-8'
            self.send_file(os.path.join(ADMIN_DIR,name),ctype); return
        if p in ADMIN_GET_API and not self.require_admin(api=True): return
        if p=='/api/session-state':
            self.sendj({'admin':self.is_admin()}); return
        if p=='/api/version':
            self.sendj({'version':'4.3.4','name':'Nawader Coins Visitor Sections Final Fix','port':getattr(self.server,'server_port',None)}); return
        if p=='/api/settings/public':
            st=load_settings(); self.sendj({'buyerFeePercent':st['buyerFeePercent'],'charityProfitPercent':st['charityProfitPercent'],'auctionEntryFee':st['auctionEntryFee'],'entryFeeEnabled':st['entryFeeEnabled'],'negotiationPercents':st['negotiationPercents'],'negotiationHours':st['negotiationHours'],'visitorSections':st['visitorSections']}); return
        if p=='/api/settings/admin':
            if not self.require_admin(api=True): return
            self.sendj({'settings':load_settings()}); return
        if p=='/api/ocr/status':
            exe,version,diag=resolve_tesseract()
            langs=sorted(_tesseract_languages(exe)) if exe else []
            self.sendj({'ok':bool(exe),'path':exe,'version':version,'hasArabic':'ara' in langs,'hasEnglish':'eng' in langs,'languages':langs[:80],'diagnostics':diag[-5:]}); return
        if p=='/api/owner/items':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
            if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
            submissions={str(x.get('itemId') or ''):x for x in load_collectible_submissions() if str(x.get('participantId') or '')==pid and x.get('itemId')}
            owned=[]
            for i in load():
                if str(i.get('ownerParticipantId') or '')!=pid or i.get('ownerArchived'): continue
                y={k:i.get(k) for k in (
                    'id','country','denomination','issueEdition','year','type','condition','notes','frontImg','backImg',
                    'inventoryUnitType','inventoryUnitCount','piecesPerUnit','quantity','availableQuantity',
                    'forMarket','marketApproved','marketSalePrice','marketPriceUnit','marketNegotiationEnabled','marketNegotiationPercent',
                    'forAuction','auctionApproved','auctionEnd','auctionOpeningPrice','auctionStartPrice','auctionCurrentPrice',
                    'auctionBidStep','auctionTargetPrice','auctionAdditionalTerms','auctionRound','auctionOutcome','auctionSold'
                )}
                sub=submissions.get(str(i.get('id') or '')) or {}
                y['desiredDestination']=sub.get('desiredDestination') or 'vault'
                y['sourceSubmissionId']=i.get('sourceSubmissionId') or sub.get('id') or ''
                round_no=int(i.get('auctionRound') or 1)
                y['bidCount']=sum(1 for b in load_bids() if str(b.get('itemId'))==str(i.get('id')) and int(b.get('auctionRound') or 1)==round_no)
                y['marketOpenRequests']=sum(1 for r in load_market_requests() if str(r.get('itemId'))==str(i.get('id')) and str(r.get('status') or 'new') not in ('completed','cancelled','rejected'))
                owned.append(y)
            self.sendj({'items':owned}); return
        if p=='/api/collectible-submissions':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=next((x for x in load_people() if str(x.get('id'))==pid),None)
            if not participant_can_access(person): self.sendj({'error':'الحساب غير متاح'},403); return
            rows=[x for x in load_collectible_submissions() if str(x.get('participantId'))==pid]
            rows.sort(key=lambda x:x.get('created',''),reverse=True)
            safe=[]
            for x in rows:
                y={k:v for k,v in x.items() if k not in ('frontImage','backImage')}
                # لا نعيد Base64 القديم حتى لا تمتلئ ذاكرة الجوال؛ الروابط الدائمة آمنة للعرض.
                if str(x.get('frontImage') or '').startswith('/uploads/'): y['frontImage']=x.get('frontImage')
                if str(x.get('backImage') or '').startswith('/uploads/'): y['backImage']=x.get('backImage')
                y['hasFrontImage']=bool(x.get('frontImage')); y['hasBackImage']=bool(x.get('backImage'))
                safe.append(y)
            self.sendj({'submissions':safe}); return
        if p=='/api/collectible-submissions/admin':
            rows=load_collectible_submissions(); rows.sort(key=lambda x:x.get('created',''),reverse=True)
            self.sendj({'submissions':rows,'pending':sum(1 for x in rows if x.get('status')=='pending'),'needsChanges':sum(1 for x in rows if x.get('status')=='needs_changes')}); return
        if p=='/api/notifications':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=next((x for x in load_people() if str(x.get('id'))==pid),None)
            if not participant_can_access(person): self.sendj({'error':'الحساب غير متاح'},403); return
            ensure_auction_outcomes(); rows=[x for x in load_notifications() if x.get('recipientType')=='participant' and str(x.get('recipientId'))==pid]
            rows.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'notifications':rows[:200],'unread':sum(1 for x in rows if not x.get('read'))}); return
        if p=='/api/notifications/admin':
            ensure_auction_outcomes(); rows=[dict(x) for x in load_notifications() if x.get('recipientType')=='admin']; rows.sort(key=lambda x:x.get('created',''),reverse=True)
            # Link approval notifications to their participant, including older
            # notifications that were created before participantId was stored.
            people=load_people()
            for row in rows:
                if row.get('category')!='approval': continue
                pid=str(row.get('participantId') or row.get('itemId') or '')
                if not pid.startswith('p-'):
                    msg=str(row.get('message') or '')
                    person=next((x for x in people if str(x.get('phone') or '') and str(x.get('phone')) in msg),None)
                    pid=str((person or {}).get('id') or '')
                if pid: row['participantId']=pid
            self.sendj({'notifications':rows[:300],'unread':sum(1 for x in rows if not x.get('read'))}); return
        if p=='/api/permissions':
            people=load_people(); perms=load_user_permissions(); self.sendj({'participants':[{**{k:v for k,v in x.items() if k not in ('otp','otpExpires','otpAttempts')},'permissions':participant_permissions(x.get('id'))} for x in people],'raw':perms}); return
        if p=='/api/dues':
            rows=ensure_auction_outcomes(); people={x.get('id'):x for x in load_people()}
            out=[]
            for x in rows:
                y=dict(x); y['participantName']=people.get(x.get('participantId'),{}).get('name','مشارك'); y['participantPhone']=people.get(x.get('participantId'),{}).get('phone',''); out.append(y)
            out.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'dues':out}); return
        if p=='/api/orders':
            ensure_auction_outcomes(); rows=load_orders(); rows.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'orders':rows,'active':sum(1 for x in rows if not x.get('archived')),'archived':sum(1 for x in rows if x.get('archived'))}); return
        if p=='/api/inventory/summary':
            self.sendj(inventory_summary()); return
        if p=='/api/operations':
            rows=load_operations_log(); rows.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'events':rows[:500]}); return
        if p=='/api/permissions/me':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
            if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
            self.sendj({'permissions':participant_permissions(pid)}); return
        if p=='/api/seller/ended':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
            if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
            perm=participant_permissions(pid)
            if not perm.get('sellerEndedAuctions'): self.sendj({'error':'لا توجد صلاحية لعرض المزادات المنتهية'},403); return
            phone=str(person.get('phone') or '').replace(' ',''); now=datetime.datetime.now(); out=[]
            for i in load():
                if str(i.get('ownerPhone') or '').replace(' ','')!=phone: continue
                try: ended=bool(i.get('auctionEnd')) and datetime.datetime.fromisoformat(str(i.get('auctionEnd')))<=now
                except Exception: ended=False
                if ended: out.append(public_item(i))
            self.sendj({'items':out}); return
        if p=='/api/seller/market':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
            if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
            perm=participant_permissions(pid)
            if not (perm.get('sellerMarket') or perm.get('marketSupervision')): self.sendj({'error':'لا توجد صلاحية لمتابعة السوق'},403); return
            phone=str(person.get('phone') or '').replace(' ',''); items=load(); ids={str(i.get('id')) for i in items if perm.get('marketSupervision') or str(i.get('ownerPhone') or '').replace(' ','')==phone}
            req=[x for x in load_market_requests() if str(x.get('itemId')) in ids]
            safe=[{k:v for k,v in x.items() if k not in ('ownerPhone',)} for x in req]
            self.sendj({'requests':safe}); return
        if p=='/api/negotiations':
            q=urlparse(self.path).query
            qs=parse_qs(q); item_id=(qs.get('itemId') or [''])[0]; pid=(qs.get('participantId') or [''])[0]
            with LOCK:
                a=load_negotiations()
                if item_id: a=[x for x in a if x.get('itemId')==item_id]
                if pid: a=[x for x in a if x.get('participantId')==pid]
                self.sendj({'negotiations':a}); return
        if p=='/api/backup/full':
            with LOCK: raw=create_full_backup_bytes()
            stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            self.send_response(200); self.send_header('Content-Type','application/zip'); self.send_header('Content-Disposition',f'attachment; filename=khazina_full_{stamp}.khzbackup'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p=='/api/items':
            with LOCK:
                ensure_auction_outcomes()
                self.sendj({'items':load()}); return
        if p=='/api/participants':
            with LOCK:
                people=load_people(); rows=[participant_public(x) for x in people]; active=[x for x in rows if x['approvalStatus']!='cancelled']; archived=[x for x in rows if x['approvalStatus']=='cancelled']
                active.sort(key=lambda x:(APPROVAL_STATUSES.index(x['approvalStatus']),x.get('created',''))); archived.sort(key=lambda x:x.get('archivedAt',''),reverse=True); counts={s:sum(1 for x in rows if x['approvalStatus']==s) for s in APPROVAL_STATUSES}
                self.sendj({'participants':active,'archive':archived,'total':len(active),'pending':counts['new']+counts['preliminary'],'archived':len(archived),'counts':counts}); return
        if p=='/api/participants/summary':
            with LOCK:
                people=load_people(); counts={s:sum(1 for x in people if participant_approval_status(x)==s) for s in APPROVAL_STATUSES}; active=len(people)-counts['cancelled']
                self.sendj({'total':active,'pending':counts['new']+counts['preliminary'],'approved':counts['final'],'archived':counts['cancelled'],'counts':counts}); return
        if p=='/api/participant/status':
            q=urlparse(self.path).query
            pid=(parse_qs(q).get('id') or [''])[0]
            with LOCK:
                person=next((x for x in load_people() if x.get('id')==pid),None)
                if not person: self.sendj({'found':False},404); return
                safe=participant_public(person)
                self.sendj({'found':True,'participant':safe}); return
        if p=='/api/bids':
            with LOCK:
                people={x.get('id'):x for x in load_people()}; bids=load_bids()
                for b in bids:
                    person=people.get(b.get('participantId'),{}); b['bidderName']=person.get('name','مشارك'); b['approvalStatus']=participant_approval_status(person); b['approvalLabel']=APPROVAL_LABELS[b['approvalStatus']]
                self.sendj({'bids':bids}); return
        if p=='/api/public/special-numbers':
            rows=[public_special_item(i) for i in load() if i.get('specialNumberEnabled')]
            self.sendj({'items':rows}); return
        if p=='/api/public/transitional-issues':
            rows=[]
            for i in load():
                if not i.get('transitionalIssueEnabled'): continue
                market_public=bool(i.get('forMarket') and i.get('marketApproved'))
                auction_public=bool(i.get('forAuction') and i.get('auctionApproved'))
                special_public=bool(i.get('specialNumberEnabled'))
                if not (market_public or auction_public or special_public): continue
                row=public_market_item(i) if market_public else public_item(i)
                for k in ('transitionalIssueType','transitionalPreviousIssue','transitionalNextIssue','transitionalRarity','transitionalEstimatedPopulation','transitionalReason','transitionalNotes'):
                    row[k]=i.get(k)
                row['marketPublic']=market_public; row['auctionPublic']=auction_public; row['specialPublic']=special_public
                rows.append(row)
            rows.sort(key=lambda x:str(x.get('updated') or ''), reverse=True)
            self.sendj({'items':rows}); return
        if p=='/api/public/auctions':
            with LOCK:
                ensure_auction_outcomes()
                items=[]
                now=datetime.datetime.now()
                for i in load():
                    if not (i.get('forAuction') and i.get('auctionApproved')): continue
                    public=public_item(i)
                    # V4.0.20: المزادات المنتهية تُفصل عن صفحة المزادات النشطة العامة.
                    if public.get('auctionEnded'): continue
                    items.append(public)
                items.sort(key=lambda x:str(x.get('auctionEnd') or ''))
                self.sendj({'items':items}); return
        if p=='/api/visitor/orders':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=next((x for x in load_people() if x.get('id')==pid),None)
            if not participant_can_access(person): self.sendj({'error':'الحساب غير متاح'},403); return
            ensure_auction_outcomes(); phone=str(person.get('phone') or '').replace(' ',''); labels={'new':'طلب جديد','awaiting_payment':'بانتظار السداد','paid':'تم السداد','preparing':'قيد التجهيز','ready_to_ship':'جاهز للشحن','shipped':'تم الشحن','received':'تم الاستلام','completed':'مكتمل','stalled':'متعثر','cancelled':'ملغي','returned':'مرتجع'}
            rows=[]
            for o in load_orders():
                if str(o.get('participantId') or '')!=pid and str(o.get('customerPhone') or '').replace(' ','')!=phone: continue
                first=(o.get('items') or [{}])[0]
                rows.append({'id':o.get('id'),'orderNumber':o.get('orderNumber'),'source':o.get('source'),'itemTitle':first.get('title','مقتنى'),'quantity':sum(int(x.get('quantity') or 1) for x in o.get('items') or []),'buyerTotal':o.get('total',0),'status':o.get('status'),'statusLabel':labels.get(o.get('status'),o.get('status')),'created':o.get('created'),'shippingCompany':o.get('shippingCompany'),'trackingNumber':o.get('trackingNumber'),'archived':o.get('archived',False)})
            rows.sort(key=lambda x:x.get('created') or '',reverse=True); self.sendj({'requests':rows}); return
        if p=='/api/visitor/invoice':
            qs=parse_qs(urlparse(self.path).query)
            pid=str((qs.get('participantId') or [''])[0])
            oid=str((qs.get('orderId') or [''])[0])
            person=next((x for x in load_people() if x.get('id')==pid),None)
            if not participant_can_access(person):
                self.sendj({'error':'الحساب غير متاح'},403); return
            phone=str(person.get('phone') or '').replace(' ','')
            order=next((o for o in load_orders() if str(o.get('id') or '')==oid and (str(o.get('participantId') or '')==pid or str(o.get('customerPhone') or '').replace(' ','')==phone)),None)
            if not order:
                self.sendj({'error':'الفاتورة غير موجودة'},404); return
            labels={'new':'طلب جديد','awaiting_payment':'بانتظار السداد','paid':'تم السداد','preparing':'قيد التجهيز','ready_to_ship':'جاهز للشحن','shipped':'تم الشحن','received':'تم الاستلام','completed':'مكتمل','stalled':'متعثر','cancelled':'ملغي','returned':'مرتجع'}
            items=[]
            for x in order.get('items') or []:
                items.append({'itemId':x.get('itemId'),'title':x.get('title','مقتنى'),'quantity':int(x.get('quantity') or 1),'unitPrice':float(x.get('unitPrice') or 0),'total':float(x.get('total') or 0),'image':((x.get('images') or [''])[0] or '')})
            verify=hashlib.sha256((str(order.get('id'))+'|'+str(order.get('orderNumber'))+'|NAWADER').encode('utf-8')).hexdigest()[:12].upper()
            subtotal=float(order.get('subtotal') or sum(x['total'] for x in items))
            buyer_fee=float(order.get('buyerFee') or 0)
            shipping=float(order.get('shippingFee') or order.get('deliveryFee') or 0)
            total=float(order.get('total') or subtotal+buyer_fee+shipping)
            paid=total if str(order.get('paymentStatus') or order.get('status')) in ('paid','completed','received','shipped','preparing','ready_to_ship') else float(order.get('paidAmount') or 0)
            self.sendj({'invoice':{
                'invoiceNumber':'INV-'+str(order.get('orderNumber') or order.get('id') or '').replace('NW-',''),
                'orderNumber':order.get('orderNumber'),'orderId':order.get('id'),'source':order.get('source'),
                'created':order.get('created'),'paidAt':order.get('paidAt'),'customerName':order.get('customerName') or person.get('name') or '',
                'customerPhone':order.get('customerPhone') or person.get('phone') or '',
                'sellerName':'نوادر العملات','platformName':'نوادر العملات','items':items,
                'subtotal':subtotal,'buyerFee':buyer_fee,'shippingFee':shipping,'total':total,'paid':paid,
                'balance':max(0,total-paid),'status':order.get('status'),'statusLabel':labels.get(order.get('status'),order.get('status')),
                'shippingCompany':order.get('shippingCompany') or '','trackingNumber':order.get('trackingNumber') or '',
                'verificationCode':verify
            }}); return
        if p=='/api/public/market':
            with LOCK:
                items=[public_market_item(i) for i in load() if i.get('forMarket') and i.get('marketApproved')]
                self.sendj({'items':items}); return
        if p=='/api/market/requests':
            with LOCK:
                req=load_market_requests(); req.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'requests':req}); return
        if p=='/api/subscriptions':
            with LOCK:
                a=load_subscriptions(); a.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'subscriptions':a}); return
        if p=='/api/daily-qr':
            try:
                import qrcode
                host=self.headers.get('Host') or f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
                # If admin opened localhost, QR must still point to the LAN address for phones.
                if host.startswith('localhost') or host.startswith('127.0.0.1'):
                    host=f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
                url=public_portal_url(host); im=qrcode.make(url); buf=io.BytesIO(); im.save(buf,format='PNG'); data=buf.getvalue()
                self.send_response(200); self.send_header('Content-Type','image/png'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data); return
            except Exception as e:
                self.send_error(500,'QR generation failed'); return
        if p=='/api/market-qr':
            try:
                import qrcode
                host=self.headers.get('Host') or f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
                if host.startswith('localhost') or host.startswith('127.0.0.1'):
                    host=f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
                url=public_market_url(host); im=qrcode.make(url); buf=io.BytesIO(); im.save(buf,format='PNG'); data=buf.getvalue()
                self.send_response(200); self.send_header('Content-Type','image/png'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data); return
            except Exception:
                self.send_error(500,'QR generation failed'); return
        if p=='/api/market-qr-info':
            host=self.headers.get('Host') or f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
            if host.startswith('localhost') or host.startswith('127.0.0.1'): host=f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
            self.sendj({'stable':True,'url':public_market_url(host)}); return
        if p=='/api/daily-qr-info':
            host=self.headers.get('Host') or f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
            if host.startswith('localhost') or host.startswith('127.0.0.1'): host=f'{local_ip()}:{getattr(self.server,"server_port",8080)}'
            self.sendj({'stable':True,'url':public_portal_url(host)}); return
        if p=='/daily-auction':
            # توافق مع أي QR قديم مطبوع: لا تنتهي صلاحيته بعد الآن.
            self.send_file(os.path.join(PUBLIC_DIR,'public_auction.html'),'text/html; charset=utf-8'); return
        # Robust public-auction aliases so the visitor page works even when the browser uses a clean URL.
        if p in ('/announcements','/announcements/','/announcements.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'announcements.html'),'text/html; charset=utf-8'); return
        if p in ('/account','/account/','/account.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'account.html'),'text/html; charset=utf-8'); return
        if p in ('/invoice','/invoice/','/invoice.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'invoice.html'),'text/html; charset=utf-8'); return
        if p in ('/notifications','/notifications/','/notifications.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'notifications.html'),'text/html; charset=utf-8'); return
        if p in ('/seller','/seller/','/seller_portal.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'seller_portal.html'),'text/html; charset=utf-8'); return
        if p in ('/special-numbers','/special-numbers/','/special_numbers.html'):
            if not load_settings()['visitorSections']['specialNumbers']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'special_numbers.html'),'text/html; charset=utf-8'); return
        if p in ('/transitional-issues','/transitional-issues/','/transitional_issues.html'):
            if not load_settings()['visitorSections']['transitionalIssues']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'transitional_issues.html'),'text/html; charset=utf-8'); return
        if p in ('/auction','/auction/','/public_auction.html','/public-auction'):
            if not load_settings()['visitorSections']['auction']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_auction.html'),'text/html; charset=utf-8'); return
        if p in ('/market','/market/','/public_market.html','/public-market'):
            if not load_settings()['visitorSections']['market']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_market.html'),'text/html; charset=utf-8'); return
        # لا نسمح بعرض مجلد المشروع أو الملفات الإدارية مباشرة.
        if p=='/app.js':
            if not self.require_admin(): return
            self.send_file(os.path.join(ADMIN_DIR,'app.js'),'application/javascript; charset=utf-8'); return
        if p.startswith('/uploads/'):
            rel=os.path.basename(p); full=os.path.join(UPLOAD_DIR,rel)
            if self.is_admin() or is_public_upload_url(p):
                self.send_file(full); return
            self.send_error(403,'Private image'); return
        if p in PUBLIC_STATIC:
            self.send_file(os.path.join(PUBLIC_DIR,p.lstrip('/'))); return
        if p.startswith('/assets/') or p.startswith('/icons/'):
            rel=os.path.normpath(p.lstrip('/'))
            if rel.startswith('..'): self.send_error(404); return
            self.send_file(os.path.join(SHARED_DIR,rel)); return
        self.send_error(404,'Not found'); return
    def do_POST(self):
        p=urlparse(self.path).path
        if p=='/admin-login':
            try:
                n=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(n).decode('utf-8','replace'); form=parse_qs(raw)
                username=(form.get('username') or [''])[0]; password=(form.get('password') or [''])[0]
            except Exception:
                self.login_page('تعذر قراءة بيانات الدخول.'); return
            if not verify_admin_password(username,password):
                time.sleep(0.35); self.login_page('اسم المستخدم أو كلمة المرور غير صحيحة.'); return
            token=secrets.token_urlsafe(32); ADMIN_SESSIONS[token]={'created':time.time(),'last':time.time()}
            secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
            self.send_response(302); self.send_header('Set-Cookie',f'KhazinaAdmin={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL_SECONDS}{secure}'); self.send_header('Location','/admin'); self.end_headers(); return
        if p not in PUBLIC_POST_API:
            if not self.require_admin(api=True): return
            if not self.same_origin_ok(): self.sendj({'error':'تم رفض الطلب لأسباب أمنية.'},403); return
        if p=='/api/backup/restore':
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<=0: self.sendj({'error':'اختر ملف النسخة الاحتياطية الكاملة'},400); return
                raw=self.rfile.read(n)
                with LOCK: result=restore_full_backup_bytes(raw)
                self.sendj(result); return
            except zipfile.BadZipFile:
                self.sendj({'error':'ملف النسخة الاحتياطية تالف أو ليس ملف خزينة كامل'},400); return
            except Exception as e:
                self.sendj({'error':'تعذر استعادة النسخة الكاملة: '+str(e)},400); return
        if p in ('/api/upload','/api/visitor/upload'):
            try:
                if p=='/api/visitor/upload':
                    pid=str(self.headers.get('X-Participant-Id') or '')
                    person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                    if not person: self.sendj({'error':'يجب تسجيل الدخول بحساب موثق أولًا'},403); return
                n=int(self.headers.get('Content-Length','0'))
                if n<=0 or n>50*1024*1024: self.sendj({'error':'حجم الصورة غير مناسب (الحد 50 ميجابايت)'},413); return
                ctype=(self.headers.get('Content-Type') or '').lower(); ext='.jpg'
                if 'png' in ctype: ext='.png'
                elif 'webp' in ctype: ext='.webp'
                elif 'heic' in ctype or 'heif' in ctype: ext='.heic'
                stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'); name='photo_'+stamp+ext; dst=os.path.join(UPLOAD_DIR,name); tmp=dst+'.tmp'; remain=n
                with open(tmp,'wb') as f:
                    while remain:
                        chunk=self.rfile.read(min(1024*1024,remain))
                        if not chunk: break
                        f.write(chunk); remain-=len(chunk)
                if remain: raise IOError('رفع الصورة غير مكتمل')
                os.replace(tmp,dst)
                # Reduce storage and mobile-memory pressure after upload when Pillow can decode the image.
                try:
                    from PIL import Image, ImageOps
                    im=Image.open(dst); im=ImageOps.exif_transpose(im); im.thumbnail((1800,1800))
                    if im.mode not in ('RGB','L'): im=im.convert('RGB')
                    jpg=os.path.join(UPLOAD_DIR,'photo_'+stamp+'.jpg')
                    im.save(jpg,'JPEG',quality=82,optimize=True)
                    if os.path.abspath(jpg)!=os.path.abspath(dst):
                        try: os.remove(dst)
                        except OSError: pass
                    name=os.path.basename(jpg); dst=jpg
                except Exception:
                    pass
                self.sendj({'ok':True,'url':'/uploads/'+name}); return
            except Exception as e:
                try:
                    if 'tmp' in locals() and os.path.exists(tmp): os.remove(tmp)
                except OSError: pass
                self.sendj({'error':'تعذر حفظ الصورة على الكمبيوتر: '+str(e)},500); return
        try: d=self.body()
        except Exception: self.sendj({'error':'bad json'},400); return
        with LOCK:
            if p=='/api/collectible-submissions':
                pid=str(d.get('participantId') or '')
                person=next((x for x in load_people() if str(x.get('id'))==pid),None)
                if not participant_can_transact(person): self.sendj({'error':'إرسال مقتنى يتطلب الاعتماد النهائي من الإدارة'},403); return
                country=str(d.get('country') or '').strip(); denomination=str(d.get('denomination') or '').strip()
                if not country or not denomination: self.sendj({'error':'الدولة والفئة مطلوبتان'},400); return
                front=str(d.get('frontImage') or ''); back=str(d.get('backImage') or '')
                for label,img in [('الوجه',front),('الخلف',back)]:
                    if img and not img.startswith('/uploads/') and (not img.startswith('data:image/') or len(img)>6*1024*1024): self.sendj({'error':f'صورة {label} غير صالحة أو كبيرة جدًا'},400); return
                rows=load_collectible_submissions(); now=datetime.datetime.now().isoformat()
                sid=str(d.get('id') or '')
                if sid:
                    row=next((x for x in rows if str(x.get('id'))==sid and str(x.get('participantId'))==pid),None)
                    if not row: self.sendj({'error':'السجل غير موجود أو لا تملك صلاحية تعديله'},404); return
                    if row.get('itemId') or row.get('status')=='approved': self.sendj({'error':'تم اعتماد السجل؛ اطلب من الإدارة تعديله'},409); return
                    inv=submission_inventory_values(d)
                    row.update({'country':country,'denomination':denomination,'year':str(d.get('year') or '').strip(),'issueEdition':str(d.get('issueEdition') or '').strip(),'type':str(d.get('type') or 'عملة ورقية').strip(),'condition':str(d.get('condition') or 'UNC').strip(),'serial':str(d.get('serial') or '').strip(),'notes':str(d.get('notes') or '').strip(),'desiredDestination':str(d.get('desiredDestination') or 'vault'),'frontImage':front,'backImage':back,'status':'pending','adminNote':'','updated':now,**inv})
                    save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                    add_notification('admin','','approval','✏️ تم تعديل طلب مقتنى',f"عدّل {person.get('name','عميل')} مقتنى {country} — {denomination} وأعاده للمراجعة.",'','/admin')
                    self.sendj({'ok':True,'submission':{k:v for k,v in row.items() if k not in ('frontImage','backImage')}}); return
                inv=submission_inventory_values(d)
                row={'id':'cs-'+secrets.token_hex(6),'participantId':pid,'participantName':person.get('name',''),'participantPhone':person.get('phone',''),'country':country,'denomination':denomination,'year':str(d.get('year') or '').strip(),'issueEdition':str(d.get('issueEdition') or '').strip(),'type':str(d.get('type') or 'عملة ورقية').strip(),'condition':str(d.get('condition') or 'UNC').strip(),'serial':str(d.get('serial') or '').strip(),'notes':str(d.get('notes') or '').strip(),'desiredDestination':str(d.get('desiredDestination') or 'vault'),'frontImage':front,'backImage':back,'status':'pending','adminNote':'','created':now,'updated':now,'itemId':'',**inv}
                rows.append(row); save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                add_notification('admin','','approval','🪙 طلب اعتماد مقتنى جديد',f"أرسل {person.get('name','عميل')} مقتنى {country} — {denomination} للمراجعة والاعتماد.",'','/admin')
                add_notification('participant',pid,'approval','تم استلام المقتنى للمراجعة',f'تم استلام {country} — {denomination}. الحالة الآن: قيد المراجعة.','','/account')
                append_operation('إرسال مقتنى للاعتماد',{'submissionId':row['id'],'participantId':pid,'country':country,'denomination':denomination},actor='العميل')
                self.sendj({'ok':True,'submission':{k:v for k,v in row.items() if k not in ('frontImage','backImage')}}); return
            if p=='/api/collectible-submissions/delete':
                pid=str(d.get('participantId') or ''); sid=str(d.get('id') or '')
                person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'يجب تسجيل الدخول بحساب موثق أولًا'},403); return
                rows=load_collectible_submissions(); row=next((x for x in rows if str(x.get('id'))==sid and str(x.get('participantId'))==pid),None)
                if not row: self.sendj({'error':'السجل غير موجود أو لا تملك صلاحية حذفه'},404); return
                if row.get('itemId') or row.get('status')=='approved': self.sendj({'error':'تم اعتماد السجل؛ الحذف من صلاحية الإدارة'},409); return
                rows=[x for x in rows if str(x.get('id'))!=sid]; save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                append_operation('حذف طلب مقتنى',{'submissionId':sid,'participantId':pid},actor='العميل')
                self.sendj({'ok':True}); return
            if p=='/api/collectible-submissions/status':
                sid=str(d.get('id') or ''); action=str(d.get('status') or ''); note=str(d.get('note') or '').strip()
                if action not in ('approved','needs_changes','rejected'): self.sendj({'error':'الإجراء غير صالح'},400); return
                rows=load_collectible_submissions(); row=next((x for x in rows if str(x.get('id'))==sid),None)
                if not row: self.sendj({'error':'طلب الاعتماد غير موجود'},404); return
                now=datetime.datetime.now().isoformat()
                if action=='approved' and not row.get('itemId'):
                    items=load(); item_id='k-'+secrets.token_hex(8)
                    serial=str(row.get('serial') or '').strip()
                    normalized_serial=re.sub(r'\s+','',serial).upper()
                    if normalized_serial:
                        for other in items:
                            other_serials=other.get('serials') or [other.get('serial')]
                            if not isinstance(other_serials,list): other_serials=[other_serials]
                            if normalized_serial in {re.sub(r'\s+','',str(s or '')).upper() for s in other_serials if str(s or '').strip()}:
                                self.sendj({'error':'لا يمكن الاعتماد: الرقم التسلسلي مسجل مسبقًا في المستودع'},409); return
                    inv=submission_inventory_values(row)
                    item={'id':item_id,'country':row.get('country',''),'denomination':row.get('denomination',''),'issueEdition':row.get('issueEdition',''),'year':row.get('year',''),'type':row.get('type') or 'عملة ورقية','condition':row.get('condition','UNC'),'soldQuantity':0,'damagedQuantity':0,'serial':serial,'serials':[serial] if serial else [],'frontImg':row.get('frontImage',''),'backImg':row.get('backImage',''),'notes':row.get('notes',''),'ownerName':row.get('participantName',''),'ownerPhone':row.get('participantPhone',''),'ownerParticipantId':row.get('participantId',''),'sourceSubmissionId':sid,'storageStatus':'warehouse','warehouse':'المستودع الرئيسي','forMarket':False,'marketApproved':False,'forAuction':False,'auctionApproved':False,'created':now,'updated':int(time.time()*1000),**inv}
                    items.append(item); save(items)
                    saved=next((x for x in load() if str(x.get('id'))==item_id),None)
                    snap=inventory_snapshot(saved) if saved else None
                    preserved=bool(saved and saved.get('country')==row.get('country') and saved.get('denomination')==row.get('denomination') and saved.get('frontImg','')==row.get('frontImage','') and saved.get('backImg','')==row.get('backImage','') and saved.get('inventoryClassification')==inv['inventoryClassification'] and inventory_total(saved)==inv['quantity'] and snap and snap.get('warehouse')==inv['quantity'])
                    if not preserved:
                        save([x for x in load() if str(x.get('id'))!=item_id])
                        append_save_audit({'id':item_id,'ok':False,'created':now,'reason':'submission_warehouse_verification_failed'})
                        self.sendj({'error':'تعذر التحقق من حفظ التصنيف أو الصور أو الكمية داخل المستودع؛ لم يُعتمد الطلب'},500); return
                    row['itemId']=item_id; row['warehouseVerified']=True; row['warehouseVerifiedAt']=now
                    destination=str(row.get('desiredDestination') or 'vault')
                    if destination=='market':
                        item['forMarket']=True; item['marketApproved']=False
                        # لا ينشر في السوق العام قبل تحديد سعر البيع واعتماد العرض.
                        if not item.get('marketSalePrice'): item['marketSalePrice']=0
                        save(items)
                        add_notification('participant',row.get('participantId'),'market','🛒 المقتنى جاهز لإكمال عرض السوق',
                                         f"{item.get('country','')} — {item.get('denomination','')} تم اعتماده. افتح «مقتنياتي المعتمدة» وحدد سعر البيع ليُرسل العرض للاعتماد.",item_id,'/account')
                    elif destination=='auction':
                        item['forAuction']=True; item['auctionApproved']=False; save(items)
                        add_notification('participant',row.get('participantId'),'auction','⚖ المقتنى جاهز لإعداد المزاد',
                                         f"{item.get('country','')} — {item.get('denomination','')} تم اعتماده. أكمل وقت المزاد وسعر الافتتاح والزيادة من حسابك.",item_id,'/account')
                    append_save_audit({'id':item_id,'ok':True,'country':item.get('country'),'denomination':item.get('denomination'),'created':now,'source':'collectible_submission','warehouse':snap})
                row['status']=action; row['adminNote']=note; row['updated']=now
                save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                pid=row.get('participantId'); title=f"{row.get('country','')} — {row.get('denomination','')}".strip(' —')
                if action=='approved':
                    dest=str(row.get('desiredDestination') or 'vault')
                    suffix=' وهو جاهز لإكمال بيانات السوق من «مقتنياتي المعتمدة».' if dest=='market' else (' وهو جاهز لإكمال إعداد المزاد من «مقتنياتي المعتمدة».' if dest=='auction' else '.')
                    nt=('✅ تم اعتماد المقتنى وإيداعه في المستودع',f'تم اعتماد {title} وحفظ تصنيفه وصوره وكميته في المستودع'+suffix)
                elif action=='needs_changes': nt=('✏️ يحتاج المقتنى إلى استكمال',f'طلب {title} يحتاج تعديل/استكمال بيانات.'+((' ملاحظة الإدارة: '+note) if note else ''))
                else: nt=('تم رفض طلب اعتماد المقتنى',f'لم يتم اعتماد {title}.'+((' السبب: '+note) if note else ''))
                add_notification('participant',pid,'approval',nt[0],nt[1],row.get('itemId',''),'/account')
                append_operation('تحديث طلب اعتماد مقتنى',{'submissionId':sid,'status':action,'itemId':row.get('itemId',''),'warehouseVerified':bool(row.get('warehouseVerified')),'note':note})
                saved_item=next((x for x in load() if str(x.get('id'))==str(row.get('itemId') or '')),None)
                self.sendj({'ok':True,'submission':row,'inventory':inventory_snapshot(saved_item) if saved_item else None}); return
            if p=='/api/permissions/update':
                pid=str(d.get('participantId') or ''); people=load_people()
                if not any(str(x.get('id'))==pid for x in people): self.sendj({'error':'المشارك غير موجود'},404); return
                allowed=('sellerEndedAuctions','sellerMarket','marketSupervision','auctionSupervision','ordersView','ordersManage'); perms=load_user_permissions(); current=participant_permissions(pid)
                for k in allowed:
                    if k in d: current[k]=bool(d.get(k))
                perms[pid]=current; save_json(USER_PERMISSIONS,{'users':perms}); append_operation('تحديث صلاحيات مستخدم',{'participantId':pid,'permissions':current}); self.sendj({'ok':True,'permissions':current}); return
            if p=='/api/dues/status':
                did=str(d.get('id') or ''); status=str(d.get('status') or '');
                if status not in ('unpaid','paid','cancelled'): self.sendj({'error':'حالة المستحق غير صالحة'},400); return
                rows=ensure_auction_outcomes(); row=next((x for x in rows if str(x.get('id'))==did),None)
                if not row: self.sendj({'error':'المستحق غير موجود'},404); return
                row['status']=status; row['updated']=datetime.datetime.now().isoformat();
                if status=='paid':
                    row['paidAt']=datetime.datetime.now().isoformat(); order=create_order_for_due(row); update_order_status(order,'paid','تم اعتماد السداد من المستحقات'); orders=load_orders(); orders=[order if str(x.get('id'))==str(order.get('id')) else x for x in orders]; save_json(ORDERS,{'orders':orders}); add_notification('participant',row.get('participantId'),'finance','✅ تم اعتماد السداد',f"تم اعتماد سداد مستحق مزاد {row.get('itemTitle') or ''}. أصبحت المشاركة متاحة ما لم يوجد مستحق متأخر آخر.",row.get('itemId'),'/account')
                save_json(AUCTION_DUES,{'dues':rows}); append_operation('تحديث حالة مستحق مزاد',{'dueId':did,'status':status}); self.sendj({'ok':True,'due':row}); return
            if p=='/api/owner/item/update':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية تعديله'},404); return
                if item.get('auctionSold'): self.sendj({'error':'المقتنى مباع ولا يمكن تعديل بياناته الأساسية'},409); return
                for k in ('country','denomination','issueEdition','year','type','condition','notes','frontImg','backImg'):
                    if k in d: item[k]=str(d.get(k) or '').strip()
                # الكمية لا تتغير مع التزامات قائمة.
                if 'inventoryUnitCount' in d or 'piecesPerUnit' in d:
                    round_no=int(item.get('auctionRound') or 1)
                    has_bids=any(str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==round_no for b in load_bids())
                    has_market=any(str(r.get('itemId'))==iid and str(r.get('status') or 'new') not in ('completed','cancelled','rejected') for r in load_market_requests())
                    if item.get('forMarket') or item.get('forAuction') or has_bids or has_market:
                        self.sendj({'error':'لا يمكن تغيير الكمية أثناء وجود عرض أو مزاد أو طلب قائم'},409); return
                    units=max(1,int(float(d.get('inventoryUnitCount') or item.get('inventoryUnitCount') or 1)))
                    pieces=max(1,int(float(d.get('piecesPerUnit') or item.get('piecesPerUnit') or 1)))
                    item['inventoryUnitCount']=units; item['piecesPerUnit']=pieces; item['quantity']=units*pieces; item['availableQuantity']=units*pieces
                item['updated']=int(time.time()*1000); save(items)
                append_operation('تعديل المقتنى بواسطة المالك',{'itemId':iid,'participantId':pid},actor='العميل')
                add_notification('admin','','approval','✏️ عدّل المالك بيانات مقتناه',f"{item.get('country','')} — {item.get('denomination','')}",iid,'/admin')
                self.sendj({'ok':True}); return

            if p=='/api/owner/item/delete':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية حذفه'},404); return
                round_no=int(item.get('auctionRound') or 1)
                has_bids=any(str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==round_no for b in load_bids())
                has_market=any(str(r.get('itemId'))==iid and str(r.get('status') or 'new') not in ('completed','cancelled','rejected') for r in load_market_requests())
                has_orders=any(any(str(line.get('itemId'))==iid for line in (o.get('items') or [])) for o in load_orders())
                if item.get('forMarket') or item.get('forAuction') or has_bids or has_market or has_orders or item.get('auctionSold'):
                    self.sendj({'error':'لا يمكن حذف مقتنى مرتبط بعرض أو مزاد أو طلب. اسحب العرض/ألغ المزاد وأغلق الالتزامات أولًا.'},409); return
                item['ownerArchived']=True; item['ownerArchivedAt']=datetime.datetime.now().isoformat(); item['storageStatus']='owner_removed'
                item['updated']=int(time.time()*1000); save(items)
                append_operation('حذف/أرشفة مقتنى بواسطة المالك',{'itemId':iid,'participantId':pid},actor='العميل')
                add_notification('participant',pid,'approval','تم حذف المقتنى من قائمتك',f"{item.get('country','')} — {item.get('denomination','')} حُفظ في الأرشيف الداخلي ولم يعد ظاهرًا في حسابك.",iid,'/account')
                self.sendj({'ok':True}); return

            if p=='/api/owner/market/update':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية إدارته'},404); return
                active_requests=[r for r in load_market_requests() if str(r.get('itemId'))==iid and str(r.get('status') or 'new') not in ('completed','cancelled','rejected')]
                enable=bool(d.get('enable',True))
                if not enable:
                    if active_requests: self.sendj({'error':'لا يمكن سحب العرض لوجود طلب شراء أو تفاوض قائم'},409); return
                    item['forMarket']=False; item['marketApproved']=False; item['updated']=int(time.time()*1000); save(items)
                    append_operation('سحب عرض السوق بواسطة المالك',{'itemId':iid,'participantId':pid},actor='العميل')
                    self.sendj({'ok':True}); return
                price=max(0,float(d.get('marketSalePrice') or item.get('marketSalePrice') or 0))
                qty=max(1,int(float(d.get('availableQuantity') or item.get('availableQuantity') or 1)))
                max_qty=max(1,int(item.get('quantity') or item.get('availableQuantity') or qty))
                item['marketSalePrice']=price; item['availableQuantity']=min(qty,max_qty)
                item['marketNegotiationEnabled']=bool(d.get('marketNegotiationEnabled',item.get('marketNegotiationEnabled',False)))
                item['marketNegotiationPercent']=max(0,min(50,float(d.get('marketNegotiationPercent') or item.get('marketNegotiationPercent') or 0)))
                was_approved=bool(item.get('marketApproved'))
                item['forMarket']=True
                if not was_approved:
                    item['marketApproved']=False
                    add_notification('admin','','approval','🛒 طلب عرض مقتنى في السوق',f"{item.get('country','')} — {item.get('denomination','')} بسعر {price:g} ر.س",iid,'/admin')
                item['updated']=int(time.time()*1000); save(items)
                append_operation('إدارة السوق بواسطة المالك',{'itemId':iid,'participantId':pid,'price':price,'approved':was_approved},actor='العميل')
                self.sendj({'ok':True,'pendingApproval':not was_approved}); return

            if p=='/api/owner/auction/update':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية إدارته'},404); return
                if item.get('auctionSold') or str(item.get('auctionOutcome') or '')=='sold':
                    self.sendj({'error':'المزاد مباع ومغلق نهائيًا'},409); return
                round_no=int(item.get('auctionRound') or 1)
                bids=[b for b in load_bids() if str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==round_no]
                if not bids:
                    opening=max(0,float(d.get('auctionOpeningPrice') or item.get('auctionOpeningPrice') or item.get('auctionStartPrice') or 0))
                    item['auctionOpeningPrice']=opening; item['auctionStartPrice']=opening
                    if not item.get('auctionCurrentPrice'): item['auctionCurrentPrice']=opening
                item['auctionBidStep']=max(.01,float(d.get('auctionBidStep') or item.get('auctionBidStep') or 1))
                item['auctionTargetPrice']=max(0,float(d.get('auctionTargetPrice') or item.get('auctionTargetPrice') or 0))
                item['auctionAdditionalTerms']=str(d.get('auctionAdditionalTerms') or item.get('auctionAdditionalTerms') or '').strip()[:1000]
                if d.get('auctionEnd'): item['auctionEnd']=str(d.get('auctionEnd')).strip()
                was_approved=bool(item.get('auctionApproved'))
                item['forAuction']=True
                if not was_approved:
                    item['auctionApproved']=False
                    add_notification('admin','','approval','⚖ طلب إدخال مقتنى للمزاد',f"{item.get('country','')} — {item.get('denomination','')}",iid,'/admin')
                item['updated']=int(time.time()*1000); save(items)
                append_operation('إدارة المزاد بواسطة المالك',{'itemId':iid,'participantId':pid,'bidCount':len(bids),'approved':was_approved},actor='العميل')
                self.sendj({'ok':True,'openingLocked':bool(bids),'pendingApproval':not was_approved}); return

            if p=='/api/owner/auction/cancel':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or ''); reason=str(d.get('reason') or '').strip()
                person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية إدارته'},404); return
                if item.get('auctionSold') or str(item.get('auctionOutcome') or '')=='sold':
                    self.sendj({'error':'المزاد الناجح مغلق ولا يمكن إلغاؤه'},409); return
                round_no=int(item.get('auctionRound') or 1)
                bids=[b for b in load_bids() if str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==round_no]
                if bids and not reason: self.sendj({'error':'سبب الإلغاء إلزامي لوجود مزايدات'},400); return
                item['forAuction']=False; item['auctionApproved']=False; item['auctionCancelledAt']=datetime.datetime.now().isoformat(); item['auctionCancelReason']=reason or 'إلغاء بواسطة المالك'
                item['updated']=int(time.time()*1000); save(items)
                seen=set()
                for b in bids:
                    bidder=str(b.get('participantId') or '')
                    if bidder and bidder not in seen:
                        seen.add(bidder); add_notification('participant',bidder,'auction','تم إلغاء المزاد',f"أُلغي مزاد {item.get('country','')} — {item.get('denomination','')}. السبب: {reason or 'إلغاء بواسطة المالك'}",iid,'/auction')
                add_notification('admin','','auction','⛔ ألغى المالك مزاده',f"{item.get('country','')} — {item.get('denomination','')}. {reason}",iid,'/admin')
                append_operation('إلغاء المزاد بواسطة المالك',{'itemId':iid,'participantId':pid,'reason':reason,'bidCount':len(bids)},actor='العميل')
                self.sendj({'ok':True}); return

            if p=='/api/notifications/read':
                pid=str(d.get('participantId') or ''); nid=str(d.get('id') or ''); person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير مفعل أو موقوف'},403); return
                rows=load_notifications(); changed=False
                for x in rows:
                    if x.get('recipientType')=='participant' and str(x.get('recipientId'))==pid and (not nid or str(x.get('id'))==nid): x['read']=True; changed=True
                if changed: save_json(NOTIFICATIONS,{'notifications':rows})
                self.sendj({'ok':True}); return
            if p=='/api/notifications/admin/read':
                nid=str(d.get('id') or ''); rows=load_notifications(); changed=False
                for x in rows:
                    if x.get('recipientType')=='admin' and (not nid or str(x.get('id'))==nid): x['read']=True; changed=True
                if changed: save_json(NOTIFICATIONS,{'notifications':rows})
                self.sendj({'ok':True}); return
            if p=='/api/order/update':
                oid=str(d.get('id') or ''); status=str(d.get('status') or ''); rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==oid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                if row.get('archived') and status not in ('completed','returned'): self.sendj({'error':'الطلب المكتمل مؤرشف ولا يعاد للخلف إلا كمرتجع'},409); return
                if 'shippingCompany' in d: row['shippingCompany']=str(d.get('shippingCompany') or '').strip()
                if 'trackingNumber' in d: row['trackingNumber']=str(d.get('trackingNumber') or '').strip()
                try: update_order_status(row,status,str(d.get('note') or ''))
                except ValueError as e: self.sendj({'error':str(e)},400); return
                if status=='paid' and row.get('source')=='auction':
                    dues=load_auction_dues(); due=next((x for x in dues if str(x.get('id'))==str(row.get('sourceId'))),None)
                    if due:
                        due['status']='paid'; due['paidAt']=datetime.datetime.now().isoformat(); due['updated']=due['paidAt']; save_json(AUCTION_DUES,{'dues':dues})
                        add_notification('participant',due.get('participantId'),'finance','✅ تم اعتماد السداد',f"تم اعتماد سداد الطلب {row.get('orderNumber')}. عادت أهلية المشاركة وفق النظام.",due.get('itemId'),'/account')
                save_json(ORDERS,{'orders':rows}); append_operation('تحديث طلب وشحن',{'orderId':oid,'orderNumber':row.get('orderNumber'),'status':status})
                if row.get('participantId'): add_notification('participant',row.get('participantId'),'order','تحديث حالة الطلب',f"الطلب {row.get('orderNumber')} أصبح: {status}",'', '/account')
                self.sendj({'ok':True,'order':row}); return
            if p=='/api/order/shipping':
                oid=str(d.get('id') or ''); rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==oid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                row['shippingCompany']=str(d.get('shippingCompany') or '').strip(); row['trackingNumber']=str(d.get('trackingNumber') or '').strip(); row['updated']=datetime.datetime.now().isoformat(); save_json(ORDERS,{'orders':rows}); self.sendj({'ok':True,'order':row}); return
            if p=='/api/inventory/return-resolution':
                iid=str(d.get('itemId') or ''); action=str(d.get('action') or '')
                if action not in ('warehouse','damaged'): self.sendj({'error':'اختر إعادة المرتجع للمستودع أو تسجيله تالفًا'},400); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                orders=load_orders(); affected=[]; physical=0; now=datetime.datetime.now().isoformat()
                for order in orders:
                    if order.get('status')!='returned': continue
                    lines=[line for line in order.get('items') or [] if str(line.get('itemId'))==iid]
                    if not lines: continue
                    physical+=sum(order_line_physical(line,item) for line in lines); affected.append(order.get('id'))
                    order['status']='cancelled'; order['returnResolution']=action; order['returnResolvedAt']=now; order['updated']=now
                    order.setdefault('history',[]).append({'status':'cancelled','at':now,'note':'إعادة المرتجع للمستودع' if action=='warehouse' else 'اعتماد المرتجع كتالف/مفقود'})
                if not affected: self.sendj({'error':'لا توجد كمية مرتجعة معلقة لهذا المقتنى'},409); return
                item['marketApproved']=False; item['auctionApproved']=False
                if action=='damaged': item['damagedQuantity']=min(inventory_total(item),inventory_int(item.get('damagedQuantity'),0)+physical)
                item['updated']=int(datetime.datetime.now().timestamp()*1000)
                save(items); save_json(ORDERS,{'orders':orders}); append_operation('معالجة مرتجع',{'itemId':iid,'action':action,'quantity':physical,'orders':affected})
                self.sendj({'ok':True,'itemId':iid,'action':action,'quantity':physical,'inventory':inventory_snapshot(item,orders)}); return
            if p=='/api/inventory/repair-approved-submissions':
                self.sendj(repair_approved_submission_inventory()); return
            if p=='/api/subscription/add':
                typ=str(d.get('type','daily')).strip(); customer=str(d.get('customer','')).strip(); note=str(d.get('note','')).strip(); amount=float(d.get('amount') or 0)
                if typ not in {'daily','seasonal','package'}: self.sendj({'error':'نوع الاشتراك غير صالح'},400); return
                if amount<=0: self.sendj({'error':'أدخل مبلغ اشتراك صحيح'},400); return
                row={'id':'s-'+secrets.token_hex(6),'type':typ,'customer':customer,'amount':amount,'note':note,'created':datetime.datetime.now().isoformat()}
                a=load_subscriptions(); a.append(row); save_json(SUBSCRIPTIONS,{'subscriptions':a}); self.sendj({'ok':True,'subscription':row}); return
            if p=='/api/special/request':
                pid=str(d.get('participantId') or ''); person=next((x for x in load_people() if str(x.get('id'))==pid),None)
                if not participant_can_transact(person): self.sendj({'error':'الشراء والتفاوض يتطلبان الاعتماد النهائي من الإدارة'},403); return
                item_id=str(d.get('itemId') or ''); action=str(d.get('action') or 'buy'); item=next((i for i in load() if str(i.get('id'))==item_id and i.get('specialNumberEnabled')),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لم يعد ضمن الأرقام المميزة'},404); return
                price=special_sale_price(item)
                if not (item.get('forMarket') and item.get('marketApproved') and price>0): self.sendj({'error':'هذا المقتنى معروض للتعريف حاليًا وليس للبيع'},409); return
                pool=special_serial_pool(item); available=special_available_serials(item); selected=d.get('selectedSerials') or []
                if not isinstance(selected,list): selected=[selected]
                selected=list(dict.fromkeys(str(x).strip() for x in selected if str(x).strip()))
                if pool:
                    if not selected: self.sendj({'error':'اختر الرقم أو الأرقام التي ترغب في شرائها'},400); return
                    bad=[x for x in selected if x not in available]
                    if bad: self.sendj({'error':'بعض الأرقام المختارة لم تعد متاحة: '+', '.join(bad)},409); return
                    qty=len(selected)
                else:
                    qty=max(1,int(d.get('quantity') or 1)); avail=max(0,int(item.get('marketQuantity') or item.get('quantity') or 1)-int(item.get('marketSoldQuantity') or 0))
                    if qty>avail: self.sendj({'error':f'الكمية المتاحة حاليًا {avail}'},409); return
                base=round(price*qty,2); offered=float(d.get('offeredAmount') or 0)
                if action=='offer':
                    if not item.get('marketNegotiationEnabled'): self.sendj({'error':'التفاوض غير مفعّل لهذا المقتنى'},409); return
                    pct=float(item.get('marketNegotiationPercent') or 0); minimum=base*(1-pct/100)
                    if offered<=0 or offered+1e-9<minimum: self.sendj({'error':f'أقل عرض تفاوض مسموح {minimum:.2f} ر.س'},409); return
                else: offered=base
                fee_pct=float(load_settings().get('buyerFeePercent') or 0); fee=round((offered if action=='offer' else base)*fee_pct/100,2); total=round((offered if action=='offer' else base)+fee,2); now=datetime.datetime.now(); reserve_until=now+datetime.timedelta(minutes=30)
                row={'id':'m-'+secrets.token_hex(6),'itemId':item_id,'itemTitle':item.get('marketTitle') or item_title(item),'ownerName':item.get('ownerName') or 'الإدارة / غير محدد','ownerPhone':item.get('ownerPhone') or '','participantId':pid,'marketOfferType':item.get('marketOfferType') or 'single','unitPrice':price,'name':person.get('name',''),'phone':person.get('phone',''),'action':action,'quantity':qty,'selectedSerials':selected,'listedAmount':base,'offeredAmount':offered,'buyerFeePercent':fee_pct,'buyerFeeAmount':fee,'buyerTotal':total,'status':'pending','sourcePage':'special_numbers','images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'reservedUntil':reserve_until.isoformat(),'created':now.isoformat()}
                a=load_market_requests(); a.append(row); save_json(MARKET_REQUESTS,{'requests':a}); add_notification('admin','','market','🛒 طلب من صفحة الأرقام المميزة',f"{person.get('name','عميل')} طلب {item_title(item)}"+((' — الأرقام: '+', '.join(selected)) if selected else f' — الكمية: {qty}'),'','/admin'); add_notification('participant',pid,'order','تم تسجيل طلبك',f"تم حجز اختيارك من {item_title(item)} مؤقتًا وإرسال الطلب للإدارة.",item_id,'/account'); self.sendj({'ok':True,'request':row}); return
            if p=='/api/market/request':
                item_id=str(d.get('itemId','')); name=str(d.get('name','')).strip(); phone=''.join(ch for ch in str(d.get('phone','')) if ch.isdigit() or ch=='+')
                action=str(d.get('action','buy')); qty=max(1,int(d.get('quantity') or 1)); offered=float(d.get('offeredAmount') or 0)
                pid=str(d.get('participantId') or ''); people=load_people(); person=next((x for x in people if str(x.get('id'))==pid),None) if pid else next((x for x in people if str(x.get('phone') or '').replace(' ','')==phone.replace(' ','')),None)
                if not participant_can_transact(person): self.sendj({'error':'الشراء والتفاوض يتطلبان تسجيل الحساب ثم الاعتماد النهائي من الإدارة'},403); return
                pid=str(person.get('id')); name=str(person.get('name') or name); phone=str(person.get('phone') or phone)
                item=next((i for i in load() if str(i.get('id'))==item_id and i.get('forMarket') and i.get('marketApproved')),None)
                if not item: self.sendj({'error':'العرض غير متاح في السوق'},404); return
                if not name or len(''.join(ch for ch in phone if ch.isdigit()))<7: self.sendj({'error':'الاسم ورقم الجوال الصحيح مطلوبان'},400); return
                _,_,reserved=item_order_quantities(item.get('id'),item=item); per_unit=market_physical_per_unit(item)
                reserved_units=(reserved.get('market',0)+per_unit-1)//per_unit
                avail=max(0,int(item.get('marketQuantity') or item.get('quantity') or 1)-int(item.get('marketSoldQuantity') or 0)-reserved_units)
                if avail<=0: self.sendj({'error':'نفدت الكمية المتاحة'},409); return
                offer_type=str(item.get('marketOfferType') or 'single')
                if qty>avail: self.sendj({'error':f'الكمية المتاحة حاليًا {avail}'},409); return
                # V2.8: marketQuantity is always the number of sellable units (sets/bundles/pieces).
                # marketSalePrice is the price of ONE selected selling unit. This keeps cart totals predictable.
                if item.get('marketPriceUnit'):
                    unit=float(item.get('marketSalePrice') or 0)
                elif offer_type=='set' and float(item.get('marketUnitPrice') or 0)>0:
                    # Compatibility with V2.7 set records where the intended set price was entered in unit price.
                    unit=float(item.get('marketUnitPrice') or 0)
                else:
                    unit=float(item.get('marketSalePrice') or item.get('marketUnitPrice') or 0)
                if unit<=0: self.sendj({'error':'سعر وحدة البيع غير محدد'},409); return
                base=unit*qty
                if action=='offer':
                    if not item.get('marketNegotiationEnabled'): self.sendj({'error':'التفاوض غير مفعّل لهذا العرض'},409); return
                    pct=float(item.get('marketNegotiationPercent') or 0); minimum=base*(1-pct/100)
                    if offered<=0 or offered+1e-9<minimum: self.sendj({'error':f'أقل عرض تفاوض مسموح {minimum:.2f} ر.س'},409); return
                else: offered=base
                fee_pct=float(load_settings().get('buyerFeePercent') or 0); fee=(offered if action=='offer' else base)*fee_pct/100; total=(offered if action=='offer' else base)+fee
                row={'id':'m-'+secrets.token_hex(6),'itemId':item_id,'itemTitle':item.get('marketTitle') or ((item.get('country') or '')+' — '+(item.get('denomination') or '')),'ownerName':item.get('ownerName') or 'الإدارة / غير محدد','ownerPhone':item.get('ownerPhone') or '','participantId':pid,'marketOfferType':item.get('marketOfferType') or 'single','unitPrice':unit,'name':name,'phone':phone,'action':action,'quantity':qty,'listedAmount':base,'offeredAmount':offered,'buyerFeePercent':fee_pct,'buyerFeeAmount':round(fee,2),'buyerTotal':round(total,2),'status':'pending','images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'created':datetime.datetime.now().isoformat()}
                a=load_market_requests(); a.append(row); save_json(MARKET_REQUESTS,{'requests':a})
                chk=next((x for x in load_market_requests() if x.get('id')==row['id']),None)
                if not chk: self.sendj({'error':'تعذر التحقق من تسجيل طلب السوق'},500); return
                self.sendj({'ok':True,'request':chk}); return
            if p=='/api/market/request/respond':
                rid=str(d.get('id','')); status=str(d.get('status','')).strip(); allowed={'accepted','rejected','shipped','completed','pending'}
                if status not in allowed: self.sendj({'error':'حالة الطلب غير صالحة'},400); return
                a=load_market_requests(); row=next((x for x in a if x.get('id')==rid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                previous=row.get('status')
                if status=='shipped':
                    row['shippingCompany']=str(d.get('shippingCompany') or '').strip(); row['trackingNumber']=str(d.get('trackingNumber') or '').strip(); row['shippedAt']=datetime.datetime.now().isoformat()
                if previous=='completed' and status!='completed': self.sendj({'error':'الطلب المكتمل لا يمكن إعادته لحالة سابقة'},409); return
                row['status']=status; row['updated']=datetime.datetime.now().isoformat();
                order=create_order_for_market(row) if status=='accepted' else next((o for o in load_orders() if str(o.get('sourceId'))==rid and o.get('source')=='market'),None)
                if order and status in ('completed','returned','cancelled'):
                    update_order_status(order,status,'تحديث من طلب السوق'); orders=load_orders(); target=next((o for o in orders if str(o.get('id'))==str(order.get('id'))),None)
                    if target:
                        target.update(order); save_json(ORDERS,{'orders':orders})
                if status=='completed' and row.get('selectedSerials'):
                    items=load(); item=next((i for i in items if str(i.get('id'))==str(row.get('itemId'))),None)
                    if item:
                        done=list(item.get('marketSoldSerials') or [])
                        for sn in row.get('selectedSerials') or []:
                            if sn not in done: done.append(sn)
                        item['marketSoldSerials']=done; item['updated']=int(datetime.datetime.now().timestamp()*1000); save(items)
                save_json(MARKET_REQUESTS,{'requests':a}); self.sendj({'ok':True,'request':row}); return
            if p=='/api/auction/cancel':
                iid=str(d.get('id') or '').strip(); reason=str(d.get('reason') or '').strip()
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'ok':False,'error':'المزاد غير موجود'},404); return
                if not (item.get('forAuction') and item.get('auctionApproved')): self.sendj({'ok':False,'error':'المزاد غير نشط أو غير معتمد'},409); return
                if str(item.get('auctionOutcome') or '')=='sold': self.sendj({'ok':False,'error':'المزاد الناجح لا يُلغى؛ استخدم الاستثناء الموثق'},409); return
                try:
                    enddt=datetime.datetime.fromisoformat(str(item.get('auctionEnd') or ''))
                    if enddt<=datetime.datetime.now(): self.sendj({'ok':False,'error':'المزاد منتهٍ بالفعل'},409); return
                except Exception: pass
                rnd=int(item.get('auctionRound') or 1); round_bids=[b for b in load_bids() if str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==rnd]
                if round_bids and not reason: self.sendj({'ok':False,'error':'سبب الإلغاء مطلوب عند وجود مزايدات'},400); return
                if not reason: reason='إلغاء إداري قبل وجود مزايدات'
                now=datetime.datetime.now(); nowiso=now.isoformat(); notified=set()
                for b in round_bids:
                    pid=str(b.get('participantId') or '')
                    if pid and pid not in notified:
                        add_notification('participant',pid,'auction','⛔ تم إلغاء المزاد',f"تم إلغاء مزاد {item_title(item)} من الإدارة. السبب: {reason}. جميع المزايدات في الجولة أُغلقت دون بيع.",iid,'/auction'); notified.add(pid)
                history=list(item.get('auctionHistory') or [])
                history.append({'round':rnd,'event':'cancelled_by_admin','reason':reason,'bidCount':len(round_bids),'finalPrice':item.get('auctionCurrentPrice',0),'at':nowiso})
                item['auctionHistory']=history; item['auctionOutcome']='cancelled'; item['auctionCancelReason']=reason; item['auctionCancelledAt']=nowiso
                item['auctionApproved']=False; item['forAuction']=False; item['forMarket']=False; item['marketApproved']=False
                item['adminLocation']='warehouse'; item['inWarehouse']=True; item['warehouseAvailable']=True; item['locationUpdatedAt']=nowiso; item['updated']=int(now.timestamp()*1000)
                save(items); append_operation('إلغاء مزاد نشط',{'itemId':iid,'auctionRound':rnd,'reason':reason,'bidCount':len(round_bids),'notifiedCount':len(notified)})
                add_notification('admin','','auction','⛔ تم إلغاء المزاد',f"{item_title(item)} — {reason}",iid,'/admin')
                self.sendj({'ok':True,'item':item,'bidCount':len(round_bids),'notifiedCount':len(notified)}); return
            if p=='/api/auction/quick-edit':
                iid=str(d.get('id') or '').strip(); items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'ok':False,'error':'المزاد غير موجود'},404); return
                if not (item.get('forAuction') and item.get('auctionApproved')): self.sendj({'ok':False,'error':'المقتنى ليس في مزاد نشط معتمد'},409); return
                if str(item.get('auctionOutcome') or '')=='sold': self.sendj({'ok':False,'error':'المزاد الناجح مغلق ولا يمكن تعديل جولته'},409); return
                old_end=str(item.get('auctionEnd') or '').strip()
                try: old_end_dt=datetime.datetime.fromisoformat(old_end) if old_end else None
                except Exception: old_end_dt=None
                now=auction_local_now()
                if old_end_dt and old_end_dt<=now: self.sendj({'ok':False,'error':'انتهت الجولة بالفعل؛ استخدم إجراءات المزادات المنتهية'},409); return
                new_end=str(d.get('auctionEnd') or '').strip()
                if not new_end: self.sendj({'ok':False,'error':'موعد انتهاء المزاد مطلوب'},400); return
                try: new_end_dt=datetime.datetime.fromisoformat(new_end)
                except Exception: self.sendj({'ok':False,'error':'صيغة موعد انتهاء المزاد غير صحيحة'},400); return
                if new_end_dt<=now: self.sendj({'ok':False,'error':'موعد انتهاء المزاد الجديد يجب أن يكون في المستقبل'},409); return
                try: step=float(d.get('auctionBidStep'))
                except Exception: step=0
                if step<=0: self.sendj({'ok':False,'error':'قيمة الزيادة يجب أن تكون أكبر من صفر'},400); return
                try: target=float(d.get('auctionTargetPrice'))
                except Exception: target=-1
                if target<0: self.sendj({'ok':False,'error':'حد البيع لا يمكن أن يكون سالبًا'},400); return
                rnd=int(item.get('auctionRound') or 1); bids=load_bids(); round_bids=[b for b in bids if str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==rnd]
                opening=float(item.get('auctionOpeningPrice') or item.get('auctionStartPrice') or 0)
                if 'auctionOpeningPrice' in d:
                    try: requested_opening=float(d.get('auctionOpeningPrice') or 0)
                    except Exception: requested_opening=-1
                    if requested_opening<0: self.sendj({'ok':False,'error':'سعر الافتتاح لا يمكن أن يكون سالبًا'},400); return
                    if round_bids and abs(requested_opening-opening)>1e-9: self.sendj({'ok':False,'error':'لا يمكن تغيير سعر الافتتاح بعد تسجيل أول مزايدة'},409); return
                    opening=requested_opening
                before={'auctionEnd':old_end,'auctionOpeningPrice':float(item.get('auctionOpeningPrice') or item.get('auctionStartPrice') or 0),'auctionBidStep':float(item.get('auctionBidStep') or 1),'auctionTargetPrice':float(item.get('auctionTargetPrice') if item.get('auctionTargetPrice') not in (None,'') else auction_target(item)),'auctionAdditionalTerms':str(item.get('auctionAdditionalTerms') or '')}
                terms=str(d.get('auctionAdditionalTerms') or '').strip()[:1000]
                item['auctionEnd']=new_end; item['auctionOpeningPrice']=opening; item['auctionBidStep']=step; item['auctionTargetPrice']=target; item['auctionAdditionalTerms']=terms; item['updated']=int(now.timestamp()*1000)
                changes=[]
                labels={'auctionEnd':'موعد الانتهاء','auctionOpeningPrice':'سعر الافتتاح','auctionBidStep':'قيمة الزيادة','auctionTargetPrice':'حد البيع','auctionAdditionalTerms':'الشروط الإضافية'}
                after={'auctionEnd':new_end,'auctionOpeningPrice':opening,'auctionBidStep':step,'auctionTargetPrice':target,'auctionAdditionalTerms':terms}
                for k in after:
                    if str(before.get(k))!=str(after.get(k)): changes.append(k)
                history=item.get('auctionEditHistory') or []
                if not isinstance(history,list): history=[]
                history.append({'at':now.isoformat(),'round':rnd,'before':before,'after':after,'changed':changes,'bidCount':len(round_bids),'actor':'admin'})
                item['auctionEditHistory']=history[-50:]
                save(items)
                notified=set()
                if round_bids and changes:
                    title=item_title(item)
                    public_changes=[]
                    if 'auctionEnd' in changes: public_changes.append('موعد انتهاء المزاد')
                    if 'auctionBidStep' in changes: public_changes.append('قيمة الزيادة للمزايدات القادمة')
                    if 'auctionTargetPrice' in changes: public_changes.append('إعدادات البيع الإدارية')
                    if 'auctionAdditionalTerms' in changes: public_changes.append('الشروط الإضافية')
                    msg='تم تحديث '+(' و'.join(public_changes) if public_changes else 'إعدادات المزاد')+f' في {title}. مزايداتك المسجلة محفوظة كما هي.'
                    for b in round_bids:
                        pid=str(b.get('participantId') or '')
                        if pid and pid not in notified:
                            add_notification('participant',pid,'auction','⚙️ تم تحديث إعدادات المزاد',msg,iid,'/auction#'+iid); notified.add(pid)
                append_operation('تعديل مزاد نشط',{'itemId':iid,'round':rnd,'changed':changes,'before':before,'after':after,'bidCount':len(round_bids)})
                self.sendj({'ok':True,'item':item,'changed':changes,'bidCount':len(round_bids),'notifiedCount':len(notified)}); return
            if p=='/api/auction/exception':
                iid=str(d.get('id','')).strip(); reason=str(d.get('reason','')).strip(); note=str(d.get('note','')).strip()
                allowed={'non_payment','bidder_withdrawal','winner_ineligible','admin_exception','other'}
                if not iid: self.sendj({'error':'رقم المقتنى مطلوب'},400); return
                if reason not in allowed: self.sendj({'error':'سبب الاستثناء غير صالح'},400); return
                if reason=='other' and not note: self.sendj({'error':'اكتب سبب الاستثناء'},400); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                if str(item.get('auctionOutcome') or '')!='sold': self.sendj({'error':'زر الاستثناء مخصص للمزاد الناجح فقط'},409); return
                rnd=int(item.get('auctionRound') or 1)
                dues=load_auction_dues(); due=next((x for x in dues if str(x.get('itemId'))==iid and int(x.get('auctionRound') or 1)==rnd),None)
                orders=load_orders(); order=None
                if due and due.get('orderId'): order=next((x for x in orders if str(x.get('id'))==str(due.get('orderId'))),None)
                if not order and item.get('auctionOrderId'): order=next((x for x in orders if str(x.get('id'))==str(item.get('auctionOrderId'))),None)
                # A paid or fulfilled sale is no longer a simple auction exception; it must use the return/refund flow.
                if due and str(due.get('status') or '')=='paid': self.sendj({'error':'تم سداد المزاد؛ لا يمكن فتحه كاستثناء. استخدم مسار المرتجع/الإلغاء المالي.'},409); return
                if order:
                    status=str(order.get('status') or '')
                    if order.get('paymentStatus')=='paid' or status in ('paid','preparing','ready_to_ship','shipped','received','completed','returned'):
                        self.sendj({'error':'بدأ تنفيذ البيع أو تم السداد؛ لا يمكن إعادة فتح المزاد من الاستثناء.'},409); return
                now=datetime.datetime.now().isoformat()
                if due:
                    due['status']='cancelled'; due['cancelledAt']=now; due['cancelReason']=reason; due['cancelNote']=note; due['updated']=now
                    save_json(AUCTION_DUES,{'dues':dues})
                if order:
                    order['status']='cancelled'; order['archived']=True; order['archivedAt']=now; order['updated']=now
                    order.setdefault('history',[]).append({'status':'cancelled','at':now,'note':'استثناء مزاد ناجح: '+reason+((' — '+note) if note else '')})
                    save_json(ORDERS,{'orders':orders})
                history=list(item.get('auctionHistory') or [])
                history.append({'round':rnd,'event':'exception','reason':reason,'note':note,'winnerParticipantId':item.get('auctionWinnerParticipantId'),'winningAmount':item.get('auctionWinningAmount',item.get('auctionCurrentPrice',0)),'at':now})
                item['auctionHistory']=history
                item['auctionOutcome']='exception'; item['auctionExceptionReason']=reason; item['auctionExceptionNote']=note; item['auctionExceptionAt']=now
                item['auctionApproved']=False; item['updated']=int(datetime.datetime.now().timestamp()*1000)
                save(items)
                append_operation('استثناء مزاد ناجح',{'itemId':iid,'auctionRound':rnd,'reason':reason,'note':note})
                add_notification('admin','','auction','تم اعتماد استثناء مزاد ناجح',f"{item_title(item)} — {reason}"+(f" — {note}" if note else ''),iid,'/admin')
                self.sendj({'ok':True,'item':item,'orderId':order.get('id') if order else '','dueId':due.get('id') if due else ''}); return
            if p=='/api/auction/relaunch':
                iid=str(d.get('id','')); end=str(d.get('auctionEnd','')).strip()
                if not iid or not end: self.sendj({'error':'رقم المقتنى وموعد انتهاء المزاد مطلوبان'},400); return
                try:
                    enddt=datetime.datetime.fromisoformat(end)
                    if enddt<=datetime.datetime.now(): self.sendj({'error':'اختر موعد انتهاء جديدًا في المستقبل'},400); return
                except Exception: self.sendj({'error':'تاريخ انتهاء المزاد غير صالح'},400); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                if str(item.get('auctionOutcome') or '')=='sold': self.sendj({'error':'المزاد الناجح مغلق نهائيًا. اعتمد استثناء موثق أولًا إذا لم يكتمل البيع.'},409); return
                # V3.8: preserve a permanent snapshot of the completed round before relaunching.
                old_round=int(item.get('auctionRound') or 1)
                round_bids=[b for b in load_bids() if str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==old_round]
                history=list(item.get('auctionHistory') or [])
                history.append({'round':old_round,'auctionEnd':item.get('auctionEnd'),'openingPrice':item.get('auctionOpeningPrice',item.get('auctionStartPrice',0)),'bidStep':item.get('auctionBidStep',1),'targetPrice':item.get('auctionTargetPrice',auction_target(item)),'finalPrice':item.get('auctionCurrentPrice',0),'bidCount':len(round_bids),'targetReached':float(item.get('auctionCurrentPrice') or 0)>=auction_target(item),'closedAt':datetime.datetime.now().isoformat()})
                item['auctionHistory']=history
                item['auctionRound']=old_round+1
                # A physical collectible cannot be actively allocated to market and auction at the same time.
                # Preserve its auction history, but stop the market listing before publishing the new round.
                item['forMarket']=False; item['marketApproved']=False
                item['auctionEnd']=end; item['forAuction']=True; item['auctionApproved']=bool(d.get('auctionApproved',True)); item['auctionCurrentPrice']=0
                item['adminLocation']='auction'; item['inWarehouse']=False; item['warehouseAvailable']=False
                item['reauctionedAt']=datetime.datetime.now().isoformat(); item['updated']=int(datetime.datetime.now().timestamp()*1000)
                for key in ('auctionOpeningPrice','auctionBidStep','auctionTargetPrice','negotiationEnabled','negotiationPercent'):
                    if key in d: item[key]=d[key]
                save(items); append_operation('إعادة إدراج مزاد',{'itemId':iid,'newRound':item['auctionRound'],'auctionEnd':end}); self.sendj({'ok':True,'auctionRound':item['auctionRound'],'item':item}); return
            if p=='/api/visitor/receive':
                rid=str(d.get('id','')); pid=str(d.get('participantId','')); person=next((x for x in load_people() if x.get('id')==pid and x.get('verified') and not x.get('blocked')),None)
                if not person: self.sendj({'error':'الحساب غير موثق'},403); return
                rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==rid),None); phone=str(person.get('phone') or '').replace(' ','')
                if not row or (str(row.get('participantId') or '')!=pid and str(row.get('customerPhone') or '').replace(' ','')!=phone): self.sendj({'error':'الطلب غير موجود'},404); return
                if row.get('status')!='shipped': self.sendj({'error':'لا يمكن تأكيد الاستلام قبل تسجيل الشحن'},409); return
                update_order_status(row,'received','أكد العميل الاستلام'); save_json(ORDERS,{'orders':rows}); append_operation('تأكيد استلام العميل',{'orderId':rid},actor='العميل')
                self.sendj({'ok':True,'request':row}); return
            if p=='/api/settings':
                st=load_settings()
                for k in ('buyerFeePercent','charityProfitPercent','auctionEntryFee','entryFeeEnabled','negotiationPercents','negotiationHours','adminEmail','platformName','ocrTesseractPath'):
                    if k in d: st[k]=d[k]
                incoming=d.get('visitorSections')
                if isinstance(incoming,dict):
                    current=dict(st.get('visitorSections') or {})
                    for key in ('market','auction','specialNumbers','transitionalIssues'):
                        if key in incoming: current[key]=bool(incoming[key])
                    st['visitorSections']=current
                save_json(SETTINGS,st)
                saved=load_settings()
                self.sendj({'ok':True,'settings':saved}); return
            if p=='/api/negotiate':
                item_id=str(d.get('itemId','')); pid=str(d.get('participantId','')); amount=float(d.get('amount') or 0)
                person=next((x for x in load_people() if x.get('id')==pid),None)
                item=next((i for i in load() if i.get('id')==item_id and i.get('forAuction') and i.get('auctionApproved')),None)
                if not participant_can_transact(person): self.sendj({'error':'تقديم عرض تفاوض يتطلب الاعتماد النهائي من الإدارة'},403); return
                if not item: self.sendj({'error':'المقتنى غير متاح للتفاوض'},404); return
                if not item.get('negotiationEnabled'): self.sendj({'error':'التفاوض غير مفعّل لهذا المقتنى'},409); return
                base=max(float(item.get('auctionCurrentPrice') or 0), float(item.get('auctionTargetPrice') or 0), float(item.get('expectedPrice') or 0))
                percent=float(item.get('negotiationPercent') or 0)
                if percent not in (5,10,15,20): self.sendj({'error':'نسبة التفاوض غير صالحة'},409); return
                minimum=max(0,base*(1-percent/100.0))
                if amount<=0: self.sendj({'error':'أدخل مبلغ عرض صحيح'},409); return
                if base>0 and amount+1e-9<minimum: self.sendj({'error':f'أقل عرض مسموح وفق نسبة التفاوض هو {minimum:.2f} ر.س'},409); return
                now=datetime.datetime.now(); hours=float(load_settings().get('negotiationHours') or 48)
                row={'id':'n-'+secrets.token_hex(6),'itemId':item_id,'participantId':pid,'amount':amount,'basePrice':base,'percent':percent,'minimum':minimum,'status':'pending','created':now.isoformat(),'expires':(now+datetime.timedelta(hours=hours)).isoformat()}
                a=load_negotiations(); a.append(row); save_json(NEGOTIATIONS,{'negotiations':a}); self.sendj({'ok':True,'negotiation':row}); return
            if p=='/api/negotiate/respond':
                nid=str(d.get('id','')); action=str(d.get('action','')); counter=float(d.get('counterAmount') or 0); a=load_negotiations(); row=next((x for x in a if x.get('id')==nid),None)
                if not row: self.sendj({'error':'عرض التفاوض غير موجود'},404); return
                if action not in ('accepted','rejected','countered'): self.sendj({'error':'الإجراء غير صالح'},400); return
                row['status']=action; row['updated']=datetime.datetime.now().isoformat()
                if action=='countered':
                    if counter<=0: self.sendj({'error':'أدخل قيمة العرض المقابل'},400); return
                    row['counterAmount']=counter
                save_json(NEGOTIATIONS,{'negotiations':a}); self.sendj({'ok':True,'negotiation':row}); return
            if p=='/api/analyze':
                ok,data,note=analyze_image(d.get('url','')); self.sendj({'ok':ok,'data':data,'note':note}); return
            if p=='/api/participant/register':
                name=str(d.get('name','')).strip(); reg_country=str(d.get('country','')).strip()[:80]; raw_phone=str(d.get('phone','')).strip(); phone=''.join(ch for ch in raw_phone if ch.isdigit() or ch=='+')
                if not name or not phone: self.sendj({'error':'الاسم والجوال مطلوبان'},400); return
                if len(''.join(ch for ch in phone if ch.isdigit())) < 7: self.sendj({'error':'رقم الجوال غير مكتمل'},400); return
                a=load_people(); existing=next((x for x in a if str(x.get('phone','')).replace(' ','')==phone.replace(' ','')),None)
                now=datetime.datetime.now(); nowiso=now.isoformat()
                existing_status=participant_approval_status(existing) if existing else ''
                if existing_status in ('stopped','cancelled'):
                    self.sendj({'error':'هذا الرقم موقوف أو ملغى ولا يمكن إنشاء حساب جديد به. تواصل مع الإدارة.'},403); return
                if existing:
                    existing.update({'name':name or existing.get('name',''),'country':reg_country or existing.get('country',''),'lastSeen':nowiso,'verifiedAt':existing.get('verifiedAt') or nowiso,'otp':'','otpExpires':'','otpAttempts':0}); apply_approval_status(existing,existing_status or 'preliminary')
                    x=existing
                else:
                    x={'id':'p-'+secrets.token_hex(6),'name':name,'phone':phone,'country':reg_country,'approved':False,'verified':True,'blocked':False,'archived':False,'approvalStatus':'preliminary','created':nowiso,'lastSeen':nowiso,'verifiedAt':nowiso,'preliminaryApprovedAt':nowiso,'verificationMode':'automatic','otp':'','otpExpires':'','otpAttempts':0,'approvalHistory':[{'status':'preliminary','previousStatus':'new','reason':'تحقق آلي من رقم الجوال دون رمز','actor':'النظام','at':nowiso}]}; a.append(x)
                save_json(PEOPLE,{'participants':a})
                saved=next((z for z in load_people() if z.get('id')==x['id']),None)
                if not saved: self.sendj({'error':'تعذر تثبيت التسجيل على الخادم'},500); return
                add_notification('admin','','approval','طلب مراجعة اعتماد نهائي',f"تم التحقق آليًا ومنح {saved.get('name','مشارك')} — {saved.get('phone','')} اعتمادًا مبدئيًا.",saved.get('id',''), '/admin')
                append_operation('اعتماد مبدئي تلقائي',{'participantId':saved.get('id'),'phone':saved.get('phone','')},actor='النظام'); safe=participant_public(saved)
                self.sendj({'ok':True,'participant':safe,'verified':True,'approved':False,'approvalStatus':safe['approvalStatus'],'otpRequired':False,'message':'تم التحقق ومنحك اعتمادًا مبدئيًا. تنتظر الاعتماد النهائي للمزايدة والشراء والبيع.'}); return

            if p=='/api/participant/profile':
                pid=str(d.get('id') or '').strip()
                a=load_people(); person=next((x for x in a if str(x.get('id') or '')==pid),None)
                if not person: self.sendj({'error':'الحساب غير موجود'},404); return
                alias=str(d.get('alias') or '').strip()[:60]
                country=str(d.get('country') or '').strip()[:80]
                avatar=str(d.get('avatarUrl') or '').strip()[:500]
                if avatar and not (avatar.startswith('/uploads/') or avatar.startswith('data:image/')):
                    self.sendj({'error':'مسار صورة الحساب غير صالح'},400); return

                nowiso=datetime.datetime.now().isoformat()
                person['alias']=alias; person['country']=country; person['avatarUrl']=avatar; person['profileUpdatedAt']=nowiso

                # توحيد الهوية العامة لكل سجلات الحساب القديمة التي تحمل الجوال نفسه.
                phone_key=_norm_phone(person.get('phone'))
                synced=0
                if phone_key:
                    for other in a:
                        if str(other.get('id') or '')==pid: continue
                        if _norm_phone(other.get('phone'))==phone_key:
                            other['alias']=alias; other['country']=country
                            if avatar: other['avatarUrl']=avatar
                            other['profileUpdatedAt']=nowiso
                            synced+=1

                save_json(PEOPLE,{'participants':a})
                append_operation('تحديث هوية الحساب العامة',{'participantId':pid,'country':country,'syncedDuplicateAccounts':synced},actor='العميل')
                self.sendj({'ok':True,'participant':participant_public(person),'syncedDuplicateAccounts':synced}); return

            if p=='/api/participant/verify':
                pid=str(d.get('id','')); code=str(d.get('code','')).strip(); a=load_people(); person=next((x for x in a if x.get('id')==pid),None)
                if not person: self.sendj({'error':'المشارك غير موجود'},404); return
                if person.get('blocked'): self.sendj({'error':'هذا الحساب موقوف من الإدارة'},403); return
                if person.get('verified'):
                    self.sendj({'ok':True,'participant':person,'message':'الحساب موثق مسبقًا'}); return
                try: expired=datetime.datetime.fromisoformat(person.get('otpExpires','')) < datetime.datetime.now()
                except Exception: expired=True
                if expired: self.sendj({'error':'انتهت صلاحية الرمز. اطلب رمزًا جديدًا.'},409); return
                attempts=int(person.get('otpAttempts') or 0)
                if attempts>=5: self.sendj({'error':'تم تجاوز عدد المحاولات. اطلب رمزًا جديدًا.'},429); return
                if not secrets.compare_digest(str(person.get('otp','')),code):
                    person['otpAttempts']=attempts+1; save_json(PEOPLE,{'participants':a}); self.sendj({'error':'رمز التحقق غير صحيح'},403); return
                nowiso=datetime.datetime.now().isoformat(); person.update({'verifiedAt':nowiso,'otp':'','otpExpires':'','otpAttempts':0,'lastSeen':nowiso}); apply_approval_status(person,'preliminary'); save_json(PEOPLE,{'participants':a})
                add_notification('participant',pid,'approval','تم التحقق من حسابك','مُنحت اعتمادًا مبدئيًا، وتنتظر مراجعة الإدارة للاعتماد النهائي.','','/account'); append_operation('اعتماد مبدئي بعد التحقق',{'participantId':pid,'name':person.get('name','')},actor='النظام')
                self.sendj({'ok':True,'participant':participant_public(person),'message':'تم التحقق ومنحك اعتمادًا مبدئيًا.'}); return
            if p=='/api/participant/approval-status':
                a=load_people(); iid=str(d.get('id') or ''); status=str(d.get('status') or '').strip().lower(); reason=str(d.get('reason') or '').strip()
                if status not in APPROVAL_STATUSES or status=='new': self.sendj({'error':'حالة الاعتماد غير صالحة'},400); return
                if status in ('suspended','stopped','cancelled') and not reason: self.sendj({'error':'كتابة السبب إلزامية لهذا القرار'},400); return
                person=next((x for x in a if str(x.get('id'))==iid),None)
                if not person: self.sendj({'error':'المشارك غير موجود'},404); return
                previous=participant_approval_status(person)
                if previous=='cancelled': self.sendj({'error':'الإلغاء نهائي ولا يمكن إعادة تفعيل الحساب'},409); return
                nowiso=datetime.datetime.now().isoformat(); apply_approval_status(person,status); person['approvalUpdatedAt']=nowiso; person['approvalUpdatedBy']='الإدارة'
                if status=='preliminary': person['preliminaryApprovedAt']=nowiso
                if status=='final': person['approvedAt']=nowiso; person['finalApprovedAt']=nowiso
                if status=='cancelled': person['archivedAt']=nowiso; person['archiveReason']=reason
                history=person.get('approvalHistory') if isinstance(person.get('approvalHistory'),list) else []; history.append({'status':status,'previousStatus':previous,'reason':reason or 'قرار اعتماد إداري','actor':'الإدارة','at':nowiso}); person['approvalHistory']=history[-200:]
                save_json(PEOPLE,{'participants':a}); messages={'preliminary':'تم تحديث حسابك إلى اعتماد مبدئي. يمكنك الدخول والتصفح حتى اكتمال المراجعة.','final':'تم منح حسابك الاعتماد النهائي، ويمكنك استخدام خدمات المزاد والسوق وفق الأنظمة.','suspended':'تم تعليق اعتماد حسابك مؤقتًا. يمكنك الدخول والتصفح، بينما أوقفت العمليات حتى المراجعة.','stopped':'تم إيقاف اعتماد حسابك وعملياته. تواصل مع الإدارة للمراجعة.','cancelled':'تم إلغاء اعتماد الحساب نهائيًا. تواصل مع الإدارة عند الحاجة.'}
                add_notification('participant',iid,'approval','تحديث حالة الاعتماد: '+APPROVAL_LABELS[status],messages[status],'','/account'); append_operation('تغيير حالة اعتماد مشارك',{'participantId':iid,'previousStatus':previous,'status':status,'statusLabel':APPROVAL_LABELS[status],'reason':reason},actor='الإدارة')
                self.sendj({'ok':True,'participant':participant_public(person)}); return
            if p=='/api/participant/approve':
                self.sendj({'error':'تم استبدال الاعتماد المباشر بنظام حالات الاعتماد الجديد'},410); return
                a=load_people(); iid=d.get('id'); approved=bool(d.get('approved')); direct=bool(d.get('direct')); found=False
                for x in a:
                    if x.get('id')==iid:
                        nowiso=datetime.datetime.now().isoformat()
                        x['approved']=approved; x['approvedAt']=nowiso if approved else ''
                        if approved and direct:
                            x['verified']=True; x['verifiedAt']=nowiso; x['otp']=''; x['otpExpires']=''; x['otpAttempts']=0; x['archived']=False; x['archivedAt']=''; x['archiveReason']=''
                        elif not approved:
                            x['archived']=True; x['archivedAt']=nowiso; x['archiveReason']='إلغاء أو رفض الاعتماد'
                        found=True
                save_json(PEOPLE,{'participants':a})
                if found:
                    add_notification('participant',iid,'approval','✅ تم اعتماد حسابك' if approved else 'تم إيقاف اعتماد المشاركة','يمكنك الآن المشاركة في المزادات.' if approved else 'تم إيقاف صلاحية المشاركة من الإدارة.','','/account')
                    append_operation('تحديث اعتماد مشارك',{'participantId':iid,'approved':approved,'direct':direct})
                self.sendj({'ok':found,'approved':approved,'direct':direct}); return
            if p=='/api/participant/restore':
                self.sendj({'error':'تم إلغاء الاستعادة القديمة؛ استخدم قرار حالة الاعتماد'},410); return
                a=load_people(); iid=d.get('id'); approve=bool(d.get('approve')); found=False
                for x in a:
                    if x.get('id')==iid:
                        nowiso=datetime.datetime.now().isoformat(); x['archived']=False; x['archivedAt']=''; x['archiveReason']=''; x['approved']=approve; x['approvedAt']=nowiso if approve else ''
                        if approve: x['verified']=True; x['verifiedAt']=nowiso; x['otp']=''; x['otpExpires']=''; x['otpAttempts']=0
                        found=True; break
                if found:
                    save_json(PEOPLE,{'participants':a}); append_operation('استعادة مشارك من الأرشيف',{'participantId':iid,'approved':approve})
                self.sendj({'ok':found,'approved':approve}); return
            if p=='/api/participant/delete':
                self.sendj({'error':'الحذف النهائي معطّل لحماية سجل المستخدم والمزايدات والطلبات والمستحقات'},409); return
            if p=='/api/bid':
                itemId=d.get('itemId'); pid=d.get('participantId'); amount=float(d.get('amount') or 0)
                person=next((x for x in load_people() if x.get('id')==pid),None)
                item=next((i for i in load() if i.get('id')==itemId and i.get('forAuction') and i.get('auctionApproved')),None)
                if not participant_can_transact(person): self.sendj({'error':'المزايدة تتطلب الاعتماد النهائي من الإدارة'},403); return
                if not item: self.sendj({'error':'المزاد غير متاح'},404); return
                overdue=overdue_due_for(pid)
                if overdue:
                    add_notification('participant',pid,'finance','⛔ المشاركة موقوفة بسبب مستحق متأخر',f"لديك مستحق سابق غير مسدد تجاوز 24 ساعة بقيمة {float(overdue.get('amount') or 0):g} ر.س. يرجى السداد أولًا.",overdue.get('itemId'),'/account')
                    self.sendj({'error':'تعذر المشاركة: لديك مستحقات سابقة غير مسددة تجاوزت 24 ساعة. يرجى السداد أولًا.'},403); return
                if item.get('auctionEnd'):
                    try:
                        end=datetime.datetime.fromisoformat(str(item['auctionEnd']));
                        if end<=datetime.datetime.now(): self.sendj({'error':'انتهى المزاد'},409); return
                    except Exception: pass
                bids=load_bids(); round_no=int(item.get('auctionRound') or 1); item_bids=[b for b in bids if b.get('itemId')==itemId and int(b.get('auctionRound') or 1)==round_no]; current=max([float(b.get('amount') or 0) for b in item_bids]+[0.0])
                opening=float(item.get('auctionOpeningPrice') or item.get('auctionStartPrice') or 0)
                step=float(item.get('auctionBidStep') or 1)
                if step<=0: step=1
                if amount<=0: self.sendj({'error':'أدخل مبلغ مزايدة أكبر من صفر'},409); return
                if not item_bids:
                    if opening>0 and amount<opening:
                        self.sendj({'error':f'السومة الأولى تبدأ من {opening:g} ر.س أو أكثر'},409); return
                else:
                    minimum=current+step
                    if amount+1e-9<minimum:
                        self.sendj({'error':f'الزيادة المحددة للمزاد {step:g} ر.س؛ أقل سوم مقبول الآن {minimum:g} ر.س'},409); return
                previous_top=max(item_bids,key=lambda b:float(b.get('amount') or 0)) if item_bids else None
                bid={'id':'b-'+secrets.token_hex(6),'itemId':itemId,'auctionRound':round_no,'participantId':pid,'amount':amount,'created':datetime.datetime.now().isoformat()}; bids.append(bid); save_json(BIDS,{'bids':bids})
                title=item_title(item)
                add_notification('participant',pid,'auction','✅ تم تسجيل مزايدتك',f"تم قبول مزايدتك على {title} بقيمة {amount:g} ر.س.",itemId,'/auction#'+str(itemId))
                if previous_top and str(previous_top.get('participantId'))!=str(pid):
                    add_notification('participant',previous_top.get('participantId'),'auction','⚡ تمت المزايدة عليك',f"مزايدتك لم تعد الأعلى في {title}. السعر الحالي {amount:g} ر.س، ويمكنك العودة للمزاد والزيادة.",itemId,'/auction#'+str(itemId))
                items=load();
                for i in items:
                    if i.get('id')==itemId: i['auctionCurrentPrice']=amount; i['updated']=int(datetime.datetime.now().timestamp()*1000)
                save(items); self.sendj({'ok':True,'current':amount}); return
            items=load()
            if p=='/api/item':
                x=d.get('item',{}) if isinstance(d,dict) else {}
                iid=str(x.get('id') or '').strip()
                country=str(x.get('country') or '').strip()
                denom=str(x.get('denomination') or '').strip()
                if not iid or not country or not denom:
                    self.sendj({'ok':False,'error':'بيانات الحفظ الأساسية ناقصة: رقم السجل أو الدولة أو الفئة'},400); return
                old_item=next((i for i in items if str(i.get('id'))==iid),None)
                # نموذج الإدارة يرسل الحقول القابلة للتعديل فقط. نحافظ على حقول
                # التاريخ والنتائج والمعرّفات التي لا تظهر في النموذج.
                if old_item:
                    x={**old_item,**x}
                    # لا نرقّي تفسير الكمية تلقائيًا عند تعديل سجل قديم؛
                    # فهذا قد يحول 3 قطع قديمة إلى 3 أطقم × 3 قطع ويخلق 409 وهمي.
                    x['inventorySchemaVersion']=inventory_schema_version(old_item)
                else:
                    # السجلات الجديدة تستخدم نموذج الوحدة/الطقم الحديث.
                    x['inventorySchemaVersion']=2
                classification=str(x.get('inventoryClassification') or '').strip().lower()
                if classification not in ('graded','ungraded','set'):
                    classification='set' if (x.get('isSet') or str(x.get('marketOfferType') or '')=='set') else ('graded' if x.get('isGraded') else 'ungraded')
                x['inventoryClassification']=classification
                x['collectionClass']='set' if classification=='set' else 'single'
                x['isSet']=classification=='set'
                if not str(x.get('warehouse') or '').strip(): x['warehouse']='المستودع الرئيسي'
                if not str(x.get('storageStatus') or '').strip(): x['storageStatus']='warehouse'
                # يسمح بتعديل بيانات المستودع لمزاد محفوظ انتهى سابقًا. الموعد
                # المستقبلي مطلوب فقط للنشر الجديد أو عند تغيير موعد الانتهاء.
                if x.get('forAuction') and x.get('auctionApproved'):
                    end=str(x.get('auctionEnd') or '').strip()
                    if not end:
                        self.sendj({'ok':False,'error':'اعتماد المزاد للنشر يتطلب تاريخ ووقت انتهاء'},400); return
                    try:
                        end_dt=datetime.datetime.fromisoformat(end)
                        old_was_approved=bool(old_item and old_item.get('forAuction') and old_item.get('auctionApproved'))
                        end_changed=str((old_item or {}).get('auctionEnd') or '').strip()!=end
                        needs_fresh_schedule=not old_was_approved or end_changed
                        if needs_fresh_schedule and end_dt <= datetime.datetime.now():
                            self.sendj({'ok':False,'error':'موعد انتهاء المزاد يجب أن يكون في المستقبل'},400); return
                    except ValueError:
                        self.sendj({'ok':False,'error':'صيغة تاريخ انتهاء المزاد غير صحيحة'},400); return
                if x.get('forMarket') and x.get('marketApproved'):
                    if float(x.get('marketSalePrice') or 0) <= 0:
                        self.sendj({'ok':False,'error':'اعتماد السوق للنشر يتطلب سعر بيع أكبر من صفر'},400); return
                    if int(x.get('marketQuantity') or 0) < 1:
                        self.sendj({'ok':False,'error':'الكمية المعروضة في السوق يجب أن تكون 1 على الأقل'},400); return
                total=inventory_total(x); sold=inventory_int(x.get('soldQuantity'),0); damaged=inventory_int(x.get('damagedQuantity'),0)
                market_alloc=market_listing_physical(x); auction_alloc=auction_listing_physical(x)
                reserved,_,reserved_by_source=item_order_quantities(iid,item=old_item or x)
                market_alloc=max(0,market_alloc-reserved_by_source.get('market',0)); auction_alloc=max(0,auction_alloc-reserved_by_source.get('auction',0))
                new_used=sold+damaged+reserved+market_alloc+auction_alloc
                # بعض السجلات القديمة حُفظت قبل اعتماد حساب الأطقم الفيزيائي.
                # يسمح بتعديل موقعها ما دام التعديل لا يزيد التجاوز القديم.
                old_overflow=0
                if old_item:
                    old_total=inventory_total(old_item)
                    old_sold=inventory_int(old_item.get('soldQuantity'),0)
                    old_damaged=inventory_int(old_item.get('damagedQuantity'),0)
                    old_market=max(0,market_listing_physical(old_item)-reserved_by_source.get('market',0))
                    old_auction=max(0,auction_listing_physical(old_item)-reserved_by_source.get('auction',0))
                    old_used=old_sold+old_damaged+reserved+old_market+old_auction
                    old_overflow=max(0,old_used-old_total)
                new_overflow=max(0,new_used-total)
                if new_overflow>old_overflow:
                    self.sendj({'ok':False,'error':f'توزيع الكمية يتجاوز الرصيد: الإجمالي {total}، والموزع/المباع/المحجوز {sold+damaged+reserved+market_alloc+auction_alloc}'},409); return
                serials=x.get('serials') or []
                if not isinstance(serials,list): serials=[serials]
                normalized=[re.sub(r'\s+','',str(s or '')).upper() for s in serials if str(s or '').strip()]
                old_serials=(old_item or {}).get('serials') or [(old_item or {}).get('serial')]
                if not isinstance(old_serials,list): old_serials=[old_serials]
                old_normalized=[re.sub(r'\s+','',str(s or '')).upper() for s in old_serials if str(s or '').strip()]
                if len(normalized)!=len(set(normalized)) and normalized!=old_normalized:
                    self.sendj({'ok':False,'error':'يوجد رقم تسلسلي مكرر داخل السجل نفسه'},409); return
                newly_added_serials=set(normalized)-set(old_normalized)
                for other in items:
                    if str(other.get('id'))==iid: continue
                    other_serials=other.get('serials') or [other.get('serial')]
                    if not isinstance(other_serials,list): other_serials=[other_serials]
                    duplicate=newly_added_serials&{re.sub(r'\s+','',str(s or '')).upper() for s in other_serials if str(s or '').strip()}
                    if duplicate:
                        self.sendj({'ok':False,'error':'الرقم التسلسلي مسجل مسبقًا: '+next(iter(duplicate))},409); return
                before=len(items)
                items=[i for i in items if str(i.get('id'))!=iid]
                x['id']=iid
                x['updated']=int(datetime.datetime.now().timestamp()*1000)
                items.append(x)
                try:
                    save(items)
                    check=load()
                    saved=next((i for i in check if str(i.get('id'))==iid),None)
                    if not saved:
                        append_save_audit({'id':iid,'ok':False,'country':country,'denomination':denom,'created':datetime.datetime.now().isoformat(),'reason':'verify_missing'})
                        self.sendj({'ok':False,'error':'تمت محاولة الكتابة لكن تعذر التحقق من وجود السجل بعد الحفظ'},500); return
                    append_save_audit({'id':iid,'ok':True,'country':country,'denomination':denom,'created':datetime.datetime.now().isoformat(),'before':before,'after':len(check)})
                    before_snap=inventory_snapshot(old_item) if old_item else None; after_snap=inventory_snapshot(saved)
                    append_operation('إضافة مقتنى للمستودع' if not old_item else 'تحديث مقتنى بالمستودع',{'itemId':iid,'before':before_snap,'after':after_snap})
                    self.sendj({'ok':True,'saved':saved,'total':len(check),'verified':True,'publication':{'auction':bool(saved.get('forAuction') and saved.get('auctionApproved')),'market':bool(saved.get('forMarket') and saved.get('marketApproved'))}}); return
                except Exception as e:
                    try: append_save_audit({'id':iid,'ok':False,'country':country,'denomination':denom,'created':datetime.datetime.now().isoformat(),'reason':str(e)})
                    except Exception: pass
                    self.sendj({'ok':False,'error':'فشل حفظ السجل على القرص: '+str(e)},500); return
            if p=='/api/merge':
                incoming=d.get('items',[]); ids={i.get('id') for i in items}; ss={sig(i) for i in items}; added=0
                for x in incoming:
                    if x.get('id') in ids or sig(x) in ss: continue
                    items.append(x); ids.add(x.get('id')); ss.add(sig(x)); added+=1
                save(items); self.sendj({'ok':True,'added':added,'total':len(items)}); return
            if p=='/api/clear': save([]); self.sendj({'ok':True}); return
        self.sendj({'error':'not found'},404)
    def do_DELETE(self):
        p=urlparse(self.path).path
        if not self.require_admin(api=True): return
        if not self.same_origin_ok(): self.sendj({'error':'تم رفض الطلب لأسباب أمنية.'},403); return
        if p.startswith('/api/item/'):
            iid=p.split('/')[-1]
            with LOCK:
                if any(str(line.get('itemId'))==iid for order in load_orders() for line in (order.get('items') or [])):
                    self.sendj({'error':'لا يمكن حذف مقتنى مرتبط بطلب. يمكن إبقاؤه في السجل أو أرشفته بعد اكتمال الدورة.'},409); return
                if any(str(b.get('itemId'))==iid for b in load_bids()):
                    self.sendj({'error':'لا يمكن حذف مقتنى مرتبط بسجل مزايدات محفوظ.'},409); return
                items=[i for i in load() if str(i.get('id'))!=iid]; save(items)
                append_operation('حذف مقتنى غير مرتبط',{'itemId':iid})
            self.sendj({'ok':True}); return
        self.sendj({'error':'not found'},404)

os.chdir(ROOT); backup_data('startup')
# تشغيل آمن: تأكد من وجود ملفات الواجهات الأساسية قبل بدء الخدمة.
_required_runtime_files=[
    os.path.join(ADMIN_DIR,'index.html'), os.path.join(ADMIN_DIR,'app.js'), os.path.join(ADMIN_DIR,'styles.css'),
    os.path.join(PUBLIC_DIR,'public_home.html'), os.path.join(PUBLIC_DIR,'public_auction.html'), os.path.join(PUBLIC_DIR,'public_market.html')
]
_missing_runtime=[p for p in _required_runtime_files if not os.path.isfile(p)]
if _missing_runtime:
    raise RuntimeError('ملفات تشغيل أساسية مفقودة: '+', '.join(os.path.relpath(p,ROOT) for p in _missing_runtime))
ensure_dues_tracking_start()
_auth_cfg,_new_admin_password=ensure_admin_auth()
VERSION='4.3.4-VISITOR-SECTIONS-FINAL-FIX'
def local_ip():
    try:
        x=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); x.connect(('8.8.8.8',80)); ip=x.getsockname()[0]; x.close(); return ip
    except Exception: return '127.0.0.1'

def make_server():
    preferred=int(os.environ.get('PORT') or os.environ.get('KHAZINA_PORT','8080'))
    for port in range(preferred,preferred+10):
        try: return ThreadingHTTPServer(('0.0.0.0',port),H),port
        except OSError as e:
            if getattr(e,'errno',None) not in (98,10048): raise
    raise OSError('تعذر إيجاد منفذ متاح بين 8080 و8089')

server,PORT=make_server(); IP=local_ip()
admin_url=f'http://localhost:{PORT}/admin'
public_url=f'http://{IP}:{PORT}/auction'
market_url=f'http://{IP}:{PORT}/market'
try:
    with open(os.path.join(ROOT,'رابط_الجوال.txt'),'w',encoding='utf-8') as f:
        f.write('واجهة الزوار:\n'+f'http://{IP}:{PORT}/home\n\nرابط المزاد للزوار:\n'+public_url+'\n\nرابط السوق العام:\n'+market_url+'\n\nالإدارة محمية بكلمة مرور ولا يُنصح بإرسال رابطها للعملاء.\n')
except Exception: pass
print(f'خزينة المقتنيات V{VERSION} - الخادم يعمل على المنفذ {PORT}')
if PORT!=8080: print('تنبيه: المنفذ 8080 مستخدم من نسخة أخرى، لذلك تم تشغيل هذه النسخة على منفذ بديل.')
print('الإدارة:',admin_url)
print('بيانات دخول الإدارة محفوظة في:',ADMIN_CREDENTIALS)
if _new_admin_password: print('تم إنشاء كلمة مرور إدارة جديدة. افتح ملف بيانات_دخول_الإدارة.txt داخل مجلد البرنامج.')
print('واجهة الزوار:',f'http://{IP}:{PORT}/home')
print('المزاد للزوار:',public_url)
print('السوق العام:',market_url)
print('لا تغلق هذه النافذة أثناء استخدام البرنامج من الأجهزة الأخرى.')
def open_browser():
    time.sleep(1)
    try: webbrowser.open(admin_url)
    except Exception: pass
threading.Thread(target=open_browser,daemon=True).start()
def final_backup(): backup_data('shutdown')
atexit.register(final_backup)
def auction_settlement_worker():
    # Settlement must not depend on a visitor/admin refreshing the page.
    while True:
        try:
            time.sleep(5)
            with LOCK:
                ensure_auction_outcomes()
        except Exception as e:
            print('تنبيه تسوية المزاد:', e)
threading.Thread(target=auction_settlement_worker,daemon=True).start()
try: server.serve_forever()
except KeyboardInterrupt: print('\nإيقاف آمن للخادم...')
finally: server.server_close(); final_backup()
