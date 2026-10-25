#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, hashlib, html, json, os, re, signal, subprocess, sys, threading, time, urllib.parse
from collections import OrderedDict
import tempfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION='6.3.0-dev.5'
MIN_PY=(3,7)
if sys.version_info < MIN_PY:
    raise SystemExit('CodexView requires Python >= 3.7; current: %s' % sys.version.split()[0])
DEFAULT_PORT=17864
EXPORT_RE=re.compile(r'^codex-session-([0-9a-fA-F-]{20,})-(20\d{2})-(\d{4})-(\d{4,6})\.md$')
ROLE_RE=re.compile(br'^## (User|Assistant|Activity|Reasoning)\s*$')
NATIVE_RE=re.compile(r'^rollout-.+-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.jsonl$')
FENCE_RE=re.compile(br'^\s*(`{3,}|~{3,})')

def dt(ts): return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
def norm(s): return '\n'.join(re.sub(r'\s+',' ',x.strip()) for x in s.replace('\r','').splitlines() if x.strip())
def safe(s): return re.sub(r'[^A-Za-z0-9_.-]+','_',s)
def atomic(path,obj):
    owner=next((p for p in path.parents if p.name=='codexview'),None)
    if owner is None or owner.resolve()!=owner or path.parent.resolve()!=path.parent or path.is_symlink():
        raise ValueError('Refusing redirected or non-CodexView write: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,separators=(',',':'))
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def owned_open(path,append=False):
    """Open only our own runtime files; refuse redirected write targets."""
    owner=next((p for p in path.parents if p.name=='codexview'),None)
    if owner is None or owner.resolve()!=owner or path.parent.resolve()!=path.parent or path.is_symlink():
        raise ValueError('Refusing redirected or non-CodexView write: '+str(path))
    flags=os.O_WRONLY|os.O_CREAT|(os.O_APPEND if append else os.O_TRUNC)|getattr(os,'O_NOFOLLOW',0)
    return os.fdopen(os.open(path,flags,0o600),'a' if append else 'w',encoding='utf-8')

def codex_home(explicit=None):
    if explicit: return Path(explicit).expanduser().resolve()
    if os.environ.get('CODEX_HOME'): return Path(os.environ['CODEX_HOME']).expanduser().resolve()
    return (Path.home()/'.codex').resolve()
def runtime(home):
    b=home/'codexview'; return {k:v for k,v in {
      'base':b,'state':b/'state','index':b/'index','logs':b/'logs','run':b/'run','exports':b/'exports',
      'log':b/'logs'/'codexview.log','pid':b/'run'/'codexview.pid','config':b/'config.json'}.items()}
def ensure_rt(r):
    for k in ('base','state','index','logs','run','exports'):
        if r[k].resolve()!=r[k]:raise ValueError('Refusing redirected write directory: '+str(r[k]))
        r[k].mkdir(parents=True,exist_ok=True)
def rotate_log(r,max_bytes,backups):
    p=r['log']
    try:
        if p.stat().st_size < max_bytes:return
    except FileNotFoundError:return
    for i in range(backups-1,0,-1):
        a=p.with_name(p.name+f'.{i}'); b=p.with_name(p.name+f'.{i+1}')
        if a.exists(): os.replace(a,b)
    os.replace(p,p.with_name(p.name+'.1'))
def log(r,msg,max_bytes=10*1024*1024,backups=3):
    ensure_rt(r); rotate_log(r,max_bytes,backups)
    with owned_open(r['log'],append=True) as f:f.write(datetime.now().strftime('%F %T')+' '+msg+'\n')
def pid_alive(p):
    try: os.kill(p,0); return True
    except OSError:return False
def read_pid(r):
    try:
        p=int(r['pid'].read_text().strip()); return p if pid_alive(p) else None
    except Exception:return None

def session_id(path):
    m=EXPORT_RE.match(path.name)
    if m:return m.group(1)
    stem=path.stem
    for pat in (r'^(.*?)[-_]20\d{6}[-_]\d{4,6}$',r'^(.*?)[-_]20\d{2}[-_]\d{2}[-_]\d{2}[-_]\d{4,6}$'):
        m=re.match(pat,stem)
        if m:return m.group(1).rstrip('-_')
    return stem

def readonly_open(path):
    # Hard rule: source files are opened read-only. Never touch/lock/rename/write source.
    return os.open(path,os.O_RDONLY | getattr(os,'O_CLOEXEC',0))
def pread(path,start,end,max_bytes=None):
    n=max(0,end-start)
    if max_bytes is not None:n=min(n,max_bytes)
    fd=readonly_open(path)
    try:return os.pread(fd,n,start)
    finally:os.close(fd)

def native_session_id(path):
    m=NATIVE_RE.match(path.name)
    return m.group(1) if m else path.stem

def _texts(v):
    out=[]
    if isinstance(v,str):
        if v.strip():out.append(v)
    elif isinstance(v,list):
        for x in v:
            if isinstance(x,str):
                if x.strip():out.append(x)
            elif isinstance(x,dict):
                z=x.get('text') or x.get('summary_text') or x.get('input_text') or x.get('output_text')
                if z:out.append(str(z))
    elif isinstance(v,dict):
        z=v.get('text') or v.get('summary_text') or v.get('input_text') or v.get('output_text')
        if z:out.append(str(z))
    return out

def json_record_text(obj):
    """Semantic projection of one Codex record. Internal/replay-only data is intentionally omitted."""
    typ=obj.get('type'); p=obj.get('payload') or {}
    if typ=='response_item':
        pt=p.get('type')
        if pt=='message':
            role=str(p.get('role','')).lower()
            if role not in ('user','assistant'):return (None,'')
            return ('User' if role=='user' else 'Assistant','\n'.join(_texts(p.get('content'))))
        if pt=='reasoning':
            chunks=_texts(p.get('summary'))+_texts(p.get('content'))
            # encrypted_content is opaque replay material; never expose it.
            return ('Reasoning','\n'.join(chunks))
        if pt in ('function_call','custom_tool_call'):
            name=p.get('name') or p.get('tool_name') or pt
            args=p.get('arguments')
            if args is None:args=p.get('input')
            if isinstance(args,(dict,list)):args=json.dumps(args,ensure_ascii=False,indent=2)
            return ('Activity',('$ '+str(name)+('\n'+str(args) if args not in (None,'') else '')).strip())
        if pt in ('function_call_output','custom_tool_call_output'):
            out=p.get('output')
            if out is None:out=p.get('content')
            if isinstance(out,(dict,list)):out=json.dumps(out,ensure_ascii=False,indent=2)
            return ('Activity',str(out or ''))
        if pt in ('web_search_call','computer_call','computer_call_output','tool_search_call','tool_search_output'):
            q={k:v for k,v in p.items() if k not in ('encrypted_content','internal_chat_message_metadata_passthrough')}
            return ('Activity',json.dumps(q,ensure_ascii=False,indent=2))
    return (None,'')

def _turn_id(obj):
    p=obj.get('payload') or {}
    md=p.get('internal_chat_message_metadata_passthrough') or {}
    return md.get('turn_id') or p.get('turn_id')

def _phase(obj):
    p=obj.get('payload') or {}
    return str(p.get('phase') or '').lower()

def _call_id(obj):
    p=obj.get('payload') or {}
    return p.get('call_id') or p.get('id')


def native_section_text(path,sec):
    parts=sec.get('parts') or [[sec['start'],sec['end']]]
    chunks=[];role=sec.get('role','Activity')
    for start,end in parts:
        raw=pread(path,start,end)
        try:
            obj=json.loads(raw);r,text=json_record_text(obj)
            if text.strip():chunks.append(text)
            if r:role=r
        except Exception:
            pass
    return role,'\n\n'.join(chunks)

def title_from_user(raw):
    s=raw.decode('utf-8','replace'); x=re.sub(r'[`*_]','',norm(s)); return (x[:117]+'…') if len(x)>118 else (x or 'Untitled task')

def build_index(path,sid):
    st=path.stat(); sections=[]; current=None; inside=False; fchar=None; flen=0; offset=0
    # Streaming parse: memory stays bounded by one line + compact offset metadata.
    with open(path,'rb',buffering=1024*1024) as f:
        while True:
            start=offset; line=f.readline()
            if not line:break
            # Attention is deliberately excluded from the fast path.
            offset += len(line); stripped=line.rstrip(b'\r\n'); fm=FENCE_RE.match(stripped)
            if fm:
                fence=fm.group(1)
                if not inside:inside=True;fchar=fence[:1];flen=len(fence)
                elif fence[:1]==fchar and len(fence)>=flen:inside=False;fchar=None;flen=0
                continue
            if not inside:
                rm=ROLE_RE.match(stripped)
                if rm:
                    if current:current['end']=start
                    current={'role':rm.group(1).decode(),'start':offset,'end':st.st_size,'attention':False}; sections.append(current)
    if current:current['end']=st.st_size
    tasks=[]; cur=None; occurrences={}
    for sec in sections:
        if sec['role']=='User':
            raw=pread(path,sec['start'],sec['end'],2*1024*1024)
            base=hashlib.sha256(norm(raw.decode('utf-8','replace')).encode()).hexdigest()[:16]
            occurrences[base]=occurrences.get(base,0)+1
            tid=hashlib.sha256(f'{base}:{occurrences[base]}'.encode()).hexdigest()[:16]
            cur={'n':len(tasks)+1,'id':tid,'title':title_from_user(raw),'sections':[sec]};tasks.append(cur)
        elif cur:cur['sections'].append(sec)
    return {'version':2,'session_id':sid,'source':str(path),'dev':st.st_dev,'inode':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'indexed_at':time.time(),'tasks':tasks}

def load_session_titles(home):
    """Read Codex-owned title indexes strictly read-only. Later session_index entries win."""
    titles={}
    p=home/'session_index.jsonl'
    if p.is_file():
        fd=readonly_open(p)
        try:
            with os.fdopen(fd,'rb',closefd=True) as f:
                fd=None
                for line in f:
                    try:x=json.loads(line)
                    except Exception:continue
                    sid=x.get('id') or x.get('session_id'); title=x.get('thread_name') or x.get('title')
                    if sid and title:titles[str(sid)]=str(title)
        finally:
            if fd is not None:os.close(fd)
    # Optional state SQLite is deliberately not queried in v4.3.0: session_index is append-only,
    # cheap, and avoids interacting with Codex's live DB. First user prompt is the fallback.
    return titles

class DiscoveryStore:
    def __init__(self,home,r,scan_dirs,cache_sessions=2,refresh_interval=60,log_bytes=10*1024*1024,log_backups=3,native=True):
        self.home=home;self.r=r;self.scan_dirs=[Path(x).expanduser().resolve() for x in (scan_dirs or [])]
        self.native=native;self.cache_limit=max(1,cache_sessions);self.refresh_interval=max(10,refresh_interval)
        self.log_bytes=log_bytes;self.log_backups=log_backups;self.meta={};self.cache=OrderedDict()
        self.last_scan=0;self.lock=threading.RLock();self.titles={};self.scan(True)
    def roots(self):
        return [self.r['exports'],*self.scan_dirs]
    def _scan_native(self,found):
        root=self.home/'sessions'
        if not root.is_dir(): return
        # Fixed-depth scandir only: sessions/YYYY/MM/DD/*.jsonl. No content read during discovery.
        try: years=os.scandir(root)
        except OSError:return
        with years:
            for y in years:
                if not y.is_dir(follow_symlinks=False): continue
                try: months=os.scandir(y.path)
                except OSError: continue
                with months:
                    for m in months:
                        if not m.is_dir(follow_symlinks=False): continue
                        try: days=os.scandir(m.path)
                        except OSError: continue
                        with days:
                            for d in days:
                                if not d.is_dir(follow_symlinks=False): continue
                                try: files=os.scandir(d.path)
                                except OSError: continue
                                with files:
                                    for e in files:
                                        if not e.name.endswith('.jsonl') or not NATIVE_RE.match(e.name) or not e.is_file(follow_symlinks=False): continue
                                        try: st=e.stat(follow_symlinks=False)
                                        except OSError: continue
                                        self._add(found,native_session_id(Path(e.path)),Path(e.path),st,'native-jsonl')
    def scan(self,force=False):
        with self.lock:
            if not force and time.time()-self.last_scan < self.refresh_interval:return self.list(False)
            found={}
            self.titles=load_session_titles(self.home)
            self._scan_native(found)
            for root in self.roots():
                if not root.is_dir():continue
                try:entries=os.scandir(root)
                except OSError:continue
                with entries:
                    for e in entries:
                        if not e.name.endswith('.md') or not e.is_file(follow_symlinks=False):continue
                        p=Path(e.path)
                        try:st=e.stat(follow_symlinks=False)
                        except OSError:continue
                        self._add(found,session_id(p),p,st,'markdown')
            self.meta=found;self.last_scan=time.time();return self.list(False)
    def state_path(self,sid):return self.r['state']/(safe(sid)+'.json')

    def patch(self,sid,tid,d):
        state=self.load_state(sid);s=state['tasks'].setdefault(tid,{})
        for k,v in d.items():
            if k in ('important','marked','later','reviewed'):s[k]=bool(v)
            elif k=='note':s[k]=str(v)[:20000]
        atomic(self.state_path(sid),state);return state
    def baseline(self,sid):
        idx=self.get_index(sid);s=self.load_state(sid);s['baseline_task_ids']=[t['id'] for t in idx['tasks']]
        s['baseline_file']=Path(idx['source']).name;atomic(self.state_path(sid),s);return s

__NAVIGATION__

__SEARCH_CACHE__

class Store(SearchCacheMixin,NavigationStoreMixin,DiscoveryStore):
    """Small persistent task manifests; source data is never opened for writing."""
    def __init__(self,*args,**kwargs):
        self.manifests={};self.jobs={};self.task_cache=OrderedDict();self.task_lock=threading.RLock()
        self.state_lock=threading.RLock();self.worker_gate=threading.Semaphore(1)
        self.search_cache=OrderedDict();self.search_cache_lock=threading.RLock()
        self.search_builds={};self.search_build_lock=threading.RLock();self.search_build_gate=threading.Semaphore(1)
        self.metrics={'manifest_bytes':0,'task_bytes':0,'search_bytes':0,'builds':0,'appends':0}
        super().__init__(*args,**kwargs)
    def _scan_native(self,found):
        return super()._scan_native(found)
    def scan(self,force=False):
        # The old scan(False) called list() on every section request.
        if not force and time.time()-self.last_scan<self.refresh_interval:return []
        return super().scan(force)
    def _add(self,found,sid,p,st,adapter):
        old=found.get(sid)
        # Prefer live native data. Keep exports available as fallback.
        if old is None or (adapter=='native-jsonl' and old['adapter']!='native-jsonl') or (adapter==old['adapter'] and st.st_mtime_ns>old['mtime_ns']):
            found[sid]={'id':sid,'path':str(p),'file':p.name,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'updated':dt(st.st_mtime),'adapter':adapter}
    def list(self,auto=True):
        if auto and time.time()-self.last_scan>=self.refresh_interval:self.scan(True)
        out=[]
        for sid,m in list(self.meta.items()):
            x=dict(m);manifest=self.manifests.get(sid)
            x.update(title=self.titles.get(sid,''),tasks=len(manifest['tasks']) if manifest else None,new=None,important=0,later=0,reviewed=0,indexed=manifest is not None)
            try:state=self.load_state(sid)
            except ValueError:state={'tasks':{}};x['state_error']=True
            for flag in ('important','later','reviewed'):x[flag]=sum(bool(v.get(flag)) for v in state.get('tasks',{}).values())
            out.append(x)
        return sorted(out,key=lambda x:x['mtime_ns'],reverse=True)
    def load_state(self,sid):
        p=self.state_path(sid)
        try:
            state=json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(state.get('tasks'),dict):raise ValueError('Invalid review state')
            return state
        except FileNotFoundError:
            return {'version':4,'session_id':sid,'tasks':{},'baseline_task_ids':[],'baseline_file':None}
        except Exception as e:
            raise ValueError('Review state cannot be read; original preserved: '+str(e))
    def manifest_path(self,sid):return self.r['base']/'cache'/'manifests'/(safe(sid)+'.json')
    def metadata(self,sid):
        self.scan(False)
        if sid not in self.meta:raise KeyError(sid)
        return self.meta[sid]
    def _fingerprint(self,path,offset):
        return hashlib.sha256(pread(path,max(0,offset-8192),offset)).hexdigest()
    def manifest(self,sid):
        m=self.metadata(sid);path=Path(m['path']);st=path.stat()
        with self.lock:
            idx=self.manifests.get(sid)
            if idx is None:
                try:
                    idx=json.loads(self.manifest_path(sid).read_text(encoding='utf-8'))
                    if idx.get('version')!=10:idx=None
                except (OSError,ValueError):idx=None
                if idx:self.manifests[sid]=idx
            job=self.jobs.get(sid,{})
            if job.get('state') in ('queued','indexing'):return idx,dict(job)
            if job.get('state')=='error':return idx,dict(job)
            valid=bool(idx and idx['source']==str(path) and idx['adapter']==m['adapter'] and idx['dev']==st.st_dev and idx['inode']==st.st_ino and idx['offset']<=st.st_size)
            if valid and idx.get('observed_size')==st.st_size and idx.get('mtime_ns')==st.st_mtime_ns:
                return idx,{'state':'ready','indexed_bytes':idx['offset'],'source_bytes':st.st_size}
            if valid:valid=self._fingerprint(path,idx['offset'])==idx.get('fingerprint')
            if valid and m['adapter']=='markdown':valid=False
            # Never reuse a changed generation or publish its offsets to readers.
            if not valid:idx=None;self.manifests.pop(sid,None)
            self.jobs[sid]={'state':'queued','indexed_bytes':idx['offset'] if idx else 0,'source_bytes':st.st_size}
            threading.Thread(target=self._build,args=(sid,dict(m),idx),daemon=True).start()
            return idx,dict(self.jobs[sid])
    def _build(self,sid,m,old):
        try:
            with self.worker_gate:
                started=time.monotonic();path=Path(m['path'])
                with self.lock:self.jobs[sid]['state']='indexing'
                if m['adapter']=='markdown':
                    idx=build_index(path,sid);st=path.stat()
                    idx.update(version=10,adapter='markdown',offset=idx['size'],observed_size=st.st_size,generation=str(time.time_ns()),occurrences={})
                else:
                    fd=readonly_open(path)
                    with os.fdopen(fd,'rb',buffering=1024*1024) as f:
                        st=os.fstat(f.fileno());limit=st.st_size
                        if old and ((old['dev'],old['inode'])!=(st.st_dev,st.st_ino) or st.st_size<old['offset'] or self._fingerprint(path,old['offset'])!=old['fingerprint']):old=None
                        idx=json.loads(json.dumps(old)) if old else {'version':10,'adapter':m['adapter'],'session_id':sid,'source':str(path),'dev':st.st_dev,'inode':st.st_ino,'generation':str(time.time_ns()),'offset':0,'tasks':[],'occurrences':{}}
                        f.seek(idx['offset']);offset=idx['offset'];tasks=idx['tasks'];occ=idx['occurrences'];last=time.monotonic()
                        while offset<limit:
                            start=offset;line=f.readline(limit-offset)
                            if not line or not line.endswith(b'\n'):break
                            offset+=len(line);self.metrics['manifest_bytes']+=len(line)
                            try:obj=json.loads(line)
                            except ValueError:continue
                            p=obj.get('payload') or {}
                            if obj.get('type')=='response_item' and p.get('type')=='message' and p.get('role')=='user':
                                text='\n'.join(_texts(p.get('content')))
                                if text.strip():
                                    ntext=norm(text);base=hashlib.sha256(ntext.encode()).hexdigest()[:16];occ[base]=occ.get(base,0)+1
                                    tid=hashlib.sha256(('%s:%s'%(base,occ[base])).encode()).hexdigest()[:16]
                                    title=re.sub(r'[`*_]','',ntext);title=title[:117]+'…' if len(ntext)>118 else title
                                    if tasks:tasks[-1]['end']=start
                                    tasks.append({'n':len(tasks)+1,'id':tid,'title':title or 'Untitled task','start':start,'end':offset})
                            if time.monotonic()-last>.4:
                                with self.lock:self.jobs[sid].update(indexed_bytes=offset,source_bytes=limit)
                                last=time.monotonic()
                        if tasks:tasks[-1]['end']=offset
                        idx.update(offset=offset,size=offset,observed_size=limit,mtime_ns=st.st_mtime_ns)
                idx['fingerprint']=self._fingerprint(path,idx['offset'])
                # Check descriptor identity against the pathname before publishing.
                now=path.stat()
                if (now.st_dev,now.st_ino)!=(idx['dev'],idx['inode']) or now.st_size<idx['offset']:raise ValueError('Source changed during indexing; refresh to retry')
                atomic(self.manifest_path(sid),idx)
                with self.lock:
                    self.manifests[sid]=idx;self.jobs[sid]={'state':'ready','indexed_bytes':idx['offset'],'source_bytes':now.st_size,'elapsed_ms':round((time.monotonic()-started)*1000)}
                    self.metrics['appends' if old else 'builds']+=1
                log(self.r,'MANIFEST %s sid=%s bytes=%s ms=%s'%('append' if old else 'build',sid,idx['offset']-(old['offset'] if old else 0),self.jobs[sid]['elapsed_ms']))
        except Exception as e:
            with self.lock:self.jobs[sid]={'state':'error','error':str(e)}
            log(self.r,'MANIFEST error sid=%s %s'%(sid,e))
    def status(self,sid,retry=False):
        if retry:
            with self.lock:
                if self.jobs.get(sid,{}).get('state')=='error':self.jobs.pop(sid,None)
        idx,job=self.manifest(sid)
        with self.state_lock:
            state=self.load_state(sid)
            if idx and job['state']=='ready' and not state.get('baseline_file'):
                state['baseline_task_ids']=[t['id'] for t in idx['tasks']];state['baseline_file']=Path(idx['source']).name;atomic(self.state_path(sid),state)
        base=set(state.get('baseline_task_ids',[]))
        tasks=[{'id':t['id'],'n':t['n'],'title':t['title'],'new':bool(state.get('baseline_file')) and t['id'] not in base,'sections':[]} for t in idx['tasks']] if idx else []
        return dict(job,tasks=tasks,review_state=state,generation=idx['generation'] if idx else None,source_token=self.watch(sid)['token'])
    def get_index(self,sid):
        idx,job=self.manifest(sid)
        if idx is None:raise ValueError('Preparing session')
        return idx
    def task(self,sid,tid):
        idx=self.get_index(sid);task=next((t for t in idx['tasks'] if t['id']==tid),None)
        if task is None:raise KeyError('task')
        key=(sid,idx['generation'],tid,task.get('end'),idx['offset'] if idx['adapter']=='markdown' else None)
        with self.task_lock:
            if key in self.task_cache:self.task_cache.move_to_end(key);return self.task_cache[key]
            if idx['adapter']=='markdown':result=task
            else:
                sections=[];calls={};started_at=None;path=Path(idx['source'])
                with os.fdopen(readonly_open(path),'rb',buffering=1024*1024) as f:
                    stat=os.fstat(f.fileno())
                    if (stat.st_dev,stat.st_ino)!=(idx['dev'],idx['inode']):raise ValueError('Source replaced; refresh')
                    f.seek(task['start']);offset=task['start']
                    while offset<task['end']:
                        start=offset;line=f.readline(task['end']-offset)
                        if not line:break
                        offset+=len(line);self.metrics['task_bytes']+=len(line)
                        try:obj=json.loads(line)
                        except ValueError:continue
                        if start==task['start'] and isinstance(obj.get('timestamp'),str):started_at=obj['timestamp']
                        if obj.get('type')!='response_item':continue
                        p=obj.get('payload') or {};pt=p.get('type');role=None
                        if pt=='message' and p.get('role') in ('user','assistant'):role=p['role'].title()
                        elif pt=='reasoning' and (_texts(p.get('summary')) or _texts(p.get('content'))):role='Reasoning'
                        elif pt in ('function_call','custom_tool_call','function_call_output','custom_tool_call_output','web_search_call','computer_call','computer_call_output','tool_search_call','tool_search_output'):role='Activity'
                        if role is None:continue
                        cid=_call_id(obj)
                        if pt in ('function_call_output','custom_tool_call_output') and cid in calls:calls[cid]['parts'].append([start,offset]);continue
                        sec={'role':role,'start':start,'end':offset,'parts':[[start,offset]],'phase':_phase(obj),'label':str(p.get('name') or pt)};sections.append(sec)
                        if cid and pt in ('function_call','custom_tool_call'):calls[cid]=sec
                result=dict(task,sections=sections,started_at=started_at)
            self.task_cache[key]=result
            while len(self.task_cache)>3:self.task_cache.popitem(last=False)
            return result
    def section(self,sid,tid,section_no,preview=False,text_offset=0,focus=None):
        idx=self.get_index(sid);task=self.task(sid,tid)
        if section_no<0 or section_no>=len(task['sections']):raise KeyError('section')
        sec=task['sections'][section_no];path=Path(idx['source'])
        text_offset=max(0,int(text_offset))
        st=path.stat()
        if (st.st_dev,st.st_ino)!=(idx['dev'],idx['inode']):raise ValueError('Source replaced; refresh')
        if idx['adapter']=='markdown':
            if focus:
                full=pread(path,sec['start'],sec['end']).decode('utf-8','replace')
                hit=full.lower().find(focus.lower());text_offset=len(full[:max(0,hit-500)].encode('utf-8')) if hit>=0 else 0
            start=sec['start']+text_offset;raw=pread(path,start,sec['end'],256*1024);text=raw.decode('utf-8','replace')
            if start+len(raw)<sec['end']:
                for trim in range(4):
                    try:
                        chunk=raw[:-trim] if trim else raw;text=chunk.decode('utf-8');raw=chunk;break
                    except UnicodeDecodeError:pass
            return {'role':sec['role'],'text':text,'text_offset':text_offset,'next_offset':text_offset+len(raw) if start+len(raw)<sec['end'] else None}
        role,text=native_section_text(path,sec)
        if focus:
            hit=text.lower().find(focus.lower());text_offset=max(0,hit-500) if hit>=0 else 0
        end=text_offset+262144
        return {'role':role,'text':text[text_offset:end],'text_offset':text_offset,'next_offset':end if end<len(text) else None}
    def search(self,sid,query,scope='All',limit=200,cancel=None):
        if cancel and cancel.is_set():return {'matches':[],'total':0,'cancelled':True}
        idx=self.get_index(sid);meta=self.metadata(sid);stat=Path(meta['path']).stat()
        key=(sid,idx['generation'],idx['offset'],stat.st_size,stat.st_mtime_ns,str(query).strip().lower(),scope,limit)
        with self.search_cache_lock:
            if key in self.search_cache:
                self.search_cache.move_to_end(key);return dict(self.search_cache[key],cached=True,elapsed_ms=0)
        result=self._search(sid,query,scope,limit,cancel)
        if not result.get('cancelled'):
            with self.search_cache_lock:
                self.search_cache[key]=result
                while len(self.search_cache)>12:self.search_cache.popitem(last=False)
        return result
    def _search(self,sid,query,scope='All',limit=200,cancel=None):
        q=str(query or '').strip();scope=str(scope).title();limit=max(1,min(int(limit),200));matches=[]
        if len(q)<2:return {'matches':[],'total':0,'truncated':False}
        idx=self.get_index(sid);needle=q.lower();path=Path(idx['source']);tasks=idx['tasks'];started=time.monotonic()
        if idx['adapter']=='markdown':
            for t in tasks:
                for no,sec in enumerate(t['sections']):
                    if cancel and cancel.is_set():return {'matches':[],'total':0,'cancelled':True}
                    if scope!='All' and scope!=sec['role']:continue
                    text=pread(path,sec['start'],sec['end']).decode('utf-8','replace');self.metrics['search_bytes']+=sec['end']-sec['start']
                    hit=text.lower().find(needle)
                    if hit>=0:matches.append({'task_id':t['id'],'task_n':t['n'],'section':no,'role':sec['role'],'snippet':text[max(0,hit-90):hit+len(q)+130]})
                    if len(matches)>=limit:break
                if len(matches)>=limit:break
        else:
            ti=0;offset=0;accelerated=False
            try:cached=self.cached_text_matches(sid,idx,q,scope,limit,cancel)
            except (OSError,ValueError,KeyError,TypeError,zlib.error):cached=None
            if cached:
                if cached.get('cancelled'):return {'matches':[],'total':0,'cancelled':True}
                matches=cached['matches'];offset=cached['offset'];accelerated=True
                if len(matches)>=limit:offset=idx['offset']
            with os.fdopen(readonly_open(path),'rb',buffering=1024*1024) as f:
                stat=os.fstat(f.fileno())
                if (stat.st_dev,stat.st_ino)!=(idx['dev'],idx['inode']):raise ValueError('Source replaced; refresh')
                f.seek(offset)
                while offset<idx['offset']:
                    if cancel and cancel.is_set():return {'matches':[],'total':0,'cancelled':True}
                    start=offset;line=f.readline(idx['offset']-offset)
                    if not line:break
                    offset+=len(line);self.metrics['search_bytes']+=len(line)
                    while ti+1<len(tasks) and tasks[ti+1]['start']<=start:ti+=1
                    if not tasks or start<tasks[ti]['start']:continue
                    try:obj=json.loads(line)
                    except ValueError:continue
                    role,text=json_record_text(obj)
                    if not role or (scope!='All' and scope!=role):continue
                    hit=text.lower().find(needle)
                    if hit>=0:
                        t=tasks[ti];matches.append({'task_id':t['id'],'task_n':t['n'],'record_start':start,'role':role,'snippet':re.sub(r'\s+',' ',text[max(0,hit-90):hit+len(q)+130])})
                    if len(matches)>=limit:break
        return {'query':q,'matches':matches,'total':len(matches),'truncated':len(matches)>=limit,'cached':False,'accelerated':locals().get('accelerated',False),'elapsed_ms':round((time.monotonic()-started)*1000)}
    def patch(self,sid,tid,d):
        self.load_state(sid)  # Detect damaged state before starting any background work.
        idx=self.get_index(sid)
        if not any(t['id']==tid for t in idx['tasks']):raise KeyError('Unknown task')
        if not isinstance(d,dict):raise ValueError('Expected a JSON object')
        with self.state_lock:return super().patch(sid,tid,d)
    def baseline(self,sid):
        idx,job=self.manifest(sid)
        if job['state']!='ready':raise ValueError('Wait for indexing to finish')
        with self.state_lock:return super().baseline(sid)
    def model(self,sid):
        m=self.metadata(sid)
        return {'adapter':m['adapter'],'tasks':[]},self.load_state(sid),[]


CSS=__ASSET_STYLE__





def index_html(home):
    return __ASSET_HOME__.replace('%%STYLE%%',CSS).replace('%%SCRIPT%%',__ASSET_HOME_JS__).replace('%%VERSION%%',VERSION)

def workspace_html(sid,idx,state,tasks,items):
    opts=''.join(f'<option value="{html.escape(x["id"])}" {"selected" if x["id"]==sid else ""}>{html.escape((x.get("title") or x["file"])[:70])}</option>' for x in items)
    meta=[]
    for t0,t in zip(idx['tasks'],tasks):
        z=dict(t); z['sections']=[{'i':i,'role':x.get('role','Activity'),'phase':x.get('phase','') or '','attention':bool(x.get('attention'))} for i,x in enumerate(t0['sections'])]; z['attention']=any(x.get('attention') for x in t0['sections']); meta.append(z)
    model=json.dumps({'sid':sid,'adapter':idx.get('adapter'),'tasks':meta,'state':state},ensure_ascii=False).replace('<','\\u003c')
    js=__ASSET_READER__
    extra=''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CodexView · {html.escape(sid)}</title><style>{CSS}{extra}</style></head><body><a class="skip-link" href="#reader">Skip to conversation</a><header class="top appbar"><button id="mobileNav" class="quiet-btn mobile-nav-toggle" aria-label="Open task navigator" aria-expanded="false">☰</button><div class="app-left"><a href="/" class="app-brand" title="Recent workspace"><span class="app-logo"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7.2 5.2A8 8 0 1 0 17.5 17"/><path d="M16.8 6.4A6.1 6.1 0 0 0 12 4"/><path d="M9 9.2a4 4 0 1 0 6 5.2"/></svg></span><b>CodexView</b><small class="app-version">v{VERSION}</small></a><span class="app-sep"></span><div class="session-crumb"><span class="crumb-label">Session</span><select id="ss" class="session-select">{opts}</select></div></div><span class="grow"></span><span class="readonly-badge">● Read-only</span><button id="searchSession" class="quiet-btn" title="Search session · Ctrl/Cmd F">⌕ Search</button><button id="refreshSession" class="quiet-btn">↻ Refresh</button><div class="view-switch"><button id="mode" class="quiet-btn">Overview</button></div><div class="font-group"><button id="minus" class="quiet-btn icon-only" title="Decrease text size">A−</button><button id="resetfont" class="quiet-btn font-reset" title="Reset text size">A</button><button id="plus" class="quiet-btn icon-only" title="Increase text size">A+</button></div><button id="theme" class="quiet-btn icon-only" title="Toggle theme">☀</button><button id="helpbtn" class="quiet-btn icon-only" title="Keyboard shortcuts"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.8 9a2.4 2.4 0 0 1 4.6 1c0 1.8-2.4 2.1-2.4 3.8"/><path d="M12 17h.01"/></svg></button><details class="more-menu"><summary class="quiet-btn icon-only" title="More actions"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/></svg></summary><div class="more-pop"><div class="menu-label">Session actions</div><button id="baseline" class="menu-item"><span>Set NEW baseline</span></button><div class="menu-rule"></div><label class="menu-item layout-option">Task density<select id="readerDensity" aria-label="Task density"><option value="standard">Standard</option><option value="compact">Compact</option></select></label><label class="menu-item layout-option">Reading width<select id="readerWidth" aria-label="Reading width"><option value="custom">Custom</option><option value="comfortable">Comfortable</option><option value="wide">Wide</option></select></label><div class="menu-meta">Codex source is read-only</div></div></details><span id="exportmsg" class="export-status"></span></header><div class="layout"><aside class="side"><div class="sidehead"><div class="nav-head"><div class="nav-title-row"><button id="sidecollapse" class="side-collapse" title="Collapse navigator" aria-label="Collapse navigator"><svg viewBox="0 0 20 20"><path d="m12.5 5-5 5 5 5"/></svg></button><a class="nav-title" href="/" title="Back to sessions">Tasks</a><span id="navpos" class="nav-pos">— / —</span></div><button id="overviewBtn" class="review-summary" title="Review overview" aria-label="Review overview"><span aria-hidden="true">◴</span><b id="reviewpct">0%</b></button></div><div class="nav-search"><input id="taskq" class="tasksearch" aria-label="Filter task titles" placeholder="Filter task titles…"><kbd>/</kbd></div><div class="nav-tools"><select id="taskFilter" aria-label="Filter tasks"><option value="all">All tasks</option><option value="new">New</option><option value="important">★ Important</option><option value="later">Later</option><option value="reviewed">Reviewed</option><option value="marked">Marked</option></select><label class="jump-control" for="jumpTask"><span class="sr-only">Go to task</span><input id="jumpTask" type="number" min="1" placeholder="#" inputmode="numeric"></label><button id="latestTask" class="btn" title="Jump to latest task">Latest ↓</button></div></div><div class="nav-list-wrap"><div id="tl"></div><div id="minimap" class="minimap" aria-label="Task review map"></div></div></aside><div id="sideResizer" class="sidebar-resizer" role="separator" aria-orientation="vertical" aria-valuemin="236" aria-valuemax="520" aria-label="Resize task navigator" tabindex="0"></div><button id="drawerScrim" class="drawer-scrim" aria-label="Close task navigator"></button><main class="main"><div id="readingContext" class="reading-context"><span id="readingTitle">Loading task…</span><time id="readingTime"></time><button id="loadedReports" class="quiet-btn">Reports<span id="reportCount"></span></button><button id="relatedSessions" class="quiet-btn">Related</button><button id="newContent" class="quiet-btn" hidden>New content · Refresh</button><button id="followLatest" class="quiet-btn" aria-pressed="false">Follow latest</button></div><div class="session-ready" id="sessionReady" role="status"><b>● Native source</b><span id="readinessText">Preparing session…</span></div><div id="reader" tabindex="-1" class="reader"><div class="session-loading" aria-label="Loading session"><div class="load-line load-title"></div><div class="load-line"></div><div class="load-line"></div><div class="load-line"></div></div></div></main></div><div id="contentResizer" class="content-resizer" role="separator" aria-orientation="vertical" aria-label="Resize reading width" aria-valuemin="480" aria-valuemax="1400" tabindex="0" title="Drag to resize reading width · Double-click for Auto"></div><div id="contentWidthPill" class="content-width-pill"></div><div id="tasknav"><button data-nav="prev" title="Previous task"><svg viewBox="0 0 24 24"><path d="m18 15-6-6-6 6"/></svg></button><span class="navcount"></span><button data-nav="next" title="Next task"><svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button></div><dialog id="readerDialog" class="reader-dialog"><header><b id="readerDialogTitle"></b><button id="readerDialogClose" aria-label="Close panel">×</button></header><div id="readerDialogBody"></div></dialog><div id="toast" role="status" aria-live="polite"></div><div id="palette"><div class="palette-card"><div class="palette-search"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg><input id="paletteInput" placeholder="Type a command…"></div><div id="paletteList" class="palette-list"></div></div></div><div id="helpmodal" class="helpmodal"><div class="help-card"><div class="help-title"><b>Keyboard shortcuts</b><button id="helpclose">×</button></div><div class="help-grid"><span>Session search</span><kbd>⌘/Ctrl F</kbd><span>Command palette</span><kbd>⌘/Ctrl K</kbd><span>Search tasks</span><kbd>/</kbd><span>Next / previous task</span><kbd>J / K</kbd><span>Important</span><kbd>I</kbd><span>Marked</span><kbd>M</kbd><span>Review later</span><kbd>L</kbd><span>Reviewed</span><kbd>R</kbd><span>Overview / Full</span><kbd>O</kbd><span>Close dialogs</span><kbd>Esc</kbd></div><p>Codex source files remain read-only. Review state is stored separately by CodexView.</p></div></div><div id="sessionSearchPanel" class="session-search-panel" role="dialog" aria-label="Search this session" aria-modal="true"><div class="session-search-card"><div class="session-search-head"><input id="sessionSearchInput" aria-label="Search session content" placeholder="Search this session…"><select id="sessionSearchScope" aria-label="Search scope"><option>All</option><option>User</option><option>Assistant</option><option>Activity</option><option>Reasoning</option></select><button id="sessionSearchClose" title="Close">×</button></div><div id="sessionSearchMeta" class="search-meta">Search User, Assistant, Activity, and Reasoning</div><div id="sessionSearchResults" class="search-results"></div><div class="search-cache-tools"><button id="buildSearchCache" class="btn">Build search cache</button><button id="cancelSearchCache" class="btn" hidden>Cancel</button><span id="searchCacheStatus">Optional · prepared only when requested</span></div><div class="search-hint"><span>↑ ↓ select · Enter open · Esc close</span><span>Up to 200 matching records</span></div></div></div><div id="overviewPanel" class="overview-panel"><div class="overview-card"><div class="overview-head"><div><span class="overview-kicker">Session</span><h2>Review overview</h2></div><button id="overviewClose">×</button></div><div class="overview-grid"><div><b id="ovTasks">0</b><span>Tasks</span></div><div><b id="ovReviewed">0</b><span>Reviewed</span></div><div><b id="ovNew">0</b><span>New</span></div><div><b id="ovImportant">0</b><span>Important</span></div><div><b id="ovLater">0</b><span>Later</span></div><div><b id="ovMarked">0</b><span>Marked</span></div></div><p class="overview-foot">Review state is stored separately. Codex source remains read-only.</p></div></div><div class="statusbar"><span id="count"></span><span>Adapter: {html.escape(idx.get('adapter','markdown'))}</span><span>Virtual Reader · 3-task window</span><span class="grow"></span><span>Codex source: read-only</span></div><script id="model" type="application/json">{model}</script><script>{js}</script></body></html>'''

__DOCUMENTS__

class App:
    def __init__(self,store,file_roots=None):self.s=store;self.files=ReportFiles(store.home,file_roots);self.searches={};self.search_lock=threading.Lock();self.search_gate=threading.Semaphore(1)
    def handler(self):
        app=self
        class H(BaseHTTPRequestHandler):
            def log_message(self,fmt,*args):log(app.s.r,f'HTTP {self.client_address[0]} {fmt%args}',app.s.log_bytes,app.s.log_backups)
            def sendx(self,x,typ='text/html; charset=utf-8',status=200,csp=None):
                if isinstance(x,str):x=x.encode()
                self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(x)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('Content-Security-Policy',csp or "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https: http:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'");self.end_headers();
                try:self.wfile.write(x)
                except (BrokenPipeError,ConnectionResetError):pass
            def jsonx(self,x,status=200):self.sendx(json.dumps(x,ensure_ascii=False),'application/json; charset=utf-8',status)
            def do_GET(self):
                u=urllib.parse.urlparse(self.path);p=urllib.parse.unquote(u.path)
                if p=='/':return self.sendx(index_html(app.s.home))
                if p=='/api/health':return self.jsonx({'version':VERSION,'native':True})
                if p=='/file':
                    qs=urllib.parse.parse_qs(u.query)
                    return self.sendx(document_html((qs.get('path') or [''])[0],(qs.get('sid') or [''])[0],(qs.get('task') or [''])[0],(qs.get('from') or [''])[0]))
                if p in ('/api/file','/files/resource') or p.startswith('/files/raw/'):
                    try:
                        qs=urllib.parse.parse_qs(u.query)
                        context_sid=(qs.get('sid') or [''])[0];context_task=(qs.get('task') or [''])[0]
                        if p.startswith('/files/raw/'):
                            m=re.fullmatch(r'/files/raw/(\d+)/(.*)',p)
                            if not m:raise ReportError('Invalid report URL.',400)
                            value=app.files.raw_path(int(m.group(1)),m.group(2));sid=None
                        else:
                            qs=urllib.parse.parse_qs(u.query);value=(qs.get('path') or [''])[0];sid=(qs.get('sid') or [None])[0]
                        info,data=app.files.read(value,sid,app.s,document=(p=='/api/file'))
                        if p=='/api/file':
                            if info['kind']=='image':return self.jsonx(dict(info,text=''))
                            try:text=data.decode('utf-8-sig')
                            except UnicodeDecodeError:raise ReportError('Report must use UTF-8 text.',415)
                            if info['kind']=='html':
                                parser=StaticReport(info['raw_url']);parser.feed(text);info['images']=[url for url in (report_navigation(app.files,target,context_sid,context_task) for target in parser.images) if url]
                            return self.jsonx(dict(info,text=text))
                        if info['kind']=='html':
                            try:data=static_report(data.decode('utf-8-sig'),info['raw_url'],lambda target: report_navigation(app.files,target,context_sid,context_task))
                            except UnicodeDecodeError:raise ReportError('Report must use UTF-8 text.',415)
                        return self.sendx(data,info['type'],csp=REPORT_CSP)
                    except ReportError as e:return self.jsonx({'error':str(e)},e.status)
                    except (KeyError,ValueError):return self.jsonx({'error':'Invalid session or report path.'},400)

                m=re.fullmatch(r'/api/session/([^/]+)/(watch|related|search-cache)',p)
                if m:
                    try:
                        sid,kind=m.groups()
                        if kind=='watch':return self.jsonx(app.s.watch(sid))
                        if kind=='related':return self.jsonx(app.s.related(sid,int((urllib.parse.parse_qs(u.query).get('cursor') or ['0'])[0])))
                        return self.jsonx(app.s.search_cache_status(sid))
                    except Exception as e:return self.jsonx({'error':str(e)},400)
                m=re.match(r'^/api/session/(.+?)/manifest$',p)
                if m:
                    try:return self.jsonx(app.s.status(m.group(1),retry=('retry=1' in u.query)))
                    except Exception as e:return self.jsonx({'error':str(e)},400)
                m=re.match(r'^/api/session/(.+?)/task/([^/]+)$',p)
                if m:
                    try:
                        t=app.s.task(m.group(1),m.group(2))
                        return self.jsonx({'started_at':t.get('started_at'),'sections':[dict(i=i,role=z['role'],phase=z.get('phase',''),label=z.get('label',''),record_start=z['start'],parts=z.get('parts',[])) for i,z in enumerate(t['sections'])]})
                    except Exception as e:return self.jsonx({'error':str(e)},409)
                if p=='/api/sessions':return self.jsonx(app.s.scan(True) if 'refresh=1' in u.query else app.s.list(True))
                m=re.match(r'^/api/session/(.+?)/search$',p)
                if m:
                    try:
                        qs=urllib.parse.parse_qs(u.query);q=(qs.get('q') or [''])[0];scope=(qs.get('scope') or ['All'])[0];limit=int((qs.get('limit') or ['200'])[0])
                        client=(qs.get('client') or [self.client_address[0]])[0][:100]
                        ctl=threading.Event();key=(m.group(1),client)
                        with app.search_lock:
                            previous=app.searches.get(key)
                            if previous:previous.set()
                            app.searches[key]=ctl
                        try:
                            with app.search_gate:
                                result=app.s.search(m.group(1),q,scope,limit,cancel=ctl)
                            return self.jsonx(result)
                        finally:
                            with app.search_lock:
                                if app.searches.get(key) is ctl:app.searches.pop(key,None)
                    except Exception as e:return self.jsonx({'error':str(e)},400)
                m=re.match(r'^/api/session/(.+?)/task/([^/]+)/section/(\d+)$',p)
                if m:
                    try:return self.jsonx(app.s.section(m.group(1),m.group(2),int(m.group(3)),preview=False,text_offset=int((urllib.parse.parse_qs(u.query).get('offset') or ['0'])[0]),focus=(urllib.parse.parse_qs(u.query).get('focus') or [None])[0]))
                    except Exception as e:return self.jsonx({'error':str(e)},404)
                if p.startswith('/session/'):
                    sid=p[len('/session/'):].strip('/')
                    try:idx,state,tasks=app.s.model(sid);return self.sendx(workspace_html(sid,idx,state,tasks,app.s.list(False)))
                    except KeyError:return self.sendx('Session not found',status=404)
                self.send_error(404)
            def do_POST(self):
                origin=self.headers.get('Origin')
                if self.headers.get('Sec-Fetch-Site')=='cross-site' or (origin and urllib.parse.urlsplit(origin).netloc!=self.headers.get('Host')):
                    return self.jsonx({'error':'Cross-origin writes are not allowed'},403)
                try:n=int(self.headers.get('Content-Length','0'))
                except ValueError:return self.jsonx({'error':'Invalid body length'},400)
                if n<0 or n>65536:return self.jsonx({'error':'Request body too large'},413)
                p=urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
                m=re.fullmatch(r'/api/session/([^/]+)/search-cache(/cancel)?',p)
                if m:
                    try:
                        self.rfile.read(n)
                        return self.jsonx(app.s.cancel_search_cache(m.group(1)) if m.group(2) else app.s.start_search_cache(m.group(1)))
                    except Exception as e:return self.jsonx({'error':str(e)},400)
                m=re.match(r'^/api/session/(.+?)/search-cancel$',p)
                if m:
                    qs=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);client=(qs.get('client') or [self.client_address[0]])[0][:100]
                    with app.search_lock:
                        ctl=app.searches.get((m.group(1),client))
                        if ctl:ctl.set()
                    return self.jsonx({'cancelled':True})
                m=re.match(r'^/api/session/(.+?)/task/([^/]+)$',p)
                if m:
                    try:d=json.loads(self.rfile.read(n) or b'{}');return self.jsonx({'state':app.s.patch(m.group(1),m.group(2),d)})
                    except Exception as e:return self.jsonx({'error':str(e)},400)
                m=re.match(r'^/api/session/(.+?)/baseline$',p)
                if m:
                    try:return self.jsonx({'state':app.s.baseline(m.group(1))})
                    except Exception as e:return self.jsonx({'error':str(e)},400)
                self.send_error(404)
        return H

def parse_size(s):
    m=re.match(r'^(\d+)([KMG]?)$',str(s).strip().upper())
    if not m:raise argparse.ArgumentTypeError('use e.g. 10M, 512K, 1G')
    return int(m.group(1))*{'':1,'K':1024,'M':1024**2,'G':1024**3}[m.group(2)]
def run_server(a):
    h=codex_home(a.codex_home);r=runtime(h);ensure_rt(r)
    if read_pid(r) and not a.child:raise SystemExit(f'CodexView already running PID {read_pid(r)}')
    store=Store(h,r,a.scan_dir,a.cache_sessions,a.refresh_interval,a.max_log_size,a.log_backups,True)
    try:srv=ThreadingHTTPServer((a.host,a.port),App(store,a.file_root).handler())
    except OSError as e:raise SystemExit(f'cannot bind {a.host}:{a.port}: {e}')
    with owned_open(r['pid']) as pid_file:pid_file.write(str(os.getpid()))
    atomic(r['config'],{'version':VERSION,'host':a.host,'port':a.port,'codex_home':str(h),'scan_dir':a.scan_dir or [],'file_roots':a.file_root or [],'cache_sessions':a.cache_sessions,'refresh_interval':a.refresh_interval,'native':True,'started':datetime.now().isoformat()})
    log(r,f'START v{VERSION} pid={os.getpid()} listen={a.host}:{a.port} codex_home={h}',a.max_log_size,a.log_backups)
    print(f'CodexView {VERSION} · Codex Review Server\nPID        : {os.getpid()}\nListen     : {a.host}:{a.port}\nCodex Home : {h}\nExports    : {r["exports"]}\nLog        : {r["log"]}',flush=True)
    def stop(*_):threading.Thread(target=srv.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:srv.serve_forever(.5)
    finally:
        srv.server_close()
        try:r['pid'].unlink()
        except FileNotFoundError:pass
        log(r,'STOP',a.max_log_size,a.log_backups)
def daemon(a):
    h=codex_home(a.codex_home);r=runtime(h);ensure_rt(r)
    if read_pid(r):print(f'CodexView already running PID {read_pid(r)}');return
    cmd=[sys.executable,str(Path(__file__).resolve()),'serve','--foreground','--child','--host',a.host,'--port',str(a.port),'--codex-home',str(h),'--cache-sessions',str(a.cache_sessions),'--refresh-interval',str(a.refresh_interval),'--max-log-size',str(a.max_log_size),'--log-backups',str(a.log_backups)]
    for d in a.scan_dir or []:cmd+=['--scan-dir',d]
    for d in a.file_root or []:cmd+=['--file-root',d]
    with owned_open(r['log'],append=True) as f:p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=f,stderr=f,start_new_session=True,close_fds=True)
    for _ in range(40):
        time.sleep(.1)
        if read_pid(r):break
    print(f'CodexView started in background\nPID        : {read_pid(r) or p.pid}\nListen     : {a.host}:{a.port}\nCodex Home : {h}\nExports    : {r["exports"]}\nLog        : {r["log"]}')
    if a.host=='127.0.0.1':print(f'SSH tunnel : ssh -L {a.port}:127.0.0.1:{a.port} USER@SERVER')

def doctor(a):
    h=codex_home(a.codex_home);r=runtime(h);ensure_rt(r);ok=True
    print('CodexView doctor')
    print('Codex Home :',h, 'EXISTS' if h.exists() else 'MISSING')
    print('Write root :',r['base'])
    try:
        test=r['base']/'.write-test';atomic(test,{'ok':True});test.unlink();print('State write: OK (codexview subtree only)')
    except Exception as e:print('State write: FAIL',e);ok=False
    print('Codex data : READ-ONLY BY DESIGN (source opened O_RDONLY; no touch/lock/rename/write)')
    print('Discovery  : metadata-only; fixed-depth CODEX_HOME/sessions/YYYY/MM/DD + Markdown scan dirs')
    print('Payload    : shell-first, local task offsets, on-demand activity, bounded response')
    print('Cache      : task manifests + 3-task offset metadata LRU')
    return 0 if ok else 2

HELP = """Default: codexview serve (127.0.0.1:17864).
Remote: ssh -L 17864:127.0.0.1:17864 user@server
Native session discovery is always enabled. Source files remain read-only.
Only CODEX_HOME/codexview stores manifests, review state and logs.
"""
EMBEDDED_GUIDE = """# CodexView 6.3.0-dev.2
Run `codexview serve` on the Codex CLI server. Python 3.7+; no dependencies.
Use an SSH tunnel for private remote access. Open http://127.0.0.1:17864.
Session discovery reads filesystem metadata; first open builds a task manifest.
Tasks and execution evidence load on demand. Refresh checks newly appended content.
Search content using Cmd/Ctrl F, task titles using /, and navigate using J/K.
Review marks and notes are stored separately in CODEX_HOME/codexview/state.
Native source, rollout, config and auth files remain read-only.
This is a personal viewer; place public deployments behind authentication.
"""

def parser():
    p=argparse.ArgumentParser(description='CodexView — Codex Session Review Workspace',epilog=HELP,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('--version',action='version',version='CodexView '+VERSION);sp=p.add_subparsers(dest='cmd')
    s=sp.add_parser('serve',help='启动 Review Server（默认后台）');s.add_argument('--codex-home');s.add_argument('--host',default='127.0.0.1');s.add_argument('--port',type=int,default=DEFAULT_PORT);s.add_argument('--scan-dir',action='append');s.add_argument('--file-root',action='append',help='Read-only project report directory (repeatable; disabled by default)');s.add_argument('--foreground',action='store_true');s.add_argument('--child',action='store_true',help=argparse.SUPPRESS);s.add_argument('--cache-sessions',type=int,default=2);s.add_argument('--refresh-interval',type=int,default=60);s.add_argument('--max-log-size',type=parse_size,default=10*1024*1024);s.add_argument('--log-backups',type=int,default=3);s.add_argument('--no-native',action='store_true',help=argparse.SUPPRESS)
    for name in ('status','stop','logs','sessions','doctor','guide'):
        q=sp.add_parser(name);q.add_argument('--codex-home')
        if name=='logs':q.add_argument('--lines',type=int,default=100);q.add_argument('-f','--follow',action='store_true')
        if name=='sessions':q.add_argument('--scan-dir',action='append');q.add_argument('--no-native',action='store_true',help=argparse.SUPPRESS)
        if name=='guide':q.add_argument('-o','--output',help='将内置中文说明写入指定 Markdown 文件；不指定时输出到终端')
    return p
def main():
    p=parser();a=p.parse_args()
    if not a.cmd:p.print_help();return
    if a.cmd=='serve':return run_server(a) if a.foreground else daemon(a)
    if a.cmd=='doctor':raise SystemExit(doctor(a))
    if a.cmd=='guide':
        if a.output:
            out=Path(a.output).expanduser().resolve();home=codex_home(a.codex_home)
            if home in out.parents and home/'codexview' not in out.parents:raise SystemExit('Cannot write a guide into Codex-owned data')
            out.write_text(EMBEDDED_GUIDE,encoding='utf-8');print('Guide written:',out)
        else:print(EMBEDDED_GUIDE)
        return
    h=codex_home(a.codex_home);r=runtime(h)
    if a.cmd=='status':
        x=read_pid(r);print('Status     :','RUNNING' if x else 'STOPPED');print('PID        :',x or '-');print('Codex Home :',h);print('Write root :',r['base']);print('Log        :',r['log']);return
    if a.cmd=='stop':
        x=read_pid(r)
        if not x:print('CodexView is not running.');return
        os.kill(x,signal.SIGTERM);print('Stopping PID',x);return
    if a.cmd=='sessions':
        ensure_rt(r);s=Store(h,r,a.scan_dir,native=True)
        for x in s.list(False):print(f'{x["updated"]}  {str(x["tasks"]):>11} tasks  {x["id"]}  {x["file"]}')
        return
    if a.cmd=='logs':
        if not r['log'].exists():print('No log:',r['log']);return
        for x in r['log'].read_text(errors='replace').splitlines()[-a.lines:]:print(x)
        if a.follow:
            pos=r['log'].stat().st_size
            try:
                while True:
                    time.sleep(.5)
                    with r['log'].open(errors='replace') as f:
                        f.seek(pos)
                        for x in f:print(x,end='')
                        pos=f.tell()
            except KeyboardInterrupt:pass
if __name__=='__main__':main()