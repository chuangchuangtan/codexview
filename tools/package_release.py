"""Create deterministic public release artifacts from an explicit allowlist."""
from pathlib import Path
import ast
import gzip
import hashlib
import io
import json
import shutil
import tarfile
import zipfile
from build import build, ROOT

FILES = [
    'codexview', 'README.md', 'README.zh-CN.md', 'LICENSE', 'SECURITY.md',
    'CONTRIBUTING.md', 'CHANGELOG.md', 'package.json', 'package-lock.json',
    '.gitignore', 'tools/build.py', 'tools/package_release.py', 'tools/benchmark.py', 'tools/demo.py',
]
DIRS = ['src', 'docs', '.github', 'tests']
SUFFIXES = {'.py', '.js', '.css', '.html', '.md', '.json', '.yml', '.cjs', '.mjs', '.png'}
# Fixed archive timestamps, no workstation identity or filesystem timestamps.
ZIP_EPOCH = (2020, 1, 1, 0, 0, 0)


def public_files():
    files = [ROOT / name for name in FILES]
    for directory in DIRS:
        files.extend(path for path in (ROOT / directory).rglob('*')
                     if path.is_file() and not any(part in ('__pycache__', 'node_modules', '.git') for part in path.parts)
                     and path.suffix in SUFFIXES and not any(part.startswith('.')
                         for part in path.relative_to(ROOT / directory).parts))
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing or redirected release input: ' + str(path))
        # Also reject symlinked parent directories.
        if path.resolve() != path:
            raise ValueError('Redirected release directory: ' + str(path))
    return sorted(set(files))


def package():
    executable = build()
    tree = ast.parse((ROOT / 'src/server.py').read_text(encoding='utf-8'))
    version = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == 'VERSION'
                       for target in node.targets))
    prefix = 'codexview-' + version
    files = public_files()
    dist = ROOT / 'dist'
    if dist.is_symlink():
        raise ValueError('Redirected release output directory')
    dist.mkdir(exist_ok=True)
    archive = dist / (prefix + '.tar.gz')
    source_zip = dist / (prefix + '.zip')
    standalone = dist / prefix
    source_prefix = prefix + '-source'
    standalone.write_bytes(executable.read_bytes())
    standalone.chmod(0o755)

    # Build neutral tar headers ourselves instead of inheriting host uid/gid/uname.
    with archive.open('wb') as output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                for path in files:
                    data = path.read_bytes()
                    info = tarfile.TarInfo(source_prefix + '/' + path.relative_to(ROOT).as_posix())
                    info.size = len(data)
                    info.mode = 0o755 if path == executable else 0o644
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    tar.addfile(info, io.BytesIO(data))
    with zipfile.ZipFile(source_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in files:
            name = source_prefix + '/' + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = ((0o100755 if path == executable else 0o100644) << 16)
            output.writestr(info, path.read_bytes())

    # A clean upload directory: never publish the parent workspace wholesale.
    clean = dist / source_prefix
    if clean.exists():
        if clean.is_symlink() or not clean.is_dir():
            raise ValueError('Invalid generated upload directory')
        shutil.rmtree(clean)
    clean.mkdir()
    manifest = {}
    for path in files:
        relative = path.relative_to(ROOT)
        target = clean / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        target.chmod(0o755 if path == executable else 0o644)
        manifest[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = dist / (prefix + '.manifest.json')
    manifest_path.write_text(json.dumps({'version': version, 'files': manifest},
                                     ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    artifacts = [standalone, archive, source_zip, manifest_path]
    checksums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                        for path in artifacts)
    (dist / 'SHA256SUMS').write_text(checksums, encoding='utf-8')
    return artifacts


if __name__ == '__main__':
    for artifact in package():
        print(artifact)
