"""Build the standalone standard-library executable from canonical sources."""
from pathlib import Path
import ast, hashlib
ROOT = Path(__file__).resolve().parent.parent

def build():
    s = (ROOT / 'src/server.py').read_text(encoding='utf-8')
    s = s.replace('__DOCUMENTS__', (ROOT/'src/documents.py').read_text(encoding='utf-8'))
    for marker,name in [('__NAVIGATION__','navigation.py'),('__SEARCH_CACHE__','search_cache.py')]:
        s=s.replace(marker,(ROOT/'src'/name).read_text(encoding='utf-8'))
    assets = {'STYLE': (ROOT/'src/web/style.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/studio.css').read_text(encoding='utf-8'),
              'READER': (ROOT/'src/web/markdown.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/reading.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/reader-window.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/reader.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/reader-features.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/media.js').read_text(encoding='utf-8'),
              'MARKDOWN': (ROOT/'src/web/markdown.js').read_text(encoding='utf-8'),
              'FILE_JS': (ROOT/'src/web/file.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/media.js').read_text(encoding='utf-8'),
              'HOME': (ROOT/'src/web/home.html').read_text(encoding='utf-8'),
              'HOME_JS': (ROOT/'src/web/home.js').read_text(encoding='utf-8')}
    for key, value in assets.items():
        marker = '__ASSET_'+key+'__'
        assert marker in s, marker
        s = s.replace(marker, repr(value))
    ast.parse(s)
    out = ROOT/'codexview'
    out.write_text(s,encoding='utf-8');out.chmod(0o755)
    return out
if __name__=='__main__':
    p=build();print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
