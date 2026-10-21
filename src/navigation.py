"""Explicit, bounded navigation metadata. Discovery never depends on these reads."""
class NavigationStoreMixin:
    def watch(self,sid):
        meta=self.meta.get(sid)
        if meta is None:raise KeyError(sid)
        st=Path(meta['path']).stat();idx=self.manifests.get(sid)
        token='%s:%s:%s:%s'%(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
        return {'token':token,'source_bytes':st.st_size,'replaced':bool(idx and ((st.st_dev,st.st_ino)!=(idx['dev'],idx['inode']) or st.st_size<idx['offset']))}
    def session_header(self,sid):
        meta=self.meta.get(sid)
        if not meta or meta['adapter']!='native-jsonl':return {}
        try:
            with os.fdopen(readonly_open(Path(meta['path'])),'rb') as f:first=f.readline(65537)
            if len(first)>65536:return {}
            obj=json.loads(first)
            if obj.get('type')!='session_meta':return {}
            p=obj.get('payload') or {}
            if not isinstance(p,dict):return {}
            source=p.get('source');spawn={}
            if isinstance(source,dict):
                sub=source.get('subagent') or {};spawn=sub.get('thread_spawn') or {} if isinstance(sub,dict) else {}
            if not isinstance(spawn,dict):spawn={}
            return {k:str(v)[:300] for k,v in {'parent':spawn.get('parent_thread_id') or p.get('parent_thread_id'),
                    'fork':p.get('forked_from_id'),'agent_role':spawn.get('agent_role') or p.get('agent_role'),
                    'agent_name':spawn.get('agent_nickname') or spawn.get('agent_path')}.items() if isinstance(v,str)}
        except (OSError,ValueError,TypeError):return {}
    def related(self,sid,cursor=0):
        self.metadata(sid);ids=sorted(self.meta);cursor=max(0,int(cursor));part=ids[cursor:cursor+128]
        current=self.session_header(sid);result=[]
        def item(key,relation,header=None):return {'id':key,'title':self.titles.get(key,''),'relation':relation,'agent_role':(header or {}).get('agent_role','')}
        if cursor==0:
            for kind,relation in [('parent','Parent'),('fork','Fork origin')]:
                key=current.get(kind)
                if key and key!=sid and key in self.meta:result.append(item(key,relation,self.session_header(key)))
        for key in part:
            if key==sid:continue
            header=self.session_header(key)
            if header.get('parent')==sid:result.append(item(key,'Child agent',header))
            elif header.get('fork')==sid:result.append(item(key,'Fork',header))
        return {'sessions':result,'next_cursor':cursor+len(part) if cursor+len(part)<len(ids) else None,'checked':len(part)}
