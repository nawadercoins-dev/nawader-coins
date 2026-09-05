from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'server.py'
MARKER = '# V4.9.1 FACEBOOK OAUTH — unified Facebook/Google/WhatsApp entry.'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


server = SERVER.read_text(encoding='utf-8')

if MARKER not in server:
    old = "GOOGLE_FLOW_TTL_SECONDS=10*60\nAUTH_FILE=os.path.join(DATA_ROOT,'admin_auth.json')"
    new = """GOOGLE_FLOW_TTL_SECONDS=10*60
# V4.9.1 FACEBOOK OAUTH — unified Facebook/Google/WhatsApp entry.
# Secrets stay in Render environment variables; privileged roles stay server-side.
FACEBOOK_APP_ID=str(os.environ.get('FACEBOOK_APP_ID') or '').strip()
FACEBOOK_APP_SECRET=str(os.environ.get('FACEBOOK_APP_SECRET') or '').strip()
FACEBOOK_REDIRECT_URI=str(os.environ.get('FACEBOOK_REDIRECT_URI') or '').strip()
FACEBOOK_OAUTH_STATES={}
FACEBOOK_PENDING_LINKS={}
FACEBOOK_STATE_TTL_SECONDS=10*60
FACEBOOK_PENDING_TTL_SECONDS=24*60*60
AUTH_FILE=os.path.join(DATA_ROOT,'admin_auth.json')"""
    server = replace_once(server, old, new, 'facebook env config')

    old = """def _oauth_prune():
    now=time.time()
    for bag in (GOOGLE_OAUTH_STATES,GOOGLE_PENDING_LINKS):
        for key,val in list(bag.items()):
            if now-float(val.get('created') or 0)>GOOGLE_FLOW_TTL_SECONDS:
                bag.pop(key,None)"""
    new = """def _oauth_prune():
    now=time.time()
    for bag,ttl in ((GOOGLE_OAUTH_STATES,GOOGLE_FLOW_TTL_SECONDS),(GOOGLE_PENDING_LINKS,GOOGLE_FLOW_TTL_SECONDS),(FACEBOOK_OAUTH_STATES,FACEBOOK_STATE_TTL_SECONDS),(FACEBOOK_PENDING_LINKS,FACEBOOK_PENDING_TTL_SECONDS)):
        for key,val in list(bag.items()):
            if now-float(val.get('created') or 0)>ttl:
                bag.pop(key,None)"""
    server = replace_once(server, old, new, 'oauth prune')

    old = """def _google_public_profile(p):
    return {'name':p.get('name',''),'email':p.get('email',''),'picture':p.get('picture','')}

ADMIN_GET_API={"""
    new = """def _google_public_profile(p):
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

ADMIN_GET_API={"""
    server = replace_once(server, old, new, 'facebook helpers')

    server = replace_once(
        server,
        "'/api/participant/register','/api/participant/verify','/api/google/link/start','/api/participant/profile'",
        "'/api/participant/register','/api/participant/verify','/api/google/link/start','/api/facebook/link/start','/api/participant/profile'",
        'public facebook post api',
    )

    old = """    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/google/status':"""
    new = """    def do_GET(self):
        p=urlparse(self.path).path
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
        if p=='/api/google/status':"""
    server = replace_once(server, old, new, 'facebook GET routes')

    server = replace_once(
        server,
        "self.send_header('Location','/account?google=link-phone'); self.end_headers(); return",
        "self.send_header('Location','/account?google=link-phone&next='+quote(_safe_next_path(flow.get('next')),safe='')); self.end_headers(); return",
        'google next preservation',
    )

    old = """            if p in ('/api/participant/register','/api/google/link/start'):
                google_link=(p=='/api/google/link/start') or bool(d.get('googleLink'))
                google_pending=None
                if google_link:
                    _oauth_prune(); gtoken=self.cookie_value('NawaderGooglePending'); google_pending=GOOGLE_PENDING_LINKS.get(gtoken) if gtoken else None
                    if not google_pending:
                        self.sendj({'error':'انتهت جلسة ربط Google. اضغط الدخول عبر Google من جديد.'},401); return
                name=str((google_pending or {}).get('name') or d.get('name','')).strip()[:120]"""
    new = """            if p in ('/api/participant/register','/api/google/link/start','/api/facebook/link/start'):
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
                name=str(social_pending.get('name') or d.get('name','')).strip()[:120]"""
    server = replace_once(server, old, new, 'social registration head')

    old = """                if google_pending:
                    person['pendingGoogleSub']=google_pending.get('sub','')
                    person['pendingGoogleEmail']=google_pending.get('email','')
                    person['pendingGoogleName']=google_pending.get('name','')
                    person['pendingGooglePicture']=google_pending.get('picture','')
                    person['pendingGoogleRequestedAt']=nowiso

                reqs=[]"""
    new = """                if google_pending:
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

                reqs=[]"""
    server = replace_once(server, old, new, 'pending facebook fields')

    old = """reqs.append({'id':request_id,'tokenHash':hashlib.sha256(request_token.encode()).hexdigest(),'code':request_code,'status':'pending','created':nowiso,'expires':expires,'approvedAt':'','rejectedAt':'','consumedAt':'','googleLink':bool(google_pending),'googleSub':(google_pending or {}).get('sub',''),'googleEmail':(google_pending or {}).get('email','')})"""
    new = """reqs.append({'id':request_id,'tokenHash':hashlib.sha256(request_token.encode()).hexdigest(),'code':request_code,'status':'pending','created':nowiso,'expires':expires,'approvedAt':'','rejectedAt':'','consumedAt':'','googleLink':bool(google_pending),'googleSub':(google_pending or {}).get('sub',''),'googleEmail':(google_pending or {}).get('email',''),'facebookLink':bool(facebook_pending),'facebookId':(facebook_pending or {}).get('id',''),'facebookEmail':(facebook_pending or {}).get('email','')})"""
    server = replace_once(server, old, new, 'facebook verification request')

    old = """                    for k in ('pendingGoogleSub','pendingGoogleEmail','pendingGoogleName','pendingGooglePicture','pendingGoogleRequestedAt'):
                        person.pop(k,None)
                save_json(PEOPLE,{'participants':people})"""
    new = """                    for k in ('pendingGoogleSub','pendingGoogleEmail','pendingGoogleName','pendingGooglePicture','pendingGoogleRequestedAt'):
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
                save_json(PEOPLE,{'participants':people})"""
    server = replace_once(server, old, new, 'facebook verification finalize')


SERVER.write_text(server, encoding='utf-8')
print('Facebook server patch applied successfully.')
