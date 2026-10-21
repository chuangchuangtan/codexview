"""Opt-in, bounded, read-only access to generated reports. No directory scanning."""
import posixpath
import stat
from html.parser import HTMLParser

DOCUMENT_TYPES={'.md':'text/plain; charset=utf-8','.markdown':'text/plain; charset=utf-8',
                '.html':'text/html; charset=utf-8','.htm':'text/html; charset=utf-8'}
RESOURCE_TYPES={'.css':'text/css; charset=utf-8','.png':'image/png','.jpg':'image/jpeg',
                '.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp','.ico':'image/x-icon'}
REPORT_CSP="default-src 'none'; script-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'none'; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'; sandbox"

class ReportError(ValueError):
    def __init__(self,message,status=403):super().__init__(message);self.status=status

class ReportFiles:
    def __init__(self,home,roots=None):
        self.home=Path(home).resolve();self.roots=[]
        for value in roots or []:
            root=Path(value).expanduser().resolve()
            if root==Path(root.anchor) or root==self.home or self.home in root.parents or not root.is_dir():
                raise ValueError('Choose an existing project report directory, outside Codex data: '+str(root))
            if root not in self.roots:self.roots.append(root)
        self.bytes_read=0
    def locate(self,value,sid=None,store=None):
        if not self.roots:raise ReportError('File reading is not enabled. Restart with --file-root /path/to/project/reports.')
        if not value or len(value)>4096 or '\x00' in value or '\\' in value:raise ReportError('Invalid report path',400)
        path=Path(value)
        if not path.is_absolute():
            if not sid or store is None:raise ReportError('Use an absolute server path for this report.',400)
            meta=store.metadata(sid)
            if meta['adapter']!='native-jsonl':raise ReportError('Relative paths need a Native session working directory.',400)
            # A Native session_meta record is first. Never index or scan the rollout for links.
            first=pread(Path(meta['path']),0,65536).split(b'\n',1)[0]
            try:
                obj=json.loads(first);cwd=obj['payload']['cwd'] if obj.get('type')=='session_meta' else None
            except (ValueError,KeyError,TypeError):cwd=None
            if not cwd or not Path(cwd).is_absolute():raise ReportError('No working directory found. Use an absolute server path.',400)
            path=Path(cwd)/path
        path=Path(os.path.abspath(str(path)))
        if path==self.home or self.home in path.parents:raise ReportError('Codex-owned data cannot be opened as a report.')
        for index,root in enumerate(self.roots):
            try:rel=path.relative_to(root)
            except ValueError:continue
            if not rel.parts or any(part.startswith('.') for part in rel.parts):raise ReportError('Hidden files and directories are not shared.')
            return index,rel,path
        raise ReportError('This file is outside the configured --file-root directories.')
    def read(self,value,sid=None,store=None,document=False):
        index,rel,path=self.locate(value,sid,store)
        suffix=path.suffix.lower();types=DOCUMENT_TYPES if document else dict(DOCUMENT_TYPES,**RESOURCE_TYPES)
        if suffix not in types:raise ReportError('Only Markdown, HTML, CSS and supported raster images can be read.',415)
        limit=(2 if suffix in ('.md','.markdown') else 4 if suffix in ('.html','.htm') else 1 if suffix=='.css' else 16)*1024*1024
        # Walk from / using directory descriptors: no symlink or FIFO/device traversal,
        # including parent replacement between checking a path and opening the file.
        fd=None
        try:
            fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|getattr(os,'O_CLOEXEC',0))
            for part in path.parts[1:-1]:
                child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0),dir_fd=fd)
                os.close(fd);fd=child
            leaf=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|getattr(os,'O_CLOEXEC',0),dir_fd=fd)
            os.close(fd);fd=leaf;st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):raise ReportError('Only regular report files can be read.')
            if st.st_size>limit:raise ReportError('File exceeds the preview limit (%d MiB).'%(limit//1024//1024),413)
            data=bytearray()
            while len(data)<=limit:
                chunk=os.read(fd,min(65536,limit+1-len(data)))
                if not chunk:break
                data.extend(chunk)
            if len(data)>limit:raise ReportError('File grew beyond the preview limit.',413)
            self.bytes_read+=len(data)
        except FileNotFoundError:raise ReportError('Report not found on this server.',404)
        except OSError:raise ReportError('Cannot read this report. Symlinks and special files are not allowed.')
        finally:
            if fd is not None:os.close(fd)
        raw='/files/raw/'+str(index)+'/'+urllib.parse.quote(rel.as_posix(),safe='/')
        return {'path':str(path),'name':path.name,'kind':'html' if suffix in ('.html','.htm') else 'markdown',
                'type':types[suffix],'raw_url':raw,'size':len(data)},bytes(data)
    def raw_path(self,index,relative):
        if index<0 or index>=len(self.roots):raise ReportError('Unknown report directory.',404)
        path=Path(os.path.abspath(str(self.roots[index]/relative)))
        try:path.relative_to(self.roots[index])
        except ValueError:raise ReportError('Path escapes the report directory.')
        return str(path)

class StaticReport(HTMLParser):
    """Keep passive report layout. URL-bearing attributes use the bounded file routes."""
    tags=set('html head title body main header footer nav section article aside div span p h1 h2 h3 h4 h5 h6 pre code blockquote ul ol li dl dt dd table thead tbody tfoot tr th td caption colgroup col figure figcaption picture img a b strong i em s del u small sub sup br hr details summary style link time mark abbr'.split())
    void={'img','br','hr','link','col'}
    blocked={'script','iframe','object','embed','svg','math','template','noscript','textarea','xmp','plaintext'}
    attrs=set('id class title style lang dir role alt width height colspan rowspan scope datetime start reversed open media'.split())
    def __init__(self,raw_url):super().__init__(convert_charrefs=True);self.base=raw_url;self.out=[];self.skip=[];self.in_style=False
    def url(self,value,kind):
        u=urllib.parse.urlsplit(value)
        if u.scheme or u.netloc or u.query or '\\' in value:return None
        if not u.path:return '#'+urllib.parse.quote(u.fragment) if u.fragment and kind=='link' else None
        path=urllib.parse.unquote(u.path)
        if path.startswith('/'):return None
        target=posixpath.normpath(posixpath.join(posixpath.dirname(urllib.parse.unquote(self.base)),path))
        prefix='/'.join(self.base.split('/')[:4])+'/'
        if not target.startswith(prefix) or any(p.startswith('.') for p in target[len(prefix):].split('/')):return None
        suffix=Path(target).suffix.lower()
        if suffix not in (RESOURCE_TYPES if kind=='asset' else DOCUMENT_TYPES):return None
        return urllib.parse.quote(target,safe='/')+('#'+urllib.parse.quote(u.fragment) if u.fragment else '')
    def handle_starttag(self,tag,attrs):
        if self.skip:
            if tag in self.blocked and tag not in ('embed',):self.skip.append(tag)
            return
        if tag in self.blocked:
            if tag!='embed':self.skip.append(tag)
            return
        if tag not in self.tags:return
        if tag=='style':self.in_style=True
        values=dict(attrs);clean=[]
        for name,value in attrs:
            if value is None:value=''
            if name in self.attrs or name.startswith('aria-'):
                clean.append((name,value))
        if tag=='img':
            src=self.url(values.get('src',''),'asset')
            if not src:return
            clean.extend([('src',src),('loading','lazy'),('decoding','async')])
        elif tag=='a':
            href=self.url(values.get('href',''),'link')
            if href:clean.append(('href',href))
        elif tag=='link':
            href=self.url(values.get('href',''),'asset')
            if values.get('rel','').lower()!='stylesheet' or not href or not urllib.parse.urlsplit(href).path.lower().endswith('.css'):return
            clean.extend([('rel','stylesheet'),('href',href)])
        self.out.append('<'+tag+''.join(' '+k+'="'+html.escape(v,quote=True)+'"' for k,v in clean)+'>')
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.void:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        if self.skip:
            if tag==self.skip[-1]:self.skip.pop()
            return
        if tag=='style':self.in_style=False
        if tag in self.tags and tag not in self.void:self.out.append('</'+tag+'>')
    def handle_data(self,data):
        if not self.skip:self.out.append(data if self.in_style else html.escape(data))

def static_report(text,raw_url):
    parser=StaticReport(raw_url);parser.feed(text);parser.close()
    return '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>img{max-width:100%;height:auto}body{overflow-wrap:anywhere}</style>'+''.join(parser.out)

def document_html(value,sid=''):
    model=json.dumps({'path':value,'sid':sid},ensure_ascii=False).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Report · CodexView</title><style>'''+CSS+'''
body{margin:0}.filebar{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:12px;padding:12px 20px;border-bottom:1px solid var(--line);background:var(--bg);flex-wrap:wrap}.filebrand{font-weight:700}.filebar button,.filebar a{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--p);color:inherit;text-decoration:none;cursor:pointer}.filebar button[aria-pressed=true]{outline:2px solid #709ce8}.filepath{overflow-wrap:anywhere;font-size:12px;color:var(--m);flex-basis:100%}.filemessage{padding:16px 24px;margin:0;color:var(--m);font-size:13px}.filecontent{max-width:1000px;margin:auto;padding:16px 28px 60px}.filecontent pre{white-space:pre-wrap;overflow-wrap:anywhere}.fileframe{display:block;width:100%;height:calc(100dvh - 160px);border:0;background:white}.filehidden{display:none!important}@media(max-width:600px){.filecontent{padding:12px 16px}.filebar{gap:8px;padding:10px}.filebar button,.filebar a{font-size:12px}}
</style></head><body><header class="filebar"><a id="fileBack" href="/">← Sessions</a><span class="filebrand">CodexView · Report</span><span class="grow"></span><button id="fileRendered" aria-pressed="true">Read</button><button id="fileSource" aria-pressed="false">Source</button><button id="fileRefresh">↻ Refresh</button><button id="fileTheme" aria-label="Toggle theme">◐</button><span id="filePath" class="filepath"></span></header><p id="fileMessage" class="filemessage" role="status">Loading report…</p><main id="fileContent" class="filecontent md"></main><iframe id="fileFrame" class="fileframe filehidden" sandbox="" referrerpolicy="no-referrer" title="Isolated static HTML report"></iframe><script id="fileModel" type="application/json">'''+model+'''</script><script>'''+__ASSET_MARKDOWN__+'\n'+__ASSET_FILE_JS__+'''</script></body></html>'''
