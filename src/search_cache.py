"""Optional bounded normalized-text sidecars. No SQLite/tokenizer dependency.

Only the user's Build action starts work. Original JSONL remains the authority;
cache matches are verified against it, and uncovered tails stream normally.
"""
import struct, zlib

SEARCH_CACHE_LIMIT=128*1024*1024
SEARCH_RECORD_LIMIT=1024*1024

class SearchCacheMixin:
    def search_root(self,create=False):
        root=self.r['base']/'cache'/'search'
        if root.is_symlink() or root.parent.resolve()!=root.parent:raise ValueError('Redirected search cache directory')
        if create:root.mkdir(mode=0o700,parents=True,exist_ok=True)
        if root.exists() and root.resolve()!=root:raise ValueError('Redirected search cache directory')
        return root
    def search_cache_info(self,sid,idx=None):
        root=self.search_root();path=root/(safe(sid)+'.json')
        if path.is_symlink():raise ValueError('Redirected search cache')
        try:info=json.loads(path.read_text())
        except (OSError,ValueError):return None
        if info.get('version')!=2 or not re.fullmatch(r'[0-9a-f]{32}\.data',str(info.get('file',''))):return None
        idx=idx or self.manifests.get(sid)
        if not idx or info.get('generation')!=idx['generation'] or info.get('source')!=idx['source'] or not 0<=info.get('offset',-1)<=idx['offset']:return None
        data=root/info['file']
        if data.is_symlink() or not data.is_file() or (data.stat().st_size!=info.get('cache_bytes') or str(data.stat().st_mtime_ns)!=info.get('cache_mtime')):return None
        return info
    def search_cache_status(self,sid):
        meta=self.meta.get(sid)
        if not meta:raise KeyError(sid)
        info=self.search_cache_info(sid);job=self.search_builds.get(sid,{})
        result={k:v for k,v in job.items() if k!='cancel'}
        result.update(ready=bool(info),complete=bool(info and info['offset']==Path(meta['path']).stat().st_size),offset=job.get('offset',info['offset'] if info else 0),source_bytes=Path(meta['path']).stat().st_size)
        result.setdefault('state','ready' if info else 'idle')
        return result
    def start_search_cache(self,sid):
        idx=self.get_index(sid)
        if idx['adapter']!='native-jsonl':raise ValueError('Search cache is available for Native sessions; Markdown uses streaming search')
        with self.search_build_lock:
            if self.search_builds.get(sid,{}).get('state') not in ('queued','building'):
                if sum(j.get('state') in ('queued','building') for j in self.search_builds.values())>=2:raise ValueError('Another search cache is being prepared; try again later')
                ctl=threading.Event();self.search_builds[sid]={'state':'queued','offset':0,'source_bytes':idx['offset'],'cancel':ctl}
                threading.Thread(target=self._build_search_cache,args=(sid,json.loads(json.dumps(idx)),ctl),daemon=True).start()
        return self.search_cache_status(sid)
    def cancel_search_cache(self,sid):
        with self.search_build_lock:
            ctl=self.search_builds.get(sid,{}).get('cancel')
            if ctl:ctl.set()
        return {'cancelled':True}
    def _build_search_cache(self,sid,idx,cancel):
        temporary=None;target=None;published=False
        try:
            with self.search_build_gate:
                if cancel.is_set():return
                root=self.search_root(True);previous=self.search_cache_info(sid,idx);offset=0;ti=0;tasks=idx['tasks'];written=0
                self.search_builds[sid].update(state='building')
                fd,name=tempfile.mkstemp(suffix='.building',dir=str(root));temporary=Path(name)
                with os.fdopen(fd,'wb') as output,os.fdopen(readonly_open(Path(idx['source'])),'rb',buffering=1024*1024) as source:
                    st=os.fstat(source.fileno())
                    if (st.st_dev,st.st_ino)!=(idx['dev'],idx['inode']):raise ValueError('Source replaced')
                    if previous and self._fingerprint(Path(idx['source']),previous['offset'])==previous.get('fingerprint'):
                        with os.fdopen(readonly_open(root/previous['file']),'rb') as old:
                            while True:
                                chunk=old.read(1024*1024)
                                if not chunk:break
                                if cancel.is_set():return
                                output.write(chunk);written+=len(chunk)
                        offset=previous['offset']
                    source.seek(offset);last=time.monotonic()
                    while offset<idx['offset'] and written<SEARCH_CACHE_LIMIT:
                        if cancel.is_set():return
                        start=offset;line=source.readline(min(SEARCH_RECORD_LIMIT+1,idx['offset']-offset));offset+=len(line);overflow=not line.endswith(b'\n')
                        if overflow:
                            while offset<idx['offset'] and line and not line.endswith(b'\n'):
                                line=source.readline(min(65536,idx['offset']-offset));offset+=len(line)
                        while ti+1<len(tasks) and tasks[ti+1]['start']<=start:ti+=1
                        if not tasks or start<tasks[ti]['start']:continue
                        role='';lower=b''
                        if not overflow:
                            try:role,text=json_record_text(json.loads(line))
                            except ValueError:continue
                            if not role:continue
                            lower=text.lower().encode('utf-8')
                            if len(lower)>SEARCH_RECORD_LIMIT:overflow=True;lower=b''
                        compressed=False
                        if len(lower)>1024:
                            packed=zlib.compress(lower,1)
                            if len(packed)+32<len(lower):lower=packed;compressed=True
                        meta=json.dumps([ti,start,offset,role,overflow,compressed],separators=(',',':')).encode();size=8+len(meta)+len(lower)
                        if written+size>SEARCH_CACHE_LIMIT:offset=start;break
                        output.write(struct.pack('!II',len(meta),len(lower)));output.write(meta);output.write(lower);written+=size
                        if time.monotonic()-last>.2:
                            self.search_builds[sid].update(offset=offset);time.sleep(.005);last=time.monotonic()
                    output.flush();os.fsync(output.fileno())
                if cancel.is_set():return
                now=Path(idx['source']).stat()
                if (now.st_dev,now.st_ino)!=(idx['dev'],idx['inode']) or now.st_size<idx['offset'] or self._fingerprint(Path(idx['source']),idx['offset'])!=idx['fingerprint']:raise ValueError('Source changed while preparing search cache')
                import uuid
                target=root/(uuid.uuid4().hex+'.data');os.replace(str(temporary),str(target));temporary=None
                info={'version':2,'generation':idx['generation'],'source':idx['source'],'offset':offset,'fingerprint':self._fingerprint(Path(idx['source']),offset),'cache_bytes':written,'cache_mtime':str(target.stat().st_mtime_ns),'file':target.name}
                atomic(root/(safe(sid)+'.json'),info);published=True
                self.search_builds[sid].update(state='ready',offset=offset)
                # Only two generated search caches are retained; review state is never cache.
                manifests=sorted(root.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
                live={target.name}
                for i,p in enumerate(manifests):
                    if p.is_symlink():continue
                    try:old_info=json.loads(p.read_text())
                    except (OSError,ValueError):continue
                    if old_info.get('version')!=2 or not re.fullmatch(r'[0-9a-f]{32}\.data',str(old_info.get('file',''))):continue
                    if i<2:live.add(old_info.get('file'))
                    elif p.name!=safe(sid)+'.json':p.unlink()
                for p in root.glob('*.data'):
                    if re.fullmatch(r'[0-9a-f]{32}\.data',p.name) and not p.is_symlink() and p.name not in live:p.unlink()
        except Exception as e:self.search_builds[sid].update(state='error',error=str(e))
        finally:
            if target is not None and not published:
                try:target.unlink()
                except OSError:pass
            if temporary is not None:
                try:temporary.unlink()
                except OSError:pass
            if cancel.is_set():self.search_builds[sid].update(state='cancelled')
    def cached_text_matches(self,sid,idx,query,scope,limit,cancel):
        info=self.search_cache_info(sid,idx)
        if not info:return None
        if self._fingerprint(Path(idx['source']),info['offset'])!=info.get('fingerprint'):return None
        needle=query.lower().encode('utf-8');matches=[];tasks=idx['tasks'];root=self.search_root()
        with os.fdopen(readonly_open(root/info['file']),'rb',buffering=1024*1024) as f:
            while True:
                if cancel and cancel.is_set():return {'matches':[],'offset':0,'cancelled':True}
                header=f.read(8)
                if not header:break
                if len(header)!=8:raise ValueError('Incomplete search cache')
                ml,tl=struct.unpack('!II',header)
                if ml>512 or tl>SEARCH_RECORD_LIMIT:raise ValueError('Invalid search cache record')
                meta=f.read(ml);lower=f.read(tl)
                if len(meta)!=ml or len(lower)!=tl:raise ValueError('Incomplete search cache')
                ti,start,end,role,overflow,compressed=json.loads(meta)
                if not 0<=ti<len(tasks) or not 0<=start<end<=info['offset'] or not tasks[ti]['start']<=start<tasks[ti]['end']:raise ValueError('Invalid search offsets')
                if not overflow:
                    if scope!='All' and scope!=role:continue
                    if compressed:
                        decoder=zlib.decompressobj();lower=decoder.decompress(lower,SEARCH_RECORD_LIMIT+1)
                        if len(lower)>SEARCH_RECORD_LIMIT or not decoder.eof:raise ValueError('Invalid compressed search record')
                    if needle not in lower:continue
                role,text=json_record_text(json.loads(pread(Path(idx['source']),start,end)))
                if not role or scope!='All' and role!=scope:continue
                hit=text.lower().find(query.lower())
                if hit<0:continue
                task=tasks[ti];matches.append({'task_id':task['id'],'task_n':task['n'],'record_start':start,'role':role,'snippet':re.sub(r'\s+',' ',text[max(0,hit-90):hit+len(query)+130])})
                if len(matches)>=limit:break
        return {'matches':matches,'offset':info['offset']}
