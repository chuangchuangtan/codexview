"""Build the standalone standard-library executable from canonical sources."""
from pathlib import Path
import ast, hashlib
ROOT = Path(__file__).resolve().parent.parent

def build():
    s = (ROOT / 'src/server.py').read_text(encoding='utf-8')
    assets = {'STYLE': (ROOT/'src/web/style.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/web/studio.css').read_text(encoding='utf-8'),
              'READER': (ROOT/'src/web/reader.js').read_text(encoding='utf-8'),
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
