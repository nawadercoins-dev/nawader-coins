# V4.9.0 LAUNCH CANDIDATE — durable customer sessions, market-first launch, grader filters and checkout recovery.
# V4.8.0 — direct customer publishing across inventory, market, auction, special/rare, transitional; admin moderation only.
# V4.7.0 — final collectible lifecycle reconciliation and owner controls.
# V4.6.6 — platform-owner seller country: admin ownerCountry field, default Saudi Arabia, public flag fallback.
# V4.6.5 — seller flag repair: normalize country and sync duplicate participant identities by phone.
# V4.6.4 — approved collectible lifecycle, owner records/actions, destination routing, clean activity feed.
# V4.6.3 — public seller identity uses flag icon on cards; country retained in API for shipping/filtering.
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote, urlencode
import json, os, threading, shutil, datetime, atexit, re, secrets, mimetypes, socket, webbrowser, time, io, hashlib, hmac, zipfile, tempfile, subprocess, glob, base64
import urllib.request, urllib.error

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
IMAGE_VAULT=os.path.join(DATA_ROOT,'image_vault.json')
LIVE_AUCTIONS=os.path.join(DATA_ROOT,'live_auctions.json')
LIVEKIT_URL=str(os.environ.get('LIVEKIT_URL') or '').strip()
LIVEKIT_API_KEY=str(os.environ.get('LIVEKIT_API_KEY') or '').strip()
LIVEKIT_API_SECRET=str(os.environ.get('LIVEKIT_API_SECRET') or '').strip()
# V5.6.2-R9.5 — Google OAuth is configured only through environment variables.
# Never store the client secret in browser files or the data JSON.
GOOGLE_CLIENT_ID=str(os.environ.get('GOOGLE_CLIENT_ID') or '').strip()
GOOGLE_CLIENT_SECRET=str(os.environ.get('GOOGLE_CLIENT_SECRET') or '').strip()
GOOGLE_REDIRECT_URI=str(os.environ.get('GOOGLE_REDIRECT_URI') or '').strip()
GOOGLE_OAUTH_STATES={}
GOOGLE_PENDING_LINKS={}
GOOGLE_FLOW_TTL_SECONDS=10*60
# V4.9.1 FACEBOOK OAUTH — unified Facebook/Google/WhatsApp entry.
# Secrets stay in Render environment variables; privileged roles stay server-side.
FACEBOOK_APP_ID=str(os.environ.get('FACEBOOK_APP_ID') or '').strip()
FACEBOOK_APP_SECRET=str(os.environ.get('FACEBOOK_APP_SECRET') or '').strip()
FACEBOOK_REDIRECT_URI=str(os.environ.get('FACEBOOK_REDIRECT_URI') or '').strip()
FACEBOOK_OAUTH_STATES={}
FACEBOOK_PENDING_LINKS={}
FACEBOOK_STATE_TTL_SECONDS=10*60
FACEBOOK_PENDING_TTL_SECONDS=24*60*60
AUTH_FILE=os.path.join(DATA_ROOT,'admin_auth.json')
PARTICIPANT_SESSION_SECRET_FILE=os.path.join(DATA_ROOT,'.participant_session_secret')
ADMIN_CREDENTIALS=''
ADMIN_SESSIONS={}
PARTICIPANT_SESSIONS={}
ADMIN_LOGIN_ATTEMPTS={}
ADMIN_LOGIN_WINDOW_SECONDS=15*60
ADMIN_LOGIN_MAX_ATTEMPTS=5
SESSION_TTL_SECONDS=12*60*60
PARTICIPANT_SESSION_TTL_SECONDS=90*24*60*60
MARKET_FIRST_LAUNCH=False
LOCK=threading.Lock()
BACKUP_DIR=os.path.join(DATA_ROOT,'backups')
UPLOAD_DIR=os.path.join(DATA_ROOT,'uploads')
os.makedirs(BACKUP_DIR,exist_ok=True)
os.makedirs(UPLOAD_DIR,exist_ok=True)

# تهيئة القرص في أول تشغيل فقط من الملفات المرفقة مع المشروع، دون استبدال أي بيانات دائمة.
if DATA_ROOT != ROOT:
    for _dst in (DATA,PEOPLE,BIDS,NEGOTIATIONS,MARKET_REQUESTS,SUBSCRIPTIONS,SAVE_AUDIT,SETTINGS,NOTIFICATIONS,AUCTION_DUES,USER_PERMISSIONS,OPERATIONS_LOG,ORDERS,COLLECTIBLE_SUBMISSIONS,IMAGE_VAULT,AUTH_FILE):
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
def load_image_vault(): return load_json(IMAGE_VAULT,{'images':[]}).get('images',[])
def load_live_auctions(): return load_json(LIVE_AUCTIONS,{'sessions':[]}).get('sessions',[])

def live_timer_remaining(row):
    """Return authoritative remaining lot seconds from the server clock.
    The browser must never infer the auction state from a wall-clock timestamp.
    """
    if not (row.get('currentItemId') or row.get('currentLot')):
        return None
    raw=str(row.get('lotEndsAt') or '').strip()
    if not raw:
        return None
    try:
        end=datetime.datetime.fromisoformat(raw.replace('Z','+00:00'))
        if end.tzinfo is None:
            # Legacy rows without an offset are treated as UTC for live-auction timers.
            end=end.replace(tzinfo=datetime.timezone.utc)
        remaining=end.timestamp()-time.time()
        return max(0,int(__import__('math').ceil(remaining)))
    except Exception:
        return None

def with_live_timer(row):
    x=dict(row)
    x['remainingSec']=live_timer_remaining(row)
    x['serverEpochMs']=int(time.time()*1000)
    return x

def live_lot_expired(row):
    rem=live_timer_remaining(row)
    return rem is not None and rem<=0 and bool(row.get('currentItemId') or row.get('currentLot'))

def load_save_audit(): return load_json(SAVE_AUDIT,{'events':[]}).get('events',[])
def append_save_audit(event):
    rows=load_save_audit(); rows.append(event); rows=rows[-500:]; save_json(SAVE_AUDIT,{'events':rows})
def append_operation(action, details=None, actor='الإدارة'):
    rows=load_operations_log(); rows.append({'id':'op-'+secrets.token_hex(6),'action':str(action),'details':details or {},'actor':actor,'created':datetime.datetime.now().isoformat()}); rows=rows[-2000:]; save_json(OPERATIONS_LOG,{'events':rows})

def add_notification(recipient_type, recipient_id, category, title, message, item_id='', action_url=''):
    rows=load_notifications()
    row={'id':'nt-'+secrets.token_hex(6),'recipientType':recipient_type,'recipientId':str(recipient_id or ''),'category':category,'title':title,'message':message,'itemId':str(item_id or ''),'actionUrl':action_url,'read':False,'created':datetime.datetime.now().isoformat()}
    rows.append(row); rows=rows[-4000:]; save_json(NOTIFICATIONS,{'notifications':rows}); return row

APPROVAL_STATUSES=('new','final','suspended','stopped','cancelled')
APPROVAL_LABELS={'new':'طلب جديد','final':'توثيق كامل','suspended':'معلّق','stopped':'موقوف','cancelled':'ملغى'}

def participant_approval_status(person):
    status=str((person or {}).get('approvalStatus') or '').strip().lower()
    # V5.0: التوثيق المبدئي أُلغي نهائيًا؛ أي سجل قديم مبدئي يرحّل إلى توثيق كامل.
    if status=='preliminary': return 'final'
    if status in APPROVAL_STATUSES: return status
    if (person or {}).get('archived'): return 'cancelled'
    if (person or {}).get('blocked'): return 'stopped'
    if (person or {}).get('verified') or (person or {}).get('approved'): return 'final'
    return 'new'

def apply_approval_status(person,status):
    if status=='preliminary': status='final'
    status=status if status in APPROVAL_STATUSES else 'new'; person['approvalStatus']=status
    person['verified']=status!='new'; person['approved']=status=='final'; person['blocked']=status in ('stopped','cancelled'); person['archived']=status=='cancelled'
    if status!='cancelled': person['archivedAt']=''; person['archiveReason']=''
    return person

def participant_can_access(person): return participant_approval_status(person) in ('final','suspended','stopped')
def participant_can_transact(person): return participant_approval_status(person)=='final'
def participant_public(person):
    blocked={'otp','otpExpires','otpAttempts','pinHash','pinSalt','pinIterations','authUpdatedAt','whatsappVerificationRequests'}
    safe={k:v for k,v in (person or {}).items() if k not in blocked}; status=participant_approval_status(person)
    safe['approvalStatus']=status; safe['approvalLabel']=APPROVAL_LABELS[status]; safe['hasPin']=False
    reqs=list((person or {}).get('whatsappVerificationRequests') or [])
    pending=next((r for r in reversed(reqs) if str(r.get('status'))=='pending'),None)
    safe['whatsappPending']=bool(pending)
    safe['whatsappPendingCode']=str((pending or {}).get('code') or '')
    safe['whatsappPendingRequestId']=str((pending or {}).get('id') or '')
    safe['whatsappPendingCreated']=str((pending or {}).get('created') or '')
    safe['whatsappPendingExpires']=str((pending or {}).get('expires') or '')
    return safe

def participant_public_safe(person):
    # لا نرسل أسرار تسجيل الدخول أو بيانات المصادقة إلى المتصفح.
    blocked={'otp','otpExpires','otpAttempts','pinHash','pinSalt','pinIterations','authUpdatedAt','whatsappVerificationRequests'}
    safe={k:v for k,v in (person or {}).items() if k not in blocked}
    status=participant_approval_status(person)
    safe['approvalStatus']=status; safe['approvalLabel']=APPROVAL_LABELS[status]
    safe['hasPin']=False
    return safe

def _pin_hash(pin,salt,iterations=180000):
    return hashlib.pbkdf2_hmac('sha256',str(pin).encode('utf-8'),bytes.fromhex(str(salt)),int(iterations)).hex()

def set_participant_pin(person,pin):
    pin=str(pin or '')
    if len(pin)<4 or len(pin)>32:
        raise ValueError('رمز الدخول يجب أن يكون بين 4 و32 خانة')
    salt=secrets.token_hex(16); iterations=180000
    person['pinSalt']=salt; person['pinIterations']=iterations; person['pinHash']=_pin_hash(pin,salt,iterations)
    person['authUpdatedAt']=datetime.datetime.now().isoformat()

def verify_participant_pin(person,pin):
    if not person or not person.get('pinHash') or not person.get('pinSalt'): return False
    try:
        got=_pin_hash(str(pin or ''),person['pinSalt'],int(person.get('pinIterations') or 180000))
        return secrets.compare_digest(got,str(person.get('pinHash') or ''))
    except Exception:
        return False

def _participant_session_secret():
    env=str(os.environ.get('PARTICIPANT_SESSION_SECRET') or '').strip()
    if env: return env.encode('utf-8')
    try:
        if os.path.isfile(PARTICIPANT_SESSION_SECRET_FILE):
            with open(PARTICIPANT_SESSION_SECRET_FILE,'r',encoding='utf-8') as f:
                val=f.read().strip()
                if val: return val.encode('utf-8')
        val=secrets.token_hex(32)
        with open(PARTICIPANT_SESSION_SECRET_FILE,'w',encoding='utf-8') as f: f.write(val)
        try: os.chmod(PARTICIPANT_SESSION_SECRET_FILE,0o600)
        except Exception: pass
        return val.encode('utf-8')
    except Exception:
        return hashlib.sha256((ROOT+'|nawader-session').encode('utf-8')).digest()

def _participant_session_token(person):
    pid=str((person or {}).get('id') or '')
    issued=int(time.time()); nonce=secrets.token_hex(8)
    payload=f'{pid}.{issued}.{nonce}'
    sig=hmac.new(_participant_session_secret(),payload.encode('utf-8'),hashlib.sha256).hexdigest()
    return payload+'.'+sig

def _participant_from_signed_session(token):
    try:
        pid,issued_s,nonce,sig=str(token or '').rsplit('.',3)
        payload=f'{pid}.{issued_s}.{nonce}'
        expected=hmac.new(_participant_session_secret(),payload.encode('utf-8'),hashlib.sha256).hexdigest()
        if not secrets.compare_digest(expected,sig): return None
        issued=int(issued_s)
        if issued<=0 or time.time()-issued>PARTICIPANT_SESSION_TTL_SECONDS: return None
        person=next((x for x in load_people() if str(x.get('id'))==pid),None)
        if not person: return None
        updated=str(person.get('authUpdatedAt') or '')
        if updated:
            try:
                auth_ts=datetime.datetime.fromisoformat(updated).timestamp()
                if issued+1 < auth_ts: return None
            except Exception: pass
        return person
    except Exception:
        return None

def clean_participant_sessions():
    now=time.time()
    for token,meta in list(PARTICIPANT_SESSIONS.items()):
        if now-float(meta.get('last',0))>PARTICIPANT_SESSION_TTL_SECONDS:
            PARTICIPANT_SESSIONS.pop(token,None)

def moderation_status(item):
    status=str((item or {}).get('moderationStatus') or '').strip().lower()
    if status in ('active','hidden','suspended','archived','removed'): return status
    if (item or {}).get('ownerArchived'): return 'archived'
    return 'active'

def item_is_public(item):
    return moderation_status(item)=='active'

# V5.6.0 — Dar Al Muqtanyat multi-store foundation.
# One shared platform/database powers two independent storefronts:
#   coins        = نوادر العملات (official/original currencies)
#   collectibles = نوادر المقتنيات (fantasia, antiques and other collectibles)
STORE_TYPES=('coins','collectibles')
STORE_LABELS={'coins':'نوادر العملات','collectibles':'نوادر المقتنيات'}

def item_store_type(item):
    raw=str((item or {}).get('storeType') or '').strip().lower()
    if raw in STORE_TYPES: return raw
    # Fantasia is deliberately separated from official currency inventory.
    if (item or {}).get('fantasiaEnabled'): return 'collectibles'
    text=' '.join(str((item or {}).get(k) or '') for k in ('type','marketCategory','category','notes')).lower()
    collectible_words=('تحف','تحفة','سبح','سبحة','مسباح','خاتم','خواتم','حجر كريم','أحجار','مجسم','سيارة','طائرة','سفينة','لعبة','ألعاب','ميدالية','فنتازيا','fantasia','collectible')
    if any(w in text for w in collectible_words): return 'collectibles'
    # Existing records are currency records unless explicitly classified otherwise.
    return 'coins'

def normalize_store_type(value,item=None):
    raw=str(value or '').strip().lower()
    if raw in STORE_TYPES: return raw
    return item_store_type(item or {})

def requested_store(path):
    try:
        raw=str((parse_qs(urlparse(path).query).get('store') or [''])[0]).strip().lower()
        return raw if raw in STORE_TYPES else ''
    except Exception:
        return ''

def store_auction_path(item):
    iid=quote(str((item or {}).get('id') or ''))
    return f'/auction?store={item_store_type(item)}#{iid}'

def store_market_path(item):
    iid=quote(str((item or {}).get('id') or ''))
    return f'/market?store={item_store_type(item)}#{iid}'

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

def participant_linked_ids(pid):
    """Return all historical participant ids that belong to the same normalized phone."""
    pid=str(pid or '').strip()
    people=load_people()
    person=next((x for x in people if str(x.get('id') or '')==pid),None)
    phone_key=_norm_phone((person or {}).get('phone'))
    ids=[]
    if pid: ids.append(pid)
    if phone_key:
        for row in people:
            rid=str(row.get('id') or '').strip()
            if rid and _norm_phone(row.get('phone'))==phone_key and rid not in ids:
                ids.append(rid)
    return ids

def participant_permissions(pid):
    # R9.5D: permissions follow the person by normalized phone, not one duplicate legacy id.
    defaults={'sellerEndedAuctions':False,'sellerMarket':False,'liveBroadcast':False,'marketSupervision':False,'auctionSupervision':False,'ordersView':False,'ordersManage':False,'dataEntry':False}
    perms=load_user_permissions()
    for linked_pid in participant_linked_ids(pid):
        x=perms.get(str(linked_pid),{})
        if not isinstance(x,dict): continue
        for key in defaults:
            if key in x:
                defaults[key]=bool(defaults[key] or x.get(key))
    return defaults


def image_vault_cleanup(rows=None, stale_seconds=4*60*60):
    """Release abandoned temporary reservations without duplicating image files."""
    rows=rows if isinstance(rows,list) else load_image_vault()
    now=time.time(); changed=False
    for row in rows:
        if row.get('status')!='reserved' or row.get('linkedSubmissionId'): continue
        raw=str(row.get('reservedAt') or '').strip()
        try: ts=datetime.datetime.fromisoformat(raw).timestamp() if raw else 0
        except Exception: ts=0
        if ts and now-ts <= stale_seconds: continue
        row['status']='available'; row['reservedByParticipantId']=''; row['reservedByName']=''; row['reservedAt']=''; row['updatedAt']=datetime.datetime.now().isoformat(); changed=True
    return rows,changed

def image_vault_record_by_url(url, rows=None):
    path=urlparse(str(url or '')).path
    if not path: return None
    for row in (rows if isinstance(rows,list) else load_image_vault()):
        if urlparse(str(row.get('url') or '')).path==path: return row
    return None

def image_vault_release_for_submission(submission_id, rows=None, reason=''):
    rows=rows if isinstance(rows,list) else load_image_vault(); changed=False; now=datetime.datetime.now().isoformat()
    sid=str(submission_id or '')
    for row in rows:
        if str(row.get('linkedSubmissionId') or '')!=sid: continue
        hist=row.setdefault('linkHistory',[])
        hist.append({'submissionId':sid,'itemId':str(row.get('linkedItemId') or ''),'releasedAt':now,'reason':str(reason or '')[:300]})
        if len(hist)>20: del hist[:-20]
        row.update({'status':'available','linkedSubmissionId':'','linkedItemId':'','reservedByParticipantId':'','reservedByName':'','reservedAt':'','updatedAt':now})
        changed=True
    return rows,changed

def livekit_configured():
    return bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)

def _b64url(raw):
    if not isinstance(raw,(bytes,bytearray)): raw=str(raw).encode('utf-8')
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

def livekit_room_name(session_id):
    clean=re.sub(r'[^A-Za-z0-9_-]+','-',str(session_id or 'live'))[:80].strip('-') or 'live'
    return 'nawader-'+clean

def livekit_token(session_id, identity, publish=False, ttl=3600):
    if not livekit_configured(): raise RuntimeError('LiveKit غير مهيأ على الخادم')
    now=int(time.time())
    header={'alg':'HS256','typ':'JWT'}
    grants={'roomJoin':True,'room':livekit_room_name(session_id),'canSubscribe':True,'canPublish':bool(publish),'canPublishData':False}
    if publish: grants['canPublishSources']=['camera','microphone']
    payload={'iss':LIVEKIT_API_KEY,'sub':str(identity),'nbf':now-5,'iat':now,'exp':now+max(300,int(ttl)),'video':grants}
    h=_b64url(json.dumps(header,separators=(',',':')).encode())
    b=_b64url(json.dumps(payload,separators=(',',':')).encode())
    sig=hmac.new(LIVEKIT_API_SECRET.encode('utf-8'),f'{h}.{b}'.encode('ascii'),hashlib.sha256).digest()
    return f'{h}.{b}.{_b64url(sig)}'

def live_broadcast_allowed(person):
    return bool(person and participant_can_transact(person) and participant_permissions(person.get('id')).get('liveBroadcast'))

def live_session_owned_by(row,person):
    return bool(row and person and row.get('broadcasterType')=='participant' and str(row.get('broadcasterParticipantId') or '')==str(person.get('id') or ''))

def make_free_live_item(row, lot):
    """Create the inventory source record only when a camera-only lot is actually sold."""
    items=load(); now_iso=datetime.datetime.now().isoformat(); title=str((lot or {}).get('title') or 'مقتنى من بث مباشر').strip()[:180]
    item={'id':'live-item-'+secrets.token_hex(6),'country':str((lot or {}).get('country') or 'بث مباشر').strip()[:120],
          'denomination':title,'marketTitle':title,'type':'مقتنى بث مباشر','condition':str((lot or {}).get('condition') or '').strip()[:80],
          'notes':str((lot or {}).get('notes') or 'أُنشئ السجل من مزاد كاميرا مباشر بعد اعتماد البيع.').strip()[:1000],
          'ownerParticipantId':str(row.get('broadcasterParticipantId') or ''),'ownerName':str(row.get('broadcasterName') or 'الإدارة'),
          'forMarket':False,'forAuction':False,'archived':False,'sourceChannel':'live_camera','sourceLiveSessionId':str(row.get('id') or ''),
          'created':now_iso,'updated':int(time.time()*1000)}
    items.append(item); save(items); return item

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
    # R9.2A: use the same Saudi-time/epoch normalization as the public auction feed.
    # This avoids Render UTC making an ended auction look active for extra hours.
    try:
        end_ms=auction_end_epoch_ms(raw)
        return bool(end_ms and end_ms>int(time.time()*1000))
    except Exception:
        try: return datetime.datetime.fromisoformat(raw)>auction_local_now()
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

def reconcile_collectible_lifecycle(participant_id=None):
    """
    إصلاح دورة حياة مقتنيات العملاء دون حذف التاريخ:
    - يفك السجلات العالقة التي تحمل itemId غير موجود.
    - يعيد ربط المقتنى الموجود عبر sourceSubmissionId.
    - يعيد إنشاء المقتنى المعتمد المفقود عند إمكان ذلك بأمان.
    - يثبت ownerParticipantId و sourceSubmissionId.
    - لا ينشئ نسخة ثانية لمقتنى موجود.
    """
    items=load()
    rows=load_collectible_submissions()
    pid_filter=str(participant_id or '').strip()
    changed_items=False
    changed_rows=False
    report={'ok':True,'relinked':0,'recreated':0,'unlocked':0,'ownerFixed':0,'approvedFixed':0,'manualReview':[]}

    by_id={str(x.get('id') or ''):x for x in items if x.get('id')}
    by_submission={str(x.get('sourceSubmissionId') or ''):x for x in items if x.get('sourceSubmissionId')}

    def _safe_new_item(row, preferred_id=''):
        nonlocal changed_items
        sid=str(row.get('id') or '')
        serial=str(row.get('serial') or '').strip()
        norm=re.sub(r'\s+','',serial).upper()
        if norm:
            for other in items:
                values=other.get('serials') or [other.get('serial')]
                if not isinstance(values,list): values=[values]
                other_norms={re.sub(r'\s+','',str(v or '')).upper() for v in values if str(v or '').strip()}
                if norm in other_norms:
                    report['manualReview'].append({'submissionId':sid,'reason':'duplicate_serial','serial':serial})
                    return None
        inv=submission_inventory_values(row)
        item_id=str(preferred_id or '').strip()
        if not item_id or item_id in by_id:
            item_id='k-'+secrets.token_hex(8)
        now=datetime.datetime.now().isoformat()
        destination=str(row.get('desiredDestination') or 'vault')
        item={
            'id':item_id,
            'country':row.get('country',''),
            'denomination':row.get('denomination',''),
            'issueEdition':row.get('issueEdition',''),
            'year':row.get('year',''),
            'type':row.get('type') or 'عملة ورقية',
            'condition':row.get('condition','UNC'),
            'soldQuantity':0,
            'damagedQuantity':0,
            'serial':serial,
            'serials':[serial] if serial else [],
            'frontImg':row.get('frontImage',''),
            'backImg':row.get('backImage',''),
            'notes':row.get('notes',''),
            'ownerName':row.get('participantName',''),
            'ownerPhone':row.get('participantPhone',''),
            'ownerParticipantId':row.get('participantId',''),
            'sourceSubmissionId':sid,
            'storageStatus':'warehouse',
            'warehouse':'المستودع الرئيسي',
            'forMarket':False,
            'marketApproved':False,
            'forAuction':False,
            'auctionApproved':False,
            'created':now,
            'updated':int(time.time()*1000),
            **inv
        }
        items.append(item)
        by_id[item_id]=item
        by_submission[sid]=item
        changed_items=True
        report['recreated']+=1
        return item

    for row in rows:
        if pid_filter and str(row.get('participantId') or '')!=pid_filter:
            continue

        # من V4.8.0 لا توجد موافقة مسبقة لطلبات العملاء العادية.
        # R9.3: سجلات «مسؤول إدخال البيانات» مستثناة صراحةً؛ تبقى بانتظار اعتماد الإدارة.
        if row.get('submissionSource')!='data_entry' and row.get('status') in ('pending','needs_changes') and not row.get('itemId'):
            if str(row.get('country') or '').strip() and str(row.get('denomination') or '').strip():
                item=_safe_new_item(row,'')
                if item:
                    row['itemId']=item.get('id')
                    row['status']='approved'
                    row['warehouseVerified']=True
                    row['warehouseVerifiedAt']=datetime.datetime.now().isoformat()
                    row['autoApproved']=True
                    row['autoApprovedAt']=row['warehouseVerifiedAt']
                    changed_rows=True

        sid=str(row.get('id') or '')
        row_item_id=str(row.get('itemId') or '')
        item=by_id.get(row_item_id) if row_item_id else None

        if not item and sid:
            linked=by_submission.get(sid)
            if linked:
                item=linked
                if row_item_id!=str(item.get('id') or ''):
                    row['itemId']=item.get('id')
                    changed_rows=True
                    report['relinked']+=1

        # itemId عالق بلا مقتنى:
        if not item and row_item_id:
            if row.get('status')=='approved' or row.get('warehouseVerified'):
                item=_safe_new_item(row,row_item_id)
                if not item:
                    # لا نتركه عالقًا: يرجع للاستكمال مع الحفاظ على التاريخ.
                    row['itemId']=''
                    row['warehouseVerified']=False
                    row['warehouseVerifiedAt']=''
                    row['status']='needs_changes'
                    note='تعذر استعادة المقتنى تلقائيًا بسبب تعارض يحتاج مراجعة الإدارة.'
                    row['adminNote']=((str(row.get('adminNote') or '')+' '+note).strip())
                    changed_rows=True
                    report['unlocked']+=1
            else:
                # لم يُعتمد فعليًا، إذن itemId القديم رابط يتيم ويمنع التعديل والحذف.
                row['itemId']=''
                row['warehouseVerified']=False
                row['warehouseVerifiedAt']=''
                changed_rows=True
                report['unlocked']+=1

        # معتمد بلا itemId:
        if not item and row.get('status')=='approved':
            item=_safe_new_item(row,'')
            if item:
                row['itemId']=item.get('id')
                row['warehouseVerified']=True
                row['warehouseVerifiedAt']=datetime.datetime.now().isoformat()
                changed_rows=True

        if item:
            # تثبيت الربط والمالك من المصدر الأصلي، لكن لا نستولي على مقتنى يملكه حساب آخر.
            item_pid=str(item.get('ownerParticipantId') or '')
            row_pid=str(row.get('participantId') or '')
            phones_match=_norm_phone(item.get('ownerPhone')) and _norm_phone(item.get('ownerPhone'))==_norm_phone(row.get('participantPhone'))
            if not item_pid or item_pid==row_pid or phones_match:
                if item_pid!=row_pid and row_pid:
                    item['ownerParticipantId']=row_pid
                    changed_items=True
                    report['ownerFixed']+=1
            if not item.get('sourceSubmissionId') and sid:
                item['sourceSubmissionId']=sid
                changed_items=True
            if str(row.get('itemId') or '')!=str(item.get('id') or ''):
                row['itemId']=item.get('id')
                changed_rows=True
                report['relinked']+=1

            # إذا كان المقتنى موجودًا ومصدره هذا الطلب، فالطلب تم اعتماده فعليًا.
            if str(item.get('sourceSubmissionId') or '')==sid and row.get('status')!='approved':
                row['status']='approved'
                row['warehouseVerified']=True
                row['warehouseVerifiedAt']=row.get('warehouseVerifiedAt') or datetime.datetime.now().isoformat()
                changed_rows=True
                report['approvedFixed']+=1

            # استكمال الحقول الناقصة فقط دون الكتابة فوق بيانات أحدث.
            inv=submission_inventory_values(row)
            fill_pairs=(
                ('country',row.get('country','')),('denomination',row.get('denomination','')),
                ('issueEdition',row.get('issueEdition','')),('year',row.get('year','')),
                ('type',row.get('type') or 'عملة ورقية'),('condition',row.get('condition','UNC')),
                ('frontImg',row.get('frontImage','')),('backImg',row.get('backImage','')),
                ('ownerName',row.get('participantName','')),('ownerPhone',row.get('participantPhone',''))
            )
            for key,value in fill_pairs:
                if item.get(key) in (None,'') and value not in (None,''):
                    item[key]=value
                    changed_items=True
            for key,value in inv.items():
                if item.get(key) in (None,''):
                    item[key]=value
                    changed_items=True

            destination=str(row.get('desiredDestination') or 'vault')
            if destination=='market' and not item.get('auctionSold'):
                if not item.get('forMarket'):
                    item['forMarket']=True
                    item['marketApproved']=False
                    changed_items=True
            elif destination=='auction' and not item.get('auctionSold'):
                if not item.get('forAuction'):
                    item['forAuction']=True
                    item['auctionApproved']=False
                    changed_items=True

    if changed_items:
        save(items)
    if changed_rows:
        save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
    if changed_items or changed_rows:
        append_operation('إصلاح تلقائي لدورة مقتنيات العملاء',{
            'participantId':pid_filter,'relinked':report['relinked'],'recreated':report['recreated'],
            'unlocked':report['unlocked'],'ownerFixed':report['ownerFixed'],
            'approvedFixed':report['approvedFixed'],'manualReview':report['manualReview']
        })
    return report

def repair_approved_submission_inventory():
    # توافق خلفي مع زر الإصلاح الإداري القديم.
    report=reconcile_collectible_lifecycle()
    report['inventory']=inventory_summary()
    return report

def storage_location(item):
    return {'warehouse':item.get('warehouse',''),'cabinet':item.get('cabinet',''),'shelf':item.get('shelf',''),'box':item.get('box',''),'album':item.get('album',''),'pocket':item.get('pocket','')}

def participant_shipping_address(person):
    person=person or {}
    raw=person.get('shippingAddress') if isinstance(person.get('shippingAddress'),dict) else {}
    return {
        'recipientName':str(raw.get('recipientName') or person.get('name') or '').strip()[:120],
        'recipientPhone':str(raw.get('recipientPhone') or person.get('phone') or '').strip()[:40],
        'country':str(raw.get('country') or person.get('country') or '').strip()[:80],
        'city':str(raw.get('city') or '').strip()[:100],
        'district':str(raw.get('district') or '').strip()[:120],
        'addressLine':str(raw.get('addressLine') or '').strip()[:240],
        'postalCode':str(raw.get('postalCode') or '').strip()[:30],
        'notes':str(raw.get('notes') or '').strip()[:240],
    }

def order_from_auction(due,item,person):
    physical=max(1,inventory_int(item.get('auctionQuantity'),1))
    return {'id':'ord-'+secrets.token_hex(6),'orderNumber':'NW-'+datetime.datetime.now().strftime('%y%m%d')+'-'+secrets.token_hex(3).upper(),'source':'auction','storeType':item_store_type(item),'sourceId':due.get('id'),'auctionRound':due.get('auctionRound'),'participantId':due.get('participantId'),'customerName':person.get('name',''),'customerPhone':person.get('phone',''),'status':'awaiting_payment','paymentStatus':'unpaid','created':datetime.datetime.now().isoformat(),'updated':datetime.datetime.now().isoformat(),'subtotal':float(due.get('amount') or 0),'buyerFee':0,'total':float(due.get('amount') or 0),'items':[{'itemId':item.get('id'),'title':item_title(item),'quantity':1,'physicalQuantity':physical,'unitPrice':float(due.get('amount') or 0),'total':float(due.get('amount') or 0),'images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'storage':storage_location(item)}],'shippingFee':0,'shippingFeeConfirmed':False,'shippingCompany':'','trackingNumber':'','shippingAddress':participant_shipping_address(person),'history':[{'status':'awaiting_payment','at':datetime.datetime.now().isoformat(),'note':'تم إنشاء الطلب تلقائيًا من فوز المزاد'}],'archived':False}

def create_order_for_due(due):
    orders=load_orders(); existing=next((o for o in orders if o.get('source')=='auction' and str(o.get('sourceId'))==str(due.get('id'))),None)
    if existing: return existing
    item=next((i for i in load() if str(i.get('id'))==str(due.get('itemId'))),{})
    person=next((x for x in load_people() if str(x.get('id'))==str(due.get('participantId'))),{})
    row=order_from_auction(due,item,person); orders.append(row); save_json(ORDERS,{'orders':orders}); due['orderId']=row['id']; return row

def create_order_for_market(req):
    orders=load_orders(); existing=next((o for o in orders if o.get('source')=='market' and str(o.get('sourceId'))==str(req.get('id'))),None)
    if existing:
        if bool(existing.get('archived')) or str(existing.get('status') or '') in ('cancelled','returned'):
            now=datetime.datetime.now().isoformat()
            existing['archived']=False
            existing['archivedAt']=''
            existing['archiveReason']=''
            existing['status']='awaiting_payment'
            existing['paymentStatus']='unpaid'
            existing['paidAt']=''
            existing['paidAmount']=0
            existing['shippingFee']=0
            existing['shippingFeeConfirmed']=False
            existing['shippingCompany']=''
            existing['trackingNumber']=''
            person=next((x for x in load_people() if str(x.get('id'))==str(req.get('participantId') or '')),{})
            existing['shippingAddress']=participant_shipping_address(person)
            existing['total']=float(existing.get('subtotal') or 0)+float(existing.get('buyerFee') or 0)
            existing['updated']=now
            hist=list(existing.get('history') or [])
            hist.append({'status':'awaiting_payment','at':now,'note':'إعادة تفعيل الطلب إداريًا من طلب السوق'})
            existing['history']=hist
            save_json(ORDERS,{'orders':orders})
        return existing
    item=next((i for i in load() if str(i.get('id'))==str(req.get('itemId'))),{})
    subtotal=float(req.get('offeredAmount') or req.get('listedAmount') or 0); fee=float(req.get('buyerFeeAmount') or 0)
    units=max(1,inventory_int(req.get('quantity'),1)); physical=units*market_physical_per_unit(item)
    person=next((x for x in load_people() if str(x.get('id'))==str(req.get('participantId') or '')),{})
    row={'id':'ord-'+secrets.token_hex(6),'orderNumber':'NW-'+datetime.datetime.now().strftime('%y%m%d')+'-'+secrets.token_hex(3).upper(),'source':'market','storeType':item_store_type(item),'sourceId':req.get('id'),'participantId':str(req.get('participantId') or ''),'customerName':req.get('name',''),'customerPhone':req.get('phone',''),'status':'awaiting_payment','paymentStatus':'unpaid','created':datetime.datetime.now().isoformat(),'updated':datetime.datetime.now().isoformat(),'subtotal':subtotal,'buyerFee':fee,'total':float(req.get('buyerTotal') or subtotal+fee),'items':[{'itemId':item.get('id'),'title':req.get('itemTitle') or item_title(item),'quantity':units,'physicalQuantity':physical,'unitPrice':float(req.get('unitPrice') or 0),'total':subtotal,'images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'storage':storage_location(item),'selectedSerials':list(req.get('selectedSerials') or [])}],'shippingFee':0,'shippingFeeConfirmed':False,'shippingCompany':'','trackingNumber':'','shippingAddress':participant_shipping_address(person),'history':[{'status':'awaiting_payment','at':datetime.datetime.now().isoformat(),'note':'تم إنشاء الطلب من السوق العام'}],'archived':False}
    orders.append(row); save_json(ORDERS,{'orders':orders}); req['orderId']=row['id']; return row

def reconcile_direct_market_buy_orders(participant_id=''):
    """Direct purchases do not wait for admin approval. Repair older pending buy rows too."""
    requests=load_market_requests(); changed=False; repaired=0
    for req in requests:
        if str(req.get('action') or 'buy')!='buy': continue
        if participant_id and str(req.get('participantId') or '')!=str(participant_id): continue
        if str(req.get('status') or 'pending')=='pending':
            req['status']='accepted'; req['acceptedAt']=req.get('acceptedAt') or datetime.datetime.now().isoformat(); req['updated']=datetime.datetime.now().isoformat(); changed=True
        if str(req.get('status'))=='accepted':
            order=create_order_for_market(req)
            if order and not req.get('orderId'):
                req['orderId']=order.get('id'); changed=True
            repaired+=1
    if changed: save_json(MARKET_REQUESTS,{'requests':requests})
    return repaired

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
    if status=='paid':
        order['paymentStatus']='paid'; order['paidAt']=now
        if str(order.get('paymentProofStatus') or '')=='pending': order['paymentProofStatus']='approved'; order['paymentProofApprovedAt']=now
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

AUCTION_TZ=datetime.timezone(datetime.timedelta(hours=3))
def auction_end_epoch_ms(value):
    """Convert stored auctionEnd to a real epoch. Naive values are Saudi wall-clock."""
    raw=str(value or '').strip()
    if not raw: return 0
    try:
        dt=datetime.datetime.fromisoformat(raw.replace('Z','+00:00'))
        if dt.tzinfo is None: dt=dt.replace(tzinfo=AUCTION_TZ)
        return int(dt.timestamp()*1000)
    except Exception:
        return 0

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
    now=datetime.datetime.now(); dues=ensure_auction_outcomes(); orders=load_orders()
    for x in dues:
        if str(x.get('participantId'))!=str(pid) or x.get('status')!='unpaid': continue
        # R9: العميل الذي رفع إثبات السداد في المهلة لا يُعاقب أثناء انتظار مراجعة الإدارة.
        linked=next((o for o in orders if o.get('source')=='auction' and str(o.get('sourceId') or '')==str(x.get('id') or '')),None)
        if linked and (str(linked.get('paymentStatus') or '')=='proof_submitted' or str(linked.get('paymentProofStatus') or '')=='pending'): continue
        try:
            if datetime.datetime.fromisoformat(str(x.get('paymentDeadline')))<=now: return x
        except Exception: pass
    return None

def load_settings():
    defaults={'buyerFeePercent':2.5,'charityProfitPercent':5.0,'auctionEntryFee':10.0,'entryFeeEnabled':True,'negotiationPercents':[5,10,15,20],'negotiationHours':48,'adminEmail':'','platformName':'نوادر العملات','whatsappVerificationNumber':'966551892409','duesTrackingStartedAt':'','paymentBankName':'','paymentAccountName':'','paymentIban':'','paymentInstructions':'حوّل المبلغ النهائي بعد اعتماد الشحن، ثم ارفع صورة إشعار التحويل من صفحة المستحقات.','paymentWhatsapp':'','visitorSections':{'market':True,'auction':True,'specialNumbers':True,'transitionalIssues':True,
            'fantasia':True},'fullPublicEnableV493':False}
    x=load_json(SETTINGS,defaults.copy())
    defaults.update(x if isinstance(x,dict) else {})
    vis=defaults.get('visitorSections')
    if not isinstance(vis,dict): vis={}
    defaults['visitorSections']={
        'market': bool(vis.get('market',True)),
        'auction': bool(vis.get('auction',True)),
        'specialNumbers': bool(vis.get('specialNumbers',True)),
        'transitionalIssues': bool(vis.get('transitionalIssues',True)),
        'fantasia': bool(vis.get('fantasia',True)),
    }
    # V4.9.3 one-time corrective migration:
    # previous market-first launch mode may have left public sections/auction fee disabled.
    # Enable all once, persist the correction, then future admin changes remain authoritative.
    if not bool(defaults.get('fullPublicEnableV493')):
        defaults['visitorSections']={
            'market':True,
            'auction':True,
            'specialNumbers':True,
            'transitionalIssues':True,
            'fantasia':True,
        }
        defaults['entryFeeEnabled']=True
        defaults['fullPublicEnableV493']=True
        save_json(SETTINGS,defaults)
    return defaults

def effective_visitor_sections(settings=None):
    st=settings or load_settings(); vs=dict(st.get('visitorSections') or {})
    return {
        'market':vs.get('market',True) is not False,
        'auction':vs.get('auction',True) is not False,
        'specialNumbers':vs.get('specialNumbers',True) is not False,
        'transitionalIssues':vs.get('transitionalIssues',True) is not False,
        'fantasia':vs.get('fantasia',True) is not False,
    }

BACKUP_FILES=[
    ('khazina_shared_data.json',DATA),('auction_participants.json',PEOPLE),
    ('auction_bids.json',BIDS),('auction_negotiations.json',NEGOTIATIONS),
    ('market_requests.json',MARKET_REQUESTS),('subscription_ledger.json',SUBSCRIPTIONS),('save_audit.json',SAVE_AUDIT),('platform_settings.json',SETTINGS),
    ('notifications.json',NOTIFICATIONS),('auction_dues.json',AUCTION_DUES),('user_permissions.json',USER_PERMISSIONS),('operations_log.json',OPERATIONS_LOG),('orders_shipping.json',ORDERS),('collectible_submissions.json',COLLECTIBLE_SUBMISSIONS),('image_vault.json',IMAGE_VAULT),('live_auctions.json',LIVE_AUCTIONS)
]

def create_full_backup_bytes():
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_DEFLATED) as z:
        manifest={'format':'khazina-full-backup','version':2,'created':datetime.datetime.now().isoformat(),'includes':['data','participants','bids','negotiations','market_requests','orders_shipping','collectible_submissions','image_vault','subscriptions','settings','uploads']}
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
    # Public auction serialization must never fail the whole auction feed because of one legacy value.
    try: round_no=max(1,int(float(i.get('auctionRound') or 1)))
    except Exception: round_no=1
    bids=[]
    for b in load_bids():
        try: br=max(1,int(float(b.get('auctionRound') or 1)))
        except Exception: br=1
        if str(b.get('itemId') or '')==str(i.get('id') or '') and br==round_no:
            bids.append(b)
    amounts=[]
    for b in bids:
        try: amounts.append(float(b.get('amount') or 0))
        except Exception: amounts.append(0.0)
    top=max(amounts+[0.0])
    try: target=auction_target(i)
    except Exception: target=0.0
    reserve_state='none' if target<=0 else ('met' if top>=target else 'below')
    ended=False
    end=str(i.get('auctionEnd') or '').strip()
    if end:
        try: ended=datetime.datetime.fromisoformat(end) <= auction_local_now()
        except Exception: ended=False
    sold=bool(ended and bids and (target<=0 or top>=target))
    public_keys=['id','storeType','collectibleCategory','collectibleBrand','collectibleMaterial','collectibleModel','collectibleScale','country','denomination','year','type','condition','quantity','serials','frontImg','backImg','gradingCertImage','additionalImages','auctionEnd','auctionOpeningPrice','auctionBidStep','auctionAdditionalTerms','notes','negotiationEnabled','negotiationPercent','auctionRound','issueEdition','issueEditionOther','isGraded','gradingCompany','gradeValue','gradePercent','gradingCertNumber','specialNumberEnabled','specialNumberType','specialNumberTypes','specialNumberReason','transitionalIssueEnabled','transitionalIssueType','transitionalRarity','fantasiaEnabled','homeFeatured','homeQuickDeal','homeDiscounted','homeDiscountPercent','homePromoUntil','homePromoBadge','homePromoPriority','updated']
    out={k:i.get(k) for k in public_keys}
    out['storeType']=item_store_type(i)
    out.update(public_seller_identity(i))
    out.update({'auctionCurrentPrice':top,'bidCount':len(bids),'reserveState':reserve_state,'auctionEnded':ended,'auctionSold':sold})
    out['auctionEndEpochMs']=auction_end_epoch_ms(end)
    out['auctionActive']=bool(i.get('forAuction') and i.get('auctionApproved') and not ended)
    return out



def public_market_item(i):
    # السوق العام لا يرسل سعر الشراء أو الموقع الداخلي أو أي بيانات مالية/إدارية سرية.
    keys=['id','storeType','collectibleCategory','collectibleBrand','collectibleMaterial','collectibleModel','collectibleScale','country','denomination','year','type','condition','quantity','frontImg','backImg','gradingCertImage','additionalImages','notes',
          'issueEdition','issueEditionOther','isGraded','gradingCompany','gradeValue','gradePercent','gradingCertNumber','gradingVerificationStatus','gradingNotes',
          'marketCategory','marketOfferType','marketSalePrice','marketUnitPrice','marketQuantity','marketSetPieces','marketSetSize','marketSetCurrencyMode','marketPriceUnit',
          'marketPartialAllowed','marketNegotiationEnabled','marketNegotiationPercent','marketTitle','homeFeatured','homeQuickDeal','homeDiscounted','homeDiscountPercent','homePromoUntil','homePromoBadge','homePromoPriority','updated','specialNumberEnabled','specialNumberType','specialNumberTypes','specialNumberReason','transitionalIssueEnabled','transitionalIssueType','transitionalRarity','fantasiaEnabled']
    out={k:i.get(k) for k in keys}
    out['storeType']=item_store_type(i)
    out.update(public_seller_identity(i))
    _,_,reserved=item_order_quantities(i.get('id'),item=i)
    per_unit=market_physical_per_unit(i)
    reserved_units=(reserved.get('market',0)+per_unit-1)//per_unit
    sold_units=int(i.get('marketSoldQuantity') or 0)
    out['availableQuantity']=max(0,int(i.get('marketQuantity') or i.get('quantity') or 1)-sold_units-reserved_units)
    out['availabilityStatus']='available' if out['availableQuantity']>0 else ('reserved' if reserved_units>0 else 'sold')
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
    keys=("id","storeType","country","denomination","year","condition","serial","serials","frontImg","backImg","gradingCertImage","additionalImages","specialNumberType","specialNumberTypes","specialNumberReason","marketSalePrice","marketUnitPrice","marketNegotiationEnabled","marketNegotiationPercent","marketOfferType","marketTitle","homeFeatured","homeQuickDeal","homeDiscounted","homeDiscountPercent","homePromoUntil","homePromoBadge","homePromoPriority","quantity")
    out={k:item.get(k) for k in keys}; out['storeType']=item_store_type(item); out.update(public_seller_identity(item)); out.update({"availableSerials":available,"availableQuantity":qty,"unitPrice":price,"saleEnabled":sale,"soldOut":status=="sold","availabilityStatus":status}); return out

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
    # لا توجد كلمة مرور افتراضية مضمنة. تستخدم فقط عند تهيئة auth لأول مرة.
    return str(os.environ.get('ADMIN_PASSWORD') or '')

def ensure_admin_auth():
    cfg=load_json(AUTH_FILE,{})
    password=_configured_admin_password()
    if isinstance(cfg,dict) and cfg.get('salt') and cfg.get('hash') and cfg.get('username'):
        # إذا وُضع ADMIN_PASSWORD في Render بقيمة جديدة، يُعتبر ذلك تدويرًا مقصودًا لكلمة المرور.
        if password:
            try:
                current=_pbkdf2(password,cfg['salt'],int(cfg.get('iterations') or 260000))
                if not secrets.compare_digest(current,str(cfg.get('hash') or '')):
                    iterations=260000; salt=secrets.token_hex(16)
                    cfg={'version':3,'username':'admin','salt':salt,'iterations':iterations,'hash':_pbkdf2(password,salt,iterations),'created':datetime.datetime.now().isoformat(),'source':'ADMIN_PASSWORD-ROTATED'}
                    save_json(AUTH_FILE,cfg)
            except Exception:
                pass
        return cfg, None
    if not password:
        raise RuntimeError('لم يتم تهيئة دخول الإدارة. عيّن متغير ADMIN_PASSWORD في Render مرة واحدة ثم أعد التشغيل.')
    iterations=260000
    salt=secrets.token_hex(16)
    cfg={'version':3,'username':'admin','salt':salt,'iterations':iterations,'hash':_pbkdf2(password,salt,iterations),'created':datetime.datetime.now().isoformat(),'source':'ADMIN_PASSWORD'}
    save_json(AUTH_FILE,cfg)
    return cfg, None

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
        for extra in (row.get('additionalImages') or []):
            if urlparse(str(extra or '')).path==path: return True
    return False


def archive_item_record(item,reason='',actor='الإدارة'):
    if not item: return False
    if moderation_status(item)=='archived': return True
    now=datetime.datetime.now().isoformat()
    item['archivePreviousState']={
        'forMarket':bool(item.get('forMarket')),
        'marketApproved':bool(item.get('marketApproved')),
        'forAuction':bool(item.get('forAuction')),
        'auctionApproved':bool(item.get('auctionApproved')),
        'storageStatus':item.get('storageStatus','warehouse'),
        'moderationStatus':moderation_status(item),
    }
    item['moderationStatus']='archived'
    item['archiveReason']=str(reason or '').strip()
    item['archivedAt']=now
    item['archivedBy']=actor
    # الإخفاء من جميع الواجهات فورًا مع إبقاء المعاملات والسجل محفوظين.
    item['forMarket']=False; item['marketApproved']=False
    if item.get('forAuction') and not item.get('auctionSold') and not item.get('auctionOutcome')=='sold':
        item['auctionCancelled']=True
        item['auctionCancelReason']='نقل المقتنى إلى الأرشيف بواسطة الإدارة'
        item['auctionCancelledAt']=now
    item['forAuction']=False; item['auctionApproved']=False
    item['storageStatus']='archived'
    item['updated']=int(time.time()*1000)
    return True

def restore_archived_item(item,actor='الإدارة'):
    if not item: return {'ok':False,'warning':''}
    prev=item.get('archivePreviousState') if isinstance(item.get('archivePreviousState'),dict) else {}
    warning=''
    item['moderationStatus']='active'
    item['storageStatus']=prev.get('storageStatus') or 'warehouse'
    item['ownerArchived']=False; item['ownerArchivedAt']=''
    item['archiveRestoredAt']=datetime.datetime.now().isoformat(); item['archiveRestoredBy']=actor
    # السوق يمكن استعادته إذا بقيت كمية متاحة.
    available=max(0,int(item.get('quantity') or 0)-int(item.get('soldQuantity') or 0)-int(item.get('damagedQuantity') or 0))
    market_restore=bool(prev.get('forMarket') and prev.get('marketApproved') and available>0)
    item['forMarket']=market_restore; item['marketApproved']=market_restore
    # المزاد يعاد فقط إذا كان ما زال صالحًا زمنيًا ولم يبع سابقًا.
    auction_restore=False
    if prev.get('forAuction') and prev.get('auctionApproved') and not item.get('auctionSold') and item.get('auctionOutcome')!='sold':
        try:
            end_dt=datetime.datetime.fromisoformat(str(item.get('auctionEnd') or '').replace('Z','+00:00'))
            now_dt=datetime.datetime.now(end_dt.tzinfo) if end_dt.tzinfo else auction_local_now()
            auction_restore=end_dt>now_dt
        except Exception:
            auction_restore=False
    item['forAuction']=auction_restore; item['auctionApproved']=auction_restore
    if auction_restore:
        item['auctionCancelled']=False; item['auctionCancelReason']=''; item['auctionCancelledAt']=''
    elif prev.get('forAuction'):
        warning='تمت استعادة المقتنى، لكن المزاد السابق لم يُعد تلقائيًا لأنه منتهٍ أو غير صالح لإعادة التشغيل.'
    item['updated']=int(time.time()*1000)
    return {'ok':True,'warning':warning}

def platform_integrity_report():
    items=load(); people=load_people(); submissions=load_collectible_submissions()
    duplicate_ids={}
    seen={}
    for i in items:
        iid=str(i.get('id') or '')
        if not iid: continue
        seen.setdefault(iid,[]).append(i)
    duplicate_ids={k:len(v) for k,v in seen.items() if len(v)>1}

    serial_map={}
    for i in items:
        vals=i.get('serials') or [i.get('serial')]
        if not isinstance(vals,list): vals=[vals]
        for s in vals:
            norm=re.sub(r'\s+','',str(s or '')).upper()
            if norm: serial_map.setdefault(norm,[]).append(str(i.get('id') or ''))
    duplicate_serials={k:v for k,v in serial_map.items() if len(set(v))>1}

    phones={}
    for p in people:
        key=_norm_phone(p.get('phone'))
        if key: phones.setdefault(key,[]).append(str(p.get('id') or ''))
    duplicate_phones={k:v for k,v in phones.items() if len(v)>1}

    orphan_owners=[str(i.get('id') or '') for i in items if i.get('ownerParticipantId') and not any(str(p.get('id'))==str(i.get('ownerParticipantId')) for p in people)]
    zero_price_market=[str(i.get('id') or '') for i in items if item_is_public(i) and i.get('forMarket') and i.get('marketApproved') and float(i.get('marketSalePrice') or i.get('marketUnitPrice') or 0)<=0]
    invalid_auctions=[str(i.get('id') or '') for i in items if item_is_public(i) and i.get('forAuction') and i.get('auctionApproved') and (not i.get('auctionEnd') or float(i.get('auctionOpeningPrice') or i.get('auctionStartPrice') or 0)<=0)]
    item_ids={str(i.get('id') or '') for i in items}
    orphan_submissions=[str(x.get('id') or '') for x in submissions if x.get('itemId') and str(x.get('itemId')) not in item_ids]
    missing_images=[str(i.get('id') or '') for i in items if not i.get('frontImg') and not i.get('backImg')]

    return {
        'version':'4.8.1',
        'counts':{'items':len(items),'participants':len(people),'submissions':len(submissions)},
        'issues':{
            'duplicateIds':duplicate_ids,
            'duplicateSerials':duplicate_serials,
            'duplicatePhones':duplicate_phones,
            'orphanOwners':orphan_owners,
            'zeroPriceMarket':zero_price_market,
            'invalidAuctions':invalid_auctions,
            'orphanSubmissions':orphan_submissions,
            'missingImages':missing_images
        },
        'issueCount':sum([
            len(duplicate_ids),len(duplicate_serials),len(duplicate_phones),len(orphan_owners),
            len(zero_price_market),len(invalid_auctions),len(orphan_submissions),len(missing_images)
        ])
    }


def _oauth_prune():
    now=time.time()
    for bag,ttl in ((GOOGLE_OAUTH_STATES,GOOGLE_FLOW_TTL_SECONDS),(GOOGLE_PENDING_LINKS,GOOGLE_FLOW_TTL_SECONDS),(FACEBOOK_OAUTH_STATES,FACEBOOK_STATE_TTL_SECONDS),(FACEBOOK_PENDING_LINKS,FACEBOOK_PENDING_TTL_SECONDS)):
        for key,val in list(bag.items()):
            if now-float(val.get('created') or 0)>ttl:
                bag.pop(key,None)

def _safe_next_path(value):
    value=str(value or '').strip()
    if value.startswith('/') and not value.startswith('//') and '\\' not in value:
        return value[:500]
    return '/account'

def _google_redirect_uri(handler):
    if GOOGLE_REDIRECT_URI: return GOOGLE_REDIRECT_URI
    proto=(handler.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
    if proto not in ('http','https'): proto='https'
    host=(handler.headers.get('Host') or '').strip()
    return f'{proto}://{host}/auth/google/callback'

def _google_http_json(url, method='GET', data=None, headers=None, timeout=15):
    body=None
    hdr={'Accept':'application/json','User-Agent':'DarAlMuqtanyat/1.0'}
    if headers: hdr.update(headers)
    if data is not None:
        body=urlencode(data).encode('utf-8')
        hdr.setdefault('Content-Type','application/x-www-form-urlencoded')
    req=urllib.request.Request(url,data=body,headers=hdr,method=method)
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        raw=resp.read()
    return json.loads(raw.decode('utf-8'))

def _google_profile_from_code(code, redirect_uri):
    token=_google_http_json('https://oauth2.googleapis.com/token','POST',{
        'code':code,'client_id':GOOGLE_CLIENT_ID,'client_secret':GOOGLE_CLIENT_SECRET,
        'redirect_uri':redirect_uri,'grant_type':'authorization_code'
    })
    access=str(token.get('access_token') or '')
    if not access: raise ValueError('لم يصل رمز دخول صالح من Google')
    profile=_google_http_json('https://openidconnect.googleapis.com/v1/userinfo','GET',headers={'Authorization':'Bearer '+access})
    sub=str(profile.get('sub') or '').strip(); email=str(profile.get('email') or '').strip().lower()
    if not sub or not email or profile.get('email_verified') is False:
        raise ValueError('تعذر التحقق من هوية حساب Google')
    return {'sub':sub,'email':email[:240],'name':str(profile.get('name') or '').strip()[:120],
            'picture':str(profile.get('picture') or '').strip()[:500]}

def _google_public_profile(p):
    return {'name':p.get('name',''),'email':p.get('email',''),'picture':p.get('picture','')}

def _facebook_redirect_uri(handler):
    if FACEBOOK_REDIRECT_URI: return FACEBOOK_REDIRECT_URI
    proto=(handler.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
    if proto not in ('http','https'): proto='https'
    host=(handler.headers.get('Host') or '').strip()
    return f'{proto}://{host}/auth/facebook/callback'

def _facebook_profile_from_code(code,redirect_uri):
    token_url='https://graph.facebook.com/oauth/access_token?'+urlencode({
        'client_id':FACEBOOK_APP_ID,'client_secret':FACEBOOK_APP_SECRET,
        'redirect_uri':redirect_uri,'code':code
    })
    token=_google_http_json(token_url)
    access=str(token.get('access_token') or '').strip()
    if not access: raise ValueError('لم يصل رمز دخول صالح من Facebook')
    profile_url='https://graph.facebook.com/me?'+urlencode({
        'fields':'id,name,email,picture.type(large)','access_token':access
    })
    profile=_google_http_json(profile_url)
    fid=str(profile.get('id') or '').strip()
    if not fid: raise ValueError('تعذر التحقق من هوية حساب Facebook')
    picture=''
    try: picture=str((((profile.get('picture') or {}).get('data') or {}).get('url')) or '').strip()
    except Exception: picture=''
    return {'id':fid[:120],'email':str(profile.get('email') or '').strip().lower()[:240],
            'name':str(profile.get('name') or '').strip()[:120],'picture':picture[:500]}

def _facebook_public_profile(p):
    return {'name':p.get('name',''),'email':p.get('email',''),'picture':p.get('picture','')}

ADMIN_GET_API={
    '/api/negotiations','/api/backup/full','/api/items','/api/participants','/api/participants/summary',
    '/api/bids','/api/market/requests','/api/subscriptions','/api/daily-qr','/api/market-qr',
    '/api/market-qr-info','/api/daily-qr-info','/api/settings/admin','/api/ocr/status','/api/notifications/admin','/api/permissions','/api/image-vault/admin','/api/dues','/api/operations','/api/orders','/api/collectible-submissions/admin','/api/inventory/summary','/api/integrity','/api/archive/items','/api/live-auctions/admin'
}
PUBLIC_POST_API={'/api/special/request','/api/fantasia/request','/api/market/request','/api/negotiate','/api/participant/register','/api/participant/verify','/api/google/link/start','/api/facebook/link/start','/api/participant/profile','/api/bid','/api/visitor/receive','/api/visitor/order/action','/api/visitor/payment-proof','/api/notifications/read','/api/collectible-submissions','/api/collectible-submissions/delete','/api/data-entry/submissions','/api/image-vault/pull','/api/image-vault/release','/api/visitor/upload','/api/owner/item/update','/api/owner/item/delete','/api/owner/market/update','/api/owner/auction/update','/api/owner/auction/cancel','/api/seller/order/update','/api/live-auctions/bid','/api/live-auctions/seller-save','/api/live-auctions/seller-control','/api/live-auctions/chat'}
PUBLIC_STATIC={'/styles.css','/public_home.html','/dar_home.html','/collectibles_home.html','/public_market.html','/public_market.js','/public_auction.html','/public_auction.js','/special_numbers.html','/fantasia.html','/announcements.html','/account.html','/visitor.js','/visitor.css','/manifest.webmanifest','/sw.js','/notifications.html','/seller_portal.html','/seller_portal.css','/seller_portal.js','/data_entry.html','/invoice.html','/live_auction.html','/live_auction.js','/live_studio.html','/live_studio.js'}

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
    def participant_person(self):
        clean_participant_sessions(); token=self.cookie_value('NawaderParticipant')
        if not token: return None
        meta=PARTICIPANT_SESSIONS.get(token); person=None
        if meta:
            person=next((x for x in load_people() if str(x.get('id'))==str(meta.get('participantId'))),None); meta['last']=time.time()
        else:
            person=_participant_from_signed_session(token)
            if person: PARTICIPANT_SESSIONS[token]={'participantId':str(person.get('id')),'created':time.time(),'last':time.time(),'persistent':True}
        if not person or person.get('blocked') or participant_approval_status(person) in ('stopped','cancelled'):
            PARTICIPANT_SESSIONS.pop(token,None); return None
        return person
    def require_participant(self,requested_id='',api=True):
        person=self.participant_person()
        if not person:
            if api: self.sendj({'error':'انتهت جلسة الحساب أو لم يتم تسجيل الدخول. سجل الدخول من صفحة حسابي.'},401)
            return None
        if requested_id and str(person.get('id'))!=str(requested_id):
            if api: self.sendj({'error':'لا تملك صلاحية تنفيذ هذه العملية باسم حساب آخر.'},403)
            return None
        return person
    def sendj_participant(self,obj,person,status=200):
        token=_participant_session_token(person)
        PARTICIPANT_SESSIONS[token]={'participantId':str(person.get('id')),'created':time.time(),'last':time.time(),'persistent':True}
        secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store')
        self.send_header('Set-Cookie',f'NawaderParticipant={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={PARTICIPANT_SESSION_TTL_SECONDS}{secure}')
        self.end_headers(); self.wfile.write(b)
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
        self.send_header('Permissions-Policy','camera=(self), microphone=(self), geolocation=()')
        self.send_header('Content-Security-Policy',"frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        super().end_headers()
    def log_message(self, fmt, *args):
        if self.path.startswith('/api/'): print(fmt%args)
    def sendj(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8'); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(b)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def readj(self):
        # V5.2.7: live-auction routes historically called readj(); keep a single JSON reader.
        return self.body()
    def send_file(self,path,content_type=None):
        # R9.5E: stream files instead of reading the whole image into RAM.
        # Browsers request several collectible images in parallel; reading each
        # image fully could spike Render memory and surface as HTTP 502.
        try:
            f=open(path,'rb')
        except FileNotFoundError:
            self.send_error(404,'File not found'); return False
        except PermissionError:
            self.send_error(403,'File access denied'); return False
        except OSError as e:
            print('File open error:',path,repr(e))
            self.send_error(500,'File read error'); return False
        try:
            size=os.fstat(f.fileno()).st_size
            self.send_response(200)
            self.send_header('Content-Type',content_type or mimetypes.guess_type(path)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(size))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            while True:
                chunk=f.read(256*1024)
                if not chunk: break
                self.wfile.write(chunk)
            return True
        except (BrokenPipeError,ConnectionResetError):
            return False
        except OSError as e:
            print('File stream error:',path,repr(e))
            return False
        finally:
            try: f.close()
            except Exception: pass
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/auth/route':
            # Authoritative post-login routing. Public UI never grants or selects roles.
            if self.is_admin():
                self.sendj({'ok':True,'authenticated':True,'role':'admin','redirect':'/admin'}); return
            person=self.participant_person()
            if not person:
                self.sendj({'ok':True,'authenticated':False,'role':'visitor','redirect':'/account'}); return
            pid=str(person.get('id') or '')
            perms=participant_permissions(pid)
            if perms.get('dataEntry'):
                role,redirect='data_entry','/data-entry'
            elif perms.get('sellerMarket') or perms.get('sellerEndedAuctions') or perms.get('liveBroadcast'):
                role,redirect='seller','/seller'
            else:
                role,redirect='customer','/account'
            self.sendj({'ok':True,'authenticated':True,'role':role,'redirect':redirect}); return
        if p=='/api/facebook/status':
            _oauth_prune(); token=self.cookie_value('NawaderFacebookPending'); pending=FACEBOOK_PENDING_LINKS.get(token) if token else None
            self.sendj({'ok':True,'configured':bool(FACEBOOK_APP_ID and FACEBOOK_APP_SECRET),'pending':_facebook_public_profile(pending) if pending else None}); return
        if p=='/auth/facebook':
            if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
                self.send_response(302); self.send_header('Location','/account?facebook=not-configured'); self.end_headers(); return
            _oauth_prune(); qs=parse_qs(urlparse(self.path).query); nxt=_safe_next_path((qs.get('next') or ['/account'])[0])
            state=secrets.token_urlsafe(24); FACEBOOK_OAUTH_STATES[state]={'created':time.time(),'next':nxt}
            redirect_uri=_facebook_redirect_uri(self)
            params={'client_id':FACEBOOK_APP_ID,'redirect_uri':redirect_uri,'response_type':'code','scope':'public_profile,email','state':state}
            self.send_response(302); self.send_header('Location','https://www.facebook.com/dialog/oauth?'+urlencode(params)); self.end_headers(); return
        if p=='/auth/facebook/callback':
            _oauth_prune(); qs=parse_qs(urlparse(self.path).query); state=str((qs.get('state') or [''])[0]); code=str((qs.get('code') or [''])[0]); err=str((qs.get('error') or [''])[0])
            flow=FACEBOOK_OAUTH_STATES.pop(state,None)
            if err or not flow or not code:
                self.send_response(302); self.send_header('Location','/account?facebook=cancelled'); self.end_headers(); return
            try:
                fp=_facebook_profile_from_code(code,_facebook_redirect_uri(self))
                person=next((x for x in load_people() if str(x.get('facebookId') or '')==fp['id']),None)
                if person and not person.get('blocked') and participant_approval_status(person) not in ('stopped','cancelled'):
                    person['lastSeen']=datetime.datetime.now().isoformat(); people=load_people()
                    for x in people:
                        if str(x.get('id'))==str(person.get('id')): x['lastSeen']=person['lastSeen']; break
                    save_json(PEOPLE,{'participants':people})
                    token=_participant_session_token(person); PARTICIPANT_SESSIONS[token]={'participantId':str(person.get('id')),'created':time.time(),'last':time.time(),'persistent':True}
                    secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
                    self.send_response(302); self.send_header('Set-Cookie',f'NawaderParticipant={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={PARTICIPANT_SESSION_TTL_SECONDS}{secure}')
                    self.send_header('Location',_safe_next_path(flow.get('next'))); self.end_headers(); return
                if person:
                    self.send_response(302); self.send_header('Location','/account?facebook=blocked'); self.end_headers(); return
                pending_token=secrets.token_urlsafe(28); FACEBOOK_PENDING_LINKS[pending_token]={**fp,'created':time.time(),'next':_safe_next_path(flow.get('next'))}
                secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
                self.send_response(302); self.send_header('Set-Cookie',f'NawaderFacebookPending={pending_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={FACEBOOK_PENDING_TTL_SECONDS}{secure}')
                self.send_header('Location','/account?facebook=link-phone&next='+quote(_safe_next_path(flow.get('next')),safe='')); self.end_headers(); return
            except Exception as e:
                print('Facebook OAuth error:',repr(e)); self.send_response(302); self.send_header('Location','/account?facebook=error'); self.end_headers(); return
        if p=='/api/google/status':
            _oauth_prune(); token=self.cookie_value('NawaderGooglePending'); pending=GOOGLE_PENDING_LINKS.get(token) if token else None
            self.sendj({'ok':True,'configured':bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),'pending':_google_public_profile(pending) if pending else None}); return
        if p=='/auth/google':
            if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
                self.send_response(302); self.send_header('Location','/account?google=not-configured'); self.end_headers(); return
            _oauth_prune(); qs=parse_qs(urlparse(self.path).query); nxt=_safe_next_path((qs.get('next') or ['/account'])[0])
            state=secrets.token_urlsafe(24); GOOGLE_OAUTH_STATES[state]={'created':time.time(),'next':nxt}
            redirect_uri=_google_redirect_uri(self)
            params={'client_id':GOOGLE_CLIENT_ID,'redirect_uri':redirect_uri,'response_type':'code','scope':'openid email profile','state':state,'prompt':'select_account'}
            self.send_response(302); self.send_header('Location','https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(params)); self.end_headers(); return
        if p=='/auth/google/callback':
            _oauth_prune(); qs=parse_qs(urlparse(self.path).query); state=str((qs.get('state') or [''])[0]); code=str((qs.get('code') or [''])[0]); err=str((qs.get('error') or [''])[0])
            flow=GOOGLE_OAUTH_STATES.pop(state,None)
            if err or not flow or not code:
                self.send_response(302); self.send_header('Location','/account?google=cancelled'); self.end_headers(); return
            try:
                gp=_google_profile_from_code(code,_google_redirect_uri(self))
                person=next((x for x in load_people() if str(x.get('googleSub') or '')==gp['sub']),None)
                if person and not person.get('blocked') and participant_approval_status(person) not in ('stopped','cancelled'):
                    person['lastSeen']=datetime.datetime.now().isoformat(); people=load_people()
                    for x in people:
                        if str(x.get('id'))==str(person.get('id')): x['lastSeen']=person['lastSeen']; break
                    save_json(PEOPLE,{'participants':people})
                    token=_participant_session_token(person); PARTICIPANT_SESSIONS[token]={'participantId':str(person.get('id')),'created':time.time(),'last':time.time(),'persistent':True}
                    secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
                    self.send_response(302); self.send_header('Set-Cookie',f'NawaderParticipant={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={PARTICIPANT_SESSION_TTL_SECONDS}{secure}')
                    self.send_header('Location',_safe_next_path(flow.get('next'))); self.end_headers(); return
                pending_token=secrets.token_urlsafe(28); GOOGLE_PENDING_LINKS[pending_token]={**gp,'created':time.time(),'next':_safe_next_path(flow.get('next'))}
                secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
                self.send_response(302); self.send_header('Set-Cookie',f'NawaderGooglePending={pending_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={GOOGLE_FLOW_TTL_SECONDS}{secure}')
                self.send_header('Location','/account?google=link-phone&next='+quote(_safe_next_path(flow.get('next')),safe='')); self.end_headers(); return
            except Exception as e:
                print('Google OAuth error:',repr(e)); self.send_response(302); self.send_header('Location','/account?google=error'); self.end_headers(); return
        if p=='/api/version':
            self.sendj({'version':'5.6.2-R9.5F','channel':'DAR-MUQTANYAT-R9.5F-DATA-ENTRY-DEVICE-SESSION','marketFirstLaunch':False,'liveVideoProvider':'livekit','liveVideoConfigured':livekit_configured()}); return
        if p=='/account-logout':
            token=self.cookie_value('NawaderParticipant'); PARTICIPANT_SESSIONS.pop(token,None)
            q=parse_qs(urlparse(self.path).query); next_path=str((q.get('next') or [''])[0] or '').strip()
            if not (next_path.startswith('/') and not next_path.startswith('//')): next_path=''
            target='/account'+(('?next='+quote(next_path,safe='')) if next_path else '')
            self.send_response(302); self.send_header('Set-Cookie','NawaderParticipant=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'); self.send_header('Location',target); self.end_headers(); return
        if p=='/admin-login':
            if self.is_admin():
                self.send_response(302); self.send_header('Location','/admin'); self.end_headers(); return
            self.login_page(); return
        if p=='/admin-logout':
            token=self.cookie_value('KhazinaAdmin'); ADMIN_SESSIONS.pop(token,None)
            self.send_response(302); self.send_header('Set-Cookie','KhazinaAdmin=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'); self.send_header('Location','/'); self.end_headers(); return
        # V5.6.2-R5: Dar Al Muqtanyat is the single umbrella homepage.
        # Keep Nawader Coins as a dedicated store under /coins.
        if p in ('/','/home','/home/'):
            self.send_file(os.path.join(PUBLIC_DIR,'dar_home.html'),'text/html; charset=utf-8'); return
        if p in ('/dar','/dar/','/dar_home.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'dar_home.html'),'text/html; charset=utf-8'); return
        if p in ('/coins','/coins/','/public_home.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'public_home.html'),'text/html; charset=utf-8'); return
        if p in ('/collectibles','/collectibles/','/collectibles_home.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'collectibles_home.html'),'text/html; charset=utf-8'); return
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
        if p=='/api/settings/public':
            st=load_settings(); self.sendj({'buyerFeePercent':st['buyerFeePercent'],'charityProfitPercent':st['charityProfitPercent'],'auctionEntryFee':st['auctionEntryFee'],'entryFeeEnabled':st['entryFeeEnabled'],'negotiationPercents':st['negotiationPercents'],'negotiationHours':st['negotiationHours'],'visitorSections':effective_visitor_sections(st),'marketFirstLaunch':MARKET_FIRST_LAUNCH,'whatsappVerificationNumber':st.get('whatsappVerificationNumber','966551892409'),'payment':{'method':'bank_transfer','bankName':st.get('paymentBankName',''),'accountName':st.get('paymentAccountName',''),'iban':st.get('paymentIban',''),'instructions':st.get('paymentInstructions',''),'whatsapp':st.get('paymentWhatsapp','')}}); return
        if p=='/api/settings/admin':
            if not self.require_admin(api=True): return
            self.sendj({'settings':load_settings()}); return
        if p=='/api/ocr/status':
            exe,version,diag=resolve_tesseract()
            langs=sorted(_tesseract_languages(exe)) if exe else []
            self.sendj({'ok':bool(exe),'path':exe,'version':version,'hasArabic':'ara' in langs,'hasEnglish':'eng' in langs,'languages':langs[:80],'diagnostics':diag[-5:]}); return
        if p=='/api/owner/items':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=self.require_participant(pid)
            if not person: return
            reconcile_collectible_lifecycle(pid)
            submissions={str(x.get('itemId') or ''):x for x in load_collectible_submissions() if str(x.get('participantId') or '')==pid and x.get('itemId')}
            owned=[]
            for i in load():
                if str(i.get('ownerParticipantId') or '')!=pid or i.get('ownerArchived'): continue
                y={k:i.get(k) for k in (
                    'id','storeType','collectibleCategory','country','denomination','issueEdition','year','type','condition','notes','frontImg','backImg',
                    'inventoryUnitType','inventoryUnitCount','piecesPerUnit','quantity','availableQuantity',
                    'forMarket','marketApproved','marketSalePrice','marketPriceUnit','marketNegotiationEnabled','marketNegotiationPercent',
                    'forAuction','auctionApproved','auctionEnd','auctionOpeningPrice','auctionStartPrice','auctionCurrentPrice',
                    'auctionBidStep','auctionTargetPrice','auctionAdditionalTerms','auctionRound','auctionOutcome','auctionSold',
                    'specialNumberEnabled','specialNumberType','specialNumberTypes','specialNumberReason',
                    'fantasiaEnabled','fantasiaType','fantasiaIssuer','fantasiaNotes',
                    'transitionalIssueEnabled','transitionalIssueType','transitionalPreviousIssue','transitionalNextIssue','transitionalRarity','transitionalReason','transitionalNotes','moderationStatus','moderationReason'
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
            person=self.require_participant(pid)
            if not person: return
            reconcile_collectible_lifecycle(pid)
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
            person=self.require_participant(pid)
            if not person: return
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
        if p=='/api/integrity':
            self.sendj(platform_integrity_report()); return
        if p=='/api/archive/items':
            rows=[dict(i) for i in load() if moderation_status(i) in ('archived','removed') or i.get('ownerArchived')]
            rows.sort(key=lambda x:str(x.get('archivedAt') or x.get('ownerArchivedAt') or x.get('updated') or ''),reverse=True)
            self.sendj({'items':rows,'total':len(rows)}); return
        if p=='/api/operations':
            rows=load_operations_log(); rows.sort(key=lambda x:x.get('created',''),reverse=True); self.sendj({'events':rows[:500]}); return
        if p=='/api/permissions/me':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=self.require_participant(pid)
            if not person: return
            self.sendj({'permissions':participant_permissions(pid)}); return
        if p=='/api/seller/ended':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=self.require_participant(pid)
            if not person: return
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
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=self.require_participant(pid)
            if not person: return
            perm=participant_permissions(pid)
            if not (perm.get('sellerMarket') or perm.get('marketSupervision')): self.sendj({'error':'لا توجد صلاحية لمتابعة السوق'},403); return
            phone=str(person.get('phone') or '').replace(' ',''); items=load(); ids={str(i.get('id')) for i in items if perm.get('marketSupervision') or str(i.get('ownerPhone') or '').replace(' ','')==phone}
            req=[x for x in load_market_requests() if str(x.get('itemId')) in ids]
            safe=[{k:v for k,v in x.items() if k not in ('ownerPhone',)} for x in req]
            self.sendj({'requests':safe}); return
        if p=='/api/seller/dashboard':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0]); person=self.require_participant(pid)
            if not person: return
            ensure_auction_outcomes(); reconcile_direct_market_buy_orders()
            phone=str(person.get('phone') or '').replace(' ',''); inventory=[]
            for item in load():
                same_id=str(item.get('ownerParticipantId') or '')==pid
                same_phone=bool(phone and str(item.get('ownerPhone') or '').replace(' ','')==phone)
                if (same_id or same_phone) and not item.get('ownerArchived'): inventory.append(item)
            owned_ids={str(x.get('id') or '') for x in inventory}
            labels={'new':'طلب جديد','awaiting_payment':'بانتظار السداد','paid':'تم السداد','preparing':'قيد التجهيز','ready_to_ship':'جاهز للشحن','shipped':'تم الشحن','received':'تم الاستلام','completed':'مكتمل','stalled':'متعثر','cancelled':'ملغي','returned':'مرتجع'}
            orders=[]
            for order in load_orders():
                lines=[x for x in (order.get('items') or []) if str(x.get('itemId') or '') in owned_ids]
                if not lines: continue
                subtotal=sum(float(x.get('total') or 0) for x in lines)
                if subtotal<=0: subtotal=float(order.get('subtotal') or 0)
                paid=str(order.get('paymentStatus') or '')=='paid'
                address=order.get('shippingAddress') if paid and isinstance(order.get('shippingAddress'),dict) else {}
                orders.append({'id':order.get('id'),'orderNumber':order.get('orderNumber'),'source':order.get('source'),'storeType':normalize_store_type(order.get('storeType'),next((z for z in inventory if str(z.get('id'))==str((lines[0] or {}).get('itemId') or '')),{})),'status':order.get('status'),'statusLabel':labels.get(order.get('status'),order.get('status')),'paymentStatus':order.get('paymentStatus','unpaid'),'created':order.get('created'),'updated':order.get('updated'),'customerName':order.get('customerName') or 'مشتري','subtotal':subtotal,'sellerFee':round(subtotal*.025,2),'sellerNet':round(subtotal*.975,2),'shippingCompany':order.get('shippingCompany') or '','trackingNumber':order.get('trackingNumber') or '','shippingAddress':address,'items':[{'itemId':x.get('itemId'),'title':x.get('title') or 'مقتنى','quantity':int(x.get('quantity') or 1),'image':((x.get('images') or [''])[0] or '')} for x in lines]})
            orders.sort(key=lambda x:str(x.get('created') or ''),reverse=True)
            paid_orders=[x for x in orders if x.get('paymentStatus')=='paid' and x.get('status') not in ('cancelled','returned')]
            open_orders=[x for x in orders if x.get('status') in OPEN_ORDER_STATUSES]
            requests=[x for x in load_market_requests() if str(x.get('itemId') or '') in owned_ids]
            permissions=participant_permissions(pid)
            seller_country=person.get('country') or 'المملكة العربية السعودية'
            self.sendj({'seller':{'id':pid,'name':person.get('alias') or person.get('displayName') or person.get('name') or 'بائع','country':seller_country,'flag':SELLER_COUNTRY_FLAGS.get(_norm_country(seller_country),'🇸🇦'),'avatarUrl':person.get('avatarUrl') or '','verified':bool(person.get('verified') or person.get('approved'))},'permissions':permissions,'metrics':{'inventory':len(inventory),'marketActive':sum(1 for x in inventory if x.get('forMarket') and x.get('marketApproved')),'auctionActive':sum(1 for x in inventory if x.get('forAuction') and x.get('auctionApproved')),'orders':len(orders),'openOrders':len(open_orders),'paidGross':round(sum(float(x.get('subtotal') or 0) for x in paid_orders),2),'sellerNet':round(sum(float(x.get('sellerNet') or 0) for x in paid_orders),2),'pendingPayments':sum(1 for x in orders if x.get('paymentStatus')!='paid' and x.get('status') not in ('cancelled','returned','completed')),'readyToShip':sum(1 for x in orders if x.get('status')=='ready_to_ship'),'shipped':sum(1 for x in orders if x.get('status')=='shipped'),'completed':sum(1 for x in orders if x.get('status')=='completed'),'offers':sum(1 for x in requests if x.get('action')=='offer' and str(x.get('status') or 'pending') not in ('completed','cancelled','rejected'))},'orders':orders,'inventory':[{'id':x.get('id'),'storeType':item_store_type(x),'collectibleCategory':x.get('collectibleCategory') or '','title':item_title(x),'image':x.get('frontImg') or x.get('backImg') or '','forMarket':bool(x.get('forMarket')),'marketApproved':bool(x.get('marketApproved')),'marketPrice':float(x.get('marketSalePrice') or x.get('marketUnitPrice') or 0),'forAuction':bool(x.get('forAuction')),'auctionApproved':bool(x.get('auctionApproved')),'auctionEnd':x.get('auctionEnd') or '','auctionOutcome':x.get('auctionOutcome') or '','availableQuantity':inventory_snapshot(x).get('current',0)} for x in inventory],'requests':[{k:v for k,v in x.items() if k not in ('ownerPhone','phone')} for x in requests[-100:]]}); return
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
                rows=[]
                for i in load():
                    x=dict(i); x['storeType']=item_store_type(i); rows.append(x)
                self.sendj({'items':rows}); return
        if p=='/api/participants':
            with LOCK:
                people=load_people(); rows=[participant_public(x) for x in people]
                # R9.5A: الحسابات القديمة قد تكون مكررة لنفس رقم الجوال بصيغ 05 / +966.
                # إذا كان طلب واتساب المعلّق محفوظًا على نسخة أخرى من نفس الجوال،
                # نعرضه على كل النسخ حتى يظهر زر «مطابقة واتساب واعتماد كامل» للإدارة.
                pending_by_phone={}
                now_dt=datetime.datetime.now()
                for raw_person in people:
                    phone_key=_norm_phone(raw_person.get('phone'))
                    if not phone_key: continue
                    for req in reversed(list(raw_person.get('whatsappVerificationRequests') or [])):
                        if str(req.get('status') or '')!='pending': continue
                        try:
                            if datetime.datetime.fromisoformat(str(req.get('expires') or '')) <= now_dt:
                                continue
                        except Exception:
                            pass
                        prev=pending_by_phone.get(phone_key)
                        if not prev or str(req.get('created') or '') > str(prev.get('created') or ''):
                            pending_by_phone[phone_key]=req
                        break
                for row in rows:
                    phone_key=_norm_phone(row.get('phone'))
                    req=pending_by_phone.get(phone_key)
                    if req and not row.get('whatsappPending'):
                        row['whatsappPending']=True
                        row['whatsappPendingCode']=str(req.get('code') or '')
                        row['whatsappPendingRequestId']=str(req.get('id') or '')
                        row['whatsappPendingCreated']=str(req.get('created') or '')
                        row['whatsappPendingExpires']=str(req.get('expires') or '')
                        row['whatsappPendingShared']=True
                active=[x for x in rows if x['approvalStatus']!='cancelled']; archived=[x for x in rows if x['approvalStatus']=='cancelled']
                active.sort(key=lambda x:(APPROVAL_STATUSES.index(x['approvalStatus']),x.get('created',''))); archived.sort(key=lambda x:x.get('archivedAt',''),reverse=True); counts={s:sum(1 for x in rows if x['approvalStatus']==s) for s in APPROVAL_STATUSES}
                self.sendj({'participants':active,'archive':archived,'total':len(active),'pending':counts['new'],'archived':len(archived),'counts':counts}); return
        if p=='/api/participants/summary':
            with LOCK:
                people=load_people(); counts={s:sum(1 for x in people if participant_approval_status(x)==s) for s in APPROVAL_STATUSES}; active=len(people)-counts['cancelled']
                self.sendj({'total':active,'pending':counts['new'],'approved':counts['final'],'archived':counts['cancelled'],'counts':counts}); return
        if p=='/api/participant/me':
            person=self.require_participant('')
            if not person: return
            self.sendj({'ok':True,'participant':participant_public(person)}); return
        if p=='/api/image-vault/admin':
            q=parse_qs(urlparse(self.path).query); status=str((q.get('status') or ['all'])[0] or 'all').strip().lower()
            try: limit=max(1,min(100,int((q.get('limit') or ['60'])[0]))); offset=max(0,int((q.get('offset') or ['0'])[0]))
            except Exception: limit,offset=60,0
            rows,changed=image_vault_cleanup(load_image_vault())
            if changed: save_json(IMAGE_VAULT,{'images':rows})
            ordered=sorted(rows,key=lambda x:str(x.get('createdAt') or ''),reverse=True)
            counts={'total':len(ordered),'available':sum(1 for x in ordered if x.get('status')=='available'),'reserved':sum(1 for x in ordered if x.get('status')=='reserved'),'used':sum(1 for x in ordered if x.get('status')=='used')}
            filtered=ordered if status not in ('available','reserved','used') else [x for x in ordered if x.get('status')==status]
            self.sendj({'ok':True,'counts':counts,'totalFiltered':len(filtered),'offset':offset,'limit':limit,'images':filtered[offset:offset+limit]}); return
        if p=='/api/image-vault/available':
            person=self.require_participant('')
            if not person: return
            pid=str(person.get('id') or '')
            if not participant_permissions(pid).get('dataEntry'):
                self.sendj({'error':'صلاحية مسؤول إدخال البيانات غير مفعلة لهذا الحساب'},403); return
            q=parse_qs(urlparse(self.path).query)
            try: limit=max(1,min(100,int((q.get('limit') or ['100'])[0]))); offset=max(0,int((q.get('offset') or ['0'])[0]))
            except Exception: limit,offset=100,0
            rows,changed=image_vault_cleanup(load_image_vault())
            if changed: save_json(IMAGE_VAULT,{'images':rows})
            visible=[x for x in rows if x.get('status')=='available' or (x.get('status')=='reserved' and str(x.get('reservedByParticipantId') or '')==pid)]
            visible.sort(key=lambda x:str(x.get('createdAt') or ''),reverse=True)
            self.sendj({'ok':True,'total':len(visible),'offset':offset,'limit':limit,'images':visible[offset:offset+limit]}); return
        if p=='/api/data-entry/submissions':
            person=self.require_participant('')
            if not person: return
            pid=str(person.get('id') or '')
            if not participant_permissions(pid).get('dataEntry'):
                self.sendj({'error':'صلاحية مسؤول إدخال البيانات غير مفعلة لهذا الحساب'},403); return
            rows=[x for x in load_collectible_submissions() if x.get('submissionSource')=='data_entry' and str(x.get('dataEntryParticipantId') or '')==pid]
            rows.sort(key=lambda x:str(x.get('updated') or x.get('created') or ''),reverse=True)
            safe=[]
            for x in rows:
                y=dict(x)
                safe.append(y)
            self.sendj({'ok':True,'operator':{'id':pid,'name':person.get('alias') or person.get('name') or 'مسؤول إدخال البيانات'},'submissions':safe,
                        'counts':{'draft':sum(1 for x in rows if x.get('status')=='draft'),'pending':sum(1 for x in rows if x.get('status')=='pending'),'needsChanges':sum(1 for x in rows if x.get('status')=='needs_changes'),'approved':sum(1 for x in rows if x.get('status')=='approved'),'rejected':sum(1 for x in rows if x.get('status')=='rejected')}}); return
        if p=='/api/participant/status':
            q=urlparse(self.path).query
            pid=(parse_qs(q).get('id') or [''])[0]
            person=self.require_participant(pid)
            if not person: return
            self.sendj({'found':True,'participant':participant_public(person)}); return
        if p=='/api/bids':
            with LOCK:
                people={x.get('id'):x for x in load_people()}; bids=load_bids()
                for b in bids:
                    person=people.get(b.get('participantId'),{}); b['bidderName']=person.get('name','مشارك'); b['approvalStatus']=participant_approval_status(person); b['approvalLabel']=APPROVAL_LABELS[b['approvalStatus']]
                self.sendj({'bids':bids}); return
        if p=='/api/public/special-numbers':
            if not effective_visitor_sections()['specialNumbers']:
                self.sendj({'items':[],'hidden':True,'launchMode':True}); return
            rows=[public_special_item(i) for i in load() if i.get('specialNumberEnabled') and item_is_public(i) and item_store_type(i)=='coins']
            self.sendj({'items':rows}); return
        if p=='/api/public/fantasia':
            if not effective_visitor_sections()['fantasia']:
                self.sendj({'items':[],'hidden':True,'launchMode':True}); return
            rows=[public_special_item(i) for i in load() if i.get('fantasiaEnabled') and item_is_public(i) and item_store_type(i)=='collectibles']
            for row in rows:
                src=next((x for x in load() if str(x.get('id'))==str(row.get('id'))),{})
                row['storeType']='collectibles'; row['fantasiaType']=src.get('fantasiaType') or 'other'; row['fantasiaIssuer']=src.get('fantasiaIssuer') or ''; row['fantasiaNotes']=src.get('fantasiaNotes') or ''
            self.sendj({'items':rows}); return
        if p=='/api/public/transitional-issues':
            if not effective_visitor_sections()['transitionalIssues']:
                self.sendj({'items':[],'hidden':True,'launchMode':True}); return
            rows=[]
            for i in load():
                if not i.get('transitionalIssueEnabled') or not item_is_public(i) or item_store_type(i)!='coins': continue
                market_public=bool(i.get('forMarket') and i.get('marketApproved'))
                auction_public=bool(i.get('forAuction') and i.get('auctionApproved'))
                special_public=bool(i.get('specialNumberEnabled'))
                row=public_market_item(i) if market_public else public_item(i)
                for k in ('transitionalIssueType','transitionalPreviousIssue','transitionalNextIssue','transitionalRarity','transitionalEstimatedPopulation','transitionalReason','transitionalNotes'):
                    row[k]=i.get(k)
                row['marketPublic']=market_public; row['auctionPublic']=auction_public; row['specialPublic']=special_public
                rows.append(row)
            rows.sort(key=lambda x:str(x.get('updated') or ''), reverse=True)
            self.sendj({'items':rows}); return
        if p=='/api/live-media/status':
            self.sendj({'provider':'livekit','configured':livekit_configured(),'urlConfigured':bool(LIVEKIT_URL)}); return
        if p=='/api/live-media/token':
            q=parse_qs(urlparse(self.path).query); sid=str((q.get('sessionId') or [''])[0]); role=str((q.get('role') or ['viewer'])[0])
            row=next((x for x in load_live_auctions() if str(x.get('id'))==sid),None)
            if not row or row.get('status') not in ('scheduled','live'):
                self.sendj({'error':'جلسة البث غير موجودة أو منتهية'},404); return
            if not livekit_configured():
                self.sendj({'error':'خدمة الفيديو المباشر لم تُربط بعد. أضف LIVEKIT_URL وLIVEKIT_API_KEY وLIVEKIT_API_SECRET في Render.'},503); return
            publish=(role=='publisher')
            if publish:
                if self.is_admin(): ident='admin-'+secrets.token_hex(5)
                else:
                    person=self.participant_person()
                    if not live_broadcast_allowed(person) or not live_session_owned_by(row,person):
                        self.sendj({'error':'لا تملك صلاحية بث الكاميرا لهذه الجلسة'},403); return
                    ident='seller-'+hashlib.sha256(str(person.get('id')).encode()).hexdigest()[:16]+'-'+secrets.token_hex(3)
            else:
                ident='viewer-'+secrets.token_hex(8)
            try: token=livekit_token(sid,ident,publish=publish,ttl=3600 if publish else 1800)
            except Exception as e: self.sendj({'error':str(e)},503); return
            self.sendj({'provider':'livekit','url':LIVEKIT_URL,'room':livekit_room_name(sid),'token':token,'role':'publisher' if publish else 'viewer'}); return
        if p=='/api/live-auctions/mine':
            sessions=load_live_auctions(); self._settle_expired_live_sessions(sessions)
            person=self.require_participant('')
            if not person: return
            allowed=live_broadcast_allowed(person)
            rows=[x for x in sessions if live_session_owned_by(x,person)] if allowed else []
            self.sendj({'allowed':allowed,'permissions':participant_permissions(person.get('id')),'sessions':[with_live_timer(x) for x in rows]}); return
        if p=='/api/live-auctions/admin':
            # V5.3.1: this endpoint is administration-only. Besides closing an
            # unintended data exposure, this lets the studio reliably distinguish
            # an admin session from a normal participant session.
            if not self.is_admin():
                self.sendj({'error':'يلزم تسجيل دخول الإدارة'},401); return
            sessions=load_live_auctions(); self._settle_expired_live_sessions(sessions); items={str(i.get('id')):i for i in load()}
            out=[]
            for row in sessions:
                x=with_live_timer(row); x['itemsDetailed']=[{'itemId':iid,'title':item_title(items.get(str(iid),{})),'frontImg':items.get(str(iid),{}).get('frontImg'),'backImg':items.get(str(iid),{}).get('backImg')} for iid in (row.get('itemIds') or [])]
                out.append(x)
            self.sendj({'sessions':out}); return
        if p=='/api/public/live-auctions':
            sessions=[]; items={str(i.get('id')):i for i in load()}
            now=datetime.datetime.now(); live_rows=load_live_auctions(); self._settle_expired_live_sessions(live_rows)
            for row in live_rows:
                if row.get('status') not in ('scheduled','live'): continue
                x={k:row.get(k) for k in ('id','title','description','startAt','startedAt','status','mode','marketEnabled','currentItemId','currentLot','currentPrice','latestBidderName','itemIds','bidStep','lotEndsAt','broadcasterName','lastResult')}
                x['remainingSec']=live_timer_remaining(row); x['serverEpochMs']=int(time.time()*1000)
                x['items']=[{'id':iid,'title':item_title(items.get(str(iid),{})),'frontImg':items.get(str(iid),{}).get('frontImg'),'backImg':items.get(str(iid),{}).get('backImg')} for iid in (row.get('itemIds') or [])]
                x['chat']=[{'id':m.get('id'),'name':m.get('name') or 'زائر','text':m.get('text') or '','role':m.get('role') or 'guest','created':m.get('created')} for m in (row.get('chat') or [])[-120:]]
                x['bids']=[{'id':b.get('id'),'bidderName':b.get('bidderName') or 'مشارك','amount':float(b.get('amount') or 0),'created':b.get('created')} for b in (row.get('bids') or [])[-80:]]
                sessions.append(x)
            sessions.sort(key=lambda x:str(x.get('startAt') or ''))
            self.sendj({'sessions':sessions,'count':len(sessions)}); return
        if p=='/api/public/auctions':
            if not effective_visitor_sections()['auction']:
                self.sendj({'items':[],'hidden':True,'launchMode':True}); return
            with LOCK:
                try: ensure_auction_outcomes()
                except Exception as e: print('تنبيه تسوية المزادات العامة:',e)
                items=[]; skipped=0
                try:
                    source_items=load()
                except Exception as e:
                    print('خطأ تحميل مصدر المزادات العامة:',e)
                    self.sendj({'items':[],'error':'تعذر قراءة مصدر المزادات مؤقتًا','retryable':True},503); return
                store=requested_store(self.path)
                for i in source_items:
                    if not (i.get('forAuction') and i.get('auctionApproved') and item_is_public(i)): continue
                    if store and item_store_type(i)!=store: continue
                    try:
                        public=public_item(i)
                        # المزادات المنتهية تُفصل عن صفحة المزادات النشطة العامة.
                        if public.get('auctionEnded'): continue
                        items.append(public)
                    except Exception as e:
                        skipped+=1; print('تنبيه مقتنى مزاد عام غير صالح:',i.get('id'),e)
                items.sort(key=lambda x:str(x.get('auctionEnd') or ''))
                self.sendj({'items':items,'store':store,'skipped':skipped,'ok':True,'serverEpochMs':int(time.time()*1000),'generatedAt':datetime.datetime.now().isoformat()}); return
        if p=='/api/visitor/auction-activity':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=self.require_participant(pid)
            if not person: return
            now=auction_local_now(); bids=[b for b in load_bids() if str(b.get('participantId') or '')==pid]
            items_by_id={str(i.get('id')):i for i in load()}
            grouped={}
            for b in bids:
                iid=str(b.get('itemId') or ''); item=items_by_id.get(iid)
                if not item or not (item.get('forAuction') and item.get('auctionApproved')): continue
                rnd=int(item.get('auctionRound') or 1)
                if int(b.get('auctionRound') or 1)!=rnd: continue
                endraw=str(item.get('auctionEnd') or '').strip()
                try: ended=bool(endraw and datetime.datetime.fromisoformat(endraw)<=now)
                except Exception: ended=False
                if ended: continue
                row=grouped.setdefault(iid,{'itemId':iid,'title':item_title(item),'auctionEnd':endraw,'myHighestBid':0.0,'currentBid':0.0,'url':store_auction_path(item)})
                row['myHighestBid']=max(float(row['myHighestBid'] or 0),float(b.get('amount') or 0))
            all_bids=load_bids()
            for iid,row in grouped.items():
                item=items_by_id.get(iid) or {}; rnd=int(item.get('auctionRound') or 1)
                rb=[x for x in all_bids if str(x.get('itemId') or '')==iid and int(x.get('auctionRound') or 1)==rnd]
                row['currentBid']=max([float(x.get('amount') or 0) for x in rb] or [float(item.get('auctionStartPrice') or 0)])
            out=list(grouped.values()); out.sort(key=lambda x:str(x.get('auctionEnd') or ''))
            self.sendj({'items':out,'count':len(out)}); return
        if p=='/api/visitor/orders':
            qs=parse_qs(urlparse(self.path).query); pid=str((qs.get('participantId') or [''])[0])
            person=self.require_participant(pid)
            if not person: return
            ensure_auction_outcomes(); reconcile_direct_market_buy_orders(pid); phone=str(person.get('phone') or '').replace(' ',''); labels={'new':'طلب جديد','awaiting_payment':'بانتظار السداد','paid':'تم السداد','preparing':'قيد التجهيز','ready_to_ship':'جاهز للشحن','shipped':'تم الشحن','received':'تم الاستلام','completed':'مكتمل','stalled':'متعثر','cancelled':'ملغي','returned':'مرتجع'}
            rows=[]
            for o in load_orders():
                if str(o.get('participantId') or '')!=pid and str(o.get('customerPhone') or '').replace(' ','')!=phone: continue
                first=(o.get('items') or [{}])[0]
                rows.append({'id':o.get('id'),'orderNumber':o.get('orderNumber'),'source':o.get('source'),'itemTitle':first.get('title','مقتنى'),'quantity':sum(int(x.get('quantity') or 1) for x in o.get('items') or []),'buyerTotal':o.get('total',0),'subtotal':o.get('subtotal',0),'buyerFee':o.get('buyerFee',0),'shippingFee':o.get('shippingFee',0),'shippingFeeConfirmed':bool(o.get('shippingFeeConfirmed')),'paymentStatus':o.get('paymentStatus','unpaid'),'paidAt':o.get('paidAt'),'status':o.get('status'),'statusLabel':labels.get(o.get('status'),o.get('status')),'created':o.get('created'),'shippingCompany':o.get('shippingCompany'),'trackingNumber':o.get('trackingNumber'),'shippingAddress':o.get('shippingAddress') or participant_shipping_address(person),'archived':o.get('archived',False),'cancellationRequestedAt':o.get('cancellationRequestedAt'),'refundRequestedAt':o.get('refundRequestedAt'),'refundStatus':o.get('refundStatus'),'paymentProofStatus':o.get('paymentProofStatus',''),'paymentProofSubmittedAt':o.get('paymentProofSubmittedAt'),'paymentProofRejectedAt':o.get('paymentProofRejectedAt'),'paymentProofRejectNote':o.get('paymentProofRejectNote',''),'paymentReference':o.get('paymentReference',''),'paymentProofBatchId':o.get('paymentProofBatchId','')})
            rows.sort(key=lambda x:x.get('created') or '',reverse=True); self.sendj({'requests':rows}); return
        if p=='/api/visitor/invoice':
            qs=parse_qs(urlparse(self.path).query)
            pid=str((qs.get('participantId') or [''])[0])
            oid=str((qs.get('orderId') or [''])[0])
            person=self.require_participant(pid)
            if not person: return
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
            first_item_id=str(((order.get('items') or [{}])[0] or {}).get('itemId') or '')
            first_item=next((i for i in load() if str(i.get('id') or '')==first_item_id),{}) if first_item_id else {}
            order_store=normalize_store_type(order.get('storeType'),first_item)
            store_label=STORE_LABELS.get(order_store,'نوادر العملات')
            self.sendj({'invoice':{
                'invoiceNumber':'INV-'+str(order.get('orderNumber') or order.get('id') or '').replace('NW-',''),
                'orderNumber':order.get('orderNumber'),'orderId':order.get('id'),'source':order.get('source'),
                'storeType':order_store,'storeLabel':store_label,
                'created':order.get('created'),'paidAt':order.get('paidAt'),'customerName':order.get('customerName') or person.get('name') or '',
                'customerPhone':order.get('customerPhone') or person.get('phone') or '',
                'sellerName':store_label,'platformName':'دار المقتنيات','items':items,
                'subtotal':subtotal,'buyerFee':buyer_fee,'shippingFee':shipping,'total':total,'paid':paid,
                'balance':max(0,total-paid),'status':order.get('status'),'statusLabel':labels.get(order.get('status'),order.get('status')),
                'shippingCompany':order.get('shippingCompany') or '','trackingNumber':order.get('trackingNumber') or '',
                'verificationCode':verify
            }}); return
        if p=='/api/public/market':
            with LOCK:
                store=requested_store(self.path)
                items=[public_market_item(i) for i in load() if i.get('forMarket') and i.get('marketApproved') and item_is_public(i) and (not store or item_store_type(i)==store)]
                self.sendj({'items':items,'store':store}); return
        if p=='/api/market/requests':
            with LOCK:
                all_req=load_market_requests()
                req=[x for x in all_req if not bool(x.get('archived'))]
                req.sort(key=lambda x:x.get('created',''),reverse=True)
                archived=sum(1 for x in all_req if bool(x.get('archived')))
                self.sendj({'requests':req,'archivedCount':archived}); return
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
            # أثناء إطلاق السوق فقط، أي QR قديم للمزاد يعاد إلى الواجهة الرئيسية بدل كشف القسم المؤجل.
            if not effective_visitor_sections()['auction']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
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
        if p in ('/data-entry','/data-entry/','/data_entry.html'):
            # R9.5F: the participant login cookie is per browser/device.
            # If this browser has no account session, send it to account login and
            # return automatically after WhatsApp verification.
            if not self.participant_person():
                self.send_response(302); self.send_header('Location','/account?next=%2Fdata-entry'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'data_entry.html'),'text/html; charset=utf-8'); return
        if p in ('/special-numbers','/special-numbers/','/special_numbers.html'):
            if not effective_visitor_sections()['specialNumbers']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'special_numbers.html'),'text/html; charset=utf-8'); return
        if p in ('/live-auction','/live-auction/','/live_auction.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'live_auction.html'),'text/html; charset=utf-8'); return
        if p in ('/live-studio','/live-studio/','/live_studio.html'):
            self.send_file(os.path.join(PUBLIC_DIR,'live_studio.html'),'text/html; charset=utf-8'); return
        if p in ('/fantasia','/fantasia/','/fantasia.html'):
            if not effective_visitor_sections()['fantasia']:
                self.sendj({'error':'قسم فانتازيا غير متاح حاليًا'},404); return
            self.send_file(os.path.join(PUBLIC_DIR,'fantasia.html'),'text/html; charset=utf-8'); return
        if p in ('/transitional-issues','/transitional-issues/','/transitional_issues.html'):
            if not effective_visitor_sections()['transitionalIssues']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'transitional_issues.html'),'text/html; charset=utf-8'); return
        if p in ('/auction','/auction/','/public_auction.html','/public-auction'):
            if not effective_visitor_sections()['auction']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_auction.html'),'text/html; charset=utf-8'); return
        if p in ('/market','/market/','/public_market.html','/public-market'):
            if not effective_visitor_sections()['market']:
                self.send_response(302); self.send_header('Location','/'); self.end_headers(); return
            self.send_file(os.path.join(PUBLIC_DIR,'public_market.html'),'text/html; charset=utf-8'); return
        # لا نسمح بعرض مجلد المشروع أو الملفات الإدارية مباشرة.
        if p=='/app.js':
            if not self.require_admin(): return
            self.send_file(os.path.join(ADMIN_DIR,'app.js'),'application/javascript; charset=utf-8'); return
        if p.startswith('/uploads/'):
            rel=os.path.basename(p); full=os.path.join(UPLOAD_DIR,rel)
            # R9.5E: older deployments may still have legacy images under
            # ROOT/uploads while current data lives on the persistent disk.
            # Recover a missing persistent copy automatically without touching JSON.
            if (not os.path.isfile(full)) or (os.path.getsize(full)==0 if os.path.isfile(full) else False):
                legacy=os.path.join(ROOT,'uploads',rel)
                if os.path.isfile(legacy) and os.path.getsize(legacy)>0:
                    try:
                        os.makedirs(UPLOAD_DIR,exist_ok=True)
                        shutil.copy2(legacy,full)
                    except OSError:
                        full=legacy
            allowed=self.is_admin() or is_public_upload_url(p)
            if not allowed:
                person=self.participant_person()
                if person and participant_permissions(person.get('id')).get('dataEntry') and image_vault_record_by_url(p): allowed=True
            if allowed:
                self.send_file(full); return
            self.send_error(403,'Private image'); return
        if p in PUBLIC_STATIC:
            self.send_file(os.path.join(PUBLIC_DIR,p.lstrip('/'))); return
        if p.startswith('/assets/') or p.startswith('/icons/'):
            rel=os.path.normpath(p.lstrip('/'))
            if rel.startswith('..'): self.send_error(404); return
            self.send_file(os.path.join(SHARED_DIR,rel)); return
        self.send_error(404,'Not found'); return
    def _close_live_item(self,row,sold=False):
        closed_item=str(row.get('currentItemId') or ''); lot=row.get('currentLot') if isinstance(row.get('currentLot'),dict) else None; winner_id=str(row.get('latestBidderId') or '')
        hist={'itemId':closed_item or str((lot or {}).get('id') or ''),'lot':dict(lot) if lot else None,'price':float(row.get('currentPrice') or 0),'bidderName':row.get('latestBidderName') or '','participantId':winner_id,'sold':bool(sold),'closedAt':datetime.datetime.now().isoformat()}
        if sold and winner_id and (closed_item or lot):
            if closed_item: item=next((i for i in load() if str(i.get('id'))==closed_item),{})
            else:
                item=make_free_live_item(row,lot); closed_item=str(item.get('id') or ''); hist['itemId']=closed_item; hist['createdInventoryItem']=True
            person=next((x for x in load_people() if str(x.get('id'))==winner_id),{})
            due={'id':'live-due-'+secrets.token_hex(5),'itemId':closed_item,'itemTitle':item_title(item),'participantId':winner_id,'amount':float(row.get('currentPrice') or 0),'auctionRound':1}
            order=order_from_auction(due,item,person); order['source']='live_auction'; order['sourceId']=row.get('id'); order['history'][0]['note']='تم إنشاء الطلب تلقائيًا من فوز المزاد المباشر بالكاميرا' if lot else 'تم إنشاء الطلب تلقائيًا من فوز المزاد المباشر'
            orders=load_orders(); orders.append(order); save_json(ORDERS,{'orders':orders}); hist['orderId']=order['id']
            # ثبّت نتيجة المزاد على سجل المقتنى حتى يظهر البيع في الإدارة والسلة ولا تضيع النتيجة بعد إعادة التشغيل.
            items=load(); stored=next((i for i in items if str(i.get('id'))==closed_item),None)
            if stored:
                stored['auctionOutcome']='sold'; stored['auctionSold']=True; stored['auctionWinnerParticipantId']=winner_id
                stored['auctionWinningAmount']=float(row.get('currentPrice') or 0); stored['auctionOrderId']=order['id']
                stored['auctionOutcomeAt']=datetime.datetime.now().isoformat(); stored['updated']=int(time.time()*1000)
                save(items)
            add_notification('participant',winner_id,'orders','🏆 فوز في المزاد المباشر',f"تم إنشاء طلب بقيمة {float(row.get('currentPrice') or 0):g} ر.س للمقتنى {item_title(item)}.",closed_item,'/account')
            add_notification('admin','','auction','🏆 تم إرساء مزاد مباشر',f"فاز {person.get('name') or 'مشارك'} بالمقتنى {item_title(item)} بقيمة {float(row.get('currentPrice') or 0):g} ر.س وتم إنشاء طلب المبيعات تلقائيًا.",closed_item,'/admin')
        row.setdefault('history',[]).append(hist); row['lastResult']=dict(hist); row['currentItemId']=''; row['currentLot']=None; row['currentPrice']=0; row['lotEndsAt']=''; row['latestBidderName']=''; row['latestBidderId']=''
        return hist

    def _settle_expired_live_sessions(self,sessions):
        """Settle expired live lots exactly once. A winner creates the sales order; no bids closes without sale."""
        changed=False
        for row in sessions:
            if row.get('status')!='live' or not live_lot_expired(row):
                continue
            sold=bool(row.get('latestBidderId'))
            self._close_live_item(row,sold=sold)
            row['updated']=datetime.datetime.now().isoformat(); changed=True
            append_operation('إغلاق تلقائي لقطعة المزاد المباشر',{'sessionId':row.get('id'),'sold':sold,'orderId':(row.get('lastResult') or {}).get('orderId','')},actor='النظام')
        if changed:
            save_json(LIVE_AUCTIONS,{'sessions':sessions})
        return changed

    def do_POST(self):
        p=urlparse(self.path).path
        if p=='/admin-login':
            try:
                n=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(n).decode('utf-8','replace'); form=parse_qs(raw)
                username=(form.get('username') or [''])[0]; password=(form.get('password') or [''])[0]
            except Exception:
                self.login_page('تعذر قراءة بيانات الدخول.'); return
            client_key=(self.headers.get('X-Forwarded-For') or '').split(',')[0].strip() or str(self.client_address[0] if self.client_address else 'unknown')
            now=time.time(); tries=[t for t in ADMIN_LOGIN_ATTEMPTS.get(client_key,[]) if now-t<ADMIN_LOGIN_WINDOW_SECONDS]
            if len(tries)>=ADMIN_LOGIN_MAX_ATTEMPTS:
                self.login_page('تم إيقاف محاولات دخول الإدارة مؤقتًا بسبب تكرار المحاولات. حاول بعد 15 دقيقة.'); return
            if not verify_admin_password(username,password):
                tries.append(now); ADMIN_LOGIN_ATTEMPTS[client_key]=tries
                time.sleep(0.5); self.login_page('اسم المستخدم أو كلمة المرور غير صحيحة.'); return
            ADMIN_LOGIN_ATTEMPTS.pop(client_key,None)
            token=secrets.token_urlsafe(32); ADMIN_SESSIONS[token]={'created':time.time(),'last':time.time()}
            secure='; Secure' if (self.headers.get('X-Forwarded-Proto') or '').lower()=='https' else ''
            self.send_response(302); self.send_header('Set-Cookie',f'KhazinaAdmin={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL_SECONDS}{secure}'); self.send_header('Location','/admin'); self.end_headers(); return
        if not self.same_origin_ok():
            self.sendj({'error':'تم رفض الطلب لأسباب أمنية.'},403); return
        if p not in PUBLIC_POST_API:
            if not self.require_admin(api=True): return
        if p=='/api/seller/order/update':
            person=self.require_participant('')
            if not person: return
            d=self.readj(); oid=str(d.get('id') or ''); target=str(d.get('status') or '')
            if target not in ('preparing','ready_to_ship','shipped'):
                self.sendj({'error':'هذه الحالة لا يمكن للبائع اعتمادها'},400); return
            permissions=participant_permissions(person.get('id'))
            if not permissions.get('ordersManage'):
                self.sendj({'error':'صلاحية إدارة الطلبات غير مفعلة لهذا الحساب'},403); return
            phone=str(person.get('phone') or '').replace(' ',''); owned_ids=set()
            for item in load():
                if str(item.get('ownerParticipantId') or '')==str(person.get('id')) or (phone and str(item.get('ownerPhone') or '').replace(' ','')==phone): owned_ids.add(str(item.get('id') or ''))
            rows=load_orders(); row=next((x for x in rows if str(x.get('id') or '')==oid and any(str(line.get('itemId') or '') in owned_ids for line in (x.get('items') or []))),None)
            if not row: self.sendj({'error':'الطلب غير موجود ضمن مبيعاتك'},404); return
            current=str(row.get('status') or ''); allowed={'paid':'preparing','preparing':'ready_to_ship','ready_to_ship':'shipped'}
            if allowed.get(current)!=target:
                self.sendj({'error':'يجب تحديث الطلب حسب تسلسل التجهيز والشحن المعتمد'},409); return
            if str(row.get('paymentStatus') or '')!='paid': self.sendj({'error':'لا يمكن تجهيز الطلب قبل تأكيد السداد من الإدارة'},409); return
            if 'shippingCompany' in d: row['shippingCompany']=str(d.get('shippingCompany') or '').strip()[:120]
            if 'trackingNumber' in d: row['trackingNumber']=str(d.get('trackingNumber') or '').strip()[:120]
            address=row.get('shippingAddress') if isinstance(row.get('shippingAddress'),dict) else {}
            if target in ('ready_to_ship','shipped') and (not str(address.get('country') or '').strip() or not str(address.get('city') or '').strip() or not str(address.get('addressLine') or '').strip()):
                self.sendj({'error':'عنوان المشتري غير مكتمل؛ اطلب منه تحديثه قبل الشحن'},409); return
            if target in ('ready_to_ship','shipped') and not str(row.get('shippingCompany') or '').strip(): self.sendj({'error':'حدد شركة الشحن أولًا'},409); return
            if target=='shipped' and not str(row.get('trackingNumber') or '').strip(): self.sendj({'error':'أدخل رقم التتبع أو مرجع الشحنة'},409); return
            update_order_status(row,target,'تحديث بواسطة البائع'); save_json(ORDERS,{'orders':rows})
            add_notification('participant',row.get('participantId'),'order','تحديث حالة الطلب',f"الطلب {row.get('orderNumber')} أصبح: {({'preparing':'قيد التجهيز','ready_to_ship':'جاهز للشحن','shipped':'تم الشحن'}).get(target,target)}",'', '/account')
            append_operation('تحديث طلب بواسطة البائع',{'orderId':oid,'participantId':person.get('id'),'status':target},actor='البائع')
            self.sendj({'ok':True,'status':target}); return
        if p=='/api/live-auctions/chat':
            d=self.readj(); sid=str(d.get('id') or ''); text=' '.join(str(d.get('text') or '').strip().split())[:500]
            if not text: self.sendj({'error':'اكتب التعليق أولًا'},400); return
            sessions=load_live_auctions(); row=next((x for x in sessions if str(x.get('id'))==sid),None)
            if not row or row.get('status') not in ('scheduled','live'): self.sendj({'error':'جلسة البث غير متاحة'},404); return
            if self.is_admin(): name='الإدارة'; role='admin'; participant_id=''
            else:
                person=self.participant_person()
                if person:
                    name=str(person.get('alias') or person.get('displayName') or person.get('name') or 'مشارك')[:60]; role='participant'; participant_id=str(person.get('id') or '')
                else:
                    name=' '.join(str(d.get('guestName') or 'زائر').strip().split())[:40] or 'زائر'; role='guest'; participant_id=''
            msg={'id':'lc-'+secrets.token_hex(6),'name':name,'text':text,'role':role,'participantId':participant_id,'created':datetime.datetime.now().isoformat()}
            row.setdefault('chat',[]).append(msg); row['chat']=row['chat'][-300:]; row['updated']=datetime.datetime.now().isoformat()
            save_json(LIVE_AUCTIONS,{'sessions':sessions}); self.sendj({'ok':True,'message':{'id':msg['id'],'name':name,'text':text,'role':role,'created':msg['created']}}); return
        if p=='/api/live-auctions/bid':
            person=self.require_participant('')
            if not person: return
            if not participant_can_transact(person): self.sendj({'error':'يتطلب الاشتراك في المزاد توثيقًا كاملًا للحساب'},403); return
            d=self.readj(); sid=str(d.get('id') or ''); sessions=load_live_auctions(); self._settle_expired_live_sessions(sessions); row=next((x for x in sessions if str(x.get('id'))==sid),None)
            if not row or row.get('status')!='live' or not (row.get('currentItemId') or row.get('currentLot')): self.sendj({'error':'لا يوجد مقتنى مفتوح للمزايدة الآن'},409); return
            if row.get('lotEndsAt'):
                try:
                    if datetime.datetime.fromisoformat(str(row.get('lotEndsAt')).replace('Z','+00:00')).timestamp() <= time.time(): self.sendj({'error':'انتهى وقت المزايدة على هذه القطعة'},409); return
                except Exception: pass
            try: amount=float(d.get('amount') or 0)
            except Exception: amount=0
            current=float(row.get('currentPrice') or 0); step=max(1,float(row.get('bidStep') or 1))
            minimum=current+step if current>0 else step
            if amount<minimum: self.sendj({'error':f'الحد الأدنى للمزايدة {minimum:g} ر.س'},409); return
            bid={'id':'lb-'+secrets.token_hex(5),'itemId':str(row.get('currentItemId') or (row.get('currentLot') or {}).get('id') or ''),'participantId':str(person.get('id')),'bidderName':str(person.get('name') or 'مشارك'),'amount':amount,'created':datetime.datetime.now().isoformat()}
            row.setdefault('bids',[]).append(bid); row['bids']=row['bids'][-500:]; row['currentPrice']=amount; row['latestBidderName']=bid['bidderName']; row['latestBidderId']=bid['participantId']; row['updated']=datetime.datetime.now().isoformat(); save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('مزايدة بث مباشر',{'sessionId':sid,'itemId':bid['itemId'],'participantId':bid['participantId'],'amount':amount},actor='العميل'); self.sendj({'ok':True,'currentPrice':amount,'latestBidderName':bid['bidderName']}); return
        if p=='/api/live-auctions/seller-save':
            person=self.require_participant('')
            if not person: return
            if not live_broadcast_allowed(person): self.sendj({'error':'صلاحية البث المباشر غير مفعلة لهذا الحساب'},403); return
            d=self.readj(); sessions=load_live_auctions(); sid=str(d.get('id') or '') or 'live-'+secrets.token_hex(5)
            row=next((x for x in sessions if str(x.get('id'))==sid),None)
            if row is not None and not live_session_owned_by(row,person): self.sendj({'error':'لا تملك هذه الجلسة'},403); return
            if row is None:
                row={'id':sid,'created':datetime.datetime.now().isoformat(),'status':'scheduled','currentItemId':'','currentLot':None,'currentPrice':0,'latestBidderName':'','history':[],'broadcasterType':'participant','broadcasterParticipantId':str(person.get('id')),'broadcasterName':str(person.get('alias') or person.get('displayName') or person.get('name') or 'بائع موثق')[:120]}; sessions.append(row)
            owned={str(i.get('id')) for i in load() if not i.get('archived') and item_store_type(i)=='coins' and str(i.get('ownerParticipantId') or '')==str(person.get('id'))}
            ids=[]
            for iid in (d.get('itemIds') or []):
                iid=str(iid)
                if iid in owned and iid not in ids: ids.append(iid)
            try: bid_step=max(1,float(d.get('bidStep') or row.get('bidStep') or 1))
            except Exception: bid_step=1
            mode=str(d.get('mode') or ('prepared' if ids else 'camera')); mode=mode if mode in ('camera','prepared') else 'camera'
            row.update({'title':str(d.get('title') or 'بث مباشر').strip()[:160],'description':str(d.get('description') or '').strip()[:1000],'startAt':str(d.get('startAt') or '').strip(),'itemIds':ids,'bidStep':bid_step,'mode':mode,'marketEnabled':bool(d.get('marketEnabled',row.get('marketEnabled',False))),'updated':datetime.datetime.now().isoformat()})
            save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('حفظ جلسة بث للبائع',{'sessionId':sid,'participantId':str(person.get('id'))},actor='البائع'); self.sendj({'ok':True,'session':with_live_timer(row)}); return
        if p=='/api/live-auctions/seller-control':
            person=self.require_participant('')
            if not person: return
            if not live_broadcast_allowed(person): self.sendj({'error':'صلاحية البث المباشر غير مفعلة لهذا الحساب'},403); return
            d=self.readj(); sessions=load_live_auctions(); sid=str(d.get('id') or ''); row=next((x for x in sessions if str(x.get('id'))==sid),None)
            if not live_session_owned_by(row,person): self.sendj({'error':'الجلسة غير موجودة أو لا تملكها'},404); return
            action=str(d.get('action') or '')
            if action in ('start','end'):
                row['status']='live' if action=='start' else 'ended'
                row['startedAt']=row.get('startedAt') or (datetime.datetime.now().isoformat() if action=='start' else '')
                if action=='end': row['endedAt']=datetime.datetime.now().isoformat(); row['archivedAt']=row['endedAt']
            elif action=='open-free-lot':
                title=str(d.get('title') or '').strip()
                if not title: self.sendj({'error':'اكتب اسم القطعة المعروضة أمام الكاميرا'},400); return
                try: start=max(0,float(d.get('startPrice') or 0)); step=max(1,float(d.get('bidStep') or row.get('bidStep') or 1)); duration=max(10,min(7200,int(float(d.get('durationSec') or 60))))
                except Exception: self.sendj({'error':'راجع السعر والزيادة والمدة'},400); return
                lot={'id':'lot-'+secrets.token_hex(6),'title':title[:180],'country':str(d.get('country') or '').strip()[:120],'condition':str(d.get('condition') or '').strip()[:80],'notes':str(d.get('notes') or '').strip()[:500],'openedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'startPrice':start,'bidStep':step}
                row['currentLot']=lot; row['currentItemId']=''; row['currentPrice']=start; row['bidStep']=step; row['lotEndsAt']=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=duration)).isoformat(); row['latestBidderName']=''; row['latestBidderId']=''; row['status']='live'
            elif action=='open-item':
                iid=str(d.get('itemId') or '')
                if iid not in [str(x) for x in (row.get('itemIds') or [])]: self.sendj({'error':'المقتنى غير مدرج في هذه الجلسة'},403); return
                src=next((i for i in load() if str(i.get('id'))==iid),None)
                if not src or item_store_type(src)!='coins': self.sendj({'error':'البث المباشر مخصص حاليًا لنوادر العملات فقط'},409); return
                try: price=max(0,float(d.get('price') or 0))
                except Exception: price=0
                row['currentItemId']=iid; row['currentLot']=None; row['currentPrice']=price; row['lotEndsAt']=''; row['latestBidderName']=''; row['latestBidderId']=''; row['status']='live'
            elif action=='close-item':
                self._close_live_item(row,bool(d.get('sold')))
            elif action=='market-toggle':
                row['marketEnabled']=bool(d.get('enabled'))
            else: self.sendj({'error':'أمر البث غير معروف'},400); return
            row['updated']=datetime.datetime.now().isoformat(); save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('تحكم بائع بالبث المباشر',{'sessionId':sid,'action':action},actor='البائع'); self.sendj({'ok':True,'session':with_live_timer(row)}); return
        if p=='/api/live-auctions/save':
            d=self.readj(); sessions=load_live_auctions(); sid=str(d.get('id') or '') or 'live-'+secrets.token_hex(5)
            row=next((x for x in sessions if str(x.get('id'))==sid),None)
            if row is None:
                row={'id':sid,'created':datetime.datetime.now().isoformat(),'status':'scheduled','currentItemId':'','currentPrice':0,'latestBidderName':'','history':[]}; sessions.append(row)
            ids=[]
            valid={str(i.get('id')) for i in load() if not i.get('archived') and item_store_type(i)=='coins'}
            for iid in (d.get('itemIds') or []):
                iid=str(iid)
                if iid in valid and iid not in ids: ids.append(iid)
            try: bid_step=max(1,float(d.get('bidStep') or row.get('bidStep') or 1))
            except (TypeError,ValueError): bid_step=1
            row.update({'title':str(d.get('title') or 'مزاد مباشر').strip()[:160],'description':str(d.get('description') or '').strip()[:1000],'startAt':str(d.get('startAt') or '').strip(),'itemIds':ids,'bidStep':bid_step,'mode':str(d.get('mode') or row.get('mode') or ('prepared' if ids else 'camera')) if str(d.get('mode') or row.get('mode') or '') in ('camera','prepared') else ('prepared' if ids else 'camera'),'broadcasterType':row.get('broadcasterType') or 'admin','broadcasterName':row.get('broadcasterName') or 'إدارة نوادر العملات','marketEnabled':bool(d.get('marketEnabled',row.get('marketEnabled',False)))})
            if d.get('status') in ('scheduled','live','ended','cancelled'): row['status']=d.get('status')
            row['updated']=datetime.datetime.now().isoformat()
            try:
                os.makedirs(DATA_ROOT,exist_ok=True)
                save_json(LIVE_AUCTIONS,{'sessions':sessions})
            except Exception as e:
                print('LIVE_AUCTION_SAVE_ERROR:',repr(e))
                self.sendj({'error':'تعذر حفظ جلسة البث في مساحة البيانات الدائمة','detail':str(e)[:240]},500); return
            try: append_operation('حفظ جلسة مزاد مباشر',{'sessionId':sid,'items':ids,'status':row['status']})
            except Exception as e: print('LIVE_AUCTION_AUDIT_WARNING:',repr(e))
            self.sendj({'ok':True,'session':with_live_timer(row)}); return
        if p=='/api/live-auctions/control':
            d=self.readj(); sessions=load_live_auctions(); sid=str(d.get('id') or ''); row=next((x for x in sessions if str(x.get('id'))==sid),None)
            if not row: self.sendj({'error':'جلسة البث غير موجودة'},404); return
            action=str(d.get('action') or '')
            if action=='delete':
                sessions=[x for x in sessions if str(x.get('id'))!=sid]; save_json(LIVE_AUCTIONS,{'sessions':sessions}); self.sendj({'ok':True}); return
            if action in ('start','end','cancel'):
                row['status']={'start':'live','end':'ended','cancel':'cancelled'}[action]
                if action=='start': row['startedAt']=row.get('startedAt') or datetime.datetime.now().isoformat()
                if action in ('end','cancel'): row['endedAt']=datetime.datetime.now().isoformat(); row['archivedAt']=row['endedAt']
            if action=='open-item':
                iid=str(d.get('itemId') or '')
                src=next((i for i in load() if str(i.get('id'))==iid),None)
                if not src or item_store_type(src)!='coins': self.sendj({'error':'البث المباشر مخصص حاليًا لنوادر العملات فقط'},409); return
                row['currentItemId']=iid; row['currentPrice']=float(d.get('price') or 0); row['latestBidderName']=''
            if action=='price': row['currentPrice']=float(d.get('price') or 0); row['latestBidderName']=str(d.get('bidderName') or '').strip()[:120]
            if action=='open-free-lot':
                title=str(d.get('title') or '').strip()
                if not title: self.sendj({'error':'اكتب اسم القطعة المعروضة أمام الكاميرا'},400); return
                try: start=max(0,float(d.get('startPrice') or 0)); step=max(1,float(d.get('bidStep') or row.get('bidStep') or 1)); duration=max(10,min(7200,int(float(d.get('durationSec') or 60))))
                except Exception: self.sendj({'error':'راجع السعر والزيادة والمدة'},400); return
                row['currentLot']={'id':'lot-'+secrets.token_hex(6),'title':title[:180],'country':str(d.get('country') or '').strip()[:120],'condition':str(d.get('condition') or '').strip()[:80],'notes':str(d.get('notes') or '').strip()[:500],'openedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'startPrice':start,'bidStep':step}; row['currentItemId']=''; row['currentPrice']=start; row['bidStep']=step; row['lotEndsAt']=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=duration)).isoformat(); row['latestBidderName']=''; row['latestBidderId']=''; row['status']='live'
            if action=='close-item': self._close_live_item(row,bool(d.get('sold')))
            if action=='market-toggle': row['marketEnabled']=bool(d.get('enabled'))
            row['updated']=datetime.datetime.now().isoformat(); save_json(LIVE_AUCTIONS,{'sessions':sessions}); append_operation('تحكم بالمزاد المباشر',{'sessionId':sid,'action':action}); self.sendj({'ok':True,'session':row}); return
        if p=='/api/promotions/update':
            d=self.readj(); iid=str(d.get('itemId') or ''); items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
            if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
            item['homeFeatured']=bool(d.get('featured')); item['homeQuickDeal']=bool(d.get('quick')); item['homeDiscounted']=bool(d.get('discounted')); item['homeDiscountPercent']=max(0,min(100,float(d.get('discountPercent') or 0))); item['homePromoUntil']=str(d.get('until') or '').strip(); item['homePromoBadge']=str(d.get('badge') or '').strip()[:60]; item['homePromoPriority']=int(float(d.get('priority') or 0)); item['updated']=int(time.time()*1000); save(items); append_operation('تحديث تمييز الواجهة',{'itemId':iid}); self.sendj({'ok':True}); return
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
        if p=='/api/image-vault/upload':
            try:
                os.makedirs(UPLOAD_DIR,exist_ok=True)
                n=int(self.headers.get('Content-Length','0'))
                if n<=0 or n>50*1024*1024: self.sendj({'error':'حجم الصورة غير مناسب (الحد 50 ميجابايت)'},413); return
                ctype=(self.headers.get('Content-Type') or '').lower(); ext='.jpg'
                if 'png' in ctype: ext='.png'
                elif 'webp' in ctype: ext='.webp'
                elif 'heic' in ctype or 'heif' in ctype: ext='.heic'
                stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'); name='vault_'+stamp+ext; dst=os.path.join(UPLOAD_DIR,name); tmp=dst+'.tmp'; remain=n
                with open(tmp,'wb') as f:
                    while remain:
                        chunk=self.rfile.read(min(1024*1024,remain))
                        if not chunk: break
                        f.write(chunk); remain-=len(chunk)
                if remain: raise IOError('رفع الصورة غير مكتمل')
                os.replace(tmp,dst)
                already_light=('jpeg' in ctype or 'jpg' in ctype) and n<=700*1024
                if not already_light:
                    try:
                        from PIL import Image, ImageOps
                        im=Image.open(dst); im=ImageOps.exif_transpose(im); im.thumbnail((1600,1600))
                        if im.mode not in ('RGB','L'): im=im.convert('RGB')
                        jpg=os.path.join(UPLOAD_DIR,'vault_'+stamp+'.jpg'); im.save(jpg,'JPEG',quality=80,optimize=False)
                        if os.path.abspath(jpg)!=os.path.abspath(dst):
                            try: os.remove(dst)
                            except OSError: pass
                        name=os.path.basename(jpg); dst=jpg
                    except Exception: pass
                now=datetime.datetime.now().isoformat(); rows=load_image_vault(); rec={'id':'iv-'+secrets.token_hex(7),'url':'/uploads/'+name,'filename':name,'status':'available','createdAt':now,'updatedAt':now,'sizeBytes':os.path.getsize(dst) if os.path.exists(dst) else n,'reservedByParticipantId':'','reservedByName':'','reservedAt':'','linkedSubmissionId':'','linkedItemId':'','linkHistory':[]}; rows.append(rec); save_json(IMAGE_VAULT,{'images':rows}); append_operation('رفع صورة إلى خزينة الصور',{'imageVaultId':rec['id'],'url':rec['url']},actor='الإدارة'); self.sendj({'ok':True,'image':rec}); return
            except Exception as e:
                try:
                    if 'tmp' in locals() and os.path.exists(tmp): os.remove(tmp)
                except OSError: pass
                self.sendj({'error':'تعذر حفظ صورة الخزينة: '+str(e)},500); return
        if p in ('/api/upload','/api/visitor/upload'):
            try:
                if p=='/api/visitor/upload':
                    pid=str(self.headers.get('X-Participant-Id') or '')
                    person=self.require_participant(pid)
                    if not person: return
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
                # R3: تطبيق الإدارة يرسل JPEG مضغوطًا وخفيفًا غالبًا. لا نعيد
                # فتحه وضغطه على الخادم إذا كان صغيرًا؛ فهذا كان يضيف انتظارًا
                # واضحًا على الجوال بعد اكتمال الرفع. الصور الكبيرة/غير JPEG
                # تستمر في المرور بمعالجة Pillow للحماية من الأحجام الضخمة.
                already_light = ('jpeg' in ctype or 'jpg' in ctype) and n <= 700*1024
                if not already_light:
                    try:
                        from PIL import Image, ImageOps
                        im=Image.open(dst); im=ImageOps.exif_transpose(im); im.thumbnail((1600,1600))
                        if im.mode not in ('RGB','L'): im=im.convert('RGB')
                        jpg=os.path.join(UPLOAD_DIR,'photo_'+stamp+'.jpg')
                        im.save(jpg,'JPEG',quality=80,optimize=False)
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
            if p=='/api/image-vault/pull':
                person=self.require_participant('')
                if not person: return
                pid=str(person.get('id') or '')
                if not participant_permissions(pid).get('dataEntry'):
                    self.sendj({'error':'صلاحية مسؤول إدخال البيانات غير مفعلة لهذا الحساب'},403); return
                ids=d.get('ids') if isinstance(d.get('ids'),list) else []
                ids=[str(x or '').strip() for x in ids if str(x or '').strip()][:8]
                if not ids: self.sendj({'error':'حدد صورة واحدة على الأقل من الخزينة'},400); return
                rows,_=image_vault_cleanup(load_image_vault()); chosen=[]; now=datetime.datetime.now().isoformat()
                for iid in ids:
                    row=next((x for x in rows if str(x.get('id'))==iid),None)
                    if not row: self.sendj({'error':'إحدى صور الخزينة غير موجودة'},404); return
                    if row.get('status')=='reserved' and str(row.get('reservedByParticipantId') or '')!=pid:
                        self.sendj({'error':'إحدى الصور سحبها مسؤول إدخال آخر بالفعل'},409); return
                    if row.get('status')=='used': self.sendj({'error':'إحدى الصور مرتبطة بمقتنى بالفعل'},409); return
                    if row.get('status') not in ('available','reserved'): self.sendj({'error':'إحدى الصور غير متاحة للسحب'},409); return
                    chosen.append(row)
                for row in chosen:
                    row.update({'status':'reserved','reservedByParticipantId':pid,'reservedByName':person.get('alias') or person.get('name') or 'مسؤول إدخال البيانات','reservedAt':now,'updatedAt':now})
                save_json(IMAGE_VAULT,{'images':rows}); append_operation('سحب صور من خزينة الصور',{'operatorId':pid,'imageIds':ids},actor='مسؤول إدخال البيانات'); self.sendj({'ok':True,'images':chosen}); return
            if p=='/api/image-vault/release':
                person=self.require_participant('')
                if not person: return
                pid=str(person.get('id') or '')
                if not participant_permissions(pid).get('dataEntry'):
                    self.sendj({'error':'صلاحية مسؤول إدخال البيانات غير مفعلة لهذا الحساب'},403); return
                ids=d.get('ids') if isinstance(d.get('ids'),list) else []
                ids={str(x or '').strip() for x in ids if str(x or '').strip()}; rows=load_image_vault(); released=[]; now=datetime.datetime.now().isoformat()
                for row in rows:
                    if str(row.get('id')) not in ids: continue
                    if row.get('status')=='reserved' and str(row.get('reservedByParticipantId') or '')==pid and not row.get('linkedSubmissionId'):
                        row.update({'status':'available','reservedByParticipantId':'','reservedByName':'','reservedAt':'','updatedAt':now}); released.append(row.get('id'))
                if released: save_json(IMAGE_VAULT,{'images':rows})
                self.sendj({'ok':True,'released':released}); return
            if p=='/api/image-vault/action':
                action=str(d.get('action') or '').strip().lower(); iid=str(d.get('id') or '').strip(); rows=load_image_vault(); row=next((x for x in rows if str(x.get('id'))==iid),None)
                if not row: self.sendj({'error':'صورة الخزينة غير موجودة'},404); return
                now=datetime.datetime.now().isoformat()
                if action=='release':
                    if row.get('status')!='reserved': self.sendj({'error':'يمكن إعادة الصور المحجوزة فقط'},409); return
                    row.update({'status':'available','reservedByParticipantId':'','reservedByName':'','reservedAt':'','updatedAt':now}); save_json(IMAGE_VAULT,{'images':rows}); append_operation('إعادة صورة محجوزة إلى خزينة الصور',{'imageVaultId':iid},actor='الإدارة'); self.sendj({'ok':True}); return
                if action=='delete':
                    if row.get('status')!='available' or row.get('linkedSubmissionId') or row.get('linkedItemId'):
                        self.sendj({'error':'لا يمكن حذف صورة مرتبطة أو قيد الاستخدام'},409); return
                    url=str(row.get('url') or ''); referenced=any(url in [str(x.get('frontImage') or ''),str(x.get('backImage') or '')]+[str(z or '') for z in (x.get('additionalImages') or [])] for x in load_collectible_submissions()) or any(url in [str(x.get('frontImg') or ''),str(x.get('backImg') or '')]+[str(z or '') for z in (x.get('additionalImages') or [])] for x in load())
                    if referenced: self.sendj({'error':'الصورة ما زالت مرتبطة بسجل ولا يمكن حذفها'},409); return
                    full=os.path.join(UPLOAD_DIR,os.path.basename(urlparse(url).path))
                    try:
                        if os.path.isfile(full): os.remove(full)
                    except OSError: pass
                    rows=[x for x in rows if str(x.get('id'))!=iid]; save_json(IMAGE_VAULT,{'images':rows}); append_operation('حذف صورة متاحة من خزينة الصور',{'imageVaultId':iid},actor='الإدارة'); self.sendj({'ok':True}); return
                self.sendj({'error':'إجراء خزينة الصور غير معروف'},400); return
            if p=='/api/data-entry/submissions':
                person=self.require_participant('')
                if not person: return
                pid=str(person.get('id') or '')
                if not participant_permissions(pid).get('dataEntry'):
                    self.sendj({'error':'صلاحية مسؤول إدخال البيانات غير مفعلة لهذا الحساب'},403); return
                mode=str(d.get('mode') or 'draft').strip().lower()
                if mode not in ('draft','submit'): mode='draft'
                sid=str(d.get('id') or '').strip()
                rows=load_collectible_submissions(); row=None
                if sid:
                    row=next((x for x in rows if str(x.get('id'))==sid and x.get('submissionSource')=='data_entry' and str(x.get('dataEntryParticipantId') or '')==pid),None)
                    if not row:
                        self.sendj({'error':'سجل الإدخال غير موجود'},404); return
                    if row.get('status') not in ('draft','needs_changes'):
                        self.sendj({'error':'هذا السجل أُرسل بالفعل ولا يمكن تعديله قبل قرار الإدارة'},409); return
                store_type=normalize_store_type(d.get('storeType'),d)
                category=str(d.get('collectibleCategory') or '').strip().lower() if store_type=='collectibles' else ''
                allowed_categories={'fantasia','antiques','prayer-beads','vehicles-models','aviation-marine','jewelry-stones','games','other'}
                if store_type=='collectibles' and category not in allowed_categories:
                    if mode=='submit': self.sendj({'error':'اختر تصنيفًا صحيحًا لنوادر المقتنيات'},400); return
                    category=category if category in allowed_categories else 'other'
                country=str(d.get('country') or '').strip()[:120]
                denomination=str(d.get('denomination') or '').strip()[:180]
                if mode=='submit' and (not country or not denomination):
                    self.sendj({'error':'الدولة/المنشأ واسم المقتنى/الفئة مطلوبان قبل الإرسال للاعتماد'},400); return
                serial=str(d.get('serial') or '').strip()[:160]
                normalized_serial=re.sub(r'\s+','',serial).upper()
                if normalized_serial:
                    for other in load():
                        vals=other.get('serials') or [other.get('serial')]
                        if not isinstance(vals,list): vals=[vals]
                        if normalized_serial in {re.sub(r'\s+','',str(v or '')).upper() for v in vals if str(v or '').strip()}:
                            self.sendj({'error':'الرقم التسلسلي مسجل مسبقًا في المستودع'},409); return
                # R9.4: الصور لا تُنسخ إلى سجل الإدخال؛ تُسحب من خزينة الصور ويُحفظ نفس رابط الملف الأصلي.
                vault_ids=d.get('imageVaultIds') if isinstance(d.get('imageVaultIds'),list) else []
                vault_ids=[str(x or '').strip() for x in vault_ids if str(x or '').strip()][:8]
                now=datetime.datetime.now().isoformat()
                if row is None and not sid: sid='de-'+secrets.token_hex(7)
                vault_rows=load_image_vault(); selected_vault=[]
                for iid in vault_ids:
                    vr=next((x for x in vault_rows if str(x.get('id'))==iid),None)
                    if not vr: self.sendj({'error':'إحدى الصور المختارة لم تعد موجودة في خزينة الصور'},404); return
                    st=str(vr.get('status') or 'available')
                    owned_reserved=st=='reserved' and str(vr.get('reservedByParticipantId') or '')==pid
                    owned_used=st=='used' and str(vr.get('linkedSubmissionId') or '')==sid
                    if not (st=='available' or owned_reserved or owned_used): self.sendj({'error':'إحدى الصور أصبحت مستخدمة أو محجوزة لمسؤول آخر'},409); return
                    selected_vault.append(vr)
                if mode=='submit' and not selected_vault and not (row and (row.get('frontImage') or row.get('backImage'))):
                    self.sendj({'error':'اسحب صورة واحدة على الأقل من خزينة الصور قبل الإرسال للاعتماد'},400); return
                if selected_vault:
                    urls=[str(x.get('url') or '') for x in selected_vault]
                    front=urls[0] if urls else ''; back=urls[1] if len(urls)>1 else ''; extras=urls[2:8]
                else:
                    # توافق مع مسودات R9.3 القديمة التي رفعت صورها مباشرة قبل إنشاء الخزينة.
                    front=str((row or {}).get('frontImage') or '').strip(); back=str((row or {}).get('backImage') or '').strip(); extras=list((row or {}).get('additionalImages') or [])[:6]
                inv=submission_inventory_values(d)
                purchase=max(0,float(d.get('purchase') or 0)); shipping=max(0,float(d.get('shipping') or 0)); other_cost=max(0,float(d.get('other') or 0)); sale_price=max(0,float(d.get('salePrice') if d.get('salePrice') not in (None,'') else d.get('expectedPrice') or 0))
                payload={
                    'submissionSource':'data_entry','createdByRole':'data_entry','dataEntryParticipantId':pid,
                    'dataEntryName':person.get('alias') or person.get('name') or 'مسؤول إدخال البيانات',
                    'storeType':store_type,'collectibleCategory':category,'country':country,'denomination':denomination,
                    'year':str(d.get('year') or '').strip()[:80],'issueEdition':str(d.get('issueEdition') or '').strip()[:140],
                    'type':str(d.get('type') or ('مقتنى' if store_type=='collectibles' else 'عملة ورقية')).strip()[:120],
                    'condition':str(d.get('condition') or '').strip()[:120],'serial':serial,'serials':[serial] if serial else [],
                    'notes':str(d.get('notes') or '').strip()[:3000],
                    'frontImage':front,'backImage':back,'additionalImages':extras,
                    'desiredDestination':'vault','purchase':purchase,'shipping':shipping,'other':other_cost,'salePrice':sale_price,'expectedPrice':sale_price,'vaultImageIds':vault_ids,
                    'warehouse':str(d.get('warehouse') or 'المستودع الرئيسي').strip()[:120] or 'المستودع الرئيسي',
                    'cabinet':str(d.get('cabinet') or '').strip()[:120],'shelf':str(d.get('shelf') or '').strip()[:120],
                    'box':str(d.get('box') or '').strip()[:120],'album':str(d.get('album') or '').strip()[:120],'pocket':str(d.get('pocket') or '').strip()[:120],
                    **inv
                }
                if row is None:
                    row={'id':sid,'created':now,'itemId':'','adminNote':'','reviewHistory':[]}; rows.append(row)
                previous=row.get('status') or 'draft'
                old_vault_ids={str(x or '') for x in (row.get('vaultImageIds') or []) if str(x or '')}
                selected_ids={str(x.get('id')) for x in selected_vault}
                # الصور التي أزيلت من مسودة قابلة للتعديل ترجع إلى المتاحة؛ الملف نفسه لا يُنسخ ولا يُحذف.
                for vr in vault_rows:
                    vid=str(vr.get('id') or '')
                    if vid in old_vault_ids-selected_ids and str(vr.get('linkedSubmissionId') or '')==sid and not vr.get('linkedItemId'):
                        vr.update({'status':'available','linkedSubmissionId':'','reservedByParticipantId':'','reservedByName':'','reservedAt':'','updatedAt':now})
                for vr in selected_vault:
                    vr.update({'status':'used','linkedSubmissionId':sid,'linkedItemId':'','reservedByParticipantId':'','reservedByName':'','reservedAt':'','usedAt':vr.get('usedAt') or now,'updatedAt':now})
                if selected_vault or old_vault_ids: save_json(IMAGE_VAULT,{'images':vault_rows})
                row.update(payload); row['updated']=now; row['status']='pending' if mode=='submit' else 'draft'
                if mode=='submit':
                    row['submittedAt']=now; row['adminNote']=''
                    add_notification('admin','','approval','📥 مقتنى بانتظار الاعتماد',f"أرسل مسؤول إدخال البيانات {payload['dataEntryName']} — {country or '—'} / {denomination or '—'} — للمراجعة.",sid,'/admin')
                    append_operation('إرسال مقتنى للاعتماد بواسطة مسؤول إدخال البيانات',{'submissionId':sid,'operatorId':pid,'storeType':store_type,'country':country,'denomination':denomination},actor='مسؤول إدخال البيانات')
                else:
                    append_operation('حفظ مسودة إدخال مقتنى',{'submissionId':sid,'operatorId':pid,'previousStatus':previous},actor='مسؤول إدخال البيانات')
                save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                self.sendj({'ok':True,'status':row['status'],'submission':row}); return

            if p=='/api/collectible-submissions':
                pid=str(d.get('participantId') or '')
                person=self.require_participant(pid)
                if not person: return

                country=str(d.get('country') or '').strip()
                denomination=str(d.get('denomination') or '').strip()
                if not country or not denomination:
                    self.sendj({'error':'الدولة والفئة مطلوبتان'},400); return

                front=str(d.get('frontImage') or '')
                back=str(d.get('backImage') or '')
                for label,img in [('الوجه',front),('الخلف',back)]:
                    if img and not img.startswith('/uploads/') and (not img.startswith('data:image/') or len(img)>6*1024*1024):
                        self.sendj({'error':f'صورة {label} غير صالحة أو كبيرة جدًا'},400); return

                now=datetime.datetime.now().isoformat()
                rows=load_collectible_submissions()
                items=load()
                sid=str(d.get('id') or '').strip()
                destination=str(d.get('desiredDestination') or 'vault').strip()
                if destination not in ('vault','market','auction'): destination='vault'
                requested_store_type=normalize_store_type(d.get('storeType'),d)
                collectible_category=str(d.get('collectibleCategory') or '').strip().lower()
                allowed_collectible_categories={'fantasia','antiques','prayer-beads','vehicles-models','aviation-marine','jewelry-stones','games','other'}
                if requested_store_type=='collectibles':
                    if collectible_category not in allowed_collectible_categories:
                        self.sendj({'error':'اختر تصنيفًا صحيحًا لنوادر المقتنيات'},400); return
                else:
                    collectible_category=''

                inv=submission_inventory_values(d)
                serial=str(d.get('serial') or '').strip()
                normalized_serial=re.sub(r'\s+','',serial).upper()
                existing_item=None
                row=None

                if sid:
                    row=next((x for x in rows if str(x.get('id'))==sid and str(x.get('participantId'))==pid),None)
                    if not row:
                        self.sendj({'error':'السجل غير موجود أو لا تملك صلاحية تعديله'},404); return
                    if row.get('itemId'):
                        existing_item=next((x for x in items if str(x.get('id'))==str(row.get('itemId')) and str(x.get('ownerParticipantId') or '')==pid),None)

                # منع تكرار الرقم التسلسلي على مقتنى آخر.
                if normalized_serial:
                    for other in items:
                        if existing_item and str(other.get('id'))==str(existing_item.get('id')): continue
                        vals=other.get('serials') or [other.get('serial')]
                        if not isinstance(vals,list): vals=[vals]
                        norms={re.sub(r'\s+','',str(v or '')).upper() for v in vals if str(v or '').strip()}
                        if normalized_serial in norms:
                            self.sendj({'error':'الرقم التسلسلي مسجل مسبقًا في المنصة'},409); return

                # إعداد السوق المباشر عند اختياره.
                market_price=max(0,float(d.get('marketSalePrice') or 0))
                market_qty=max(1,int(float(d.get('marketQuantity') or d.get('inventoryUnitCount') or 1)))
                market_neg=bool(d.get('marketNegotiationEnabled'))
                market_neg_pct=max(0,min(50,float(d.get('marketNegotiationPercent') or 5)))
                if destination=='market' and market_price<=0:
                    self.sendj({'error':'حدد سعر البيع قبل نشر المقتنى في السوق'},400); return

                # إعداد المزاد المباشر عند اختياره.
                auction_end=str(d.get('auctionEnd') or '').strip()
                opening=max(0,float(d.get('auctionOpeningPrice') or 0))
                step=max(.01,float(d.get('auctionBidStep') or 1))
                target=max(0,float(d.get('auctionTargetPrice') or 0))
                terms=str(d.get('auctionAdditionalTerms') or '').strip()[:1000]
                if destination=='auction':
                    if not auction_end:
                        self.sendj({'error':'حدد موعد انتهاء المزاد'},400); return
                    try:
                        end_dt=datetime.datetime.fromisoformat(auction_end.replace('Z','+00:00'))
                        now_dt=datetime.datetime.now(end_dt.tzinfo) if end_dt.tzinfo else auction_local_now()
                        if end_dt<=now_dt:
                            self.sendj({'error':'موعد انتهاء المزاد يجب أن يكون في المستقبل'},400); return
                    except ValueError:
                        self.sendj({'error':'صيغة موعد انتهاء المزاد غير صحيحة'},400); return
                    if opening<=0:
                        self.sendj({'error':'حدد سعر افتتاح أكبر من صفر للمزاد'},400); return

                # تصنيفات عامة مباشرة.
                special_enabled=(requested_store_type=='coins' and bool(d.get('specialNumberEnabled')))
                special_types=d.get('specialNumberTypes') if isinstance(d.get('specialNumberTypes'),list) else []
                special_types=[str(x).strip() for x in special_types if str(x).strip()]
                special_reason=str(d.get('specialNumberReason') or '').strip()[:1000]

                fantasia_enabled=(requested_store_type=='collectibles' and (bool(d.get('fantasiaEnabled')) or collectible_category=='fantasia'))
                fantasia_type=str(d.get('fantasiaType') or '').strip()
                fantasia_issuer=str(d.get('fantasiaIssuer') or '').strip()[:300]
                fantasia_notes=str(d.get('fantasiaNotes') or '').strip()[:1000]

                transitional_enabled=(requested_store_type=='coins' and bool(d.get('transitionalIssueEnabled')))
                transitional_type=str(d.get('transitionalIssueType') or '').strip()
                transitional_prev=str(d.get('transitionalPreviousIssue') or '').strip()
                transitional_next=str(d.get('transitionalNextIssue') or '').strip()
                transitional_rarity=str(d.get('transitionalRarity') or '').strip()
                transitional_reason=str(d.get('transitionalReason') or '').strip()[:1000]
                transitional_notes=str(d.get('transitionalNotes') or '').strip()[:1000]

                if requested_store_type!='coins':
                    special_types=[]; special_reason=''
                    transitional_type=''; transitional_prev=''; transitional_next=''; transitional_rarity=''; transitional_reason=''; transitional_notes=''
                if requested_store_type!='collectibles':
                    fantasia_enabled=False; fantasia_type=''; fantasia_issuer=''; fantasia_notes=''

                if special_enabled and not special_types:
                    self.sendj({'error':'اختر نوع الرقم المميز أو النادر'},400); return
                if transitional_enabled and not transitional_type:
                    self.sendj({'error':'اختر نوع الحالة الانتقالية'},400); return

                base_fields={
                    'storeType':requested_store_type,
                    'collectibleCategory':collectible_category if requested_store_type=='collectibles' else '',
                    'country':country,'denomination':denomination,
                    'year':str(d.get('year') or '').strip(),
                    'issueEdition':str(d.get('issueEdition') or '').strip(),
                    'type':str(d.get('type') or 'عملة ورقية').strip(),
                    'condition':str(d.get('condition') or 'UNC').strip(),
                    'serial':serial,'serials':[serial] if serial else [],
                    'notes':str(d.get('notes') or '').strip(),
                    'frontImg':front,'backImg':back,
                    'ownerName':person.get('alias') or person.get('name',''),
                    'ownerPhone':person.get('phone',''),
                    'ownerParticipantId':pid,
                    'storageStatus':'warehouse','warehouse':'المستودع الرئيسي',
                    'forMarket':destination=='market','marketApproved':destination=='market',
                    'marketSalePrice':market_price if destination=='market' else 0,
                    'marketQuantity':market_qty if destination=='market' else 0,
                    'marketNegotiationEnabled':market_neg if destination=='market' else False,
                    'marketNegotiationPercent':market_neg_pct if destination=='market' else 0,
                    'forAuction':destination=='auction','auctionApproved':destination=='auction',
                    'auctionEnd':auction_end if destination=='auction' else '',
                    'auctionOpeningPrice':opening if destination=='auction' else 0,
                    'auctionStartPrice':opening if destination=='auction' else 0,
                    'auctionCurrentPrice':opening if destination=='auction' else 0,
                    'auctionBidStep':step if destination=='auction' else 1,
                    'auctionTargetPrice':target if destination=='auction' else 0,
                    'auctionAdditionalTerms':terms if destination=='auction' else '',
                    'specialNumberEnabled':special_enabled,
                    'specialNumberTypes':special_types,
                    'specialNumberType':special_types[0] if special_types else '',
                    'specialNumberReason':special_reason,
                    'fantasiaEnabled':fantasia_enabled,
                    'fantasiaType':fantasia_type,
                    'fantasiaIssuer':fantasia_issuer,
                    'fantasiaNotes':fantasia_notes,
                    'transitionalIssueEnabled':transitional_enabled,
                    'transitionalIssueType':transitional_type,
                    'transitionalPreviousIssue':transitional_prev,
                    'transitionalNextIssue':transitional_next,
                    'transitionalRarity':transitional_rarity,
                    'transitionalReason':transitional_reason,
                    'transitionalNotes':transitional_notes,
                    'updated':int(time.time()*1000),
                    **inv
                }

                if existing_item:
                    # السجل المعتمد يعدل مقتناه مباشرة دون إعادة اعتماد.
                    protected_quantity=bool(existing_item.get('forMarket') or existing_item.get('forAuction'))
                    if protected_quantity:
                        for k in ('inventoryUnitType','inventoryUnitCount','piecesPerUnit','quantity'):
                            base_fields.pop(k,None)
                    existing_item.update(base_fields)
                    existing_item['sourceSubmissionId']=sid
                    item=existing_item
                    item_id=str(item.get('id'))
                else:
                    item_id='k-'+secrets.token_hex(8)
                    item={'id':item_id,'soldQuantity':0,'damagedQuantity':0,'sourceSubmissionId':sid or '', 'created':now, **base_fields}
                    items.append(item)

                # سجل تاريخي فقط؛ لا توجد مرحلة موافقة.
                if row is None:
                    sid='cs-'+secrets.token_hex(6)
                    item['sourceSubmissionId']=sid
                    row={'id':sid,'created':now}
                    rows.append(row)

                row.update({
                    'storeType':requested_store_type,'collectibleCategory':collectible_category if requested_store_type=='collectibles' else '','participantId':pid,'participantName':person.get('name',''),'participantPhone':person.get('phone',''),
                    'country':country,'denomination':denomination,'year':base_fields['year'],
                    'issueEdition':base_fields['issueEdition'],'type':base_fields['type'],
                    'condition':base_fields['condition'],'serial':serial,'notes':base_fields['notes'],
                    'desiredDestination':destination,'frontImage':front,'backImage':back,
                    'status':'approved','adminNote':'','updated':now,'itemId':item_id,
                    'warehouseVerified':True,'warehouseVerifiedAt':now,
                    'autoApproved':True,'autoApprovedAt':now,
                    'specialNumberEnabled':special_enabled,'specialNumberTypes':special_types,
                    'transitionalIssueEnabled':transitional_enabled,'transitionalIssueType':transitional_type,
                    **inv
                })

                save(items)
                save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                append_operation('إضافة/تعديل مقتنى مباشر بواسطة العميل',{
                    'submissionId':sid,'itemId':item_id,'participantId':pid,'storeType':requested_store_type,
                    'destination':destination,'marketPublished':destination=='market',
                    'auctionPublished':destination=='auction',
                    'specialNumberEnabled':special_enabled,
                    'transitionalIssueEnabled':transitional_enabled
                },actor='العميل')

                # الإدارة تستلم إشعار رقابي فقط، بلا طلب اعتماد.
                add_notification('admin','','moderation','🪙 إضافة مباشرة جديدة',
                                 f"{person.get('name','عميل')} أضاف {country} — {denomination} مباشرة إلى المنصة. يمكن للإدارة الإيقاف أو الإخفاء عند الحاجة.",
                                 item_id,'/admin')
                add_notification('participant',pid,'approval','✅ تمت إضافة المقتنى مباشرة',
                                 f"تمت إضافة {country} — {denomination} بنجاح دون انتظار اعتماد الإدارة.",
                                 item_id,'/account')

                self.sendj({
                    'ok':True,'directApproved':True,'itemId':item_id,
                    'publishedMarket':destination=='market',
                    'publishedAuction':destination=='auction',
                    'submission':{k:v for k,v in row.items() if k not in ('frontImage','backImage')}
                }); return
            if p=='/api/collectible-submissions/delete':
                pid=str(d.get('participantId') or ''); sid=str(d.get('id') or '')
                person=self.require_participant(pid)
                if not person: return
                rows=load_collectible_submissions(); row=next((x for x in rows if str(x.get('id'))==sid and str(x.get('participantId'))==pid),None)
                if not row: self.sendj({'error':'السجل غير موجود أو لا تملك صلاحية حذفه'},404); return
                if row.get('itemId'):
                    linked=next((x for x in load() if str(x.get('id'))==str(row.get('itemId')) or str(x.get('sourceSubmissionId') or '')==sid),None)
                    if linked or row.get('status')=='approved':
                        self.sendj({'error':'تم اعتماد السجل؛ استخدم الحذف الآمن من «مقتنياتي المعتمدة»'},409); return
                    row['itemId']=''
                if row.get('status')=='approved':
                    self.sendj({'error':'تم اعتماد السجل؛ استخدم الحذف الآمن من «مقتنياتي المعتمدة»'},409); return
                rows=[x for x in rows if str(x.get('id'))!=sid]; save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                append_operation('حذف طلب مقتنى',{'submissionId':sid,'participantId':pid},actor='العميل')
                self.sendj({'ok':True}); return
            if p=='/api/collectible-submissions/status':
                self.sendj({'error':'تم إلغاء الاعتماد المسبق في V4.8.1. استخدم مراقبة المقتنيات للإيقاف أو الإخفاء.'},410); return

            if p=='/api/data-entry/review':
                action=str(d.get('action') or '').strip().lower()
                ids=d.get('ids') if isinstance(d.get('ids'),list) else [d.get('id')]
                ids=[str(x or '').strip() for x in ids if str(x or '').strip()][:100]
                note=str(d.get('note') or '').strip()[:2000]
                if action not in ('approve','needs_changes','reject'):
                    self.sendj({'error':'إجراء الاعتماد غير صالح'},400); return
                if action in ('needs_changes','reject') and not note:
                    self.sendj({'error':'اكتب ملاحظة توضح سبب الإعادة أو الرفض'},400); return
                if not ids:
                    self.sendj({'error':'لم يتم اختيار أي سجل'},400); return
                rows=load_collectible_submissions(); items=load(); now=datetime.datetime.now().isoformat(); results=[]; changed=False
                for sid in ids:
                    row=next((x for x in rows if str(x.get('id'))==sid and x.get('submissionSource')=='data_entry'),None)
                    if not row:
                        results.append({'id':sid,'ok':False,'error':'السجل غير موجود'}); continue
                    if row.get('status')!='pending':
                        results.append({'id':sid,'ok':False,'error':'السجل ليس بانتظار الاعتماد'}); continue
                    operator_id=str(row.get('dataEntryParticipantId') or '')
                    if action=='approve':
                        serial=str(row.get('serial') or '').strip(); norm=re.sub(r'\s+','',serial).upper()
                        duplicate=False
                        if norm:
                            for it in items:
                                vals=it.get('serials') or [it.get('serial')]
                                if not isinstance(vals,list): vals=[vals]
                                if norm in {re.sub(r'\s+','',str(v or '')).upper() for v in vals if str(v or '').strip()}: duplicate=True; break
                        if duplicate:
                            results.append({'id':sid,'ok':False,'error':'الرقم التسلسلي مسجل مسبقًا'}); continue
                        inv=submission_inventory_values(row); item_id='k-'+secrets.token_hex(8)
                        item={
                            'id':item_id,'storeType':normalize_store_type(row.get('storeType'),row),
                            'collectibleCategory':str(row.get('collectibleCategory') or ''),'country':str(row.get('country') or ''),
                            'denomination':str(row.get('denomination') or ''),'year':str(row.get('year') or ''),'issueEdition':str(row.get('issueEdition') or ''),
                            'type':str(row.get('type') or ''),'condition':str(row.get('condition') or ''),'serial':serial,'serials':[serial] if serial else [],
                            'frontImg':str(row.get('frontImage') or ''),'backImg':str(row.get('backImage') or ''),'additionalImages':list(row.get('additionalImages') or [])[:6],
                            'notes':str(row.get('notes') or ''),'purchase':max(0,float(row.get('purchase') or 0)),'shipping':max(0,float(row.get('shipping') or 0)),
                            'other':max(0,float(row.get('other') or 0)),'salePrice':max(0,float(row.get('salePrice') if row.get('salePrice') not in (None,'') else row.get('expectedPrice') or 0)),'expectedPrice':max(0,float(row.get('salePrice') if row.get('salePrice') not in (None,'') else row.get('expectedPrice') or 0)),'vaultImageIds':list(row.get('vaultImageIds') or [])[:8],
                            'warehouse':str(row.get('warehouse') or 'المستودع الرئيسي'),'cabinet':str(row.get('cabinet') or ''),'shelf':str(row.get('shelf') or ''),
                            'box':str(row.get('box') or ''),'album':str(row.get('album') or ''),'pocket':str(row.get('pocket') or ''),
                            'storageStatus':'warehouse','forMarket':False,'marketApproved':False,'forAuction':False,'auctionApproved':False,
                            'ownerName':'دار المقتنيات','ownerPhone':'','ownerParticipantId':'',
                            'enteredByParticipantId':operator_id,'enteredByName':str(row.get('dataEntryName') or 'مسؤول إدخال البيانات'),
                            'sourceSubmissionId':sid,'moderationStatus':'active','soldQuantity':0,'damagedQuantity':0,
                            'created':now,'updated':int(time.time()*1000),**inv
                        }
                        items.append(item); row['status']='approved'; row['itemId']=item_id; row['warehouseVerified']=True; row['warehouseVerifiedAt']=now
                        vault_rows=load_image_vault(); vault_changed=False
                        for vr in vault_rows:
                            if str(vr.get('id') or '') in {str(x or '') for x in (row.get('vaultImageIds') or [])}:
                                vr.update({'status':'used','linkedSubmissionId':sid,'linkedItemId':item_id,'updatedAt':now}); vault_changed=True
                        if vault_changed: save_json(IMAGE_VAULT,{'images':vault_rows})
                        row['approvedAt']=now; row['adminNote']=note; row['reviewedAt']=now; row['reviewedBy']='الإدارة'
                        row.setdefault('reviewHistory',[]).append({'action':'approve','at':now,'note':note,'actor':'الإدارة','itemId':item_id})
                        append_operation('اعتماد مقتنى من مسؤول إدخال البيانات وإرساله للمستودع',{'submissionId':sid,'itemId':item_id,'operatorId':operator_id},actor='الإدارة')
                        if operator_id: add_notification('participant',operator_id,'approval','✅ تم اعتماد المقتنى',f"تم اعتماد {row.get('country','')} — {row.get('denomination','')} وإرساله إلى المستودع.",item_id,'/data-entry')
                        results.append({'id':sid,'ok':True,'status':'approved','itemId':item_id}); changed=True
                    elif action=='needs_changes':
                        row['status']='needs_changes'; row['adminNote']=note; row['reviewedAt']=now; row['reviewedBy']='الإدارة'
                        row.setdefault('reviewHistory',[]).append({'action':'needs_changes','at':now,'note':note,'actor':'الإدارة'})
                        append_operation('إعادة إدخال مقتنى للتعديل',{'submissionId':sid,'operatorId':operator_id,'note':note},actor='الإدارة')
                        if operator_id: add_notification('participant',operator_id,'approval','✏️ إعادة للتعديل',f"{row.get('country','')} — {row.get('denomination','')}: {note}",sid,'/data-entry')
                        results.append({'id':sid,'ok':True,'status':'needs_changes'}); changed=True
                    else:
                        vault_rows,vault_changed=image_vault_release_for_submission(sid,load_image_vault(),'رفض الإدخال من الإدارة')
                        if vault_changed: save_json(IMAGE_VAULT,{'images':vault_rows})
                        row['status']='rejected'; row['adminNote']=note; row['reviewedAt']=now; row['reviewedBy']='الإدارة'; row['rejectedAt']=now
                        row.setdefault('reviewHistory',[]).append({'action':'reject','at':now,'note':note,'actor':'الإدارة'})
                        append_operation('رفض مقتنى من مسؤول إدخال البيانات',{'submissionId':sid,'operatorId':operator_id,'note':note},actor='الإدارة')
                        if operator_id: add_notification('participant',operator_id,'approval','❌ تم رفض المقتنى',f"{row.get('country','')} — {row.get('denomination','')}: {note}",sid,'/data-entry')
                        results.append({'id':sid,'ok':True,'status':'rejected'}); changed=True
                if changed:
                    save(items); save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                self.sendj({'ok':all(x.get('ok') for x in results) if results else False,'results':results,'approved':sum(1 for x in results if x.get('status')=='approved')}); return

            if p=='/api/permissions/update':
                pid=str(d.get('participantId') or ''); people=load_people()
                if not any(str(x.get('id'))==pid for x in people): self.sendj({'error':'المشارك غير موجود'},404); return
                allowed=('sellerEndedAuctions','sellerMarket','liveBroadcast','marketSupervision','auctionSupervision','ordersView','ordersManage','dataEntry'); perms=load_user_permissions(); current=participant_permissions(pid)
                for k in allowed:
                    if k in d: current[k]=bool(d.get(k))
                # R9.5D: keep duplicate legacy records for the same phone on one permission set.
                linked_ids=participant_linked_ids(pid) or [pid]
                for linked_pid in linked_ids: perms[linked_pid]=dict(current)
                save_json(USER_PERMISSIONS,{'users':perms}); append_operation('تحديث صلاحيات مستخدم',{'participantId':pid,'linkedParticipantIds':linked_ids,'permissions':current}); self.sendj({'ok':True,'permissions':current,'linkedParticipantIds':linked_ids}); return
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
                person=self.require_participant(pid)
                if not person: return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية تعديله'},404); return
                if item.get('auctionSold'): self.sendj({'error':'المقتنى مباع ولا يمكن تعديل بياناته الأساسية'},409); return
                for k in ('country','denomination','issueEdition','year','type','condition','notes','frontImg','backImg'):
                    if k in d: item[k]=str(d.get(k) or '').strip()
                if 'specialNumberEnabled' in d:
                    item['specialNumberEnabled']=bool(d.get('specialNumberEnabled'))
                    types=d.get('specialNumberTypes') if isinstance(d.get('specialNumberTypes'),list) else []
                    types=[str(x).strip() for x in types if str(x).strip()]
                    item['specialNumberTypes']=types
                    item['specialNumberType']=types[0] if types else ''
                    item['specialNumberReason']=str(d.get('specialNumberReason') or '').strip()[:1000]
                    if item['specialNumberEnabled'] and not types:
                        self.sendj({'error':'اختر نوع الرقم المميز أو النادر'},400); return
                if 'fantasiaEnabled' in d:
                    item['fantasiaEnabled']=bool(d.get('fantasiaEnabled'))
                    item['fantasiaType']=str(d.get('fantasiaType') or '').strip()
                    item['fantasiaIssuer']=str(d.get('fantasiaIssuer') or '').strip()[:300]
                    item['fantasiaNotes']=str(d.get('fantasiaNotes') or '').strip()[:1000]
                if 'transitionalIssueEnabled' in d:
                    item['transitionalIssueEnabled']=bool(d.get('transitionalIssueEnabled'))
                    item['transitionalIssueType']=str(d.get('transitionalIssueType') or '').strip()
                    item['transitionalPreviousIssue']=str(d.get('transitionalPreviousIssue') or '').strip()
                    item['transitionalNextIssue']=str(d.get('transitionalNextIssue') or '').strip()
                    item['transitionalRarity']=str(d.get('transitionalRarity') or '').strip()
                    item['transitionalReason']=str(d.get('transitionalReason') or '').strip()[:1000]
                    item['transitionalNotes']=str(d.get('transitionalNotes') or '').strip()[:1000]
                    if item['transitionalIssueEnabled'] and not item['transitionalIssueType']:
                        self.sendj({'error':'اختر نوع الحالة الانتقالية'},400); return
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
                add_notification('admin','','moderation','✏️ عدّل المالك بيانات مقتناه',f"{item.get('country','')} — {item.get('denomination','')}",iid,'/admin')
                self.sendj({'ok':True}); return

            if p=='/api/owner/item/delete':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=self.require_participant(pid)
                if not person: return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية حذفه'},404); return
                round_no=int(item.get('auctionRound') or 1)
                has_bids=any(str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==round_no for b in load_bids())
                has_market=any(str(r.get('itemId'))==iid and str(r.get('status') or 'new') not in ('completed','cancelled','rejected') for r in load_market_requests())
                has_orders=any(any(str(line.get('itemId'))==iid for line in (o.get('items') or [])) for o in load_orders())
                if item.get('forMarket') or item.get('forAuction') or has_bids or has_market or has_orders or item.get('auctionSold'):
                    self.sendj({'error':'لا يمكن حذف مقتنى مرتبط بعرض أو مزاد أو طلب. اسحب العرض/ألغ المزاد وأغلق الالتزامات أولًا.'},409); return
                archive_item_record(item,'حذف بواسطة صاحب المقتنى','العميل')
                item['ownerArchived']=True; item['ownerArchivedAt']=datetime.datetime.now().isoformat()
                item['updated']=int(time.time()*1000); save(items)
                append_operation('نقل مقتنى إلى الأرشيف بواسطة المالك',{'itemId':iid,'participantId':pid},actor='العميل')
                add_notification('participant',pid,'approval','تم حذف المقتنى من قائمتك',f"{item.get('country','')} — {item.get('denomination','')} حُفظ في الأرشيف الداخلي ولم يعد ظاهرًا في حسابك.",iid,'/account')
                self.sendj({'ok':True}); return

            if p=='/api/owner/market/update':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=self.require_participant(pid)
                if not person: return
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
                if price<=0: self.sendj({'error':'حدد سعر بيع أكبر من صفر قبل إرسال العرض للسوق'},400); return
                qty=max(1,int(float(d.get('availableQuantity') or item.get('availableQuantity') or 1)))
                max_qty=max(1,int(item.get('quantity') or item.get('availableQuantity') or qty))
                item['marketSalePrice']=price; item['availableQuantity']=min(qty,max_qty)
                item['marketNegotiationEnabled']=bool(d.get('marketNegotiationEnabled',item.get('marketNegotiationEnabled',False)))
                item['marketNegotiationPercent']=max(0,min(50,float(d.get('marketNegotiationPercent') or item.get('marketNegotiationPercent') or 0)))
                item['forMarket']=True
                item['marketApproved']=True
                add_notification('admin','','moderation','🛒 عرض سوق مباشر',f"{item.get('country','')} — {item.get('denomination','')} نُشر مباشرة بواسطة صاحبه.",iid,'/admin')
                item['updated']=int(time.time()*1000); save(items)
                append_operation('نشر/تحديث السوق مباشرة بواسطة المالك',{'itemId':iid,'participantId':pid,'price':price,'approved':True},actor='العميل')
                self.sendj({'ok':True,'pendingApproval':False,'published':True}); return

            if p=='/api/owner/auction/update':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or '')
                person=self.require_participant(pid)
                if not person: return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid and str(x.get('ownerParticipantId') or '')==pid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لا تملك صلاحية إدارته'},404); return
                if item.get('auctionSold') or str(item.get('auctionOutcome') or '')=='sold':
                    self.sendj({'error':'المزاد مباع ومغلق نهائيًا'},409); return
                requested_end=str(d.get('auctionEnd') or item.get('auctionEnd') or '').strip()
                if not requested_end:
                    self.sendj({'error':'اختر موعد انتهاء المزاد'},400); return
                try:
                    end_dt=datetime.datetime.fromisoformat(requested_end.replace('Z','+00:00'))
                    now_dt=datetime.datetime.now(end_dt.tzinfo) if end_dt.tzinfo else auction_local_now()
                    if end_dt<=now_dt: self.sendj({'error':'موعد انتهاء المزاد يجب أن يكون في المستقبل'},400); return
                except ValueError:
                    self.sendj({'error':'موعد انتهاء المزاد غير صالح. اختر التاريخ والوقت من الحقل المخصص.'},400); return
                round_no=int(item.get('auctionRound') or 1)
                bids=[b for b in load_bids() if str(b.get('itemId'))==iid and int(b.get('auctionRound') or 1)==round_no]
                try: step=float(d.get('auctionBidStep') if d.get('auctionBidStep') not in (None,'') else item.get('auctionBidStep') or 1)
                except Exception: step=0
                if step<=0: self.sendj({'error':'قيمة الزيادة لكل مزايدة يجب أن تكون أكبر من صفر'},400); return
                try: target=float(d.get('auctionTargetPrice') if d.get('auctionTargetPrice') not in (None,'') else item.get('auctionTargetPrice') or 0)
                except Exception: target=-1
                if target<0: self.sendj({'error':'الحد الأدنى لإرساء البيع لا يمكن أن يكون سالبًا'},400); return
                opening=float(item.get('auctionOpeningPrice') or item.get('auctionStartPrice') or 0)
                if not bids:
                    try: opening=float(d.get('auctionOpeningPrice') if d.get('auctionOpeningPrice') not in (None,'') else opening)
                    except Exception: opening=0
                    if opening<=0: self.sendj({'error':'سعر افتتاح المزايدة مطلوب ويجب أن يكون أكبر من صفر'},400); return
                    item['auctionOpeningPrice']=opening; item['auctionStartPrice']=opening; item['auctionCurrentPrice']=opening
                elif 'auctionOpeningPrice' in d:
                    try: requested_opening=float(d.get('auctionOpeningPrice') or 0)
                    except Exception: requested_opening=opening
                    if abs(requested_opening-opening)>1e-9:
                        self.sendj({'error':'تم تسجيل مزايدات؛ لا يمكن تغيير سعر الافتتاح الآن'},409); return
                if target>0 and opening>0 and target<opening:
                    self.sendj({'error':'الحد الأدنى لإرساء البيع يجب أن يساوي سعر الافتتاح أو يكون أعلى منه، أو اجعله 0 بدون حد'},400); return
                item['auctionBidStep']=step
                item['auctionTargetPrice']=target
                item['auctionAdditionalTerms']=str(d.get('auctionAdditionalTerms') if d.get('auctionAdditionalTerms') is not None else item.get('auctionAdditionalTerms') or '').strip()[:1000]
                item['auctionEnd']=requested_end
                item['forAuction']=True
                item['auctionApproved']=True
                add_notification('admin','','moderation','⚖ مزاد مباشر',f"{item.get('country','')} — {item.get('denomination','')} نُشر مباشرة بواسطة صاحبه.",iid,'/admin')
                item['updated']=int(time.time()*1000); save(items)
                append_operation('نشر/تحديث المزاد مباشرة بواسطة المالك',{'itemId':iid,'participantId':pid,'bidCount':len(bids),'approved':True,'auctionEnd':requested_end,'openingPrice':opening,'bidStep':step,'targetPrice':target},actor='العميل')
                self.sendj({'ok':True,'openingLocked':bool(bids),'pendingApproval':False,'published':True,'auctionEnd':requested_end,'auctionOpeningPrice':opening,'auctionBidStep':step}); return

            if p=='/api/owner/auction/cancel':
                pid=str(d.get('participantId') or ''); iid=str(d.get('itemId') or ''); reason=str(d.get('reason') or '').strip()
                person=self.require_participant(pid)
                if not person: return
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

            if p=='/api/visitor/order/action':
                pid=str(d.get('participantId') or ''); oid=str(d.get('orderId') or ''); action=str(d.get('action') or '')
                person=self.require_participant(pid)
                if not person: return
                phone=''.join(ch for ch in str(person.get('phone') or '') if ch.isdigit())
                rows=load_orders(); row=next((x for x in rows if str(x.get('id') or '')==oid and (str(x.get('participantId') or '')==pid or ''.join(ch for ch in str(x.get('customerPhone') or '') if ch.isdigit())==phone)),None)
                if not row: self.sendj({'error':'الطلب غير موجود أو لا يخص هذا الحساب'},404); return
                status=str(row.get('status') or ''); payment=str(row.get('paymentStatus') or 'unpaid'); now=datetime.datetime.now().isoformat(); number=row.get('orderNumber') or oid
                if action=='cancel':
                    if str(row.get('source') or '')!='market': self.sendj({'error':'إلغاء طلب المزاد يحتاج اعتماد الإدارة؛ استخدم زر «طلب إلغاء»'},409); return
                    if payment in ('paid','proof_submitted') or status not in ('new','awaiting_payment','stalled'):
                        self.sendj({'error':'الإلغاء الفوري متاح فقط لطلب السوق غير المسدد وغير المشحون'},409); return
                    update_order_status(row,'cancelled','ألغاه المشتري قبل السداد؛ أعيدت الكمية إلى المتاح')
                    row['cancelledBy']='participant'; row['cancelledAt']=now
                    requests=load_market_requests()
                    req=next((x for x in requests if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                    if req: req['status']='cancelled'; req['cancelledAt']=now; req['updated']=now; save_json(MARKET_REQUESTS,{'requests':requests})
                    save_json(ORDERS,{'orders':rows}); append_operation('إلغاء طلب غير مسدد وإعادة الكمية',{'orderId':oid,'orderNumber':number,'participantId':pid},actor='العميل')
                    add_notification('admin','','order','أُلغي طلب غير مسدد',f'ألغى العميل الطلب {number} وعادت كميته إلى المتاح.','', '/admin')
                    self.sendj({'ok':True,'message':f'تم إلغاء الطلب {number} وإعادة كميته إلى المتاح.'}); return
                if action=='cancel_request':
                    if payment in ('paid','proof_submitted') or status not in ('new','awaiting_payment','stalled'):
                        self.sendj({'error':'لا يمكن طلب الإلغاء في حالة الطلب الحالية'},409); return
                    if row.get('cancellationRequestedAt'): self.sendj({'ok':True,'message':'طلب الإلغاء مسجل بالفعل لدى الإدارة.'}); return
                    row['cancellationRequestedAt']=now; row['cancellationStatus']='requested'; row['updated']=now; row.setdefault('history',[]).append({'status':status,'at':now,'note':'طلب العميل إلغاء الطلب'})
                    save_json(ORDERS,{'orders':rows}); add_notification('admin','','order','طلب إلغاء',f'طلب العميل إلغاء الطلب {number}.','', '/admin'); append_operation('طلب إلغاء من العميل',{'orderId':oid,'orderNumber':number,'participantId':pid},actor='العميل')
                    self.sendj({'ok':True,'message':'تم إرسال طلب الإلغاء إلى الإدارة.'}); return
                if action=='refund_request':
                    if payment!='paid' or status not in ('paid','preparing','ready_to_ship'):
                        self.sendj({'error':'طلب الاسترداد متاح للطلب المسدد الذي لم يُشحن فقط'},409); return
                    if row.get('refundRequestedAt'): self.sendj({'ok':True,'message':'طلب الاسترداد مسجل بالفعل لدى الإدارة.'}); return
                    row['refundRequestedAt']=now; row['refundStatus']='requested'; row['updated']=now; row.setdefault('history',[]).append({'status':status,'at':now,'note':'طلب العميل استرداد المبلغ قبل الشحن'})
                    save_json(ORDERS,{'orders':rows}); add_notification('admin','','finance','طلب استرداد',f'طلب العميل استرداد مبلغ الطلب {number} قبل الشحن.','', '/admin'); append_operation('طلب استرداد من العميل',{'orderId':oid,'orderNumber':number,'participantId':pid},actor='العميل')
                    self.sendj({'ok':True,'message':'تم إرسال طلب الاسترداد إلى الإدارة للمراجعة.'}); return
                self.sendj({'error':'الإجراء المطلوب غير صالح'},400); return

            if p=='/api/visitor/payment-proof':
                pid=str(d.get('participantId') or ''); person=self.require_participant(pid)
                if not person: return
                raw_ids=d.get('orderIds') or []
                if isinstance(raw_ids,str): raw_ids=[raw_ids]
                order_ids=[]
                for oid in raw_ids:
                    oid=str(oid or '').strip()
                    if oid and oid not in order_ids: order_ids.append(oid)
                if not order_ids or len(order_ids)>30: self.sendj({'error':'اختر طلبًا واحدًا على الأقل وبحد أقصى 30 طلبًا في الدفعة'},400); return
                proof_url=str(d.get('proofUrl') or '').strip(); proof_path=urlparse(proof_url).path
                if not proof_path.startswith('/uploads/'):
                    self.sendj({'error':'ارفع صورة إشعار التحويل أولًا'},400); return
                proof_name=os.path.basename(proof_path); proof_file=os.path.join(UPLOAD_DIR,proof_name)
                if not proof_name or not os.path.isfile(proof_file): self.sendj({'error':'ملف إثبات التحويل غير موجود؛ أعد رفع الصورة'},400); return
                reference=' '.join(str(d.get('reference') or '').strip().split())[:100]; note=' '.join(str(d.get('note') or '').strip().split())[:500]
                phone=''.join(ch for ch in str(person.get('phone') or '') if ch.isdigit()); rows=load_orders(); targets=[]; blocked=[]
                for oid in order_ids:
                    row=next((x for x in rows if str(x.get('id') or '')==oid and (str(x.get('participantId') or '')==pid or ''.join(ch for ch in str(x.get('customerPhone') or '') if ch.isdigit())==phone)),None)
                    if not row: blocked.append(oid+' (غير موجود)'); continue
                    status=str(row.get('status') or ''); payment=str(row.get('paymentStatus') or 'unpaid')
                    if payment in ('paid','refunded','proof_submitted') or status not in ('new','awaiting_payment','stalled'):
                        blocked.append(str(row.get('orderNumber') or oid)+' (غير قابل للسداد أو إثباته قيد المراجعة)'); continue
                    if row.get('cancellationRequestedAt'):
                        blocked.append(str(row.get('orderNumber') or oid)+' (طلب إلغاء معلق)'); continue
                    if not bool(row.get('shippingFeeConfirmed')):
                        blocked.append(str(row.get('orderNumber') or oid)+' (الشحن لم يُحدد)'); continue
                    targets.append(row)
                if blocked: self.sendj({'error':'تعذر إرسال إثبات السداد لهذه الطلبات: '+', '.join(blocked[:8])},409); return
                if not targets: self.sendj({'error':'لا توجد طلبات جاهزة للسداد'},409); return
                now=datetime.datetime.now().isoformat(); batch_id='pay-'+secrets.token_hex(6); total=round(sum(float(x.get('total') or 0) for x in targets),2)
                for row in targets:
                    previous={'status':row.get('paymentProofStatus'),'proofUrl':row.get('paymentProofUrl'),'submittedAt':row.get('paymentProofSubmittedAt'),'reference':row.get('paymentReference')}
                    if previous.get('proofUrl'): row.setdefault('paymentProofHistory',[]).append(previous)
                    row['paymentStatus']='proof_submitted'; row['paymentProofStatus']='pending'; row['paymentProofUrl']=proof_url; row['paymentReference']=reference; row['paymentProofNote']=note; row['paymentProofBatchId']=batch_id; row['paymentProofBatchAmount']=total; row['paymentProofSubmittedAt']=now; row['updated']=now
                    row.pop('paymentProofRejectedAt',None); row.pop('paymentProofRejectNote',None)
                    row.setdefault('history',[]).append({'status':str(row.get('status') or 'awaiting_payment'),'at':now,'note':'رفع العميل إثبات تحويل بنكي؛ بانتظار اعتماد الإدارة'})
                save_json(ORDERS,{'orders':rows})
                numbers=', '.join(str(x.get('orderNumber') or x.get('id')) for x in targets[:6])
                if len(targets)>6: numbers+=f' +{len(targets)-6}'
                add_notification('admin','','finance','💳 إثبات سداد جديد',f'رفع {person.get("name") or "عميل"} إثبات تحويل بقيمة {total:g} ر.س لعدد {len(targets)} طلب: {numbers}.','','/admin')
                add_notification('participant',pid,'finance','تم إرسال إثبات السداد',f'تم استلام إثبات التحويل لعدد {len(targets)} طلب بقيمة إجمالية {total:g} ر.س وهو الآن بانتظار اعتماد الإدارة.','','/account')
                append_operation('إرسال إثبات سداد',{'participantId':pid,'batchId':batch_id,'orderIds':[x.get('id') for x in targets],'total':total,'reference':reference},actor='العميل')
                self.sendj({'ok':True,'batchId':batch_id,'count':len(targets),'total':total,'message':'تم إرسال إثبات السداد للإدارة للمراجعة.'}); return

            if p=='/api/notifications/read':
                pid=str(d.get('participantId') or ''); nid=str(d.get('id') or ''); person=next((x for x in load_people() if str(x.get('id'))==pid and x.get('verified') and not x.get('blocked')),None)
                person_session=self.require_participant(pid)
                if not person_session: return
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
            if p=='/api/order/payment-proof':
                action=str(d.get('action') or ''); oid=str(d.get('id') or ''); batch_id=str(d.get('batchId') or ''); note=' '.join(str(d.get('note') or '').strip().split())[:500]
                if action not in ('approve','reject'): self.sendj({'error':'إجراء إثبات السداد غير صالح'},400); return
                rows=load_orders(); targets=[]
                if batch_id:
                    targets=[x for x in rows if str(x.get('paymentProofBatchId') or '')==batch_id and str(x.get('paymentProofStatus') or '')=='pending']
                elif oid:
                    row=next((x for x in rows if str(x.get('id') or '')==oid and str(x.get('paymentProofStatus') or '')=='pending'),None)
                    if row: targets=[row]
                if not targets: self.sendj({'error':'لا يوجد إثبات سداد معلق بهذه البيانات'},404); return
                now=datetime.datetime.now().isoformat(); dues=load_auction_dues(); affected=[]
                if action=='approve':
                    missing=[str(x.get('orderNumber') or x.get('id')) for x in targets if not bool(x.get('shippingFeeConfirmed'))]
                    if missing: self.sendj({'error':'لا يمكن اعتماد السداد قبل اعتماد الشحن للطلبات: '+', '.join(missing[:8])},409); return
                    for row in targets:
                        update_order_status(row,'paid',note or 'اعتمدت الإدارة إثبات التحويل البنكي')
                        row['paymentProofStatus']='approved'; row['paymentProofApprovedAt']=now; row['paymentProofAdminNote']=note; row['updated']=now
                        if row.get('source')=='auction':
                            due=next((x for x in dues if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                            if due: due['status']='paid'; due['paidAt']=now; due['updated']=now
                        add_notification('participant',row.get('participantId'),'finance','✅ تم اعتماد السداد',f'تم اعتماد سداد الطلب {row.get("orderNumber") or row.get("id")}. انتقل الطلب إلى مرحلة تم السداد.','', '/account')
                        affected.append(row.get('id'))
                else:
                    for row in targets:
                        row['paymentStatus']='unpaid'; row['paymentProofStatus']='rejected'; row['paymentProofRejectedAt']=now; row['paymentProofRejectNote']=note or 'تعذر التحقق من إثبات التحويل'; row['updated']=now
                        row.setdefault('history',[]).append({'status':str(row.get('status') or 'awaiting_payment'),'at':now,'note':'رفضت الإدارة إثبات السداد: '+row['paymentProofRejectNote']})
                        add_notification('participant',row.get('participantId'),'finance','⚠️ يلزم إعادة إثبات السداد',f'تعذر اعتماد إثبات سداد الطلب {row.get("orderNumber") or row.get("id")}. '+row['paymentProofRejectNote'],'', '/account')
                        affected.append(row.get('id'))
                save_json(ORDERS,{'orders':rows}); save_json(AUCTION_DUES,{'dues':dues})
                append_operation('معالجة إثبات سداد',{'action':action,'batchId':batch_id,'orderIds':affected,'note':note})
                self.sendj({'ok':True,'action':action,'count':len(affected),'orderIds':affected}); return

            if p=='/api/order/update':
                oid=str(d.get('id') or ''); status=str(d.get('status') or ''); rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==oid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                if row.get('archived') and status not in ('completed','returned'): self.sendj({'error':'الطلب المكتمل مؤرشف ولا يعاد للخلف إلا كمرتجع'},409); return
                if 'shippingCompany' in d: row['shippingCompany']=str(d.get('shippingCompany') or '').strip()
                if 'trackingNumber' in d: row['trackingNumber']=str(d.get('trackingNumber') or '').strip()
                if status=='paid' and not bool(row.get('shippingFeeConfirmed')):
                    self.sendj({'error':'حدد واعتمد مبلغ الشحن أولًا (يمكن اعتماد 0 للشحن المجاني) قبل تأكيد السداد'},409); return
                if status=='cancelled' and str(row.get('paymentStatus') or '')=='paid':
                    self.sendj({'error':'الطلب مسدد؛ استخدم إجراء «تسجيل الاسترداد وإعادة الكمية» بدل الإلغاء المباشر'},409); return
                if status in ('preparing','ready_to_ship','shipped') and str(row.get('paymentStatus') or '')!='paid':
                    self.sendj({'error':'لا يمكن تجهيز أو شحن الطلب قبل تأكيد السداد'},409); return
                if status in ('ready_to_ship','shipped'):
                    addr=row.get('shippingAddress') if isinstance(row.get('shippingAddress'),dict) else {}
                    if not str(addr.get('country') or '').strip() or not str(addr.get('city') or '').strip() or not str(addr.get('addressLine') or '').strip():
                        self.sendj({'error':'أكمل عنوان التسليم في حساب العميل قبل جعل الطلب جاهزًا للشحن'},409); return
                    if not str(row.get('shippingCompany') or '').strip():
                        self.sendj({'error':'حدد شركة الشحن قبل جعل الطلب جاهزًا للشحن'},409); return
                if status=='shipped' and not str(row.get('trackingNumber') or '').strip():
                    self.sendj({'error':'أدخل رقم التتبع أو مرجع الشحنة قبل اعتماد تم الشحن'},409); return
                try: update_order_status(row,status,str(d.get('note') or ''))
                except ValueError as e: self.sendj({'error':str(e)},400); return
                if status=='cancelled':
                    if row.get('source')=='market':
                        requests=load_market_requests(); req=next((x for x in requests if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                        if req: req['status']='cancelled'; req['cancelledAt']=datetime.datetime.now().isoformat(); req['updated']=req['cancelledAt']; save_json(MARKET_REQUESTS,{'requests':requests})
                    elif row.get('source')=='auction':
                        dues=load_auction_dues(); due=next((x for x in dues if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                        if due: due['status']='cancelled'; due['cancelledAt']=datetime.datetime.now().isoformat(); due['updated']=due['cancelledAt']; save_json(AUCTION_DUES,{'dues':dues})
                if status=='paid' and row.get('source')=='auction':
                    dues=load_auction_dues(); due=next((x for x in dues if str(x.get('id'))==str(row.get('sourceId'))),None)
                    if due:
                        due['status']='paid'; due['paidAt']=datetime.datetime.now().isoformat(); due['updated']=due['paidAt']; save_json(AUCTION_DUES,{'dues':dues})
                        add_notification('participant',due.get('participantId'),'finance','✅ تم اعتماد السداد',f"تم اعتماد سداد الطلب {row.get('orderNumber')}. عادت أهلية المشاركة وفق النظام.",due.get('itemId'),'/account')
                save_json(ORDERS,{'orders':rows}); append_operation('تحديث طلب وشحن',{'orderId':oid,'orderNumber':row.get('orderNumber'),'status':status})
                if row.get('participantId'): add_notification('participant',row.get('participantId'),'order','تحديث حالة الطلب',f"الطلب {row.get('orderNumber')} أصبح: {status}",'', '/account')
                self.sendj({'ok':True,'order':row}); return
            if p=='/api/order/request/resolve':
                oid=str(d.get('id') or ''); action=str(d.get('action') or ''); note=str(d.get('note') or '').strip(); rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==oid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                status=str(row.get('status') or ''); payment=str(row.get('paymentStatus') or 'unpaid'); now=datetime.datetime.now().isoformat(); number=row.get('orderNumber') or oid
                if action=='approve_cancel':
                    if not row.get('cancellationRequestedAt') or payment=='paid' or status not in ('new','awaiting_payment','stalled'):
                        self.sendj({'error':'طلب الإلغاء غير صالح للاعتماد في حالته الحالية'},409); return
                    update_order_status(row,'cancelled',note or 'اعتمدت الإدارة طلب الإلغاء؛ أعيدت الكمية إلى المتاح'); row['cancellationStatus']='approved'; row['cancellationResolvedAt']=now
                    if row.get('source')=='auction':
                        dues=load_auction_dues(); due=next((x for x in dues if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                        if due: due['status']='cancelled'; due['cancelledAt']=now; due['updated']=now; save_json(AUCTION_DUES,{'dues':dues})
                elif action=='complete_refund':
                    if payment!='paid' or status not in ('paid','preparing','ready_to_ship'):
                        self.sendj({'error':'طلب الاسترداد غير صالح للاعتماد في حالته الحالية'},409); return
                    update_order_status(row,'cancelled',note or 'اعتمدت الإدارة الاسترداد قبل الشحن؛ أعيدت الكمية إلى المتاح'); row['paymentStatus']='refunded'; row['refundStatus']='completed'; row['refundedAt']=now; row['refundedAmount']=float(row.get('total') or 0)
                    if row.get('source')=='market':
                        requests=load_market_requests(); req=next((x for x in requests if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                        if req: req['status']='refunded'; req['refundedAt']=now; req['updated']=now; save_json(MARKET_REQUESTS,{'requests':requests})
                    elif row.get('source')=='auction':
                        dues=load_auction_dues(); due=next((x for x in dues if str(x.get('id') or '')==str(row.get('sourceId') or '')),None)
                        if due: due['status']='refunded'; due['refundedAt']=now; due['updated']=now; save_json(AUCTION_DUES,{'dues':dues})
                elif action=='reject':
                    if row.get('refundStatus')=='requested': row['refundStatus']='rejected'; row['refundResolvedAt']=now
                    elif row.get('cancellationStatus')=='requested': row['cancellationStatus']='rejected'; row['cancellationResolvedAt']=now
                    else: self.sendj({'error':'لا يوجد طلب إلغاء أو استرداد معلق'},409); return
                    row['updated']=now; row.setdefault('history',[]).append({'status':status,'at':now,'note':note or 'رفضت الإدارة طلب الإلغاء/الاسترداد'})
                else: self.sendj({'error':'إجراء المعالجة غير صالح'},400); return
                save_json(ORDERS,{'orders':rows}); append_operation('معالجة طلب إلغاء/استرداد',{'orderId':oid,'orderNumber':number,'action':action,'note':note})
                add_notification('participant',row.get('participantId'),'finance' if action=='complete_refund' else 'order','تحديث طلب الإلغاء/الاسترداد',f'تمت معالجة الطلب {number}: '+({'approve_cancel':'تم الإلغاء وإعادة الكمية','complete_refund':'تم تسجيل الاسترداد وإعادة الكمية','reject':'تعذر اعتماد الطلب'}).get(action,action),'','/account')
                self.sendj({'ok':True,'order':row}); return
            if p=='/api/order/shipping':
                oid=str(d.get('id') or ''); rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==oid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                row['shippingCompany']=str(d.get('shippingCompany') or '').strip(); row['trackingNumber']=str(d.get('trackingNumber') or '').strip()
                if 'shippingFee' in d:
                    if str(row.get('paymentStatus') or '')=='paid': self.sendj({'error':'لا يمكن تغيير مبلغ الشحن بعد تأكيد السداد'},409); return
                    try: fee=max(0,float(d.get('shippingFee') or 0))
                    except Exception: self.sendj({'error':'مبلغ الشحن غير صالح'},400); return
                    row['shippingFee']=fee; row['shippingFeeConfirmed']=True
                    row['total']=float(row.get('subtotal') or 0)+float(row.get('buyerFee') or 0)+fee
                row['updated']=datetime.datetime.now().isoformat(); save_json(ORDERS,{'orders':rows}); self.sendj({'ok':True,'order':row}); return
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
                person_session=self.require_participant(pid)
                if not person_session: return
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
                row={'id':'m-'+secrets.token_hex(6),'itemId':item_id,'storeType':item_store_type(item),'itemTitle':item.get('marketTitle') or item_title(item),'ownerName':item.get('ownerName') or 'الإدارة / غير محدد','ownerPhone':item.get('ownerPhone') or '','participantId':pid,'marketOfferType':item.get('marketOfferType') or 'single','unitPrice':price,'name':person.get('name',''),'phone':person.get('phone',''),'action':action,'quantity':qty,'selectedSerials':selected,'listedAmount':base,'offeredAmount':offered,'buyerFeePercent':fee_pct,'buyerFeeAmount':fee,'buyerTotal':total,'status':'pending','sourcePage':'special_numbers','images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'reservedUntil':reserve_until.isoformat(),'created':now.isoformat()}
                a=load_market_requests(); a.append(row); save_json(MARKET_REQUESTS,{'requests':a}); add_notification('admin','','market','🛒 طلب من صفحة الأرقام المميزة',f"{person.get('name','عميل')} طلب {item_title(item)}"+((' — الأرقام: '+', '.join(selected)) if selected else f' — الكمية: {qty}'),'','/admin'); add_notification('participant',pid,'order','تم تسجيل طلبك',f"تم حجز اختيارك من {item_title(item)} مؤقتًا وإرسال الطلب للإدارة.",item_id,'/account'); self.sendj({'ok':True,'request':row}); return
            if p=='/api/fantasia/request':
                pid=str(d.get('participantId') or ''); person=next((x for x in load_people() if str(x.get('id'))==pid),None)
                person_session=self.require_participant(pid)
                if not person_session: return
                if not participant_can_transact(person): self.sendj({'error':'الشراء والتفاوض يتطلبان الاعتماد النهائي من الإدارة'},403); return
                item_id=str(d.get('itemId') or ''); action=str(d.get('action') or 'buy'); item=next((i for i in load() if str(i.get('id'))==item_id and i.get('fantasiaEnabled')),None)
                if not item: self.sendj({'error':'المقتنى غير موجود أو لم يعد ضمن قسم فانتازيا'},404); return
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
                row={'id':'m-'+secrets.token_hex(6),'itemId':item_id,'storeType':item_store_type(item),'itemTitle':item.get('marketTitle') or item_title(item),'ownerName':item.get('ownerName') or 'الإدارة / غير محدد','ownerPhone':item.get('ownerPhone') or '','participantId':pid,'marketOfferType':item.get('marketOfferType') or 'single','unitPrice':price,'name':person.get('name',''),'phone':person.get('phone',''),'action':action,'quantity':qty,'selectedSerials':selected,'listedAmount':base,'offeredAmount':offered,'buyerFeePercent':fee_pct,'buyerFeeAmount':fee,'buyerTotal':total,'status':'pending','sourcePage':'fantasia','images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'reservedUntil':reserve_until.isoformat(),'created':now.isoformat()}
                a=load_market_requests(); a.append(row); save_json(MARKET_REQUESTS,{'requests':a}); add_notification('admin','','market','🛒 طلب من قسم فانتازيا',f"{person.get('name','عميل')} طلب {item_title(item)}"+((' — الأرقام: '+', '.join(selected)) if selected else f' — الكمية: {qty}'),'','/admin'); add_notification('participant',pid,'order','تم تسجيل طلبك',f"تم حجز اختيارك من {item_title(item)} مؤقتًا وإرسال الطلب للإدارة.",item_id,'/account'); self.sendj({'ok':True,'request':row}); return
            if p=='/api/market/request':
                item_id=str(d.get('itemId','')); name=str(d.get('name','')).strip(); phone=''.join(ch for ch in str(d.get('phone','')) if ch.isdigit() or ch=='+')
                action=str(d.get('action','buy')); qty=max(1,int(d.get('quantity') or 1)); offered=float(d.get('offeredAmount') or 0)
                pid=str(d.get('participantId') or ''); people=load_people(); person=next((x for x in people if str(x.get('id'))==pid),None) if pid else next((x for x in people if str(x.get('phone') or '').replace(' ','')==phone.replace(' ','')),None)
                person_session=self.require_participant(pid)
                if not person_session: return
                if not participant_can_transact(person): self.sendj({'error':'الشراء والتفاوض يتطلبان تسجيل الحساب ثم الاعتماد النهائي من الإدارة'},403); return
                pid=str(person.get('id')); name=str(person.get('name') or name); phone=str(person.get('phone') or phone)
                item=next((i for i in load() if str(i.get('id'))==item_id and i.get('forMarket') and i.get('marketApproved')),None)
                if not item: self.sendj({'error':'العرض غير متاح في السوق'},404); return
                if not name or len(''.join(ch for ch in phone if ch.isdigit()))<7: self.sendj({'error':'الاسم ورقم الجوال الصحيح مطلوبان'},400); return
                _,_,reserved=item_order_quantities(item.get('id'),item=item); per_unit=market_physical_per_unit(item)
                reserved_units=(reserved.get('market',0)+per_unit-1)//per_unit
                avail=max(0,int(item.get('marketQuantity') or item.get('quantity') or 1)-int(item.get('marketSoldQuantity') or 0)-reserved_units)
                if avail<=0:
                    labels={'new':'طلب جديد','awaiting_payment':'بانتظار السداد','paid':'تم السداد','preparing':'قيد التجهيز','ready_to_ship':'جاهز للشحن','shipped':'تم الشحن','received':'تم الاستلام','stalled':'متعثر'}
                    buyer_phone=''.join(ch for ch in str(phone or '') if ch.isdigit())
                    existing=None
                    for order in load_orders():
                        if str(order.get('status') or '') not in OPEN_ORDER_STATUSES: continue
                        same_buyer=(str(order.get('participantId') or '')==pid)
                        if not same_buyer and buyer_phone:
                            order_phone=''.join(ch for ch in str(order.get('customerPhone') or '') if ch.isdigit())
                            same_buyer=(order_phone==buyer_phone)
                        if same_buyer and any(str(line.get('itemId') or '')==item_id for line in (order.get('items') or [])):
                            existing=order; break
                    if existing:
                        number=existing.get('orderNumber') or existing.get('id') or 'السابق'
                        status=str(existing.get('status') or '')
                        self.sendj({'error':f'هذا المقتنى محجوز بالفعل في طلبك {number}، وحالته: {labels.get(status,status)}. تابعه من «حسابي».','availabilityStatus':'reserved','existingOrderNumber':number},409); return
                    if reserved_units>0:
                        self.sendj({'error':'الكمية المعروضة محجوزة حاليًا في طلب قائم، وليست مفقودة من المقتنيات.','availabilityStatus':'reserved'},409); return
                    self.sendj({'error':'تم بيع الكمية المعروضة ولا توجد وحدة متاحة حاليًا.','availabilityStatus':'sold'},409); return
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
                now=datetime.datetime.now().isoformat(); direct_buy=(action=='buy')
                row={'id':'m-'+secrets.token_hex(6),'itemId':item_id,'storeType':item_store_type(item),'itemTitle':item.get('marketTitle') or ((item.get('country') or '')+' — '+(item.get('denomination') or '')),'ownerName':item.get('ownerName') or 'الإدارة / غير محدد','ownerPhone':item.get('ownerPhone') or '','participantId':pid,'marketOfferType':item.get('marketOfferType') or 'single','unitPrice':unit,'name':name,'phone':phone,'action':action,'quantity':qty,'listedAmount':base,'offeredAmount':offered,'buyerFeePercent':fee_pct,'buyerFeeAmount':round(fee,2),'buyerTotal':round(total,2),'status':'accepted' if direct_buy else 'pending','images':[x for x in [item.get('frontImg'),item.get('backImg'),item.get('gradingCertImage')] if x]+list(item.get('additionalImages') or []),'created':now,'updated':now}
                if direct_buy: row['acceptedAt']=now
                a=load_market_requests(); a.append(row); save_json(MARKET_REQUESTS,{'requests':a})
                if direct_buy:
                    order=create_order_for_market(row); save_json(MARKET_REQUESTS,{'requests':a})
                    add_notification('participant',pid,'order','تم إنشاء طلب الشراء',f"تم تسجيل طلب {row.get('itemTitle') or 'المقتنى'} ويمكن متابعته من مشترياتي وطلباتي.",item_id,'/account')
                chk=next((x for x in load_market_requests() if x.get('id')==row['id']),None)
                if not chk: self.sendj({'error':'تعذر التحقق من تسجيل طلب السوق'},500); return
                self.sendj({'ok':True,'request':chk,'orderId':row.get('orderId')}); return
            if p=='/api/market/request/reset':
                rid=str(d.get('id','')).strip()
                a=load_market_requests(); row=next((x for x in a if str(x.get('id'))==rid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                now=datetime.datetime.now().isoformat()
                previous=str(row.get('status') or '')
                row['archived']=False; row['archivedAt']=''; row['archiveReason']=''
                row['shippingCompany']=''; row['trackingNumber']=''; row['shippedAt']=''
                row['completedAt']=''; row['rejectedAt']=''; row['cancelledAt']=''
                if str(row.get('action') or '')=='buy':
                    row['status']='accepted'; row['acceptedAt']=now
                    order=create_order_for_market(row)
                    if order:
                        orders=load_orders(); target=next((o for o in orders if str(o.get('id'))==str(order.get('id'))),None)
                        if target:
                            target['archived']=False; target['archivedAt']=''; target['archiveReason']=''
                            target['status']='awaiting_payment'; target['paymentStatus']='unpaid'
                            target['shippingCompany']=''; target['trackingNumber']=''; target['updated']=now
                            hist=list(target.get('history') or [])
                            hist.append({'status':'awaiting_payment','at':now,'note':'إعادة الطلب إداريًا إلى بداية مسار الشراء'})
                            target['history']=hist
                            save_json(ORDERS,{'orders':orders})
                else:
                    row['status']='pending'; row['acceptedAt']=''
                    orders=load_orders()
                    target=next((o for o in orders if o.get('source')=='market' and str(o.get('sourceId'))==rid),None)
                    if target:
                        target['archived']=True; target['archivedAt']=now
                        target['archiveReason']='إعادة عرض التفاوض للمراجعة'
                        target['status']='cancelled'; target['updated']=now
                        hist=list(target.get('history') or [])
                        hist.append({'status':'cancelled','at':now,'note':'إعادة طلب التفاوض للمراجعة الإدارية'})
                        target['history']=hist
                        save_json(ORDERS,{'orders':orders})
                row['updated']=now
                save_json(MARKET_REQUESTS,{'requests':a})
                append_operation('إعادة طلب سوق',{'requestId':rid,'previousStatus':previous,'newStatus':row.get('status')},actor='الإدارة')
                self.sendj({'ok':True,'request':row}); return

            if p=='/api/market/request/archive':
                rid=str(d.get('id','')).strip(); reason=str(d.get('reason') or '').strip()
                a=load_market_requests(); row=next((x for x in a if str(x.get('id'))==rid),None)
                if not row: self.sendj({'error':'الطلب غير موجود'},404); return
                now=datetime.datetime.now().isoformat()
                row['archived']=True; row['archivedAt']=now; row['archiveReason']=reason or 'إزالة من قائمة الطلبات النشطة'
                row['updated']=now
                orders=load_orders()
                target=next((o for o in orders if o.get('source')=='market' and str(o.get('sourceId'))==rid),None)
                if target:
                    target['archived']=True; target['archivedAt']=now
                    target['archiveReason']=row['archiveReason']; target['updated']=now
                    hist=list(target.get('history') or [])
                    hist.append({'status':target.get('status') or 'archived','at':now,'note':'أرشفة الطلب إداريًا دون حذف السجل المالي'})
                    target['history']=hist
                    save_json(ORDERS,{'orders':orders})
                save_json(MARKET_REQUESTS,{'requests':a})
                append_operation('أرشفة طلب سوق',{'requestId':rid,'reason':row['archiveReason'],'linkedOrderId':row.get('orderId') or ''},actor='الإدارة')
                self.sendj({'ok':True,'archived':True,'request':row}); return

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
            if p=='/api/auction/return-owner':
                iid=str(d.get('id') or '').strip(); items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'ok':False,'error':'المقتنى غير موجود'},404); return
                if not (item.get('forAuction') or item.get('auctionOutcome') or item.get('auctionApproved')):
                    self.sendj({'ok':False,'error':'المقتنى غير مرتبط بمزاد'},409); return
                now=datetime.datetime.now(); nowiso=now.isoformat(); rnd=int(item.get('auctionRound') or 1)
                outcome=str(item.get('auctionOutcome') or '')
                dues=load_auction_dues(); due=next((x for x in dues if str(x.get('itemId'))==iid and int(x.get('auctionRound') or 1)==rnd and str(x.get('status') or '')!='cancelled'),None)
                orders=load_orders(); order=None
                if due and due.get('orderId'): order=next((x for x in orders if str(x.get('id'))==str(due.get('orderId'))),None)
                if not order and item.get('auctionOrderId'): order=next((x for x in orders if str(x.get('id'))==str(item.get('auctionOrderId'))),None)
                if outcome=='sold':
                    if due and str(due.get('status') or '')=='paid': self.sendj({'ok':False,'error':'تم سداد المزاد؛ استخدم مسار المرتجع/الإلغاء المالي قبل إعادة المقتنى.'},409); return
                    if order:
                        st=str(order.get('status') or '')
                        if order.get('paymentStatus')=='paid' or st in ('paid','preparing','ready_to_ship','shipped','received','completed','returned'):
                            self.sendj({'ok':False,'error':'بدأ السداد أو تنفيذ الطلب؛ لا يمكن إعادة المقتنى مباشرة. استخدم مسار المرتجع/الإلغاء المالي.'},409); return
                    if due:
                        due['status']='cancelled'; due['cancelledAt']=nowiso; due['cancelReason']='إعادة المقتنى إلى صاحبه من إدارة المزادات'; due['updated']=nowiso
                        save_json(AUCTION_DUES,{'dues':dues})
                    if order:
                        order['status']='cancelled'; order['archived']=True; order['archivedAt']=nowiso; order['updated']=nowiso
                        order.setdefault('history',[]).append({'status':'cancelled','at':nowiso,'note':'إلغاء نتيجة المزاد وإعادة المقتنى إلى صاحبه الأصلي'})
                        save_json(ORDERS,{'orders':orders})
                history=list(item.get('auctionHistory') or [])
                history.append({'round':rnd,'event':'returned_to_owner','previousOutcome':outcome,'winnerParticipantId':item.get('auctionWinnerParticipantId'),'winningAmount':item.get('auctionWinningAmount',item.get('auctionCurrentPrice',0)),'at':nowiso,'actor':'admin'})
                item['auctionHistory']=history; item['auctionOutcome']='returned_to_owner'; item['auctionReturnedToOwnerAt']=nowiso
                item['auctionApproved']=False; item['forAuction']=False; item['forMarket']=False; item['marketApproved']=False
                item['adminLocation']='owner'; item['inWarehouse']=False; item['warehouseAvailable']=False; item['storageStatus']='owner_record'; item['locationUpdatedAt']=nowiso; item['updated']=int(now.timestamp()*1000)
                save(items); append_operation('إعادة مقتنى مزاد إلى صاحبه',{'itemId':iid,'auctionRound':rnd,'previousOutcome':outcome,'orderId':order.get('id') if order else '','dueId':due.get('id') if due else ''},actor='الإدارة')
                add_notification('admin','','auction','↩ إعادة مقتنى لصاحبه',f"{item_title(item)} — تم إخراجه من المزاد وإعادته إلى سجل صاحبه مع حفظ سجل الجولة.",iid,'/admin')
                self.sendj({'ok':True,'item':item,'message':'تمت إعادة المقتنى إلى سجل صاحبه الأصلي وحفظ سجل المزاد.'}); return
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
                            add_notification('participant',pid,'auction','⚙️ تم تحديث إعدادات المزاد',msg,iid,store_auction_path(item)); notified.add(pid)
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
                rid=str(d.get('id','')); pid=str(d.get('participantId','')); person=self.require_participant(pid)
                if not person: return
                rows=load_orders(); row=next((x for x in rows if str(x.get('id'))==rid),None); phone=str(person.get('phone') or '').replace(' ','')
                if not row or (str(row.get('participantId') or '')!=pid and str(row.get('customerPhone') or '').replace(' ','')!=phone): self.sendj({'error':'الطلب غير موجود'},404); return
                if row.get('status')!='shipped': self.sendj({'error':'لا يمكن تأكيد الاستلام قبل تسجيل الشحن'},409); return
                update_order_status(row,'received','أكد العميل الاستلام'); save_json(ORDERS,{'orders':rows}); append_operation('تأكيد استلام العميل',{'orderId':rid},actor='العميل')
                self.sendj({'ok':True,'request':row}); return
            if p=='/api/settings':
                st=load_settings()
                for k in ('buyerFeePercent','charityProfitPercent','auctionEntryFee','entryFeeEnabled','negotiationPercents','negotiationHours','adminEmail','platformName','ocrTesseractPath','whatsappVerificationNumber'):
                    if k in d: st[k]=d[k]
                if 'paymentBankName' in d: st['paymentBankName']=str(d.get('paymentBankName') or '').strip()[:120]
                if 'paymentAccountName' in d: st['paymentAccountName']=str(d.get('paymentAccountName') or '').strip()[:160]
                if 'paymentIban' in d: st['paymentIban']=''.join(ch for ch in str(d.get('paymentIban') or '').upper() if ch.isalnum())[:40]
                if 'paymentInstructions' in d: st['paymentInstructions']=str(d.get('paymentInstructions') or '').strip()[:800]
                if 'paymentWhatsapp' in d: st['paymentWhatsapp']=''.join(ch for ch in str(d.get('paymentWhatsapp') or '') if ch.isdigit() or ch=='+')[:24]
                incoming=d.get('visitorSections')
                if isinstance(incoming,dict):
                    current=dict(st.get('visitorSections') or {})
                    for key in ('market','auction','specialNumbers','transitionalIssues','fantasia'):
                        if key in incoming: current[key]=bool(incoming[key])
                    st['visitorSections']=current
                save_json(SETTINGS,st)
                saved=load_settings()
                self.sendj({'ok':True,'settings':saved}); return
            if p=='/api/negotiate':
                item_id=str(d.get('itemId','')); pid=str(d.get('participantId','')); amount=float(d.get('amount') or 0)
                person=self.require_participant(pid)
                if not person: return
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
            if p in ('/api/participant/register','/api/google/link/start','/api/facebook/link/start'):
                google_link=(p=='/api/google/link/start') or bool(d.get('googleLink'))
                facebook_link=(p=='/api/facebook/link/start') or bool(d.get('facebookLink'))
                google_pending=None; facebook_pending=None; gtoken=''; ftoken=''
                if google_link:
                    _oauth_prune(); gtoken=self.cookie_value('NawaderGooglePending'); google_pending=GOOGLE_PENDING_LINKS.get(gtoken) if gtoken else None
                    if not google_pending:
                        self.sendj({'error':'انتهت جلسة ربط Google. اضغط الدخول عبر Google من جديد.'},401); return
                if facebook_link:
                    _oauth_prune(); ftoken=self.cookie_value('NawaderFacebookPending'); facebook_pending=FACEBOOK_PENDING_LINKS.get(ftoken) if ftoken else None
                    if not facebook_pending:
                        self.sendj({'error':'انتهت جلسة ربط Facebook. اضغط الدخول عبر Facebook من جديد.'},401); return
                social_pending=google_pending or facebook_pending or {}
                name=str(social_pending.get('name') or d.get('name','')).strip()[:120]
                reg_country=str(d.get('country','')).strip()[:80]
                raw_phone=str(d.get('phone','')).strip()
                phone=''.join(ch for ch in raw_phone if ch.isdigit() or ch=='+')
                if len(''.join(ch for ch in phone if ch.isdigit())) < 7:
                    self.sendj({'error':'رقم الجوال غير مكتمل'},400); return
                phone_key=_norm_phone(phone)
                people=load_people()
                matches=[x for x in people if _norm_phone(x.get('phone'))==phone_key]
                person=max(matches,key=lambda x:str(x.get('lastSeen') or x.get('created') or '')) if matches else None
                now=datetime.datetime.now(); nowiso=now.isoformat()
                if person and google_pending and person.get('googleSub') and str(person.get('googleSub'))!=str(google_pending.get('sub')):
                    self.sendj({'error':'رقم الجوال مرتبط بحساب Google آخر. تواصل مع الإدارة إذا تغير حسابك.'},409); return
                if person and participant_approval_status(person) in ('stopped','cancelled'):
                    self.sendj({'error':'هذا الحساب موقوف أو ملغى. تواصل مع الإدارة.'},403); return
                if not person:
                    if not name: self.sendj({'error':'اكتب الاسم الكامل لإنشاء الحساب الجديد'},400); return
                    if not reg_country: self.sendj({'error':'اختر دولة الحساب والشحن لإنشاء الحساب الجديد'},400); return
                    person={'id':'p-'+secrets.token_hex(6),'name':name,'phone':phone,'country':reg_country,'approved':False,'verified':False,'blocked':False,'archived':False,'approvalStatus':'new','created':nowiso,'lastSeen':nowiso,'verificationMode':'whatsapp-admin','approvalHistory':[{'status':'new','previousStatus':'new','reason':'إنشاء طلب توثيق عبر واتساب','actor':'النظام','at':nowiso}]}
                    people.append(person)
                else:
                    if name: person['name']=name
                    if reg_country: person['country']=reg_country
                    person['lastSeen']=nowiso
                    person['verificationMode']='whatsapp-admin'
                if google_pending:
                    person['pendingGoogleSub']=google_pending.get('sub','')
                    person['pendingGoogleEmail']=google_pending.get('email','')
                    person['pendingGoogleName']=google_pending.get('name','')
                    person['pendingGooglePicture']=google_pending.get('picture','')
                    person['pendingGoogleRequestedAt']=nowiso
                if facebook_pending:
                    person['pendingFacebookId']=facebook_pending.get('id','')
                    person['pendingFacebookEmail']=facebook_pending.get('email','')
                    person['pendingFacebookName']=facebook_pending.get('name','')
                    person['pendingFacebookPicture']=facebook_pending.get('picture','')
                    person['pendingFacebookRequestedAt']=nowiso

                reqs=[]
                for old_req in list(person.get('whatsappVerificationRequests') or []):
                    try:
                        exp=datetime.datetime.fromisoformat(str(old_req.get('expires') or ''))
                        if exp>now-datetime.timedelta(days=7): reqs.append(old_req)
                    except Exception:
                        pass
                # R9.5B: لا تعِد استخدام طلب واتساب قديم، لأن الخادم لا يخزن token الخام
                # وإنما hash فقط. إعادة الطلب القديم كانت تُرجع requestToken فارغًا للمتصفح،
                # وبذلك يستحيل تسجيل الدخول حتى لو اعتمدت الإدارة الحساب.
                # كل ضغطة «التحقق عبر واتساب» تنشئ طلبًا جديدًا وتلغي أي طلب pending سابق.
                for candidate in reqs:
                    if str(candidate.get('status') or '')=='pending':
                        candidate['status']='superseded'; candidate['supersededAt']=nowiso
                request_id='wv-'+secrets.token_hex(8)
                request_token=secrets.token_urlsafe(24)
                request_code='NW-'+secrets.token_hex(3).upper()
                expires=(now+datetime.timedelta(hours=24)).isoformat()
                reqs.append({'id':request_id,'tokenHash':hashlib.sha256(request_token.encode()).hexdigest(),'code':request_code,'status':'pending','created':nowiso,'expires':expires,'approvedAt':'','rejectedAt':'','consumedAt':'','googleLink':bool(google_pending),'googleSub':(google_pending or {}).get('sub',''),'googleEmail':(google_pending or {}).get('email',''),'facebookLink':bool(facebook_pending),'facebookId':(facebook_pending or {}).get('id',''),'facebookEmail':(facebook_pending or {}).get('email','')})
                person['whatsappVerificationRequests']=reqs[-12:]
                save_json(PEOPLE,{'participants':people})

                st=load_settings()
                wa=''.join(ch for ch in str(st.get('whatsappVerificationNumber') or '966551892409') if ch.isdigit())
                google_line=(f"\nGoogle: {google_pending.get('email','')}" if google_pending else '')
                message=(f"طلب توثيق حساب دار المقتنيات\n"
                         f"الاسم: {person.get('name','')}\n"
                         f"رقم الجوال المسجل: {person.get('phone','')}"
                         f"{google_line}\n"
                         f"رمز الطلب: {request_code}\n"
                         f"أرجو اعتماد التوثيق الكامل لهذا الحساب.")
                whatsapp_url='https://wa.me/'+wa+'?text='+quote(message,safe='')
                append_operation('إنشاء طلب توثيق واتساب',{'participantId':person.get('id'),'requestId':request_id,'requestCode':request_code,'phone':person.get('phone')},actor='العميل')
                add_notification('admin','admin','approval','طلب توثيق حساب عبر واتساب',f"{person.get('name','')} — {person.get('phone','')} — {request_code}",person.get('id'),'/admin')
                self.sendj({'ok':True,'pending':True,'requestId':request_id,'requestToken':request_token,'requestCode':request_code,'expires':expires,'whatsappUrl':whatsapp_url,'whatsappNumber':wa,'message':'تم إنشاء طلب التوثيق. افتح واتساب وأرسل الرسالة الجاهزة ثم انتظر اعتماد الإدارة.'}); return

            if p=='/api/participant/profile':
                pid=str(d.get('id') or '').strip()
                person=self.require_participant(pid)
                if not person: return
                a=load_people(); person=next((x for x in a if str(x.get('id') or '')==str(person.get('id'))),None)
                alias=str(d.get('alias') or '').strip()[:60]
                country=str(d.get('country') or '').strip()[:80]
                avatar=str(d.get('avatarUrl') or '').strip()[:500]
                if avatar and not (avatar.startswith('/uploads/') or avatar.startswith('data:image/')):
                    self.sendj({'error':'مسار صورة الحساب غير صالح'},400); return
                address_in=d.get('shippingAddress') if isinstance(d.get('shippingAddress'),dict) else None
                shipping_address=None
                if address_in is not None:
                    shipping_address={
                        'recipientName':str(address_in.get('recipientName') or person.get('name') or '').strip()[:120],
                        'recipientPhone':str(address_in.get('recipientPhone') or person.get('phone') or '').strip()[:40],
                        'country':str(address_in.get('country') or country or person.get('country') or '').strip()[:80],
                        'city':str(address_in.get('city') or '').strip()[:100],
                        'district':str(address_in.get('district') or '').strip()[:120],
                        'addressLine':str(address_in.get('addressLine') or '').strip()[:240],
                        'postalCode':str(address_in.get('postalCode') or '').strip()[:30],
                        'notes':str(address_in.get('notes') or '').strip()[:240],
                    }
                    if not shipping_address['country'] or not shipping_address['city'] or not shipping_address['addressLine']:
                        self.sendj({'error':'أكمل دولة ومدينة وعنوان التسليم قبل الحفظ'},400); return

                nowiso=datetime.datetime.now().isoformat()
                person['alias']=alias; person['country']=country; person['avatarUrl']=avatar; person['profileUpdatedAt']=nowiso
                if shipping_address is not None: person['shippingAddress']=shipping_address; person['shippingAddressUpdatedAt']=nowiso

                # توحيد الهوية العامة لكل سجلات الحساب القديمة التي تحمل الجوال نفسه.
                phone_key=_norm_phone(person.get('phone'))
                synced=0
                if phone_key:
                    for other in a:
                        if str(other.get('id') or '')==pid: continue
                        if _norm_phone(other.get('phone'))==phone_key:
                            other['alias']=alias; other['country']=country
                            if avatar: other['avatarUrl']=avatar
                            if shipping_address is not None: other['shippingAddress']=shipping_address; other['shippingAddressUpdatedAt']=nowiso
                            other['profileUpdatedAt']=nowiso
                            synced+=1

                save_json(PEOPLE,{'participants':a})
                address_orders_updated=0
                if shipping_address is not None:
                    orders=load_orders()
                    for order in orders:
                        if str(order.get('participantId') or '')!=pid: continue
                        if str(order.get('status') or '') in ('shipped','received','completed','cancelled','returned'): continue
                        order['shippingAddress']=dict(shipping_address); order['updated']=nowiso; address_orders_updated+=1
                    if address_orders_updated: save_json(ORDERS,{'orders':orders})
                append_operation('تحديث هوية الحساب العامة',{'participantId':pid,'country':country,'syncedDuplicateAccounts':synced,'shippingAddressUpdated':shipping_address is not None,'activeOrdersUpdated':address_orders_updated},actor='العميل')
                self.sendj({'ok':True,'participant':participant_public(person),'syncedDuplicateAccounts':synced,'activeOrdersUpdated':address_orders_updated}); return

            if p=='/api/participant/verify':
                request_id=str(d.get('requestId') or '').strip()
                request_token=str(d.get('requestToken') or '').strip()
                if not request_id or not request_token:
                    self.sendj({'error':'بيانات طلب التوثيق غير مكتملة'},400); return
                people=load_people(); person=None; req=None
                token_hash=hashlib.sha256(request_token.encode()).hexdigest()
                for candidate in people:
                    for candidate_req in list(candidate.get('whatsappVerificationRequests') or []):
                        if str(candidate_req.get('id'))==request_id:
                            person=candidate; req=candidate_req; break
                    if req: break
                if not person or not req or not secrets.compare_digest(str(req.get('tokenHash') or ''),token_hash):
                    self.sendj({'error':'طلب التوثيق غير موجود أو غير صالح'},404); return
                try:
                    expired=datetime.datetime.fromisoformat(str(req.get('expires') or '')) < datetime.datetime.now()
                except Exception:
                    expired=True
                status=str(req.get('status') or 'pending')
                if expired and status=='pending':
                    req['status']='expired'; save_json(PEOPLE,{'participants':people})
                    self.sendj({'ok':True,'status':'expired','message':'انتهت صلاحية طلب التوثيق. أنشئ طلبًا جديدًا.'}); return
                if status=='rejected':
                    self.sendj({'ok':True,'status':'rejected','message':'تم رفض طلب التوثيق. راجع البيانات وتواصل مع الإدارة.'}); return
                if status=='consumed':
                    self.sendj({'ok':True,'status':'consumed','message':'تم استخدام طلب التوثيق سابقًا. إذا لم يظهر حسابك فأعد فتح صفحة حسابي.'}); return
                if status!='approved':
                    self.sendj({'ok':True,'status':'pending','requestCode':req.get('code'),'message':'بانتظار اعتماد الإدارة بعد مطابقة رسالة واتساب.'}); return
                if participant_approval_status(person)!='final':
                    self.sendj({'error':'لم يكتمل التوثيق الكامل للحساب بعد'},403); return
                req['status']='consumed'; req['consumedAt']=datetime.datetime.now().isoformat()
                if req.get('googleLink'):
                    req_sub=str(req.get('googleSub') or person.get('pendingGoogleSub') or '')
                    if req_sub:
                        conflict=next((x for x in people if str(x.get('id'))!=str(person.get('id')) and str(x.get('googleSub') or '')==req_sub),None)
                        if conflict:
                            self.sendj({'error':'حساب Google مرتبط مسبقًا بحساب آخر. تواصل مع الإدارة.'},409); return
                        person['googleSub']=req_sub
                        person['googleEmail']=str(req.get('googleEmail') or person.get('pendingGoogleEmail') or '')[:240]
                        person['googleName']=str(person.get('pendingGoogleName') or person.get('name') or '')[:120]
                        person['googlePicture']=str(person.get('pendingGooglePicture') or '')[:500]
                        person['googleLinkedAt']=datetime.datetime.now().isoformat()
                    for k in ('pendingGoogleSub','pendingGoogleEmail','pendingGoogleName','pendingGooglePicture','pendingGoogleRequestedAt'):
                        person.pop(k,None)
                if req.get('facebookLink'):
                    req_fid=str(req.get('facebookId') or person.get('pendingFacebookId') or '').strip()
                    conflict=next((x for x in people if req_fid and str(x.get('facebookId') or '')==req_fid and str(x.get('id'))!=str(person.get('id'))),None)
                    if not conflict and req_fid:
                        person['facebookId']=req_fid
                        person['facebookEmail']=str(req.get('facebookEmail') or person.get('pendingFacebookEmail') or '')[:240]
                        person['facebookName']=str(person.get('pendingFacebookName') or person.get('name') or '')[:120]
                        person['facebookPicture']=str(person.get('pendingFacebookPicture') or '')[:500]
                        person['facebookLinkedAt']=datetime.datetime.now().isoformat()
                    for k in ('pendingFacebookId','pendingFacebookEmail','pendingFacebookName','pendingFacebookPicture','pendingFacebookRequestedAt'):
                        person.pop(k,None)
                save_json(PEOPLE,{'participants':people})
                self.sendj_participant({'ok':True,'status':'approved','verified':True,'approved':True,'participant':participant_public(person),'message':'تم التوثيق الكامل وتسجيل الدخول بنجاح.'},person); return

            if p=='/api/participant/reset-pin':
                self.sendj({'error':'تم إلغاء رمز الدخول. تسجيل العملاء يتم عبر توثيق واتساب واعتماد الإدارة.'},410); return

            if p=='/api/moderation/item':
                iid=str(d.get('itemId') or ''); status=str(d.get('status') or '').strip().lower(); reason=str(d.get('reason') or '').strip()
                if status=='removed': self.sendj({'error':'الإزالة النهائية تتم من الأرشيف فقط'},409); return
                if status not in ('active','hidden','suspended','archived'):
                    self.sendj({'error':'حالة المراقبة غير صالحة'},400); return
                if status!='active' and not reason:
                    self.sendj({'error':'سبب الإجراء إلزامي عند الإخفاء أو الإيقاف أو الأرشفة أو الإزالة'},400); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                previous=moderation_status(item)
                item['moderationStatus']=status
                item['moderationReason']=reason
                item['moderationUpdatedAt']=datetime.datetime.now().isoformat()
                item['updated']=int(time.time()*1000)
                save(items)
                append_operation('تحديث مراقبة مقتنى',{'itemId':iid,'previous':previous,'status':status,'reason':reason},actor='الإدارة')
                pid=str(item.get('ownerParticipantId') or '')
                if pid:
                    labels={'active':'إعادة تفعيل','hidden':'إخفاء','suspended':'إيقاف','archived':'أرشفة'}
                    add_notification('participant',pid,'moderation',f"إجراء إداري: {labels.get(status,status)}",f"{item.get('country','')} — {item.get('denomination','')}. {reason}".strip(),iid,'/account')
                self.sendj({'ok':True,'itemId':iid,'status':status,'previous':previous}); return

            if p=='/api/archive/item':
                iid=str(d.get('itemId') or ''); reason=str(d.get('reason') or '').strip()
                if not reason: self.sendj({'error':'سبب الحذف/الأرشفة إلزامي'},400); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                previous=moderation_status(item); archive_item_record(item,reason,'الإدارة'); save(items)
                append_operation('نقل مقتنى إلى الأرشيف',{'itemId':iid,'previous':previous,'reason':reason},actor='الإدارة')
                pid=str(item.get('ownerParticipantId') or '')
                if pid: add_notification('participant',pid,'moderation','تم نقل المقتنى إلى الأرشيف',f"{item.get('country','')} — {item.get('denomination','')}. السبب: {reason}",iid,'/account')
                self.sendj({'ok':True,'archived':True,'itemId':iid}); return

            if p=='/api/archive/restore':
                iid=str(d.get('itemId') or '')
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                if moderation_status(item) not in ('archived','removed') and not item.get('ownerArchived'):
                    self.sendj({'error':'المقتنى ليس في الأرشيف'},409); return
                result=restore_archived_item(item,'الإدارة'); save(items)
                append_operation('استعادة مقتنى من الأرشيف',{'itemId':iid,'warning':result.get('warning','')},actor='الإدارة')
                self.sendj({'ok':True,'restored':True,'warning':result.get('warning','')}); return

            if p=='/api/archive/purge':
                iid=str(d.get('itemId') or ''); confirm_text=str(d.get('confirmText') or '').strip(); reason=str(d.get('reason') or '').strip()
                if confirm_text!='إزالة نهائية': self.sendj({'error':'اكتب «إزالة نهائية» للتأكيد'},400); return
                if not reason: self.sendj({'error':'سبب الإزالة النهائية إلزامي'},400); return
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                if moderation_status(item) not in ('archived','removed') and not item.get('ownerArchived'):
                    self.sendj({'error':'الإزالة النهائية مسموحة من الأرشيف فقط'},409); return
                order_refs=sum(1 for o in load_orders() if any(str(line.get('itemId'))==iid for line in (o.get('items') or [])))
                bid_refs=sum(1 for b in load_bids() if str(b.get('itemId'))==iid)
                market_refs=sum(1 for r in load_market_requests() if str(r.get('itemId'))==iid)
                tomb={'itemId':iid,'country':item.get('country',''),'denomination':item.get('denomination',''),'serial':item.get('serial',''),'ownerParticipantId':item.get('ownerParticipantId',''),'orderRefs':order_refs,'bidRefs':bid_refs,'marketRefs':market_refs,'reason':reason}
                items=[x for x in items if str(x.get('id'))!=iid]; save(items)
                rows=load_collectible_submissions(); changed=False
                for row in rows:
                    if str(row.get('itemId') or '')==iid:
                        row['purgedItemId']=iid; row['itemId']=''; row['status']='purged'; row['warehouseVerified']=False; row['purgedAt']=datetime.datetime.now().isoformat(); row['adminNote']=((str(row.get('adminNote') or '')+' تمت إزالة المقتنى نهائيًا من الأرشيف.').strip()); changed=True
                if changed: save_json(COLLECTIBLE_SUBMISSIONS,{'submissions':rows})
                append_operation('إزالة مقتنى نهائيًا من الأرشيف',tomb,actor='الإدارة')
                self.sendj({'ok':True,'purged':True,'itemId':iid,'historyPreserved':{'orders':order_refs,'bids':bid_refs,'marketRequests':market_refs}}); return

            if p=='/api/participant/whatsapp-decision':
                pid=str(d.get('id') or '').strip()
                request_id=str(d.get('requestId') or '').strip()
                action=str(d.get('action') or '').strip().lower()
                if action not in ('approve','reject'):
                    self.sendj({'error':'قرار التوثيق غير صالح'},400); return
                people=load_people()
                requested_person=next((x for x in people if str(x.get('id'))==pid),None)
                # R9.5A: قد يكون الطلب محفوظًا على حساب قديم/مكرر يحمل الجوال نفسه.
                # ابحث عن requestId على مستوى جميع الحسابات بدل تقييده بالسجل المضغوط عليه.
                person=None; req=None
                for candidate in people:
                    candidate_req=next((x for x in reversed(list(candidate.get('whatsappVerificationRequests') or [])) if str(x.get('id'))==request_id),None)
                    if candidate_req:
                        person=candidate; req=candidate_req; break
                if not person and requested_person:
                    person=requested_person
                if not person: self.sendj({'error':'الحساب غير موجود'},404); return
                if not req: self.sendj({'error':'طلب واتساب غير موجود لهذا الرقم. أنشئ طلبًا جديدًا من صفحة حسابي.'},404); return
                if str(req.get('status'))!='pending':
                    self.sendj({'error':'طلب التوثيق حُسم سابقًا أو انتهت صلاحيته'},409); return
                nowiso=datetime.datetime.now().isoformat()
                phone_key=_norm_phone(person.get('phone') or (requested_person or {}).get('phone'))
                same_phone=[x for x in people if phone_key and _norm_phone(x.get('phone'))==phone_key]
                if not same_phone: same_phone=[person]
                if action=='reject':
                    req['status']='rejected'; req['rejectedAt']=nowiso
                    save_json(PEOPLE,{'participants':people})
                    append_operation('رفض طلب توثيق واتساب',{'participantId':person.get('id'),'requestedParticipantId':pid,'requestId':request_id,'requestCode':req.get('code'),'matchedAccounts':len(same_phone)},actor='الإدارة')
                    self.sendj({'ok':True,'status':'rejected'}); return
                req['status']='approved'; req['approvedAt']=nowiso
                approved_ids=[]
                for target in same_phone:
                    # لا نلغي قرار إيقاف/إلغاء إداري سابق على نسخة قديمة.
                    if participant_approval_status(target) in ('stopped','cancelled'):
                        continue
                    previous=participant_approval_status(target)
                    apply_approval_status(target,'final')
                    target['verified']=True; target['approved']=True
                    target['verifiedAt']=target.get('verifiedAt') or nowiso; target['approvedAt']=nowiso; target['finalApprovedAt']=nowiso
                    history=list(target.get('approvalHistory') or [])
                    history.append({'status':'final','previousStatus':previous,'reason':'توثيق كامل بعد مطابقة طلب واتساب لنفس رقم الجوال','actor':'الإدارة','at':nowiso})
                    target['approvalHistory']=history[-200:]
                    approved_ids.append(str(target.get('id') or ''))
                save_json(PEOPLE,{'participants':people})
                append_operation('اعتماد توثيق واتساب',{'participantId':person.get('id'),'requestedParticipantId':pid,'requestId':request_id,'requestCode':req.get('code'),'approvedDuplicateIds':approved_ids},actor='الإدارة')
                for approved_id in approved_ids:
                    add_notification('participant',approved_id,'approval','✅ تم التوثيق الكامل','تم اعتماد حسابك عبر واتساب. ستسجل صفحة حسابي دخولك تلقائيًا.',approved_id,'/account')
                self.sendj({'ok':True,'status':'approved','participant':participant_public(person),'approvedDuplicateIds':approved_ids}); return

            if p=='/api/participant/approval-status':
                a=load_people(); iid=str(d.get('id') or ''); status=str(d.get('status') or '').strip().lower(); reason=str(d.get('reason') or '').strip()
                if status not in APPROVAL_STATUSES or status=='new': self.sendj({'error':'حالة التوثيق غير صالحة'},400); return
                if status in ('suspended','stopped','cancelled') and not reason: self.sendj({'error':'كتابة السبب إلزامية لهذا القرار'},400); return
                person=next((x for x in a if str(x.get('id'))==iid),None)
                if not person: self.sendj({'error':'المشارك غير موجود'},404); return
                if status=='final' and participant_approval_status(person)=='new':
                    # R9.5B: زر «توثيق كامل» القديم في الإدارة يجب أن يعتمد أحدث طلب واتساب
                    # بدل أن يفشل، حتى لو لم تُحدّث واجهة الإدارة أو كان الطلب على سجل مكرر للجوال.
                    phone_key=_norm_phone(person.get('phone'))
                    same_phone=[x for x in a if phone_key and _norm_phone(x.get('phone'))==phone_key] or [person]
                    now_dt=datetime.datetime.now(); pending_owner=None; pending_req=None
                    for candidate in same_phone:
                        for candidate_req in reversed(list(candidate.get('whatsappVerificationRequests') or [])):
                            if str(candidate_req.get('status') or '')!='pending': continue
                            try:
                                if datetime.datetime.fromisoformat(str(candidate_req.get('expires') or '')) <= now_dt: continue
                            except Exception:
                                pass
                            if not pending_req or str(candidate_req.get('created') or '') > str(pending_req.get('created') or ''):
                                pending_owner=candidate; pending_req=candidate_req
                            break
                    if not pending_req:
                        self.sendj({'error':'لا يوجد طلب واتساب معلّق لهذا الجوال. أنشئ طلبًا جديدًا من صفحة حسابي ثم أعد التوثيق الكامل.'},409); return
                    nowiso=datetime.datetime.now().isoformat(); pending_req['status']='approved'; pending_req['approvedAt']=nowiso
                    approved_ids=[]
                    for target in same_phone:
                        if participant_approval_status(target) in ('stopped','cancelled'): continue
                        previous_target=participant_approval_status(target); apply_approval_status(target,'final')
                        target['verified']=True; target['approved']=True; target['verifiedAt']=target.get('verifiedAt') or nowiso; target['approvedAt']=nowiso; target['finalApprovedAt']=nowiso
                        history=target.get('approvalHistory') if isinstance(target.get('approvalHistory'),list) else []
                        history.append({'status':'final','previousStatus':previous_target,'reason':'توثيق كامل واعتماد أحدث طلب واتساب','actor':'الإدارة','at':nowiso}); target['approvalHistory']=history[-200:]
                        approved_ids.append(str(target.get('id') or ''))
                    save_json(PEOPLE,{'participants':a})
                    append_operation('اعتماد توثيق واتساب من زر التوثيق الكامل',{'participantId':iid,'requestId':pending_req.get('id'),'requestCode':pending_req.get('code'),'approvedDuplicateIds':approved_ids},actor='الإدارة')
                    for approved_id in approved_ids:
                        add_notification('participant',approved_id,'approval','✅ تم التوثيق الكامل','تم اعتماد أحدث طلب واتساب. ارجع إلى صفحة حسابي واضغط «تحقق من الاعتماد الآن».',approved_id,'/account')
                    self.sendj({'ok':True,'participant':participant_public(person),'whatsappApproved':True,'requestId':pending_req.get('id'),'approvedDuplicateIds':approved_ids}); return
                previous=participant_approval_status(person)
                if previous=='cancelled': self.sendj({'error':'الإلغاء نهائي ولا يمكن إعادة تفعيل الحساب'},409); return
                nowiso=datetime.datetime.now().isoformat(); apply_approval_status(person,status); person['approvalUpdatedAt']=nowiso; person['approvalUpdatedBy']='الإدارة'
                if status=='final': person['approvedAt']=nowiso; person['finalApprovedAt']=nowiso
                if status=='cancelled': person['archivedAt']=nowiso; person['archiveReason']=reason
                history=person.get('approvalHistory') if isinstance(person.get('approvalHistory'),list) else []; history.append({'status':status,'previousStatus':previous,'reason':reason or 'قرار اعتماد إداري','actor':'الإدارة','at':nowiso}); person['approvalHistory']=history[-200:]
                save_json(PEOPLE,{'participants':a}); messages={'final':'تم توثيق حسابك بالكامل، ويمكنك استخدام خدمات المزاد والسوق وفق الأنظمة.','suspended':'تم تعليق حسابك مؤقتًا. يمكنك الدخول والتصفح، بينما أوقفت العمليات حتى المراجعة.','stopped':'تم إيقاف حسابك وعملياته. تواصل مع الإدارة للمراجعة.','cancelled':'تم إلغاء الحساب نهائيًا. تواصل مع الإدارة عند الحاجة.'}
                add_notification('participant',iid,'approval','تحديث حالة الاعتماد: '+APPROVAL_LABELS[status],messages[status],'','/account'); append_operation('تغيير حالة اعتماد مشارك',{'participantId':iid,'previousStatus':previous,'status':status,'statusLabel':APPROVAL_LABELS[status],'reason':reason},actor='الإدارة')
                self.sendj({'ok':True,'participant':participant_public(person)}); return
            if p=='/api/participant/approve':
                self.sendj({'error':'تم إيقاف مسار الاعتماد القديم؛ استخدم التوثيق الكامل أو التعليق/الإيقاف.'},410); return
            if p=='/api/participant/restore':
                self.sendj({'error':'تم إلغاء مسار الاستعادة القديم؛ استخدم حالات الحساب الحالية.'},410); return
            if p=='/api/participant/delete':
                self.sendj({'error':'الحذف النهائي معطّل لحماية سجل المستخدم والمزايدات والطلبات والمستحقات'},409); return
            if p=='/api/bid':
                itemId=d.get('itemId'); pid=str(d.get('participantId') or ''); amount=float(d.get('amount') or 0)
                person=self.require_participant(pid)
                if not person: return
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
                        if end<=auction_local_now(): self.sendj({'error':'انتهى المزاد'},409); return
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
                add_notification('participant',pid,'auction','✅ تم تسجيل مزايدتك',f"تم قبول مزايدتك على {title} بقيمة {amount:g} ر.س.",itemId,store_auction_path(item))
                if previous_top and str(previous_top.get('participantId'))!=str(pid):
                    add_notification('participant',previous_top.get('participantId'),'auction','⚡ تمت المزايدة عليك',f"مزايدتك لم تعد الأعلى في {title}. السعر الحالي {amount:g} ر.س، ويمكنك العودة للمزاد والزيادة.",itemId,store_auction_path(item))
                items=load();
                for i in items:
                    if i.get('id')==itemId: i['auctionCurrentPrice']=amount; i['updated']=int(datetime.datetime.now().timestamp()*1000)
                save(items); self.sendj({'ok':True,'current':amount}); return
            items=load()
            if p=='/api/item':
                x=d.get('item',{}) if isinstance(d,dict) else {}
                iid=str(x.get('id') or '').strip()
                old_item=next((i for i in items if str(i.get('id'))==iid),None) if iid else None
                x['storeType']=normalize_store_type(x.get('storeType'),old_item or x)
                x['collectibleCategory']=str(x.get('collectibleCategory') or '').strip().lower()
                country=str(x.get('country') or '').strip()
                denom=str(x.get('denomination') or '').strip()

                # R3: متطلبات الحفظ تختلف بين المتجرين.
                # العملات تحتاج دولة + فئة، أما المقتنيات فتحتاج تصنيف + اسم،
                # وبلد المنشأ اختياري ويُحفظ كـ «غير محدد» عند تركه فارغًا.
                if not iid:
                    self.sendj({'ok':False,'error':'تعذر الحفظ: رقم السجل غير موجود'},400); return
                if x.get('storeType')=='collectibles':
                    if not x.get('collectibleCategory'):
                        self.sendj({'ok':False,'error':'اختر تصنيف نوادر المقتنيات'},400); return
                    if not denom:
                        self.sendj({'ok':False,'error':'اكتب اسم المقتنى'},400); return
                    if not country:
                        country='غير محدد'; x['country']=country
                else:
                    if not country:
                        self.sendj({'ok':False,'error':'اختر الدولة للعملة'},400); return
                    if not denom:
                        self.sendj({'ok':False,'error':'اكتب الفئة / القيمة للعملة'},400); return
                if x.get('fantasiaEnabled') or x.get('collectibleCategory')=='fantasia':
                    x['storeType']='collectibles'
                    if x.get('collectibleCategory')=='fantasia': x['fantasiaEnabled']=True
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
                        self.sendj({'ok':False,'error':'نشر المزاد يتطلب تاريخ ووقت انتهاء'},400); return
                    try:
                        end_dt=datetime.datetime.fromisoformat(end)
                        old_was_approved=bool(old_item and old_item.get('forAuction') and old_item.get('auctionApproved'))
                        end_changed=str((old_item or {}).get('auctionEnd') or '').strip()!=end
                        needs_fresh_schedule=not old_was_approved or end_changed
                        if needs_fresh_schedule and end_dt <= auction_local_now():
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
                items=load(); item=next((x for x in items if str(x.get('id'))==iid),None)
                if not item: self.sendj({'error':'المقتنى غير موجود'},404); return
                archive_item_record(item,'حذف من واجهة الإدارة','الإدارة'); save(items)
                append_operation('نقل مقتنى إلى الأرشيف عبر زر الحذف',{'itemId':iid},actor='الإدارة')
            self.sendj({'ok':True,'archived':True}); return
        self.sendj({'error':'not found'},404)

os.chdir(ROOT); backup_data('startup')
# تشغيل آمن: تأكد من وجود ملفات الواجهات الأساسية قبل بدء الخدمة.
_required_runtime_files=[
    os.path.join(ADMIN_DIR,'index.html'), os.path.join(ADMIN_DIR,'app.js'), os.path.join(ADMIN_DIR,'styles.css'),
    os.path.join(PUBLIC_DIR,'public_home.html'), os.path.join(PUBLIC_DIR,'dar_home.html'), os.path.join(PUBLIC_DIR,'collectibles_home.html'), os.path.join(PUBLIC_DIR,'public_auction.html'), os.path.join(PUBLIC_DIR,'public_market.html')
]
_missing_runtime=[p for p in _required_runtime_files if not os.path.isfile(p)]
if _missing_runtime:
    # R9.2A SAFE LOAD:
    # لا نوقف الخادم بالكامل أثناء التركيب الجزئي. بعض ملفات الواجهة قد تُرفع
    # في المرحلة التالية مباشرة، لذلك نكتفي بتحذير واضح في السجل.
    print('Startup warning - missing UI files:', ', '.join(os.path.relpath(p,ROOT) for p in _missing_runtime))
ensure_dues_tracking_start()
_auth_cfg,_new_admin_password=ensure_admin_auth()
VERSION='5.6.2-R9.5F-DATA-ENTRY-DEVICE-SESSION'
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
